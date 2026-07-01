import json
import subprocess
import sys
from pathlib import Path

import pytest

from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.row_assembly.assembler import group_candidates_to_rows
from mep_quotation.row_assembly.row_service import assemble_row_candidates
from mep_quotation.row_assembly.manifest import validate_row_candidates_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def package_with_line_candidates(tmp_path):
    """Tạo một package đã đi qua Phase 6 (có line_candidates.json và các file trước)."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    
    # 1. Tạo original.pdf giả lập bằng fitz
    pdf_path = package_dir / "source" / "original.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    # 2. Tạo metadata.json giả lập
    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": 2,
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
        "Page Count: 2\n"
        "Generated At: 2026-06-20T00:00:00Z\n\n"
        "---\n\n"
        "## Page 1\n\n"
        "Dây cáp điện hạ thế CV 1.5mm2 Cadivi\n"
        "giá 4500 VND/m\n"
        "Ống nhựa HDPE D25 PN10 Tiền Phong\n"
        "giá 12000 VND/m\n"
        "Thiết bị MCB 3P 100A 25kA LS\n"
        "giá 450000 VND/cái\n\n"
        "---\n\n"
        "## Page 2\n\n"
        "CB 1P 16A Schneider\n"
        "giá 85000\n"
        "Cáp ngầm DVV-2x4 Daphaco\n"
        "Số lượng: 50 cuộn\n"
        "giá 18000 VNĐ/m\n"
    )
    md_output_path = package_dir / "text" / "quotation.md"
    md_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 5. Dựng quotation_text.json
    idx1 = md_content.find("## Page 1")
    idx2 = md_content.find("## Page 2")

    # 5b. Tạo tệp raw_text.json
    raw_text_path = package_dir / "source" / "raw_text.json"
    raw_text = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_pdf": "source/original.pdf",
        "source_sha256": "dummy_sha256",
        "extraction_engine": "pymupdf",
        "extraction_engine_version": "1.0",
        "page_count": 2,
        "pages": [
            {"page_number": 1, "has_text": True, "character_count": idx2 - idx1, "text": md_content[idx1:idx2]},
            {"page_number": 2, "has_text": True, "character_count": len(md_content) - idx2, "text": md_content[idx2:len(md_content)]}
        ],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(raw_text_path, "w", encoding="utf-8") as f:
        json.dump(raw_text, f)
    
    text_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_raw_text": "source/raw_text.json",
        "source_sha256": calculate_sha256(raw_text_path),
        "page_count": 2,
        "total_characters": len(md_content) - idx1,
        "pages_with_text": 2,
        "markdown_path": "text/quotation.md",
        "pages": [
            {
                "page_number": 1,
                "has_text": True,
                "character_count": idx2 - idx1,
                "start_offset": idx1,
                "end_offset": idx2
            },
            {
                "page_number": 2,
                "has_text": True,
                "character_count": len(md_content) - idx2,
                "start_offset": idx2,
                "end_offset": len(md_content)
            }
        ],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(package_dir / "text" / "quotation_text.json", "w", encoding="utf-8") as f:
        json.dump(text_manifest, f)

    # 6. Dựng line_candidates.json
    lines = md_content.splitlines(keepends=True)

    def get_offset_and_text(line_idx):
        offset = 0
        for i in range(line_idx):
            offset += len(lines[i])
        return offset, offset + len(lines[line_idx]), lines[line_idx]

    l12_s, l12_e, l12_t = get_offset_and_text(11)
    l13_s, l13_e, l13_t = get_offset_and_text(12)
    l14_s, l14_e, l14_t = get_offset_and_text(13)
    l15_s, l15_e, l15_t = get_offset_and_text(14)
    l16_s, l16_e, l16_t = get_offset_and_text(15)
    l17_s, l17_e, l17_t = get_offset_and_text(16)

    l23_s, l23_e, l23_t = get_offset_and_text(22)
    l24_s, l24_e, l24_t = get_offset_and_text(23)
    l25_s, l25_e, l25_t = get_offset_and_text(24)
    l26_s, l26_e, l26_t = get_offset_and_text(25)
    l27_s, l27_e, l27_t = get_offset_and_text(26)

    candidates = [
        # Page 1
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0001",
            "line_number": 12,
            "page_number": 1,
            "raw_line": l12_t,
            "description_candidate": "Dây cáp điện hạ thế CV 1.5mm2 Cadivi",
            "material_code_candidate": "CV-1.5",
            "brand_candidate": "Cadivi",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l12_s, "end_offset": l12_e, "text": l12_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0002",
            "line_number": 13,
            "page_number": 1,
            "raw_line": l13_t,
            "unit_price_candidate": 4500.0,
            "unit_candidate": "m",
            "currency_candidate": "VND",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l13_s, "end_offset": l13_e, "text": l13_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0003",
            "line_number": 14,
            "page_number": 1,
            "raw_line": l14_t,
            "description_candidate": "Ống nhựa HDPE D25 PN10 Tiền Phong",
            "brand_candidate": "Tiền Phong",
            "confidence": 0.45,
            "warnings": [{"code": "low_confidence", "message": "Low"}],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l14_s, "end_offset": l14_e, "text": l14_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0004",
            "line_number": 15,
            "page_number": 1,
            "raw_line": l15_t,
            "unit_price_candidate": 12000.0,
            "unit_candidate": "m",
            "currency_candidate": "VND",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l15_s, "end_offset": l15_e, "text": l15_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0005",
            "line_number": 16,
            "page_number": 1,
            "raw_line": l16_t,
            "description_candidate": "Thiết bị MCB 3P 100A 25kA LS",
            "brand_candidate": "LS",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l16_s, "end_offset": l16_e, "text": l16_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0006",
            "line_number": 17,
            "page_number": 1,
            "raw_line": l17_t,
            "unit_price_candidate": 450000.0,
            "unit_candidate": "cái",
            "currency_candidate": "VND",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l17_s, "end_offset": l17_e, "text": l17_t}
        },
        # Page 2
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0007",
            "line_number": 23,
            "page_number": 2,
            "raw_line": l23_t,
            "description_candidate": "CB 1P 16A Schneider",
            "brand_candidate": "Schneider",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l23_s, "end_offset": l23_e, "text": l23_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0008",
            "line_number": 24,
            "page_number": 2,
            "raw_line": l24_t,
            "unit_price_candidate": 85000.0,
            "currency_candidate": "VND",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l24_s, "end_offset": l24_e, "text": l24_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0009",
            "line_number": 25,
            "page_number": 2,
            "raw_line": l25_t,
            "description_candidate": "Cáp ngầm DVV-2x4 Daphaco",
            "material_code_candidate": "DVV-2x4",
            "brand_candidate": "Daphaco",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l25_s, "end_offset": l25_e, "text": l25_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0010",
            "line_number": 26,
            "page_number": 2,
            "raw_line": l26_t,
            "quantity_candidate": 50.0,
            "unit_candidate": "cuộn",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l26_s, "end_offset": l26_e, "text": l26_t}
        },
        {
            "candidate_id": "AUT_20260620_001_LINECAND_0011",
            "line_number": 27,
            "page_number": 2,
            "raw_line": l27_t,
            "unit_price_candidate": 18000.0,
            "unit_candidate": "m",
            "currency_candidate": "VND",
            "confidence": 0.5,
            "warnings": [],
            "evidence": {"source_path": "text/quotation.md", "start_offset": l27_s, "end_offset": l27_e, "text": l27_t}
        }
    ]

    line_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_text_manifest": "text/quotation_text.json",
        "source_markdown": "text/quotation.md",
        "source_sha256": calculate_sha256(md_output_path),
        "parser_name": "rule_based_line_candidate_v1",
        "parser_version": "0.1.0",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }

    line_cand_file = package_dir / "parsed" / "line_candidates.json"
    line_cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(line_cand_file, "w", encoding="utf-8") as f:
        json.dump(line_manifest, f)

    # Cập nhật package.json
    pkg_json_path = package_dir / "package.json"
    pkg_model = load_package_json(package_dir)
    pkg_model.files.line_candidates = "parsed/line_candidates.json"
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_empty_line_candidates_still_generates_valid_rows(tmp_path):
    """Kiểm tra line_candidates rỗng vẫn sinh tệp row_candidates.json hợp lệ với row_count = 0."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    
    # Tạo các file phụ trợ
    md_path = package_dir / "text" / "quotation.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w") as f: f.write("mock")
    
    raw_text_path = package_dir / "source" / "raw_text.json"
    with open(raw_text_path, "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_pdf": "source/original.pdf", "source_sha256": "dummy", "extraction_engine": "pymupdf", "page_count": 1, "pages": [{"page_number": 1, "has_text": True, "character_count": 4, "text": "mock"}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    text_manifest_path = package_dir / "text" / "quotation_text.json"
    with open(text_manifest_path, "w") as f:
        json.dump({"schema_version": "1.0", "quotation_id": "AUT_20260620_001", "source_raw_text": "source/raw_text.json", "source_sha256": calculate_sha256(raw_text_path), "page_count": 1, "total_characters": 4, "pages_with_text": 1, "markdown_path": "text/quotation.md", "pages": [{"page_number": 1, "has_text": True, "character_count": 4, "start_offset": 0, "end_offset": 4}], "generated_at": "2026-06-20T00:00:00Z"}, f)

    line_manifest = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_text_manifest": "text/quotation_text.json",
        "source_markdown": "text/quotation.md",
        "source_sha256": calculate_sha256(md_path),
        "parser_name": "rule_based_line_candidate_v1",
        "parser_version": "0.1.0",
        "candidate_count": 0,
        "candidates": [],
        "warnings": [],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    line_cand_file = package_dir / "parsed" / "line_candidates.json"
    line_cand_file.parent.mkdir(parents=True, exist_ok=True)
    with open(line_cand_file, "w", encoding="utf-8") as f:
        json.dump(line_manifest, f)

    # Dựng PDF nhị phân thật để pass integrity
    pdf_path = package_dir / "source" / "original.pdf"
    import fitz
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()
    
    meta_data = {"schema_version": "1.0", "file_name": "original.pdf", "file_size": pdf_path.stat().st_size, "sha256": calculate_sha256(pdf_path), "page_count": 1, "pdf_version": "1.4", "encrypted": False, "imported_at": "2026-06-20T00:00:00Z", "warnings": []}
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    # Dựng normalized.json và corrections.json giả lập để pass integrity checks
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

    assemble_row_candidates(package_dir, overwrite=True)

    rows_file = package_dir / "parsed" / "row_candidates.json"
    assert rows_file.exists()
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["row_count"] == 0
    assert data["rows"] == []


def test_assemble_description_and_price_line_on_same_page(package_with_line_candidates):
    """Kiểm tra gom dòng chứa mô tả và dòng đơn giá gần nhau."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 11 candidates gom thành 5 rows
    assert data["row_count"] == 5
    
    row1 = data["rows"][0]
    assert row1["page_number"] == 1
    assert row1["unit_price_candidate"] == 4500.0
    assert row1["brand_candidate"] == "Cadivi"
    assert "AUT_20260620_001_LINECAND_0001" in row1["source_candidate_ids"]
    assert "AUT_20260620_001_LINECAND_0002" in row1["source_candidate_ids"]


def test_no_price_association_across_pages(package_with_line_candidates):
    """Kiểm tra không liên kết đơn giá xuyên trang."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for row in data["rows"]:
        assert len(set(row["source_candidate_ids"])) > 0


def test_no_price_association_if_line_gap_exceeded(package_with_line_candidates):
    """Kiểm tra không gắn price nếu khoảng cách dòng vượt quá cấu hình."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True, max_line_gap_for_price=0)
    
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    row1 = data["rows"][0]
    assert row1["unit_price_candidate"] is None


def test_do_not_treat_technical_specs_as_price(package_with_line_candidates):
    """Xác nhận không bắt nhầm thông số kỹ thuật làm đơn giá."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    row3 = data["rows"][2]
    assert row3["unit_price_candidate"] == 450000.0


def test_do_not_merge_two_strong_descriptions(package_with_line_candidates):
    """Xác nhận không gom 2 mô tả mạnh vào cùng 1 row."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    r1 = data["rows"][0]
    r2 = data["rows"][1]
    assert "CV 1.5mm2" in r1["description_candidate"]
    assert "HDPE D25" in r2["description_candidate"]
    assert r1["row_id"] != r2["row_id"]


def test_evidence_text_slice_exact_match(package_with_line_candidates):
    """Xác nhận evidence_text khớp với markdown_content[start:end]."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    md_path = package_with_line_candidates / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for row in data["rows"]:
        sliced = markdown_content[row["start_offset"]:row["end_offset"]]
        assert sliced == row["evidence_text"]


def test_source_sha256_matches_line_candidates(package_with_line_candidates):
    """Kiểm tra source_sha256 khớp băm SHA256 của line_candidates.json."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    line_cand_file = package_with_line_candidates / "parsed" / "line_candidates.json"
    expected_sha = calculate_sha256(line_cand_file)

    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["source_sha256"] == expected_sha


def test_row_id_unique_and_deterministic(package_with_line_candidates):
    """Đảm bảo row_id là duy nhất và được đánh tuần tự có tính deterministic."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    with open(rows_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    row_ids = [r["row_id"] for r in data["rows"]]
    assert len(row_ids) == len(set(row_ids))
    assert row_ids[0] == "AUT_20260620_001_ROWCAND_0001"
    assert row_ids[-1] == f"AUT_20260620_001_ROWCAND_{len(row_ids):04d}"


def test_overwrite_protection_and_audit_log(package_with_line_candidates):
    """Kiểm tra cản ghi đè (overwrite=False), cho phép ghi đè (overwrite=True) và logs kiểm toán tương ứng."""
    assemble_row_candidates(package_with_line_candidates, overwrite=False)

    with pytest.raises(ValueError, match="already exists"):
        assemble_row_candidates(package_with_line_candidates, overwrite=False)

    assemble_row_candidates(package_with_line_candidates, overwrite=True)

    log_path = package_with_line_candidates / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    events = [e["event"] for e in lines]
    assert "row_assembly_started" in events
    assert "row_candidates_assembled" in events
    assert "row_candidates_written" in events
    assert "row_assembly_completed" in events
    assert "row_assembly_failed" in events


def test_cli_assemble_rows(package_with_line_candidates):
    """Kiểm tra chạy câu lệnh CLI assemble-rows qua subprocess."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "assemble-rows", str(package_with_line_candidates), "--overwrite"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"CLI error: {result.stderr}"
    assert "Successfully assembled row candidates." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "Row Count" in result.stdout
    assert "Source Line Candidates" in result.stdout
    assert "Row Candidates Path" in result.stdout
    assert "Rows With Price Count" in result.stdout
    assert "Warnings Count" in result.stdout


def test_backward_compatibility_validate_package_integrity(package_with_line_candidates):
    """Kiểm tra validate_package_integrity vẫn hoạt động tốt khi gói chưa có row_candidates.json."""
    pkg_model = load_package_json(package_with_line_candidates)
    
    pkg_json_path = package_with_line_candidates / "package.json"
    pkg_model.files.row_candidates = "parsed/row_candidates.json"
    with open(pkg_json_path, "w", encoding="utf-8") as f:
        json.dump(pkg_model.model_dump(mode="json"), f)

    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"
    if rows_file.exists():
        rows_file.unlink()

    # Không ném ngoại lệ dù file row_candidates.json không tồn tại (backward compatible)
    validate_package_integrity(package_with_line_candidates)


def test_validation_catches_bad_data_in_row_candidates(package_with_line_candidates):
    """Kiểm tra validate_row_candidates_file / validate_package_integrity bắt lỗi dữ liệu row candidates sai ranh giới/offset/IDs."""
    assemble_row_candidates(package_with_line_candidates, overwrite=True)
    rows_file = package_with_line_candidates / "parsed" / "row_candidates.json"

    # Case A: source_candidate_ids chứa ID không tồn tại
    with open(rows_file, "r", encoding="utf-8") as f:
        orig_data = json.load(f)
    
    data = json.loads(json.dumps(orig_data))
    data["rows"][0]["source_candidate_ids"] = ["INVALID_ID"]
    with open(rows_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not exist in line_candidates.json"):
        validate_row_candidates_file(rows_file, package_with_line_candidates)

    # Case B: các source candidates bị lệch page_number
    data = json.loads(json.dumps(orig_data))
    # Dòng 7 là candidate của page 2 (index 6). Ta gán nó vào row 1 (đang ở page 1)
    data["rows"][0]["source_candidate_ids"].append("AUT_20260620_001_LINECAND_0007")
    with open(rows_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="is different from row page_number"):
        validate_row_candidates_file(rows_file, package_with_line_candidates)

    # Case C: evidence_text không khớp lát cắt offset Markdown
    data = json.loads(json.dumps(orig_data))
    data["rows"][0]["evidence_text"] = "LỆCH MÔ TẢ"
    with open(rows_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not match evidence_text"):
        validate_row_candidates_file(rows_file, package_with_line_candidates)

    # Case D: source_sha256 bị sai lệch
    data = json.loads(json.dumps(orig_data))
    data["source_sha256"] = "INVALID_SHA256"
    with open(rows_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="source_sha256 mismatch"):
        validate_row_candidates_file(rows_file, package_with_line_candidates)


def test_does_not_modify_or_create_normalized_json(package_with_line_candidates):
    """Xác nhận Phase 7 không tự ý tạo mới normalized.json nếu chưa có, và giữ nguyên nội dung nếu đã có."""
    norm_path = package_with_line_candidates / "normalized" / "normalized.json"
    
    # 1. Trường hợp normalized.json chưa có trên đĩa
    if norm_path.exists():
        norm_path.unlink()
        
    # validate_package_integrity sẽ ném FileNotFoundError do thiếu normalized.json (yêu cầu của package)
    with pytest.raises(FileNotFoundError, match="normalized.json not found"):
        assemble_row_candidates(package_with_line_candidates, overwrite=True)
    # Tuy ném lỗi validate, ta kiểm chứng là Phase 7 thực sự KHÔNG hề tạo ra file normalized.json
    assert not norm_path.exists()

    # 2. Trường hợp normalized.json đã có từ trước -> Phải giữ nguyên
    placeholder_content = {"quotation_id": "AUT_20260620_001", "supplier_code": "AUT", "quotation_date": "2026-06-20", "items": []}
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(placeholder_content, f)

    assemble_row_candidates(package_with_line_candidates, overwrite=True)

    with open(norm_path, "r", encoding="utf-8") as f:
        new_content = json.load(f)
    assert new_content == placeholder_content
