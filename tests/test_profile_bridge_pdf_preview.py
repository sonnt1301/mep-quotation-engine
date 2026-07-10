# -*- coding: utf-8 -*-
import pytest
import fitz
import shutil
from pathlib import Path
from tools.profile_bridge_review_helpers import (
    render_pdf_page_to_image,
    resolve_session_pdf_path,
    validate_pdf_page_number
)

@pytest.fixture
def temp_pdf_file():
    # Tạo động một tệp PDF giả lập gồm 2 trang trống để phục vụ test
    pdf_path = Path("temp_test_preview.pdf")
    doc = fitz.open()
    doc.new_page() # Trang 1
    doc.new_page() # Trang 2
    doc.save(str(pdf_path.resolve()))
    doc.close()
    yield pdf_path
    if pdf_path.exists():
        pdf_path.unlink()

def test_render_pdf_page_to_image(temp_pdf_file):
    # Render trang 1 thành công
    img_bytes = render_pdf_page_to_image(temp_pdf_file, 1, scale=1.0)
    assert len(img_bytes) > 0
    assert img_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # Signature của tệp PNG

def test_render_pdf_page_to_image_out_of_range(temp_pdf_file):
    # Render trang 3 (vượt phạm vi 2 trang) ném ra ValueError
    with pytest.raises(ValueError) as excinfo:
        render_pdf_page_to_image(temp_pdf_file, 3, scale=1.0)
    assert "out of range" in str(excinfo.value)

def test_validate_pdf_page_number(temp_pdf_file):
    # Trang hợp lệ
    ok, err = validate_pdf_page_number(temp_pdf_file, 2)
    assert ok is True
    assert err == ""
    
    # Trang không hợp lệ (vượt range)
    ok, err = validate_pdf_page_number(temp_pdf_file, 5)
    assert ok is False
    assert "vượt ngoài phạm vi" in err
    
    # PDF không tồn tại
    ok, err = validate_pdf_page_number(Path("nonexistent.pdf"), 1)
    assert ok is False
    assert "không tồn tại" in err

def test_resolve_session_pdf_path(tmp_path):
    # Test không tìm thấy PDF
    with pytest.raises(FileNotFoundError) as excinfo:
        resolve_session_pdf_path(tmp_path)
    assert "Không tìm thấy file PDF nào" in str(excinfo.value)
    
    # Test tìm thấy PDF thành công
    pdf_file = tmp_path / "invoice.pdf"
    pdf_file.touch()
    resolved = resolve_session_pdf_path(tmp_path)
    assert resolved == pdf_file

def test_no_mojibake_in_preview_test():
    # Test đảm bảo tệp test không có mojibake
    test_file = Path(__file__)
    with open(test_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    mojibake_patterns = [
        "Chá" + chr(187), 
        chr(196), 
        chr(226) + chr(353), 
        chr(240) + chr(376)
    ]
    for pattern in mojibake_patterns:
        assert pattern not in content
