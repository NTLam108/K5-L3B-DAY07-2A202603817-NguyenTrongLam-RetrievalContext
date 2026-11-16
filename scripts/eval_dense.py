"""Dense retrieval baseline trên vector store Day 6 (bge-m3 + pgvector), cùng định dạng output với TF-IDF.

Chạy từ thư mục gốc:
    python -m scripts.eval_dense --split dev --output starter/results/dev-dense

- Dùng đúng `hit` và `pack_context` của starter/baseline.py: Hit@1, Evidence Hit@3, Context Evidence Rate
  so sánh trực tiếp được với TF-IDF (cùng top-3, cùng context budget 800 ký tự).
- Không filter (giống strategy A ở Day 6). `--use-filter` chỉ áp filter do người hỏi nêu (trường `filter`).
- Thêm hit theo trang (định nghĩa Day 6) để đối chiếu với Day 6: dev Hit@3 = 15/15, Hit@1 = 9/15.
- Câu hỏi đưa vào retrieval chỉ là `question`; gold chỉ dùng để chấm sau khi đã có kết quả.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from baseline import hit, pack_context, validate  # noqa: E402


def page_hit(chunk: dict, gold: list[dict]) -> bool:
    return any(chunk["source_id"] == g["source_id"] and chunk["page"] == g["page"] for g in gold)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dense retrieval baseline trên pgvector Day 6")
    parser.add_argument("--chunks", type=Path, default=ROOT / "starter/data/day6/chunks.json")
    parser.add_argument("--questions", type=Path, default=ROOT / "starter/data/day6/questions.json")
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--budget", type=int, default=800)
    parser.add_argument("--use-filter", action="store_true")
    args = parser.parse_args()

    from src.agent.retriever import DenseRetriever  # cùng retriever với agent

    chunks = json.loads(args.chunks.read_text(encoding="utf-8"))
    questions = [q for q in json.loads(args.questions.read_text(encoding="utf-8")) if q["split"] == args.split]
    validate(chunks, questions)

    t0 = time.perf_counter()
    retriever = DenseRetriever()
    emb, strategy = retriever.embedder, retriever.strategy
    load_seconds = time.perf_counter() - t0

    traces = []
    for q in questions:
        filters = q.get("filter") if args.use_filter else None
        start = time.perf_counter()
        error = None
        try:
            results = retriever.search(q["question"], filters=filters, top_k=max(args.top_k, 3))
        except Exception as exc:  # ghi lỗi thật, không thay bằng kết quả giả
            results, error = [], f"{type(exc).__name__}: {exc}"
        context, ids = pack_context(results[:args.top_k], args.budget)
        elapsed_ms = (time.perf_counter() - start) * 1000
        marked = [{**c, "hit": hit(c, q["gold"]), "page_hit": page_hit(c, q["gold"])} for c in results]
        top3 = marked[:3]
        traces.append({
            "query_id": q["id"], "split": q["split"], "question": q["question"], "strategy": "dense",
            "store_strategy": strategy, "embedding_model": emb.model_name, "top_k": args.top_k,
            "budget_chars": args.budget, "filter": filters, "gold": q["gold"], "results": marked,
            "context": context, "context_ids": ids, "context_chars": len(context), "elapsed_ms": elapsed_ms,
            "error": error,
            "hit1": bool(top3 and top3[0]["hit"]), "hit3": any(c["hit"] for c in top3),
            "context_hit": any(c["hit"] and c["id"] in ids for c in marked),
            "page_hit1": bool(top3 and top3[0]["page_hit"]), "page_hit3": any(c["page_hit"] for c in top3),
        })

    n = len(traces)
    summary = {
        "strategy": "dense", "split": args.split, "n": n, "store_strategy": strategy,
        "embedding_model": emb.model_name, "dimensions": emb.dimensions, "top_k": args.top_k,
        "budget_chars": args.budget, "use_filter": args.use_filter,
        "hit1": sum(t["hit1"] for t in traces), "hit3": sum(t["hit3"] for t in traces),
        "context_hit": sum(t["context_hit"] for t in traces),
        "page_hit1_day6_def": sum(t["page_hit1"] for t in traces),
        "page_hit3_day6_def": sum(t["page_hit3"] for t in traces),
        "errors": sum(t["error"] is not None for t in traces),
        "avg_context_chars": statistics.mean(t["context_chars"] for t in traces),
        "median_ms": statistics.median(t["elapsed_ms"] for t in traces),
        "model_load_seconds": round(load_seconds, 2), "service_cost_usd": 0,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, obj in (("traces.json", traces), ("summary.json", summary)):
        (args.output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
