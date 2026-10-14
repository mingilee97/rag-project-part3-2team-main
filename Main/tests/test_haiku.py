"""실제 키·네트워크 없이 Anthropic 설정과 기존 JSON 호출 규약을 확인한다."""
import json
import os
import sys
import unittest
from types import ModuleType
from unittest.mock import patch

from langchain_core.runnables import RunnableLambda
from rfp_rag import providers, settings


class HaikuTest(unittest.TestCase):
    def test_default_and_historical_config(self):
        cfg = settings.load('07_verify')
        self.assertEqual(cfg['llm']['provider'], 'anthropic')
        self.assertEqual(cfg['llm']['model'], 'claude-haiku-4-5-20251001')
        self.assertEqual(cfg['embeddings']['model'], 'nlpai-lab/KURE-v1')
        self.assertEqual((cfg['chunk']['size'], cfg['chunk']['overlap']), (1000, 200))
        self.assertEqual(cfg['retrieve']['k'], 5)
        self.assertFalse(cfg['reranker']['enabled'])
        self.assertEqual(settings.load('07_verify_exaone')['llm']['provider'], 'local')

    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'ANTHROPIC_API_KEY'):
                providers.get_llm(settings.load('07_verify'))

    def test_mock_schema_and_plain_model(self):
        calls = []
        schema = {'type': 'object', 'properties': {'answer': {'type': 'string'}}}
        class FakeAnthropic:
            def __init__(self, **kwargs):
                calls.append(kwargs)
            def with_structured_output(self, tool, method):
                self.tool = tool
                self.method = method
                return RunnableLambda(lambda messages: {'answer': '합성 답변'})
        module = ModuleType('langchain_anthropic')
        module.ChatAnthropic = FakeAnthropic
        with patch.dict(sys.modules, {'langchain_anthropic': module}), patch.dict(os.environ, {}, clear=True):
            model = providers.get_llm(settings.load('07_verify'), json_schema=schema, api_key='synthetic-test')
            self.assertEqual(json.loads(model.invoke('합성 질문').content)['answer'], '합성 답변')
            plain = providers.get_llm(settings.load('07_verify'), api_key='synthetic-test')
            self.assertIsInstance(plain, FakeAnthropic)
        self.assertEqual(calls[0]['model'], 'claude-haiku-4-5-20251001')
        self.assertEqual(calls[0]['max_retries'], 0)
        self.assertEqual(schema, {'type': 'object', 'properties': {'answer': {'type': 'string'}}})


if __name__ == '__main__':
    unittest.main()
