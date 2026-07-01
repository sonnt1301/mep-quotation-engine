import json
import subprocess
import sys
from pathlib import Path

import pytest

from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.item_candidates.builder import convert_row_to_item
from mep_quotation.item_candidates.item_service import build_item_candidates
from mep_quotation.item_candidates.manifest import validate_item_candidates_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def package_with_row_candidates(tmp_path):
    """Tạo một package đã đi qua Phase 7 (có row_candidates.json và các file trước)."""
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

    # 3. Dựng normalized.json và corrections.json giả lập để pass integrity checks
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
            "unit_candidate": "pcs", # alias test
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
            "currency_candidate": None, # Sẽ gán VND do có chữ VND trong evidence_text
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
            "quantity_candidate": None, # amount = null test
            "unit_price_candidate": 450000.0,
            "currency_candidate": None, # Sẽ gán VND do có chữ VND trong evidence_text
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
            "unit_candidate": "set", # alias test bộ
            "quantity_candidate": 5.0,
            "unit_price_candidate": 85000.0,
            "currency_candidate": "USD", # giữ nguyên USD
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
            "currency_candidate": None, # Giữ nguyên Null do evidence_text không có tín hiệu tiền tệ
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

    # Cập nhật package.json
    pkg_json_path = package_dir / "package.json"
    pkg_model = load_package_json(package_dir)
    pkg_model.files.line_candidates = "parsed/line_candidates.json"
    pkg_model.files.row_candidates = "parsed/row_candidates.json"
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_build_item_candidates_success(package_with_row_candidates):
    """Kiểm tra build_item_candidates chạy thành công và chuyển đổi đúng logic."""
    build_item_candidates(package_with_row_candidates, overwrite=True)
    
    items_file = package_with_row_candidates / "parsed" / "item_candidates.json"
    assert items_file.exists()
    
    with open(items_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["item_count"] == 5
    items = data["items"]

    # 1. Alias test: pcs -> cái
    assert items[0]["unit_candidate"] == "cái"
    assert items[0]["amount_candidate"] == 10.0 * 4500.0 # 45000.0
    assert items[0]["currency_candidate"] == "VND"

    # 2. Currency conditional test: row 2 không có currency nhưng evidence có chữ 'VND' -> gán VND
    assert items[1]["currency_candidate"] == "VND"
    assert items[1]["amount_candidate"] == 100.0 * 12000.0 # 1200000.0

    # 3. Amount null test: row 3 thiếu quantity -> amount_candidate = null
    assert items[2]["quantity_candidate"] is None
    assert items[2]["amount_candidate"] is None
    assert items[2]["currency_candidate"] == "VND" # có VND trong evidence_text

    # 4. Alias test: set -> bộ, giữ nguyên USD
    assert items[3]["unit_candidate"] == "bộ"
    assert items[3]["currency_candidate"] == "USD"
    assert items[3]["amount_candidate"] == 5.0 * 85000.0

    # 5. Currency conditional test: row 5 không có currency và evidence không có chữ VND -> giữ nguyên Null
    assert items[4]["currency_candidate"] is None
    assert items[4]["amount_candidate"] == 2.0 * 350000.0


def test_empty_row_candidates_still_generates_valid_items(tmp_path):
    """Kiểm tra row_candidates rỗng vẫn sinh tệp item_candidates.json hợp lệ với item_count = 0."""
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

    row_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_line_candidates": "parsed/line_candidates.json",
        "source_sha256": calculate_sha256(line_cand_file),
        "source_text_manifest": "text/quotation_text.json",
        "assembler_name": "rule",
        "assembler_version": "1.0",
        "row_count": 0,
        "rows": [],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    row_cand_file = package_dir / "parsed" / "row_candidates.json"
    with open(row_cand_file, "w") as f: json.dump(row_manifest, f)

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

    build_item_candidates(package_dir, overwrite=True)

    items_file = package_dir / "parsed" / "item_candidates.json"
    assert items_file.exists()
    with open(items_file, "r") as f:
        data = json.load(f)
    assert data["item_count"] == 0
    assert data["items"] == []


def test_overwrite_protection_and_audit_logs(package_with_row_candidates):
    """Kiểm tra cản ghi đè (overwrite=False), cho phép ghi đè (overwrite=True) và logs kiểm toán tương ứng."""
    build_item_candidates(package_with_row_candidates, overwrite=False)

    with pytest.raises(ValueError, match="already exists"):
        build_item_candidates(package_with_row_candidates, overwrite=False)

    build_item_candidates(package_with_row_candidates, overwrite=True)

    log_path = package_with_row_candidates / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    events = [e["event"] for e in lines]
    assert "item_candidate_build_started" in events
    assert "item_candidates_built" in events
    assert "item_candidates_written" in events
    assert "item_candidate_build_completed" in events
    assert "item_candidate_build_failed" in events


def test_cli_build_item_candidates(package_with_row_candidates):
    """Kiểm tra chạy câu lệnh CLI build-item-candidates qua subprocess."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "build-item-candidates", str(package_with_row_candidates), "--overwrite"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"CLI error: {result.stderr}"
    assert "Successfully built item candidates." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "Item Count" in result.stdout
    assert "Source Row Candidates" in result.stdout
    assert "Item Candidates Path" in result.stdout
    assert "Items With Price Count" in result.stdout
    assert "Items With Amount Count" in result.stdout
    assert "Warnings Count" in result.stdout


def test_backward_compatibility_integrity_check(package_with_row_candidates):
    """Kiểm tra validate_package_integrity vẫn hoạt động tốt khi gói chưa có item_candidates.json."""
    pkg_model = load_package_json(package_with_row_candidates)
    
    pkg_json_path = package_with_row_candidates / "package.json"
    pkg_model.files.item_candidates = "parsed/item_candidates.json"
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    items_file = package_with_row_candidates / "parsed" / "item_candidates.json"
    if items_file.exists():
        items_file.unlink()

    # Không ném ngoại lệ dù file item_candidates.json không tồn tại (backward compatible)
    validate_package_integrity(package_with_row_candidates)


def test_validation_catches_bad_data_in_item_candidates(package_with_row_candidates):
    """Kiểm tra validate_item_candidates_file / validate_package_integrity bắt lỗi dữ liệu item candidates sai lệch."""
    build_item_candidates(package_with_row_candidates, overwrite=True)
    items_file = package_with_row_candidates / "parsed" / "item_candidates.json"

    # Case A: source_row_id chứa ID không tồn tại
    with open(items_file, "r", encoding="utf-8") as f:
        orig_data = json.load(f)
    
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["source_row_id"] = "INVALID_ROW_ID"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not exist in row_candidates.json"):
        validate_item_candidates_file(items_file, package_with_row_candidates)

    # Case B: raw_evidence_text bị lệch so với row gốc
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["raw_evidence_text"] = "LỆCH EVIDENCE"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not match source row evidence_text"):
        validate_item_candidates_file(items_file, package_with_row_candidates)

    # Case C: amount_candidate tính toán sai
    data = json.loads(json.dumps(orig_data))
    data["items"][0]["amount_candidate"] = 99999.0 # Lệch so với 10 * 4500 = 45000
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not equal quantity \\* unit_price"):
        validate_item_candidates_file(items_file, package_with_row_candidates)

    # Case D: source_sha256 bị sai lệch
    data = json.loads(json.dumps(orig_data))
    data["source_sha256"] = "INVALID_SHA256"
    with open(items_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="source_sha256 mismatch"):
        validate_item_candidates_file(items_file, package_with_row_candidates)


def test_does_not_modify_or_create_normalized_json(package_with_row_candidates):
    """Xác nhận Phase 8 không tự ý tạo mới normalized.json nếu chưa có, và giữ nguyên nội dung nếu đã có."""
    norm_path = package_with_row_candidates / "normalized" / "normalized.json"
    
    # 1. Trường hợp normalized.json chưa có trên đĩa
    if norm_path.exists():
        norm_path.unlink()
        
    with pytest.raises(FileNotFoundError, match="normalized.json not found"):
        build_item_candidates(package_with_row_candidates, overwrite=True)
    assert not norm_path.exists()

    # 2. Trường hợp normalized.json đã có từ trước -> Phải giữ nguyên
    placeholder_content = {"quotation_id": "AUT_20260620_001", "supplier_code": "AUT", "quotation_date": "2026-06-20", "items": []}
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(placeholder_content, f)

    build_item_candidates(package_with_row_candidates, overwrite=True)

    with open(norm_path, "r", encoding="utf-8") as f:
        new_content = json.load(f)
    assert new_content == placeholder_content
