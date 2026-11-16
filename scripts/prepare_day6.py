"""Xuất chunk Day 6 từ pgvector và chuyển benchmark Day 6 sang schema Day 7.

Chạy từ thư mục gốc:
    python -m scripts.prepare_day6 [--day6 <repo Day 6>] [--strategy A] [--output starter/data/day6]

- Chunk lấy trực tiếp từ bảng `chunks` (đúng bản đang được index), không từ file JSONL.
- Câu hỏi: gold_page "p63" -> page 63; alt_evidence được gộp vào `gold` làm evidence thay thế.
- Không suy đoán evidence hay filter; chỉ đổi tên trường. Kiểm tra bằng starter/baseline.validate.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAY6 = ROOT.parent / "K5-L3B-DAY06-NguyenTrongLam-2A202603817-DataIngestion"


def export_chunks(database_url: str, strategy: str) -> list[dict]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, connect_timeout=5, row_factory=dict_row) as conn:
        rows = conn.execute(
            """SELECT chunk_id, document_id, source, page, printed_page, section, text, metadata
               FROM chunks WHERE strategy = %s ORDER BY page, chunk_id""", (strategy,)).fetchall()
    if not rows:
        raise RuntimeError(f"Không có chunk nào cho strategy {strategy!r}")
    return [{"id": r["chunk_id"], "text": r["text"], "source_id": r["document_id"], "source": r["source"],
             "page": r["page"],
             "metadata": {**(r["metadata"] or {}), "section": r["section"], "printed_page": r["printed_page"]}}
            for r in rows]


# Evidence Day 6 chấm theo trang; Day 7 yêu cầu mỗi evidence nằm trọn trong MỘT chunk.
# Khi một evidence bị cắt giữa hai chunk, thay bằng đoạn con NGUYÊN VĂN vẫn đủ hỗ trợ đáp án.
# Quyết định thủ công, ghi lý do; chỉ dựa trên text nguồn, không dựa trên kết quả retrieval.
EVIDENCE_OVERRIDES = {
    ("q10", 86): {
        "evidence": "nhờ người thi hộ đều bị kỷ luật ở mức đình chỉ học tập 01 (một) năm đối với trường hợp "
                    "vi phạm lần thứ nhất và buộc thôi học đối với trường hợp vi phạm lần thứ hai.",
        "reason": "Quote gốc (alt_evidence p86) bị cắt giữa A-p86-002 và A-p86-003 (overlap 50 ký tự). "
                  "Đoạn con này nằm trọn trong A-p86-003 và vẫn đủ cho đáp án (đình chỉ 1 năm; tái phạm "
                  "buộc thôi học). Evidence chính p98 giữ nguyên.",
    },
}


def to_page(value) -> int:
    text = str(value).strip()
    if text.startswith("p"):
        text = text[1:]
    if not text.isdigit():
        raise ValueError(f"gold_page không hợp lệ: {value!r}")
    return int(text)


def to_gold(g: dict) -> dict:
    return {"source_id": g["gold_source_id"], "page": to_page(g["gold_page"]), "evidence": g["evidence_quote"]}


def apply_override(qid: str, gold: dict) -> dict:
    override = EVIDENCE_OVERRIDES.get((qid, gold["page"]))
    if not override:
        return gold
    if override["evidence"] not in gold["evidence"]:
        raise ValueError(f"{qid}: evidence thay thế phải là đoạn con nguyên văn của quote Day 6")
    return {**gold, "evidence": override["evidence"], "original_evidence": gold["evidence"],
            "override_reason": override["reason"]}


def convert_questions(raw: dict) -> list[dict]:
    out = []
    for q in raw["questions"]:
        golds = [to_gold(q)] + [to_gold(a) for a in (q.get("alt_evidence") or [])]
        item = {"id": q["id"], "split": q["split"], "question": q["question"],
                "expected_answer": q["expected_answer"], "type": q.get("type"),
                "gold": [apply_override(q["id"], g) for g in golds]}
        if q.get("filter"):
            item["filter"] = q["filter"]  # filter section do người hỏi nêu, theo filter_rule Day 6
        out.append(item)
    return out


def build_cases(questions: list[dict], unanswerable: list[dict]) -> list[dict]:
    """Danh sách câu cho agent/agent_metrics: chỉ id, split, question và nhãn answerable (không gold)."""
    ids = [q["id"] for q in questions] + [u["id"] for u in unanswerable]
    if len(ids) != len(set(ids)):
        raise ValueError("ID câu hỏi bị trùng giữa questions và unanswerable")
    for u in unanswerable:
        if u.get("split") not in ("dev", "test") or u.get("answerable") is not False \
                or u.get("expected_behavior") != "search_and_abstain" or not u.get("absence_reason"):
            raise ValueError(f"{u.get('id')}: câu thiếu evidence cần split, answerable=false, "
                             "expected_behavior=search_and_abstain và absence_reason")
    cases = [{"id": q["id"], "split": q["split"], "question": q["question"], "answerable": True,
              "expected_behavior": "search_and_answer", **({"filter": q["filter"]} if "filter" in q else {})}
             for q in questions]
    cases += [{"id": u["id"], "split": u["split"], "question": u["question"], "answerable": False,
               "expected_behavior": "search_and_abstain"} for u in unanswerable]
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--day6", type=Path, default=DEFAULT_DAY6)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "starter" / "data" / "day6")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("Thiếu DATABASE_URL trong .env")
    strategy = args.strategy or os.getenv("DAY6_STRATEGY", "A")

    qpath = args.day6 / "benchmark" / "questions.json"
    raw = json.loads(qpath.read_text(encoding="utf-8"))
    chunks = export_chunks(url, strategy)
    questions = convert_questions(raw)

    sys.path.insert(0, str(ROOT / "starter"))
    from baseline import hit, validate  # cùng quy tắc chấm với baseline
    validate(chunks, questions)  # lỗi nếu ID trùng, thiếu trường hoặc evidence không nằm trọn trong chunk

    unanswerable = json.loads((ROOT / "benchmark" / "unanswerable.json").read_text(encoding="utf-8"))["questions"]
    cases = build_cases(questions, unanswerable)

    gold_chunks = {q["id"]: sorted({c["id"] for c in chunks if hit(c, q["gold"])}) for q in questions}
    args.output.mkdir(parents=True, exist_ok=True)
    files = {"chunks.json": chunks, "questions.json": questions, "cases.json": cases}
    for name, data in files.items():
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    splits = {s: sum(q["split"] == s for q in questions) for s in ("dev", "test")}
    abstain_splits = {s: sum(u["split"] == s for u in unanswerable) for s in ("dev", "test")}
    meta = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": "python -m scripts.prepare_day6",
        "day6_repo": args.day6.name,
        "strategy": strategy,
        "chunks": len(chunks),
        "pages": [min(c["page"] for c in chunks), max(c["page"] for c in chunks)],
        "questions": len(questions),
        "splits": splits,
        "unanswerable": len(unanswerable),
        "unanswerable_splits": abstain_splits,
        "cases": len(cases),
        "questions_with_alt_evidence": [q["id"] for q in questions if len(q["gold"]) > 1],
        "questions_with_filter": {q["id"]: q["filter"] for q in questions if "filter" in q},
        "evidence_overrides": [{"id": q["id"], "page": g["page"], "reason": g["override_reason"]}
                               for q in questions for g in q["gold"] if "override_reason" in g],
        "chunks_containing_gold": gold_chunks,  # để tra cứu khi đọc lỗi, KHÔNG đưa vào agent
        "day6_benchmark_rules": {k: v for k, v in raw.items() if k != "questions"},
        "sha256": {name: hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in files},
        "note": "Không đưa gold, expected_answer hay chunks_containing_gold vào agent hoặc retrieval tool.",
    }
    (args.output / "prepare_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                                                   encoding="utf-8")
    print(f"Strategy {strategy}: {len(chunks)} chunk (trang {meta['pages'][0]}-{meta['pages'][1]}); "
          f"{len(questions)} câu {splits}; alt evidence: {meta['questions_with_alt_evidence']}; "
          f"filter: {list(meta['questions_with_filter'])}")
    print(f"Câu thiếu evidence: {len(unanswerable)} {abstain_splits}; cases.json: {len(cases)} câu")
    for split, need_ans, need_abs in (("dev", 15, 2), ("test", 5, 2)):
        if splits[split] < need_ans or abstain_splits[split] < need_abs:
            print(f"CẢNH BÁO: {split} cần >= {need_ans} câu có đáp án và >= {need_abs} câu thiếu evidence")
    missing = [qid for qid, ids in gold_chunks.items() if not ids]
    print("Mọi câu có ít nhất một chunk chứa evidence." if not missing else f"THIẾU chunk chứa evidence: {missing}")
    print(f"Đã ghi {args.output.relative_to(ROOT)}/: chunks.json, questions.json, cases.json, prepare_meta.json")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
