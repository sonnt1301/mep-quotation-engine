import json
from datetime import datetime, timezone
from pathlib import Path
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.pdf_pages.rasterizer import rasterize_pdf_pages
from mep_quotation.pdf_pages.manifest import write_page_manifest, validate_manifest_file
from mep_quotation.spec.models import PageManifestModel

def prepare_pdf_pages(
    package_path: Path,
    dpi: int = 150,
    image_format: str = "png",
    overwrite: bool = False,
) -> Path:
    """
    Chuẩn bị các ảnh trang từ tệp PDF gốc của package:
    1. Kiểm tra trạng thái mã hóa
    2. Kiểm tra trùng lặp atomic (nếu overwrite=False)
    3. Ghi log khởi tạo
    4. Tiến hành render các trang ảnh thành PNG
    5. Ghi tệp page_manifest.json
    6. Validate tệp manifest sau khi sinh
    7. Cập nhật package.json và chạy kiểm tra toàn vẹn
    8. Ghi log hoàn tất
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")
        
    # Nạp package.json
    package = load_package_json(package_path)
    
    # 1. Kiểm tra mã hóa từ metadata.json
    metadata_path = package_path / "source" / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            try:
                meta_data = json.load(f)
                if meta_data.get("encrypted") is True:
                    raise ValueError(f"PDF package '{package.quotation_id}' is encrypted. Cannot process encrypted files.")
            except json.JSONDecodeError:
                pass
                
    pdf_file_path = package_path / "source" / "original.pdf"
    if not pdf_file_path.exists():
        raise FileNotFoundError(f"Original PDF file not found: {pdf_file_path}")
        
    # Lấy số trang thực tế của PDF
    import fitz
    doc = fitz.open(pdf_file_path)
    try:
        if doc.is_encrypted:
            raise ValueError(f"PDF file is encrypted: {pdf_file_path}. Cannot process encrypted files.")
        page_count = len(doc)
    finally:
        doc.close()
        
    # 2. Kiểm Tra Trùng Lặp Atomic
    manifest_path = package_path / "source" / "page_manifest.json"
    output_dir = package_path / "source" / "pages"
    
    if not overwrite:
        # Kiểm tra nếu manifest đã tồn tại
        if manifest_path.exists():
            raise ValueError(
                f"Page manifest already exists at {manifest_path}. Set overwrite=True to replace it."
            )
        # Kiểm tra nếu bất kỳ ảnh trang nào đã tồn tại
        if output_dir.exists():
            for page_idx in range(page_count):
                page_number = page_idx + 1
                expected_img = output_dir / f"page_{page_number:04d}.{image_format.lower()}"
                if expected_img.exists():
                    raise ValueError(
                        f"Page image already exists at {expected_img}. Set overwrite=True to replace existing images."
                    )
                    
    try:
        # Ghi log bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_page_preparation_started",
            quotation_id=package.quotation_id,
            details={
                "dpi": dpi,
                "image_format": image_format,
                "overwrite": overwrite
            }
        )
        
        # 3. Tiến hành render
        page_images = rasterize_pdf_pages(
            pdf_path=pdf_file_path,
            output_dir=output_dir,
            dpi=dpi,
            image_format=image_format
        )
        
        # Map lại image_path thành relative path từ package root
        for img in page_images:
            abs_path = Path(img.image_path)
            rel_path = abs_path.relative_to(package_path).as_posix()
            img.image_path = rel_path
            
        # Ghi log đã render xong
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_page_rasterized",
            quotation_id=package.quotation_id,
            details={
                "page_count": len(page_images),
                "dpi": dpi,
                "image_format": image_format,
                "output_dir": "source/pages"
            }
        )
        
        # 4. Tạo và ghi manifest
        manifest_data = PageManifestModel(
            schema_version="1.0",
            quotation_id=package.quotation_id,
            source_pdf="source/original.pdf",
            page_count=len(page_images),
            dpi=dpi,
            image_format=image_format.lower(),
            pages=page_images
        )
        
        write_page_manifest(manifest_path, manifest_data)
        
        # Ghi log đã viết manifest
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_page_manifest_written",
            quotation_id=package.quotation_id,
            details={
                "manifest_path": "source/page_manifest.json"
            }
        )
        
        # 5. Xác thực toàn diện tệp manifest sau khi ghi
        validate_manifest_file(manifest_path, package_path)
        
        # 6. Cập nhật package.json
        package.files.page_manifest = "source/page_manifest.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)
        
        # 7. Chạy kiểm tra toàn vẹn package
        validate_package_integrity(package_path)
        
        # Ghi log hoàn tất
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_page_preparation_completed",
            quotation_id=package.quotation_id,
            details={
                "page_count": len(page_images)
            }
        )
        
        return package_path
        
    except Exception as e:
        # Ghi log lỗi
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="pdf_page_preparation_failed",
                quotation_id=package.quotation_id,
                details={
                    "error": str(e)
                }
            )
        except Exception:
            pass
        raise e
