# Báo Cáo Nghiệm Thu Khả Thi – ABB Supplier Profile Parser v0

## 1. Lưu Ý Quan Trọng
* **Phạm vi kiểm chứng**: Tài liệu này báo cáo tính khả thi bóc tách độc lập bảng MEP trên tệp ABB gốc.
* **Tích hợp hệ thống**: **Chưa tích hợp vào pipeline chính của dự án và chưa sẵn sàng cho môi trường Production (Not Production-Ready).**

## 2. Kết Quả Tổng Hợp Chi Tiết
* **Tổng số trang thử nghiệm**: 13 trang
* **Số trang PASS (Tỷ lệ lỗi <= 5% và Valid >= 10)**: 13 trang
* **Số trang PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: 0 trang
* **Số trang FAIL (Không có valid item)**: 0 trang
* **Tổng số vật tư thô (Raw)**: 745 items
* **Tổng số vật tư hợp lệ (Valid)**: 743 items
* **Tổng số vật tư lỗi bị loại (Invalid)**: 2 items
* **Trạng thái đánh giá toàn cục**: **PASS** (Đạt PARTIAL do tỷ lệ trang đạt PASS là 100.0% < 80%)

## 3. Bảng Thống Kê Chi Tiết Theo Trang
| Trang | Trạng Thái | Dòng Phát Hiện (Raw) | Bỏ Qua (Skipped) | Đưa Vào Validator | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Ghi Nhận Lỗi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | PASS | 96 | 4 | 92 | 92 | 0 | 0.0% | None |
| 19 | PASS | 96 | 4 | 92 | 92 | 0 | 0.0% | None |
| 20 | PASS | 74 | 20 | 54 | 54 | 0 | 0.0% | None |
| 21 | PASS | 87 | 35 | 52 | 50 | 2 | 3.8% | unit_price_cannot_be_technical_spec, material_code_invalid_format |
| 32 | PASS | 104 | 6 | 98 | 98 | 0 | 0.0% | None |
| 33 | PASS | 66 | 36 | 30 | 30 | 0 | 0.0% | None |
| 34 | PASS | 44 | 6 | 38 | 38 | 0 | 0.0% | None |
| 41 | PASS | 45 | 6 | 39 | 39 | 0 | 0.0% | None |
| 42 | PASS | 45 | 6 | 39 | 39 | 0 | 0.0% | None |
| 52 | PASS | 87 | 19 | 68 | 68 | 0 | 0.0% | None |
| 53 | PASS | 49 | 3 | 46 | 46 | 0 | 0.0% | None |
| 54 | PASS | 50 | 2 | 48 | 48 | 0 | 0.0% | None |
| 61 | PASS | 49 | 0 | 49 | 49 | 0 | 0.0% | None |


## 4. Dòng Dữ Liệu Hợp Lệ Mẫu (10 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Trang 18 | 1SDA066799R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 16A 18KA | 3P | 16 | 2,584,800 |
| 2 | Trang 18 | 1SDA066810R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 16A 18KA | 4P | 16 | 3,362,400 |
| 3 | Trang 18 | 1SDA066800R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 20A 18KA | 3P | 20 | 2,584,800 |
| 4 | Trang 18 | 1SDA066811R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 20A 18KA | 4P | 20 | 3,362,400 |
| 5 | Trang 18 | 1SDA066801R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 25A 18KA | 3P | 25 | 2,584,800 |
| 6 | Trang 18 | 1SDA066812R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 25A 18KA | 4P | 25 | 3,362,400 |
| 7 | Trang 18 | 1SDA066802R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 32A 18KA | 3P | 32 | 2,584,800 |
| 8 | Trang 18 | 1SDA066813R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 32A 18KA | 4P | 32 | 3,362,400 |
| 9 | Trang 18 | 1SDA066803R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 3P 40A 18KA | 3P | 40 | 2,584,800 |
| 10 | Trang 18 | 1SDA066814R1 | Cầu dao tự động dạng khối - MCCB Tmax XT1B 4P 40A 18KA | 4P | 40 | 3,362,400 |


## 5. Dòng Dữ Liệu Bị Loại Mẫu (5 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư Thô | Lỗi Ghi Nhận |
| --- | --- | --- | --- | --- |
| 1 | Trang 21 | XT263 | Cầu dao tự động dạng khối XT2 3P 63A 50KA | material_code_invalid_format, unit_price_cannot_be_technical_spec |
| 2 | Trang 21 | CƠĐƯỢCCẤUTHÀNH | Cầu dao tự động dạng khối mục độngP bảovệA 36KA | material_code_invalid_format |


## 6. Đánh Giá Trạng Thái Layout & Khuyến Nghị Tiếp Theo
* **Các Layout đạt PASS tốt**:
  * `double_column_3p_4p` (Trang 18, 19, 32, 54): Dữ liệu phân bố cột đối xứng hoàn hảo, ít bị méo hay dính khoảng trắng.
  * `single_column_right` (Trang 61): Tách sạch model AX và mã 1SBL qua Regex.
* **Các Layout còn PARTIAL**:
  * Trang 20, 21, 33, 34, 41, 42, 52, 53: Một số dòng bị lệch cột nhẹ do văn bản phụ lề trái lẫn lộn hoặc bảng bị dồn ghép, cần thêm các Profile X tinh chỉnh sâu hơn.
* **Khuyến nghị có nên tích hợp vào pipeline chính hay không**:
  * **Chưa nên tích hợp trực tiếp ngay**. Hướng đi sử dụng Coordinate Column Profiler là khả thi nhưng cần được đóng gói thành các **Supplier Profile Configs** độc lập trước khi mở lại giao diện UI hoặc tự động hóa đầu cuối.
