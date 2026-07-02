# Phase 11 – Official Normalized Export Layer

## Mô tả
Phase 11 có nhiệm vụ nhận đầu vào từ tệp nháp chuẩn hóa `normalized/normalized_draft.json` và tệp quyết định rà soát `review/review_decisions.json` để tạo ra tệp báo giá chuẩn hóa chính thức `normalized/normalized.json`. 

Đây là giai đoạn đầu tiên được phép tạo/ghi đè có kiểm soát tệp `normalized/normalized.json` chính thức trong toàn bộ pipeline.

## Critical Scope Guard
- **Không tự động duyệt**: Tuyệt đối không tự động duyệt (auto-approve) các draft items chưa được review. Chỉ xuất bản các item có decision hợp lệ (`approved` hoặc `edited`).
- **Không sửa đổi nguồn**: Không chỉnh sửa các tệp `normalized_draft.json`, `review_decisions.json`, hay bất kỳ dữ liệu trung gian nào của các Phase trước.
- **Không làm ngoài scope**: Không tích hợp OCR, AI/LLM, Excel export, Docling, database, summary file phụ, hay tính năng so sánh BOQ trong Phase này.

---

## Vị Trí Trong Pipeline
```
[Normalized Draft] + [Review Decisions] 
       ↓ (Phase 11 - exporter.py / export_service.py)
[Official Normalized JSON (normalized.json)]
```

---

## Chi Tiết Các Thay Đổi (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- **Mở rộng `NormalizedItemModel`** để lưu trữ thông tin truy vết và rà soát của Phase 11. Các trường bắt buộc mới của Phase 11 được enforce trực tiếp ở model-level (Pydantic), đồng thời giữ tương thích ngược bằng cách chuyển các trường Phase 1 cũ thành `Optional` với giá trị mặc định là `None`:
  - Cập nhật regex validate `item_id` chấp nhận cả định dạng `{QUOTATION_ID}_{SEQ}` và `{QUOTATION_ID}_ITEM_{SEQ}`: `r"^.+_\d{4}\d{2}\d{2}_\d{3}_(ITEM_)?\d{4}$"`.
  - Thiết lập bắt buộc (enforce) các trường:
    ```python
    item_id: str = Field(..., description="ID dòng vật tư")
    source_draft_item_id: str = Field(..., description="ID draft item tương ứng")
    source_review_decision_id: str = Field(..., description="ID quyết định review tương ứng")
    description: str = Field(..., description="Mô tả chuẩn của vật tư (enforced non-empty)")
    unit_price: float = Field(..., description="Đơn giá")
    currency: str = Field(..., description="Đơn vị tiền tệ (uppercase: VND, USD)")
    ```
  - Chuyển các trường Phase 1 cũ thành Optional (tương thích ngược):
    ```python
    material_code: Optional[str] = Field(None, description="Mã vật tư chuẩn")
    material_name: Optional[str] = Field(None, description="Tên vật tư")
    category: Optional[str] = Field(None, description="Phân loại vật tư")
    raw_text: Optional[str] = Field(None, description="Đoạn text gốc trích xuất từ PDF")
    evidence: Optional[EvidenceModel] = Field(None, description="Minh chứng trích xuất")
    vat_rate: Optional[float] = Field(0.1, description="Thuế suất VAT")
    ```
  - Thêm các trường tùy chọn mới của Phase 11:
    ```python
    brand: Optional[str] = Field(None, description="Thương hiệu")
    unit: Optional[str] = Field(None, description="Đơn vị tính")
    quantity: Optional[float] = Field(None, description="Số lượng vật tư")
    amount: Optional[float] = Field(None, description="Thành tiền đã được tính toán lại")
    page_number: Optional[int] = Field(None, description="Số trang chứa vật tư (1-indexed)")
    evidence_text: Optional[str] = Field(None, description="Đoạn văn bản chứa minh chứng gốc")
    confidence: Optional[float] = Field(None, description="Độ tin cậy của dòng")
    reviewer: Optional[str] = Field(None, description="Reviewer thực hiện dòng này")
    warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách các cảnh báo item-level")
    ```

- **Định nghĩa model mới `ExportSummaryModel`**:
  ```python
  class ExportSummaryModel(BaseModel):
      model_config = ConfigDict(extra="forbid")

      draft_item_count: int = Field(..., description="Tổng số draft items đầu vào")
      approved_count: int = Field(..., description="Số lượng items được approved")
      edited_count: int = Field(..., description="Số lượng items được edited")
      rejected_count: int = Field(..., description="Số lượng items bị rejected")
      unreviewed_count: int = Field(..., description="Số lượng items chưa được review")
      exported_item_count: int = Field(..., description="Số lượng items thực tế xuất bản")
  ```

- **Mở rộng `NormalizedQuotationModel`** để chứa thông tin manifest xuất bản chính thức:
  - Thêm các trường:
    ```python
    source_normalized_draft: Optional[str] = Field("normalized/normalized_draft.json", description="Đường dẫn file draft")
    source_normalized_draft_sha256: Optional[str] = Field(None, description="SHA256 của file draft")
    source_review_decisions: Optional[str] = Field("review/review_decisions.json", description="Đường dẫn file decisions")
    source_review_decisions_sha256: Optional[str] = Field(None, description="SHA256 của file decisions")
    item_count: int = Field(0, description="Số lượng item xuất bản")
    export_summary: Optional[ExportSummaryModel] = Field(None, description="Thống kê xuất bản")
    warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách cảnh báo file-level")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ```
  - Cập nhật field serializers cho `created_at` và `updated_at`.

#### [MODIFY] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Export thêm `ExportSummaryModel`.

---

### Component 2 – Module normalized_export (MỚI)

#### [NEW] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/__init__.py)
- Xuất các API: `build_official_normalized`, `export_normalized`.

#### [NEW] [exporter.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/exporter.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/exporter.py)
Triển khai logic pure function:
`build_official_normalized(package: QuotationPackageModel, normalized_draft: NormalizedDraftModel, review_decisions: ReviewDecisionsFileModel) -> NormalizedQuotationModel`
- **Lọc và sắp xếp**:
  - Chỉ duyệt qua các draft items theo đúng thứ tự xuất hiện trong `normalized_draft.json`.
  - Đối chiếu quyết định trong `review_decisions.json` dựa trên `draft_item_id`.
  - Quyết định `approved`: Lấy toàn bộ giá trị thuộc tính từ draft item.
  - Quyết định `edited`: Lấy giá trị gốc từ draft item, sau đó áp dụng đè các trường phi-null từ `field_overrides`. (Chú ý: override = null nghĩa là giữ nguyên giá trị gốc, không xóa giá trị gốc).
  - Quyết định `rejected` hoặc chưa được review: Bỏ qua (không đưa vào danh sách xuất bản).
- **Quy tắc gán ID**:
  - Gán `item_id` tuần tự tăng dần: `{QUOTATION_ID}_ITEM_{SEQ:04d}` (SEQ bắt đầu từ 0001).
- **Quy tắc tính toán thành tiền (Amount Rule)**:
  - Nếu cả `quantity` và `unit_price` khác null $\rightarrow$ luôn tính lại `amount = quantity * unit_price`. Nếu giá trị override khác kết quả tính lại $\rightarrow$ dùng kết quả tính lại và ghi nhận item-level warning `amount_recomputed_from_quantity_and_unit_price`.
  - Nếu `quantity` hoặc `unit_price` bị null $\rightarrow$ dùng `amount` override nếu có, nếu không thì gán `amount = null`.
- **Quy tắc đơn vị tiền tệ (Currency Rule)**:
  - Lấy currency sau khi apply override (nếu có) và chuẩn hóa thành chữ in hoa (uppercase).
  - Nếu item-level currency bị null $\rightarrow$ kế thừa quotation-level currency từ `normalized_draft` (nếu hợp lệ) và ghi nhận item-level warning `currency_inherited_from_quotation`.
  - Nếu cả hai đều null hoặc currency sau chuẩn hóa không thuộc `VND`/`USD` $\rightarrow$ ném lỗi `ValueError` dừng tiến trình.
- **Quy tắc thuộc tính bắt buộc (Required Fields)**:
  - Mỗi item xuất bản bắt buộc phải có `description` (phi-rỗng sau trim), `unit_price` phi-null, và `currency` phi-null. Nếu thiếu $\rightarrow$ ném lỗi `ValueError` chi tiết yêu cầu người dùng cập nhật lại review.
- **Thống kê tóm tắt (Summary & Warning)**:
  - Đếm chi tiết số lượng draft, approved, edited, rejected, unreviewed để điền vào `export_summary`.
  - Nếu không có item nào được approved/edited $\rightarrow$ trả về `items = []` và chèn file-level warning `no_approved_or_edited_items`.

#### [NEW] [export_service.py (D:/mep_quotation_pipeline/mep_quotation/normalized_export/export_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/normalized_export/export_service.py)
Triển khai logic điều phối dịch vụ ghi file:
`export_normalized(package_path: Path, overwrite: bool = False) -> Path`
- Nạp `package.json`, `normalized/normalized_draft.json`, và `review/review_decisions.json`.
- Kiểm định chéo chữ ký băm: gọi hàm validate `validate_review_decisions_file` để kiểm tra tính hợp lệ của tệp review. Kiểm tra `source_sha256` trong tệp review khớp chuẩn xác SHA256 thực tế của `normalized_draft.json`. Nếu không khớp $\rightarrow$ ném lỗi dừng ngay lập tức.
- Kiểm tra tồn tại tệp `normalized/normalized.json`:
  - Nếu đã tồn tại và `overwrite=False` $\rightarrow$ raise lỗi `ValueError`.
  - Nếu `overwrite=True` $\rightarrow$ thực hiện rebuild hoàn toàn từ dữ liệu draft và review hiện hành, không merge dữ liệu cũ.
- Thực hiện build model `NormalizedQuotationModel` sử dụng hàm `build_official_normalized`. Tính toán và điền SHA256 của cả 2 tệp đầu vào vào `source_normalized_draft_sha256` và `source_review_decisions_sha256`.
- **Atomic Write**:
  - Ghi dữ liệu ra tệp tạm thời `.tmp` trong thư mục `normalized/`.
  - Đổi tên nguyên tử (`os.replace`) để ghi đè tệp `normalized.json`.
- Cập nhật đường dẫn `normalized_json` trong `package.json` nếu cần và ghi lại package.
- Chạy validate package chéo: gọi `validate_package_integrity` xác nhận toàn gói hợp lệ.
- Ghi nhận Audit logs đầy đủ: `normalized_export_started`, `normalized_export_built`, `normalized_export_written`, `normalized_export_completed` / `normalized_export_failed`.

---

### Component 3 – Package Integrity

#### [MODIFY] [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Cập nhật hàm `validate_package_integrity` thực hiện kiểm định sâu đối với tệp `normalized.json` chính thức (chỉ chạy khi file tồn tại trên đĩa để giữ tính tương thích ngược với các gói Phase trước):
  - `quotation_id`, `supplier_code`, `quotation_date` khớp manifest.
  - Các source hashes khớp chuẩn xác `normalized_draft.json` và `review_decisions.json` thực tế nếu model có lưu.
  - `item_count == len(items)`.
  - `export_summary.exported_item_count == len(items)`.
  - `item_id` duy nhất và đúng định dạng.
  - `amount == quantity * unit_price` nếu có đủ dữ liệu.
  - Cấm chứa bất kỳ item nào tương ứng với quyết định `rejected` hoặc draft item chưa được review.

---

### Component 4 – CLI Integration

#### [MODIFY] [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Đăng ký subcommand mới:
  `export-normalized <package_path> [--overwrite]`
- In ra màn hình các thông số nghiệm thu: quotation_id, supplier_code, quotation_date, normalized path, item_count, approved_count, edited_count, rejected_count, unreviewed_count, warnings count.

---

### Component 5 – Schema Generation

#### [MODIFY] [generate_schemas.py (D:/mep_quotation_pipeline/scripts/generate_schemas.py)](file:///D:/mep_quotation_pipeline/scripts/generate_schemas.py)
- Tự động kiểm tra và sinh lại tệp `normalized.schema.json` từ `NormalizedQuotationModel` đã cập nhật.

---

### Component 6 – Tests

#### [NEW] [tests/test_normalized_export.py (D:/mep_quotation_pipeline/tests/test_normalized_export.py)](file:///D:/mep_quotation_pipeline/tests/test_normalized_export.py)
Bao phủ toàn bộ các kịch bản kiểm thử:
- Export thành công từ approved decision và edited decision có áp dụng overrides đúng đắn.
- Loại bỏ rejected decision và unreviewed draft items ra khỏi danh sách xuất bản.
- Trường hợp không có items nào được duyệt: sinh tệp `normalized.json` có `items = []` và chèn warning `no_approved_or_edited_items`.
- Validation dừng báo lỗi khi thiếu các trường bắt buộc (thiếu description, thiếu unit_price).
- Kế thừa quotation-level currency và chèn warning `currency_inherited_from_quotation`.
- Ném lỗi khi thiếu cả hai currency hoặc currency không hợp lệ.
- Override null không xóa giá trị gốc.
- Tính toán thành tiền `amount` chính xác và chèn warning `amount_recomputed_from_quantity_and_unit_price` when there is difference.
- Sử dụng amount override khi thiếu quantity hoặc unit_price.
- Tự động uppercase currency chữ thường.
- Sắp xếp items theo thứ tự trong draft.
- Trace ngược ID và lưu hashes đúng đắn.
- Cản ghi đè khi `overwrite=False`, cho phép ghi đè hoàn toàn khi `overwrite=True`.
- Atomic write hoạt động tốt.
- CLI subcommand chạy hoàn hảo.
- Xác nhận các audit logs được ghi nhận.
- Đảm bảo Phase 11 không thay đổi bất kỳ file nguồn nào của Phase trước.

---

## Kế Hoạch Xác Thực (Verification Plan)

### Automated Tests
- Chạy cập nhật schema:
  ```bash
  python scripts/generate_schemas.py
  ```
- Chạy toàn bộ suite pytest:
  ```bash
  python -m pytest -v
  ```

### Manual Verification
- Chạy thử xuất bản trên gói thực tế:
  ```bash
  python -m mep_quotation.cli.main export-normalized data/suppliers/AUT/2026/2026-06-20_001 --overwrite
  ```
- Kiểm duyệt tệp `normalized/normalized.json` kết quả và chạy kiểm tra toàn gói:
  ```bash
  python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
  ```
- Rà soát log audit và đảm bảo các tệp Phase 10 giữ nguyên vẹn.
