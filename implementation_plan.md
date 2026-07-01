# Phase 7 – Row Candidate Assembly / Price Association Layer

## Mô tả
Phase 7 nhận đầu vào từ Phase 6 (`parsed/line_candidates.json`) và tạo ra `parsed/row_candidates.json`. Mục tiêu là liên kết các line candidates đơn lẻ (mô tả, mã vật tư, đơn vị, đơn giá) nằm gần nhau trên cùng một trang của file Markdown thành các **Row Candidates** (dòng ứng viên báo giá ghép) đầy đủ thông tin và logic hơn.

Phase này chỉ dừng ở mức nhận diện ứng viên ghép (candidates) dựa trên các quy tắc định sẵn (rule-based). Tuyệt đối không khẳng định đây là dữ liệu báo giá chuẩn hóa cuối cùng, không sinh tệp `normalized.json` mới, không sử dụng AI/LLM/OCR/Docling.

## Phạm vi thực hiện (In Scope)
- Cập nhật `FilePathsModel` trong `spec/models.py` bổ sung trường `row_candidates`.
- Định nghĩa các Pydantic models mới: `RowCandidateModel`, `RowCandidateManifestModel` (sử dụng lại `ParserWarningModel` và `LineCandidateEvidenceModel` nếu phù hợp).
- Export các model mới trong `spec/__init__.py`.
- Nâng cấp `integrity.py` để tự động gọi validate của Phase 7 nếu tệp `row_candidates.json` tồn tại thực tế trên đĩa (đảm bảo tương thích ngược).
- Tạo module mới `mep_quotation/row_assembly/` gồm 4 file:
  - `__init__.py`
  - `assembler.py` (chứa logic quét và gom dòng, liên kết giá, chấm điểm confidence)
  - `manifest.py` (hàm ghi json deterministic và hàm validate toàn diện)
  - `row_service.py` (dịch vụ điều phối luồng, kiểm tra ghi đè, ghi log audit đầy đủ 5 sự kiện)
- CLI: Thêm subcommand `assemble-rows <package_path> [--overwrite] [--max-line-gap-for-price 6]`.
- Schema Generation: Đăng ký sinh schema `row_candidates.schema.json` trong `scripts/generate_schemas.py`.
- Tests: Tạo bộ unit tests `tests/test_row_assembly.py` bao phủ tất cả các kịch bản ghép dòng, cản ghi đè, kiểm tra toàn vẹn package và CLI.

## Phạm vi ngoài Phase này (Out of Scope)
- Không OCR.
- Không AI / LLM / Docling.
- Không table detection bằng layout/bbox.
- Không parser ngữ nghĩa cuối cùng hoặc sinh tệp `normalized.json` mới.
- Không so khớp BOQ, so sánh giá hay tương tác database/API/Web.

---

## Chi Tiết Các Thay Đổi (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel` bổ sung:
  ```python
  row_candidates: str = Field("parsed/row_candidates.json", description="Đường dẫn file row candidates JSON, tương đối từ package root")
  ```
- Định nghĩa các Pydantic models mới ở cuối file:
  ```python
  class RowCandidateModel(BaseModel):
      row_id: str = Field(..., description="ID dòng ứng viên ghép định dạng {QUOTATION_ID}_ROWCAND_{SEQ}")
      page_number: int = Field(..., description="Số trang chứa dòng ứng viên (1-indexed)")
      start_line_number: int = Field(..., description="Số dòng bắt đầu trong file MD")
      end_line_number: int = Field(..., description="Số dòng kết thúc trong file MD")
      source_candidate_ids: List[str] = Field(..., description="Danh sách các ID line candidate được ghép")
      description_candidate: Optional[str] = Field(None, description="Mô tả vật tư thô gộp")
      material_code_candidate: Optional[str] = Field(None, description="Mã vật tư thô phát hiện được")
      brand_candidate: Optional[str] = Field(None, description="Thương hiệu thô")
      unit_candidate: Optional[str] = Field(None, description="Đơn vị tính thô")
      quantity_candidate: Optional[float] = Field(None, description="Số lượng thô")
      unit_price_candidate: Optional[float] = Field(None, description="Đơn giá thô")
      currency_candidate: Optional[str] = Field(None, description="Đơn vị tiền tệ thô")
      evidence_text: str = Field(..., description="Văn bản thô nguyên bản ghép từ start_offset đến end_offset trong Markdown")
      start_offset: int = Field(..., description="Vị trí bắt đầu nhỏ nhất của các candidates trong dòng")
      end_offset: int = Field(..., description="Vị trí kết thúc lớn nhất của các candidates trong dòng")
      confidence: float = Field(..., description="Độ tin cậy của dòng ứng viên ghép (0.0 đến 1.0)")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")

  class RowCandidateManifestModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      source_line_candidates: str = Field("parsed/line_candidates.json", description="Đường dẫn tương đối tới file line_candidates")
      source_text_manifest: str = Field("text/quotation_text.json", description="Đường dẫn tương đối tới file text_manifest")
      source_sha256: str = Field(..., description="SHA256 của file parsed/line_candidates.json")
      assembler_name: str = Field("rule_based_row_candidate_assembler", description="Tên công cụ ghép dòng")
      assembler_version: str = Field("1.0", description="Phiên bản công cụ ghép dòng")
      row_count: int = Field(..., description="Tổng số row candidates ghép được")
      rows: List[RowCandidateModel] = Field(..., description="Danh sách chi tiết các row candidates")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo cấp độ manifest")
      generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("generated_at")
      def serialize_generated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất thêm: `RowCandidateModel`, `RowCandidateManifestModel`.

---

### Component 2 – Package Builder & Integrity

#### [MODIFY] [builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)
- Khởi tạo mặc định `row_candidates="parsed/row_candidates.json"` trong `FilePathsModel`.

#### [MODIFY] [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Tích hợp kiểm duyệt toàn vẹn Phase 7:
  - Nếu tệp `parsed/row_candidates.json` tồn tại thực tế trên đĩa, gọi hàm validate `validate_row_candidates_file(manifest_path, package_path)`.

---

### Component 3 – Module row_assembly (MỚI)

#### [NEW] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/row_assembly/__init__.py)
- Export API: `assemble_row_candidates` và các models liên quan.

#### [NEW] [assembler.py](file:///D:/mep_quotation_pipeline/mep_quotation/row_assembly/assembler.py)
Triển khai thuật toán ghép dòng ứng viên thô:
1. **Phân Nhóm Theo Trang (Page Isolation)**:
   - Gom các line candidates theo từng `page_number`. Quy trình ghép chỉ thực hiện trong phạm vi từng trang. Không ghép xuyên trang.
2. **Thuật Toán Gom Dòng Trong Trang**:
   - Duyệt các line candidates theo thứ tự tăng dần của `line_number`.
   - Duy trì một `current_row` (bắt đầu trống).
   - Với mỗi candidate mới `lc`:
     - Nếu `current_row` trống: khởi tạo `current_row` chứa `lc`.
     - Nếu `current_row` không trống:
       - Tính khoảng cách dòng: `gap = lc.line_number - current_row.end_line_number`.
       - Nếu `gap > max_line_gap_for_price` (mặc định = 6) -> Không gộp. Đóng `current_row` và khởi tạo `current_row` mới với `lc`.
       - Nếu `gap <= max_line_gap_for_price`:
         - **Trường hợp A**: `lc` là dòng chứa description mạnh (có mep keywords, hoặc có mô tả thô khác Null và có độ dài đáng kể):
           - Nếu `current_row` đã có description mạnh -> Không gộp (tách item). Đóng `current_row`, bắt đầu `current_row` mới với `lc`.
           - Nếu `current_row` chưa có description mạnh -> Gộp `lc` vào `current_row`.
         - **Trường hợp B**: `lc` là price-only line (chỉ có `unit_price_candidate`, không có description/brand):
           - Nếu `current_row` chưa có đơn giá -> Gộp `lc` vào `current_row` (liên kết giá).
           - Nếu `current_row` đã có đơn giá -> Bắt đầu `current_row` mới với `lc` để tránh gộp sai 2 đơn giá riêng biệt vào cùng một item.
         - **Trường hợp C**: `lc` là thông số phụ trợ (chỉ chứa mã hàng, thương hiệu, hoặc đơn vị tính):
           - Nếu `gap <= 3` (khoảng cách rất gần) -> Gộp vào `current_row`.
           - Nếu `gap > 3` -> Không gộp, tách `current_row` mới.
3. **Price Association Rules**:
   - Chỉ liên kết đơn giá từ `price-only` line sang description line gần nhất trên cùng trang.
   - Thận trọng tránh bắt nhầm thông số kỹ thuật (ví dụ: `1.5mm2`, `100A`, `25kA`, `D25`, `DN25`, `PN10`, `3P`, v.v.) làm đơn giá.
   - Nếu không chắc chắn, đặt `unit_price_candidate = None` and thêm cảnh báo `low_confidence`.
4. **Confidence Calculation**:
   - Tính toán deterministic:
     - có description: +0.3
     - có material_code: +0.15
     - có brand: +0.1
     - có unit_price: +0.25
     - có unit/currency: +0.1
     - các line candidates liên tiếp nhau không có dòng trống ở giữa (gap = 1): +0.1
     - Clamp trong khoảng `[0.0, 1.0]`.
     - Nếu `confidence < 0.5`, đính kèm cảnh báo `low_confidence`.
5. **Evidence Text Mapping**:
   - `start_offset` = `min(lc.evidence.start_offset for lc in row_candidates)`
   - `end_offset` = `max(lc.evidence.end_offset for lc in row_candidates)`
   - `evidence_text` = `markdown_content[start_offset:end_offset]`

#### [NEW] [manifest.py](file:///D:/mep_quotation_pipeline/mep_quotation/row_assembly/manifest.py)
- Hàm `write_row_candidates_manifest(path, data)`: ghi JSON deterministic.
- Hàm `validate_row_candidates_file(manifest_path, package_path)`: kiểm duyệt các quy tắc validate:
  - quotation_id khớp `package.json`.
  - `source_line_candidates` và `source_text_manifest` tồn tại thực tế.
  - `source_sha256` khớp chuẩn xác SHA256 của `parsed/line_candidates.json`.
  - `row_id` là duy nhất và tuân thủ định dạng `{QUOTATION_ID}_ROWCAND_{SEQ}`.
  - `page_number` trong dải hợp lệ.
  - `start_line_number <= end_line_number`.
  - `source_candidate_ids` đều tồn tại trong `line_candidates.json` và cùng chung `page_number` với `row.page_number`.
  - Lát cắt `markdown_content[start_offset:end_offset] == evidence_text`.
  - `row_count == len(rows)`.
  - Phase 7 không được tạo mới hoặc sửa đổi tệp normalized.json (nếu file đã có từ Phase trước thì phải giữ nguyên).

#### [NEW] [row_service.py](file:///D:/mep_quotation_pipeline/mep_quotation/row_assembly/row_service.py)
Triển khai hàm `assemble_row_candidates(package_path, overwrite=False, max_line_gap_for_price=6) -> Path`:
- Nạp `package.json` và kiểm duyệt tệp tin đầu vào Phase 6.
- Kiểm tra ghi đè: Nếu `overwrite=False` và `parsed/row_candidates.json` đã tồn tại -> ném lỗi `ValueError` rõ ràng.
- Ghi log audit bắt đầu: `row_assembly_started`.
- Phân tích ghép dòng và liên kết đơn giá từ `line_candidates.json`.
- Ghi log audit trung gian: `row_candidates_assembled`.
- Đảm bảo tạo thư mục `parsed/` trước khi ghi file, ghi tệp `parsed/row_candidates.json`.
- Ghi log audit ghi file: `row_candidates_written`.
- Validate tệp tin manifest vừa ghi bằng `validate_row_candidates_file`.
- Cập nhật `package.json` (bổ sung đường dẫn `row_candidates` và trường `updated_at`).
- Chạy kiểm tra toàn vẹn package `validate_package_integrity`.
- Ghi log audit hoàn tất: `row_assembly_completed`.
- Khối `except Exception`: ghi log audit lỗi `row_assembly_failed` và re-raise ngoại lệ.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Thêm handler `handle_assemble_rows(args)`.
- Đăng ký subcommand `assemble-rows <package_path> [--overwrite] [--max-line-gap-for-price 6]`.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Đăng ký sinh schema `row_candidates.schema.json` từ `RowCandidateManifestModel`.

---

### Component 6 – Tests

#### [NEW] [tests/test_row_assembly.py](file:///D:/mep_quotation_pipeline/tests/test_row_assembly.py)
Bao phủ các ca kiểm thử:
- `line_candidates` rỗng vẫn sinh tệp `row_candidates.json` hợp lệ với `row_count = 0` và `rows = []`.
- Gom dòng chứa mô tả và dòng đơn giá (`price-only`) nằm gần nhau trên cùng trang.
- Tránh liên kết giá xuyên trang.
- Không liên kết đơn giá nếu khoảng cách dòng vượt quá cấu hình `max_line_gap_for_price`.
- Tránh bắt nhầm thông số kỹ thuật làm đơn giá.
- Không gom hai mô tả vật tư độc lập mạnh vào cùng một row.
- `evidence_text` khớp chuẩn xác lát cắt Markdown qua offset.
- `source_sha256` khớp SHA256 của `line_candidates.json`.
- `row_id` duy nhất và có tính deterministic.
- Kiểm tra cản ghi đè `overwrite=False` ném lỗi và ghi log `row_assembly_failed` tương ứng.
- Kiểm tra cho phép ghi đè `overwrite=True` hoạt động thành công.
- CLI subprocess `assemble-rows` chạy thành công.
- `validate_package_integrity` bảo đảm tính tương thích ngược cho gói chưa có `row_candidates.json`.
- Xác nhận ghi nhận đầy đủ audit event `row_assembly_completed` khi chạy thành công và `row_assembly_failed` khi gặp lỗi.
- Xác nhận kiểm duyệt validation của `validate_package_integrity` / `validate_row_candidates_file` bắt lỗi chính xác khi:
  - `source_candidate_ids` không tồn tại trong `line_candidates.json`.
  - các source candidates trong một row bị lệch `page_number` khác nhau.
  - `evidence_text` không khớp lát cắt `markdown_content[start_offset:end_offset]`.
  - `source_sha256` của manifest bị sai lệch.
- Xác nhận Phase 7 không tự ý tạo ra file `normalized.json` nếu fixture chưa có, và giữ nguyên không sửa đổi nội dung tệp `normalized.json` nếu tệp đã được tạo sẵn từ trước.

---

## Kế Hoạch Xác Minh (Verification Plan)

### Automated Tests
1. Regenerate schemas:
   ```bash
   python scripts/generate_schemas.py
   ```
   Xác thực tạo ra thành công tệp `schemas/row_candidates.schema.json`.
2. Chạy pytest cho toàn bộ dự án:
   ```bash
   python -m pytest -v
   ```
   Mục tiêu: Đạt **102 tests pass** (87 tests cũ + ~15 tests mới của Phase 7), 0 FAILED.

### Manual Verification
1. Sử dụng một package thật đã qua Phase 6.
2. Chạy subcommand:
   ```bash
   python -m mep_quotation.cli.main assemble-rows data/suppliers/AUT/2026/2026-06-20_001
   ```
3. Xác minh tệp `parsed/row_candidates.json` được tạo thành công với cấu trúc JSON chuẩn.
4. Chạy lại câu lệnh trên mà không có `--overwrite` -> Phải fail và ghi audit log `row_assembly_failed`.
5. Chạy kiểm duyệt gói:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
   Lệnh kiểm duyệt phải PASS thành công.
