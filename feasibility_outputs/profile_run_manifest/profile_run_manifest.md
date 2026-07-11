# Báo Cáo Profile Run Manifest – Milestone H

Báo cáo này tổng hợp kết quả chạy bóc tách (Profile Run Manifest) và đánh giá độ sẵn sàng tích hợp (Integration Readiness) cho cả ba nhà cung cấp **ABB**, **LS** và **CHINT**.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thông Tin Chung

* **Trạng Thái Benchmark**: `PASS`
* **Thời Gian Khởi Tạo**: `2026-07-11T09:30:22.995894Z`
* **Giai Đoạn Dự Án**: `Feasibility Reset`

---

## 2. Kết Quả Nghiệm Thu Chi Tiết Theo Nhà Cung Cấp

| Nhà Cung Cấp | Trạng Thái | Số Vật Tư Hợp Lệ | Số Vật Tư Bị Loại | Trang PASS | Trang PARTIAL | Tổng Số Trang |
| --- | --- | --- | --- | --- | --- | --- |
| **ABB** | `PASS` | 743 | 2 | 13 | 0 | 13 |
| **LS** | `ACCEPTED_WITH_KNOWN_LIMITATIONS` | 284 | 16 | 3 | 2 | 5 |
| **CHINT** | `ACCEPTED_WITH_KNOWN_LIMITATIONS` | 45 | 0 | 2 | 1 | 3 |

---

## 3. Các Giới Hạn Đã Biết (Known Limitations) & Ghi Chú Tinh Chỉnh

### Hãng ABB
* **Tinh chỉnh chất lượng**: N/A - Bóc tách chính xác 100% các dòng dữ liệu thiết bị.
* **Giới hạn kỹ thuật**:
  * Không có giới hạn nghiêm trọng.

### Hãng LS
* **Tinh chỉnh chất lượng**: Giữ nguyên known limitation cho phụ kiện MCCB (Trang 2) và phụ kiện ACB (Trang 5) để tránh regression cho thiết bị chính.
* **Giới hạn kỹ thuật**:
  * Trang 2, 5 vẫn ở trạng thái PARTIAL và cần tiếp tục tinh chỉnh trong tương lai.
  * Các dòng phụ kiện (accessories) bị chồng lấn tọa độ với layout MCCB chính trên cùng layout split_half_left_right, chưa harden để tránh regression cho thiết bị chính.

### Hãng CHINT
* **Tinh chỉnh chất lượng**: Bổ sung bộ lọc tiêu đề rác tiếng Việt ('tiêu chuẩn:', 'định mức:', 'số pha:', 'đơn giá', 'iđm (a)', 'icu:') giúp nâng chất lượng Trang 3 từ PARTIAL lên PASS (0% lỗi).
* **Giới hạn kỹ thuật**:
  * Trang 5 vẫn ở trạng thái PARTIAL và cần tiếp tục tinh chỉnh trong tương lai.
  * Trang 5 rơ le nhiệt chỉ có 7 dòng thiết bị hợp lệ thực tế, thấp hơn ngưỡng PASS tối thiểu (10 dòng); không hạ tiêu chí threshold để làm đẹp báo cáo.

---

## 4. Đánh Giá Độ Sẵn Sàng Tích Hợp (Integration Readiness)

* **Sẵn sàng tích hợp vào main pipeline**: **`FALSE`**
* **Lý do**: Vẫn còn các giới hạn đã biết (known limitations) về các trang PARTIAL (LS Trang 2 & 5, CHINT Trang 5) và chưa xây dựng/kiểm thử mô-đun cầu nối tích hợp (Integration Bridge).
* **Công việc yêu cầu cho phase tiếp theo**: Thiết kế mô-đun cầu nối tích hợp (Integration Bridge) để chuyển đổi dữ liệu từ Coordinate Column Profiler sang pipeline chuẩn hóa chính, đồng thời tiếp tục tinh chỉnh layout nếu cần.

---

## 5. Danh Sách Không Thực Hiện Ở Giai Đoạn Này (Non-Goals)

* Không sửa đổi Streamlit UI trong phase hiện tại
* Không tích hợp trực tiếp vào main pipeline hiện tại khi chưa được kiểm thử
* Không bổ sung thêm nhà cung cấp mới
* Không sử dụng OCR, AI/LLM hay parse Excel
* Không tuyên bố hệ thống đã sẵn sàng vận hành thực tế (Not Ready for Production)