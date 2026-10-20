"""임베딩 모델과 실행 장치 연결. 생성 전에는 다운로드하지 않는다."""
def device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"

def create_embeddings(settings, target):
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model,
        model_kwargs={"device": target, "trust_remote_code": settings.embedding_trust_remote_code},
        encode_kwargs={"batch_size": settings.embedding_batch_size, "normalize_embeddings": settings.normalize_embeddings},
    )
