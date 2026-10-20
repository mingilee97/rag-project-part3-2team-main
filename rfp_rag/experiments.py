"""FINAL-02의 문항별 체크포인트와 RAGAS 평가 실행."""
import json
import os
import time
from pathlib import Path
from .config import RagSettings
from .data import prepare_corpus
from .metrics import build_source_text_index, score_retrieval_text

ROOT = Path(__file__).resolve().parent.parent
TRANSIENT = ("429", "ResourceExhausted", "DeadlineExceeded", "504", "503", "overloaded", "Overloaded")
METRICS = ["hit_at_5", "mrr", "llm_as_judge", "factual_correctness", "faithfulness"]

def settings_final02():
    return RagSettings()

def atomic_json(path: Path, payload) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def retry(fn, label: str, tries: int = 10, wait: int = 75):
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as exc:  # 사용량 제한만 기다렸다가 다시 시도
            if "PerDay" in str(exc):  # 하루 한도는 기다려도 안 풀리므로 바로 멈춤 (체크포인트는 남아 있음)
                raise SystemExit(f"\n[멈춤] {label}: Gemini 하루 사용량 한도에 걸렸습니다. "
                                 "다른 키로 이어서 돌리세요: python final02.py ragas --gemini-key-var GOOGLE_API_KEY_2")
            if not any(t in str(exc) for t in TRANSIENT) or attempt == tries:
                raise
            print(f"{label}: 사용량 제한. {wait}초 후 재시도 ({attempt}/{tries})", flush=True)
            time.sleep(wait)


def cmd_base(args):
    import pandas as pd
    import rfp_rag.pipeline as P
    from rfp_rag.evaluation import GeminiJudge

    prompt_path = ROOT / "prompts/final02.txt"
    P.ANSWER_RULES = prompt_path.read_text(encoding="utf-8")
    if "{context}" not in P.ANSWER_RULES or "{query}" not in P.ANSWER_RULES:
        raise ValueError("prompt_final.txt에 {context}와 {query}가 있어야 합니다.")

    settings = settings_final02()
    settings.validate()
    out = args.out_dir
    (out / "answer_checkpoints").mkdir(parents=True, exist_ok=True)
    (out / "base_checkpoints").mkdir(exist_ok=True)

    started = time.time()
    items, documents, chunks = prepare_corpus(args.data_dir, args.metadata_csv, args.benchmark, settings)
    if len(documents) != 100 or len(items) != 300:
        raise RuntimeError(f"문서/질문 수 오류: {len(documents)}개 / {len(items)}문항")
    identity = {
        "experiment": "FINAL-02", "metric_version": "chunk_body_text_v2_full_rag",
        "settings": settings.to_dict(), "chunk_header": False, "prompt": P.ANSWER_RULES,
        "question_ids": [it["id"] for it in items], "chunks": len(chunks),
    }
    id_path = out / "base_run_identity.json"
    if id_path.exists():
        if json.loads(id_path.read_text(encoding="utf-8")) != json.loads(json.dumps(identity, ensure_ascii=False)):
            raise ValueError("이 결과 폴더에는 다른 설정의 체크포인트가 있습니다. --out-dir을 바꾸세요.")
    else:
        atomic_json(id_path, identity)
    atomic_json(out / "run_config.json", settings.to_dict())

    pipeline = P.RagPipeline(chunks, settings)
    judge = GeminiJudge(settings)
    index = build_source_text_index(chunks)
    print(f"준비 완료: 문서 {len(documents)}개, 청크 {len(chunks)}개, 질문 {len(items)}개 "
          f"({time.time() - started:.0f}초)", flush=True)

    todo = items[:args.limit] if args.limit else items
    rows, answers, samples = [], [], []
    for n, item in enumerate(todo, start=1):
        done_path = out / "base_checkpoints" / f"{item['id']}.json"
        ans_path = out / "answer_checkpoints" / f"{item['id']}.json"
        if done_path.exists():
            done = json.loads(done_path.read_text(encoding="utf-8"))
        else:
            if ans_path.exists():
                record = json.loads(ans_path.read_text(encoding="utf-8"))["record"]
            else:
                record = retry(lambda: pipeline.answer(item["query"]), f"{item['id']} 답변")
                atomic_json(ans_path, {"id": item["id"], "record": record})
            answer = record["answer"].split("답변:", 1)[-1].strip()
            if not answer or not record["contexts"]:
                raise ValueError(f"답변 또는 검색 문맥이 비어 있습니다: {item['id']}")
            score, reason = retry(lambda: judge.score(item["query"], item["reference"], answer), f"{item['id']} Judge")
            ranked = [chunks[i] for i in record["ranked_chunk_ids"]]
            contexts = [chunks[i] for i in record["chunk_ids"]]
            ret = score_retrieval_text(item, ranked, contexts, index)
            row = {"id": item["id"], "document_id": item["document_id"],
                   "question_type": item.get("question_type", ""),
                   "source_length_chars": item["source_length_chars"], **ret,
                   "context_chars": sum(len(c) for c in record["contexts"]),
                   "retrieval_scope": record["retrieval_scope"],
                   "retrieval_time_ms": record["retrieval_time_ms"],
                   "llm_as_judge": score, "judge_reason": reason}
            sample = {"user_input": item["query"], "retrieved_contexts": record["contexts"],
                      "response": answer, "reference": item["reference"]}
            done = {"id": item["id"], "row": row, "answer": {"id": item["id"], **record}, "sample": sample}
            atomic_json(done_path, done)
        rows.append(done["row"])
        answers.append(done["answer"])
        samples.append(done["sample"])
        r = done["row"]
        print(f"[{n}/{len(todo)}] {item['id']}  Hit@5 {r['hit_at_5']}  Judge {r['llm_as_judge']:.2f}  "
              f"근거 {r['recall_ctx']:.2f}  ({time.time() - started:.0f}초)", flush=True)

    frame = pd.DataFrame(rows)
    if args.limit:
        print("\n[시험 실행] 300문항이 아니라 결과 파일은 만들지 않습니다.")
        print(frame[["hit_at_5", "mrr", "llm_as_judge", "recall_ctx", "context_chars"]].mean().round(4).to_string())
        return
    frame.to_csv(out / "base_scores.csv", index=False, encoding="utf-8-sig")
    with (out / "base_answers.jsonl").open("w", encoding="utf-8") as f:
        for a in answers:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    (out / "ragas_samples.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n1단계 완료:", out / "base_scores.csv")
    print(frame[["hit_at_5", "mrr", "llm_as_judge", "recall_ctx", "all_found_ctx"]].mean().round(4).to_string())


def cmd_ragas(args):
    import pandas as pd
    from langchain_core.rate_limiters import InMemoryRateLimiter
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ragas import EvaluationDataset, evaluate
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import FactualCorrectness, Faithfulness
    from ragas.run_config import RunConfig

    out = args.out_dir
    base = pd.read_csv(out / "base_scores.csv", encoding="utf-8-sig", dtype={"id": str})
    samples = json.loads((out / "ragas_samples.json").read_text(encoding="utf-8"))
    if len(base) != 300 or len(samples) != 300:
        raise ValueError("1단계 결과(base_scores.csv, ragas_samples.json)가 300문항이어야 합니다.")

    ckpt = out / "ragas_metric_checkpoints"
    ckpt.mkdir(exist_ok=True)
    api_key = os.environ.get(args.gemini_key_var, "").strip()
    if not api_key:
        raise SystemExit(f".env에 {args.gemini_key_var}가 없습니다.")
    print(f"Gemini 키: {args.gemini_key_var} 사용, 호출 간격 {args.seconds_per_call}초", flush=True)
    limiter = InMemoryRateLimiter(requests_per_second=1 / args.seconds_per_call,
                                  check_every_n_seconds=0.5, max_bucket_size=1)

    def make_llm():
        # evaluate()는 부를 때마다 새 이벤트 루프를 쓰므로, Gemini 클라이언트도 매번 새로 만들어야
        # "Event loop is closed" 오류가 나지 않음 (Colab은 루프가 하나라 이 문제가 없음)
        return LangchainLLMWrapper(
            ChatGoogleGenerativeAI(model=settings_final02().ragas_model, google_api_key=api_key,
                                   timeout=300, max_retries=2, rate_limiter=limiter),
            bypass_temperature=True, bypass_n=True)

    specs = (("factual_correctness", lambda: FactualCorrectness(mode="f1")),
             ("faithfulness", Faithfulness))

    for n, (qid, sample) in enumerate(zip(base["id"], samples), start=1):
        for name, factory in specs:
            path = ckpt / f"{qid}_{name}.json"
            if path.exists():
                continue

            def run_one():
                result = evaluate(dataset=EvaluationDataset.from_list([sample]), metrics=[factory()],
                                  llm=make_llm(), run_config=RunConfig(max_workers=1, max_retries=10, timeout=300),
                                  raise_exceptions=True, show_progress=False)
                row = result.to_pandas().iloc[0]
                col = next((c for c in row.index if c.startswith(name)), None)
                if col is None:
                    raise RuntimeError(f"RAGAS 결과 열이 없습니다: {name}, {list(row.index)}")
                return float(row[col])

            score = retry(run_one, f"{qid} {name}")
            if not 0 <= score <= 1:
                raise ValueError(f"RAGAS 점수 오류: {qid} {name}={score}")
            atomic_json(path, {"id": qid, "metric": name, "score": score})
            print(f"[{n}/300] {qid} {name} {score:.2f}", flush=True)

    rows = []
    for qid in base["id"]:
        rows.append({"id": qid, **{name: json.loads((ckpt / f"{qid}_{name}.json").read_text())["score"]
                                   for name, _ in specs}})
    ragas = pd.DataFrame(rows)
    ragas.to_csv(out / "ragas_results.csv", index=False, encoding="utf-8-sig")
    base.merge(ragas, on="id", how="inner", validate="one_to_one").to_csv(
        out / "all_scores.csv", index=False, encoding="utf-8-sig")
    print("2단계 완료:", out / "all_scores.csv")
    cmd_summary(args)


def cmd_summary(args):
    import pandas as pd
    out = args.out_dir
    path = out / "all_scores.csv"
    if not path.exists():
        path = out / "base_scores.csv"
        print("[알림] RAGAS가 아직 없어 1단계 결과만 표시합니다.")
    s = pd.read_csv(path, encoding="utf-8-sig")
    cols = [c for c in METRICS + ["recall_ctx", "all_found_ctx", "context_chars"] if c in s]
    summary = s[cols].agg(["count", "mean", "min", "max"]).T.round(4)
    summary["missing"] = len(s) - summary["count"]
    print(f"\n== FINAL-02 ({len(s)}문항) ==")
    print(summary.to_string())
    if "question_type" in s:
        print("\n[질문 유형별 평균]")
        print(s.groupby("question_type")[cols].mean().round(4).to_string())
    summary.to_csv(out / "five_metric_summary.csv", encoding="utf-8-sig")
