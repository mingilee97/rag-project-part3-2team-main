"""HWP와 PDF를 읽고 제공된 파싱 캐시를 보존한다."""
from __future__ import annotations
import json
import os
import unicodedata
from collections import Counter
from pathlib import Path
from .data import SUPPORTED_SUFFIXES, normalize_filename

def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"파싱 캐시는 JSON 객체여야 합니다: {path}")
    return value


def _extract_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        import pymupdf4llm

        return pymupdf4llm.to_markdown(str(path))
    from .hwp_parser_fix import apply_hwp_parser_fix

    apply_hwp_parser_fix()
    from hwp_hwpx_parser import ExtractOptions, TableStyle
    from langchain_hwp_hwpx import HwpHwpxLoader

    loader = HwpHwpxLoader(
        str(path), mode="single",
        extract_options=ExtractOptions(table_style=TableStyle.MARKDOWN),
    )
    return "\n\n".join(document.page_content for document in loader.load())


def parse_files(data_dir: Path, required_names: set[str], refresh_cache: bool = False) -> dict[str, str]:
    """Parse each required supported file once; no filename-specific skips/patches."""
    if not data_dir.is_dir():
        raise FileNotFoundError(f"문서 폴더가 없습니다: {data_dir}")
    files = sorted(
        (path for path in data_dir.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES),
        key=lambda path: (unicodedata.normalize("NFKC", path.name).casefold(), path.name),
    )
    selected = [path for path in files if normalize_filename(path.name) in required_names]
    found = Counter(normalize_filename(path.name) for path in selected)
    duplicate = [name for name, count in found.items() if count > 1]
    if duplicate:
        raise ValueError(f"정규화 후 같은 이름의 문서가 중복됩니다: {duplicate[:10]}")
    missing = required_names - set(found)
    if missing:
        raise FileNotFoundError(f"벤치마크 문서가 data 폴더에 없습니다: {sorted(missing)[:10]}")

    cache_dir = data_dir / "parsed_results"
    success_path = cache_dir / "success_files.json"
    failed_path = cache_dir / "failed_files.json"
    success = _read_json(success_path)
    failed = _read_json(failed_path)
    parsed = {}
    for index, path in enumerate(selected, 1):
        cached = success.get(path.name)
        if not refresh_cache and isinstance(cached, str) and cached.strip():
            parsed[path.name] = cached
            if path.name in failed:
                failed.pop(path.name)
                _write_json(failed_path, failed)
            continue
        try:
            text = _extract_file(path)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("본문이 비어 있습니다.")
        except Exception as exc:
            failed[path.name] = {"error": str(exc)}
            _write_json(failed_path, failed)
            raise RuntimeError(f"문서 파싱 실패 ({index}/{len(selected)}): {path.name}") from exc
        success[path.name] = text
        parsed[path.name] = text
        failed.pop(path.name, None)
        _write_json(success_path, success)
        _write_json(failed_path, failed)
    return parsed
