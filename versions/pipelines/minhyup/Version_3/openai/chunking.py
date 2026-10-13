"""공개 노트북의 chunking 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_chunking():
    global CHUNK_OVERLAP, CHUNK_SIZE, PARENT_SIZE, all_splits, parent_documents
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 150
    PARENT_SIZE = 8000
    parent_documents, all_splits = build_parent_children(pages, CHUNK_SIZE, CHUNK_OVERLAP, parent_size=PARENT_SIZE)
    if not all_splits:
        raise ValueError('생성된 child 청크가 없습니다.')
