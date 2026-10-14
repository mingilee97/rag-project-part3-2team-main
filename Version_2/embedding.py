"""공개 노트북의 embedding 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def stage_embedding():
    global embedding_model_name, embeddings
    embedding_model_name = 'dragonkue/BGE-m3-ko'
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name, model_kwargs={'device': 'cuda', 'trust_remote_code': True}, encode_kwargs={'batch_size': 64, 'normalize_embeddings': True})
