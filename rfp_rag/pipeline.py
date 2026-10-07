"""ask(question, state, cfg): 질문 하나를 받아 답을 만든다.

순서(각 단계는 설정으로 켜고 끈다):
  1 앞 대화를 이은 질문이면 혼자 읽어도 뜻이 통하게 고친다      pipeline.route
  2 이름 맞추기(route.match_names)                                pipeline.route
  3 종류 가르기: meta | single | compare | search                pipeline.route
  4 종류마다 다르게 근거를 모은다
      meta    CSV 값을 근거로(금액·마감). 문서가 정해져 있으면 본문 청크도 조금 붙인다
      single  검색(하이브리드·다시 줄 세우기는 retrieve 설정) 상위 몇 개
      compare 문서마다 single 로 답한 뒤 표 하나로 합친다
      search  문서별 요약에서 찾는다(pipeline.use_enriched). 기관 이름이 잡히면 그 기관 문서의 CSV 값을 늘어놓는다
  5 번호 붙은 근거로 JSON 답 {answer, evidence_ids, found}
  6 숫자·날짜가 인용한 근거에 있는지 확인 pipeline.verify. 다시 물어 보고, 그래도 없으면 그 문장을 뺀다.
    질문과 근거 청크의 최고 코사인 유사도가 pipeline.min_score 아래면 모델을 부르지 않고 "찾을 수 없다"고 답한다.
세 스위치가 모두 꺼져 있으면 검색 상위 k개 -> 프롬프트 한 번 -> 답이다(00_baseline).

돌려주는 값: {"answer", "found", "route", "evidence": [{doc_id, chunk_id, score}], "given": [{doc_id, chunk_id, score}], "seconds"}
  evidence 는 모델이 인용한 청크, given 은 최종 답을 만들 때 모델에게 준 청크 전부(순서 유지, chunk_id 로 중복 제거).
  compare 는 문서별 답에 준 청크의 합집합이고, 모델을 부르기 전에 약한 검색으로 거절한 경우는 확인한 청크(검색된 것)를 담는다.
state 는 memory.new_state() 가 만든 dict 이고 ask 가 고쳐 쓴다.
"""
import re
import time

from langchain_core.documents import Document

from rfp_rag import answer as A
from rfp_rag import index, memory, retrieve, route

MIN_SCORE = 0.45  # 개발용 답 있는 질문의 최저 코사인 0.48 아래. 주제가 아예 다른 질문만 거른다(답 없는 질문 대부분은 0.61 이상이라 모델의 found 가 맡는다)
SUPERLATIVE = re.compile(r"가장|제일|최대|최소|최고")
OVERVIEW = re.compile(r"비교|차이")
ASCENDING = re.compile(r"적|작|낮|빠른|이른|최소|임박")
MAX_META_DOCS, MAX_COMPARE_DOCS, SEARCH_N = 6, 4, 6


# ---- 검색 ----------------------------------------------------------------------------------
def _widen(q, docs, doc_ids, cfg):
    """문서 하나 안의 근거를 넓힌다(pipeline.wide_evidence): 앞 3개 청크의 앞뒤 청크 -> 낱말 검색(BM25) 상위 3개 순으로
    의미 검색 결과 뒤에 붙이고, 겹친 것은 빼고, pipeline.max_evidence(8)개까지 자른다."""
    cap = cfg["pipeline"].get("max_evidence", 8)
    near = []
    for d in docs[:3]:
        m = re.match(r"^(.+:)(\d+)$", d.metadata["chunk_id"])
        if m:
            w = len(m.group(2))
            near += [f"{m.group(1)}{int(m.group(2)) + k:0{w}d}" for k in (-1, 1) if int(m.group(2)) + k >= 0]
    have = {d.metadata["chunk_id"] for d in docs}
    near = [i for i in dict.fromkeys(near) if i not in have]
    got = index.open_chroma(cfg).get(ids=near, include=["documents", "metadatas"]) if near else {"ids": [], "documents": [], "metadatas": []}
    by_id = {i: Document(page_content=t, metadata=m) for i, t, m in zip(got["ids"], got["documents"], got["metadatas"])}
    out = list(docs) + [by_id[i] for i in near if i in by_id] + retrieve._bm25(cfg, doc_ids, 3).invoke(q)[:3]
    uniq = {}
    for d in out:
        uniq.setdefault(d.metadata["chunk_id"], d)  # 겹치면 앞선 것을 남긴다
    return list(uniq.values())[:cap]


def _search(q, doc_ids, cfg, wide=False):
    """청크 k개(metadata["score"]에 질문과의 코사인 유사도를 단다). doc_ids 가 있으면 그 문서 안에서만 찾고,
    없으면 retrieve 가 설정대로 한다(agency_filter 등). wide 이고 문서가 하나이면 pipeline.wide_evidence 로 근거를 넓힌다."""
    if doc_ids:
        docs = retrieve.get_retriever(cfg, doc_ids).invoke(q)[:cfg["retrieve"]["k"]]
        if wide and len(doc_ids) == 1 and cfg["pipeline"].get("wide_evidence", False):
            docs = _widen(q, docs, doc_ids, cfg)
    else:
        docs = retrieve.retrieve(cfg, q)
    _score(cfg, q, docs)
    return docs


def _score(cfg, q, docs):
    """검색 방식(dense·bm25·hybrid)과 다시 줄 세우기 여부에 상관없이 쓰는 신호: 질문과 청크의 코사인 유사도.
    색인에 저장된 청크 벡터를 그대로 읽으니 청크를 다시 임베딩하지 않는다."""
    if not docs:
        return
    import numpy as np
    vs = index.open_chroma(cfg)
    ids = [d.metadata["chunk_id"] for d in docs]
    got = vs.get(ids=ids, include=["embeddings"])
    vec = dict(zip(got["ids"], got["embeddings"]))
    qv = np.asarray(index.get_embeddings(cfg).embed_query(q), dtype=float)
    for d in docs:
        v = vec.get(d.metadata["chunk_id"])
        if v is not None:
            v = np.asarray(v, dtype=float)
            d.metadata["score"] = float(qv @ v / (np.linalg.norm(qv) * np.linalg.norm(v) + 1e-9))


def _weak(cfg, docs):
    """verify 가 켜져 있고 가장 높은 유사도가 pipeline.min_score 아래면 True(모델을 부르지 않고 "찾을 수 없다"로 답한다)."""
    sc = [d.metadata["score"] for d in docs if "score" in d.metadata]
    return cfg["pipeline"]["verify"] and bool(sc) and max(sc) < cfg["pipeline"].get("min_score", MIN_SCORE)


_SUMMARIES = {}


def _summaries(cfg):
    """문서별 요약(enrich 가 만든 것) {doc_id: Document}. 없으면 빈 dict."""
    from rfp_rag.ingest.enrich import load_summaries
    key = str(cfg["data_dir"])
    if key not in _SUMMARIES:
        _SUMMARIES[key] = {s["doc_id"]: Document(page_content=s["summary_text"], metadata={
            "doc_id": s["doc_id"], "chunk_id": f"{s['doc_id']}:summary"}) for s in load_summaries(cfg)}
    return _SUMMARIES[key]


_INDEX = {}


def _summary_search(q, cfg, n=SEARCH_N):
    from langchain_core.vectorstores import InMemoryVectorStore
    from rfp_rag.index import get_embeddings  # 검색과 같은 모델 한 벌을 함께 쓴다(따로 불러오면 두 벌이 올라가 상한에 걸린다)
    key = (str(cfg["data_dir"]), cfg["embeddings"]["model"])
    if key not in _INDEX:
        docs = list(_summaries(cfg).values())
        _INDEX[key] = InMemoryVectorStore.from_documents(docs, get_embeddings(cfg)) if docs else None
    return _INDEX[key].similarity_search(q, k=n) if _INDEX[key] else []


# ---- 종류별 처리 ----------------------------------------------------------------------------
def _answer(q, docs, cfg, note="", detail=False):
    """detail 이고 pipeline.detail 이 켜져 있으면 항목별로 옮겨 적는 답(A.detail)을 쓴다."""
    if _weak(cfg, docs):  # 모델을 부르기 전 거절: given 은 확인한(검색된) 청크로 둔다. 심사가 무엇이 검색됐는지 볼 수 있게
        return {"answer": A.NOT_FOUND, "found": False, "cited": [], "given": list(docs)}
    if detail and cfg["pipeline"].get("detail", False):
        return A.detail(q, docs, cfg, verify=cfg["pipeline"]["verify"], note=note)
    return A.answer(q, docs, cfg, verify=cfg["pipeline"]["verify"], note=note)


def _with_summary(docs, cfg):
    """use_enriched 이면 가장 위 청크가 속한 문서의 요약을 맨 앞 근거로 붙인다."""
    if cfg["pipeline"]["use_enriched"] and docs:
        s = _summaries(cfg).get(docs[0].metadata["doc_id"])
        if s:
            return [s] + docs
    return docs


def _ranked(q, info):
    """"가장 큰 사업"처럼 이름 없이 순위를 묻는 질문의 문서들. 순위 질문이 아니면 []."""
    if not SUPERLATIVE.search(q):
        return []
    key = "deadline" if "마감" in q else "amount"
    rows = sorted((d for d in info.values() if d[key]), key=lambda d: d[key], reverse=not ASCENDING.search(q))
    return [d["doc_id"] for d in rows[:3]]


def _meta(q, doc_ids, info, cfg, note=""):
    docs = [A.meta_doc(info[d]) for d in doc_ids[:MAX_META_DOCS]]
    if 0 < len(doc_ids) <= 3:  # 사업 기간·계약 방법처럼 CSV 에 없는 것을 함께 물었을 수 있어 본문도 붙인다
        for d in doc_ids:
            docs += _search(q, [d], cfg)[:3 if len(doc_ids) == 1 else 2]
    return A.answer(q, docs, cfg, verify=cfg["pipeline"]["verify"], note=note)


def _compare(q, doc_ids, info, cfg):
    """기관마다 가장 점수가 높은 문서 하나씩 뽑아 각각 답하고, 그 답을 이어 붙인 뒤 비교 요약을 덧붙인다."""
    picked = list({info[d]["agency"]: d for d in reversed(doc_ids)}.values())[::-1][:MAX_COMPARE_DOCS]
    parts, cited, given = [], [], []
    for d in picked:
        note = (f"이 근거는 「{info[d]['title']}」({info[d]['agency']}) 문서 하나에서 온 것이다. 질문이 묻는 항목(예: 예산, 기간, 요구사항)을 이 문서의 값만으로 "
                "정리한다. 다른 문서와 견주지 않고 다른 문서 이야기는 쓰지 않으며, 답 본문에 근거 번호를 적지 않는다.")
        meta = route.META_WORDS.findall(q)
        # 두 문서가 한 질문에 섞여 있으면 모델이 엇갈리므로, 문서 하나에 던질 질문으로 바꾼다
        pq = f"이 사업의 {', '.join(dict.fromkeys(meta))}을(를) 알려 줘." if meta else (
            "이 사업의 사업 기간, 예산, 목적, 주요 범위를 정리해 줘." if OVERVIEW.search(q) else q)
        if meta:
            r = _meta(pq, [d], info, cfg, note)
        else:
            docs = _search(pq, [d], cfg, wide=True)
            if pq != q:  # 항목 없는 비교 질문: 개요 청크를 더한다
                docs += [c for c in _search(f"{info[d]['title']} 사업 개요 사업 기간 예산 주요 범위", [d], cfg)[:3] if c not in docs]
            r = _answer(pq, docs, cfg, note, detail=True)
        parts.append((info[d], r))
        given += r["given"]  # 못 찾은 문서의 청크도 넣는다(그 문서에서 무엇을 봤는지)
        if r["found"]:  # 병합 답이 기댄 근거는 문서별 답에 준 청크 전부다(인용한 것만이 아니라)
            cited += [d for d in r.get("given", r["cited"]) if d not in cited]
    if not any(r["found"] for _, r in parts):
        return {"answer": A.NOT_FOUND, "found": False, "cited": [], "given": given}
    from rfp_rag.providers import get_llm
    body = "\n\n".join(f"### {i['agency']} - {i['title']}\n{r['answer']}" for i, r in parts)
    # 표로 다시 짜면 7.8B 모델이 칸을 엇갈리게 채워 근거에 없는 내용이 생긴다. 문서별 답(각각 자기 근거로 확인한 것)은
    # 그대로 두고, 모델은 차이를 두세 문장으로 요약만 한다.
    prompt = ("아래는 문서마다 따로 만든 답이다. 질문에 맞춰 두 문서의 같은 점과 다른 점을 두세 문장으로 요약한다. "
              "아래 답에 적힌 내용과 숫자만 쓰고, 한쪽에만 있는 항목은 그 문서에만 있다고 쓴다. 없는 내용은 만들지 않는다.\n"
              f"JSON 한 줄로 {{\"answer\": \"...\"}} 만 답한다.\n\n[질문]\n{q}\n\n[문서별 답]\n{body}")
    schema = {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}
    try:
        import json
        summary = json.loads(get_llm(cfg, json_schema=schema, purpose="compare_merge").invoke(prompt).content)["answer"].strip()
    except Exception:  # 요약이 실패하면 문서별 답만 늘어놓는다
        summary = ""
    merged = body + ("\n\n### 비교 요약\n" + summary if summary else "")
    if cfg["pipeline"]["verify"]:
        merged = A.drop_unsupported(merged, "\n".join(d.page_content for d in cited) + "\n" + body) or A.NOT_FOUND
    return {"answer": merged, "found": merged != A.NOT_FOUND, "cited": cited, "given": given}


def _list(q, doc_ids, info, cfg):
    """search: 이름이 잡힌 기관의 문서들을 CSV 값으로 늘어놓는다."""
    return A.answer(q, [A.meta_doc(info[d]) for d in doc_ids[:10]], cfg, verify=cfg["pipeline"]["verify"])


def _handle(kind, q, doc_ids, info, cfg):
    if kind == "compare":
        return _compare(q, doc_ids, info, cfg)
    if kind == "meta":
        return _meta(q, doc_ids, info, cfg)
    if kind == "search" and doc_ids:
        return _list(q, doc_ids, info, cfg)
    if kind == "search" and cfg["pipeline"]["use_enriched"] and _summaries(cfg):
        return _answer(q, _summary_search(q, cfg), cfg)
    return _answer(q, _with_summary(_search(q, doc_ids or None, cfg, wide=kind == "single"), cfg), cfg, detail=kind == "single")


# ---- 진입점 ---------------------------------------------------------------------------------
def _ev(d):
    return {"doc_id": d.metadata["doc_id"], "chunk_id": d.metadata["chunk_id"], "score": d.metadata.get("relevance_score", d.metadata.get("score"))}


def _dedup(docs):
    """chunk_id 가 같은 것은 한 번만 두고 처음 나온 자리를 지킨다(같은 청크라 어느 쪽이든 내용이 같다)."""
    return list({d.metadata["chunk_id"]: d for d in docs}.values())


def ask(question, state, cfg):
    t0, p = time.time(), cfg["pipeline"]
    if not (p["route"] or p["verify"] or p["use_enriched"]):  # 기준선: 검색 -> 프롬프트 한 번
        docs = _search(question, None, cfg)
        r, kind, doc_ids = A.generate(question, docs, cfg), "plain", []
    else:
        info = A.doc_info(cfg)
        q, doc_ids = question, []
        if p["route"]:
            doc_ids = route.name_filter(question)
            q = question if doc_ids else memory.rewrite(question, state, cfg, info)  # 이름이 이미 있으면 혼자 읽어도 된다
            doc_ids = doc_ids or route.name_filter(q)
            if not doc_ids and q != question:  # 고친 질문에도 이름이 없으면 방금 다룬 문서로 본다
                doc_ids = list(state.get("last_docs", []))
        if not p["route"]:
            kind = "single"
        else:
            kind = route.classify(q, doc_ids, info, cfg)
            if kind == "meta" and not doc_ids:
                doc_ids = _ranked(q, info)
                kind = "meta" if doc_ids else "search"
            elif kind == "compare" and len({info[d]["agency"] for d in doc_ids}) < 2:
                kind = "single"
        r = _handle(kind, q, doc_ids, info, cfg)
        docs = r.get("cited", [])
    seen = list(dict.fromkeys(d.metadata["doc_id"] for d in r["cited"]))
    memory.remember(state, question, r["answer"], doc_ids or seen[:3])
    return {"answer": r["answer"], "found": r["found"], "route": kind, "evidence": [_ev(d) for d in r["cited"]],
            "given": [_ev(d) for d in _dedup(r["given"])], "seconds": round(time.time() - t0, 2)}




if __name__ == "__main__":
    import argparse
    import json

    from rfp_rag.settings import load

    ap = argparse.ArgumentParser(description="질문을 한 대화로 차례대로 묻는다")
    ap.add_argument("--exp")
    ap.add_argument("--ask", nargs="*", default=[], help="질문 여러 개(앞 질문이 뒤 질문의 앞 대화가 된다)")
    a = ap.parse_args()
    cfg, st = load(a.exp), memory.new_state()
    for q in a.ask:
        r = ask(q, st, cfg)
        print(json.dumps({**r, "evidence": [e["chunk_id"] for e in r["evidence"]]}, ensure_ascii=False, indent=1))
