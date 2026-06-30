# Báo Cáo Nghiệm Thu Phase 6 – Rule-based Line Candidate Extraction (Cập Nhật: Xác Thực Ranh Giới Offset Trang)

Phase 6 đã được cập nhật cơ chế xác thực ranh giới offset của các trang một cách chặt chẽ, loại bỏ hoàn toàn các lỗi tiềm ẩn do lệch page_number trong quá trình định vị. Hệ thống đã vượt qua toàn bộ 87 ca kiểm thử tự động thành công.

---

## 1. Các Thay Đổi & Nâng Cấp Mới Về Xác Thực Offset

1. **scan_markdown_lines (`line_parser.py`)**:
   - Loại bỏ cơ chế fallback trang cuối (`page_number = assembly_manifest.page_count`).
   - Nếu một dòng Markdown (không phải dòng trống, heading, separator, hay metadata đầu file) có offset nằm ngoài tầm ranh giới của tất cả các trang, hệ thống sẽ ném lỗi `ValueError` trực tiếp.
   - Bổ sung việc tự động bỏ qua các dòng siêu dữ liệu đầu file Markdown (`Quotation ID:`, `Source PDF:`, `Page Count:`, `Generated At:`) để tránh gây nhiễu cho scanner.
2. **validate_line_candidates_file (`candidate_manifest.py`)**:
   - Đọc và validate tệp manifest `text/quotation_text.json` bằng model Pydantic chính thức `TextAssemblyManifestModel`.
   - Với từng candidate, đối chiếu `evidence.start_offset` và `evidence.end_offset` xem có nằm trọn vẹn trong ranh giới `[page.start_offset : page.end_offset]` của trang `cand.page_number` tương ứng hay không. Ném lỗi `ValueError` chi tiết nếu phát hiện sự lệch ranh giới.
3. **Bổ Sung Bộ Kiểm Thử (`tests/test_line_parser.py`)**:
   - `test_validation_catches_tampered_page_number`: Kiểm chứng việc đổi `page_number` của candidate hợp lệ sang trang khác (nhưng giữ nguyên offset/text) sẽ bị hàm kiểm duyệt phát hiện và báo lỗi lệch range.
   - `test_scan_markdown_lines_raises_error_for_out_of_bounds_offset`: Kiểm chứng Line Scanner sẽ ném lỗi `ValueError` nếu phát hiện offset của dòng text không map được vào bất kỳ trang nào được định nghĩa trong text manifest.

---

## 2. Kết Quả Xác Thực Kỹ Thuật

### 🔹 Kết Quả Sinh JSON Schema
Đã sinh thành công **9 tệp schema JSON** deterministic trong thư mục `schemas/`.

### 🔹 Bộ Unit Tests Pytest (`python -m pytest -v`)
Toàn bộ **87 tests passed / 0 failed** thành công mỹ mãn trong 3.05 giây.

```text
tests/test_line_parser.py::test_parse_simple_line_with_price_unit PASSED [ 14%]
tests/test_line_parser.py::test_do_not_treat_technical_specs_as_price PASSED [ 16%]
tests/test_line_parser.py::test_parse_price_with_marker_or_safe_ending PASSED [ 17%]
tests/test_line_parser.py::test_parse_brand PASSED                       [ 18%]
tests/test_line_parser.py::test_quantity_missing_warning_logic PASSED    [ 19%]
tests/test_line_parser.py::test_ignore_markdown_headings_and_separators PASSED [ 20%]
tests/test_line_parser.py::test_line_number_one_based PASSED             [ 21%]
tests/test_line_parser.py::test_evidence_slice_exact_match PASSED        [ 22%]
tests/test_line_parser.py::test_page_number_mapping_from_offset PASSED   [ 24%]
tests/test_line_parser.py::test_candidate_id_format_and_uniqueness PASSED [ 25%]
tests/test_line_parser.py::test_confidence_calculation_deterministic PASSED [ 26%]
tests/test_line_parser.py::test_validation_catches_bad_evidence_offset PASSED [ 27%]
tests/test_line_parser.py::test_overwrite_protection_and_audit_log PASSED [ 28%]
tests/test_line_parser.py::test_cli_parse_line_candidates PASSED         [ 29%]
tests/test_line_parser.py::test_does_not_create_normalized_json PASSED   [ 31%]
tests/test_line_parser.py::test_validation_catches_tampered_page_number PASSED [ 32%]
tests/test_line_parser.py::test_scan_markdown_lines_raises_error_for_out_of_bounds_offset PASSED [ 33%]
...
============================= 87 passed in 3.05s ==============================
```
