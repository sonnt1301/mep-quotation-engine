import json
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfWriter

from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.pdf_text.extractor import extract_pdf_text
from mep_quotation.pdf_text.text_service import extract_package_text
from mep_quotation.spec.models import RawTextManifestModel, RawTextPageModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_mock_pdf(dest_path: Path, pages: int = 2, encrypted_password: str = None) -> Path:
    """Tạo file PDF giả lập bằng pypdf. Blank pages – không có native text layer."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    writer.add_metadata({
        "/CreationDate": "D:20260630000000Z",
        "/ModDate": "D:20260630000000Z"
    })
    if encrypted_password:
        writer.encrypt(encrypted_password)
    with open(dest_path, "wb") as f:
        writer.write(f)
    return dest_path


def create_text_pdf(dest_path: Path, texts: list[str]) -> Path:
    """
    Tạo PDF có native text layer sử dụng PyMuPDF.
    texts: list[str] – một phần tử ứng với một trang.
    """
    import fitz
    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(dest_path))
    doc.close()
    return dest_path


@pytest.fixture
def test_package(tmp_path):
    """Package cơ bản với blank PDF (không có text layer)."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    pdf_path = package_dir / "source" / "original.pdf"
    create_mock_pdf(pdf_path, pages=3)

    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": 3,
        "pdf_version": "1.4",
        "encrypted": False,
        "imported_at": "2026-06-20T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    return package_dir


@pytest.fixture
def text_package(tmp_path):
    """Package với PDF có native text layer."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    pdf_path = package_dir / "source" / "original.pdf"
    create_text_pdf(pdf_path, texts=["Hello World Page One", "Second page content", "Third page"])

    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": 3,
        "pdf_version": "1.4",
        "encrypted": False,
        "imported_at": "2026-06-20T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    return package_dir


@pytest.fixture
def encrypted_package(tmp_path):
    """Package với PDF bị mã hóa."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", seq=1)
    pdf_path = package_dir / "source" / "original.pdf"
    create_mock_pdf(pdf_path, pages=2, encrypted_password="secret")

    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": None,
        "pdf_version": "1.4",
        "encrypted": True,
        "imported_at": "2026-06-20T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    return package_dir


# ---------------------------------------------------------------------------
# Test 1: PDF có text – extract thành công
# ---------------------------------------------------------------------------

def test_extract_pdf_text_with_text(text_package):
    pdf_path = text_package / "source" / "original.pdf"
    result = extract_pdf_text(pdf_path)

    assert isinstance(result, RawTextManifestModel)
    assert result.page_count == 3
    assert len(result.pages) == 3

    # Ít nhất 1 trang phải có text
    assert any(p.has_text for p in result.pages)

    # Kiểm tra trang đầu có chứa text "Hello"
    page1 = result.pages[0]
    assert page1.page_number == 1
    assert page1.has_text is True
    assert "Hello" in page1.text
    assert page1.character_count == len(page1.text)


# ---------------------------------------------------------------------------
# Test 2: PDF không có text layer (blank pages)
# ---------------------------------------------------------------------------

def test_extract_pdf_text_no_text(test_package):
    pdf_path = test_package / "source" / "original.pdf"
    result = extract_pdf_text(pdf_path)

    assert result.page_count == 3
    # Blank pages không có text
    for page in result.pages:
        assert page.has_text is False
        assert page.text == ""
        assert page.character_count == 0


# ---------------------------------------------------------------------------
# Test 3: PDF encrypted – phải fail rõ ràng
# ---------------------------------------------------------------------------

def test_extract_pdf_text_encrypted(encrypted_package):
    pdf_path = encrypted_package / "source" / "original.pdf"
    with pytest.raises(ValueError, match="encrypted"):
        extract_pdf_text(pdf_path)


def test_extract_package_text_encrypted_audit_failed(encrypted_package):
    with pytest.raises(ValueError, match="encrypted"):
        extract_package_text(encrypted_package, overwrite=False)

    assert not (encrypted_package / "source" / "raw_text.json").exists()

    log_path = encrypted_package / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line)["event"] for line in f if line.strip()]

    assert "pdf_text_extraction_failed" in events


# ---------------------------------------------------------------------------
# Test 4: Pydantic schema hợp lệ
# ---------------------------------------------------------------------------

def test_raw_text_schema_valid(text_package):
    pdf_path = text_package / "source" / "original.pdf"
    result = extract_pdf_text(pdf_path)
    result.quotation_id = "AUT_20260620_001"

    # Serialize và deserialize lại – phải pass
    data = result.model_dump(mode="json")
    restored = RawTextManifestModel(**data)
    assert restored.quotation_id == "AUT_20260620_001"
    assert restored.page_count == result.page_count
    assert len(restored.pages) == len(result.pages)


# ---------------------------------------------------------------------------
# Test 5: character_count chính xác
# ---------------------------------------------------------------------------

def test_character_count_accuracy(text_package):
    pdf_path = text_package / "source" / "original.pdf"
    result = extract_pdf_text(pdf_path)

    for page in result.pages:
        assert page.character_count == len(page.text), (
            f"Page {page.page_number}: character_count={page.character_count} "
            f"but len(text)={len(page.text)}"
        )


# ---------------------------------------------------------------------------
# Test 6: page_count khớp số trang PDF thực tế
# ---------------------------------------------------------------------------

def test_page_count_matches_pdf(text_package):
    import fitz
    pdf_path = text_package / "source" / "original.pdf"
    doc = fitz.open(pdf_path)
    actual_pages = len(doc)
    doc.close()

    result = extract_pdf_text(pdf_path)
    assert result.page_count == actual_pages


# ---------------------------------------------------------------------------
# Test 7: Cross-check page_count với metadata.json
# ---------------------------------------------------------------------------

def test_page_count_cross_check_metadata(text_package):
    # Chạy extract_package_text để có full validation
    extract_package_text(text_package, overwrite=False)
    raw_text_path = text_package / "source" / "raw_text.json"
    with open(raw_text_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(text_package / "source" / "metadata.json", "r") as f:
        meta = json.load(f)

    assert data["page_count"] == meta["page_count"]


# ---------------------------------------------------------------------------
# Test 8: Cross-check page_count với page_manifest.json
# ---------------------------------------------------------------------------

def test_page_count_cross_check_page_manifest(text_package):
    """
    Kiểm tra cross-check page_count giữa raw_text.json và page_manifest.json.
    Gọi validate_raw_text_file trực tiếp để tránh integrity check Phase 3
    yêu cầu ảnh trang thực tế tồn tại trong source/pages/.
    """
    from mep_quotation.pdf_text.manifest import validate_raw_text_file
    from mep_quotation.pdf_text.text_service import extract_package_text

    # Extract text trước (không có page_manifest)
    extract_package_text(text_package, overwrite=False)

    # Inject page_manifest.json với đúng page_count để cross-check pass
    manifest_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_pdf": "source/original.pdf",
        "page_count": 3,
        "dpi": 150,
        "image_format": "png",
        "pages": [
            {"page_number": i, "image_path": f"source/pages/page_{i:04d}.png",
             "width": 100, "height": 100, "rotation": 0,
             "sha256": "abc", "file_size": 100}
            for i in range(1, 4)
        ],
        "generated_at": "2026-06-20T00:00:00Z"
    }
    pm_path = text_package / "source" / "page_manifest.json"
    with open(pm_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f)

    # Validate trực tiếp – phải pass vì page_count khớp
    raw_text_path = text_package / "source" / "raw_text.json"
    validate_raw_text_file(raw_text_path, text_package)

    # Inject page_manifest.json với page_count sai để cross-check fail
    manifest_data_wrong = dict(manifest_data)
    manifest_data_wrong["page_count"] = 99
    with open(pm_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data_wrong, f)

    with pytest.raises(ValueError, match="page_manifest.json page_count"):
        validate_raw_text_file(raw_text_path, text_package)


# ---------------------------------------------------------------------------
# Test 9: Luồng hoàn chỉnh – package.json được cập nhật
# ---------------------------------------------------------------------------

def test_extract_package_text_flow(text_package):
    result_path = extract_package_text(text_package, overwrite=False)
    assert result_path == text_package

    # raw_text.json phải tồn tại
    raw_text_path = text_package / "source" / "raw_text.json"
    assert raw_text_path.exists()

    # package.json phải có files.raw_text
    pkg = load_package_json(text_package)
    assert pkg.files.raw_text == "source/raw_text.json"

    # Validate toàn vẹn package phải pass
    validate_package_integrity(text_package)

    # Đọc raw_text.json và kiểm tra cấu trúc
    with open(raw_text_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["quotation_id"] == "AUT_20260620_001"
    assert data["page_count"] == 3
    assert len(data["pages"]) == 3
    assert data["extraction_engine"] == "pymupdf"
    assert data["source_pdf"] == "source/original.pdf"


# ---------------------------------------------------------------------------
# Test 10: Overwrite=False phải fail nếu file đã tồn tại
# ---------------------------------------------------------------------------

def test_overwrite_false_fail(text_package):
    # Extract lần đầu
    extract_package_text(text_package, overwrite=False)

    # Extract lần hai – phải fail
    with pytest.raises(ValueError, match="raw_text.json already exists"):
        extract_package_text(text_package, overwrite=False)


# ---------------------------------------------------------------------------
# Test 11: Overwrite=True phải thành công và ghi audit có overwrite=True
# ---------------------------------------------------------------------------

def test_overwrite_true_pass(text_package):
    # Extract lần đầu
    extract_package_text(text_package, overwrite=False)

    # Extract lần hai với overwrite=True – phải pass
    extract_package_text(text_package, overwrite=True)

    # Kiểm tra audit log có event với overwrite=True
    log_path = text_package / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]

    started_events = [
        e for e in lines
        if e.get("event") == "pdf_text_extraction_started"
        and e.get("details", {}).get("overwrite") is True
    ]
    assert len(started_events) >= 1, "Audit event with overwrite=True not found"


# ---------------------------------------------------------------------------
# Test 12: source_sha256 traceability
# ---------------------------------------------------------------------------

def test_source_sha256_traceability(text_package):
    extract_package_text(text_package, overwrite=False)

    raw_text_path = text_package / "source" / "raw_text.json"
    with open(raw_text_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pdf_path = text_package / "source" / "original.pdf"
    expected_sha256 = calculate_sha256(pdf_path)
    assert data["source_sha256"] == expected_sha256


# ---------------------------------------------------------------------------
# Test 13: CLI extract-text qua subprocess
# ---------------------------------------------------------------------------

def test_cli_extract_text(text_package):
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "extract-text", str(text_package)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "Successfully extracted PDF text." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "Page Count" in result.stdout
    assert "Total Characters" in result.stdout
    assert "Pages With Text" in result.stdout


# ---------------------------------------------------------------------------
# Test 14: Audit events – success path có đủ 4 events theo thứ tự
# ---------------------------------------------------------------------------

def test_audit_events(text_package):
    extract_package_text(text_package, overwrite=False)

    log_path = text_package / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line)["event"] for line in f if line.strip()]

    expected_success_events = [
        "pdf_text_extraction_started",
        "pdf_text_extracted",
        "raw_text_written",
        "pdf_text_extraction_completed"
    ]

    # Lấy 4 event của Phase 4 (bỏ qua các event Phase khác)
    phase4_events = [e for e in events if e.startswith("pdf_text_") or e == "raw_text_written"]
    assert phase4_events == expected_success_events, (
        f"Expected events {expected_success_events}, got {phase4_events}"
    )

    # Không được có pdf_text_extraction_failed trong success path
    assert "pdf_text_extraction_failed" not in phase4_events
