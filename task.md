# Danh Sách Công Việc MEP Quotation Pipeline Phase 1 - Harden Data Contract

- `[x]` Sửa lỗi packaging trong `pyproject.toml`
- `[x]` Thắt chặt validation cho `NormalizedQuotationModel` trong `mep_quotation/spec/models.py`
- `[x]` Tạo module `mep_quotation/package/integrity.py` và hàm `validate_package_integrity`
- `[x]` Cập nhật CLI `validate-package` để kiểm tra toàn vẹn liên kết dữ liệu
- `[x]` Nâng cấp `build_material_index` trong `mep_quotation/indexer/material_indexer.py` (chữ ký hàm mới và strict mode)
- `[x]` Cập nhật CLI `build-index` và các test cũ tương thích với chữ ký hàm mới của indexer
- `[x]` Cập nhật tài liệu `README.md`
- `[x]` Sinh lại các file JSON Schema qua script `generate_schemas.py`
- `[x]` Viết bộ test mới `tests/test_integrity_mismatch.py`
- `[x]` Thực hiện quy trình xác minh bắt buộc (Verify):
  - `[x]` Chạy `python -m pip install -e ".[dev]"`
  - `[x]` Chạy `python scripts/generate_schemas.py`
  - `[x]` Chạy `python -m pytest -v` và kiểm tra tất cả test đều pass.
