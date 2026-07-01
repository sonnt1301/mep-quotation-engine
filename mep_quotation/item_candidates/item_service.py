import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.spec.models import RowCandidateManifestModel, ItemCandidateManifestModel
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.item_candidates.builder import convert_row_to_item
from mep_quotation.item_candidates.manifest import write_item_candidates_manifest, validate_item_candidates_file


def build_item_candidates(
    package_path: Path,
    overwrite: bool = False
) -> Path:
    """
    Điều phối việc xây dựng item candidates từ row candidates.

    Flow:
    1. Load package.json
    2. Kiểm duyệt đầu vào (sự tồn tại của các tệp Phase 7)
    3. Overwrite check -> fail nếu item_candidates.json đã tồn tại và overwrite=False
    4. Ghi log audit: item_candidate_build_started
    5. Đọc row candidates và thực hiện chuyển đổi cấu trúc sang item candidates
    6. Ghi log audit: item_candidates_built
    7. Ghi tệp parsed/item_candidates.json
    8. Ghi log audit: item_candidates_written
    9. Validate tệp tin item_candidates.json sau ghi
    10. Cập nhật package.json
    11. Chạy validate_package_integrity
    12. Ghi log audit: item_candidate_build_completed

    Nếu lỗi: Ghi log audit item_candidate_build_failed và re-raise.

    Args:
        package_path: Đường dẫn tới thư mục package.
        overwrite: Cho phép ghi đè nếu item_candidates.json đã tồn tại.

    Returns:
        package_path (Path) sau khi hoàn tất.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    # Xác định đường dẫn các file
    row_candidates_path = package_path / "parsed" / "row_candidates.json"
    items_output_path = package_path / "parsed" / "item_candidates.json"

    try:
        # Ghi log audit bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="item_candidate_build_started",
            quotation_id=package.quotation_id,
            details={"overwrite": overwrite}
        )

        # 2. Kiểm duyệt đầu vào
        if not row_candidates_path.exists():
            raise FileNotFoundError(f"Row candidates file not found: {row_candidates_path}")

        # 3. Overwrite check (Atomic check)
        if not overwrite and items_output_path.exists():
            raise ValueError(
                f"Item candidates file already exists at {items_output_path}. "
                "Set overwrite=True to replace it."
            )

        # Đọc dữ liệu
        with open(row_candidates_path, "r", encoding="utf-8") as f:
            row_cand_data = json.load(f)
        row_manifest = RowCandidateManifestModel(**row_cand_data)

        # 5. Chuyển đổi cấu trúc sang item candidates
        items = []
        for seq, row in enumerate(row_manifest.rows, start=1):
            item = convert_row_to_item(row, package.quotation_id, seq)
            items.append(item)

        # 6. Log built
        log_event(
            package_path=package_path,
            level="INFO",
            event="item_candidates_built",
            quotation_id=package.quotation_id,
            details={"item_count": len(items)}
        )

        # 7. Đảm bảo parsed/ tồn tại trước khi ghi tệp
        items_output_path.parent.mkdir(parents=True, exist_ok=True)

        source_sha256 = calculate_sha256(row_candidates_path)
        manifest = ItemCandidateManifestModel(
            schema_version="1.0",
            quotation_id=package.quotation_id,
            source_row_candidates="parsed/row_candidates.json",
            source_sha256=source_sha256,
            source_text_manifest="text/quotation_text.json",
            builder_name="rule_based_item_candidate_builder",
            builder_version="1.0",
            item_count=len(items),
            items=items,
            warnings=[],
            generated_at=datetime.now(timezone.utc)
        )

        # Ghi tệp
        write_item_candidates_manifest(items_output_path, manifest)

        # 8. Log written
        log_event(
            package_path=package_path,
            level="INFO",
            event="item_candidates_written",
            quotation_id=package.quotation_id,
            details={"item_candidates_path": "parsed/item_candidates.json"}
        )

        # 9. Validate sau ghi
        validate_item_candidates_file(items_output_path, package_path)

        # 10. Cập nhật package.json
        package.files.item_candidates = "parsed/item_candidates.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Log completed
        log_event(
            package_path=package_path,
            level="INFO",
            event="item_candidate_build_completed",
            quotation_id=package.quotation_id,
            details={"item_count": len(items)}
        )

        return package_path

    except Exception as e:
        # Ghi log audit thất bại
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="item_candidate_build_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
