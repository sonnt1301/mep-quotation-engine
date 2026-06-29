import argparse
import sys
import os
from pathlib import Path
import json
from typing import Any

# Thêm project root vào sys.path để import mep_quotation
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

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
        rel_path = package_dir.relative_to(project_root).as_posix()
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
        rel_path = index_file.relative_to(project_root).as_posix()
        print(f"Successfully built material index.")
        print(f"Index File: {rel_path}")
        if skipped:
            print(f"\nWarning: Skipped {len(skipped)} invalid normalized files:")
            for path in skipped:
                print(f"  - {path.relative_to(project_root).as_posix()}")
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

def main():
    parser = argparse.ArgumentParser(
        description="MEP Quotation Pipeline CLI Tool - Phase 1 Foundation"
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

    # Command search-material
    parser_search = subparsers.add_parser("search-material", help="Tìm kiếm vật tư từ chỉ mục")
    parser_search.add_argument("query", help="Từ khóa tìm kiếm (mã hoặc tên vật tư)")
    parser_search.set_defaults(func=handle_search_material)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
