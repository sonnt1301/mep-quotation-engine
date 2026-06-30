import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.text_assembly.assembler import assemble_raw_text
from mep_quotation.text_assembly.manifest import write_assembly_manifest, validate_assembly_manifest_file


def assemble_package_text(
    package_path: Path,
    overwrite: bool = False,
) -> Path:
    """
    Chuẩn bị dữ liệu text assembled từ source/raw_text.json cho parser.

    Flow:
    1. Load package.json
    2. Kiểm tra PDF encrypted từ metadata.json -> fail nếu encrypted
    3. Overwrite check -> fail nếu output đã tồn tại và overwrite=False (Atomic check)
    4. Ghi log: text_assembly_started
    5. Thực hiện assemble raw text
    6. Ghi log: text_assembled
    7. Ghi tệp text/quotation.md -> ghi log: quotation_markdown_written
    8. Ghi tệp text/quotation_text.json -> ghi log: quotation_text_manifest_written
    9. Validate tệp quotation_text.json sau khi ghi
    10. Cập nhật package.json (text_markdown, text_manifest, updated_at)
    11. Chạy validate_package_integrity
    12. Ghi log: text_assembly_completed

    Nếu có lỗi: Ghi log: text_assembly_failed và re-raise lỗi.

    Args:
        package_path: Đường dẫn tới thư mục package.
        overwrite: Cho phép ghi đè nếu các tệp output đã tồn tại.

    Returns:
        package_path (Path) sau khi hoàn tất.

    Raises:
        FileNotFoundError: Nếu package hoặc raw_text.json không tìm thấy.
        ValueError: Nếu PDF encrypted hoặc vi phạm kiểm tra cản ghi đè.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    try:
        # 2. Kiểm tra encrypted từ metadata.json
        metadata_path = package_path / "source" / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as f:
                try:
                    meta_data = json.load(f)
                    if meta_data.get("encrypted") is True:
                        raise ValueError(
                            f"PDF package '{package.quotation_id}' is encrypted. "
                            "Cannot assemble text from encrypted files."
                        )
                except json.JSONDecodeError:
                    pass

        raw_text_path = package_path / "source" / "raw_text.json"
        if not raw_text_path.exists():
            raise FileNotFoundError(f"raw_text.json file not found in package: {raw_text_path}")

        # 3. Overwrite check (Atomic check)
        md_output_path = package_path / "text" / "quotation.md"
        manifest_output_path = package_path / "text" / "quotation_text.json"

        if not overwrite:
            if md_output_path.exists():
                raise ValueError(
                    f"Assembled Markdown file already exists at {md_output_path}. "
                    "Set overwrite=True to replace it."
                )
            if manifest_output_path.exists():
                raise ValueError(
                    f"Assembly manifest file already exists at {manifest_output_path}. "
                    "Set overwrite=True to replace it."
                )

        # 4. Ghi log bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="text_assembly_started",
            quotation_id=package.quotation_id,
            details={
                "overwrite": overwrite,
                "source_raw_text": "source/raw_text.json"
            }
        )

        # 5. Assemble
        markdown_content, assembly_manifest = assemble_raw_text(raw_text_path)

        # 6. Ghi log đã assemble xong trong memory
        log_event(
            package_path=package_path,
            level="INFO",
            event="text_assembled",
            quotation_id=package.quotation_id,
            details={
                "page_count": assembly_manifest.page_count,
                "total_characters": assembly_manifest.total_characters,
                "pages_with_text": assembly_manifest.pages_with_text
            }
        )

        # Đảm bảo thư mục text/ tồn tại
        md_output_path.parent.mkdir(parents=True, exist_ok=True)

        # 7. Ghi tệp Markdown và ghi log
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        log_event(
            package_path=package_path,
            level="INFO",
            event="quotation_markdown_written",
            quotation_id=package.quotation_id,
            details={
                "markdown_path": "text/quotation.md"
            }
        )

        # 8. Ghi tệp Manifest và ghi log
        write_assembly_manifest(manifest_output_path, assembly_manifest)

        log_event(
            package_path=package_path,
            level="INFO",
            event="quotation_text_manifest_written",
            quotation_id=package.quotation_id,
            details={
                "manifest_path": "text/quotation_text.json"
            }
        )

        # 9. Validate sau khi ghi xuống đĩa
        validate_assembly_manifest_file(manifest_output_path, package_path)

        # 10. Cập nhật package.json
        package.files.text_markdown = "text/quotation.md"
        package.files.text_manifest = "text/quotation_text.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Ghi log hoàn tất
        log_event(
            package_path=package_path,
            level="INFO",
            event="text_assembly_completed",
            quotation_id=package.quotation_id,
            details={
                "quotation_id": package.quotation_id,
                "page_count": assembly_manifest.page_count,
                "total_characters": assembly_manifest.total_characters
            }
        )

        return package_path

    except Exception as e:
        # Ghi log lỗi kiểm toán
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="text_assembly_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
