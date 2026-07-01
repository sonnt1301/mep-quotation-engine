import json
import re
from pathlib import Path

from mep_quotation.spec.models import ItemCandidateManifestModel, RowCandidateManifestModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_item_candidates_manifest(path: Path, data: ItemCandidateManifestModel) -> None:
    """Ghi ItemCandidateManifestModel xuống file JSON dạng deterministic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_item_candidates_file(manifest_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp item_candidates.json và các item candidates.

    Các quy tắc xác thực:
    1. Parse JSON và validate Pydantic model ItemCandidateManifestModel.
    2. quotation_id khớp với package.json.
    3. Tệp parsed/row_candidates.json nguồn tồn tại thực tế.
    4. Tệp text/quotation_text.json nguồn tồn tại thực tế.
    5. source_sha256 khớp chuẩn xác mã băm SHA256 của row_candidates.json.
    6. item_count == len(items).
    7. item_candidate_id là duy nhất và tuân thủ định dạng {QUOTATION_ID}_ITEMCAND_{SEQ}.
    8. Đọc file row_candidates.json để đối chiếu:
       - source_row_id của từng item candidate phải tồn tại trong row_candidates.json.
       - Các thuộc tính định vị (page_number, start_line_number, end_line_number, start_offset, end_offset, raw_evidence_text)
         phải khớp chuẩn xác với row candidate nguồn.
    9. Đọc file Markdown text/quotation.md và so khớp:
       - markdown_content[start_offset:end_offset] == raw_evidence_text.
    10. amount_candidate bằng quantity_candidate * unit_price_candidate (nếu có đủ), ngược lại bằng null.

    Raises:
        ValueError: Nếu bất kỳ quy tắc nào bị vi phạm.
    """
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    # 1. Parse JSON và validate Pydantic
    if not manifest_path.exists():
        raise ValueError(f"Item candidates manifest file does not exist: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from item candidates manifest: {e}")

    try:
        manifest = ItemCandidateManifestModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Item candidates manifest failed Pydantic validation: {e}")

    # 2. quotation_id khớp package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. Tệp row_candidates.json tồn tại
    row_candidates_path = package_path / manifest.source_row_candidates
    if not row_candidates_path.exists():
        raise ValueError(f"Source row candidates file not found: {row_candidates_path}")

    # 4. Tệp text_manifest tồn tại
    text_manifest_path = package_path / manifest.source_text_manifest
    if not text_manifest_path.exists():
        raise ValueError(f"Source text manifest file not found: {text_manifest_path}")

    # 5. source_sha256 khớp SHA256 của row_candidates.json
    actual_sha256 = calculate_sha256(row_candidates_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256 mismatch: manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of row_candidates.json is '{actual_sha256}'"
        )

    # 6. item_count == len(items)
    if manifest.item_count != len(manifest.items):
        raise ValueError(
            f"item_count ({manifest.item_count}) "
            f"does not match actual items size ({len(manifest.items)})"
        )

    # Đọc nội dung Markdown
    md_path = package_path / "text" / "quotation.md"
    if not md_path.exists():
        raise ValueError(f"Markdown file not found: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Nạp row candidates để đối chiếu chéo
    with open(row_candidates_path, "r", encoding="utf-8") as f:
        try:
            row_cand_data = json.load(f)
            row_manifest = RowCandidateManifestModel(**row_cand_data)
            row_cand_map = {row.row_id: row for row in row_manifest.rows}
        except Exception as e:
            raise ValueError(f"Failed to load row candidates: {e}")

    item_ids = set()

    # Xác thực từng item candidate
    for item in manifest.items:
        # 7. item_candidate_id unique và đúng định dạng
        if item.item_candidate_id in item_ids:
            raise ValueError(f"Duplicate item_candidate_id found: '{item.item_candidate_id}'")
        item_ids.add(item.item_candidate_id)

        id_pattern = rf"^{re.escape(pkg.quotation_id)}_ITEMCAND_\d{{4}}$"
        if not re.match(id_pattern, item.item_candidate_id):
            raise ValueError(
                f"item_candidate_id '{item.item_candidate_id}' does not match format "
                f"'{pkg.quotation_id}_ITEMCAND_XXXX'"
            )

        # 8. Đối chiếu chéo source_row_id với row_candidates.json
        if item.source_row_id not in row_cand_map:
            raise ValueError(
                f"Item {item.item_candidate_id}: source_row_id '{item.source_row_id}' "
                f"does not exist in row_candidates.json"
            )

        row_src = row_cand_map[item.source_row_id]

        # Kiểm chứng các thuộc tính định vị khớp row nguồn
        if item.page_number != row_src.page_number:
            raise ValueError(
                f"Item {item.item_candidate_id}: page_number {item.page_number} "
                f"does not match source row page_number {row_src.page_number}."
            )
        if item.start_line_number != row_src.start_line_number:
            raise ValueError(
                f"Item {item.item_candidate_id}: start_line_number {item.start_line_number} "
                f"does not match source row start_line_number {row_src.start_line_number}."
            )
        if item.end_line_number != row_src.end_line_number:
            raise ValueError(
                f"Item {item.item_candidate_id}: end_line_number {item.end_line_number} "
                f"does not match source row end_line_number {row_src.end_line_number}."
            )
        if item.start_offset != row_src.start_offset:
            raise ValueError(
                f"Item {item.item_candidate_id}: start_offset {item.start_offset} "
                f"does not match source row start_offset {row_src.start_offset}."
            )
        if item.end_offset != row_src.end_offset:
            raise ValueError(
                f"Item {item.item_candidate_id}: end_offset {item.end_offset} "
                f"does not match source row end_offset {row_src.end_offset}."
            )
        if item.raw_evidence_text != row_src.evidence_text:
            raise ValueError(
                f"Item {item.item_candidate_id}: raw_evidence_text "
                f"does not match source row evidence_text."
            )

        # 9. So khớp raw_evidence_text với lát cắt Markdown
        slice_text = markdown_content[item.start_offset:item.end_offset]
        if slice_text != item.raw_evidence_text:
            raise ValueError(
                f"Item {item.item_candidate_id}: slice from Markdown content at "
                f"[{item.start_offset}:{item.end_offset}] does not match raw_evidence_text."
            )

        # 10. amount_candidate xác thực
        if item.quantity_candidate is not None and item.unit_price_candidate is not None:
            expected_amount = item.quantity_candidate * item.unit_price_candidate
            if item.amount_candidate is None:
                raise ValueError(
                    f"Item {item.item_candidate_id}: amount_candidate is None "
                    f"but quantity and unit_price are both provided."
                )
            if abs(item.amount_candidate - expected_amount) > 1e-4:
                raise ValueError(
                    f"Item {item.item_candidate_id}: amount_candidate {item.amount_candidate} "
                    f"does not equal quantity * unit_price ({expected_amount})."
                )
        else:
            if item.amount_candidate is not None:
                raise ValueError(
                    f"Item {item.item_candidate_id}: amount_candidate must be None "
                    f"when quantity or unit_price is missing."
                )
