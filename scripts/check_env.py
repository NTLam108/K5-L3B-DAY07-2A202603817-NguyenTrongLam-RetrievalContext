"""Kiểm tra môi trường Day 7: thư viện, .env, embedding model, vector store Day 6.

Chạy từ thư mục gốc:  python -m scripts.check_env
Mỗi bước in OK/FAIL; không thay lỗi bằng kết quả giả. Ghi kết quả vào starter/results/env_check.json.
"""
import json
import os
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"model": "BAAI/bge-m3", "dimensions": 1024, "strategy": "A", "chunks": 363}
report: dict = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "python": sys.version.split()[0],
                "platform": platform.platform(), "steps": {}}


def step(name, fn):
    t = time.perf_counter()
    try:
        info = fn()
        report["steps"][name] = {"ok": True, "seconds": round(time.perf_counter() - t, 2), **(info or {})}
        print(f"[OK]   {name}: {info or ''}")
        return True
    except Exception as exc:  # báo lỗi thật
        report["steps"][name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
        return False


def check_libs():
    import psycopg, sentence_transformers, torch, transformers  # noqa: E401
    return {"torch": torch.__version__, "sentence_transformers": sentence_transformers.__version__,
            "transformers": transformers.__version__, "psycopg": psycopg.__version__}


def check_env_file():
    from dotenv import load_dotenv
    if not (ROOT / ".env").exists():
        raise FileNotFoundError("Thiếu .env: sao chép .env.example thành .env")
    load_dotenv(ROOT / ".env")
    missing = [k for k in ("DATABASE_URL", "EMBEDDING_MODEL") if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Thiếu biến: {missing}")
    if os.getenv("EMBEDDING_MODEL") != EXPECTED["model"]:
        raise RuntimeError(f"EMBEDDING_MODEL={os.getenv('EMBEDDING_MODEL')} khác model ingest Day 6 ({EXPECTED['model']})")
    return {"EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL"), "DAY6_STRATEGY": os.getenv("DAY6_STRATEGY", "A"),
            "LLM_PROVIDER": os.getenv("LLM_PROVIDER") or "(chưa đặt — checkpoint 2)"}


state: dict = {}


def check_embedder():
    from src.day6.embeddings import MyEmbedder
    emb = MyEmbedder()
    if emb.dimensions != EXPECTED["dimensions"]:
        raise RuntimeError(f"Model có {emb.dimensions} chiều, index Day 6 dùng {EXPECTED['dimensions']}")
    vec = emb.embed_query("Điều kiện xét tốt nghiệp là gì?")
    norm = sum(x * x for x in vec) ** 0.5
    state["emb"] = emb
    info = emb.info()
    return {"model": info["model"], "dimensions": info["dimensions"], "device": info["device"],
            "max_seq_length": info["max_seq_length"], "query_norm": round(norm, 4)}


def check_store():
    from src.day6.store import PgVectorStore
    store = PgVectorStore.from_env(EXPECTED["dimensions"])
    counts = store.counts()
    strategy = os.getenv("DAY6_STRATEGY", EXPECTED["strategy"])
    rows, distinct = counts.get(strategy, (0, 0))
    if rows != distinct:
        raise RuntimeError(f"Strategy {strategy} có chunk_id trùng: {rows} dòng / {distinct} ID")
    if rows != EXPECTED["chunks"]:
        raise RuntimeError(f"Strategy {strategy} có {rows} chunk, Day 6 ghi {EXPECTED['chunks']}; cần ingest lại?")
    state["store"] = store
    return {"versions": store.versions(), "counts": {k: v[0] for k, v in counts.items()}}


def check_search():
    emb, store = state["emb"], state["store"]
    q = "Sinh viên được kéo dài thời gian học thêm tối đa bao nhiêu năm so với kế hoạch học tập?"
    hits = store.search(os.getenv("DAY6_STRATEGY", "A"), emb.embed_query(q), top_k=3)
    return {"query": q, "top3": [{"chunk_id": h["chunk_id"], "page": h["page"], "score": round(h["score"], 4)}
                                 for h in hits]}


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    ok = step("thư viện", check_libs) and step(".env", check_env_file)
    ok = step("embedding model", check_embedder) and ok
    store_ok = step("vector store Day 6", check_store)
    if store_ok and "emb" in state:
        step("dense search thử", check_search)
    out = ROOT / "starter" / "results" / "env_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã ghi {out.relative_to(ROOT)}")
    sys.exit(0 if all(s["ok"] for s in report["steps"].values()) else 1)
