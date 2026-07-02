import json
import subprocess
import sys
from pathlib import Path
import pytest
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.review.review_service import record_review_decision
from mep_quotation.normalized_export.export_service import export_normalized
from mep_quotation.spec.models import (
    ReviewFieldOverridesModel,
    NormalizedQuotationModel,
    NormalizedDraftModel
)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def package_ready_for_export(tmp_path):
    """Tạo một package đã đi qua Phase 10 (có draft và decisions)."""
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
    md_content = "mock\nmock\nmock\nmock\n"
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
        "candidate_count": 4,
        "candidates": [
            {"candidate_id": "AUT_20260620_001_LINECAND_0001", "page_number": 1, "line_number": 1, "raw_line": "mock", "confidence": 0.9, "warnings": [], "evidence": {"source_path": "text/quotation.md", "start_offset": 0, "end_offset": 4, "text": "mock"}},
            {"candidate_id": "AUT_20260620_001_LINECAND_0002", "page_number": 1, "line_number": 2, "raw_line": "mock", "confidence": 0.9, "warnings": [], "evidence": {"source_path": "text/quotation.md", "start_offset": 5, "end_offset": 9, "text": "mock"}},
            {"candidate_id": "AUT_20260620_001_LINECAND_0003", "page_number": 1, "line_number": 3, "raw_line": "mock", "confidence": 0.9, "warnings": [], "evidence": {"source_path": "text/quotation.md", "start_offset": 10, "end_offset": 14, "text": "mock"}},
            {"candidate_id": "AUT_20260620_001_LINECAND_0004", "page_number": 1, "line_number": 4, "raw_line": "mock", "confidence": 0.9, "warnings": [], "evidence": {"source_path": "text/quotation.md", "start_offset": 15, "end_offset": 19, "text": "mock"}}
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
        "row_count": 4,
        "rows": [
            {"row_id": "AUT_20260620_001_ROWCAND_0001", "page_number": 1, "start_line_number": 1, "end_line_number": 2, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0001"], "description_candidate": "Item 1", "brand_candidate": None, "unit_candidate": "cái", "quantity_candidate": 10.0, "unit_price_candidate": 5000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 0, "end_offset": 4, "confidence": 0.9, "warnings": []},
            {"row_id": "AUT_20260620_001_ROWCAND_0002", "page_number": 1, "start_line_number": 2, "end_line_number": 3, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0002"], "description_candidate": "Item 2", "brand_candidate": None, "unit_candidate": "m", "quantity_candidate": 2.0, "unit_price_candidate": 10000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 5, "end_offset": 9, "confidence": 0.8, "warnings": []},
            {"row_id": "AUT_20260620_001_ROWCAND_0003", "page_number": 1, "start_line_number": 3, "end_line_number": 4, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0003"], "description_candidate": "Item 3", "brand_candidate": None, "unit_candidate": "bộ", "quantity_candidate": 5.0, "unit_price_candidate": 20000.0, "currency_candidate": "VND", "evidence_text": "mock", "start_offset": 10, "end_offset": 14, "confidence": 0.8, "warnings": []},
            {"row_id": "AUT_20260620_001_ROWCAND_0004", "page_number": 1, "start_line_number": 4, "end_line_number": 5, "source_candidate_ids": ["AUT_20260620_001_LINECAND_0004"], "description_candidate": "Item 4", "brand_candidate": None, "unit_candidate": "cái", "quantity_candidate": 1.0, "unit_price_candidate": 50000.0, "currency_candidate": None, "evidence_text": "mock", "start_offset": 15, "end_offset": 19, "confidence": 0.8, "warnings": []}
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
        "item_count": 4,
        "items": [
            {"item_candidate_id": "AUT_20260620_001_ITEMCAND_0001", "source_row_id": "AUT_20260620_001_ROWCAND_0001", "page_number": 1, "start_line_number": 1, "end_line_number": 2, "description_candidate": "Item 1", "brand_candidate": None, "unit_candidate": "cái", "quantity_candidate": 10.0, "unit_price_candidate": 5000.0, "amount_candidate": 50000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 0, "end_offset": 4, "confidence": 0.9, "warnings": []},
            {"item_candidate_id": "AUT_20260620_001_ITEMCAND_0002", "source_row_id": "AUT_20260620_001_ROWCAND_0002", "page_number": 1, "start_line_number": 2, "end_line_number": 3, "description_candidate": "Item 2", "brand_candidate": None, "unit_candidate": "m", "quantity_candidate": 2.0, "unit_price_candidate": 10000.0, "amount_candidate": 20000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 5, "end_offset": 9, "confidence": 0.8, "warnings": []},
            {"item_candidate_id": "AUT_20260620_001_ITEMCAND_0003", "source_row_id": "AUT_20260620_001_ROWCAND_0003", "page_number": 1, "start_line_number": 3, "end_line_number": 4, "description_candidate": "Item 3", "brand_candidate": None, "unit_candidate": "bộ", "quantity_candidate": 5.0, "unit_price_candidate": 20000.0, "amount_candidate": 100000.0, "currency_candidate": "VND", "raw_evidence_text": "mock", "start_offset": 10, "end_offset": 14, "confidence": 0.8, "warnings": []},
            {"item_candidate_id": "AUT_20260620_001_ITEMCAND_0004", "source_row_id": "AUT_20260620_001_ROWCAND_0004", "page_number": 1, "start_line_number": 4, "end_line_number": 5, "description_candidate": "Item 4", "brand_candidate": None, "unit_candidate": "cái", "quantity_candidate": 1.0, "unit_price_candidate": 50000.0, "amount_candidate": 50000.0, "currency_candidate": None, "raw_evidence_text": "mock", "start_offset": 15, "end_offset": 19, "confidence": 0.8, "warnings": []}
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
        "item_count": 4,
        "review_required_count": 4,
        "items": [
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0001", "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0001", "source_row_id": "AUT_20260620_001_ROWCAND_0001",
                "page_number": 1, "start_line_number": 1, "end_line_number": 2, "description": "Item 1", "unit": "cái", "quantity": 10.0, "unit_price": 5000.0, "currency": "VND", "amount": 50000.0, "review_status": "needs_review", "review_reasons": [], "confidence": 0.9, "warnings": [], "evidence": {"raw_evidence_text": "mock", "start_offset": 0, "end_offset": 4}
            },
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0002", "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0002", "source_row_id": "AUT_20260620_001_ROWCAND_0002",
                "page_number": 1, "start_line_number": 2, "end_line_number": 3, "description": "Item 2", "unit": "m", "quantity": 2.0, "unit_price": 10000.0, "currency": "VND", "amount": 20000.0, "review_status": "needs_review", "review_reasons": [], "confidence": 0.8, "warnings": [], "evidence": {"raw_evidence_text": "mock", "start_offset": 5, "end_offset": 9}
            },
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0003", "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0003", "source_row_id": "AUT_20260620_001_ROWCAND_0003",
                "page_number": 1, "start_line_number": 3, "end_line_number": 4, "description": "Item 3", "unit": "bộ", "quantity": 5.0, "unit_price": 20000.0, "currency": "VND", "amount": 100000.0, "review_status": "needs_review", "review_reasons": [], "confidence": 0.8, "warnings": [], "evidence": {"raw_evidence_text": "mock", "start_offset": 10, "end_offset": 14}
            },
            {
                "draft_item_id": "AUT_20260620_001_DRAFTITEM_0004", "source_item_candidate_id": "AUT_20260620_001_ITEMCAND_0004", "source_row_id": "AUT_20260620_001_ROWCAND_0004",
                "page_number": 1, "start_line_number": 4, "end_line_number": 5, "description": "Item 4", "unit": "cái", "quantity": 1.0, "unit_price": 50000.0, "currency": None, "amount": 50000.0, "review_status": "needs_review", "review_reasons": [], "confidence": 0.8, "warnings": [], "evidence": {"raw_evidence_text": "mock", "start_offset": 15, "end_offset": 19}
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
    
    # Tạo normalized.json giả lập rỗng để vượt qua validate_package_integrity ban đầu
    with open(package_dir / "normalized" / "normalized.json", "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "supplier_code": "AUT", "quotation_date": "2026-06-20", "items": []}, f)
        
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_export_normalized_success(package_ready_for_export):
    """Kiểm thử export thành công với approved và edited decisions."""
    # 1. Ghi nhận decisions
    # Item 1: approved
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        reviewer="human_a",
        reason="Good"
    )
    # Item 2: edited (có overrides đổi giá trị)
    overrides = ReviewFieldOverridesModel(
        description="Item 2 Override",
        quantity=5.0,
        unit_price=12000.0,
        currency="USD" # uppercase
    )
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0002",
        decision_type="edited",
        reviewer="human_b",
        reason="Revised",
        field_overrides=overrides
    )
    # Item 3: rejected
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0003",
        decision_type="rejected",
        reason="Spam"
    )
    # Item 4: bỏ qua không review (unreviewed)

    # 2. Thực hiện export
    export_file = export_normalized(package_ready_for_export, overwrite=True)
    assert export_file.exists()

    with open(export_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 3. Kiểm định các trường official bắt buộc ở file-level
    assert data["quotation_id"] == "AUT_20260620_001"
    assert data["supplier_code"] == "AUT"
    assert data["quotation_date"] == "2026-06-20"
    assert data["source_normalized_draft"] == "normalized/normalized_draft.json"
    assert data["source_review_decisions"] == "review/review_decisions.json"
    assert data["source_normalized_draft_sha256"] is not None
    assert data["source_review_decisions_sha256"] is not None
    assert data["item_count"] == 2

    # Kiểm tra summary
    sum_data = data["export_summary"]
    assert sum_data["draft_item_count"] == 4
    assert sum_data["approved_count"] == 1
    assert sum_data["edited_count"] == 1
    assert sum_data["rejected_count"] == 1
    assert sum_data["unreviewed_count"] == 1
    assert sum_data["exported_item_count"] == 2

    # 4. Kiểm định chi tiết các item
    items = data["items"]
    assert len(items) == 2

    # Approved item 1
    item_1 = items[0]
    assert item_1["item_id"] == "AUT_20260620_001_ITEM_0001"
    assert item_1["source_draft_item_id"] == "AUT_20260620_001_DRAFTITEM_0001"
    assert item_1["source_review_decision_id"] == "AUT_20260620_001_REVIEW_0001"
    assert item_1["description"] == "Item 1"
    assert item_1["quantity"] == 10.0
    assert item_1["unit_price"] == 5000.0
    assert item_1["currency"] == "VND"
    assert item_1["amount"] == 50000.0 # recomputed amount

    # Edited item 2
    item_2 = items[1]
    assert item_2["item_id"] == "AUT_20260620_001_ITEM_0002"
    assert item_2["source_draft_item_id"] == "AUT_20260620_001_DRAFTITEM_0002"
    assert item_2["source_review_decision_id"] == "AUT_20260620_001_REVIEW_0002"
    assert item_2["description"] == "Item 2 Override"
    assert item_2["quantity"] == 5.0
    assert item_2["unit_price"] == 12000.0
    assert item_2["currency"] == "USD" # uppercase check
    assert item_2["amount"] == 60000.0 # recomputed amount (5 * 12000)

    # 5. Kiểm định chéo validate_package_integrity vượt qua thành công
    validate_package_integrity(package_ready_for_export)


def test_export_no_approved_or_edited_items(package_ready_for_export):
    """Kiểm thử trường hợp không có item nào được approved/edited sinh items = [] và warning."""
    # Chỉ ghi nhận rejected
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="rejected",
        reason="spam"
    )

    export_file = export_normalized(package_ready_for_export, overwrite=True)
    with open(export_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["item_count"] == 0
    assert data["items"] == []
    
    # Kiểm tra warning file-level
    warnings = data["warnings"]
    assert len(warnings) == 1
    assert warnings[0]["code"] == "no_approved_or_edited_items"


def test_export_required_field_missing_description(package_ready_for_export):
    """Kiểm thử khi approved/edited item thiếu description sẽ báo lỗi."""
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        reviewer="human"
    )

    # Sửa đè description của draft_item_id thành trống trực tiếp để test validation
    draft_file = package_ready_for_export / "normalized" / "normalized_draft.json"
    with open(draft_file, "r", encoding="utf-8") as f:
        draft_data = json.load(f)
    
    draft_data["items"][0]["description"] = "   " # trống
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(draft_data, f)

    # Cập nhật source_sha256 trong review_decisions.json để tránh lỗi lệch hash
    new_sha256 = calculate_sha256(draft_file)
    review_file = package_ready_for_export / "review" / "review_decisions.json"
    with open(review_file, "r", encoding="utf-8") as f:
        rev_data = json.load(f)
    rev_data["source_sha256"] = new_sha256
    with open(review_file, "w", encoding="utf-8") as f:
        json.dump(rev_data, f)


    # Chạy export phải báo lỗi ValueError do thiếu description
    with pytest.raises(ValueError, match="description is missing or empty"):
        export_normalized(package_ready_for_export, overwrite=True)


def test_export_currency_inheritance_and_validation(package_ready_for_export):
    """Kiểm thử thừa kế currency và bắt lỗi currency không hợp lệ."""
    # Item 4: có currency = null trong draft item
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0004",
        decision_type="approved"
    )

    # 1. Thừa kế currency từ quotation-level (VND)
    export_file = export_normalized(package_ready_for_export, overwrite=True)
    with open(export_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    item = data["items"][0]
    assert item["currency"] == "VND"
    # Kiểm tra item warning thừa kế currency
    warnings = item["warnings"]
    assert any(w["code"] == "currency_inherited_from_quotation" for w in warnings)

    # 2. Trường hợp thiếu cả hai currency
    # Sửa quotation-level currency trong draft thành null
    draft_file = package_ready_for_export / "normalized" / "normalized_draft.json"
    with open(draft_file, "r", encoding="utf-8") as f:
        draft_data = json.load(f)
    draft_data["currency"] = None
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(draft_data, f)

    # Cập nhật source_sha256 trong review_decisions.json để tránh lỗi lệch hash
    new_sha256 = calculate_sha256(draft_file)
    review_file = package_ready_for_export / "review" / "review_decisions.json"
    with open(review_file, "r", encoding="utf-8") as f:
        rev_data = json.load(f)
    rev_data["source_sha256"] = new_sha256
    with open(review_file, "w", encoding="utf-8") as f:
        json.dump(rev_data, f)


    # Chạy export phải báo lỗi do thiếu currency
    with pytest.raises(ValueError, match="lacks both item-level and valid quotation-level currency"):
        export_normalized(package_ready_for_export, overwrite=True)


def test_export_amount_recompute_and_warning(package_ready_for_export):
    """Kiểm thử tự động tính amount và tạo warning khi bị lệch."""
    # Item 1: quantity=10, unit_price=5000, amount=50000
    # Thử truyền override amount lệch (ví dụ 60000)
    overrides = ReviewFieldOverridesModel(amount=60000.0)
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="edited",
        field_overrides=overrides,
        reason="Adjustment"
    )

    export_file = export_normalized(package_ready_for_export, overwrite=True)
    with open(export_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    item = data["items"][0]
    assert item["amount"] == 50000.0 # luôn recompute dựa trên quantity * unit_price
    
    # Kiểm tra item warning phát sinh
    warnings = item["warnings"]
    assert any(w["code"] == "amount_recomputed_from_quantity_and_unit_price" for w in warnings)


def test_export_overwrite_check(package_ready_for_export):
    """Kiểm thử cản ghi đè khi overwrite=False và rebuilding khi overwrite=True."""
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved"
    )

    # 1. Chạy export lần đầu -> tạo file
    export_file = export_normalized(package_ready_for_export, overwrite=True)
    assert export_file.exists()

    # 2. Chạy lần hai với overwrite=False -> lỗi
    with pytest.raises(ValueError, match="already exists"):
        export_normalized(package_ready_for_export, overwrite=False)

    # 3. Chạy lần hai với overwrite=True -> ok
    export_normalized(package_ready_for_export, overwrite=True)


def test_cli_export_normalized(package_ready_for_export):
    """Kiểm thử chạy CLI subcommand export-normalized."""
    record_review_decision(
        package_ready_for_export,
        draft_item_id="AUT_20260620_001_DRAFTITEM_0001",
        decision_type="approved",
        reason="CLI test"
    )

    res = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "export-normalized", str(package_ready_for_export), "--overwrite"
        ],
        capture_output=True, text=True, encoding="utf-8"
    )
    assert res.returncode == 0, f"CLI error: {res.stderr}"
    assert "Successfully exported official normalized quotation" in res.stdout
    assert "Exported Item Count   : 1" in res.stdout
