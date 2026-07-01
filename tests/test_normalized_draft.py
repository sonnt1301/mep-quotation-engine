import json
import subprocess
import sys
from pathlib import Path

import pytest

from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.item_candidates.item_service import build_item_candidates
from mep_quotation.normalized_draft.draft_service import build_normalized_draft
from mep_quotation.normalized_draft.manifest import validate_normalized_draft_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def package_with_item_candidates(tmp_path):
    """Tạo một package đã đi qua Phase 8 (có item_candidates.json và các file trước)."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    
    # 1. Tạo original.pdf giả lập bằng fitz
    pdf_path = package_dir / "source" / "original.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    # 2. Tạo metadata.json giả lập
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

    # Dựng corrections.json giả lập để pass integrity checks
    corr_dir = package_dir / "corrections"
    corr_dir.mkdir(parents=True, exist_ok=True)
    corr_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "corrections": []
    }
    with open(corr_dir / "corrections.json", "w", encoding="utf-8") as f:
        json.dump(corr_data, f)

    # 4. Dựng quotation.md
    md_content = (
        "# Quotation Text\n\n"
        "Quotation ID: AUT_20260620_001\n"
        "Source PDF: source/original.pdf\n"
        "Page Count: 1\n"
        "Generated At: 2026-06-20T00:00:00Z\n\n"
        "---\n\n"
        "## Page 1\n\n"
        "Dây cáp điện hạ thế CV 1.5mm2 Cadivi\n"
        "giá 4500 VND/m\n"
        "Ống nhựa HDPE D25 PN10 Tiền Phong\n"
        "giá 12000 VND/m\n"
        "Thiết bị MCB 3P 100A 25kA LS\n"
        "giá 450000 VND/cái\n"
        "CB 1P 16A Schneider\n"
        "giá 85000 USD/set\n"
        "Thiết bị rò điện RCCB không có tiền tệ rõ\n"
        "giá 350000\n"
    )
    md_output_path = package_dir / "text" / "quotation.md"
    md_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 5. Dựng quotation_text.json
    idx1 = md_content.find("## Page 1")
    raw_text_path = package_dir / "source" / "raw_text.json"
    raw_text = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_pdf": "source/original.pdf",
        "source_sha256": "dummy_sha256",
        "extraction_engine": "pymupdf",
        "page_count": 1,
        "pages": [{"page_number": 1, "has_text": True, "character_count": len(md_content) - idx1, "text": md_content[idx1:len(md_content)]}],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(raw_text_path, "w", encoding="utf-8") as f:
        json.dump(raw_text, f)
    
    text_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_raw_text": "source/raw_text.json",
        "source_sha256": calculate_sha256(raw_text_path),
        "page_count": 1,
        "total_characters": len(md_content) - idx1,
        "pages_with_text": 1,
        "markdown_path": "text/quotation.md",
        "pages": [{"page_number": 1, "has_text": True, "character_count": len(md_content) - idx1, "start_offset": idx1, "end_offset": len(md_content)}],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(package_dir / "text" / "quotation_text.json", "w", encoding="utf-8") as f:
        json.dump(text_manifest, f)

    # 6. Dựng line_candidates.json giả lập để pass validation chéo
    lines = md_content.splitlines(keepends=True)
    def get_offset_and_text(start_line_idx, end_line_idx):
        offset = 0
        for i in range(start_line_idx):
            offset += len(lines[i])
        end_offset = offset
        for i in range(start_line_idx, end_line_idx + 1):
            end_offset += len(lines[i])
        return offset, end_offset, "".join(lines[start_line_idx:end_line_idx + 1])

    r1_s, r1_e, r1_t = get_offset_and_text(11, 12)
    r2_s, r2_e, r2_t = get_offset_and_text(13, 14)
    r3_s, r3_e, r3_t = get_offset_and_text(15, 16)
    r4_s, r4_e, r4_t = get_offset_and_text(17, 18)
    r5_s, r5_e, r5_t = get_offset_and_text(19, 20)

    # Đăng ký các line candidates để khớp các source_candidate_ids của row
    line_ids = [
        "AUT_20260620_001_LINECAND_0001",
        "AUT_20260620_001_LINECAND_0002",
        "AUT_20260620_001_LINECAND_0003",
        "AUT_20260620_001_LINECAND_0004",
        "AUT_20260620_001_LINECAND_0005",
        "AUT_20260620_001_LINECAND_0006",
        "AUT_20260620_001_LINECAND_0007",
        "AUT_20260620_001_LINECAND_0008",
        "AUT_20260620_001_LINECAND_0009",
        "AUT_20260620_001_LINECAND_0010"
    ]
    line_candidates_list = []
    for lid in line_ids:
        line_candidates_list.append({
            "candidate_id": lid,
            "line_number": 12,
            "page_number": 1,
            "raw_line": "mock",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": idx1, "end_offset": idx1 + 4, "text": "## P"}
        })

    line_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_text_manifest": "text/quotation_text.json",
        "source_markdown": "text/quotation.md",
        "source_sha256": calculate_sha256(md_output_path),
        "parser_name": "rule_based_line_candidate_v1",
        "parser_version": "0.1.0",
        "candidate_count": len(line_candidates_list),
        "candidates": line_candidates_list,
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    line_cand_file = package_dir / "parsed" / "line_candidates.json"
    line_cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(line_cand_file, "w", encoding="utf-8") as f:
        json.dump(line_manifest, f)

    # 7. Dựng row_candidates.json
    rows = [
        {
            "row_id": "AUT_20260620_001_ROWCAND_0001",
            "page_number": 1,
            "start_line_number": 12,
            "end_line_number": 13,
            "source_candidate_ids": ["AUT_20260620_001_LINECAND_0001", "AUT_20260620_001_LINECAND_0002"],
            "description_candidate": "Dây cáp điện hạ thế CV 1.5mm2 Cadivi",
            "material_code_candidate": "CV-1.5",
            "brand_candidate": "Cadivi",
            "unit_candidate": "pcs",
            "quantity_candidate": 10.0,
            "unit_price_candidate": 4500.0,
            "currency_candidate": "VND",
            "evidence_text": r1_t,
            "start_offset": r1_s,
            "end_offset": r1_e,
            "confidence": 0.9,
            "warnings": []
        },
        {
            "row_id": "AUT_20260620_001_ROWCAND_0002",
            "page_number": 1,
            "start_line_number": 14,
            "end_line_number": 15,
            "source_candidate_ids": ["AUT_20260620_001_LINECAND_0003", "AUT_20260620_001_LINECAND_0004"],
            "description_candidate": "Ống nhựa HDPE D25 PN10 Tiền Phong",
            "brand_candidate": "Tiền Phong",
            "unit_candidate": "m",
            "quantity_candidate": 100.0,
            "unit_price_candidate": 12000.0,
            "currency_candidate": None,
            "evidence_text": r2_t,
            "start_offset": r2_s,
            "end_offset": r2_e,
            "confidence": 0.8,
            "warnings": []
        },
        {
            "row_id": "AUT_20260620_001_ROWCAND_0003",
            "page_number": 1,
            "start_line_number": 16,
            "end_line_number": 17,
            "source_candidate_ids": ["AUT_20260620_001_LINECAND_0005", "AUT_20260620_001_LINECAND_0006"],
            "description_candidate": "Thiết bị MCB 3P 100A 25kA LS",
            "brand_candidate": "LS",
            "unit_candidate": "cái",
            "quantity_candidate": None,
            "unit_price_candidate": 450000.0,
            "currency_candidate": None,
            "evidence_text": r3_t,
            "start_offset": r3_s,
            "end_offset": r3_e,
            "confidence": 0.7,
            "warnings": []
        },
        {
            "row_id": "AUT_20260620_001_ROWCAND_0004",
            "page_number": 1,
            "start_line_number": 18,
            "end_line_number": 19,
            "source_candidate_ids": ["AUT_20260620_001_LINECAND_0007", "AUT_20260620_001_LINECAND_0008"],
            "description_candidate": "CB 1P 16A Schneider",
            "brand_candidate": "Schneider",
            "unit_candidate": "set",
            "quantity_candidate": 5.0,
            "unit_price_candidate": 85000.0,
            "currency_candidate": "USD",
            "evidence_text": r4_t,
            "start_offset": r4_s,
            "end_offset": r4_e,
            "confidence": 0.8,
            "warnings": []
        },
        {
            "row_id": "AUT_20260620_001_ROWCAND_0005",
            "page_number": 1,
            "start_line_number": 20,
            "end_line_number": 21,
            "source_candidate_ids": ["AUT_20260620_001_LINECAND_0009", "AUT_20260620_001_LINECAND_0010"],
            "description_candidate": "Thiết bị rò điện RCCB không có tiền tệ rõ",
            "quantity_candidate": 2.0,
            "unit_price_candidate": 350000.0,
            "currency_candidate": None,
            "evidence_text": r5_t,
            "start_offset": r5_s,
            "end_offset": r5_e,
            "confidence": 0.6,
            "warnings": []
        }
    ]

    row_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_line_candidates": "parsed/line_candidates.json",
        "source_sha256": calculate_sha256(line_cand_file),
        "source_text_manifest": "text/quotation_text.json",
        "assembler_name": "rule_based_row_candidate_assembler",
        "assembler_version": "1.0",
        "row_count": len(rows),
        "rows": rows,
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }

    row_cand_file = package_dir / "parsed" / "row_candidates.json"
    row_cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(row_cand_file, "w", encoding="utf-8") as f:
        json.dump(row_manifest, f)

    # Dựng item_candidates.json bằng service của Phase 8
    pkg_json_path = package_dir / "package.json"
    pkg_model = load_package_json(package_dir)
    pkg_model.files.line_candidates = "parsed/line_candidates.json"
    pkg_model.files.row_candidates = "parsed/row_candidates.json"
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    # 3. Tạo sẵn normalized.json giả lập để pass integrity check ban đầu
    # Nhưng ta sẽ kiểm soát Phase 9 không được sửa đổi nó
    norm_dir = package_dir / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    norm_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "supplier_code": "AUT",
        "quotation_date": "2026-06-20",
        "items": []
    }
    with open(norm_dir / "normalized.json", "w", encoding="utf-8") as f:
        json.dump(norm_data, f)

    build_item_candidates(package_dir, overwrite=True)

    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_build_normalized_draft_success(package_with_item_candidates):
    """Kiểm tra build_normalized_draft chạy thành công và tạo các draft items chính xác."""
    build_normalized_draft(package_with_item_candidates, overwrite=True)

    draft_file = package_with_item_candidates / "normalized" / "normalized_draft.json"
    assert draft_file.exists()

    with open(draft_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["item_count"] == 5
    assert data["supplier_code"] == "AUT"
    assert data["quotation_date"] == "2026-06-20"
    
    items = data["items"]
    
    # 1. Trạng thái auto_ready: item 1 (description + unit_price + confidence >= 0.75 + evidence valid)
    assert items[0]["review_status"] == "auto_ready"
    assert items[0]["amount"] == 10.0 * 4500.0 # 45000.0
    assert items[0]["currency"] == "VND"

    # 2. Trạng thái needs_review: item 3 (thiếu quantity -> amount = null, cần review)
    assert items[2]["review_status"] == "needs_review"
    assert items[2]["quantity"] is None
    assert items[2]["amount"] is None
    assert "missing_quantity" in items[2]["review_reasons"]

    # 3. Kế thừa currency: item 2 có currency null ban đầu nhưng evidence có chữ VND -> VND
    assert items[1]["currency"] == "VND"


def test_empty_candidates_generates_valid_empty_draft(tmp_path):
    """Kiểm tra package rỗng vẫn tạo tệp normalized_draft.json rỗng hợp lệ."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)

    md_path = package_dir / "text" / "quotation.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w") as f: f.write("mock")

    raw_text_path = package_dir / "source" / "raw_text.json"
    with open(raw_text_path, "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_pdf": "source/original.pdf", "source_sha256": "dummy", "extraction_engine": "pymupdf", "page_count": 1, "pages": [{"page_number": 1, "has_text": True, "character_count": 4, "text": "mock"}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    text_manifest_path = package_dir / "text" / "quotation_text.json"
    with open(text_manifest_path, "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_raw_text": "source/raw_text.json", "source_sha256": calculate_sha256(raw_text_path), "page_count": 1, "total_characters": 4, "pages_with_text": 1, "markdown_path": "text/quotation.md", "pages": [{"page_number": 1, "has_text": True, "character_count": 4, "start_offset": 0, "end_offset": 4}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    line_manifest = {"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_text_manifest": "text/quotation_text.json", "source_markdown": "text/quotation.md", "source_sha256": calculate_sha256(md_path), "parser_name": "rule", "parser_version": "1.0", "candidate_count": 0, "candidates": [], "warnings": [], "generated_at": "2026-06-20T00:00:00Z"}
    line_cand_file = package_dir / "parsed" / "line_candidates.json"
    line_cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(line_cand_file, "w") as f: json.dump(line_manifest, f)

    row_manifest = {"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_line_candidates": "parsed/line_candidates.json", "source_sha256": calculate_sha256(line_cand_file), "source_text_manifest": "text/quotation_text.json", "assembler_name": "rule", "assembler_version": "1.0", "row_count": 0, "rows": [], "warnings": [], "generated_at": "2026-06-20T00:00:00Z"}
    row_cand_file = package_dir / "parsed" / "row_candidates.json"
    with open(row_cand_file, "w") as f: json.dump(row_manifest, f)

    item_manifest = {"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_row_candidates": "parsed/row_candidates.json", "source_sha256": calculate_sha256(row_cand_file), "source_text_manifest": "text/quotation_text.json", "builder_name": "rule", "builder_version": "1.0", "item_count": 0, "items": [], "warnings": [], "generated_at": "2026-06-20T00:00:00Z"}
    item_cand_file = package_dir / "parsed" / "item_candidates.json"
    with open(item_cand_file, "w") as f: json.dump(item_manifest, f)

    pdf_path = package_dir / "source" / "original.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    
    meta_data = {"schema_version": "1.0", "file_name": "original.pdf", "file_size": pdf_path.stat().st_size, "sha256": calculate_sha256(pdf_path), "page_count": 1, "pdf_version": "1.4", "encrypted": False, "imported_at": "2026-06-20T00:00:00Z", "warnings": []}
    with open(package_dir / "source" / "metadata.json", "w") as f: json.dump(meta_data, f)

    norm_dir = package_dir / "normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    with open(norm_dir / "normalized.json", "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "supplier_code": "AUT", "quotation_date": "2026-06-20", "items": []}, f)

    corr_dir = package_dir / "corrections"
    corr_dir.mkdir(parents=True, exist_ok=True)
    with open(corr_dir / "corrections.json", "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "corrections": []}, f)

    # Cập nhật package.json
    pkg_model = load_package_json(package_dir)
    pkg_model.files.line_candidates = "parsed/line_candidates.json"
    pkg_model.files.row_candidates = "parsed/row_candidates.json"
    pkg_model.files.item_candidates = "parsed/item_candidates.json"
    with open(package_dir / "package.json", "w") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    build_normalized_draft(package_dir, overwrite=True)

    draft_file = package_dir / "normalized" / "normalized_draft.json"
    assert draft_file.exists()
    with open(draft_file, "r") as f:
        data = json.load(f)
    assert data["item_count"] == 0
    assert data["items"] == []


def test_overwrite_protection_and_integrity_audit(package_with_item_candidates):
    """Kiểm tra overwrite=False cản ghi đè và ghi đầy đủ audit logs."""
    build_normalized_draft(package_with_item_candidates, overwrite=False)

    with pytest.raises(ValueError, match="already exists"):
        build_normalized_draft(package_with_item_candidates, overwrite=False)

    build_normalized_draft(package_with_item_candidates, overwrite=True)

    log_path = package_with_item_candidates / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    events = [e["event"] for e in lines]
    assert "normalized_draft_build_started" in events
    assert "normalized_draft_built" in events
    assert "normalized_draft_written" in events
    assert "normalized_draft_build_completed" in events


def test_cli_build_normalized_draft(package_with_item_candidates):
    """Kiểm tra lệnh CLI build-normalized-draft."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "build-normalized-draft", str(package_with_item_candidates), "--overwrite"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"CLI error: {result.stderr}"
    assert "Successfully built normalized draft." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "Supplier Code" in result.stdout
    assert "Item Count" in result.stdout
    assert "Review Required Count" in result.stdout


def test_normalized_json_safety_protection(package_with_item_candidates):
    """Kiểm tra tệp normalized.json không bị thay đổi hoặc tạo mới trái phép."""
    official_norm_path = package_with_item_candidates / "normalized" / "normalized.json"
    
    # 1. Nếu normalized.json đã có từ trước -> Phải lưu lại SHA256 và so khớp không đổi
    with open(official_norm_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": "1.0",
            "quotation_id": "AUT_20260620_001",
            "supplier_code": "AUT",
            "quotation_date": "2026-06-20",
            "items": []
        }, f)
    initial_sha = calculate_sha256(official_norm_path)

    build_normalized_draft(package_with_item_candidates, overwrite=True)

    after_sha = calculate_sha256(official_norm_path)
    assert initial_sha == after_sha

    # 2. Nếu normalized.json không tồn tại -> Đảm bảo Phase 9 không tự tạo mới nó
    official_norm_path.unlink()
    # Chạy build_normalized_draft sẽ ném ValueError do package integrity của các Phase trước bắt buộc normalized.json phải có.
    # Nhưng đối với Phase 9, dịch vụ draft_service của ta tự bảo vệ không tạo mới.
    # Để kiểm tra không tự tạo mới:
    with pytest.raises(Exception):
        build_normalized_draft(package_with_item_candidates, overwrite=True)
    assert not official_norm_path.exists()


def test_validation_catches_errors_in_manifest(package_with_item_candidates):
    """Kiểm duyệt các lỗi cấu trúc và dữ liệu lệch trong validate_normalized_draft_file."""
    build_normalized_draft(package_with_item_candidates, overwrite=True)
    draft_file = package_with_item_candidates / "normalized" / "normalized_draft.json"

    # Load dữ liệu gốc
    with open(draft_file, "r", encoding="utf-8") as f:
        orig_data = json.load(f)

    # Case A: source_item_candidate_id không tồn tại
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["source_item_candidate_id"] = "INVALID_CAND_ID"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    with pytest.raises(ValueError, match="does not exist in item_candidates.json"):
        validate_normalized_draft_file(draft_file, package_with_item_candidates)

    # Case B: raw_evidence_text bị lệch
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["evidence"]["raw_evidence_text"] = "LỆCH TEXT"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    with pytest.raises(ValueError, match="raw_evidence_text mismatch"):
        validate_normalized_draft_file(draft_file, package_with_item_candidates)

    # Case C: review_status invalid
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["review_status"] = "INVALID_STATUS"
    with open(draft_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    with pytest.raises(ValueError, match="invalid review_status"):
        validate_normalized_draft_file(draft_file, package_with_item_candidates)


def test_amount_mismatch_warning_generation():
    """Kiểm tra sinh cảnh báo amount_mismatch_recomputed khi amount của item candidate không khớp."""
    from mep_quotation.spec.models import ItemCandidateModel
    from mep_quotation.normalized_draft.builder import build_draft_item

    mock_item = ItemCandidateModel(
        item_candidate_id="AUT_20260620_001_ITEMCAND_0001",
        source_row_id="AUT_20260620_001_ROWCAND_0001",
        page_number=1,
        start_line_number=12,
        end_line_number=13,
        description_candidate="Dây cáp điện hạ thế CV 1.5mm2 Cadivi",
        material_code_candidate="CV-1.5",
        brand_candidate="Cadivi",
        unit_candidate="cái",
        quantity_candidate=10.0,
        unit_price_candidate=4500.0,
        amount_candidate=999999.0,  # Sai lệch
        currency_candidate="VND",
        raw_evidence_text="Dây cáp điện hạ thế CV 1.5mm2 Cadivi\ngiá 4500 VND/m",
        start_offset=10,
        end_offset=50,
        confidence=0.9,
        warnings=[]
    )

    draft_item = build_draft_item(mock_item, "AUT_20260620_001", 1, "VND")
    
    assert "amount_mismatch_recomputed" in draft_item.review_reasons
    assert any(w.code == "amount_mismatch_recomputed" for w in draft_item.warnings)
    assert draft_item.amount == 45000.0  # được tính lại đúng

