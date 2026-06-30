import json
import hashlib
from pathlib import Path
from mep_quotation.spec.models import PageManifestModel
from mep_quotation.package.writer import write_json_file

def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def write_page_manifest(manifest_path: Path, manifest_data: PageManifestModel) -> None:
    """Ghi dữ liệu manifest vào file một cách deterministic."""
    write_json_file(manifest_path, manifest_data)

def validate_manifest_file(manifest_path: Path, package_root: Path) -> None:
    """
    Xác thực toàn diện tệp manifest sau khi ghi:
    - Định dạng PageManifestModel hợp lệ
    - page_count == len(pages)
    - Đường dẫn tương đối từ package root (không tuyệt đối)
    - File ảnh thực tế phải tồn tại trên đĩa
    - file_size và sha256 khớp chính xác với file ảnh thực tế
    """
    manifest_path = Path(manifest_path)
    package_root = Path(package_root)
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
        
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # 1. Validate bằng Pydantic model
    try:
        manifest = PageManifestModel(**data)
    except Exception as e:
        raise ValueError(f"Invalid page_manifest data format: {e}")
        
    # 2. Kiểm tra page_count == len(pages)
    if manifest.page_count != len(manifest.pages):
        raise ValueError(
            f"page_count ({manifest.page_count}) does not match the number of pages ({len(manifest.pages)}) in manifest."
        )
        
    # 3. Kiểm tra các đường dẫn tương đối và sự tồn tại của file ảnh
    if Path(manifest.source_pdf).is_absolute() or manifest.source_pdf.startswith("\\") or manifest.source_pdf.startswith("/"):
        raise ValueError(f"source_pdf path must be relative to package root: {manifest.source_pdf}")
        
    source_pdf_path = package_root / manifest.source_pdf
    if not source_pdf_path.exists():
        raise FileNotFoundError(f"Source PDF file declared in manifest does not exist: {source_pdf_path}")
        
    for page in manifest.pages:
        # Đường dẫn phải tương đối
        img_path_str = page.image_path
        if Path(img_path_str).is_absolute() or img_path_str.startswith("\\") or img_path_str.startswith("/"):
            raise ValueError(f"Image path must be relative to package root: {img_path_str}")
            
        # File ảnh phải tồn tại
        img_file_path = package_root / img_path_str
        if not img_file_path.exists():
            raise FileNotFoundError(f"Page image file does not exist: {img_file_path}")
            
        # file_size và sha256 phải khớp
        actual_size = img_file_path.stat().st_size
        if page.file_size != actual_size:
            raise ValueError(f"File size mismatch for {img_path_str}: manifest={page.file_size}, actual={actual_size}")
            
        actual_sha256 = calculate_sha256(img_file_path)
        if page.sha256 != actual_sha256:
            raise ValueError(f"SHA256 mismatch for {img_path_str}: manifest={page.sha256}, actual={actual_sha256}")
