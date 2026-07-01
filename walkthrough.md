# Kết Quả Nghiệm Thu MEP Quotation Pipeline Phase 9 – Normalized Draft Layer

## Các công việc đã thực hiện
Phase 9 nhận dữ liệu đầu vào từ tệp ứng viên vật tư (`parsed/item_candidates.json`) được tạo ở Phase 8, và xây dựng thành công tệp dữ liệu nháp chuẩn hóa `normalized/normalized_draft.json` để phục vụ rà soát thủ công hoặc đối chiếu ở các phase sau.

### 1. Spec & Models
- Bổ sung trường `normalized_draft` vào `FilePathsModel` trong `models.py`.
- Định nghĩa các Pydantic models mới chính xác làm Source of Truth:
  - `NormalizedDraftEvidenceModel`: trace vết văn bản gốc từ candidate.
  - `NormalizedDraftItemModel`: chứa cấu trúc dữ liệu nháp chuẩn hóa chi tiết cho từng dòng vật tư.
  - `NormalizedDraftModel`: manifest kê khai tổng số lượng items, trạng thái cần rà soát và siêu dữ liệu đi kèm.
- Xuất các model qua `mep_quotation/spec/__init__.py`.

### 2. Module mep_quotation/normalized_draft/
- Triển khai `builder.py` để chuyển đổi deterministic từ item candidates sang draft items:
  - Trim whitespace mô tả.
  - Tự động tính toán thành tiền `amount = quantity * unit_price` và validate so khớp với dữ liệu ứng viên gốc, phát cảnh báo `amount_mismatch_recomputed` khi lệch.
  - Gán tiền tệ chung có điều kiện hoặc kế thừa từ thuộc tính candidate.
  - Điều chỉnh điểm tin cậy `confidence` clamp trong `[0.0, 1.0]` và phân loại trạng thái rà soát `review_status` (`auto_ready`, `needs_review`, `rejected_candidate`).
- Triển khai `manifest.py` chứa logic ghi tệp JSON deterministic và hàm validate toàn vẹn 14 quy tắc chéo bắt buộc.
- Triển khai `draft_service.py` để điều phối luồng xử lý: kiểm duyệt đầu vào, overwrite check, ghi audit log, cập nhật package.json và bảo vệ tuyệt đối tệp `normalized.json` chính thức (không thay đổi SHA256, không tự ý tạo mới).

### 3. CLI & Schema
- Tích hợp subcommand `build-normalized-draft` vào CLI.
- Tích hợp tự động sinh JSON Schema mới `normalized_draft.schema.json` trong `generate_schemas.py`.

---

## Kết quả kiểm thử tự động (Pytest)
Chạy toàn bộ 115 pytest thành công 100%:
```
tests/test_normalized_draft.py::test_build_normalized_draft_success PASSED
tests/test_normalized_draft.py::test_empty_candidates_generates_valid_empty_draft PASSED
tests/test_normalized_draft.py::test_overwrite_protection_and_integrity_audit PASSED
tests/test_normalized_draft.py::test_cli_build_normalized_draft PASSED
tests/test_normalized_draft.py::test_normalized_json_safety_protection PASSED
tests/test_normalized_draft.py::test_validation_catches_errors_in_manifest PASSED
tests/test_normalized_draft.py::test_amount_mismatch_warning_generation PASSED

============================= 115 passed in 5.30s =============================
```

---

## Kết quả nghiệm thu thủ công (Manual Acceptance Test)
Chạy trực tiếp CLI trên gói dữ liệu thực tế `data/suppliers/AUT/2026/2026-06-20_001`:
```bash
python -m mep_quotation.cli.main build-normalized-draft data/suppliers/AUT/2026/2026-06-20_001 --overwrite
```
**Kết quả hiển thị:**
```
Successfully built normalized draft.
  Quotation ID          : AUT_20260620_001
  Supplier Code         : AUT
  Quotation Date        : 2026-06-20
  Item Count            : 287
  Review Required Count : 264
  Auto Ready Count      : 0
  Rejected Candidate Count: 23
  Source Item Candidates: data/suppliers/AUT/2026/2026-06-20_001/parsed/item_candidates.json
  Normalized Draft Path : data/suppliers/AUT/2026/2026-06-20_001/normalized/normalized_draft.json
  Warnings Count        : 856
```

### 1. Overwrite Protection:
Chạy lại không có `--overwrite` ném lỗi đúng mong đợi:
`Error building normalized draft: Normalized draft file already exists at ... Set overwrite=True to replace it.`

### 2. Dữ liệu nháp được tạo:
- Tạo thành công tệp `normalized/normalized_draft.json` khớp schema.
- Toàn bộ 287 ứng viên được giữ lại đầy đủ (không silently drop).
- Trạng thái rà soát và lý do cần rà soát (`missing_unit`, `missing_quantity`, `currency_uncertain`, `low_confidence`) được định nghĩa rõ ràng.

### 3. Bảo vệ dữ liệu chính thức:
- Chạy `git status` xác nhận tệp `normalized.json` chính thức không bị chạm vào hoặc chỉnh sửa nội dung, SHA256 hoàn toàn không đổi.
- Chạy `validate-package` thành công, báo cáo gói dữ liệu hoàn toàn hợp lệ.
