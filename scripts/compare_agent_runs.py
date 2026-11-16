"""Gộp summary.json của nhiều lần chạy agent thành bảng so sánh (chỉ số tự động + chấm tay nếu có).

Chạy từ thư mục gốc:
    python -m scripts.compare_agent_runs --split dev --runs baseline baseline-dev-run2 improve_query ...

- Mỗi run là thư mục starter/results/agent-<run>-<split> (hoặc agent-<run> nếu đã kèm split).
- Nếu có nhãn chấm tay labels/<split>/<run>.reviews.json (hoặc .reviews.draft.json) thì tính thêm
  grounded answer, citation hợp lệ, abstention bằng starter/agent_metrics.aggregate.
- Output: starter/results/agent-comparison-<split>.{json,md}
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "starter" / "results"


def run_dir(run: str, split: str) -> Path:
    for cand in (RESULTS / f"agent-{run}-{split}", RESULTS / f"agent-{run}"):
        if (cand / "summary.json").exists():
            return cand
    raise SystemExit(f"Không thấy summary cho run '{run}'")


def load_reviews(run: str, split: str):
    for suffix in ("reviews.json", "reviews.draft.json"):
        p = ROOT / "labels" / split / f"{run}.{suffix}"
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return (data["reviews"] if isinstance(data, dict) else data), suffix
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--runs", nargs="+", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "starter"))
    from agent_metrics import aggregate

    cases = [c for c in json.loads((ROOT / "starter/data/day6/cases.json").read_text(encoding="utf-8"))
             if c["split"] == args.split]
    rows = []
    for run in args.runs:
        d = run_dir(run, args.split)
        s = json.loads((d / "summary.json").read_text(encoding="utf-8"))
        traces = json.loads((d / "traces.json").read_text(encoding="utf-8"))
        a = s["answerable"]
        answered_wrong = None
        row = {"run": run, "dir": d.relative_to(ROOT).as_posix(), "config_file": s["config"].get("config_file"),
               "config_sha256": (s["config"].get("config_sha256") or "")[:8],
               "first_search_hit1": a["first_search_hit1"], "first_search_hit3": a["first_search_hit3"],
               "context_evidence_rate": a["context_evidence_rate"], "answered": a["answered"],
               "false_abstention": a["false_abstention"], "unanswerable_abstained": s["unanswerable"]["abstained"],
               "searches_distribution": s["searches_distribution"], "errors": s["errors"],
               "cost_usd": s["cost_usd"], "median_case_ms": s["median_case_ms"],
               "prompt_tokens": s["prompt_tokens"], "completion_tokens": s["completion_tokens"]}
        reviews, source = load_reviews(run, args.split)
        if reviews is not None:
            m = aggregate(cases, traces, reviews)
            by_id = {t["query_id"]: t for t in traces}
            answered_wrong = sum(1 for r in reviews if r.get("answer_grade") == 0
                                 and by_id[r["query_id"]]["status"] == "answered")
            row.update(review_source=source, grounded=m["grounded_answer"], citation_validity=m["citation_validity"],
                       abstention=m["abstention"], answered_wrong_with_citation=answered_wrong)
        rows.append(row)

    out = RESULTS / f"agent-comparison-{args.split}"
    out.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nN = lambda x: f"{x['n']}/{x['N']}"  # noqa: E731
    lines = ["| Run | First-search Hit@1 | First-search Hit@3 | Context Evidence | Trả lời | Từ chối nhầm | "
             "Từ chối đúng | Grounded TB /2 | Citation hợp lệ | Sai có citation | Chi phí $ | Trung vị s/câu |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        g = r.get("grounded")
        lines.append(" | ".join([
            f"| {r['run']}", nN(r["first_search_hit1"]), nN(r["first_search_hit3"]), nN(r["context_evidence_rate"]),
            nN(r["answered"]), nN(r["false_abstention"]), nN(r["unanswerable_abstained"]),
            f"{g['mean']:.2f}" + (" (nháp)" if r.get("review_source", "").endswith("draft.json") else "") if g else "chưa chấm",
            nN(r["citation_validity"]) if g else "–", str(r.get("answered_wrong_with_citation", "–")),
            f"{r['cost_usd']:.4f}", f"{r['median_case_ms'] / 1000:.1f} |"]))
    out.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
