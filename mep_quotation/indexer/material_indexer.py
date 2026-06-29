from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Dict, List

from mep_quotation.spec.models import (
    MaterialIndexFileModel,
    MaterialIndexEntryModel,
    NormalizedQuotationModel
)
from mep_quotation.package.writer import write_json_file

def build_material_index(data_root: Path, project_root: Path, strict: bool = False) -> tuple[Path, list[Path]]:
    """Quét tất cả các file normalized.json và xây dựng tệp chỉ mục material_index.json."""
    data_root = Path(data_root)
    project_root = Path(project_root)
    
    suppliers_dir = data_root / "suppliers"
    index_file_path = data_root / "indexes" / "material_index.json"
    
    # 1. Tìm tất cả các file normalized.json
    normalized_files = list(suppliers_dir.rglob("normalized/normalized.json"))
    
    materials_map: Dict[str, List[MaterialIndexEntryModel]] = {}
    skipped_files: List[Path] = []
    
    # 2. Quét từng file normalized.json
    for file_path in normalized_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            
            # Validate cấu trúc bằng model
            norm_quot = NormalizedQuotationModel.model_validate(raw_data)
            
            # Xác định package_dir (thư mục cha của thư mục chứa normalized.json, ví dụ: 2026-05-20_001)
            package_dir = file_path.parent.parent
            package_rel_path = package_dir.relative_to(project_root).as_posix()
            
            # Duyệt các items trong quotation
            for item in norm_quot.items:
                code = item.material_code
                
                entry = MaterialIndexEntryModel(
                    quotation_id=norm_quot.quotation_id,
                    supplier_code=norm_quot.supplier_code,
                    quotation_date=norm_quot.quotation_date,
                    material_name=item.material_name,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    currency=norm_quot.currency,
                    package_path=package_rel_path,
                    source_path="normalized/normalized.json"
                )
                
                if code not in materials_map:
                    materials_map[code] = []
                materials_map[code].append(entry)
                
        except Exception as e:
            if strict:
                raise e
            else:
                print(f"Warning: Error indexing file {file_path}: {e}")
                skipped_files.append(file_path)
                continue

    # 3. Sắp xếp các entry trong từng material_code theo quy chuẩn:
    # quotation_date -> supplier_code -> quotation_id
    for code in materials_map:
        materials_map[code].sort(key=lambda x: (
            x.quotation_date,
            x.supplier_code,
            x.quotation_id
        ))
        
    # 4. Xây dựng index file model
    index_model = MaterialIndexFileModel(
        schema_version="1.0",
        generated_at=datetime.now(timezone.utc),
        materials=materials_map
    )
    
    # 5. Ghi tệp chỉ mục deterministic (sort_keys=True sẽ tự động sort các key material_code)
    write_json_file(index_file_path, index_model, sort_keys=True)
    
    return index_file_path, skipped_files
