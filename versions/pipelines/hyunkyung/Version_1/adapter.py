"""메인 문서 dict 계약을 보존하는 별도 정제 어댑터. 운영 ingestion에는 연결하지 않는다."""
from functools import lru_cache
import importlib.util
from pathlib import Path


@lru_cache(maxsize=1)
def implementation():
    source = Path(__file__).with_name('cleaning.py')
    spec = importlib.util.spec_from_file_location('review_hyunkyung_cleaning', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def adapt_document(document, protected_spans=()):
    """(같은 키의 새 문서, 별도 진단)을 반환한다. 보호 구간이 사라지면 원문으로 되돌린다.

    protected_spans는 승인된 evaluator의 인용 구간·수치·날짜 등을 명시적으로 전달한다.
    지정하지 않은 의미·표 구조·전체 사실의 보존까지 확인했다고 해석하지 않는다.
    """
    if not isinstance(document.get('text'), str):
        raise TypeError('메인 문서의 text 필드가 문자열이어야 합니다')
    native = implementation()
    raw = document['text']
    candidate, removed_lines = native.clean_document_text(raw)
    normalize = native.compact_for_preservation
    original = normalize(raw)
    cleaned = normalize(candidate)
    eligible = [span for span in protected_spans if span and normalize(span) in original]
    lost = sum(normalize(span) not in cleaned for span in eligible)
    output = dict(document)
    output['text'] = raw if lost else candidate
    diagnostic = {'candidate': 'hyunkyung-5e79101-cleaning', 'checked_protected_spans': len(eligible),
        'lost_protected_spans_before_fallback': lost, 'fallback_to_original': bool(lost),
        'original_characters': len(raw), 'candidate_characters': len(candidate),
        'native_removed_line_count': len(removed_lines),
        'metadata_and_main_document_keys_preserved': True, 'semantic_fidelity_evaluated': False}
    assert output.keys() == document.keys() and all(output[k] == document[k] for k in document if k != 'text')
    return output, diagnostic
