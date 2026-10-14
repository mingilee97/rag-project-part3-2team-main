"""근거에 번호를 붙여 모델에게 주고, JSON `{answer, evidence_ids, found}` 로 답을 받는다.

- `generate`: 근거 문서 목록 -> 답 하나. `answer`: generate + 규칙 확인(숫자·금액·날짜가 인용한 근거에 있는지).
- 확인에 걸리면 한 번 다시 묻고, 그래도 걸리는 문장은 뺀다.
- `doc_info`: docs.jsonl 과 data_list.csv(표준 csv)를 합친 문서별 정보. meta 종류의 답과 이름 매칭이 쓴다.
"""
import csv
import json
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

NOT_FOUND = "문서에서 찾을 수 없습니다."
SCHEMA = {"type": "object", "required": ["answer", "evidence_ids", "found"],
          "properties": {"answer": {"type": "string"}, "evidence_ids": {"type": "array", "items": {"type": "integer"}},
                         "found": {"type": "boolean"}}}
SYSTEM = ("너는 공공 입찰 제안요청서(RFP)를 읽고 답하는 도우미다. 아래 [근거]에 적힌 내용만 써서 한국어로 답한다.\n"
          "- 근거에 답이 없으면 found 를 false, answer 를 \"" + NOT_FOUND + "\" 로 쓴다. 추측하지 않는다.\n"
          "- 금액, 날짜, 수량, 이름은 근거에 적힌 그대로 옮긴다. 근거에 없는 숫자를 만들지 않는다.\n"
          "- 답에 쓴 내용이 나온 근거 번호를 evidence_ids 에 모두 넣는다.\n"
          "- 여러 항목은 줄을 나눠 번호나 글머리로 정리한다.\n"
          "JSON 한 개만 출력한다: {\"answer\": 글, \"evidence_ids\": [번호...], \"found\": true 또는 false}")


# ---- 문서 정보 ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _info(data_dir):
    d = Path(data_dir)
    by_file = {}
    with open(d / "raw" / "data_list.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            by_file[r["파일명"].strip()] = r
    out = {}
    with open(d / "processed" / "docs.jsonl", encoding="utf-8") as f:
        for line in f:
            x = json.loads(line)
            r = by_file.get(x["source_file"], {})
            out[x["doc_id"]] = dict(
                doc_id=x["doc_id"], agency=x["agency"], title=x["title"], amount=x["amount"], deadline=x["deadline"],
                source_file=x["source_file"], text=x["text"], announced=r.get("공개 일자", "").strip(),
                start=r.get("입찰 참여 시작일", "").strip(), csv_summary=r.get("사업 요약", "").strip())
    return out


def doc_info(cfg):
    """doc_id -> dict(agency, title, amount, deadline, announced, start, csv_summary, text, ...)"""
    return _info(str(cfg["data_dir"]))


def meta_doc(info):
    """CSV 값을 한 덩어리 근거로 만든다(chunk_id 는 `<doc_id>:meta`)."""
    amt = f"{info['amount']:,}원" if info["amount"] else "정보 없음"
    lines = [f"[{info['agency']}] {info['title']}", f"공고 번호: {info['doc_id']}", f"발주 기관: {info['agency']}",
             f"사업 금액: {amt}", f"공개 일자: {info['announced'] or '정보 없음'}",
             f"입찰 참여 시작일: {info['start'] or '정보 없음'}", f"입찰 참여 마감일: {info['deadline'] or '정보 없음'}"]
    if info["csv_summary"]:
        lines.append("사업 요약: " + info["csv_summary"][:600])
    return Document(page_content="\n".join(lines), metadata={"doc_id": info["doc_id"], "chunk_id": f"{info['doc_id']}:meta"})


# ---- 규칙 확인 ---------------------------------------------------------------------------
_DATE = re.compile(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})")
_KOR_AMT = re.compile(r"(?:\d[\d,]*(?:\.\d+)?\s*(?:천만|백만|억|만|천)\s*)+")
_KOR_PART = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(천만|백만|억|만|천)")
_UNIT = {"천만": 1e7, "백만": 1e6, "억": 1e8, "만": 1e4, "천": 1e3}
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?(%?)")
_ID = re.compile(r"\b([A-Z]{2,4})\s?-\s?(\d{2,3})\b")  # 요구사항 고유번호 SFR-004. 숫자가 아니라 글자 그대로 맞춘다


def _facts(text):
    """(날짜 집합, 숫자 값 집합, 확인이 필요한 숫자, 고유번호 집합). 3자리 이상 숫자, %, 억·만 단위 금액만 확인 대상으로 본다."""
    ids = {f"{a}-{b}" for a, b in _ID.findall(text)}
    text = _ID.sub(" ", text)
    dates = {f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in _DATE.findall(text)}
    text = _DATE.sub(" ", text)
    values, checked = set(), set()
    for m in _KOR_AMT.finditer(text):
        v = sum(float(n.replace(",", "")) * _UNIT[u] for n, u in _KOR_PART.findall(m.group()))
        values.add(round(v))
        checked.add(round(v))
    text = _KOR_AMT.sub(" ", text)
    for m in _NUM.finditer(text):
        raw = m.group().rstrip("%").replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        values.add(round(v, 3))
        if len(raw.split(".")[0]) >= 3 or m.group(1):
            checked.add(round(v, 3))
    return dates, values, checked, ids


def unsupported(text, evidence):
    """text 에 있는 날짜·숫자 중 evidence 에 없는 것들의 목록. 비어 있으면 통과."""
    e_dates, e_values, _, e_ids = _facts(evidence)
    dates, _, checked, ids = _facts(text)
    return sorted(ids - e_ids) + sorted(dates - e_dates) + [f"{n:,.10g}" for n in sorted(checked - e_values)]


def drop_unsupported(text, evidence):
    """근거에 없는 숫자가 든 문장(줄 안에서 문장 단위)을 뺀 글."""
    lines = []
    for line in text.split("\n"):
        keep = [s for s in re.split(r"(?<=[.!?])\s+", line) if not unsupported(s, evidence)]
        if keep:
            lines.append(" ".join(keep))
    return "\n".join(lines).strip()


# ---- 답 만들기 ---------------------------------------------------------------------------
def _context(docs):
    out = []
    for i, d in enumerate(docs, 1):
        sp = d.metadata.get("section_path")
        out.append(f"[{i}]" + (f" ({sp})" if sp else "") + "\n" + d.page_content.strip())
    return "\n\n".join(out)


def generate(question, docs, cfg, purpose="answer", note=""):
    """{answer, found, cited: [docs 안의 Document], given: 모델에게 준 docs 전부}. 모델이 JSON 을 못 지키면 글 전체를 답으로 본다.
    given 은 모델을 부른 뒤의 어떤 반환(찾을 수 없음 포함)에도 들어 있다."""
    from rfp_rag.providers import get_llm
    llm = get_llm(cfg, json_schema=SCHEMA, purpose=purpose)
    user = f"[근거]\n{_context(docs)}\n\n[질문]\n{question}" + (f" ({note})" if note else "")
    try:
        raw = llm.invoke([("system", SYSTEM), ("human", user)]).content
    except Exception:  # 같은 말을 되풀이하다 끊긴 경우 등: 질문 하나 때문에 전체가 멈추지 않게 "찾을 수 없음"으로 답한다
        return {"answer": NOT_FOUND, "found": False, "cited": [], "given": list(docs)}
    try:
        r = json.loads(raw)
        ans, ids, found = str(r["answer"]).strip(), r.get("evidence_ids") or [], bool(r.get("found", True))
    except (ValueError, KeyError, TypeError):
        ans, ids, found = str(raw).strip(), [], True
    cited = [docs[i - 1] for i in dict.fromkeys(ids) if isinstance(i, int) and 1 <= i <= len(docs)]
    if not found or not ans:
        return {"answer": NOT_FOUND, "found": False, "cited": [], "given": list(docs)}
    return {"answer": ans, "found": True, "cited": cited or list(docs), "given": list(docs)}


def answer(question, docs, cfg, verify=False, purpose="answer", note=""):
    """generate 한 번 + (verify 이면) 규칙 확인. 근거 밖 값이 있으면 한 번 다시 묻고, 두 답에서 각각
    근거 밖 문장을 뺀 뒤 더 긴 쪽을 쓴다(다시 물은 답이 오히려 짧아지는 일을 막는다)."""
    out = generate(question, docs, cfg, purpose, note)
    if not (verify and out["found"]):
        return out
    ev = lambda o: "\n".join(d.page_content for d in o["cited"])  # noqa: E731
    bad = unsupported(out["answer"], ev(out))
    if not bad:
        return out
    retry = generate(question, docs, cfg, purpose, note=(note + " " if note else "")
                     + f"근거에 없는 값({', '.join(bad)})은 쓰지 말고 근거에 있는 내용만 빠짐없이 정리한다")
    best = {"answer": "", "found": False, "cited": []}
    for o in (out, retry):
        if o["found"]:
            o = dict(o, answer=drop_unsupported(o["answer"], ev(o)))
            if len(o["answer"]) > len(best["answer"]):
                best = o
    return best if best["answer"] else {"answer": NOT_FOUND, "found": False, "cited": [], "given": list(docs)}


# ---- 항목별로 옮겨 적는 답 (pipeline.detail) -----------------------------------------------
_ITEMS_SYSTEM = ("공공 입찰 제안요청서(RFP)에 대한 질문이 묻는 것을 항목 목록으로 뽑는다.\n"
                 "- 항목은 6개까지, 짧은 명사구로 쓴다. 예) 사업 기간, 계약 방법, 새로 구축하는 시스템\n"
                 "- 질문이 하나만 묻고 있으면 항목 하나로 둔다.\n"
                 "- \"정리해 줘\", \"요구사항\", \"주요 과업\"처럼 범위가 넓으면 [소제목]마다 항목 하나로 나눈다(소제목이 없으면 질문이 뜻하는 갈래로 나눈다).\n"
                 "JSON 한 개만 출력한다: {\"items\": [항목...]}")
_ITEMS_SCHEMA = {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "maxItems": 6, "items": {"type": "string"}}}}
_EXTRACT_SYSTEM = ("너는 공공 입찰 제안요청서(RFP)의 [근거]에서 항목별로 내용을 옮겨 적는 도우미다. [근거]에 적힌 것만 쓴다.\n"
                   "- 요약하지 않는다. 숫자, 이름, 요구사항 번호(예: SFR-004), 금액, 날짜는 근거에 적힌 그대로 옮긴다.\n"
                   "- 항목에 해당하는 내용은 근거에 있는 대로 하나도 빼지 않고 lines 에 한 줄씩 담는다. 요구사항이 여럿이면 모두 적는다.\n"
                   "- 근거에 없는 항목은 lines 를 빈 목록으로 둔다. 추측하지 않는다.\n"
                   "- 항목마다 옮긴 내용이 나온 근거 번호를 evidence_ids 에 넣는다.\n"
                   "JSON 한 개만 출력한다: {\"items\": [{\"item\": 항목, \"lines\": [글...], \"evidence_ids\": [번호...]}]}")
_EXTRACT_SCHEMA = {"type": "object", "required": ["items"], "properties": {"items": {"type": "array", "items": {
    "type": "object", "required": ["item", "lines", "evidence_ids"],
    "properties": {"item": {"type": "string"}, "lines": {"type": "array", "items": {"type": "string"}},
                   "evidence_ids": {"type": "array", "items": {"type": "integer"}}}}}}}
ITEM_MISSING = "문서에서 찾지 못했습니다."


def _json_call(cfg, schema, purpose, system, user):
    """로컬 LLM 을 한 번 불러 JSON dict 를 돌려준다. 실패하면 None."""
    from rfp_rag.providers import get_llm
    try:
        return json.loads(get_llm(cfg, json_schema=schema, purpose=purpose).invoke([("system", system), ("human", user)]).content)
    except Exception:  # noqa: BLE001 - 끊기거나 JSON 을 못 지킨 경우
        return None


def detail(question, docs, cfg, verify=False, purpose="answer", note=""):
    """항목 목록을 뽑고(1) 항목마다 근거에서 옮겨 적게 한 뒤(2) 코드가 이어 붙인다. 반환 모양은 generate 와 같다.
    verify 이면 줄마다 drop_unsupported 로 근거에 없는 값이 든 문장만 뺀다. 모두 비면 NOT_FOUND. 두 번째 호출이 깨지면 generate 로 돌아간다."""
    heads = list(dict.fromkeys(d.metadata["section_path"] for d in docs if d.metadata.get("section_path")))
    r = _json_call(cfg, _ITEMS_SCHEMA, purpose + "_items", _ITEMS_SYSTEM,
                   f"[질문]\n{question}" + (f"\n[소제목]\n" + "\n".join(heads[:12]) if heads else ""))
    items = [str(i).strip() for i in (r or {}).get("items", []) if str(i).strip()][:6] or [question]
    tail = f"[근거]\n{_context(docs)}\n\n[질문]\n{question}" + (f" ({note})" if note else "") + "\n[항목]\n" + "\n".join(f"- {i}" for i in items)
    r = _json_call(cfg, _EXTRACT_SCHEMA, purpose + "_extract", _EXTRACT_SYSTEM, tail)
    if not r or not isinstance(r.get("items"), list):
        return generate(question, docs, cfg, purpose, note)
    got = []
    for x in r["items"]:
        if isinstance(x, dict):
            lines = [re.sub(r"^\s*[-•*]\s*", "", str(t)).strip() for t in x.get("lines") or []]
            got.append((str(x.get("item", "")).strip() or "내용", [t for t in lines if t], x.get("evidence_ids") or []))
    ids = [i for _, _, e in got for i in e if isinstance(i, int) and 1 <= i <= len(docs)]
    cited = [docs[i - 1] for i in dict.fromkeys(ids)] or list(docs)
    ev = "\n".join(d.page_content for d in cited)
    blocks, filled = [], False
    for item, lines, _ in got:
        if verify:
            lines = [t for t in (drop_unsupported(t, ev) for t in lines) if t]
        filled = filled or bool(lines)
        blocks.append(f"**{item}**\n" + ("\n".join(f"- {t}" for t in lines) if lines else f"- {ITEM_MISSING}"))
    if not filled:
        return {"answer": NOT_FOUND, "found": False, "cited": [], "given": list(docs)}
    return {"answer": "\n\n".join(blocks), "found": True, "cited": cited, "given": list(docs)}




if __name__ == "__main__":
    print("답 확인 규칙 자체 점검 통과")
