# Walkthrough – Phase 2B.1 – Visual Adapter Output Package

Tất cả các mục tiêu phát triển chức năng kết xuất dữ liệu Adapter đầu ra dưới dạng CSV và Excel đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Controlled Write Adapter Dry-run**.
> * **Không ghi dữ liệu vào main pipeline chính và không sửa đổi dữ liệu gốc.**
> * **Không set ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Kết Xuất Visual Package

1. **normalized_items_preview.csv**:
   - Ghi lại toàn bộ dữ liệu vật tư được phép ghi nhận (APPROVED, EDIT_AND_APPROVE, ACCEPT_WITH_LIMITATION).
   - Mã hóa chuẩn `utf-8-sig` (UTF-8 với BOM) để Excel hiển thị đúng tiếng Việt gốc.
   
2. **blocked_items.csv**:
   - Ghi nhận tất cả các vật tư bị khóa (REJECT, NEEDS_INVESTIGATION, UNREVIEWED) kèm theo lý do khóa.

3. **profile_write_adapter_review.xlsx**:
   - Tệp Excel báo cáo chuyên nghiệp gồm 3 sheet:
     * **Summary**: tóm tắt đệ trình các chỉ số counts và metadata an toàn.
     * **Exportable Preview**: chứa thông số các dòng được duyệt.
     * **Blocked Items**: chứa các dòng bị khóa.
   - Định dạng Excel nâng cao:
     * Cố định dòng tiêu đề (Freeze row header 1).
     * Bật tính năng tự động lọc (Auto-filter).
     * Thiết lập tự động căn lề cột, format number (`#,##0`) cho cột đơn giá/số lượng/thành tiền.
     * Highlight tự động màu đỏ nhạt cho các dòng bị khóa cảnh báo (`NEEDS_INVESTIGATION`, `REJECT`).

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 201 unit tests đã vượt qua thành công: **201/201 passed** (tỷ lệ 100%).
* Cập nhật unit test bảo vệ: [test_profile_write_adapter_dry_run.py](file:///D:/mep_quotation_pipeline/tests/test_profile_write_adapter_dry_run.py)
  - Xác minh các file CSV và XLSX mới được sinh ra tại thư mục đầu ra.
  - Xác minh workbook có đủ 3 sheet hợp lệ.
  - Xác minh logic nạp khi chưa có quyết định human review (exportable = 0, blocked = tổng số dòng bridge).
  - Đảm bảo `ready_for_write_to_main_pipeline` luôn luôn được set là `False`.
