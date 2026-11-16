"""So sánh các phương pháp retrieval (không qua agent) trên cùng corpus, câu hỏi và nhãn.

Chạy từ thư mục gốc:
    python -m scripts.eval_retrieval --split dev --methods dense bm25 bm25_bigram hybrid_rrf rerank_dense rerank_hybrid

- Query = nguyên văn `question` (không viết lại); filter chỉ khi --use-filter (trường `filter` của câu).
- Chấm bằng đúng `hit` và `pack_context` của starter/baseline.py: Hit@1, Evidence Hit@3, Context Evidence Rate
  (top-3, budget 800 ký tự) — so sánh trực tiếp với TF-IDF baseline. Thêm Hit@10 và MRR@10.
- Gold chỉ dùng để chấm sau khi có kết quả. Output: starter/results/<split>-<method>/{traces,summary}.json
  và starter/results/retrieval-comparison-<split>.{json,md}.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "starter" / "data" / "day6"
METHODS = ("dense", "bm25", "bm25_bigram", "hybrid_rrf", "hybrid_rrf_bigram", "rerank_dense",
           "rerank_hybrid", "rerank_hybrid_bigram")


def evaluate(retriever, questions, hit, pack_context, *, use_filter: bool, depth: int, top_k: int, budget: int):
    traces = []
    for q in questions:
        filters = q.get("filter") if use_filter else None
        t0 = time.perf_counter()
        error = None
        try:
            results = retriever.search(q["question"], filters=filters, top_k=depth)
        except Exception as exc:  # ghi lỗi thật
            results, error = [], f"{type(exc).__name__}: {exc}"
        elapsed_ms = (time.perf_counter() - t0) * 1000
        context, ids = pack_context(results[:top_k], budget)
        marked = [{**r, "hit": hit(r, q["gold"])} for r in results]
        first = next((r["rank"] for r in marked if r["hit"]), None)
        traces.append({
            "query_id": q["id"], "split": q["split"], "question": q["question"], "filter": filters,
            "gold": q["gold"], "results": marked, "context": context, "context_ids": ids,
            "context_chars": len(context), "elapsed_ms": elapsed_ms, "timing": dict(retriever.last_timing),
            "error": error, "first_hit_rank": first,
            "hit1": bool(marked and marked[0]["hit"]), "hit3": any(r["hit"] for r in marked[:3]),
            "hit10": any(r["hit"] for r in marked[:10]),
            "context_hit": any(r["hit"] and r["id"] in ids for r in marked),
            "rr10": 1 / first if first and first <= 10 else 0.0,
            # với rerank: chunk gold đứng hạng mấy ở first stage
            "first_stage_rank_of_gold": next((r.get("first_stage_rank") for r in marked if r["hit"]), None),
        })
    return traces


def summarize(method, retriever, traces, *, load_seconds, split, use_filter, depth, top_k, budget):
    n = len(traces)
    frac = lambda k: {"n": sum(t[k] for t in traces), "N": n, "rate": round(sum(t[k] for t in traces) / n, 3)}  # noqa
    return {
        "method": method, "split": split, "n": n, "use_filter": use_filter, "query": "nguyên văn question",
        "depth": depth, "top_k_context": top_k, "budget_chars": budget, "retriever": retriever.describe(),
        "hit1": frac("hit1"), "hit3": frac("hit3"), "context_hit": frac("context_hit"), "hit10": frac("hit10"),
        "mrr10": round(sum(t["rr10"] for t in traces) / n, 3),
        "missed_hit1": [t["query_id"] for t in traces if not t["hit1"]],
        "missed_hit3": [t["query_id"] for t in traces if not t["hit3"]],
        "errors": [t["query_id"] for t in traces if t["error"]],
        "median_ms": round(statistics.median(t["elapsed_ms"] for t in traces), 1),
        "load_seconds": round(load_seconds, 2), "service_cost_usd": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="So sánh phương pháp retrieval trên một split")
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--methods", nargs="+", default=list(METHODS), choices=METHODS)
    parser.add_argument("--use-filter", action="store_true")
    parser.add_argument("--depth", type=int, default=10, help="Số kết quả lấy để tính Hit@10/MRR@10")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--budget", type=int, default=800)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--fusion-depth", type=int, default=20)
    parser.add_argument("--candidates", type=int, default=20, help="Số candidate cho reranker")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "starter"))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from baseline import hit, pack_context, validate
    from src.agent.retriever import DenseRetriever, build_retriever

    chunks = json.loads((DATA / "chunks.json").read_text(encoding="utf-8"))
    questions = [q for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))
                 if q["split"] == args.split]
    validate(chunks, questions)

    shared: dict = {}
    rows = []
    for method in args.methods:
        t0 = time.perf_counter()
        if method != "bm25" and method != "bm25_bigram" and "dense" not in shared:
            shared["dense"] = DenseRetriever()
        if method.startswith("rerank") and "reranker" not in shared:
            from sentence_transformers import CrossEncoder
            import os
            shared["reranker"] = CrossEncoder(os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"), max_length=512,
                                              cache_folder=os.getenv("RERANKER_CACHE_DIR") or None, device="cpu")
        retriever = build_retriever(method, chunks=chunks, dense=shared.get("dense"), rrf_k=args.rrf_k,
                                    depth=args.fusion_depth, candidates=args.candidates,
                                    reranker=shared.get("reranker"))
        load_seconds = time.perf_counter() - t0
        traces = evaluate(retriever, questions, hit, pack_context, use_filter=args.use_filter, depth=args.depth,
                          top_k=args.top_k, budget=args.budget)
        summary = summarize(method, retriever, traces, load_seconds=load_seconds, split=args.split,
                            use_filter=args.use_filter, depth=args.depth, top_k=args.top_k, budget=args.budget)
        out = ROOT / "starter" / "results" / f"{args.split}-{method}{'-filter' if args.use_filter else ''}"
        out.mkdir(parents=True, exist_ok=True)
        for name, obj in (("traces.json", traces), ("summary.json", summary)):
            (out / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rows.append(summary)
        f = lambda k: f"{summary[k]['n']}/{summary[k]['N']}"  # noqa: E731
        print(f"{method:<14} Hit@1 {f('hit1'):>5}  Hit@3 {f('hit3'):>5}  Context {f('context_hit'):>5}  "
              f"Hit@10 {f('hit10'):>5}  MRR@10 {summary['mrr10']:.3f}  {summary['median_ms']:>7.1f} ms/câu  "
              f"miss@3 {summary['missed_hit3']}")

    suffix = "-filter" if args.use_filter else ""
    (ROOT / "starter" / "results" / f"retrieval-comparison-{args.split}{suffix}.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["| Phương pháp | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Hit@10 | MRR@10 | Trung vị ms/câu | Nạp (s) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f = lambda k: f"{r[k]['n']}/{r[k]['N']} ({r[k]['rate']:.0%})"  # noqa: E731
        lines.append(f"| {r['method']} | {f('hit1')} | {f('hit3')} | {f('context_hit')} | {f('hit10')} | "
                     f"{r['mrr10']:.3f} | {r['median_ms']} | {r['load_seconds']} |")
    (ROOT / "starter" / "results" / f"retrieval-comparison-{args.split}{suffix}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
