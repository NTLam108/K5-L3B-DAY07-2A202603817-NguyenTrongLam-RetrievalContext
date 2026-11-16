# Báo cáo Day 7

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: Sổ tay sinh viên năm học 2025-2026, Trường ĐH Khoa học tự nhiên, ĐHQG-HCM ([PDF](https://hcmus.edu.vn/wp-content/uploads/2025/08/STSV2025_ONLINE.pdf)), tài liệu trường công bố công khai cho sinh viên. Corpus là trang PDF 61–173 (quy chế, quy định, chính sách), giống Day 6. 363 chunk của strategy A (fixed 500 ký tự, overlap 50), xuất trực tiếp từ pgvector bằng `python -m scripts.prepare_day6`; trùng khớp 363/363 chunk với `chunks_A.jsonl` của Day 6.
- Vector store, embedding model, phiên bản và số chiều: PostgreSQL 16.16 + pgvector 0.8.7, tìm exact theo cosine; `BAAI/bge-m3` (sentence-transformers 6.3.0, torch 2.15.0+cpu), 1024 chiều, chuẩn hóa L2, không tiền tố query/document, chạy CPU, chi phí 0. Module kết nối sao chép từ repo Day 6 (commit `8094c36`) vào `src/day6/`. Kiểm tra bằng `python -m scripts.check_env`.
- Agent model, cách chạy và phân chia dev/test: OpenAI `gpt-5-nano` (Chat Completions + tool calling, `reasoning_effort=low`); cấu hình chốt trong [configs/baseline.json](../../configs/baseline.json); cách chạy trong [src/README.md](../../src/README.md). Dev 15 câu có đáp án + 2 câu thiếu evidence; test 5 + 2. 20 câu có đáp án lấy từ benchmark Day 6 (q01–q15 dev, q16–q20 test, chia trước khi chạy Day 6; test Day 6 chỉ được chạy sau khi chốt cấu hình, không dùng để chỉnh). 4 câu thiếu evidence tự viết trong [benchmark/unanswerable.json](../../benchmark/unanswerable.json), chia split trước khi chạy Day 7.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: câu có đáp án có `gold` = {source_id, page, evidence}, evidence là chuỗi con nguyên văn nằm trọn trong một chunk (kiểm tra bằng `starter/baseline.validate`). Ngoại lệ: evidence thay thế p86 của q10 bị cắt giữa hai chunk nên được rút về đoạn con nguyên văn nằm trọn trong `A-p86-003`, vẫn đủ hỗ trợ đáp án (lý do ghi trong `EVIDENCE_OVERRIDES`). Câu thiếu evidence được kiểm tra bằng regex trên 363 chunk và toàn bộ 179 trang PDF, có `absence_reason`; u02 có đáp án ở trang 54, ngoài corpus. Chấm theo [BENCHMARK.md](../../BENCHMARK.md).

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline (`configs/baseline.json`) | Dense bge-m3 + pgvector strategy A, top-3, filter chỉ khi người hỏi nêu, không rerank, budget 800 ký tự; agent gpt-5-nano, tối đa 3 lần tìm | Mốc so sánh | dev | 7/15 (47%) | 11/15 (73%) | 7/15 (47%) | 9,6 s/câu (trung vị); $0.0081 / 17 câu |
| Baseline, chạy lại | Như trên, cùng file cấu hình | Đo dao động giữa các lần chạy | dev | 5/15 (33%) | 14/15 (93%) | 6/15 (40%) | 12,0 s/câu; $0.0086 |
| Phương pháp 2: lexical (chỉ đo retrieval) | BM25 tự cài (k1 = 1,5, b = 0,75), tách âm tiết / thêm bigram âm tiết; TF-IDF của starter để đối chiếu | Kiểm tra ảnh hưởng tách từ tiếng Việt | dev | âm tiết 9/15 · bigram 11/15 · TF-IDF 10/15 | 13/15 · 13/15 · 13/15 | 9/15 · 11/15 · 10/15 | ~2 ms/câu; $0 |
| Phương pháp 3: Hybrid RRF (`configs/method_hybrid.json`) | Dense + BM25 bigram, RRF k = 60, top-20 mỗi bên; agent như baseline | Hit@1 retrieval cao hơn → evidence vào được budget 800 | dev | retrieval 13/15 · agent 10/15 | 14/15 · 14/15 | 13/15 · 10/15 | retrieval 99 ms/câu; agent 13,0 s/câu, $0.0057 |
| Phương pháp 4: Rerank (`configs/method_rerank.json`) | Dense top-20 → cross-encoder `BAAI/bge-reranker-v2-m3` (CPU); agent như baseline | Đưa evidence lên hạng 1 | dev | retrieval 13/15 · agent 11/15 | 15/15 · 14/15 | 13/15 · 11/15 | retrieval 5,5 s/câu; agent 27,4 s/câu, $0.0071 |
| Cải thiện 1 (`configs/improve_query.json`) | Baseline + lần tìm đầu dùng nguyên văn câu hỏi, chặn query trùng, prompt v2 (quy tắc viết query) | Sửa Lỗi 2 (query viết lại kém) | dev | 10/15 (67%) | 15/15 (100%) | 10/15 (67%) | 7,4 s/câu; $0.0060 |
| Cải thiện 2 (`configs/improve_context.json`) | Baseline + budget 2000 ký tự, xếp context theo score cosine | Sửa Lỗi 1 (budget loại evidence) | dev | 7/15 (47%) | 11/15 (73%) | 12/15 (80%) | 9,2 s/câu; $0.0078 |
| **Cấu hình đã chọn: `combined`** (`configs/combined.json`) | Rerank dense top-20 + Cải thiện 1 + budget 2000 xếp theo score rerank | Hai lỗi độc lập nên cải thiện cộng dồn | dev | 13/15 (87%) | 15/15 (100%) | 15/15 (100%) | 12,1 s/câu; $0.0057 |
| Cấu hình đã chọn: `combined` | Như trên, không chỉnh thêm (sha256 `824470c1`) | Đánh giá độc lập, chạy một lần sau commit `0876960` | test | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | 9,8 s/câu; $0.0025 / 7 câu |
| Baseline | Như trên (sha256 `9b5cc833`) | Đánh giá độc lập, chạy một lần sau commit `0876960` | test | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | 7,1 s/câu; $0.0028 / 7 câu |
| Dense / Rerank (chỉ đo retrieval) | Nguyên văn câu hỏi, top-3, budget 800 | Báo cáo, không dùng để chọn lại | test | 4/5 · 5/5 | 5/5 · 5/5 | 4/5 · 5/5 | 101 ms · 6,3 s/câu; $0 |

Cách đọc: với dòng agent, Hit@1 và Evidence Hit@3 tính trên kết quả **lần tìm đầu** của agent; Context Evidence Rate tính trên **context cuối** gửi model (có thể gộp nhiều lần tìm). Dòng "chỉ đo retrieval" dùng nguyên văn câu hỏi, không qua agent (`scripts/eval_retrieval.py`, kết quả `starter/results/retrieval-comparison-dev.md`). Cùng corpus 363 chunk, cùng 15 câu dev có đáp án, cùng định nghĩa hit của `starter/baseline.py`. Chi phí $ là tiền API OpenAI cho 17 câu dev; embedding, BM25 và reranker chạy local, $0. Bảng retrieval không dùng filter; agent dùng filter do người hỏi nêu (q11, q12). Mỗi cấu hình agent chỉ đổi một nhóm yếu tố so với baseline, trừ `combined`.

### Chọn cấu hình

Tiêu chí công bố trước khi chạy cấu hình cải thiện: [configs/selection_criteria.json](../../configs/selection_criteria.json). Quyết định: [configs/selected.json](../../configs/selected.json), chỉ dựa trên dev; commit `0876960` ("Chot cau hinh combined tren dev truoc khi chay test") được tạo trước khi chạy test.

| Cấu hình (dev) | Grounded 0 / 1 / 2 · trung bình | Citation hợp lệ | Từ chối đúng | Từ chối nhầm | Sai có citation |
|---|---|---|---|---|---|
| baseline | 8 / 0 / 7 · 0,93 | 8/10 | 2/2 | 5/15 | 3 |
| baseline (chạy lại) | 8 / 1 / 6 · 0,87 | 8/10 | 2/2 | 6/15 | 2 |
| improve_query | 5 / 0 / 10 · 1,33 | 11/12 | 2/2 | 3/15 | 2 |
| improve_context | 3 / 0 / 12 · 1,60 | 16/16 | 2/2 | 2/15 | 1 |
| method_hybrid | 5 / 0 / 10 · 1,33 | 10/12 | 2/2 | 3/15 | 2 |
| method_rerank | 4 / 0 / 11 · 1,47 | 12/12 | 2/2 | 3/15 | 1 |
| **combined** | **0 / 0 / 15 · 2,00** | **16/16** | **2/2** | **0/15** | **0** |

1. **Ràng buộc bắt buộc:** mọi ứng viên đều đạt — không có lỗi hệ thống, từ chối đúng 2/2, tỷ lệ citation hợp lệ không thấp hơn baseline (0,80).
2. **Chỉ số chính (grounded trung bình):** `combined` 2,00, xếp sau là `improve_context` 1,60.
3. **Quy tắc dao động:** hai lần chạy baseline chênh 0,07. `combined` hơn ứng viên thứ hai 0,40 và hơn baseline 1,07 → vượt mức dao động, không cần xét tiêu chí phụ (dù `combined` cũng dẫn đầu mọi tiêu chí phụ: 0 câu sai có citation, Context Evidence 15/15, 0 từ chối nhầm, chi phí thấp nhất).
4. **Đánh đổi:** chậm hơn baseline 2,5 s/câu (reranker ~5,5 s mỗi lần tìm trên CPU, tải model ~2,3 GB một lần), nhưng ít lượt tìm hơn (11/17 câu chỉ cần 1 lần tìm), prompt tokens giảm 30% (41.027 so với 58.410) nên chi phí API giảm 30%.
5. **Rủi ro:** các thay đổi được thiết kế từ lỗi dev và `combined` mới chạy một lần → điểm dev có thể lạc quan; lỗi ranh giới chunk ở q14 vẫn còn. Test là phép kiểm tra độc lập.

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; giải thích rõ. Báo `n/N` và tỷ lệ, ghi đơn vị thời gian/chi phí, so sánh test sau khi chốt. Nêu hai lỗi dev, nguyên nhân, cách thử và lý do chọn cấu hình:

### Phân tích lỗi dev

Nguồn: trace của agent baseline trên 17 câu dev (`starter/results/agent-baseline-dev/traces.json`), lần chạy lại cùng cấu hình (`agent-baseline-dev-run2`) và 5 cấu hình thử nghiệm. Điểm câu trả lời theo nhãn trong `labels/dev/*.reviews.json` (0 = sai/thiếu, 1 = đúng một phần, 2 = đúng và đủ; từ chối câu có đáp án = 0). Baseline: 7/15 câu đạt 2 điểm, **3 câu trả lời sai nhưng có citation** (q05, q07, q11) và **5 câu từ chối nhầm** (q04, q09, q13, q14, q15). Hai câu thiếu bằng chứng (u01, u02) được từ chối đúng ở mọi lần chạy.

Ký hiệu trong bảng trước/sau: điểm câu trả lời · `A` = trả lời, `X` = từ chối · `fs3` = lần tìm đầu có evidence trong top-3 · `ctx` = context cuối gửi model có evidence.

#### Lỗi 1 — Context budget 800 ký tự loại mất evidence hạng 2–3

| Mục | Nội dung |
|---|---|
| Hiện tượng | **q11** ("Theo Quy định công tác khảo thí, sinh viên bị kỷ luật khiển trách thì chịu hậu quả gì?"): lần tìm đầu trả `A-p97-001, A-p98-000, A-p98-001` nhưng context chỉ có `A-p97-001` (592 ký tự). Agent trả lời bằng danh sách lỗi khiển trách của **cán bộ coi thi** (đi trễ, không đeo thẻ…) [A-p97-001] — sai đối tượng. Đáp án "trừ 25% điểm tổng kết học phần" nằm ở `A-p98-000`, hạng 2. **q07**: context chỉ có `A-p123-000` (kết quả rèn luyện không vượt quá Trung bình khi bị cảnh cáo); agent suy diễn thành "hạng tốt nghiệp bị giới hạn ở Trung bình", trong khi đáp án "giảm đi một mức" ở `A-p82-000`, hạng 2. **q05**: ngưỡng điểm trung bình ở `A-p80-000`, hạng 3; agent trả lời bằng điều kiện khác (< 7 tín chỉ) [A-p79-001]. |
| Nguyên nhân | `pack_context` của starter tính cả dòng `[id \| nguồn \| page]`; với chunk 500 ký tự, budget 800 thường chỉ vừa **1 chunk**. Retrieval không phải vấn đề: dense với câu hỏi gốc có evidence trong top-3 ở 15/15 câu dev, nhưng Context Evidence Rate chỉ 10/15. Ngoài ra loop giữ chunk của lần tìm trước, nên chunk tốt hơn tìm được sau không vào được (q13: lần tìm 3 trả `A-p122-001` ở hạng 2 nhưng context đã đầy bằng `A-p119-001`). Prompt cảnh báo "thông tin khác đối tượng không phải là câu trả lời" không đủ để model nhận ra, vì trong context không có đoạn đúng để so sánh. |
| Giả thuyết (ghi trước khi chạy) | Đưa được evidence hạng 2–3 vào context sẽ tăng Context Evidence Rate, giảm câu trả lời sai có citation và từ chối nhầm. Hai cách: (a) budget 2000 ký tự + xếp context theo score cosine (`configs/improve_context.json`); (b) rerank cross-encoder để evidence lên hạng 1 trong budget cũ (`configs/method_rerank.json`). |
| Kết quả trước → sau | **q11**: 0 A, ctx 0 → 2 A, ctx 1 ở cả `improve_context` và `method_rerank`. **q07**: 0 A, ctx 0 → 2 A, ctx 1 ở cả hai. **q14**: 0 X → 2 A ở cả hai. **q05**: vẫn 0 ở cả hai — `improve_context` có context lớn hơn nhưng các query model viết lại kéo về `A-p78-000`, `A-p77-001` thay vì `A-p80-000`; ở `method_rerank` agent trích `A-p79-001` (hạng 1) vì budget 800 chỉ chứa một chunk — trong bài đo retrieval với nguyên văn câu hỏi, rerank cũng chỉ đưa `A-p80-000` từ hạng 3 lên hạng 2. Toàn dev: Context Evidence Rate 7/15 → 12/15 (`improve_context`), 11/15 (`method_rerank`); câu sai có citation 3 → 1 → 1; grounded 0,93 → 1,60 → 1,47. |

#### Lỗi 2 — Model viết lại query làm retrieval kém hơn câu hỏi gốc

| Mục | Nội dung |
|---|---|
| Hiện tượng | **q04** ("Sinh viên đã tích lũy được 80 tín chỉ thì được xếp trình độ năm thứ mấy?"): cả 3 query của model đều có dạng "80 tín chỉ xếp trình độ năm thứ mấy sinh viên **Sổ tay sinh viên 2025-2026 ĐHQG-HCM**", chỉ đảo vị trí cụm từ; không lần nào tìm ra `A-p79-001` (76 ≤ N < 114: năm thứ ba). Agent từ chối. **q09**: query 2 và 3 trùng y nguyên ("quy định bài thi được dùng bút chì hay không sinh viên Sổ tay sinh viên 2025-2026 ĐHQG-HCM"). **q15**: query ghi sai tên văn bản ("theo **quy chế đào tạo**") cho câu hỏi về khen thưởng. |
| Nguyên nhân | Model tự viết lại câu hỏi ngay ở lần tìm đầu và chèn tên tài liệu, năm học, tên trường — các từ có trong rất nhiều chunk nên làm loãng query (với dense, embedding bị kéo về các đoạn giới thiệu chung như `A-p102-000`, `A-p113-002`). Lần tìm đầu của agent chỉ có evidence trong top-3 ở 11/15 câu, trong khi dùng nguyên văn câu hỏi được 15/15. Model không đổi cách diễn đạt khi tìm lại: 9 lượt tìm của baseline nằm trong các cặp query trùng y nguyên. |
| Giả thuyết (ghi trước khi chạy) | Lần tìm đầu dùng nguyên văn câu hỏi, chặn query trùng và thêm quy tắc viết query (không chèn tên tài liệu/năm học, chỉ nêu tên văn bản khi câu hỏi nêu) sẽ đưa first-search Hit@3 về khoảng 15/15 và giảm từ chối nhầm ở q04, q09, q15 (`configs/improve_query.json`, prompt v2). |
| Kết quả trước → sau | **q04**: fs3 0 → 1, 0 X → 2 A (lần tìm đầu trả `A-p79-001` ở hạng 1). **q09**: fs3 0 → 1, 0 X → 2 A. **q15**: fs3 0 → 1 nhưng vẫn 0 X — `A-p141-001` ở hạng 2, bị budget 800 loại (Lỗi 1). Toàn dev: first-search Hit@3 11/15 → 15/15, từ chối nhầm 5 → 3, grounded 0,93 → 1,33, chi phí $0.0081 → $0.0060, trung vị 9,6 s → 7,4 s/câu (ít lượt tìm hơn: 9/17 câu chỉ cần 1 lần tìm). Chặn trùng kích hoạt 2 lần. |

#### Hai lỗi chồng lên nhau

Sửa riêng từng lỗi chỉ giải quyết một phần, vì một câu có thể vướng cả hai: ở `improve_query`, q13 và q15 đã có evidence trong top-3 lần tìm đầu nhưng vẫn từ chối do budget; ở `improve_context`, q05 và q09 có context lớn nhưng query viết lại không tìm đúng chỗ. Cấu hình `combined` (rerank + nguyên văn câu hỏi ở lần tìm đầu + chặn trùng + prompt v2 + budget 2000 xếp theo score rerank) xử lý cả hai: 15/15 câu có đáp án được trả lời với citation đúng chunk gold, Context Evidence Rate 15/15, không còn câu sai có citation, grounded 2,00; vẫn từ chối đúng u01, u02.

#### Lỗi còn lại và giới hạn

- **Ranh giới chunk (q14):** `A-p123-001` bắt đầu bằng mẩu câu "thôi học không được đánh giá kết quả rèn luyện", là phần đuôi của "Sinh viên bị kỷ luật mức **buộc** thôi học…" ở chunk trước. Cả 3 cấu hình trả lời được q14 (`improve_context`, `method_rerank`, `combined`) đều thêm ý sai "thôi học/bỏ học thì không được đánh giá". Ý chính vẫn đúng nên chấm 2 thống nhất cho cả ba (quyết định của người chấm); đây là hạn chế của chunk cố định 500 ký tự (strategy A, chọn ở Day 6) mà Day 7 không sửa, vì đổi chunking cần index mới.
- **Suy diễn từ quy định gần nghĩa (q07):** chỉ hết khi `A-p82-000` vào context; prompt hiện tại không ngăn được model suy diễn khi thiếu đoạn đúng.
- **Dao động giữa các lần chạy:** cùng cấu hình baseline, hai lần chạy cho 10/15 và 9/15 câu được trả lời, first-search Hit@3 11/15 và 14/15, grounded 0,93 và 0,87. Chênh lệch dưới khoảng 0,1 điểm grounded hoặc 1–2 câu không đủ để kết luận một cấu hình tốt hơn.
- **Nguy cơ quá khớp dev:** các thay đổi được thiết kế từ chính lỗi dev, và `combined` mới chạy một lần; điểm tuyệt đối trên dev có thể cao hơn thực tế. Bộ test (5 câu có đáp án + 2 câu thiếu bằng chứng) đã chạy sau khi chốt: cả baseline và `combined` đều đạt tối đa, nên test không xác nhận được mức cải thiện trên dev (xem phần kết luận).
- **Nhãn:** Claude đề xuất nhãn nháp kèm lý do; người làm bài đã đọc trace và chunk từng câu của cả 7 lần chạy, xác nhận ngày 2026-11-16 (`labels/dev/*.reviews.json`). Quyết định có tính khẳng định thừa ở q14 hay không do người làm bài chọn: giữ 2 điểm, áp dụng thống nhất cho `improve_context`, `method_rerank`, `combined`.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: xem chi tiết bên dưới.

### Cấu hình baseline và điều kiện dừng

Cấu hình chốt ngày 2026-11-16 trong [configs/baseline.json](../../configs/baseline.json). Mỗi lần chạy ghi đường dẫn và sha256 của file vào `summary.json`; ghi đè bằng CLI bắt buộc đặt tên cấu hình mới.

| Thành phần | Baseline | Lý do |
|---|---|---|
| Retrieval | Dense, bge-m3 + pgvector strategy A, `top_k = 3` | Phương pháp bắt buộc; strategy A được Day 6 chọn trên dev và Day 7 tái lập top-3 trùng 15/15 câu dev. `top_k = 3` khớp cutoff Evidence Hit@3 |
| Filter | Chỉ trường `filter` người hỏi nêu (q11, q12, q16), key `section` | Không suy ra filter từ gold |
| Context | `pack_context` của starter, budget 800 ký tự (tính cả dòng nguồn), cộng dồn qua các lần tìm, bỏ trùng | Mặc định starter, giữ làm mốc trước/sau. Hạn chế đã biết: thường chỉ vừa 1 chunk (dense dev: Context Evidence Rate 10/15 so với Hit@3 15/15) |
| Số lượt tìm | `max_searches = 3` | 1 lần tìm + 2 lần tìm lại; giới hạn độ trễ (~3 giây mỗi lượt LLM) và tránh vòng lặp |
| Model | `gpt-5-nano`, `reasoning_effort = low`, `max_completion_tokens = 4000`, prompt `895e9fceb1f4` | Model OpenAI rẻ nhất có tool calling ($0.05 / $0.40 mỗi 1M token input/output); mọi cấu hình so sánh dùng cùng model |
| Tool | `search_documents(query)`, `submit_answer(answer, citations)`, `abstain(reason)` | Tách rõ trả lời và chủ động từ chối |

Quy tắc điều khiển:
- Lượt đầu bắt buộc gọi `search_documents`: không trả lời hay từ chối khi chưa xem tài liệu.
- Khi hết lượt tìm, tool tìm kiếm bị gỡ; model chỉ còn trả lời hoặc từ chối.
- Context gửi model được đánh dấu là dữ liệu, không phải chỉ dẫn. Prompt cấm dùng kiến thức ngoài và cảnh báo thông tin gần đúng (khác đối tượng, khác loại phí).
- Nếu `submit_answer` sai định dạng citation (thiếu `[id]` trong answer hoặc ID không có trong context), controller nhắc model sửa **một lần**; không tự chèn citation thay model.

Điều kiện dừng (trường `stop_reason` trong trace):

| `stop_reason` | Status | Khi nào |
|---|---|---|
| `answered` | answered | `submit_answer` có mọi citation nằm trong context cuối và xuất hiện dạng `[id]` trong answer |
| `model_abstain` | abstain | Model gọi `abstain`; trace ghi lý do và `searched_before_abstain` |
| `invalid_or_missing_citations` | abstain | Citation vẫn sai sau 1 lần nhắc; câu trả lời bị loại vẫn lưu để phân tích |
| `search_limit` | abstain | Model đòi tìm khi đã hết lượt. Hiếm xảy ra vì tool tìm kiếm bị gỡ khi `searches_left = 0` |
| `error` | error | Lỗi provider/database sau 3 lần thử lại có backoff, hoặc model không trả tool call hợp lệ sau 1 lần nhắc. Báo riêng, không tính vào chất lượng, không thay bằng kết quả giả |
| `max_steps` | abstain | Chốt chặn an toàn của loop; không xảy ra với controller hiện tại |

Thay đổi trước khi chốt (phát hiện khi smoke test q01, q10, u02 trên dev):
1. q10 trả lời đúng nhưng không viết `[A-p98-003]` trong answer nên bị loại → sửa prompt và thêm nhắc sửa citation 1 lần.
2. q01 dùng hết 3 lần tìm dù lần đầu đã có evidence → thêm quy tắc "context đã có đoạn trả lời trực tiếp thì trả lời ngay"; sau sửa q01 chỉ cần 1 lần tìm.

Ghi nhận cho phân tích lỗi: ở u02 model lặp lại y nguyên một query ở lần tìm 2 và 3. Mạng đôi khi gặp `APIConnectionError`; cơ chế thử lại xử lý được và lỗi được ghi trong trace.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| baseline / dev | 17/17 | 1 lần: 4 · 2 lần: 4 · 3 lần: 9 | 8 / 0 / 7 · 0,93 | 8/10 | 10/10 câu trả lời | 2/2 | 5/15 |
| baseline (chạy lại) / dev | 17/17 | 4 · 2 · 11 | 8 / 1 / 6 · 0,87 | 8/10 | 9/9 | 2/2 | 6/15 |
| improve_query / dev | 17/17 | 9 · 3 · 5 | 5 / 0 / 10 · 1,33 | 11/12 | 12/12 | 2/2 | 3/15 |
| improve_context / dev | 17/17 | 6 · 3 · 8 | 3 / 0 / 12 · 1,60 | 16/16 | 13/13 | 2/2 | 2/15 |
| method_hybrid / dev | 17/17 | 10 · 2 · 5 | 5 / 0 / 10 · 1,33 | 10/12 | 12/12 | 2/2 | 3/15 |
| method_rerank / dev | 17/17 | 8 · 2 · 7 | 4 / 0 / 11 · 1,47 | 12/12 | 12/12 | 2/2 | 3/15 |
| **combined (đã chọn) / dev** | 17/17 | 11 · 2 · 4 | **0 / 0 / 15 · 2,00** | **16/16** | 15/15 | 2/2 | **0/15** |
| **combined / test** | 7/7 | 1 lần: 4 · 2 lần: 1 · 3 lần: 2 (tổng 12) | 0 / 0 / 5 · 2,00 | 5/5 | 5/5 | 2/2 | 0/5 |
| baseline / test | 7/7 | 1 lần: 2 · 2 lần: 1 · 3 lần: 4 (tổng 16) | 0 / 0 / 5 · 2,00 | 5/5 | 5/5 | 2/2 | 0/5 |

**Context trên test** (chấm tay context cuối gửi model, 5 câu có đáp án, `context_grade` trong `labels/test/*.reviews.json`): baseline 0 câu mức 0 · 0 câu mức 1 · **5 câu mức 2**; `combined` 0 · 0 · **5**. Mọi context cuối đều chứa chunk gold kèm đủ điều kiện/ngoại lệ (q16 "nếu SV không tái phạm…", q18 "trừ các ngày nghỉ lễ") và nguồn/trang. Context của `combined` có thêm chunk không liên quan do budget 2000 (vd. q18: `A-p66-000`, `A-p133-001`) nhưng không ảnh hưởng câu trả lời. Test không có lỗi hệ thống.

Không có lỗi hệ thống (status `error`) ở lần chạy nào trên dev. Lỗi kết nối tạm thời (`APIConnectionError`) đã xảy ra ở smoke test và được xử lý bằng thử lại; vẫn ghi trong trace. Số lượt gọi tính theo số lần `search_documents`; với `improve_query` và `combined`, lần tìm đầu là nguyên văn câu hỏi (không qua model).

Bảng dưới là **toàn bộ 7 câu test** của cấu hình đã chọn `combined`, kèm so sánh baseline ở cột lý do.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| q16 | Có đáp án (filter `section: khen_thuong_ky_luat`) | 1 lần tìm (nguyên văn câu hỏi) → `A-p147-002` hạng 1; context `A-p147-002, A-p147-003, A-p148-000` | "Sau 03 tháng kể từ ngày có quyết định kỷ luật khiển trách, nếu SV không tái phạm… thì đương nhiên được chấm dứt hiệu lực…" [A-p147-002] | Đáp án 2, citation đúng, context 2. Baseline cũng 2 nhưng cần 3 lần tìm, query 2 và 3 trùng y nguyên |
| q17 | Có đáp án | 2 lần tìm → `A-p158-003`; context `A-p158-003, A-p159-000, A-p158-001` | "Phải báo địa chỉ ngoại trú cho trường trong thời hạn 30 ngày, kể từ ngày nhập học" [A-p158-003] | 2 / citation đúng / context 2. Baseline 2 (3 lần tìm) |
| q18 | Có đáp án | 1 lần tìm → `A-p164-001`; context thêm `A-p66-000`, `A-p133-001` không liên quan | "Trường hoạt động từ 6g00 đến 21g30 các ngày trong tuần, trừ các ngày nghỉ lễ…" [A-p164-001] | 2 / đúng / context 2 (có nhiễu). Baseline 2, nhưng query đầu chỉ là "Sổ tay sinh viên 2025-2026 Trường ĐH Khoa học tự nhiên ĐHQG-…" |
| q19 | Có đáp án | 1 lần tìm → `A-p169-000`; context `A-p169-000, A-p168-000, A-p172-001` | "50% học phí" [A-p169-000] | 2 / đúng / context 2. Ngắn, không nhắc lại đối tượng; câu hỏi đã nêu đủ đối tượng nên chấm 2 (cùng chuẩn với baseline) |
| q20 | Có đáp án | 1 lần tìm → `A-p81-003`; context `A-p81-003, A-p82-001, A-p80-002` | "…được cấp bằng trong thời hạn 03 tháng tính từ thời điểm sinh viên đáp ứng đầy đủ điều kiện tốt nghiệp và hoàn thành các nghĩa vụ…" [A-p81-003] | 2 / đúng / context 2. Baseline 2 |
| u03 | Thiếu bằng chứng | 3 lần tìm ("…phí nội trú bao nhiêu tiền", "phí nội trú mỗi tháng khu nội trú phí", "phí nội trú mỗi tháng"); context `A-p161-002, A-p170-000, A-p161-001` | Từ chối: "có thông tin về phí nội trú nhưng không chứa mức phí cụ thể theo tháng, chỉ ghi nhận việc nộp phí theo hợp đồng" | Từ chối đúng. Context có cả bẫy 100.000đ/tháng (trợ cấp, `A-p170-000`) nhưng model không lấy nhầm. Baseline cũng từ chối đúng |
| u04 | Thiếu bằng chứng | 3 lần tìm về "vay vốn ngân hàng chính sách… hộ nghèo"; context `A-p170-000, A-p173-000, A-p171-000` | Từ chối: "không có thông tin về mức vay vốn… chỉ có thông tin trợ cấp và chính sách cho khuyết tật/dân tộc thiểu số" | Từ chối đúng. Baseline từ chối đúng nhưng lý do lẫn tiếng Indonesia ("CONTEXT tidak mengandung informasi tentang…"); các mức 100.000đ, 140.000đ baseline nhắc tới có thật trong context, được nêu để giải thích không phải vay vốn |

**Ví dụ trình bày:** câu trả lời có bằng chứng: **q16** (kèm điều kiện, citation đúng điều khoản). Câu thiếu bằng chứng: **u03** (từ chối dù context có con số gần nghĩa). Lỗi: **q11 dev của baseline** (trả lời bằng quy định khiển trách của cán bộ coi thi, do budget 800 loại mất `A-p98-000`), **q14 dev** (ý thừa do ranh giới chunk) và **u04 test của baseline** (lý do từ chối lẫn tiếng Indonesia).

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: trace `starter/results/agent-<cấu hình>-dev/traces.json` và `summary.json` (cấu hình, sha256 file config, token, chi phí, thời gian); nhãn `labels/dev/<cấu hình>.reviews.json`; bảng tổng hợp `starter/results/agent-comparison-dev.md` (`python -m scripts.compare_agent_runs`). Lệnh chạy trong [src/README.md](../../src/README.md). Tổng chi phí API cho 7 lần chạy dev ≈ $0.05. Test: `starter/results/agent-{baseline,combined}-test/`, nhãn `labels/test/{baseline,combined}.reviews.json`, bảng `starter/results/agent-comparison-test.md`, retrieval `starter/results/retrieval-comparison-test.md`; tổng chi phí test $0.0053.
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:

### Kết luận dev và test

- **Trên dev**, `combined` tăng grounded từ 0,93 lên 2,00 (/2), Context Evidence Rate từ 7/15 lên 15/15, đưa câu sai có citation từ 3 về 0 và từ chối nhầm từ 5 về 0, với chi phí API thấp hơn 30% và chậm hơn 2,5 s/câu. Cải thiện đến từ việc sửa hai lỗi độc lập: query do model viết lại (Lỗi 2) và context budget quá nhỏ (Lỗi 1); mức chênh lớn hơn nhiều so với dao động giữa hai lần chạy baseline (0,07).
- **Trên test**, cả baseline và `combined` đều đạt tối đa: 5/5 câu đúng và đủ, 5/5 citation hợp lệ, context mức 2 ở 5/5 câu, từ chối đúng 2/2. Test **không phân biệt được** hai cấu hình về chất lượng, nên không xác nhận được mức cải thiện quan sát trên dev. Lý do: 5 câu test có đáp án đều dễ cho retrieval (dense với câu hỏi gốc có evidence trong top-3 ở 5/5 câu, hạng 1 ở 4/5) và không câu nào rơi vào hai kiểu lỗi đã thấy ở dev (evidence ở hạng 2–3, câu hỏi mà query viết lại làm lệch).
- **Điều test cho thấy:** `combined` không làm hỏng câu dễ, cần ít lượt tìm hơn (12 so với 16 trên 7 câu) và rẻ hơn ($0.0025 so với $0.0028), đổi lại chậm hơn (9,8 so với 7,1 s/câu) do reranker trên CPU. Lỗi 2 vẫn xuất hiện ở baseline trên test (query trùng y nguyên ở q16, u04; query chỉ gồm tên tài liệu ở q18, u03) nhưng không làm sai câu trả lời vì evidence dễ tìm — đây là bằng chứng độc lập rằng lỗi có thật, không chỉ riêng dev.
- **Đánh đổi của cấu hình chọn:** reranker `bge-reranker-v2-m3` cần tải ~2,3 GB và ~5,5–6,3 s mỗi lần tìm trên CPU (có GPU sẽ nhanh hơn nhiều); budget 2000 ký tự kéo thêm chunk không liên quan vào context (nhiễu, chưa gây sai trên dev/test).
- **Giới hạn:**
  - Benchmark nhỏ (dev 17 câu, test 7 câu, đúng mức tối thiểu) và một tài liệu duy nhất; một câu khác biệt tương ứng 0,13 điểm grounded trên dev và 0,4 trên test.
  - `combined` được thiết kế từ chính lỗi dev và chỉ chạy một lần trên dev → điểm dev có thể lạc quan; test quá dễ để kiểm tra điều này. Cần thêm câu test khó (evidence ở hạng thấp, nhiều điều kiện, multi-hop) để đánh giá độc lập.
  - Model `gpt-5-nano` không cố định temperature: cùng cấu hình, kết quả từng câu có thể khác giữa các lần chạy.
  - Lỗi ranh giới chunk (strategy A, 500 ký tự) vẫn còn (q14 dev); sửa cần chunking theo điều/khoản và index mới.
  - Nhãn do Claude đề xuất bản nháp kèm lý do, người làm bài đọc trace/chunk và xác nhận từng câu; một người chấm, chưa có đánh giá chéo.

## Thử thách nâng cao (nếu thực hiện)

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản:
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý:
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev:

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | | | |
| Ảnh, sơ đồ | | | |
| Biểu đồ | | | |
| Multi-hop | | | |
| Text | | | |
| Thiếu bằng chứng | | | |
| **Toàn bộ** | | | |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống:
- Giới hạn, cách tái lập và đường dẫn benchmark:
