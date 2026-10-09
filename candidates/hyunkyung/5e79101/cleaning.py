"""원본cell10의순수정제함수만추출. 노트북로더·모델·출력·guard는포함하지않는다."""
import re
import unicodedata

def compact_for_preservation(text):
    """Ignore only Unicode composition and whitespace when comparing source text."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))

def clean_document_text(text):
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    kept_lines = []
    removed_lines = []
    for line in text.split("\n"):
        # 손상된 글머리기호(PUA 문자 또는 U+FFFD)가 줄 앞에 있을 때만 제거
        line = re.sub(r"^[\ue000-\uf8ff\uFFFD]+[ \t]*", "", line)
        short = line.strip()

        # 숫자만 있거나 '- 12 -' 형태인 쪽 번호 줄
        is_page_number = bool(re.fullmatch(r"(?:[-–—]\s*)?\d{1,4}(?:\s*[-–—])?", short))
        # '제목 ........ 12'와 같은 점선형 목차 항목
        is_toc_entry = bool(re.fullmatch(r".{2,200}?(?:\s*[.·…⋯]){2,}\s*\d{1,4}", short))
        is_toc_title = bool(re.fullmatch(r"목\s*차", short))
        is_empty_table_row = short.startswith("|") and all(
            not cell.strip() for cell in short.split("|")
        )
        if is_page_number or is_toc_entry or is_toc_title or is_empty_table_row:
            removed_lines.append(line)
            continue
        kept_lines.append(line)

    cleaned = "\n".join(kept_lines)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, removed_lines
