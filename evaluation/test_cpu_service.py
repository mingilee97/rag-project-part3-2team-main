"""실제 모델 호출 없이 CPU 전용 계약과 원격 URL 차단을 확인한다."""
import unittest
from cpu_service import CPUService


class FakeService(CPUService):
    def __init__(self, vram=0, loaded=True):
        super().__init__()
        self.vram, self.loaded, self.requests = vram, loaded, []

    def request(self, endpoint, payload=None, timeout=900):
        self.requests.append((endpoint, payload))
        if endpoint == '/api/ps':
            return {'models': [{'name': self.model, 'size_vram': self.vram}] if self.loaded else []}
        return {'message': {'content': '합성 응답'}, 'done': True, 'eval_count': 2, 'prompt_eval_count': 50}


class TestCPUContract(unittest.TestCase):
    def test_remote_or_credentialed_url_rejected(self):
        for url in ['https://example.com', 'http://user:password@localhost:11435', 'http://127.0.0.1:11435@evil.example']:
            with self.assertRaises(ValueError): CPUService(url)

    def test_gpu_or_unknown_memory_fails_before_generation(self):
        for vram in [1, None]:
            service = FakeService(vram)
            with self.assertRaises(RuntimeError): service.chat([{'role': 'user', 'content': '합성'}])
            self.assertEqual([p for p, _ in service.requests], ['/api/ps'])

    def test_cpu_options_and_observed_memory_required(self):
        service = FakeService()
        raw, metrics = service.chat([{'role': 'user', 'content': '합성'}], num_predict=16)
        payload = next(p for endpoint, p in service.requests if endpoint == '/api/chat')
        self.assertEqual(payload['options']['num_gpu'], 0)
        self.assertEqual(payload['options']['num_thread'], 4)
        self.assertEqual(payload['options']['num_predict'], 16)
        self.assertFalse(payload['stream'])
        self.assertEqual(raw, '합성 응답')
        self.assertTrue(metrics['size_vram_zero_verified'])

    def test_missing_loaded_model_after_response_fails(self):
        service = FakeService(loaded=False)
        with self.assertRaises(RuntimeError): service.chat([{'role': 'user', 'content': '합성'}])


if __name__ == '__main__': unittest.main()
