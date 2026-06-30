import fitz  # PyMuPDF
import hashlib
from pathlib import Path
from typing import List
from mep_quotation.spec.models import PageImageModel

def calculate_sha256(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def rasterize_pdf_pages(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 150,
    image_format: str = "png",
) -> List[PageImageModel]:
    """
    Render từng trang của tệp PDF thành các tệp ảnh định dạng PNG và lưu vào output_dir.
    Chỉ chịu trách nhiệm render và lưu ảnh.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
        
    if dpi <= 0:
        raise ValueError(f"DPI must be a positive integer: {dpi}")
        
    fmt = image_format.lower()
    if fmt != "png":
        raise ValueError(f"Unsupported image format: {image_format}. Only 'png' is supported.")
        
    # Tạo thư mục output nếu chưa có
    output_dir.mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted:
            raise ValueError(f"PDF file is encrypted: {pdf_path}. Cannot process encrypted files.")
            
        page_images = []
        # Hệ số zoom từ DPI (DPI chuẩn là 72)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_number = page_idx + 1
            
            # Ghi nhận góc xoay gốc của trang
            rotation = page.rotation
            
            # Render trang thành Pixmap theo hiển thị mặc định của PyMuPDF
            pix = page.get_pixmap(matrix=mat)
            
            # Định dạng tên file: page_0001.png
            filename = f"page_{page_number:04d}.{fmt}"
            dest_file = output_dir / filename
            
            # Lưu ảnh
            pix.save(str(dest_file))
            
            # Lấy thông tin kích thước ảnh
            width = pix.width
            height = pix.height
            
            # Tính toán SHA256 và dung lượng file
            file_size = dest_file.stat().st_size
            sha256 = calculate_sha256(dest_file)
            
            # Lưu tạm đường dẫn tuyệt đối, page_service sẽ chuẩn hóa thành tương đối từ package root
            page_image = PageImageModel(
                page_number=page_number,
                image_path=str(dest_file),
                width=width,
                height=height,
                rotation=rotation,
                sha256=sha256,
                file_size=file_size
            )
            page_images.append(page_image)
            
        return page_images
    finally:
        doc.close()
