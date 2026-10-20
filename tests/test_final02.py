"""합성 자료와 모의 객체만 사용한다. 모델 다운로드와 네트워크는 금지한다."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import socket
import tempfile
import types
import unittest
from unittest.mock import patch

from rfp_rag.config import RagSettings
from rfp_rag.data import load_benchmark, normalize_filename
from rfp_rag.evaluation import GeminiJudge
from rfp_rag.metrics import build_source_text_index, score_retrieval_text
from rfp_rag.pipeline import RagPipeline
from rfp_rag.retrieval import HybridRetriever


@dataclass
class Document:
    page_content: str
    metadata: dict = field(default_factory=dict)


def doc(n, text='가상 근거', title='별빛도서관 예약 개선'):
    return Document(text, {'chunk_id': n, '파일명': '가상문서.hwp', '발주 기관': '가상기관', '사업명': title})


class ListRetriever:
    def __init__(self, rows): self.rows, self.calls = rows, 0
    def invoke(self, query):
        self.calls += 1
        return self.rows


class Reranker:
    def rank(self, query, texts, **kwargs):
        return [{'corpus_id': n} for n in reversed(range(len(texts)))]


class Chat:
    def __init__(self): self.calls = 0
    def invoke(self, prompt):
        self.calls += 1
        return types.SimpleNamespace(content='답변: 합성 답변')


class OfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.no_network = patch.object(socket.socket, 'connect', side_effect=AssertionError('오프라인 검사에서 네트워크 호출'))
        cls.no_network.start()

    @classmethod
    def tearDownClass(cls): cls.no_network.stop()

    def pipeline(self, chunks=None):
        chunks = chunks or [doc(i) for i in range(8)]
        with patch.object(HybridRetriever, '_device', return_value='cpu'):
            p = RagPipeline(chunks, RagSettings(), embeddings=object(), chat_model=Chat(), reranker=Reranker(), kiwi=object())
        dense, sparse = ListRetriever(chunks), ListRetriever(chunks[:3])
        p._get_retrievers = lambda project, mode: (dense, sparse)
        return p, dense, sparse

    def test_final_configuration(self):
        s = RagSettings(); s.validate()
        self.assertEqual(s.document_numbers, tuple(range(1, 101)))
        self.assertEqual((s.chunk_size, s.chunk_overlap, s.dense_k, s.bm25_k, s.rrf_k, s.final_context_count), (1000, 200, 20, 20, 60, 6))
        self.assertEqual(s.reranker_model, 'BAAI/bge-reranker-v2-m3')

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError): RagSettings(document_numbers=(True,)).validate()
        with self.assertRaises(ValueError): RagSettings(chunk_overlap=1000).validate()
        with self.assertRaises(ValueError): RagSettings(final_context_count=0).validate()

    def test_rrf_uses_both_rankings_and_deduplicates(self):
        a,b,c = doc(1),doc(2),doc(3)
        got = HybridRetriever.rrf([a,b],[b,c],60)
        self.assertEqual([d.metadata['chunk_id'] for d in got], [2,1,3])

    def test_project_routing_and_unknown_fallback(self):
        p,_,_ = self.pipeline()
        self.assertEqual(p.identify_project('별빛도서관 예약 개선의 요구사항은?'), ('가상기관','별빛도서관 예약 개선'))
        self.assertIsNone(p.retrieve('등록되지 않은 사업')[0])

    def test_retrieval_reranks_all_and_keeps_six_contexts(self):
        p,dense,sparse = self.pipeline()
        result = p.retrieve('별빛도서관 예약 개선')
        self.assertEqual([d.metadata['chunk_id'] for d in result[3]], [7,6,5,4,3,2])
        p.retrieve('별빛도서관 예약 개선')
        self.assertEqual((dense.calls,sparse.calls),(1,1))

    def test_generation_cache_and_record_contract(self):
        p,_,_ = self.pipeline()
        first = p.answer('별빛도서관 예약 개선')
        second = p.answer('별빛도서관 예약 개선')
        self.assertFalse(first['answer_cached']); self.assertTrue(second['answer_cached'])
        self.assertEqual(first['chunk_ids'],[7,6,5,4,3,2])
        self.assertEqual(p.chat_model.calls,1)
        self.assertEqual(first['retrieval_scope'],'identified_project')

    def test_unaligned_evidence_is_missing_not_zero(self):
        chunks=[doc(0,'첫 번째 근거')]
        item={'id':'SYN-1','source_filename':'가상문서.hwp','evidence_quotes':['없는 근거']}
        score=score_retrieval_text(item,chunks,chunks,build_source_text_index(chunks))
        self.assertIsNone(score['hit_at_5']); self.assertIsNone(score['mrr'])
        self.assertEqual(score['all_found_ctx'],0)

    def test_ranking_and_context_coverage_are_separate(self):
        chunks=[doc(0,'근거 하나'),doc(1,'근거 둘')]
        item={'id':'SYN-2','source_filename':'가상문서.hwp','evidence_quotes':['근거 하나','근거 둘']}
        score=score_retrieval_text(item,chunks,chunks[:1],build_source_text_index(chunks))
        self.assertEqual((score['hit_at_5'],score['mrr'],score['recall_ctx'],score['all_found_ctx']),(1,1,0.5,0))

    def test_judge_rejects_boolean_score_and_caches_valid_result(self):
        class JudgeClient:
            calls=0
            def invoke(self,prompt):
                self.calls+=1
                return types.SimpleNamespace(content=json.dumps({'score':True if self.calls==1 else .75,'reason':'합성 판정'}))
        client=JudgeClient(); judge=GeminiJudge(RagSettings(),client=client)
        self.assertEqual(judge.score('질문','기준','답변'),(.75,'합성 판정'))
        judge.score('질문','기준','답변'); self.assertEqual(client.calls,2)

    def test_benchmark_validates_document_and_question_identity(self):
        rows=[{'id':f'DOC{i:03d}-Q{q:02d}','document_id':f'DOC{i:03d}','source_filename':f'가상{i}.hwp','project_name':'가상 사업','question':'합성 질문','reference_answer':'합성 답','evidence':[{'text':'합성 근거'}]} for i in range(1,101) for q in range(1,4)]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic.json'
            p.write_text(json.dumps({'metadata':{'version':'1.1'},'items':rows}),encoding='utf-8')
            self.assertEqual(len(load_benchmark(p)),300)
            rows[1]['id']=rows[0]['id']
            p.write_text(json.dumps({'metadata':{'version':'1.1'},'items':rows}),encoding='utf-8')
            with self.assertRaises(ValueError):load_benchmark(p)

    def test_chunking_uses_original_boundaries_without_headers(self):
        from rfp_rag.chunking import split_documents
        calls={}
        class Splitter:
            def __init__(self,**kwargs):calls.update(kwargs)
            def split_documents(self,documents):return [doc(99,'합성 본문')]
        module=types.ModuleType('langchain_text_splitters');module.RecursiveCharacterTextSplitter=Splitter
        with patch.dict('sys.modules',{'langchain_text_splitters':module}):
            rows=split_documents([doc(0)],RagSettings())
        self.assertEqual(calls,{'separators':['\n\n','\n',' '],'chunk_size':1000,'chunk_overlap':200})
        self.assertEqual(rows[0].metadata['chunk_id'],0)
        self.assertEqual(rows[0].page_content,'합성 본문')

    def test_filename_normalization(self):
        self.assertEqual(normalize_filename('  가상   문서.HWP'),'가상 문서')


if __name__ == '__main__': unittest.main()
