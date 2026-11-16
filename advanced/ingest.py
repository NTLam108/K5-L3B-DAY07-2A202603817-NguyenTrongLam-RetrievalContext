"""Ingest đa phương thức cho OECD Economic Surveys: Viet Nam 2025.

Ba bước, chạy riêng hoặc gộp (`all`):

  extract   PDF -> advanced/data/extracted.json + ảnh crop + ingest_stats.json (không gọi API)
            - text: các block văn bản ngoài vùng hình/bảng, gộp theo trang và heading (<= MAX_CHARS)
            - table: vùng từ caption "Table x.y." tới dòng Source/StatLink; bảng nhiều trang tách theo trang
            - figure: vùng từ caption "Figure x.y." tới StatLink; ghi bbox, crop PNG, có phải ảnh raster không,
              nhãn chữ trong hình (với hình vector), Note/Source, StatLink
  describe  Gửi crop từng hình cho vision model -> advanced/data/figure_descriptions.json (có cache theo
            SHA256 crop + model + phiên bản prompt; ghi token, chi phí, thời gian từng lần gọi)
  build     Gộp extracted + mô tả -> advanced/data/chunks.json theo định dạng chunk Day 7
            (id, text, source_id, source, page, metadata)

Mọi chunk giữ liên kết về trang PDF, trang in, bbox (point, gốc trên-trái) và crop để kiểm chứng.
Không dùng benchmark, đáp án hay gold ở bất kỳ bước nào.

Cách chạy (từ thư mục gốc repo):
  .venv/Scripts/python.exe advanced/ingest.py extract
  .venv/Scripts/python.exe advanced/ingest.py describe [--raster-only] [--ids "Figure 1.10,Figure 4.1"] [--limit N]
  .venv/Scripts/python.exe advanced/ingest.py build
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
ADV = ROOT / "advanced"
PDF = ADV / "source" / "oecd-economic-surveys-viet-nam-2025.pdf"
PDF_URL = ("https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/06/"
           "oecd-economic-surveys-viet-nam-2025_f2511b78/fb37254b-en.pdf")
PDF_SHA256 = "e8ca6a3c51f44585c915bc032f991d91026ba772400584ff3a3fa764c05f5b0c"
DATA = ADV / "data"
CROPS = DATA / "crops"
EXTRACTED = DATA / "extracted.json"
DESCRIPTIONS = DATA / "figure_descriptions.json"
CHUNKS = DATA / "chunks.json"
STATS = DATA / "ingest_stats.json"

DOC_ID = "oecd-vn-2025"
SOURCE = "OECD Economic Surveys: Viet Nam 2025"
PRINTED_OFFSET = 2          # trang in = trang PDF - 2 (đã đối chiếu trang PDF 82 -> in 80, 99 -> 97)
HEADER_Y, FOOTER_Y = 60, 740  # header (số trang) ở y~38-52, footer bản quyền ở y~745
MAX_CHARS = 1200            # độ dài tối đa một chunk text
TABLE_PART_CHARS = 2500     # bảng dài hơn được tách theo hàng, mỗi phần lặp caption + header
CROP_DPI = 200
MAX_TABLE_CONT_PAGES = 4    # chốt chặn: bảng kéo dài quá số trang này thì cảnh báo
PROMPT_VERSION = "fig-v2"  # v1 ước lượng giá trị theo gridline -> sai năm/thứ tự (Figure 2.2); v2 chỉ chép số in sẵn

CAPTION_RE = re.compile(r"^(Figure|Table)\s+(\d+(?:\.\d+)?)\.\s*([A-Z].+)", re.S)  # "Figure 2.2.Income..." thiếu dấu cách
SOURCE_RE = re.compile(r"(^|\n)\s*Sources?\s*:")
STATLINK_RE = re.compile(r"https://stat\.link/\w+")
# Bảng không có caption "Table x.y." nhưng chứa số liệu: chỉ định thủ công cả vùng nội dung trang.
EXTRA_TABLES = {9: "Basic statistics of Viet Nam, 2023"}


# ----------------------------------------------------------------------------- tiện ích

def clean(text: str) -> str:
    text = text.replace(" ", " ").replace("", " ").replace("­", "")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # nối từ bị ngắt dòng bằng gạch nối
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def one_line(text: str) -> str:
    return re.sub(r"\s+", " ", clean(text)).strip()


def printed(page_no: int) -> int | None:
    n = page_no - PRINTED_OFFSET
    return n if n >= 1 else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "_", s.lower()).strip("_")


def open_pdf() -> pymupdf.Document:
    if not PDF.exists():
        sys.exit(f"Thiếu {rel(PDF)}. Tải theo hướng dẫn trong advanced/README.md:\n  {PDF_URL}")
    digest = sha256_file(PDF)
    if digest != PDF_SHA256:
        sys.exit(f"SHA256 của PDF không khớp ({digest}); bản tải về khác bản đã dùng để làm benchmark.")
    return pymupdf.open(PDF)


# ----------------------------------------------------------------------------- heading / section

def chapter_slug(title: str) -> str:
    m = re.match(r"^(\d)\s", title)
    if m:
        return f"ch{m.group(1)}"
    t = title.lower()
    if t.startswith("executive summary"):
        return "exec_summary"
    if t.startswith("basic statistics"):
        return "basic_statistics"
    return "front_matter"


def locate_headings(doc: pymupdf.Document) -> list[dict[str, Any]]:
    """Vị trí (trang, y) của từng mục trong mục lục PDF, để gán section cho từng block."""
    out = []
    for level, title, page_no in doc.get_toc():
        title = one_line(title)
        page = doc[page_no - 1]
        y = None
        for probe in (title[:60], " ".join(title.split()[:4])):
            hits = page.search_for(probe) if probe else []
            hits = [r for r in hits if HEADER_Y <= r.y0 <= FOOTER_Y]
            if hits:
                y = hits[0].y0
                break
        out.append({"level": level, "title": title, "page": page_no, "y": y if y is not None else HEADER_Y,
                    "located": y is not None})
    out.sort(key=lambda h: (h["page"], h["y"]))
    chapter = "front_matter"
    path: list[str] = []
    for h in out:
        if h["level"] == 1:
            chapter = chapter_slug(h["title"])
        path = path[: h["level"] - 1] + [h["title"]]
        h["chapter"], h["path"] = chapter, list(path)
    return out


def section_at(headings: list[dict[str, Any]], page_no: int, y: float) -> dict[str, Any] | None:
    current = None
    for h in headings:
        if (h["page"], h["y"]) <= (page_no, y + 1):
            current = h
        else:
            break
    return current


# ----------------------------------------------------------------------------- vùng hình / bảng

def body_blocks(page: pymupdf.Page) -> list[dict[str, Any]]:
    blocks = []
    for x0, y0, x1, y1, text, _no, kind in page.get_text("blocks", sort=False):
        if kind != 0 or not text.strip():
            continue
        if y0 < HEADER_Y or y0 > FOOTER_Y:
            continue
        blocks.append({"rect": pymupdf.Rect(x0, y0, x1, y1), "text": text})
    blocks.sort(key=lambda b: (round(b["rect"].y0), b["rect"].x0))
    return blocks


def is_caption(block: dict[str, Any]) -> re.Match | None:
    return CAPTION_RE.match(block["text"].strip())


def is_body_paragraph(block: dict[str, Any]) -> bool:
    """Đoạn văn thường: chạy hết khổ chữ (x 65-533). Ô bảng thụt vào (x >= 71, x1 <= 527)."""
    r, t = block["rect"], clean(block["text"])
    return r.x0 < 68 and r.x1 > 529 and len(t) > 150 and not is_note(t) and not STATLINK_RE.search(t)


def find_end(blocks, start_y: float, heading_ys: list[float], kind: str = "figure") -> tuple[float, bool, str]:
    """Tìm đáy vùng hình/bảng bắt đầu tại start_y. Trả (y_end, closed, marker)."""
    candidates: list[tuple[float, str]] = []
    if kind == "table":  # bảng không có Source (vd. Table 4.2) kết thúc khi văn bản thường bắt đầu
        for b in blocks:
            if b["rect"].y0 > start_y + 2 and is_body_paragraph(b):
                candidates.append((b["rect"].y0 - 3, "body_text"))
                break
    statlinks = [b for b in blocks if b["rect"].y0 > start_y + 2 and STATLINK_RE.search(b["text"])]
    for b in statlinks:
        candidates.append((b["rect"].y1, "statlink"))
    for b in blocks:
        if b["rect"].y0 > start_y + 2 and SOURCE_RE.search(b["text"]):
            end = b["rect"].y1
            for s in statlinks:  # StatLink nằm ngay dưới dòng Source thuộc cùng vùng
                if 0 <= s["rect"].y0 - end <= 25:
                    end = max(end, s["rect"].y1)
            candidates.append((end, "source"))
    for b in blocks:
        if b["rect"].y0 > start_y + 2 and is_caption(b):
            candidates.append((b["rect"].y0 - 3, "next_caption"))
    for y in heading_ys:
        if y > start_y + 2:
            candidates.append((y - 3, "heading"))
    if not candidates:
        return FOOTER_Y, False, "page_bottom"
    y, marker = min(candidates)
    return y, True, marker


def region_rect(page: pymupdf.Page, y0: float, y1: float) -> pymupdf.Rect:
    return pymupdf.Rect(50, max(y0 - 2, HEADER_Y - 5), page.rect.width - 50, min(y1 + 2, FOOTER_Y))


def inside(rect: pymupdf.Rect, region: pymupdf.Rect) -> bool:
    cy = (rect.y0 + rect.y1) / 2
    return region.y0 <= cy <= region.y1


def save_crop(page: pymupdf.Page, rect: pymupdf.Rect, name: str) -> Path:
    CROPS.mkdir(parents=True, exist_ok=True)
    path = CROPS / f"{name}.png"
    page.get_pixmap(dpi=CROP_DPI, clip=rect).save(path)
    return path


def raster_images(page: pymupdf.Page) -> list[dict[str, Any]]:
    out = []
    for img in page.get_images(full=True):
        for r in page.get_image_rects(img[0]):
            out.append({"xref": img[0], "width_px": img[2], "height_px": img[3], "rect": r})
    return out


NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)*")


def table_markdown(page: pymupdf.Page, rect: pymupdf.Rect) -> tuple[str | None, int, float | None]:
    """Markdown của các bảng find_tables thấy trong vùng, số bảng, và y mép trên của bảng đầu tiên."""
    try:
        found = page.find_tables(clip=rect)
    except Exception:  # noqa: BLE001 - layout lạ; quay về text theo hàng
        return None, 0, None
    tables = [t for t in found.tables if t.row_count >= 2]
    parts = [p for p in (t.to_markdown().strip() for t in tables) if p]
    top = min((t.bbox[1] for t in tables), default=None)
    return ("\n\n".join(parts) if parts else None), len(parts), top


def compact_markdown(md: str) -> str:
    """Bỏ ô văn bản dài bị lặp do ô gộp (merged cell) và ô rỗng thừa trong mỗi hàng markdown.

    Chỉ gộp ô trùng dài > 30 ký tự để không xoá nhầm số liệu bằng nhau ở các cột liền kề (vd. 2.3 | 2.3).
    """
    out = []
    for line in md.splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            out.append(line)
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        kept: list[str] = []
        for c in cells:
            if kept and len(c) > 30 and c == kept[-1]:
                continue
            kept.append(c)
        out.append("|" + "|".join(kept) + "|")
    return "\n".join(out)


def split_table(text: str, limit: int) -> list[str]:
    """Tách bảng dài theo hàng; mỗi phần lặp lại phụ đề + header markdown (tới dòng |---|) nếu có."""
    lines = text.splitlines()
    sep = next((i for i, ln in enumerate(lines[:6]) if ln.startswith("|-")), None)
    header = lines[: sep + 1] if sep is not None else []
    body = lines[len(header):]
    parts, cur = [], []
    for ln in body:
        if cur and sum(len(x) + 1 for x in header + cur) + len(ln) > limit:
            parts.append("\n".join(header + cur))
            cur = []
        cur.append(ln)
    if cur:
        parts.append("\n".join(header + cur))
    return parts


def row_text(page: pymupdf.Page, rect: pymupdf.Rect) -> str:
    """Dựng lại bảng theo hàng từ toạ độ từng từ: mỗi hàng một dòng, ô cách nhau ' | ' khi khoảng trống > 10pt.

    Không mất cột như find_tables, nhưng ô nhiều dòng bị tách thành nhiều hàng.
    """
    words = [w for w in page.get_text("words", clip=rect) if w[4].strip()]
    words.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows: list[list[tuple]] = []
    for w in words:
        cy = (w[1] + w[3]) / 2
        if rows and abs(cy - (rows[-1][0][1] + rows[-1][0][3]) / 2) <= 3:
            rows[-1].append(w)
        else:
            rows.append([w])
    lines = []
    for row in rows:
        row.sort(key=lambda w: w[0])
        line, prev_x1 = "", None
        for w in row:
            if prev_x1 is not None:
                line += " | " if w[0] - prev_x1 > 10 else " "
            line += w[4]
            prev_x1 = w[2]
        lines.append(line)
    return "\n".join(lines)


def numbers_missing(reference: str, candidate: str) -> list[str]:
    """Các số có trong reference nhưng thiếu (tính cả số lần) trong candidate."""
    def norm(s: str) -> str:  # "6 802.46" (cách hàng nghìn) và "6802.46" là cùng một số
        return re.sub(r"(?<=\d)[  ](?=\d{3}(?!\d))", "", s)

    reference, candidate = norm(reference), norm(candidate)
    have: dict[str, int] = {}
    for n in NUMBER_RE.findall(candidate.replace(" ", "")):
        have[n] = have.get(n, 0) + 1
    missing = []
    for n in NUMBER_RE.findall(reference):
        if have.get(n, 0) > 0:
            have[n] -= 1
        else:
            missing.append(n)
    return missing


def is_note(text: str) -> bool:
    t = clean(text)
    return bool(re.match(r"^(Note|Notes|Source|Sources)\s*:", t) or (SOURCE_RE.search(t) and len(t) > 40))


def split_note(blocks: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    """Tách các block trong vùng thành (nội dung, note/source, statlink)."""
    content, notes, links = [], [], []
    for b in blocks:
        t = clean(b["text"])
        if STATLINK_RE.search(t):
            links += STATLINK_RE.findall(t)
            rest = one_line(STATLINK_RE.sub("", t).replace("StatLink", ""))
            if len(rest) > 2:
                notes.append(rest)
        elif is_note(t):
            notes.append(one_line(t))
        else:
            content.append(t)
    return content, notes, links


# ----------------------------------------------------------------------------- extract

def skip_reason(page: pymupdf.Page, blocks, ref_pages: set[int], last_page: int) -> str | None:
    pno = page.number + 1
    body = "".join(b["text"] for b in blocks).strip()
    if len(body) < 50:
        if page.get_images():
            return "chỉ có ảnh trang trí (bìa / ảnh đầu chương), không có text"
        return "trang trắng hoặc chỉ có tiêu đề sách"
    text = page.get_text()
    if re.search(r"^\s*Table of contents", text, re.M):
        return "mục lục"
    if len(re.findall(r"^(Figure|Table) \d+(?:\.\d+)?\. ", text, re.M)) >= 8 and not STATLINK_RE.search(text):
        return "danh mục hình và bảng (chỉ lặp tiêu đề kèm số trang)"
    if pno == last_page:
        return "bìa sau (đoạn giới thiệu trùng Executive Summary, mã QR)"
    if pno in ref_pages:
        return "danh mục tài liệu tham khảo (không có dữ kiện để hỏi đáp)"
    return None


def extract(_args=None) -> None:
    doc = open_pdf()
    headings = locate_headings(doc)
    ref_pages = references_pages(doc, headings)
    records: list[dict[str, Any]] = []
    skipped_pages: list[dict[str, Any]] = []
    decorative: list[dict[str, Any]] = []
    warnings: list[str] = []
    open_table: dict[str, Any] | None = None   # bảng còn tiếp sang trang sau

    for page in doc:
        pno = page.number + 1
        blocks = body_blocks(page)
        h_here = [h for h in headings if h["page"] == pno and h["located"]]
        reason = skip_reason(page, blocks, ref_pages, doc.page_count)
        if reason:
            skipped_pages.append({"page": pno, "printed_page": printed(pno), "reason": reason})
            open_table = None  # bảng cuối chương kết thúc ngay trước trang tham khảo / ảnh chương
            for img in raster_images(page):
                decorative.append(image_note(pno, img))
            continue

        heading_ys = [h["y"] for h in h_here if h["y"] > HEADER_Y + 1]
        regions: list[dict[str, Any]] = []

        if pno in EXTRA_TABLES:
            regions.append({"kind": "table", "object_id": "Basic statistics", "title": EXTRA_TABLES[pno],
                            "y0": HEADER_Y, "y1": FOOTER_Y, "closed": True, "marker": "manual", "cont": 0})

        # Phần tiếp của bảng từ trang trước: từ đầu trang tới marker đầu tiên.
        if open_table:
            first = blocks[0] if blocks else None
            starts_new = (first is None or is_caption(first) or is_body_paragraph(first)
                          or any(abs(y - first["rect"].y0) < 4 for y in heading_ys))
            if starts_new:
                open_table = None
            else:
                y1, closed, marker = find_end(blocks, HEADER_Y - 1, heading_ys, "table")
                cont = open_table["cont"] + 1
                regions.append({**open_table, "y0": HEADER_Y, "y1": y1, "closed": closed, "marker": marker,
                                "cont": cont})
                if cont > MAX_TABLE_CONT_PAGES:
                    warnings.append(f"{open_table['object_id']}: kéo dài hơn {MAX_TABLE_CONT_PAGES} trang, kiểm tra lại")
                open_table = {**open_table, "cont": cont} if not closed else None

        for b in blocks:
            m = is_caption(b)
            if not m:
                continue
            kind = m.group(1).lower()
            y1, closed, marker = find_end(blocks, b["rect"].y0, heading_ys, kind)
            region = {"kind": kind, "object_id": f"{m.group(1)} {m.group(2)}", "title": one_line(m.group(3)),
                      "y0": b["rect"].y0, "y1": y1, "closed": closed, "marker": marker, "cont": 0}
            regions.append(region)
            if not closed:
                if kind == "table":
                    open_table = region
                else:
                    warnings.append(f"{region['object_id']} (trang {pno}): không thấy StatLink/Source, lấy tới cuối trang")

        images = raster_images(page)
        used_images: set[int] = set()
        region_rects = []
        for r in regions:
            rect = region_rect(page, r["y0"], r["y1"])
            region_rects.append(rect)
            inner = [b for b in blocks if inside(b["rect"], rect)]
            content, notes, links = split_note(inner)
            caption_text = ""
            if r["cont"] == 0 and inner and is_caption(inner[0]):
                caption_text = one_line(inner[0]["text"])
                content = content[1:] if content and is_caption({"text": content[0]}) else content
            sec = section_at(headings, pno, rect.y0)
            name = f"p{pno:03d}_{slug(r['object_id'])}" + (f"_cont{r['cont']}" if r["cont"] else "")
            crop = save_crop(page, rect, name)
            hit_imgs = [i for i, img in enumerate(images) if img["rect"].intersects(rect)
                        and (img["rect"] & rect).get_area() > 0.3 * img["rect"].get_area()]
            used_images.update(hit_imgs)
            rec = {
                "type": r["kind"], "object_id": r["object_id"], "title": r["title"], "caption": caption_text,
                "page": pno, "printed_page": printed(pno), "bbox": [round(v, 1) for v in rect],
                "crop_path": rel(crop), "crop_sha256": sha256_file(crop),
                "continuation": r["cont"], "region_end": r["marker"], "region_closed": r["closed"],
                "chapter": sec["chapter"] if sec else "front_matter", "heading_path": sec["path"] if sec else [],
                "notes": notes, "statlinks": sorted(set(links)),
            }
            if r["kind"] == "table":
                body = [b for b in inner if not is_caption(b) and not STATLINK_RE.search(b["text"])
                        and not is_note(b["text"])]
                crect = pymupdf.Rect(body[0]["rect"]) if body else rect
                for b in body[1:]:
                    crect |= b["rect"]
                rows = row_text(page, crect + (-1, -1, 1, 1))
                md_raw, n_tables, top = table_markdown(page, rect)
                md = compact_markdown(md_raw) if md_raw else None
                # Dòng đơn vị / phụ đề giữa caption và khung bảng (vd. "Per cent changes from previous year")
                subtitle = [one_line(b["text"]) for b in body if top is not None and b["rect"].y1 <= top + 1]
                if md and subtitle:
                    md = "\n".join(subtitle) + "\n" + md
                missing = numbers_missing(rows, md) if md else None
                use_md = bool(md) and not missing
                rec.update({"table_text": md if use_md else rows,
                            "table_format": "markdown" if use_md else "rows",
                            "tables_detected": n_tables, "markdown_missing_numbers": missing,
                            "rows_text": rows, "markdown_raw": md_raw})
            else:
                rec.update({"is_raster": bool(hit_imgs),
                            "raster_pixels": [f"{images[i]['width_px']}x{images[i]['height_px']}" for i in hit_imgs],
                            "text_labels": " | ".join(one_line(c) for c in content) if content else ""})
                if r["kind"] == "figure" and not links:
                    warnings.append(f"{r['object_id']} (trang {pno}): không có StatLink")
            records.append(rec)

        for i, img in enumerate(images):
            if i not in used_images:
                decorative.append(image_note(pno, img))

        # Text: block ngoài mọi vùng, gộp theo heading và MAX_CHARS.
        free = [b for b in blocks if not any(inside(b["rect"], rr) for rr in region_rects)]
        buf: list[dict[str, Any]] = []
        buf_sec = None

        def flush():
            if not buf:
                return
            rect = pymupdf.Rect(buf[0]["rect"])
            for b in buf[1:]:
                rect |= b["rect"]
            text = "\n".join(clean(b["text"]) for b in buf)
            sec = buf_sec
            records.append({"type": "text", "page": pno, "printed_page": printed(pno),
                            "bbox": [round(v, 1) for v in rect], "text": text,
                            "chapter": sec["chapter"] if sec else "front_matter",
                            "heading_path": sec["path"] if sec else []})
            buf.clear()

        for b in free:
            sec = section_at(headings, pno, b["rect"].y0)
            size = sum(len(x["text"]) for x in buf)
            if buf and (sec is not buf_sec or size + len(b["text"]) > MAX_CHARS):
                flush()
            if not buf:
                buf_sec = sec
            buf.append(b)
        flush()

    # Đánh số ổn định cho text chunk theo trang.
    counters: dict[int, int] = {}
    for rec in records:
        if rec["type"] == "text":
            counters[rec["page"]] = counters.get(rec["page"], 0) + 1
            rec["id"] = f"{DOC_ID}:p{rec['page']:03d}:text{counters[rec['page']]:02d}"
        else:
            suffix = f":cont{rec['continuation']}" if rec["continuation"] else ""
            rec["id"] = f"{DOC_ID}:p{rec['page']:03d}:{slug(rec['object_id'])}{suffix}"
    ids = [r["id"] for r in records]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit(f"ID trùng: {sorted(dup)}")
    records.sort(key=lambda r: (r["page"], r["bbox"][1]))

    meta = {"document_id": DOC_ID, "source": SOURCE, "pdf": rel(PDF), "pdf_url": PDF_URL, "pdf_sha256": PDF_SHA256,
            "pages": doc.page_count, "printed_page_offset": PRINTED_OFFSET, "pymupdf": pymupdf.__version__,
            "crop_dpi": CROP_DPI, "max_text_chars": MAX_CHARS,
            "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    write_json(EXTRACTED, {"meta": meta, "records": records, "skipped_pages": skipped_pages,
                           "decorative_images": decorative, "warnings": warnings})
    stats = extraction_stats(meta, records, skipped_pages, decorative, warnings)
    write_json(STATS, stats)
    print_stats(stats)


def image_note(pno: int, img: dict[str, Any]) -> dict[str, Any]:
    """Ảnh không thuộc hình có caption: phân loại để ghi vào thống kê phần không index."""
    r = img["rect"]
    if r.width > 500 and r.height > 400:
        reason = "ảnh bìa / ảnh đầu chương (trang trí, bản quyền Shutterstock)"
    elif img["width_px"] == img["height_px"] and img["width_px"] < 400:
        reason = "mã QR"
    elif img["width_px"] < 200:
        reason = "logo"
    else:
        reason = "ảnh ngoài vùng hình có caption — cần kiểm tra"
    return {"page": pno, "bbox": [round(v, 1) for v in r], "pixels": f"{img['width_px']}x{img['height_px']}",
            "reason": reason}


def references_pages(doc: pymupdf.Document, headings: list[dict[str, Any]]) -> set[int]:
    """Trang danh mục tham khảo: từ mục 'References' tới trước mục cấp 1 kế tiếp."""
    level1 = sorted(h["page"] for h in headings if h["level"] == 1)
    pages: set[int] = set()
    for h in headings:
        if h["title"] == "References":
            nxt = next((p for p in level1 if p > h["page"]), doc.page_count + 1)
            pages.update(range(h["page"], nxt))
    return pages


def extraction_stats(meta, records, skipped_pages, decorative, warnings) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    for r in records:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    figures = [r for r in records if r["type"] == "figure"]
    tables = [r for r in records if r["type"] == "table"]
    indexed_pages = sorted({r["page"] for r in records})
    return {
        **meta,
        "records_by_type": by_type,
        "figures": len(figures),
        "figures_raster": sorted(f"{r['object_id']} (p{r['page']})" for r in figures if r["is_raster"]),
        "tables_objects": len({r["object_id"] for r in tables}),
        "table_pages": len(tables),
        "tables_with_markdown": sum(1 for r in tables if r["table_format"] == "markdown"),
        "tables_text_fallback": sorted(
            f"{r['object_id']} (p{r['page']}): " + ("không nhận diện được bảng" if not r["markdown_raw"]
                                                   else f"markdown thiếu số {r['markdown_missing_numbers'][:6]}")
            for r in tables if r["table_format"] != "markdown"),
        "text_chars": sum(len(r["text"]) for r in records if r["type"] == "text"),
        "indexed_pages": len(indexed_pages),
        "skipped_pages": skipped_pages,
        "decorative_images": decorative,
        "warnings": warnings,
    }


def print_stats(stats: dict[str, Any]) -> None:
    print(f"Trang: {stats['pages']} | có nội dung index: {stats['indexed_pages']} | bỏ qua: {len(stats['skipped_pages'])}")
    print(f"Record theo loại: {stats['records_by_type']}")
    print(f"Hình: {stats['figures']} (raster: {len(stats['figures_raster'])}) | "
          f"bảng: {stats['tables_objects']} ({stats['table_pages']} trang, markdown: {stats['tables_with_markdown']})")
    for t in stats["tables_text_fallback"]:
        print("Bảng dùng text theo hàng:", t)
    print(f"Ảnh trang trí/không dùng: {len(stats['decorative_images'])}")
    for w in stats["warnings"]:
        print("CẢNH BÁO:", w)
    print(f"-> {rel(EXTRACTED)}, {rel(STATS)}, crop trong {rel(CROPS)}/")


# ----------------------------------------------------------------------------- describe

SYSTEM_PROMPT = """You transcribe figures from an OECD economic report so they can be searched and cited.
Describe ONLY what is visible in the image. Do not use outside knowledge. A wrong number is far worse than
a missing number: never estimate values from gridlines or bar/line heights.
Write in English, plain text, using exactly these sections:
TYPE: chart type(s); number of panels and each panel's title exactly as printed.
AXES AND UNITS: for each panel, what the x-axis and y-axis show, units, and the first and last printed tick
labels; secondary axis if any.
LEGEND: every series / category name as printed and how it is drawn (colour, line, bar, marker).
Only mention markers if they are clearly drawn.
HIGHLIGHTS: elements emphasised visually (e.g. one country in a different colour, boxes, arrows, annotations).
PRINTED VALUES: a markdown table per panel containing ONLY numbers that are printed as text inside the plot
(data labels on bars, slices or points), copied exactly with their category/year. If a panel has no printed
data labels, write "No printed data labels." Do not add estimated values here.
SHAPE: for each panel without printed values, describe only what is unambiguous:
- direction of the trend over the whole period (rising / falling / flat / mixed);
- abrupt changes: name the two adjacent x-axis labels between which the change happens. Before writing it,
  trace vertically from the change down to the x-axis and check which tick labels it falls between.
  If you cannot tell which interval, say "around <label>" and state that the exact position is unclear;
- ranking of categories (highest, lowest, order) only where the difference is clearly visible;
  if two bars or points look about equal, say they are similar instead of ordering them.
KEY POINTS: 2-5 factual statements supported by printed values or by the SHAPE section above.
"""


def describe(args) -> None:
    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv(ROOT / ".env")
    if not EXTRACTED.exists():
        sys.exit("Chưa có extracted.json: chạy `extract` trước.")
    model = args.model or os.getenv("VISION_MODEL") or "gpt-5-mini"
    effort = os.getenv("VISION_REASONING_EFFORT", "low")
    prices = {k: os.getenv(f"VISION_PRICE_{k.upper()}_PER_M") for k in ("input", "cached_input", "output")}
    prices = {k: float(v) for k, v in prices.items() if v}
    if len(prices) < 3:
        print("Lưu ý: thiếu VISION_PRICE_INPUT/CACHED_INPUT/OUTPUT_PER_M trong .env -> cost_usd = null")

    figures = [r for r in json.loads(EXTRACTED.read_text(encoding="utf-8"))["records"] if r["type"] == "figure"]
    if args.raster_only:
        figures = [f for f in figures if f["is_raster"]]
    if args.ids:
        wanted = {s.strip() for s in args.ids.split(",")}
        figures = [f for f in figures if f["object_id"] in wanted or f["id"] in wanted]
    cache: dict[str, Any] = json.loads(DESCRIPTIONS.read_text(encoding="utf-8")) if DESCRIPTIONS.exists() else {}
    client = OpenAI(base_url=os.getenv("LLM_BASE_URL") or None, timeout=180, max_retries=0)

    todo = [f for f in figures if args.force or not (
        f["id"] in cache and cache[f["id"]].get("crop_sha256") == f["crop_sha256"]
        and cache[f["id"]].get("model") == model and cache[f["id"]].get("prompt_version") == PROMPT_VERSION
        and cache[f["id"]].get("description"))]
    if args.limit:
        todo = todo[: args.limit]
    print(f"Model {model} | {len(figures)} hình được chọn, {len(todo)} cần gọi API")

    total_cost, errors = 0.0, 0
    for n, fig in enumerate(todo, 1):
        img_b64 = base64.b64encode((ROOT / fig["crop_path"]).read_bytes()).decode()
        context = (f"{fig['caption'] or fig['object_id'] + '. ' + fig['title']}\n"
                   f"Notes printed under the figure: {' '.join(fig['notes']) or '(none)'}")
        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Caption and notes printed with this figure (from the PDF text):\n"
                                                 + context},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}",
                                                            "detail": "high"}}]}]
        entry: dict[str, Any] = {"figure": fig["object_id"], "page": fig["page"], "crop_sha256": fig["crop_sha256"],
                                 "model": model, "reasoning_effort": effort, "prompt_version": PROMPT_VERSION}
        for attempt in range(3):
            t0 = time.perf_counter()
            try:
                kwargs = {"model": model, "messages": messages, "max_completion_tokens": 8000}
                if effort:
                    kwargs["reasoning_effort"] = effort
                resp = client.chat.completions.create(**kwargs)
                choice = resp.choices[0]
                u = resp.usage
                cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
                reasoning = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
                cost = None
                if len(prices) == 3:
                    cost = ((u.prompt_tokens - cached) * prices["input"] + cached * prices["cached_input"]
                            + u.completion_tokens * prices["output"]) / 1e6
                    total_cost += cost
                text = (choice.message.content or "").strip()
                entry.update({"description": text if choice.finish_reason == "stop" else None,
                              "finish_reason": choice.finish_reason, "error": None,
                              "usage": {"prompt_tokens": u.prompt_tokens, "cached_tokens": cached,
                                        "completion_tokens": u.completion_tokens, "reasoning_tokens": reasoning},
                              "cost_usd": cost, "latency_s": round(time.perf_counter() - t0, 2),
                              "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              "verified": False})
                if choice.finish_reason != "stop":
                    entry["error"] = f"finish_reason={choice.finish_reason}"
                break
            except Exception as exc:  # noqa: BLE001 - ghi lỗi, thử lại, không bịa mô tả
                entry.update({"description": None, "error": f"{type(exc).__name__}: {exc}"})
                time.sleep(2 * (attempt + 1))
        if entry.get("error"):
            errors += 1
        cache[fig["id"]] = entry
        write_json(DESCRIPTIONS, cache)  # ghi sau mỗi hình để dừng giữa chừng không mất kết quả
        status = "LỖI " + entry["error"] if entry.get("error") else f"{entry['latency_s']}s"
        print(f"[{n}/{len(todo)}] {fig['object_id']} p{fig['page']}: {status}")
    print(f"Xong. Lỗi: {errors} | chi phí lần chạy này: "
          + (f"${total_cost:.4f}" if len(prices) == 3 else "không tính (thiếu đơn giá)") + f" -> {rel(DESCRIPTIONS)}")


# ----------------------------------------------------------------------------- chartdata

CHART_DATA = DATA / "chart_data.json"
CHART_METHOD = "đọc từ toạ độ PDF"
CHART_METHOD_EN = ("read from PDF vector coordinates: bar/line geometry mapped onto the printed axis tick labels; "
                   "these numbers are NOT printed in the report")


def parse_num(s: str) -> float | None:
    s = s.strip().replace("−", "-").replace("–", "-").replace(",", "").rstrip("%")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return None
    return float(s)


def decimals(s: str) -> int:
    s = s.strip().rstrip("%")
    return len(s.split(".")[1]) if "." in s else 0


def hex_color(c) -> str | None:
    return None if c is None else "#" + "".join(f"{round(v * 255):02x}" for v in c[:3])


def is_whiteish(c) -> bool:
    return c is not None and min(c) > 0.93


def is_greyish(c) -> bool:
    return c is not None and max(c) - min(c) < 0.06


def subpaths(drawing: dict) -> list[tuple[str, Any]]:
    """Tách một drawing thành các hình con: ("rect", Rect) hoặc ("poly", [Point,...])."""
    out: list[tuple[str, Any]] = []
    cur: list[pymupdf.Point] = []
    last = None
    for it in drawing["items"]:
        op = it[0]
        if op == "re":
            out.append(("rect", pymupdf.Rect(it[1])))
            last = None
            continue
        if op == "qu":
            out.append(("rect", it[1].rect))
            last = None
            continue
        start, end = pymupdf.Point(it[1]), pymupdf.Point(it[-1])
        if last is None or abs(start.x - last.x) > 0.05 or abs(start.y - last.y) > 0.05:
            if cur:
                out.append(("poly", cur))
            cur = [start]
        cur.append(end)
        last = end
    if cur:
        out.append(("poly", cur))
    # polyline khép kín, song song trục, 4-5 điểm -> hình chữ nhật (Excel vẽ cột bằng 4 đoạn thẳng)
    fixed = []
    for kind, g in out:
        if kind == "poly" and 4 <= len(g) <= 5:
            xs, ys = {round(p.x, 1) for p in g}, {round(p.y, 1) for p in g}
            if len(xs) == 2 and len(ys) == 2:
                fixed.append(("rect", pymupdf.Rect(min(xs), min(ys), max(xs), max(ys))))
                continue
        fixed.append((kind, g))
    return fixed


def phrases(words: list[tuple]) -> list[dict[str, Any]]:
    """Gộp các từ liền nhau trên cùng một dòng thành cụm (nhãn danh mục, tên series...)."""
    words = sorted(words, key=lambda w: (w[5], w[6], w[7]))  # thứ tự từ của PDF (đúng cả với chữ xoay)
    out: list[dict[str, Any]] = []
    for w in words:
        r = pymupdf.Rect(w[:4])
        both_numeric = parse_num(w[4]) is not None and parse_num(out[-1]["text"].split()[-1]) is not None if out else False
        vertical = r.height > r.width * 1.5 and len(w[4]) > 1  # chữ xoay dọc: các từ chồng theo y, không theo x
        same_line = out and out[-1]["key"] == (w[5], w[6])
        if same_line and vertical and out[-1]["vertical"] and abs(r.x0 - out[-1]["rect"].x0) < 2 and not both_numeric:
            out[-1]["text"] += " " + w[4]
            out[-1]["rect"] |= r
        elif same_line and 0 <= r.x0 - out[-1]["rect"].x1 < 4.5 and not both_numeric:
            out[-1]["text"] += " " + w[4]
            out[-1]["rect"] |= r
        else:
            out.append({"key": (w[5], w[6]), "order": (w[5], w[6], w[7]), "text": w[4], "rect": r,
                        "vertical": vertical})
    return out


def find_axes(words: list[tuple]) -> list[dict[str, Any]]:
    """Trục y: >= 3 nhãn số thẳng hàng theo mép phải (hoặc trái), giá trị tuyến tính theo y."""
    nums = [(w, parse_num(w[4])) for w in words]
    nums = [(w, v) for w, v in nums if v is not None and (w[3] - w[1]) < 14 and (w[2] - w[0]) < 40]
    groups: list[list[tuple]] = []
    for edge in (2, 0):  # căn phải (trục trái) rồi căn trái (trục phải)
        nums.sort(key=lambda t: t[0][edge])
        cluster: list[tuple] = []
        for t in nums:
            if cluster and abs(t[0][edge] - cluster[-1][0][edge]) > 1.5:
                groups.append(cluster)
                cluster = []
            cluster.append(t)
        if cluster:
            groups.append(cluster)
    axes, seen = [], set()
    for g in groups:
        g.sort(key=lambda t: (t[0][1] + t[0][3]) / 2)
        # tách theo khoảng trống lớn (hai panel chồng dọc dùng chung cột x)
        runs, cur = [], [g[0]]
        for prev, t in zip(g, g[1:]):
            if (t[0][1] - prev[0][3]) > 30:
                runs.append(cur)
                cur = []
            cur.append(t)
        runs.append(cur)
        for run in runs:
            if len(run) < 3:
                continue
            key = frozenset((round(t[0][0], 1), round(t[0][1], 1)) for t in run)
            if key in seen:
                continue
            ys = [(t[0][1] + t[0][3]) / 2 for t in run]
            vs = [t[1] for t in run]
            if len(set(vs)) < 3:
                continue
            a, b, r2 = linfit(ys, vs)
            if a >= 0 or r2 < 0.9999:  # giá trị phải tăng lên phía trên và tuyến tính (loại trục log, nhãn năm)
                continue
            seen.add(key)
            axes.append({"words": [t[0] for t in run], "values": vs, "ys": ys,
                         "x0": min(t[0][0] for t in run), "x1": max(t[0][2] for t in run),
                         "top": min(ys), "bottom": max(ys),
                         "decimals": max(decimals(t[0][4]) for t in run),
                         "unit_pct": any(t[0][4].strip().endswith("%") for t in run)})
    # Một trục có thể được nhận hai lần (căn phải và căn trái, mỗi lần một tập nhãn con): giữ bản nhiều nhãn nhất.
    axes.sort(key=lambda a: -len(a["words"]))
    kept: list[dict[str, Any]] = []
    for ax in axes:
        ids = {tuple(w[:4]) for w in ax["words"]}
        if any(len(ids & {tuple(w[:4]) for w in k["words"]}) >= 2 for k in kept):
            continue
        kept.append(ax)
    return kept


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return 0.0, my, 0.0
    a = sxy / sxx
    b = my - a * mx
    ss_tot = sum((y - my) ** 2 for y in ys)
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    return a, b, (1 - ss_res / ss_tot) if ss_tot else 0.0


def snap_ticks(axis: dict, hlines: list[float]) -> None:
    """Dùng y của đường lưới/trục ngay cạnh nhãn (chính xác hơn tâm chữ) nếu mọi nhãn đều khớp."""
    snapped = []
    for y in axis["ys"]:
        near = [h for h in hlines if abs(h - y) <= 4]
        if not near:
            break
        snapped.append(min(near, key=lambda h: abs(h - y)))
    if len(snapped) == len(axis["ys"]):
        axis["ys_used"], axis["snapped"] = snapped, True
    else:
        axis["ys_used"], axis["snapped"] = axis["ys"], False
    axis["a"], axis["b"], axis["r2"] = linfit(axis["ys_used"], axis["values"])


def chart_from_figure(page: pymupdf.Page, rec: dict[str, Any]) -> dict[str, Any]:
    region = pymupdf.Rect(rec["bbox"])
    blocks = [b for b in body_blocks(page) if inside(b["rect"], region)]
    top = max([b["rect"].y1 for b in blocks if is_caption(b)] or [region.y0])
    stops = [b["rect"].y0 for b in blocks if b["rect"].y0 > top and (is_note(b["text"]) or STATLINK_RE.search(b["text"]))]
    plot = pymupdf.Rect(region.x0, top + 1, region.x1, min(stops) - 1 if stops else region.y1)
    words = [w for w in page.get_text("words", clip=plot) if w[4].strip()]
    # Đường ngang/dọc có bbox cao/rộng 0 -> Rect.intersects() luôn False; nới 1pt để không mất đường lưới, chú giải.
    drawings = [d for d in page.get_drawings() if (d["rect"] + (-1, -1, 1, 1)).intersects(plot)]

    shapes = []  # (kind, geom, fill, stroke)
    hlines: list[float] = []
    for d in drawings:
        for kind, g in subpaths(d):
            if kind == "poly":
                if len(g) >= 2 and all(abs(p.y - g[0].y) < 0.3 for p in g):
                    hlines.append(g[0].y)
                if not (plot.contains(g[0]) or plot.contains(g[-1])):
                    continue
            elif not (g + (-1, -1, 1, 1)).intersects(plot):
                continue
            if kind == "rect" and g.height < 0.6 and d.get("color") is None and d.get("fill") is not None:
                hlines.append((g.y0 + g.y1) / 2)  # đường lưới vẽ bằng hình chữ nhật rất mỏng
            shapes.append((kind, g, d.get("fill") if d["type"] in ("f", "fs") else None,
                           d.get("color") if d["type"] in ("s", "fs") else None, d.get("width") or 0))

    axes = find_axes(words)
    if not axes:
        return {"status": "unsupported", "reason": "không tìm thấy trục y dạng số tuyến tính (cột ngang, scatter, "
                                                    "trục log hoặc không có nhãn trục)", "panels": []}
    for ax in axes:
        snap_ticks(ax, hlines)
    axes.sort(key=lambda a: (round(a["top"] / 40), a["x0"]))
    axis_wordset = {tuple(w[:5]) for ax in axes for w in ax["words"]}

    panels = []
    for i, ax in enumerate(axes):
        band = [o for o in axes if o is not ax and not (o["bottom"] < ax["top"] - 5 or o["top"] > ax["bottom"] + 5)]
        right = [o["x0"] for o in band if o["x0"] > ax["x1"] + 5]
        x_end = min(right) - 2 if right else plot.x1
        step = abs((ax["values"][-1] - ax["values"][0]) / (ax["ys"][-1] - ax["ys"][0])) if ax["ys"][-1] != ax["ys"][0] else 0
        spacing = (ax["bottom"] - ax["top"]) / max(len(ax["ys"]) - 1, 1)
        area = pymupdf.Rect(ax["x1"] + 1, ax["top"] - spacing * 0.6, x_end, ax["bottom"] + 2)
        val = lambda y, a=ax: a["a"] * y + a["b"]  # noqa: E731
        y_of = lambda v, a=ax: (v - a["b"]) / a["a"]  # noqa: E731
        vmin, vmax = min(ax["values"]), max(ax["values"])
        base_v = 0.0 if vmin <= 0 <= vmax else vmin
        base_y = y_of(base_v)
        panel: dict[str, Any] = {"axis": {"ticks": [w[4] for w in ax["words"]], "snapped_to_gridlines": ax["snapped"],
                                          "r2": round(ax["r2"], 6), "pt_resolution": round(abs(ax["a"]) * 0.5, 4)},
                                 "series": [], "notes": []}
        # Trục phụ bên phải: một trục khác trong cùng dải nằm sát mép phải và không có hình nào bên phải nó.
        if right:
            nxt = min((o for o in band if o["x0"] > ax["x1"] + 5), key=lambda o: o["x0"])
            has_right_shapes = any((k == "rect" and g.x0 > nxt["x1"]) or (k == "poly" and g[0].x > nxt["x1"])
                                   for k, g, *_ in shapes if (k == "rect" and ax["top"] - 5 < g.y1 < ax["bottom"] + 5)
                                   or (k == "poly" and ax["top"] - 5 < g[0].y < ax["bottom"] + 5))
            if not has_right_shapes:
                panels.append({**panel, "status": "unsupported",
                               "reason": "biểu đồ hai trục y (không xác định series nào thuộc trục nào)"})
                continue
        # Nhãn trục x: cụm chữ ngay dưới vùng vẽ, lan xuống các dòng liền kề.
        below = [w for w in words if tuple(w[:5]) not in axis_wordset and area.x0 - 8 <= (w[0] + w[2]) / 2 <= area.x1 + 8
                 and w[1] > ax["bottom"] - 4]
        below.sort(key=lambda w: w[1])
        label_words, y_lim = [], ax["bottom"] + 16
        for w in below:
            if w[1] <= y_lim:
                label_words.append(w)
                y_lim = max(y_lim, w[3] + 3)
        cats = cluster_labels(phrases(label_words))
        texts = [c["text"] for c in cats]
        if len(set(texts)) < len(texts):
            # Trục x nhiều cấp (vd. Figure 1.15: quốc gia × 2000/2023/2050): nhãn lặp -> không gán được giá trị.
            panels.append({**panel, "status": "unsupported", "title": "",
                           "reason": "trục x nhiều cấp (nhãn lặp lại, vd. quốc gia × năm)"})
            continue

        # Tiêu đề panel: cụm chữ phía trên tick cao nhất.
        title_ph = [p for p in phrases([w for w in words if tuple(w[:5]) not in axis_wordset])
                    if p["rect"].y1 <= ax["top"] - 2 and p["rect"].y0 >= ax["top"] - 45
                    and p["rect"].x1 > area.x0 - 30 and p["rect"].x0 < area.x1]
        panel["title"] = " ".join(p["text"] for p in sorted(title_ph, key=lambda p: (round(p["rect"].y0), p["rect"].x0)))

        # Chú giải: chỉ trong phạm vi panel này (Figure 1.1: đường đen panel B từng lấy nhầm tên "Indonesia" của panel A)
        zone = pymupdf.Rect(area.x0 - 40, ax["top"] - 50, area.x1 + 10, ax["bottom"] + 45)
        legend_ph = [p for p in phrases([w for w in words if tuple(w[:5]) not in axis_wordset])
                     if zone.contains(p["rect"].tl) and p["rect"].y1 <= zone.y1]
        legend_shapes = [s for s in shapes
                         if (s[0] == "rect" and zone.contains(s[1].tl)) or (s[0] == "poly" and zone.contains(s[1][0]))]

        # Trục phụ khai báo bằng chữ ("(rhs)", "right axis", "right scale") trong vùng panel: series của trục phải
        # sẽ bị quy đổi sai theo trục trái -> bỏ, không đoán.
        panel_text = " ".join(w[4] for w in words if area.x0 - 30 <= (w[0] + w[2]) / 2 <= area.x1 + 30
                              and ax["top"] - 45 <= w[1] <= ax["bottom"] + 5).lower()
        if re.search(r"\brhs\b|right[- ]hand|right axis|right scale", panel_text):
            panels.append({**panel, "status": "unsupported", "title": panel.get("title", ""),
                           "reason": "biểu đồ hai trục y (chữ 'rhs'/'right axis' trong panel)"})
            continue

        # ---- cột
        rects = [(g, fill) for k, g, fill, stroke, _ in shapes if k == "rect" and fill is not None
                 and not is_whiteish(fill) and g.width < area.width * 0.5 and g.height >= 0.3
                 and area.x0 - 1 <= (g.x0 + g.x1) / 2 <= area.x1 + 1]
        bars = [(g, f) for g, f in rects if abs(g.y1 - base_y) < 1.5 or abs(g.y0 - base_y) < 1.5]
        floating = [(g, f) for g, f in rects if (g, f) not in bars and g.width > 3 and g.height > 3
                    and area.y0 <= g.y0 and g.y1 <= area.y1 + 1 and not (g.width < 12 and g.height < 12)]
        if bars and floating and any(abs((g.x0 + g.x1) / 2 - (b.x0 + b.x1) / 2) < 1 for g, _ in floating for b, _ in bars):
            panel["notes"].append("cột chồng (stacked): chưa hỗ trợ, bỏ phần cột")
            bars = []
        by_color: dict[str, list] = {}
        for g, f in bars:
            by_color.setdefault(hex_color(f), []).append(g)
        # Cột tô màu riêng để làm nổi bật (vd. Viet Nam đỏ, OECD xanh lá trong biểu đồ xếp hạng): gộp vào series
        # chính nếu không trùng vị trí x, để bảng không tách Viet Nam ra khỏi thứ hạng.
        highlighted: dict[float, str] = {}
        if len(by_color) > 1:
            main = max(by_color, key=lambda k: len(by_color[k]))
            main_x = [(g.x0 + g.x1) / 2 for g in by_color[main]]
            gap = min((b - a for a, b in zip(sorted(main_x), sorted(main_x)[1:])), default=10)
            for color in [k for k in by_color if k != main and len(by_color[k]) <= 2
                          and len(by_color[main]) >= 4]:
                xs = [(g.x0 + g.x1) / 2 for g in by_color[color]]
                if all(min(abs(x - m) for m in main_x) > gap * 0.4 for x in xs):
                    for g in by_color.pop(color):
                        by_color[main].append(g)
                        highlighted[round((g.x0 + g.x1) / 2, 1)] = color
        for color, gs in by_color.items():
            fill = next(f for g, f in bars if hex_color(f) == color)
            pts = []
            for g in gs:
                top_y = g.y0 if abs(g.y1 - base_y) < 1.5 else g.y1
                pts.append(((g.x0 + g.x1) / 2, val(top_y)))
            s = make_series("bar", color, pts, cats, legend_name(legend_ph, legend_shapes, fill, "bar"), ax["decimals"])
            hl = [(x, c) for x, c in highlighted.items() if any(abs(x - (g.x0 + g.x1) / 2) < 0.2 for g in gs)]
            if hl:
                near = {min(cats, key=lambda c: abs(c["xc"] - x))["text"]: c for x, c in hl} if cats else {}
                s["highlighted"] = [{"x": k, "color": v} for k, v in near.items()]
            if s["points"] >= 2 or s["values"]:  # bỏ hình chữ nhật lẻ không gắn được nhãn nào (ô chú giải, khung)
                panel["series"].append(s)

        # ---- đường
        for k, g, fill, stroke, width in shapes:
            if k != "poly" or stroke is None or fill is not None or len(g) < 3:
                continue
            xs = [p.x for p in g]
            if max(xs) - min(xs) < 25:
                continue
            if all(abs(p.y - g[0].y) < 0.3 for p in g) and is_greyish(stroke):
                continue  # đường lưới / trục (xám, đen); đường ngang có màu là dữ liệu (vd. ngưỡng thu nhập cao)
            if all(abs(p.x - g[0].x) < 0.3 for p in g):
                continue
            inside_pts = [p for p in g if area.x0 - 2 <= p.x <= area.x1 + 2 and area.y0 - 2 <= p.y <= area.y1 + 2]
            if len(inside_pts) < 0.8 * len(g):
                continue
            pts = [(p.x, val(p.y)) for p in g]
            panel["series"].append(make_series("line", hex_color(stroke), pts, cats,
                                               legend_name(legend_ph, legend_shapes, stroke, "line"), ax["decimals"]))

        if any(re.search(r"\brhs\b|right", (s["name"] or "").lower()) for s in panel["series"]):
            panel["series"] = []
            panel["notes"].append("chú giải ghi series thuộc trục phải (rhs)")
        panel["status"] = "ok" if panel["series"] else "unsupported"
        if not panel["series"]:
            panel["reason"] = "; ".join(panel["notes"]) or "không nhận được cột/đường nào gắn với trục này"
        panel["x_labels"] = [c["text"] for c in cats]
        panels.append(panel)

    ok = [p for p in panels if p["status"] == "ok"]
    return {"status": "ok" if ok else "unsupported", "panels": panels,
            "reason": None if ok else "; ".join(sorted({p.get("reason") or "" for p in panels}))}


def cluster_labels(ph: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Gộp các cụm chữ chồng nhau theo phương ngang thành một nhãn danh mục (nhãn nhiều dòng)."""
    ph = sorted(ph, key=lambda p: p["rect"].x0)
    cats: list[dict[str, Any]] = []
    for p in ph:
        r = p["rect"]
        for c in cats:
            if min(r.x1, c["x1"]) - max(r.x0, c["x0"]) > 1:
                c["parts"].append(p)
                c["x0"], c["x1"] = min(c["x0"], r.x0), max(c["x1"], r.x1)
                break
        else:
            cats.append({"x0": r.x0, "x1": r.x1, "parts": [p]})
    for c in cats:
        # thứ tự đọc PDF (block, line, word) đúng cả với nhãn xoay dọc nhiều dòng (Figure 2.6)
        c["parts"].sort(key=lambda p: p.get("order", (0, 0, 0)))
        c["text"] = " ".join(p["text"] for p in c["parts"])
        c["xc"] = (c["x0"] + c["x1"]) / 2
    return sorted(cats, key=lambda c: c["xc"])


def legend_name(legend_ph, shapes, color, kind: str) -> str | None:
    """Tên series: mẫu chú giải cùng màu (ô vuông nhỏ hoặc đoạn ngang ngắn) + cụm chữ ngay bên phải."""
    target = hex_color(color)
    for k, g, fill, stroke, _ in shapes:
        if kind == "bar" and k == "rect" and fill is not None and hex_color(fill) == target \
                and g.width <= 12 and g.height <= 12:
            sw = g
        elif kind == "line" and k == "poly" and stroke is not None and hex_color(stroke) == target \
                and len(g) == 2 and abs(g[0].y - g[1].y) < 0.3 and 5 < abs(g[1].x - g[0].x) < 30:
            sw = pymupdf.Rect(min(g[0].x, g[1].x), g[0].y - 2, max(g[0].x, g[1].x), g[0].y + 2)
        else:
            continue
        cy = (sw.y0 + sw.y1) / 2
        right = [p for p in legend_ph if abs((p["rect"].y0 + p["rect"].y1) / 2 - cy) < 5 and 0 <= p["rect"].x0 - sw.x1 < 25]
        if right:
            return min(right, key=lambda p: p["rect"].x0)["text"]
    return None


def make_series(kind: str, color: str, pts: list[tuple[float, float]], cats, name, dec: int) -> dict[str, Any]:
    """Gắn từng điểm (x, giá trị) vào nhãn trục x gần nhất; điểm không khớp nhãn nào giữ ở dạng tóm tắt."""
    spacing = min((b["xc"] - a["xc"] for a, b in zip(cats, cats[1:])), default=40)
    tol = max(spacing * 0.45, 2)
    nd = dec + 1
    # Trục x là năm (nhãn số cách đều): suy năm của mọi điểm từ toạ độ x, kể cả điểm nằm giữa hai nhãn in.
    year_fit = None
    nums = [(c["xc"], parse_num(c["text"])) for c in cats]
    years = [(x, n) for x, n in nums if n is not None and 1900 <= n <= 2100 and float(n).is_integer()]
    # >= 80% nhãn là năm: bỏ nhãn lạ lẫn vào (vd. tiêu đề trục "y-o-y % change" nằm dưới trục, Figure 1.13)
    if len(years) >= 2 and len(years) >= 0.8 * len(nums):
        a, b, r2 = linfit([x for x, _ in years], [n for _, n in years])
        if r2 > 0.9995 and a > 0:
            year_fit = (a, b)
            cats = [c for c in cats if any(abs(c["xc"] - x) < 0.01 for x, _ in years)]
    values: dict[str, float] = {}
    conflicts = 0
    if not year_fit and cats:
        # Nhãn chữ (danh mục, "Jan-13"): mỗi nhãn lấy điểm GẦN tâm nhãn nhất (series dày, nhiều điểm trong dung sai).
        best: dict[str, tuple[float, float]] = {}
        for x, v in pts:
            c = min(cats, key=lambda c: abs(c["xc"] - x))
            d = abs(c["xc"] - x)
            if d <= tol and (c["text"] not in best or d < best[c["text"]][0]):
                best[c["text"]] = (d, v)
        values = {k: round(v, nd) for k, (_, v) in best.items()}
        pts_loop: list[tuple[float, float]] = []
    else:
        pts_loop = sorted(pts)
    for x, v in pts_loop:
        if year_fit:
            yr = year_fit[0] * x + year_fit[1]
            if abs(yr - round(yr)) > 0.15:  # điểm theo tháng/quý: không gán năm, để vào phần tóm tắt
                continue
            if not (min(n for _, n in years) - 1 <= yr <= max(n for _, n in years) + 1):
                continue  # ngoài khoảng nhãn năm (hình lẻ không phải dữ liệu)
            key = str(round(yr))
        else:
            if not cats:
                break
            c = min(cats, key=lambda c: abs(c["xc"] - x))
            if abs(c["xc"] - x) > tol:
                continue
            key = c["text"]
        if key in values and abs(values[key] - v) > 10 ** -nd:
            conflicts += 1
        values.setdefault(key, round(v, nd))
    if year_fit and pts:
        years = [year_fit[0] * x + year_fit[1] for x, _ in pts]
        span = max(years) - min(years) + 1
        if len(pts) > 1.5 * span:  # series theo tháng/quý: điểm trùng vị trí năm chỉ là một tháng, không phải số năm
            values = {}
    keys = sorted(values, key=float) if year_fit else [c["text"] for c in cats if c["text"] in values]
    ordered = [{"x": k, "value": values[k]} for k in keys]
    vs = [v for _, v in pts]
    s = {"type": kind, "name": name, "color": color, "points": len(pts), "values": ordered,
         "matched_to_labels": len(ordered), "x_from_year_axis": bool(year_fit)}
    if len(pts) > len(ordered) * 1.5 or not ordered:
        imax = max(range(len(pts)), key=lambda i: pts[i][1])
        imin = min(range(len(pts)), key=lambda i: pts[i][1])
        if year_fit:
            near = lambda x: f"{year_fit[0] * x + year_fit[1]:.1f}"  # noqa: E731
        else:
            near = lambda x: min(cats, key=lambda c: abs(c["xc"] - x))["text"] if cats else "?"  # noqa: E731
        s["summary"] = {"first": round(pts[0][1], nd), "last": round(pts[-1][1], nd),
                        "max": round(vs[imax], nd), "max_near": near(pts[imax][0]),
                        "min": round(vs[imin], nd), "min_near": near(pts[imin][0])}
    if conflicts:
        s["warning"] = f"{conflicts} điểm trùng nhãn với giá trị khác nhau"
    return s


def chartdata(args) -> None:
    if not EXTRACTED.exists():
        sys.exit("Chưa có extracted.json: chạy `extract` trước.")
    doc = open_pdf()
    figures = [r for r in json.loads(EXTRACTED.read_text(encoding="utf-8"))["records"] if r["type"] == "figure"]
    if getattr(args, "ids", None):
        wanted = {s.strip() for s in args.ids.split(",")}
        figures = [f for f in figures if f["object_id"] in wanted or f["id"] in wanted]
    out = json.loads(CHART_DATA.read_text(encoding="utf-8")) if CHART_DATA.exists() and getattr(args, "ids", None) else {}
    counts = {"ok": 0, "unsupported": 0, "raster": 0}
    for f in figures:
        if f["is_raster"]:
            out[f["id"]] = {"figure": f["object_id"], "page": f["page"], "status": "raster",
                            "reason": "hình raster: không có toạ độ vector, dùng vision"}
            counts["raster"] += 1
            continue
        try:
            res = chart_from_figure(doc[f["page"] - 1], f)
        except Exception as exc:  # noqa: BLE001 - một hình lỗi không làm hỏng cả bước
            res = {"status": "unsupported", "reason": f"lỗi: {type(exc).__name__}: {exc}", "panels": []}
        out[f["id"]] = {"figure": f["object_id"], "page": f["page"], "method": CHART_METHOD, **res}
        counts[res["status"]] += 1
        n_ok = sum(1 for p in res["panels"] if p["status"] == "ok")
        print(f"{f['object_id']:<12} p{f['page']:<4} {res['status']:<12} panels ok {n_ok}/{len(res['panels'])}"
              + (f"  ({res['reason']})" if res["status"] != "ok" else ""))
    write_json(CHART_DATA, out)
    print(f"Xong: {counts} -> {rel(CHART_DATA)}")


def chart_markdown(entry: dict[str, Any]) -> str | None:
    """Bảng số từ toạ độ để gắn vào chunk hình (một bảng mỗi panel, cột = series)."""
    if entry.get("status") != "ok":
        return None
    out = [f"Data {CHART_METHOD_EN} (method: {CHART_METHOD}). Values are approximate; "
           "precision is about half a point on the page (see per-panel resolution)."]
    for i, p in enumerate(entry["panels"], 1):
        if p["status"] != "ok":
            out.append(f"Panel {i}: not extracted ({p.get('reason')}).")
            continue
        out.append(f"Panel {i}{': ' + p['title'] if p.get('title') else ''} "
                   f"(y-axis ticks {p['axis']['ticks'][-1]}..{p['axis']['ticks'][0]}, "
                   f"resolution ±{p['axis']['pt_resolution']})")
        res = p["axis"]["pt_resolution"]
        series = []
        for s in p["series"]:
            vals = [v["value"] for v in s["values"]]
            if len(vals) > 3 and max(vals) - min(vals) <= 2 * res:  # đường hằng (ngưỡng, mức tham chiếu)
                out.append(f"- {s['name'] or s['type'] + ' ' + s['color']}: constant horizontal line at {vals[0]}")
            else:
                series.append(s)
        names = [s["name"] or ("value" if len(series) == 1 else f"{s['type']} colour {s['color']} (legend not matched)")
                 for s in series]
        xs: list[str] = []
        for s in series:
            for v in s["values"]:
                if v["x"] not in xs:
                    xs.append(v["x"])
        if xs:
            out.append("| x | " + " | ".join(names) + " |")
            out.append("|---|" + "---|" * len(names))
            for x in xs:
                row = [next((str(v["value"]) for v in s["values"] if v["x"] == x), "") for s in series]
                out.append(f"| {x} | " + " | ".join(row) + " |")
        for s, n in zip(series, names):
            if s.get("highlighted"):
                out.append(f"- {n}: bars drawn in a different colour (highlighted): "
                           + ", ".join(f"{h['x']} ({h['color']})" for h in s["highlighted"]))
            if "summary" in s:
                m = s["summary"]
                out.append(f"- {n}: {s['points']} points; first {m['first']}, last {m['last']}, "
                           f"max {m['max']} near {m['max_near']}, min {m['min']} near {m['min_near']}")
    return "\n".join(out)


# ----------------------------------------------------------------------------- build

def build(_args=None) -> None:
    if not EXTRACTED.exists():
        sys.exit("Chưa có extracted.json: chạy `extract` trước.")
    data = json.loads(EXTRACTED.read_text(encoding="utf-8"))
    desc = json.loads(DESCRIPTIONS.read_text(encoding="utf-8")) if DESCRIPTIONS.exists() else {}
    cdata = json.loads(CHART_DATA.read_text(encoding="utf-8")) if CHART_DATA.exists() else {}
    chunks, missing = [], []
    for r in data["records"]:
        where = f"(PDF page {r['page']}, printed page {r['printed_page']})"
        heading = " > ".join(r["heading_path"])
        meta = {"type": r["type"], "section": r["chapter"], "heading": heading, "printed_page": r["printed_page"],
                "bbox": r["bbox"]}
        if r["type"] == "text":
            text = f"[{heading}]\n{r['text']}" if heading else r["text"]
        else:
            title = r["caption"] or (f"{r['object_id']}. {r['title']}"
                                     + (" (continued)" if r["continuation"] else ""))
            parts = [f"{title} {where}"]
            meta.update({"object_id": r["object_id"], "crop_path": r["crop_path"], "statlinks": r["statlinks"],
                         "continuation": r["continuation"]})
            if r["type"] == "table":
                meta["table_format"] = r["table_format"]
                intro = ("Table rows as laid out on the page (cells separated by ' | '):\n"
                         if r["table_format"] == "rows" else "")
                pieces = split_table(r["table_text"], TABLE_PART_CHARS)
                notes = "\n".join(r["notes"])
                for i, piece in enumerate(pieces, 1):
                    label = f" [part {i}/{len(pieces)}]" if len(pieces) > 1 else ""
                    body = "\n".join(x for x in (f"{title}{label} {where}", intro + piece, notes) if x)
                    cid = r["id"] + (f":part{i}" if len(pieces) > 1 else "")
                    chunks.append({"id": cid, "text": body, "source_id": DOC_ID, "source": SOURCE,
                                   "page": r["page"], "metadata": {**meta, "part": i, "parts": len(pieces)}})
                continue
            else:
                meta["is_raster"] = r["is_raster"]
                if r["text_labels"]:
                    parts.append("Text labels inside the figure (PDF text layer): " + r["text_labels"])
                d = desc.get(r["id"])
                if d and d.get("description") and d.get("crop_sha256") == r["crop_sha256"]:
                    parts.append(f"Visual description (generated by {d['model']}, prompt {d['prompt_version']}):\n"
                                 + d["description"])
                    meta["description"] = {"model": d["model"], "prompt_version": d["prompt_version"],
                                           "verified": d.get("verified", False)}
                else:
                    missing.append(f"{r['object_id']} (p{r['page']})")
                    meta["description"] = None
                cd = cdata.get(r["id"], {})
                table = chart_markdown(cd)
                if table:
                    parts.append(table)
                meta["chart_data"] = {"method": CHART_METHOD, "status": cd["status"]} if cd else None
            if r["notes"]:
                parts.append("\n".join(r["notes"]))
            text = "\n".join(parts)
        chunks.append({"id": r["id"], "text": text, "source_id": DOC_ID, "source": SOURCE, "page": r["page"],
                       "metadata": meta})
    write_json(CHUNKS, chunks)
    stats = json.loads(STATS.read_text(encoding="utf-8")) if STATS.exists() else {}
    stats["chunks"] = len(chunks)
    stats["figures_without_description"] = missing
    stats["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    write_json(STATS, stats)
    by_type: dict[str, int] = {}
    for c in chunks:
        by_type[c["metadata"]["type"]] = by_type.get(c["metadata"]["type"], 0) + 1
    print(f"{len(chunks)} chunk {by_type} -> {rel(CHUNKS)}")
    if missing:
        print(f"CẢNH BÁO: {len(missing)} hình chưa có mô tả vision: {', '.join(missing[:8])}"
              + (" ..." if len(missing) > 8 else ""))


# ----------------------------------------------------------------------------- CLI

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("extract", help="PDF -> extracted.json + crop (không gọi API)")
    d = sub.add_parser("describe", help="Mô tả hình bằng vision model (có cache)")
    c = sub.add_parser("chartdata", help="Đọc số liệu cột/đường từ toạ độ vector PDF (không gọi API)")
    c.add_argument("--ids", help="Danh sách object_id hoặc chunk id, cách nhau bằng dấu phẩy")
    sub.add_parser("build", help="extracted + chart data + mô tả -> chunks.json")
    a = sub.add_parser("all", help="extract + chartdata + describe + build")
    for p in (d, a):
        p.add_argument("--model", help="Vision model; mặc định VISION_MODEL trong .env hoặc gpt-5-mini")
        p.add_argument("--raster-only", action="store_true", help="Chỉ mô tả 16 hình raster")
        p.add_argument("--ids", help="Danh sách object_id hoặc chunk id, cách nhau bằng dấu phẩy")
        p.add_argument("--limit", type=int, help="Chỉ gọi API cho N hình đầu tiên (thử nghiệm)")
        p.add_argument("--force", action="store_true", help="Bỏ qua cache, gọi lại")
    args = ap.parse_args()
    if args.cmd == "extract":
        extract(args)
    elif args.cmd == "describe":
        describe(args)
    elif args.cmd == "chartdata":
        chartdata(args)
    elif args.cmd == "build":
        build(args)
    else:
        extract(args)
        chartdata(argparse.Namespace(ids=None))
        describe(args)
        build(args)


if __name__ == "__main__":
    main()
