"""외부 의존성 없이 설정·권한·파일 검증과 공통 호출 규약을 확인한다."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from team_versions import VersionSession, load_config
from team_versions.runtime import _verified_bundle


class VersionsTest(unittest.TestCase):
    def test_configs(self):
        for version in ('baseline', 'v1', 'v2', 'v3', 'v4'):
            config = load_config(version)
            self.assertEqual(config['id'], version)
            self.assertEqual(len(config['source']['commit']), 40)
            self.assertEqual(set(config['modules']), {'parser', 'chunker', 'embedder', 'retriever', 'generator'})
            self.assertEqual(config['comparison'], '비교 보류')
            self.assertEqual(config['deployment_generator']['model'], 'claude-haiku-4-5-20251001')
        with self.assertRaises(ValueError):
            load_config('../v1')

    def test_permissions(self):
        for i in range(1, 5):
            with self.assertRaises(PermissionError):
                VersionSession(f'v{i}')
        with self.assertRaises(ValueError):
            VersionSession('v1', reuse_authorized=True)

    def test_original_arguments_and_return(self):
        session = VersionSession('baseline')
        fake = SimpleNamespace(chunk_fixed=lambda doc, size, overlap: (doc, size, overlap))
        with patch('team_versions.runtime.importlib.import_module', return_value=fake):
            self.assertEqual(session.run('chunker', 'synthetic', size=1000, overlap=200), ('synthetic', 1000, 200))
        with self.assertRaises(ValueError):
            session.run('unknown')

    def test_reject_incomplete_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                _verified_bundle(load_config('v1'), folder)

    @unittest.skipUnless(os.environ.get('RAG_TEST_BUNDLE'), '권한을 확인한 로컬 테스트 모듈이 없음')
    def test_pinned_local_chunking_and_isolation(self):
        class Splitter:
            def __init__(self, **options):
                self.options = options
            def split_documents(self, documents):
                return list(documents)
        for i in range(1, 5):
            doc = SimpleNamespace(page_content='합성 문서 본문', metadata={})
            providers = {'Embeddings': object, 'RecursiveCharacterTextSplitter': Splitter,
                         'documents': [doc], 'pages': [doc],
                         'build_parent_children': lambda pages, *a, **k: ({'p0': pages[0]}, pages)}
            session = VersionSession(f'v{i}', bundle_root=os.environ['RAG_TEST_BUNDLE'],
                                     reuse_authorized=True, providers=providers)
            state = session.run('chunker')
            config = load_config(f'v{i}')['historical_settings']['chunker']
            if i in (1, 2):
                self.assertEqual(state['splitter'].options['chunk_size'], config['size'])
            else:
                self.assertEqual(state['CHUNK_SIZE'], config['size'])
                self.assertEqual(state['CHUNK_OVERLAP'], config['overlap'])
            other = VersionSession(f'v{i}', bundle_root=os.environ['RAG_TEST_BUNDLE'],
                                   reuse_authorized=True, providers=providers)
            self.assertIsNot(other.engine.namespace, session.engine.namespace)
            sentinel = object()
            with patch('rfp_rag.providers.get_llm', return_value=sentinel):
                self.assertIs(session.connect_haiku(), sentinel)
            self.assertIs(session.engine.namespace['chat_model'], sentinel)
            self.assertIs(session.engine.namespace['llm'], sentinel)


if __name__ == '__main__':
    unittest.main()
