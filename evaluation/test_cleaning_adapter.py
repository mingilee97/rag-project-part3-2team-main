"""외부 모델 없이 보호 구간 소실 시 원문 복귀와 메인 문서 계약을 확인한다."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'candidates/hyunkyung/5e79101/adapter.py'
spec = importlib.util.spec_from_file_location('cleaning_adapter', path)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class TestCleaningAdapter(unittest.TestCase):
    def test_source_and_metadata_unchanged(self):
        document = {'doc_id': 'synthetic', 'agency': '합성 기관', 'title': '합성 제목', 'text': '계약 금액은 123원입니다.\r\n', 'amount': 123}
        snapshot = dict(document)
        output, info = module.adapt_document(document, ['계약 금액은 123원입니다.'])
        self.assertEqual(document, snapshot)
        self.assertEqual(output.keys(), document.keys())
        self.assertEqual(output['amount'], 123)
        self.assertFalse(info['fallback_to_original'])

    def test_deleted_protected_page_line_falls_back(self):
        document = {'doc_id': 'synthetic', 'text': '123\n요구사항 본문만 남음'}
        output, info = module.adapt_document(document, ['123'])
        self.assertEqual(output['text'], document['text'])
        self.assertTrue(info['fallback_to_original'])
        self.assertEqual(info['lost_protected_spans_before_fallback'], 1)
        self.assertEqual(info['native_removed_line_count'], 1)

    def test_invalid_text_rejected(self):
        with self.assertRaises(TypeError): module.adapt_document({'doc_id': 'synthetic', 'text': None})


if __name__ == '__main__': unittest.main()
