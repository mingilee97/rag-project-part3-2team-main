"""공개 노트북의 retrieval 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def tokenize_korean(text):
    return text.lower().split()

def _document_key(doc):
    """동일 청크를 판별하기 위한 키"""
    return (doc.metadata.get('source'), doc.metadata.get('page'), doc.page_content)

def hybrid_search(query):
    """FAISS와 BM25 순위를 RRF로 결합해 상위 문서를 반환."""
    dense_docs = vector_store.similarity_search(query, k=dense_k)
    sparse_docs = bm25_retriever.invoke(query)
    scores = defaultdict(float)
    documents = {}
    for ranked_docs in (dense_docs, sparse_docs):
        for rank, doc in enumerate(ranked_docs, start=1):
            key = _document_key(doc)
            documents[key] = doc
            scores[key] += 1.0 / (rrf_constant + rank)
    ranked_keys = sorted(scores, key=scores.get, reverse=True)
    return [documents[key] for key in ranked_keys[:final_k]]

def stage_retrieval():
    global bm25_retriever, dense_k, final_k, hybrid_retrieval_chain, hybrid_retriever, rrf_constant, sparse_k
    dense_k = 5
    sparse_k = 5
    final_k = 5
    rrf_constant = 60
    bm25_retriever = BM25Retriever.from_documents(all_splits, preprocess_func=tokenize_korean)
    bm25_retriever.k = sparse_k
    hybrid_retriever = RunnableLambda(hybrid_search)
    hybrid_retrieval_chain = {'context': hybrid_retriever | format_docs, 'question': RunnablePassthrough()} | prompt | chat_model | StrOutputParser()
