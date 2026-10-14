"""질문 종류를 가른다. 이 파일에는 두 사람의 코드가 있다.

- 위쪽 `# ---- 분류` 구간: rfp-generation. 규칙으로 먼저 가르고, 남으면 로컬 LLM이 가른다.
- `# ---- 이름 맞추기` 구간: rfp-retrieval. 질문에서 기관·사업 이름을 찾아 문서를 좁힌다.

종류: meta(CSV에 있는 값) | single(문서 하나) | compare(기관이 둘 이상) | search(여러 문서에서 찾기)
"""
import json
import re

# ---- 분류 (rfp-generation) ---------------------------------------------------------------
META_WORDS = re.compile(r"예산|사업비|사업 금액|금액|얼마|마감|공고 번호|공개 일자|시작일")
STRONG_LIST_WORDS = re.compile(r"어떤 기관|목록|리스트|몇 건|몇 개|몇 곳|다른 기관|다른 사업|없나|있는지 모두")
# 문서 하나를 이름으로 짚고 이렇게 물으면 그 사업 안의 것들을 묻는 것이다(Q10). 문서가 둘 이상이면 목록을 묻는 것이다(Q15)
LIST_WORDS = re.compile(r"어떤 것들|어떤 사업|" + STRONG_LIST_WORDS.pattern)
COMPARE_WORDS = re.compile(r"비교|차이|각각|중에서|중에|보다|더 (?:크|큰|많|적|작|높|낮|길|짧|빠|이르|늦)")
ROUTES = ("meta", "single", "compare", "search")

_PROMPT = """공공 입찰 제안요청서(RFP) 100건에 대한 질문을 두 종류로 나눈다.
- single: 문서 하나의 내용을 묻는다. 예) "OO 사업의 요구사항을 알려 줘", "이 사업의 목적은?"
- search: 어떤 문서가 있는지 찾거나 여러 문서를 훑어야 한다. 예) "교육 관련 사업은 어떤 것들이 있어?", "ISP를 세우는 사업은?"
질문: {q}
JSON 한 줄로 {{"route": "single"}} 또는 {{"route": "search"}} 만 답한다."""


def _llm_route(question, cfg):
    from rfp_rag.providers import get_llm
    llm = get_llm(cfg, json_schema={"type": "object", "properties": {"route": {"type": "string", "enum": ["single", "search"]}},
                                    "required": ["route"]}, purpose="route")
    try:
        r = json.loads(llm.invoke(_PROMPT.format(q=question)).content)["route"]
    except Exception:  # 모델이 JSON 을 못 지키면 문서 하나로 본다
        return "single"
    return r if r in ROUTES else "single"


def classify(question, doc_ids, info, cfg):
    """(종류) 를 돌려준다. doc_ids: 이름 맞추기에서 나온 문서 번호, info: doc_id -> {agency, ...}.

    규칙: 기관이 둘 이상이면 compare(목록 낱말이 있고 비교 낱말이 없으면 목록을 묻는 것이라 아래로 내려간다)
    -> 이름이 나온 문서가 있으면 (금액·마감 낱말 → meta, 목록 낱말 → search, 그 밖 → single;
    문서가 하나이고 "어떤 것들"만 있으면 그 사업 안의 것을 묻는 것이라 single)
    -> 이름이 없으면 (금액·마감 낱말 → meta, 그 밖 → 로컬 LLM 이 single/search).
    """
    if len({info[d]["agency"] for d in doc_ids if d in info}) >= 2 and not (
            LIST_WORDS.search(question) and not COMPARE_WORDS.search(question)):
        return "compare"
    if META_WORDS.search(question) and (doc_ids or not LIST_WORDS.search(question)):
        return "meta"
    if doc_ids:
        if len(doc_ids) == 1 and not STRONG_LIST_WORDS.search(question):
            return "single"
        return "search" if LIST_WORDS.search(question) else "single"
    return _llm_route(question, cfg)



# ---- 이름 맞추기 (rfp-retrieval) ---------------------------------------------------------


from functools import lru_cache  # noqa: E402
from pathlib import Path  # noqa: E402

from rapidfuzz import fuzz  # noqa: E402

_NOISE_WORDS = re.compile(r"\(사\)|\(재\)|\(주\)|\(사）|㈜|\(용역\)|재단법인|사단법인|입찰공고|산학협력단")
_TITLE_NOISE = re.compile(r"\[[^\]]*\]|\([^)]*\)|「|」|\d{4}\s*(?:년도|년|학년도)|재공고|입찰|공고의 건|공고|용역|위탁|"
                          r"사업|구축|고도화|기능개선|개선|운영|개발|재구축|유지|보수|긴급|협상")


def _ns(s):
    """공백과 괄호를 빼고 소문자로 맞춘다."""
    return re.sub(r"[\s()\[\]「」·]", "", s).lower()


def _agency_variants(agency):
    """기관명에서 질문에 나올 만한 이름들: 전체와 마지막 낱말(`경기도 평택시` -> `평택시`). 3글자 이상만."""
    clean = _NOISE_WORDS.sub(" ", agency).strip()
    words = clean.split()
    return {v for v in (_ns(clean), _ns(words[-1]) if words else "") if len(v) >= 3}


def _title_core(title):
    return _ns(_TITLE_NOISE.sub(" ", title))


@lru_cache(maxsize=1)
def _doc_table(data_dir=None):
    """docs.jsonl에서 문서마다 (doc_id, 기관 이름들, 사업명 핵심)을 읽는다."""
    if data_dir is None:
        from rfp_rag.settings import load
        data_dir = load()["data_dir"]
    rows = []
    with open(Path(data_dir) / "processed" / "docs.jsonl", encoding="utf-8") as fh:
        for line in fh:
            d = json.loads(line)
            rows.append(dict(doc_id=d["doc_id"], agency=d["agency"], title=d["title"],
                             variants=_agency_variants(d["agency"]), core=_title_core(d["title"])))
    return tuple(rows)


def doc_info(data_dir=None):
    """doc_id -> {agency, title}. classify()의 info 인자로 쓴다."""
    return {r["doc_id"]: {"agency": r["agency"], "title": r["title"]} for r in _doc_table(data_dir)}


AGENCY_MIN = 90   # 기관 이름이 질문에 든 정도(rapidfuzz partial_ratio). 3~4글자 이름은 그대로 들어 있어야 한다
TITLE_MIN = 92    # 사업명 핵심이 질문에 든 정도. 핵심이 6글자 이상일 때만 본다


def _agency_hit(variants, q):
    """(점수, 이름) 중 가장 높은 것. 짧은 이름은 글자 그대로 있을 때만 센다."""
    best = (0, "")
    for v in variants:
        s = 100 if v in q else (fuzz.partial_ratio(v, q) if len(v) >= 5 else 0)
        if s >= AGENCY_MIN and (s, len(v)) > (best[0], len(best[1])):
            best = (s, v)
    return best


def match_names(question, data_dir=None):
    """질문에 나온 기관·사업 이름으로 문서를 찾는다. [(doc_id, 점수)] 점수 높은 순. 없으면 [].

    기관이 맞으면 그 기관의 문서를 모두 돌려준다(점수는 기관 점수). 같은 기관 문서 중 사업명이 따로 맞는 것이
    있으면 그것만 남긴다. `서울특별시`가 `서울특별시교육청` 안에 들어 있는 것처럼 더 긴 이름이 맞으면 짧은 쪽은 뺀다.
    기관이 안 맞고 사업명만 맞으면 그 문서들만 돌려준다.
    """
    q = _ns(question)
    rows = _doc_table(data_dir)
    hits = {r["doc_id"]: _agency_hit(r["variants"], q) for r in rows}
    hits = {d: h for d, h in hits.items() if h[0]}
    names = {h[1] for h in hits.values()}
    hits = {d: h for d, h in hits.items() if not any(h[1] != n and h[1] in n for n in names)}
    title = {r["doc_id"]: fuzz.partial_ratio(r["core"], q) for r in rows if len(r["core"]) >= 6}
    title = {d: s for d, s in title.items() if s >= TITLE_MIN}
    out = {}
    for d, (s, name) in hits.items():
        same = [x for x in title if x in hits and hits[x][1] == name]
        if title and same and d not in title:
            continue  # 같은 기관의 다른 문서가 사업명까지 맞으면 그 문서만 남긴다
        out[d] = s
    for d, s in title.items():
        out.setdefault(d, s)
    return sorted(out.items(), key=lambda x: -x[1])


def name_filter(question, data_dir=None):
    """질문에서 찾은 문서 번호 목록(검색 범위를 좁힐 때 쓴다). 이름이 없으면 []."""
    return [d for d, _ in match_names(question, data_dir)]
