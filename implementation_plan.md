# Kế Hoạch Triển Khai – Phase 2F – Master Data / Existing Record Matching Dry-run

Kế hoạch này triển khai lớp đối chiếu khô (Dry-run Matching) giữa các simulated material records và dữ liệu master hiện có hoặc master index giả lập để xác định chính xác hành động đề xuất trước khi ghi thật.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Master Matching Dry-run**.
> * **Không ghi dữ liệu vào database và không thay đổi production pipeline.**
> * **Không set ready_for_write_to_main_pipeline = True hoặc ready_for_real_write = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Master Data Matching

### A. Giao diện & Kết xuất
* **Matching script**: [run_profile_master_match_dry_run.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_profile_master_match_dry_run.py) (So khớp simulated records với master index).
* **Ràng buộc an toàn & Logic**:
  - Không đọc trực tiếp từ raw bridge items hay tệp blocked của adapter. Chỉ so khớp simulated records.
  - Hỗ trợ so khớp: `exact_write_key_match`, `supplier_material_code_match` (trùng mã trùng giá, trùng mã khác giá/mô tả), và `no_match`.
  - Phân loại hành động an toàn: `WOULD_INSERT`, `WOULD_UPDATE`, `WOULD_SKIP`, và `NEEDS_MASTER_REVIEW`.
  - Cấm tự động gộp các dòng trùng mã hàng nhưng khác đơn giá hoặc mô tả (đẩy sang trạng thái `NEEDS_MASTER_REVIEW`).
* **Sản phẩm xuất bản tại `feasibility_outputs/profile_master_match_dry_run/`**:
  - `master_index_fixture.json`: kho dữ liệu master index mẫu.
  - `master_match_results.json`: danh sách các bản ghi kết quả đối chiếu.
  - `master_match_summary.json`: tóm tắt metadata.
  - `master_match_review.csv` và `master_match_review.xlsx`: Excel có 4 sheet (`Summary`, `Match Results`, `Possible Duplicates`, `Master Index Fixture`).
  - `master_match_report.md`: báo cáo markdown đối chiếu.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy đối chiếu dry-run:
   ```powershell
   python tools/feasibility/run_profile_master_match_dry_run.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_master_match_dry_run.py -q
   ```
