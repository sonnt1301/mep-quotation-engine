import json
from pathlib import Path

from mep_quotation.spec.models import TextAssemblyManifestModel, RawTextManifestModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_assembly_manifest(path: Path, data: TextAssemblyManifestModel) -> None:
    """Ghi TextAssemblyManifestModel xuống file JSON dạng deterministic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_assembly_manifest_file(manifest_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp quotation_text.json và quotation.md sau khi ghép văn bản.

    Các quy tắc xác thực bao gồm:
    1. Parse được JSON và khớp Pydantic schema của TextAssemblyManifestModel.
    2. quotation_id khớp với package.json.
    3. Tệp raw_text.json nguồn tồn tại thực tế trên đĩa.
    4. source_sha256 khớp chuẩn xác mã băm SHA256 của source/raw_text.json.
    5. page_count khớp với raw_text.page_count.
    6. Độ dài danh sách pages khớp với page_count.
    7. page_number trong pages phải bắt đầu từ 1, liên tục không đứt đoạn.
    8. character_count của từng trang khớp với raw_text.pages[n].character_count.
    9. total_characters bằng tổng character_count của các trang.
    10. pages_with_text bằng tổng số trang có has_text=True.
    11. File Markdown (markdown_path) tồn tại trên đĩa.
    12. Đọc file Markdown và kiểm chứng: markdown_content[start_offset:end_offset] == raw_text.pages[n].text.
    13. Không chứa các trường thông tin vật tư parsed (materials, items, v.v.).

    Raises:
        ValueError: Nếu bất kỳ quy tắc xác thực nào không thỏa mãn.
    """
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    # 1. Parse JSON và validate Pydantic
    if not manifest_path.exists():
        raise ValueError(f"Assembly manifest file does not exist: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from assembly manifest: {e}")

    try:
        manifest = TextAssemblyManifestModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Assembly manifest failed Pydantic validation: {e}")

    # Kiểm tra không chứa các trường parsed vật tư
    invalid_keys = {"items", "materials", "parsed_items", "quotation_data"}
    found_keys = invalid_keys.intersection(manifest_data.keys())
    if found_keys:
        raise ValueError(f"Assembly manifest must not contain parsed material/quotation fields: {found_keys}")

    # 2. quotation_id khớp package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. Tệp raw_text.json nguồn tồn tại
    raw_text_path = package_path / manifest.source_raw_text
    if not raw_text_path.exists():
        raise ValueError(f"Source raw_text file not found: {raw_text_path}")

    # 4. source_sha256 khớp SHA256 của source/raw_text.json
    actual_sha256 = calculate_sha256(raw_text_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256 mismatch: manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of raw_text.json is '{actual_sha256}'"
        )

    # Nạp raw_text.json để làm mốc đối chiếu
    with open(raw_text_path, "r", encoding="utf-8") as f:
        raw_manifest = RawTextManifestModel(**json.load(f))

    # 5. page_count khớp raw_text.page_count
    if manifest.page_count != raw_manifest.page_count:
        raise ValueError(
            f"page_count mismatch: manifest has {manifest.page_count}, "
            f"but raw_text.json has {raw_manifest.page_count}"
        )

    # 6. pages length khớp page_count
    if len(manifest.pages) != manifest.page_count:
        raise ValueError(
            f"pages list size ({len(manifest.pages)}) does not match page_count ({manifest.page_count})"
        )

    # 7. page_number bắt đầu từ 1, liên tục
    expected_numbers = list(range(1, manifest.page_count + 1))
    actual_numbers = [p.page_number for p in manifest.pages]
    if actual_numbers != expected_numbers:
        raise ValueError(
            f"pages page_numbers are not sequential starting from 1. "
            f"Expected: {expected_numbers}, Got: {actual_numbers}"
        )

    # 11. File Markdown tồn tại
    md_path = package_path / manifest.markdown_path
    if not md_path.exists():
        raise ValueError(f"Assembled Markdown file not found: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    total_chars_calc = 0
    pages_with_text_calc = 0

    # Đối chiếu chéo từng trang
    for i, page in enumerate(manifest.pages):
        raw_page = raw_manifest.pages[i]

        # 8. character_count khớp raw_text
        if page.character_count != raw_page.character_count:
            raise ValueError(
                f"Page {page.page_number}: character_count ({page.character_count}) "
                f"does not match raw_text page character_count ({raw_page.character_count})"
            )

        if page.has_text != raw_page.has_text:
            raise ValueError(
                f"Page {page.page_number}: has_text ({page.has_text}) "
                f"does not match raw_text page has_text ({raw_page.has_text})"
            )

        # 12. markdown_content[start_offset:end_offset] == raw_text.pages[n].text
        slice_text = markdown_content[page.start_offset:page.end_offset]
        if slice_text != raw_page.text:
            raise ValueError(
                f"Page {page.page_number}: slice from Markdown content at "
                f"[{page.start_offset}:{page.end_offset}] does not match raw page text."
            )

        total_chars_calc += page.character_count
        if page.has_text:
            pages_with_text_calc += 1

    # 9. total_characters bằng tổng character_count
    if manifest.total_characters != total_chars_calc:
        raise ValueError(
            f"total_characters mismatch: manifest has {manifest.total_characters}, "
            f"calculated sum is {total_chars_calc}"
        )

    # 10. pages_with_text bằng số page has_text=True
    if manifest.pages_with_text != pages_with_text_calc:
        raise ValueError(
            f"pages_with_text mismatch: manifest has {manifest.pages_with_text}, "
            f"calculated count is {pages_with_text_calc}"
        )
