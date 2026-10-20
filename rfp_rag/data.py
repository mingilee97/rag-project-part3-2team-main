"""평가 문항과 문서 메타데이터를 검증하고 같은 자료로 말뭉치를 만든다."""
from __future__ import annotations
import re
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from .config import DEFAULT_DOCUMENT_NUMBERS, RagSettings

SUPPORTED_SUFFIXES = {".pdf", ".hwp", ".hwpx"}
METADATA_COLUMNS = ("공고 번호", "공고 차수", "사업명", "사업 금액", "발주 기관", "공개 일자", "입찰 참여 시작일", "입찰 참여 마감일", "파일명")
EVALUATION_DOCUMENT_NUMBERS = DEFAULT_DOCUMENT_NUMBERS


def evaluation_question_ids(document_numbers) -> tuple[str, ...]:
    return tuple(
        f"DOC{document_number:03d}-Q{question_number:02d}"
        for document_number in document_numbers
        for question_number in range(1, 4)
    )


def normalize_filename(value: str) -> str:
    """Match file, CSV, and benchmark names despite Hangul normalization/spacing."""
    name = str(value)
    if Path(name).suffix.lower() in SUPPORTED_SUFFIXES:
        name = name.rsplit(".", 1)[0]
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", name)).strip()


def clean_text(value: str) -> str:
    text = value.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def load_benchmark(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("DEV 벤치마크는 metadata와 items가 있는 JSON 객체여야 합니다.")
    if payload.get("metadata", {}).get("version") != "1.1":
        raise ValueError("DEV 벤치마크 버전이 1.1인지 확인하세요.")
    records = payload["items"]
    if len(records) != 300:
        raise ValueError(f"평가 문항 수: {len(records)}/300")

    required = ("id", "document_id", "source_filename", "project_name", "question", "reference_answer")
    result = []
    for record in records:
        if not isinstance(record, dict) or not all(
            isinstance(record.get(field), str) and record[field].strip() for field in required
        ):
            raise ValueError(f"필수 평가 필드가 없거나 비어 있습니다: {record!r}")
        evidence = record.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, dict) for item in evidence):
            raise ValueError(f"evidence 형식 오류: {record['id']}")
        quotes = [item["text"].strip() for item in evidence
                  if isinstance(item.get("text"), str) and item["text"].strip()]
        result.append({
            "id": record["id"], "document_id": record["document_id"],
            "source_filename": record["source_filename"],
            "project": record["project_name"], "query": record["question"],
            "reference": record["reference_answer"],
            "question_type": record.get("question_type", ""),
            "answerable": record.get("answerable"),
            "evidence_quotes": quotes,
            "atomic_facts": record.get("atomic_facts", []),
        })
    counts = Counter(item["document_id"] for item in result)
    if len(counts) != 100 or set(counts.values()) != {3}:
        raise ValueError("100개 문서에 각 3문항이 있는지 확인하세요.")
    if len({item["id"] for item in result}) != 300:
        raise ValueError("평가 문항 ID가 중복됩니다.")
    return result


def select_evaluation_questions(
    items: list[dict[str, Any]], document_numbers=EVALUATION_DOCUMENT_NUMBERS,
) -> list[dict[str, Any]]:
    """Use all three questions from each selected document, in number order."""
    by_id = {item["id"]: item for item in items}
    selected = []
    for question_id in evaluation_question_ids(document_numbers):
        document_id = question_id.split("-", 1)[0]
        item = by_id.get(question_id)
        if item is None or item["document_id"] != document_id:
            raise ValueError(f"선택한 평가 문항이 없거나 문서 ID가 다릅니다: {question_id}")
        selected.append(item)
    return selected


def load_documents(parsed: dict[str, str], metadata_csv: Path):
    import pandas as pd
    from langchain_core.documents import Document

    frame = pd.read_csv(metadata_csv, encoding="utf-8-sig")
    missing_columns = set(METADATA_COLUMNS) - set(frame.columns)
    if missing_columns:
        raise ValueError(f"data_list.csv에 없는 열: {sorted(missing_columns)}")
    by_name: dict[str, list] = {}
    for _, row in frame.iterrows():
        by_name.setdefault(normalize_filename(row["파일명"]), []).append(row)

    documents = []
    unmatched = []
    for name, text in parsed.items():
        rows = by_name.get(normalize_filename(name), [])
        if not rows:
            unmatched.append(name)
            continue
        identities = {
            (str(row["발주 기관"]), str(row["사업명"])) for row in rows
        }
        if len(identities) != 1:
            raise ValueError(f"파일의 사업 메타데이터가 여러 개입니다: {name}")
        row = rows[0]
        metadata = {column: "" if pd.isna(row[column]) else str(row[column])
                    for column in METADATA_COLUMNS}
        documents.append(Document(page_content=clean_text(text), metadata=metadata))
    if unmatched:
        raise ValueError(f"data_list.csv와 연결되지 않은 문서: {unmatched[:10]}")
    if not documents:
        raise ValueError("파싱·메타데이터 연결에 성공한 문서가 없습니다.")
    return documents


def prepare_corpus(data_dir: Path, metadata_csv: Path, benchmark_path: Path,
                   settings: RagSettings, refresh_cache: bool = False):
    from .parsing import parse_files
    from .chunking import split_documents

    settings.validate()
    items = select_evaluation_questions(load_benchmark(benchmark_path), settings.document_numbers)
    required = {normalize_filename(item["source_filename"]) for item in items}
    expected_count = len(settings.document_numbers)
    if len(required) != expected_count:
        raise ValueError(f"선택한 문서와 정답 문서 수가 다릅니다: {len(required)}/{expected_count}")
    parsed = parse_files(data_dir, required, refresh_cache=refresh_cache)
    documents = load_documents(parsed, metadata_csv)
    sources = {normalize_filename(doc.metadata["파일명"]) for doc in documents}
    if sources != required or len(documents) != expected_count:
        raise ValueError(f"선택한 문서 {expected_count}개 중 {len(documents)}개를 로드했습니다.")
    lengths = {normalize_filename(doc.metadata["파일명"]): len(doc.page_content)
               for doc in documents}
    for item in items:
        item["source_length_chars"] = lengths[normalize_filename(item["source_filename"])]
        if item["source_length_chars"] <= 0:
            raise ValueError(f"문서 길이가 0입니다: {item['source_filename']}")
    chunks = split_documents(documents, settings)
    return items, documents, chunks
