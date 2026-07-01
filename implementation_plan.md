# Phase 8 – Structured Item Candidate Layer

## Mô tả
Phase 8 nhận đầu vào từ Phase 7 (`parsed/row_candidates.json`) và tạo ra `parsed/item_candidates.json`. Mục tiêu là chuyển đổi các row candidates thô (dòng ứng viên ghép) thành các **Item Candidates** (ứng viên vật tư báo giá) có cấu trúc dữ liệu rõ ràng hơn, phục vụ cho các bước Review / Normalization / Matching ở các Phase sau.

Phase này chỉ thực hiện chuẩn hóa cấu trúc thô cấp độ candidate (như map unit alias cơ bản, tính amount_candidate). Tuyệt đối không khẳng định đây là dòng báo giá đúng cuối cùng, không sinh tệp `normalized.json` mới hoặc sửa đổi tệp này (nếu đã có thì phải giữ nguyên), không sử dụng AI/LLM/OCR/Docling.

## Phạm vi thực hiện (In Scope)
- Cập nhật `FilePathsModel` trong `spec/models.py` bổ sung trường `item_candidates`.
- Định nghĩa các Pydantic models mới: `ItemCandidateModel`, `ItemCandidateManifestModel` (sử dụng lại `ParserWarningModel` nếu phù hợp).
- Export các model mới trong `spec/__init__.py`.
- Nâng cấp `integrity.py` để tự động gọi validate của Phase 8 nếu tệp `item_candidates.json` tồn tại thực tế trên đĩa (đảm bảo tương thích ngược).
- Tạo module mới `mep_quotation/item_candidates/` gồm 4 file:
  - `__init__.py`
  - `builder.py` (chứa logic chuyển đổi cấu trúc RowCandidate -> ItemCandidate, map đơn vị tính alias cơ bản, tính amount)
  - `manifest.py` (hàm ghi json deterministic và hàm validate các quy tắc dữ liệu của item candidates)
  - `item_service.py` (dịch vụ điều phối luồng chính, kiểm tra ghi đè, ghi log audit đầy đủ 5 sự kiện kiểm toán)
- CLI: Thêm subcommand `build-item-candidates <package_path> [--overwrite]`.
- Schema Generation: Đăng ký sinh schema `item_candidates.schema.json` trong `scripts/generate_schemas.py`.
- Tests: Tạo bộ unit tests `tests/test_item_candidates.py` bao phủ tất cả các kịch bản chuyển đổi cấu trúc, tính amount, cảnh báo độ tin cậy thấp, cản ghi đè, validate dữ liệu lỗi và CLI.

## Phạm vi ngoài Phase này (Out of Scope)
- Không OCR.
- Không AI / LLM / Docling.
- Không table detection bằng layout/bbox.
- Không so khớp BOQ hay so sánh đơn giá cuối cùng.
- Không tự ý tạo mới hay sửa đổi tệp `normalized/normalized.json`.
- Không database/API/Web.

---

## Chi Tiết Các Thay Đổi (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel` bổ sung:
  ```python
  item_candidates: str = Field("parsed/item_candidates.json", description="Đường dẫn file item candidates JSON, tương đối từ package root")
  ```
- Định nghĩa các Pydantic models mới ở cuối file:
  ```python
  class ItemCandidateModel(BaseModel):
      item_candidate_id: str = Field(..., description="ID ứng viên vật tư định dạng {QUOTATION_ID}_ITEMCAND_{SEQ}")
      source_row_id: str = Field(..., description="ID row candidate nguồn từ Phase 7")
      page_number: int = Field(..., description="Số trang chứa ứng viên (1-indexed)")
      start_line_number: int = Field(..., description="Số dòng bắt đầu trong file MD")
      end_line_number: int = Field(..., description="Số dòng kết thúc trong file MD")
      description_candidate: Optional[str] = Field(None, description="Mô tả vật tư thô")
      material_code_candidate: Optional[str] = Field(None, description="Mã vật tư thô")
      brand_candidate: Optional[str] = Field(None, description="Thương hiệu thô")
      unit_candidate: Optional[str] = Field(None, description="Đơn vị tính candidate, có thể được map alias rất hạn chế nếu chắc chắn; không phải normalized unit")
      quantity_candidate: Optional[float] = Field(None, description="Số lượng thô")
      unit_price_candidate: Optional[float] = Field(None, description="Đơn giá thô")
      currency_candidate: Optional[str] = Field(None, description="Đơn vị tiền tệ thô")
      amount_candidate: Optional[float] = Field(None, description="Thành tiền candidate (chỉ tính khi có đủ đơn giá và số lượng)")
      raw_evidence_text: str = Field(..., description="Văn bản thô nguyên bản từ row.evidence_text")
      start_offset: int = Field(..., description="Vị trí bắt đầu nhỏ nhất của các candidates")
      end_offset: int = Field(..., description="Vị trí kết thúc lớn nhất của các candidates")
      confidence: float = Field(..., description="Độ tin cậy của ứng viên vật tư (0.0 đến 1.0)")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")

  class ItemCandidateManifestModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      source_row_candidates: str = Field("parsed/row_candidates.json", description="Đường dẫn tương đối tới file row_candidates")
      source_sha256: str = Field(..., description="SHA256 của file parsed/row_candidates.json")
      source_text_manifest: str = Field("text/quotation_text.json", description="Đường dẫn tương đối tới tệp text_manifest")
      builder_name: str = Field("rule_based_item_candidate_builder", description="Tên công cụ dựng item")
      builder_version: str = Field("1.0", description="Phiên bản công cụ dựng item")
      item_count: int = Field(..., description="Tổng số item candidates dựng được")
      items: List[ItemCandidateModel] = Field(..., description="Danh sách chi tiết các item candidates")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo cấp độ manifest")
      generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("generated_at")
      def serialize_generated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất thêm: `ItemCandidateModel`, `ItemCandidateManifestModel`.

---

### Component 2 – Package Builder & Integrity

#### [MODIFY] [builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)
- Khởi tạo mặc định `item_candidates="parsed/item_candidates.json"` trong `FilePathsModel`.

#### [MODIFY] [integrity.py](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Tích hợp kiểm duyệt toàn vẹn Phase 8:
  - Nếu tệp `parsed/item_candidates.json` tồn tại thực tế trên đĩa, gọi hàm validate `validate_item_candidates_file(manifest_path, package_path)`.

---

### Component 3 – Module item_candidates (MỚI)

#### [NEW] [__init__.py](file:///D:/mep_quotation_pipeline/mep_quotation/item_candidates/__init__.py)
- Export API: `build_item_candidates` và các models liên quan.

#### [NEW] [builder.py](file:///D:/mep_quotation_pipeline/mep_quotation/item_candidates/builder.py)
Triển khai logic chuyển đổi Row Candidates thành Item Candidates:
1. **Duyệt Row Candidates**:
   - Chuyển đổi deterministic từ danh sách row candidates sang item candidates. Mỗi row candidate tạo ra một item candidate tương ứng.
2. **Field Rules**:
   - `description_candidate`: lấy từ row.description_candidate, trim whitespace.
   - `material_code_candidate`: lấy từ row.material_code_candidate.
   - `brand_candidate`: lấy từ row.brand_candidate.
   - `unit_candidate`: Map alias đơn vị tính thô ở mức candidate-level rất hạn chế nếu chắc chắn (ví dụ: `pcs`, `piece`, `cái` ➔ `cái`, `m`, `meter`, `met` ➔ `m`, `bộ`, `set` ➔ `bộ`). Đây không phải normalized unit và không tạo normalized output. Ngược lại giữ nguyên hoặc để Null.
   - `quantity_candidate`: lấy từ row.quantity_candidate.
   - `unit_price_candidate`: lấy từ row.unit_price_candidate.
   - `currency_candidate`: lấy từ row.currency_candidate nếu có. Nếu có đơn giá nhưng currency Null, chỉ được mặc định `VND` khi package/row/context thể hiện rõ báo giá dùng VND. Nếu không có tín hiệu rõ ràng thì để Null (không tự đoán currency).
   - `amount_candidate`: `quantity_candidate * unit_price_candidate` nếu cả hai phi-Null. Ngược lại là Null.
   - `raw_evidence_text`: giữ nguyên `row.evidence_text`.
   - `start_offset` và `end_offset`: giữ nguyên từ row.
3. **Confidence Chấm Điểm**:
   - Chấm điểm deterministic:
     - có description_candidate: +0.25
     - có material_code_candidate: +0.15
     - có brand_candidate: +0.10
     - có unit_candidate: +0.10
     - có unit_price_candidate: +0.20
     - có quantity_candidate: +0.10
     - có evidence offset hợp lệ: +0.10
     - Clamp trong dải `[0.0, 1.0]`.
     - Nếu `confidence < 0.5`, thêm warning `low_confidence`.
   - Gộp các warnings từ row candidate sang.

#### [NEW] [manifest.py](file:///D:/mep_quotation_pipeline/mep_quotation/item_candidates/manifest.py)
- Hàm `write_item_candidates_manifest(path, data)`: ghi JSON deterministic.
- Hàm `validate_item_candidates_file(manifest_path, package_path)`: kiểm duyệt các quy tắc validate:
  - `quotation_id` khớp `package.json`.
  - `source_row_candidates` và `source_text_manifest` tồn tại thực tế.
  - `source_sha256` khớp SHA256 của `parsed/row_candidates.json`.
  - `item_candidate_id` duy nhất và đúng định dạng `{QUOTATION_ID}_ITEMCAND_{SEQ}`.
  - `source_row_id` tồn tại thực tế trong `row_candidates.json` và có các thuộc tính tương thích (page_number, line_number, offset, evidence text khớp).
  - Lát cắt `markdown_content[start_offset:end_offset] == raw_evidence_text`.
  - `item_count == len(items)`.
  - `amount_candidate` tính toán chính xác.
  - Phase 8 không tự ý tạo mới hoặc sửa đổi nội dung tệp `normalized.json`.

#### [NEW] [item_service.py](file:///D:/mep_quotation_pipeline/mep_quotation/item_candidates/item_service.py)
Triển khai hàm `build_item_candidates(package_path, overwrite=False) -> Path`:
- Nạp `package.json` và kiểm duyệt tệp tin đầu vào Phase 7.
- Kiểm tra ghi đè: Nếu `overwrite=False` và `parsed/item_candidates.json` đã tồn tại -> ném lỗi `ValueError` rõ ràng.
- Ghi log audit bắt đầu: `item_candidate_build_started`.
- Thực hiện chuyển đổi cấu trúc sang item candidates.
- Ghi log audit trung gian: `item_candidates_built`.
- Đảm bảo tạo thư mục `parsed/` trước khi ghi file, ghi tệp `parsed/item_candidates.json`.
- Ghi log audit ghi file: `item_candidates_written`.
- Validate tệp tin manifest vừa ghi bằng `validate_item_candidates_file`.
- Cập nhật `package.json` (bổ sung đường dẫn `item_candidates` và `updated_at`).
- Chạy kiểm tra toàn vẹn package `validate_package_integrity`.
- Ghi log audit hoàn tất: `item_candidate_build_completed`.
- Khối `except Exception`: ghi log audit lỗi `item_candidate_build_failed` và re-raise ngoại lệ.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Thêm handler `handle_build_item_candidates(args)`.
- Đăng ký subcommand `build-item-candidates <package_path> [--overwrite]`.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Đăng ký sinh schema `item_candidates.schema.json` từ `ItemCandidateManifestModel`.

---

### Component 6 – Tests

#### [NEW] [tests/test_item_candidates.py](file:///D:/mep_quotation_pipeline/tests/test_item_candidates.py)
Bao phủ các ca kiểm thử:
- Chuyển đổi item candidate thành công từ row candidate hợp lệ.
- `item_candidate_id` duy nhất và có tính deterministic.
- `source_sha256` khớp SHA256 của `row_candidates.json`.
- `raw_evidence_text` giữ nguyên từ row candidate và khớp lát cắt offset Markdown.
- `amount_candidate` tính toán chính xác khi đủ dữ liệu, và bằng Null khi thiếu.
- Không tự ý sinh cảnh báo `quantity_missing` mặc định.
- Tự động gán cảnh báo `low_confidence` khi thiếu nhiều thuộc tính.
- Unit alias mapping cơ bản hoạt động đúng (pcs ➔ cái, m ➔ m, bộ ➔ bộ).
- `row_candidates` rỗng vẫn sinh tệp `item_candidates.json` hợp lệ.
- Kiểm tra cản ghi đè `overwrite=False` ném lỗi và ghi log `item_candidate_build_failed` tương ứng.
- Kiểm tra cho phép ghi đè `overwrite=True` hoạt động thành công.
- CLI subprocess `build-item-candidates` chạy thành công.
- `validate_package_integrity` bảo đảm tính tương thích ngược cho gói chưa có `item_candidates.json`.
- Bắt lỗi validation của `validate_item_candidates_file` khi:
  - `source_row_id` không tồn tại hoặc sai lệch.
  - `source_sha256` sai.
  - `raw_evidence_text` lệch.
  - `amount_candidate` tính toán sai.
- Phase 8 không tự ý tạo mới hoặc sửa đổi nội dung tệp `normalized.json`.

---

## Kế Hoạch Xác Minh (Verification Plan)

### Automated Tests
1. Regenerate schemas:
   ```bash
   python scripts/generate_schemas.py
   ```
   Xác thực tạo ra thành công tệp `schemas/item_candidates.schema.json`.
2. Chạy pytest cho toàn bộ dự án:
   ```bash
   python -m pytest -v
   ```
   Mục tiêu: Đạt **117 tests pass** (101 tests cũ + ~16 tests mới của Phase 8), 0 FAILED.

### Manual Verification
1. Sử dụng một package thật đã qua Phase 7.
2. Chạy subcommand:
   ```bash
   python -m mep_quotation.cli.main build-item-candidates data/suppliers/AUT/2026/2026-06-20_001
   ```
3. Xác minh tệp `parsed/item_candidates.json` được tạo thành công với cấu trúc JSON chuẩn.
4. Chạy lại câu lệnh trên mà không có `--overwrite` -> Phải fail và ghi audit log `item_candidate_build_failed`.
5. Chạy kiểm duyệt gói:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
   Lệnh kiểm duyệt phải PASS thành công.
