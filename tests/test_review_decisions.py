import json
import subprocess
import sys
from pathlib import Path
import pytest
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.review.review_service import (
    create_empty_review_file,
    record_review_decision,
    list_review_decisions
)
from mep_quotation.review.decisions import (
    validate_review_decisions_file,
    write_review_decisions
)
from mep_quotation.spec.models import ReviewFieldOverridesModel, ReviewDecisionsFileModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def package_with_normalized_draft(tmp_path):
    """Tạo một package đã đi qua Phase 9 (có normalized_draft.json và các file trước)."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    
    # original.pdf giả lập
    pdf_path = package_dir / "source" / "original.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    # metadata.json
    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": 1,
        "pdf_version": "1.4",
        "encrypted": False,
        "imported_at": "2026-06-20T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    # corrections.json
    corr_dir = package_dir / "corrections"
    corr_dir.mkdir(parents=True, exist_ok=True)
    with open(corr_dir / "corrections.json", "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "corrections": []}, f)

    # quotation.md
    md_content = "# Quotation Text\n## Page 1\nLine 1\nLine 2\n"
    md_path = package_dir / "text" / "quotation.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    # 4. Dựng quotation.md
    md_content = "mock\nmock\nmock\n"
    md_path = package_dir / "text" / "quotation.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # quotation_text.json
    raw_text_path = package_dir / "source" / "raw_text.json"
    with open(raw_text_path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_pdf": "source/original.pdf", "source_sha256": "dummy", "extraction_engine": "pymupdf", "page_count": 1, "pages": [{"page_number": 1, "has_text": True, "character_count": len(md_content), "text": md_content}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    with open(package_dir / "text" / "quotation_text.json", "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_raw_text": "source/raw_text.json", "source_sha256": calculate_sha256(raw_text_path), "page_count": 1, "total_characters": len(md_content), "pages_with_text": 1, "markdown_path": "text/quotation.md", "pages": [{"page_number": 1, "has_text": True, "character_count": len(md_content), "start_offset": 0, "end_offset": len(md_content)}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    # line_candidates.json
    line_cand_file = package_dir / "parsed" / "line_candidates.json"
    line_cand_file.parent.mkdir(parents=True, exist_ok=True)
    line_cand_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_text_manifest": "text/quotation_text.json",
        "source_markdown": "text/quotation.md",
        "source_sha256": calculate_sha256(md_path),
        "parser_name": "rule",
        "parser_version": "1.0",
        "candidate_count": 3,
        "candidates": [
            {
                "candidate_id": "AUT_20260620_001_LINECAND_0001", "page_number": 1, "line_number": 1,
                "raw_line": "mock", "confidence": 0.9, "warnings": [],
                "evidence": {"source_path": "text/quotation.md", "start_offset": 0, "end_offset": 4, "text": "mock"}
            },
            {
                "candidate_id": "AUT_20260620_001_LINECAND_0002", "page_number": 1, "line_number": 2,
                "raw_line": "mock", "confidence": 0.9, "warnings": [],
                "evidence": {"source_path": "text/quotation.md", "start_offset": 5, "end_offset": 9, "text": "mock"}
            },
            {
                "candidate_id": "AUT_20260620_001_LINECAND_0003", "page_number": 1, "line_number": 3,
                "raw_line": "mock", "confidence": 0.9, "warnings": [],
                "evidence": {"source_path": "text/quotation.md", "start_offset": 10, "end_offset": 14, "text": "mock"}
            }
        ],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(line_cand_file, "w", encoding="utf-8") as f:
        json.dump(line_cand_manifest, f)

    # row_candidates.json
    row_cand_file = package_dir / "parsed" / "row_candidates.json"
    row_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_line_candidates": "parsed/line_candidates.json",
        "source_sha256": calculate_sha256(line_cand_file),
        "source_text_manifest": "text/quotation_text.json",
        "assembler_name": "rule",
        "assembler_version": "1.0",
        "row_count": 3,
        "rows": [
            {
                "row_id": "AUT_20260620_001_ROWCAND_0001", "page_number": 1, "start_line_number": 1, "end_line_number": 2, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0001"],
                "description_candidate": "Item 1 description", "brand_candidate": "BrandA", "unit_candidate": "cái", "quantity_candidate": 10.0, "unit_price_candidate": 5000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 0, "end_offset": 4, "confidence": 0.9, "warnings": []
            },
            {
                "row_id": "AUT_20260620_001_ROWCAND_0002", "page_number": 1, "start_line_number": 2, "end_line_number": 3, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0002"],
                "description_candidate": "Item 2 description", "brand_candidate": None, "unit_candidate": "m", "quantity_candidate": 2.0, "unit_price_candidate": 10000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 5, "end_offset": 9, "confidence": 0.8, "warnings": []
            },
            {
                "row_id": "AUT_20260620_001_ROWCAND_0003", "page_number": 1, "start_line_number": 3, "end_line_number": 4, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0003"],
                "description_candidate": "Item 3 description", "brand_candidate": None, "unit_candidate": "bộ", "quantity_candidate": 5.0, "unit_price_candidate": 20000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 10, "end_offset": 14, "confidence": 0.8, "warnings": []
            }
        ],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(row_cand_file, "w", encoding="utf-8") as f:
        json.dump(row_manifest, f)

    # item_candidates.json
    item_cand_file = package_dir / "parsed" / "item_candidates.json"
    item_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_row_candidates": "parsed/row_candidates.json",
        "source_sha256": calculate_sha256(row_cand_file),
        "source_text_manifest": "text/quotation_text.json",
        "builder_name": "rule",
        "builder_version": "1.0",
        "item_count": 3,
        "items": [
            {
                "item_candidate_id": "AUT_20260620_001_ITEMCAND_0001", "source_row_id": "AUT_20260620_001_ROWCAND_0001", "page_number": 1, "start_line_number": 1, "end_line_number": 2,
                "description_candidate": "Item 1 description", "brand_candidate": "BrandA", "unit_candidate": "cái", "quantity_candidate": 10.0, "unit_price_candidate": 5000.0, "amount_candidate": 50000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 0, "end_offset": 4, "confidence": 0.9, "warnings": []
            },
            {
                "item_candidate_id": "AUT_20260620_001_ITEMCAND_0002", "source_row_id": "AUT_20260620_001_ROWCAND_0002", "page_number": 1, "start_line_number": 2, "end_line_number": 3,
                "description_candidate": "Item 2 description", "brand_candidate": None, "unit_candidate": "m", "quantity_candidate": 2.0, "unit_price_candidate": 10000.0, "amount_candidate": 20000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 5, "end_offset": 9, "confidence": 0.8, "warnings": []
            },
            {
                "item_candidate_id": "AUT_20260620_001_ITEMCAND_0003", "source_row_id": "AUT_20260620_001_ROWCAND_0003", "page_number": 1, "start_line_number": 3, "end_line_number": 4,
                "description_candidate": "Item 3 description", "brand_candidate": None, "unit_candidate": "bộ", "quantity_candidate": 5.0, "unit_price_candidate": 20000.0, "amount_candidate": 100000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 10, "end_offset": 14, "confidence": 0.8, "warnings": []
            }
        ],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(item_cand_file, "w", encoding="utf-8") as f:
        json.dump(item_manifest, f)

    # normalized_draft.json
    draft_dir = package_dir / "normalized"
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_file = draft_dir / "normalized_draft.json"
    
    draft_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "supplier_code": "AUT",
        "quotation_date": "2026-06-20",
        "currency": "VND",
        "source_item_candidates": "parsed/item_candidates.json",
        "source_sha256": calculate_sha256(item_cand_file),
        "draft_builder_name": "rule",
        "draft_builder_version": "1.0",
        "item_count": 3,
        "review_required_count": 3,
        "items": [
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0001",
                "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0001",
                "source_row_id": "AUT_20260620_001_ROWCAND_0001",
                "page_number": 1,
                "start_line_number": 1,
                "end_line_number": 2,
                "material_code": "MC-01",
                "description": "Item 1 description",
                "brand": "BrandA",
                "unit": "cái",
                "quantity": 10.0,
                "unit_price": 5000.0,
                "currency": "VND",
                "amount": 50000.0,
                "review_status": "needs_review",
                "review_reasons": ["missing_unit"],
                "confidence": 0.6,
                "warnings": [],
                "evidence": {"raw_evidence_text": "mock", "start_offset": 0, "end_offset": 4}
            },
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0002",
                "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0002",
                "source_row_id": "AUT_20260620_001_ROWCAND_0002",
                "page_number": 1,
                "start_line_number": 2,
                "end_line_number": 3,
                "description": "Item 2 description",
                "unit": "m",
                "quantity": 2.0,
                "unit_price": 10000.0,
                "currency": "VND",
                "amount": 20000.0,
                "review_status": "needs_review",
                "review_reasons": [],
                "confidence": 0.7,
                "warnings": [],
                "evidence": {"raw_evidence_text": "mock", "start_offset": 5, "end_offset": 9}
            },
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0003",
                "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0003",
                "source_row_id": "AUT_20260620_001_ROWCAND_0003",
                "page_number": 1,
                "start_line_number": 3,
                "end_line_number": 4,
                "description": "Item 3 description",
                "unit": "bộ",
                "quantity": 5.0,
                "unit_price": 20000.0,
                "currency": "VND",
                "amount": 100000.0,
                "review_status": "needs_review",
                "review_reasons": [],
                "confidence": 0.8,
                "warnings": [],
                "evidence": {"raw_evidence_text": "mock", "start_offset": 10, "end_offset": 14}
            }
        ],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(draft_data, f)

    # Đăng ký các files và lưu package.json
    pkg_json_path = package_dir / "package.json"
    pkg_model = load_package_json(package_dir)
    pkg_model.files.line_candidates = "parsed/line_candidates.json"
    pkg_model.files.row_candidates = "parsed/row_candidates.json"
    pkg_model.files.item_candidates = "parsed/item_candidates.json"
    pkg_model.files.normalized_draft = "normalized/normalized_draft.json"
    
    # Tạo normalized.json giả lập rỗng để vượt qua validate_package_integrity
    with open(package_dir / "normalized" / "normalized.json", "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "supplier_code": "AUT", "quotation_date": "2026-06-20", "items": []}, f)
        
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_create_empty_review_file(package_with_normalized_draft):
    """Kiểm thử hàm tạo review file rỗng và cản ghi đè."""
    # 1. Tạo file review rỗng lần đầu
    review_file = create_empty_review_file(package_with_normalized_draft, reviewer="human_a", overwrite=False)
    assert review_file.exists()
    
    with open(review_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["decision_count"] == 0
    assert data["decisions"] == []
    assert data["reviewer"] == "human_a"
    
    # 2. Ghi đè mà overwrite=False -> lỗi
    with pytest.raises(ValueError, match="already exists"):
        create_empty_review_file(package_with_normalized_draft, reviewer="human_b", overwrite=False)

    # 3. Ghi đè với overwrite=True -> ok
    create_empty_review_file(package_with_normalized_draft, reviewer="human_b", overwrite=True)
    with open(review_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["reviewer"] == "human_b"


def test_record_approved_decision(package_with_normalized_draft):
    """Kiểm thử ghi nhận quyết định approved thành công."""
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        reviewer="reviewer_1",
        reason="Looks perfect",
        overwrite=False
    )

    review_file = package_with_normalized_draft / "review" / "review_decisions.json"
    with open(review_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["decision_count"] == 1
    dec = data["decisions"][0]
    assert dec["decision_id"] == "AUT_20260620_001_REVIEW_0001"
    assert dec["draft_item_id"] == "AUT_20260620_001_DRAFTITEM_0001"
    assert dec["decision_type"] == "approved"
    assert dec["reviewer"] == "reviewer_1"
    assert dec["field_overrides"] is None
    assert dec["reason"] == "Looks perfect"


def test_record_rejected_decision_validation(package_with_normalized_draft):
    """Kiểm thử validation đối với quyết định rejected."""
    # 1. rejected không có reason -> lỗi
    with pytest.raises(ValueError, match="must have a non-empty reason"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="rejected",
            reason="",
            overwrite=False
        )

    # 2. rejected có reason chỉ chứa whitespace -> lỗi
    with pytest.raises(ValueError, match="must have a non-empty reason"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="rejected",
            reason="   ",
            overwrite=False
        )

    # 3. rejected có field_overrides -> lỗi
    overrides = ReviewFieldOverridesModel(description="Mock")
    with pytest.raises(ValueError, match="must not have field overrides"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="rejected",
            reason="Duplicate line",
            field_overrides=overrides,
            overwrite=False
        )


def test_record_edited_decision_validation(package_with_normalized_draft):
    """Kiểm thử validation đối với quyết định edited."""
    # 1. edited không truyền overrides -> lỗi
    with pytest.raises(ValueError, match="must have field overrides"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="edited",
            reason="Correction",
            field_overrides=None,
            overwrite=False
        )

    # 2. edited truyền overrides trống toàn bộ -> lỗi
    empty_overrides = ReviewFieldOverridesModel()
    with pytest.raises(ValueError, match="must contain at least one non-null field"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="edited",
            reason="Correction",
            field_overrides=empty_overrides,
            overwrite=False
        )

    # 3. edited truyền quantity âm -> lỗi
    bad_qty = ReviewFieldOverridesModel(quantity=-5.0)
    with pytest.raises(ValueError, match="quantity must be non-negative"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="edited",
            reason="Correction",
            field_overrides=bad_qty,
            overwrite=False
        )

    # 4. edited truyền unit rỗng -> lỗi
    bad_unit = ReviewFieldOverridesModel(unit="  ")
    with pytest.raises(ValueError, match="unit must not be empty"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="edited",
            reason="Correction",
            field_overrides=bad_unit,
            overwrite=False
        )

    # 5. edited truyền currency sai -> lỗi
    bad_currency = ReviewFieldOverridesModel(currency="EUR")
    with pytest.raises(ValueError, match="currency must be VND, USD or null"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="edited",
            reason="Correction",
            field_overrides=bad_currency,
            overwrite=False
        )


def test_duplicate_decision_and_overwrite_replacement(package_with_normalized_draft):
    """Kiểm thử cấm trùng lặp và logic thay thế (overwrite=True) cập nhật reviewer/timestamps."""
    # 1. Ghi nhận decision đầu tiên
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        reviewer="reviewer_1",
        reason="Good",
        overwrite=False
    )

    # 2. Ghi đè mà overwrite=False -> lỗi
    with pytest.raises(ValueError, match="already exists"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
            decision_type="rejected",
            reviewer="reviewer_2",
            reason="Actually bad",
            overwrite=False
        )

    # 3. Ghi đè với overwrite=True
    # Phải giữ nguyên decision_id và created_at cũ, nhưng cập nhật reviewer mới và updated_at mới
    review_file = package_with_normalized_draft / "review" / "review_decisions.json"
    with open(review_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    old_dec = old_data["decisions"][0]
    old_created = old_dec["created_at"]
    old_dec_id = old_dec["decision_id"]

    import time
    time.sleep(1.1) # để đảm bảo timestamps cập nhật khác biệt (do định dạng ISO chỉ lưu tới giây)

    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="rejected",
        reviewer="reviewer_new",  # Cập nhật reviewer mới
        reason="Actually bad",
        overwrite=True
    )

    with open(review_file, "r", encoding="utf-8") as f:
        new_data = json.load(f)
    
    new_dec = new_data["decisions"][0]
    assert new_dec["decision_id"] == old_dec_id
    assert new_dec["created_at"] == old_created
    assert new_dec["reviewer"] == "reviewer_new"
    assert new_dec["decision_type"] == "rejected"
    assert new_dec["reason"] == "Actually bad"
    assert new_dec["updated_at"] != old_dec["updated_at"]


def test_sequence_calculation_independent(package_with_normalized_draft):
    """Kiểm thử cách tính sequence ID dựa trên max(seq) chứ không dựa trên len(decisions)."""
    # 1. Ghi nhận 2 items đầu tiên -> sequence 0001, 0002
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        overwrite=False
    )
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0002",
        decision_type="approved",
        overwrite=False
    )

    # 2. Xóa đi item đầu tiên bằng cách sửa file trực tiếp (giả lập xóa record)
    review_file = package_with_normalized_draft / "review" / "review_decisions.json"
    with open(review_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert len(data["decisions"]) == 2
    # Chỉ giữ lại decision có ID _REVIEW_0002
    data["decisions"] = [d for d in data["decisions"] if "0002" in d["decision_id"]]
    data["decision_count"] = 1
    with open(review_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # 3. Ghi nhận thêm item 3. Sequence tiếp theo phải là 0003 chứ không phải 0002 (do len=1)
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0003",
        decision_type="approved",
        overwrite=False
    )

    with open(review_file, "r", encoding="utf-8") as f:
        data_after = json.load(f)

    decision_ids = [d["decision_id"] for d in data_after["decisions"]]
    assert "AUT_20260620_001_REVIEW_0003" in decision_ids
    assert "AUT_20260620_001_REVIEW_0002" in decision_ids


def test_validate_review_decisions_file_source_sha_mismatch(package_with_normalized_draft):
    """Kiểm thử hàm validate phát hiện lỗi lệch source_sha256."""
    create_empty_review_file(package_with_normalized_draft, overwrite=True)
    review_file = package_with_normalized_draft / "review" / "review_decisions.json"

    # Sửa tệp normalized_draft.json để làm lệch SHA256 thực tế
    draft_file = package_with_normalized_draft / "normalized" / "normalized_draft.json"
    with open(draft_file, "r", encoding="utf-8") as f:
        draft_data = json.load(f)
    
    draft_data["warnings"].append({"code": "low_confidence", "message": "tamper test"})
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(draft_data, f)

    # Gọi validate phải ném lỗi source_sha256_mismatch
    with pytest.raises(ValueError, match="source_sha256_mismatch"):
        validate_review_decisions_file(review_file, package_with_normalized_draft)


def test_cli_subcommands(package_with_normalized_draft):
    """Kiểm thử toàn bộ các lệnh CLI của Phase 10."""
    # 1. CLI create-review-file
    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "create-review-file", str(package_with_normalized_draft), "--reviewer", "human_cli", "--overwrite"
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully created empty review decisions file." in res.stdout

    # 2. CLI record-review approved
    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "record-review", str(package_with_normalized_draft),
            "--draft-item-id", "AUT_20260620_001_DRAFTITEM_0001",
            "--decision", "approved", "--reviewer", "human_cli", "--reason", "Good CLI"
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully recorded review decision" in res.stdout

    # 3. CLI record-review rejected (bắt buộc --reason)
    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "record-review", str(package_with_normalized_draft),
            "--draft-item-id", "AUT_20260620_001_DRAFTITEM_0002",
            "--decision", "rejected", "--reason", "Not a real item", "--reviewer", "human_cli"
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully recorded review decision" in res.stdout

    # 4. CLI record-review edited (bắt buộc overrides và reason)
    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "record-review", str(package_with_normalized_draft),
            "--draft-item-id", "AUT_20260620_001_DRAFTITEM_0003",
            "--decision", "edited", "--description", "Override Desc", "--quantity", "10",
            "--reason", "CLI Manual Adjust", "--reviewer", "human_cli", "--currency", "vnd"
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully recorded review decision" in res.stdout

    # 5. CLI list-review
    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "list-review", str(package_with_normalized_draft)
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully loaded review decisions statistics." in res.stdout
    assert "Decision Count        : 3" in res.stdout
    assert "Approved Count        : 1" in res.stdout
    assert "Rejected Count        : 1" in res.stdout
    assert "Edited Count          : 1" in res.stdout


def test_atomic_write_protection(package_with_normalized_draft, monkeypatch):
    """Kiểm thử cơ chế atomic write giữ nguyên file cũ khi ghi bị lỗi."""
    # 1. Ghi nhận một decision đầu tiên thành công
    record_review_decision(
        package_with_normalized_draft,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        overwrite=False
    )
    review_file = package_with_normalized_draft / "review" / "review_decisions.json"
    initial_sha = calculate_sha256(review_file)

    # 2. Mock hàm write_review_decisions để nó ném lỗi khi ghi (giả lập lỗi ổ đĩa/giữa chừng)
    def mock_write(path, data):
        tmp_path = path.with_suffix(".tmp")
        # Ghi dở dang rồi ném lỗi
        with open(tmp_path, "w") as f:
            f.write("{ INVALID JSON PARTIAL GHI }")
        raise OSError("Disk full simulation")

    import mep_quotation.review.review_service as service_mod
    monkeypatch.setattr(service_mod, "write_review_decisions", mock_write)


    # 3. Thử record decision mới -> ném OSError
    with pytest.raises(OSError, match="Disk full simulation"):
        record_review_decision(
            package_with_normalized_draft,
            draft_item_id="AUT_20260620_001_DRAFTITEM_0002",
            decision_type="approved",
            overwrite=False
        )

    # 4. Kiểm chứng file review gốc không bị hỏng, SHA256 giữ nguyên
    assert review_file.exists()
    assert calculate_sha256(review_file) == initial_sha
