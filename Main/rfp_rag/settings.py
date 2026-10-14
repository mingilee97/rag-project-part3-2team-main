"""configs/base.yaml 위에 실험 파일(configs/exp/<이름>.yaml)을 덮어 읽는다."""
import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def _merge(base, over):
    for k, v in over.items():
        base[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return base


def load(exp=None):
    """exp: 실험 이름(`00_baseline`) 또는 yaml 경로. 없으면 기본값만 읽는다."""
    cfg = yaml.safe_load((ROOT / "configs/base.yaml").read_text(encoding="utf-8"))
    cfg["name"] = "base"
    if exp:
        p = Path(exp)
        if not p.exists():
            p = ROOT / "configs/exp" / f"{exp}.yaml"
        cfg = _merge(cfg, yaml.safe_load(p.read_text(encoding="utf-8")) or {})
        cfg["name"] = p.stem
    data_dir = Path(os.environ.get("RFP_DATA_DIR") or cfg["data_dir"])
    cfg["data_dir"] = data_dir if data_dir.is_absolute() else ROOT / data_dir
    return cfg


if __name__ == "__main__":
    assert _merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 9}}) == {"a": {"b": 9, "c": 2}}
    print(load()["data_dir"])
