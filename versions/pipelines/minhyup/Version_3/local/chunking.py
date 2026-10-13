"""공개 노트북의 chunking 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_chunking():
    global CHUNK_OVERLAP, CHUNK_SIZE, all_splits, chunk_id, doc, text_splitter
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, length_function=len, add_start_index=True)
    all_splits = [doc for doc in text_splitter.split_documents(pages) if doc.page_content.strip()]
    for chunk_id, doc in enumerate(all_splits):
        doc.metadata['chunk_id'] = chunk_id
    if not all_splits:
        raise ValueError('생성된 청크가 없습니다.')
