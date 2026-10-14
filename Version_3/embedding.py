"""공개 노트북의 embedding 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_embedding():
    global BATCH_SIZE, EMBEDDING_MODEL, batch, doc, embeddings, ids, manifest, retriever, start, vector_store
    EMBEDDING_MODEL = 'text-embedding-3-small'
    BATCH_SIZE = 64
    embeddings = OpenAIEmbeddings(model='text-embedding-3-small', chunk_size=BATCH_SIZE)
    vector_store = None
    for start in range(0, len(all_splits), BATCH_SIZE):
        batch = all_splits[start:start + BATCH_SIZE]
        ids = [str(doc.metadata['chunk_id']) for doc in batch]
        if vector_store is None:
            vector_store = FAISS.from_documents(batch, embeddings, ids=ids)
        else:
            vector_store.add_documents(batch, ids=ids)
    manifest = {'chunking_strategy': 'section_parent_child_v2', 'parent_size': PARENT_SIZE, 'parent_count': len(parent_documents), 'pdf_markdown_report': pdf_markdown_report, 'created_at': datetime.now(timezone.utc).isoformat(), 'files_dir': str(FILES_DIR), 'embedding_model': EMBEDDING_MODEL, 'embedding_dimension': vector_store.index.d, 'chunk_size': CHUNK_SIZE, 'chunk_overlap': CHUNK_OVERLAP, 'file_count_found': len(file_paths), 'file_count_loaded': len(loaded_files), 'chunk_count': len(all_splits), 'loaded_files': loaded_files, 'load_errors': load_errors, 'empty_pdf_pages': empty_pdf_pages}
    retriever = RunnableLambda(lambda query: rerank_to_parents(query, vector_store.similarity_search(query, k=CANDIDATE_K), parent_documents, candidate_k=CANDIDATE_K, parent_k=PARENT_K))
