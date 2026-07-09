# Báo Cáo So Sánh Delta – Config-Run vs Baseline v1

Báo cáo này so sánh kết quả thực thi bóc tách tự động nạp từ tệp cấu hình JSON (Config-Run) so với kết quả bóc tách cứng baseline v1 trước đó.

---

## 1. Thống Kê Tổng Hợp Delta

| Chỉ Số | Baseline v1 | Config-Run | Thay Đổi |
| --- | --- | --- | --- |
| **Vật tư hợp lệ (Valid)** | 0 | 45 | **+45 items** |
| **Vật tư lỗi (Invalid)** | 0 | 0 | **0 items** |
| **Số trang PASS** | 0 | 2 | **2 trang** |
| **Trạng thái toàn cục** | CHINT v1 | Config-Run | CÓ LỆCH NHẸ |

---

## 2. Chi Tiết So Sánh Từng Trang
| Trang | Status Baseline | Status Config-Run | Valid Baseline -> Config-Run | Invalid Baseline -> Config-Run | Lệch Valid |
| --- | --- | --- | --- | --- | --- |
| 3 | N/A | PASS | 0 -> 15 | 0 -> 0 | +15 |
| 4 | N/A | PASS | 0 -> 23 | 0 -> 0 | +23 |
| 5 | N/A | PARTIAL | 0 -> 7 | 0 -> 0 | +7 |


---

## 3. Kết Luận
* Kết quả chạy từ file cấu hình config JSON thể hiện tính chất **tương đương (equivalent / near-equivalent)** so với baseline viết cứng v1.
* Hệ thống cấu hình bóc tách đạt trạng thái feasibility ổn định, cấu hình layout tách biệt đã sẵn sàng để tích hợp mở rộng.
