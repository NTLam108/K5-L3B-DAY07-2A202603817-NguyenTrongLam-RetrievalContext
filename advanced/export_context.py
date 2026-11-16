"""Dựng lại context đã gửi model cho từng câu của một lần chạy (không gọi lại model).

Agent gửi model kết quả của từng lần search_documents (chunk định dạng bằng agent.format_chunk, cắt ở
max_chunk_chars; chunk đã hiện ở lượt trước được thay bằng "(already shown above)") và kết quả inspect_figure.
Trace lưu id/rank/score của từng kết quả và câu trả lời của vision model, nên context dựng lại được nguyên văn từ
advanced/data/chunks.json (cùng commit với lần chạy).

  .venv/Scripts/python.exe advanced/export_context.py advanced/results/a_mini_rerank-test
  -> <run>/contexts.json: {id: [{"step", "tool", "query"|"chunk_id", "content"}...]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "advanced"))

from agent import format_chunk  # noqa: E402


def main() -> None:
    run = Path(sys.argv[1]).resolve()
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    max_chars = summary["config"]["agent"]["max_chunk_chars"]
    chunks = {c["id"]: c for c in json.loads((ROOT / "advanced/data/chunks.json").read_text(encoding="utf-8"))}
    out = {}
    for t in json.loads((run / "traces.json").read_text(encoding="utf-8")):
        seen: set[str] = set()
        searches = iter(t["retrieval"])
        visions = iter(c for c in t["llm_calls"] if c.get("kind") == "vision")
        items = []
        for call in t["tool_calls"]:
            if call["tool"] == "search_documents":
                r = next(searches)
                parts = []
                for h in r["results"]:
                    if h["id"] in seen:
                        parts.append(f"[{h['id']}] (already shown above)")
                    else:
                        seen.add(h["id"])
                        parts.append(format_chunk(chunks[h["id"]], max_chars))
                items.append({"step": call["step"], "tool": "search_documents", "query": r["query"],
                              "content": "\n\n".join(parts)})
            elif call["tool"] == "inspect_figure":
                v = next(visions, None)
                items.append({"step": call["step"], "tool": "inspect_figure",
                              "chunk_id": call["arguments"].get("chunk_id"),
                              "question": call["arguments"].get("question"),
                              "content": v["answer"] if v else "(không có kết quả)"})
        out[t["id"]] = items
    (run / "contexts.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {(run / 'contexts.json').relative_to(ROOT).as_posix()} ({len(out)} câu)")


if __name__ == "__main__":
    main()
