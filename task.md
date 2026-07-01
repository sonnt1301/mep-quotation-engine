# Danh Sách Công Việc MEP Quotation Pipeline Phase 8 – Structured Item Candidate Layer

## Component 1 – Spec & Models

- [x] Thêm trường `item_candidates: str = Field("parsed/item_candidates.json", ...)` vào `FilePathsModel` trong `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `ItemCandidateModel` vào `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `ItemCandidateManifestModel` vào `mep_quotation/spec/models.py`
- [x] Export `ItemCandidateModel` và `ItemCandidateManifestModel` trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder & Integrity

- [x] Cập nhật `builder.py` để gán mặc định `item_candidates="parsed/item_candidates.json"` khi khởi tạo gói mới
- [x] Cập nhật `integrity.py` gọi hàm `validate_item_candidates_file(manifest_path, package_path)` kiểm tra tính toàn vẹn của item candidates (chỉ chạy khi tệp manifest thực tế tồn tại trên đĩa)

## Component 3 – Module item_candidates (MỚI)

- [x] Tạo thư mục `mep_quotation/item_candidates/`
- [x] Tạo `mep_quotation/item_candidates/__init__.py` (export `build_item_candidates` và các lớp models)
- [x] Tạo `mep_quotation/item_candidates/builder.py`
  - [x] Triển khai chuyển đổi Row Candidates sang Item Candidates thô
  - [x] Triển khai gộp mapping alias cho `unit_candidate` cơ bản (`pcs`/`piece`/`cái` -> `cái`, `m`/`meter`/`met` -> `m`, `bộ`/`set` -> `bộ`). Đây là candidate-level alias mapping, không phải normalized unit và không tạo normalized output.
  - [x] Triển khai tính toán `amount_candidate = quantity_candidate * unit_price_candidate` khi có đủ dữ liệu, ngược lại gán Null
  - [x] Triển khai gán đơn vị tiền tệ mặc định `VND` cho `currency_candidate` có điều kiện (chỉ khi có đơn giá mà currency Null, và package/row/context thể hiện rõ báo giá VND, không tự đoán)
  - [x] Triển khai tính toán Confidence deterministic theo điểm cộng dồn thuộc tính và clamp trong khoảng `[0.0, 1.0]`
  - [x] Triển khai gán warnings và mã warnings `low_confidence` nếu confidence < 0.5
- [x] Tạo `mep_quotation/item_candidates/manifest.py`
  - [x] Hàm `write_item_candidates_manifest(path, data)`: ghi JSON deterministic
  - [x] Hàm `validate_item_candidates_file(manifest_path, package_path)` thực hiện kiểm duyệt các quy tắc validation (độc bản ID, khớp SHA256 file row_candidates.json, page_number/line_number/offset khớp row nguồn, raw_evidence_text khớp lát cắt, amount_candidate tính toán đúng)
  - [x] Bảo đảm rule: Phase 8 không tự ý tạo mới hoặc sửa đổi nội dung tệp `normalized.json` (nếu đã có từ Phase trước thì giữ nguyên)
- [x] Tạo `mep_quotation/item_candidates/item_service.py`
  - [x] Hàm `build_item_candidates(package_path, overwrite=False) -> Path`
  - [x] Kiểm duyệt đầu vào (sự tồn tại của các tệp Phase 7)
  - [x] Kiểm tra cản ghi đè (Atomic check)
  - [x] Tạo thư mục `parsed/` trước khi ghi file, điều phối builder và manifest writer
  - [x] Cập nhật `package.json` và chạy đối chiếu toàn vẹn gói
  - [x] Đảm bảo ghi log audit thành công (item_candidate_build_started, item_candidates_built, item_candidates_written, item_candidate_build_completed) / thất bại (item_candidate_build_failed) trước khi re-raise lỗi

## Component 4 – CLI Integration

- [x] Thêm handler `handle_build_item_candidates(args)` trong `cli/main.py`
- [x] Đăng ký subcommand `build-item-candidates <package_path> [--overwrite]` trong `cli/main.py`
- [x] Cập nhật description CLI hỗ trợ thông tin Phase 8

## Component 5 – Schema Generation

- [x] Thêm `ItemCandidateManifestModel` vào `scripts/generate_schemas.py`
- [x] Chạy sinh schema mới và xác thực tệp `schemas/item_candidates.schema.json` được tạo thành công

## Component 6 – Tests

- [x] Tạo tệp kiểm thử `tests/test_item_candidates.py` bao phủ đầy đủ:
  - [x] Chuyển đổi thành công từ row candidate hợp lệ sang item candidate
  - [x] `item_candidate_id` duy nhất và có tính deterministic
  - [x] `source_sha256` khớp SHA256 của `row_candidates.json`
  - [x] `raw_evidence_text` khớp lát cắt Markdown qua offset
  - [x] `amount_candidate` tính toán chính xác khi đủ dữ liệu, và bằng Null khi thiếu
  - [x] Không tự ý sinh cảnh báo `quantity_missing` mặc định
  - [x] Tự động gán cảnh báo `low_confidence` khi thiếu nhiều thuộc tính
  - [x] Đơn vị tính alias mapping cơ bản hoạt động đúng
  - [x] `row_candidates` rỗng vẫn sinh tệp `item_candidates.json` hợp lệ
  - [x] Kiểm tra cản ghi đè `overwrite=False` ném lỗi và ghi log `item_candidate_build_failed` tương ứng
  - [x] Kiểm tra cho phép ghi đè `overwrite=True` hoạt động thành công
  - [x] CLI subprocess `build-item-candidates` chạy thành công và ghi log `item_candidate_build_completed`
  - [x] Tương thích ngược: validate gói chưa có `item_candidates.json` vẫn hoạt động tốt
  - [x] Bắt lỗi validation chính xác của validate_package_integrity / validate_item_candidates_file khi:
    - [x] `source_row_id` không tồn tại hoặc sai lệch
    - [x] `source_sha256` sai lệch
    - [x] `raw_evidence_text` bị lệch so với dòng gốc
    - [x] `amount_candidate` tính toán sai
  - [x] Xác nhận Phase 8 không tự ý tạo ra file `normalized.json` nếu fixture chưa có, và giữ nguyên không sửa đổi nội dung tệp `normalized.json` nếu tệp đã được tạo sẵn từ trước.

## Component 7 – Tài liệu

- [x] Cập nhật `README.md` hướng dẫn sử dụng lệnh CLI `build-item-candidates`
- [x] Ghi nhận báo cáo nghiệm thu Phase 8 vào `walkthrough.md` sau khi hoàn tất

## Verification Bắt Buộc

- [x] `python -m pip install -e ".[dev]"` thành công
- [x] `python scripts/generate_schemas.py` sinh đủ **11 schemas**
- [x] `python -m pytest -v` đạt 100% passed (khoảng 108 tests passed)
- [x] Thực hiện Manual Acceptance Test kiểm tra log kiểm toán và cấu trúc file JSON kết quả
