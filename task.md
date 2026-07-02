# Danh Sách Công Việc MEP Quotation Pipeline Phase 10 – Human Review / Approval Layer

## Component 1 – Spec & Models

- [x] Thêm trường `review_decisions: Optional[str] = Field("review/review_decisions.json", ...)` vào `FilePathsModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- [x] Thêm Pydantic model `ReviewFieldOverridesModel` vào [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) (thiết lập cấm extra fields)
- [x] Thêm Pydantic model `ReviewDecisionModel` vào [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) (thiết lập cấm extra fields)
- [x] Thêm Pydantic model `ReviewDecisionsFileModel` vào [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) (thiết lập cấm extra fields)
- [x] Export `ReviewFieldOverridesModel`, `ReviewDecisionModel` và `ReviewDecisionsFileModel` trong [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)

## Component 2 – Package Builder & Integrity

- [x] Cập nhật [builder.py (D:/mep_quotation_pipeline/mep_quotation/package/builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py) khởi tạo mặc định `review_decisions="review/review_decisions.json"` cho gói mới
- [x] Cập nhật [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) gọi hàm `validate_review_decisions_file` (chỉ chạy khi file tồn tại thực tế)

## Component 3 – Module review (MỚI)

- [x] Tạo thư mục `mep_quotation/review/`
- [x] Tạo [__init__.py (D:/mep_quotation_pipeline/mep_quotation/review/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/__init__.py) xuất các API nghiệp vụ chính
- [x] Tạo [decisions.py (D:/mep_quotation_pipeline/mep_quotation/review/decisions.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/decisions.py)
  - [x] Hàm `write_review_decisions(path, data)`: triển khai atomic write sử dụng tệp tạm thời `.tmp` và `os.replace`
  - [x] Hàm `load_review_decisions(path)` đọc file JSON trả về `ReviewDecisionsFileModel`
  - [x] Hàm `validate_review_decisions_file` thực thi validation 14 quy tắc chéo bắt buộc (SHA256 khớp draft item, reason trim/non-empty cho reject/edit, quantity/unit_price/amount phi-âm, duplicate check, allowed currency VND/USD/null)
  - [x] Bảo vệ nghiêm ngặt: validate báo lỗi `source_sha256_mismatch` nếu draft thay đổi, không tự động sửa, không thay đổi tệp Phase 1-9
- [x] Tạo [review_service.py (D:/mep_quotation_pipeline/mep_quotation/review/review_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/review_service.py)
  - [x] Hàm `create_empty_review_file(package_path, reviewer, overwrite) -> Path` (overwrite=False cản ghi đè, overwrite=True sinh timestamps mới)
  - [x] Hàm `record_review_decision(...) -> Path`
    - [x] Tự tạo file review rỗng nếu chưa tồn tại
    - [x] Kiểm thử `draft_item_id` tồn tại thực tế trong draft
    - [x] Xử lý thay thế (overwrite=True): giữ nguyên `decision_id` cũ, `created_at` cũ, cập nhật `reviewer` mới được truyền vào, cập nhật `decision_type` / `reason` / `field_overrides` theo dữ liệu mới, cập nhật `updated_at` mới, và ghi audit event `review_decision_replaced`
    - [x] Xử lý thêm mới: sequence tăng tuần tự theo `max(seq) + 1` không phụ thuộc vào `len(decisions)`
    - [x] Validate dữ liệu, trim reason trước khi ghi
    - [x] Atomic write, cập nhật package.json và gọi validate toàn gói
  - [x] Hàm `list_review_decisions(package_path)`
  - [x] Ghi audit logs đầy đủ: `review_file_created`, `review_decision_recorded`, `review_decision_replaced`, `review_validation_completed` / `review_operation_failed`
  - [x] **Critical Scope Guard**:
    - [x] Phase 10 chỉ ghi và quản lý tệp `review/review_decisions.json`, package.json path metadata và audit log
    - [x] Phase 10 không áp dụng (apply) decisions vào dữ liệu báo giá
    - [x] Phase 10 không tự ý sinh tệp báo giá chính thức `normalized/normalized.json`
    - [x] Phase 10 không sửa đổi nội dung tệp nháp `normalized/normalized_draft.json`
    - [x] Đảm bảo không có function hay CLI command nào trong Phase 10 tạo normalized output chính thức

## Component 4 – CLI Integration

- [x] Cập nhật [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
  - [x] Handler và parser cho `create-review-file`
  - [x] Handler và parser cho `record-review` (hỗ trợ normalize currency, validate enum)
  - [x] Handler và parser cho `list-review` (in thống kê)

## Component 5 – Schema Generation

- [x] Đăng ký `ReviewDecisionsFileModel` trong [generate_schemas.py (D:/mep_quotation_pipeline/scripts/generate_schemas.py)](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- [x] Chạy sinh schema và kiểm tra tệp `schemas/review_decisions.schema.json` được tạo thành công

## Component 6 – Tests

- [x] Tạo tệp kiểm thử [test_review_decisions.py (D:/mep_quotation_pipeline/tests/test_review_decisions.py)](file:///D:/mep_quotation_pipeline/tests/test_review_decisions.py) bao phủ toàn bộ:
  - [x] `create_empty_review_file` hợp lệ
  - [x] overwrite check hoạt động đúng với cả create và record
  - [x] approved/rejected/edited decision validation đúng quy chuẩn
  - [x] reject/edit reason whitespace check
  - [x] edit overrides (non-negative, non-empty, allowed currency)
  - [x] CLI currency normalization và invalid enum prevention
  - [x] draft_item_id tồn tại check
  - [x] duplicate check và replacement logic (giữ id/created_at cũ, cập nhật reviewer mới và updated_at mới)
  - [x] sequence calculation `max(seq) + 1` độc lập
  - [x] source_sha256 mismatch bắt lỗi đúng
  - [x] validate package chéo
  - [x] CLI subcommands test (create, record, list)
  - [x] Audit logs ghi nhận đầy đủ
  - [x] Hậu kiểm Phase 1-9 không bị sửa đổi
  - [x] Atomic write mô phỏng lỗi ghi file giữa chừng hoạt động tốt

## Component 7 – Tài liệu

- [x] Cập nhật [README.md (D:/mep_quotation_pipeline/README.md)](file:///D:/mep_quotation_pipeline/README.md) hướng dẫn chạy CLI Phase 10
- [x] Cập nhật [walkthrough.md (D:/mep_quotation_pipeline/walkthrough.md)](file:///D:/mep_quotation_pipeline/walkthrough.md) báo cáo nghiệm thu sau khi hoàn thành

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` sinh đủ **13 schemas**
- [x] `python -m pytest -v` đạt 100% passed (khoảng 140 tests passed - thực tế là 124 tests)
- [x] Thực hiện Manual Acceptance Test trên package thật và kiểm duyệt package
