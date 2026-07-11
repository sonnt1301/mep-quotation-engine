# Walkthrough – Phase 2F – Master Data / Existing Record Matching Dry-run

Tất cả các mục tiêu phát triển Sandbox Master Data matching và kết xuất báo cáo Excel 4 sheet đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Master Matching Dry-run**.
> * **Không ghi dữ liệu vào database và không thay đổi production pipeline.**
> * **Không set ready_for_write_to_main_pipeline = True hoặc ready_for_real_write = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Sandbox Master Matching

1. **Safety Lọc & Trích xuất**:
   - Chỉ đối chiếu dựa trên simulated material records đã được simulation ở sandbox, tuyệt đối không lấy trực tiếp từ raw bridge hay adapter blocked items.
   - Trạng thái an toàn: `ready_for_real_write = FALSE` và `ready_for_write_to_main_pipeline = FALSE`.

2. **Matching Logic đa tầng**:
   - So khớp `exact_write_key_match` -> `WOULD_SKIP` (trùng khớp hoàn toàn) hoặc `WOULD_UPDATE` (khác mô tả/đơn vị).
   - So khớp `supplier_material_code_match` (trùng mã trùng giá -> `NEEDS_MASTER_REVIEW` / `POSSIBLE_DUPLICATE`; trùng mã khác giá/mô tả -> `NEEDS_MASTER_REVIEW` / `POSSIBLE_UPDATE`). Cấm tự động gộp dòng trùng mã khác giá.
   - So khớp `no_match` -> `WOULD_INSERT`.
   - Sinh tệp tin `master_index_fixture.json` chứa các bản ghi master mẫu phục vụ kiểm thử matching.

3. **Báo cáo và Excel tại `feasibility_outputs/profile_master_match_dry_run/`**:
   - Sinh đầy đủ các file JSON (results, summary).
   - Excel Workbook `master_match_review.xlsx` gồm 4 sheet: `Summary`, `Match Results`, `Possible Duplicates`, `Master Index Fixture` định dạng chuyên nghiệp và highlight màu.
   - `master_match_report.md` báo cáo markdown đối chiếu.

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 217 unit tests đã vượt qua thành công: **217/217 passed** (tỷ lệ 100%).
* Tạo tệp unit test bảo vệ: [test_profile_master_match_dry_run.py](file:///D:/mep_quotation_pipeline/tests/test_profile_master_match_dry_run.py)
  - Xác minh input simulated records rỗng trả về `BLOCKED_NO_SIMULATION_RECORDS`.
  - Xác minh `NO_MATCH` đề xuất `WOULD_INSERT`.
  - Xác minh exact `write_key` match đề xuất `WOULD_SKIP`/`WOULD_UPDATE`.
  - Xác minh trùng mã khác giá/mô tả đề xuất `NEEDS_MASTER_REVIEW`.
  - Xác minh `ready_for_real_write` và `ready_for_write_to_main_pipeline` luôn `False`.
  - Xác minh workbook có đủ 4 sheet hợp lệ.
