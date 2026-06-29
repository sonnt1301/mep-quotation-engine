import json
from pathlib import Path
from typing import Dict, Any
from mep_quotation.spec.models import (
    QuotationPackageModel,
    NormalizedQuotationModel,
    CorrectionsFileModel
)
from mep_quotation.spec.validators import (
    validate_package_data,
    validate_normalized_data,
    validate_corrections_data
)

def load_package_json(package_path: Path) -> QuotationPackageModel:
    """Đọc và validate package.json từ thư mục package."""
    file_path = package_path / "package.json"
    if not file_path.exists():
        raise FileNotFoundError(f"package.json not found in {package_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_package_data(data)

def load_normalized_json(package_path: Path) -> NormalizedQuotationModel:
    """Đọc và validate normalized.json từ thư mục package."""
    # Lấy thông tin package.json để tìm đường dẫn tương đối của file normalized_json
    pkg = load_package_json(package_path)
    normalized_rel_path = pkg.files.normalized_json
    file_path = package_path / normalized_rel_path
    
    if not file_path.exists():
        raise FileNotFoundError(f"normalized.json not found at {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_normalized_data(data)

def load_corrections_json(package_path: Path) -> CorrectionsFileModel:
    """Đọc và validate corrections.json từ thư mục package."""
    pkg = load_package_json(package_path)
    corrections_rel_path = pkg.files.corrections_json
    file_path = package_path / corrections_rel_path
    
    if not file_path.exists():
        raise FileNotFoundError(f"corrections.json not found at {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return validate_corrections_data(data)
