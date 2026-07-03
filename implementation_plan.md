# Kế Hoạch Triển Khai Phase 13 – Local Pipeline Orchestrator / Human Review UI

Kế hoạch này xây dựng một giao diện UI cục bộ (chạy bằng Streamlit) để điều phối, giám sát và thực hiện kiểm thử trực quan (Manual Acceptance Test) cho toàn bộ luồng MEP Quotation Pipeline từ Phase 1 đến Phase 12.

---

## User Review Required

> [!IMPORTANT]
> - **Cơ chế Run Pipeline to Draft**: Chỉ tự động chạy từ Phase 2 đến Phase 9 (`import-pdf` đến `build-normalized-draft`). Sau Phase 9, pipeline bắt buộc dừng lại để thực hiện rà soát thủ công (Human Review). Tuyệt đối không tự động approve, tự động xuất normalized JSON hoặc tự động xuất Excel.
> - **Cơ chế Run Selected Step**:
>   - Dropdown trong UI cho phép lựa chọn từng bước đơn lẻ.
>   - Kiểm tra sự tồn tại của tệp tin đầu vào (input artifact) tương ứng với bước được chọn trước khi chạy. Nếu thiếu, báo lỗi rõ ràng và dừng ngay lập tức; không tự chạy các bước trước đó trừ khi người dùng chọn `Run Pipeline to Draft`.
> - **Tách biệt Overwrite Checkboxes**: Thiết lập 4 checkbox riêng biệt trong sidebar để ghi đè có chọn lọc:
>   1. *Overwrite Intermediate*: Ghi đè các artifact trung gian từ Phase 3 đến Phase 9.
>   2. *Overwrite Decisions*: Ghi đè quyết định rà soát Phase 10 (`review_decisions.json`).
>   3. *Overwrite Normalized*: Ghi đè tệp tin báo giá chuẩn hóa chính thức Phase 11 (`normalized.json`).
>   4. *Overwrite Excel*: Ghi đè file Excel báo giá xuất bản Phase 12 (`quotation.xlsx` và `export_manifest.json`).
> - **Không Hardcode Đường Dẫn Artifacts**: Trình xem dữ liệu (Artifact Viewer) luôn ưu tiên đọc đường dẫn thực tế từ tệp `package.json` (`package.files` thông qua `FilePathsModel`). Chỉ sử dụng đường dẫn quy ước (fallback) khi thiếu cấu hình trong metadata.

---

## Orchestration State Structure

Trạng thái của pipeline sẽ được quản lý tập trung thông qua cấu trúc dữ liệu `PipelineStepStatus` (sử dụng `dataclass` hoặc Pydantic) để bảo đảm sự tường minh và không phân tán logic trạng thái trong giao diện:

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class PipelineStepStatus(BaseModel):
    step_id: str                          # CLI command tương ứng (ví dụ: "prepare-pages")
    step_name: str                        # Tên hiển thị trực quan (ví dụ: "Prepare Pages")
    phase_number: str                     # Số Phase hoặc loại kiểm định (ví dụ: "Phase 3" hoặc "Check")
    status: str = "pending"               # pending | running | pass | fail | skipped
    output_paths: List[str] = Field(default_factory=list) # Danh sách đường dẫn tệp đầu ra
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
```

---

## Subprocess Execution Rule

Các bước trong pipeline sẽ được kích hoạt thông qua CLI chính thức của hệ thống bằng lệnh gọi `subprocess` với các ràng buộc:
- Thiết lập `shell=False`.
- Thiết lập `cwd` là thư mục gốc của dự án (`project_root`).
- Bắt giữ (`capture_output=True`) cả `stdout` và `stderr`.
- Cấu hình thời gian chờ (`timeout`) có thể tùy chỉnh trong UI (mặc định từ 10 - 30 phút cho các PDF có dung lượng lớn). Nếu xảy ra timeout, đánh dấu bước đó là `fail` và in ra lỗi cụ thể.

Các subcommand CLI được gọi khớp chính xác 100% với tên thực tế hiện có trong repo:
- `import-pdf`, `prepare-pages`, `extract-text`, `assemble-text`, `parse-line-candidates`, `assemble-rows`, `build-item-candidates`, `build-normalized-draft`, `create-review-file`, `record-review`, `list-review`, `export-normalized`, `export-excel`, `validate-package`.

---

## Data Safety & Upload Safety

1. **Upload PDF**:
   - Chỉ cho phép tệp tin có đuôi `.pdf`.
   - Lọc sạch tên tệp tin (sanitize filename) để ngăn ngừa các đường dẫn nguy hiểm.
   - Lưu trữ tạm thời vào thư mục `temp_uploads/` nằm trong thư mục gốc dự án.
   - Cấu hình bỏ qua `temp_uploads/` trong `.gitignore`.
2. **Data Safety**:
   - Trình xem dữ liệu (Artifact Viewer) hoàn toàn là read-only. Không cho phép chỉnh sửa trực tiếp JSON artifacts trên giao diện.
   - Mọi thay đổi lên `review_decisions.json` bắt buộc đi qua CLI/service `record-review`.
   - Xuất bản `normalized.json` và Excel bắt buộc đi qua CLI/service của Phase 11 và Phase 12 tương ứng.
   - Không tự ý tạo hoặc ghi đè JSON artifacts bằng logic UI riêng.

---

## Proposed Changes

### [Component 1 – Dependencies & Git Config]

#### [MODIFY] [pyproject.toml](file:///D:/mep_quotation_pipeline/pyproject.toml)
- Thêm dependency `"streamlit>=1.36.0"`.

#### [MODIFY] [.gitignore](file:///D:/mep_quotation_pipeline/.gitignore)
- Bổ sung thư mục `temp_uploads/` vào danh sách bỏ qua của Git (không bỏ qua *.xlsx).

---

### [Component 2 – local_review_app Module (tools/)]

#### [NEW] [local_review_app.py](file:///D:/mep_quotation_pipeline/tools/local_review_app.py)
- Khởi dựng ứng dụng Streamlit cục bộ chính.
- **Sidebar**:
  - `Project Root` (mặc định: `D:\mep_quotation_pipeline`).
  - Nút tải lên PDF hoặc nhập đường dẫn PDF cục bộ.
  - Các ô nhập dữ liệu: `Supplier Code`, `Quotation Date`, `Sequence`.
  - Checkboxes Overwrite độc lập.
  - Bộ nút điều phối: `Run Pipeline to Draft`, `Run Selected Step`, `Export Normalized`, `Export Excel`, `Refresh Package`, `Validate Package`.
- **Main Area**:
  - Bảng trạng thái pipeline sử dụng cấu trúc `PipelineStepStatus`.
  - Bảng rà soát thủ công (Human Review Table) hiển thị toàn bộ draft items kèm theo Warnings và Confidence.
  - Form chi tiết cho draft item được chọn để thực hiện `Approve` / `Reject` / `Edit` và lưu quyết định thông qua CLI `record-review`.
  - Tabs hiển thị Artifacts (read-only) và Nút tải file Excel `quotation.xlsx` sau khi export thành công.

#### [NEW] [ui_helpers.py](file:///D:/mep_quotation_pipeline/tools/ui_helpers.py)
- Hàm `run_cli_command(args, timeout=600)` điều phối chạy CLI an toàn.
- Hàm `safe_load_json(path)` chống crash khi tệp JSON chưa tồn tại hoặc bị lỗi cấu trúc.
- Helper sanitize tên file upload.

---

### [Component 3 – Documentation]

#### [MODIFY] [README.md](file:///D:/mep_quotation_pipeline/README.md)
- Bổ sung hướng dẫn cài đặt và chạy ứng dụng Streamlit Local UI.

---

### [Component 4 – Tests]

#### [NEW] [test_ui_app.py](file:///D:/mep_quotation_pipeline/tests/test_ui_app.py)
- Viết unit tests kiểm thử các helpers: `safe_load_json`, bộ lọc an toàn filename, và subprocess command runner.

---

## Verification Plan

### Automated Tests
- Chạy bộ unit tests:
  ```bash
  python -m pytest -q
  ```

### Manual Verification
1. Khởi động ứng dụng Streamlit:
   ```bash
   python -m streamlit run tools/local_review_app.py
   ```
2. Chuẩn bị 1 tệp PDF thật bên ngoài (ví dụ: `C:/test_quotation.pdf`).
3. Trên giao diện UI:
   - Tải tệp PDF lên hoặc nhập đường dẫn tuyệt đối của nó.
   - Nhập: `Supplier Code = AUT`, `Quotation Date = 2026-06-20`, `Sequence = 1`.
   - Bấm `Run Pipeline to Draft`.
4. Xác nhận bảng trạng thái hiển thị trạng thái `pass` từ Phase 2 đến Phase 9.
5. Kiểm tra các tab: `Raw Text`, `Line Candidates`, `Row Candidates`, `Item Candidates`, `Normalized Draft` hiển thị dữ liệu read-only chính xác.
6. Chọn 1 item trong bảng Draft Items để rà soát:
   - Đặt decision = `edited`.
   - Nhập unit_price override mới.
   - Bấm `Save Decision`.
7. Xác nhận tệp `review_decisions.json` được tạo chính xác trên đĩa.
8. Bấm `Export Normalized` $\rightarrow$ sinh tệp normalized.json.
9. Bấm `Export Excel` $\rightarrow$ sinh tệp Excel và manifest.
10. Tải tệp Excel về máy và xác nhận mở bình thường.
11. Bấm `Validate Package` để kiểm định toàn bộ package thành công.
