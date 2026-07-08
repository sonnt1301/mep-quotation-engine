# Báo Cáo Tính Khả Thi Bóc Tách Bảng Hệ Thống – ABB Batch Benchmark

## 1. Kết Quả Tổng Hợp Chân Thực
* **Tổng số trang thử nghiệm**: 13 trang
* **Số trang đạt trạng thái PASS (Valid >= 10 và Tỷ Lệ Lỗi <= 5%)**: 4 trang
* **Số trang đạt trạng thái PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: 9 trang
* **Số trang thất bại (FAIL / Lỗi)**: 0 trang
* **Tổng số vật tư thô (Raw)**: 886 items
* **Tổng số vật tư hợp lệ (Valid)**: 681 items
* **Tổng số vật tư lỗi (Invalid)**: 205 items
* **Trạng thái đánh giá toàn cục**: **PARTIAL**

## 2. Bảng Thống Kê Chi Tiết Theo Trang
| Trang | Trạng Thái | Raw Items | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Lý Do / Lỗi Ghi Nhận |
| --- | --- | --- | --- | --- | --- | --- |
| 18 | PASS | 96 | 92 | 4 | 4.2% | material_code_empty, material_code_invalid_format, unit_price_zero_or_negative |
| 19 | PASS | 96 | 92 | 4 | 4.2% | material_code_empty, material_code_invalid_format, unit_price_zero_or_negative |
| 20 | PARTIAL | 74 | 54 | 20 | 27.0% | material_code_empty, material_code_invalid_format, material_code_too_long_merged, unit_price_zero_or_negative |
| 21 | PARTIAL | 80 | 50 | 30 | 37.5% | material_code_invalid_format, unit_price_zero_or_negative |
| 32 | PARTIAL | 104 | 98 | 6 | 5.8% | material_code_empty, material_code_invalid_format, unit_price_zero_or_negative |
| 33 | PARTIAL | 66 | 30 | 36 | 54.5% | material_code_empty, material_code_invalid_format, unit_price_zero_or_negative |
| 34 | PARTIAL | 44 | 38 | 6 | 13.6% | material_code_empty, material_code_invalid_format, unit_price_zero_or_negative |
| 41 | PARTIAL | 46 | 8 | 38 | 82.6% | material_code_invalid_format, material_code_too_long_merged, unit_price_zero_or_negative |
| 42 | PARTIAL | 46 | 8 | 38 | 82.6% | material_code_invalid_format, material_code_too_long_merged, unit_price_zero_or_negative |
| 52 | PARTIAL | 87 | 68 | 19 | 21.8% | material_code_empty, material_code_invalid_format, type_cannot_be_price, unit_price_zero_or_negative |
| 53 | PARTIAL | 49 | 46 | 3 | 6.1% | material_code_invalid_format, material_code_too_long_merged, unit_price_zero_or_negative |
| 54 | PASS | 49 | 48 | 1 | 2.0% | unit_price_zero_or_negative |
| 61 | PASS | 49 | 49 | 0 | 0.0% | None |


## 3. Dòng Dữ Liệu Hợp Lệ Mẫu (20 Dòng Đầu)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) | Đơn Vị |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Trang 18 | 1SDA066799R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 16A 18KA | 3P | 16 | 2,584,800 | cái |
| 2 | Trang 18 | 1SDA066810R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 16A 18KA | 4P | 16 | 3,362,400 | cái |
| 3 | Trang 18 | 1SDA066800R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 20A 18KA | 3P | 20 | 2,584,800 | cái |
| 4 | Trang 18 | 1SDA066811R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 20A 18KA | 4P | 20 | 3,362,400 | cái |
| 5 | Trang 18 | 1SDA066801R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 25A 18KA | 3P | 25 | 2,584,800 | cái |
| 6 | Trang 18 | 1SDA066812R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 25A 18KA | 4P | 25 | 3,362,400 | cái |
| 7 | Trang 18 | 1SDA066802R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 32A 18KA | 3P | 32 | 2,584,800 | cái |
| 8 | Trang 18 | 1SDA066813R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 32A 18KA | 4P | 32 | 3,362,400 | cái |
| 9 | Trang 18 | 1SDA066803R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 40A 18KA | 3P | 40 | 2,584,800 | cái |
| 10 | Trang 18 | 1SDA066814R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 40A 18KA | 4P | 40 | 3,362,400 | cái |
| 11 | Trang 18 | 1SDA066804R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 50A 18KA | 3P | 50 | 2,985,600 | cái |
| 12 | Trang 18 | 1SDA066815R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 50A 18KA | 4P | 50 | 3,880,800 | cái |
| 13 | Trang 18 | 1SDA066805R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 63A 18KA | 3P | 63 | 2,985,600 | cái |
| 14 | Trang 18 | 1SDA066816R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 63A 18KA | 4P | 63 | 3,880,800 | cái |
| 15 | Trang 18 | 1SDA066806R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 80A 18KA | 3P | 80 | 2,985,600 | cái |
| 16 | Trang 18 | 1SDA066817R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 80A 18KA | 4P | 80 | 3,880,800 | cái |
| 17 | Trang 18 | 1SDA066807R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 100A 18KA | 3P | 100 | 3,583,200 | cái |
| 18 | Trang 18 | 1SDA066818R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 100A 18KA | 4P | 100 | 4,658,400 | cái |
| 19 | Trang 18 | 1SDA066808R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 125A 18KA | 3P | 125 | 3,760,800 | cái |
| 20 | Trang 18 | 1SDA066888R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 125A 18KA | 4P | 125 | 4,888,800 | cái |


## 4. Các Lỗi Mapping Đã Phát Hiện & Cách Khắc Phục
* **Lệch cột trang 21**: Trang 21 có cấu trúc 3 cột khả năng cắt song song (N, S, H) độc lập thay vì cột 3P/4P của dòng XT Tmax thông dụng. Đã khắc phục bằng cách thiết lập cấu hình tọa độ `three_cutoff_groups_page21` riêng biệt.
* **Ghép bẩn AX trang 61**: Do khoảng cách quá hẹp, model AX50... bị dính liền vào mã sản phẩm `1SBL...`. Đã viết hàm `split_dirty_merged_code` tách model và mã sạch qua Regex.
* **Lẫn lộn cột giá/mô tả trang 52**: Dòng giá của bảng trái bị tràn sang cột lề trái của bảng phải. Đã xử lý bằng cách siết chặt tọa độ X0 nửa phải (`x0 >= 312`) và loại trừ số tiền chứa dấu phẩy ra khỏi description.

## 5. Kết Luận & Khuyến Nghị
* **Độ tin cậy của Coordinate Column Profiler**: Hướng đi bóc tách theo tọa độ word có tính khả thi cao, nhưng đòi hỏi phải thiết kế các **Supplier Profiles** chặt chẽ chứa cấu hình tọa độ X riêng cho từng nhóm trang layout.
* **Đề xuất tiếp theo**: Đánh giá toàn cục ở trạng thái **PARTIAL** phản ánh trung thực rằng một số trang vẫn tồn tại tỷ lệ lỗi mapping cột nhất định và cần bổ sung thêm các bộ profile tinh chỉnh.
