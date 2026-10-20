"""BGE로 결합한 후보의 순서를 다시 정한다."""
def create_reranker(settings, target):
    from sentence_transformers import CrossEncoder
    return CrossEncoder(settings.reranker_model, trust_remote_code=True, device=target)

def rerank(query, found, model, batch_size):
    ranking = model.rank(query, [doc.page_content for doc in found], top_k=len(found), batch_size=batch_size)
    return [found[row["corpus_id"]] for row in ranking]
