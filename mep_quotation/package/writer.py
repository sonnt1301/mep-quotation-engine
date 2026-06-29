import json
from pathlib import Path
from typing import Any, Dict

def write_json_file(file_path: Path, data: Any, sort_keys: bool = True) -> None:
    """Ghi dữ liệu JSON ra file theo định dạng deterministic chuẩn."""
    # Tạo thư mục cha nếu chưa tồn tại
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Nếu data là Pydantic model
    if hasattr(data, "model_dump"):
        # Dùng model_dump(mode="json") của Pydantic v2 để có kiểu JSON serializable
        data_dict = data.model_dump(mode="json")
    else:
        data_dict = data

    # Ghi file UTF-8, indent=2, ensure_ascii=False
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=2, ensure_ascii=False, sort_keys=sort_keys)
        f.write("\n") # Newline ở cuối file
