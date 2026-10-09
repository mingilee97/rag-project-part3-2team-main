"""같은 검색 context와 메인 answer/verify를 Linux VM GPU에서 평가한다. CPU 기록과 분리한다."""
import argparse
from collections import Counter
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
from vm_service import VMService, DIGEST, OLLAMA_VERSION, choose_question_indices
from rfp_rag import answer as A, providers
from langchain_core.documents import Document


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.new')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    os.replace(temporary, path)


def literal_recall(answer, facts):
    def normalize(text): return ''.join(text.lower().split()).replace(',', '')
    text = normalize(answer)
    return sum(any(normalize(alt) in text for alt in fact.split('|')) for fact in facts)/len(facts) if facts else None


class OutputSchemaError(ValueError): pass
class OutputLengthError(RuntimeError): pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', required=True, type=Path)
    parser.add_argument('--retrieval-run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-url', default='http://127.0.0.1:11435')
    parser.add_argument('--execution-environment', choices=['vm', 'colab'], required=True)
    parser.add_argument('--scope', choices=['pilot4', 'full'], default='pilot4')
    parser.add_argument('--guard-file', type=Path)
    args = parser.parse_args()
    service = VMService(args.base_url, args.execution_environment)
    output = args.output.resolve()
    if output.is_relative_to(REPOSITORY) and not output.is_relative_to(REPOSITORY/'data'):
        raise ValueError('문항별 답변은 저장소 밖 또는 Git에서 제외한 data 아래에 저장하세요')
    output.mkdir(parents=True, exist_ok=True)
    private = output/'items.local'; private.mkdir(exist_ok=True)
    if (output/'STOP_REQUEST.local').exists(): raise SystemExit('생성 보류 표시를 유지합니다')
    questions = [json.loads(x) for x in args.questions.read_text(encoding='utf-8').splitlines() if x]
    source_plan = read(args.retrieval_run/'plan.local.json')
    assert len(questions) == 168 and source_plan['corpus_documents'] == 100
    assert sha(args.questions) == source_plan['questions_sha256']
    selected = choose_question_indices(questions, args.scope)
    order = ['main_dense_top5', 'candidate_bge_top5', 'candidate_bge_parent4_pool20']
    items = [(qi*3+ti, qi, questions[qi], title) for qi in selected for ti, title in enumerate(order)]
    provenance = {'schema': 'vm-gpu-answer-component-v1', 'scope': args.scope,
        'component': 'main answer.answer + verify=True', 'transport': 'Linux loopback Ollama REST GPU',
        'execution_environment_claimed': args.execution_environment, 'Windows_and_WSL_execution_rejected': True,
        'registration_guard_removed': False, 'registered_07_verify_pipeline_run': False,
        'route_metadata_enrichment_retrieval_gate': False,
        'source_answer_sha256': sha(REPOSITORY/'rfp_rag/answer.py'), 'evaluator_sha256': sha(Path(__file__)),
        'source_answer_sha256_lf': hashlib.sha256((REPOSITORY/'rfp_rag/answer.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        'system_prompt_sha256': hashlib.sha256(A.SYSTEM.encode('utf-8')).hexdigest(),
        'JSON_schema_sha256': hashlib.sha256(json.dumps(A.SCHEMA, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest(),
        'transport_sha256': sha(REPOSITORY/'evaluation/vm_service.py'),
        'CPU_transport_sha256': sha(REPOSITORY/'evaluation/cpu_service.py'),
        'source_retrieval_plan_sha256': sha(args.retrieval_run/'plan.local.json'),
        'questions_sha256': sha(args.questions), 'registered_guard_sha256': sha(args.guard_file) if args.guard_file else None,
        'model': service.model, 'model_digest': DIGEST, 'ollama_version': OLLAMA_VERSION,
        'quantization': 'Q4_K_M', 'num_ctx': 8192, 'num_predict': 1500, 'num_gpu': 999, 'num_thread': 4,
        'seed': 42, 'temperature': 0, 'judge_calls': 0, 'paid_API_calls': 0,
        'GPU_50_percent_utilization_or_VRAM_limit_guaranteed': False,
        'output_raw_answers_private_only': True, 'items': len(items),
        'pilot_selection': 'first question from first four distinct projects before observing results' if args.scope == 'pilot4' else None,
        'strict_error_policy': ['transport_or_model_protocol_failures', 'invalid_JSON_schema', 'length_stop', 'GPU_observation_failure']}
    plan = output/'plan.json'
    if plan.exists(): assert read(plan) == provenance, '같은 코드·입력·GPU 조건일 때만 재개할 수 있습니다'
    else: save(plan, provenance)
    # 모델/서버 불일치는 질문 실패504개로 변환하지 않고 실행 준비 오류로 중단한다.
    service.verify_protocol()
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
    # CPU 원본과 등록 가드는 보존하며 이 GPU 평가 프로세스에서만 transport를 주입한다.
    providers.get_llm = lambda *a, **kw: Transport()
    started = time.perf_counter()
    for completed, (index, qi, q, treatment) in enumerate(items):
        target = private/f'{index:03d}.json'
        if (output/'STOP_REQUEST.local').exists(): raise SystemExit('생성 중단 표시를 확인했습니다')
        variant = 'main_fixed1000_200' if treatment.startswith('main') else 'minhyup_child1000_200'
        source = args.retrieval_run/'items.local'/f'{qi:03d}-{variant}.json'
        if target.exists():
            old = read(target)
            assert (old['index'] == index and old['question_id'] == q['id'] and old['treatment'] == treatment
                    and source.is_file() and old['source_retrieval_item_sha256'] == sha(source)), '완료 항목의 입력이 달라 재개할 수 없습니다'
            continue
        while not source.exists():
            save(output/'progress.local.json', {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
                'phase': 'waiting_for_retrieval_checkpoint', 'completed': completed, 'total': len(items)})
            if (output/'STOP_REQUEST.local').exists(): raise SystemExit('생성 중단 표시를 확인했습니다')
            time.sleep(60)
        source_item = read(source)
        assert source_item['question_id'] == q['id'] and source_item['question_index'] == qi
        context = next(c for c in source_item['contexts'] if c['treatment'] == treatment)
        docs = [Document(page_content=body, metadata={'doc_id': ident}) for ident, body in context['bodies']]
        calls.clear(); failures.clear(); raw_outputs.clear(); tick = time.perf_counter()
        try:
            result = A.answer(q['question'], docs, {}, verify=True)
            if failures or not calls: raise RuntimeError('GPU transport 실패 또는 성공 호출 누락')
            for raw in raw_outputs:
                parsed = json.loads(raw)
                if (not isinstance(parsed, dict) or not isinstance(parsed.get('answer'), str)
                    or not isinstance(parsed.get('found'), bool) or not isinstance(parsed.get('evidence_ids'), list)
                    or any(type(i) is not int for i in parsed['evidence_ids'])):
                    raise OutputSchemaError('모델 출력 JSON 스키마가 맞지 않습니다')
            if any(c.get('done_reason') == 'length' for c in calls): raise OutputLengthError('출력 한도에서 생성이 중단됐습니다')
            record = {'index': index, 'question_id': q['id'], 'treatment': treatment, 'answer': result['answer'],
                'found': result['found'], 'calls': list(calls), 'status': 'success', 'judge': None,
                'source_retrieval_item_sha256': sha(source),
                'unsupported_final_count': len(A.unsupported(result['answer'], '\n'.join(d.page_content for d in docs))),
                'literal_required_fact_recall': literal_recall(result['answer'], q.get('required_facts') or []),
                'wall_seconds': time.perf_counter()-tick}
        except Exception as error:
            # 오류 원문은 비공개 본문을 포함할 수 있으므로 유형만 저장한다.
            record = {'index': index, 'question_id': q['id'], 'treatment': treatment, 'status': 'error',
                'error_type': type(error).__name__, 'transport_error_types': list(failures), 'calls': list(calls),
                'source_retrieval_item_sha256': sha(source), 'judge': None, 'wall_seconds': time.perf_counter()-tick}
        save(target, record)
        progress = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(), 'phase': 'generation',
            'completed': completed+1, 'total': len(items), 'status': record['status'], 'treatment': treatment,
            'seconds_once': record['wall_seconds'], 'elapsed_seconds_this_invocation': time.perf_counter()-started}
        save(output/'progress.local.json', progress)
        print(json.dumps(progress), flush=True)
        if (output/'STOP_REQUEST.local').exists(): raise SystemExit('생성 중단 표시를 확인했습니다')
    rows = [read(private/f'{index:03d}.json') for index, *_ in items]
    assert len(rows) == len(items)
    aggregates = []
    for treatment in order:
        local = [r for r in rows if r['treatment'] == treatment]
        ok = [r for r in local if r['status'] == 'success']
        facts = [r['literal_required_fact_recall'] for r in ok if r['literal_required_fact_recall'] is not None]
        prompt_counts = [r['calls'][0]['prompt_eval_count'] for r in ok
                         if type(r['calls'][0].get('prompt_eval_count')) is int]
        aggregates.append({'treatment': treatment, 'total': len(local), 'successful': len(ok), 'errors': len(local)-len(ok),
            'error_types': dict(Counter(r['error_type'] for r in local if r['status'] == 'error')),
            'found_true': sum(r['found'] for r in ok), 'unsupported_final_answers': sum(r['unsupported_final_count'] > 0 for r in ok),
            'mean_wall_seconds_successes': sum(r['wall_seconds'] for r in ok)/len(ok) if ok else None,
            'prompt_eval_count_mean': sum(prompt_counts)/len(prompt_counts) if prompt_counts else None,
            'prompt_count_observed_successes': len(prompt_counts),
            'regenerated_questions': sum(len(r['calls']) > 1 for r in ok),
            'literal_required_fact_recall_macro': sum(facts)/len(facts) if facts else None, 'judge_score': None})
    observed = [c['observed_size_vram_bytes'] for r in rows for c in r['calls']]
    save(output/'aggregate.json', {'schema': provenance['schema'], 'completed_utc': datetime.now(timezone.utc).isoformat(),
        'scope': args.scope, 'provenance': provenance, 'aggregates': aggregates,
        'GPU_observations': {'successful_call_checks': len(observed), 'all_observed_positive': bool(observed) and all(v > 0 for v in observed),
            'maximum_observed_size_vram_bytes': max(observed) if observed else None,
            'not_peak_device_memory_or_utilization_limit_proof': True},
        'final_model_selection': 'pending', 'limits': ['not_full_route07verify_pipeline', 'no_independent_semantic_judge',
            'rule_check_and_literal_recall_not_semantic_accuracy', 'failed_generation_not_zero_score',
            'CPU_GPU_timing_not_direct_algorithm_comparison', 'GPU_numerical_outputs_may_differ_from_CPU',
            'o200k_budget_not_formally_EXAONE_tokenizer_fit']})
    service.unload()
    print(json.dumps({'completed': True, 'scope': args.scope, 'aggregates': aggregates}))


if __name__ == '__main__': main()
