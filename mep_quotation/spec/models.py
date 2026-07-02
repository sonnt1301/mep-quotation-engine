from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_serializer, model_validator, ConfigDict
import re

# Helper to serialize datetime to ISO 8601 UTC format ending with Z
def serialize_dt(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    # Ensure it formats with Z (UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

class SupplierModel(BaseModel):
    code: str = Field(..., description="Mã nhà cung cấp, ví dụ: AUT, CADIVI")
    name: str = Field(..., description="Tên nhà cung cấp")

    @model_validator(mode="after")
    def validate_code(self):
        if not self.code.isalnum():
            raise ValueError("Supplier code must be alphanumeric")
        self.code = self.code.upper()
        return self

class VersionMetadataModel(BaseModel):
    schema_version: str = Field("1.0", description="Phiên bản schema dữ liệu")
    parser_version: Optional[str] = Field(None, description="Phiên bản parser sử dụng")
    llm: Optional[str] = Field(None, description="Tên model LLM sử dụng")
    prompt_version: Optional[str] = Field(None, description="Phiên bản prompt sử dụng")
    workflow_version: str = Field("mvp_spec_v1", description="Phiên bản quy trình xử lý")

class FilePathsModel(BaseModel):
    source_pdf: str = Field(..., description="Đường dẫn file PDF gốc, tương đối từ package root")
    pdf_metadata: str = Field("source/metadata.json", description="Đường dẫn file metadata PDF, tương đối từ package root")
    page_manifest: str = Field("source/page_manifest.json", description="Đường dẫn file manifest trang PDF, tương đối từ package root")
    raw_text: str = Field("source/raw_text.json", description="Đường dẫn file raw text JSON, tương đối từ package root")
    text_markdown: str = Field("text/quotation.md", description="Đường dẫn file Markdown text assembled, tương đối từ package root")
    text_manifest: str = Field("text/quotation_text.json", description="Đường dẫn file manifest text assembly JSON, tương đối từ package root")
    line_candidates: str = Field("parsed/line_candidates.json", description="Đường dẫn file line candidates JSON, tương đối từ package root")
    row_candidates: str = Field("parsed/row_candidates.json", description="Đường dẫn file row candidates JSON, tương đối từ package root")
    item_candidates: str = Field("parsed/item_candidates.json", description="Đường dẫn file item candidates JSON, tương đối từ package root")
    parsed_json: str = Field(..., description="Đường dẫn file JSON thô parsed, tương đối")
    parsed_markdown: str = Field(..., description="Đường dẫn file Markdown parsed, tương đối")
    normalized_json: str = Field(..., description="Đường dẫn file normalized JSON, tương đối")
    normalized_draft: str = Field("normalized/normalized_draft.json", description="Đường dẫn file nháp chuẩn hóa JSON, tương đối từ package root")
    review_decisions: Optional[str] = Field("review/review_decisions.json", description="Đường dẫn file quyết định review JSON, tương đối từ package root")
    corrections_json: str = Field(..., description="Đường dẫn file corrections JSON, tương đối")
    logs_jsonl: str = Field(..., description="Đường dẫn file nhật ký log JSONL, tương đối")
    excel_export: Optional[str] = Field("exports/quotation.xlsx", description="Đường dẫn file Excel xuất bản, tương đối từ package root")
    excel_export_manifest: Optional[str] = Field("exports/export_manifest.json", description="Đường dẫn file manifest Excel xuất bản, tương đối từ package root")



class QuotationPackageModel(BaseModel):
    quotation_id: str = Field(..., description="ID báo giá định dạng {SUPPLIER}_{YYYYMMDD}_{SEQ}")
    supplier: SupplierModel = Field(..., description="Thông tin nhà cung cấp")
    quotation_date: str = Field(..., description="Ngày báo giá định dạng YYYY-MM-DD")
    sequence: int = Field(..., description="Số thứ tự trong ngày")
    versions: VersionMetadataModel = Field(default_factory=VersionMetadataModel)
    files: FilePathsModel = Field(..., description="Danh sách các file trong gói báo giá")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

    @model_validator(mode="after")
    def validate_id_and_date(self):
        # Validate quotation_date format YYYY-MM-DD
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", self.quotation_date):
            raise ValueError("quotation_date must be in YYYY-MM-DD format")
        
        try:
            datetime.strptime(self.quotation_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"quotation_date '{self.quotation_date}' is not a valid date")
        
        # Validate quotation_id format {SUPPLIER}_{YYYYMMDD}_{SEQ}
        expected_seq = f"{self.sequence:03d}"
        clean_date = self.quotation_date.replace("-", "")
        expected_id = f"{self.supplier.code}_{clean_date}_{expected_seq}"
        if self.quotation_id != expected_id:
            raise ValueError(f"quotation_id '{self.quotation_id}' does not match expected format '{expected_id}'")
        return self

class EvidenceModel(BaseModel):
    source_pdf: str = Field(..., description="Đường dẫn file PDF gốc chứa thông tin")
    page: Optional[int] = Field(None, description="Trang chứa thông tin (1-indexed)")
    bbox: Optional[List[float]] = Field(None, description="Hộp bao quanh bounding box [x0, y0, x1, y1]")
    crop_path: Optional[str] = Field(None, description="Đường dẫn ảnh cắt chứa thông tin minh chứng")

class ExportSummaryModel(BaseModel):
    """Model chứa thống kê tóm tắt kết quả xuất bản của Phase 11."""
    model_config = ConfigDict(extra="forbid")

    draft_item_count: int = Field(..., description="Tổng số draft items đầu vào")
    approved_count: int = Field(..., description="Số lượng items được approved")
    edited_count: int = Field(..., description="Số lượng items được edited")
    rejected_count: int = Field(..., description="Số lượng items bị rejected")
    unreviewed_count: int = Field(..., description="Số lượng items chưa được review")
    exported_item_count: int = Field(..., description="Số lượng items thực tế xuất bản")


class NormalizedItemModel(BaseModel):
    # Các trường bắt buộc mới của Phase 11
    item_id: str = Field(..., description="ID dòng vật tư chuẩn hóa định dạng {QUOTATION_ID}_ITEM_{SEQ}")
    source_draft_item_id: str = Field(..., description="ID draft item nguồn")
    source_review_decision_id: str = Field(..., description="ID quyết định review nguồn")
    description: str = Field(..., description="Mô tả chuẩn của vật tư (enforced non-empty)")
    unit_price: float = Field(..., description="Đơn giá vật tư")
    currency: str = Field(..., description="Đơn vị tiền tệ (uppercase: VND, USD)")

    # Các trường tùy chọn mới của Phase 11
    brand: Optional[str] = Field(None, description="Thương hiệu")
    unit: Optional[str] = Field(None, description="Đơn vị tính")
    quantity: Optional[float] = Field(None, description="Số lượng vật tư")
    amount: Optional[float] = Field(None, description="Thành tiền đã được tính toán lại")
    page_number: Optional[int] = Field(None, description="Số trang chứa vật tư (1-indexed)")
    evidence_text: Optional[str] = Field(None, description="Đoạn văn bản chứa minh chứng gốc")
    confidence: Optional[float] = Field(None, description="Độ tin cậy của dòng")
    reviewer: Optional[str] = Field(None, description="Reviewer thực hiện dòng này")
    warnings: List["ParserWarningModel"] = Field(default_factory=list, description="Danh sách các cảnh báo item-level")

    # Các trường cũ của Phase 1 chuyển thành Optional để giữ tương thích ngược
    material_code: Optional[str] = Field(None, description="Mã vật tư chuẩn")
    material_name: Optional[str] = Field(None, description="Tên vật tư")
    category: Optional[str] = Field(None, description="Phân loại vật tư")
    vat_rate: Optional[float] = Field(None, description="Thuế suất VAT")
    origin: Optional[str] = Field(None, description="Xuất xứ")
    raw_text: Optional[str] = Field(None, description="Đoạn text gốc trích xuất từ PDF để truy vết")
    evidence: Optional[EvidenceModel] = Field(None, description="Minh chứng trích xuất")

    @model_validator(mode="after")
    def validate_item_id(self):
        if not re.match(r"^.+_\d{4}\d{2}\d{2}_\d{3}_(ITEM_)?\d{4}$", self.item_id):
            raise ValueError("item_id must be in format {QUOTATION_ID}_{ITEM_SEQ} or {QUOTATION_ID}_ITEM_{ITEM_SEQ}")
        
        # Enforce description non-empty
        if not self.description.strip():
            raise ValueError("description must be a non-empty string after trim")
            
        return self


class NormalizedQuotationModel(BaseModel):
    schema_version: str = Field("1.0", description="Phiên bản schema normalized")
    quotation_id: str = Field(..., description="ID báo giá gốc")
    supplier_code: str = Field(..., description="Mã nhà cung cấp")
    quotation_date: str = Field(..., description="Ngày báo giá")
    currency: str = Field("VND", description="Đơn vị tiền tệ")
    
    # Thiết lập model config thắt chặt required fields trong JSON Schema sinh ra
    model_config = ConfigDict(
        json_schema_extra={
            "required": [
                "schema_version",
                "quotation_id",
                "supplier_code",
                "quotation_date",
                "currency",
                "source_normalized_draft",
                "source_normalized_draft_sha256",
                "source_review_decisions",
                "source_review_decisions_sha256",
                "item_count",
                "export_summary",
                "warnings",
                "items",
                "created_at",
                "updated_at"
            ]
        }
    )

    # Các trường manifest mới của Phase 11 (bắt buộc trong Schema, có default trong model để tương thích ngược)
    source_normalized_draft: str = Field("normalized/normalized_draft.json", description="Đường dẫn tương đối tới file normalized_draft")
    source_normalized_draft_sha256: str = Field("", description="SHA256 của file normalized_draft")
    source_review_decisions: str = Field("review/review_decisions.json", description="Đường dẫn tương đối tới file review_decisions")
    source_review_decisions_sha256: str = Field("", description="SHA256 của file review_decisions")
    item_count: int = Field(0, description="Số lượng items xuất bản")
    export_summary: ExportSummaryModel = Field(
        default_factory=lambda: ExportSummaryModel(
            draft_item_count=0,
            approved_count=0,
            edited_count=0,
            rejected_count=0,
            unreviewed_count=0,
            exported_item_count=0
        ),
        description="Thống kê tóm tắt xuất bản"
    )
    warnings: List["ParserWarningModel"] = Field(default_factory=list, description="Danh sách các cảnh báo file-level")
    
    items: List[NormalizedItemModel] = Field(default_factory=list, description="Danh sách vật tư đã chuẩn hóa")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Thời điểm tạo")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Thời điểm cập nhật")

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

    @field_serializer("updated_at")
    def serialize_updated_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

    @model_validator(mode="after")
    def validate_id_and_date_supplier(self):
        # 1. Validate format quotation_id: {SUPPLIER}_{YYYYMMDD}_{SEQ}
        match = re.match(r"^([A-Z0-9]+)_(\d{8})_(\d{3})$", self.quotation_id)
        if not match:
            raise ValueError(f"quotation_id '{self.quotation_id}' must match format {{SUPPLIER}}_{{YYYYMMDD}}_{{SEQ}}")
        
        supplier_in_id, date_in_id, seq_in_id = match.groups()
        
        # 2. Validate quotation_date format YYYY-MM-DD và check xem ngày có hợp lệ thực tế không
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", self.quotation_date):
            raise ValueError("quotation_date must be in YYYY-MM-DD format")
        
        try:
            datetime.strptime(self.quotation_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"quotation_date '{self.quotation_date}' is not a valid date")
            
        # 3. Validate supplier_code (sau khi clean) khớp với supplier_in_id
        clean_supplier_code = re.sub(r'[^A-Z0-9]', '', self.supplier_code.upper())
        if clean_supplier_code != supplier_in_id:
            raise ValueError(f"supplier_code '{self.supplier_code}' (cleaned: '{clean_supplier_code}') does not match supplier in quotation_id '{supplier_in_id}'")
            
        # 4. Validate quotation_date khớp với date_in_id
        clean_date = self.quotation_date.replace("-", "")
        if clean_date != date_in_id:
            raise ValueError(f"quotation_date '{self.quotation_date}' does not match date in quotation_id '{date_in_id}'")
            
        return self

class CorrectionEntryModel(BaseModel):
    correction_id: str = Field(..., description="ID chỉnh sửa dạng corr_XXX")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: str = Field("human", description="Tên người hoặc hệ thống thực hiện chỉnh sửa")
    field_path: str = Field(..., description="Đường dẫn trường dữ liệu bị chỉnh sửa, ví dụ: items[0].unit_price")
    old_value: Any = Field(..., description="Giá trị cũ trước khi sửa")
    new_value: Any = Field(..., description="Giá trị mới sau khi sửa")
    reason: str = Field(..., description="Lý do chỉnh sửa")
    correction_type: str = Field(..., description="Phân loại chỉnh sửa (ví dụ: price_update, unit_update)")

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return serialize_dt(dt)

    @model_validator(mode="after")
    def validate_correction(self):
        if not self.field_path.strip():
            raise ValueError("field_path cannot be empty")
        if not re.match(r"^corr_\d{3,}$", self.correction_id):
            raise ValueError("correction_id must be in format 'corr_XXX'")
        return self

class CorrectionsFileModel(BaseModel):
    schema_version: str = Field("1.0", description="Phiên bản schema corrections")
    quotation_id: str = Field(..., description="ID báo giá gốc")
    corrections: List[CorrectionEntryModel] = Field(default_factory=list, description="Danh sách các chỉnh sửa")

class AuditLogEntryModel(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str = Field("INFO", description="Mức độ log (INFO, WARN, ERROR)")
    event: str = Field(..., description="Tên sự kiện")
    quotation_id: str = Field(..., description="ID báo giá liên quan")
    details: Dict[str, Any] = Field(default_factory=dict, description="Các thông tin chi tiết bổ sung")

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return serialize_dt(dt)

class MaterialIndexEntryModel(BaseModel):
    quotation_id: str = Field(..., description="ID báo giá gốc")
    supplier_code: str = Field(..., description="Mã nhà cung cấp")
    quotation_date: str = Field(..., description="Ngày báo giá")
    material_name: str = Field(..., description="Tên vật tư")
    unit: str = Field(..., description="Đơn vị tính")
    unit_price: float = Field(..., description="Đơn giá")
    currency: str = Field("VND", description="Đơn vị tiền tệ")
    package_path: str = Field(..., description="Đường dẫn tương đối tới package, tính từ Project Root")
    source_path: str = Field("normalized/normalized.json", description="Đường dẫn tương đối tới file normalized.json")

class MaterialIndexFileModel(BaseModel):
    schema_version: str = Field("1.0", description="Phiên bản schema index")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    materials: Dict[str, List[MaterialIndexEntryModel]] = Field(default_factory=dict, description="Bản đồ các vật tư theo mã vật tư")

    @field_serializer("generated_at")
    def serialize_generated_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

class WarningModel(BaseModel):
    code: str = Field(..., description="Mã cảnh báo kỹ thuật")
    message: str = Field(..., description="Nội dung chi tiết cảnh báo")

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

    @field_serializer("imported_at")
    def serialize_imported_at(self, dt: datetime) -> str:
        return serialize_dt(dt)

class PdfValidationResult(BaseModel):
    is_valid: bool = Field(..., description="Kết quả validate tổng thể")
    warnings: List[WarningModel] = Field(default_factory=list, description="Danh sách cảnh báo")
    error_message: Optional[str] = Field(None, description="Thông báo lỗi chi tiết nếu không valid")

class PageImageModel(BaseModel):
    page_number: int = Field(..., description="Số trang (1-indexed)")
    image_path: str = Field(..., description="Đường dẫn tương đối tới ảnh trang từ package root")
    width: int = Field(..., description="Chiều rộng ảnh tính bằng pixels")
    height: int = Field(..., description="Chiều cao ảnh tính bằng pixels")
    rotation: int = Field(..., description="Góc xoay của trang gốc (độ)")
    sha256: str = Field(..., description="Mã băm SHA256 của file ảnh")
    file_size: int = Field(..., description="Dung lượng file ảnh tính bằng bytes")

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


class RawTextPageModel(BaseModel):
    """Model cho text thô của một trang PDF."""
    page_number: int = Field(..., description="Số trang (1-indexed)")
    has_text: bool = Field(..., description="True nếu trang có text, False nếu không")
    character_count: int = Field(..., description="Số ký tự Unicode trong text (len(text) Python)")
    text: str = Field(..., description="Text thô do engine trả về, không trim/normalize")


class RawTextManifestModel(BaseModel):
    """Model cho file raw_text.json – artifact chính của Phase 4."""
    schema_version: str = Field("1.0", description="Phiên bản schema")
    quotation_id: str = Field(..., description="ID báo giá liên kết")
    source_pdf: str = Field(..., description="Đường dẫn tương đối tới file PDF gốc")
    source_sha256: str = Field(..., description="SHA256 của file source/original.pdf")
    extraction_engine: str = Field(..., description="Tên engine dùng để extract, ví dụ: pymupdf")
    extraction_engine_version: Optional[str] = Field(None, description="Phiên bản engine, None nếu không lấy được")
    page_count: int = Field(..., description="Tổng số trang PDF")
    pages: List[RawTextPageModel] = Field(..., description="Danh sách text từng trang")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("generated_at")
    def serialize_generated_at(self, dt: datetime) -> str:
        return serialize_dt(dt)


class TextAssemblyPageModel(BaseModel):
    """Model cho thông tin lắp ghép văn bản của một trang PDF."""
    page_number: int = Field(..., description="Số trang (1-indexed)")
    has_text: bool = Field(..., description="True nếu trang có chứa ký tự văn bản")
    character_count: int = Field(..., description="Số lượng ký tự văn bản của trang gốc")
    start_offset: int = Field(..., description="Vị trí bắt đầu của text trang trong file MD (Python string index)")
    end_offset: int = Field(..., description="Vị trí kết thúc ngay sau ký tự cuối cùng của text trang trong file MD (Python string index)")


class TextAssemblyManifestModel(BaseModel):
    """Model cho file quotation_text.json – artifact chính của Phase 5."""
    schema_version: str = Field("1.0", description="Phiên bản schema")
    quotation_id: str = Field(..., description="ID báo giá liên kết")
    source_raw_text: str = Field("source/raw_text.json", description="Đường dẫn tương đối tới file raw_text.json nguồn")
    source_sha256: str = Field(..., description="SHA256 của tệp source/raw_text.json")
    page_count: int = Field(..., description="Tổng số trang")
    total_characters: int = Field(..., description="Tổng số ký tự văn bản gốc")
    pages_with_text: int = Field(..., description="Số lượng trang thực tế có chứa text")
    markdown_path: str = Field("text/quotation.md", description="Đường dẫn tương đối tới file Markdown kết quả")
    pages: List[TextAssemblyPageModel] = Field(..., description="Danh sách chi tiết offset các trang")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer("generated_at")
    def serialize_generated_at(self, dt: datetime) -> str:
        return serialize_dt(dt)


class ParserWarningModel(BaseModel):
    """Model cho cảnh báo phân tích cú pháp ở cấp độ dòng hoặc manifest."""
    code: str = Field(..., description="Mã cảnh báo (ví dụ: low_confidence, quantity_missing)")
    message: str = Field(..., description="Chi tiết nội dung cảnh báo")


class LineCandidateEvidenceModel(BaseModel):
    """Model cho thông tin bằng chứng định vị dòng trong file Markdown."""
    source_path: str = Field("text/quotation.md", description="Đường dẫn file văn bản Markdown nguồn")
    start_offset: int = Field(..., description="Vị trí bắt đầu của dòng trong file MD (Python string index)")
    end_offset: int = Field(..., description="Vị trí kết thúc ngay sau ký tự cuối của dòng trong file MD (Python string index)")
    text: str = Field(..., description="Đoạn văn bản thô nguyên bản của dòng")


class LineCandidateModel(BaseModel):
    """Model cho thông tin một dòng ứng viên chứa báo giá MEP thô."""
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
    """Model cho file line_candidates.json – artifact chính của Phase 6."""
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


class RowCandidateModel(BaseModel):
    """Model cho thông tin một dòng ứng viên ghép chứa báo giá MEP thô từ Phase 7."""
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
    """Model cho file row_candidates.json – artifact chính của Phase 7."""
    schema_version: str = Field("1.0", description="Phiên bản schema")
    quotation_id: str = Field(..., description="ID báo giá liên kết")
    source_line_candidates: str = Field("parsed/line_candidates.json", description="Đường dẫn tương đối tới file line_candidates")
    source_text_manifest: str = Field("text/quotation_text.json", description="Đường dẫn tương đối tới tệp text_manifest")
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


class ItemCandidateModel(BaseModel):
    """Model cho thông tin một ứng viên vật tư báo giá MEP từ Phase 8."""
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
    """Model cho file item_candidates.json – tệp tin kê khai ứng viên vật tư của Phase 8."""
    schema_version: str = Field("1.0", description="Phiên bản schema")
    quotation_id: str = Field(..., description="ID báo giá liên kết")
    source_row_candidates: str = Field("parsed/row_candidates.json", description="Đường dẫn tương đối tới tệp row_candidates")
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


class NormalizedDraftEvidenceModel(BaseModel):
    """Model lưu trữ trace vết chứng cứ văn bản thô cho draft item."""
    raw_evidence_text: str = Field(..., description="Văn bản gốc từ row candidate")
    start_offset: int = Field(..., description="Vị trí bắt đầu trong file MD")
    end_offset: int = Field(..., description="Vị trí kết thúc trong file MD")


class NormalizedDraftItemModel(BaseModel):
    """Model lưu trữ thông tin một dòng vật tư chuẩn hóa nháp của Phase 9."""
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
    """Model kê khai tệp normalized_draft.json chứa dữ liệu nháp chuẩn hóa."""
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


class ReviewFieldOverridesModel(BaseModel):
    """Model chứa các trường dữ liệu ghi đè khi decision_type = edited."""
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
    """Model lưu trữ một quyết định review đối với một draft item."""
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
    """Model manifest cho tệp review_decisions.json."""
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


class ExcelExportSheetModel(BaseModel):
    """Model chứa thông tin thống kê từng worksheet Excel."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Tên worksheet")
    row_count: int = Field(..., description="Số dòng dữ liệu (không tính header row)")


class ExcelExportContextModel(BaseModel):
    """Model context trung gian cho việc xuất Excel."""
    model_config = ConfigDict(extra="forbid")

    source_normalized_sha256: str = Field(..., description="SHA256 của tệp normalized.json")
    exported_at: datetime = Field(..., description="Thời điểm xuất bản")
    exporter_name: str = Field("openpyxl_excel_exporter", description="Tên bộ xuất bản")
    exporter_version: str = Field("1.0", description="Phiên bản bộ xuất bản")


class ExcelExportManifestModel(BaseModel):
    """Model manifest ghi nhận kết quả xuất bản Excel chính thức."""
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field("1.0", description="Phiên bản schema export manifest")
    quotation_id: str = Field(..., description="ID báo giá gốc")
    supplier_code: Optional[str] = Field(None, description="Mã nhà cung cấp")
    quotation_date: Optional[str] = Field(None, description="Ngày báo giá")
    source_normalized: str = Field("normalized/normalized.json", description="Đường dẫn tương đối tới file normalized")
    source_normalized_sha256: str = Field(..., description="SHA256 của file normalized")
    export_file: str = Field("exports/quotation.xlsx", description="Đường dẫn tương đối tới file Excel xuất bản")
    export_file_sha256: str = Field(..., description="SHA256 của file Excel xuất bản")
    sheet_count: int = Field(..., description="Số lượng worksheets")
    sheets: List[ExcelExportSheetModel] = Field(..., description="Danh sách chi tiết sheets")
    exported_at: datetime = Field(..., description="Thời điểm xuất bản")
    exporter_name: str = Field("openpyxl_excel_exporter", description="Tên bộ xuất bản")
    exporter_version: str = Field("1.0", description="Phiên bản bộ xuất bản")
    warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách các cảnh báo")

    @field_serializer("exported_at")
    def serialize_exported_at(self, dt: datetime) -> str:
        return serialize_dt(dt)







