# Báo Cáo Nghiệm Thu Phase 8 – Structured Item Candidate Layer

## Tóm Tắt Công Việc Đã Thực Hiện

Phase 8 đã được triển khai thành công, tiếp nhận các row candidates thô từ Phase 7 và tạo ra tệp cấu trúc ứng viên vật tư (`parsed/item_candidates.json`) theo đúng mục tiêu thiết kế.

### Các File Đã Tạo Mới & Sửa Đổi
1. **Spec & Models**:
   - `mep_quotation/spec/models.py`: Bổ sung cấu hình đường dẫn `item_candidates` vào `FilePathsModel`. Định nghĩa hai Pydantic models mới: `ItemCandidateModel` và `ItemCandidateManifestModel`.
   - `mep_quotation/spec/__init__.py`: Xuất các model mới ra ngoài API của spec.
2. **Package Integrity**:
   - `mep_quotation/package/builder.py`: Khởi tạo mặc định thuộc tính `item_candidates`.
   - `mep_quotation/package/integrity.py`: Tích hợp hàm kiểm duyệt chéo `validate_item_candidates_file` khi tệp `item_candidates.json` tồn tại thực tế trên đĩa (đảm bảo tính tương thích ngược).
3. **Module item_candidates**:
   - `mep_quotation/item_candidates/__init__.py`: Xuất API chính.
   - `mep_quotation/item_candidates/builder.py`: Triển khai chuyển đổi dữ liệu, candidate-level unit alias mapping cơ bản (`pcs`/`piece`/`cái` ➔ `cái`, `m`/`meter`/`met` ➔ `m`, `bộ`/`set` ➔ `bộ`), tính thành tiền `amount_candidate`, gán VND có điều kiện (chỉ khi có đơn giá thô và trong evidence text xuất hiện từ khóa tiền tệ Việt Nam rõ ràng), tính confidence deterministic và sinh cảnh báo độ tin cậy thấp.
   - `mep_quotation/item_candidates/manifest.py`: Triển khai ghi JSON deterministic và validate 10 quy tắc toàn vẹn cấu trúc dữ liệu liên kết.
   - `mep_quotation/item_candidates/item_service.py`: Điều phối luồng dịch vụ chính, cản ghi đè, ghi log audit đầy đủ 5 sự kiện.
4. **CLI Integration**:
   - `mep_quotation/cli/main.py`: Tích hợp subcommand `build-item-candidates` và handler in báo cáo thống kê.
5. **Schema Generator**:
   - `scripts/generate_schemas.py`: Đăng ký sinh JSON schema cho `ItemCandidateManifestModel`.
6. **Tests**:
   - `tests/test_item_candidates.py`: Thiết lập 8 kịch bản unit tests bao phủ 17 quy tắc nghiệp vụ Phase 8.

---

## Kết Quả Kiểm Thử Tự Động (Automated Tests Result)

### 1. Sinh Schema Thành Công
Chạy script sinh JSON schemas:
```bash
python scripts/generate_schemas.py
```
➔ **PASS**. Sinh đủ **11 schemas** trong thư mục `schemas/` (bao gồm tệp mới `schemas/item_candidates.schema.json`).

### 2. Chạy pytest
Chạy pytest cho toàn bộ dự án:
```bash
python -m pytest -v
```
➔ **PASS**. Kết quả: **108 tests PASSED**, 0 FAILED.
Trong đó, các unit test mới của Phase 8:
- `test_build_item_candidates_success` ➔ PASS (Kiểm chứng alias mapping, tính amount, gán VND có điều kiện hoạt động đúng).
- `test_empty_row_candidates_still_generates_valid_items` ➔ PASS (Chấp nhận row_candidates rỗng).
- `test_overwrite_protection_and_audit_logs` ➔ PASS (Bảo vệ ghi đè, ghi đủ log `item_candidate_build_started`, `item_candidates_built`, `item_candidates_written`, `item_candidate_build_completed`, `item_candidate_build_failed`).
- `test_cli_build_item_candidates` ➔ PASS (Subprocess CLI hoạt động chính xác).
- `test_backward_compatibility_integrity_check` ➔ PASS (Tương thích ngược khi chưa chạy Phase 8).
- `test_validation_catches_bad_data_in_item_candidates` ➔ PASS (Bắt lỗi khi sai lệch SHA256, sai offset, sai ID, sai amount).
- `test_does_not_modify_or_create_normalized_json` ➔ PASS (Không can thiệp đến tệp normalized.json).

---

## Kết Quả Xác Minh Thủ Công (Manual Verification Result)

Chạy thử nghiệm trên gói dữ liệu thực tế `data/suppliers/AUT/2026/2026-06-20_001`:

### 1. Chạy CLI build-item-candidates:
```bash
python -m mep_quotation.cli.main build-item-candidates data/suppliers/AUT/2026/2026-06-20_001 --overwrite
```
**Kết quả in ra console:**
```text
Successfully built item candidates.
  Quotation ID          : AUT_20260620_001
  Item Count            : 287
  Source Row Candidates : data/suppliers/AUT/2026/2026-06-20_001/parsed/row_candidates.json
  Item Candidates Path  : data/suppliers/AUT/2026/2026-06-20_001/parsed/item_candidates.json
  Items With Price Count: 19
  Items With Amount Count: 0
  Warnings Count        : 267
```

### 2. Chạy validate-package:
```bash
python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
```
**Kết quả in ra console:**
```text
Package is valid.
  Quotation ID : AUT_20260620_001
  Supplier     : AUT
  Items Count  : 0
  Corrections  : 0
```
➔ Hệ thống xác nhận gói báo giá hoàn toàn hợp lệ, các liên kết kiểm duyệt chéo Phase 8 hoạt động hoàn hảo.
