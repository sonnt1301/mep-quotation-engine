# Kế Hoạch Triển Khai MEP Quotation Pipeline Phase 1 - Harden Data Contract (Bản Cập Nhật 2)

Tài liệu này trình bày kế hoạch chi tiết nhằm thắt chặt dữ liệu nền tảng và sửa lỗi đóng gói trước khi chuyển sang Phase 2. Toàn bộ các thay đổi được áp dụng tại thư mục dự án **[D:/mep_quotation_pipeline](file:///D:/mep_quotation_pipeline)**.

---

## Các Thay Đổi Chi Tiết (Proposed Changes)

### 1. Sửa Lỗi Đóng Gói (Packaging)

#### [MODIFY] [pyproject.toml](file:///D:/mep_quotation_pipeline/pyproject.toml)
- Thêm cấu hình chỉ định setuptools chỉ đóng gói thư mục `mep_quotation` và loại bỏ các thư mục phụ trợ (`data`, `schemas`, `tests`, `scripts`):
  ```toml
  [tool.setuptools.packages.find]
  include = ["mep_quotation*"]
  exclude = ["data*", "schemas*", "tests*", "scripts*"]
  ```

---

### 2. Định Nghĩa Mô Hình Dữ Liệu và Xác Thực Hệ Thống

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Thắt chặt validation cho `NormalizedQuotationModel` thông qua `@model_validator(mode="after")`:
  - `quotation_id` phải khớp hoàn toàn biểu thức chính quy: `^([A-Z0-9]+)_(\d{8})_(\d{3})$`.
  - `quotation_date` phải là ngày hợp lệ (sử dụng `datetime.strptime(date_str, "%Y-%m-%d")`).
  - `supplier_code` (sau khi clean) phải khớp với phần supplier trong `quotation_id`.
  - `quotation_date` (sau khi loại bỏ dấu `-`) phải khớp với phần ngày `YYYYMMDD` trong `quotation_id`.
- Cập nhật mô tả (`Field(..., description=...)`) của trường `package_path` trong `MaterialIndexEntryModel` ghi rõ: *"Đường dẫn tương đối tính từ Project Root, ví dụ: data/suppliers/AUT/2026/2026-05-20_001"*.

#### [NEW] [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Tạo module mới chứa hàm `validate_package_integrity(package_path: Path) -> None` để tránh circular import giữa `spec` và `package`:
  - Đọc `package.json`, `normalized.json`, `corrections.json` bằng các loader tương ứng trong `mep_quotation/package/loader.py`.
  - Kiểm tra và so khớp chéo:
    - `normalized.quotation_id == package.quotation_id`
    - `corrections.quotation_id == package.quotation_id`
    - `normalized.supplier_code.upper() == package.supplier.code.upper()`
    - `normalized.quotation_date == package.quotation_date`

---

### 3. Nâng Cấp Chỉ Mục (Indexer) và CLI

#### [MODIFY] [material_indexer.py](file:///D:/mep_quotation_pipeline/mep_quotation/indexer/material_indexer.py)
- Cập nhật chữ ký hàm `build_material_index` để trả về `tuple[Path, list[Path]]` đại diện cho `(index_file_path, list_of_skipped_files)` và nhận thêm tham số `strict: bool = False`:
  - Trong Strict Mode (`strict=True`): Ném exception ngay khi bắt gặp bất kỳ file `normalized.json` nào bị lỗi validation.
  - Trong Non-Strict Mode (`strict=False`): Gom các tệp lỗi vào danh sách `skipped_files`, in warning rõ ràng ra stdout và tiếp tục build index cho các file còn lại.

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Cập nhật lệnh `validate-package` để tự động gọi thêm `validate_package_integrity` nhằm thực hiện kiểm tra tính toàn vẹn liên kết.
- Cập nhật lệnh `build-index`:
  - Nhận thêm flag `--strict` (strict mode).
  - Cập nhật call site để nhận tuple trả về `(index_file_path, skipped_files)`.
  - In ra màn hình cảnh báo rõ ràng kèm danh sách `skipped_files` nếu có file lỗi.

---

### 4. Bổ Sung Bộ Kiểm Thử (Tests)

#### [NEW] [test_integrity_mismatch.py](file:///D:/mep_quotation_pipeline/tests/test_integrity_mismatch.py)
- Viết bộ kiểm thử bao phủ toàn bộ các kịch bản mismatch và thắt chặt dữ liệu:
  - Reject `NormalizedQuotationModel` có format `quotation_id` sai.
  - Reject `NormalizedQuotationModel` có `supplier_code` không khớp `quotation_id`.
  - Reject `NormalizedQuotationModel` có `quotation_date` không khớp `quotation_id` hoặc là ngày không tồn tại (ví dụ: ngày 2026-02-30).
  - Reject `validate_package_integrity` khi `normalized.quotation_id` hoặc `corrections.quotation_id` bị lệch so với `package.json`.
  - Kiểm thử `build_material_index` chế độ non-strict trả về chính xác danh sách các tệp bị bỏ qua.
  - Kiểm thử `build_material_index` chế độ strict ném ra ngoại lệ.

#### [MODIFY] [test_material_indexer.py](file:///D:/mep_quotation_pipeline/tests/test_material_indexer.py)
- Cập nhật call site của `build_material_index` để nhận tuple trả về `(index_file, skipped)` để tương thích với thay đổi chữ ký hàm.

---

### 5. Cập Nhật Tài Liệu và JSON Schemas

#### [MODIFY] [README.md](file:///D:/mep_quotation_pipeline/README.md)
- Ghi nhận mô tả convention của `package_path` là relative path từ Project Root.
- Bổ sung tài liệu hướng dẫn cho flag `--strict` của lệnh `build-index`.

#### [RUN] [Schema Generator]
- Thực thi `python scripts/generate_schemas.py` để cập nhật lại các file JSON Schema trên đĩa, phản ánh đúng thay đổi mô tả (description) của models.

---

## Quy Trình Xác Minh Bắt Buộc (Verification)
1. Cài đặt lại thư viện ở chế độ editable:
   ```bash
   python -m pip install -e ".[dev]"
   ```
2. Sinh lại schema:
   ```bash
   python scripts/generate_schemas.py
   ```
3. Chạy toàn bộ bộ unit tests:
   ```bash
   python -m pytest -v
   ```
