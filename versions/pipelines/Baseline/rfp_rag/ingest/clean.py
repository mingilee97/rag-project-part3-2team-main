"""문서에서 뽑은 글을 정규화하고 쪽 번호·목차·빈 표를 정리한다."""
import re
import unicodedata

from rfp_rag.ingest.eda import PAGE_RE, toc_blocks
from rfp_rag.ingest.load import hwp_read, pdf_read

PUA = re.compile("[-\U000f0000-\U0010ffff�]")  # 글머리 기호 등 사용자 정의 영역, U+FFFD
TOC_HEAD_SHARE = 0.2  # 문서 앞 20% 안에서 시작한 목차 덩어리만 지운다


def _drop(text, bad):
    """bad(줄)이 참인 줄을 줄바꿈과 함께 지운다."""
    return "\n".join(l for l in text.split("\n") if not bad(l))


def nfc(text, kind):
    return unicodedata.normalize("NFC", text)  # NFKC는 Ⅰ을 I로 바꿔 제목 패턴을 깨므로 쓰지 않는다


def pua(text, kind):
    return PUA.sub("", text)


def page_num(text, kind):
    """쪽 번호만 있는 줄. hwp는 꾸민 모양(`- 12 -`, `12 / 30`, `Page 12`, `[12]`, `(12)`)만, pdf는 숫자만 있는 줄도 지운다."""
    return _drop(text, lambda l: bool(PAGE_RE.match(l)) and (kind == "pdf" or not l.strip().isdigit()))


def early_toc_lines(text):
    """지울 목차 줄의 번호 집합: 문서 앞 20% 안에서 시작한 목차 덩어리."""
    lines = text.split("\n")
    return {i for a, b, pos in toc_blocks(lines) if pos < TOC_HEAD_SHARE * len(text) for i in range(a, b + 1)}


def toc(text, kind):
    drop = early_toc_lines(text)
    return "\n".join(l for i, l in enumerate(text.split("\n")) if i not in drop)


def empty_table(text, kind):
    """`|`와 공백만 있는 표 줄(칸이 모두 빈 줄)."""
    return _drop(text, lambda l: "|" in l and not l.replace("|", "").strip())


STEPS = [("nfc", nfc), ("pua", pua), ("page_num", page_num), ("toc", toc), ("empty_table", empty_table)]


def clean(text, kind):
    """kind는 "hwp" 또는 "pdf". 돌려주는 값: (다듬은 글, {단계 이름: 줄어든 글자 수})."""
    stats = {}
    for name, fn in STEPS:
        new = fn(text, kind)
        stats[name], text = len(text) - len(new), new
    return re.sub(r"\n{3,}", "\n\n", text), stats


def extract(path, kind, with_raw=False):
    """(원본 글, 다듬은 글, 단계별 줄어든 글자 수, 잠김 여부). 원본 글(머리말 포함)은 with_raw일 때만 읽는다."""
    if kind == "pdf":
        raw = pdf_read(path)["text"]
        return (raw, *clean(raw, kind), False)
    r = hwp_read(path, skip_hf=True)
    if r["locked"]:
        return "", "", {}, True
    text, stats = clean(r["text"], "hwp")
    stats["hf"] = r["hf_chars"]
    return (hwp_read(path)["text"] if with_raw else ""), text, stats, False
