"""공개 네 흐름을 합성 공급자로 끝까지 연결한다. 네트워크와 실제 모델은 사용하지 않는다."""
import ast
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from versions.pipelines.notebook_runtime import NotebookRuntime


class Doc:
    def __init__(self, page_content, metadata=None):
        self.page_content, self.metadata = page_content, dict(metadata or {})


class R:
    def __init__(self, f): self.f = f
    def invoke(self, value): return self.f(value)
    def __or__(self, other):
        return R(lambda v: invoke(other, self.invoke(v)))
    def __ror__(self, other):
        return R(lambda v: self.invoke(invoke(other, v)))


def invoke(target, value):
    if isinstance(target, dict): return {k: invoke(v, value) for k, v in target.items()}
    return target.invoke(value) if hasattr(target, 'invoke') else target(value)


class Chat(R):
    def __init__(self, **kwargs):
        super().__init__(lambda value: NS(content='합성 근거에 따른 답변'))


class Splitter:
    def __init__(self, **kwargs): self.options = kwargs
    def split_documents(self, docs):
        return [Doc(d.page_content, {**d.metadata, 'start_index': 0}) for d in docs]


class Embed:
    def __init__(self, **kwargs): self.options = kwargs
    def embed_documents(self, texts): return [[1.0, 0.0] for _ in texts]
    def embed_query(self, text): return [1.0, 0.0]


class Vector:
    @classmethod
    def from_documents(cls, docs, embeddings, **kwargs):
        instance = cls()
        instance.docs, instance.embeddings = list(docs), embeddings
        vectors = embeddings.embed_documents([d.page_content for d in docs])
        instance.index = NS(d=len(vectors[0]), ntotal=len(vectors))
        return instance
    def add_documents(self, docs, **kwargs):
        self.embeddings.embed_documents([d.page_content for d in docs])
        self.docs.extend(docs)
    def as_retriever(self, search_kwargs):
        return R(lambda query: self.similarity_search(query, search_kwargs['k']))
    def similarity_search(self, query, k):
        self.embeddings.embed_query(query)
        return self.docs[:k]


class BM25:
    @classmethod
    def from_documents(cls, docs, **kwargs):
        item = cls(); item.docs, item.k = list(docs), 20
        return item
    def invoke(self, query): return list(reversed(self.docs))[:self.k]


class Ranker:
    def __init__(self, *args, **kwargs): pass
    def rank(self, query, docs, top_k):
        return [{'corpus_id': i} for i in range(min(len(docs), top_k))]


class Series(list):
    def apply(self, f): return Series(map(f, self))
    def __eq__(self, value): return [x == value for x in self]


class Frame:
    def __init__(self, rows): self.rows = rows
    def __getitem__(self, key):
        return Series(r[key] for r in self.rows) if isinstance(key, str) else Frame([r for r, yes in zip(self.rows, key) if yes])
    @property
    def empty(self): return not self.rows
    @property
    def iloc(self): return self.rows


class Loader:
    def __init__(self, *args, **kwargs): pass
    def load(self): return [Doc('합성 문서에 적힌 제출 안내입니다.', {'page': 0})]


class Encoder:
    def __init__(self, *args, **kwargs): self.max_seq_length = 512
    def tokenizer(self, values, **kwargs):
        return {'input_ids': [[1] * len(v) for v in values]} if isinstance(values, list) else {'input_ids': [1] * len(values)}
    def encode(self, values, **kwargs):
        class Array(list):
            def tolist(self): return list(self)
        return Array(Array([1.0] * 1024) for v in values)


def providers(directory):
    columns = ['공고 번호', '공고 차수', '사업명', '사업 금액', '발주 기관', '공개 일자', '입찰 참여 시작일', '입찰 참여 마감일', '파일명']
    row = dict.fromkeys(columns, '합성값')
    row.update({'파일명': 'sample.pdf', '사업명': '합성 사업', '발주 기관': '합성 기관'})
    def parents(pages, *args, **kwargs):
        parent = Doc(pages[0].page_content, {**pages[0].metadata, 'parent_id': 'p0'})
        child = Doc(parent.page_content, {**parent.metadata, 'chunk_id': 0})
        return {'p0': parent}, [child]
    return dict(Document=Doc, RecursiveCharacterTextSplitter=Splitter,
        FAISS=Vector, BM25Retriever=BM25, CrossEncoder=Ranker, Embeddings=object,
        HuggingFaceEmbeddings=Embed, OpenAIEmbeddings=Embed, SentenceTransformer=Encoder,
        ChatOpenAI=Chat, chat_model=Chat(), method='basic',
        pd=NS(isna=lambda v: v is None), df=Frame([row]), folder=str(directory),
        sorted_file_names=['sample.pdf'], FILES_DIR=directory, MARKDOWN_DIR=directory / 'markdown',
        pymupdf4llm=NS(to_markdown=lambda p, **kw: [{'text': '합성 문서에 적힌 제출 안내입니다.'}] if kw else '합성 문서에 적힌 제출 안내입니다.'),
        PyPDFLoader=Loader, HwpHwpxLoader=Loader, ExtractOptions=lambda **kw: kw,
        TableStyle=NS(MARKDOWN='markdown'), HWP5Reader=type('Reader', (), {}), CTRL_ID_HYPERLINK=1,
        Kiwi=lambda: NS(tokenize=lambda t: [NS(form=w, tag='NNG') for w in t.split()]),
        build_parent_children=parents, expand_parents=lambda children, parents: list(parents.values()),
        markdown_table_count=lambda t: 0,
        rerank_to_parents=lambda q, docs, parents, **kw: list(parents.values())[:kw['parent_k']],
        RERANKER_MODEL='synthetic', CANDIDATE_K=20, PARENT_K=4,
        format_context=lambda docs, **kw: '\n'.join(d.page_content for d in docs),
        CONTEXT_TOKEN_BUDGET=8000, LLM_MODEL='synthetic', OUTPUT_TOKEN_LIMIT=4096,
        RunnableLambda=R, RunnablePassthrough=lambda: R(lambda v: v),
        PromptTemplate=NS(from_template=lambda s: R(lambda values: s.format(**values))),
        StrOutputParser=lambda: R(lambda v: v.content if hasattr(v, 'content') else str(v)))


class Tests(unittest.TestCase):
    def setUp(self):
        self.old_socket = socket.socket
        socket.socket = lambda *a, **k: (_ for _ in ()).throw(AssertionError('외부 통신 금지'))
    def tearDown(self): socket.socket = self.old_socket

    def test_four_end_to_end_variants_and_isolation(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw); (directory / 'sample.pdf').write_bytes(b'synthetic')
            for member, variants in [('hyunkyung', ['business', 'kiwi']), ('minhyup', ['openai', 'local'])]:
                for variant in variants:
                    with self.subTest(member=member, variant=variant):
                        runtime = NotebookRuntime(member, variant, providers(directory))
                        runtime.run('parser')
                        if member == 'hyunkyung': runtime.run('cleaning')
                        runtime.run('chunking'); runtime.run('embedding')
                        if member == 'minhyup' and variant == 'openai': runtime.run('generation_model')
                        if member == 'minhyup' and variant == 'local': runtime.namespace['chat_model'] = Chat()
                        if member == 'minhyup':
                            runtime.run('generation'); runtime.run('retrieval')
                        else:
                            runtime.run('retrieval'); runtime.run('generation')
                        if member == 'hyunkyung':
                            result = runtime.call('answer_question', '합성 사업 제출 안내')
                            self.assertEqual(result['identified_project'], '합성 사업')
                            self.assertTrue(result['contexts'])
                            before = len(runtime.namespace['retrieval_cache'])
                            runtime.call('answer_question', '합성 사업 제출 안내')
                            self.assertEqual(len(runtime.namespace['retrieval_cache']), before)
                            if variant == 'kiwi': runtime.call('answer_question', '합성 사업 제출 안내', bm25_mode='kiwi')
                            self.assertTrue(runtime.call('extract_quotes', ['"합성 문서의 확인 가능한 근거 문구"']))
                            with self.assertRaises(ValueError): runtime.call('identify_project', '없는 사업')
                        else:
                            result = runtime.namespace['hybrid_retrieval_chain'].invoke('합성 질문')
                            self.assertEqual(result, '합성 근거에 따른 답변')
                        other = NotebookRuntime(member, variant, providers(directory))
                        self.assertNotIn('chunks', other.namespace)
                        self.assertNotIn('all_splits', other.namespace)
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ['sample.pdf'])

    def test_original_definition_hashes_and_file_integrity(self):
        for member in ('hyunkyung', 'minhyup'):
            for p in (ROOT / 'versions/pipelines' / member / 'Version_3').glob('*/provenance.json'):
                provenance = json.loads(p.read_text(encoding='utf-8'))
                for record in provenance['files']:
                    path = ROOT / record['module']
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'])
                    definitions = {n.name: n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
                    for original in record['source_definitions']:
                        digest = hashlib.sha256(ast.dump(definitions[original['name']], include_attributes=False).encode()).hexdigest()
                        self.assertEqual(digest, original['ast_sha256'])


if __name__ == '__main__': unittest.main()
