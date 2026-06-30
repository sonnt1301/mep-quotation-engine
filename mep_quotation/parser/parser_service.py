import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.spec.models import TextAssemblyManifestModel, LineCandidatesManifestModel
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.parser.line_parser import scan_markdown_lines
from mep_quotation.parser.candidate_manifest import write_line_candidates_manifest, validate_line_candidates_file


def parse_package_line_candidates(
    package_path: Path,
    overwrite: bool = False
) -> Path:
    """
    Quét và trích xuất các dòng ứng viên chứa báo giá thô từ Markdown của package.

    Flow:
    1. Load package.json
    2. Kiểm tra sự tồn tại của text/quotation.md và text/quotation_text.json
    3. Overwrite check -> fail nếu parsed/line_candidates.json đã tồn tại và overwrite=False
    4. Ghi log audit: line_parser_started
    5. Đọc Markdown và trích xuất dòng ứng viên
    6. Ghi log audit: line_parser_lines_scanned và line_candidates_extracted
    7. Tạo thư mục parsed/ (nếu chưa có) và ghi file parsed/line_candidates.json
    8. Ghi log audit: line_candidates_written
    9. Validate tệp line_candidates.json sau khi ghi
    10. Cập nhật package.json (files.line_candidates, updated_at)
    11. Chạy validate_package_integrity
    12. Ghi log audit: line_parser_completed

    Nếu có lỗi: Ghi log audit line_parser_failed và re-raise.

    Args:
        package_path: Đường dẫn tới thư mục package.
        overwrite: Cho phép ghi đè nếu line_candidates.json đã tồn tại.

    Returns:
        package_path (Path) sau khi hoàn tất.

    Raises:
        FileNotFoundError: Nếu package hoặc các file đầu vào Phase 5 không tìm thấy.
        ValueError: Nếu vi phạm quy tắc cản ghi đè.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    # Xác định đường dẫn file đầu vào và đầu ra
    md_path = package_path / "text" / "quotation.md"
    assembly_manifest_path = package_path / "text" / "quotation_text.json"
    candidates_output_path = package_path / "parsed" / "line_candidates.json"

    try:
        # 1. Ghi log audit bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="line_parser_started",
            quotation_id=package.quotation_id,
            details={
                "overwrite": overwrite,
                "source_markdown": "text/quotation.md"
            }
        )

        # 2. Kiểm tra sự tồn tại của file đầu vào Phase 5
        if not md_path.exists():
            raise FileNotFoundError(f"Assembled Markdown file not found: {md_path}")
        if not assembly_manifest_path.exists():
            raise FileNotFoundError(f"Assembly manifest file not found: {assembly_manifest_path}")

        # 3. Overwrite check (Atomic check)
        if not overwrite and candidates_output_path.exists():
            raise ValueError(
                f"Line candidates file already exists at {candidates_output_path}. "
                "Set overwrite=True to replace it."
            )

        # Đọc dữ liệu đầu vào
        with open(md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        with open(assembly_manifest_path, "r", encoding="utf-8") as f:
            assembly_manifest_data = json.load(f)
        assembly_manifest = TextAssemblyManifestModel(**assembly_manifest_data)

        # 5. Phân tích trích xuất dòng ứng viên
        candidates = scan_markdown_lines(
            markdown_content=markdown_content,
            assembly_manifest=assembly_manifest,
            quotation_id=package.quotation_id
        )

        # 6. Ghi log audit quét dòng và trích xuất xong
        total_lines = len(markdown_content.splitlines())
        log_event(
            package_path=package_path,
            level="INFO",
            event="line_parser_lines_scanned",
            quotation_id=package.quotation_id,
            details={
                "total_lines_scanned": total_lines
            }
        )

        log_event(
            package_path=package_path,
            level="INFO",
            event="line_candidates_extracted",
            quotation_id=package.quotation_id,
            details={
                "candidate_count": len(candidates)
            }
        )

        # 7. Đảm bảo thư mục parsed/ được tạo trước khi ghi file
        candidates_output_path.parent.mkdir(parents=True, exist_ok=True)

        source_sha256 = calculate_sha256(md_path)
        manifest = LineCandidatesManifestModel(
            schema_version="1.0",
            quotation_id=package.quotation_id,
            source_text_manifest="text/quotation_text.json",
            source_markdown="text/quotation.md",
            source_sha256=source_sha256,
            parser_name="rule_based_line_candidate_v1",
            parser_version="0.1.0",
            candidate_count=len(candidates),
            candidates=candidates,
            warnings=[],
            generated_at=datetime.now(timezone.utc)
        )

        # Ghi tệp
        write_line_candidates_manifest(candidates_output_path, manifest)

        # 8. Ghi log audit ghi file
        log_event(
            package_path=package_path,
            level="INFO",
            event="line_candidates_written",
            quotation_id=package.quotation_id,
            details={
                "line_candidates_path": "parsed/line_candidates.json"
            }
        )

        # 9. Validate sau khi ghi
        validate_line_candidates_file(candidates_output_path, package_path)

        # 10. Cập nhật package.json
        package.files.line_candidates = "parsed/line_candidates.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Ghi log audit hoàn tất
        log_event(
            package_path=package_path,
            level="INFO",
            event="line_parser_completed",
            quotation_id=package.quotation_id,
            details={
                "candidate_count": len(candidates)
            }
        )

        return package_path

    except Exception as e:
        # Ghi log audit lỗi
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="line_parser_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
