# Code

Đặt code của bạn tại đây hoặc mở rộng [starter](../starter/README.md). Khung agent chưa kết nối model và vector store thật.

## Môi trường (Windows, Python 3.12)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.15.0 -r requirements.txt   # torch trên PyPI cho Windows là bản CPU
Copy-Item .env.example .env                                                   # không commit .env
$env:PYTHONUTF8 = "1"                                                         # test/starter đọc file không chỉ định encoding
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m scripts.check_env                               # ghi starter/results/env_check.json
```

## Vector store Day 6

- `src/day6/` sao chép `embeddings.py`, `store.py`, `models.py` từ repo Day 6 (commit `8094c36`); chỉ đổi đường dẫn `.env` sang thư mục gốc repo này.
- Embedding `BAAI/bge-m3`, 1024 chiều, chuẩn hóa L2, không tiền tố query/document, chạy CPU, chi phí 0.
- PostgreSQL 16.16 + pgvector 0.8.7, bảng `chunks`, tìm exact theo cosine (`<=>`). Day 7 dùng strategy **A** (fixed 500 ký tự, overlap 50, 363 chunk) — cấu hình Day 6 chọn trên dev.
- Container chạy với compose project `day6_student_starter`. Bật lại từ thư mục `starter/` của repo Day 6:

```powershell
docker compose -p day6_student_starter up -d
```

Chạy `docker compose up -d` không có `-p` sẽ tạo container mới với volume rỗng và trùng cổng 55433.

## Dữ liệu Day 7

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_day6    # -> starter/data/day6/{chunks,questions,cases,prepare_meta}.json
```

## Baseline retrieval (dev)

```powershell
.\.venv\Scripts\python.exe starter/baseline.py --chunks starter/data/day6/chunks.json --questions starter/data/day6/questions.json --split dev --output starter/results/dev-tfidf
.\.venv\Scripts\python.exe -m scripts.eval_dense --split dev --output starter/results/dev-dense
```

Cả hai dùng chung `hit` và `pack_context` của `starter/baseline.py` (top-3, context budget 800 ký tự). Dense tái lập Day 6: top-3 trùng 15/15 câu; Hit@1 10/15 thay vì 9/15 chỉ vì q10 (top-1 `A-p86-003`) được tính hit sau khi sửa evidence p86 ở bước chuẩn bị dữ liệu.

## So sánh phương pháp retrieval (dev, không qua agent)

```powershell
.\.venv\Scripts\python.exe -m scripts.eval_retrieval --split dev --methods dense bm25 bm25_bigram hybrid_rrf hybrid_rrf_bigram rerank_dense rerank_hybrid rerank_hybrid_bigram
```

Query = nguyên văn câu hỏi; top-3, budget 800, cùng `hit`/`pack_context` của starter. Kết quả: `starter/results/retrieval-comparison-dev.{md,json}`. BM25 tự cài (k1=1.5, b=0.75, tách âm tiết, tùy chọn bigram âm tiết); Hybrid RRF k=60, độ sâu 20 mỗi bên; Rerank: `BAAI/bge-reranker-v2-m3` trên 20 candidate (cache ở `RERANKER_CACHE_DIR`, ~2.3 GB).

## Cấu hình thử nghiệm (dev)

`configs/improve_query.json`, `improve_context.json`, `method_hybrid.json`, `method_rerank.json`, `combined.json` — mỗi file ghi thay đổi so với baseline, giả thuyết và lỗi nhắm tới. Tiêu chí chọn công bố trước trong `configs/selection_criteria.json`.

```powershell
.\.venv\Scripts\python.exe -m scripts.run_agent --split dev --config-file configs/combined.json
.\.venv\Scripts\python.exe -m scripts.compare_agent_runs --split dev --runs baseline baseline-dev-run2 improve_query improve_context method_hybrid method_rerank combined
```

Nhãn chấm tay: `labels/dev/<run>.reviews.json` (bản nháp `.reviews.draft.json` cần người làm bài xác nhận).

## Agent

```powershell
.\.venv\Scripts\python.exe -m scripts.run_agent --split dev --config-file configs/baseline.json --ids q01 q10 u02   # smoke
.\.venv\Scripts\python.exe -m scripts.run_agent --split dev --config-file configs/baseline.json                     # toàn bộ dev
```

Cấu hình chốt nằm trong `configs/*.json` (tham số, model, đơn giá, điều kiện dừng, lý do); `summary.json` ghi đường dẫn và sha256 của file. Ghi đè bằng `--top-k`, `--budget`, `--max-searches`, `--no-filter` chỉ để thử nhanh và bắt buộc kèm `--name` mới.

- `src/agent/loop.py`: vòng lặp từ `starter/agentic.py`, thêm action `abstain`, `stop_reason`, event `llm_call`.
- `src/agent/retriever.py`: `DenseRetriever` (bge-m3 + pgvector, strategy A); filter chỉ lấy từ trường `filter` của câu.
- `src/agent/controller.py`: OpenAI Chat Completions + tool calling (`search_documents`, `submit_answer`, `abstain`).
  Lượt đầu ép search; hết lượt search chỉ còn answer/abstain; không gửi `temperature` (GPT-5 là reasoning model);
  lỗi tạm thời thử lại có backoff; citation sai định dạng được nhắc model sửa một lần (không tự sửa thay model).
- Cần `OPENAI_API_KEY`, `LLM_MODEL`, `LLM_REASONING_EFFORT`, `LLM_PRICE_*` trong `.env`.
- Output: `starter/results/agent-<config>-<split>/traces.json` (dùng được cho `starter/agent_metrics.py`) và `summary.json`.
  `auto_scores` chỉ khớp chuỗi evidence; câu trả lời và citation vẫn phải chấm thủ công.

Benchmark: 20 câu có đáp án từ Day 6 (dev 15 / test 5) + 4 câu thiếu bằng chứng tự viết trong [benchmark/unanswerable.json](../benchmark/unanswerable.json) (dev u01–u02 / test u03–u04), mỗi câu ghi `absence_reason` và cách kiểm tra. `cases.json` gộp 24 câu, chỉ có id/split/question/nhãn answerable — không chứa gold.

Xuất chunk strategy A trực tiếp từ pgvector và chuyển `benchmark/questions.json` của Day 6 sang schema Day 7 (`gold_page "p63"` → `page 63`, gộp `alt_evidence`). Kiểm tra bằng `starter/baseline.validate`. Ngoại lệ duy nhất: evidence thay thế p86 của q10 bị cắt giữa hai chunk nên được rút về đoạn con nguyên văn nằm trọn trong `A-p86-003`; lý do ghi trong `EVIDENCE_OVERRIDES` và `prepare_meta.json`.
