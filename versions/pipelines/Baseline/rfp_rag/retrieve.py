"""설정 이름으로 검색기를 조립한다. 기법을 더하려면 함수 하나를 만들어 METHODS나 WRAPPERS에 이름을 올린다.

  cfg["retrieve"]["method"]        dense | bm25 | hybrid      (METHODS)
  cfg["retrieve"]["search_type"]   similarity | mmr           (dense에만)
  cfg["retrieve"]["multi_query"]   true면 로컬 LLM으로 질문을 여러 개로 바꿔 찾고 순위를 합친다
  cfg["reranker"]["enabled"]       true면 후보를 cross-encoder로 다시 줄 세운다(늘 로컬)
  cfg["retrieve"]["agency_filter"] true면 질문에서 기관·사업 이름을 찾아 그 문서 안에서만 찾는다
  cfg["retrieve"]["k"]             돌려줄 청크 수

설정 파일에 아직 없는 키(없으면 기본값): retrieve.pool(20, 합치거나 다시 줄 세우기 전 후보 수),
retrieve.hybrid_weights([0.5, 0.5], bm25와 dense 순서), retrieve.mmr_lambda(0.5), reranker.device(cuda),
reranker.max_length(None, 재순위 모델이 읽는 토큰 수. None이면 모델 기본값 8192),
검색 설정에 따라 후보 수와 재순위 모델의 입력 길이를 조정한다.

    retrieve(cfg, "질문") -> [Document]          get_retriever(cfg, doc_ids=None) -> LangChain 검색기
    retrieve_ids(cfg, "질문") -> [(doc_id, chunk_id)]
"""
import time
from functools import lru_cache

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document

from rfp_rag import index, route

POOL = 20


def _r(cfg):
    return cfg["retrieve"]


def _pool(cfg):
    return max(_r(cfg).get("pool", POOL), _r(cfg)["k"])


def _fetch(cfg):
    """기본 검색기가 가져올 개수. 합치거나 다시 줄 세울 때는 후보를 넉넉히 가져온다."""
    fused = _r(cfg)["method"] == "hybrid" or _r(cfg)["multi_query"] or cfg["reranker"]["enabled"]
    return _pool(cfg) if fused else _r(cfg)["k"]


# ---------- 기본 검색기 (METHODS) ----------
def _dense(cfg, doc_ids, n):
    kw = {"k": n}
    if _r(cfg)["search_type"] == "mmr":
        kw.update(fetch_k=max(_pool(cfg), 4 * n), lambda_mult=_r(cfg).get("mmr_lambda", 0.5))
    if doc_ids:
        kw["filter"] = {"doc_id": {"$in": list(doc_ids)}}
    return index.open_chroma(cfg).as_retriever(search_type=_r(cfg)["search_type"], search_kwargs=kw)


@lru_cache(maxsize=4)
def _bm25_full(path):
    from rank_bm25 import BM25Okapi
    return BM25Okapi(index._bm25_data(path)["tokens"])


def _bm25(cfg, doc_ids, n):
    from langchain_community.retrievers import BM25Retriever
    from rank_bm25 import BM25Okapi
    docs, toks = index.load_bm25(cfg)
    if doc_ids:  # 문서 몇 개뿐이라 그 청크만으로 그때그때 만든다
        want = set(doc_ids)
        keep = [i for i, d in enumerate(docs) if d.metadata["doc_id"] in want]
        docs, vec = [docs[i] for i in keep], BM25Okapi([toks[i] for i in keep])
    else:
        vec = _bm25_full(str(index.index_dir(cfg) / f"bm25_{cfg['chunk']['method']}.pkl"))
    return BM25Retriever(vectorizer=vec, docs=docs, k=n, preprocess_func=index.tokenize)


def _hybrid(cfg, doc_ids, n):
    from langchain_classic.retrievers import EnsembleRetriever
    return EnsembleRetriever(retrievers=[_bm25(cfg, doc_ids, n), _dense(cfg, doc_ids, n)],
                             weights=_r(cfg).get("hybrid_weights", [0.5, 0.5]), id_key="chunk_id")


METHODS = {"dense": _dense, "bm25": _bm25, "hybrid": _hybrid}


# ---------- 덧붙이는 기법 (WRAPPERS) ----------
_MQ_PROMPT = ("다음 질문을 공공 입찰 제안요청서에서 찾기 좋게 서로 다르게 바꿔 쓴 질문 3개를 한 줄에 하나씩 써라. "
              "기관 이름과 사업 이름은 그대로 두고, 번호나 설명은 붙이지 않는다.\n질문: {question}")


def _rrf(lists, c=60):
    score, keep = {}, {}
    for docs in lists:
        for r, d in enumerate(docs):
            key = d.metadata["chunk_id"]
            score[key] = score.get(key, 0) + 1 / (c + r + 1)
            keep.setdefault(key, d)
    return [keep[k] for k in sorted(score, key=score.get, reverse=True)]


def _multi_query(cfg, base):
    from langchain_classic.retrievers.multi_query import MultiQueryRetriever
    from langchain_core.prompts import PromptTemplate

    from rfp_rag.providers import get_llm

    class RRFMultiQuery(MultiQueryRetriever):
        """MultiQueryRetriever가 합집합만 내는 것을, 순위를 살려 합치도록 바꾼다."""

        def _get_relevant_documents(self, query, *, run_manager: CallbackManagerForRetrieverRun):
            qs = [query] + self.generate_queries(query, run_manager)
            return _rrf([self.retriever.invoke(q, config={"callbacks": run_manager.get_child()}) for q in qs])

    return RRFMultiQuery.from_llm(base, get_llm(cfg, purpose="multi_query"), prompt=PromptTemplate.from_template(_MQ_PROMPT))


_LOAD_S = {}  # (model, device, max_length) -> 모델을 올리는 데 걸린 초(워밍업 제외)


@lru_cache(maxsize=1)
def _cross_encoder(model, device, max_length=None):
    """max_length가 캐시 키에 들어 있어, 길이를 바꾸면 모델을 다시 올린다. 올린 직후 더미 쌍 하나로 워밍업한다."""
    from langchain_community.cross_encoders import HuggingFaceCrossEncoder
    kw = {"device": device}
    if max_length:
        kw["max_length"] = max_length  # sentence-transformers가 토크나이저 model_max_length로 바꿔 그 길이에서 자른다
    if device == "cuda":
        import torch
        kw["model_kwargs"] = {"torch_dtype": torch.float16}  # 처음부터 반 크기로 올려 메모리를 아낀다
    t0 = time.perf_counter()
    ce = HuggingFaceCrossEncoder(model_name=model, model_kwargs=kw)
    _LOAD_S[(model, device, max_length)] = round(time.perf_counter() - t0, 1)
    ce.score([("워밍업", "워밍업")])
    return ce


def _ce_of(cfg):
    rk = cfg["reranker"]
    return _cross_encoder(rk["model"], rk.get("device", "cuda"), rk.get("max_length"))


def _rerank(cfg, base):
    from langchain_classic.retrievers import ContextualCompressionRetriever
    from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
    rk = cfg["reranker"]
    ce = _ce_of(cfg)
    return ContextualCompressionRetriever(base_compressor=CrossEncoderReranker(model=ce, top_n=_r(cfg)["k"]),
                                          base_retriever=base)


WRAPPERS = {"multi_query": (lambda c: _r(c)["multi_query"], _multi_query),
            "rerank": (lambda c: c["reranker"]["enabled"], _rerank)}  # 이 순서로 겹친다


# ---------- 조립 ----------
def get_retriever(cfg, doc_ids=None):
    """설정에 맞는 LangChain 검색기. doc_ids가 있으면 그 문서 안에서만 찾는다."""
    r = METHODS[_r(cfg)["method"]](cfg, doc_ids, _fetch(cfg))
    for on, wrap in WRAPPERS.values():
        if on(cfg):
            r = wrap(cfg, r)
    return r


def retrieve(cfg, question):
    """질문에 맞는 청크 k개. agency_filter가 켜져 있으면 질문에서 찾은 기관·사업 문서 안에서만 찾는다."""
    ids = route.name_filter(question) if _r(cfg)["agency_filter"] else None
    return get_retriever(cfg, ids).invoke(question)[:_r(cfg)["k"]]


def retrieve_ids(cfg, question):
    return [(d.metadata["doc_id"], d.metadata["chunk_id"]) for d in retrieve(cfg, question)]
