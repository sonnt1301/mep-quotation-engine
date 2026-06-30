# Kế Hoạch Triển Khai MEP Quotation Pipeline Phase 3 - PDF Page Preparation (Bản Cập Nhật)

Tài liệu này trình bày kế hoạch triển khai chi tiết cho **Phase 3 – PDF Page Preparation / Page Image Layer** sau khi điều chỉnh các yêu cầu từ người dùng. Toàn bộ các thay đổi sẽ được phát triển trên nhánh `feature/pdf-page-preparation` tại thư mục dự án: **[D:/mep_quotation_pipeline](file:///D:/mep_quotation_pipeline)**.

---

## Mục Tiêu Phase 3
Xây dựng lớp quản lý ảnh trang PDF (Page Image Layer - v0.3.0). Lớp này thực hiện chuyển đổi (rasterize) các trang của tệp PDF gốc thành các tệp ảnh định dạng PNG riêng biệt, lưu trữ chúng một cách deterministic trong thư mục `source/pages/` dưới dạng `page_0001.png`, `page_0002.png`,... và sinh tệp chỉ mục trang `source/page_manifest.json` phục vụ đối chiếu minh chứng (evidence-based) cho các Phase sau.

---

## Các Thay Đổi Đề Xuất (Proposed Changes)

### 1. Phụ Thuộc (Dependencies)

#### [MODIFY] [pyproject.toml](file:///D:/mep_quotation_pipeline/pyproject.toml)
- Bổ sung thư viện `pymupdf>=1.24.0` vào danh sách `dependencies` chính.

---

### 2. Định Nghĩa Mô Hình Dữ Liệu (Models & Schemas)

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel`: Bổ sung trường `page_manifest: str = Field("source/page_manifest.json", description="...")` (có giá trị mặc định là `"source/page_manifest.json"` để giữ tương thích ngược 100%).
- Tạo `PageImageModel` đại diện cho thông tin của một ảnh trang:
  ```python
  class PageImageModel(BaseModel):
      page_number: int = Field(..., description="Số trang (1-indexed)")
      image_path: str = Field(..., description="Đường dẫn tương đối tới ảnh trang từ package root")
      width: int = Field(..., description="Chiều rộng ảnh tính bằng pixels")
      height: int = Field(..., description="Chiều cao ảnh tính bằng pixels")
      rotation: int = Field(..., description="Góc xoay của trang gốc (độ)")
      sha256: str = Field(..., description="Mã băm SHA256 của file ảnh")
      file_size: int = Field(..., description="Dung lượng file ảnh tính bằng bytes")
  ```
- Tạo `PageManifestModel` đại diện cho cấu trúc của `source/page_manifest.json`:
  ```python
  class PageManifestModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema manifest")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      source_pdf: str = Field(..., description="Đường dẫn tương đối tới file PDF gốc")
      page_count: int = Field(..., description="Tổng số trang")
      dpi: int = Field(..., description="Độ phân giải dùng để rasterize")
      image_format: str = Field("png", description="Định dạng ảnh (chỉ chấp nhận png)")
      pages: List[PageImageModel] = Field(..., description="Danh sách chi tiết các trang")
      generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("generated_at")
      def serialize_generated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất các model mới: `PageImageModel`, `PageManifestModel`.

#### [MODIFY] [generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Import `PageManifestModel` và bổ sung `"page_manifest.schema.json": PageManifestModel` vào cấu hình để sinh schema `schemas/page_manifest.schema.json` tự động.

---

### 3. Khởi Tạo Package Builder (Tương Thích Ngược)

#### [MODIFY] [builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)
- Cập nhật hàm `create_empty_package`: Bổ sung gán mặc định trường `page_manifest="source/page_manifest.json"` cho `FilePathsModel`.

---

### 4. Module Nghiệp Vụ PDF Pages (mep_quotation/pdf_pages/)

#### [NEW] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_pages/__init__.py)
- Xuất các hàm nghiệp vụ chính: `rasterize_pdf_pages` và `prepare_pdf_pages`.

#### [NEW] [rasterizer.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_pages/rasterizer.py)
- Triển khai hàm:
  ```python
  def rasterize_pdf_pages(
      pdf_path: Path,
      output_dir: Path,
      dpi: int = 150,
      image_format: str = "png",
  ) -> List[PageImageModel]
  ```
- Quy tắc hoạt động:
  - Kiểm tra `pdf_path` tồn tại và đọc được.
  - Sử dụng `PyMuPDF` (`import fitz`) để mở file.
  - Kiểm tra trạng thái mã hóa: Nếu tệp bị encrypted (`doc.is_encrypted` là True), **ném ngoại lệ ValueError ngay lập tức và dừng lại**.
  - Kiểm tra `dpi` phải là số nguyên dương (`dpi > 0`), nếu không, ném lỗi ValueError.
  - Kiểm tra định dạng ảnh: Chỉ hỗ trợ định dạng `"png"` (case-insensitive). Nếu truyền định dạng khác, ném lỗi ValueError.
  - **Không kiểm tra trùng lặp file ảnh hay manifest trong hàm này** (hàm này chỉ chịu trách nhiệm render ảnh trang và ghi vào `output_dir`).
  - Duyệt qua từng trang của PDF:
    - **Không tự xoay trang thủ công** (không tự thực hiện xoay theo `page.rotation` để tránh double-rotation). Render theo cách mặc định hiển thị của PyMuPDF.
    - Ghi nhận `rotation = page.rotation` vào `PageImageModel`.
    - Rasterize trang thành Pixmap với độ phân giải DPI tương ứng (sử dụng ma trận tỉ lệ `zoom = dpi / 72`).
    - Lưu Pixmap thành tệp ảnh `page_0001.png`, `page_0002.png` (luôn định dạng 4 chữ số, đệm số 0).
    - Tính toán kích thước ảnh thực tế (width, height), dung lượng file và SHA256 checksum của ảnh trang.
    - Tạo đối tượng `PageImageModel`.
  - Trả về danh sách `PageImageModel`.

#### [NEW] [manifest.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_pages/manifest.py)
- Triển khai hàm tạo manifest `source/page_manifest.json` theo cấu trúc của `PageManifestModel`, ghi tệp deterministic và chạy validate lại trước khi lưu.

#### [NEW] [page_service.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_pages/page_service.py)
- Triển khai hàm dịch vụ chuẩn hóa:
  ```python
  def prepare_pdf_pages(
      package_path: Path,
      dpi: int = 150,
      image_format: str = "png",
      overwrite: bool = False,
  ) -> Path
  ```
- Quy trình hoạt động:
  1. Đọc và nạp `package.json`.
  2. Nối đường dẫn tệp PDF gốc `source/original.pdf` và tệp metadata `source/metadata.json`.
  3. Kiểm tra xem tệp PDF có bị encrypted không dựa trên `metadata.json` (`encrypted` == True) hoặc trực tiếp từ file. Nếu encrypted, ném ngoại lệ ValueError và dừng lại ngay lập tức (không decrypt, không tiếp tục).
  4. **Kiểm Tra Trùng Lặp Atomic**:
     - Nếu `overwrite=False`:
       - Kiểm tra nếu file manifest `source/page_manifest.json` đã tồn tại trên đĩa.
       - Kiểm tra nếu bất kỳ file ảnh trang mong đợi nào (ví dụ `source/pages/page_0001.png` ứng với tổng số trang của PDF gốc) đã tồn tại trên đĩa.
       - Nếu bất kỳ tệp nào đã tồn tại, **ném ngoại lệ ValueError rõ ràng ngay lập tức trước khi gọi tiến trình render** (tránh sinh ảnh dở dang).
     - Nếu `overwrite=True`: Chấp nhận xóa hoặc ghi đè toàn bộ ảnh trang và tệp manifest cũ.
  5. Ghi event log `pdf_page_preparation_started`.
  6. Gọi hàm `rasterize_pdf_pages` xuất các trang ảnh vào thư mục `source/pages/`.
  7. Ghi event log `pdf_page_rasterized` kèm thông tin chi tiết (`page_count`, `dpi`, `image_format`, `output_dir`) **sau khi hoàn thành toàn bộ các trang** (tránh spam log cho mỗi trang).
  8. Sinh tệp chỉ mục `source/page_manifest.json` và lưu deterministic. Ghi event log `pdf_page_manifest_written`.
  9. **Kiểm tra tính hợp lệ của manifest sau khi sinh**:
     - Validate bằng `PageManifestModel`.
     - Kiểm tra `page_manifest.page_count == len(page_manifest.pages)`.
     - Tất cả các đường dẫn trong manifest phải là đường dẫn tương đối tính từ package root (ví dụ: `source/original.pdf` và `source/pages/page_0001.png`), không chấp nhận đường dẫn tuyệt đối.
     - Mỗi `image_path` khai báo trong manifest phải thực sự tồn tại trên đĩa.
     - Dung lượng file `file_size` và mã băm `sha256` của từng trang ảnh trong manifest phải khớp chính xác với file ảnh thực tế trên đĩa.
  10. Cập nhật `package.json` với trường `files.page_manifest = "source/page_manifest.json"` và cập nhật `updated_at`.
  11. Chạy kiểm tra toàn vẹn package `validate_package_integrity`.
  12. Ghi event log `pdf_page_preparation_completed` và trả về `package_path`.
  13. Nếu có lỗi xảy ra sau khi bắt đầu, ghi nhận sự kiện `pdf_page_preparation_failed` vào log trước khi ném ngoại lệ lên.

---

### 5. Kiểm Tra Toàn Vẹn Package (Integrity)

#### [MODIFY] [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- **Tương Thích Ngược**: Bộ xác thực kiểm tra chéo package **không được bắt buộc** tệp `page_manifest.json` phải tồn tại. Điều này đảm bảo các package Phase 1 và Phase 2 (chưa chạy prepare-pages) vẫn validate pass bình thường.
- Chỉ thực hiện kiểm tra chéo manifest nếu tệp `source/page_manifest.json` **thực sự tồn tại trên đĩa**:
  - Đối chiếu `page_manifest.quotation_id == package.quotation_id`.
  - Đối chiếu `page_manifest.page_count` phải khớp với số lượng ảnh trang thực tế trong thư mục `source/pages/`.
  - Đảm bảo các tệp ảnh trang khai báo trong manifest thực sự tồn tại trên đĩa.
- Sau khi tiến trình `prepare-pages` chạy xong thành công, tệp `page_manifest.json` bắt buộc phải tồn tại và hợp lệ.

---

### 6. CLI Giao Diện Dòng Lệnh

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Thêm subcommand `prepare-pages <package_path>`:
  `python -m mep_quotation.cli.main prepare-pages data/suppliers/AUT/2026/2026-06-20_001 [--dpi 150] [--format png] [--overwrite]`
- Lệnh chỉ chấp nhận format `png`. Nếu truyền định dạng khác hoặc DPI <= 0, báo lỗi rõ ràng và thoát.
- Sau khi chuẩn bị thành công, in ra stdout: `quotation_id`, `package path`, `page count`, `output directory`, `manifest path`, `dpi`, `image format`.

---

### 7. Bộ Kiểm Thử (Tests)

#### [NEW] [test_pdf_pages.py](file:///D:/mep_quotation_pipeline/tests/test_pdf_pages.py)
- Viết test suite bao phủ tất cả các kịch bản:
  - Rasterize PDF hợp lệ (đọc được ảnh, kích thước > 0, SHA256 khớp).
  - Tên file ảnh đệm đúng 4 chữ số `page_0001.png`.
  - Validate schema của `page_manifest.json` và kiểm tra tính tương thích ngược của `validate_package_integrity`.
  - Kiểm tra `overwrite=False` ném lỗi trước khi render nếu tệp đã tồn tại, `overwrite=True` ghi đè thành công.
  - Từ chối tệp PDF bị mã hóa (encrypted PDF) ngay lập tức.
  - Gọi lệnh CLI `prepare-pages` và kiểm tra log kiểm toán đầy đủ các sự kiện.

---

## Quy Trình Xác Minh Bắt Buộc (Verify)
1. Cài đặt các phụ thuộc chính và dev dependencies:
   ```bash
   python -m pip install -e ".[dev]"
   ```
2. Sinh lại các file JSON Schema trên đĩa:
   ```bash
   python scripts/generate_schemas.py
   ```
3. Chạy toàn bộ các unit tests (đảm bảo tương thích ngược 100%):
   ```bash
   python -m pytest -v
   ```
