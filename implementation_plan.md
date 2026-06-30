# Phase 6 – Rule-based Line Candidate Extraction

## Mô tả
Phase 6 triển khai hạ tầng phát hiện và trích xuất các dòng báo giá thô (Rule-based Line Candidate Extraction - v0.6.0). 
Đầu vào là tệp `text/quotation.md` và tệp manifest `text/quotation_text.json`. 
Đầu ra là tệp manifest chứa danh sách các dòng ứng viên `parsed/line_candidates.json` cùng chỉ mục định vị offset nguồn chính xác.

Phase này chỉ dừng ở mức nhận diện các dòng ứng viên có tiềm năng chứa thông tin báo giá (line candidates) dựa trên các quy tắc định sẵn (rule-based). Tuyệt đối không khẳng định dòng nào là vật tư chính thức, không chuẩn hóa vật tư hay đơn giá, không so sánh giá, không sử dụng AI/LLM/OCR và không gọi API bên ngoài.

## Phạm vi thực hiện (In Scope)
- Cập nhật `FilePathsModel` trong `spec/models.py` để bổ sung trường `line_candidates`.
- Định nghĩa 4 Pydantic models: `ParserWarningModel`, `LineCandidateEvidenceModel`, `LineCandidateModel`, và `LineCandidatesManifestModel`.
- Cập nhật `builder.py` để tự động gán mặc định đường dẫn `line_candidates="parsed/line_candidates.json"`.
- Nâng cấp `integrity.py` tích hợp gọi validate của Phase 6 (đối chiếu chéo `line_candidates.json` nếu tồn tại, tương thích ngược).
- Tạo module mới `mep_quotation/parser/` gồm 5 file:
  - `__init__.py`
  - `candidate_models.py` (export/import models từ spec)
  - `line_parser.py` (line scanner và trích xuất candidate attributes)
  - `candidate_manifest.py` (ghi tệp JSON và validate 12 quy tắc)
  - `parser_service.py` (điều phối luồng, cản ghi đè, ghi log kiểm toán)
- CLI: Thêm subcommand `parse-line-candidates <package_path> [--overwrite]`.
- Schema Generation: Đăng ký sinh schema `line_candidates.schema.json`.
- Tests: Tạo bộ unit tests `tests/test_line_parser.py` bao phủ tất cả các kịch bản trích xuất, cản ghi đè, và log kiểm toán.
- Tài liệu: Cập nhật `README.md`, `task.md`, `walkthrough.md`.

## Phạm vi ngoài Phase này (Out of Scope)
- Không OCR
- Không AI / LLM / Docling
- Không trích xuất cấu trúc bảng hoặc dòng cột phức tạp
- Không khẳng định vật tư cuối cùng, không so khớp BOQ hay so sánh giá
- Không chuẩn hóa vật tư (normalization) hay sinh tệp `normalized.json` từ dòng ứng viên
- Không database/API/Web
- Không cho phép người dùng can thiệp sửa đổi qua giao diện ở Phase này

---

## Proposed Changes

### Component 1 – Spec & Models

#### [MODIFY] [models.py](file:///<project_root>/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel` bổ sung:
  ```python
  line_candidates: str = Field("parsed/line_candidates.json", description="Đường dẫn file line candidates JSON, tương đối từ package root")
  ```
- Định nghĩa các Pydantic models mới ở cuối file:
  ```python
  class ParserWarningModel(BaseModel):
      code: str = Field(..., description="Mã cảnh báo, ví dụ: low_confidence, quantity_missing")
      message: str = Field(..., description="Chi tiết nội dung cảnh báo")

  class LineCandidateEvidenceModel(BaseModel):
      source_path: str = Field("text/quotation.md", description="Đường dẫn file văn bản Markdown nguồn")
      start_offset: int = Field(..., description="Vị trí bắt đầu của dòng trong file MD (Python string index)")
      end_offset: int = Field(..., description="Vị trí kết thúc ngay sau ký tự cuối của dòng trong file MD (Python string index)")
      text: str = Field(..., description="Đoạn văn bản thô nguyên bản của dòng")

  class LineCandidateModel(BaseModel):
      candidate_id: str = Field(..., description="ID dòng ứng viên định dạng {QUOTATION_ID}_LINECAND_{SEQ}")
      line_number: int = Field(..., description="Số dòng (1-indexed tính theo file Markdown nguồn)")
      page_number: int = Field(..., description="Số trang chứa dòng (1-indexed)")
      raw_line: str = Field(..., description="Nội dung văn bản thô của dòng")
      description_candidate: Optional[str] = Field(None, description="Mô tả vật tư thô")
      material_code_candidate: Optional[str] = Field(None, description="Mã vật tư thô phát hiện được")
      brand_candidate: Optional[str] = Field(None, description="Thương hiệu thô")
      unit_candidate: Optional[str] = Field(None, description="Đơn vị tính thô")
      quantity_candidate: Optional[float] = Field(None, description="Số lượng thô")
      unit_price_candidate: Optional[float] = Field(None, description="Đơn giá thô")
      currency_candidate: Optional[str] = Field(None, description="Đơn vị tiền tệ thô")
      confidence: float = Field(..., description="Độ tin cậy của dòng ứng viên (0.0 đến 1.0)")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")
      evidence: LineCandidateEvidenceModel = Field(..., description="Minh chứng định vị dòng văn bản")

  class LineCandidatesManifestModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      source_text_manifest: str = Field("text/quotation_text.json", description="Đường dẫn tương đối tới file text_manifest")
      source_markdown: str = Field("text/quotation.md", description="Đường dẫn tương đối tới file text_markdown")
      source_sha256: str = Field(..., description="SHA256 của file text/quotation.md")
      parser_name: str = Field("rule_based_line_candidate_v1", description="Tên công cụ phân tích")
      parser_version: str = Field("0.1.0", description="Phiên bản công cụ phân tích")
      candidate_count: int = Field(..., description="Tổng số dòng ứng viên trích xuất được")
      candidates: List[LineCandidateModel] = Field(..., description="Danh sách chi tiết các dòng ứng viên")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo cấp độ manifest")
      generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("generated_at")
      def serialize_generated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py](file:///<project_root>/mep_quotation/spec/__init__.py)
- Xuất thêm: `ParserWarningModel`, `LineCandidateEvidenceModel`, `LineCandidateModel`, `LineCandidatesManifestModel`.

---

### Component 2 – Package Builder & Integrity

#### [MODIFY] [builder.py](file:///<project_root>/mep_quotation/package/builder.py)
- Khởi tạo mặc định `line_candidates="parsed/line_candidates.json"` trong `FilePathsModel`.

#### [MODIFY] [integrity.py](file:///<project_root>/mep_quotation/package/integrity.py)
- Bổ sung kiểm tra chéo toàn vẹn cho `parsed/line_candidates.json` nếu tệp tồn tại:
  - Gọi hàm validate chính thức `validate_line_candidates_file(manifest_path, package_path)`.

---

### Component 3 – Module parser (MỚI)

#### [NEW] [__init__.py](file:///<project_root>/mep_quotation/parser/__init__.py)
- Xuất các hàm nghiệp vụ chính: `parse_package_line_candidates` và các lớp models liên quan.

#### [NEW] [candidate_models.py](file:///<project_root>/mep_quotation/parser/candidate_models.py)
- Import và tái xuất các model Pydantic từ `mep_quotation.spec.models` để module độc lập dễ sử dụng.

#### [NEW] [line_parser.py](file:///<project_root>/mep_quotation/parser/line_parser.py)
Triển khai logic phân tích và trích xuất từng dòng văn bản:
1. **Line Scanner**:
   - Đọc tệp `text/quotation.md`.
   - Bỏ qua các dòng trống, dòng heading Markdown (`# Quotation Text`, `## Page N`, `---`).
   - Ghi nhận `line_number` (1-indexed tính theo file Markdown nguồn).
   - Xác định `page_number` của từng dòng bằng cách ánh xạ offset `start_offset` và `end_offset` của dòng vào dải trang tương ứng trong `text/quotation_text.json`.
2. **Candidate Detection Rules**:
   Một dòng được coi là ứng viên chứa báo giá (Line Candidate) nếu có ít nhất một dấu hiệu:
   - Có đơn giá/số tiền rõ ràng.
   - Có đơn vị đo lường phổ biến (`m`, `mét`, `cái`, `bộ`, `pcs`, `set`, `kg`, `cuộn`, `box`).
   - Có mã vật tư chứa cả ký tự và chữ số (ví dụ: `CV-1.5`, `DVV-2x4`, `MCB-1P`, `M30`).
   - Chứa từ khóa/pattern MEP phổ biến: `cáp`, `dây`, `ống`, `tủ`, `CB`, `MCCB`, `MCB`, `RCCB`, `RCBO`, `đèn`, `công tắc`, `ổ cắm`.
3. **Price Extraction Rules**:
   - Chỉ nhận diện số tiền nếu không gắn liền với các thông số kỹ thuật phổ biến: `mm2`, `mm²`, `A`, `kA`, `P`, `D`, `DN`, `PN`, `Ø`, `phi`, `Hz`, `V`, `W`, `kW`.
   - Ưu tiên nhận diện đơn giá nếu số nằm gần các marker tiền tệ/đơn giá: `VND`, `VNĐ`, `đ`, `đồng`, `/m`, `/cái`, `/bộ`, `/set`, `/pcs`, `/kg`, `/cuộn`.
   - Nếu không có marker: Chỉ nhận diện khi số nằm ở cuối dòng (hoặc gần cuối dòng) và giá trị số >= 1000.
   - Trường hợp không chắc chắn, đặt `unit_price_candidate = None` và đính kèm cảnh báo phù hợp.
4. **Brand Extraction Rules**:
   - So khớp thô với danh sách thương hiệu MEP cứng nội bộ: `CADIVI`, `LS`, `Schneider`, `Panasonic`, `Sino`, `Daphaco`, `Trần Phú`, `Hager`, `ABB`, `Siemens`.
5. **Quantity Extraction Rules**:
   - Chỉ trích xuất số lượng khi có cấu trúc rõ ràng (ví dụ: `Số lượng: 10`, `Qty: 50`). Nếu không phát hiện, trả về `None`.
   - Chỉ thêm cảnh báo `quantity_missing` nếu dòng đó có cấu trúc item đầy đủ (ví dụ có mô tả, đơn giá, đơn vị tính) nhưng thiếu số lượng.
6. **Confidence & Warnings**:
   - Tính toán deterministic: Base = 0.3.
     - +0.2 nếu có `unit_price_candidate`.
     - +0.15 nếu có `unit_candidate`.
     - +0.15 nếu có `brand_candidate`.
     - +0.1 nếu có `material_code_candidate`.
     - +0.1 nếu có `quantity_candidate`.
     - Max = 1.0.
   - Nếu `confidence < 0.5`, thêm cảnh báo `low_confidence`.
7. **Evidence Mapping**:
   - Trả về đối tượng `LineCandidateEvidenceModel` với offset bắt đầu và kết thúc chuẩn xác trong `text/quotation.md`.

#### [NEW] [candidate_manifest.py](file:///<project_root>/mep_quotation/parser/candidate_manifest.py)
- Triển khai hàm `write_line_candidates_manifest(path, data)` ghi JSON deterministic.
- Triển khai hàm `validate_line_candidates_file(manifest_path, package_path)` thực hiện 12 kiểm tra validation:
  - Validate Pydantic schema của `LineCandidatesManifestModel`.
  - Kiểm tra `quotation_id` khớp với `package.json`.
  - Kiểm tra các tệp `text/quotation_text.json` và `text/quotation.md` tồn tại.
  - So khớp `source_sha256` với SHA256 của `text/quotation.md`.
  - Kiểm tra `candidate_count == len(candidates)`.
  - Đảm bảo `candidate_id` là duy nhất và tuân thủ định dạng `{QUOTATION_ID}_LINECAND_{SEQ}`.
  - Đọc file Markdown và kiểm chứng: `markdown_content[start_offset:end_offset] == evidence.text` cho từng candidate.
  - Kiểm tra `page_number` trong dải hợp lệ.
  - Đảm bảo các giá trị `unit_price_candidate >= 0` và `quantity_candidate > 0` nếu không null.
  - Đảm bảo không chứa bất kỳ trường chuẩn hóa bắt buộc nào (như `normalized/normalized.json`).

#### [NEW] [parser_service.py](file:///<project_root>/mep_quotation/parser/parser_service.py)
Triển khai hàm `parse_package_line_candidates(package_path: Path, overwrite: bool = False) -> Path`:
- Nạp `package.json` và kiểm tra sự tồn tại của các file đầu vào Phase 5.
- Atomic check: Nếu `overwrite=False` và `parsed/line_candidates.json` đã tồn tại trên đĩa → ném lỗi `ValueError` rõ ràng.
- Ghi log audit bắt đầu: `line_parser_started`.
- Quét từng dòng của file Markdown, lọc và trích xuất các candidates.
- Ghi log audit trung gian: `line_parser_lines_scanned` và `line_candidates_extracted`.
- Tạo thư mục `parsed/` nếu chưa tồn tại và ghi tệp `parsed/line_candidates.json`.
- Ghi log audit ghi file: `line_candidates_written`.
- Validate tệp tin manifest vừa ghi bằng `validate_line_candidates_file`.
- Cập nhật `package.json` (bổ sung đường dẫn `line_candidates` và trường `updated_at`).
- Chạy kiểm tra toàn vẹn package `validate_package_integrity`.
- Ghi log audit hoàn tất: `line_parser_completed`.
- Khối `except Exception`: ghi log audit lỗi `line_parser_failed` và re-raise ngoại lệ.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py](file:///<project_root>/mep_quotation/cli/main.py)
- Thêm handler `handle_parse_line_candidates(args)`.
- Thêm subcommand `parse-line-candidates <package_path> [--overwrite]`.
- Cập nhật mô tả CLI sang Phase 6.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py](file:///<project_root>/scripts/generate_schemas.py)
- Import `LineCandidatesManifestModel` và đăng ký sinh schema `line_candidates.schema.json`.

---

### Component 6 – Tests

#### [NEW] [tests/test_line_parser.py](file:///<project_root>/tests/test_line_parser.py)
- Thử nghiệm trích xuất dòng báo giá cơ bản (có giá/đơn vị).
- Kiểm chứng không bắt nhầm thông số kỹ thuật làm đơn giá (`1.5mm2`, `100A`, `25kA`, `D25`, v.v.).
- Thử nghiệm nhận diện đơn giá bằng marker và kết dòng.
- Thử nghiệm trích xuất thương hiệu (brand) từ config.
- Kiểm định logic cảnh báo thiếu số lượng (`quantity_missing`) và độ tin cậy thấp (`low_confidence`).
- Kiểm tra bỏ qua tiêu đề/heading của Markdown.
- Kiểm tra tính duy nhất và cấu trúc định dạng của `candidate_id`.
- Kiểm định ánh xạ offset và so khớp text thô trong evidence.
- Kiểm tra cản ghi đè và ghi log `line_parser_failed` tương ứng.
- Chạy CLI bằng subprocess để xác nhận tích hợp thành công.
- Đảm bảo tính tương thích ngược: validation không làm hỏng các Phase 1-5.

---

## Verification Plan

### Automated Tests
1. Cài đặt lại package:
   ```bash
   python -m pip install -e ".[dev]"
   ```
2. Sinh schema và xác nhận thành công (Tổng cộng **9 schemas**):
   ```bash
   python scripts/generate_schemas.py
   ```
3. Chạy pytest cho toàn bộ suite:
   ```bash
   python -m pytest -v
   ```
Mục tiêu: Đạt **84 tests pass** (70 cũ + 14 mới của Phase 6), 0 FAILED.

### Manual Verification
1. Sử dụng một package thật đã qua Phase 5.
2. Chạy lệnh:
   ```bash
   python -m mep_quotation.cli.main parse-line-candidates data/suppliers/CADIVI/2026/2026-06-25_002
   ```
3. Kiểm tra tệp `parsed/line_candidates.json` tồn tại, cấu trúc JSON hợp lệ.
4. Kiểm tra các dòng thông số kỹ thuật không bị bắt nhầm thành đơn giá.
5. Chạy lại lệnh trên mà không có `--overwrite` -> Phải fail và ghi audit `line_parser_failed`.
6. Chạy lại lệnh với `--overwrite` -> Phải pass.
7. Chạy kiểm thử toàn vẹn gói:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/CADIVI/2026/2026-06-25_002
   ```
