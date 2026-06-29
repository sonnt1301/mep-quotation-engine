import pytest
from mep_quotation.package.paths import generate_quotation_id
from mep_quotation.spec.models import QuotationPackageModel, SupplierModel, FilePathsModel

def test_generate_quotation_id():
    # Trường hợp thông thường
    qid = generate_quotation_id("AUT", "2026-05-20", 1)
    assert qid == "AUT_20260520_001"
    
    # Supplier chứa ký tự đặc biệt và chữ thường
    qid2 = generate_quotation_id("cadivi-cable", "2026-01-15", 15)
    assert qid2 == "CADIVICABLE_20260115_015"

def test_quotation_package_model_validation():
    supplier = SupplierModel(code="AUT", name="AUT Supplier")
    files = FilePathsModel(
        source_pdf="source/original.pdf",
        parsed_json="parsed/quotation.json",
        parsed_markdown="parsed/quotation.md",
        normalized_json="normalized/normalized.json",
        corrections_json="corrections/corrections.json",
        logs_jsonl="logs/processing.log.jsonl"
    )
    
    # Trường hợp đúng
    pkg = QuotationPackageModel(
        quotation_id="AUT_20260520_001",
        supplier=supplier,
        quotation_date="2026-05-20",
        sequence=1,
        files=files
    )
    assert pkg.quotation_id == "AUT_20260520_001"
    
    # Trường hợp sai: ID không khớp với date/seq/supplier
    with pytest.raises(ValueError, match="does not match expected format"):
        QuotationPackageModel(
            quotation_id="AUT_20260520_999", # Seq không khớp
            supplier=supplier,
            quotation_date="2026-05-20",
            sequence=1,
            files=files
        )
        
    # Trường hợp sai: Định dạng ngày sai
    with pytest.raises(ValueError, match="quotation_date must be in YYYY-MM-DD format"):
        QuotationPackageModel(
            quotation_id="AUT_20260520_001",
            supplier=supplier,
            quotation_date="20-05-2026", # Sai định dạng
            sequence=1,
            files=files
        )

    # Trường hợp sai: Ngày không tồn tại thực tế (như 31/02)
    with pytest.raises(ValueError, match="is not a valid date"):
        QuotationPackageModel(
            quotation_id="AUT_20260231_001",
            supplier=supplier,
            quotation_date="2026-02-31", # Ngày không hợp lệ thực tế
            sequence=1,
            files=files
        )
