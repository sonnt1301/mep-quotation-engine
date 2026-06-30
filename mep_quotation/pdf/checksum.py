import hashlib
from pathlib import Path

def calculate_sha256(file_path: Path) -> str:
    """Tính toán mã băm SHA256 của một tệp tin."""
    file_path = Path(file_path)
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Đọc theo từng khối 64KB để tối ưu bộ nhớ
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest()
