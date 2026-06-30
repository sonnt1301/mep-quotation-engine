# Danh Sách Công Việc MEP Quotation Pipeline Phase 4 – PDF Native Content Extraction

## Component 1 – Spec & Models

- [x] Thêm `RawTextPageModel` vào `mep_quotation/spec/models.py`
- [x] Thêm `RawTextManifestModel` vào `mep_quotation/spec/models.py`
- [x] Thêm trường `raw_text: str = Field("source/raw_text.json", ...)` vào `FilePathsModel`
- [x] Export `RawTextPageModel`, `RawTextManifestModel` trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder

- [x] Cập nhật `builder.py`: thêm `raw_text="source/raw_text.json"` khi khởi tạo `FilePathsModel`

## Component 3 – Package Integrity

- [x] Cập nhật `integrity.py`: thêm đối chiếu chéo `raw_text.json` (backward compatible)
  - [x] Chỉ chạy khi `source/raw_text.json` tồn tại thực tế trên đĩa
  - [x] Gọi thẳng `validate_raw_text_file(raw_text_path, package_path)` từ `pdf_text.manifest`
  - [x] Không tự duplicate logic validation trong integrity.py

## Component 4 – Module pdf_text (MỚI)

- [x] Tạo thư mục `mep_quotation/pdf_text/`
- [x] Tạo `mep_quotation/pdf_text/__init__.py` (export `extract_pdf_text`, `extract_package_text`)
- [x] Tạo `mep_quotation/pdf_text/extractor.py`
  - [x] Hàm `extract_pdf_text(pdf_path: Path) -> RawTextManifestModel`
  - [x] Mở PDF bằng PyMuPDF (`fitz`), block encrypted ngay lập tức
  - [x] Lấy text bằng `page.get_text()`, không trim/clean/normalize
  - [x] `has_text = bool(text)`, `character_count = len(text)`
  - [x] Ghi nhận `extraction_engine = "pymupdf"`, `extraction_engine_version`
  - [x] Tính `source_sha256` của file PDF
- [x] Tạo `mep_quotation/pdf_text/manifest.py`
  - [x] Hàm `write_raw_text_manifest(path, data)`: ghi JSON deterministic
  - [x] Hàm `validate_raw_text_file(raw_text_path, package_path)`:
    - [x] Validate `quotation_id` khớp `package.json`
    - [x] Validate `page_count` khớp số trang PDF thực tế
    - [x] Cross-check `page_count` với `metadata.json` nếu tồn tại
    - [x] Cross-check `page_count` với `page_manifest.json` nếu tồn tại
    - [x] Validate `page_number` bắt đầu từ 1, liên tục, không thiếu trang
    - [x] Validate `character_count == len(text)` cho từng trang
- [x] Tạo `mep_quotation/pdf_text/text_service.py`
  - [x] Hàm `extract_package_text(package_path, overwrite=False) -> Path`
  - [x] Load `package.json`
  - [x] Kiểm tra `metadata.json` → block encrypted
  - [x] Overwrite check: fail rõ nếu `raw_text.json` đã tồn tại và `overwrite=False`
  - [x] Gọi `extract_pdf_text()`
  - [x] Ghi `source/raw_text.json`
  - [x] Validate sau khi ghi
  - [x] Cập nhật `package.json` (`files.raw_text`, `updated_at`)
  - [x] Ghi audit log đầy đủ các success events (4 events: `pdf_text_extraction_started` → `pdf_text_extracted` → `raw_text_written` → `pdf_text_extraction_completed`); `pdf_text_extraction_failed` chỉ ghi khi có lỗi, không ghi trên success path

## Component 5 – CLI

- [x] Thêm handler `handle_extract_text(args)` trong `main.py`
- [x] Thêm subcommand `extract-text <package_path> [--overwrite]`
- [x] Output: `Quotation ID`, `Page Count`, `Total Characters`, `Pages With Text`, `Output Path`
- [x] Cập nhật description CLI từ Phase 3 sang Phase 4

## Component 6 – Schema Generation

- [x] Thêm `RawTextManifestModel` vào `scripts/generate_schemas.py`
- [x] Chạy `python scripts/generate_schemas.py` và verify `schemas/raw_text.schema.json` sinh ra đúng

## Component 7 – Tests

- [x] Tạo `tests/test_pdf_text.py` với đầy đủ các test cases:
  - [x] `test_extract_pdf_text_with_text`
  - [x] `test_extract_pdf_text_no_text`
  - [x] `test_extract_pdf_text_encrypted`
  - [x] `test_raw_text_schema_valid`
  - [x] `test_character_count_accuracy`
  - [x] `test_page_count_matches_pdf`
  - [x] `test_page_count_cross_check_metadata`
  - [x] `test_page_count_cross_check_page_manifest`
  - [x] `test_extract_package_text_flow`
  - [x] `test_overwrite_false_fail`
  - [x] `test_overwrite_true_pass`
  - [x] `test_source_sha256_traceability`
  - [x] `test_cli_extract_text`
  - [x] `test_audit_events`

## Component 8 – Tài liệu

- [x] Cập nhật `implementation_plan.md`
- [x] Cập nhật `task.md` (file này)
- [x] Thay `walkthrough.md` bằng báo cáo nghiệm thu Phase 4

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` → sinh đủ 7 schemas (bao gồm `raw_text.schema.json`)
- [x] `python -m pytest -v` → **59 PASSED**, 0 FAILED (45 cũ + 14 mới Phase 4)
