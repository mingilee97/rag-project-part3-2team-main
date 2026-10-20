"""같은 검색 결과와 프롬프트로 답변을 만들고 결과를 기록한다."""
import hashlib
from .retrieval import HybridRetriever
from .generation import ANSWER_RULES, _content, create_chat_model

class RagPipeline(HybridRetriever):
    def __init__(self, chunks, settings, *, aliases=None, embeddings=None, chat_model=None, reranker=None, kiwi=None):
        super().__init__(chunks, settings, aliases=aliases, embeddings=embeddings, reranker=reranker, kiwi=kiwi)
        self.chat_model = chat_model if chat_model is not None else create_chat_model(settings)
        self.answer_cache = {}

    def answer(self, query, *, bm25_mode=None):
        bm25_mode = bm25_mode or self.settings.bm25_mode
        project_key, search_text, found, contexts, ranked_sources, ranked_chunk_ids, elapsed_ms = self.retrieve(
            query, bm25_mode=bm25_mode
        )
        context = "\n\n".join(
            f"[{i}] 메타데이터: {doc.metadata}\n본문: {doc.page_content}"
            for i, doc in enumerate(contexts, start=1)
        )
        prompt = ANSWER_RULES.format(context=context, query=query)
        cache_key = hashlib.sha256(
            f"{self.settings.generation_model}|{bm25_mode}|{prompt}".encode("utf-8")
        ).hexdigest()
        if cache_key in self.answer_cache:
            return dict(self.answer_cache[cache_key], answer_cached=True)
        answer = _content(self.chat_model.invoke(prompt))
        if not answer:
            raise ValueError(f"답변이 비어 있습니다: {query}")
        record = {
            "query": query, "answer_cached": False, "bm25_mode": bm25_mode,
            "identified_agency": project_key[0] if project_key else "",
            "identified_project": project_key[1] if project_key else "",
            "retrieval_scope": "identified_project" if project_key else "all_documents",
            "retrieved_sources": [doc.metadata.get("파일명", "") for doc in contexts],
            "ranked_document_sources": ranked_sources,
            "ranked_chunk_ids": ranked_chunk_ids,
            "retrieval_time_ms": elapsed_ms,
            "search_text": search_text, "answer": answer,
            "contexts": [doc.page_content for doc in contexts],
            "chunk_ids": [doc.metadata["chunk_id"] for doc in contexts],
            "rrf_chunk_ids": [doc.metadata["chunk_id"] for doc in found],
        }
        self.answer_cache[cache_key] = record
        return record
