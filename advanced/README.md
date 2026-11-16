# Thử thách nâng cao — OECD Economic Surveys: Viet Nam 2025

Yêu cầu: [ADVANCED.md](../ADVANCED.md).

## 1. Tài liệu nguồn

| Mục | Giá trị |
|---|---|
| Tên | OECD Economic Surveys: Viet Nam 2025 (Volume 2025/16) |
| Tổ chức, phiên bản | OECD, phát hành 06/2025 (bản PDF tiếng Anh) |
| Trang giới thiệu | https://www.oecd.org/en/publications/oecd-economic-surveys-viet-nam-2025_fb37254b-en.html |
| PDF gốc | https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/06/oecd-economic-surveys-viet-nam-2025_f2511b78/fb37254b-en.pdf |
| SHA256 | `e8ca6a3c51f44585c915bc032f991d91026ba772400584ff3a3fa764c05f5b0c` (5 754 637 byte) |
| Số trang | 139 trang PDF; số trang in = trang PDF − 2 (ví dụ trang PDF 82 in số 80) |
| Quyền sử dụng | © OECD 2025, Creative Commons Attribution 4.0 International (CC BY 4.0), ghi trên trang bản quyền (trang PDF 4). Ảnh bìa và ảnh đầu chương thuộc bên thứ ba (Shutterstock), nằm ngoài giấy phép |
| Dữ liệu kiểm chứng | Mỗi hình có StatLink (`https://stat.link/...`) tải dữ liệu gốc dạng Excel |

PDF không được commit (`advanced/source/` nằm trong `.gitignore`). Cách tái tạo:

```powershell
New-Item -ItemType Directory -Force advanced/source
curl.exe -L -o advanced/source/oecd-economic-surveys-viet-nam-2025.pdf "https://www.oecd.org/content/dam/oecd/en/publications/reports/2025/06/oecd-economic-surveys-viet-nam-2025_f2511b78/fb37254b-en.pdf"
(Get-FileHash advanced/source/oecd-economic-surveys-viet-nam-2025.pdf -Algorithm SHA256).Hash
```

### Thống kê nội dung (kiểm tra bằng PyMuPDF)

- Lớp text: có ở mọi trang, trừ trang PDF 2 (trắng), 3 (trang tên sách) và 95 (trang bìa chương). Không cần OCR.
- Bảng: 14 bảng có tiêu đề (Table 1.1–4.3).
- Biểu đồ: khoảng 70 hình có tiêu đề (Figure 1–4 trong tóm tắt, Figure 1.1–4.28). Phần lớn vẽ dạng vector, nên nhãn trục, chú giải và số liệu nằm trong lớp text của PDF.
- Ảnh nhúng: 23 ảnh. Gồm 16 biểu đồ dạng raster (bảng bên dưới), 1 ảnh bìa (trang 1), 4 ảnh đầu chương (trang 18, 48, 70, 96), 1 logo (trang 4) và 1 mã QR (trang 139). Ảnh bìa, ảnh chương, logo và QR chỉ để trang trí nên không dùng để đặt câu hỏi.

## 2. Phân loại nhóm "Ảnh, sơ đồ" và lý do

Tài liệu không có sơ đồ quy trình hay ảnh chụp mang thông tin. Mọi hình có dữ liệu đều là biểu đồ. Để phủ nhóm **Ảnh, sơ đồ** theo ADVANCED.md, bài này chỉ lấy nguồn từ **16 hình được nhúng dưới dạng ảnh raster (bitmap)**. Nhóm **Biểu đồ** chỉ lấy từ các hình vẽ vector.

Lý do tách như vậy:

1. **Khác bản chất dữ liệu trong PDF.** Hình raster là một ảnh bitmap: tiêu đề trục, chú giải, nhãn danh mục và số liệu đều là pixel, không có trong lớp text. Hình vector có toàn bộ nhãn và số trích được bằng text extraction.
2. **Khác pipeline xử lý.** Với hình raster, chỉ đọc text thì không lấy được nội dung hình (chỉ còn tiêu đề và ghi chú bên ngoài). Phải crop ảnh rồi dùng vision model mô tả hoặc trích dữ liệu, và agent có thể xem lại ảnh crop lúc trả lời. Đây đúng là năng lực "tìm evidence từ nội dung trực quan" mà nhóm ảnh cần kiểm tra.
3. **Không dùng ảnh trang trí.** Ảnh bìa, ảnh chương, logo và QR không chứa thông tin hữu ích nên bị loại, đúng quy định "không dùng các hình chỉ để trang trí".
4. **Kiểm chứng được.** Mỗi hình raster có StatLink dữ liệu gốc. Đáp án được đối chiếu với ảnh trong PDF và file Excel, không dựa vào mô tả do model sinh ra.

Hạn chế: người chấm có thể xem các hình này là biểu đồ chứ không phải "ảnh/sơ đồ" theo nghĩa hẹp. Câu hỏi nhóm ảnh vì vậy tập trung vào **nhận diện và giải thích nội dung hiển thị trong ảnh**: thành phần lớn nhất, quốc gia hay ngành được tô nổi bật, panel nào thể hiện gì, so sánh trực quan giữa các phần. Các câu đọc trục hoặc giá trị theo thời gian để dành cho nhóm Biểu đồ (hình vector).

Quy tắc chặn rò rỉ: mỗi câu chỉ thuộc một nhóm chính. Một hình raster đã dùng cho câu nhóm Ảnh thì không dùng làm evidence chính cho câu nhóm Biểu đồ.

### 16 hình raster dùng cho nhóm Ảnh

| # | Trang PDF | Trang in | Hình | Nội dung (theo tiêu đề) | Bbox ảnh (pt, x0,y0,x1,y1) | Pixel | StatLink |
|---:|---:|---:|---|---|---|---|---|
| 1 | 11 | 9 | Figure 1 (tóm tắt) | Viet Nam's growth has outperformed peers | 87,457,508,644 | 878×389 | https://stat.link/tsol34 |
| 2 | 16 | 14 | Figure 4 (tóm tắt) | Viet Nam's share in world goods trade has risen | 73,334,523,521 | 1249×519 | https://stat.link/trswx8 |
| 3 | 32 | 30 | Figure 1.10 | Property and construction sector accounts for a third of corporate sector debt | 144,87,452,261 | 855×484 | https://stat.link/ku5anq |
| 4 | 36 | 34 | Figure 1.14 | Viet Nam has reduced government spending and its budget deficit since the mid-2010s | 71,202,525,410 | 1261×577 | https://stat.link/nt4agi |
| 5 | 39 | 37 | Figure 1.18 | Expected rise in public social spending calls for offsetting fiscal measures | 86,81,509,263 | 1176×506 | https://stat.link/nvyc0x |
| 6 | 40 | 38 | Figure 1.19 | Tax revenue steady at close to 20% during the past 20 years | 65,401,531,607 | 1293×572 | https://stat.link/hgwiek |
| 7 | 50 | 48 | Figure 2.1 | Poverty indicators | 85,341,510,539 | 1181×551 | https://stat.link/rmiecu |
| 8 | 74 | 72 | Figure 3.2 | Electricity generation is the main source of GHG emissions | 91,97,504,283 | 1147×517 | https://stat.link/a05zm1 |
| 9 | 82 | 80 | Figure 3.8 | Viet Nam has a considerable renewable energy potential | 77,500,518,678 | 1225×493 | https://stat.link/95oc0m |
| 10 | 98 | 96 | Figure 4.1 | Rapid development supported by FDI inflows and international trade (4 panel A–D) | 79,229,517,605 | 1215×1045 | https://stat.link/hyaic6 |
| 11 | 100 | 98 | Figure 4.3 | Stock of inward FDI has increased rapidly since 2007 | 87,498,508,685 | 1170×518 | https://stat.link/zuypjq |
| 12 | 101 | 99 | Figure 4.4 | Wages remain relatively low compared to ASEAN peers | 65,103,531,258 | 1293×431 | https://stat.link/wcu0a3 |
| 13 | 108 | 106 | Figure 4.11 | FDI restrictions above OECD average, close to ASEAN (panel A, B) | 82,107,513,482 | 1196×1042 | https://stat.link/jh91vg |
| 14 | 111 | 109 | Figure 4.13 | Foreign value-added in exports is high but GVC participation is low | 92,290,503,482 | 1143×533 | https://stat.link/lyvua1 |
| 15 | 112 | 110 | Figure 4.14 | Production workers ≈ 85% of employees in the export sector | 82,361,516,554 | 1203×536 | https://stat.link/7zq9lu |
| 16 | 131 | 129 | Figure 4.27 | State-owned enterprises play a large role in Viet Nam | 71,103,524,297 | 945×406 | https://stat.link/3ofz2k |

Lưu ý trùng lặp: Figure 1 (trang 11) trùng nội dung với panel A của Figure 4.1 (trang 98), và Figure 4 (trang 16) trùng với panel D của Figure 4.1. Câu dev và test không được dùng hai bản trùng của cùng một hình cho cùng một câu trả lời.

## 3. Ingest: [ingest.py](ingest.py)

```powershell
.venv/Scripts/python.exe advanced/ingest.py extract    # PDF -> extracted.json + crops (không gọi API)
.venv/Scripts/python.exe advanced/ingest.py chartdata  # số liệu cột/đường đọc từ toạ độ vector PDF (không gọi API)
.venv/Scripts/python.exe advanced/ingest.py describe   # vision model mô tả 72 hình (có cache, tốn phí API)
.venv/Scripts/python.exe advanced/ingest.py build      # -> advanced/data/chunks.json
```

Cần `pymupdf` (đã cài trong `.venv`). Bước `describe` dùng `OPENAI_API_KEY` và các biến `VISION_*` trong `.env` (xem `.env.example`).

| Loại chunk | Cách xử lý |
|---|---|
| Text | Block văn bản ngoài vùng hình/bảng, bỏ header/footer, gộp theo trang và heading tới ~1 200 ký tự. Đầu chunk ghi đường dẫn heading lấy từ mục lục PDF. |
| Bảng | Vùng tính từ caption `Table x.y.` tới dòng `Source`/StatLink, đoạn văn thường kế tiếp hoặc heading. Dùng `find_tables().to_markdown()` và **kiểm tra lại số liệu**: nếu markdown thiếu bất kỳ con số nào có trong vùng thì chuyển sang text theo hàng (dựng từ toạ độ từng từ). Giữ dòng đơn vị nằm trên bảng. Bảng dài trên 2 500 ký tự được tách theo hàng, mỗi phần lặp lại caption và header. |
| Hình | Vùng từ caption `Figure x.y.` tới StatLink. Crop PNG 200 dpi. Lưu nhãn chữ trong lớp text (với hình vector), Note/Source, StatLink, cờ `is_raster`. Hình vector có thêm bảng số **đọc từ toạ độ PDF** (xem mục dưới). Vision model (prompt `fig-v2`) mô tả trục, đơn vị, chú giải, điểm nổi bật và chỉ chép số được in sẵn trên hình. Mô tả lưu kèm tên model và phiên bản prompt, đánh dấu `verified: false` cho tới khi được đối chiếu tay. |

### Số liệu biểu đồ "đọc từ toạ độ PDF" (`chartdata`)

Vision model chép đúng số được in trên hình. Khi phải ước lượng theo đường lưới thì hay sai: prompt v1 đọc sai năm Gini giảm mạnh và sai thứ tự vùng ở Figure 2.2. Vì vậy prompt v2 chỉ chép số in sẵn, còn số liệu của hình vector lấy bằng cách tính từ hình học trong PDF:

1. **Trục y:** tìm ≥ 3 nhãn số thẳng hàng. Giá trị phải tuyến tính theo y (R² ≥ 0,9999), nên tự loại trục log và nhãn năm. Vị trí nhãn được căn theo đường lưới hoặc trục ngay cạnh (73/77 panel căn được).
2. **Cột:** hình chữ nhật tô màu chạm baseline (0, hoặc đáy trục nếu trục không chứa 0). Giá trị lấy theo mép trên, với cột âm thì theo mép dưới.
3. **Đường:** polyline có màu, bỏ đường lưới hoặc trục màu xám hay đen. Đường ngang có màu (ngưỡng) được giữ lại.
4. **Trục x:** cột hoặc điểm được gán vào nhãn trục x gần nhất. Nếu nhãn là năm cách đều, năm của từng điểm được suy từ toạ độ x, nên điểm nằm giữa hai nhãn in vẫn có năm. Series theo tháng hoặc quý chỉ ghi phần tóm tắt (đầu, cuối, max, min kèm năm thập phân).
5. **Tên series:** lấy từ mẫu chú giải cùng màu (ô vuông hoặc đoạn ngang ngắn) cộng với chữ bên phải nó.
6. **Không đoán:** các trường hợp sau được ghi lý do rồi bỏ qua:
   - biểu đồ hai trục y (phát hiện qua hình học, hoặc chữ "rhs" / "right axis");
   - cột chồng;
   - cột ngang, scatter, hoặc không có trục số.

Bảng số được gắn vào chunk hình với câu "Data read from PDF vector coordinates … (method: đọc từ toạ độ PDF) … NOT printed in the report", kèm độ phân giải của từng panel (±0,5 pt quy ra đơn vị trục). Metadata ghi `chart_data.method = "đọc từ toạ độ PDF"`. Kết quả chi tiết (nhãn trục, R², số điểm, màu) nằm trong [data/chart_data.json](data/chart_data.json).

**Độ phủ:** 40/56 hình vector có số liệu (52/77 panel, 107 series). 16 hình còn lại được đánh dấu không hỗ trợ, kèm lý do trong `chart_data.json`:
- không có trục y dạng số: cột ngang, scatter (Figure 1.2, 2.9, 4.6, 4.10, 4.15, 4.18–4.21);
- hai trục y (2.8, 4.5);
- trục x nhiều cấp, kiểu quốc gia × năm (1.15);
- cột chồng, hoặc không nhận được cột/đường nào (1.20, 3.3, 3.9, 4.12).

Panel hai trục y bên trong một hình được hỗ trợ cũng bị bỏ, ví dụ Figure 1.1 panel C. 16 hình raster không có toạ độ vector nên chỉ dùng mô tả vision.

### Kiểm chứng với StatLink: [validate_chartdata.py](validate_chartdata.py)

```powershell
.venv/Scripts/python.exe -m pip install openpyxl          # chỉ cần cho bước kiểm chứng
.venv/Scripts/python.exe -I advanced/validate_chartdata.py  # tải StatLink (.xlsx) vào advanced/source/statlink/ rồi so
```

File StatLink là Excel dữ liệu gốc OECD công bố kèm từng hình. File này **chỉ dùng để đo độ chính xác** của bước `chartdata`, không đưa vào index hay vào pipeline trả lời.

Cách so sánh:
- Với mỗi series đã trích, script dò mọi cặp (cột nhãn, cột số) trong Excel, cả dữ liệu xếp theo cột lẫn theo hàng, với hệ số đơn vị ×1 / ×100 / ×0,01…
- Chọn cột phủ ≥ 60% nhãn x có sai số nhỏ nhất.
- Ngưỡng "đúng" = độ phân giải của panel (±0,5 pt quy ra đơn vị trục) + làm tròn khi ghi.

Kết quả chi tiết từng series nằm trong [data/chartdata_validation.json](data/chartdata_validation.json).

| Chỉ số | Kết quả |
|---|---|
| Hình / series / điểm đã so | 30 hình, 70 series (33 cột, 37 đường), 1 106 điểm |
| Điểm nằm trong độ phân giải | **1 105 / 1 106 (99,9%)** |
| Sai số tuyệt đối trung bình (trung vị theo series) | 0,03% thang trục |
| Sai số lớn nhất của series (phân vị 95) | 0,71% thang trục |
| Series không ghép được với Excel | 5 (xem hạn chế) |

Điểm duy nhất vượt ngưỡng là Figure 2.11, Thailand: đọc ra 0,0, Excel ghi −0,56. Cột cao dưới 1 pt nên bị lọc. Ví dụ khớp:
- Gini ở Figure 2.2 khớp từng số với Excel (0,420 … 0,374).
- Tăng trưởng GDP 2022 ở Figure 1.1 panel B là 8,5, khớp Excel và Table 1.1.
- Ngưỡng thu nhập cao ở Figure 4.2 đọc ra 13 841, ghi chú in USD 13 845.

**Lỗi tìm ra nhờ bước kiểm chứng và đã sửa trong `ingest.py`:**
- Chú giải bị lấy nhầm từ panel khác cùng màu (Figure 1.1).
- Trục x nhiều cấp bị gán sai năm (Figure 1.15).
- Series theo tháng lấy điểm đầu khoảng dung sai thay vì điểm gần nhãn nhất (Figure 1.6, từng lệch tới 20% thang trục).
- Tiêu đề trục lẫn vào nhãn năm làm series theo tháng bị ghi thành số năm (Figure 1.13).
- Cột tô màu nổi bật (Viet Nam, OECD) bị tách khỏi bảng xếp hạng.

**Hạn chế còn lại:**
- Cột hoặc đoạn rất nhỏ (< 1 pt) có thể bị đọc thành 0.
- 5 series chưa kiểm chứng được:
  - Figure 4.26: nhãn năm 2 chữ số "70", "72" (giá trị vẫn được trích);
  - Figure 2.3: nhãn danh mục dài bị gộp sai;
  - Figure 3.1: một cột lẻ.
- Nhãn xoay dọc có thể mất chữ số đầu (Figure 2.6: "6 - Food…" thay vì "56 - Food…").
- Tổng cộng 52/77 panel, 107 series; 73 series có tên từ chú giải. Trong 34 series không có tên, 20 series là series duy nhất của panel (bảng ghi "value"). 14 series còn lại được ghi tên theo màu.

### Mô tả vision (`describe`)

| Mục | Giá trị |
|---|---|
| Model | `gpt-5-mini`, `reasoning_effort=low`, prompt `fig-v2`, ảnh crop 200 dpi `detail=high` |
| Số hình | 72/72 thành công, 0 lỗi |
| Token | 128 506 input, 87 951 output (gồm reasoning) |
| Chi phí | $0,208 (đơn giá $0,25 / $0,025 / $2,00 cho 1M token input / cached / output, tra ngày 2026-11-16) |
| Thời gian | trung vị 11,9 giây/hình |

Đối chiếu tay với ảnh gốc:
- **Số in sẵn:** chép đúng. Figure 3.8 đúng 11/11 giá trị, Figure 1.10 đúng 10/10.
- **So sánh bằng mắt khi hình không có số in sẵn:** vẫn có lỗi. Figure 4.1 panel B ghi "Viet Nam có cột 2023 thấp nhất", nhưng thực tế thấp nhất là Philippines.
- Mô tả vì vậy giữ `verified: false`. Câu benchmark nhóm Ảnh phải lấy đáp án từ ảnh gốc hoặc StatLink, không lấy từ mô tả.

Mỗi chunk có `metadata`: `type`, `section` (ch1–ch4, exec_summary…), `heading`, `printed_page`, `bbox` (point, gốc trên-trái), `object_id`, `crop_path`, `statlinks`. Nhờ vậy citation truy được về trang và vùng trên PDF gốc.

### Thống kê index (lần chạy `extract` + `build` hiện tại, chưa có mô tả vision)

- 120/139 trang có nội dung được index. Tổng 488 chunk: 390 text, 26 bảng (17 bảng, tách thành 26 phần), 72 hình (16 raster).
- 14/17 bảng dùng markdown. 3 bảng dùng text theo hàng vì markdown thiếu số:
  - Basic statistics (trang 9)
  - Table 1.4: `find_tables` làm mất cột "Policy area" và "Long term"
  - Table 4.2
- Toàn bộ danh sách nằm trong [data/ingest_stats.json](data/ingest_stats.json).

### Phần không index và ảnh hưởng

| Trang PDF | Lý do | Ảnh hưởng |
|---|---|---|
| 2, 3, 95 | Trang trắng / trang tên sách | Không có |
| 6–8 | Mục lục, danh mục hình và bảng | Chỉ lặp tiêu đề kèm số trang. Bỏ để retrieval không trả về mục lục thay cho hình thật |
| 18, 48, 70, 96 | Ảnh đầu chương (Shutterstock, trang trí) | Không có thông tin |
| 47, 68–69, 93–94, 136–138 | Danh mục tài liệu tham khảo | Không hỏi được nguồn trích dẫn chi tiết |
| 139 | Bìa sau (đoạn giới thiệu, mã QR) | Nội dung trùng Executive Summary |
| 1, 4 | Ảnh bìa, logo (text trang 4 vẫn được index) | Không có |

Hạn chế đã biết:
- Header của một số bảng khuyến nghị bị dính chữ do chữ in đậm (vd. `ActionstakensinceApril2023`), nhưng nội dung các ô vẫn đúng.
- Nhãn chữ trong hình vector bị xếp theo thứ tự block, không theo cấu trúc trục. Mô tả vision bù cho phần này nhưng phải được kiểm tra lại.

## 4. Benchmark: [benchmark/](benchmark/)

| Nhóm | Test | Dev |
|---|---:|---:|
| Bảng | 6 | 3 |
| Ảnh (16 hình raster) | 5 | 3 |
| Biểu đồ (hình vector) | 5 | 4 |
| Multi-hop (≥ 2 trang/bảng/hình) | 4 | 3 |
| Text | 4 | 3 |
| Thiếu bằng chứng | 6 | 4 |
| **Tổng** | **30** (24 có đáp án) | **20** (16 có đáp án) |

**Cấu trúc mỗi câu:**
- `id`, `group`, `question`, `expected_answer`, `key_facts`;
- `unit`, `calculation`, `tolerance`;
- `gold`: trang PDF, đối tượng (Table/Figure), chuỗi evidence nguyên văn, mô tả ô/hàng/cột hoặc vùng hình kèm mã StatLink;
- `rationale`.

Câu thiếu bằng chứng có thêm `absence_reason` và `check_method` (từ khoá đã tìm, kết quả và số trang).

**Nguyên tắc soạn:**
- Đáp án lấy từ bản gốc: chữ trong PDF, ảnh crop và dữ liệu StatLink. Không lấy từ mô tả do model sinh ra hay từ bảng số đọc theo toạ độ.
- Câu nhóm Ảnh hỏi về nhận diện và thứ hạng nhìn rõ (cột tô màu, khung đỏ, lớn nhất/nhỏ nhất). Giá trị xấp xỉ có dung sai ghi rõ.
- Tránh các ô mâu thuẫn trong chính tài liệu:
  - Table 1 (trang 12) và Table 1.1 (trang 23) lệch nhau ở xuất khẩu 2023 (−3,2 so với −2,5) và thất nghiệp 2024 (2,2 so với 2,3);
  - Table 4.2 ghi "USD 7 874" cho số tiền thu hồi, trong khi văn bản ghi USD 52,1 triệu.
- Dev và test không chung câu trả lời. Benchmark được soạn và commit trước khi chạy thử nghiệm. Cấu hình chỉ được chọn trên dev.

`check_benchmark.py` kiểm tra cơ cấu nhóm và xác nhận **mọi chuỗi evidence có mặt nguyên văn trên đúng trang PDF**. Nó cũng sinh `gold_index.json` (chunk id, bbox evidence, crop) để chấm retrieval và citation. Cả benchmark lẫn `gold_index.json` không được đưa vào pipeline lúc chạy.

```powershell
.venv/Scripts/python.exe advanced/benchmark/check_benchmark.py
```

## 5. Kết quả

_(Điền sau: cấu hình đã thử trên dev, trace, nhãn, metrics theo nhóm, lỗi, thời gian, chi phí.)_
