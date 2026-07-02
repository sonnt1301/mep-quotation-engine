import json
from pathlib import Path
from typing import List, Optional

from mep_quotation.spec.models import (
    NormalizedQuotationModel,
    ExcelExportSheetModel,
    ExcelExportContextModel,
    ExcelExportManifestModel,
    ParserWarningModel
)

def build_excel_export_manifest(
    package_path: Path,
    normalized: NormalizedQuotationModel,
    export_file_sha256: str,
    workbook_sheets: List[ExcelExportSheetModel],
    export_context: ExcelExportContextModel,
    warnings: List[ParserWarningModel] = None
) -> ExcelExportManifestModel:
    """Xây dựng đối tượng ExcelExportManifestModel cho tệp export_manifest.json."""
    package_path = Path(package_path)
    
    # 1. Xác định supplier_code và quotation_date
    supplier_code: Optional[str] = normalized.supplier_code
    quotation_date: Optional[str] = normalized.quotation_date
    
    # Nếu thiếu trong normalized, thử nạp từ package.json
    package_json_path = package_path / "package.json"
    if (not supplier_code or not quotation_date) and package_json_path.exists():
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                if not supplier_code and "supplier" in pkg_data and isinstance(pkg_data["supplier"], dict):
                    supplier_code = pkg_data["supplier"].get("code")
                if not quotation_date:
                    quotation_date = pkg_data.get("quotation_date")
        except Exception:
            pass # Bỏ qua nếu đọc package.json lỗi
            
    # 2. Xây dựng model manifest
    manifest = ExcelExportManifestModel(
        schema_version="1.0",
        quotation_id=normalized.quotation_id,
        supplier_code=supplier_code or None,
        quotation_date=quotation_date or None,
        source_normalized="normalized/normalized.json",
        source_normalized_sha256=export_context.source_normalized_sha256,
        export_file="exports/quotation.xlsx",
        export_file_sha256=export_file_sha256,
        sheet_count=len(workbook_sheets),
        sheets=workbook_sheets,
        exported_at=export_context.exported_at,
        exporter_name=export_context.exporter_name,
        exporter_version=export_context.exporter_version,
        warnings=warnings or []
    )
    return manifest
