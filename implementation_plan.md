# Phase 10 – Human Review / Approval Layer

## Mô tả
Phase 10 xây dựng cơ chế ghi nhận và quản lý các quyết định rà soát thủ công (Human Review Decisions) từ người dùng đối với từng ứng viên nháp chuẩn hóa (`draft item`). Đầu ra của Phase này là tệp tin `review/review_decisions.json`. 

Phase này **không** sinh tệp báo giá chính thức `normalized/normalized.json` (nhiệm vụ này thuộc về Phase 11). Phase 10 chỉ ghi nhận quyết định phê duyệt (approve), từ chối (reject) hoặc chỉnh sửa (edit) các thuộc tính và giữ trace liên kết đến draft item gốc.

## Nguyên tắc bảo vệ dữ liệu và an toàn
- **Không tự ý tạo/sửa normalized.json hoặc normalized_draft.json**: Phase 10 chỉ tạo mới/chỉnh sửa tệp `review/review_decisions.json` và cập nhật thông tin đường dẫn tệp này trong `package.json`. Tuyệt đối không chạm vào dữ liệu Phase 1-9.
- **Không tự cập nhật source_sha256 trong validate**: Hàm validate phải kiểm tra chéo `source_sha256` của file `normalized_draft.json` nguồn. Nếu bị lệch, hàm phải raise lỗi `source_sha256_mismatch` rõ ràng chứ không tự ý cập nhật đè.
- **Atomic Write**: Tệp `review_decisions.json` phải được ghi bằng cơ chế ghi an toàn (atomic write) nhằm tránh tạo ra file JSON hỏng khi xảy ra lỗi đột ngột giữa chừng.

## Critical Scope Guard
Phase 10 là lớp Human Review / Approval Layer, chỉ có nhiệm vụ ghi nhận và lưu trữ các quyết định phê duyệt/từ chối/chỉnh sửa của người dùng vào tệp `review/review_decisions.json`. 
- **Tuyệt đối không áp dụng decisions** để sinh ra tệp báo giá chính thức `normalized/normalized.json` trong Phase này. Việc này thuộc phạm vi của Phase 11.
- **Không sửa đổi** nội dung tệp nháp chuẩn hóa `normalized/normalized_draft.json`.
- **Không sửa đổi** bất kỳ artifact nào của Phase 1-9 (ngoại trừ việc cập nhật trường metadata `file_paths.review_decisions` trong `package.json`).
- **Không có bất kỳ function hay CLI command nào** trong Phase 10 thực hiện sinh normalized output chính thức.


---

## Chi Tiết Các Thay Đổi (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- Cập nhật `FilePathsModel` bổ sung:
  ```python
  review_decisions: Optional[str] = Field("review/review_decisions.json", description="Đường dẫn file quyết định review JSON, tương đối từ package root")
  ```
- Định nghĩa các Pydantic models mới ở cuối file (sử dụng cấu hình cấm thuộc tính thừa `extra="forbid"`):
  ```python
  class ReviewFieldOverridesModel(BaseModel):
      model_config = ConfigDict(extra="forbid")

      material_code: Optional[str] = Field(None, description="Mã vật tư ghi đè")
      description: Optional[str] = Field(None, description="Mô tả vật tư ghi đè")
      brand: Optional[str] = Field(None, description="Thương hiệu ghi đè")
      unit: Optional[str] = Field(None, description="Đơn vị tính ghi đè")
      quantity: Optional[float] = Field(None, description="Số lượng ghi đè")
      unit_price: Optional[float] = Field(None, description="Đơn giá ghi đè")
      currency: Optional[str] = Field(None, description="Đơn vị tiền tệ ghi đè")
      amount: Optional[float] = Field(None, description="Thành tiền ghi đè")

  class ReviewDecisionModel(BaseModel):
      model_config = ConfigDict(extra="forbid")

      decision_id: str = Field(..., description="ID quyết định định dạng {QUOTATION_ID}_REVIEW_{SEQ}")
      draft_item_id: str = Field(..., description="ID draft item liên kết từ Phase 9")
      decision_type: str = Field(..., description="Loại quyết định (approved | rejected | edited)")
      reviewer: str = Field("human", description="Người thực hiện rà soát dòng này")
      reason: Optional[str] = Field(None, description="Lý do phê duyệt/từ chối/chỉnh sửa")
      field_overrides: Optional[ReviewFieldOverridesModel] = Field(None, description="Các trường dữ liệu ghi đè khi decision_type = edited")
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("created_at")
      def serialize_created_at(self, dt: datetime) -> str:
          return serialize_dt(dt)

      @field_serializer("updated_at")
      def serialize_updated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)

  class ReviewDecisionsFileModel(BaseModel):
      model_config = ConfigDict(extra="forbid")

      schema_version: str = Field("1.0", description="Phiên bản schema")
      quotation_id: str = Field(..., description="ID báo giá liên kết")
      source_normalized_draft: str = Field("normalized/normalized_draft.json", description="Đường dẫn tương đối tới file normalized_draft")
      source_sha256: str = Field(..., description="SHA256 của file normalized/normalized_draft.json")
      reviewer: str = Field("human", description="Reviewer mặc định cấp độ file")
      decision_count: int = Field(..., description="Tổng số quyết định hiện có")
      decisions: List[ReviewDecisionModel] = Field(..., description="Danh sách các quyết định review chi tiết")
      warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

      @field_serializer("created_at")
      def serialize_created_at(self, dt: datetime) -> str:
          return serialize_dt(dt)

      @field_serializer("updated_at")
      def serialize_updated_at(self, dt: datetime) -> str:
          return serialize_dt(dt)
  ```

#### [MODIFY] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Xuất thêm: `ReviewFieldOverridesModel`, `ReviewDecisionModel`, `ReviewDecisionsFileModel`.

---

### Component 2 – Package Builder & Integrity

#### [MODIFY] [builder.py (D:/mep_quotation_pipeline/mep_quotation/package/builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/builder.py)
- Khởi tạo mặc định `review_decisions="review/review_decisions.json"` trong `FilePathsModel`.

#### [MODIFY] [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Tích hợp kiểm duyệt toàn vẹn Phase 10:
  - Nếu tệp `review/review_decisions.json` tồn tại thực tế trên đĩa, gọi validate `validate_review_decisions_file(review_decisions_file, package_path)`.

---

### Component 3 – Module review (MỚI)

#### [NEW] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/review/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/__init__.py)
- Export API: `validate_review_decisions_file`, `write_review_decisions`, `load_review_decisions`, `create_empty_review_file`, `record_review_decision`, `list_review_decisions`, `ReviewFieldOverridesModel`, `ReviewDecisionModel`, `ReviewDecisionsFileModel`.

#### [NEW] [decisions.py (D:/mep_quotation_pipeline/mep_quotation/review/decisions.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/decisions.py)
Triển khai các hàm nghiệp vụ chính:
1. `write_review_decisions(path, data)`:
   - Sử dụng atomic write: Ghi dữ liệu vào file tạm thời `.tmp` trong cùng thư mục và sau đó đổi tên (`os.replace`) để thay thế file gốc. Việc này đảm bảo file JSON không bị hỏng nửa chừng nếu xảy ra sự cố đột ngột. Ghi định dạng deterministic JSON (indent=2, sort_keys=True).
2. `load_review_decisions(path)`:
   - Đọc và trả về `ReviewDecisionsFileModel`.
3. `validate_review_decisions_file(review_file_path, package_path)`:
   - `quotation_id` khớp `package.json`.
   - `source_normalized_draft` và `source_sha256` khớp SHA256 thực tế của `normalized/normalized_draft.json`. Nếu không khớp -> ném lỗi `ValueError` có thông báo `source_sha256_mismatch` rõ ràng. Không tự cập nhật đè.
   - `decision_count == len(decisions)`.
   - `decision_id` duy nhất và đúng định dạng `{QUOTATION_ID}_REVIEW_{SEQ}`.
   - `draft_item_id` tồn tại thực tế trong `normalized_draft.json` và không bị trùng lặp record trong file decisions.
   - Quy tắc kiểm duyệt từng loại quyết định:
     - **approved**: `field_overrides` phải là null.
     - **rejected**: `field_overrides` phải là null. `reason` bắt buộc khác null và không được rỗng sau trim.
     - **edited**: `field_overrides` bắt buộc khác null và có ít nhất một trường phi-null. `reason` bắt buộc khác null và không được rỗng sau trim.
     - Kiểm duyệt giá trị override cho **edited**: `quantity`, `unit_price`, `amount` phải $\ge 0$. `description` và `unit` không rỗng sau trim. `currency` phải thuộc danh sách VND, USD hoặc null.
   - Đảm bảo hàm không tự tạo mới hoặc chỉnh sửa `normalized.json` hay `normalized_draft.json`.

#### [NEW] [review_service.py (D:/mep_quotation_pipeline/mep_quotation/review/review_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/review/review_service.py)
Triển khai logic nghiệp vụ ghi nhận quyết định:
1. `create_empty_review_file(package_path, reviewer, overwrite) -> Path`:
   - Load package.json, tính toán `source_sha256` của `normalized_draft.json` hiện tại.
   - Tạo thư mục `review/` nếu chưa có.
   - Nếu tệp đã có và `overwrite=False` -> ném lỗi `ValueError`.
   - Ghi file review rỗng (`decisions = []`, `decision_count = 0`), ghi log audit `review_file_created` (đưa tham số `overwrite` vào details).
   - Cập nhật đường dẫn `review_decisions` trong `package.json` và gọi validate package.
2. `record_review_decision(package_path, draft_item_id, decision_type, reviewer, reason, field_overrides, overwrite) -> Path`:
   - Kiểm tra tệp review đã có chưa, nếu chưa có -> tự động gọi `create_empty_review_file`.
   - Load `ReviewDecisionsFileModel` hiện tại.
   - Kiểm thử `draft_item_id` tồn tại thực tế trong `normalized_draft.json`.
     - Nếu đã có và `overwrite=True` -> Thay thế decision cũ: giữ nguyên `decision_id` cũ, `created_at` cũ. Cập nhật `reviewer` theo reviewer mới được truyền vào. Cập nhật `decision_type` / `reason` / `field_overrides` theo dữ liệu mới. Cập nhật `updated_at` mới, và ghi audit event `review_decision_replaced`.
     - Nếu chưa có -> Tính toán sequence ID tăng dần theo quy tắc: `max(seq) + 1` (parse từ các `decision_id` hiện tại, nếu chưa có thì bắt đầu bằng 1). Tạo `decision_id` mới dạng `{QUOTATION_ID}_REVIEW_{seq:04d}` và ghi audit event `review_decision_recorded`.
   - Thực hiện validate cấu trúc dữ liệu theo đúng rule (reason trim, quantity/unit_price/amount phi-âm, currency VND/USD/null) trước khi ghi file.
   - Thực hiện atomic write và cập nhật `updated_at` cấp manifest.
   - Cập nhật đường dẫn trong `package.json` nếu cần, sau đó chạy validate toàn vẹn package.
3. `list_review_decisions(package_path) -> ReviewDecisionsFileModel`:
   - Đọc và trả về danh sách quyết định.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
Tích hợp 3 subcommand mới:
1. `create-review-file <package_path> [--reviewer human] [--overwrite]`:
   - Tạo file review rỗng.
2. `record-review <package_path> --draft-item-id <id> --decision <approved|rejected|edited> [--reviewer human] [--reason "..." ] [--overwrite] [overrides]`:
   - Tham số overrides: `--material-code`, `--description`, `--brand`, `--unit`, `--quantity`, `--unit-price`, `--currency`, `--amount`.
   - Chuẩn hóa currency: vnd/usd -> VND/USD trước khi validate.
   - Ràng buộc: validate enum decision trước khi ghi file.
3. `list-review <package_path>`:
   - In thống kê: quotation_id, decision_count, approved_count, rejected_count, edited_count, review file path.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py (D:/mep_quotation_pipeline/scripts/generate_schemas.py)](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Đăng ký sinh schema `review_decisions.schema.json` từ model `ReviewDecisionsFileModel`.

---

### Component 6 – Tests

#### [NEW] [tests/test_review_decisions.py (D:/mep_quotation_pipeline/tests/test_review_decisions.py)](file:///D:/mep_quotation_pipeline/tests/test_review_decisions.py)
Bao phủ các kịch bản kiểm thử:
- Tạo review file rỗng thành công, cản ghi đè khi `overwrite=False`, cho phép khi `overwrite=True` và sinh timestamps mới.
- Ghi nhận quyết định `approved` thành công, cấm có overrides.
- Ghi nhận quyết định `rejected` thành công, lý do bắt buộc, cấm rỗng sau trim, cấm có overrides.
- Ghi nhận quyết định `edited` thành công, lý do bắt buộc, đòi hỏi ít nhất một trường override phi-null, kiểm duyệt dữ liệu không âm, currency thuộc VND/USD/null.
- Tự động chuẩn hóa currency `vnd`/`usd` thành `VND`/`USD`.
- Đảm bảo cấm duplicate `draft_item_id` nếu `overwrite=False`. Cho phép thay thế giữ nguyên ID/created_at cũ, đồng thời cập nhật reviewer mới và updated_at mới khi `overwrite=True`.
- Validate logic tính toán ID sequence tăng tiến `max(seq) + 1` không bị phụ thuộc vào số lượng phần tử `len(decisions)`.
- Kiểm duyệt SHA256 chéo: validate lỗi `source_sha256_mismatch` nếu `normalized_draft.json` thay đổi, không tự động cập nhật đè.
- CLI subcommands chạy hoàn hảo.
- Đảm bảo tính tương thích ngược cho gói chưa chạy Phase 10.
- Bảo đảm Phase 10 không chạm/chỉnh sửa tệp `normalized_draft.json` và `normalized.json`.
- Kiểm tra tính năng atomic write hoạt động chính xác (mô phỏng lỗi ghi file giữa chừng và đảm bảo file cũ vẫn nguyên vẹn).

---

## Kế Hoạch Xác Minh (Verification Plan)

### Automated Tests
1. Sinh schema:
   ```bash
   python scripts/generate_schemas.py
   ```
   Kiểm tra tệp `schemas/review_decisions.schema.json` được tạo thành công.
2. Chạy pytest:
   ```bash
   python -m pytest -v
   ```
   Mục tiêu: Đạt **~140 tests pass** (115 tests cũ + ~25 tests mới Phase 10), 0 FAILED.

### Manual Verification
1. Khởi tạo file review:
   ```bash
   python -m mep_quotation.cli.main create-review-file data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
2. Thử ghi nhận quyết định `approved` cho item 1:
   ```bash
   python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0001 --decision approved
   ```
3. Thử ghi nhận quyết định `rejected` cho item 2 (phải có reason):
   ```bash
   python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0002 --decision rejected --reason "Not a material line"
   ```
4. Thử ghi nhận quyết định `edited` cho item 3:
   ```bash
   python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0003 --decision edited --description "Ống nhựa HDPE D25" --quantity 15 --reason "Manual adjustment"
   ```
5. Đọc thống kê review:
   ```bash
   python -m mep_quotation.cli.main list-review data/suppliers/AUT/2026/2026-06-20_001
   ```
6. Chạy `validate-package` để xác nhận gói dữ liệu hoàn toàn hợp lệ, không có cảnh báo sai lệch nào.
