import pytest
import json
import subprocess
import sys
from pathlib import Path
from pypdf import PdfWriter
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf_pages.rasterizer import rasterize_pdf_pages
from mep_quotation.pdf_pages.page_service import prepare_pdf_pages
from mep_quotation.spec.models import PageManifestModel

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

# Fixture tạo một package tạm để chạy test
@pytest.fixture
def test_package(tmp_path):
    data_root = tmp_path / "data"
    supplier = "AUT"
    date_str = "2026-06-20"
    seq = 1
    
    # 1. Tạo package rỗng
    package_dir = create_empty_package(data_root, supplier, date_str, seq)
    
    # 2. Tạo PDF giả lập trong source/original.pdf
    pdf_path = package_dir / "source" / "original.pdf"
    create_mock_pdf(pdf_path, pages=3)
    
    # 3. Tạo metadata.json giả lập
    meta_path = package_dir / "source" / "metadata.json"
    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": "dummy_sha256",
        "page_count": 3,
        "pdf_version": "1.4",
        "encrypted": False,
        "warnings": []
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    return package_dir

# 1. Test rasterize_pdf_pages hợp lệ
def test_rasterize_pdf_pages_success(test_package):
    pdf_path = test_package / "source" / "original.pdf"
    output_dir = test_package / "source" / "pages_temp"
    
    page_images = rasterize_pdf_pages(
        pdf_path=pdf_path,
        output_dir=output_dir,
        dpi=150,
        image_format="png"
    )
    
    assert len(page_images) == 3
    # Kiểm tra các thuộc tính của trang đầu tiên
    p1 = page_images[0]
    assert p1.page_number == 1
    assert Path(p1.image_path).name == "page_0001.png"
    assert p1.width > 0
    assert p1.height > 0
    assert p1.rotation >= 0
    assert p1.file_size > 0
    assert len(p1.sha256) == 64
    
    # Đảm bảo file tồn tại trên đĩa
    assert Path(p1.image_path).exists()

# 2. Test rasterize_pdf_pages chặn encrypted PDF
def test_rasterize_pdf_pages_encrypted(tmp_path):
    pdf_path = tmp_path / "encrypted.pdf"
    output_dir = tmp_path / "pages"
    create_mock_pdf(pdf_path, pages=1, encrypted_password="secret")
    
    with pytest.raises(ValueError, match="PDF file is encrypted"):
        rasterize_pdf_pages(pdf_path, output_dir)

# 3. Test prepare_pdf_pages tạo manifest và tương thích ngược integrity
def test_prepare_pdf_pages_flow(test_package):
    # Trước khi chuẩn bị, validate_package_integrity phải pass (tương thích ngược package cũ không có manifest)
    validate_package_integrity(test_package)
    
    # Chạy chuẩn bị trang
    prepare_pdf_pages(
        package_path=test_package,
        dpi=150,
        image_format="png",
        overwrite=False
    )
    
    # Sau khi chạy xong, manifest phải tồn tại và hợp lệ
    manifest_path = test_package / "source" / "page_manifest.json"
    assert manifest_path.exists()
    
    # Load manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    
    # Validate bằng model
    manifest = PageManifestModel(**manifest_data)
    assert manifest.page_count == 3
    assert len(manifest.pages) == 3
    assert manifest.source_pdf == "source/original.pdf"
    
    # Đảm bảo đường dẫn trong manifest là tương đối
    for p in manifest.pages:
        assert not Path(p.image_path).is_absolute()
        assert p.image_path.startswith("source/pages/")
        assert (test_package / p.image_path).exists()
        
    # validate_package_integrity tiếp tục pass sau khi có manifest
    validate_package_integrity(test_package)

# 4. Test atomic overwrite check (overwrite=False ném lỗi)
def test_prepare_pdf_pages_overwrite_false(test_package):
    # Lần đầu thành công
    prepare_pdf_pages(test_package, overwrite=False)
    
    # Lần hai không overwrite -> Phải ném ValueError
    with pytest.raises(ValueError, match="Page manifest already exists|Page image already exists"):
        prepare_pdf_pages(test_package, overwrite=False)

# 5. Test overwrite=True ghi đè thành công
def test_prepare_pdf_pages_overwrite_true(test_package):
    # Lần đầu thành công
    prepare_pdf_pages(test_package, overwrite=False)
    
    # Chạy lần hai với overwrite=True -> Không crash
    prepare_pdf_pages(test_package, overwrite=True)

# 6. Test prepare_pdf_pages chặn encrypted PDF
def test_prepare_pdf_pages_encrypted(tmp_path):
    data_root = tmp_path / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-06-20", 1)
    
    pdf_path = package_dir / "source" / "original.pdf"
    create_mock_pdf(pdf_path, pages=1, encrypted_password="secret")
    
    # Cập nhật metadata
    meta_path = package_dir / "source" / "metadata.json"
    meta_data = {
        "schema_version": "1.0",
        "file_name": "original.pdf",
        "file_size": pdf_path.stat().st_size,
        "sha256": "dummy",
        "page_count": None,
        "pdf_version": "1.4",
        "encrypted": True,
        "warnings": []
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta_data, f)
        
    with pytest.raises(ValueError, match="is encrypted"):
        prepare_pdf_pages(package_dir)

# 7. Test CLI prepare-pages
def test_cli_prepare_pages(test_package):
    # Sử dụng subprocess chạy lệnh CLI
    result = subprocess.run(
        [
            sys.executable, "-m", "mep_quotation.cli.main", 
            "prepare-pages", str(test_package), 
            "--dpi", "150", 
            "--format", "png", 
            "--overwrite"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    assert result.returncode == 0
    assert "Successfully prepared PDF pages" in result.stdout
    assert "Page Count     : 3" in result.stdout
    assert "DPI            : 150" in result.stdout
    assert "Image Format   : png" in result.stdout
