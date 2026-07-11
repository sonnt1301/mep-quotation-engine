# Kế Hoạch Triển Khai – Phase 2G – Master Review Resolution Package

Kế hoạch này triển khai gói review/resolution cho các kết quả master matching có vấn đề, cung cấp các template CSV và Excel (có tích hợp dropdown validation) để reviewer phân xử các dòng trùng lặp, cảnh báo đơn giá/mô tả trước khi sang Phase tiếp theo.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Master Review Resolution Package**.
> * **Không ghi dữ liệu vào database và không thay đổi dữ liệu thật.**
> * **Không set ready_for_write_plan = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Master Review Resolution Package

### A. Giao diện & Kết xuất
* **Resolution script**: [export_profile_master_review_resolution.py](file:///D:/mep_quotation_pipeline/tools/feasibility/export_profile_master_review_resolution.py) (Lọc dữ liệu có cảnh báo từ đối chiếu master để đóng gói resolution).
* **Ràng buộc an toàn & Logic**:
  - Không đọc trực tiếp từ raw bridge items hay tệp blocked của adapter. Chỉ phân tích kết quả đối chiếu master.
  - Lọc ra các dòng cần giải quyết: `match_status` là `POSSIBLE_UPDATE`/`POSSIBLE_DUPLICATE`, hoặc `recommended_action` là `NEEDS_MASTER_REVIEW`/`BLOCKED`, hoặc warnings khác rỗng.
  - Mặc định quyết định phân xử là `PENDING`.
  - Dropdown phân xử hợp lệ: `PENDING`, `CONFIRM_INSERT`, `CONFIRM_UPDATE`, `CONFIRM_SKIP`, `MARK_DUPLICATE`, `NEEDS_MORE_INFO`, `REJECT_CANDIDATE`.
  - Excel `master_review_resolution_template.xlsx` gồm 4 sheet: `Summary`, `Resolution Items` (có dropdown validation), `Decision Options`, `Warnings`.
  - CSV `master_review_resolution_template.csv` phẳng.
  - `master_review_resolution_guide.md` tài liệu hướng dẫn.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy đóng gói resolution:
   ```powershell
   python tools/feasibility/export_profile_master_review_resolution.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_master_review_resolution.py -q
   ```
