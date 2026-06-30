# Danh Sách Công Việc MEP Quotation Pipeline Phase 6 – Rule-based Line Candidate Extraction

## Component 1 – Spec & Models

- [x] Thêm trường `line_candidates: str = Field("parsed/line_candidates.json", ...)` vào `FilePathsModel` trong `mep_quotation/spec/models.py`
- [x] Thêm `ParserWarningModel` vào `mep_quotation/spec/models.py`
- [x] Thêm `LineCandidateEvidenceModel` vào `mep_quotation/spec/models.py`
- [x] Thêm `LineCandidateModel` vào `mep_quotation/spec/models.py`
- [x] Thêm `LineCandidatesManifestModel` vào `mep_quotation/spec/models.py`
- [x] Export 4 models mới trong `mep_quotation/spec/__init__.py`

## Component 2 – Package Builder & Integrity

- [x] Cập nhật `builder.py` để gán mặc định `line_candidates="parsed/line_candidates.json"` khi khởi tạo gói mới
- [x] Cập nhật `integrity.py` gọi hàm `validate_line_candidates_file(manifest_path, package_path)` kiểm tra tính toàn vẹn của ứng viên dòng (chỉ chạy khi tệp manifest thực tế tồn tại trên đĩa)

## Component 3 – Module parser (MỚI)

- [x] Tạo thư mục `mep_quotation/parser/`
- [x] Tạo `mep_quotation/parser/__init__.py` (export `parse_package_line_candidates` và các lớp models)
- [x] Tạo `mep_quotation/parser/candidate_models.py` (tái xuất models từ spec)
- [x] Tạo `mep_quotation/parser/line_parser.py`
  - [x] Triển khai Line Scanner: duyệt từng dòng Markdown, bỏ qua dòng trống/headings/metadata đầu file, map offset sang page_number từ `quotation_text.json`
  - [x] Ném lỗi `ValueError` rõ ràng khi offset của dòng không nằm trong range của trang nào, không fallback sang trang cuối
  - [x] Triển khai Candidate Detection Rules (giá, đơn vị tính, từ khóa MEP, mã vật tư)
  - [x] Triển khai Price Extraction Rules (bỏ qua thông số kỹ thuật `mm2`, `A`, `kA`, `PN`, `D`, v.v.; ưu tiên marker giá hoặc cuối dòng; gán Null + warning nếu không chắc chắn)
  - [x] Triển khai Brand Extraction Rules (so khớp với CADIVI, LS, Schneider, Panasonic, Sino, Daphaco, Trần Phú, Hager, ABB, Siemens)
  - [x] Triển khai Quantity Extraction Rules (số lượng thô + warning `quantity_missing` chỉ khi dòng đủ cấu trúc)
  - [x] Triển khai tính toán Confidence deterministic và đính kèm warning `low_confidence`
  - [x] Triển khai xuất evidence offset chính xác trong Markdown
- [x] Tạo `mep_quotation/parser/candidate_manifest.py`
  - [x] Hàm `write_line_candidates_manifest(path, data)`: ghi JSON deterministic
  - [x] Hàm `validate_line_candidates_file(manifest_path, package_path)` kiểm duyệt 12 quy tắc validate bao gồm so khớp SHA256 của file MD, tính độc bản ID, so khớp text thô qua offset, kiểm tra logic đơn giá/số lượng và cản ghi tệp chuẩn hóa
  - [x] Nạp `quotation_text.json` bằng `TextAssemblyManifestModel` và xác thực chặt chẽ range offset của candidate so với page tương ứng
- [x] Tạo `mep_quotation/parser/parser_service.py`
  - [x] Hàm `parse_package_line_candidates(package_path, overwrite=False) -> Path`
  - [x] Kiểm duyệt đầu vào (sự tồn tại của các file Phase 5)
  - [x] Kiểm tra ghi đè (Atomic check)
  - [x] Điều phối scanner và trích xuất candidates, ghi tệp `parsed/line_candidates.json`
  - [x] Thực hiện validate manifest sau ghi, cập nhật `package.json` và chạy đối chiếu toàn vẹn gói
  - [x] Đảm bảo ghi log audit thành công (5 events) / thất bại (re-raise lỗi và ghi `line_parser_failed`)

## Component 4 – CLI Integration

- [x] Thêm handler `handle_parse_line_candidates(args)` trong `cli/main.py`
- [x] Thêm subcommand `parse-line-candidates <package_path> [--overwrite]` trong `cli/main.py`
- [x] Cập nhật description CLI hỗ trợ thông tin Phase 6

## Component 5 – Schema Generation

- [x] Thêm `LineCandidatesManifestModel` vào `scripts/generate_schemas.py`
- [x] Chạy sinh schema mới và xác thực tệp `schemas/line_candidates.schema.json` được tạo thành công

## Component 6 – Tests

- [x] Tạo tệp kiểm thử `tests/test_line_parser.py` bao phủ đầy đủ:
  - [x] Phân tích dòng thô cơ bản, trích xuất giá/đơn vị/thương hiệu
  - [x] Tránh bắt nhầm thông số kỹ thuật (`1.5mm2`, `100A`, `25kA`, `D25`, v.v.)
  - [x] Cảnh báo `quantity_missing` và độ tin cậy thấp `low_confidence` đúng logic
  - [x] Bỏ qua headings/separators, mapping dòng và offset trang chuẩn xác
  - [x] Kiểm tra lỗi thiếu file đầu vào Phase 5
  - [x] Kiểm tra cản ghi đè khi `overwrite=False` và cho phép khi `overwrite=True` cùng log tương ứng
  - [x] Chạy CLI subprocess của lệnh `parse-line-candidates`
  - [x] Xác nhận chuỗi audit log đầy đủ và tính tương thích ngược của hàm kiểm tra toàn vẹn package
  - [x] Kiểm thử ném lỗi `ValueError` khi candidate có `page_number` bị lệch range offset
  - [x] Kiểm thử ném lỗi `ValueError` trong Line Scanner nếu offset dòng Markdown nằm ngoài tầm định vị trang

## Component 7 – Tài liệu

- [x] Cập nhật `README.md` hướng dẫn sử dụng lệnh CLI `parse-line-candidates`
- [x] Ghi nhận báo cáo nghiệm thu Phase 6 vào `walkthrough.md` sau khi hoàn tất

## Verification Bắt Buộc

- [x] `python -m pip install -e ".[dev]"` thành công
- [x] `python scripts/generate_schemas.py` sinh đủ **9 schemas**
- [x] `python -m pytest -v` đạt 100% passed (87 tests passed)
- [x] Thực hiện Manual Acceptance Test kiểm tra log kiểm toán và cấu trúc file JSON kết quả
