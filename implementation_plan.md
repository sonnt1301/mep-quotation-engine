# Phase 4 – PDF Native Content Extraction

## Mô tả

Phase 4 triển khai hạ tầng trích xuất nội dung văn bản gốc từ PDF (Native PDF Text Extraction). Không OCR, không AI, không parser nội dung. Chỉ lấy text thô mà PDF engine trả về cho từng trang và lưu vào `source/raw_text.json`.

## Phạm vi thực hiện (In Scope)

- Tạo module `mep_quotation/pdf_text/` gồm 4 file
- Thêm `RawTextPageModel`, `RawTextManifestModel` vào `spec/models.py`
- Cập nhật `FilePathsModel` thêm trường `raw_text`
- Cập nhật `builder.py` để gán mặc định `raw_text`
- Cập nhật `integrity.py` để đối chiếu chéo `raw_text.json` (backward compatible)
- Thêm CLI subcommand `extract-text`
- Cập nhật `generate_schemas.py` và sinh `schemas/raw_text.schema.json`
- Viết test suite `tests/test_pdf_text.py`
- Cập nhật tài liệu

## Phạm vi ngoài Phase này (Out of Scope)

- Không OCR
- Không AI / LLM
- Không parser nội dung báo giá
- Không table detection / table parsing
- Không normalization
- Không database / API / Web

---

## Proposed Changes

### Component 1 – Spec & Models

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)

Thêm 2 model mới sau `PageManifestModel`:

```python
class RawTextPageModel(BaseModel):
    page_number: int           # 1-indexed
    has_text: bool             # True nếu page có text
    character_count: int       # len(text) Python, tính trên Unicode string
    text: str                  # text thô do engine trả về, không trim/normalize

class RawTextManifestModel(BaseModel):
    schema_version: str = "1.0"
    quotation_id: str
    source_pdf: str            # "source/original.pdf"
    source_sha256: str         # SHA256 của source/original.pdf
    extraction_engine: str     # "pymupdf" hoặc "pypdf"
    extraction_engine_version: Optional[str]  # version nếu lấy được, None nếu không
    page_count: int            # tổng số trang
    pages: List[RawTextPageModel]
    generated_at: datetime
```

Cập nhật `FilePathsModel`:

```python
raw_text: str = Field("source/raw_text.json", ...)
```

#### [MODIFY] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)

Export `RawTextPageModel`, `RawTextManifestModel`.

---

### Component 2 – Package Builder

#### [MODIFY] [builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)

Thêm `raw_text="source/raw_text.json"` khi khởi tạo `FilePathsModel`.

---

### Component 3 – Package Integrity

#### [MODIFY] [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)

Thêm kiểm tra đối chiếu `raw_text.json` (chỉ khi file tồn tại thực tế, backward compatible).
**Không tự check thủ công** – gọi thẳng `validate_raw_text_file(raw_text_path, package_path)` từ `pdf_text.manifest` để đảm bảo tất cả validation rules được áp dụng nhất quán:
- `raw_text.quotation_id == package.quotation_id`
- `raw_text.page_count` khớp số trang PDF thực tế
- Nếu có `source/metadata.json` → khớp `page_count`
- Nếu có `source/page_manifest.json` → khớp `page_count`
- `page_number` bắt đầu từ 1, liên tục, không thiếu trang
- `character_count == len(text)` cho từng trang

---

### Component 4 – Module pdf_text (MỚI)

#### [NEW] [mep_quotation/pdf_text/__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_text/__init__.py)

Export `extract_pdf_text`, `extract_package_text`.

#### [NEW] [mep_quotation/pdf_text/extractor.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_text/extractor.py)

Hàm `extract_pdf_text(pdf_path: Path) -> RawTextManifestModel`:
- Mở PDF bằng PyMuPDF (`fitz`)
- Kiểm tra `doc.is_encrypted` → fail ngay lập tức, không decrypt
- Lấy text từng trang bằng `page.get_text()` (text thô, không trim/clean)
- Tính `has_text = bool(text)`, `character_count = len(text)`
- Ghi nhận `extraction_engine = "pymupdf"`, `extraction_engine_version = fitz.version[0]` (hoặc None nếu fail)
- Tính `source_sha256` của file PDF
- Trả về `RawTextManifestModel`

#### [NEW] [mep_quotation/pdf_text/manifest.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_text/manifest.py)

Hàm `write_raw_text_manifest(path: Path, data: RawTextManifestModel) -> None`:
- Serialize deterministic (sort_keys=True, ensure_ascii=False)
- Ghi ra file JSON

Hàm `validate_raw_text_file(raw_text_path: Path, package_path: Path) -> None`:
- Đọc và parse lại `raw_text.json`
- Validate `quotation_id` khớp với `package.json`
- Validate `page_count` khớp số trang PDF thực tế (mở PDF bằng fitz)
- Nếu có `source/metadata.json` → kiểm tra khớp `page_count`
- Nếu có `source/page_manifest.json` → kiểm tra khớp `page_count`
- Kiểm tra `page_number` bắt đầu từ 1, liên tục, không thiếu trang
- Kiểm tra `character_count == len(text)` cho từng trang

#### [NEW] [mep_quotation/pdf_text/text_service.py](file:///D:/mep_quotation_pipeline/mep_quotation/pdf_text/text_service.py)

Hàm `extract_package_text(package_path: Path, overwrite: bool = False) -> Path`:
- Load `package.json`
- Kiểm tra `metadata.json` → nếu `encrypted == True` → fail rõ ràng
- Kiểm tra `overwrite` → nếu `source/raw_text.json` đã tồn tại và `overwrite=False` → fail rõ ràng
- Gọi `extract_pdf_text(pdf_path)`
- Ghi file `source/raw_text.json`
- Validate sau khi ghi
- Cập nhật `package.json` (set `files.raw_text = "source/raw_text.json"`, cập nhật `updated_at`)
- Ghi audit log
- Trả về `package_path`

Audit events: `pdf_text_extraction_started`, `pdf_text_extracted`, `raw_text_written`, `pdf_text_extraction_completed`, `pdf_text_extraction_failed`

---

### Component 5 – CLI

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)

Thêm subcommand `extract-text <package_path> [--overwrite]`.

Output:
```
Successfully extracted PDF text.
  Quotation ID     : AUT_20260620_001
  Page Count       : 8
  Total Characters : 4523
  Pages With Text  : 7
  Output Path      : source/raw_text.json
```

---

### Component 6 – Schema Generation

#### [MODIFY] [generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)

Thêm `RawTextManifestModel` vào danh sách sinh schema.

---

### Component 7 – Tests

#### [NEW] [tests/test_pdf_text.py](file:///D:/mep_quotation_pipeline/tests/test_pdf_text.py)

Các kịch bản kiểm thử:
- `test_extract_pdf_text_with_text`: PDF có text, kiểm tra `has_text=True`, `character_count`, nội dung text
- `test_extract_pdf_text_no_text`: PDF rasterized không có text layer, kiểm tra `has_text=False`, `text=""`
- `test_extract_pdf_text_encrypted`: PDF encrypted → fail rõ ràng
- `test_raw_text_schema_valid`: validate Pydantic schema
- `test_character_count_accuracy`: `character_count == len(text)` cho từng trang
- `test_page_count_matches_pdf`: `raw_text.page_count == số trang PDF thực tế`
- `test_page_count_cross_check_metadata`: Cross-check với `metadata.json` nếu tồn tại
- `test_page_count_cross_check_page_manifest`: Cross-check với `page_manifest.json` nếu tồn tại
- `test_extract_package_text_flow`: Luồng hoàn chỉnh, kiểm tra `package.json` được cập nhật
- `test_overwrite_false_fail`: Gọi lại mà không có `--overwrite` → fail
- `test_overwrite_true_pass`: Gọi lại với `overwrite=True` → pass, audit event có `overwrite: true`
- `test_source_sha256_traceability`: `source_sha256` khớp SHA256 của `original.pdf`
- `test_cli_extract_text`: CLI subprocess chạy đúng, returncode=0
- `test_audit_events`: Kiểm tra audit log ghi đủ 4 events theo thứ tự

---

## Verification Plan

### Automated Tests
```bash
python -m pip install -e ".[dev]"
python scripts/generate_schemas.py
python -m pytest -v
```

Mục tiêu: **59 tests pass** (45 cũ + 14 mới), 0 FAILED.

### Manual Verification (Acceptance Test với Package thật)

Sau khi có package đã qua Phase 2/3, chạy tuần tự các bước sau:

**Bước 1 – Extract lần đầu:**
```bash
python -m mep_quotation.cli.main extract-text data/suppliers/AUT/2026/2026-06-20_001
```
Kiểm tra:
- `returncode == 0`
- In ra `Quotation ID`, `Page Count`, `Total Characters`, `Pages With Text`, `Output Path`

**Bước 2 – Kiểm tra file sinh ra:**
- `source/raw_text.json` tồn tại
- `raw_text.quotation_id` khớp với `package.json`
- `raw_text.page_count` đúng số trang PDF
- `raw_text.pages` có đúng số phần tử = `page_count`
- `raw_text.source_sha256` khớp SHA256 của `source/original.pdf`
- `raw_text.extraction_engine == "pymupdf"`

**Bước 3 – Overwrite protection:**
```bash
python -m mep_quotation.cli.main extract-text data/suppliers/AUT/2026/2026-06-20_001
```
→ Phải fail rõ ràng với error message đề cập `raw_text.json already exists`

**Bước 4 – Overwrite cho phép:**
```bash
python -m mep_quotation.cli.main extract-text data/suppliers/AUT/2026/2026-06-20_001 --overwrite
```
→ Phải pass, `returncode == 0`

**Bước 5 – Validate toàn vẹn package:**
```bash
python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
```
→ Phải pass, `Package is valid`

**Bước 6 – Kiểm tra audit log:**
- Mở `logs/processing.log.jsonl`
- Phải tồn tại events theo thứ tự: `pdf_text_extraction_started` → `pdf_text_extracted` → `raw_text_written` → `pdf_text_extraction_completed`
- Audit event overwrite phải có `"overwrite": true` trong `details`

**Bước 7 – Verify schema:**
```bash
python scripts/generate_schemas.py
```
→ File `schemas/raw_text.schema.json` tồn tại và hợp lệ

---

## Assumptions

1. Sử dụng PyMuPDF (`fitz`) làm extraction engine (đã cài sẵn từ Phase 3).
2. Text thô được lấy bằng `page.get_text()` mặc định của PyMuPDF – không dùng `get_text("blocks")` hay `get_text("dict")`.
3. Không trim, không normalize, không sửa khoảng trắng ngoài kết quả engine trả về.
4. `character_count = len(text)` tính trên Python str (Unicode), không phải byte count.
5. Backward compatible: Package Phase 1/2/3 chưa có `raw_text.json` vẫn qua kiểm tra integrity thành công.

## Open Questions

Không có câu hỏi mở. Yêu cầu Phase 4 đã rõ ràng và đủ chi tiết.
