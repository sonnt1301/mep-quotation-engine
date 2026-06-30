from pathlib import Path
from pypdf import PdfReader
from mep_quotation.spec.models import PdfValidationResult, WarningModel

def validate_pdf(pdf_path: Path, max_size_mb: int = 50) -> PdfValidationResult:
    """Xác thực kỹ thuật cho tệp PDF đầu vào."""
    pdf_path = Path(pdf_path)
    
    # 1. Kiểm tra file tồn tại
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
        
    # 2. Kiểm tra có phải là file không
    if not pdf_path.is_file():
        raise ValueError(f"Path is a directory, not a file: {pdf_path}")
        
    # 3. Kiểm tra extension .pdf
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid file extension. Expected '.pdf', got '{pdf_path.suffix}'")
        
    # 4. Kiểm tra file size > 0
    file_size = pdf_path.stat().st_size
    if file_size == 0:
        raise ValueError("PDF file is empty (0 bytes)")
        
    # 5. Kiểm tra file header bắt đầu bằng %PDF-
    try:
        with open(pdf_path, "rb") as f:
            header = f.read(5)
        if not header.startswith(b"%PDF-"):
            raise ValueError("File header does not start with '%PDF-'")
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Cannot read file header: {e}")
        
    # 6. Kiểm tra đọc được bằng pypdf
    try:
        reader = PdfReader(pdf_path)
        if not reader.is_encrypted:
            # Truy cập thuộc tính cơ bản để kích hoạt đọc file thực tế
            _ = len(reader.pages)
    except Exception as e:
        raise ValueError(f"PDF file is corrupted or cannot be read by pypdf: {e}")
        
    # 7. Phát hiện tệp quá dung lượng cấu hình (Large PDF Handling)
    warnings = []
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        file_size_mb = file_size / (1024 * 1024)
        warnings.append(WarningModel(
            code="large_pdf",
            message=f"File size ({file_size_mb:.2f} MB) exceeds configured threshold ({max_size_mb} MB). Import continues."
        ))
        
    return PdfValidationResult(
        is_valid=True,
        warnings=warnings
    )
