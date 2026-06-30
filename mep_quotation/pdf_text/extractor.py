from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mep_quotation.spec.models import RawTextPageModel, RawTextManifestModel
from mep_quotation.pdf.checksum import calculate_sha256


def extract_pdf_text(pdf_path: Path) -> RawTextManifestModel:
    """
    Trích xuất text gốc (native text) từng trang của tệp PDF.

    Yêu cầu:
    - Chỉ extract native text, không OCR, không AI, không parse nội dung.
    - Không trim, không normalize, không sửa khoảng trắng.
    - Lưu nguyên chuỗi text do engine trả về.
    - Nếu PDF encrypted → fail ngay lập tức, không attempt decrypt.
    - Nếu trang không có text → has_text=False, text="".

    Args:
        pdf_path: Đường dẫn tuyệt đối tới file PDF gốc.

    Returns:
        RawTextManifestModel chứa text từng trang và metadata kỹ thuật.

    Raises:
        FileNotFoundError: Nếu file PDF không tồn tại.
        ValueError: Nếu PDF bị mã hóa (encrypted).
    """
    import fitz  # PyMuPDF

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Lấy version engine
    engine_version: Optional[str] = None
    try:
        engine_version = fitz.version[0]
    except Exception:
        engine_version = None

    # Tính SHA256 của file PDF gốc
    source_sha256 = calculate_sha256(pdf_path)

    # Mở PDF và kiểm tra mã hóa
    doc = fitz.open(pdf_path)
    try:
        if doc.is_encrypted:
            raise ValueError(
                f"PDF file is encrypted: {pdf_path}. "
                "Cannot extract text from encrypted files. "
                "Do not attempt to decrypt."
            )

        page_count = len(doc)
        pages = []

        for page_idx in range(page_count):
            page = doc[page_idx]
            # Lấy text thô – không trim, không normalize, không sửa khoảng trắng
            text: str = page.get_text()
            has_text: bool = bool(text)
            character_count: int = len(text)

            pages.append(RawTextPageModel(
                page_number=page_idx + 1,
                has_text=has_text,
                character_count=character_count,
                text=text
            ))
    finally:
        doc.close()

    return RawTextManifestModel(
        schema_version="1.0",
        quotation_id="",  # Sẽ được gán bởi text_service sau khi load package
        source_pdf="source/original.pdf",
        source_sha256=source_sha256,
        extraction_engine="pymupdf",
        extraction_engine_version=engine_version,
        page_count=page_count,
        pages=pages,
        generated_at=datetime.now(timezone.utc)
    )
