"""김현경 제출본의 사업명 식별 동작을 보존하는 비교용 모듈.

노트북 셀, 모델 생성, 파일 로드와 인증 코드는 실행하지 않는다.
카탈로그와 별칭은 호출마다 분리해 대화 사이에 상태가 섞이지 않게 한다.
"""
import unicodedata
from types import FunctionType

def normalize_project_text(value):
    return ''.join((char for char in unicodedata.normalize('NFKC', str(value)).casefold() if char.isalnum()))

def choose_project(matches, query):
    matches = sorted(set(matches))
    if len(matches) == 1:
        return matches[0]
    normalized_query = normalize_project_text(query)
    agency_matches = [key for key in matches if key[0] and normalize_project_text(key[0]) in normalized_query]
    if len(agency_matches) == 1:
        return agency_matches[0]
    labels = ', '.join((f'[{agency}] "{title}"' for agency, title in matches))
    raise ValueError(f'사업을 하나로 특정할 수 없습니다: {labels}')

def identify_project(query):
    normalized_query = normalize_project_text(query)
    if not normalized_query:
        raise ValueError('질문이 비어 있습니다.')
    direct_matches = [key for key in project_catalog if normalize_project_text(key[1]) in normalized_query]
    if direct_matches:
        specific_matches = [key for key in direct_matches if not any((normalize_project_text(key[1]) != normalize_project_text(other[1]) and normalize_project_text(key[1]) in normalize_project_text(other[1]) for other in direct_matches))]
        return choose_project(specific_matches, query)
    alias_matches = [(alias, target) for alias, target in PROJECT_ALIASES.items() if normalize_project_text(alias) in normalized_query]
    if alias_matches:
        longest = max((len(normalize_project_text(alias)) for alias, _ in alias_matches))
        targets = [target for alias, target in alias_matches if len(normalize_project_text(alias)) == longest]
        unknown = [target for target in targets if target not in project_chunks_by_key]
        if unknown:
            raise ValueError(f'PROJECT_ALIASES의 사업이 문서 목록에 없습니다: {unknown}')
        return choose_project(targets, query)
    raise ValueError('질문에서 사업명을 찾지 못했습니다. 정식 사업명을 질문에 적거나 PROJECT_ALIASES에 줄임말을 등록해 주세요.')

def resolve_project(question, info, aliases=None):
    """메인 문서 정보를 원본 함수 계약에 맞추고 문서 번호를 돌려준다."""
    catalog = {}
    for doc_id, row in info.items():
        agency, title = row.get("agency"), row.get("title")
        if not isinstance(agency, str) or not isinstance(title, str) or not normalize_project_text(title):
            raise ValueError("사업 카탈로그에 유효한 기관명·사업명이 없습니다.")
        catalog.setdefault((agency, title), []).append(doc_id)
    alias_map = {}
    for alias, target in (aliases or {}).items():
        if not isinstance(alias, str) or not normalize_project_text(alias) or not isinstance(target, (tuple, list)) or len(target) != 2:
            raise ValueError("사업 별칭은 비어 있지 않은 이름과 [기관명, 사업명]으로 지정해야 합니다.")
        alias_map[alias] = tuple(target)
    namespace = {
        "normalize_project_text": normalize_project_text,
        "project_catalog": tuple(catalog),
        "project_chunks_by_key": catalog,
        "PROJECT_ALIASES": alias_map,
    }
    namespace["choose_project"] = FunctionType(choose_project.__code__, namespace)
    identify = FunctionType(identify_project.__code__, namespace)
    try:
        key = identify(question)
    except ValueError as exc:
        return {"status": "rejected", "doc_ids": [], "reason": str(exc)}
    return {"status": "matched", "doc_ids": sorted(catalog[key]), "reason": "정식 사업명 또는 등록 별칭으로 식별했습니다."}


def select_for_pipeline(question, state, info, aliases=None):
    """단일 사업 질문에 적용한다. 비교·목록·전체 순위·대화 후속 질문은 메인 동작을 유지한다."""
    from rfp_rag import memory, route
    from rfp_rag.pipeline import SUPERLATIVE
    if (route.COMPARE_WORDS.search(question) or route.LIST_WORDS.search(question)
            or (SUPERLATIVE.search(question) and route.META_WORDS.search(question))
            or (state.get("history") and memory.FOLLOWUP.search(question))):
        return {"status": "bypassed", "doc_ids": [], "reason": "이번 비교 범위 밖의 질문은 메인 경로로 처리합니다."}
    return resolve_project(question, info, aliases)
