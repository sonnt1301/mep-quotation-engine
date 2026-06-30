import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.pdf_text.extractor import extract_pdf_text
from mep_quotation.pdf_text.manifest import write_raw_text_manifest, validate_raw_text_file


def extract_package_text(
    package_path: Path,
    overwrite: bool = False,
) -> Path:
    """
    Trích xuất text gốc từ PDF của package và ghi vào source/raw_text.json.

    Flow:
    1. Load package.json
    2. Kiểm tra encrypted từ metadata.json → fail rõ ràng nếu encrypted
    3. Overwrite check → fail rõ ràng nếu raw_text.json đã tồn tại và overwrite=False
    4. Ghi audit event: pdf_text_extraction_started
    5. Extract text từng trang bằng extractor
    6. Ghi audit event: pdf_text_extracted
    7. Ghi source/raw_text.json
    8. Ghi audit event: raw_text_written
    9. Validate raw_text.json sau khi ghi
    10. Cập nhật package.json (files.raw_text, updated_at)
    11. Chạy kiểm tra toàn vẹn package
    12. Ghi audit event: pdf_text_extraction_completed
    13. Trả về package_path

    Nếu có lỗi bất kỳ: ghi audit event pdf_text_extraction_failed và re-raise.

    Args:
        package_path: Đường dẫn tới thư mục package.
        overwrite: Cho phép ghi đè nếu raw_text.json đã tồn tại.

    Returns:
        package_path (Path) sau khi xử lý xong.

    Raises:
        FileNotFoundError: Nếu package hoặc PDF không tìm thấy.
        ValueError: Nếu PDF encrypted, hoặc raw_text.json đã tồn tại khi overwrite=False.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    # 2. Kiểm tra mã hóa từ metadata.json
    metadata_path = package_path / "source" / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            try:
                meta_data = json.load(f)
                if meta_data.get("encrypted") is True:
                    raise ValueError(
                        f"PDF package '{package.quotation_id}' is encrypted. "
                        "Cannot extract text from encrypted files."
                    )
            except json.JSONDecodeError:
                pass

    pdf_file_path = package_path / "source" / "original.pdf"
    if not pdf_file_path.exists():
        raise FileNotFoundError(f"Original PDF file not found: {pdf_file_path}")

    # 3. Overwrite check
    raw_text_path = package_path / "source" / "raw_text.json"
    if not overwrite and raw_text_path.exists():
        raise ValueError(
            f"raw_text.json already exists at {raw_text_path}. "
            "Set overwrite=True to re-extract."
        )

    try:
        # 4. Audit: bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_text_extraction_started",
            quotation_id=package.quotation_id,
            details={
                "overwrite": overwrite,
                "pdf_path": "source/original.pdf"
            }
        )

        # 5. Extract text
        manifest = extract_pdf_text(pdf_file_path)

        # Gán quotation_id từ package vào manifest
        manifest.quotation_id = package.quotation_id

        # 6. Audit: extract xong
        total_chars = sum(p.character_count for p in manifest.pages)
        pages_with_text = sum(1 for p in manifest.pages if p.has_text)
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_text_extracted",
            quotation_id=package.quotation_id,
            details={
                "page_count": manifest.page_count,
                "total_characters": total_chars,
                "pages_with_text": pages_with_text,
                "extraction_engine": manifest.extraction_engine,
                "extraction_engine_version": manifest.extraction_engine_version
            }
        )

        # 7. Ghi raw_text.json
        write_raw_text_manifest(raw_text_path, manifest)

        # 8. Audit: ghi file xong
        log_event(
            package_path=package_path,
            level="INFO",
            event="raw_text_written",
            quotation_id=package.quotation_id,
            details={
                "raw_text_path": "source/raw_text.json"
            }
        )

        # 9. Validate sau khi ghi
        validate_raw_text_file(raw_text_path, package_path)

        # 10. Cập nhật package.json
        package.files.raw_text = "source/raw_text.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Audit: hoàn tất
        log_event(
            package_path=package_path,
            level="INFO",
            event="pdf_text_extraction_completed",
            quotation_id=package.quotation_id,
            details={
                "page_count": manifest.page_count,
                "total_characters": total_chars,
                "pages_with_text": pages_with_text
            }
        )

        return package_path

    except Exception as e:
        # Ghi audit lỗi – không re-raise ngoại lệ thứ hai nếu log thất bại
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="pdf_text_extraction_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
