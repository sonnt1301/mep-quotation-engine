import json
import os
import sys
from pathlib import Path

# Đảm bảo import được module mep_quotation
sys.path.append(str(Path(__file__).parent.parent))

from mep_quotation.spec.models import (
    QuotationPackageModel,
    NormalizedQuotationModel,
    CorrectionsFileModel,
    MaterialIndexFileModel,
    PdfMetadataModel,
    PageManifestModel,
    RawTextManifestModel
)

def generate_schemas():
    project_root = Path(__file__).parent.parent
    schemas_dir = project_root / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    # Bản đồ các model và tên file schema tương ứng
    models_to_generate = {
        "quotation_package.schema.json": QuotationPackageModel,
        "normalized.schema.json": NormalizedQuotationModel,
        "corrections.schema.json": CorrectionsFileModel,
        "material_index.schema.json": MaterialIndexFileModel,
        "pdf_metadata.schema.json": PdfMetadataModel,
        "page_manifest.schema.json": PageManifestModel,
        "raw_text.schema.json": RawTextManifestModel
    }

    for filename, model in models_to_generate.items():
        schema_path = schemas_dir / filename
        print(f"Generating {filename} from {model.__name__}...")
        
        # Sinh schema dưới dạng dict
        schema_dict = model.model_json_schema()
        
        # Ghi ra file với định dạng deterministic
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n") # Add newline at end of file

    print("All schemas generated successfully.")

if __name__ == "__main__":
    generate_schemas()
