from pathlib import Path
import json
from typing import Dict, List
from mep_quotation.spec.models import MaterialIndexFileModel, MaterialIndexEntryModel

def search_materials(index_file_path: Path, query: str) -> Dict[str, List[MaterialIndexEntryModel]]:
    """Tìm kiếm vật tư từ file chỉ mục material_index.json."""
    index_file_path = Path(index_file_path)
    
    if not index_file_path.exists():
        print(f"Warning: Index file not found at {index_file_path}. Please build index first.")
        return {}
        
    with open(index_file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    # Validate cấu trúc index
    index_file = MaterialIndexFileModel.model_validate(raw_data)
    
    query_clean = query.strip().lower()
    if not query_clean:
        return {}
        
    results: Dict[str, List[MaterialIndexEntryModel]] = {}
    
    for code, entries in index_file.materials.items():
        code_lower = code.lower()
        
        # 1. Kiểm tra exact match với material_code
        is_match = (code_lower == query_clean)
        
        # 2. Nếu không exact match, kiểm tra simple case-insensitive contains trên code hoặc name
        if not is_match:
            # Kiểm tra xem query có nằm trong material_code không
            if query_clean in code_lower:
                is_match = True
            else:
                # Kiểm tra xem query có nằm trong bất kỳ material_name nào của entries không
                # Chỉ cần khớp một trong các entries là ta chọn mã vật tư này
                for entry in entries:
                    if query_clean in entry.material_name.lower():
                        is_match = True
                        break
                        
        if is_match:
            results[code] = entries
            
    return results
