"""전처리가 사용하는 쪽 번호와 목차 판별 함수."""
import re
from rfp_rag.ingest.chunk import HEADINGS

T = {"toc_block_min": 4}

TOC_DOT = re.compile(r"[·.…ㆍ]{3,}\s*\d*\s*$")

PAGE_TAIL = re.compile(r"\s\d{1,4}$")

_P = r"\d{1,4}"

PAGE_RE = re.compile(
    rf"^\s*(?:[-–—]\s*{_P}\s*[-–—]|{_P}|{_P}\s*/\s*{_P}|(?:page|p\.?)\s*{_P}(?:\s*/\s*{_P})?|\[\s*{_P}\s*\]|\(\s*{_P}\s*\))\s*$",
    re.I)

def _level(s):
    return next((lv for lv, rx in HEADINGS if rx.match(s)), 0) if s else 0

def _is_toc(s, lv):
    return bool(s) and (bool(TOC_DOT.search(s)) or (0 < lv < 5 and bool(PAGE_TAIL.search(s))))

def toc_blocks(lines):
    """목차 덩어리 [(시작 줄, 끝 줄, 시작 글자 위치)]. 목차 줄이 toc_block_min줄 넘게 이어진 곳이다.
    빈 줄은 이어짐을 끊지 않는다. 끝 줄까지 안에는 목차 줄과 빈 줄만 있다."""
    blocks, run, pos = [], [], 0  # run: [(줄 번호, 시작 위치)]

    def flush():
        if len(run) >= T["toc_block_min"]:
            blocks.append((run[0][0], run[-1][0], run[0][1]))
        run.clear()

    for i, line in enumerate(lines):
        s = line.strip()
        if _is_toc(s, _level(s)):
            run.append((i, pos))
        elif s:
            flush()
        pos += len(line) + 1
    flush()
    return blocks
