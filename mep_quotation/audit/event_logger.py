import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from mep_quotation.spec.models import AuditLogEntryModel
from mep_quotation.package.loader import load_package_json

def log_event(
    package_path: Path,
    level: str,
    event: str,
    quotation_id: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Ghi một sự kiện kiểm toán dưới định dạng JSON Lines vào file log của package."""
    package_path = Path(package_path)
    
    # 1. Đọc package.json để lấy đường dẫn log file thực tế
    pkg = load_package_json(package_path)
    log_rel_path = pkg.files.logs_jsonl
    log_file_path = package_path / log_rel_path
    
    # Tạo thư mục logs nếu chưa tồn tại
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 2. Xây dựng log entry và validate bằng Pydantic
    log_entry = AuditLogEntryModel(
        timestamp=datetime.now(timezone.utc),
        level=level.upper(),
        event=event,
        quotation_id=quotation_id,
        details=details or {}
    )
    
    # 3. Serialize sang JSON deterministic (chuyển đổi qua model_dump dạng json)
    entry_dict = log_entry.model_dump(mode="json")
    
    # Dùng json.dumps đảm bảo unicode hiển thị đúng và deterministic
    log_line = json.dumps(entry_dict, ensure_ascii=False, sort_keys=True)
    
    # 4. Ghi append vào file log
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
