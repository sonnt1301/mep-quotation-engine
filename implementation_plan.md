# Phase 9 – Normalized Draft Layer / Review-Ready Normalization

## Mô tả
Phase 9 nhận đầu vào từ Phase 8 (`parsed/item_candidates.json`) và tạo ra tệp nháp chuẩn hóa `normalized/normalized_draft.json`. Mục tiêu là chuyển đổi các ứng viên vật tư (item candidates) thành bản dữ liệu chuẩn hóa nháp có cấu trúc gần giống với báo giá chính thức, hỗ trợ cho việc rà soát thủ công (human review) hoặc chạy đối chiếu ở các Phase tiếp theo.

Phase này chỉ sinh bản nháp review. Tuyệt đối không được coi đây là kết quả chuẩn hóa báo giá cuối cùng, không được tự ý tạo mới, ghi đè hoặc sửa đổi tệp kết quả chính thức `normalized/normalized.json`.

## Nguyên tắc bảo vệ dữ liệu và bảo mật
- **Không can thiệp normalized.json**: Nếu tệp `normalized/normalized.json` đã tồn tại trước đó từ Phase khác, Phase 9 phải lưu lại SHA256 của nó và bảo đảm SHA256 này không thay đổi sau khi chạy xong. Nếu tệp chưa tồn tại, Phase 9 không được tự sinh ra tệp đó.
- **Không tự đoán thông tin**: Không tự ý đoán đơn vị tiền tệ hoặc parse dữ liệu bừa bãi khi thiếu thông tin rõ ràng. Giữ trace liên kết đầy đủ đối với từng item.
- **Không sử dụng AI/OCR/LLM**: Luồng xử lý hoàn toàn rule-based deterministic.

---

## Chi Tiết Các Thay Đổi (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py (D:\mep_quotation_pipeline\mep_quotation\spec\models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel` bổ sung:
  ```python
  normalized_draft: str = Field("normalized/normalized_draft.json", description="Đường dẫn file nháp chuẩn hóa JSON, tương đối từ package root")
  ```
- Định nghĩa các Pydantic models mới ở cuối file:
  ```python
  class NormalizedDraftEvidenceModel(BaseModel):
      raw_evidence_text: str = Field(..., description="Văn bản gốc từ row candidate")
      start_offset: int = Field(..., description="Vị trí bắt đầu trong file MD")
      end_offset: int = Field(..., description="Vị trí kết thúc trong file MD")

  class NormalizedDraftItemModel(BaseModel):
      draft_item_id: str = Field(..., description="ID nháp chuẩn hóa định dạng {QUOTATION_ID}_DRAFTITEM_{SEQ}")
      source_item_candidate_id: str = Field(..., description="ID item candidate nguồn từ Phase 8")
      source_row_id: str = Field(..., description="ID row candidate nguồn từ Phase 7")
      page_number: int = Field(..., description="Số trang chứa ứng viên (1-indexed)")
      start_line_number: int = Field(..., description="Số dòng bắt đầu trong file MD")
      end_line_number: int = Field(..., description="Số dòng kết thúc trong file MD")
      material_code: Optional[str] = Field(None, description="Mã vật tư chuẩn hóa nháp")
      description: Optional[str] = Field(None, description="Mô tả vật tư chuẩn hóa nháp")
      brand: Optional[str] = Field(None, description="Thương hiệu chuẩn hóa nháp")
      unit: Optional[str] = Field(None, description="Đơn vị tính chuẩn hóa nháp")
      quantity: Optional[float] = Field(None, description="Số lượng chuẩn hóa nháp")
      unit_price: Optional[float] = Field(None, description="Đơn giá chuẩn hóa nháp")
      currency: Optional[str] = Field(None, description="Đơn vị tiền tệ chuẩn hóa nháp")
      amount: Optional[float] = Field(None, description="Thành tiền chuẩn hóa nháp")
      review_status: str = Field(..., description="Trạng thái review (auto_ready | needs_review | rejected_candidate)")
      review_reasons: List[str] = Field(default_factory=list, description="Danh sách mã lý do cần review")
      confidence: float = Field(..., description="Điểm tin cậy điều chỉnh (0.0 đến 1.0)")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")
      evidence: NormalizedDraftEvidenceModel = Field(..., description="Trace vết văn bản chứng cứ")

  class NormalizedDraftModel(BaseModel):
      schema_version: str = Field("1.0", description="Phiên bản schema")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      supplier_code: Optional[str] = Field(None, description="Mã nhà cung cấp lấy từ package.json")
      quotation_date: Optional[str] = Field(None, description="Ngày báo giá lấy từ package.json")
      currency: Optional[str] = Field(None, description="Đơn vị tiền tệ chung của báo giá")
      source_item_candidates: str = Field("parsed/item_candidates.json", description="Đường dẫn tương đối tới file item_candidates")
      source_sha256: str = Field(..., description="SHA256 của file parsed/item_candidates.json")
      draft_builder_name: str = Field("rule_based_normalized_draft_builder", description="Tên công cụ dựng nháp")
      draft_builder_version: str = Field("1.0", description="Phiên bản công cụ dựng nháp")
      item_count: int = Field(..., description="Tổng số draft items")
      review_required_count: int = Field(..., description="Số draft items cần review (review_status = needs_review)")
      items: List[NormalizedDraftItemModel] = Field(..., description="Danh sách các draft items")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo cấp độ manifest")
      generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("generated_at")
      def serialize_generated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py (D:\mep_quotation_pipeline\mep_quotation\spec\__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất thêm: `NormalizedDraftEvidenceModel`, `NormalizedDraftItemModel`, `NormalizedDraftModel`.

---

### Component 2 – Package Builder & Integrity

#### [MODIFY] [builder.py (D:\mep_quotation_pipeline\mep_quotation\package\builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)
- Khởi tạo mặc định `normalized_draft="normalized/normalized_draft.json"` trong `FilePathsModel`.

#### [MODIFY] [integrity.py (D:\mep_quotation_pipeline\mep_quotation\package\integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Tích hợp kiểm duyệt toàn vẹn Phase 9:
  - Nếu tệp `normalized/normalized_draft.json` tồn tại thực tế trên đĩa, gọi validate `validate_normalized_draft_file(manifest_path, package_path)`.

---

### Component 3 – Module normalized_draft (MỚI)

#### [NEW] [__init__.py (D:\mep_quotation_pipeline\mep_quotation\normalized_draft\__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_draft/__init__.py)
- Export API: `build_normalized_draft` và các models liên quan.

#### [NEW] [builder.py (D:\mep_quotation_pipeline\mep_quotation\normalized_draft\builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_draft/builder.py)
Triển khai logic chuyển đổi Item Candidates sang Normalized Draft Items:
1. **Duyệt Item Candidates**:
   - Chuyển đổi deterministic từng item candidate sang draft item tương ứng.
2. **Quy tắc gán thuộc tính**:
   - `description`: trim whitespace, không dịch, không viết lại. Nếu null -> gán lý do review `missing_description`.
   - `material_code`: lấy từ item, không tự đoán.
   - `brand`: lấy từ item.
   - `unit`: lấy từ item. Nếu null và item không bị `rejected_candidate` -> gán lý do review `missing_unit`.
   - `quantity`: lấy từ item. Không mặc định 1. Chỉ cảnh báo `missing_quantity` nếu có đơn giá và thành tiền cần tính mà số lượng bị khuyết.
   - `unit_price`: lấy từ item. Nếu null và item không bị `rejected_candidate` -> gán lý do review `missing_unit_price`.
   - `currency`: lấy từ item. Nếu null, có thể gán currency chung nếu package metadata có currency rõ ràng hoặc đa số item candidates có cùng currency. Ngược lại để null.
   - `amount`: `quantity * unit_price` nếu cả hai phi-Null. Validate khớp với `item.amount_candidate`. Nếu không khớp, dùng amount tính lại và cảnh báo warning `amount_mismatch_recomputed`.
3. **Phân loại Trạng thái Review (`review_status`)**:
   - `auto_ready`:
     - có description khác null
     - có unit_price khác null
     - confidence >= 0.75
     - evidence offset hợp lệ (`start_offset >= 0` và `end_offset > start_offset`)
     - không có warning nghiêm trọng
   - `rejected_candidate`:
     - thiếu cả description, material_code và unit_price
     - hoặc confidence < 0.20
     - hoặc bị đánh dấu là rejected_weak_candidate.
   - `needs_review`: các trường hợp còn lại.
4. **Điều chỉnh Confidence**:
   - `base_confidence = item.confidence`
   - Trừ điểm: thiếu description (-0.20), thiếu unit_price (-0.20), evidence invalid (-0.20), low_confidence từ source (-0.10).
   - Cộng điểm: có description + unit_price + evidence hợp lệ (+0.10), amount tính được (+0.05).
   - Clamp trong khoảng `[0.0, 1.0]`.

#### [NEW] [manifest.py (D:\mep_quotation_pipeline\mep_quotation\normalized_draft\manifest.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_draft/manifest.py)
- Hàm `write_normalized_draft(path, data)`: ghi JSON deterministic.
- Hàm `validate_normalized_draft_file(manifest_path, package_path)`:
  - `quotation_id`, `supplier_code`, `quotation_date` khớp `package.json`.
  - `source_item_candidates` và `source_sha256` khớp SHA256 thực tế của `item_candidates.json`.
  - `draft_item_id` duy nhất và đúng format.
  - Các thuộc tính định vị và chứng cứ khớp source item candidate.
  - Lát cắt Markdown khớp `raw_evidence_text`.
  - `item_count` và `review_required_count` tính toán chính xác.
  - Bảo đảm không được sửa đổi, tạo mới hoặc làm thay đổi SHA256 của `normalized/normalized.json`.

#### [NEW] [draft_service.py (D:\mep_quotation_pipeline\mep_quotation\normalized_draft\draft_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_draft/draft_service.py)
- Hàm `build_normalized_draft(package_path, overwrite=False) -> Path`:
  - Kiểm duyệt đầu vào. Đảm bảo thư mục `normalized/` tồn tại.
  - Nếu `normalized/normalized.json` đã có, tính SHA256 ban đầu.
  - Overwrite check: Nếu `overwrite=False` và `normalized/normalized_draft.json` đã có -> ném lỗi `ValueError`.
  - Ghi audit bắt đầu: `normalized_draft_build_started`.
  - Thực hiện chuyển đổi và ghi file nháp.
  - Ghi audit trung gian: `normalized_draft_built`, `normalized_draft_written`.
  - Validate tệp vừa ghi và toàn vẹn gói.
  - Nếu `normalized/normalized.json` đã có, so khớp SHA256 xem có bị thay đổi không. Nếu có thay đổi -> ném lỗi. Nếu chưa có, đảm bảo không tự tạo nó.
  - Ghi audit hoàn tất: `normalized_draft_build_completed`.
  - Khối `except`: Ghi log audit thất bại `normalized_draft_build_failed` và re-raise.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py (D:\mep_quotation_pipeline\mep_quotation\cli\main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Thêm subcommand `build-normalized-draft <package_path> [--overwrite]`.
- Handler in thống kê: quotation_id, supplier_code, quotation_date, item_count, review_required_count, auto_ready_count, rejected_candidate_count, warnings count.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py (D:\mep_quotation_pipeline\scripts\generate_schemas.py)](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Đăng ký sinh schema `normalized_draft.schema.json` từ `NormalizedDraftModel`.

---

### Component 6 – Tests

#### [NEW] [tests/test_normalized_draft.py (D:\mep_quotation_pipeline\tests\test_normalized_draft.py)](file:///D:/mep_quotation_pipeline/tests/test_normalized_draft.py)
Bao phủ các kịch bản:
- Dựng thành công draft từ item_candidates hợp lệ.
- `supplier_code` và `quotation_date` lấy đúng từ `package.json` nếu có, hoặc để null không fail nếu khuyết.
- `draft_item_id` unique và deterministic.
- Không silently drop bất kỳ item candidate nào.
- Trạng thái `auto_ready`, `needs_review` và `rejected_candidate` phân loại chính xác theo rule.
- Không mặc định `quantity = 1` hay `VND` khi không có bằng chứng.
- Tự động tính toán `amount = quantity * unit_price` và validate so khớp, phát ra cảnh báo `amount_mismatch_recomputed` khi lệch.
- Ghi đè protection hoạt động đúng.
- CLI chạy thành công.
- Đảm bảo tính tương thích ngược cho gói chưa chạy Phase 9.
- Kiểm duyệt SHA256 của `normalized.json` không đổi khi chạy Phase 9.
- Đảm bảo Phase 9 không tự tạo `normalized.json` nếu file chưa tồn tại.

---

## Kế Hoạch Xác Minh (Verification Plan)

### Automated Tests
1. Sinh schema:
   ```bash
   python scripts/generate_schemas.py
   ```
   Kiểm tra tệp `schemas/normalized_draft.schema.json` được tạo thành công.
2. Chạy pytest:
   ```bash
   python -m pytest -v
   ```
   Mục tiêu: Đạt **~124 tests pass** (108 tests cũ + ~16 tests mới Phase 9), 0 FAILED.

### Manual Verification
1. Chạy trên gói dữ liệu thật:
   ```bash
   python -m mep_quotation.cli.main build-normalized-draft data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
2. Xác minh tệp `normalized/normalized_draft.json` được tạo thành công với cấu trúc JSON nháp chuẩn xác.
3. Xác minh tệp `normalized/normalized.json` (nếu có từ trước) không bị thay đổi nội dung (SHA256 giữ nguyên).
4. Kiểm duyệt package hợp lệ.
