# Báo Cáo Nghiệm Thu Phase 12 – Excel Export Layer

Báo cáo tóm tắt quá trình triển khai, kết quả chạy kiểm thử tự động và thủ công cho Phase 12.

## Kết quả đạt bộ

1. **Spec & Models**:
   * Cập nhật mô hình [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) bổ sung đường dẫn xuất Excel `excel_export` và `excel_export_manifest` vào `FilePathsModel`.
   * Định nghĩa 3 models mới: `ExcelExportSheetModel`, `ExcelExportContextModel`, và `ExcelExportManifestModel` được tích hợp serialize `exported_at` và thắt chặt extra fields (`extra="forbid"`).
   * Đăng ký và xuất bản đồng bộ các model này tại [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py).

2. **Xây Dựng Excel Workbook (workbook_builder.py)**:
   * Dựng workbook Excel bằng thư viện `openpyxl` với 4 sheet có cấu trúc rõ ràng:
     * **Sheet 1: Summary**: Chứa các siêu dữ liệu báo giá (Quotation ID, Supplier Code, Quotation Date, Currency, Item Count, Source Normalized Path/SHA256, Exported At, Exporter Name, Exporter Version, và thống kê tóm tắt review). Currency được đối chiếu tự động (nếu duy nhất thì ghi nhận, nếu nhiều thì ghi `"MULTIPLE"`, nếu không có thì để trống).
     * **Sheet 2: Items**: Ghi nhận toàn bộ items chính thức. Giữ đúng kiểu dữ liệu số (numeric) cho `quantity`, `unit_price`, `amount`, `confidence`, và `page_number`. Cố định dòng tiêu đề (freeze pane A2), bật bộ lọc (auto filter) và tự động căn chỉnh độ rộng cột thông minh (auto-width).
     * **Sheet 3: Warnings**: Ghi nhận cảnh báo cấp file và cấp item rõ ràng theo dạng danh sách (`level`, `item_id`, `code`, `message`).
     * **Sheet 4: Trace**: Ghi nhận thông tin truy vết (`item_id`, `source_draft_item_id`, `source_review_decision_id`, `page_number`, `evidence_text`).
   * **Chống Formula Injection**: Tất cả các ô dạng text bắt đầu bằng `=`, `+`, `-`, `@` đều được chèn dấu nháy đơn `'` ở đầu để đảm bảo an toàn tuyệt đối.
   * **Lọc ký tự XML Excel-illegal**: Lọc sạch các ký tự điều khiển ASCII < 32 (ngoại trừ `\n`, `\r`, `\t`) trước khi ghi để tránh lỗi hỏng tệp Excel.

3. **Điều Phối Xuất Bản & An Toàn (export_service.py)**:
   * Tự động tạo thư mục `exports/` nếu chưa tồn tại.
   * Kiểm duyệt `item_count`: Đối chiếu `normalized.item_count` phi-zero với kích thước `len(normalized.items)` thực tế để ngăn lệch dòng.
   * Cơ chế cản ghi đè khi `overwrite=False` (fail rõ ràng nếu tệp Excel hoặc manifest đã có trên đĩa).
   * Cơ chế ghi tệp tin an toàn (Atomic Write): Ghi ra file `.tmp` rồi rename nguyên tử qua `os.replace` (thay thế nguyên tử thật sự).
   * Đọc load kiểm thử lại workbook sau khi ghi thành công để validate cấu trúc sheet và số lượng dòng dữ liệu khớp chính xác.
   * Cập nhật an toàn `package.json` và ghi nhật ký logs audit đầy đủ.
   * Nếu gặp lỗi ghi `package.json`, ném lỗi RuntimeError rõ ràng, ghi log event `excel_export_failed` và bảo vệ dữ liệu Phase trước không bị sửa đổi.

4. **Kiểm Định Chéo Toàn Gói Sâu (validate_package_integrity)**:
   * Cập nhật hàm `validate_package_integrity` tại [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) thực thi kiểm định sâu tệp Excel manifest nếu tệp này có trên đĩa (đối chiếu SHA256 của normalized.json, quotation.xlsx, kiểm tra sheet_count và thứ tự sheet names).

5. **CLI Subcommand**:
   * Đăng ký subcommand `export-excel` tại CLI [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py).

6. **Schema & Tests**:
   * Sinh mới tệp schema `excel_export_manifest.schema.json` đồng bộ và Deterministic.
   * Viết suite tests đầy đủ [test_excel_export.py (D:/mep_quotation_pipeline/tests/test_excel_export.py)](file:///D:/mep_quotation_pipeline/tests/test_excel_export.py).
   * Vượt qua toàn bộ **136/136 tests** tự động của hệ thống (100% passed).

---

## Xác nhận kiểm thử tự động (Pytest)

Chạy tất cả các test cases bằng `pytest`:
```bash
python -m pytest -v
```
Kết quả thực tế:
```text
tests/test_excel_export.py::test_export_excel_success PASSED
tests/test_excel_export.py::test_export_excel_overwrite_rule PASSED
tests/test_excel_export.py::test_export_excel_mismatch_item_count PASSED
tests/test_excel_export.py::test_export_excel_package_json_update_fail PASSED
tests/test_excel_export.py::test_export_excel_missing_exports_dir_success PASSED

============================ 136 passed in 10.11s =============================
```

---

## Kiểm thử thủ công trên gói thực tế

Chạy trên gói `data/suppliers/AUT/2026/2026-06-20_001`:

1. **Thực hiện xuất Excel**:
   ```bash
   python -m mep_quotation.cli.main export-excel data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
   *Kết quả in*:
   ```text
   Successfully exported official Excel quotation.
     Quotation ID          : AUT_20260620_001
     Supplier Code         : AUT
     Quotation Date        : 2026-06-20
     Item Count            : 1
     Excel Export Path     : data/suppliers/AUT/2026/2026-06-20_001/exports/quotation.xlsx
     Manifest JSON Path    : data/suppliers/AUT/2026/2026-06-20_001/exports/export_manifest.json
     Sheet Count           : 4
     Source Normalized SHA256 : cd4ddf1412f7f9a4f612f7aba207c73693ab5a4d5324de12fde6fadef6a78bbd
     Export File SHA256    : fe3efb2de3fc614e1ae56a9ede04712b52e114f718daf4b3dbf54207fe8197cb
   ```

2. **Xác thực toàn vẹn gói**:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
   *Kết quả in*:
   ```text
   Package is valid.
     Quotation ID : AUT_20260620_001
     Supplier     : AUT
     Items Count  : 1
     Corrections  : 0
   ```

3. **Nhật ký Audit Log (logs/processing.log.jsonl)**:
   ```json
   {"details": {"overwrite": true}, "event": "excel_export_started", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:38Z"}
   {"details": {}, "event": "excel_workbook_built", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:39Z"}
   {"details": {"path": "exports/quotation.xlsx"}, "event": "excel_workbook_written", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:40Z"}
   {"details": {}, "event": "excel_workbook_validated", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:42Z"}
   {"details": {"path": "exports/export_manifest.json"}, "event": "excel_export_manifest_written", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:43Z"}
   {"details": {"excel_path": "exports/quotation.xlsx", "manifest_path": "exports/export_manifest.json"}, "event": "excel_export_completed", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T07:21:46Z"}
   ```

Toàn bộ tiến trình diễn ra hoàn hảo, dữ liệu liên kết chéo của 12 phases được thắt chặt và kiểm định toàn vẹn sâu sắc.
