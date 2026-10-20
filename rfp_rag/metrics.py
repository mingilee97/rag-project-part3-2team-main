"""원문 근거의 첫 검색 순위와 최종 문맥의 근거 포함을 따로 계산한다."""
import re
import unicodedata
from collections import defaultdict
from .data import normalize_filename

def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())


def build_source_text_index(chunks):
    index = defaultdict(list)
    for chunk in chunks:
        index[normalize_filename(chunk.metadata["파일명"])].append(norm(chunk.page_content))
    return index


def score_retrieval_text(item, ranked_chunks, contexts, source_text_index):
    quotes = [norm(q) for q in item["evidence_quotes"]]
    if not quotes:
        raise ValueError(f"근거 문장이 없는 문항: {item['id']}")
    source = normalize_filename(item["source_filename"])
    original = source_text_index.get(source, [])
    if not original:
        raise ValueError(f"정답 문서의 청크가 없습니다: {item['id']}")
    aligned = [any(q in t for t in original) for q in quotes]
    ranked = [(normalize_filename(c.metadata["파일명"]), norm(c.page_content)) for c in ranked_chunks]
    ctx = [norm(c.page_content) for c in contexts]
    first = next((r for r, (src, t) in enumerate(ranked, start=1)
                  if src == source and any(q in t for q in quotes)), None)
    hit5 = float(first is not None and first <= 5)
    mrr = 1.0 / first if first else 0.0
    if not all(aligned):  # 근거가 청크와 연결되지 않은 문항은 순위 점수에서 제외 (노트북과 같음)
        hit5 = mrr = None
    top5 = [t for _, t in ranked[:5]]
    in_top5 = [any(q in t for t in top5) for q in quotes]
    in_ctx = [any(q in t for t in ctx) for q in quotes]
    return {
        "hit_at_5": hit5, "mrr": mrr, "first_correct_rank": first,
        "recall_top5": sum(in_top5) / len(quotes), "recall_ctx": sum(in_ctx) / len(quotes),
        "all_found_ctx": int(all(in_ctx)), "evidence_aligned": all(aligned),
        "evidence_quote_count": len(quotes), "evidence_quote_aligned_count": sum(aligned),
    }
