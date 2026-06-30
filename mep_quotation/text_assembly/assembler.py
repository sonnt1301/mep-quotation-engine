import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.spec.models import RawTextManifestModel, TextAssemblyManifestModel, TextAssemblyPageModel
from mep_quotation.pdf.checksum import calculate_sha256


def assemble_raw_text(raw_text_path: Path) -> tuple[str, TextAssemblyManifestModel]:
    """
    Nạp tệp raw_text.json và lắp ghép thành cấu trúc văn bản Markdown cùng siêu dữ liệu định vị offset.

    Quy tắc:
    - Không sửa nội dung text của từng trang, không trim, không normalize, giữ nguyên dòng trắng và khoảng trắng.
    - start_offset và end_offset được tính theo Python string index trong tệp Markdown kết quả.
    - markdown_content[start_offset:end_offset] == raw_text.pages[n].text.

    Args:
        raw_text_path: Đường dẫn tuyệt đối tới file source/raw_text.json.

    Returns:
        tuple[markdown_content_str, TextAssemblyManifestModel]

    Raises:
        FileNotFoundError: Nếu tệp raw_text.json không tồn tại.
        ValueError: Nếu offset mapping kiểm tra chéo thất bại hoặc dữ liệu không khớp.
    """
    raw_text_path = Path(raw_text_path).resolve()
    if not raw_text_path.exists():
        raise FileNotFoundError(f"raw_text.json file not found: {raw_text_path}")

    with open(raw_text_path, "r", encoding="utf-8") as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from raw_text.json: {e}")

    # Khởi tạo model để validate cấu trúc đầu vào
    raw_manifest = RawTextManifestModel(**raw_data)
    source_sha256 = calculate_sha256(raw_text_path)

    # 1. Dựng header chung của file Markdown
    gen_at_str = (
        raw_manifest.generated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        if isinstance(raw_manifest.generated_at, datetime)
        else str(raw_manifest.generated_at)
    )

    md_lines = [
        "# Quotation Text",
        "",
        f"Quotation ID: {raw_manifest.quotation_id}",
        f"Source PDF: {raw_manifest.source_pdf}",
        f"Page Count: {raw_manifest.page_count}",
        f"Generated At: {gen_at_str}"
    ]
    markdown_content = "\n".join(md_lines)

    pages_assembly = []
    total_characters = 0
    pages_with_text = 0

    # 2. Duyệt qua từng trang và lắp ghép văn bản
    for page in raw_manifest.pages:
        # Thêm separator và page heading chuẩn tắc
        separator = f"\n\n---\n\n## Page {page.page_number}\n\n"
        markdown_content += separator

        start_offset = len(markdown_content)
        markdown_content += page.text
        end_offset = len(markdown_content)

        # Kiểm định tính đồng nhất của offset ngay tại chỗ
        extracted_text = markdown_content[start_offset:end_offset]
        if extracted_text != page.text:
            raise ValueError(
                f"Offset mapping validation failed on page {page.page_number}. "
                "The sliced markdown string does not match the original page text."
            )

        pages_assembly.append(TextAssemblyPageModel(
            page_number=page.page_number,
            has_text=page.has_text,
            character_count=page.character_count,
            start_offset=start_offset,
            end_offset=end_offset
        ))

        total_characters += page.character_count
        if page.has_text:
            pages_with_text += 1

    # Thêm một ký tự xuống dòng ở cuối file Markdown cho chuẩn tắc
    markdown_content += "\n"

    manifest = TextAssemblyManifestModel(
        schema_version="1.0",
        quotation_id=raw_manifest.quotation_id,
        source_raw_text="source/raw_text.json",
        source_sha256=source_sha256,
        page_count=raw_manifest.page_count,
        total_characters=total_characters,
        pages_with_text=pages_with_text,
        markdown_path="text/quotation.md",
        pages=pages_assembly,
        generated_at=datetime.now(timezone.utc)
    )

    return markdown_content, manifest
