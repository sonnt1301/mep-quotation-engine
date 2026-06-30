import json
import re
from pathlib import Path


from mep_quotation.spec.models import LineCandidatesManifestModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_line_candidates_manifest(path: Path, data: LineCandidatesManifestModel) -> None:
    """Ghi LineCandidatesManifestModel xuống file JSON dạng deterministic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_line_candidates_file(manifest_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp line_candidates.json và line candidates trích xuất được.

    Các quy tắc xác thực:
    1. Parse được JSON và khớp Pydantic schema của LineCandidatesManifestModel.
    2. quotation_id khớp với package.json.
    3. Tệp text/quotation_text.json nguồn tồn tại thực tế.
    4. Tệp text/quotation.md tồn tại thực tế.
    5. source_sha256 khớp chuẩn xác mã băm SHA256 của text/quotation.md.
    6. candidate_count == len(candidates).
    7. candidate_id là duy nhất và tuân thủ định dạng {QUOTATION_ID}_LINECAND_{SEQ}.
    8. Đọc file Markdown và kiểm chứng: markdown_content[start_offset:end_offset] == evidence.text.
    9. page_number trong dải 1..page_count.
    10. confidence nằm trong 0..1.
    11. unit_price_candidate >= 0 nếu không null.
    12. quantity_candidate > 0 nếu không null.
    13. Đảm bảo không chứa bất kỳ trường chuẩn hóa nào và không sinh file normalized.json.

    Raises:
        ValueError: Nếu bất kỳ quy tắc nào không thỏa mãn.
    """
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    # 1. Parse JSON và validate Pydantic
    if not manifest_path.exists():
        raise ValueError(f"Line candidates manifest file does not exist: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from line candidates manifest: {e}")

    try:
        manifest = LineCandidatesManifestModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Line candidates manifest failed Pydantic validation: {e}")

    # Đảm bảo không chứa các trường chuẩn hóa của các phase sau
    invalid_keys = {"items_normalized", "final_items", "normalized_items"}
    found_keys = invalid_keys.intersection(manifest_data.keys())
    if found_keys:
        raise ValueError(f"Line candidates manifest must not contain normalized quotation fields: {found_keys}")

    # 2. quotation_id khớp package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. Tệp text_manifest tồn tại
    text_manifest_path = package_path / manifest.source_text_manifest
    if not text_manifest_path.exists():
        raise ValueError(f"Source text manifest file not found: {text_manifest_path}")

    # 4. Tệp text_markdown tồn tại
    md_path = package_path / manifest.source_markdown
    if not md_path.exists():
        raise ValueError(f"Source markdown file not found: {md_path}")

    # 5. source_sha256 khớp SHA256 của text/quotation.md
    actual_sha256 = calculate_sha256(md_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256 mismatch: manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of quotation.md is '{actual_sha256}'"
        )

    # 6. candidate_count == len(candidates)
    if manifest.candidate_count != len(manifest.candidates):
        raise ValueError(
            f"candidate_count ({manifest.candidate_count}) "
            f"does not match actual candidates size ({len(manifest.candidates)})"
        )

    # Đọc nội dung Markdown
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Nạp text manifest bằng TextAssemblyManifestModel
    with open(text_manifest_path, "r", encoding="utf-8") as f:
        try:
            text_manifest_data = json.load(f)
            from mep_quotation.spec.models import TextAssemblyManifestModel
            text_manifest = TextAssemblyManifestModel(**text_manifest_data)
            page_count = text_manifest.page_count
        except Exception as e:
            raise ValueError(f"Failed to load text manifest: {e}")

    candidate_ids = set()

    # Xác thực từng candidate
    for cand in manifest.candidates:
        # 7. candidate_id unique và đúng định dạng
        if cand.candidate_id in candidate_ids:
            raise ValueError(f"Duplicate candidate_id found: '{cand.candidate_id}'")
        candidate_ids.add(cand.candidate_id)

        id_pattern = rf"^{re.escape(pkg.quotation_id)}_LINECAND_\d{{4}}$"
        if not re.match(id_pattern, cand.candidate_id):
            raise ValueError(
                f"candidate_id '{cand.candidate_id}' does not match format "
                f"'{pkg.quotation_id}_LINECAND_XXXX'"
            )

        # 8. markdown_content[start_offset:end_offset] == evidence.text
        ev = cand.evidence
        slice_text = markdown_content[ev.start_offset:ev.end_offset]
        if slice_text != ev.text:
            raise ValueError(
                f"Candidate {cand.candidate_id}: slice from Markdown content at "
                f"[{ev.start_offset}:{ev.end_offset}] does not match evidence text."
            )

        # 9. page_number trong dải 1..page_count
        if cand.page_number < 1 or cand.page_number > page_count:
            raise ValueError(
                f"Candidate {cand.candidate_id}: page_number {cand.page_number} "
                f"is out of valid range (1..{page_count})"
            )

        # 9b. Kiểm tra evidence offset nằm đúng trong range tương ứng với cand.page_number
        target_page = next((p for p in text_manifest.pages if p.page_number == cand.page_number), None)
        if target_page is None:
            raise ValueError(
                f"Candidate {cand.candidate_id}: page_number {cand.page_number} "
                f"does not exist in TextAssemblyManifestModel pages."
            )
        if ev.start_offset < target_page.start_offset or ev.end_offset > target_page.end_offset:
            raise ValueError(
                f"Candidate {cand.candidate_id}: evidence offset [{ev.start_offset}:{ev.end_offset}] "
                f"is out of the bounds [{target_page.start_offset}:{target_page.end_offset}] for page {cand.page_number}."
            )

        # 10. confidence trong 0..1
        if cand.confidence < 0.0 or cand.confidence > 1.0:
            raise ValueError(
                f"Candidate {cand.candidate_id}: confidence {cand.confidence} "
                f"is out of valid range (0.0..1.0)"
            )

        # 11. unit_price_candidate >= 0
        if cand.unit_price_candidate is not None and cand.unit_price_candidate < 0:
            raise ValueError(
                f"Candidate {cand.candidate_id}: unit_price_candidate "
                f"{cand.unit_price_candidate} cannot be negative"
            )

        # 12. quantity_candidate > 0
        if cand.quantity_candidate is not None and cand.quantity_candidate <= 0:
            raise ValueError(
                f"Candidate {cand.candidate_id}: quantity_candidate "
                f"{cand.quantity_candidate} must be greater than zero"
            )
