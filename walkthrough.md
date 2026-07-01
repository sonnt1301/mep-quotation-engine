# Báo Cáo Nghiệm Thu Phase 7 – Row Candidate Assembly / Price Association Layer

Phase 7 đã được triển khai hoàn chỉnh và nghiệm thu thành công. Hệ thống có khả năng gom nhóm các line candidates đơn lẻ thành các row candidates ghép hợp lý và liên kết giá thô chặt chẽ, đồng thời đáp ứng 100% các yêu cầu về kiểm toán, kiểm thử tự động và kiểm duyệt toàn vẹn package.

---

## 1. Các Thay Đổi & Nâng Cấp Hệ Thống

1. **Spec & Models ([models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py))**:
   - Thêm trường `row_candidates: str = Field("parsed/row_candidates.json", ...)` vào `FilePathsModel`.
   - Định nghĩa hai model Pydantic chính thức `RowCandidateModel` và `RowCandidateManifestModel` chứa đầy đủ thông tin nguồn, các thuộc tính của dòng ứng viên ghép, evidence offset và cảnh báo warnings.
   - Xuất (export) models trong `spec/__init__.py`.
2. **Package Builder & Integrity ([builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py) & [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py))**:
   - Gán mặc định đường dẫn file row candidates khi dựng package mới.
   - Tích hợp kiểm duyệt toàn vẹn `validate_row_candidates_file` vào `validate_package_integrity` khi tệp `row_candidates.json` tồn tại thực tế trên đĩa (bảo đảm tính tương thích ngược).
3. **Module row_assembly (MỚI)**:
   - `assembler.py`: Triển khai thuật toán phân nhóm theo trang, gom dòng trong trang dựa trên khoảng cách (gap) và đặc trưng của line candidates (mô tả mạnh, price-only line, thông số phụ trợ). Tính toán deterministic confidence và clamp `[0.0, 1.0]`.
   - `manifest.py`: Ghi tệp JSON dạng deterministic và thực hiện kiểm duyệt validation 14 quy tắc chặt chẽ (độc bản ID, khớp SHA256 line candidates, offset và evidence text khớp lát cắt Markdown, v.v.). Phase 7 không tự ý tạo mới hoặc sửa đổi nội dung tệp `normalized.json`.
   - `row_service.py`: Điều phối toàn bộ luồng, kiểm tra ghi đè, ghi log audit đầy đủ 5 sự kiện (`row_assembly_started`, `row_candidates_assembled`, `row_candidates_written`, `row_assembly_completed`, `row_assembly_failed`).
4. **CLI Integration ([main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py))**:
   - Đăng ký subcommand `assemble-rows <package_path> [--overwrite] [--max-line-gap-for-price 6]`.
   - In ra báo cáo tóm tắt: Quotation ID, Row count, Source line candidates, Output path, Rows with price count, Warnings count.
5. **Schema Generation ([generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py))**:
   - Đăng ký và sinh thành công tệp `schemas/row_candidates.schema.json`.

---

## 2. Kết Quả Xác Thực Kỹ Thuật

### 🔹 Kết Quả Sinh JSON Schema
Chạy script sinh schema thành công:
```bash
python scripts/generate_schemas.py
```
Sinh đủ **10 schemas** (bao gồm `row_candidates.schema.json`).

### 🔹 Kết Quả Bộ Unit Tests Pytest
Chạy pytest trên toàn bộ dự án:
```bash
python -m pytest -v
```
Toàn bộ **101 tests PASSED / 0 FAILED** thành công tốt đẹp.
Các kịch bản kiểm thử quan trọng đã được xác minh thành công trong `tests/test_row_assembly.py`:
- `line_candidates` rỗng vẫn sinh tệp row candidates hợp lệ.
- Gom dòng chứa mô tả và dòng đơn giá (`price-only`) nằm gần nhau trên cùng trang.
- Tránh liên kết giá xuyên trang hoặc khoảng cách dòng quá xa.
- Không bắt nhầm thông số kỹ thuật làm đơn giá.
- Không gom hai mô tả vật tư độc lập mạnh vào cùng một row.
- `evidence_text` khớp chuẩn xác lát cắt Markdown qua offset.
- `source_sha256` khớp SHA256 của `line_candidates.json`.
- `row_id` duy nhất và có tính deterministic.
- Kiểm tra cản ghi đè `overwrite=False` ném lỗi và ghi log `row_assembly_failed` tương ứng.
- Kiểm tra cho phép ghi đè `overwrite=True` hoạt động thành công.
- CLI subprocess `assemble-rows` chạy thành công.
- `validate_package_integrity` bảo đảm tính tương thích ngược cho gói chưa có `row_candidates.json`.
- Xác nhận ghi nhận đầy đủ audit event `row_assembly_completed` khi chạy thành công và `row_assembly_failed` khi gặp lỗi.
- Xác nhận kiểm duyệt validation của `validate_package_integrity` / `validate_row_candidates_file` bắt lỗi chính xác khi sai ranh giới trang, sai offset, hoặc sai SHA256.
- Xác nhận Phase 7 không tự ý tạo ra file `normalized.json` nếu fixture chưa có, và giữ nguyên không sửa đổi nội dung tệp `normalized.json` nếu tệp đã được tạo sẵn từ trước.

---

## 3. Thử Nghiệm Thực Tế Trên Gói Báo Giá Thật

Thực hiện chạy trên gói báo giá `data/suppliers/AUT/2026/2026-06-20_001`:

1. **Khởi chạy thành công**:
   ```bash
   python -m mep_quotation.cli.main assemble-rows data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
   **Output**:
   ```text
   Successfully assembled row candidates.
     Quotation ID          : AUT_20260620_001
     Row Count             : 287
     Source Line Candidates: data/suppliers/AUT/2026/2026-06-20_001/parsed/line_candidates.json
     Row Candidates Path   : data/suppliers/AUT/2026/2026-06-20_001/parsed/row_candidates.json
     Rows With Price Count : 19
     Warnings Count        : 267
   ```
2. **Kiểm tra cản ghi đè (không truyền `--overwrite`)**:
   ```bash
   python -m mep_quotation.cli.main assemble-rows data/suppliers/AUT/2026/2026-06-20_001
   ```
   **Output**:
   ```text
   Error assembling row candidates: Row candidates file already exists at D:\mep_quotation_pipeline\data\suppliers\AUT\2026\2026-06-20_001\parsed\row_candidates.json. Set overwrite=True to replace it.
   ```
3. **Xác thực toàn gói**:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
   **Output**:
   ```text
   Package is valid.
     Quotation ID : AUT_20260620_001
     Supplier     : AUT
     Items Count  : 0
     Corrections  : 0
   ```
4. **Log audit ghi nhận đầy đủ**:
   Tệp `logs/processing.log.jsonl` ghi nhận chuỗi kiểm toán logic thành công:
   `row_assembly_started` ➔ `row_candidates_assembled` ➔ `row_candidates_written` ➔ `row_assembly_completed`.
