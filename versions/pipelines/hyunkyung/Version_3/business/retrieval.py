"""공개 노트북의 retrieval 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def normalize_project_text(value):
    return ''.join((char for char in unicodedata.normalize('NFKC', str(value)).casefold() if char.isalnum()))

def metadata_text(value):
    return '' if pd.isna(value) else str(value).strip()

def choose_project(matches, query):
    matches = sorted(set(matches))
    if len(matches) == 1:
        return matches[0]
    normalized_query = normalize_project_text(query)
    agency_matches = [key for key in matches if key[0] and normalize_project_text(key[0]) in normalized_query]
    if len(agency_matches) == 1:
        return agency_matches[0]
    labels = ', '.join((f'[{agency}] "{title}"' for agency, title in matches))
    raise ValueError(f'사업을 하나로 특정할 수 없습니다: {labels}')

def identify_project(query):
    normalized_query = normalize_project_text(query)
    if not normalized_query:
        raise ValueError('질문이 비어 있습니다.')
    direct_matches = [key for key in project_catalog if normalize_project_text(key[1]) in normalized_query]
    if direct_matches:
        specific_matches = [key for key in direct_matches if not any((normalize_project_text(key[1]) != normalize_project_text(other[1]) and normalize_project_text(key[1]) in normalize_project_text(other[1]) for other in direct_matches))]
        return choose_project(specific_matches, query)
    alias_matches = [(alias, target) for alias, target in PROJECT_ALIASES.items() if normalize_project_text(alias) in normalized_query]
    if alias_matches:
        longest = max((len(normalize_project_text(alias)) for alias, _ in alias_matches))
        targets = [target for alias, target in alias_matches if len(normalize_project_text(alias)) == longest]
        unknown = [target for target in targets if target not in project_chunks_by_key]
        if unknown:
            raise ValueError(f'PROJECT_ALIASES의 사업이 문서 목록에 없습니다: {unknown}')
        return choose_project(targets, query)
    raise ValueError('질문에서 사업명을 찾지 못했습니다. 정식 사업명을 질문에 적거나 PROJECT_ALIASES에 줄임말을 등록해 주세요.')

def get_retrievers(project_key):
    if project_key not in retrievers_by_project:
        project_chunks = project_chunks_by_key[project_key]
        store = FAISS.from_documents(project_chunks, embeddings)
        dense = store.as_retriever(search_kwargs={'k': 20})
        bm25 = BM25Retriever.from_documents(project_chunks)
        bm25.k = 20
        retrievers_by_project[project_key] = (dense, bm25)
    return retrievers_by_project[project_key]

def rrf_search(query, project_key, k=60):
    dense_retriever, bm25_retriever = get_retrievers(project_key)
    dense_results = dense_retriever.invoke(query)
    sparse_results = bm25_retriever.invoke(query)
    scores = {}
    for results in (dense_results, sparse_results):
        for rank, doc in enumerate(results, start=1):
            doc_id = doc.metadata['chunk_id']
            if doc_id not in scores:
                scores[doc_id] = {'doc': doc, 'score': 0}
            scores[doc_id]['score'] += 1 / (k + rank)
    ranked = sorted(scores.values(), key=lambda item: item['score'], reverse=True)
    return [item['doc'] for item in ranked]

def make_search_text(query, method):
    if method == 'basic':
        return query
    if method == 'hyde':
        hyde_prompt = f'{hyde_search_rules}\n\n질문: {query}\n가상 안내문:'
        return chat_model.invoke(hyde_prompt).content.strip()
    raise ValueError(f'지원하지 않는 검색 방식: {method}')

def retrieve_and_rerank(query, method):
    project_key = identify_project(query)
    cache_key = (project_key, method, query)
    if cache_key not in retrieval_cache:
        search_text = make_search_text(query, method)
        found = rrf_search(search_text, project_key)
        ranking = reranker.rank(query, [doc.page_content for doc in found], top_k=6)
        reranked_docs = [found[row['corpus_id']] for row in ranking]
        retrieval_cache[cache_key] = (project_key, search_text, found, reranked_docs)
    return retrieval_cache[cache_key]

def stage_retrieval():
    global PROJECT_ALIASES, agency, doc, project_catalog, project_chunks_by_key, reranker, retrieval_cache, retrievers_by_project, title
    PROJECT_ALIASES = {}
    project_chunks_by_key = defaultdict(list)
    for doc in chunks:
        agency = metadata_text(doc.metadata.get('발주 기관'))
        title = metadata_text(doc.metadata.get('사업명'))
        if title:
            project_chunks_by_key[agency, title].append(doc)
    project_catalog = sorted(project_chunks_by_key)
    if not project_catalog:
        raise ValueError('사업명 메타데이터가 있는 청크가 없습니다.')
    retrievers_by_project = {}
    reranker = CrossEncoder('Alibaba-NLP/gte-multilingual-reranker-base', trust_remote_code=True, device='cuda')
    retrieval_cache = {}
