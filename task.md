# Danh Sách Công Việc MEP Quotation Pipeline Phase 9 – Normalized Draft Layer

## Component 1 – Spec & Models

- [x] Thêm trường `normalized_draft: str = Field("normalized/normalized_draft.json", ...)` vào `FilePathsModel` trong `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `NormalizedDraftEvidenceModel` vào `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `NormalizedDraftItemModel` vào `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `NormalizedDraftModel` vào `mep_quotation/spec/models.py`
- [x] Export `NormalizedDraftEvidenceModel`, `NormalizedDraftItemModel`, và `NormalizedDraftModel` trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder & Integrity

- [x] Cập nhật `builder.py` để gán mặc định `normalized_draft="normalized/normalized_draft.json"` khi khởi tạo gói mới
- [x] Cập nhật `integrity.py` gọi hàm `validate_normalized_draft_file(manifest_path, package_path)` kiểm tra tính toàn vẹn của normalized draft (chỉ chạy khi tệp manifest thực tế tồn tại trên đĩa)

## Component 3 – Module normalized_draft (MỚI)

- [x] Tạo thư mục `mep_quotation/normalized_draft/`
- [x] Tạo `mep_quotation/normalized_draft/__init__.py` (export `build_normalized_draft` và các lớp models)
- [x] Tạo `mep_quotation/normalized_draft/builder.py`
  - [x] Triển khai chuyển đổi Item Candidates sang Normalized Draft Items
  - [x] Triển khai mapping thuộc tính thô từ candidate (description trim, material_code, brand, unit, quantity, unit_price, currency)
  - [x] Triển khai gán lý do review (`missing_description`, `missing_unit`, `missing_unit_price`, `missing_quantity`) theo đúng quy tắc
  - [x] Triển khai gán currency chung cấp manifest có điều kiện (nếu có currency rõ ràng trong package metadata hoặc đa số items)
  - [x] Triển khai tính toán và so khớp `amount = quantity * unit_price`, gán warning `amount_mismatch_recomputed` nếu sai lệch
  - [x] Triển khai chấm điểm Confidence điều chỉnh theo các tiêu chí trừ điểm/cộng điểm và clamp trong khoảng `[0.0, 1.0]`
  - [x] Triển khai phân loại `review_status` chính xác (`auto_ready`, `needs_review`, `rejected_candidate`)
- [x] Tạo `mep_quotation/normalized_draft/manifest.py`
  - [x] Hàm `write_normalized_draft(path, data)`: ghi JSON dạng deterministic
  - [x] Hàm `validate_normalized_draft_file(manifest_path, package_path)` kiểm duyệt các quy tắc validation (độc bản ID, khớp SHA256 file item_candidates.json, page_number/line/offset khớp source, raw_evidence_text khớp lát cắt, amount tính toán đúng, review_required_count đúng)
  - [x] Ràng buộc nghiêm ngặt: kiểm tra Phase 9 không được phép can thiệp thay đổi nội dung tệp `normalized.json`
- [x] Tạo `mep_quotation/normalized_draft/draft_service.py`
  - [x] Hàm `build_normalized_draft(package_path, overwrite=False) -> Path`
  - [x] Tạo thư mục `normalized/` nếu chưa tồn tại
  - [x] Kiểm duyệt đầu vào (sự tồn tại của các tệp Phase 8)
  - [x] Ghi nhận SHA256 ban đầu của `normalized.json` nếu có từ trước, so khớp sau khi build để đảm bảo KHÔNG bị thay đổi
  - [x] Đảm bảo không tự tạo mới `normalized.json` nếu file chưa tồn tại trước đó
  - [x] Kiểm tra cản ghi đè cho `normalized_draft.json`
  - [x] Tạo `normalized/normalized_draft.json`
  - [x] Cập nhật package.json và chạy đối chiếu toàn vẹn gói
  - [x] Đảm bảo ghi log audit đầy đủ (normalized_draft_build_started, normalized_draft_built, normalized_draft_written, normalized_draft_build_completed) / thất bại (normalized_draft_build_failed)

## Component 4 – CLI Integration

- [x] Thêm handler `handle_build_normalized_draft(args)` trong `cli/main.py`
- [x] Đăng ký subcommand `build-normalized-draft <package_path> [--overwrite]` trong `cli/main.py`
- [x] Cập nhật description CLI hỗ trợ thông tin Phase 9

## Component 5 – Schema Generation

- [x] Thêm `NormalizedDraftModel` vào `scripts/generate_schemas.py`
- [x] Chạy sinh schema mới và xác thực tệp `schemas/normalized_draft.schema.json` được tạo thành công

## Component 6 – Tests

- [x] Tạo tệp kiểm thử `tests/test_normalized_draft.py` bao phủ đầy đủ:
  - [x] Dựng thành công draft từ item_candidates hợp lệ
  - [x] `supplier_code` và `quotation_date` lấy đúng từ package.json hoặc để null không fail
  - [x] `draft_item_id` unique và deterministic
  - [x] Không silently drop bất kỳ item candidate nào
  - [x] Phân loại `review_status` chính xác (auto_ready, needs_review, rejected_candidate)
  - [x] Không mặc định quantity = 1 hay VND nếu không có bằng chứng
  - [x] amount tính toán đúng, gán warning `amount_mismatch_recomputed` khi lệch
  - [x] Overwrite rule và CLI subprocess hoạt động đúng
  - [x] Audit logs ghi đầy đủ
  - [x] Tương thích ngược: validate gói chưa chạy Phase 9 hoạt động tốt
  - [x] SHA256 của `normalized.json` trước/sau không đổi
  - [x] Phase 9 không tự tạo `normalized.json` nếu chưa tồn tại
  - [x] Bắt lỗi validation của validate_normalized_draft_file khi:
    - [x] `source_item_candidate_id` không tồn tại
    - [x] `source_sha256` sai lệch
    - [x] `raw_evidence_text` bị lệch so với dòng gốc
    - [x] `review_status` sai
    - [x] `review_required_count` không chính xác

## Component 7 – Tài liệu

- [x] Cập nhật `README.md` hướng dẫn sử dụng lệnh CLI `build-normalized-draft`
- [x] Ghi nhận báo cáo nghiệm thu Phase 9 vào `walkthrough.md` sau khi hoàn tất

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` sinh đủ **12 schemas**
- [x] `python -m pytest -v` đạt 100% passed (115 tests passed)
- [x] Thực hiện Manual Acceptance Test kiểm tra log kiểm toán và cấu trúc file JSON kết quả
