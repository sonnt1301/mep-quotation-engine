from pathlib import Path
import re
from datetime import datetime
from mep_quotation.spec.constants import DATE_FORMAT

def generate_quotation_id(supplier_code: str, date_str: str, seq: int) -> str:
    """Sinh Quotation ID định dạng {SUPPLIER}_{YYYYMMDD}_{SEQ}."""
    # Đảm bảo supplier_code viết hoa và không chứa ký tự đặc biệt
    clean_supplier = re.sub(r'[^A-Z0-9]', '', supplier_code.upper())
    
    # Parse ngày để validate định dạng YYYY-MM-DD
    dt = datetime.strptime(date_str, DATE_FORMAT)
    clean_date = dt.strftime("%Y%m%d")
    
    # Sinh sequence với 3 chữ số padding
    formatted_seq = f"{seq:03d}"
    
    return f"{clean_supplier}_{clean_date}_{formatted_seq}"

def get_package_dir(data_root: Path, supplier_code: str, date_str: str, seq: int) -> Path:
    """Tính toán đường dẫn tuyệt đối của thư mục gói báo giá."""
    clean_supplier = re.sub(r'[^A-Z0-9]', '', supplier_code.upper())
    dt = datetime.strptime(date_str, DATE_FORMAT)
    year_str = dt.strftime("%Y")
    
    folder_name = f"{date_str}_{seq:03d}"
    return data_root / "suppliers" / clean_supplier / year_str / folder_name

def get_next_sequence(data_root: Path, supplier_code: str, date_str: str) -> int:
    """Tìm số sequence tiếp theo cho supplier trong ngày được chỉ định."""
    clean_supplier = re.sub(r'[^A-Z0-9]', '', supplier_code.upper())
    dt = datetime.strptime(date_str, DATE_FORMAT)
    year_str = dt.strftime("%Y")
    
    supplier_year_dir = data_root / "suppliers" / clean_supplier / year_str
    if not supplier_year_dir.exists():
        return 1
        
    pattern = re.compile(rf"^{re.escape(date_str)}_(\d{{3}})$")
    max_seq = 0
    
    for child in supplier_year_dir.iterdir():
        if child.is_dir():
            match = pattern.match(child.name)
            if match:
                seq_val = int(match.group(1))
                if seq_val > max_seq:
                    max_seq = seq_val
                    
    return max_seq + 1
