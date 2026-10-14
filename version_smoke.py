"""원본 알고리즘과 호출 순서를 실행하되 모델·파일 로더의 외부 공급자만 합성한다."""
from pathlib import Path
from types import SimpleNamespace as NS
import socket
import tempfile
from unittest.mock import patch

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda,RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever

from version_runtime import VersionSession

class Embed:
    def __init__(self,**kwargs): pass
    def embed_documents(self,texts): return [[1.,0.] for _ in texts]
    def embed_query(self,text): return [1.,0.]
class Vector:
    @classmethod
    def from_documents(cls,docs,embeddings,**kwargs):
        instance=cls(); instance.docs=list(docs); instance.embeddings=embeddings
        vectors=embeddings.embed_documents([d.page_content for d in docs])
        instance.index=NS(d=len(vectors[0]),ntotal=len(docs)); return instance
    def add_documents(self,docs,**kwargs): self.docs.extend(docs)
    def similarity_search(self,query,k): self.embeddings.embed_query(query); return self.docs[:k]
    def as_retriever(self,search_kwargs): return RunnableLambda(lambda q:self.similarity_search(q,search_kwargs['k']))
class Ranker:
    def __init__(self,*args,**kwargs): pass
    def rank(self,query,docs,top_k): return [{'corpus_id':i} for i in range(min(top_k,len(docs)))]
class Encoder:
    def __init__(self,*args,**kwargs): self.max_seq_length=512
    def tokenizer(self,values,**kwargs):
        return {'input_ids':[[1]*len(v) for v in values]} if isinstance(values,list) else {'input_ids':[1]*len(values)}
    def encode(self,values,**kwargs):
        class Array(list):
            def tolist(self): return list(self)
        return Array(Array([1.]*1024) for _ in values)
class Loader:
    def __init__(self,*args,**kwargs): pass
    def load(self): return [Document(page_content='합성 문서에 적힌 제출 안내입니다.\n예산은 1000원입니다.',metadata={'page':0})]
class Series(list):
    def apply(self,f): return Series(map(f,self))
    def __eq__(self,value): return [x==value for x in self]
class Frame:
    def __init__(self,rows): self.rows=rows
    def __getitem__(self,key):
        return Series(r[key] for r in self.rows) if isinstance(key,str) else Frame([r for r,yes in zip(self.rows,key) if yes])
    @property
    def empty(self): return not self.rows
    @property
    def iloc(self): return self.rows
class Tokens:
    def encode(self,text,**kwargs): return list(text)
    def decode(self,tokens): return ''.join(tokens)
    def num_special_tokens_to_add(self,**kwargs): return 3
class ChildRanker:
    tokenizer=Tokens()
    def predict(self,pairs,**kwargs): return [1. for _ in pairs]

def providers(folder):
    columns=['공고 번호','공고 차수','사업명','사업 금액','발주 기관','공개 일자','입찰 참여 시작일','입찰 참여 마감일','파일명']
    row=dict.fromkeys(columns,'합성값'); row.update({'파일명':'sample.pdf','사업명':'합성 사업','발주 기관':'합성 기관'})
    from version_inputs import components
    result=components()
    result.update(Document=Document,RecursiveCharacterTextSplitter=RecursiveCharacterTextSplitter,
        FAISS=Vector,BM25Retriever=BM25Retriever,CrossEncoder=Ranker,
        HuggingFaceEmbeddings=Embed,OpenAIEmbeddings=Embed,SentenceTransformer=Encoder,
        pd=NS(isna=lambda v:v is None),df=Frame([row]),folder=str(folder),sorted_file_names=['sample.pdf'],
        FILES_DIR=folder,MARKDOWN_DIR=folder/'markdown',
        pymupdf4llm=NS(to_markdown=lambda p,**kw:[{'text':'# 합성 사업\n합성 문서에 적힌 제출 안내입니다.'}] if kw else '합성 문서에 적힌 제출 안내입니다.'),
        PyPDFLoader=Loader,HwpHwpxLoader=Loader,ExtractOptions=lambda **kw:kw,TableStyle=NS(MARKDOWN='markdown'),
        HWP5Reader=type('SyntheticReader',(),{}),CTRL_ID_HYPERLINK=1,
        Kiwi=lambda:NS(tokenize=lambda t:[NS(form=w,tag='NNG') for w in t.split()]),
        RunnableLambda=RunnableLambda,RunnablePassthrough=RunnablePassthrough,PromptTemplate=PromptTemplate,StrOutputParser=StrOutputParser)
    return result

def smoke(version):
    from Version_3.components import rag_reranking,rag_context
    with tempfile.TemporaryDirectory() as name,patch.object(socket,'socket',side_effect=AssertionError('모델/네트워크 호출 금지')):
        folder=Path(name); (folder/'sample.pdf').write_bytes(b'synthetic')
        session=VersionSession(version,providers(folder))
        model=RunnableLambda(lambda q:AIMessage(content='합성 근거에 따른 답변'))
        session.connect_haiku=lambda:session.namespace.update(chat_model=model,llm=model,method='basic')
        with patch.object(rag_reranking,'load_reranker',return_value=ChildRanker()),patch.object(rag_context,'encoding',return_value=Tokens()):
            result=session.execute('합성 사업 제출 안내')
        if version in ('v1','v2'):
            assert result['identified_project']=='합성 사업' and result['contexts']
            assert result['answer']=='합성 근거에 따른 답변'
            chunks=len(session.namespace['chunks'])
            assert session.namespace['retrieval_cache']
        else:
            assert result=='합성 근거에 따른 답변'
            chunks=len(session.namespace['all_splits'])
            assert session.namespace['CHUNK_SIZE']==(800 if version=='v3' else 500)
            if version=='v3': assert session.namespace['parent_documents']
            if version=='v4': assert session.namespace['EMBEDDING_MODEL']=='nlpai-lab/KoE5'
        other=VersionSession(version,providers(folder))
        assert 'chunks' not in other.namespace and 'all_splits' not in other.namespace
        return {'version':version,'status':'passed','source_stages':len(session.stages),'chunks':chunks,
                'real_chunking':True,'real_bm25_rrf':True,'api_calls':0,'model_quality_evaluation':False}
