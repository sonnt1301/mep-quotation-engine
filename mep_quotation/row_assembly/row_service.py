import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.spec.models import LineCandidatesManifestModel, RowCandidateManifestModel
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.row_assembly.assembler import group_candidates_to_rows
from mep_quotation.row_assembly.manifest import write_row_candidates_manifest, validate_row_candidates_file


def assemble_row_candidates(
    package_path: Path,
    overwrite: bool = False,
    max_line_gap_for_price: int = 6
) -> Path:
    """
    Điều phối dịch vụ quét và ghép các line candidates thành row candidates.

    Flow:
    1. Load package.json
    2. Kiểm duyệt đầu vào (sự tồn tại của các tệp Phase 6 và Phase 5)
    3. Overwrite check -> fail nếu row_candidates.json đã tồn tại và overwrite=False
    4. Ghi log audit: row_assembly_started
    5. Đọc line candidates, MD content và thực hiện ghép dòng
    6. Ghi log audit: row_candidates_assembled
    7. Ghi tệp parsed/row_candidates.json
    8. Ghi log audit: row_candidates_written
    9. Validate tệp tin row_candidates.json sau ghi
    10. Cập nhật package.json
    11. Chạy validate_package_integrity
    12. Ghi log audit: row_assembly_completed

    Nếu lỗi: Ghi log audit row_assembly_failed và re-raise.

    Args:
        package_path: Đường dẫn tới thư mục package.
        overwrite: Cho phép ghi đè nếu row_candidates.json đã tồn tại.
        max_line_gap_for_price: Khoảng cách dòng tối đa cho phép liên kết giá.

    Returns:
        package_path (Path) sau khi hoàn tất.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    # Xác định đường dẫn các file
    md_path = package_path / "text" / "quotation.md"
    line_candidates_path = package_path / "parsed" / "line_candidates.json"
    rows_output_path = package_path / "parsed" / "row_candidates.json"

    try:
        # Ghi log audit bắt đầu ngay lập tức để ghi nhận mọi lỗi validation sau đó
        log_event(
            package_path=package_path,
            level="INFO",
            event="row_assembly_started",
            quotation_id=package.quotation_id,
            details={
                "overwrite": overwrite,
                "max_line_gap_for_price": max_line_gap_for_price
            }
        )

        # 2. Kiểm duyệt đầu vào
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
        if not line_candidates_path.exists():
            raise FileNotFoundError(f"Line candidates file not found: {line_candidates_path}")

        # 3. Overwrite check (Atomic check)
        if not overwrite and rows_output_path.exists():
            raise ValueError(
                f"Row candidates file already exists at {rows_output_path}. "
                "Set overwrite=True to replace it."
            )

        # Đọc dữ liệu
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        with open(line_candidates_path, "r", encoding="utf-8") as f:
            line_cand_data = json.load(f)
        line_manifest = LineCandidatesManifestModel(**line_cand_data)

        # 5. Phân tích ghép dòng
        rows = group_candidates_to_rows(
            line_candidates=line_manifest.candidates,
            markdown_content=markdown_content,
            quotation_id=package.quotation_id,
            max_line_gap_for_price=max_line_gap_for_price
        )

        # 6. Log assembled
        log_event(
            package_path=package_path,
            level="INFO",
            event="row_candidates_assembled",
            quotation_id=package.quotation_id,
            details={
                "row_count": len(rows)
            }
        )

        # 7. Đảm bảo parsed/ tồn tại trước khi ghi tệp
        rows_output_path.parent.mkdir(parents=True, exist_ok=True)

        source_sha256 = calculate_sha256(line_candidates_path)
        manifest = RowCandidateManifestModel(
            schema_version="1.0",
            quotation_id=package.quotation_id,
            source_line_candidates="parsed/line_candidates.json",
            source_text_manifest="text/quotation_text.json",
            source_sha256=source_sha256,
            assembler_name="rule_based_row_candidate_assembler",
            assembler_version="1.0",
            row_count=len(rows),
            rows=rows,
            warnings=[],
            generated_at=datetime.now(timezone.utc)
        )

        # Ghi tệp
        write_row_candidates_manifest(rows_output_path, manifest)

        # 8. Log written
        log_event(
            package_path=package_path,
            level="INFO",
            event="row_candidates_written",
            quotation_id=package.quotation_id,
            details={
                "row_candidates_path": "parsed/row_candidates.json"
            }
        )

        # 9. Validate sau ghi
        validate_row_candidates_file(rows_output_path, package_path)

        # 10. Cập nhật package.json
        package.files.row_candidates = "parsed/row_candidates.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Log completed
        log_event(
            package_path=package_path,
            level="INFO",
            event="row_assembly_completed",
            quotation_id=package.quotation_id,
            details={
                "row_count": len(rows)
            }
        )

        return package_path

    except Exception as e:
        # Ghi log audit thất bại
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="row_assembly_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
