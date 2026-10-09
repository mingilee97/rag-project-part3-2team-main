"""승인된 100문서 CPU 비교. 원본을 보존하고 배치·문항별 체크포인트에서 재개한다."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

sys.dont_write_bytecode = True
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                  CUDA_VISIBLE_DEVICES='', TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='4',
                  MKL_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4')
import argparse
REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / 'candidates/minhyup/10882e3'))
parser = argparse.ArgumentParser(description='같은 100문서·168질문의 CPU 검색 비교. 비공개 재현 자산은 별도 제공해야 합니다.')
for name in ['docs', 'questions', 'reference', 'prior-results', 'prior-alignment', 'prior-vectors', 'query-vectors', 'kure-snapshot', 'bge-snapshot', 'output']:
    parser.add_argument('--' + name, required=True, type=Path)
parser.add_argument('--guard-file', type=Path)
ARGS = parser.parse_args()
ROOT = ARGS.output.resolve()
if ROOT.is_relative_to(REPOSITORY) and not ROOT.is_relative_to(REPOSITORY / 'data'):
    raise ValueError('평가 원문·벡터·응답은 저장소 밖 또는 Git에서 제외한 data 아래에 저장하세요')
import socket
def no_network(*args, **kwargs):
    raise RuntimeError('CPU 검색 비교는 외부 통신을 사용하지 않습니다')
socket.socket.connect = no_network
socket.create_connection = no_network
from components import build, bounded, coverage, anchors, facts, covered, alignment, test_helpers
from langchain_core.documents import Document
from rag_reranking import rerank_children
from rag_context import count_tokens
import numpy as np

RUN = ROOT
RUN.mkdir(parents=True, exist_ok=True)


def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))


def save(p, value):
    p = Path(p)
    temp = p.with_suffix(p.suffix + '.new')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, p)


def event(**values):
    item = {'utc': now(), 'pid': os.getpid(), **values}
    save(RUN / 'progress.local.json', item)
    with (RUN / 'events.local.jsonl').open('a', encoding='utf-8') as out:
        out.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(json.dumps(item, ensure_ascii=False), flush=True)


def treatments(q, name, source_chunks, detail, parent_docs, by_id, order, scores, model):
    kind = 'main' if name.startswith('main') else 'candidate'
    pool = []
    for index in order:
        chunk = source_chunks[int(index)]
        d = detail[(kind, chunk['chunk_id'])]
        pid = f"{d['parent_key'][0]}|{d['parent_key'][1]}" if kind == 'candidate' else chunk['chunk_id']
        body = parent_docs[pid].page_content[d['start']:d['end']] if kind == 'candidate' else chunk['text']
        if kind == 'main':
            doc = by_id[chunk['doc_id']]
            prefix = f"[{doc['agency']}] {doc['title']}\n"
            assert body.startswith(prefix)
            body = body[len(prefix):]
        pool.append(Document(page_content=body, metadata={'doc_id': chunk['doc_id'], 'source': d['source'],
            'section_title': d['section_title'], 'parent_id': pid, 'chunk_id': chunk['chunk_id'],
            'start_index': d['start'], 'end_index': d['end'], 'pages': d.get('pages', []),
            'retrieval_score': float(scores[int(index)])}))
    start = time.perf_counter()
    ranked = rerank_children(q['question'], pool, model=model, candidate_k=20)
    elapsed = time.perf_counter() - start
    out = [(kind + '_dense_top5', pool[:5], 4000), (kind + '_bge_top5', ranked[:5], 4000)]
    if kind == 'candidate':
        for title, children in [('candidate_dense_parent4_pool20', pool), ('candidate_bge_parent4_pool20', ranked)]:
            expanded, used = [], set()
            for child in children:
                pid = child.metadata['parent_id']
                if pid in used: continue
                used.add(pid)
                p = parent_docs[pid]
                passage = child.metadata.get('reranker_best_passage', '')
                offset = child.page_content.find(passage) if passage else 0
                expanded.append(Document(page_content=p.page_content, metadata={**p.metadata,
                    'matched_start_index': child.metadata['start_index'] + max(0, offset),
                    'matched_child_pages': child.metadata['pages']}))
                if len(expanded) == 4: break
            out.append((title, expanded, 2000))
    aq, af = anchors(q), facts(q)
    present = covered(aq, [by_id[i]['text'] for i in q['answer_doc_ids']])
    rows, contexts = [], []
    for title, docs, per_item in out:
        docs = [Document(page_content=d.page_content, metadata={**d.metadata,
            'matched_start_index': d.metadata.get('matched_start_index', 0),
            'matched_child_pages': d.metadata.get('matched_child_pages', d.metadata.get('pages', []))}) for d in docs]
        text, bodies = bounded(docs, 4000, per_item)
        hits = coverage(q, bodies, aq, af, present)
        rows.append({'treatment': title, 'eligible_quotes': len(aq), 'raw_present_quotes': sum(present),
            'quote_gold_hits': hits['quote_gold_hits'], 'present_quote_gold_hits': hits['present_quote_gold_hits'],
            'context_tokens': count_tokens(text), 'gold_doc_recall': hits['provided_gold_doc_recall'],
            'budget_overflow': max(0, count_tokens(text) - 4000), 'rerank_seconds_once': elapsed,
            'bge_pairs': sum(c.metadata['reranker_window_count'] for c in ranked)})
        contexts.append({'treatment': title, 'context': text, 'bodies': bodies})
    return rows, contexts


def main():
    started = time.perf_counter()
    qpath = ARGS.questions
    data = ARGS.docs
    reference = read(ARGS.reference)
    assert sha(data) == reference['corpus_sha256'] and sha(qpath) == reference['questions_sha256']
    docs = [json.loads(x) for x in data.read_text(encoding='utf-8').splitlines() if x]
    questions = [json.loads(x) for x in qpath.read_text(encoding='utf-8').splitlines() if x]
    assert len(docs) == 100 and len(questions) == 168
    by_id = {d['doc_id']: d for d in docs}
    chunks, details, parents, errors = build(docs)
    common = {i for q in questions for i in q['answer_doc_ids']}
    prior_chunks, _, _, _ = build([d for d in docs if d['doc_id'] in common])
    previous = read(ARGS.prior_results)
    manifest = read(ARGS.prior_alignment)
    state = {'schema': 'full-cpu-100-v1', 'corpus_sha256': sha(data), 'questions_sha256': sha(qpath),
        'corpus_documents': 100, 'questions': 168, 'projects': 14, 'full_distractor_corpus': True,
        'variants': [{'id': n, 'chunks': len(v), 'alignment_sha256': alignment(v)} for n, v in chunks.items()],
        'conditions': {'device': 'cpu', 'dtype': 'bfloat16', 'threads': 4, 'batch_size': 8, 'exact_cosine': True,
            'chunk_chars': 1000, 'overlap_chars': 200, 'parent_chars': 8000, 'pool': 20, 'child_k': 5,
            'parent_k': 4, 'context_budget_o200k': 4000, 'body_only_bge': True,
            'generator_calls': 0, 'judge_calls': 0, 'network_calls': 0, 'gpu_calls': 0},
        'source_code_sha256': sha(__file__), 'selftests': test_helpers(),
        'registered_generation_guard_sha256': sha(ARGS.guard_file) if ARGS.guard_file else None}
    if (RUN / 'plan.local.json').exists():
        assert read(RUN / 'plan.local.json') == state, '체크포인트 실행조건이 달라 재개할 수 없습니다'
    else: save(RUN / 'plan.local.json', state)
    queries = np.load(ARGS.query_vectors, mmap_mode='r')
    assert sha(ARGS.query_vectors) == reference['model_info']['query_vectors_sha256']
    import torch
    from sentence_transformers import SentenceTransformer, CrossEncoder
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    snapshot = ARGS.kure_snapshot.resolve()
    model = SentenceTransformer(str(snapshot), device='cpu', local_files_only=True, trust_remote_code=False)
    model.to(torch.bfloat16)
    assert str(next(model.parameters()).device) == 'cpu'
    event(phase='loaded_kure', variants=state['variants'], revision=snapshot.name)
    vectors_by_name = {}
    for name, rows in chunks.items():
        prior = prior_chunks[name]
        saved = next(m for m in manifest if m['variant'] == name)
        assert alignment(prior) == saved['chunk_order_and_text_sha256']
        oldfile = ARGS.prior_vectors / (name + '-vectors.npy')
        assert sha(oldfile) == next(r['vector_file_sha256'] for r in previous['results'] if r['variant'] == name)
        old_vectors = np.load(oldfile, mmap_mode='r')
        lookup = {r['chunk_id']: (r['text'], i) for i, r in enumerate(prior)}
        vectorfile = RUN / (name + '-vectors.local.npy')
        checkpoint = RUN / (name + '-checkpoint.local.json')
        if checkpoint.exists():
            done = read(checkpoint)['completed_fresh_chunks']
            vec = np.lib.format.open_memmap(vectorfile, mode='r+')
        else:
            done = 0
            vec = np.lib.format.open_memmap(vectorfile, mode='w+', dtype=np.float32, shape=(len(rows), 1024))
            for i, row in enumerate(rows):
                if row['chunk_id'] in lookup:
                    text, old_index = lookup[row['chunk_id']]
                    assert row['text'] == text
                    vec[i] = old_vectors[old_index]
            vec.flush()
            save(checkpoint, {'completed_fresh_chunks': 0, 'reused_chunks': len(prior)})
        pending = [i for i, row in enumerate(rows) if row['chunk_id'] not in lookup]
        assert vec.shape == (len(rows), 1024)
        tick = time.perf_counter()
        resume_start = done
        for offset in range(done, len(pending), 8):
            indices = pending[offset:offset + 8]
            values = model.encode([rows[i]['text'] for i in indices], batch_size=8, normalize_embeddings=True,
                convert_to_numpy=True, show_progress_bar=False)
            assert np.isfinite(values).all()
            vec[indices] = values
            vec.flush()
            completed = offset + len(indices)
            save(checkpoint, {'completed_fresh_chunks': completed, 'reused_chunks': len(prior)})
            if (completed - resume_start) % 64 == 0 or completed == len(pending):
                elapsed = time.perf_counter() - tick
                rate = (completed - resume_start) / elapsed
                event(phase='embedding', variant=name, fresh_completed=completed, fresh_total=len(pending),
                    reused=len(prior), rate_chunks_per_second=rate, eta_variant_seconds=(len(pending) - completed) / rate)
        assert np.isfinite(vec).all()
        vectors_by_name[name] = vec
        event(phase='embedding_variant_complete', variant=name, vectors_sha256=sha(vectorfile))
    del model
    import gc
    gc.collect()
    bge_snapshot = ARGS.bge_snapshot.resolve()
    bge = CrossEncoder(str(bge_snapshot), device='cpu', max_length=1024, activation_fn=torch.nn.Identity(),
        local_files_only=True, trust_remote_code=False, model_kwargs={'dtype': torch.bfloat16})
    assert str(next(bge.parameters()).device) == 'cpu'
    parent_docs = {f'{key[0]}|{key[1]}': Document(page_content=p.page_content, metadata={**p.metadata,
        'doc_id': key[0], 'parent_id': f'{key[0]}|{key[1]}'}) for key, p in parents.items()}
    items = RUN / 'items.local'
    items.mkdir(exist_ok=True)
    for qi, q in enumerate(questions):
        for name, rows in chunks.items():
            target = items / f'{qi:03d}-{name}.json'
            if target.exists(): continue
            scores = vectors_by_name[name] @ queries[qi]
            order = np.argsort(-scores, kind='stable')[:20]
            measures, contexts = treatments(q, name, rows, details, parent_docs, by_id, order, scores, bge)
            save(target, {'question_index': qi, 'question_id': q['id'], 'variant': name,
                'measures': measures, 'contexts': contexts, 'dense_top20': [int(i) for i in order]})
        if qi % 4 == 0 or qi == len(questions) - 1:
            event(phase='reranking', questions_completed=qi + 1, total=168, result_files=len(list(items.glob('*.json'))))
    all_rows = [r for file in sorted(items.glob('*.json')) for r in read(file)['measures']]
    aggregates = []
    for treatment in sorted({r['treatment'] for r in all_rows}):
        rows = [r for r in all_rows if r['treatment'] == treatment]
        assert len(rows) == 168
        raw = sum(r['raw_present_quotes'] for r in rows)
        eligible = sum(r['eligible_quotes'] for r in rows)
        hit = sum(r['present_quote_gold_hits'] for r in rows)
        aggregates.append({'treatment': treatment, 'questions': len(rows), 'eligible_quotes': eligible,
            'raw_present_quotes': raw, 'pooled_present_quote_hits': hit, 'pooled_present_quote_recall': hit / raw,
            'unconditional_quote_recall': sum(r['quote_gold_hits'] for r in rows) / eligible,
            'any_hit_questions': sum(r['present_quote_gold_hits'] > 0 for r in rows),
            'complete_questions': sum(r['raw_present_quotes'] > 0 and r['raw_present_quotes'] == r['present_quote_gold_hits'] for r in rows),
            'gold_doc_recall_mean': sum(r['gold_doc_recall'] for r in rows) / 168,
            'context_tokens_mean': sum(r['context_tokens'] for r in rows) / 168,
            'budget_overflows': sum(r['budget_overflow'] > 0 for r in rows)})
    save(RUN / 'aggregate.json', {'schema': state['schema'], 'completed_utc': now(), 'conditions': state['conditions'],
        'corpus_documents': 100, 'questions': 168, 'corpus_sha256': state['corpus_sha256'],
        'questions_sha256': state['questions_sha256'], 'variants': state['variants'], 'aggregates': aggregates,
        'wall_seconds_this_invocation': time.perf_counter() - started, 'generator_calls': 0, 'judge_calls': 0,
        'final_model_selection': 'pending', 'limits': ['retrieval_component_not_07_verify_end_to_end',
            '168_questions_clustered_in_14_projects', 'quote_coverage_not_answer_quality',
            'o200k_budget_not_EXAONE_full_prompt', 'native_OpenAI_RRF_not_executed']})
    event(phase='completed', aggregate='aggregate.json', aggregates=aggregates)


if __name__ == '__main__': main()
