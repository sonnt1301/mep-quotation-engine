# Danh Sách Công Việc MEP Quotation Pipeline Phase 11 – Official Normalized Export Layer

## Component 1 – Spec & Models

- [x] Mở rộng `NormalizedItemModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) để thêm các thuộc tính Phase 11, làm các trường cũ thành Optional và bắt buộc (enforce) các trường bắt buộc mới ở model-level (Pydantic)
- [x] Cập nhật regex `validate_item_id` trong `NormalizedItemModel` để chấp nhận cả định dạng `_ITEM_` mới và định dạng cũ
- [x] Định nghĩa model `ExportSummaryModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- [x] Mở rộng `NormalizedQuotationModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) bổ sung các trường thông tin manifest xuất bản chính thức, summary và warning
- [x] Export `ExportSummaryModel` trong [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)

## Component 2 – Module normalized_export (MỚI)

- [x] Tạo thư mục `mep_quotation/normalized_export/`
- [x] Tạo [__init__.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/__init__.py) để export các API dịch vụ
- [x] Tạo [exporter.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/exporter.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/exporter.py)
  - [x] Xử lý lọc items theo thứ tự draft (chỉ đưa approved/edited vào, bỏ rejected/unreviewed)
  - [x] Gán item_id tuần tự tăng dần: `{QUOTATION_ID}_ITEM_{SEQ}`
  - [x] Quy tắc Amount: Tự động recompute `amount = quantity * unit_price` khi có đủ giá và số lượng, và chèn warning `amount_recomputed_from_quantity_and_unit_price` nếu lệch
  - [x] Quy tắc Currency: Uppercase, kế thừa quotation-level currency nếu item-level null (chèn warning `currency_inherited_from_quotation`), và ném lỗi nếu cả hai đều null hoặc currency không hợp lệ (VND/USD)
  - [x] Quy tắc Required Fields: Validate bắt buộc description (phi-rỗng), unit_price phi-null và currency phi-null, raise ValueError nếu thiếu
  - [x] Xử lý edited overrides: override null giữ nguyên giá gốc chứ không xóa
  - [x] Sinh thống kê `export_summary` chính xác
  - [x] Thêm file-level warning `no_approved_or_edited_items` nếu không có item xuất bản
- [x] Tạo [export_service.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/export_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/export_service.py)
  - [x] Hàm `export_normalized(package_path, overwrite) -> Path`
  - [x] Kiểm định chéo chữ ký băm: validate review decisions và cấm export nếu lệch `source_sha256`
  - [x] Cản ghi đè khi `overwrite=False`, cho phép khi `overwrite=True` bằng cách rebuild toàn bộ, không merge file cũ
  - [x] Atomic write ghi file tạm rồi replace
  - [x] Cập nhật package.json và gọi validate toàn gói
  - [x] Ghi audit logs đầy đủ: `normalized_export_started`, `normalized_export_built`, `normalized_export_written`, `normalized_export_completed` / `normalized_export_failed`

## Component 3 – Package Integrity & CLI

- [x] Cập nhật hàm `validate_package_integrity` trong [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) để bổ sung kiểm thử tệp `normalized.json` chính thức (kiểm tra IDs, hashes, counts, amount recompute và cấm item rejected/unreviewed)
- [x] Cập nhật [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py) tích hợp lệnh `export-normalized <package_path> [--overwrite]` và in thông số thống kê

## Component 4 – Schema Generation & Tests

- [x] Chạy sinh schema bằng `python scripts/generate_schemas.py` và kiểm định tính đồng bộ của `normalized.schema.json`
- [x] Tạo tệp kiểm thử [test_normalized_export.py (D:/mep_quotation_pipeline/tests/test_normalized_export.py)](file:///D:/mep_quotation_pipeline/tests/test_normalized_export.py) bao phủ toàn bộ các yêu cầu:
  - [x] approved và edited export đúng quy tắc, rejected/unreviewed bị loại bỏ
  - [x] empty export chèn warning file-level
  - [x] required field validation (description, unit_price)
  - [x] currency inheritance, uppercase, và validation
  - [x] amount recompute và warning phát sinh khi lệch
  - [x] edited overrides application (null override không xóa gốc)
  - [x] sequence id deterministic theo thứ tự draft
  - [x] source hashes trace và export_summary
  - [x] cản ghi đè, rebuild khi overwrite
  - [x] atomic write và validation package chéo
  - [x] CLI subcommand test
  - [x] log audit đầy đủ
  - [x] bảo vệ các tệp Phase trước không bị sửa đổi

## Component 5 – Tài liệu

- [x] Cập nhật [README.md (D:/mep_quotation_pipeline/README.md)](file:///D:/mep_quotation_pipeline/README.md) bổ sung hướng dẫn chạy lệnh CLI `export-normalized`
- [x] Cập nhật [walkthrough.md (D:/mep_quotation_pipeline/walkthrough.md)](file:///D:/mep_quotation_pipeline/walkthrough.md) báo cáo nghiệm thu Phase 11 sau khi hoàn thành

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` sinh đủ **13 schemas** thành công
- [x] `python -m pytest -v` đạt 100% passed (131 tests passed)
- [x] Thực hiện Manual Acceptance Test trên package thật và chạy kiểm duyệt package
