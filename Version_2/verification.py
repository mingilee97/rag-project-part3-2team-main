"""공개 노트북의 verification 단계. 공급자는 호출자가 명시적으로 연결합니다."""
def compact(text):
    return re.sub('\\s+', '', unicodedata.normalize('NFC', str(text)))

def extract_quotes(evidence_quotes):
    quotes = []
    seen = set()
    for evidence in evidence_quotes or []:
        for curved, straight in re.findall('[“]([^”]+)[”]|"([^"]+)"', str(evidence)):
            quote = curved or straight
            if '…' in quote or '...' in quote:
                continue
            normalized = compact(quote)
            if len(normalized) >= 8 and re.search('[가-힣A-Za-z]', normalized) and (normalized not in seen):
                seen.add(normalized)
                quotes.append(normalized)
    return quotes

def stage_verification():
    global answer_record, bm25_mode, context, contexts, coverage_rows, found, item, original, quote, quotes, record, records_by_id
    records_by_id = {record['id']: record for record in original_records}
    coverage_rows = []
    for bm25_mode in BM25_MODES:
        for item, answer_record in zip(evaluation_data, answers_by_mode[bm25_mode]):
            original = records_by_id[item['id']]
            quotes = extract_quotes(original.get('evidence_quotes', []))
            contexts = [compact(context) for context in answer_record['contexts']]
            found = sum((any((quote in context for context in contexts)) for quote in quotes))
            coverage_rows.append({'id': item['id'], 'project': item['project'], 'bm25_mode': bm25_mode, 'evidence_quote_count': len(quotes), 'found_quote_count': found, 'quote_coverage': found / len(quotes) if quotes else None})
