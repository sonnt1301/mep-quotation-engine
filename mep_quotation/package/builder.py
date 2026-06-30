from pathlib import Path
from datetime import datetime, timezone
from mep_quotation.package.paths import generate_quotation_id, get_package_dir, get_next_sequence
from mep_quotation.package.writer import write_json_file
from mep_quotation.spec.models import (
    QuotationPackageModel,
    SupplierModel,
    VersionMetadataModel,
    FilePathsModel,
    NormalizedQuotationModel,
    CorrectionsFileModel
)

def create_empty_package(data_root: Path, supplier_code: str, date_str: str, seq: int = None) -> Path:
    """Khởi tạo một package báo giá mới rỗng với đầy đủ cấu trúc thư mục và các file mặc định."""
    data_root = Path(data_root)
    supplier_code = supplier_code.upper()
    
    # 1. Tìm sequence nếu không chỉ định
    if seq is None:
        seq = get_next_sequence(data_root, supplier_code, date_str)
        
    # 2. Tính toán đường dẫn thư mục và Quotation ID
    package_dir = get_package_dir(data_root, supplier_code, date_str, seq)
    if package_dir.exists():
        raise ValueError(f"Package directory already exists: {package_dir}. Overwrite is not allowed.")
    quotation_id = generate_quotation_id(supplier_code, date_str, seq)
    
    # 3. Tạo các thư mục con
    (package_dir / "source").mkdir(parents=True, exist_ok=True)
    (package_dir / "parsed").mkdir(parents=True, exist_ok=True)
    (package_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (package_dir / "corrections").mkdir(parents=True, exist_ok=True)
    (package_dir / "logs").mkdir(parents=True, exist_ok=True)
    (package_dir / "text").mkdir(parents=True, exist_ok=True)
    
    # 4. Tạo đối tượng package.json
    now = datetime.now(timezone.utc)
    package_model = QuotationPackageModel(
        quotation_id=quotation_id,
        supplier=SupplierModel(code=supplier_code, name=supplier_code),
        quotation_date=date_str,
        sequence=seq,
        versions=VersionMetadataModel(),
        files=FilePathsModel(
            source_pdf="source/original.pdf",
            pdf_metadata="source/metadata.json",
            page_manifest="source/page_manifest.json",
            raw_text="source/raw_text.json",
            text_markdown="text/quotation.md",
            text_manifest="text/quotation_text.json",
            line_candidates="parsed/line_candidates.json",
            parsed_json="parsed/quotation.json",
            parsed_markdown="parsed/quotation.md",
            normalized_json="normalized/normalized.json",
            corrections_json="corrections/corrections.json",
            logs_jsonl="logs/processing.log.jsonl"
        ),
        created_at=now,
        updated_at=now
    )
    
    # Ghi file package.json
    write_json_file(package_dir / "package.json", package_model)
    
    # 5. Tạo đối tượng normalized.json placeholder
    normalized_model = NormalizedQuotationModel(
        quotation_id=quotation_id,
        supplier_code=supplier_code,
        quotation_date=date_str,
        items=[]
    )
    write_json_file(package_dir / "normalized" / "normalized.json", normalized_model)
    
    # 6. Tạo đối tượng corrections.json placeholder
    corrections_model = CorrectionsFileModel(
        quotation_id=quotation_id,
        corrections=[]
    )
    write_json_file(package_dir / "corrections" / "corrections.json", corrections_model)
    
    # 7. Tạo file log rỗng logs/processing.log.jsonl
    log_file = package_dir / "logs" / "processing.log.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        pass # Tạo file rỗng
        
    return package_dir
