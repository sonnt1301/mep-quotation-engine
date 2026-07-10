# Kế Hoạch Triển Khai – Phase 2B.1 – Visual Adapter Output Package

Kế hoạch này tích hợp chức năng kết xuất dữ liệu review trực quan ở các định dạng thân thiện với người dùng (CSV, Excel multi-sheet) phục vụ kiểm định kết quả Controlled Write Adapter.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Controlled Write Adapter Dry-run**.
> * **Không ghi dữ liệu vào main pipeline chính và không sửa đổi dữ liệu gốc.**
> * **Không set ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Excel & CSV Exporter

### A. Giao diện & Kết xuất
* **Adapter script**: [run_profile_write_adapter_dry_run.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_profile_write_adapter_dry_run.py) (Tích hợp thêm hàm `write_csv_and_xlsx` sử dụng thư viện `openpyxl`).
* **Sản phẩm xuất bản**:
  - `normalized_items_preview.csv`: chứa các dòng được phép ghi.
  - `blocked_items.csv`: chứa các dòng bị khóa hoặc chưa được duyệt.
  - `profile_write_adapter_review.xlsx`: chứa 3 sheet (`Summary`, `Exportable Preview`, `Blocked Items`).
* **Định dạng Excel chuyên nghiệp**:
  - Freeze row header 1.
  - Tự động bật bộ lọc auto-filter.
  - Format number cho đơn giá/thành tiền (`#,##0`).
  - Tự động giãn cột vừa vặn nội dung.
  - Highlight dòng rủi ro (`NEEDS_INVESTIGATION`, `REJECT`) với màu đỏ nhạt.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy xuất Excel và CSV:
   ```powershell
   python tools/feasibility/run_profile_write_adapter_dry_run.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_write_adapter_dry_run.py -q
   ```
