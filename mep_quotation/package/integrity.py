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

    # 9. Kiểm tra line_candidates.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    line_candidates_file = package_path / "parsed" / "line_candidates.json"
    if line_candidates_file.exists():
        try:
            from mep_quotation.parser.candidate_manifest import validate_line_candidates_file
            validate_line_candidates_file(line_candidates_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: line_candidates.json validation error: {e}")

    # 10. Kiểm tra row_candidates.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    row_candidates_file = package_path / "parsed" / "row_candidates.json"
    if row_candidates_file.exists():
        try:
            from mep_quotation.row_assembly.manifest import validate_row_candidates_file
            validate_row_candidates_file(row_candidates_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: row_candidates.json validation error: {e}")

    # 11. Kiểm tra item_candidates.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    item_candidates_file = package_path / "parsed" / "item_candidates.json"
    if item_candidates_file.exists():
        try:
            from mep_quotation.item_candidates.manifest import validate_item_candidates_file
            validate_item_candidates_file(item_candidates_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: item_candidates.json validation error: {e}")

    # 12. Kiểm tra normalized_draft.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    normalized_draft_file = package_path / "normalized" / "normalized_draft.json"
    if normalized_draft_file.exists():
        try:
            from mep_quotation.normalized_draft.manifest import validate_normalized_draft_file
            validate_normalized_draft_file(normalized_draft_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: normalized_draft.json validation error: {e}")

    # 13. Kiểm tra review_decisions.json (chỉ khi file tồn tại thực tế để tương thích ngược)
    review_decisions_file = package_path / "review" / "review_decisions.json"
    if review_decisions_file.exists():
        try:
            from mep_quotation.review.decisions import validate_review_decisions_file
            validate_review_decisions_file(review_decisions_file, package_path)
        except Exception as e:
            raise ValueError(f"Integrity check failed: review_decisions.json validation error: {e}")

    # 14. Kiểm duyệt sâu tệp normalized.json chính thức (chỉ khi file tồn tại thực tế)
    normalized_file = package_path / pkg.files.normalized_json
    if normalized_file.exists():
        # Kiểm tra item_count khớp len(items)
        if norm.item_count != len(norm.items):
            raise ValueError(
                f"Integrity check failed: normalized.item_count ({norm.item_count}) "
                f"does not match items size ({len(norm.items)})"
            )

        if norm.export_summary is not None:
            if norm.export_summary.exported_item_count != len(norm.items):
                raise ValueError(
                    f"Integrity check failed: exported_item_count ({norm.export_summary.exported_item_count}) "
                    f"does not match actual items size ({len(norm.items)})"
                )

        # Kiểm định chéo chữ ký băm của các tệp nguồn nếu có lưu và tệp tồn tại thực tế
        from mep_quotation.pdf.checksum import calculate_sha256
        if norm.source_normalized_draft_sha256:
            draft_file = package_path / norm.source_normalized_draft
            if draft_file.exists():
                actual_draft_sha = calculate_sha256(draft_file)
                if norm.source_normalized_draft_sha256 != actual_draft_sha:
                    raise ValueError("Integrity check failed: source_normalized_draft_sha256 mismatch")
                
        if norm.source_review_decisions_sha256:
            review_file = package_path / norm.source_review_decisions
            if review_file.exists():
                actual_review_sha = calculate_sha256(review_file)
                if norm.source_review_decisions_sha256 != actual_review_sha:
                    raise ValueError("Integrity check failed: source_review_decisions_sha256 mismatch")

        # Kiểm tra chi tiết từng item
        item_ids = set()
        for item in norm.items:
            # item_id duy nhất
            if item.item_id in item_ids:
                raise ValueError(f"Integrity check failed: Duplicate item_id found: '{item.item_id}'")
            item_ids.add(item.item_id)
            
            # item_id đúng format
            import re
            if not re.match(r"^.+_\d{4}\d{2}\d{2}_\d{3}_(ITEM_)?\d{4}$", item.item_id):
                raise ValueError(f"Integrity check failed: item_id '{item.item_id}' has invalid format")

            # amount đúng quantity * unit_price nếu đủ dữ liệu
            if item.quantity is not None and item.unit_price is not None:
                expected_amt = item.quantity * item.unit_price
                if item.amount is None or abs(item.amount - expected_amt) > 1e-4:
                    raise ValueError(f"Integrity check failed: Item '{item.item_id}' amount does not match quantity * unit_price")

            # currency hợp lệ
            if item.currency not in ("VND", "USD"):
                raise ValueError(f"Integrity check failed: Item '{item.item_id}' has invalid currency '{item.currency}'")

        # Đối chiếu với review decisions để cấm items rejected/unreviewed
        if review_decisions_file.exists():
            from mep_quotation.review.decisions import load_review_decisions
            review_manifest = load_review_decisions(review_decisions_file)
            decisions_map = {dec.draft_item_id: dec for dec in review_manifest.decisions}
            
            for item in norm.items:
                if item.source_draft_item_id:
                    dec = decisions_map.get(item.source_draft_item_id)
                    if dec is None:
                        raise ValueError(f"Integrity check failed: Item '{item.item_id}' was exported but has no review decision")
                    if dec.decision_type == "rejected":
                        raise ValueError(f"Integrity check failed: Item '{item.item_id}' was exported but is rejected in decisions")

        # 9. Kiểm định chéo Excel export nếu exports/export_manifest.json tồn tại
        excel_manifest_path = package_path / "exports" / "export_manifest.json"
        if excel_manifest_path.exists():
            from mep_quotation.spec.models import ExcelExportManifestModel
            with open(excel_manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            excel_manifest = ExcelExportManifestModel.model_validate(manifest_data)
            
            # source_normalized_sha256 khớp SHA256 thực tế của normalized.json
            actual_norm_sha = calculate_sha256(normalized_file)
            if excel_manifest.source_normalized_sha256 != actual_norm_sha:
                raise ValueError("Excel integrity failed: source_normalized_sha256 mismatch")
                
            # export_file tồn tại
            excel_file_path = package_path / excel_manifest.export_file
            if not excel_file_path.exists():
                raise ValueError(f"Excel integrity failed: export file not found at {excel_file_path}")
                
            # export_file_sha256 khớp SHA256 thực tế của quotation.xlsx
            actual_excel_sha = calculate_sha256(excel_file_path)
            if excel_manifest.export_file_sha256 != actual_excel_sha:
                raise ValueError("Excel integrity failed: export_file_sha256 mismatch")
                
            # sheet_count == len(sheets)
            if excel_manifest.sheet_count != len(excel_manifest.sheets):
                raise ValueError("Excel integrity failed: sheet_count mismatch in manifest")
                
            # sheet names trong manifest đúng Summary, Items, Warnings, Trace
            sheet_names = [sheet.name for sheet in excel_manifest.sheets]
            expected_names = ["Summary", "Items", "Warnings", "Trace"]
            if sheet_names != expected_names:
                raise ValueError(f"Excel integrity failed: expected sheet names {expected_names}, but got {sheet_names}")








