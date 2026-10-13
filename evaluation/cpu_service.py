"""Ollama의 공식 CPU 옵션과 실제 VRAM 상태를 함께 확인하는 별도 평가용 클라이언트.

기존 등록 평가 가드를 수정하지 않는다. 합성 probe는 --run을 지정해야 실행된다.
"""
import argparse
import json
import time
import urllib.parse
import urllib.request


class CPUService:
    def __init__(self, base_url='http://127.0.0.1:11435', model='exaone3.5:7.8b', threads=4):
        url = urllib.parse.urlparse(base_url)
        if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'} or url.username:
            raise ValueError('평가 서비스는 인증정보가 없는 로컬 loopback URL이어야 합니다')
        self.base_url, self.model, self.threads = base_url.rstrip('/'), model, threads
        self.vram_checks = []

    def request(self, endpoint, payload=None, timeout=900):
        data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        req = urllib.request.Request(self.base_url + endpoint, data=data,
                                     headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout) as stream:
            return json.loads(stream.read())

    def verify_cpu(self, require_loaded=False):
        models = self.request('/api/ps', timeout=10).get('models', [])
        loaded = [m for m in models if m.get('name', m.get('model')) == self.model]
        checks = [{'name': m.get('name', m.get('model')), 'size_vram': m.get('size_vram')} for m in models]
        self.vram_checks.append(checks)
        if any(m.get('size_vram') is None or m['size_vram'] != 0 for m in models):
            raise RuntimeError('CPU 전용 조건을 확인하지 못했습니다. VRAM을 쓰는 모델이 있거나 상태 필드가 없습니다')
        if require_loaded and not loaded:
            raise RuntimeError('생성 직후 해당 모델의 CPU 적재 상태를 확인하지 못했습니다')
        return checks

    def chat(self, messages, schema=None, num_predict=1500, num_ctx=8192):
        self.verify_cpu()
        payload = {'model': self.model, 'messages': messages, 'stream': False, 'keep_alive': '5m',
                   'options': {'num_gpu': 0, 'num_thread': self.threads, 'num_ctx': num_ctx,
                               'num_predict': num_predict, 'temperature': 0, 'seed': 42}}
        if schema is not None: payload['format'] = schema
        start = time.perf_counter()
        answer = self.request('/api/chat', payload)
        self.verify_cpu(require_loaded=True)
        metrics = {k: answer.get(k) for k in ['done', 'done_reason', 'total_duration', 'load_duration',
            'prompt_eval_count', 'prompt_eval_duration', 'eval_count', 'eval_duration']}
        metrics.update(wall_seconds=time.perf_counter() - start, options=payload['options'],
                       size_vram_zero_verified=True)
        return answer.get('message', {}).get('content', ''), metrics

    def unload(self):
        return self.request('/api/generate', {'model': self.model, 'keep_alive': 0})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:11435')
    parser.add_argument('--run', action='store_true', help='승인된 로컬 서비스에서 합성 16토큰 probe 실행')
    args = parser.parse_args()
    if not args.run:
        print(json.dumps({'status': 'dry-run', 'model': 'exaone3.5:7.8b', 'num_gpu': 0,
                          'synthetic_probe_output_limit': 16, 'production_guard_changed': False}))
        return
    service = CPUService(args.base_url)
    _, metrics = service.chat([{'role': 'user', 'content': '1 더하기 1은 얼마인가요? 한 단어로 답하세요.'}], num_predict=16)
    print(json.dumps({'schema': 'ollama-cpu-probe-v1', 'metrics': metrics, 'vram_checks': service.vram_checks}, ensure_ascii=False))


if __name__ == '__main__': main()
