import pytest
import json
from pathlib import Path
from pydantic import ValidationError

from mep_quotation.spec.models import NormalizedQuotationModel, NormalizedItemModel, EvidenceModel, ExportSummaryModel
from datetime import datetime, timezone
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.indexer.material_indexer import build_material_index

# Helper sinh dữ liệu mock NormalizedQuotationModel bắt buộc của Phase 11
def make_mock_norm_data(**kwargs):
    now = datetime.now(timezone.utc)
    base = {
        "quotation_id": "AUT_20260520_001",
        "supplier_code": "AUT",
        "quotation_date": "2026-05-20",
        "currency": "VND",
        "source_normalized_draft": "normalized/normalized_draft.json",
        "source_normalized_draft_sha256": "",
        "source_review_decisions": "review/review_decisions.json",
        "source_review_decisions_sha256": "",
        "item_count": 0,
        "export_summary": ExportSummaryModel(
            draft_item_count=0,
            approved_count=0,
            edited_count=0,
            rejected_count=0,
            unreviewed_count=0,
            exported_item_count=0
        ),
        "warnings": [],
        "items": [],
        "created_at": now,
        "updated_at": now
    }
    base.update(kwargs)
    return base

# 1. Tests cho NormalizedQuotationModel validation
def test_normalized_model_invalid_id_format():
    # Sai format quotation_id (thiếu sequence padding hoặc sai cấu trúc)
    with pytest.raises(ValidationError, match="must match format"):
        NormalizedQuotationModel(**make_mock_norm_data(quotation_id="AUT_20260520_1"))

def test_normalized_model_supplier_mismatch():
    # supplier_code lệch với supplier trong quotation_id
    with pytest.raises(ValidationError, match="does not match supplier in quotation_id"):
        NormalizedQuotationModel(**make_mock_norm_data(supplier_code="CADIVI"))

def test_normalized_model_date_mismatch():
    # quotation_date lệch với date trong quotation_id
    with pytest.raises(ValidationError, match="does not match date in quotation_id"):
        NormalizedQuotationModel(**make_mock_norm_data(quotation_date="2026-05-21"))

def test_normalized_model_invalid_date_value():
    # Ngày không tồn tại thực tế (như 31/02)
    with pytest.raises(ValidationError, match="is not a valid date"):
        NormalizedQuotationModel(**make_mock_norm_data(
            quotation_id="AUT_20260231_001",
            quotation_date="2026-02-31"
        ))

# 2. Tests cho validate_package_integrity
def test_validate_package_integrity_success(temp_project_dir):
    data_root = temp_project_dir / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Mặc định tạo package rỗng là hoàn toàn hợp lệ
    # validate_package_integrity sẽ không raise lỗi
    validate_package_integrity(package_dir)

def test_validate_package_integrity_id_mismatch(temp_project_dir):
    data_root = temp_project_dir / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Sửa đổi thủ công file normalized.json để làm lệch quotation_id so với package.json
    norm_file = package_dir / "normalized" / "normalized.json"
    with open(norm_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Tạo đối tượng Model hợp lệ nhưng ID bị đổi lệch so với package_id của AUT_20260520_001
    data["quotation_id"] = "CADIVI_20260520_001"
    data["supplier_code"] = "CADIVI"
    data["quotation_date"] = "2026-05-20"
    
    with open(norm_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    with pytest.raises(ValueError, match="normalized.quotation_id.*does not match package.quotation_id"):
        validate_package_integrity(package_dir)

def test_validate_package_integrity_corrections_id_mismatch(temp_project_dir):
    data_root = temp_project_dir / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Sửa đổi corrections.json để lệch ID
    corr_file = package_dir / "corrections" / "corrections.json"
    with open(corr_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    data["quotation_id"] = "OTHER_ID_001"
    
    with open(corr_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    with pytest.raises(ValueError, match="corrections.quotation_id.*does not match package.quotation_id"):
        validate_package_integrity(package_dir)

# 3. Tests cho build_material_index strict / non-strict modes
def test_build_index_strict_mode(temp_project_dir):
    data_root = temp_project_dir / "data"
    project_root = temp_project_dir
    
    # Tạo 1 package đúng
    pkg1 = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Tạo 1 package có file normalized.json bị lỗi cấu trúc (ghi đè bằng dữ liệu sai)
    pkg2 = create_empty_package(data_root, "CADIVI", "2026-05-20", 1)
    norm_file2 = pkg2 / "normalized" / "normalized.json"
    
    with open(norm_file2, "w", encoding="utf-8") as f:
        # Ghi đè bằng dữ liệu lỗi không thể validate Pydantic
        f.write('{"schema_version": "1.0", "quotation_id": "ERR_ID"}')
        
    # Chạy build index ở strict=True -> Phải ném lỗi Exception
    with pytest.raises(Exception):
        build_material_index(data_root, project_root, strict=True)

def test_build_index_non_strict_mode(temp_project_dir):
    data_root = temp_project_dir / "data"
    project_root = temp_project_dir
    
    # Tạo 1 package đúng
    pkg1 = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Tạo 1 package có file normalized.json bị lỗi
    pkg2 = create_empty_package(data_root, "CADIVI", "2026-05-20", 1)
    norm_file2 = pkg2 / "normalized" / "normalized.json"
    
    with open(norm_file2, "w", encoding="utf-8") as f:
        f.write('{"schema_version": "1.0", "quotation_id": "ERR_ID"}')
        
    # Chạy build index ở strict=False (mặc định) -> Trả về danh sách file lỗi
    index_file, skipped = build_material_index(data_root, project_root, strict=False)
    
    assert index_file.exists()
    assert len(skipped) == 1
    assert norm_file2 in skipped
