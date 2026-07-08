# Báo Cáo Chạy Kiểm Chứng Config-Run – LS Profile
    
## 1. Lưu Ý Quan Trọng
* **Phạm vi**: Đây là kết quả thực thi bóc tách nạp cấu hình tự động từ tệp JSON cấu hình profile (Milestone D).
* **Trạng thái**: **Chưa tích hợp vào pipeline chính và chưa sẵn sàng cho môi trường Production (Not Production-Ready).**

## 2. Thống Kê Tổng Hợp
* **Tổng số trang bóc tách**: 5 trang
* **Số trang PASS**: 3 trang (60.0%)
* **Tổng số vật tư hợp lệ (Valid)**: 284 items
* **Tổng số vật tư lỗi bị loại (Invalid)**: 16 items
* **Trạng thái toàn cục**: **PARTIAL**

## 3. Chi Tiết Từng Trang
| Trang | Trạng Thái | Dòng Phát Hiện (Raw) | Bỏ Qua (Skipped) | Đưa Vào Validator | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Ghi Nhận Lỗi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | PASS | 72 | 5 | 67 | 67 | 0 | 0.0% | None |
| 2 | PARTIAL | 70 | 28 | 42 | 36 | 6 | 14.3% | material_code_invalid_format, material_code_invalid_prefix |
| 3 | PASS | 79 | 8 | 71 | 69 | 2 | 2.8% | material_code_invalid_prefix |
| 4 | PASS | 84 | 20 | 64 | 62 | 2 | 3.1% | description_contains_price_noise, material_code_invalid_prefix |
| 5 | PARTIAL | 64 | 8 | 56 | 50 | 6 | 10.7% | material_code_invalid_format, material_code_invalid_prefix |

