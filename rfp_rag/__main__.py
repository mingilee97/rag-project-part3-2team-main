"""실행 명령을 지정하기 전에는 외부 모델이나 키를 읽지 않는다."""
import argparse
import os
from pathlib import Path

def main():
    ap = argparse.ArgumentParser(description="FINAL-02 검색과 답변 및 평가")
    ap.add_argument("command", choices=["ask", "base", "ragas", "summary", "check"])
    ap.add_argument("--out-dir", type=Path, default=Path("results/FINAL-02"))
    ap.add_argument("--data-dir", type=Path, default=Path("data/raw/files"))
    ap.add_argument("--metadata-csv", type=Path, default=Path("data/data_list.csv"))
    ap.add_argument("--benchmark", type=Path, default=Path("data/dev_benchmark_v1.1.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seconds-per-call", type=float, default=5)
    ap.add_argument("--gemini-key-var", default="GOOGLE_API_KEY")
    ap.add_argument("--query", help="ask 명령의 질문")
    args = ap.parse_args()
    if args.limit < 0 or args.seconds_per_call <= 0:
        ap.error("limit은 0 이상, seconds-per-call은 양수여야 합니다.")
    if args.command == "check":
        import unittest
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent.parent / "tests"))
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    if args.command in {"ask", "base", "ragas"}:
        for name in ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGCHAIN_TRACING"):
            os.environ[name] = "false"
        os.environ.pop("CHUNK_HEADER", None)
        os.environ.pop("ANSWER_RULES_FILE", None)
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    from . import experiments
    if args.command == "ask":
        if not args.query or not args.query.strip():
            ap.error("ask에는 --query가 필요합니다.")
        from .data import prepare_corpus
        from .pipeline import RagPipeline
        settings = experiments.settings_final02()
        _, _, chunks = prepare_corpus(args.data_dir, args.metadata_csv, args.benchmark, settings)
        print(RagPipeline(chunks, settings).answer(args.query)["answer"])
    else:
        {"base": experiments.cmd_base, "ragas": experiments.cmd_ragas, "summary": experiments.cmd_summary}[args.command](args)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
