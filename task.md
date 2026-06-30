# Danh Sách Công Việc MEP Quotation Pipeline Phase 5 – Text Assembly

## Component 1 – Spec & Models

- [x] Thêm trường `text_markdown: str = Field("text/quotation.md", ...)` và `text_manifest: str = Field("text/quotation_text.json", ...)` vào `FilePathsModel` trong `mep_quotation/spec/models.py`
- [x] Thêm `TextAssemblyPageModel` vào `mep_quotation/spec/models.py`
- [x] Thêm `TextAssemblyManifestModel` vào `mep_quotation/spec/models.py`
- [x] Export `TextAssemblyPageModel` và `TextAssemblyManifestModel` trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder & Integrity

- [x] Cập nhật `builder.py` để gán mặc định `text_markdown` và `text_manifest` khi tạo package rỗng
- [x] Cập nhật `builder.py` tự động tạo thư mục con `text/` khi tạo package mới
- [x] Cập nhật `integrity.py` gọi hàm `validate_assembly_manifest_file(manifest_path, package_path)` kiểm tra tính toàn vẹn của tệp index/markdown (chỉ chạy khi tệp manifest thực tế tồn tại trên đĩa)

## Component 3 – Module text_assembly (MỚI)

- [x] Sửa đổi `mep_quotation/text_assembly/assembly_service.py`
  - [x] Di chuyển các đoạn check validation (PDF encrypted, thiếu `raw_text.json`, cản ghi đè) vào trong khối `try`
  - [x] Ghi nhận log kiểm toán `text_assembly_failed` khi bất kỳ lỗi nào xảy ra trong luồng với `level="ERROR"` và `details.error`
- [x] Tạo `mep_quotation/text_assembly/__init__.py`
- [x] Tạo `mep_quotation/text_assembly/assembler.py`
- [x] Tạo `mep_quotation/text_assembly/manifest.py`

## Component 4 – CLI Integration

- [x] Thêm handler `handle_assemble_text(args)` trong `cli/main.py`
- [x] Thêm subcommand `assemble-text <package_path> [--overwrite]` trong `cli/main.py`
- [x] Cập nhật description CLI hỗ trợ thông tin Phase 5

## Component 5 – Schema Generation

- [x] Thêm `TextAssemblyManifestModel` vào `scripts/generate_schemas.py`
- [x] Chạy sinh schema mới và xác thực tệp `schemas/quotation_text.schema.json` được tạo thành công (Xác nhận sinh đầy đủ **8 schemas**)

## Component 6 – Tests

- [x] Cập nhật bộ kiểm thử `tests/test_text_assembly.py`
  - [x] Cập nhật `test_missing_raw_text_fail` kiểm tra ném lỗi và ghi log `text_assembly_failed`
  - [x] Cập nhật `test_overwrite_protection` kiểm tra ném lỗi và ghi log `text_assembly_failed` khi trùng đè
  - [x] Bổ sung `test_encrypted_package_assembly_fail` kiểm tra PDF encrypted ném lỗi và ghi log `text_assembly_failed`

## Component 7 – Tài liệu

- [x] Cập nhật `README.md` hướng dẫn sử dụng lệnh CLI `assemble-text`
- [x] Cập nhật số lượng test pass thực tế và nghiệm thu failure path trong `walkthrough.md`
- [x] Cập nhật `implementation_plan.md`

## Verification Bắt Buộc

- [x] `python -m pip install -e ".[dev]"` thành công
- [x] `python scripts/generate_schemas.py` sinh đủ **8 schemas**
- [x] `python -m pytest -v` đạt 100% passed (70 tests passed)
- [x] Thực hiện Manual Acceptance Test kiểm tra failure path có `text_assembly_failed`
