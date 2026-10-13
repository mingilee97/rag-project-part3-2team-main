"""공개 노트북의 verification 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def compact(text):
    return re.sub('\\s+', '', unicodedata.normalize('NFC', str(text)))

def extract_quotes(evidence_quotes):
    quotes = []
    seen = set()
    for evidence in evidence_quotes or []:
        for curved, straight in re.findall('“([^”]+)”|"([^"]+)"', str(evidence)):
            quote = curved or straight
            if '…' in quote or '...' in quote:
                continue
            normalized = compact(quote)
            if len(normalized) >= 8 and re.search('[가-힣A-Za-z]', normalized) and (normalized not in seen):
                seen.add(normalized)
                quotes.append((quote, normalized))
    return quotes
