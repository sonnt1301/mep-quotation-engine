import argparse
import sys
import os
from pathlib import Path
import json
from typing import Any

# Đảm bảo console Windows hỗ trợ UTF-8 tránh crash UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm project root vào sys.path để import mep_quotation
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def get_display_path(path: Any) -> str:
    p = Path(path)
    try:
        return p.relative_to(project_root).as_posix()
    except ValueError:
        return p.resolve().as_posix()

from mep_quotation.package import (
    create_empty_package,
    load_package_json,
    load_normalized_json,
    load_corrections_json
)
from mep_quotation.corrections import record_correction
from mep_quotation.indexer import build_material_index, search_materials
from mep_quotation.audit import log_event

def handle_create_package(args):
    data_root = project_root / "data"
    try:
        package_dir = create_empty_package(
            data_root=data_root,
            supplier_code=args.supplier,
            date_str=args.date,
            seq=args.seq
        )
        
        # Load package to get ID
        pkg = load_package_json(package_dir)
        
        # Ghi log sự kiện khởi tạo thành công
        log_event(
            package_path=package_dir,
            level="INFO",
            event="package_created",
            quotation_id=pkg.quotation_id,
            details={"supplier": args.supplier, "date": args.date}
        )
        
        print(f"Successfully created empty package.")
        print(f"Quotation ID: {pkg.quotation_id}")
        # Print path with relative path for better clean display
        rel_path = get_display_path(package_dir)
        print(f"Package Path: {rel_path}")
    except Exception as e:
        print(f"Error creating package: {e}", file=sys.stderr)
        sys.exit(1)

def handle_validate_package(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path
        
    try:
        # Load and validate package.json, normalized.json, corrections.json
        pkg = load_package_json(package_path)
        norm = load_normalized_json(package_path)
        corr = load_corrections_json(package_path)
        
        # Kiểm tra toàn vẹn liên kết dữ liệu
        from mep_quotation.package import validate_package_integrity
        validate_package_integrity(package_path)
        
        # Log success event
        log_event(
            package_path=package_path,
            level="INFO",
            event="package_validated",
            quotation_id=pkg.quotation_id,
            details={"status": "valid"}
        )
        print(f"Package is valid.")
        print(f"  Quotation ID : {pkg.quotation_id}")
        print(f"  Supplier     : {pkg.supplier.code}")
        print(f"  Items Count  : {len(norm.items)}")
        print(f"  Corrections  : {len(corr.corrections)}")
    except Exception as e:
        print(f"Validation failed: {e}", file=sys.stderr)
        # Attempt to log failure if we can resolve the package path and id
        try:
            pkg = load_package_json(package_path)
            log_event(
                package_path=package_path,
                level="ERROR",
                event="package_validation_failed",
                quotation_id=pkg.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        sys.exit(1)

def handle_record_correction(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path
        
    # Chuyển đổi kiểu dữ liệu cho old/new value
    def parse_value(val_str: str) -> Any:
        # Thử parse JSON (cho số, boolean, list, dict)
        try:
            return json.loads(val_str)
        except json.JSONDecodeError:
            # Nếu không parse được JSON thì coi là chuỗi thường
            return val_str

    old_val = parse_value(args.old)
    new_val = parse_value(args.new)
    
    try:
        entry = record_correction(
            package_path=package_path,
            field_path=args.field,
            old_value=old_val,
            new_value=new_val,
            reason=args.reason,
            correction_type=args.type,
            user=args.user
        )
        print(f"Successfully recorded correction {entry.correction_id}.")
        print(f"  Field Path : {entry.field_path}")
        print(f"  Old Value  : {entry.old_value}")
        print(f"  New Value  : {entry.new_value}")
        print(f"  Timestamp  : {entry.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    except Exception as e:
        print(f"Error recording correction: {e}", file=sys.stderr)
        sys.exit(1)

def handle_build_index(args):
    data_root = project_root / "data"
    try:
        index_file, skipped = build_material_index(data_root, project_root, strict=args.strict)
        rel_path = get_display_path(index_file)
        print(f"Successfully built material index.")
        print(f"Index File: {rel_path}")
        if skipped:
            print(f"\nWarning: Skipped {len(skipped)} invalid normalized files:")
            for path in skipped:
                print(f"  - {get_display_path(path)}")
    except Exception as e:
        print(f"Error building index: {e}", file=sys.stderr)
        sys.exit(1)

def handle_search_material(args):
    data_root = project_root / "data"
    index_file = data_root / "indexes" / "material_index.json"
    
    try:
        results = search_materials(index_file, args.query)
        if not results:
            print(f"No materials found matching: '{args.query}'")
            return
            
        print(f"Search results for '{args.query}':\n")
        # Format đầu ra dưới dạng trực quan
        for code, entries in results.items():
            print(f"Material Code: {code}")
            for i, entry in enumerate(entries, 1):
                print(f"  {i}. Name        : {entry.material_name}")
                print(f"     Price       : {entry.unit_price} {entry.currency} / {entry.unit}")
                print(f"     Supplier    : {entry.supplier_code}")
                print(f"     Date        : {entry.quotation_date}")
                print(f"     Quotation ID: {entry.quotation_id}")
                print(f"     Pkg Path    : {entry.package_path}")
                print()
    except Exception as e:
        print(f"Error searching materials: {e}", file=sys.stderr)
        sys.exit(1)

def handle_import_pdf(args):
    pdf_path = Path(args.file)
    data_root = project_root / "data"
    
    try:
        from mep_quotation.pdf import import_pdf
        package_dir = import_pdf(
            pdf_path=pdf_path,
            data_root=data_root,
            supplier_code=args.supplier,
            quotation_date=args.date,
            seq=args.seq,
            max_size_mb=args.max_size_mb
        )
        
        # Load package.json và metadata.json để in thông tin
        pkg = load_package_json(package_dir)
        meta_path = package_dir / "source" / "metadata.json"
        
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
            
        print(f"Successfully imported PDF.")
        print(f"  Quotation ID   : {pkg.quotation_id}")
        print(f"  Package Path   : {get_display_path(package_dir)}")
        print(f"  Source PDF Path: {get_display_path(package_dir / pkg.files.source_pdf)}")
        print(f"  Metadata Path  : {get_display_path(meta_path)}")
        print(f"  Page Count     : {meta_data.get('page_count')}")
        print(f"  File Size      : {meta_data.get('file_size')} bytes")
        print(f"  SHA256         : {meta_data.get('sha256')}")
        print(f"  Encrypted      : {meta_data.get('encrypted')}")
        
        # Hiển thị warnings nếu có
        warnings = meta_data.get("warnings", [])
        if warnings:
            for w in warnings:
                if w.get("code") == "large_pdf":
                    file_size_mb = meta_data.get('file_size') / (1024 * 1024)
                    print()
                    print("WARNING")
                    print()
                    print("Large PDF detected.")
                    print()
                    print(f"File size: {file_size_mb:.2f} MB")
                    print(f"Configured threshold: {args.max_size_mb} MB")
                    print()
                    print("Import will continue.")
                    print()
                else:
                    print(f"\nWarning [{w.get('code')}]: {w.get('message')}")
                    
    except Exception as e:
        print(f"Error importing PDF: {e}", file=sys.stderr)
        sys.exit(1)

def handle_prepare_pages(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path
        
    # CLI validation
    if args.dpi <= 0:
        print(f"Error: DPI must be a positive integer: {args.dpi}", file=sys.stderr)
        sys.exit(1)
        
    if args.format.lower() != "png":
        print(f"Error: Unsupported image format: {args.format}. Only 'png' is supported.", file=sys.stderr)
        sys.exit(1)
        
    try:
        from mep_quotation.pdf_pages import prepare_pdf_pages
        prepare_pdf_pages(
            package_path=package_path,
            dpi=args.dpi,
            image_format=args.format,
            overwrite=args.overwrite
        )
        
        # Nạp lại package để in thông tin
        pkg = load_package_json(package_path)
        
        # Nạp page_manifest.json để lấy số trang
        manifest_path = package_path / pkg.files.page_manifest
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
            
        print("Successfully prepared PDF pages.")
        print(f"  Quotation ID   : {pkg.quotation_id}")
        print(f"  Package Path   : {get_display_path(package_path)}")
        print(f"  Page Count     : {manifest_data.get('page_count')}")
        print(f"  Output Dir     : {get_display_path(package_path / 'source' / 'pages')}")
        print(f"  Manifest Path  : {get_display_path(manifest_path)}")
        print(f"  DPI            : {manifest_data.get('dpi')}")
        print(f"  Image Format   : {manifest_data.get('image_format')}")
        
    except Exception as e:
        print(f"Error preparing PDF pages: {e}", file=sys.stderr)
        sys.exit(1)

def handle_extract_text(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.pdf_text import extract_package_text
        extract_package_text(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại package và raw_text.json để in thông tin
        pkg = load_package_json(package_path)
        raw_text_path = package_path / pkg.files.raw_text
        with open(raw_text_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        page_count = raw_data.get("page_count", 0)
        pages = raw_data.get("pages", [])
        total_chars = sum(p.get("character_count", 0) for p in pages)
        pages_with_text = sum(1 for p in pages if p.get("has_text", False))

        print("Successfully extracted PDF text.")
        print(f"  Quotation ID     : {pkg.quotation_id}")
        print(f"  Page Count       : {page_count}")
        print(f"  Total Characters : {total_chars}")
        print(f"  Pages With Text  : {pages_with_text}")
        print(f"  Output Path      : {get_display_path(raw_text_path)}")

    except Exception as e:
        print(f"Error extracting PDF text: {e}", file=sys.stderr)
        sys.exit(1)


def handle_assemble_text(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.text_assembly import assemble_package_text
        assemble_package_text(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại package và quotation_text.json để hiển thị
        pkg = load_package_json(package_path)
        manifest_path = package_path / pkg.files.text_manifest
        md_path = package_path / pkg.files.text_markdown

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        print("Successfully assembled PDF text.")
        print(f"  Quotation ID     : {pkg.quotation_id}")
        print(f"  Page Count       : {manifest_data.get('page_count')}")
        print(f"  Total Characters : {manifest_data.get('total_characters')}")
        print(f"  Pages With Text  : {manifest_data.get('pages_with_text')}")
        print(f"  Markdown Path    : {get_display_path(md_path)}")
        print(f"  Manifest Path    : {get_display_path(manifest_path)}")

    except Exception as e:
        print(f"Error assembling PDF text: {e}", file=sys.stderr)
        sys.exit(1)


def handle_parse_line_candidates(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.parser import parse_package_line_candidates
        parse_package_line_candidates(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại package và line_candidates.json để in ra
        pkg = load_package_json(package_path)
        candidates_path = package_path / pkg.files.line_candidates
        md_path = package_path / pkg.files.text_markdown

        with open(candidates_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        candidate_count = manifest_data.get("candidate_count", 0)
        
        # Đếm tổng warnings của cả manifest và các candidates
        total_warnings = len(manifest_data.get("warnings", []))
        for cand in manifest_data.get("candidates", []):
            total_warnings += len(cand.get("warnings", []))

        print("Successfully extracted line candidates.")
        print(f"  Quotation ID     : {pkg.quotation_id}")
        print(f"  Candidate Count  : {candidate_count}")
        print(f"  Source Markdown  : {get_display_path(md_path)}")
        print(f"  Candidates Path  : {get_display_path(candidates_path)}")
        print(f"  Warnings Count   : {total_warnings}")

    except Exception as e:
        print(f"Error parsing line candidates: {e}", file=sys.stderr)
        sys.exit(1)


def handle_assemble_rows(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.row_assembly import assemble_row_candidates
        assemble_row_candidates(
            package_path=package_path,
            overwrite=args.overwrite,
            max_line_gap_for_price=args.max_line_gap_for_price
        )

        # Nạp lại package và row_candidates.json để in ra
        pkg = load_package_json(package_path)
        row_candidates_path = package_path / pkg.files.row_candidates
        line_candidates_path = package_path / pkg.files.line_candidates

        with open(row_candidates_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        row_count = manifest_data.get("row_count", 0)
        
        # Đếm số rows có giá thô
        rows_with_price = 0
        total_warnings = len(manifest_data.get("warnings", []))
        for row in manifest_data.get("rows", []):
            if row.get("unit_price_candidate") is not None:
                rows_with_price += 1
            total_warnings += len(row.get("warnings", []))

        print("Successfully assembled row candidates.")
        print(f"  Quotation ID          : {pkg.quotation_id}")
        print(f"  Row Count             : {row_count}")
        print(f"  Source Line Candidates: {get_display_path(line_candidates_path)}")
        print(f"  Row Candidates Path   : {get_display_path(row_candidates_path)}")
        print(f"  Rows With Price Count : {rows_with_price}")
        print(f"  Warnings Count        : {total_warnings}")

    except Exception as e:
        print(f"Error assembling row candidates: {e}", file=sys.stderr)
        sys.exit(1)


def handle_build_item_candidates(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.item_candidates import build_item_candidates
        build_item_candidates(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại package và item_candidates.json để in ra
        pkg = load_package_json(package_path)
        row_candidates_path = package_path / pkg.files.row_candidates
        item_candidates_path = package_path / pkg.files.item_candidates

        with open(item_candidates_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        item_count = manifest_data.get("item_count", 0)
        
        # Đếm số items có đơn giá và số items có thành tiền
        items_with_price = 0
        items_with_amount = 0
        total_warnings = len(manifest_data.get("warnings", []))
        for item in manifest_data.get("items", []):
            if item.get("unit_price_candidate") is not None:
                items_with_price += 1
            if item.get("amount_candidate") is not None:
                items_with_amount += 1
            total_warnings += len(item.get("warnings", []))

        print("Successfully built item candidates.")
        print(f"  Quotation ID          : {pkg.quotation_id}")
        print(f"  Item Count            : {item_count}")
        print(f"  Source Row Candidates : {get_display_path(row_candidates_path)}")
        print(f"  Item Candidates Path  : {get_display_path(item_candidates_path)}")
        print(f"  Items With Price Count: {items_with_price}")
        print(f"  Items With Amount Count: {items_with_amount}")
        print(f"  Warnings Count        : {total_warnings}")

    except Exception as e:
        print(f"Error building item candidates: {e}", file=sys.stderr)
        sys.exit(1)


def handle_build_normalized_draft(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.normalized_draft import build_normalized_draft
        build_normalized_draft(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại package và normalized_draft.json để in ra
        pkg = load_package_json(package_path)
        item_candidates_path = package_path / pkg.files.item_candidates
        normalized_draft_path = package_path / pkg.files.normalized_draft

        with open(normalized_draft_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        item_count = manifest_data.get("item_count", 0)
        review_required_count = manifest_data.get("review_required_count", 0)
        
        # Đếm số lượng của từng trạng thái review_status
        auto_ready_count = 0
        rejected_candidate_count = 0
        total_warnings = len(manifest_data.get("warnings", []))
        for item in manifest_data.get("items", []):
            status = item.get("review_status")
            if status == "auto_ready":
                auto_ready_count += 1
            elif status == "rejected_candidate":
                rejected_candidate_count += 1
            total_warnings += len(item.get("warnings", []))

        print("Successfully built normalized draft.")
        print(f"  Quotation ID          : {pkg.quotation_id}")
        print(f"  Supplier Code         : {manifest_data.get('supplier_code')}")
        print(f"  Quotation Date        : {manifest_data.get('quotation_date')}")
        print(f"  Item Count            : {item_count}")
        print(f"  Review Required Count : {review_required_count}")
        print(f"  Auto Ready Count      : {auto_ready_count}")
        print(f"  Rejected Candidate Count: {rejected_candidate_count}")
        print(f"  Source Item Candidates: {get_display_path(item_candidates_path)}")
        print(f"  Normalized Draft Path : {get_display_path(normalized_draft_path)}")
        print(f"  Warnings Count        : {total_warnings}")

    except Exception as e:
        print(f"Error building normalized draft: {e}", file=sys.stderr)
        sys.exit(1)


def handle_create_review_file(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.review import create_empty_review_file
        review_file = create_empty_review_file(
            package_path=package_path,
            reviewer=args.reviewer,
            overwrite=args.overwrite
        )

        pkg = load_package_json(package_path)
        print("Successfully created empty review decisions file.")
        print(f"  Quotation ID     : {pkg.quotation_id}")
        print(f"  Review File Path : {get_display_path(review_file)}")
        print(f"  Reviewer         : {args.reviewer}")
        print(f"  Decision Count   : 0")

    except Exception as e:
        print(f"Error creating review decisions file: {e}", file=sys.stderr)
        sys.exit(1)


def handle_record_review(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        # Validate enum decision trước khi ghi file
        allowed_decisions = {"approved", "rejected", "edited"}
        if args.decision not in allowed_decisions:
            raise ValueError(f"Invalid decision option '{args.decision}'. Must be approved, rejected or edited.")

        # Xử lý overrides cho edited decision
        field_overrides = None
        if args.decision == "edited":
            from mep_quotation.review import ReviewFieldOverridesModel
            
            # Chuẩn hóa currency trước khi validate
            currency = args.currency
            if currency:
                currency = currency.strip().upper()

            field_overrides = ReviewFieldOverridesModel(
                material_code=args.material_code,
                description=args.description,
                brand=args.brand,
                unit=args.unit,
                quantity=args.quantity,
                unit_price=args.unit_price,
                currency=currency,
                amount=args.amount
            )

        from mep_quotation.review import record_review_decision
        record_review_decision(
            package_path=package_path,
            draft_item_id=args.draft_item_id,
            decision_type=args.decision,
            reviewer=args.reviewer,
            reason=args.reason,
            field_overrides=field_overrides,
            overwrite=args.overwrite
        )

        print(f"Successfully recorded review decision for item '{args.draft_item_id}'.")
    except Exception as e:
        print(f"Error recording review decision: {e}", file=sys.stderr)
        sys.exit(1)


def handle_list_review(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.review import list_review_decisions
        pkg = load_package_json(package_path)
        
        manifest = list_review_decisions(package_path)
        
        approved_count = 0
        rejected_count = 0
        edited_count = 0
        for dec in manifest.decisions:
            if dec.decision_type == "approved":
                approved_count += 1
            elif dec.decision_type == "rejected":
                rejected_count += 1
            elif dec.decision_type == "edited":
                edited_count += 1

        review_file = package_path / pkg.files.review_decisions

        print("Successfully loaded review decisions statistics.")
        print(f"  Quotation ID          : {pkg.quotation_id}")
        print(f"  Decision Count        : {manifest.decision_count}")
        print(f"  Approved Count        : {approved_count}")
        print(f"  Rejected Count        : {rejected_count}")
        print(f"  Edited Count          : {edited_count}")
        print(f"  Review File Path      : {get_display_path(review_file)}")

    except Exception as e:
        print(f"Error loading review decisions list: {e}", file=sys.stderr)
        sys.exit(1)


def handle_export_normalized(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.normalized_export import export_normalized
        export_file = export_normalized(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại normalized.json kết quả để in thống kê
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = data.get("export_summary", {})
        warnings_count = len(data.get("warnings", []))
        for item in data.get("items", []):
            warnings_count += len(item.get("warnings", []))

        print("Successfully exported official normalized quotation.")
        print(f"  Quotation ID          : {data.get('quotation_id')}")
        print(f"  Supplier Code         : {data.get('supplier_code')}")
        print(f"  Quotation Date        : {data.get('quotation_date')}")
        print(f"  Exported Item Count   : {data.get('item_count')}")
        print(f"  Draft Item Count      : {summary.get('draft_item_count')}")
        print(f"  Approved Count        : {summary.get('approved_count')}")
        print(f"  Edited Count          : {summary.get('edited_count')}")
        print(f"  Rejected Count        : {summary.get('rejected_count')}")
        print(f"  Unreviewed Count      : {summary.get('unreviewed_count')}")
        print(f"  Warnings Count        : {warnings_count}")
        print(f"  Normalized JSON Path  : {get_display_path(export_file)}")

    except Exception as e:
        print(f"Error exporting normalized quotation: {e}", file=sys.stderr)
        sys.exit(1)


def handle_export_excel(args):
    package_path = Path(args.package_path)
    if not package_path.is_absolute():
        package_path = project_root / package_path

    try:
        from mep_quotation.excel_export import export_excel
        excel_file = export_excel(
            package_path=package_path,
            overwrite=args.overwrite
        )

        # Nạp lại manifest.json kết quả để in thống kê
        manifest_path = package_path / "exports" / "export_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        print("Successfully exported official Excel quotation.")
        print(f"  Quotation ID          : {manifest_data.get('quotation_id')}")
        print(f"  Supplier Code         : {manifest_data.get('supplier_code')}")
        print(f"  Quotation Date        : {manifest_data.get('quotation_date')}")
        print(f"  Item Count            : {manifest_data.get('sheets')[1].get('row_count') if len(manifest_data.get('sheets', [])) > 1 else 'N/A'}")
        print(f"  Excel Export Path     : {get_display_path(excel_file)}")
        print(f"  Manifest JSON Path    : {get_display_path(manifest_path)}")
        print(f"  Sheet Count           : {manifest_data.get('sheet_count')}")
        print(f"  Source Normalized SHA256 : {manifest_data.get('source_normalized_sha256')}")
        print(f"  Export File SHA256    : {manifest_data.get('export_file_sha256')}")

    except Exception as e:
        print(f"Error exporting Excel quotation: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="MEP Quotation Pipeline CLI Tool - Phase 11 Official Normalized Export Layer"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-commands")

    # Command create-package
    parser_create = subparsers.add_parser("create-package", help="Khởi tạo gói báo giá mới")
    parser_create.add_argument("--supplier", required=True, help="Mã nhà cung cấp (ví dụ: AUT)")
    parser_create.add_argument("--date", required=True, help="Ngày báo giá định dạng YYYY-MM-DD")
    parser_create.add_argument("--seq", type=int, default=None, help="Số thứ tự báo giá (tự động tính nếu bỏ qua)")
    parser_create.set_defaults(func=handle_create_package)

    # Command validate-package
    parser_val = subparsers.add_parser("validate-package", help="Xác thực gói báo giá")
    parser_val.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_val.set_defaults(func=handle_validate_package)

    # Command record-correction
    parser_corr = subparsers.add_parser("record-correction", help="Ghi nhận chỉnh sửa dữ liệu")
    parser_corr.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_corr.add_argument("--field", required=True, help="Đường dẫn trường dữ liệu (ví dụ: items[0].unit_price)")
    parser_corr.add_argument("--old", required=True, help="Giá trị cũ (chuỗi hoặc JSON parseable)")
    parser_corr.add_argument("--new", required=True, help="Giá trị mới (chuỗi hoặc JSON parseable)")
    parser_corr.add_argument("--reason", required=True, help="Lý do chỉnh sửa")
    parser_corr.add_argument("--type", default="manual_update", help="Phân loại chỉnh sửa")
    parser_corr.add_argument("--user", default="human", help="Người thực hiện chỉnh sửa")
    parser_corr.set_defaults(func=handle_record_correction)

    # Command build-index
    parser_index = subparsers.add_parser("build-index", help="Quét các package và xây dựng chỉ mục vật tư")
    parser_index.add_argument("--strict", action="store_true", help="Chế độ nghiêm ngặt, dừng và báo lỗi ngay khi có file lỗi")
    parser_index.set_defaults(func=handle_build_index)

    # Command import-pdf
    parser_import = subparsers.add_parser("import-pdf", help="Import tệp PDF báo giá vào hệ thống")
    parser_import.add_argument("--supplier", required=True, help="Mã nhà cung cấp (ví dụ: AUT)")
    parser_import.add_argument("--date", required=True, help="Ngày báo giá định dạng YYYY-MM-DD")
    parser_import.add_argument("--file", required=True, help="Đường dẫn đến tệp PDF")
    parser_import.add_argument("--seq", type=int, default=None, help="Số thứ tự báo giá (tự động tính nếu bỏ qua)")
    parser_import.add_argument("--max-size-mb", type=int, default=50, help="Dung lượng tối đa cấu hình bằng MB")
    parser_import.set_defaults(func=handle_import_pdf)

    # Command search-material
    parser_search = subparsers.add_parser("search-material", help="Tìm kiếm vật tư từ chỉ mục")
    parser_search.add_argument("query", help="Từ khóa tìm kiếm (mã hoặc tên vật tư)")
    parser_search.set_defaults(func=handle_search_material)

    # Command prepare-pages
    parser_prep = subparsers.add_parser("prepare-pages", help="Chuyển đổi các trang PDF thành ảnh PNG")
    parser_prep.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_prep.add_argument("--dpi", type=int, default=150, help="Độ phân giải DPI (mặc định 150)")
    parser_prep.add_argument("--format", default="png", help="Định dạng ảnh xuất ra (chỉ nhận png)")
    parser_prep.add_argument("--overwrite", action="store_true", help="Ghi đè nếu ảnh trang hoặc manifest đã tồn tại")
    parser_prep.set_defaults(func=handle_prepare_pages)

    # Command extract-text
    parser_text = subparsers.add_parser("extract-text", help="Trích xuất text gốc (native) từ PDF")
    parser_text.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_text.add_argument("--overwrite", action="store_true", help="Ghi đè nếu raw_text.json đã tồn tại")
    parser_text.set_defaults(func=handle_extract_text)

    # Command assemble-text
    parser_assembly = subparsers.add_parser("assemble-text", help="Lắp ghép văn bản gốc từ raw_text.json thành Markdown")
    parser_assembly.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_assembly.add_argument("--overwrite", action="store_true", help="Ghi đè nếu quotation.md hoặc quotation_text.json đã tồn tại")
    parser_assembly.set_defaults(func=handle_assemble_text)

    # Command parse-line-candidates
    parser_cand = subparsers.add_parser("parse-line-candidates", help="Trích xuất các dòng báo giá thô từ Markdown")
    parser_cand.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_cand.add_argument("--overwrite", action="store_true", help="Ghi đè nếu line_candidates.json đã tồn tại")
    parser_cand.set_defaults(func=handle_parse_line_candidates)

    # Command assemble-rows
    parser_row = subparsers.add_parser("assemble-rows", help="Gom các line candidates thành các row candidates ghép và liên kết giá")
    parser_row.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_row.add_argument("--overwrite", action="store_true", help="Ghi đè nếu row_candidates.json đã tồn tại")
    parser_row.add_argument("--max-line-gap-for-price", type=int, default=6, help="Khoảng cách dòng tối đa cho phép liên kết giá (mặc định 6)")
    parser_row.set_defaults(func=handle_assemble_rows)

    # Command build-item-candidates
    parser_item = subparsers.add_parser("build-item-candidates", help="Chuyển các row candidates thành các item candidates có cấu trúc")
    parser_item.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_item.add_argument("--overwrite", action="store_true", help="Ghi đè nếu item_candidates.json đã tồn tại")
    parser_item.set_defaults(func=handle_build_item_candidates)

    # Command build-normalized-draft
    parser_draft = subparsers.add_parser("build-normalized-draft", help="Chuyển các item candidates thành bản dữ liệu nháp chuẩn hóa")
    parser_draft.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_draft.add_argument("--overwrite", action="store_true", help="Ghi đè nếu normalized_draft.json đã tồn tại")
    parser_draft.set_defaults(func=handle_build_normalized_draft)

    # Command create-review-file
    parser_cr_review = subparsers.add_parser("create-review-file", help="Khởi tạo file review_decisions.json rỗng")
    parser_cr_review.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_cr_review.add_argument("--reviewer", default="human", help="Reviewer mặc định")
    parser_cr_review.add_argument("--overwrite", action="store_true", help="Ghi đè nếu file review đã tồn tại")
    parser_cr_review.set_defaults(func=handle_create_review_file)

    # Command record-review
    parser_rec_review = subparsers.add_parser("record-review", help="Ghi nhận quyết định phê duyệt cho một draft item")
    parser_rec_review.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_rec_review.add_argument("--draft-item-id", required=True, help="ID draft item cần review")
    parser_rec_review.add_argument("--decision", required=True, help="Quyết định review (approved | rejected | edited)")
    parser_rec_review.add_argument("--reviewer", default="human", help="Reviewer dòng này")
    parser_rec_review.add_argument("--reason", help="Lý do phê duyệt/từ chối/chỉnh sửa")
    parser_rec_review.add_argument("--overwrite", action="store_true", help="Ghi đè thay thế quyết định cũ")
    # Override fields
    parser_rec_review.add_argument("--material-code", help="Edited: Mã vật tư ghi đè")
    parser_rec_review.add_argument("--description", help="Edited: Mô tả vật tư ghi đè")
    parser_rec_review.add_argument("--brand", help="Edited: Thương hiệu ghi đè")
    parser_rec_review.add_argument("--unit", help="Edited: Đơn vị tính ghi đè")
    parser_rec_review.add_argument("--quantity", type=float, help="Edited: Số lượng ghi đè")
    parser_rec_review.add_argument("--unit-price", type=float, help="Edited: Đơn giá ghi đè")
    parser_rec_review.add_argument("--currency", help="Edited: Tiền tệ ghi đè")
    parser_rec_review.add_argument("--amount", type=float, help="Edited: Thành tiền ghi đè")
    parser_rec_review.set_defaults(func=handle_record_review)

    # Command list-review
    parser_lst_review = subparsers.add_parser("list-review", help="Hiển thị thống kê các quyết định rà soát")
    parser_lst_review.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_lst_review.set_defaults(func=handle_list_review)

    # Command export-normalized
    parser_exp_norm = subparsers.add_parser("export-normalized", help="Xuất bản tệp normalized.json báo giá chính thức")
    parser_exp_norm.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_exp_norm.add_argument("--overwrite", action="store_true", help="Ghi đè nếu normalized.json đã tồn tại")
    parser_exp_norm.set_defaults(func=handle_export_normalized)
    # Command export-excel
    parser_exp_excel = subparsers.add_parser("export-excel", help="Xuất bản tệp Excel báo giá chính thức")
    parser_exp_excel.add_argument("package_path", help="Đường dẫn đến thư mục gói báo giá")
    parser_exp_excel.add_argument("--overwrite", action="store_true", help="Ghi đè nếu quotation.xlsx hoặc export_manifest.json đã tồn tại")
    parser_exp_excel.set_defaults(func=handle_export_excel)


    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
