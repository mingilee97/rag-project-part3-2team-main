"""공개 노트북의 parser_fix 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def _extract_hyperlink_texts_from_para(self, para_data: bytes) -> List[str]:
    hyperlink_texts = []
    i = 0
    while i < len(para_data) - 1:
        code = struct.unpack_from('<H', para_data, i)[0]
        if code == 3:
            if i + 6 > len(para_data):
                i += 2
                continue
            if i + 6 <= len(para_data):
                ctrl_id = struct.unpack_from('<I', para_data, i + 2)[0]
                if ctrl_id == CTRL_ID_HYPERLINK:
                    text_start = i + 14
                    text_chars = []
                    j = text_start
                    while j < len(para_data) - 1:
                        c = struct.unpack_from('<H', para_data, j)[0]
                        if c == 4:
                            break
                        elif c == 3:
                            j += 2
                        elif 32 <= c < 65536:
                            text_chars.append(chr(c))
                            j += 2
                        else:
                            j += 2
                    if text_chars:
                        hyperlink_texts.append(''.join(text_chars))
                    i = j
                    continue
                else:
                    i += 14
                    continue
        elif code == 4:
            i += 10
        elif code < 32:
            if code in (11, 12):
                i += 10
            elif 15 <= code <= 23:
                i += 14
            else:
                i += 2
        else:
            i += 2
    return hyperlink_texts

def apply_hwp_parser_fix():
    HWP5Reader._extract_hyperlink_texts_from_para = _extract_hyperlink_texts_from_para

def stage_parser_fix():
    """hwp-hwpx-parser 1.0.0의 잘린 필드 제어문자 무한 루프 수정.
본문/표/각주 추출 로직은 유지합니다. 원본 문서를 변경하지 않습니다.
"""
    apply_hwp_parser_fix()
