"""원본 라이브러리·입력을 연결한다. import와 입력 준비만으로 모델을 실행하지 않는다."""
import importlib
from pathlib import Path

def components():
    chunking=importlib.import_module('Version_3.components.rag_chunking')
    reranking=importlib.import_module('Version_3.components.rag_reranking')
    context=importlib.import_module('Version_3.components.rag_context')
    result={name:getattr(chunking,name) for name in ('build_parent_children','expand_parents','markdown_table_count')}
    result.update({name:getattr(reranking,name) for name in ('rerank_to_parents','RERANKER_MODEL','CANDIDATE_K','PARENT_K')})
    result.update({name:getattr(context,name) for name in ('format_context','CONTEXT_TOKEN_BUDGET','LLM_MODEL','OUTPUT_TOKEN_LIMIT')})
    return result

def prepare(version,input_dir,metadata=None):
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_core.runnables import RunnableLambda,RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS
    from langchain_community.retrievers import BM25Retriever
    from langchain_hwp_hwpx import HwpHwpxLoader
    from hwp_hwpx_parser import ExtractOptions,TableStyle
    folder=Path(input_dir).resolve()
    if not folder.is_dir(): raise FileNotFoundError('입력 문서 폴더가 없습니다.')
    result=dict(Document=Document,Embeddings=Embeddings,RunnableLambda=RunnableLambda,
        RunnablePassthrough=RunnablePassthrough,StrOutputParser=StrOutputParser,PromptTemplate=PromptTemplate,
        RecursiveCharacterTextSplitter=RecursiveCharacterTextSplitter,FAISS=FAISS,BM25Retriever=BM25Retriever,
        HwpHwpxLoader=HwpHwpxLoader,ExtractOptions=ExtractOptions,TableStyle=TableStyle)
    if version in ('v1','v2'):
        import pandas as pd
        import pymupdf4llm
        from langchain_huggingface import HuggingFaceEmbeddings
        from sentence_transformers import CrossEncoder
        if metadata is None: raise ValueError('이 원본에는 --metadata CSV가 필요합니다.')
        df=pd.read_csv(metadata)
        required={'공고 번호','공고 차수','사업명','사업 금액','발주 기관','공개 일자','입찰 참여 시작일','입찰 참여 마감일','파일명'}
        missing=required-set(df.columns)
        if missing: raise ValueError('원본 CSV 필수 열 누락: '+', '.join(sorted(missing)))
        result.update(pd=pd,pymupdf4llm=pymupdf4llm,HuggingFaceEmbeddings=HuggingFaceEmbeddings,
            CrossEncoder=CrossEncoder,df=df,folder=str(folder),sorted_file_names=sorted(p.name for p in folder.iterdir() if p.suffix.lower() in ('.pdf','.hwp')))
        if version=='v2':
            from kiwipiepy import Kiwi
            result['Kiwi']=Kiwi
    else:
        from hwp_hwpx_parser.hwp5 import HWP5Reader,CTRL_ID_HYPERLINK
        result.update(HWP5Reader=HWP5Reader,CTRL_ID_HYPERLINK=CTRL_ID_HYPERLINK,FILES_DIR=folder,MARKDOWN_DIR=folder/'extracted_markdown')
        if version=='v3':
            import pymupdf4llm
            from langchain_openai import OpenAIEmbeddings
            result.update(pymupdf4llm=pymupdf4llm,OpenAIEmbeddings=OpenAIEmbeddings)
            result.update(components())
        else:
            from langchain_community.document_loaders import PyPDFLoader
            from sentence_transformers import SentenceTransformer
            result.update(PyPDFLoader=PyPDFLoader,SentenceTransformer=SentenceTransformer)
    return result
