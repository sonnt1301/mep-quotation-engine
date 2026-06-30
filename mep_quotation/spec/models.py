from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_serializer, model_validator
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
    parsed_json: str = Field(..., description="Đường dẫn file JSON thô parsed, tương đối")
    parsed_markdown: str = Field(..., description="Đường dẫn file Markdown parsed, tương đối")
    normalized_json: str = Field(..., description="Đường dẫn file normalized JSON, tương đối")
    corrections_json: str = Field(..., description="Đường dẫn file corrections JSON, tương đối")
    logs_jsonl: str = Field(..., description="Đường dẫn file nhật ký log JSONL, tương đối")

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

class NormalizedItemModel(BaseModel):
    item_id: str = Field(..., description="ID dòng vật tư định dạng {QUOTATION_ID}_{SEQ}")
    material_code: str = Field(..., description="Mã vật tư chuẩn")
    material_name: str = Field(..., description="Tên vật tư")
    category: str = Field(..., description="Phân loại vật tư")
    unit: str = Field(..., description="Đơn vị tính")
    unit_price: float = Field(..., description="Đơn giá")
    vat_rate: float = Field(0.1, description="Thuế suất VAT (ví dụ: 0.1 đại diện cho 10%)")
    brand: Optional[str] = Field(None, description="Thương hiệu")
    origin: Optional[str] = Field(None, description="Xuất xứ")
    raw_text: str = Field(..., description="Đoạn text gốc trích xuất từ PDF để truy vết")
    evidence: EvidenceModel = Field(..., description="Minh chứng trích xuất")

    @model_validator(mode="after")
    def validate_item_id(self):
        if not re.match(r"^.+_\d{4}\d{2}\d{2}_\d{3}_\d{4}$", self.item_id):
            raise ValueError("item_id must be in format {QUOTATION_ID}_{ITEM_SEQ} where ITEM_SEQ is 4 digits")
        return self

class NormalizedQuotationModel(BaseModel):
    schema_version: str = Field("1.0", description="Phiên bản schema normalized")
    quotation_id: str = Field(..., description="ID báo giá gốc")
    supplier_code: str = Field(..., description="Mã nhà cung cấp")
    quotation_date: str = Field(..., description="Ngày báo giá")
    currency: str = Field("VND", description="Đơn vị tiền tệ")
    items: List[NormalizedItemModel] = Field(default_factory=list, description="Danh sách vật tư đã chuẩn hóa")

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
