import json
import pytest
import sys
import shutil
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter

from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.pdf.validator import validate_pdf
from mep_quotation.pdf.metadata import extract_pdf_metadata, parse_pdf_date
from mep_quotation.pdf.importer import import_pdf
from mep_quotation.package import load_package_json
from mep_quotation.cli.main import main

# Helper function để tạo file PDF giả lập
def create_mock_pdf(dest_path: Path, pages: int = 1, encrypted_password: str = None) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    
    # Nạp metadata CreationDate và ModDate giả lập
    writer.add_metadata({
        "/CreationDate": "D:20260630000000Z",
        "/ModDate": "D:20260630000000Z"
    })
    
    if encrypted_password:
        writer.encrypt(encrypted_password)
        
    with open(dest_path, "wb") as f:
        writer.write(f)
    return dest_path

# 1. Test SHA256 checksum
def test_sha256_checksum(tmp_path):
    temp_file = tmp_path / "test.txt"
    temp_file.write_bytes(b"hello world")
    
    # Mã băm SHA256 của "hello world"
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert calculate_sha256(temp_file) == expected

# 2. Test PDF validator (valid file)
def test_validator_valid_file(tmp_path):
    pdf_path = tmp_path / "valid.pdf"
    create_mock_pdf(pdf_path, pages=1)
    
    result = validate_pdf(pdf_path)
    assert result.is_valid is True
    assert len(result.warnings) == 0

# 3. Test PDF validator (file không tồn tại)
def test_validator_not_found():
    with pytest.raises(FileNotFoundError, match="PDF file not found"):
        validate_pdf(Path("non_existent_file.pdf"))

# 4. Test PDF validator (không phải file mà là folder)
def test_validator_is_directory(tmp_path):
    dir_path = tmp_path / "sub_dir"
    dir_path.mkdir()
    with pytest.raises(ValueError, match="Path is a directory"):
        validate_pdf(dir_path)

# 5. Test PDF validator (sai extension)
def test_validator_invalid_extension(tmp_path):
    file_path = tmp_path / "invalid.txt"
    file_path.write_text("not a pdf")
    with pytest.raises(ValueError, match="Invalid file extension"):
        validate_pdf(file_path)

# 6. Test PDF validator (file rỗng 0 bytes)
def test_validator_empty_file(tmp_path):
    file_path = tmp_path / "empty.pdf"
    file_path.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        validate_pdf(file_path)

# 7. Test PDF validator (header không đúng %PDF-)
def test_validator_invalid_header(tmp_path):
    file_path = tmp_path / "bad_header.pdf"
    file_path.write_bytes(b"BADHEADER\nrest of file")
    with pytest.raises(ValueError, match="header does not start with"):
        validate_pdf(file_path)

# 8. Test PDF validator (pdf corrupted, pypdf không đọc được)
def test_validator_corrupted_pdf(tmp_path):
    file_path = tmp_path / "corrupted.pdf"
    # Header đúng nhưng phần sau bị hỏng
    file_path.write_bytes(b"%PDF-1.4\nrest of corrupted content")
    with pytest.raises(ValueError, match="corrupted or cannot be read"):
        validate_pdf(file_path)

# 9. Test PDF date parser
def test_pdf_date_parser():
    # Hợp lệ UTC
    assert parse_pdf_date("D:20260629123000Z") == "2026-06-29T12:30:00Z"
    # Hợp lệ Offset
    assert parse_pdf_date("D:20260629123000+07'00'") == "2026-06-29T12:30:00+07:00"
    # Không hợp lệ hoặc thiếu dữ liệu -> Trả về None chứ không đoán mò
    assert parse_pdf_date("D:invalid-date") is None
    assert parse_pdf_date("2026-06-29") is None
    assert parse_pdf_date("") is None
    assert parse_pdf_date(None) is None

# 10. Test trích xuất metadata PDF
def test_metadata_extractor(tmp_path):
    pdf_path = tmp_path / "meta_test.pdf"
    create_mock_pdf(pdf_path, pages=3)
    
    meta = extract_pdf_metadata(pdf_path)
    assert meta["page_count"] == 3
    assert meta["encrypted"] is False
    assert meta["pdf_version"] is not None

# 11. Test Importer hoạt động thành công
def test_importer_success(tmp_path):
    data_root = tmp_path / "data"
    pdf_path = tmp_path / "test_quote.pdf"
    create_mock_pdf(pdf_path, pages=2)
    
    package_dir = import_pdf(
        pdf_path=pdf_path,
        data_root=data_root,
        supplier_code="CADIVI",
        quotation_date="2026-06-20",
        seq=1
    )
    
    assert package_dir.exists()
    assert (package_dir / "source" / "original.pdf").exists()
    
    # Kiểm tra metadata.json sinh ra
    meta_json_path = package_dir / "source" / "metadata.json"
    assert meta_json_path.exists()
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)
        
    assert meta_data["file_name"] == "test_quote.pdf"
    assert meta_data["page_count"] == 2
    assert meta_data["encrypted"] is False
    assert meta_data["warnings"] == []
    
    # Kiểm tra package.json được cập nhật
    pkg = load_package_json(package_dir)
    assert pkg.files.pdf_metadata == "source/metadata.json"
    assert pkg.updated_at is not None

# 12. Test Importer với file quá kích thước cấu hình (Large PDF)
def test_importer_large_file(tmp_path):
    data_root = tmp_path / "data"
    pdf_path = tmp_path / "large.pdf"
    create_mock_pdf(pdf_path, pages=1)
    
    # Cấu hình max_size_mb = 0 để tệp tin test chắc chắn lớn hơn ngưỡng
    package_dir = import_pdf(
        pdf_path=pdf_path,
        data_root=data_root,
        supplier_code="AUT",
        quotation_date="2026-06-20",
        seq=1,
        max_size_mb=0
    )
    
    # Large PDF không làm importer fail, vẫn sinh package và metadata
    assert package_dir.exists()
    
    # Kiểm tra metadata warnings
    meta_json_path = package_dir / "source" / "metadata.json"
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)
        
    assert len(meta_data["warnings"]) == 1
    assert meta_data["warnings"][0]["code"] == "large_pdf"
    
    # Kiểm tra log kiểm toán có sự kiện cảnh báo tệp lớn
    log_file = package_dir / "logs" / "processing.log.jsonl"
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as f:
        log_lines = [json.loads(line) for line in f]
        
    events = [entry["event"] for entry in log_lines]
    assert "pdf_large_file_warning" in events

# 13. Test ngăn chặn ghi đè khi sequence đã tồn tại
def test_importer_prevent_overwrite(tmp_path):
    data_root = tmp_path / "data"
    pdf_path1 = tmp_path / "quote1.pdf"
    pdf_path2 = tmp_path / "quote2.pdf"
    create_mock_pdf(pdf_path1, pages=1)
    create_mock_pdf(pdf_path2, pages=2)
    
    # Lần 1: import thành công
    import_pdf(
        pdf_path=pdf_path1,
        data_root=data_root,
        supplier_code="CADIVI",
        quotation_date="2026-06-20",
        seq=1
    )
    
    # Lần 2: import trùng sequence và supplier/date -> Phải báo lỗi
    with pytest.raises(ValueError, match="already exists.*Overwrite is not allowed"):
        import_pdf(
            pdf_path=pdf_path2,
            data_root=data_root,
            supplier_code="CADIVI",
            quotation_date="2026-06-20",
            seq=1
        )

# 14. Test CLI import-pdf
def test_cli_import_pdf(tmp_path, capsys):
    data_root = tmp_path / "data"
    pdf_path = tmp_path / "cli_quote.pdf"
    create_mock_pdf(pdf_path, pages=2)
    
    # Khôi phục hoặc giả lập data_root trong CLI bằng cách trỏ project_root
    # CLI import-pdf sử dụng project_root / "data", chúng ta sẽ mock project_root của main
    with patch("mep_quotation.cli.main.project_root", tmp_path):
        # Tạo thư mục data giả lập ở tmp_path
        (tmp_path / "data").mkdir(parents=True, exist_ok=True)
        
        test_args = [
            "main.py",
            "import-pdf",
            "--supplier", "AUT",
            "--date", "2026-06-20",
            "--file", str(pdf_path),
            "--seq", "2"
        ]
        
        with patch.object(sys, "argv", test_args):
            main()
            
        captured = capsys.readouterr()
        assert "Successfully imported PDF" in captured.out
        assert "Page Count     : 2" in captured.out
        assert "AUT_20260620_002" in captured.out

# 15. Test Encrypted PDF flow
def test_encrypted_pdf_flow(tmp_path):
    data_root = tmp_path / "data"
    pdf_path = tmp_path / "encrypted.pdf"
    
    # Tạo PDF bị mã hóa bằng password "secret"
    create_mock_pdf(pdf_path, pages=3, encrypted_password="secret")
    
    # 1. Validate không fail
    val_res = validate_pdf(pdf_path)
    assert val_res.is_valid is True
    
    # 2. Trích xuất metadata
    meta = extract_pdf_metadata(pdf_path)
    assert meta["encrypted"] is True
    assert meta["page_count"] is None  # encrypted thì không đọc được trang nếu chưa giải mã
    assert meta["created_at"] is None
    assert meta["modified_at"] is None
    
    # 3. Importer thành công
    package_dir = import_pdf(
        pdf_path=pdf_path,
        data_root=data_root,
        supplier_code="AUT",
        quotation_date="2026-06-20",
        seq=10
    )
    assert package_dir.exists()
    
    # Kiểm tra metadata.json
    meta_json_path = package_dir / "source" / "metadata.json"
    assert meta_json_path.exists()
    with open(meta_json_path, "r", encoding="utf-8") as f:
        meta_data = json.load(f)
        
    assert meta_data["encrypted"] is True
    assert meta_data["page_count"] is None
    assert meta_data["created_at"] is None
    assert meta_data["modified_at"] is None

# 16. Test CLI help không crash Unicode
def test_cli_unicode_help_subprocess():
    import subprocess
    import sys
    
    # Test main help
    result_main = subprocess.run(
        [sys.executable, "-m", "mep_quotation.cli.main", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result_main.returncode == 0
    assert "import-pdf" in result_main.stdout
    
    # Test import-pdf help
    result_import = subprocess.run(
        [sys.executable, "-m", "mep_quotation.cli.main", "import-pdf", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result_import.returncode == 0
    assert "--supplier" in result_import.stdout
