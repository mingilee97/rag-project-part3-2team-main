"""모델 호출 없이 Windows 차단·고정 모델 계약·실제 GPU 관측 요구를 검사한다."""
import unittest
from unittest.mock import patch
from vm_service import VMService, DIGEST, require_linux_remote_environment, choose_question_indices


class FakeService(VMService):
    def __init__(self, digest=DIGEST, vram=5_000_000_000, version='0.35.1', loaded=True):
        with patch('vm_service.require_linux_remote_environment'):
            super().__init__()
        self.digest, self.vram, self.version, self.loaded = digest, vram, version, loaded
        self.requests = []

    def request(self, endpoint, payload=None, timeout=900):
        self.requests.append((endpoint, payload))
        model = {'name': self.model, 'digest': self.digest, 'size_vram': self.vram,
                 'details': {'format': 'gguf', 'quantization_level': 'Q4_K_M'}}
        if endpoint == '/api/version': return {'version': self.version}
        if endpoint == '/api/tags': return {'models': [model]}
        if endpoint == '/api/ps': return {'models': [model] if self.loaded else []}
        return {'done': True, 'message': {'content': '합성 응답'}, 'prompt_eval_count': 50, 'eval_count': 2}


class VMContractTests(unittest.TestCase):
    def test_pilot_uses_first_question_of_four_distinct_projects(self):
        questions = [{'project_id': p} for p in ['a', 'a', 'b', 'b', 'c', 'd', 'e']]
        self.assertEqual(choose_question_indices(questions, 'pilot4'), [0, 2, 4, 5])
        self.assertEqual(choose_question_indices(questions, 'full'), list(range(7)))
        with self.assertRaises(ValueError): choose_question_indices(questions[:4], 'pilot4')

    def test_windows_or_WSL_or_unapproved_environment_is_rejected(self):
        with patch('vm_service.platform.system', return_value='Windows'):
            with self.assertRaises(RuntimeError): require_linux_remote_environment('vm')
        with patch('vm_service.platform.system', return_value='Linux'), patch('vm_service.Path.is_file', return_value=True), patch('vm_service.Path.read_text', return_value='microsoft-standard-WSL2'):
            with self.assertRaises(RuntimeError): require_linux_remote_environment('vm')
        with self.assertRaises(RuntimeError): require_linux_remote_environment('local')

    def test_other_model_or_server_version_fails_before_generation(self):
        for args in [{'digest': 'a'*64}, {'version': 'other'}]:
            service = FakeService(**args)
            with self.assertRaises(RuntimeError): service.chat([])
            self.assertNotIn('/api/chat', [name for name, _ in service.requests])

    def test_gpu_must_be_observed_after_response(self):
        for args in [{'vram': 0}, {'vram': None}, {'loaded': False}]:
            service = FakeService(**args)
            with self.assertRaises(RuntimeError): service.chat([])

    def test_same_prompt_controls_with_GPU_options_and_no_limit_claim(self):
        service = FakeService()
        raw, metrics = service.chat([{'role': 'user', 'content': '합성'}], num_predict=16)
        payload = next(p for name, p in service.requests if name == '/api/chat')
        self.assertEqual(payload['options'], {'num_gpu': 999, 'num_thread': 4, 'num_ctx': 8192,
                                             'num_predict': 16, 'temperature': 0, 'seed': 42})
        self.assertTrue(metrics['gpu_residency_verified'])
        self.assertFalse(metrics['GPU_50_percent_utilization_or_VRAM_limit_guaranteed'])
        self.assertEqual(raw, '합성 응답')


if __name__ == '__main__': unittest.main()
