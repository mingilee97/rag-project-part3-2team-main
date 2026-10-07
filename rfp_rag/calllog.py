"""모델 호출 한 번당 한 줄을 <data_dir>/logs/calls.jsonl 에 남긴다. 프롬프트·답·키는 기록하지 않는다."""
import json
from datetime import datetime

from rfp_rag import settings


def log_call(provider, model, purpose, input_tokens, output_tokens, seconds):
    path = settings.load()["data_dir"] / "logs" / "calls.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"time": datetime.now().isoformat(timespec="seconds"), "provider": provider, "model": model,
           "purpose": purpose, "input_tokens": input_tokens, "output_tokens": output_tokens,
           "seconds": round(seconds, 3)}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
