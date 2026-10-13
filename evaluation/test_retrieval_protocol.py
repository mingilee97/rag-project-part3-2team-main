"""모델을 부르지 않고 잘못된 캐시·기존 벡터 조건의 혼합을 차단한다."""
from pathlib import Path
import tempfile
import unittest
from retrieval_protocol import KURE_REVISION, BGE_REVISION, validate_reuse_protocol


class ReuseProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.kure, self.bge = self.root / KURE_REVISION, self.root / BGE_REVISION
        for path in [self.kure, self.bge]:
            path.mkdir()
            (path / 'config.json').write_text('{}', encoding='utf-8')
        self.prior = {'model': 'nlpai-lab/KURE-v1', 'revision': KURE_REVISION,
                      'device': 'cpu', 'parameter_dtype': 'torch.bfloat16',
                      'normalize_embeddings': True, 'batch_size': 8,
                      'torch_threads': 4, 'max_seq_length': 8192}

    def test_matching_cache_preserves_measured_score_definition(self):
        state = validate_reuse_protocol(self.prior, self.kure, self.bge)
        self.assertFalse(state['exact_cosine'])
        self.assertTrue(state['bf16_norm_rounding_preserved'])

    def test_other_revision_or_missing_cache_is_rejected(self):
        for path in [self.root / ('a' * 40), self.root / KURE_REVISION / 'missing']:
            with self.assertRaises(ValueError):
                validate_reuse_protocol(self.prior, path, self.bge)
        with self.assertRaises(ValueError):
            validate_reuse_protocol(self.prior, self.kure, self.kure)

    def test_prior_vector_precision_or_model_mismatch_is_rejected(self):
        for key, value in [('revision', 'a' * 40), ('parameter_dtype', 'torch.float32'),
                           ('normalize_embeddings', False), ('model', 'other')]:
            with self.assertRaises(ValueError):
                validate_reuse_protocol({**self.prior, key: value}, self.kure, self.bge)


if __name__ == '__main__': unittest.main()
