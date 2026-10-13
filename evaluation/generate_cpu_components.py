"""같은 검색 체크포인트의 메인 answer/verify를 CPU에서 비교한다. 별도 evaluator v2."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))
from cpu_service import CPUService
from rfp_rag import answer as A, providers
from langchain_core.documents import Document


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def literal_recall(answer, facts):
    def normalize(text): return ''.join(text.lower().split()).replace(',', '')
    text = normalize(answer)
    return sum(any(normalize(alt) in text for alt in fact.split('|')) for fact in facts) / len(facts) if facts else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', required=True, type=Path)
    parser.add_argument('--retrieval-run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:11435')
    parser.add_argument('--guard-file', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(REPOSITORY) and not output.is_relative_to(REPOSITORY / 'data'):
        raise ValueError('질문별 답변은 저장소 밖 또는 Git에서 제외한 data 아래에 저장하세요')
    output.mkdir(parents=True, exist_ok=True)
    private = output / 'items.local'; private.mkdir(exist_ok=True)
    questions = [json.loads(x) for x in args.questions.read_text(encoding='utf-8').splitlines() if x]
    source_plan = read(args.retrieval_run / 'plan.local.json')
    assert len(questions) == 168 and source_plan['corpus_documents'] == 100
    assert sha(args.questions) == source_plan['questions_sha256']
    order = ['main_dense_top5', 'candidate_bge_top5', 'candidate_bge_parent4_pool20']
    items = [(qi, q, title) for qi, q in enumerate(questions) for title in order]
    service = CPUService(args.base_url)
    provenance = {'schema': 'cpu-answer-component-v2', 'component': 'main answer.answer + verify=True',
        'CPU_transport_only_in_memory': True, 'registration_guard_removed': False,
        'registered_07_verify_pipeline_run': False, 'route_metadata_enrichment_retrieval_gate': False,
        'source_answer_sha256': sha(REPOSITORY / 'rfp_rag/answer.py'), 'evaluator_sha256': sha(Path(__file__)),
        'source_retrieval_plan_sha256': sha(args.retrieval_run / 'plan.local.json'),
        'questions_sha256': sha(args.questions), 'registered_guard_sha256': sha(args.guard_file) if args.guard_file else None,
        'model': service.model, 'num_ctx': 8192, 'num_predict': 1500, 'num_gpu': 0, 'num_thread': 4,
        'seed': 42, 'temperature': 0, 'judge_calls': 0, 'paid_calls': 0,
        'output_raw_answers_private_only': True, 'items': len(items),
        'strict_error_policy': ['transport_failures_even_if_main_generate_catches_them', 'invalid_JSON_schema', 'length_stop', 'CPU_verification_failure']}
    plan = output / 'plan.json'
    if plan.exists(): assert read(plan) == provenance, '같은 evaluator와 입력일 때만 재개할 수 있습니다'
    else: save(plan, provenance)
    calls, failures, raw_outputs = [], [], []
    class Transport:
        def invoke(self, messages):
            roles = {'human': 'user', 'system': 'system'}
            try:
                raw, info = service.chat([{'role': roles[r], 'content': text} for r, text in messages], A.SCHEMA)
            except Exception as error:
                failures.append(type(error).__name__)
                raise
            raw_outputs.append(raw); calls.append(info)
            return SimpleNamespace(content=raw)
    # 원본 공급 함수와 파일은 보존한다. 평가 프로세스 안에서만 CPU transport를 주입한다.
    providers.get_llm = lambda *a, **kw: Transport()
    started = time.perf_counter()
    for index, (qi, q, treatment) in enumerate(items):
        target = private / f'{index:03d}.json'
        if target.exists(): continue
        variant = 'main_fixed1000_200' if treatment.startswith('main') else 'minhyup_child1000_200'
        source = args.retrieval_run / 'items.local' / f'{qi:03d}-{variant}.json'
        while not source.exists():
            save(output / 'progress.local.json', {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                'phase': 'waiting_for_retrieval_checkpoint', 'completed': index, 'total': len(items)})
            if (output / 'STOP_REQUEST.local').exists(): raise SystemExit('사용자가 로컬 중단 표시를 남겼습니다')
            time.sleep(60)
        source_item = read(source)
        assert source_item['question_id'] == q['id'] and source_item['question_index'] == qi
        context = next(c for c in source_item['contexts'] if c['treatment'] == treatment)
        docs = [Document(page_content=body, metadata={'doc_id': ident}) for ident, body in context['bodies']]
        calls.clear(); failures.clear(); raw_outputs.clear(); tick = time.perf_counter()
        try:
            result = A.answer(q['question'], docs, {}, verify=True)
            if failures or not calls: raise RuntimeError('CPU transport 실패 또는 성공 호출 누락')
            for raw in raw_outputs:
                parsed = json.loads(raw)
                if not isinstance(parsed.get('answer'), str) or not isinstance(parsed.get('found'), bool) or not isinstance(parsed.get('evidence_ids'), list):
                    raise ValueError('모델 출력 JSON 스키마가 맞지 않습니다')
            if any(c.get('done_reason') == 'length' for c in calls): raise RuntimeError('출력 한도에서 생성이 중단됐습니다')
            record = {'index': index, 'question_id': q['id'], 'treatment': treatment, 'answer': result['answer'],
                'found': result['found'], 'calls': list(calls), 'status': 'success', 'judge': None,
                'unsupported_final_count': len(A.unsupported(result['answer'], '\n'.join(d.page_content for d in docs))),
                'literal_required_fact_recall': literal_recall(result['answer'], q.get('required_facts') or []),
                'wall_seconds': time.perf_counter() - tick}
        except Exception as error:
            # 예외 원문은 질문·본문을 포함할 수 있다. 오류 유형만 저장한다.
            record = {'index': index, 'question_id': q['id'], 'treatment': treatment, 'status': 'error',
                'error_type': type(error).__name__, 'transport_error_types': list(failures), 'calls': list(calls),
                'judge': None, 'wall_seconds': time.perf_counter() - tick}
        save(target, record)
        progress = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(), 'phase': 'generation',
            'completed': index + 1, 'total': len(items), 'status': record['status'], 'treatment': treatment,
            'seconds_once': record['wall_seconds'], 'elapsed_seconds_this_invocation': time.perf_counter() - started}
        save(output / 'progress.local.json', progress)
        print(json.dumps(progress), flush=True)
        if (output / 'STOP_REQUEST.local').exists(): raise SystemExit('사용자가 로컬 중단 표시를 남겼습니다')
    rows = [read(f) for f in sorted(private.glob('*.json'))]
    assert len(rows) == 504
    aggregate = []
    for treatment in order:
        local = [r for r in rows if r['treatment'] == treatment]
        ok = [r for r in local if r['status'] == 'success']
        facts = [r['literal_required_fact_recall'] for r in ok if r['literal_required_fact_recall'] is not None]
        aggregate.append({'treatment': treatment, 'total': len(local), 'successful': len(ok), 'errors': len(local)-len(ok),
            'found_true': sum(r['found'] for r in ok), 'unsupported_final_answers': sum(r['unsupported_final_count'] > 0 for r in ok),
            'mean_wall_seconds_successes': sum(r['wall_seconds'] for r in ok)/len(ok) if ok else None,
            'prompt_eval_count_mean': sum(r['calls'][0]['prompt_eval_count'] for r in ok)/len(ok) if ok else None,
            'regenerated_questions': sum(len(r['calls']) > 1 for r in ok),
            'literal_required_fact_recall_macro': sum(facts)/len(facts) if facts else None, 'judge_score': None})
    save(output / 'aggregate.json', {'schema': provenance['schema'], 'completed_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'full100retrievalboundedanswercomponent', 'provenance': provenance, 'aggregates': aggregate,
        'VRAM_checks': {'checks': len(service.vram_checks), 'all_observed_size_vram_zero': True},
        'final_model_selection': 'pending', 'limits': ['not_full_route07verify_pipeline', 'no_independent_semantic_judge',
            'rule_check_and_literal_recall_not_semantic_accuracy', 'failed_generation_not_zero_score',
            'successful_found_false_may_be_retrieval_failure', 'o200k_budget_not_formally_EXAONE_tokenizer_fit']})
    service.unload()
    print(json.dumps({'completed': True, 'aggregates': aggregate}))


if __name__ == '__main__': main()
