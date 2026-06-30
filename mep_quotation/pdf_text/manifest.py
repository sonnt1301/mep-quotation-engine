import json
from pathlib import Path

from mep_quotation.spec.models import RawTextManifestModel
from mep_quotation.package.loader import load_package_json


def write_raw_text_manifest(path: Path, data: RawTextManifestModel) -> None:
    """
    Ghi RawTextManifestModel ra file JSON deterministic.

    Args:
        path: Đường dẫn tuyệt đối tới file đích (source/raw_text.json).
        data: Dữ liệu manifest cần ghi.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_raw_text_file(raw_text_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp raw_text.json sau khi sinh.

    Các quy tắc kiểm tra:
    1. Parse được JSON và validate Pydantic schema.
    2. raw_text.quotation_id khớp package.json.
    3. raw_text.page_count khớp số trang PDF thực tế.
    4. Nếu có source/metadata.json → page_count phải khớp.
    5. Nếu có source/page_manifest.json → page_count phải khớp.
    6. page_number bắt đầu từ 1, liên tục, không thiếu trang.
    7. character_count == len(text) cho từng trang.

    Raises:
        ValueError: Nếu bất kỳ quy tắc nào thất bại.
    """
    import fitz  # PyMuPDF

    raw_text_path = Path(raw_text_path)
    package_path = Path(package_path)

    # 1. Parse và validate Pydantic schema
    with open(raw_text_path, "r", encoding="utf-8") as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"raw_text.json is not valid JSON: {e}")

    try:
        manifest = RawTextManifestModel(**raw_data)
    except Exception as e:
        raise ValueError(f"raw_text.json failed Pydantic validation: {e}")

    # 2. Validate quotation_id khớp package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"raw_text.quotation_id '{manifest.quotation_id}' "
            f"does not match package.quotation_id '{pkg.quotation_id}'"
        )

    # 3. Validate page_count khớp số trang PDF thực tế
    pdf_path = package_path / "source" / "original.pdf"
    if pdf_path.exists():
        doc = fitz.open(pdf_path)
        try:
            actual_page_count = len(doc)
        finally:
            doc.close()

        if manifest.page_count != actual_page_count:
            raise ValueError(
                f"raw_text.page_count ({manifest.page_count}) "
                f"does not match actual PDF page count ({actual_page_count})"
            )

    # 4. Cross-check với source/metadata.json nếu tồn tại
    metadata_path = package_path / "source" / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            try:
                meta = json.load(f)
                meta_page_count = meta.get("page_count")
                if meta_page_count is not None and manifest.page_count != meta_page_count:
                    raise ValueError(
                        f"raw_text.page_count ({manifest.page_count}) "
                        f"does not match metadata.json page_count ({meta_page_count})"
                    )
            except json.JSONDecodeError:
                pass  # Bỏ qua nếu metadata.json bị lỗi

    # 5. Cross-check với source/page_manifest.json nếu tồn tại
    page_manifest_path = package_path / "source" / "page_manifest.json"
    if page_manifest_path.exists():
        with open(page_manifest_path, "r", encoding="utf-8") as f:
            try:
                pm = json.load(f)
                pm_page_count = pm.get("page_count")
                if pm_page_count is not None and manifest.page_count != pm_page_count:
                    raise ValueError(
                        f"raw_text.page_count ({manifest.page_count}) "
                        f"does not match page_manifest.json page_count ({pm_page_count})"
                    )
            except json.JSONDecodeError:
                pass  # Bỏ qua nếu page_manifest.json bị lỗi

    # 6. Validate page_number bắt đầu từ 1, liên tục, không thiếu trang
    expected_page_numbers = list(range(1, manifest.page_count + 1))
    actual_page_numbers = [p.page_number for p in manifest.pages]
    if actual_page_numbers != expected_page_numbers:
        raise ValueError(
            f"raw_text.pages page_numbers are not sequential starting from 1. "
            f"Expected: {expected_page_numbers}, Got: {actual_page_numbers}"
        )

    # 7. Validate character_count == len(text) cho từng trang
    for page in manifest.pages:
        expected_count = len(page.text)
        if page.character_count != expected_count:
            raise ValueError(
                f"Page {page.page_number}: character_count ({page.character_count}) "
                f"does not match len(text) ({expected_count})"
            )
