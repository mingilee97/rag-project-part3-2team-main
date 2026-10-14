"""색인하기 전에 문서마다 요약을 미리 만든다(오프라인, 문서별로 캐시해서 끊겼다가 이어서 돌릴 수 있다).

실행:  python -m rfp_rag.ingest.enrich [--exp 이름] [--limit N] [--sections]
  --limit N    문서 N건만(전체에서 고르게 뽑는다). 시간을 재 볼 때 쓴다.
  --sections   큰 제목(Ⅰ, Ⅱ ...)마다 요약도 만든다. 문서 요약보다 훨씬 오래 걸려 따로 돌린다.

<data_dir>/enriched/<doc_id>.json           문서 요약: summary{period, purpose, scope}, summary_text, requirements[{id, name}]
<data_dir>/enriched/<doc_id>.sections.json  큰 제목별 요약: [{section, summary}]
사업명·기관·금액·마감은 CSV 값을 그대로 쓰고, 기간·목적·범위만 로컬 LLM 이 쓴다. 요구사항 목록은 규칙으로 뽑는다.
"""
import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from rfp_rag.answer import doc_info
from rfp_rag.ingest.chunk import read_jsonl

HEAD_CHARS = 4000     # 사업 개요 앞부분에서 읽는 글자 수(num_ctx 8192 에 들어가게)
SECTION_CHARS = 5000  # 큰 제목 하나에서 읽는 글자 수
_DOC_SCHEMA = {"type": "object", "required": ["period", "purpose", "scope"],
               "properties": {k: {"type": "string"} for k in ("period", "purpose", "scope")}}
_SEC_SCHEMA = {"type": "object", "required": ["summary"], "properties": {"summary": {"type": "string"}}}
_DOC_PROMPT = """아래는 공공 입찰 제안요청서의 사업 개요 부분이다. 적힌 내용만 써서 JSON 으로 정리한다.
- period: 사업 기간 (한 줄. 없으면 "")
- purpose: 사업의 목적과 배경 (두 문장 이내)
- scope: 주요 사업 범위와 핵심 요구 (세 문장 이내)

{text}"""
_SEC_PROMPT = """아래는 공공 입찰 제안요청서 「{title}」의 한 부분(제목: {section})이다. 담긴 내용을 세 문장 이내로 요약한다.
금액, 날짜, 수량은 적힌 그대로 쓴다. JSON 한 줄로 {{"summary": "..."}} 만 답한다.

{text}"""
# 줄 맨 앞의 "1. 사업개요", "1.1 사 업 명", "□ 사업명:" 같은 제목. 쪽 번호로 끝나는 목차 줄은 뺀다.
_BODY_START = re.compile(r"^[ \t]*(?:[□○■▶]\s*)?(?:\d+(?:\.\d+)*[.)]?\s*)?사\s*업\s*(?:명|개\s*요)(?![^\n]*[.·…\s]\d{1,3}[ \t]*$)", re.M)
_REQ = re.compile(r"요구\s*사항\s*명칭?\s*\|\s*([^|\n]{2,60})")


def enriched_dir(cfg):
    return Path(cfg["data_dir"]) / "enriched"


def body_head(text, n=HEAD_CHARS):
    """목차를 건너뛴 본문 첫머리. 사업 개요 제목이 나오는 곳부터 n 글자(못 찾으면 맨 앞부터)."""
    m = _BODY_START.search(text)
    return text[m.start():m.start() + n] if m else text[:n]


def requirement_list(chunks):
    """section 청크의 제목 경로에 든 요구사항 고유번호(SFR-001 ...)와 요구사항 명칭."""
    seen = {}
    for c in chunks:
        m = re.search(r"\b([A-Z]{2,4}-\d{2,3})\s*$", c["section_path"])
        if m and m.group(1) not in seen:
            n = re.search(m.group(1).replace("-", r"\s?-\s?") + r"\s*\|\s*([^|\n]{2,60})", c["text"]) or _REQ.search(c["text"])
            seen[m.group(1)] = n.group(1).strip() if n else ""
    return [{"id": k, "name": v} for k, v in seen.items()]


def summary_text(d, s):
    amt = f"{d['amount']:,}원" if d["amount"] else "정보 없음"
    return (f"[{d['agency']}] {d['title']}\n사업 금액: {amt} / 입찰 마감: {d['deadline'] or '정보 없음'} / 사업 기간: {s['period'] or '정보 없음'}\n"
            f"목적: {s['purpose']}\n주요 범위: {s['scope']}" + (f"\n요약: {d['csv_summary']}" if d["csv_summary"] else ""))


def _ask(cfg, schema, prompt, key=None):
    from rfp_rag.providers import get_llm
    r = json.loads(get_llm(cfg, json_schema=schema, purpose="enrich").invoke(prompt).content)
    return r[key] if key else r


def enrich_doc(d, chunks, cfg):
    s = _ask(cfg, _DOC_SCHEMA, _DOC_PROMPT.format(text=body_head(d["text"])))
    s = {k: str(s.get(k, "")).strip() for k in ("period", "purpose", "scope")}
    return {"doc_id": d["doc_id"], "summary": s, "summary_text": summary_text(d, s), "requirements": requirement_list(chunks)}


def enrich_sections(d, chunks, cfg):
    by = defaultdict(list)
    for c in chunks:
        top = c["section_path"].split(" > ")[0]
        if top:
            by[top].append(c["text"].split("\n", 1)[-1])  # 첫 줄은 [기관] 사업명 머리글
    return [{"section": t, "summary": _ask(cfg, _SEC_SCHEMA, _SEC_PROMPT.format(title=d["title"], section=t,
             text="\n".join(v)[:SECTION_CHARS]), "summary").strip()} for t, v in by.items()]


def load_summaries(cfg):
    """search 가 쓰는 문서별 요약 [{doc_id, summary_text, ...}]. 아직 만들지 않은 문서는 빠진다."""
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(enriched_dir(cfg).glob("*.json"))
            if not p.name.endswith(".sections.json")]


def run(cfg, limit=None, sections=False, log=print):
    """문서별로 캐시가 없으면 만든다. (건수, 문서당 초 목록)을 돌려준다."""
    out = enriched_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    info = doc_info(cfg)
    ids = list(info)
    if limit:
        ids = ids[::max(1, len(ids) // limit)][:limit]
    by_doc = defaultdict(list)
    for c in read_jsonl(Path(cfg["data_dir"]) / "processed" / "chunks_section.jsonl"):
        by_doc[c["doc_id"]].append(c)
    secs = []
    for n, i in enumerate(ids, 1):
        path = out / (f"{i}.sections.json" if sections else f"{i}.json")
        if path.exists():
            continue
        t0 = time.time()
        try:
            res = enrich_sections(info[i], by_doc[i], cfg) if sections else enrich_doc(info[i], by_doc[i], cfg)
        except Exception as e:  # 한 건이 실패해도 나머지는 계속한다. 다음에 돌리면 이 건부터 다시 한다.
            log(f"[{n}/{len(ids)}] {i} 실패: {type(e).__name__} {str(e)[:80]}")
            continue
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        secs.append(time.time() - t0)
        log(f"[{n}/{len(ids)}] {i} {secs[-1]:.1f}초" + (f" (큰 제목 {len(res)}개)" if sections else ""))
    return secs




if __name__ == "__main__":
    from rfp_rag.settings import load

    ap = argparse.ArgumentParser()
    ap.add_argument("--exp")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sections", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    s = run(load(a.exp), a.limit, a.sections, log=lambda m: print(m, flush=True))
    if s:
        print(f"새로 만든 {len(s)}건: 문서당 평균 {sum(s) / len(s):.1f}초, 합계 {time.time() - t0:.0f}초")
