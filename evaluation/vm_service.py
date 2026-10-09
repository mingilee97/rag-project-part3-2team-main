"""승인된 Linux VM/Colab의 같은 GGUF를 사용하는 loopback GPU 평가 transport."""
import platform
import argparse
import json
from pathlib import Path
import time
from cpu_service import CPUService

MODEL = 'exaone3.5:7.8b'
DIGEST = 'c7c4e3d1ca22fe9225f18b35eb719f67e2ca96a42e7fd17294a45b83ba8fbf03'
OLLAMA_VERSION = '0.35.1'


def choose_question_indices(questions, scope):
    if scope == 'full': return list(range(len(questions)))
    if scope != 'pilot4': raise ValueError('지원하지 않는 생성 평가 범위입니다')
    projects, indices = set(), []
    for index, question in enumerate(questions):
        project = question.get('project_id')
        if not project: raise ValueError('pilot 선택에 사업 식별자가 필요합니다')
        if project in projects: continue
        projects.add(project); indices.append(index)
        if len(indices) == 4: return indices
    raise ValueError('서로 다른 네 사업의 첫 질문이 필요합니다')


def require_linux_remote_environment(execution_environment):
    if execution_environment not in {'vm', 'colab'} or platform.system() != 'Linux':
        raise RuntimeError('GPU 실행기는 승인된 Linux VM 또는 Colab에서만 실행합니다')
    release = Path('/proc/sys/kernel/osrelease')
    if release.is_file() and 'microsoft' in release.read_text(encoding='utf-8').lower():
        raise RuntimeError('Windows/WSL의 로컬 GPU 제한을 이 실행기로 해제하지 않습니다')


class VMService(CPUService):
    def __init__(self, base_url='http://127.0.0.1:11435', execution_environment='vm', threads=4):
        require_linux_remote_environment(execution_environment)
        super().__init__(base_url, MODEL, threads)
        self.execution_environment = execution_environment
        self.protocol_verified = False

    def verify_protocol(self):
        version = self.request('/api/version', timeout=10).get('version')
        models = self.request('/api/tags', timeout=10).get('models', [])
        selected = [m for m in models if m.get('name', m.get('model')) == self.model]
        if version != OLLAMA_VERSION or len(selected) != 1 or selected[0].get('digest') != DIGEST:
            raise RuntimeError('Ollama 버전 또는 모델 digest가 고정 CPU 기준과 다릅니다')
        details = selected[0].get('details', {})
        if details.get('format') != 'gguf' or details.get('quantization_level') != 'Q4_K_M':
            raise RuntimeError('모델 형식 또는 양자화가 고정 기준과 다릅니다')
        self.protocol_verified = True

    def verify_gpu(self, require_loaded=False):
        models = self.request('/api/ps', timeout=10).get('models', [])
        if any(m.get('name', m.get('model')) != self.model for m in models):
            raise RuntimeError('전용 평가 서비스에 다른 모델이 적재되어 있습니다')
        if any(m.get('digest') != DIGEST or type(m.get('size_vram')) is not int for m in models):
            raise RuntimeError('적재 모델의 digest 또는 VRAM 상태를 확인할 수 없습니다')
        if require_loaded and (len(models) != 1 or models[0]['size_vram'] <= 0):
            raise RuntimeError('생성 직후 고정 모델의 GPU 적재 상태를 확인하지 못했습니다')
        checks = [{'size_vram_bytes': m['size_vram'], 'resident_size_bytes': m.get('size'),
                   'gpu_residency_observed': m['size_vram'] > 0} for m in models]
        self.vram_checks.append(checks)
        return checks

    def chat(self, messages, schema=None, num_predict=1500, num_ctx=8192):
        if not self.protocol_verified: self.verify_protocol()
        self.verify_gpu()
        payload = {'model': self.model, 'messages': messages, 'stream': False, 'keep_alive': '5m',
                   'options': {'num_gpu': 999, 'num_thread': self.threads, 'num_ctx': num_ctx,
                               'num_predict': num_predict, 'temperature': 0, 'seed': 42}}
        if schema is not None: payload['format'] = schema
        started = time.perf_counter()
        response = self.request('/api/chat', payload)
        observed = self.verify_gpu(require_loaded=True)
        if response.get('done') is not True:
            raise RuntimeError('완료된 비스트리밍 모델 응답이 아닙니다')
        metrics = {key: response.get(key) for key in ['done', 'done_reason', 'total_duration', 'load_duration',
            'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration']}
        metrics.update(wall_seconds=time.perf_counter()-started, options=payload['options'],
                       observed_size_vram_bytes=observed[0]['size_vram_bytes'],
                       gpu_residency_verified=True, requested_layer_offload=999,
                       GPU_50_percent_utilization_or_VRAM_limit_guaranteed=False)
        return response.get('message', {}).get('content', ''), metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:11435')
    parser.add_argument('--execution-environment', choices=['vm', 'colab'], default='vm')
    parser.add_argument('--run-probe', action='store_true')
    args = parser.parse_args()
    if not args.run_probe:
        print(json.dumps({'status': 'dry-run', 'model': MODEL, 'digest': DIGEST,
                          'ollama_version': OLLAMA_VERSION, 'GPU_model_calls': 0,
                          'requires': 'approved Linux VM/Colab; local Windows/WSL rejected'}))
        return
    service = VMService(args.base_url, args.execution_environment)
    _, metrics = service.chat([{'role': 'user', 'content': '1 더하기 1은 얼마인가요? 한 단어로 답하세요.'}], num_predict=16)
    print(json.dumps({'schema': 'linux-vm-ollama-gpu-probe-v1', 'metrics': metrics,
                      'model': MODEL, 'digest': DIGEST, 'vram_checks': service.vram_checks}, ensure_ascii=False))


if __name__ == '__main__': main()
