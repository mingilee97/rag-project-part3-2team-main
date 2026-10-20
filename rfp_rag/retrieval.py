"""Dense와 Kiwi BM25를 RRF로 합치고 BGE로 재순위화한다."""
import time
from collections import defaultdict
from .routing import ProjectRouter
from .embedding import device, create_embeddings
from .reranking import create_reranker, rerank

PUNCTUATION_TAGS = {"SF", "SP", "SS", "SE", "SO", "SW"}

class HybridRetriever(ProjectRouter):
    def __init__(self, chunks, settings, *, aliases=None, embeddings=None, reranker=None, kiwi=None):
        settings.validate()
        self.settings = settings
        self.chunks = chunks
        self.aliases = aliases or {}
        self.device = self._device()
        self.embeddings = embeddings if embeddings is not None else create_embeddings(settings, self.device)
        self.reranker = reranker if reranker is not None else create_reranker(settings, self.device)
        if kiwi is None and settings.bm25_mode == "kiwi":
            from kiwipiepy import Kiwi
            kiwi = Kiwi()
        self.kiwi = kiwi
        self.project_chunks_by_key = defaultdict(list)
        for doc in chunks:
            agency = str(doc.metadata.get("발주 기관", "") or "").strip()
            title = str(doc.metadata.get("사업명", "") or "").strip()
            if title:
                self.project_chunks_by_key[(agency, title)].append(doc)
        self.project_catalog = sorted(self.project_chunks_by_key)
        if not self.project_catalog:
            raise ValueError("사업명 메타데이터가 있는 청크가 없습니다.")
        self.dense_retrievers = {}
        self.bm25_retrievers = {}
        self.retrieval_cache = {}

    _device = staticmethod(device)

    def _kiwi_morphs(self, text):
        return [token.form for token in self.kiwi.tokenize(text)
                if token.form.strip() and token.tag not in PUNCTUATION_TAGS]

    def _get_retrievers(self, project_key, bm25_mode):
        if bm25_mode not in {"kiwi", "current"}:
            raise ValueError(f"지원하지 않는 BM25 방식: {bm25_mode}")
        from langchain_community.retrievers import BM25Retriever
        from langchain_community.vectorstores import FAISS

        project_chunks = self.chunks if project_key is None else self.project_chunks_by_key[project_key]
        if project_key not in self.dense_retrievers:
            store = None
            for start in range(0, len(project_chunks), 1000):
                batch = project_chunks[start:start + 1000]
                if store is None:
                    store = FAISS.from_documents(batch, self.embeddings)
                else:
                    store.add_documents(batch)
            # Cache only the complete index, never a partially built batch.
            self.dense_retrievers[project_key] = store.as_retriever(
                search_kwargs={"k": self.settings.dense_k}
            )
        bm25_key = (project_key, bm25_mode)
        if bm25_key not in self.bm25_retrievers:
            if bm25_mode == "kiwi":
                if self.kiwi is None:
                    from kiwipiepy import Kiwi

                    self.kiwi = Kiwi()
                bm25 = BM25Retriever.from_documents(
                    project_chunks, preprocess_func=self._kiwi_morphs
                )
            else:
                bm25 = BM25Retriever.from_documents(project_chunks)
            bm25.k = self.settings.bm25_k
            self.bm25_retrievers[bm25_key] = bm25
        return self.dense_retrievers[project_key], self.bm25_retrievers[bm25_key]

    @staticmethod
    def rrf(dense_results, sparse_results, k):
        scores = {}
        for results in (dense_results, sparse_results):
            for rank, doc in enumerate(results, start=1):
                doc_id = doc.metadata["chunk_id"]
                if doc_id not in scores:
                    scores[doc_id] = {"doc": doc, "score": 0.0}
                scores[doc_id]["score"] += 1 / (k + rank)
        ranked = sorted(scores.values(), key=lambda item: item["score"], reverse=True)
        return [item["doc"] for item in ranked]

    def retrieve(self, query, *, bm25_mode=None):
        bm25_mode = bm25_mode or self.settings.bm25_mode
        route_started = time.perf_counter()
        try:
            project_key = self.identify_project(query)
        except ValueError:
            project_key = None  # Original behavior: ambiguous/unknown -> all 100 documents.
        route_seconds = time.perf_counter() - route_started
        cache_key = (project_key, query, bm25_mode)
        if cache_key in self.retrieval_cache:
            return self.retrieval_cache[cache_key]
        dense, bm25 = self._get_retrievers(project_key, bm25_mode)
        started = time.perf_counter()  # The first index build is excluded, as in the notebook.
        found = self.rrf(dense.invoke(query), bm25.invoke(query), self.settings.rrf_k)
        if not found:
            raise RuntimeError(f"검색 결과가 없습니다: {query}")
        ranked_chunks = rerank(query, found, self.reranker, self.settings.reranker_batch_size)
        top_contexts = ranked_chunks[:self.settings.final_context_count]
        ranked_chunk_ids = [doc.metadata["chunk_id"] for doc in ranked_chunks]
        ranked_sources = list(dict.fromkeys(doc.metadata.get("파일명", "")
                                            for doc in ranked_chunks))
        elapsed_ms = 1000 * (route_seconds + time.perf_counter() - started)
        result = (project_key, query, found, top_contexts, ranked_sources,
                  ranked_chunk_ids, elapsed_ms)
        self.retrieval_cache[cache_key] = result
        return result
