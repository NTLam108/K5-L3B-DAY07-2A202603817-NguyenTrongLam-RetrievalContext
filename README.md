# Day 7 — Agentic RAG

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

## Bài nộp

Học viên: Nguyễn Trọng Lâm · MSSV 2A202603817 · Lớp L3B. Corpus: Sổ tay sinh viên 2025-2026 của Trường ĐH Khoa học tự nhiên, ĐHQG-HCM (trang PDF 61-173), vector store và embedding lấy từ [bài Day 6](https://github.com/NTLam108/K5-L3B-DAY06-NguyenTrongLam-2A202603817-DataIngestion). Thử thách nâng cao: không thực hiện.

| Thành phần | Vị trí |
|---|---|
| Báo cáo cá nhân (kết quả, phân tích lỗi, lý do chọn, kết luận) | [report/individual/2A202603817_NguyenTrongLam.md](report/individual/2A202603817_NguyenTrongLam.md) |
| Cài đặt, dựng lại vector store Day 6, lệnh chạy | [src/README.md](src/README.md) |
| Agent (loop, controller OpenAI tool calling, retriever dense/BM25/Hybrid RRF/Rerank) | [src/agent/](src/agent/), [scripts/](scripts/) |
| Cấu hình đã thử, tiêu chí chọn (công bố trước), cấu hình đã chọn | [configs/](configs/) · [selection_criteria.json](configs/selection_criteria.json) · [selected.json](configs/selected.json) |
| Benchmark: 20 câu có đáp án (từ Day 6) + 4 câu thiếu bằng chứng | [starter/data/day6/](starter/data/day6/), [benchmark/unanswerable.json](benchmark/unanswerable.json) |
| Trace, summary từng lần chạy (dev 7 lần, test 2 lần) và đo retrieval | [starter/results/](starter/results/) |
| Nhãn chấm tay dev/test | [labels/](labels/) |
| Test code (mock, không đo chất lượng) | [tests/](tests/) |

Cấu hình được chốt trên dev ở commit `0876960` trước khi chạy test; kết quả test ở commit `50196e6`. Phần dưới đây là đề bài gốc.

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.
