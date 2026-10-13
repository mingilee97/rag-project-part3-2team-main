"""기존 통제 비교 후보를 재사용합니다. 채택하지 않은 경계 변경입니다."""
from rfp_rag.ingest.chunk import _splitter, _meta

def chunk_teammate(doc, size=1000, overlap=200):
    """원본 parent/child 경계로 나누되 공통 크기 상한과 메인 메타데이터를 유지한다."""
    from langchain_core.documents import Document
    from .rag_chunking import build_parent_children
    if not isinstance(size, int) or isinstance(size, bool) or (not isinstance(overlap, int)) or isinstance(overlap, bool):
        raise ValueError('청크 크기와 overlap은 정수여야 합니다.')
    if not 0 <= overlap < size:
        raise ValueError('Require 0 <= overlap < size')
    pages = [Document(page_content=doc['text'], metadata={'source': doc['source_file']})]
    parents, children = build_parent_children(pages, child_size=size, child_overlap=overlap, parent_size=max(8000, size))
    splitter, rows = (_splitter(size, overlap), [])
    for child in children:
        parent = parents[child.metadata['parent_id']]
        start, end = (child.metadata['start_index'], child.metadata['end_index'])
        if parent.page_content[start:end] != child.page_content:
            raise ValueError('원본 child와 parent 좌표가 일치하지 않습니다.')
        bodies = splitter.split_text(child.page_content) if len(child.page_content) > size else [child.page_content]
        for body in bodies:
            path = ' > '.join(child.metadata.get('section_path', []))
            row = _meta(doc, 'teammate_boundary', len(rows), path, body)
            rows.append(row)
    return rows
