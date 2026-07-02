# Danh Sách Công Việc MEP Quotation Pipeline Phase 12 – Excel Export Layer

## Component 1 – Spec & Models

- [x] Cập nhật `FilePathsModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) bổ sung các trường đường dẫn Excel tùy chọn
- [x] Định nghĩa các model mới `ExcelExportSheetModel`, `ExcelExportContextModel`, và `ExcelExportManifestModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- [x] Export các model này trong [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)

## Component 2 – Excel Export Module (MỚI)

- [x] Tạo thư mục `mep_quotation/excel_export/`
- [x] Tạo [__init__.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/__init__.py) export các APIs
- [x] Tạo [workbook_builder.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/workbook_builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/workbook_builder.py)
  - [x] Triển khai hàm `build_excel_workbook`
  - [x] Viết helper khử các ký tự control XML Excel-illegal
  - [x] Dựng Sheet `Summary` chính xác với đầy đủ thông số và thống kê review (đối chiếu logic currency)
  - [x] Dựng Sheet `Items` chính xác (lưu đúng định dạng numeric, freeze pane dòng header, auto filter, auto-width)
  - [x] Chống formula injection cho các ô text bắt đầu bằng `=`, `+`, `-`, `@`
  - [x] Dựng Sheet `Warnings` cấp file và cấp item (đảm bảo tồn tại chỉ có header khi không có warning)
  - [x] Dựng Sheet `Trace` cho truy vết evidence
- [x] Tạo [export_manifest.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/export_manifest.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/export_manifest.py)
  - [x] Triển khai hàm `build_excel_export_manifest`
  - [x] Lấy supplier_code và quotation_date chuẩn xác từ normalized/package.json
- [x] Tạo [export_service.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/export_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/export_service.py)
  - [x] Triển khai hàm `export_excel`
  - [x] Tự động tạo thư mục `exports/` nếu chưa tồn tại (không fail chỉ vì thiếu thư mục này)
  - [x] Kiểm item_count:
    - [x] Nếu `normalized.item_count` tồn tại thì phải khớp `len(normalized.items)`
    - [x] Nếu `normalized.item_count` không tồn tại thì dùng `len(normalized.items)`
    - [x] Nếu có mismatch thì fail rõ ràng
  - [x] Cản ghi đè khi `overwrite=False` (fail rõ ràng nếu `quotation.xlsx` hoặc `export_manifest.json` đã tồn tại)
  - [x] Cho phép ghi đè hoàn toàn khi `overwrite=True` (không merge)
  - [x] Thực thi Atomic Write cho cả `quotation.xlsx` và `export_manifest.json` (sử dụng os.replace thay thế nguyên tử thật sự)
  - [x] Load lại workbook và validate cấu trúc sau khi ghi file Excel
  - [x] Cập nhật package.json và ghi logs audit đầy đủ
  - [x] Nếu package.json update lỗi sau khi đã ghi Excel/manifest: ghi audit event `excel_export_failed`, raise lỗi rõ ràng, không sửa normalized.json hay các artifact Phase 1-11, không rollback tự động phức tạp

## Component 3 – Package Integrity & CLI & Dependencies

- [x] Thêm dependency `"openpyxl>=3.1.0"` vào [pyproject.toml (D:/mep_quotation_pipeline/pyproject.toml)](file:///D:/mep_quotation_pipeline/pyproject.toml)
- [x] Cập nhật kiểm duyệt package trong [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) hỗ trợ manifest Excel tương thích ngược
- [x] Đăng ký subcommand `export-excel` tại [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)

## Component 4 – Schemas & Tests

- [x] Sinh lại schemas bao gồm tệp `excel_export_manifest.schema.json` mới
- [x] Tạo tệp kiểm thử [test_excel_export.py (D:/mep_quotation_pipeline/tests/test_excel_export.py)](file:///D:/mep_quotation_pipeline/tests/test_excel_export.py) bao phủ toàn bộ các yêu cầu của Phase 12:
  - [x] Xác nhận Phase 12 không sửa các source artifacts (`normalized.json`, `normalized_draft.json`, `review_decisions.json`) bằng cách so sánh SHA256 trước và sau khi export
  - [x] Kiểm thử cản ghi đè khi `overwrite=False` cho cả 2 trường hợp: `quotation.xlsx` đã tồn tại và `export_manifest.json` đã tồn tại
  - [x] Kiểm thử các trường hợp thành công và thất bại khác (mismatch item_count, invalid normalized.json, v.v.)

## Component 5 – Tài liệu

- [x] Cập nhật [README.md (D:/mep_quotation_pipeline/README.md)](file:///D:/mep_quotation_pipeline/README.md) hướng dẫn chạy lệnh CLI `export-excel`
- [x] Cập nhật [walkthrough.md (D:/mep_quotation_pipeline/walkthrough.md)](file:///D:/mep_quotation_pipeline/walkthrough.md) nghiệm thu sau khi hoàn thành

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` sinh đủ **14 schemas** thành công
- [x] `python -m pytest -v` đạt 100% passed (tất cả các tests cũ và mới đều passed)
- [x] Thực hiện Manual Acceptance Test trên package thật và chạy kiểm duyệt package
