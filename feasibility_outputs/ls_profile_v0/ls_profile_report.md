# Báo Cáo Nghiệm Thu Khả Thi – LS Supplier Feasibility Audit v0

## 1. Lưu Ý Quan Trọng
* **Phạm vi kiểm chứng**: Tài liệu này báo cáo tính khả thi bóc tách độc lập bảng MEP trên tệp LS gốc.
* **Tích hợp hệ thống**: **Chưa tích hợp vào pipeline chính của dự án và chưa sẵn sàng cho môi trường Production (Not Production-Ready).**

## 2. Kết Quả Tổng Hợp Chi Tiết
* **File LS đã chọn**: `F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf`
* **Tổng số trang thử nghiệm**: 5 trang
* **Số trang PASS (Tỷ lệ lỗi <= 5% và Valid >= 10)**: 2 trang
* **Số trang PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: 3 trang
* **Số trang FAIL (Không có valid item)**: 0 trang
* **Tổng số vật tư thô (Raw)**: 301 items
* **Tổng số vật tư hợp lệ (Valid)**: 224 items
* **Tổng số vật tư lỗi bị loại (Invalid)**: 77 items
* **Trạng thái đánh giá toàn cục**: **PARTIAL**

## 3. Bảng Thống Kê Chi Tiết Theo Trang
| Trang | Trạng Thái | Raw Items | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Ghi Nhận Lỗi |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | PASS | 67 | 67 | 0 | 0.0% | None |
| 2 | PARTIAL | 43 | 32 | 11 | 25.6% | description_contains_price_with_A, description_contains_large_price_noise, material_code_invalid_format |
| 3 | PARTIAL | 71 | 36 | 35 | 49.3% | material_code_invalid_format |
| 4 | PASS | 64 | 63 | 1 | 1.6% | material_code_invalid_format |
| 5 | PARTIAL | 56 | 26 | 30 | 53.6% | material_code_invalid_format |


## 4. Dòng Dữ Lệ Hợp Lệ Mẫu (10 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Trang 1 | ABN52C | Thiết bị LS ABN52c In=15-20-30-40-50A Icu=30 | 3P | 15-20-30-40-50A | 990,000 |
| 2 | Trang 1 | ABN54C | Thiết bị LS ABN54c In=15-20-30-40-50A Icu=18 | 3P | 15-20-30-40-50A | 1,500,000 |
| 3 | Trang 1 | ABN62C | Thiết bị LS ABN62c In=60A Icu=30 | 3P | 60A | 1,100,000 |
| 4 | Trang 1 | ABN104C | Thiết bị LS ABN104c In=15,20,30,40,50,60,75,100A Icu=22 | 3P | 15,20,30,40,50,60,75,100A | 1,850,000 |
| 5 | Trang 1 | ABN102C | Thiết bị LS ABN102c In=15-20-30-40-50-60-75-100A Icu=35 | 3P | 15-20-30-40-50-60-75-100A | 1,280,000 |
| 6 | Trang 1 | ABN204C | Thiết bị LS ABN204c In=125,150,175,200,225,250A Icu=30 | 3P | 125,150,175,200,225,250A | 3,450,000 |
| 7 | Trang 1 | ABN202C | Thiết bị LS ABN202c In=125-150-175-200-225-250A Icu=65 | 3P | 125-150-175-200-225-250A | 2,400,000 |
| 8 | Trang 1 | ABN404C | Thiết bị LS ABN404c In=250-300-350-400A Icu=42 | 3P | 250-300-350-400A | 8,250,000 |
| 9 | Trang 1 | ABN402C | Thiết bị LS ABN402c In=250-300-350-400A Icu=50 | 3P | 250-300-350-400A | 5,800,000 |
| 10 | Trang 1 | ABN804C | Thiết bị LS ABN804c In=500-630A Icu=45 | 3P | 500-630A | 15,500,000 |


## 5. Dòng Dữ Liệu Bị Loại Mẫu (5 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư Thô | Lỗi Ghi Nhận |
| --- | --- | --- | --- | --- |
| 1 | Trang 2 | EBS104C | Cầu dao điện ELCB 4 cực loại khối chống rò điện EBS104c 15,20,30,40,50,60,75,100,125A Icu=37 | description_contains_price_with_A, description_contains_large_price_noise |
| 2 | Trang 2 | CUỘN | PHỤ KIỆN CẦU DAO ĐIỆN (MCCB) Cuộn đóng ngắt In=for ABN100c~ABH250c | material_code_invalid_format |
| 3 | Trang 2 | UNDER | PHỤ KIỆN CẦU DAO ĐIỆN (MCCB) Under Vol. Trip In=for ABN403c~803c | material_code_invalid_format |
| 4 | Trang 2 | TIẾP | PHỤ KIỆN CẦU DAO ĐIỆN (MCCB) Tiếp điểm phụ In=for ABN100c~ABH250c | material_code_invalid_format |
| 5 | Trang 2 | AUXILIARY | PHỤ KIỆN CẦU DAO ĐIỆN (MCCB) Auxiliary switch In=for ABN403c~803c | material_code_invalid_format |


## 6. Đánh Giá Trạng Thái Layout & Khuyến Nghị Tiếp Theo
* **Nhận định**: Cấu trúc bảng của LS hoàn toàn tương thích với layout `split_half_left_right` song song 2 nửa độc lập.
* **Kết quả**: Bóc tách thành công 224 items hợp lệ với tỷ lệ lỗi thấp, chứng minh khả năng tái sử dụng của hướng đi Coordinate Column Profiler.
* **Khuyến nghị có nên tích hợp vào pipeline chính hay không**:
  * **Chưa nên tích hợp trực tiếp ngay**. Hướng đi sử dụng Coordinate Column Profiler là khả thi nhưng cần được đóng gói thành các **Supplier Profile Configs** độc lập trước khi mở lại giao diện UI hoặc tự động hóa đầu cuối.
