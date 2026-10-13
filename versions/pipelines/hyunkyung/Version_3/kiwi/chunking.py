"""공개 노트북의 chunking 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_chunking():
    global chunk, chunk_id, chunks, splitter
    splitter = RecursiveCharacterTextSplitter(separators=['\n\n', '\n', ' '], chunk_size=700, chunk_overlap=100)
    chunks = splitter.split_documents(documents)
    for chunk_id, chunk in enumerate(chunks):
        chunk.metadata['chunk_id'] = chunk_id
