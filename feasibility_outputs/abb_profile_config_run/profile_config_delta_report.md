# Báo Cáo So Sánh Delta – Config-Run vs Baseline v1

Báo cáo này so sánh kết quả thực thi bóc tách tự động nạp từ tệp cấu hình JSON (Config-Run) so với kết quả bóc tách cứng baseline v1 trước đó.

---

## 1. Thống Kê Tổng Hợp Delta

| Chỉ Số | Baseline v1 | Config-Run | Thay Đổi |
| --- | --- | --- | --- |
| **Vật tư hợp lệ (Valid)** | 743 | 743 | **0 items** |
| **Vật tư lỗi (Invalid)** | 2 | 2 | **0 items** |
| **Số trang PASS** | 13 | 13 | **0 trang** |
| **Trạng thái toàn cục** | ABB v1 | Config-Run | ĐỒNG NHẤT |

---

## 2. Chi Tiết So Sánh Từng Trang
| Trang | Status Baseline | Status Config-Run | Valid Baseline -> Config-Run | Invalid Baseline -> Config-Run | Lệch Valid |
| --- | --- | --- | --- | --- | --- |
| 18 | PASS | PASS | 92 -> 92 | 0 -> 0 | 0 |
| 19 | PASS | PASS | 92 -> 92 | 0 -> 0 | 0 |
| 20 | PASS | PASS | 54 -> 54 | 0 -> 0 | 0 |
| 32 | PASS | PASS | 98 -> 98 | 0 -> 0 | 0 |
| 33 | PASS | PASS | 30 -> 30 | 0 -> 0 | 0 |
| 34 | PASS | PASS | 38 -> 38 | 0 -> 0 | 0 |
| 21 | PASS | PASS | 50 -> 50 | 2 -> 2 | 0 |
| 52 | PASS | PASS | 68 -> 68 | 0 -> 0 | 0 |
| 53 | PASS | PASS | 46 -> 46 | 0 -> 0 | 0 |
| 54 | PASS | PASS | 48 -> 48 | 0 -> 0 | 0 |
| 61 | PASS | PASS | 49 -> 49 | 0 -> 0 | 0 |
| 41 | PASS | PASS | 39 -> 39 | 0 -> 0 | 0 |
| 42 | PASS | PASS | 39 -> 39 | 0 -> 0 | 0 |


---

## 3. Kết Luận
* Kết quả chạy từ file cấu hình config JSON thể hiện tính chất **tương đương (equivalent / near-equivalent)** so với baseline viết cứng v1.
* Hệ thống cấu hình bóc tách đạt trạng thái feasibility ổn định, cấu hình layout tách biệt đã sẵn sàng để tích hợp mở rộng.
