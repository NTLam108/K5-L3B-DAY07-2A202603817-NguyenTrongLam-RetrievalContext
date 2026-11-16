"""Đối chiếu số liệu "đọc từ toạ độ PDF" (advanced/data/chart_data.json) với dữ liệu gốc StatLink của OECD.

StatLink (https://stat.link/xxxx) là file Excel OECD công bố kèm từng hình. File này CHỈ dùng để đo độ chính xác
của bước chartdata; nó không được đưa vào index hay vào pipeline trả lời.

Với mỗi series đã trích: dò mọi cặp (cột nhãn, cột số) trong file Excel, chọn cột có nhiều nhãn x trùng nhất và sai
số nhỏ nhất, rồi tính sai số tuyệt đối. Kết quả: advanced/data/chartdata_validation.json + bảng tóm tắt in ra màn hình.

  .venv/Scripts/python.exe advanced/validate_chartdata.py            # tải file còn thiếu rồi đối chiếu
  .venv/Scripts/python.exe advanced/validate_chartdata.py --offline  # chỉ dùng file đã tải

Cần: openpyxl.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "advanced" / "data"
CHART_DATA = DATA / "chart_data.json"
EXTRACTED = DATA / "extracted.json"
OUT = DATA / "chartdata_validation.json"
CACHE = ROOT / "advanced" / "source" / "statlink"   # trong .gitignore cùng PDF gốc


def norm_label(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, (dt.date, dt.datetime)):
        return v.strftime("%b-%y").lower()  # Excel lưu ngày; hình in nhãn kiểu "Jan-12"
    if isinstance(v, (int, float)):
        return str(int(v)) if float(v).is_integer() else None
    s = re.sub(r"_x000D_|\s+", " ", str(v)).strip().lower()
    return s or None


def is_label(v: Any) -> bool:
    """Nhãn trục x: chuỗi chữ, hoặc số nguyên trông như năm. Số liệu (22, 11.5...) không phải nhãn."""
    if isinstance(v, (dt.date, dt.datetime)):
        return True
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v).is_integer() and 1900 <= v <= 2100
    return False


SCALES = (1, 100, 0.01, 1000, 0.001)  # Excel có thể lưu phân số trong khi hình vẽ theo % (Figure 3.4)


def download(code: str) -> Path | None:
    path = CACHE / f"{code}.xlsx"
    if path.exists() and path.stat().st_size > 0:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    r = subprocess.run(["curl", "-sSL", "--max-time", "60", "-A", "Mozilla/5.0", "-o", str(tmp),
                        "-w", "%{http_code} %{content_type}", f"https://stat.link/{code}"],
                       capture_output=True, text=True)
    status = r.stdout.strip()
    if r.returncode != 0 or not status.startswith("200") or "spreadsheetml" not in status:
        tmp.unlink(missing_ok=True)
        print(f"  tải {code} lỗi: {status or r.stderr.strip()}")
        return None
    tmp.replace(path)
    time.sleep(0.5)  # lịch sự với máy chủ OECD
    return path


def candidate_columns(path: Path) -> list[dict[str, Any]]:
    """Mọi cột số trong workbook, ghép với cột nhãn gần nhất bên trái: {header, values: {label: number}}."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    cols: list[dict[str, Any]] = []
    for ws in wb.worksheets:
        if ws.title.lower().startswith("about"):
            continue
        grid0 = [list(r) for r in ws.iter_rows(values_only=True)]
        if not grid0:
            continue
        width0 = max(len(r) for r in grid0)
        grid0 = [r + [None] * (width0 - len(r)) for r in grid0]
        # Dữ liệu có thể xếp theo cột hoặc theo hàng (Figure 1.1 panel B: mỗi series một hàng) -> dò cả bản chuyển vị.
        for orient, grid in (("col", grid0), ("row", [list(x) for x in zip(*grid0)])):
            cols.extend(scan_grid(ws.title, orient, grid))
    return cols


def scan_grid(sheet: str, orient: str, grid: list[list[Any]]) -> list[dict[str, Any]]:
    """Mỗi cột số trong grid + cột nhãn gần nhất bên trái -> {header, values: {nhãn: số}}."""
    cols: list[dict[str, Any]] = []
    width = len(grid[0]) if grid else 0
    for c in range(width):
        col = [r[c] for r in grid]
        nums = [i for i, v in enumerate(col) if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if len(nums) < 2:
            continue
        for lc in range(c - 1, -1, -1):  # cột nhãn: gần nhất bên trái, chứa chữ hoặc năm (không phải cột số liệu)
            labels = {i: norm_label(grid[i][lc]) if is_label(grid[i][lc]) else None for i in nums}
            if sum(1 for v in labels.values() if v) >= 0.6 * len(nums):
                break
        else:
            continue
        values = {labels[i]: float(col[i]) for i in nums if labels.get(i)}
        first = min(nums)
        header = next((str(grid[i][c]) for i in range(first - 1, -1, -1) if isinstance(grid[i][c], str)), "")
        cols.append({"sheet": sheet, "col": f"{orient}{c}", "header": re.sub(r"_x000D_|\s+", " ", header).strip(),
                     "values": values})
    return cols


def compare(series: dict[str, Any], cols: list[dict[str, Any]], tol: float) -> dict[str, Any] | None:
    pts = {norm_label(v["x"]): v["value"] for v in series["values"]}
    pts = {k: v for k, v in pts.items() if k}
    best = None
    for col in cols:
        common = [k for k in pts if k in col["values"]]
        if len(common) < max(2, 0.6 * len(pts)):
            continue
        for scale in SCALES:
            errs = [pts[k] - col["values"][k] * scale for k in common]
            mae = statistics.mean(abs(e) for e in errs)
            score = (mae, -len(common))  # sai số nhỏ nhất trong các cột phủ đủ nhãn
            if best is None or score < best[0]:
                best = (score, col, common, errs, scale)
    if best is None:
        return None
    _, col, common, errs, scale = best
    col = {**col, "values": {k: v * scale for k, v in col["values"].items()}, "scale": scale}
    abs_errs = [abs(e) for e in errs]
    worst = max(range(len(common)), key=lambda i: abs_errs[i])
    return {"excel_sheet": col["sheet"], "excel_col": col["col"], "excel_header": col["header"], "scale": col["scale"],
            "compared": len(common), "of_points": len(pts), "mae": round(statistics.mean(abs_errs), 6),
            "max_abs_err": round(abs_errs[worst], 6), "worst_x": common[worst],
            "worst_pair": [pts[common[worst]], round(col["values"][common[worst]], 6)],
            "within_tol": sum(1 for e in abs_errs if e <= tol), "tol": round(tol, 6)}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="Không tải, chỉ dùng file StatLink đã có")
    args = ap.parse_args()

    chart = json.loads(CHART_DATA.read_text(encoding="utf-8"))
    recs = {r["id"]: r for r in json.loads(EXTRACTED.read_text(encoding="utf-8"))["records"]}
    results, rows = [], []
    for fid, entry in chart.items():
        if entry.get("status") != "ok":
            continue
        links = recs[fid]["statlinks"]
        if len(links) != 1:
            print(f"{entry['figure']}: {len(links)} StatLink, bỏ qua")
            continue
        code = links[0].rsplit("/", 1)[-1]
        path = CACHE / f"{code}.xlsx" if args.offline else download(code)
        if not path or not path.exists():
            results.append({"figure": entry["figure"], "statlink": links[0], "error": "không tải được file"})
            continue
        cols = candidate_columns(path)
        for pi, panel in enumerate(entry["panels"], 1):
            if panel["status"] != "ok":
                continue
            ticks = [float(t.replace(",", "").rstrip("%").replace("−", "-")) for t in panel["axis"]["ticks"]]
            span = max(ticks) - min(ticks)
            for s in panel["series"]:
                if not s["values"]:
                    continue
                nd = max((len(str(v["value"]).split(".")[1]) if "." in str(v["value"]) else 0) for v in s["values"])
                tol = panel["axis"]["pt_resolution"] + 0.5 * 10 ** -nd   # ±0,5 pt + làm tròn khi ghi
                cmp = compare(s, cols, tol)
                row = {"figure": entry["figure"], "panel": pi, "series": s["name"] or s["color"], "type": s["type"],
                       "statlink": links[0], "axis_span": span, **(cmp or {"error": "không ghép được cột Excel"})}
                if cmp:
                    row["max_err_pct_of_axis"] = round(100 * cmp["max_abs_err"] / span, 3) if span else None
                results.append(row)
                rows.append(row)

    ok = [r for r in rows if "mae" in r]
    pts = sum(r["compared"] for r in ok)
    within = sum(r["within_tol"] for r in ok)
    summary = {
        "figures_compared": len({r["figure"] for r in ok}),
        "series_compared": len(ok), "series_unmatched": len(rows) - len(ok),
        "points_compared": pts, "points_within_resolution": within,
        "share_within_resolution": round(within / pts, 4) if pts else None,
        "median_max_err_pct_of_axis": round(statistics.median(r["max_err_pct_of_axis"] for r in ok), 3) if ok else None,
        "series_max_err_over_1pct_axis": sorted(f"{r['figure']} p{r['panel']} {r['series']}: "
                                                f"{r['max_err_pct_of_axis']}% ({r['worst_x']}: {r['worst_pair']})"
                                                for r in ok if r["max_err_pct_of_axis"] > 1),
    }
    OUT.write_text(json.dumps({"summary": summary, "series": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'Hình':<12}{'P':>2} {'Series':<34}{'n':>4}{'MAE':>10}{'max':>10}{'%trục':>7}{'≤tol':>6}")
    for r in ok:
        print(f"{r['figure']:<12}{r['panel']:>2} {str(r['series'])[:33]:<34}{r['compared']:>4}{r['mae']:>10.4g}"
              f"{r['max_abs_err']:>10.4g}{r['max_err_pct_of_axis']:>7.2f}{r['within_tol']:>3}/{r['compared']:<3}")
    for r in rows:
        if "error" in r:
            print(f"KHÔNG GHÉP ĐƯỢC: {r['figure']} panel {r['panel']} {r['series']}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"-> {OUT.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
