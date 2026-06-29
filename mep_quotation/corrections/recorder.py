from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Optional
import re

from mep_quotation.spec.models import CorrectionEntryModel, CorrectionsFileModel
from mep_quotation.package import load_package_json, load_corrections_json, write_json_file
from mep_quotation.audit import log_event

def record_correction(
    package_path: Path,
    field_path: str,
    old_value: Any,
    new_value: Any,
    reason: str,
    correction_type: str = "manual_update",
    user: str = "human"
) -> CorrectionEntryModel:
    """Ghi nhận một chỉnh sửa dữ liệu vào file corrections.json của package."""
    package_path = Path(package_path)
    
    # 1. Đọc thông tin package.json và corrections.json hiện tại
    pkg = load_package_json(package_path)
    quotation_id = pkg.quotation_id
    
    corrections_file = load_corrections_json(package_path)
    
    # 2. Sinh correction_id tự động (dạng corr_001, corr_002...)
    max_seq = 0
    id_pattern = re.compile(r"^corr_(\d+)$")
    
    for item in corrections_file.corrections:
        match = id_pattern.match(item.correction_id)
        if match:
            seq_val = int(match.group(1))
            if seq_val > max_seq:
                max_seq = seq_val
                
    next_id = f"corr_{(max_seq + 1):03d}"
    
    # 3. Tạo correction entry mới và validate
    now = datetime.now(timezone.utc)
    new_entry = CorrectionEntryModel(
        correction_id=next_id,
        timestamp=now,
        user=user,
        field_path=field_path,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        correction_type=correction_type
    )
    
    # 4. Thêm vào danh sách hiện tại
    corrections_file.corrections.append(new_entry)
    
    # 5. Sắp xếp deterministic: sort theo timestamp, nếu bằng thì sort theo correction_id
    # Lưu ý: do timestamp trong model đã là datetime, ta có thể dùng trực tiếp để so sánh.
    # Ta convert timestamp về ISO format hoặc dùng timestamp trực tiếp để so sánh chuỗi/thời gian.
    def sort_key(entry: CorrectionEntryModel):
        # Đảm bảo so sánh chính xác theo chuỗi định dạng ISO UTC
        ts_str = entry.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        return (ts_str, entry.correction_id)
        
    corrections_file.corrections.sort(key=sort_key)
    
    # 6. Ghi file corrections.json đè lên file cũ
    corrections_rel_path = pkg.files.corrections_json
    corrections_file_path = package_path / corrections_rel_path
    write_json_file(corrections_file_path, corrections_file, sort_keys=False) # Không sort key của model để giữ thứ tự trường trong Pydantic, tuy nhiên trong write_json_file sort_keys=True mặc định sẽ sắp xếp trường. Ta có thể giữ sort_keys=True để đảm bảo deterministic tuyệt đối các trường JSON
    
    # 7. Ghi audit log sự kiện
    log_event(
        package_path=package_path,
        level="INFO",
        event="correction_recorded",
        quotation_id=quotation_id,
        details={
            "correction_id": next_id,
            "field_path": field_path,
            "old_value": old_value,
            "new_value": new_value
        }
    )
    
    return new_entry
