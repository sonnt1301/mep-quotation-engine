from pathlib import Path
from mep_quotation.package.loader import load_package_json, load_normalized_json, load_corrections_json

def validate_package_integrity(package_path: Path) -> None:
    """Kiểm tra đối chiếu tính toàn vẹn liên kết dữ liệu ở cấp độ package."""
    package_path = Path(package_path)
    
    # 1. Đọc dữ liệu từ các file trong package
    pkg = load_package_json(package_path)
    norm = load_normalized_json(package_path)
    corr = load_corrections_json(package_path)
    
    # 2. Kiểm tra normalized.quotation_id == package.quotation_id
    if norm.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"Integrity check failed: normalized.quotation_id '{norm.quotation_id}' "
            f"does not match package.quotation_id '{pkg.quotation_id}'"
        )
        
    # 3. Kiểm tra corrections.quotation_id == package.quotation_id
    if corr.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"Integrity check failed: corrections.quotation_id '{corr.quotation_id}' "
            f"does not match package.quotation_id '{pkg.quotation_id}'"
        )
        
    # 4. Kiểm tra normalized.supplier_code == package.supplier.code (không phân biệt chữ hoa thường)
    if norm.supplier_code.upper() != pkg.supplier.code.upper():
        raise ValueError(
            f"Integrity check failed: normalized.supplier_code '{norm.supplier_code}' "
            f"does not match package.supplier.code '{pkg.supplier.code}'"
        )
        
    # 5. Kiểm tra normalized.quotation_date == package.quotation_date
    if norm.quotation_date != pkg.quotation_date:
        raise ValueError(
            f"Integrity check failed: normalized.quotation_date '{norm.quotation_date}' "
            f"does not match package.quotation_date '{pkg.quotation_date}'"
        )
