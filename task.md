# Danh Sách Công Việc MEP Quotation Pipeline Phase 7 – Row Candidate Assembly / Price Association Layer

## Component 1 – Spec & Models

- [x] Thêm trường `row_candidates: str = Field("parsed/row_candidates.json", ...)` vào `FilePathsModel` trong `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `RowCandidateModel` vào `mep_quotation/spec/models.py`
- [x] Thêm Pydantic model `RowCandidateManifestModel` vào `mep_quotation/spec/models.py`
- [x] Export `RowCandidateModel` và `RowCandidateManifestModel` trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder & Integrity

- [x] Cập nhật `builder.py` để gán mặc định `row_candidates="parsed/row_candidates.json"` khi khởi tạo gói mới
- [x] Cập nhật `integrity.py` gọi hàm `validate_row_candidates_file(manifest_path, package_path)` kiểm tra tính toàn vẹn của row candidates (chỉ chạy khi tệp manifest thực tế tồn tại trên đĩa)

## Component 3 – Module row_assembly (MỚI)

- [x] Tạo thư mục `mep_quotation/row_assembly/`
- [x] Tạo `mep_quotation/row_assembly/__init__.py` (export `assemble_row_candidates` và các lớp models)
- [x] Tạo `mep_quotation/row_assembly/assembler.py`
  - [x] Triển khai phân nhóm line candidates theo `page_number`
  - [x] Triển khai thuật toán gom dòng trong trang:
    - [x] Nhận diện description mạnh để tách dòng (bắt đầu row mới khi có description mạnh tiếp theo)
    - [x] Nhận diện price-only line để gộp vào mô tả gần nhất trên trang (khoảng cách gap <= `max_line_gap_for_price`)
    - [x] Không gộp 2 đơn giá riêng biệt vào cùng 1 row
    - [x] Nhận diện thông số phụ trợ (gap dòng <= 3) để gộp thông tin
  - [x] Triển khai Price Association Rules: Tránh bắt nhầm các thông số kỹ thuật (`1.5mm2`, `100A`, `25kA`, `D25`, `DN25`, `PN10`, `3P`, v.v.) làm đơn giá
  - [x] Triển khai tính toán Confidence deterministic theo điểm cộng dồn các thuộc tính và gán cảnh báo `low_confidence` nếu confidence < 0.5
  - [x] Triển khai tính toán offset bắt đầu/kết thúc lớn nhất của row candidates và trích xuất `evidence_text`
- [x] Tạo `mep_quotation/row_assembly/manifest.py`
  - [x] Hàm `write_row_candidates_manifest(path, data)`: ghi JSON deterministic
  - [x] Hàm `validate_row_candidates_file(manifest_path, package_path)` thực hiện kiểm duyệt các quy tắc validation (ids tồn tại trong line_candidates, cùng page_number, offset hợp lệ, evidence_text khớp lát cắt, checksum SHA256 của line_candidates khớp)
  - [x] Bảo đảm rule: Phase 7 không tự ý tạo mới hoặc sửa đổi nội dung tệp `normalized.json` (nếu đã có từ Phase trước thì giữ nguyên)
- [x] Tạo `mep_quotation/row_assembly/row_service.py`
  - [x] Hàm `assemble_row_candidates(package_path, overwrite=False, max_line_gap_for_price=6) -> Path`
  - [x] Kiểm duyệt đầu vào (sự tồn tại của các tệp Phase 6)
  - [x] Kiểm tra cản ghi đè (Atomic check)
  - [x] Tạo thư mục `parsed/` trước khi ghi file, điều phối assembler và manifest writer
  - [x] Cập nhật `package.json` và chạy đối chiếu toàn vẹn gói
  - [x] Đảm bảo ghi log audit thành công (row_assembly_started, row_candidates_assembled, row_candidates_written, row_assembly_completed) / thất bại (row_assembly_failed) trước khi re-raise lỗi

## Component 4 – CLI Integration

- [x] Thêm handler `handle_assemble_rows(args)` trong `cli/main.py`
- [x] Đăng ký subcommand `assemble-rows <package_path> [--overwrite] [--max-line-gap-for-price 6]` trong `cli/main.py`
- [x] Cập nhật description CLI hỗ trợ thông tin Phase 7

## Component 5 – Schema Generation

- [x] Thêm `RowCandidateManifestModel` vào `scripts/generate_schemas.py`
- [x] Chạy sinh schema mới và xác thực tệp `schemas/row_candidates.schema.json` được tạo thành công

## Component 6 – Tests

- [x] Tạo tệp kiểm thử `tests/test_row_assembly.py` bao phủ đầy đủ:
  - [x] `line_candidates` rỗng vẫn sinh tệp `row_candidates.json` hợp lệ với `row_count = 0` và `rows = []`
  - [x] Gom dòng chứa mô tả và dòng đơn giá (`price-only`) nằm gần nhau trên cùng trang
  - [x] Tránh liên kết giá xuyên trang hoặc khoảng cách dòng quá xa
  - [x] Tránh bắt nhầm thông số kỹ thuật làm đơn giá
  - [x] Không gom hai mô tả vật tư độc lập mạnh vào cùng một row
  - [x] So khớp `evidence_text` chuẩn xác lát cắt Markdown qua offset
  - [x] Kiểm tra cản ghi đè `overwrite=False` ném lỗi và ghi log `row_assembly_failed` tương ứng
  - [x] Kiểm tra cho phép ghi đè `overwrite=True` hoạt động thành công
  - [x] CLI subprocess `assemble-rows` chạy thành công và ghi log `row_assembly_completed`
  - [x] Tương thích ngược: validate gói chưa có `row_candidates.json` vẫn hoạt động tốt
  - [x] Bắt lỗi validation chính xác của validate_package_integrity / validate_row_candidates_file khi:
    - [x] `source_candidate_ids` không tồn tại trong `line_candidates.json`
    - [x] các source candidates trong một row bị lệch `page_number` khác nhau
    - [x] `evidence_text` không khớp lát cắt `markdown_content[start_offset:end_offset]`
    - [x] `source_sha256` của manifest bị sai lệch
  - [x] Xác nhận Phase 7 không tự ý tạo ra file `normalized.json` nếu fixture chưa có, và giữ nguyên không sửa đổi nội dung tệp `normalized.json` nếu tệp đã được tạo sẵn từ trước.

## Component 7 – Tài liệu

- [x] Cập nhật `README.md` hướng dẫn sử dụng lệnh CLI `assemble-rows`
- [x] Ghi nhận báo cáo nghiệm thu Phase 7 vào `walkthrough.md` sau khi hoàn tất

## Verification Bắt Buộc

- [x] `python -m pip install -e ".[dev]"` thành công
- [x] `python scripts/generate_schemas.py` sinh đủ **10 schemas**
- [x] `python -m pytest -v` đạt 100% passed (khoảng 102 tests passed)
- [x] Thực hiện Manual Acceptance Test kiểm tra log kiểm toán và cấu trúc file JSON kết quả
