# Kế Hoạch Triển Khai MEP Quotation Pipeline Phase 2 - PDF Infrastructure (Bản Cập Nhật 2)

Tài liệu này trình bày kế hoạch triển khai chi tiết cho **Phase 2 – PDF Infrastructure / PDF Intake Layer** sau khi điều chỉnh các yêu cầu nghiệp vụ từ người dùng. Toàn bộ các thay đổi được áp dụng tại thư mục dự án: **[D:/mep_quotation_pipeline](file:///D:/mep_quotation_pipeline)** trên nhánh `feature/pdf-infrastructure`.

---

## 1. Các Ràng Buộc Kỹ Thuật Điều Chỉnh

> [!IMPORTANT]
> 1. **Luồng Ghi Nhật Ký Kiểm Toán (Audit Flow)**: Do tệp log nằm trong thư mục package, hệ thống không thể ghi log trước khi package được tạo. Quy trình đúng:
>    - Validate PDF cơ bản trước (nếu fail thì raise exception ngay và kết thúc, không ghi log).
>    - Tạo package bằng `create_empty_package`.
>    - Ghi sự kiện kiểm toán `pdf_import_started` vào log của package.
>    - Thực hiện sao chép PDF, sinh metadata và cập nhật package.json.
>    - Nếu xảy ra bất kỳ lỗi nào sau khi package đã được tạo, ghi nhận sự kiện `pdf_import_failed` vào log trước khi raise exception.
> 2. **Kiểm Tra Trùng Lặp**:
>    - Nếu người dùng truyền `seq` mà package tương ứng đã tồn tại trên đĩa, ném ngoại lệ rõ ràng ngay trước khi khởi tạo package để tránh overwrite dữ liệu.
> 3. **Tương Thích Ngược (Compatibility)**:
>    - Trường `pdf_metadata` trong `FilePathsModel` bắt buộc phải có giá trị mặc định là `"source/metadata.json"` để đảm bảo các tệp cấu hình cũ và test suite của Phase 1 tiếp tục pass.
> 4. **Trích Xuất Thông Tin Siêu Dữ Liệu PDF**:
>    - Định nghĩa Pydantic models cho mọi dữ liệu cấu trúc: `WarningModel`, `PdfMetadataModel` và `PdfValidationResult` (để chứa kết quả validate).
>    - Cập nhật script `scripts/generate_schemas.py` để sinh thêm tệp schema: `schemas/pdf_metadata.schema.json`.
> 5. **Hiển Thị CLI và Source of Truth**:
>    - **Importer/Validator là Source of Truth duy nhất** cho việc kiểm tra dung lượng lớn và sinh ra WarningModel(code="large_pdf", ...).
>    - CLI không tự động kiểm tra kích thước file để sinh cảnh báo trước khi import.
>    - CLI chỉ gọi `import_pdf(...)`. Sau khi import hoàn tất, CLI nạp tệp `source/metadata.json` của package vừa được tạo và in ra màn hình thông tin siêu dữ liệu cùng danh sách các `warnings` đọc được từ tệp metadata đó (bao gồm cảnh báo `large_pdf` nếu có).
> 6. **Quy Tắc Xử Lý PDF Bị Mã Hóa (Encrypted PDF Rule)**:
>    - Encrypted PDF **không được xem là corrupted** nếu `pypdf` vẫn đọc được cấu trúc file vật lý của tệp PDF.
>    - Khi phát hiện tệp bị encrypted:
>      - Tiến trình import vẫn được tiếp tục bình thường (không bị fail).
>      - Siêu dữ liệu trong `metadata.json` ghi nhận trường `encrypted: true`.
>      - Trường số trang `page_count` sẽ được gán giá trị `null` (None) nếu không thể giải mã để đếm số trang.
>      - Hệ thống không cố giải mã tệp (decryption) hay parse nội dung của PDF.
>      - Không thu thập ngày tạo `created_at` và ngày sửa đổi `modified_at` từ document metadata nếu việc này yêu cầu mật khẩu giải mã hoặc không chắc chắn.

---

## 2. Các Thay Đổi Đề Xuất (Proposed Changes)

### A. Cấu Hình và Models dữ liệu

#### [MODIFY] [pyproject.toml](file:///D:/mep_quotation_pipeline/pyproject.toml)
- Thêm phụ thuộc `pypdf>=4.0.0` vào danh sách `dependencies`.

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel`: Bổ sung trường `pdf_metadata: str = Field("source/metadata.json", description="...")` (có giá trị mặc định).
- Tạo `WarningModel`:
  ```python
  class WarningModel(BaseModel):
      code: str = Field(..., description="Mã cảnh báo kỹ thuật")
      message: str = Field(..., description="Nội dung chi tiết cảnh báo")
  ```
- Tạo `PdfMetadataModel`:
  ```python
  class PdfMetadataModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema metadata")
      file_name: str = Field(..., description="Tên file PDF gốc")
      file_size: int = Field(..., description="Dung lượng file tính bằng bytes")
      sha256: str = Field(..., description="Mã băm SHA256 của file")
      page_count: Optional[int] = Field(None, description="Số trang của PDF")
      pdf_version: Optional[str] = Field(None, description="Phiên bản PDF")
      encrypted: bool = Field(False, description="File có bị mã hóa/đặt mật khẩu không")
      created_at: Optional[str] = Field(None, description="Thời điểm tạo PDF gốc")
      modified_at: Optional[str] = Field(None, description="Thời điểm chỉnh sửa PDF gốc")
      imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      warnings: List[WarningModel] = Field(default_factory=list, description="Danh sách các cảnh báo")
  ```
- Tạo `PdfValidationResult` phục vụ kết quả validate PDF:
  ```python
  class PdfValidationResult(BaseModel):
      is_valid: bool = Field(..., description="Kết quả validate tổng thể")
      warnings: List[WarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")
      error_message: Optional[str] = Field(None, description="Thông báo lỗi chi tiết nếu không valid")
  ```

#### [MODIFY] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất các model mới: `WarningModel`, `PdfMetadataModel`, `PdfValidationResult`.

#### [MODIFY] [generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Thêm `pdf_metadata.schema.json` sinh ra từ `PdfMetadataModel` vào danh sách sinh tự động.

---

### B. Module pdf (mep_quotation/pdf/)

#### [NEW] [checksum.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf/checksum.py)
- Hàm `calculate_sha256(file_path: Path) -> str`.

#### [NEW] [validator.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf/validator.py)
- Hàm `validate_pdf(pdf_path: Path, max_size_mb: int = 50) -> PdfValidationResult`:
  - Thực hiện các kiểm tra: Tồn tại, là file, đuôi `.pdf`, dung lượng > 0, header `%PDF-`, đọc được bằng `pypdf.PdfReader`, check trạng thái mã hóa.
  - Kiểm tra kích thước file: Nếu lớn hơn `max_size_mb`, không báo lỗi mà sinh một `WarningModel(code="large_pdf", message="...")`.
  - Trả về `PdfValidationResult`.

#### [NEW] [metadata.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf/metadata.py)
- Trích xuất thông tin kỹ thuật từ `pypdf.PdfReader`: `page_count`, `pdf_version` (từ header), `encrypted`.
- Trích xuất thông tin ngày tạo/sửa đổi thô từ metadata `/CreationDate` và `/ModDate`, chuyển đổi sang chuỗi ISO 8601 thô nếu hợp lệ, ngược lại để `None` (không đoán mò).

#### [NEW] [importer.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf/importer.py)
- Triển khai hàm `import_pdf`:
  1. Gọi `validate_pdf`. Nếu `is_valid` của kết quả validate là `False`, raise Exception ngay lập tức (không ghi log vì package chưa được tạo).
  2. Kiểm tra xem package tương ứng (dựa vào supplier, date, seq) đã tồn tại trên đĩa chưa. Nếu có truyền `seq` mà package đã tồn tại, ném ngoại lệ rõ ràng ngay lập tức (không overwrite).
  3. Gọi `create_empty_package` để khởi tạo package rỗng.
  4. Ghi sự kiện nhật ký kiểm toán `pdf_import_started` vào log của package.
  5. Bắt đầu xử lý nghiệp vụ trong khối `try...except`:
     - Ghi nhận `pdf_validated`.
     - Nếu kết quả validate trước đó có chứa warning `large_pdf`, ghi sự kiện log `pdf_large_file_warning`.
     - Sao chép file PDF gốc vào `source/original.pdf` trong package. Ghi sự kiện `pdf_copied`.
     - Trích xuất thông tin siêu dữ liệu PDF, tạo đối tượng `PdfMetadataModel` (nạp kèm danh sách warnings từ kết quả validate), ghi tệp siêu dữ liệu `source/metadata.json` một cách deterministic. Ghi sự kiện `pdf_metadata_written`.
     - Cập nhật `package.json` với trường `files.pdf_metadata = "source/metadata.json"` và cập nhật `updated_at`.
     - Chạy kiểm tra toàn vẹn package `validate_package_integrity`.
     - Ghi sự kiện `pdf_import_completed`.
  6. Nếu có lỗi xảy ra trong khối `try...except` sau khi package đã được tạo:
     - Ghi sự kiện `pdf_import_failed` vào file log của package.
     - Raise Exception đó lên để báo lỗi.

---

### C. CLI Giao Diện Dòng Lệnh

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Thêm subcommand `import-pdf` và flag tương ứng.
- CLI chỉ gọi `import_pdf(...)`. Sau khi import hoàn tất, CLI nạp tệp `source/metadata.json` từ thư mục package được trả về.
- In ra màn hình đầy đủ các thông tin siêu dữ liệu: `quotation_id`, `package path`, `source PDF path`, `metadata path`, `page count`, `file size`, `sha256`, `encrypted`.
- Nếu trong file metadata nạp được có chứa cảnh báo (warnings), in các cảnh báo đó ra console theo định dạng:
  ```
  WARNING

  Large PDF detected.

  File size: xxx MB
  Configured threshold: 50 MB

  Import will continue.
  ```

---

### D. Bộ Kiểm Thử (Tests)

#### [NEW] [test_pdf_infrastructure.py](file:///D:/mep_quotation_pipeline/tests/test_pdf_infrastructure.py)
- Viết test suite bao phủ tất cả các kịch bản kiểm định, cảnh báo dung lượng, lỗi không khớp, kiểm tra log kiểm toán và ngăn cản overwrite.

---

## Quy Trình Xác Minh Bắt Buộc (Verify)
1. Cài đặt dependencies:
   ```bash
   python -m pip install -e ".[dev]"
   ```
2. Sinh lại JSON Schemas:
   ```bash
   python scripts/generate_schemas.py
   ```
3. Chạy toàn bộ unit tests:
   ```bash
   python -m pytest -v
   ```
