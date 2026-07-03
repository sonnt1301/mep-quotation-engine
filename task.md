# Danh Sách Công Việc MEP Quotation Pipeline Phase 13 – Local Pipeline Orchestrator / Human Review UI

## Component 1 – Cấu Hình & Dependencies

- [x] Cài đặt thư viện `streamlit>=1.36.0` trong [pyproject.toml (D:/mep_quotation_pipeline/pyproject.toml)](file:///D:/mep_quotation_pipeline/pyproject.toml)
- [x] Bổ sung thư mục `temp_uploads/` vào [.gitignore (D:/mep_quotation_pipeline/.gitignore)](file:///D:/mep_quotation_pipeline/.gitignore)

## Component 2 – UI Helper Module (tools/ui_helpers.py)

- [x] Triển khai hàm `run_cli_command(args, timeout)`:
  - [x] Gọi CLI thông qua subprocess với `shell=False`
  - [x] Thiết lập thư mục làm việc `cwd` tại dự án root
  - [x] Bắt giữ stdout/stderr đầy đủ
  - [x] Có cơ chế timeout cấu hình được và đánh dấu fail nếu xảy ra timeout
- [x] Triển khai hàm `safe_load_json(path)`:
  - [x] Tự động catch lỗi nếu file không tồn tại hoặc lỗi JSON để tránh làm crash giao diện
- [x] Triển khai hàm lọc tên tệp tin tải lên (sanitize filename) để loại bỏ các ký tự nguy hiểm
- [x] Triển khai bộ giải quyết đường dẫn artifact (Artifact Path Resolver):
  - [x] Ưu tiên đọc đường dẫn của từng artifact từ package.json / package.files / FilePathsModel
  - [x] Chỉ sử dụng đường dẫn quy ước (fallback) khi package metadata thiếu field đó
  - [x] Đảm bảo Artifact Viewer không hardcode cứng các đường dẫn như source/raw_text.json, parsed/*.json, text/*.md mà lấy động từ resolver

## Component 3 – local_review_app Module (tools/local_review_app.py)

- [x] Khởi tạo cấu trúc dữ liệu `PipelineStepStatus` (BaseModel) lưu trữ chi tiết trạng thái từng phase
- [x] Thiết kế giao diện chính:
  - [x] **Sidebar**:
    - [x] Nhập đường dẫn project root (mặc định D:\mep_quotation_pipeline)
    - [x] Bộ chọn PDF (đường dẫn local hoặc Streamlit file uploader an toàn)
    - [x] Thông số: supplier, date, seq
    - [x] 4 checkboxes Overwrite độc lập
    - [x] Các nút chạy pipeline, refresh và validate
  - [x] **Pipeline Status Table**:
    - [x] Bảng trạng thái trực quan hiển thị pass/fail, stdout/stderr của từng bước
  - [x] **Human Review UI**:
    - [x] Hiển thị bảng các draft items từ `normalized_draft.json`
    - [x] Chọn 1 dòng và mở form chi tiết cho phép Approve/Reject/Edit
    - [x] Nút Save Decision ghi nhận quyết định qua CLI `record-review` của Phase 10
  - [x] **Artifacts Viewer (Tabs)**:
    - [x] Read-only view hiển thị nội dung các tệp tin trung gian và tệp tin kết quả
    - [x] Tích hợp page selector cho PDF Pages và Raw Text
    - [x] Nút tải file Excel `quotation.xlsx` sau khi export thành công
- [x] Triển khai logic `Run Pipeline to Draft`:
  - [x] Tự động chạy tuần tự Phase 2 đến Phase 9, dừng sau Phase 9
- [x] Triển khai logic `Run Selected Step`:
  - [x] Chỉ chạy duy nhất bước được chọn
  - [x] Kiểm tra sự tồn tại của tệp tin đầu vào (input artifact) trước khi chạy, ném lỗi rõ ràng nếu thiếu

## Component 4 – Unit Tests

- [x] Tạo tệp kiểm thử [test_ui_app.py (D:/mep_quotation_pipeline/tests/test_ui_app.py)](file:///D:/mep_quotation_pipeline/tests/test_ui_app.py) bao phủ:
  - [x] `safe_load_json` (khi mất file và khi JSON lỗi)
  - [x] `run_cli_command` (capture stdout/stderr, timeout, exit code)
  - [x] sanitize filename uploader
  - [x] Trích xuất bảng review từ draft

## Component 5 – Hướng dẫn sử dụng

- [x] Cập nhật [README.md (D:/mep_quotation_pipeline/README.md)](file:///D:/mep_quotation_pipeline/README.md) mục `Local Pipeline Orchestrator / Human Review UI`
- [x] Cập nhật [walkthrough.md (D:/mep_quotation_pipeline/walkthrough.md)](file:///D:/mep_quotation_pipeline/walkthrough.md) sau khi hoàn tất

## Verification Bắt Buộc

- [x] `python scripts/generate_schemas.py` sinh đủ 14 schemas thành công
- [x] `python -m pytest -q` đạt 100% passed (tất cả các tests cũ và mới đều passed)
- [x] Thực hiện Manual Acceptance Test trên UI thật với tệp PDF thật
