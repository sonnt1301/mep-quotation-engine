# Walkthrough – Phase 2G – Master Review Resolution Package

Tất cả các mục tiêu phát triển Master Review Resolution Package và kết xuất template Excel tích hợp dropdown validation đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Master Review Resolution Package**.
> * **Không ghi dữ liệu vào database và không thay đổi dữ liệu thật.**
> * **Không set ready_for_write_plan = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Resolution Package

1. **Safety Lọc & Trích xuất**:
   - Chỉ lọc dữ liệu từ kết quả đối chiếu master match dry-run (`master_match_results.json`), tuyệt đối không đọc từ raw bridge items hay adapter blocked items.
   - Trạng thái an toàn: `ready_for_write_plan = FALSE` và `ready_for_write_to_main_pipeline = FALSE`.

2. **Dropdown Validation nâng cao**:
   - Sử dụng openpyxl DataValidation để chèn trực tiếp dropdown menu cho cột `human_resolution_decision` trên Excel.
   - Quyết định mặc định: `PENDING`.
   - Các lựa chọn phân xử: `PENDING`, `CONFIRM_INSERT`, `CONFIRM_UPDATE`, `CONFIRM_SKIP`, `MARK_DUPLICATE`, `NEEDS_MORE_INFO`, `REJECT_CANDIDATE`.

3. **Báo cáo và templates tại `feasibility_outputs/profile_master_review_resolution/`**:
   - `master_review_resolution_items.json`: Các dòng có vấn đề cần xử lý.
   - `master_review_resolution_summary.json`: Tóm tắt các metrics đệ trình.
   - `master_review_resolution_template.csv`: File CSV mẫu phẳng.
   - `master_review_resolution_template.xlsx`: Excel Workbook 4 sheet (`Summary`, `Resolution Items`, `Decision Options`, `Warnings`) định dạng chuyên nghiệp.
   - `master_review_resolution_guide.md`: Tài liệu hướng dẫn phân xử và điều kiện gate đi tiếp.

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 220 unit tests đã vượt qua thành công: **220/220 passed** (tỷ lệ 100%).
* Tạo tệp unit test bảo vệ: [test_profile_master_review_resolution.py](file:///D:/mep_quotation_pipeline/tests/test_profile_master_review_resolution.py)
  - Xác minh khi đối chiếu sạch hoàn toàn trả về `NO_MASTER_REVIEW_REQUIRED`.
  - Xác minh có vấn đề (trùng/cảnh báo) tự động tạo resolution item và gán mặc định `PENDING`.
  - Xác minh dropdown validation được chèn thành công trên worksheet.
  - Xác minh ready flags luôn luôn là `False`.
