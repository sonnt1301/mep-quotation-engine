import json
from pathlib import Path
from mep_quotation.package.loader import load_package_json, load_normalized_json, load_corrections_json
from mep_quotation.spec.models import PageManifestModel

def validate_package_integrity(package_path: Path) -> None:
    """Kiểm tra đối chiếu tính toàn vẹn liên kết dữ liệu ở cấp độ package."""
    package_path = Path(package_path)
    
    # 1. Đọc dữ liệu từ các file trong package
    pkg = load_package_json(package_path)
    norm = load_normalized_json(package_path)
    corr = load_corrections_json(package_path)
    
    # 2. Kiểm tra normalized.quotation_id == package.quotation_id
    if norm.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"Integrity check failed: normalized.quotation_id '{norm.quotation_id}' "
            f"does not match package.quotation_id '{pkg.quotation_id}'"
        )
        
    # 3. Kiểm tra corrections.quotation_id == package.quotation_id
    if corr.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"Integrity check failed: corrections.quotation_id '{corr.quotation_id}' "
            f"does not match package.quotation_id '{pkg.quotation_id}'"
        )
        
    # 4. Kiểm tra normalized.supplier_code == package.supplier.code (không phân biệt chữ hoa thường)
    if norm.supplier_code.upper() != pkg.supplier.code.upper():
        raise ValueError(
            f"Integrity check failed: normalized.supplier_code '{norm.supplier_code}' "
            f"does not match package.supplier.code '{pkg.supplier.code}'"
        )
        
    # 5. Kiểm tra normalized.quotation_date == package.quotation_date
    if norm.quotation_date != pkg.quotation_date:
        raise ValueError(
            f"Integrity check failed: normalized.quotation_date '{norm.quotation_date}' "
            f"does not match package.quotation_date '{pkg.quotation_date}'"
        )

    # 6. Kiểm tra page_manifest (chỉ khi file tồn tại thực tế để tương thích ngược)
    manifest_file = package_path / "source" / "page_manifest.json"
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            try:
                manifest_data = json.load(f)
                manifest = PageManifestModel(**manifest_data)
            except Exception as e:
                raise ValueError(f"Integrity check failed: Invalid page_manifest.json format: {e}")
                
        # Đối chiếu page_manifest.quotation_id == package.quotation_id
        if manifest.quotation_id != pkg.quotation_id:
            raise ValueError(
                f"Integrity check failed: page_manifest.quotation_id '{manifest.quotation_id}' "
                f"does not match package.quotation_id '{pkg.quotation_id}'"
            )
            
        # Đối chiếu số lượng ảnh trang thực tế trong thư mục source/pages/
        output_dir = package_path / "source" / "pages"
        actual_count = 0
        if output_dir.exists():
            actual_images = list(output_dir.glob("page_*.png"))
            actual_count = len(actual_images)
            
        if manifest.page_count != actual_count:
            raise ValueError(
                f"Integrity check failed: page_manifest.page_count ({manifest.page_count}) "
                f"does not match the actual number of page image files ({actual_count}) in source/pages/."
            )
            
        # Đảm bảo các tệp ảnh trang khai báo trong manifest thực sự tồn tại
        for page in manifest.pages:
            img_file = package_path / page.image_path
            if not img_file.exists():
                raise ValueError(
                    f"Integrity check failed: Page image file declared in manifest does not exist: {page.image_path}"
                )

    # 7. Kiểm tra raw_text.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    raw_text_file = package_path / "source" / "raw_text.json"
    if raw_text_file.exists():
        try:
            from mep_quotation.pdf_text.manifest import validate_raw_text_file
            validate_raw_text_file(raw_text_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: raw_text.json validation error: {e}")

    # 8. Kiểm tra quotation_text.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    assembly_manifest_file = package_path / "text" / "quotation_text.json"
    if assembly_manifest_file.exists():
        try:
            from mep_quotation.text_assembly.manifest import validate_assembly_manifest_file
            validate_assembly_manifest_file(assembly_manifest_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: quotation_text.json validation error: {e}")

