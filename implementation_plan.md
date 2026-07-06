# Kế Hoạch Triển Khai Phase 14 – Multi-Source Intake / Source Profiling Gate

Phase 14 bổ sung một cổng phân tích và đánh giá tài liệu nguồn cục bộ (`Source Profiling Gate`). Phase này không trích xuất sản phẩm báo giá chính thức, không OCR, không dùng AI, mà chỉ nhận diện đặc trưng kỹ thuật và nghiệp vụ của file nguồn để tạo ra tệp hồ sơ `source/source_profile.json`.

---

## Các Mô Hình Dữ Liệu Pydantic Mới (spec/models.py)

Chúng ta sẽ định nghĩa các enums và models mới trực tiếp trong [spec/models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) để đồng bộ hóa với hệ thống JSON Schema generator.

### 1. Enums
* **`SourceRole`**:
  * `supplier_quotation_candidate` (Báo giá nhà cung cấp)
  * `supplier_price_list_candidate` (Bảng giá chung)
  * `supplier_catalog_candidate` (Catalog giới thiệu sản phẩm)
  * `boq_candidate` (Bảng khối lượng dự toán)
  * `purchase_order_candidate` (Đơn đặt hàng PO)
  * `technical_datasheet_candidate` (Tài liệu kỹ thuật sản phẩm)
  * `mixed_document_candidate` (Tài liệu hỗn hợp nhiều vai trò)
  * `unknown_document` (Không rõ vai trò)
* **`RecommendedNextAction`**:
  * `run_pdf_native_pipeline` (Chạy luồng xử lý văn bản PDF có sẵn)
  * `run_pdf_ocr_pipeline_later` (Yêu cầu OCR PDF quét ảnh sau)
  * `run_excel_intake_pipeline_later` (Yêu cầu luồng Excel riêng sau)
  * `run_image_ocr_pipeline_later` (Yêu cầu OCR ảnh sau)
  * `manual_profile_required` (Yêu cầu rà soát thủ công)
  * `reject_or_hold` (Từ chối xử lý)
  * `unsupported_file_type` (Định dạng chưa hỗ trợ)

### 2. Các Lớp Mô Hình Mới
* **`SourceDateCandidateModel`**:
  * `date`: `str` (YYYY-MM-DD)
  * `date_type`: `str` (`quotation_date_candidate`, `effective_date_candidate`, `issue_date_candidate`, `expiry_date_candidate`, `received_date_candidate`)
  * `source`: `str` (ví dụ `"text_probe"`, `"file_metadata"`)
  * `confidence`: `float`
  * `evidence`: `Optional[str]`
* **`TechnicalReadabilityModel`**:
  * `is_supported_file_type`: `bool`
  * `has_native_text`: `bool`
  * `native_text_probe_char_count`: `int`
  * `text_density_level`: `str` (`none` | `low` | `medium` | `high`)
  * `is_scanned_candidate`: `bool`
  * `requires_ocr`: `bool`
  * `page_count`: `Optional[int]`
  * `sheet_count`: `Optional[int]`
  * `image_width`: `Optional[int]`
  * `image_height`: `Optional[int]`
* **`SourceProfileModel`**:
  * `schema_version`: `str` (mặc định `"1.0"`)
  * `quotation_id`: `str`
  * `source_file`: `str` (Đường dẫn tương đối từ package root)
  * `source_sha256`: `str`
  * `file_name`: `str`
  * `file_extension`: `str`
  * `detected_file_type`: `str`
  * `detected_mime_type`: `str`
  * `file_size_bytes`: `int`
  * `source_role`: `SourceRole`
  * `source_role_confidence`: `float`
  * `technical_readability`: `TechnicalReadabilityModel`
  * `date_candidates`: `List[SourceDateCandidateModel]`
  * `recommended_next_action`: `RecommendedNextAction`
  * `requires_human_profile_review`: `bool`
  * `warnings`: `List[WarningModel]` (Tái sử dụng lớp `WarningModel` có sẵn)
  * `created_at`: `datetime`
  * `updated_at`: `datetime`

### 3. Cập nhật `FilePathsModel`
Bổ sung thêm trường tùy chọn:
* `source_profile: Optional[str] = Field("source/source_profile.json", description="Đường dẫn file source profile JSON, tương đối từ package root")`

---

## Chi Tiết Luồng Phân Tích (Profiling Logic)

Tạo module mới [mep_quotation/intake/profiler.py](file:///D:/mep_quotation_pipeline/mep_quotation/intake/profiler.py) triển khai các logic heuristic an toàn:

### 1. Phân giải tệp nguồn (Source Resolver Logic)
Hệ thống xác định tệp nguồn duy nhất để tiến hành phân tích theo độ ưu tiên:
* **Độ ưu tiên 1**: Nếu `package.files.source_pdf` (hoặc cấu hình file trong metadata) tồn tại và tệp tin thực sự có trên đĩa $\rightarrow$ Dùng tệp này.
* **Độ ưu tiên 2**: Nếu không có `source_pdf`, thực hiện quét thư mục `source/` để tìm các tệp có mẫu tên `original.*` (ví dụ `original.pdf`, `original.xlsx`, `original.jpg`...).
  * Nếu tìm thấy **đúng 1 tệp** duy nhất khớp mẫu $\rightarrow$ Dùng tệp đó.
  * Nếu không tìm thấy tệp nào, hoặc có **nhiều hơn 1 tệp** mà metadata của package không chỉ định chính xác $\rightarrow$ Báo lỗi thất bại rõ ràng (`ValueError`) và thoát ngay lập tức, không tự động phỏng đoán tệp nguồn.

### 2. Phân loại kỹ thuật theo định dạng file nguồn
Phase 14 v1 phân cấp xử lý như sau:
* **Deep Profiling (Hỗ trợ phân tích sâu)**:
  * **PDF**: Đọc số trang, kiểm tra mã hóa qua `pypdf`, trích xuất mẫu văn bản (probe text tối đa 3000 ký tự qua `pymupdf` / `fitz`) của tối đa 3 trang đầu để nhận diện vai trò và ngày tháng. Đánh giá tính toán Scanned/requires_ocr dựa trên mật độ chữ.
  * **XLSX**: Đọc số sheet, danh sách sheet qua `openpyxl`. Cảnh báo `multi_sheet_excel` nếu có nhiều sheets. Quét nhẹ header.
  * **JPG/JPEG/PNG**: Đọc kích cỡ ảnh `width` và `height` qua thư viện `Pillow`/`PIL`. Đặt `requires_ocr = True` và khuyến nghị `run_image_ocr_pipeline_later`.
* **Limited Support (Chỉ nhận diện phần mở rộng)**:
  * Các định dạng: **XLS, XLSM, CSV, WEBP**.
  * Chỉ phân tích phần mở rộng và ghi nhận cảnh báo `limited_support` hoặc `unsupported_file_type`. 
  * Tuyệt đối **không** dùng `openpyxl` để đọc tệp Excel cũ `.xls` (tránh lỗi crash). Ghi cảnh báo và khuyến nghị `unsupported_file_type`.

### 3. Nhận Diện Vai Trò Tài Luệu (SourceRole Heuristic)
Rule-based heuristic dựa trên từ khóa xuất hiện trong `text_probe` (hoặc tên file):
* **supplier_quotation_candidate**: Chứa từ khóa: `báo giá`, `kính gửi`, `khách hàng`, `đơn đặt hàng`, `quotation`, `quote`, `attention`, `project`.
* **supplier_price_list_candidate**: Chứa từ khóa: `bảng giá`, `bảng giá bán lẻ`, `list giá`, `price list`, `pricelist`, `mã sản phẩm`, `đơn giá`.
* **supplier_catalog_candidate**: Chứa từ khóa: `catalogue`, `catalog`, `hướng dẫn sử dụng`, `mô tả kỹ thuật`, `kích thước lắp đặt`, `chức năng`.
* **boq_candidate**: Chứa từ khóa: `bảng khối lượng`, `khối lượng mời thầu`, `tiên lượng`, `boq`, `bill of quantities`, `bảng dự toán`.
* **purchase_order_candidate**: Chứa từ khóa: `purchase order`, `đơn đặt hàng`, `đơn hàng`, `po`.
* **technical_datasheet_candidate**: Chứa từ khóa: `datasheet`, `đặc tính kỹ thuật`, `technical specification`.

### 4. Dò Tìm Ứng Viên Ngày Tháng (Date Candidates)
Sử dụng biểu thức chính quy (Regex) quét ngày dạng `DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MM-YYYY` và các cụm chỉ dẫn (`ngày báo giá`, `ngày hiệu lực`...) để phân loại.

---

## CLI Command, Ghi Đè & Atomic Write

Lệnh CLI mới:
```bash
python -m mep_quotation.cli.main profile-source <package_path> --overwrite
```

### Các Guardrails quan trọng:
* **Chặn ghi đè (No Overwrite)**: Nếu tệp `source/source_profile.json` đã tồn tại mà CLI chạy không truyền cờ `--overwrite` $\rightarrow$ Báo lỗi thất bại rõ ràng và dừng ngay lập tức.
* **Ghi an toàn (Atomic Write)**: Để tránh làm hỏng cấu hình JSON nếu tiến trình bị gián đoạn, dữ liệu mới sẽ được ghi vào một tệp tạm thời (ví dụ `source_profile.json.tmp`) rồi sử dụng lệnh đổi tên nguyên tử (`replace`/`rename`) để ghi đè tệp chính thức.

---

## Tích Hợp Kiểm Định Gói & Tương Thích Ngược (mep_quotation/package/integrity.py)

Cập nhật hàm `validate_package_integrity` trong tệp [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) để tuân thủ chặt chẽ nguyên tắc tương thích ngược:
* **Nguyên tắc tương thích ngược (Backward Compatibility)**:
  * Nếu trong `package.json` (được đọc thành đối tượng `pkg`) **không** khai báo đường dẫn `source_profile` trong `pkg.files`, đồng thời tệp `source/source_profile.json` thực tế **không tồn tại** $\rightarrow$ Bỏ qua bước kiểm định này (kiểm định `pass` bình thường). Điều này đảm bảo các gói dữ liệu từ Phase 1-13 vẫn hoạt động bình thường mà không bị fail.
* **Nguyên tắc kiểm định nghiêm ngặt (Strict Integrity)**:
  * Nếu tệp `source/source_profile.json` **thực sự tồn tại** trên đĩa, hoặc trong `package.json` **có** chứa đường dẫn khai báo `source_profile` $\rightarrow$ Bắt buộc tiến hành xác thực:
    * Nếu khai báo trỏ tới `source_profile` nhưng tệp tin thực tế lại **không tồn tại** $\rightarrow$ Báo lỗi thất bại rõ ràng (`ValueError`) để ngăn chặn việc mất mát dữ liệu sau khi đã chạy profiling.
    * Nếu tệp tồn tại, load cấu hình JSON và kiểm tra tính hợp lệ bằng `SourceProfileModel`.
    * Đối chiếu `quotation_id` trong profile khớp hoàn toàn với `package.quotation_id`.
    * Đảm bảo tệp nguồn chỉ định bởi `source_file` thực tế có tồn tại trên đĩa.
    * Tính toán mã băm SHA256 của tệp nguồn và đối chiếu xem có khớp hoàn toàn với `source_sha256` lưu trong profile hay không.

---

## Cập Nhật Giao Diện UI Phase 13

* Bổ sung tab **Hồ sơ nguồn (Source Profile)** trong mục Artifacts Viewer của Streamlit.
* Hiển thị đầy đủ thông tin: vai trò tài liệu, hướng xử lý đề xuất, khả năng đọc, ngày tháng phát hiện và các warnings.

---

## Quy Trình Xác Minh & Bộ Kiểm Thử (Verification Plan)

### 1. Bộ kiểm thử tự động
Xây dựng tệp kiểm thử mới [tests/test_profile_source.py](file:///D:/mep_quotation_pipeline/tests/test_profile_source.py) bao quát toàn bộ các trường hợp thành công, thất bại, định dạng không hỗ trợ, atomic write và kiểm định package.
* **Test tương thích ngược**: Thêm test case khẳng định gói dữ liệu chưa chạy `profile-source` (chưa có tệp `source_profile.json` và chưa khai báo trong package metadata) vẫn vượt qua kiểm định của `validate_package_integrity` thành công.

### 2. Yêu cầu chạy toàn bộ kiểm thử
Bắt buộc chạy toàn bộ hệ thống test suite của dự án để đảm bảo không lỗi hồi quy:
```bash
python -m pip install -e ".[dev]"
python scripts/generate_schemas.py
python -m pytest -v
```

### 3. Thử nghiệm thủ công (Smoke Test)
Tiến hành chạy lệnh `profile-source` trên package `AUT_20260620_002` thực tế và xác nhận qua giao diện Streamlit.
