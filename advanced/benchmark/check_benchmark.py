"""Kiểm tra benchmark dev/test của thử thách nâng cao.

1. Cơ cấu theo ADVANCED.md: test >= 30 câu (>= 24 có đáp án: bảng 6, ảnh 5, biểu đồ 5, multi-hop 4, text 4;
   >= 6 thiếu bằng chứng); dev >= 15 có đáp án + >= 3 thiếu bằng chứng; ID không trùng; câu hỏi không trùng.
2. Mỗi evidence trong `gold` phải có mặt nguyên văn (chuẩn hoá khoảng trắng, dấu nháy) trên đúng trang PDF gốc.
3. Ghi advanced/benchmark/gold_index.json: chunk id chứa evidence (hoặc chunk của hình/bảng), bbox trên trang và
   crop - dùng để chấm retrieval/citation. File này KHÔNG được đưa vào pipeline trả lời.

  .venv/Scripts/python.exe advanced/benchmark/check_benchmark.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "advanced" / "benchmark"
PDF = ROOT / "advanced" / "source" / "oecd-economic-surveys-viet-nam-2025.pdf"
CHUNKS = ROOT / "advanced" / "data" / "chunks.json"
OUT = BENCH / "gold_index.json"

MIN_TEST = {"table": 6, "image": 5, "chart": 5, "multihop": 4, "text": 4, "unanswerable": 6}
MIN_TEST_TOTAL, MIN_TEST_ANSWERABLE = 30, 24
MIN_DEV_ANSWERABLE, MIN_DEV_UNANSWERABLE = 15, 3


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace(" ", " ").replace("­", "")
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def nospace(s: str) -> str:
    return re.sub(r"\s+", "", norm(s))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    errors: list[str] = []
    doc = pymupdf.open(PDF)
    pages = {p.number + 1: p.get_text() for p in doc}
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    items = {s: json.loads((BENCH / f"{s}.json").read_text(encoding="utf-8")) for s in ("dev", "test")}

    ids = [q["id"] for qs in items.values() for q in qs]
    for dup in [i for i, n in Counter(ids).items() if n > 1]:
        errors.append(f"ID trùng: {dup}")
    questions = [norm(q["question"]) for qs in items.values() for q in qs]
    for dup in [q for q, n in Counter(questions).items() if n > 1]:
        errors.append(f"Câu hỏi trùng: {dup[:80]}")

    for split, qs in items.items():
        groups = Counter(q["group"] for q in qs)
        answerable = sum(1 for q in qs if q["answerable"])
        print(f"{split}: {len(qs)} câu, {answerable} có đáp án, {len(qs) - answerable} thiếu bằng chứng | {dict(groups)}")
        for q in qs:
            if q["split"] != split:
                errors.append(f"{q['id']}: split '{q['split']}' nằm trong file {split}")
            if q["answerable"] != (q["group"] != "unanswerable"):
                errors.append(f"{q['id']}: answerable không khớp group")
            need = ("expected_answer", "key_facts", "gold", "rationale") if q["answerable"] else \
                ("expected_behavior", "absence_reason", "check_method")
            for k in need:
                if not q.get(k):
                    errors.append(f"{q['id']}: thiếu '{k}'")
        if split == "test":
            if len(qs) < MIN_TEST_TOTAL or answerable < MIN_TEST_ANSWERABLE:
                errors.append(f"test: {len(qs)} câu / {answerable} có đáp án (cần >= {MIN_TEST_TOTAL} / {MIN_TEST_ANSWERABLE})")
            for g, n in MIN_TEST.items():
                if groups[g] < n:
                    errors.append(f"test: nhóm {g} có {groups[g]} câu (cần >= {n})")
        else:
            if answerable < MIN_DEV_ANSWERABLE or len(qs) - answerable < MIN_DEV_UNANSWERABLE:
                errors.append(f"dev: {answerable} có đáp án / {len(qs) - answerable} thiếu (cần >= 15 / 3)")

    index: dict[str, list[dict]] = {}
    for qs in items.values():
        for q in qs:
            for gi, g in enumerate(q.get("gold") or []):
                page_text = pages.get(g["page"], "")
                found = norm(g["evidence"]) in norm(page_text) or nospace(g["evidence"]) in nospace(page_text)
                if not found:
                    errors.append(f"{q['id']} gold[{gi}]: không thấy '{g['evidence'][:60]}' ở trang PDF {g['page']}")
                # chunk: ưu tiên chunk của hình/bảng (object_id), sau đó chunk text chứa evidence
                cands = [c for c in chunks if c["page"] == g["page"] and g.get("object")
                         and c["metadata"].get("object_id") == g["object"]]
                if g.get("object") and not cands and g["object"] != "Basic statistics":
                    errors.append(f"{q['id']} gold[{gi}]: không có chunk cho {g['object']} ở trang {g['page']}")
                if g.get("object") == "Basic statistics":
                    cands = [c for c in chunks if c["metadata"].get("object_id") == "Basic statistics"]
                ev = nospace(g["evidence"])
                with_text = [c for c in cands if ev in nospace(c["text"])] or \
                            [c for c in chunks if c["page"] == g["page"] and ev in nospace(c["text"])]
                chosen = with_text or cands
                rects = doc[g["page"] - 1].search_for(g["evidence"][:60]) if found else []
                index.setdefault(q["id"], []).append({
                    "gold": gi, "page": g["page"], "printed_page": g["page"] - 2, "object": g.get("object"),
                    "evidence_found_on_page": found,
                    "chunk_ids": [c["id"] for c in chosen],
                    "evidence_bbox": [round(v, 1) for v in rects[0]] if rects else None,
                    "object_bbox": chosen[0]["metadata"].get("bbox") if chosen and g.get("object") else None,
                    "crop_path": chosen[0]["metadata"].get("crop_path") if chosen and g.get("object") else None,
                })
                if not chosen:
                    errors.append(f"{q['id']} gold[{gi}]: không tìm được chunk chứa evidence")

    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {OUT.relative_to(ROOT).as_posix()}")
    for e in errors:
        print("LỖI:", e)
    print("OK" if not errors else f"{len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
