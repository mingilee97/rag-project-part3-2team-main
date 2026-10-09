"""VM/Colab 준비 상태와 입력 스키마만 검사한다. 모델 호출·설치·전송은 하지 않는다."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
from datetime import datetime, timezone
import urllib.error
from cpu_service import CPUService


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_inputs(questions_path, retrieval_run):
    plan = read(retrieval_run / 'plan.local.json')
    questions = [json.loads(x) for x in questions_path.read_text(encoding='utf-8').splitlines() if x]
    if len(questions) != 168 or plan['corpus_documents'] != 100 or sha(questions_path) != plan['questions_sha256']:
        raise ValueError('질문 수·문서 수·질문 해시가 고정 검색 계획과 다릅니다')
    count = 0
    for qi, q in enumerate(questions):
        for variant in ['main_fixed1000_200', 'minhyup_child1000_200']:
            path = retrieval_run / 'items.local' / f'{qi:03d}-{variant}.json'
            if not path.exists(): continue
            item = read(path)
            if item['question_id'] != q['id'] or item['question_index'] != qi or item['variant'] != variant:
                raise ValueError('검색 체크포인트의 문항 정렬이 다릅니다')
            contexts = {r['treatment']: r for r in item['contexts']}
            names = ['main_dense_top5'] if variant.startswith('main') else ['candidate_bge_top5', 'candidate_bge_parent4_pool20']
            for name in names:
                if name not in contexts or not isinstance(contexts[name]['bodies'], list):
                    raise ValueError('생성 입력의 treatment 또는 bodies 스키마가 다릅니다')
            count += 1
    return {'questions': len(questions), 'corpus_documents': 100,
            'retrieval_item_checkpoints': count, 'retrieval_item_checkpoints_required': 336,
            'all_generation_contexts_available': count == 336,
            'retrieval_aggregate_available': (retrieval_run / 'aggregate.json').is_file(),
            'source_retrieval_plan_sha256': sha(retrieval_run / 'plan.local.json'),
            'questions_sha256': sha(questions_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--questions', type=Path)
    parser.add_argument('--retrieval-run', type=Path)
    parser.add_argument('--check-service', action='store_true', help='loopback의 /api/tags와 /api/ps만 조회')
    parser.add_argument('--base-url', default='http://127.0.0.1:11435')
    args = parser.parse_args()
    if bool(args.questions) != bool(args.retrieval_run):
        parser.error('--questions와 --retrieval-run은 함께 지정해야 합니다')
    dependencies = {}
    for name in ['langchain-core', 'PyYAML']:
        try: dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: dependencies[name] = None
    result = {'schema': 'vm-generation-preflight-v1', 'checked_utc': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(),
              'system': platform.system(), 'dependencies': dependencies,
              'dependencies_present': all(dependencies.values()),
              'model_calls': 0, 'paid_API_calls': 0, 'files_transferred': 0,
              'private_texts_paths_keys_not_output': True}
    if args.questions:
        result['inputs'] = inspect_inputs(args.questions, args.retrieval_run)
    if args.check_service:
        service = CPUService(args.base_url)
        try:
            models = service.request('/api/tags', timeout=10).get('models', [])
            selected = [m for m in models if m.get('name', m.get('model')) == service.model]
            result['model_present'] = bool(selected)
            result['selected_model_digests'] = [m.get('digest') for m in selected]
            loaded = service.request('/api/ps', timeout=10).get('models', [])
            result['observed_size_vram_bytes'] = [m.get('size_vram') for m in loaded]
            result['no_observed_GPU_loaded'] = all(m.get('size_vram') == 0 for m in loaded)
            result['CPU_loaded_model_verified'] = bool(loaded) and all(m.get('size_vram') == 0 for m in loaded)
            result['GPU_managed_resource_policy_verified'] = False
        except (OSError, urllib.error.URLError):
            result['service_connection'] = 'unavailable'
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
