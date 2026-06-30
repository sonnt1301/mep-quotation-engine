import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from mep_quotation.spec.models import PdfMetadataModel
from mep_quotation.package import (
    create_empty_package,
    get_package_dir,
    generate_quotation_id,
    load_package_json,
    write_json_file,
    get_next_sequence
)
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.pdf.validator import validate_pdf
from mep_quotation.pdf.metadata import extract_pdf_metadata

def import_pdf(
    pdf_path: Path,
    data_root: Path,
    supplier_code: str,
    quotation_date: str,
    seq: Optional[int] = None,
    max_size_mb: int = 50,
) -> Path:
    """Import tệp PDF báo giá vào hệ thống, tạo package và lưu trữ metadata."""
    pdf_path = Path(pdf_path)
    data_root = Path(data_root)
    
    # 1. Xác thực tệp PDF kỹ thuật (nếu lỗi nghiêm trọng sẽ raise exception ngay và kết thúc)
    validation_res = validate_pdf(pdf_path, max_size_mb=max_size_mb)
    
    # 2. Xác định sequence nếu chưa truyền
    if seq is None:
        seq = get_next_sequence(data_root, supplier_code, quotation_date)
        
    # 3. Kiểm tra trùng lặp thư mục package trước khi khởi tạo
    package_dir = get_package_dir(data_root, supplier_code, quotation_date, seq)
    if package_dir.exists():
        raise ValueError(
            f"Package directory already exists: {package_dir}. Overwrite is not allowed."
        )
        
    # 4. Khởi tạo package báo giá rỗng trên đĩa
    create_empty_package(data_root, supplier_code, quotation_date, seq)
    
    # Sinh Quotation ID
    quotation_id = generate_quotation_id(supplier_code, quotation_date, seq)
    
    # 5. Ghi nhận sự kiện bắt đầu import (Chỉ ghi sau khi package được tạo thành công)
    log_event(
        package_path=package_dir,
        level="INFO",
        event="pdf_import_started",
        quotation_id=quotation_id,
        details={"pdf_file_name": pdf_path.name}
    )
    
    try:
        # Ghi log sự kiện xác thực thành công
        log_event(
            package_path=package_dir,
            level="INFO",
            event="pdf_validated",
            quotation_id=quotation_id
        )
        
        # Ghi log cảnh báo tệp lớn nếu có
        has_large_pdf_warning = any(w.code == "large_pdf" for w in validation_res.warnings)
        if has_large_pdf_warning:
            log_event(
                package_path=package_dir,
                level="WARN",
                event="pdf_large_file_warning",
                quotation_id=quotation_id,
                details={"file_size_bytes": pdf_path.stat().st_size}
            )
            
        # 6. Sao chép tệp PDF gốc vào source/original.pdf
        dest_pdf_path = package_dir / "source" / "original.pdf"
        dest_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, dest_pdf_path)
        
        log_event(
            package_path=package_dir,
            level="INFO",
            event="pdf_copied",
            quotation_id=quotation_id
        )
        
        # 7. Trích xuất metadata và tính toán hash
        meta_dict = extract_pdf_metadata(pdf_path)
        sha256_val = calculate_sha256(pdf_path)
        
        # Tạo PdfMetadataModel
        pdf_metadata = PdfMetadataModel(
            schema_version="1.0",
            file_name=pdf_path.name,
            file_size=pdf_path.stat().st_size,
            sha256=sha256_val,
            page_count=meta_dict["page_count"],
            pdf_version=meta_dict["pdf_version"],
            encrypted=meta_dict["encrypted"],
            created_at=meta_dict["created_at"],
            modified_at=meta_dict["modified_at"],
            imported_at=datetime.now(timezone.utc),
            warnings=validation_res.warnings
        )
        
        # Ghi file metadata.json deterministic
        dest_meta_path = package_dir / "source" / "metadata.json"
        write_json_file(dest_meta_path, pdf_metadata, sort_keys=True)
        
        log_event(
            package_path=package_dir,
            level="INFO",
            event="pdf_metadata_written",
            quotation_id=quotation_id
        )
        
        # 8. Cập nhật package.json
        pkg = load_package_json(package_dir)
        pkg.files.pdf_metadata = "source/metadata.json"
        pkg.updated_at = datetime.now(timezone.utc)
        
        write_json_file(package_dir / "package.json", pkg, sort_keys=True)
        
        # 9. Kiểm tra toàn vẹn gói dữ liệu
        validate_package_integrity(package_dir)
        
        # 10. Ghi log sự kiện hoàn thành
        log_event(
            package_path=package_dir,
            level="INFO",
            event="pdf_import_completed",
            quotation_id=quotation_id
        )
        
    except Exception as e:
        # Nếu có lỗi phát sinh sau khi package đã được tạo, ghi event log pdf_import_failed
        log_event(
            package_path=package_dir,
            level="ERROR",
            event="pdf_import_failed",
            quotation_id=quotation_id,
            details={"error_message": str(e)}
        )
        raise e
        
    return package_dir
