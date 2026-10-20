"""사업명을 식별한다. 모호하거나 찾지 못하면 호출자가 전체 검색으로 돌아간다."""
import unicodedata
def normalize_project_text(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", str(value)).casefold()
        if char.isalnum()
    )


def project_title_matches_query(project_key: tuple[str, str], normalized_query: str) -> bool:
    agency, title = project_key
    normalized_title = normalize_project_text(title)
    if normalized_title in normalized_query:
        return True
    normalized_agency = normalize_project_text(agency)
    if normalized_agency and normalized_title.startswith(normalized_agency):
        short_title = normalized_title[len(normalized_agency):]
        if len(short_title) >= 8 and normalized_agency in normalized_query:
            return short_title in normalized_query
    return False


class ProjectRouter:
    def _choose_project(self, matches, query):
        matches = sorted(set(matches))
        if len(matches) == 1:
            return matches[0]
        normalized_query = normalize_project_text(query)
        agency_matches = [
            key for key in matches
            if key[0] and normalize_project_text(key[0]) in normalized_query
        ]
        if len(agency_matches) == 1:
            return agency_matches[0]
        labels = ", ".join(f'[{agency}] "{title}"' for agency, title in matches)
        raise ValueError(f"사업을 하나로 특정할 수 없습니다: {labels}")

    def identify_project(self, query):
        normalized_query = normalize_project_text(query)
        if not normalized_query:
            raise ValueError("질문이 비어 있습니다.")
        direct_matches = [
            key for key in self.project_catalog
            if project_title_matches_query(key, normalized_query)
        ]
        if direct_matches:
            specific = [
                key for key in direct_matches
                if not any(
                    normalize_project_text(key[1]) != normalize_project_text(other[1])
                    and normalize_project_text(key[1]) in normalize_project_text(other[1])
                    for other in direct_matches
                )
            ]
            return self._choose_project(specific, query)

        alias_matches = [
            (alias, target) for alias, target in self.aliases.items()
            if normalize_project_text(alias) in normalized_query
        ]
        if alias_matches:
            longest = max(len(normalize_project_text(alias)) for alias, _ in alias_matches)
            targets = [target for alias, target in alias_matches
                       if len(normalize_project_text(alias)) == longest]
            unknown = [target for target in targets if target not in self.project_chunks_by_key]
            if unknown:
                raise ValueError(f"PROJECT_ALIASES의 사업이 문서 목록에 없습니다: {unknown}")
            return self._choose_project(targets, query)
        raise ValueError("질문에서 사업명을 찾지 못했습니다.")
