"""문서를 청크로 자른다. `python -m rfp_rag.ingest.chunk [--exp 이름]`이 글 뽑기부터 다시 만든다.

<data_dir>/processed/ 에 쓰는 파일 (모두 한 줄에 JSON 하나, UTF-8):
  docs.jsonl           문서당 한 줄. doc_id, agency, title, amount, deadline, source_file,
                       file_type, method, text, csv_text_len, fallback  (load.py 참고)
  extract_table.csv    file, method, chars, csv_text_len, fallback
  chunks_fixed.jsonl   `fixed` 청크. 설정의 chunk.size / chunk.overlap 으로 자른다.
  chunks_section.jsonl `section` 청크. 제목 패턴으로 자르고 긴 절은 fixed로 다시 자른다.

청크 한 줄의 필드: text, doc_id, chunk_id, agency, title, section_path, amount, deadline,
source_file.
  - text는 항상 `[발주 기관] 사업명` 줄로 시작한다(그 뒤가 본문). size는 본문 길이 기준이다.
  - doc_id는 CSV `공고 번호`(비어 있는 18건은 `NOID-<행 번호>`), chunk_id는 `<doc_id>:<방식>:<번호>`.
  - section_path는 `Ⅰ. 사업 안내 > 1. 사업개요`처럼 ` > `로 이은 제목 경로. fixed는 빈 문자열.
검색 쪽은 `load_chunks(cfg)`로 설정의 chunk.method에 맞는 파일을 읽는다.
"""
import argparse
import json
import re
import statistics
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from rfp_rag.ingest.load import load_docs, write_table

# 제목 패턴: (수준, 정규식). 수준이 작을수록 큰 제목이다.
HEADINGS = [
    (1, re.compile(r"^(?:[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*\.|제\s*\d+\s*[장편])")),
    (2, re.compile(r"^\d{1,2}\.\s")),
    (3, re.compile(r"^(?:[가-하]\.\s|\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s)")),
    (4, re.compile(r"^\d{1,2}\)\s")),
    # 요구사항 고유번호: 줄 맨 앞의 SFR-001 이나, 표의 `요구사항 고유번호 | SFR-001`
    (5, re.compile(r"^(?:요구\s*사항\s*(?:고유\s*번호|ID|번호)\s*\|\s*)?([A-Z]{2,4}\s?-\s?\d{2,3})\b")),
]
MIN_SECTION = 100  # 이보다 짧은 절은 다음 절에 붙인다(목차 줄 등)


def _prefix(doc):
    return f"[{doc['agency']}] {doc['title']}\n"


def _meta(doc, method, n, section_path, body):
    return dict(
        text=_prefix(doc) + body, doc_id=doc["doc_id"], chunk_id=f"{doc['doc_id']}:{method}:{n:04d}",
        agency=doc["agency"], title=doc["title"], section_path=section_path,
        amount=doc["amount"], deadline=doc["deadline"], source_file=doc["source_file"],
    )


def _splitter(size, overlap):
    return RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)


def chunk_fixed(doc, size=1000, overlap=200):
    parts = _splitter(size, overlap).split_text(doc["text"])
    return [_meta(doc, "fixed", n, "", p) for n, p in enumerate(parts)]


def split_sections(text):
    """글을 제목 줄에서 끊어 [(section_path, 절 글)]로 돌려준다."""
    stack, cur, out = {}, [], []  # stack: 수준 -> 제목

    def flush():
        body = "\n".join(cur).strip()
        if body:
            out.append((" > ".join(stack[k] for k in sorted(stack)), body))
        cur.clear()

    for line in text.split("\n"):
        s = line.strip()
        level = next((lv for lv, rx in HEADINGS if rx.match(s)), 0) if s else 0
        if level:
            flush()
            for k in [k for k in stack if k >= level]:
                del stack[k]
            m = HEADINGS[level - 1][1].match(s)
            stack[level] = re.sub(r"\s*-\s*", "-", m.group(1)) if level == 5 else s[:60]
        cur.append(line)
    flush()
    return out


def chunk_section(doc, size=1000, overlap=200):
    sp, chunks, carry = _splitter(size, overlap), [], ""
    secs = split_sections(doc["text"])
    for i, (path, body) in enumerate(secs):
        body = (carry + "\n" + body).strip() if carry else body
        if len(body) < MIN_SECTION and i < len(secs) - 1:  # 짧은 절은 다음 절로 넘긴다
            carry = body
            continue
        carry = ""
        for p in sp.split_text(body) if len(body) > size else [body]:
            chunks.append(_meta(doc, "section", len(chunks), path, p))
    return chunks


METHODS = {"fixed": chunk_fixed, "section": chunk_section}


def write_jsonl(rows, path):
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def load_chunks(cfg):
    """설정의 chunk.method에 맞는 청크 파일을 읽는다."""
    return read_jsonl(Path(cfg["data_dir"]) / "processed" / f"chunks_{cfg['chunk']['method']}.jsonl")


def build(cfg):
    out = Path(cfg["data_dir"]) / "processed"
    out.mkdir(parents=True, exist_ok=True)
    docs = load_docs(cfg["data_dir"])
    write_jsonl(docs, out / "docs.jsonl")
    write_table(docs, out / "extract_table.csv")
    size, overlap = cfg["chunk"]["size"], cfg["chunk"]["overlap"]
    counts = {}
    for name, fn in METHODS.items():
        rows = [c for d in docs for c in fn(d, size, overlap)]
        write_jsonl(rows, out / f"chunks_{name}.jsonl")
        counts[name] = rows
    return docs, counts


def summary(docs, counts):
    n = [len(d["text"]) for d in docs]
    lines = [
        f"문서 {len(docs)}건, 글자 수 최소 {min(n)} / 중앙값 {int(statistics.median(n))} / 최대 {max(n)}",
        f"CSV 텍스트로 대신한 문서 {sum(d['fallback'] for d in docs)}건",
    ]
    for name, rows in counts.items():
        L = [len(r["text"]) for r in rows]
        lines.append(f"청크 {name}: {len(rows)}개, 길이 중앙값 {int(statistics.median(L))} / 최대 {max(L)}")
    return "\n".join(lines)




if __name__ == "__main__":
    from rfp_rag.settings import load

    ap = argparse.ArgumentParser(description="글을 뽑고 fixed, section 청크를 모두 다시 만든다")
    ap.add_argument("--exp", help="실험 이름 또는 yaml 경로(chunk.size, chunk.overlap을 가져온다)")
    docs, counts = build(load(ap.parse_args().exp))
    assert len(docs) == 100 and all(counts.values()), "글 뽑기나 청크 만들기가 깨졌다"
    print(summary(docs, counts))
