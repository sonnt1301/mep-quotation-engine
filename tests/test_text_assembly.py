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
from mep_quotation.pdf_text.text_service import extract_package_text
from mep_quotation.text_assembly.assembler import assemble_raw_text
from mep_quotation.text_assembly.assembly_service import assemble_package_text
from mep_quotation.text_assembly.manifest import validate_assembly_manifest_file
from mep_quotation.spec.models import TextAssemblyManifestModel


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

def create_text_pdf(dest_path: Path, texts: list[str]) -> Path:
    """Tạo PDF có native text layer sử dụng PyMuPDF."""
    import fitz
    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), text, fontsize=12)
    doc.save(str(dest_path))
    doc.close()
    return dest_path


@pytest.fixture
def package_with_raw_text(tmp_path):
    """Tạo một package hoàn chỉnh đã trích xuất raw_text.json."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "CADIVI", "2026-06-25", seq=2)
    pdf_path = package_dir / "source" / "original.pdf"
    
    # PDF chứa văn bản thô đặc biệt có chứa khoảng trắng và xuống dòng phức tạp
    texts = [
        "CADIVI - CÔNG TY DÂY CÁP ĐIỆN VN\nBẢNG BÁO GIÁ CHI TIẾT",
        "Trang 2: Dây cáp điện hạ thế CV 1.5\nĐơn giá: 4,500 VND/m",
        "   Trang 3: Cáp ngầm DVV 2x4 \n   Đơn giá: 12,000 VND/m   \n"
    ]
    create_text_pdf(pdf_path, texts)

    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": calculate_sha256(pdf_path),
        "page_count": 3,
        "pdf_version": "1.4",
        "encrypted": False,
        "imported_at": "2026-06-25T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)

    # Chạy trích xuất raw_text ở Phase 4
    extract_package_text(package_dir, overwrite=False)
    return package_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_assemble_raw_text_success(package_with_raw_text):
    """Kiểm tra việc lắp ghép raw_text thành công và định vị offset chính xác."""
    raw_text_path = package_with_raw_text / "source" / "raw_text.json"
    markdown_content, manifest = assemble_raw_text(raw_text_path)

    assert isinstance(manifest, TextAssemblyManifestModel)
    assert manifest.quotation_id == "CADIVI_20260625_002"
    assert manifest.page_count == 3
    assert len(manifest.pages) == 3
    assert manifest.pages_with_text == 3

    # Đọc lại file raw_text.json nguồn để so khớp nội dung
    with open(raw_text_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Đối chiếu xem markdown_content[start_offset:end_offset] có khớp 100% text gốc
    for i, page in enumerate(manifest.pages):
        raw_text_orig = raw_data["pages"][i]["text"]
        sliced_text = markdown_content[page.start_offset:page.end_offset]
        
        assert sliced_text == raw_text_orig, f"Text mismatch on page {page.page_number}"
        assert page.character_count == len(raw_text_orig)


def test_assemble_no_alteration(package_with_raw_text):
    """Xác nhận không trim, normalize, hay can thiệp vào khoảng trắng của văn bản gốc."""
    raw_text_path = package_with_raw_text / "source" / "raw_text.json"
    markdown_content, manifest = assemble_raw_text(raw_text_path)

    with open(raw_text_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Kiểm tra page 3 chứa nhiều khoảng trắng ở đầu và cuối trang
    raw_page_3_text = raw_data["pages"][2]["text"]
    assert raw_page_3_text.startswith("   ")
    assert raw_page_3_text.endswith("   \n")

    page_3_assembly = manifest.pages[2]
    sliced_text = markdown_content[page_3_assembly.start_offset:page_3_assembly.end_offset]
    assert sliced_text == raw_page_3_text


def test_assemble_markdown_structure(package_with_raw_text):
    """Kiểm tra định dạng heading Markdown của từng trang."""
    raw_text_path = package_with_raw_text / "source" / "raw_text.json"
    markdown_content, _ = assemble_raw_text(raw_text_path)

    # Kiểm tra tiêu đề lớn và headings từng trang
    assert "# Quotation Text" in markdown_content
    assert "Quotation ID: CADIVI_20260625_002" in markdown_content
    assert "---" in markdown_content
    assert "## Page 1" in markdown_content
    assert "## Page 2" in markdown_content
    assert "## Page 3" in markdown_content


def test_missing_raw_text_fail(tmp_path):
    """Kiểm tra báo lỗi rõ ràng nếu thiếu file raw_text.json và ghi log text_assembly_failed."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "CADIVI", "2026-06-25", seq=2)
    
    with pytest.raises(FileNotFoundError, match="raw_text.json file not found"):
        assemble_package_text(package_dir, overwrite=False)

    # Kiểm tra xem có log text_assembly_failed hay không
    log_path = package_dir / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    failed_events = [e for e in events if e.get("event") == "text_assembly_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].get("level") == "ERROR"
    assert "raw_text.json file not found" in failed_events[0].get("details", {}).get("error", "")


def test_overwrite_protection(package_with_raw_text):
    """Kiểm tra overwrite=False cản ghi đè và ghi log text_assembly_failed khi lỗi."""
    # Chạy lần đầu -> Thành công
    assemble_package_text(package_with_raw_text, overwrite=False)

    # Chạy lần hai với overwrite=False -> Phải fail
    with pytest.raises(ValueError, match="already exists"):
        assemble_package_text(package_with_raw_text, overwrite=False)

    # Kiểm tra xem có log text_assembly_failed cho lần chạy thứ hai bị fail
    log_path = package_with_raw_text / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    failed_events = [e for e in events if e.get("event") == "text_assembly_failed"]
    assert len(failed_events) >= 1
    assert failed_events[0].get("level") == "ERROR"
    assert "already exists" in failed_events[0].get("details", {}).get("error", "")

    # Chạy lần hai với overwrite=True -> Phải pass
    assemble_package_text(package_with_raw_text, overwrite=True)


def test_integrity_compatibility(package_with_raw_text):
    """Kiểm tra toàn vẹn package sau khi chạy Text Assembly phải vượt qua thành công."""
    assemble_package_text(package_with_raw_text, overwrite=False)
    
    # Chạy đối chiếu toàn vẹn package
    validate_package_integrity(package_with_raw_text)


def test_cli_assemble_text(package_with_raw_text):
    """Kiểm tra chạy câu lệnh CLI assemble-text thông qua subprocess."""
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main",
            "assemble-text", str(package_with_raw_text)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, f"CLI output error: {result.stderr}"
    assert "Successfully assembled PDF text." in result.stdout
    assert "Quotation ID" in result.stdout
    assert "CADIVI_20260625_002" in result.stdout
    assert "Page Count" in result.stdout
    assert "Total Characters" in result.stdout
    assert "Markdown Path" in result.stdout
    assert "Manifest Path" in result.stdout


def test_audit_events_trail(package_with_raw_text):
    """Xác nhận các sự kiện log kiểm toán được ghi đầy đủ và theo đúng thứ tự."""
    assemble_package_text(package_with_raw_text, overwrite=False)

    log_path = package_with_raw_text / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line)["event"] for line in f if line.strip()]

    # Các sự kiện dự kiến của Phase 5
    expected_success_events = [
        "text_assembly_started",
        "text_assembled",
        "quotation_markdown_written",
        "quotation_text_manifest_written",
        "text_assembly_completed"
    ]

    # Lọc lấy các sự kiện của Phase 5
    phase5_events = [
        e for e in events 
        if e in expected_success_events or e == "text_assembly_failed"
    ]

    assert phase5_events == expected_success_events
    assert "text_assembly_failed" not in phase5_events


def test_audit_event_failed(package_with_raw_text):
    """Kiểm tra log kiểm toán ghi nhận sự kiện thất bại khi xảy ra lỗi lúc parse JSON raw_text."""
    # Làm hỏng file raw_text.json để gây lỗi lúc parse dữ liệu
    raw_text_path = package_with_raw_text / "source" / "raw_text.json"
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write("invalid json content")

    with pytest.raises(Exception):
        assemble_package_text(package_with_raw_text, overwrite=True)

    log_path = package_with_raw_text / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line)["event"] for line in f if line.strip()]

    assert "text_assembly_failed" in events


def test_encrypted_package_assembly_fail(tmp_path):
    """Kiểm tra PDF bị mã hóa (cờ encrypted: true) -> ném lỗi và ghi log text_assembly_failed."""
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "CADIVI", "2026-06-25", seq=3)
    
    # Tạo file original.pdf giả lập
    pdf_path = package_dir / "source" / "original.pdf"
    with open(pdf_path, "w") as f:
        f.write("mock pdf content")
        
    # Tạo metadata.json giả lập với cờ encrypted = True
    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": 100,
        "sha256": "dummy_sha256",
        "page_count": 2,
        "pdf_version": "1.4",
        "encrypted": True,
        "imported_at": "2026-06-25T00:00:00Z",
        "warnings": []
    }
    with open(package_dir / "source" / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    # Tạo raw_text.json giả lập để vượt qua check file tồn tại nếu chạy tiếp
    raw_text_path = package_dir / "source" / "raw_text.json"
    with open(raw_text_path, "w", encoding="utf-8") as f:
        f.write("{}")

    with pytest.raises(ValueError, match="is encrypted"):
        assemble_package_text(package_dir, overwrite=False)

    log_path = package_dir / "logs" / "processing.log.jsonl"
    with open(log_path, "r", encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]

    failed_events = [e for e in events if e.get("event") == "text_assembly_failed"]
    assert len(failed_events) == 1
    assert failed_events[0].get("level") == "ERROR"
    assert "is encrypted" in failed_events[0].get("details", {}).get("error", "")

