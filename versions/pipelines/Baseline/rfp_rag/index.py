"""색인을 만든다. `python -m rfp_rag.index [--embedder 모델 ...] [--method fixed section]`.

<data_dir>/index/<임베딩 모델 이름>/ 아래에 청크 방식마다 하나씩 둔다. 다른 임베딩이나 청크 방식의
색인은 절대 지우지 않는다.
  chroma/          Chroma 저장소. 컬렉션 이름은 chunks_<방식>
  bm25_<방식>.pkl  kiwipiepy로 나눈 낱말과 문서 목록(BM25용)
  meta_<방식>.json 청크 수, 만드는 데 걸린 초, 만든 시각
"""
import argparse
import copy
import json
import pickle
import re
import shutil
import time
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document

from rfp_rag.ingest.chunk import load_chunks

METHODS = ("fixed", "section")
EMBEDDERS = ("nlpai-lab/KURE-v1", "BAAI/bge-m3")
BATCH = 64


def embedder_name(cfg):
    e = cfg["embeddings"]
    return e["model"].split("/")[-1] if e["provider"] == "local" else f"openai-{cfg['openai']['embedding_model']}"


def index_dir(cfg):
    return Path(cfg["data_dir"]) / "index" / embedder_name(cfg)


def collection_name(cfg):
    return f"chunks_{cfg['chunk']['method']}"


def to_doc(c):
    """청크 한 줄 -> Document. Chroma 메타데이터에는 None을 넣을 수 없어 빈 값으로 채운다."""
    meta = {k: c[k] for k in ("doc_id", "chunk_id", "agency", "title", "section_path")}
    meta["amount"] = c["amount"] or 0
    meta["deadline"] = c["deadline"] or ""
    return Document(page_content=c["text"], metadata=meta)


# ---------- 임베딩 ----------
@lru_cache(maxsize=1)
def _embeddings(provider, model, device, openai_model):
    cfg = {"embeddings": {"provider": provider, "model": model, "device": device},
           "openai": {"embedding_model": openai_model}}
    from rfp_rag import providers
    emb = providers.get_embeddings(cfg)
    if provider == "local" and device == "cuda":
        emb._client.half()  # VRAM을 절반으로. Ollama와 같이 쓰는 GPU라 아껴 쓴다
    elif provider == "local":
        import torch
        emb._client.to(torch.bfloat16)  # CPU에서도 반 크기로(약 3GB → 1.5GB). 이 CPU는 bf16 연산을 지원해 느려지지 않는다
    return emb


_last = [None]


def free_if_changed(cfg):
    """임베딩 모델이 바뀌면 앞 모델과 Chroma 연결을 놓아 준다. 모델 둘을 한꺼번에 들고 있으면 메모리 상한에 걸린다."""
    if _last[0] not in (None, cfg["embeddings"]["model"]):
        import gc
        _embeddings.cache_clear()
        _chroma.cache_clear()
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except ImportError:
            pass
    _last[0] = cfg["embeddings"]["model"]


def get_embeddings(cfg):
    e = cfg["embeddings"]
    return _embeddings(e["provider"], e["model"], e.get("device", "cuda"), cfg.get("openai", {}).get("embedding_model", ""))


# ---------- Chroma ----------
@lru_cache(maxsize=2)
def _chroma(path, collection, emb_key):
    from langchain_chroma import Chroma
    return Chroma(collection_name=collection, embedding_function=_embeddings(*emb_key),
                  persist_directory=path, collection_metadata={"hnsw:space": "cosine"})


def open_chroma(cfg):
    d = index_dir(cfg) / "chroma"
    d.mkdir(parents=True, exist_ok=True)
    e = cfg["embeddings"]
    return _chroma(str(d), collection_name(cfg),
                   (e["provider"], e["model"], e.get("device", "cuda"), cfg.get("openai", {}).get("embedding_model", "")))


def build_chroma(cfg, chunks, log=print):
    vs = open_chroma(cfg)
    have = set(vs.get(include=[])["ids"])  # 중간에 끊겼으면 있는 것은 건너뛰고 이어서 만든다
    todo = [c for c in chunks if c["chunk_id"] not in have]
    for i in range(0, len(todo), BATCH):
        b = todo[i:i + BATCH]
        vs.add_documents([to_doc(c) for c in b], ids=[c["chunk_id"] for c in b])
        if (i // BATCH) % 20 == 0:
            log(f"  chroma {len(have) + i + len(b)}/{len(chunks)}")
    return vs


# ---------- BM25 ----------
@lru_cache(maxsize=1)
def _kiwi():
    from kiwipiepy import Kiwi
    return Kiwi()


KEEP = re.compile(r"^(NN|NR|NP|VV|VA|XR|SL|SN|SH)")  # 명사, 동사, 형용사, 어근, 외국어, 숫자, 한자


def tokenize(text):
    """검색어로 쓸 형태소(내용어)만 남긴다. 영문은 소문자로 맞춘다."""
    return [t.form.lower() for t in _kiwi().tokenize(text) if KEEP.match(t.tag)]


def build_bm25(cfg, chunks):
    kiwi = _kiwi()
    toks = [[t.form.lower() for t in ts if KEEP.match(t.tag)] for ts in kiwi.tokenize([c["text"] for c in chunks])]
    path = index_dir(cfg) / f"bm25_{cfg['chunk']['method']}.pkl"
    path.write_bytes(pickle.dumps({"docs": [to_doc(c) for c in chunks], "tokens": toks}))
    return path


def ensure_bm25(cfg, chunks):
    """BM25는 임베딩과 상관없어서, 다른 임베딩 폴더에 이미 있으면 복사한다(메모리와 시간을 아낀다)."""
    name = f"bm25_{cfg['chunk']['method']}.pkl"
    path = index_dir(cfg) / name
    if path.exists():
        return path
    for other in index_dir(cfg).parent.glob(f"*/{name}"):
        shutil.copyfile(other, path)
        return path
    return build_bm25(cfg, chunks)


@lru_cache(maxsize=4)
def _bm25_data(path):
    return pickle.loads(Path(path).read_bytes())


def load_bm25(cfg):
    """(docs, 낱말 목록) — 청크와 같은 순서."""
    d = _bm25_data(str(index_dir(cfg) / f"bm25_{cfg['chunk']['method']}.pkl"))
    return d["docs"], d["tokens"]


# ---------- 전체 ----------
def build(cfg, log=print):
    cfg = copy.deepcopy(cfg)
    chunks = load_chunks(cfg)
    d = index_dir(cfg)
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log(f"[{d.name} / {cfg['chunk']['method']}] 청크 {len(chunks)}개")
    ensure_bm25(cfg, chunks)
    t1 = time.time()
    vs = build_chroma(cfg, chunks, log)
    n = vs._collection.count()
    assert n == len(chunks), f"Chroma {n} != 청크 {len(chunks)}"
    meta = dict(embedder=cfg["embeddings"]["model"], method=cfg["chunk"]["method"], n_chunks=n,
                bm25_seconds=round(t1 - t0, 1), chroma_seconds=round(time.time() - t1, 1),
                built_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    (d / f"meta_{cfg['chunk']['method']}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"  끝: {meta}")
    return meta


if __name__ == "__main__":
    from rfp_rag.settings import load

    assert tokenize("Kiwi로 국민연금공단 이러닝시스템 2024") and "이러닝" in "".join(tokenize("이러닝시스템 구축"))
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp")
    ap.add_argument("--embedder", nargs="*", default=list(EMBEDDERS))
    ap.add_argument("--method", nargs="*", default=list(METHODS))
    a = ap.parse_args()
    base = load(a.exp)
    for model in a.embedder:
        for method in a.method:
            c = copy.deepcopy(base)
            c["embeddings"]["model"], c["chunk"]["method"] = model, method
            build(c)
