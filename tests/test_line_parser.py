import json
import subprocess
import sys
from pathlib import Path

import pytest

from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.parser.line_parser import parse_markdown_line, scan_markdown_lines
from mep_quotation.parser.parser_service import parse_package_line_candidates
from mep_quotation.parser.candidate_manifest import validate_line_candidates_file
from mep_quotation.spec.models import LineCandidatesManifestModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def package_with_text_assembly(tmp_path):
    """Tạo một package đã đi qua Phase 5 (có quotation.md và quotation_text.json)."""
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

    # 3. Dựng quotation.md
    md_content = (
        "# Quotation Text\n\n"
        "Quotation ID: AUT_20260620_001\n"
        "Source PDF: source/original.pdf\n"
        "Page Count: 2\n"
        "Generated At: 2026-06-20T00:00:00Z\n\n"
        "---\n\n"
        "## Page 1\n\n"
        "Dây cáp điện hạ thế CV 1.5mm2 Cadivi giá 4500 VND/m\n"
        "Ống nhựa HDPE D25 PN10 Tiền Phong giá 12000 VND/m\n"
        "Thiết bị MCB 3P 100A 25kA LS giá 450000 VND/cái\n\n"
        "---\n\n"
        "## Page 2\n\n"
        "CB 1P 16A Schneider giá 85000\n"
        "Cáp ngầm DVV-2x4 Daphaco Số lượng: 50 cuộn giá 18000 VNĐ/m\n"
        "Mặt nạ 3 lỗ Panasonic giá 15000 đồng\n"
        "Tủ điện phân phối thô không có giá rõ ràng 9999\n"
    )
    md_output_path = package_dir / "text" / "quotation.md"
    md_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 4. Dựng quotation_text.json với các offset tương ứng
    # Tính offset thô cho page 1 và page 2
    idx1 = md_content.find("## Page 1")
    idx2 = md_content.find("## Page 2")
    
    # 4. Tạo tệp raw_text.json giả lập để kiểm tra toàn vẹn backward compatible
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
            {
                "page_number": 1,
                "has_text": True,
                "character_count": idx2 - idx1,
                "text": md_content[idx1:idx2]
            },
            {
                "page_number": 2,
                "has_text": True,
                "character_count": len(md_content) - idx2,
                "text": md_content[idx2:len(md_content)]
            }
        ],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    with open(raw_text_path, "w", encoding="utf-8") as f:
        json.dump(raw_text, f)

    # 5. Dựng quotation_text.json với các offset tương ứng và SHA256 thực tế của raw_text.json
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


    return package_dir


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_parse_simple_line_with_price_unit():
    """Kiểm tra việc bóc tách một dòng cơ bản có giá và đơn vị tính."""
    line = "Dây cáp điện hạ thế CV 1.5mm2 Cadivi giá 4500 VND/m"
    cand = parse_markdown_line(line, line_number=1, page_number=1, start_offset=0, end_offset=len(line), quotation_id="Q")
    
    assert cand is not None
    assert cand.unit_price_candidate == 4500.0
    assert cand.unit_candidate == "m"
    assert cand.brand_candidate == "Cadivi"
    assert cand.currency_candidate == "VND"


def test_do_not_treat_technical_specs_as_price():
    """Kiểm tra loại trừ không bắt nhầm thông số kỹ thuật (1.5mm2, 100A, 25kA, D25, PN10, 3P, Ø25) làm đơn giá."""
    # Thử nghiệm dòng không có giá nhưng chứa nhiều spec
    line = "Ống nhựa HDPE D25 PN10 Tiền Phong Ø25"
    cand = parse_markdown_line(line, line_number=1, page_number=1, start_offset=0, end_offset=len(line), quotation_id="Q")
    
    # 25 (trong D25, Ø25) và 10 (trong PN10) không được coi là đơn giá
    if cand:
        assert cand.unit_price_candidate is None

    # Dòng chứa cả spec và giá thực tế ở cuối
    line_with_price = "MCB 3P 100A 25kA LS giá 450000 VND"
    cand2 = parse_markdown_line(line_with_price, line_number=2, page_number=1, start_offset=0, end_offset=len(line_with_price), quotation_id="Q")
    assert cand2 is not None
    # 3, 100, 25 không được bắt. 450000 phải được bắt làm đơn giá.
    assert cand2.unit_price_candidate == 450000.0


def test_parse_price_with_marker_or_safe_ending():
    """Kiểm tra nhận diện đơn giá bằng marker tiền tệ hoặc token cuối dòng >= 1000."""
    # Marker VNĐ
    l1 = "Dây cáp điện hạ thế Cadivi giá 18000 VNĐ/m"
    cand1 = parse_markdown_line(l1, 1, 1, 0, len(l1), "Q")
    assert cand1.unit_price_candidate == 18000.0

    # Token cuối dòng >= 1000, không có marker
    l2 = "CB 1P 16A Schneider giá 85000"
    cand2 = parse_markdown_line(l2, 2, 1, 0, len(l2), "Q")
    assert cand2.unit_price_candidate == 85000.0

    # Token cuối dòng < 1000, không có marker -> không được bắt làm đơn giá (đặt None)
    l3 = "CB 1P 16A Schneider số lượng 50"
    cand3 = parse_markdown_line(l3, 3, 1, 0, len(l3), "Q")
    if cand3:
        assert cand3.unit_price_candidate is None


def test_parse_brand():
    """Kiểm tra nhận diện thương hiệu từ cấu hình MEP cứng."""
    l1 = "Thiết bị MCB 3P 100A LS giá 450000 VND"
    cand1 = parse_markdown_line(l1, 1, 1, 0, len(l1), "Q")
    assert cand1.brand_candidate == "LS"

    l2 = "Mặt nạ 3 lỗ Panasonic giá 15000"
    cand2 = parse_markdown_line(l2, 2, 1, 0, len(l2), "Q")
    assert cand2.brand_candidate == "Panasonic"


def test_quantity_missing_warning_logic():
    """Kiểm tra logic cảnh báo quantity_missing chỉ khi dòng đủ cấu trúc vật tư."""
    # Không đủ cấu trúc (thiếu brand, đơn vị) -> không tự động cảnh báo
    l1 = "CB 1P 16A Schneider giá 85000"
    cand1 = parse_markdown_line(l1, 1, 1, 0, len(l1), "Q")
    warnings_code = [w.code for w in cand1.warnings]
    assert "quantity_missing" not in warnings_code

    # Đủ cấu trúc (có mep keyword 'dây', đơn giá, đơn vị 'm') nhưng thiếu số lượng -> phải có warning
    l2 = "Dây cáp điện Cadivi giá 18000 VND/m"
    cand2 = parse_markdown_line(l2, 2, 1, 0, len(l2), "Q")
    warnings_code_2 = [w.code for w in cand2.warnings]
    assert "quantity_missing" in warnings_code_2


def test_ignore_markdown_headings_and_separators(package_with_text_assembly):
    """Kiểm tra line scanner tự động bỏ qua các tiêu đề và dấu ngăn cách Markdown."""
    md_path = package_with_text_assembly / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(package_with_text_assembly / "text" / "quotation_text.json", "r", encoding="utf-8") as f:
        text_manifest_data = json.load(f)
    from mep_quotation.spec.models import TextAssemblyManifestModel
    text_manifest = TextAssemblyManifestModel(**text_manifest_data)

    candidates = scan_markdown_lines(md_content, text_manifest, "AUT_20260620_001")
    
    # Không được chứa các dòng tiêu đề làm candidate
    for cand in candidates:
        assert not cand.raw_line.startswith("#")
        assert cand.raw_line.strip() != "---"


def test_line_number_one_based(package_with_text_assembly):
    """Kiểm tra line_number được tính 1-based theo toàn bộ markdown."""
    md_path = package_with_text_assembly / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    lines = md_content.splitlines(keepends=True)

    with open(package_with_text_assembly / "text" / "quotation_text.json", "r", encoding="utf-8") as f:
        text_manifest_data = json.load(f)
    from mep_quotation.spec.models import TextAssemblyManifestModel
    text_manifest = TextAssemblyManifestModel(**text_manifest_data)

    candidates = scan_markdown_lines(md_content, text_manifest, "AUT_20260620_001")
    
    # Dựa vào md_content, dòng này nằm sau header và các dòng trống, là dòng thứ 12
    first_cand = candidates[0]
    assert first_cand.line_number == 12
    assert first_cand.raw_line.strip() == lines[11].strip()


def test_evidence_slice_exact_match(package_with_text_assembly):
    """Xác nhận evidence.text khớp chuẩn xác với markdown_content[start:end]."""
    md_path = package_with_text_assembly / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(package_with_text_assembly / "text" / "quotation_text.json", "r", encoding="utf-8") as f:
        text_manifest_data = json.load(f)
    from mep_quotation.spec.models import TextAssemblyManifestModel
    text_manifest = TextAssemblyManifestModel(**text_manifest_data)

    candidates = scan_markdown_lines(md_content, text_manifest, "AUT_20260620_001")
    
    for cand in candidates:
        ev = cand.evidence
        sliced = md_content[ev.start_offset:ev.end_offset]
        assert sliced == ev.text
        assert sliced == cand.raw_line


def test_page_number_mapping_from_offset(package_with_text_assembly):
    """Kiểm tra ánh xạ page_number dựa vào offset và quotation_text.json."""
    md_path = package_with_text_assembly / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(package_with_text_assembly / "text" / "quotation_text.json", "r", encoding="utf-8") as f:
        text_manifest_data = json.load(f)
    from mep_quotation.spec.models import TextAssemblyManifestModel
    text_manifest = TextAssemblyManifestModel(**text_manifest_data)

    candidates = scan_markdown_lines(md_content, text_manifest, "AUT_20260620_001")
    
    # 3 dòng đầu nằm ở Page 1
    # 4 dòng sau nằm ở Page 2
    assert candidates[0].page_number == 1
    assert candidates[1].page_number == 1
    assert candidates[2].page_number == 1
    
    assert candidates[3].page_number == 2
    assert candidates[4].page_number == 2
    assert candidates[5].page_number == 2
    assert candidates[6].page_number == 2


def test_candidate_id_format_and_uniqueness(package_with_text_assembly):
    """Kiểm tra candidate_id duy nhất và đúng định dạng {QUOTATION_ID}_LINECAND_{SEQ}."""
    md_path = package_with_text_assembly / "text" / "quotation.md"
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    with open(package_with_text_assembly / "text" / "quotation_text.json", "r", encoding="utf-8") as f:
        text_manifest_data = json.load(f)
    from mep_quotation.spec.models import TextAssemblyManifestModel
    text_manifest = TextAssemblyManifestModel(**text_manifest_data)

    candidates = scan_markdown_lines(md_content, text_manifest, "AUT_20260620_001")
    
    seen_ids = set()
    for idx, cand in enumerate(candidates, 1):
        assert cand.candidate_id == f"AUT_20260620_001_LINECAND_{idx:04d}"
        assert cand.candidate_id not in seen_ids
        seen_ids.add(cand.candidate_id)


def test_confidence_calculation_deterministic():
    """Kiểm tra tính toán confidence thô theo đúng thang điểm cộng dồn."""
    # Base 0.3 + 0.2 (price) + 0.15 (unit) + 0.15 (brand) = 0.8
    l1 = "Dây cáp điện hạ thế CV 1.5mm2 Cadivi giá 4500 VND/m"
    cand1 = parse_markdown_line(l1, 1, 1, 0, len(l1), "Q")
    assert cand1.confidence == 0.8

    # Base 0.3 + 0.15 (brand) = 0.45 (< 0.5 -> low_confidence warning)
    # Cần thêm từ khóa MEP 'ổ cắm' để được nhận diện là candidate
    l2 = "Ổ cắm Panasonic"
    cand2 = parse_markdown_line(l2, 2, 1, 0, len(l2), "Q")
    assert cand2.confidence == 0.45
    warnings_code = [w.code for w in cand2.warnings]
    assert "low_confidence" in warnings_code


def test_validation_catches_bad_evidence_offset(package_with_text_assembly):
    """Kiểm tra validate báo lỗi nếu dữ liệu offset trong evidence bị sai."""
    parse_package_line_candidates(package_with_text_assembly, overwrite=False)
    
    manifest_path = package_with_text_assembly / "parsed" / "line_candidates.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Làm lệch offset của candidate đầu tiên
    data["candidates"][0]["evidence"]["start_offset"] = 9999
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="does not match evidence text"):
        validate_line_candidates_file(manifest_path, package_with_text_assembly)


def test_overwrite_protection_and_audit_log(package_with_text_assembly):
    """Kiểm tra cản ghi đè, ghi đè được phép, và logs kiểm toán."""
    # Lần 1 -> Pass
    parse_package_line_candidates(package_with_text_assembly, overwrite=False)

    # Lần 2 với overwrite=False -> Fail và ghi audit line_parser_failed
    with pytest.raises(ValueError, match="already exists"):
        parse_package_line_candidates(package_with_text_assembly, overwrite=False)

    # Lần 2 với overwrite=True -> Pass
    parse_package_line_candidates(package_with_text_assembly, overwrite=True)

    # Kiểm tra log
    log_path = package_with_text_assembly / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    events = [e["event"] for e in lines]
    assert "line_parser_started" in events
    assert "line_parser_lines_scanned" in events
    assert "line_candidates_extracted" in events
    assert "line_candidates_written" in events
    assert "line_parser_completed" in events
    assert "line_parser_failed" in events


def test_cli_parse_line_candidates(package_with_text_assembly):
    """Kiểm tra chạy câu lệnh CLI parse-line-candidates qua subprocess."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "parse-line-candidates", str(package_with_raw_text_or_assembly(package_with_text_assembly))
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"CLI error: {result.stderr}"
    assert "Successfully extracted line candidates." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "Candidate Count" in result.stdout
    assert "Source Markdown" in result.stdout
    assert "Candidates Path" in result.stdout
    assert "Warnings Count" in result.stdout


def test_does_not_create_normalized_json(package_with_text_assembly):
    """Xác nhận Phase 6 không tạo hoặc ghi đè normalized/normalized.json."""
    norm_path = package_with_text_assembly / "normalized" / "normalized.json"
    
    # Đọc nội dung ban đầu
    with open(norm_path, "r", encoding="utf-8") as f:
        orig_content = f.read()

    # Chạy trích xuất candidates
    parse_package_line_candidates(package_with_text_assembly, overwrite=True)
    
    # Tuyệt đối không thay đổi hay ghi đè normalized.json
    with open(norm_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert orig_content == new_content


# Helper để vượt qua pytest fixture argument
def package_with_raw_text_or_assembly(package):
    return package


def test_validation_catches_tampered_page_number(package_with_text_assembly):
    """Kiểm tra validate báo lỗi nếu thay đổi page_number của candidate lệch khỏi range offset."""
    parse_package_line_candidates(package_with_text_assembly, overwrite=False)
    
    manifest_path = package_with_text_assembly / "parsed" / "line_candidates.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Đổi page_number của candidate đầu tiên (đang ở page 1) sang page 2
    data["candidates"][0]["page_number"] = 2
    
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="is out of the bounds"):
        validate_line_candidates_file(manifest_path, package_with_text_assembly)


def test_scan_markdown_lines_raises_error_for_out_of_bounds_offset():
    """Kiểm tra scan_markdown_lines ném lỗi ValueError nếu offset của dòng không thuộc trang nào."""
    from mep_quotation.spec.models import TextAssemblyManifestModel
    
    md_content = "Dây cáp điện hạ thế CV 1.5mm2 Cadivi giá 4500 VND/m\n"
    
    # Tạo TextAssemblyManifestModel giả lập nhưng có range offset bị lệch (từ index 100 đến 200)
    # Do đó index 0-51 của dòng trên sẽ không map được vào trang nào.
    assembly_manifest = TextAssemblyManifestModel(
        schema_version="1.0",
        quotation_id="Q",
        source_raw_text="source/raw_text.json",
        source_sha256="sha",
        page_count=1,
        total_characters=100,
        pages_with_text=1,
        markdown_path="text/quotation.md",
        pages=[
            {
                "page_number": 1,
                "has_text": True,
                "character_count": 100,
                "start_offset": 100,
                "end_offset": 200
            }
        ],
        generated_at="2026-06-20T00:00:00Z"
    )
    
    with pytest.raises(ValueError, match="does not map to any page"):
        scan_markdown_lines(md_content, assembly_manifest, "Q")

