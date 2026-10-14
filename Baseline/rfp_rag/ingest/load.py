"""원본 hwp, pdf와 data_list.csv를 읽어 `<data_dir>/processed/docs.jsonl`을 만든다.

docs.jsonl (한 줄에 문서 하나): doc_id, agency, title, amount, deadline, source_file,
    file_type, method, text, csv_text_len, fallback, open_error(열기 실패 시 예외 이름)
    - doc_id: CSV `공고 번호`. 비어 있는 18건은 `NOID-<CSV 행 번호 3자리>`로 채운다.
    - method: `olefile` | `pymupdf` | `csv`(잠겼거나 열리지 않는 문서를 CSV `텍스트`로 대신함)
    - clean_stats: 전처리 단계마다 줄어든 글자 수(clean.py, hf는 hwp 머리말·꼬리말·각주). csv로 대신한 문서는 {}
extract_table.csv: 문서마다 file, method, chars, csv_text_len, fallback 한 줄.

hwp는 olefile로 BodyText를 직접 읽는다. pyhwp의 hwp5html은 표 구조를 살리지만 큰 파일에서
문서당 46~129초가 걸린다. 여기서는 표 칸 경계를 레코드 수준으로 직접 따라가
(칸 사이는 ` | `, 줄 사이는 줄바꿈) 표 구조를 가볍게 남기고, hwp5html은 쓰지 않는다.
"""
import csv
import re
import struct
import unicodedata
import zlib
from collections import Counter
from pathlib import Path

import olefile
import pymupdf

# 한 글자 뒤에 14바이트(7글자)의 부가 정보가 붙는 제어 문자(확장 제어, 인라인 제어)
_SKIP7 = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}
FALLBACK_LIMIT = 10


def _para_text(body):
    """PARA_TEXT 레코드 본문을 글자로 바꾼다. 제어 문자와 그 부가 정보는 버린다."""
    s = body.decode("utf-16le", "ignore")
    out, i = [], 0
    while i < len(s):
        c = ord(s[i])
        if c in _SKIP7:
            i += 8
        elif c < 32:
            i += 1
            if c == 10:
                out.append("\n")
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


HF_IDS = {b"daeh", b"toof", b"  nf", b"  ne"}  # 머리말, 꼬리말, 각주, 미주 컨트롤 (글자 순서가 뒤집혀 저장된다)


def _read_section(data, skip_hf, st):
    """BodyText 한 조각의 레코드를 따라가며 st(out, tables, hf_chars)에 글을 쌓는다."""
    out, tables = st["out"], st["tables"]  # tables: [표 레벨, 마지막 칸의 행 번호]
    hf, i = None, 0  # hf: 머리말 등 컨트롤의 레벨(그 안의 문단은 더 깊은 레벨)
    while i < len(data):
        h = struct.unpack("<I", data[i:i + 4])[0]
        i += 4
        tag, level, size = h & 0x3FF, (h >> 10) & 0x3FF, h >> 20
        if size == 0xFFF:
            size = struct.unpack("<I", data[i:i + 4])[0]
            i += 4
        body = data[i:i + size]
        i += size
        while tables and level <= tables[-1][0]:  # 표가 끝났다
            tables.pop()
            out.append("\n")
        if hf is not None and level <= hf:
            hf = None
        if hf is None and tag == 71 and body[:4] in HF_IDS:
            hf = level
        if hf is not None:
            if tag == 67:
                st["hf_chars"] += len(_para_text(body).strip())
            if skip_hf:
                continue
        if tag == 71 and body[:4] == b" lbt":  # CTRL_HEADER 'tbl '
            tables.append([level, -1])
        elif tag == 72 and tables and level == tables[-1][0] + 1 and len(body) >= 12:
            row = struct.unpack("<H", body[10:12])[0]  # LIST_HEADER: 칸의 행 번호
            if tables[-1][1] >= 0:
                out.append("\n" if row != tables[-1][1] else " | ")
            tables[-1][1] = row
        elif tag == 67:
            t = _para_text(body)
            out.append(t.replace("\n", " ") + " " if tables else t.rstrip("\n") + "\n")


def hwp_read(path, skip_hf=False):
    """hwp 하나를 읽어 글과 문서 정보를 dict로 돌려준다. 잠긴 문서는 text가 빈 문자열.

    version은 FileHeader의 4바이트를 `5.1.0.1`처럼 큰 자리부터 적은 것.
    skip_hf=True면 머리말, 꼬리말, 각주, 미주 안의 문단을 text에서 뺀다(hf_chars에는 세어 둔다).
    """
    f = olefile.OleFileIO(str(path))
    try:
        hdr = f.openstream("FileHeader").read()
        flags = struct.unpack("<I", hdr[36:40])[0]
        secs = sorted((s for s in f.listdir() if s[0] == "BodyText"), key=lambda s: int(s[1][7:]))
        res = dict(
            text="", locked=bool(flags & 4), encrypted=bool(flags & 2), compressed=bool(flags & 1),
            version=".".join(str(b) for b in reversed(hdr[32:36])), sections=len(secs),
            images=sum(1 for s in f.listdir() if s[0] == "BinData"), hf_chars=0,
            has_summary=f.exists("\x05HwpSummaryInformation"),
        )
        if res["locked"]:  # 배포용 문서(글이 ViewText에 암호화되어 있다)
            return res
        st = dict(out=[], tables=[], hf_chars=0)
        for s in secs:
            data = f.openstream(s).read()
            if flags & 1:
                data = zlib.decompress(data, -15)
            _read_section(data, skip_hf, st)
        t = re.sub(r"[ \t]{2,}", " ", "".join(st["out"]))  # 칸 안쪽에 겹친 공백을 줄인다
        res["text"] = re.sub(r" ?\n(?: ?\n)+", "\n\n", t)
        res["hf_chars"] = st["hf_chars"]
        return res
    finally:
        f.close()


def hwp_text(path):
    """(글, 잠김 여부). 잠김이면 글은 빈 문자열."""
    r = hwp_read(path)
    return r["text"], r["locked"]


def pdf_text(path):
    with pymupdf.open(str(path)) as d:
        return "\n".join(p.get_text() for p in d)


def pdf_read(path):
    """pdf 하나의 글(pdf_text와 같다)과 쪽수, 암호 여부, 글이 없는 쪽 수, 그림 수."""
    with pymupdf.open(str(path)) as d:
        enc = bool(d.needs_pass or d.is_encrypted)
        texts = [] if d.needs_pass else [p.get_text() for p in d]
        return dict(
            text="\n".join(texts), pages=len(d), encrypted=enc,
            empty_pages=sum(1 for t in texts if not t.strip()),
            images=0 if d.needs_pass else sum(len(p.get_images()) for p in d),
        )


def doc_meta(n, r, name):
    """CSV 한 행(번호 n)에서 청크에 붙일 메타데이터를 만든다."""
    amount = r["사업 금액"].strip()
    return dict(
        doc_id=r["공고 번호"].strip() or f"NOID-{n:03d}",
        agency=r["발주 기관"].strip(), title=r["사업명"].strip(),
        amount=int(float(amount)) if amount else None,
        deadline=r["입찰 참여 마감일"].strip() or None, source_file=name,
    )


def load_docs(data_dir):
    """문서 100건의 글과 메타데이터를 읽는다. 뽑은 글은 전처리(clean)를 거친다.
    잠겼거나 열리지 않는 파일은 CSV `텍스트`로 대신하고, 이 글에는 전처리를 하지 않는다."""
    from rfp_rag.ingest.clean import extract  # clean이 이 파일을 가져오므로 여기서 불러온다

    raw = Path(data_dir) / "raw"
    docs = []
    with open(raw / "data_list.csv", encoding="utf-8-sig", newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh)):
            name = unicodedata.normalize("NFC", r["파일명"])
            kind = "pdf" if name.lower().endswith(".pdf") else "hwp"
            text, method, locked, open_error, stats = "", ("pymupdf" if kind == "pdf" else "olefile"), False, None, {}
            try:  # 파일 하나가 열리지 않아도 전체가 멈추지 않는다
                _, text, stats, locked = extract(raw / name, kind)
            except Exception as e:
                open_error = type(e).__name__
            fallback = bool(locked or open_error)
            if fallback:
                text, method, stats = r["텍스트"], "csv", {}
            docs.append(dict(
                **doc_meta(n, r, name), file_type=kind, method=method, text=text.strip(),
                csv_text_len=len(r["텍스트"]), fallback=fallback, open_error=open_error, clean_stats=stats,
            ))
    return docs


def write_table(docs, path):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "method", "chars", "csv_text_len", "fallback"])
        for d in docs:
            w.writerow([d["source_file"], d["method"], len(d["text"]), d["csv_text_len"], "yes" if d["fallback"] else "no"])


if __name__ == "__main__":
    # 자체 점검: 글 뽑기가 깨지면 여기서 실패한다.
    assert _para_text(("가\x02" + "\x00" * 7 + "나\r").encode("utf-16le")) == "가나"

    # 머리말 안의 문단은 hf_chars에 세고, skip_hf면 글에서 뺀다
    def rec(tag, level, body):
        return struct.pack("<I", tag | level << 10 | len(body) << 20) + body

    syn = (rec(67, 0, "본문\r".encode("utf-16le")) + rec(71, 0, b"daeh" + bytes(4)) + rec(72, 1, bytes(12))
           + rec(67, 1, "머리글\r".encode("utf-16le")) + rec(67, 0, "끝\r".encode("utf-16le")))
    for skip, want in ((False, "본문\n머리글\n끝\n"), (True, "본문\n끝\n")):
        st = dict(out=[], tables=[], hf_chars=0)
        _read_section(syn, skip, st)
        assert "".join(st["out"]) == want and st["hf_chars"] == 3, (skip, st)
    from rfp_rag.settings import load

    dd =Path(load()["data_dir"])
    docs = load_docs(dd)
    assert len(docs) == 100, len(docs)
    assert sum(d["fallback"] for d in docs) <= FALLBACK_LIMIT, "CSV로 대신한 문서가 10건을 넘었다"
    assert all(len(d["text"]) > d["csv_text_len"] for d in docs if not d["fallback"]), "CSV보다 짧은 문서가 있다"
    removed = Counter()
    for d in docs:
        removed.update(d["clean_stats"])
    print("전처리로 줄어든 글자 수(단계별 합계):", dict(removed))
    print("ok:", len(docs), "건, 대신한 문서", sum(d["fallback"] for d in docs),
          "건, 열기 실패", sum(bool(d["open_error"]) for d in docs), "건")
