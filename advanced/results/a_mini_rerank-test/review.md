# Review a_mini_rerank-test

## T01 [table] - answered
**Q:** Theo bảng chỉ tiêu kinh tế vĩ mô và dự báo của OECD, nợ chính phủ của Việt Nam được dự báo bằng bao nhiêu % GDP vào năm 2026, và tăng bao nhiêu điểm phần trăm so với năm 2023?

**Đáp án chuẩn:** Nợ chính phủ dự báo bằng 38,0% GDP năm 2026, tăng 4,8 điểm phần trăm so với 33,2% GDP năm 2023.
**Key facts:** 38,0% GDP năm 2026; 33,2% GDP năm 2023; chênh lệch 4,8 điểm phần trăm
**Dung sai:** chính xác tới 0,1

**Agent:** OECD dự báo nợ chính phủ (federal government debt) của Việt Nam ở mức 38.0% GDP vào năm 2026; tăng 4.8 điểm phần trăm so với 33.2% GDP của năm 2023 (38.0 − 33.2 = 4.8 điểm %). [oecd-vn-2025:p012:table_1] [oecd-vn-2025:p023:table_1.1]
**Citations:** ['oecd-vn-2025:p012:table_1', 'oecd-vn-2025:p023:table_1.1'] | gold hit: True [True, True]
**Queries:** ['general government gross debt % of GDP 2026 forecast Vietnam OECD Economic Surveys 2025 macroeconomic indicators table']
**Inspect:** []
**Chi phí/thời gian:** $0.0019 / 28.0s

## T02 [table] - answered
**Q:** Ở Việt Nam, người sử dụng lao động và người lao động lần lượt phải đóng tổng cộng bao nhiêu % tiền lương cho bảo hiểm xã hội, bảo hiểm y tế và bảo hiểm thất nghiệp? Cộng lại là bao nhiêu?

**Đáp án chuẩn:** Người sử dụng lao động đóng 21,5%, người lao động đóng 10,5%; tổng cộng 32% tiền lương.
**Key facts:** người sử dụng lao động 21,5%; người lao động 10,5%; tổng 32%
**Dung sai:** chính xác

**Agent:** Người sử dụng lao động phải nộp tổng cộng 21.5% tiền lương (Social insurance 17.5% ; Health insurance 3.0% ; Unemployment insurance 1.0%). [oecd-vn-2025:p059:table_2.2]
Người lao động phải nộp tổng cộng 10.5% tiền lương (Social insurance 8.0% ; Health insurance 1.5% ; Unemployment insurance 1.0%). [oecd-vn-2025:p059:table_2.2]
Cộng lại, tổng đóng góp của cả hai là 32.0% tiền lương (21.5% + 10.5%). [oecd-vn-2025:p059:table_2.2]
**Citations:** ['oecd-vn-2025:p059:table_2.2'] | gold hit: True [True]
**Queries:** ['social insurance health insurance unemployment employer employee contribution rates Vietnam % salary']
**Inspect:** []
**Chi phí/thời gian:** $0.0019 / 25.18s

## T03 [table] - answered
**Q:** Thuế bảo vệ môi trường đối với dầu diesel năm 2024/25 là bao nhiêu, so với đầu năm 2023 thay đổi thế nào, và tương đương bao nhiêu USD cho mỗi tấn CO2?

**Đáp án chuẩn:** Năm 2024/25 là 1 000 VND/lít (0,039 USD/lít), giảm một nửa so với 2 000 VND/lít (0,079 USD/lít) đầu năm 2023; tương đương 15 USD/tấn CO2.
**Key facts:** 1 000 VND/lít năm 2024/25; 2 000 VND/lít đầu năm 2023 (giảm một nửa); 15 USD/tCO2
**Dung sai:** chính xác

**Agent:** Thuế bảo vệ môi trường (EPT) đối với dầu diesel năm 2024/25 là 1 000 VND/lít (≈0.039 USD/lít); so với đầu năm 2023 (2 000 VND/lít ≈0.079 USD/lít) mức thuế đã giảm một nửa (giảm 1 000 VND/lít, tức -50%). Tương đương khoảng 15 USD cho mỗi tCO2. [oecd-vn-2025:p077:table_3.2] Ngoài ra, báo cáo ghi rõ EPT trên các sản phẩm xăng dầu đã bị cắt giảm một nửa vào đầu 2023. [oecd-vn-2025:p077:text02]
**Citations:** ['oecd-vn-2025:p077:table_3.2', 'oecd-vn-2025:p077:text02'] | gold hit: True [True]
**Queries:** ['environmental protection tax diesel Vietnam 2024 2025 rate change compared to early 2023 USD per tonne CO2']
**Inspect:** []
**Chi phí/thời gian:** $0.0020 / 23.25s

## T04 [table] - answered
**Q:** Theo mô phỏng của OECD, nếu Việt Nam giảm sở hữu nhà nước xuống mức trung bình OECD thì GDP bình quân đầu người tăng tích lũy bao nhiêu sau 5 năm, sau 10 năm và trong dài hạn?

**Đáp án chuẩn:** Tăng 1,9% sau 5 năm, 2,5% sau 10 năm và 5,0% trong dài hạn.
**Key facts:** 1,9% sau 5 năm; 2,5% sau 10 năm; 5,0% dài hạn
**Dung sai:** chính xác

**Agent:** Theo mô phỏng của OECD, nếu Việt Nam giảm sở hữu nhà nước xuống mức trung bình OECD thì GDP bình quân đầu người tăng tích lũy khoảng 1.9% sau 5 năm, 2.5% sau 10 năm và 5.0% trong dài hạn. [oecd-vn-2025:p039:table_1.4]
**Citations:** ['oecd-vn-2025:p039:table_1.4'] | gold hit: True [True]
**Queries:** ['reduce state ownership to OECD average GDP per capita increase after 5 years 10 years long-run simulation Vietnam']
**Inspect:** []
**Chi phí/thời gian:** $0.0016 / 22.89s

## T05 [table] - answered
**Q:** Trong gói biện pháp tài khoá OECD đề xuất, biện pháp tăng thu nào có tác động lớn nhất (bao nhiêu % GDP), và tổng tác động tài khoá của cả gói là bao nhiêu?

**Đáp án chuẩn:** Tăng thuế suất VAT tiêu chuẩn, +2,5% GDP; tổng tác động tài khoá bằng 0,0% GDP (các biện pháp tăng thâm hụt −6,0% bù bằng các biện pháp giảm thâm hụt +6,0%).
**Key facts:** Raise the standard VAT rate +2,5% GDP; tổng tác động 0,0% GDP
**Dung sai:** chính xác

**Agent:** Biện pháp tăng thu có tác động lớn nhất là “Raise the standard VAT rate” (tăng thuế VAT chuẩn) với +2.5 % GDP. Tổng tác động tài khoá của cả gói là 0.0 % GDP (Deficit-reducing measures +6.0 % GDP; deficit-increasing measures −6.0 % GDP; tổng = 0.0 % GDP). [oecd-vn-2025:p038:table_1.3]
**Citations:** ['oecd-vn-2025:p038:table_1.3'] | gold hit: True [True]
**Queries:** ['fiscal package revenue measures impact percent of GDP proposed revenue measure largest impact percent of GDP OECD Economic Surveys Viet Nam 2025 fiscal package revenue impact', 'Table 1.3 fiscal impact selected recommendations total fiscal impact percent of GDP largest revenue measure percent of GDP "Table 1.3" Viet Nam 2025 fiscal impact package revenue measures']
**Inspect:** []
**Chi phí/thời gian:** $0.0020 / 39.4s

## T06 [table] - answered
**Q:** Theo bảng thống kê cơ bản của Việt Nam năm 2023, tỷ lệ người 25–64 tuổi có trình độ đại học là bao nhiêu, và trung bình OECD là bao nhiêu?

**Đáp án chuẩn:** Việt Nam 14,7%, trung bình OECD 41,0%.
**Key facts:** Việt Nam 14,7%; OECD 41,0%
**Dung sai:** chính xác

**Agent:** Theo bảng "Basic statistics" (Viet Nam, 2023): Tỷ lệ người 25–64 tuổi có trình độ đại học ở Việt Nam là 14.7%; trung bình OECD là 41.0% [oecd-vn-2025:p009:basic_statistics:part1].
**Citations:** ['oecd-vn-2025:p009:basic_statistics:part1'] | gold hit: True [True]
**Queries:** ['share of 25-64 with tertiary education Vietnam 2023 OECD average basic statistics table']
**Inspect:** []
**Chi phí/thời gian:** $0.0016 / 22.12s

## T07 [image] - answered
**Q:** Trong hình so sánh mức méo mó do sự tham gia của nhà nước (thang 0–6) giữa các nước, Việt Nam đứng ở vị trí nào và có giá trị khoảng bao nhiêu? Cột màu xanh lá thể hiện gì và có giá trị khoảng bao nhiêu?

**Đáp án chuẩn:** Việt Nam có giá trị cao nhất trong tất cả các nước (cột đỏ ngoài cùng bên phải), khoảng 4,1; cột xanh lá là trung bình OECD, khoảng 2,2.
**Key facts:** Việt Nam cao nhất; ≈ 4,1; cột xanh lá = OECD; OECD ≈ 2,2
**Dung sai:** ±0,1

**Agent:** Theo biểu đồ “Distortions from state involvement on a scale of 0 to 6”, Việt Nam (VNM) đứng ở vị trí cao nhất trong các nước so sánh (tay cao nhất) và có giá trị khoảng 4.1 (khoảng 4.0–4.2) trên thang 0–6 [oecd-vn-2025:p131:figure_4.27].

Cột màu xanh lá biểu thị giá trị của “OECD” (bar được gắn nhãn OECD) và có giá trị khoảng 2.1–2.2 (khoảng 2.0–2.2) trên cùng thang; trục y chạy từ 0.0 đến 4.5 trên hình [oecd-vn-2025:p131:figure_4.27].
**Citations:** ['oecd-vn-2025:p131:figure_4.27'] | gold hit: True [True]
**Queries:** ["distortions due to state participation scale 0-6 Vietnam figure comparison countries 'state participation' 'distortion' 0-6 OECD Economic Surveys Viet Nam 2025 figure"]
**Inspect:** ['What are the approximate y-axis values for the VNM bar and the OECD (green) bar in this chart? Also confirm the label or meaning of the green bar (what text is printed for it) and the y-axis scale (min and max). Please give values as approximate if read from the figure.']
**Chi phí/thời gian:** $0.0042 / 30.41s

## T08 [image] - answered
**Q:** Theo hình về tiền lương công nhân ngành chế tạo, những nước nào có lương tháng bình quân năm 2024 thấp hơn Việt Nam? Về tăng trưởng lương thực tế bình quân năm từ 2006, Việt Nam xếp thứ mấy và sau nước nào?

**Đáp án chuẩn:** Lào, Myanmar, Campuchia và Philippines có lương thấp hơn Việt Nam (khoảng 300 USD/tháng). Về tăng trưởng lương thực tế, Việt Nam xếp thứ hai (khoảng 5%/năm), chỉ sau Trung Quốc (khoảng 8%/năm).
**Key facts:** LAO, MMR, KHM, PHL thấp hơn; Việt Nam thứ 2 về tăng trưởng lương thực tế; sau Trung Quốc
**Dung sai:** giá trị là xấp xỉ; thứ hạng phải đúng

**Agent:** Theo Hình 4.4 (Panel A), những nước có lương tháng bình quân ngành chế tạo năm 2024 thấp hơn Việt Nam là: LAO (Lào), MMR (Myanmar), KHM (Campuchia) và PHL (Philippines) [oecd-vn-2025:p101:figure_4.4].
Về tăng trưởng lương thực tế bình quân hàng năm từ 2006 (Panel B), Việt Nam xếp thứ 2 trong nhóm được so sánh (thứ tự tăng dần), tức là sau CHN (Trung Quốc) [oecd-vn-2025:p101:figure_4.4].
**Citations:** ['oecd-vn-2025:p101:figure_4.4'] | gold hit: True [True]
**Queries:** ['manufacturing workers average monthly wages 2024 Vietnam figure']
**Inspect:** []
**Chi phí/thời gian:** $0.0028 / 23.35s

## T09 [image] - answered
**Q:** Năm 2023, nguồn phát thải khí nhà kính nào lớn nhất ở Việt Nam và khoảng bao nhiêu triệu tấn CO2 tương đương? Nguồn lớn thứ hai là gì?

**Đáp án chuẩn:** Lớn nhất là ngành điện (Power Industry), khoảng 160 triệu tấn CO2e; thứ hai là đốt nhiên liệu trong công nghiệp (Industrial Combustion), khoảng 108 triệu tấn CO2e.
**Key facts:** Power Industry lớn nhất; ≈ 160 MtCO2e; Industrial Combustion thứ hai
**Dung sai:** ±10% cho giá trị

**Agent:** Theo báo cáo, năm 2023 nguồn phát thải lớn nhất là ngành điện (electricity generation / Power Industry); báo cáo nêu rõ “Electricity generation is the main source of GHG emissions” và lớp Power Industry là lớp lớn nhất trên đồ thị phân rã theo nguồn [oecd-vn-2025:p074:figure_3.2]. Tổng phát thải CO2 của Việt Nam năm 2023 được ước tính khoảng 373 million tCO2 (CO2 cho cả nước) [oecd-vn-2025:p074:text01]. Nguồn lớn thứ hai là industrial combustion (đốt cháy công nghiệp), kế tới là nông nghiệp theo biểu đồ phân lớp [oecd-vn-2025:p074:figure_3.2].
**Citations:** ['oecd-vn-2025:p074:figure_3.2', 'oecd-vn-2025:p074:text01'] | gold hit: True [True]
**Queries:** ['greenhouse gas emissions by source Vietnam 2023 largest source CO2 equivalent sector energy electricity industry agriculture land use change 2023 OECD Economic Surveys Viet Nam 2025', "In 2023 million tCO2eq Power Industry 2023 'million tCO2' 'Vietnam' 'power industry' 2023 OECD 'Figure 3.2' data read from PDF vector coordinates Crippa 2024 'In million tCO2eq' 2023 emissions by sector"]
**Inspect:** []
**Chi phí/thời gian:** $0.0040 / 45.61s

## T10 [image] - answered
**Q:** Trong biểu đồ việc làm theo loại hoạt động ở khu vực xuất khẩu của Việt Nam và các nước so sánh, nước nào được khoanh viền đỏ, nước nào có tỷ trọng lao động quản lý & kỹ thuật cao nhất, và lao động sản xuất chiếm khoảng bao nhiêu % việc làm ở Việt Nam?

**Đáp án chuẩn:** Việt Nam (VNM) được khoanh đỏ; Philippines (PHL) có tỷ trọng quản lý & kỹ thuật cao nhất (khoảng 18%); lao động sản xuất chiếm khoảng 85% ở Việt Nam.
**Key facts:** VNM khoanh đỏ; PHL cao nhất về quản lý & kỹ thuật; sản xuất ≈ 85%
**Dung sai:** ±3 điểm %

**Agent:** - Trong biểu đồ Panel B, nhãn VNM (Việt Nam) được khoanh viền đỏ (red box) [oecd-vn-2025:p112:figure_4.14].
- Nước có tỷ trọng lao động quản lý & kỹ thuật (Managerial & engineering) cao nhất là Philippines (PHL) so với các nước trong đồ thị [oecd-vn-2025:p112:figure_4.14].
- Lao động sản xuất (Production workers) chiếm khoảng 85% việc làm trong khu vực xuất khẩu của Việt Nam (số liệu cho năm 2018, “about 85%”) [oecd-vn-2025:p112:text02] và biểu đồ cũng cho thấy phần Production là thành phần lớn nhất cho VNM (Panel A và B) [oecd-vn-2025:p112:figure_4.14].
**Citations:** ['oecd-vn-2025:p112:figure_4.14', 'oecd-vn-2025:p112:text02'] | gold hit: True [True]
**Queries:** ['employment by activity in export sector Vietnam chart red box management & technical production production share']
**Inspect:** []
**Chi phí/thời gian:** $0.0024 / 21.95s

## T11 [image] - answered
**Q:** Trong so sánh tỷ lệ nghèo theo chuẩn 2,15 USD/ngày giữa các nước, nước nào có tỷ lệ cao nhất (khoảng bao nhiêu %) và cột của Việt Nam (năm 2022) có giá trị khoảng bao nhiêu?

**Đáp án chuẩn:** Philippines (năm 2021) cao nhất, khoảng 6,7–6,8%; Việt Nam (2022, cột đỏ) khoảng 1% (dưới 1%).
**Key facts:** Philippines cao nhất; ≈ 6,8%; Việt Nam ≈ 1% hoặc dưới 1%
**Dung sai:** ±0,3 điểm %

**Agent:** Trong so sánh theo chuẩn USD 2.15/ngày (2017 PPP) ở Hình 2.1, nước có tỷ lệ cao nhất là Philippines (2021) khoảng 7.3% và cột của Việt Nam (2022) có giá trị khoảng 1.8% (giá trị là xấp xỉ, đọc từ Panel B). [oecd-vn-2025:p050:figure_2.1]
**Citations:** ['oecd-vn-2025:p050:figure_2.1'] | gold hit: True [True]
**Queries:** ['poverty rate $2.15 per day by country 2022 Vietnam']
**Inspect:** ['In Panel B, what is the approximate poverty rate (%) value for each country bar? Please give approximate numeric values (%) for Philippines (2021), Indonesia (2023), Fiji (2019), Viet Nam (2022), Mongolia (2022), Thailand (2021), Malaysia (2021), and China (2021). Indicate that values are approximate.']
**Chi phí/thời gian:** $0.0039 / 31.78s

## T12 [chart] - answered
**Q:** Theo biểu đồ hệ số Gini toàn quốc của Việt Nam, chỉ số này giảm mạnh nhất giữa hai năm nào, và giảm từ khoảng bao nhiêu xuống bao nhiêu?

**Đáp án chuẩn:** Giảm mạnh nhất giữa năm 2019 và 2020, từ khoảng 0,423 xuống khoảng 0,375.
**Key facts:** giữa 2019 và 2020; ≈ 0,423; ≈ 0,375
**Dung sai:** ±0,005

**Agent:** Theo biểu đồ hệ số Gini toàn quốc (Panel A, Figure 2.2), Gini giảm mạnh nhất giữa năm 2019 và 2020, từ khoảng 0.421 xuống khoảng 0.378 (giảm khoảng 0.043). [oecd-vn-2025:p051:figure_2.2]
**Citations:** ['oecd-vn-2025:p051:figure_2.2'] | gold hit: True [True]
**Queries:** ['Gini coefficient Vietnam national chart Gini time series OECD Economic Surveys Viet Nam 2025 figure', 'Figure 2.2 Gini coefficient Viet Nam time series 2010 2023 Figure 2.2 income inequality OECD Economic Surveys Viet Nam 2025']
**Inspect:** ['In panel A (Gini index, whole country) please provide the plotted Gini index values for each year from 2018 through 2023 as read from the figure (approximate values are fine). Specify that values are approximate if read from vector coordinates.']
**Chi phí/thời gian:** $0.0050 / 45.62s

## T13 [chart] - answered
**Q:** Khoảng cách tiền lương theo giới của Việt Nam (năm 2023 hoặc gần nhất) là bao nhiêu %, cao hơn mức chung ASEAN bao nhiêu điểm phần trăm, và nước nào có giá trị âm sâu nhất?

**Đáp án chuẩn:** Việt Nam khoảng 12,1%, cao hơn ASEAN (khoảng 9,7%) khoảng 2,4 điểm phần trăm; Philippines có giá trị âm sâu nhất (khoảng −6,1%).
**Key facts:** Việt Nam ≈ 12,1%; ASEAN ≈ 9,7%; chênh ≈ 2,4 điểm %; Philippines âm sâu nhất
**Dung sai:** ±0,3

**Agent:** Theo báo cáo, khoảng cách tiền lương theo giới của Việt Nam được nêu là 11% (gần nhất) [oecd-vn-2025:p064:text03]. Biểu đồ so sánh cho giá trị xấp xỉ 12.1% cho Việt Nam và 9.7% cho trung bình ASEAN, tức Việt Nam cao hơn khoảng 1.3 điểm phần trăm (12.1 − 9.7 ≈ 1.3) (giá trị biểu đồ là xấp xỉ) [oecd-vn-2025:p065:figure_2.11]. Nước có giá trị âm sâu nhất là Philippines (khoảng −6.1%) [oecd-vn-2025:p065:figure_2.11].
**Citations:** ['oecd-vn-2025:p064:text03', 'oecd-vn-2025:p065:figure_2.11'] | gold hit: True [True]
**Queries:** ['gender wage gap Vietnam 2023 ASEAN average country with most negative gender pay gap OECD Economic Surveys Viet Nam 2025']
**Inspect:** []
**Chi phí/thời gian:** $0.0025 / 24.25s

## T14 [chart] - answered
**Q:** Theo khảo sát doanh nghiệp, trở ngại lớn nhất đối với doanh nghiệp Việt Nam là gì (tỷ lệ bao nhiêu %), và tỷ lệ doanh nghiệp Việt Nam coi tiếp cận tài chính là trở ngại chính cao hơn mức trung bình Đông Á – Thái Bình Dương bao nhiêu điểm phần trăm?

**Đáp án chuẩn:** Lớn nhất là các hành vi của khu vực phi chính thức (Informal sector practices), 22%; tiếp cận tài chính ở Việt Nam là 21% so với 12,5% của Đông Á – Thái Bình Dương, cao hơn 8,5 điểm phần trăm.
**Key facts:** Informal sector practices 22%; Access to finance 21% vs 12,5%; chênh 8,5 điểm %
**Dung sai:** ±0,5

**Agent:** Theo khảo sát (World Bank, 2023), trở ngại lớn nhất của doanh nghiệp Việt Nam là “thực hành khu vực phi chính thức” với khoảng 22% doanh nghiệp; “tiếp cận tài chính” là trở ngại đứng thứ hai, khoảng 21% doanh nghiệp. Tỷ lệ doanh nghiệp Việt Nam cho rằng tiếp cận tài chính là trở ngại chính cao hơn mức trung bình Đông Á – Thái Bình Dương khoảng 8.5 điểm phần trăm (21% − 12.5% ≈ 8.5 điểm). [oecd-vn-2025:p127:text02] [oecd-vn-2025:p128:figure_4.25]
**Citations:** ['oecd-vn-2025:p127:text02', 'oecd-vn-2025:p128:figure_4.25'] | gold hit: True [True]
**Queries:** ["main obstacle firms Vietnam enterprise survey biggest obstacle percent 'access to finance' 'East Asia and Pacific' comparison OECD Economic Surveys Viet Nam 2025"]
**Inspect:** []
**Chi phí/thời gian:** $0.0022 / 24.89s

## T15 [chart] - answered
**Q:** Năm 2020, trong bốn nước ở biểu đồ tăng trưởng GDP thực (Malaysia, Indonesia, Thái Lan, Việt Nam), nước nào vẫn tăng trưởng dương và nước nào suy giảm sâu nhất? Cho biết giá trị xấp xỉ.

**Đáp án chuẩn:** Chỉ Việt Nam tăng trưởng dương (khoảng 2,9%); Thái Lan suy giảm sâu nhất (khoảng −6,1%), tiếp theo là Malaysia (khoảng −5,5%).
**Key facts:** chỉ Việt Nam dương ≈ 2,9%; Thái Lan sâu nhất ≈ −6,1%
**Dung sai:** ±0,2

**Agent:** Năm 2020: Việt Nam là nước duy nhất tăng trưởng dương, khoảng +3.0% (khoảng +2.5% đến +3.5%); Malaysia, Indonesia, Thái Lan đều suy giảm; suy giảm sâu nhất là Thái Lan khoảng -6.0% (khoảng -6.5% đến -5.5%). (Malaysia ≈ -5.5%; Indonesia ≈ -2.0%). [oecd-vn-2025:p020:figure_1.1]
**Citations:** ['oecd-vn-2025:p020:figure_1.1'] | gold hit: True [True]
**Queries:** ['real GDP growth Malaysia Indonesia Thailand Vietnam 2020 chart OECD Economic Surveys Viet Nam 2025 figure']
**Inspect:** ["For Panel A 'Real GDP growth', what are the approximate values (percent) of real GDP growth in 2020 for each series: Malaysia (blue), Indonesia (black), Thailand (green), Viet Nam (red)? Please give approximate numbers and indicate if any value is positive or negative."]
**Chi phí/thời gian:** $0.0040 / 29.08s

## T16 [chart] - answered
**Q:** Tỷ lệ lao động phi chính thức chung của Việt Nam giảm từ bao nhiêu % năm 2013 xuống bao nhiêu % năm 2023? Trong các nước Đông Nam Á được so sánh, nước nào có tỷ lệ phi chính thức cao nhất?

**Đáp án chuẩn:** Giảm từ khoảng 79,5% (2013) xuống khoảng 67,7% (2023); Campuchia (số liệu 2019) cao nhất, khoảng 87%.
**Key facts:** ≈ 79,5% năm 2013; ≈ 67,7% năm 2023; Campuchia cao nhất
**Dung sai:** ±1 điểm %

**Agent:** Theo hình A trong Figure 2.5, tỷ lệ lao động phi chính thức “Total” của Việt Nam giảm từ khoảng 80% năm 2013 xuống khoảng 68% năm 2023 (giá trị xấp xỉ từ biểu đồ) [oecd-vn-2025:p057:figure_2.5]. Trong so sánh khu vực (Panel B của Figure 2.5), nước có tỷ lệ phi chính thức cao nhất là Campuchia (Cambodia) [oecd-vn-2025:p057:figure_2.5]; báo cáo cũng nêu informality của Việt Nam cao hơn Malaysia và hơi cao hơn Thái Lan trong phần văn bản [oecd-vn-2025:p057:text01].
**Citations:** ['oecd-vn-2025:p057:figure_2.5', 'oecd-vn-2025:p057:text01'] | gold hit: True [True]
**Queries:** ['informal employment rate Vietnam 2013 2023 Southeast Asia comparison']
**Inspect:** ["What is the approximate 'Total' informality rate for Vietnam in 2013 and 2023 (percent) from panel A? And in panel B, which country has the highest informality rate among Malaysia (2022), Thailand (2023), Viet Nam (2023), Myanmar (2020), Cambodia (2019)?"]
**Chi phí/thời gian:** $0.0030 / 26.97s

## T17 [multihop] - answered
**Q:** Sau cải cách Luật Bảo hiểm xã hội, số năm đóng tối thiểu để được hưởng lương hưu là bao nhiêu năm? Và người sử dụng lao động cùng người lao động hiện đóng tổng cộng bao nhiêu % tiền lương cho quỹ hưu trí và tử tuất?

**Đáp án chuẩn:** Số năm đóng tối thiểu giảm từ 20 xuống 15 năm; tỷ lệ đóng cho hưu trí và tử tuất là 14% (người sử dụng lao động) + 8% (người lao động) = 22% tiền lương.
**Key facts:** 15 năm (giảm từ 20); 14% + 8% = 22%
**Dung sai:** chính xác

**Agent:** Sau cải cách Luật Bảo hiểm xã hội, số năm đóng tối thiểu để được hưởng lương hưu giảm từ 20 xuống còn 15 năm [oecd-vn-2025:p055:text03][oecd-vn-2025:p055:text01].

Người sử dụng lao động và người lao động hiện đóng tổng cộng 22.0% tiền lương cho khoản “Retirement and death” (nghĩa là hưu trí và tử tuất): 14.0% do người sử dụng lao động và 8.0% do người lao động [oecd-vn-2025:p059:table_2.2].
**Citations:** ['oecd-vn-2025:p055:text03', 'oecd-vn-2025:p055:text01', 'oecd-vn-2025:p059:table_2.2'] | gold hit: True [True, True]
**Queries:** ['minimum contribution years pension Social Insurance Law reform Vietnam minimum years pension contribution employer employee contribution rates pension and survivor employer+employee contribution rate Vietnam Social Insurance Law reform OECD Economic Surveys Viet Nam 2025', 'Table 2.2 social insurance rates pension survivor pension and survivor contributions employer employee rates Table 2.2 Viet Nam pension and survivorship contributions OECD Economic Surveys Viet Nam 2025 Table 2.2 page']
**Inspect:** []
**Chi phí/thời gian:** $0.0030 / 41.41s

## T18 [multihop] - answered
**Q:** Dựa vào ngưỡng thu nhập cao của Ngân hàng Thế giới ghi trong hình về mục tiêu 'thu nhập cao' năm 2045 và tỷ lệ giữa ngưỡng này với thu nhập bình quân đầu người năm 2023 của Việt Nam được nêu trong phần văn bản, hãy ước tính thu nhập bình quân đầu người năm 2023 của Việt Nam.

**Đáp án chuẩn:** Ngưỡng thu nhập cao là 13 845 USD (GNI/người, năm 2022) và bằng 3,3 lần thu nhập bình quân đầu người năm 2023 của Việt Nam, nên thu nhập ước tính ≈ 13 845 / 3,3 ≈ 4 200 USD.
**Key facts:** ngưỡng 13 845 USD; 3,3 lần; ≈ 4 200 USD
**Dung sai:** 4 100–4 300 USD

**Agent:** Ước tính:
- Ngưỡng “high-income” (từ hình) ≈ 13 841.4 USD (giá trị đọc từ toạ độ PDF, xấp xỉ) [oecd-vn-2025:p099:figure_4.2].
- Báo cáo nêu ngưỡng này bằng 3.3 lần thu nhập bình quân đầu người năm 2023 của Việt Nam [oecd-vn-2025:p099:text02].
Tính: 13 841.4 ÷ 3.3 = 4 194.06 USD. 
Kết luận: Ước tính thu nhập bình quân đầu người năm 2023 của Việt Nam khoảng 4 194 USD (xấp xỉ) [oecd-vn-2025:p099:figure_4.2] [oecd-vn-2025:p099:text02].
**Citations:** ['oecd-vn-2025:p099:figure_4.2', 'oecd-vn-2025:p099:text02'] | gold hit: True [True, True]
**Queries:** ["World Bank high-income threshold 2045 figure 'high-income' 2045 Viet Nam OECD Economic Surveys 2025 ratio to 2023 GDP per capita"]
**Inspect:** []
**Chi phí/thời gian:** $0.0025 / 24.89s

## T19 [multihop] - answered
**Q:** Nếu áp tỷ lệ nghèo theo chuẩn của nhóm nước thu nhập trung bình thấp (3,65 USD/ngày) nêu trong báo cáo vào dân số Việt Nam năm 2023 trong bảng thống kê cơ bản, thì có khoảng bao nhiêu triệu người nghèo theo chuẩn này?

**Đáp án chuẩn:** Tỷ lệ nghèo theo chuẩn 3,65 USD/ngày là 4,2%; dân số 2023 là 100,3 triệu người; vậy khoảng 4,2 triệu người.
**Key facts:** 4,2%; 100,3 triệu; ≈ 4,2 triệu người
**Dung sai:** 4,1–4,3 triệu

**Agent:** Áp tỷ lệ nghèo USD 3.65/ngày (4.2%) vào dân số Việt Nam 2023 (100.3 triệu) được báo cáo: 100.3 × 4.2% = 4.21326 → khoảng 4.21 triệu người (khoảng 4.2 triệu). [oecd-vn-2025:p009:basic_statistics:part1] [oecd-vn-2025:p050:text02]
**Citations:** ['oecd-vn-2025:p009:basic_statistics:part1', 'oecd-vn-2025:p050:text02'] | gold hit: True [True, True]
**Queries:** ['3.65 USD per day poverty line lower-middle-income 3.65 USD/day Viet Nam 2023 population basic statistics table']
**Inspect:** []
**Chi phí/thời gian:** $0.0022 / 23.72s

## T20 [multihop] - answered
**Q:** Vốn FDI tích luỹ (stock of inward FDI) của Việt Nam năm 2023 trên hình so sánh với các nước ASEAN là khoảng bao nhiêu tỷ USD, và bằng khoảng bao nhiêu % GDP danh nghĩa năm 2023 theo bảng thống kê cơ bản?

**Đáp án chuẩn:** Khoảng 229 tỷ USD; GDP danh nghĩa 2023 là 433,7 tỷ USD, nên vốn FDI tích luỹ bằng khoảng 53% GDP.
**Key facts:** ≈ 229 tỷ USD (đọc hình: 220–235); GDP 433,7 tỷ USD; ≈ 53% GDP (50–55%)
**Dung sai:** FDI 220–235 tỷ USD; tỷ lệ 50–55%

**Agent:** Vốn FDI tích luỹ (stock of inward FDI) của Việt Nam năm 2023 trên hình là khoảng 220–230 tỷ USD (khoảng) [oecd-vn-2025:p100:figure_4.3]. Theo bảng "Basic statistics", GDP danh nghĩa 2023 của Việt Nam là 433.7 tỷ USD; vậy cổ phần này tương đương khoảng (220÷433.7)×100 ≈ 50.7% đến (230÷433.7)×100 ≈ 53.0% của GDP danh nghĩa 2023 (tính toán từ các giá trị trên) [oecd-vn-2025:p009:basic_statistics:part1][oecd-vn-2025:p100:figure_4.3].
**Citations:** ['oecd-vn-2025:p100:figure_4.3', 'oecd-vn-2025:p009:basic_statistics:part1'] | gold hit: True [True, True]
**Queries:** ['stock of inward FDI Vietnam 2023 ASEAN comparison figure', 'basic statistics table Viet Nam stock of inward FDI 2023 % GDP 2023 table basic statistics OECD Viet Nam 2025']
**Inspect:** ["What is the approximate value (billion USD) of Vietnam's inward FDI stock in 2023 as shown on this chart? Please give the value and indicate approximate if necessary."]
**Chi phí/thời gian:** $0.0041 / 49.01s

## T21 [text] - answered
**Q:** Theo báo cáo, Việt Nam đã có bao nhiêu hiệp định thương mại tự do song phương và đa phương, bao nhiêu hiệp định đang đàm phán, và các hiệp định này bao phủ bao nhiêu nước, chiếm bao nhiêu % GDP thế giới?

**Đáp án chuẩn:** 17 FTA song phương và đa phương, thêm 3 hiệp định đang đàm phán; các hiệp định bao phủ 53 nước, chiếm 87% GDP thế giới.
**Key facts:** 17 FTA; 3 đang đàm phán; 53 nước; 87% GDP thế giới
**Dung sai:** chính xác

**Agent:** Theo báo cáo: Việt Nam đã có 17 hiệp định thương mại tự do song phương và plurilateral, và có 3 hiệp định đang đàm phán; các hiệp định này bao phủ 53 nước, chiếm 87% GDP thế giới [oecd-vn-2025:p099:text01]
**Citations:** ['oecd-vn-2025:p099:text01'] | gold hit: True [True]
**Queries:** ['Vietnam free trade agreements number bilateral multilateral negotiating cover countries percent of world GDP']
**Inspect:** []
**Chi phí/thời gian:** $0.0018 / 20.33s

## T22 [text] - answered
**Q:** Thứ hạng của Việt Nam trong Chỉ số Cảm nhận Tham nhũng thay đổi thế nào từ năm 2015 đến năm 2023, và năm 2023 có bao nhiêu quốc gia được xếp hạng?

**Đáp án chuẩn:** Từ hạng 119 năm 2015 lên hạng 83 năm 2023, trên tổng số 180 quốc gia.
**Key facts:** hạng 119 (2015); hạng 83 (2023); 180 quốc gia
**Dung sai:** chính xác

**Agent:** Theo báo cáo, thứ hạng của Việt Nam trong Chỉ số Cảm nhận Tham nhũng (Corruption Perceptions Index) đã cải thiện từ thứ 119 vào năm 2015 lên thứ 83 vào năm 2023; năm 2023 có tổng cộng 180 quốc gia được xếp hạng [oecd-vn-2025:p133:text01] [oecd-vn-2025:p134:figure_4.28].
**Citations:** ['oecd-vn-2025:p133:text01', 'oecd-vn-2025:p134:figure_4.28'] | gold hit: True [True]
**Queries:** ['Corruption Perceptions Index Vietnam ranking 2015 2016 2017 2018 2019 2020 2021 2022 2023 number of countries ranked 2023 Transparency International CPI Vietnam OECD Economic Surveys Viet Nam 2025']
**Inspect:** []
**Chi phí/thời gian:** $0.0025 / 22.8s

## T23 [text] - answered
**Q:** Năm 2024, lương hưu ở Việt Nam được điều chỉnh tăng bao nhiêu % và từ thời điểm nào? Lương tối thiểu tăng bao nhiêu %, và năm 2023 đã tăng bao nhiêu %?

**Đáp án chuẩn:** Lương hưu tăng 15% từ tháng 7/2024 (mức tăng lớn nhất từ trước tới nay); lương tối thiểu tăng 6%, sau khi đã tăng 21% năm 2023.
**Key facts:** lương hưu +15% tháng 7/2024; lương tối thiểu +6%; +21% năm 2023
**Dung sai:** chính xác

**Agent:** - Năm 2024, lương hưu được điều chỉnh tăng 15% và có hiệu lực từ tháng 7/2024. [oecd-vn-2025:p026:text04]
- Lương tối thiểu tăng 6% (năm 2024); năm 2023 lương tối thiểu đã tăng 21%. [oecd-vn-2025:p026:text04]
**Citations:** ['oecd-vn-2025:p026:text04'] | gold hit: True [True]
**Queries:** ['Vietnam pension increase 2024 pension adjustment 2024 effective date Vietnam social insurance pensions 2024 OECD Economic Surveys Viet Nam 2025', 'minimum wage increase 2024 Vietnam minimum wage 2023 2024 OECD Economic Surveys Viet Nam 2025 minimum wage rose 2023 2024 percent']
**Inspect:** []
**Chi phí/thời gian:** $0.0031 / 43.19s

## T24 [text] - answered
**Q:** Báo cáo nêu những số liệu nào về ô nhiễm không khí và xe điện: Hà Nội xếp thứ mấy trong các thành phố ô nhiễm nhất thế giới, nồng độ PM2.5 trung bình năm 2023 của Việt Nam gấp khoảng bao nhiêu lần mức khuyến nghị của WHO, và xe hybrid chiếm bao nhiêu % số xe bán ra trong 9 tháng đầu năm 2024?

**Đáp án chuẩn:** Hà Nội xếp thứ 8; PM2.5 gần gấp 6 lần mức khuyến nghị của WHO; xe hybrid chiếm 3% số xe bán ra từ tháng 1 đến tháng 9/2024.
**Key facts:** thứ 8; gần 6 lần; 3%
**Dung sai:** chính xác

**Agent:** Tóm tắt theo báo cáo OECD:
- Hà Nội được xếp hạng là thành phố ô nhiễm thứ 8 trên thế giới. [oecd-vn-2025:p088:text05]
- Trung bình năm 2023, nồng độ PM2.5 của Việt Nam vào khoảng gần 6 lần mức khuyến nghị của WHO. [oecd-vn-2025:p088:text05]
- Xe hybrid chiếm 3% số xe bán ra trong giai đoạn tháng 1–tháng 9 năm 2024. [oecd-vn-2025:p088:text05]
**Citations:** ['oecd-vn-2025:p088:text05'] | gold hit: True [True, True]
**Queries:** ["Hanoi ranking most polluted cities world PM2.5 Hanoi rank 'most polluted' 'Hanoi' 'PM2.5' 'cities' site:OECD 'Viet Nam' '2025'"]
**Inspect:** []
**Chi phí/thời gian:** $0.0020 / 24.84s

## T25 [unanswerable] - abstained
**Q:** Mức lương tối thiểu vùng I của Việt Nam áp dụng năm 2024 là bao nhiêu đồng/tháng?

**Hành vi mong đợi:** từ chối. Báo cáo chỉ nêu lương tối thiểu tăng 6% (và 21% năm 2023), không nêu mức lương tối thiểu tuyệt đối hay theo vùng.

**Agent:** Searched the report for 'minimum wage' and variants; found mentions of minimum wage increases (6% in 2024) but the report's text does not state the numeric value for regional minimum wage I in 2024. I searched pages: p26-27, p9, p101-102. The document does not contain the specific VND/month amount for region I in 2024.
**Citations:** []
**Queries:** ['minimum wage region I Vietnam 2024 dong per month', 'regional minimum wage 2024 Vietnam minimum wage region I 2024 VND per month statutory minimum wage 2024 Viet Nam region I', "minimum wage 2024 Vietnam region I 'minimum wage region I' '2024' 'VND' 'regional minimum wage'", "minimum regional minimum wage 2024 Vietnam 'region I' 'VND' 'minimum wage 2024' 'regional minimum'"]
**Inspect:** []
**Chi phí/thời gian:** $0.0049 / 88.8s

## T26 [unanswerable] - abstained
**Q:** Hệ số Gini của Việt Nam năm 2024 là bao nhiêu?

**Hành vi mong đợi:** từ chối. Số liệu Gini trong báo cáo chỉ tới năm 2023 (Figure 2.2, văn bản trang PDF 50: 0,37 năm 2023; bảng thống kê cơ bản: năm 2022).

**Agent:** Tài liệu OECD Economic Surveys: Viet Nam 2025 does not state a Gini coefficient for 2024. I searched for "Gini coefficient Vietnam 2024" and "Gini 2024 Viet Nam 2024 Gini coefficient 2024 Vietnam OECD 2025 report"; the report provides Gini for 2023 (0.37) [oecd-vn-2025:p050:text04] and Gini for 2022 (0.374) in the Basic statistics table [oecd-vn-2025:p009:basic_statistics:part2], and the figure on income inequality (Figure 2.2) shows data up to 2023 [oecd-vn-2025:p051:figure_2.2]. The report does not contain a 2024 Gini value.
**Citations:** []
**Queries:** ['Gini coefficient Vietnam 2024', 'Gini 2024 Viet Nam 2024 Gini coefficient 2024 Vietnam OECD 2025 report']
**Inspect:** []
**Chi phí/thời gian:** $0.0032 / 46.7s

## T27 [unanswerable] - abstained
**Q:** Xe điện thuần (BEV) chiếm chính xác bao nhiêu % số xe mới bán ra tại Việt Nam trong 9 tháng đầu năm 2024?

**Hành vi mong đợi:** từ chối. Báo cáo chỉ nói xe hybrid chiếm 3% và xe điện thuần chiếm 'một tỷ lệ không đáng kể' (marginal proportion), không có con số.

**Agent:** Tài liệu đã được tìm kiếm trong báo cáo OECD Economic Surveys: Viet Nam 2025. Tôi đã tìm các đoạn chứa 'pure electric', 'EV', 'battery electric', 'BEV', 'January-September 2024', 'January-September' và 'hybrid'. Kết quả: báo cáo nêu rõ chỉ 3% là hybrid (January-September 2024) và ghi rằng 'pure electric vehicles (EVs) representing only a marginal proportion of sales of new vehicles' nhưng không cho tỉ lệ phần trăm chính xác cho BEV trong 9 tháng đầu năm 2024. Các chunk đã kiểm tra: oecd-vn-2025:p088:text05 và oecd-vn-2025:p089:text02. Do báo cáo không cung cấp giá trị phần trăm chính xác cho BEV trong giai đoạn này, tôi không thể cung cấp con số và không suy đoán.
**Citations:** []
**Queries:** ['battery electric vehicles share new car sales Vietnam Jan-Sep 2024 percentage', "BEV share new vehicle sales Vietnam January-September 2024 'battery electric' 'January-September 2024' '9 months' Vietnam sales", "pure electric vehicles share 'January-September 2024' 'Vietnam' 'pure electric' 'share of new vehicles' percent '9 months' 'BEV'"]
**Inspect:** []
**Chi phí/thời gian:** $0.0043 / 71.24s

## T28 [unanswerable] - abstained
**Q:** Giá bán lẻ điện bình quân của EVN năm 2024 là bao nhiêu đồng/kWh?

**Hành vi mong đợi:** từ chối. Báo cáo chỉ nói giá điện do nhà nước điều tiết, có trợ giá chéo, và nêu giá FiT cho điện tái tạo (USD/kWh), không có giá bán lẻ bình quân.

**Agent:** Tài liệu OECD Economic Surveys: Viet Nam 2025 đã được tìm kiếm với các truy vấn sau nhưng không tìm thấy giá bán lẻ điện bình quân của EVN năm 2024 (VND/kWh):
- "EVN retail electricity price 2024 VND/kWh average retail price 2024 Vietnam EVN 2024 electricity tariff"
- "average retail electricity price 2024 VND/kWh EVN average retail tariff 2024 Viet Nam Electricity retail price 2024 VND/kWh 'average retail' 'EVN' 2024 site:OECD"
- "average retail electricity price EVN 2024 'VND/kWh' 'retail tariff' 'EVN' 2024 'retail price per kWh' Viet Nam 2024 electricity retail price EVN 'VND/kWh'"
Các chunks đã kiểm tra: text trên trang 85-87 về EVN, bảng thống kê cơ bản, và Bảng 3.2; không thấy con số VND/kWh cho giá bán lẻ điện năm 2024.
**Citations:** []
**Queries:** ['EVN retail electricity price 2024 VND/kWh average retail price 2024 Vietnam EVN 2024 electricity tariff', "average retail electricity price 2024 VND/kWh EVN average retail tariff 2024 Viet Nam Electricity retail price 2024 VND/kWh 'average retail' 'EVN' 2024 site:OECD", "average retail electricity price EVN 2024 'VND/kWh' 'retail tariff' 'EVN' 2024 'retail price per kWh' Viet Nam 2024 electricity retail price EVN 'VND/kWh'"]
**Inspect:** []
**Chi phí/thời gian:** $0.0033 / 70.5s

## T29 [unanswerable] - abstained
**Q:** Năm 2024 Việt Nam xuất khẩu bao nhiêu tấn cà phê?

**Hành vi mong đợi:** từ chối. Báo cáo chỉ nhắc Tây Nguyên là vùng trồng cà phê bị hạn hán kéo dài, không có số liệu sản lượng hay xuất khẩu cà phê.

**Agent:** I could not find any figure or table specifying Vietnam coffee export quantity in tonnes for 2024 in the OECD Economic Surveys: Viet Nam 2025. I searched the report for terms: "coffee exports 2024", "coffee exports 2024 tonnes", "Vietnam coffee 2024", and inspected chapters on trade and basic statistics; no chunk with coffee export tonnage was present in the search results (checked text chunks p.1, p.9, p.12, p.21-23).
**Citations:** []
**Queries:** ['Vietnam coffee exports 2024 tonnes coffee exports 2024 Vietnam OECD Economic Surveys Viet Nam 2025', 'coffee exports 2024 tonnes Vietnam "coffee" "2024" exports tonnes OECD Economic Surveys Viet Nam 2025', "Vietnam coffee exports tonnes 2024 'coffee exports' '2024' 'tonnes' site: oecd 'Viet Nam 2025' 'coffee'", "coffee exports Vietnam 2024 'coffee' 'export' '2024' 'tonnes' 'Viet Nam' 'OECD Economic Surveys'"]
**Inspect:** []
**Chi phí/thời gian:** $0.0038 / 88.69s

## T30 [unanswerable] - abstained
**Q:** Tỷ lệ thất nghiệp của Thành phố Hồ Chí Minh năm 2024 là bao nhiêu?

**Hành vi mong đợi:** từ chối. Báo cáo chỉ có tỷ lệ thất nghiệp cấp quốc gia (Table 1.1, Table 1, bảng thống kê cơ bản), không có số liệu theo tỉnh/thành phố.

**Agent:** Không tìm thấy trong báo cáo OECD Economic Surveys: Viet Nam 2025 thông tin về tỷ lệ thất nghiệp riêng cho Thành phố Hồ Chí Minh năm 2024. Đã tìm các từ khóa: "Ho Chi Minh City unemployment rate 2024", "Ho Chi Minh" "unemployment rate" "2024" trong tài liệu; tìm thấy chỉ số thất nghiệp ở cấp quốc gia (Viet Nam) cho 2024 nhưng không có số cho TP. HCM.
**Citations:** []
**Queries:** ['Ho Chi Minh City unemployment rate 2024 OECD Economic Surveys Viet Nam 2025', "Ho Chi Minh City unemployment rate 2024 Labour Force Survey Ho Chi Minh 2024 'unemployment rate' 'Ho Chi Minh' OECD Vietnam 2025", "Ho Chi Minh City unemployment rate 2024 'Ho Chi Minh' 'unemployment rate' '2024' Viet Nam 2025 OECD", '"Ho Chi Minh" unemployment rate 2024 "city" "unemployment" Viet Nam 2025 \'Ho Chi Minh City\' rate 2024 labour force survey \'Ho Chi Minh\'']
**Inspect:** []
**Chi phí/thời gian:** $0.0047 / 89.6s
