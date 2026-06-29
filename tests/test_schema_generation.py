import json
from pathlib import Path
from mep_quotation.spec.models import (
    QuotationPackageModel,
    NormalizedQuotationModel,
    CorrectionsFileModel,
    MaterialIndexFileModel
)

def test_schema_generation_matches_models():
    # Xác định đường dẫn thư mục schemas của project thực tế
    project_root = Path(__file__).parent.parent.resolve()
    schemas_dir = project_root / "schemas"
    
    # Bản đồ các file và model tương ứng
    expected_schemas = {
        "quotation_package.schema.json": QuotationPackageModel,
        "normalized.schema.json": NormalizedQuotationModel,
        "corrections.schema.json": CorrectionsFileModel,
        "material_index.schema.json": MaterialIndexFileModel
    }
    
    for filename, model in expected_schemas.items():
        schema_file_path = schemas_dir / filename
        
        # 1. Đảm bảo file schema tồn tại trên đĩa
        assert schema_file_path.exists(), f"Schema file {filename} is missing from schemas/ directory"
        
        # 2. Đọc schema từ file
        with open(schema_file_path, "r", encoding="utf-8") as f:
            disk_schema = json.load(f)
            
        # 3. Sinh schema trực tiếp từ model
        runtime_schema = model.model_json_schema()
        
        # 4. So sánh cấu trúc (so sánh dict trực tiếp)
        # Vì json.dump trong script có sort_keys=True, khi load dict lại thì thứ tự key không ảnh hưởng đến so sánh dict của Python
        assert disk_schema == runtime_schema, f"Disk schema in {filename} does not match runtime Pydantic model {model.__name__}"
