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

def stage_verification():
    global N, answer, context, contexts, detail_rows, found, found_count, found_in, index, item, normalized_quote, original, question_id, quote, quotes, record, records_by_id, summary_rows, total
    N = 10
    if 'answers' not in globals() or len(answers) < N:
        raise ValueError('먼저 답변 생성 셀을 실행해 주세요.')
    records_by_id = {record['id']: record for record in original_records}
    summary_rows = []
    detail_rows = []
    for item, answer in zip(evaluation_data[:N], answers[:N]):
        question_id = item['id']
        if item['query'] != answer['query']:
            raise ValueError(f'{question_id}: 질문과 답변의 순서가 다릅니다.')
        if question_id not in records_by_id:
            raise ValueError(f'원본 평가셋에 {question_id} 문항이 없습니다.')
        original = records_by_id[question_id]
        if original['question'] != item['query']:
            raise ValueError(f'{question_id}: 원본 평가셋과 질문이 다릅니다.')
        quotes = extract_quotes(original.get('evidence_quotes', []))
        contexts = [compact(context) for context in answer['contexts']]
        found_count = 0
        for quote, normalized_quote in quotes:
            found_in = [index + 1 for index, context in enumerate(contexts) if normalized_quote in context]
            found = bool(found_in)
            found_count += int(found)
            detail_rows.append({'id': question_id, 'quote': quote, 'found': found, 'context_positions': ','.join(map(str, found_in))})
        total = len(quotes)
        summary_rows.append({'id': question_id, 'project': item['project'], 'question_type': item['question_type'], 'final_context_count': len(contexts), 'evidence_quote_count': total, 'found_quote_count': found_count, 'quote_coverage': found_count / total if total else None, 'status': '검사 불가' if total == 0 else '모두 발견' if found_count == total else '일부 미발견'})
