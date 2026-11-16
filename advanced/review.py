"""Hỗ trợ chấm tay một lần chạy: đặt câu trả lời cạnh đáp án chuẩn, kiểm tra citation với gold, tính metrics từ nhãn.

  .venv/Scripts/python.exe advanced/review.py advanced/results/<run>            # -> review.md + labels.json (mẫu)
  .venv/Scripts/python.exe advanced/review.py advanced/results/<run> --metrics  # tính tỷ lệ đạt từ labels.json

Citation tự động chỉ là gợi ý: "gold_hit" = với mỗi evidence bắt buộc (gold_mode=all) có ít nhất một citation trỏ
vào chunk chứa evidence đó (gold_mode=any: chỉ cần một). NHÃN ĐẠT/KHÔNG ĐẠT do người chấm ghi trong labels.json sau
khi đối chiếu bản gốc (PDF, ảnh crop, StatLink); script không tự chấm nội dung.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "advanced" / "benchmark"


def citation_check(q: dict, gold_idx: list[dict], cites: list[str]) -> dict:
    hits = [bool(set(g["chunk_ids"]) & set(cites)) for g in gold_idx]
    ok = (any(hits) if q.get("gold_mode") == "any" else all(hits)) if hits else False
    return {"gold_hit": ok, "per_gold": hits}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--metrics", action="store_true")
    args = ap.parse_args()
    run = Path(args.run_dir).resolve()
    traces = {t["id"]: t for t in json.loads((run / "traces.json").read_text(encoding="utf-8"))}
    split = "test" if run.name.endswith("-test") else "dev"
    bench = {q["id"]: q for q in json.loads((BENCH / f"{split}.json").read_text(encoding="utf-8"))}
    gold_index = json.loads((BENCH / "gold_index.json").read_text(encoding="utf-8"))
    labels_path = run / "labels.json"

    if args.metrics:
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        unlabeled = [k for k, v in labels.items() if v.get("label") not in ("pass", "fail")]
        if unlabeled:
            sys.exit(f"Chưa gán nhãn: {unlabeled}")
        by_group: dict[str, Counter] = {}
        for qid, q in bench.items():
            c = by_group.setdefault(q["group"], Counter())
            c["n"] += 1
            c["pass"] += labels[qid]["label"] == "pass"
        total = sum(c["n"] for c in by_group.values())
        passed = sum(c["pass"] for c in by_group.values())
        errors = [qid for qid, t in traces.items() if t["status"] == "error"]
        cost = sum(t.get("cost_usd") or 0 for t in traces.values())
        lat = sorted(t["latency_s"] for t in traces.values())
        metrics = {"pass": passed, "total": total, "pass_rate": round(passed / total, 4),
                   "by_group": {g: f"{c['pass']}/{c['n']}" for g, c in by_group.items()},
                   "system_errors": errors, "cost_usd_total": round(cost, 4),
                   "latency_s_total": round(sum(lat), 1), "latency_s_median": lat[len(lat) // 2]}
        (run / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        return

    lines = [f"# Review {run.name}", ""]
    old = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else {}
    labels = {}
    for qid, q in bench.items():
        t = traces.get(qid)
        if t is None:
            continue
        cites = t.get("citations", [])
        cc = citation_check(q, gold_index.get(qid, []), cites) if q["answerable"] else None
        auto = {"status": t["status"], "gold_citation_hit": cc["gold_hit"] if cc else None}
        labels[qid] = {**{"label": "", "reason": ""}, **old.get(qid, {}), "auto": auto}
        lines += [f"## {qid} [{q['group']}] - {t['status']}", f"**Q:** {q['question']}", ""]
        if q["answerable"]:
            lines += [f"**Đáp án chuẩn:** {q['expected_answer']}", f"**Key facts:** {'; '.join(q['key_facts'])}",
                      f"**Dung sai:** {q.get('tolerance')}", ""]
        else:
            lines += [f"**Hành vi mong đợi:** từ chối. {q['absence_reason']}", ""]
        lines += [f"**Agent:** {t.get('answer') or t.get('reason') or t.get('error')}",
                  f"**Citations:** {cites}" + (f" | gold hit: {cc['gold_hit']} {cc['per_gold']}" if cc else ""),
                  f"**Queries:** {[r['query'] for r in t['retrieval']]}",
                  f"**Inspect:** {[c.get('question') for c in t['llm_calls'] if c.get('kind') == 'vision']}",
                  f"**Chi phí/thời gian:** ${t.get('cost_usd') or 0:.4f} / {t['latency_s']}s", ""]
    (run / "review.md").write_text("\n".join(lines), encoding="utf-8")
    labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {(run / 'review.md').relative_to(ROOT).as_posix()}, {labels_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
