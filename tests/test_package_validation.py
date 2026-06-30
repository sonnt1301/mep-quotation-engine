import pytest
import json
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json, load_normalized_json, load_corrections_json
from mep_quotation.spec.validators import validate_package_data, validate_normalized_data

def test_create_and_validate_empty_package(temp_project_dir):
    data_root = temp_project_dir / "data"
    supplier = "AUT"
    date_str = "2026-05-20"
    
    # 1. Tạo package rỗng
    package_dir = create_empty_package(data_root, supplier, date_str, 1)
    
    # Kiểm tra các file mặc định tồn tại
    assert (package_dir / "package.json").exists()
    assert (package_dir / "normalized" / "normalized.json").exists()
    assert (package_dir / "corrections" / "corrections.json").exists()
    assert (package_dir / "logs" / "processing.log.jsonl").exists()
    
    # 2. Load và validate
    pkg = load_package_json(package_dir)
    assert pkg.quotation_id == "AUT_20260520_001"
    assert pkg.supplier.code == "AUT"
    
    norm = load_normalized_json(package_dir)
    assert norm.quotation_id == "AUT_20260520_001"
    assert len(norm.items) == 0
    
    corr = load_corrections_json(package_dir)
    assert corr.quotation_id == "AUT_20260520_001"
    assert len(corr.corrections) == 0

def test_create_package_duplicate_sequence(temp_project_dir):
    data_root = temp_project_dir / "data"
    supplier = "AUT"
    date_str = "2026-05-20"
    
    # Tạo lần 1 thành công
    create_empty_package(data_root, supplier, date_str, 1)
    
    # Tạo lần 2 trùng sequence -> Phải ném ValueError
    with pytest.raises(ValueError, match="already exists.*Overwrite is not allowed"):
        create_empty_package(data_root, supplier, date_str, 1)

def test_invalid_package_validation():
    # Trường hợp thiếu trường bắt buộc
    invalid_data = {
        "quotation_id": "AUT_20260520_001"
        # Thiếu supplier, files, v.v.
    }
    with pytest.raises(ValueError, match="Invalid package data"):
        validate_package_data(invalid_data)

def test_invalid_normalized_validation():
    # Trường hợp sai định dạng item_id trong normalized items
    invalid_norm = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260520_001",
        "supplier_code": "AUT",
        "quotation_date": "2026-05-20",
        "items": [
            {
                "item_id": "WRONG_ID_FORMAT",  # Sai định dạng item_id
                "material_code": "CV-3X2.5",
                "material_name": "Cáp điện",
                "category": "Electrical",
                "unit": "m",
                "unit_price": 10000,
                "vat_rate": 0.1,
                "raw_text": "CV-3X2.5",
                "evidence": {
                    "source_pdf": "source/original.pdf"
                }
            }
        ]
    }
    with pytest.raises(ValueError, match="item_id must be in format"):
        validate_normalized_data(invalid_norm)
