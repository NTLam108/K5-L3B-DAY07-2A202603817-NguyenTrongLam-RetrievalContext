# Dữ liệu Day 7 (xuất từ vector store Day 6)

Tạo bằng `python -m scripts.prepare_day6` (xem [src/README.md](../../../src/README.md)); sha256 từng file ghi trong `prepare_meta.json`.

| File | Nội dung |
|---|---|
| `chunks.json` | 363 chunk strategy A (fixed 500 ký tự, overlap 50), xuất trực tiếp từ bảng `chunks` của pgvector Day 6; id, text, nguồn, trang PDF, metadata (section, số trang in) |
| `questions.json` | 20 câu có đáp án từ benchmark Day 6 (dev 15, test 5) theo schema Day 7: `gold` = {source_id, page, evidence}. Có gold — **không đưa vào agent hay retrieval** |
| `cases.json` | 24 câu (thêm 4 câu thiếu bằng chứng từ `benchmark/unanswerable.json`): chỉ id, split, câu hỏi, filter do người hỏi nêu, nhãn answerable — đây là input của agent |
| `prepare_meta.json` | Thông tin lần xuất, quy tắc benchmark Day 6, chunk chứa gold từng câu (chỉ để phân tích lỗi), ngoại lệ evidence q10 |

**Nguồn và quyền sử dụng:** text trong `chunks.json` trích từ *Sổ tay sinh viên năm học 2025-2026*, Trường Đại học Khoa học tự nhiên, ĐHQG-HCM, trang PDF 61-173 — tài liệu trường công bố công khai cho sinh viên tại <https://hcmus.edu.vn/wp-content/uploads/2025/08/STSV2025_ONLINE.pdf>. Tài liệu không ghi giấy phép tái phân phối; các trích đoạn chỉ được đưa vào repo để người chấm kiểm tra benchmark, nhãn và trace của bài lab, không dùng cho mục đích khác. Bản quyền nội dung thuộc nhà trường. PDF gốc không nằm trong repo.
