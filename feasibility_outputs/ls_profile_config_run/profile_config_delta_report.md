# Báo Cáo So Sánh Delta – Config-Run vs Baseline v1

Báo cáo này so sánh kết quả thực thi bóc tách tự động nạp từ tệp cấu hình JSON (Config-Run) so với kết quả bóc tách cứng baseline v1 trước đó.

---

## 1. Thống Kê Tổng Hợp Delta

| Chỉ Số | Baseline v1 | Config-Run | Thay Đổi |
| --- | --- | --- | --- |
| **Vật tư hợp lệ (Valid)** | 282 | 284 | **+2 items** |
| **Vật tư lỗi (Invalid)** | 19 | 16 | **-3 items** |
| **Số trang PASS** | 3 | 3 | **0 trang** |
| **Trạng thái toàn cục** | LS v1 | Config-Run | CÓ LỆCH NHẸ |

---

## 2. Chi Tiết So Sánh Từng Trang
| Trang | Status Baseline | Status Config-Run | Valid Baseline -> Config-Run | Invalid Baseline -> Config-Run | Lệch Valid |
| --- | --- | --- | --- | --- | --- |
| 1 | PASS | PASS | 67 -> 67 | 0 -> 0 | 0 |
| 2 | PARTIAL | PARTIAL | 33 -> 36 | 10 -> 6 | +3 |
| 3 | PASS | PASS | 69 -> 69 | 2 -> 2 | 0 |
| 4 | PASS | PASS | 63 -> 62 | 1 -> 2 | -1 |
| 5 | PARTIAL | PARTIAL | 50 -> 50 | 6 -> 6 | 0 |


---

## 3. Kết Luận
* Kết quả chạy từ file cấu hình config JSON thể hiện tính chất **tương đương (equivalent / near-equivalent)** so với baseline viết cứng v1.
* Hệ thống cấu hình bóc tách đạt trạng thái feasibility ổn định, cấu hình layout tách biệt đã sẵn sàng để tích hợp mở rộng.
