import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from pypdf import PdfReader

def parse_pdf_date(date_str: Optional[str]) -> Optional[str]:
    """Parse chuỗi ngày tháng định dạng PDF (D:YYYYMMDDHHmmSS...) sang chuỗi ISO 8601.
    
    Trả về None nếu không parse chắc chắn hoặc sai định dạng.
    """
    if not date_str or not isinstance(date_str, str):
        return None
        
    # Pattern đầy đủ: D:YYYYMMDDHHmmSS...
    # Offset có thể là Z, +HH'mm', -HH'mm'
    match = re.match(r"^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(Z|[+-]\d{2}'\d{2}')?", date_str)
    if not match:
        # Thử trường hợp thiếu giây: D:YYYYMMDDHHmm...
        match = re.match(r"^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})()(Z|[+-]\d{2}'\d{2}')?", date_str)
        if not match:
            return None
            
    parts = match.groups()
    year, month, day, hour, minute, second, tz = parts
    if not second:
        second = "00"
        
    try:
        # Kiểm tra tính hợp lệ cơ bản của ngày giờ
        _ = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    except ValueError:
        return None
        
    iso_str = f"{year}-{month}-{day}T{hour}:{minute}:{second}"
    
    if not tz or tz == "Z":
        iso_str += "Z"
    else:
        # Ví dụ: +07'00' -> +07:00
        tz_clean = tz.replace("'", "") # +0700 hoặc -0500
        if len(tz_clean) >= 5:
            iso_str += f"{tz_clean[:3]}:{tz_clean[3:]}"
        else:
            iso_str += "Z"
            
    return iso_str

def extract_pdf_metadata(pdf_path: Path) -> Dict[str, Any]:
    """Trích xuất thông tin kỹ thuật và siêu dữ liệu của tệp PDF."""
    pdf_path = Path(pdf_path)
    reader = PdfReader(pdf_path)
    
    # 1. Số trang và mã hóa
    encrypted = reader.is_encrypted
    page_count = None
    if not encrypted:
        try:
            page_count = len(reader.pages)
        except Exception:
            page_count = None
    
    # 2. PDF Version
    pdf_version = None
    if hasattr(reader, "pdf_header"):
        header = reader.pdf_header
        if header and header.startswith("%PDF-"):
            pdf_version = header.replace("%PDF-", "").strip()
            
    # 3. Ngày tạo / chỉnh sửa từ document metadata
    created_at = None
    modified_at = None
    
    if not encrypted:
        try:
            metadata = reader.metadata
            if metadata:
                created_at_raw = metadata.get("/CreationDate")
                modified_at_raw = metadata.get("/ModDate")
                
                created_at = parse_pdf_date(created_at_raw)
                modified_at = parse_pdf_date(modified_at_raw)
        except Exception:
            pass
        
    return {
        "page_count": page_count,
        "pdf_version": pdf_version,
        "encrypted": encrypted,
        "created_at": created_at,
        "modified_at": modified_at
    }
