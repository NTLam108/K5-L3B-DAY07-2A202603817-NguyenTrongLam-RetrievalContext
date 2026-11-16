"""Chạy agent (model thật + DenseRetriever) trên cases.json và lưu trace/summary.

Ví dụ (từ thư mục gốc):
    python -m scripts.run_agent --split dev --config-file configs/baseline.json --ids q01 q10 u02   # smoke
    python -m scripts.run_agent --split dev --config-file configs/baseline.json                     # toàn bộ dev

- Cấu hình lấy từ file JSON đã chốt (configs/*.json); tên file + sha256 được ghi vào trace/summary.
  Ghi đè bằng CLI (--top-k, --budget, ...) chỉ để thử nhanh: bắt buộc đặt --name mới và được ghi lại.

- Input của agent chỉ là `question` (+ `filter` do người hỏi nêu) từ cases.json — không có gold.
- Gold (questions.json) chỉ được đọc SAU khi agent chạy xong, để chấm retrieval/context từ trace.
- Mỗi câu chạy trong try/except: lỗi provider/database -> status "error", chạy tiếp câu sau.
- Output: <output>/traces.json (định dạng dùng được cho starter/agent_metrics.py) và summary.json.
"""
import argparse
import collections
import hashlib
import json
import statistics
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "starter" / "data" / "day6"


def score_trace(trace: dict, gold_by_id: dict, chunks_by_id: dict, hit) -> dict:
    """Chấm retrieval/context sau khi chạy, bằng cùng hàm `hit` của baseline."""
    q = gold_by_id.get(trace["query_id"])
    searches = [e for e in trace.get("events", []) if e.get("event") == "search"]
    if q is None or not searches:
        return {}
    first = searches[0]["results"]
    all_ids = {r["id"] for e in searches for r in e["results"]}
    return {
        "first_search_hit1": bool(first and hit(first[0], q["gold"])),
        "first_search_hit3": any(hit(r, q["gold"]) for r in first[:3]),
        "any_search_hit": any(hit(chunks_by_id[i], q["gold"]) for i in all_ids if i in chunks_by_id),
        "context_evidence": any(hit(chunks_by_id[i], q["gold"]) for i in trace.get("context_ids", [])
                                if i in chunks_by_id),
        "cited_evidence": any(hit(chunks_by_id[i], q["gold"]) for i in trace.get("citations", [])
                              if i in chunks_by_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Chạy agent Day 7 trên một split")
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--config-file", type=Path, default=ROOT / "configs" / "baseline.json")
    parser.add_argument("--name", help="Tên cấu hình (mặc định: name trong file). Bắt buộc khi ghi đè bằng CLI.")
    parser.add_argument("--output", type=Path, help="Mặc định starter/results/agent-<name>-<split>")
    parser.add_argument("--ids", nargs="*", help="Chỉ chạy các ID này (smoke test)")
    parser.add_argument("--max-searches", type=int, help="Ghi đè agent.max_searches")
    parser.add_argument("--top-k", type=int, help="Ghi đè retrieval.top_k")
    parser.add_argument("--budget", type=int, help="Ghi đè context.budget_chars")
    parser.add_argument("--no-filter", action="store_true", help="Ghi đè retrieval.use_question_filter = false")
    args = parser.parse_args()

    raw_config = args.config_file.read_bytes()
    cfg = json.loads(raw_config.decode("utf-8"))
    overrides = {k: v for k, v in (("agent.max_searches", args.max_searches), ("retrieval.top_k", args.top_k),
                                   ("context.budget_chars", args.budget),
                                   ("retrieval.use_question_filter", False if args.no_filter else None))
                 if v is not None}
    name = args.name or cfg["name"]
    if overrides and name == cfg["name"]:
        raise SystemExit(f"Đang ghi đè {sorted(overrides)}: đặt --name khác '{cfg['name']}' để không lẫn với cấu hình đã chốt")
    method = cfg["retrieval"]["method"]
    # Các khóa mới đều có mặc định = hành vi baseline, nên configs/baseline.json không phải sửa.
    selection = cfg["context"].get("selection_mode", "order")
    first_query = cfg["agent"].get("first_query", "model")
    dedupe = cfg["agent"].get("dedupe_queries", False)
    prompt = cfg["llm"].get("prompt", "v1")
    if selection == "score" and method.startswith("hybrid"):
        raise SystemExit("selection_mode 'score' không hợp lệ với RRF (score chỉ so sánh được trong một query)")
    max_searches = overrides.get("agent.max_searches", cfg["agent"]["max_searches"])
    top_k = overrides.get("retrieval.top_k", cfg["retrieval"]["top_k"])
    budget = overrides.get("context.budget_chars", cfg["context"]["budget_chars"])
    use_filter = overrides.get("retrieval.use_question_filter", cfg["retrieval"]["use_question_filter"])

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "starter"))
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    from baseline import hit
    from src.agent.controller import LLMController
    from src.agent.loop import run_agent
    from src.agent.retriever import DenseRetriever, build_retriever

    cases = [c for c in json.loads((DATA / "cases.json").read_text(encoding="utf-8")) if c["split"] == args.split]
    if args.ids:
        unknown = set(args.ids) - {c["id"] for c in cases}
        if unknown:
            raise SystemExit(f"ID không có trong split {args.split}: {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in args.ids]
    output = args.output or ROOT / "starter" / "results" / f"agent-{name}-{args.split}"
    if args.ids:
        output = output.with_name(output.name + "-smoke")

    t0 = time.perf_counter()
    dense = DenseRetriever(strategy=cfg["retrieval"]["store_strategy"])
    if dense.describe()["embedding_model"] != cfg["retrieval"]["embedding_model"]:
        raise SystemExit("Embedding model trong .env khác embedding_model của cấu hình")
    r = cfg["retrieval"]
    retriever = dense if method == "dense" else build_retriever(
        method, chunks=json.loads((DATA / "chunks.json").read_text(encoding="utf-8")), dense=dense,
        rrf_k=r.get("rrf_k", 60), depth=r.get("fusion_depth", 20), candidates=r.get("rerank_candidates", 20))
    llm = cfg["llm"]
    controller = LLMController(model=llm["model"], reasoning_effort=llm["reasoning_effort"],
                               prices=llm["prices_usd_per_1m"], max_retries=llm["max_retries"],
                               max_completion_tokens=llm["max_completion_tokens"], prompt=prompt)
    load_seconds = time.perf_counter() - t0
    config = {"name": name, "split": args.split,
              "config_file": args.config_file.resolve().relative_to(ROOT).as_posix(),
              "config_sha256": hashlib.sha256(raw_config).hexdigest(), "cli_overrides": overrides,
              "max_searches": max_searches, "top_k": top_k, "budget_chars": budget,
              "use_question_filter": use_filter, "selection_mode": selection, "first_query": first_query,
              "dedupe_queries": dedupe, "retriever": retriever.describe(), "controller": controller.describe()}
    print(f"Cấu hình: {json.dumps(config, ensure_ascii=False)}\nChạy {len(cases)} câu...")

    traces = []
    for case in cases:
        filters = case.get("filter") if use_filter else None
        started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        try:
            result = run_agent(case["question"], controller, retriever, filters=filters,
                               max_searches=max_searches, top_k=top_k, budget=budget, selection=selection,
                               first_query=first_query, dedupe_queries=dedupe)
            error = None
        except Exception as exc:  # ghi lỗi thật, chạy tiếp câu sau
            error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc(limit=3)}
            result = {"status": "error", "stop_reason": "error", "answer": None, "citations": [],
                      "events": [{"event": "llm_call", **c} for c in controller.pop_calls()],
                      "num_searches": None, "context_ids": [], "elapsed_ms": None}
        llm = [e for e in result["events"] if e.get("event") == "llm_call"]
        trace = {"query_id": case["id"], "split": case["split"], "question": case["question"],
                 "answerable": case["answerable"], "filter": filters, "config": name,
                 "started_at": started, **result, "error": error,
                 "llm_calls": len(llm),
                 "prompt_tokens": sum(c.get("prompt_tokens", 0) for c in llm),
                 "cached_tokens": sum(c.get("cached_tokens", 0) for c in llm),
                 "completion_tokens": sum(c.get("completion_tokens", 0) for c in llm),
                 "reasoning_tokens": sum(c.get("reasoning_tokens", 0) for c in llm),
                 "cost_usd": sum(c.get("cost_usd", 0) for c in llm)}
        traces.append(trace)
        print(f"  {case['id']}: {trace['status']:<8} {trace['stop_reason']:<28} searches={trace['num_searches']} "
              f"cites={trace['citations']} {trace['cost_usd']:.5f}$"
              + (f"  ERROR {error['type']}: {error['message'][:120]}" if error else ""))

    # Chấm retrieval/context sau khi chạy xong (gold không đi vào agent).
    gold_by_id = {q["id"]: q for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))}
    chunks_by_id = {c["id"]: c for c in json.loads((DATA / "chunks.json").read_text(encoding="utf-8"))}
    for t in traces:
        t["auto_scores"] = score_trace(t, gold_by_id, chunks_by_id, hit) if t["answerable"] else {}

    ok = [t for t in traces if t["status"] != "error"]
    ans = [t for t in ok if t["answerable"]]
    una = [t for t in ok if not t["answerable"]]
    frac = lambda n, d: {"n": n, "N": d, "rate": round(n / d, 3) if d else None}  # noqa: E731
    count = lambda key, rows: sum(bool(t["auto_scores"].get(key)) for t in rows)  # noqa: E731
    summary = {
        "config": config, "load_seconds": round(load_seconds, 1), "cases": len(traces),
        "status": dict(collections.Counter(t["status"] for t in traces)),
        "stop_reason": dict(collections.Counter(t["stop_reason"] for t in traces)),
        "errors": [t["query_id"] for t in traces if t["status"] == "error"],
        "tool_use": frac(sum(bool(t["num_searches"]) for t in ok), len(ok)),
        "searches_distribution": dict(sorted(collections.Counter(t["num_searches"] for t in ok).items())),
        "answerable": {
            "answered": frac(sum(t["status"] == "answered" for t in ans), len(ans)),
            "false_abstention": frac(sum(t["status"] == "abstain" for t in ans), len(ans)),
            "first_search_hit1": frac(count("first_search_hit1", ans), len(ans)),
            "first_search_hit3": frac(count("first_search_hit3", ans), len(ans)),
            "context_evidence_rate": frac(count("context_evidence", ans), len(ans)),
            "cited_gold_chunk": frac(count("cited_evidence", ans), len(ans)),
        },
        "unanswerable": {"abstained": frac(sum(t["status"] == "abstain" for t in una), len(una))},
        "note": "auto_scores chỉ khớp chuỗi evidence trong chunk; KHÔNG thay chấm thủ công câu trả lời/citation.",
        "llm_calls": sum(t["llm_calls"] for t in traces),
        "prompt_tokens": sum(t["prompt_tokens"] for t in traces),
        "cached_tokens": sum(t["cached_tokens"] for t in traces),
        "completion_tokens": sum(t["completion_tokens"] for t in traces),
        "reasoning_tokens": sum(t["reasoning_tokens"] for t in traces),
        "cost_usd": round(sum(t["cost_usd"] for t in traces), 6),
        "median_case_ms": statistics.median([t["elapsed_ms"] for t in ok]) if ok else None,
        "total_seconds": round(time.perf_counter() - t0, 1),
    }
    output.mkdir(parents=True, exist_ok=True)
    for name, obj in (("traces.json", traces), ("summary.json", summary)):
        (output / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("status", "stop_reason", "tool_use", "answerable", "unanswerable",
                                                "cost_usd", "median_case_ms")}, ensure_ascii=False, indent=2))
    print(f"Đã ghi {output.relative_to(ROOT)}")
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
