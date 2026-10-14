"""공개 노트북의 embedding 단계. 공급자는 호출자가 명시적으로 연결합니다."""
class KoE5Embeddings(Embeddings):
    """원문은 유지하고, 임베딩할 때만 E5 접두사를 추가합니다."""

    def __init__(self):
        self.encoder = SentenceTransformer(EMBEDDING_MODEL, device='cuda')
        self.encoder.max_seq_length = EMBEDDING_CONFIG['max_seq_length']
        self.truncated_document_count = 0

    def embed_documents(self, texts):
        prefixed = [EMBEDDING_CONFIG['document_prefix'] + text for text in texts]
        lengths = self.encoder.tokenizer(prefixed, truncation=False)['input_ids']
        count = sum((len(ids) > self.encoder.max_seq_length for ids in lengths))
        self.truncated_document_count += count
        if count:
            print(f'주의: 이번 배치 {count}개 청크가 512토큰을 초과하여 임베딩 시 잘립니다. 토큰 기반 청킹을 검토하세요.')
        return self.encoder.encode(prefixed, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False).tolist()

    def embed_query(self, text):
        prefixed = EMBEDDING_CONFIG['query_prefix'] + text
        if len(self.encoder.tokenizer(prefixed)['input_ids']) > self.encoder.max_seq_length:
            raise ValueError('질문이 KoE5의 512토큰 제한을 초과합니다.')
        return self.encoder.encode([prefixed], normalize_embeddings=True, show_progress_bar=False)[0].tolist()

def stage_embedding():
    global BATCH_SIZE, EMBEDDING_CONFIG, EMBEDDING_MODEL, batch, doc, embeddings, ids, manifest, retriever, start, vector_store
    EMBEDDING_MODEL = 'nlpai-lab/KoE5'
    BATCH_SIZE = 64
    EMBEDDING_CONFIG = {'model': EMBEDDING_MODEL, 'dimension': 1024, 'document_prefix': 'passage: ', 'query_prefix': 'query: ', 'normalize_embeddings': True, 'max_seq_length': 512}
    embeddings = KoE5Embeddings()
    if len(embeddings.embed_query('임베딩 동작 확인')) != 1024:
        raise ValueError('KoE5 임베딩 차원이 예상과 다릅니다.')
    vector_store = None
    for start in range(0, len(all_splits), BATCH_SIZE):
        batch = all_splits[start:start + BATCH_SIZE]
        ids = [str(doc.metadata['chunk_id']) for doc in batch]
        if vector_store is None:
            vector_store = FAISS.from_documents(batch, embeddings, ids=ids)
        else:
            vector_store.add_documents(batch, ids=ids)
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'files_dir': str(FILES_DIR), 'embedding_model': EMBEDDING_MODEL, 'embedding_config': EMBEDDING_CONFIG, 'truncated_document_count': embeddings.truncated_document_count, 'embedding_dimension': vector_store.index.d, 'chunk_size': CHUNK_SIZE, 'chunk_overlap': CHUNK_OVERLAP, 'file_count_found': len(file_paths), 'file_count_loaded': len(loaded_files), 'chunk_count': len(all_splits), 'loaded_files': loaded_files, 'load_errors': load_errors, 'empty_pdf_pages': empty_pdf_pages}
    retriever = vector_store.as_retriever(search_kwargs={'k': 4})
