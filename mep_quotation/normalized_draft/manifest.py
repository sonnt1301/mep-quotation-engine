import json
import re
from pathlib import Path

from mep_quotation.spec.models import NormalizedDraftModel, ItemCandidateManifestModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_normalized_draft(path: Path, data: NormalizedDraftModel) -> None:
    """Ghi NormalizedDraftModel xuống file JSON dạng deterministic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_normalized_draft_file(manifest_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp normalized_draft.json.

    Các quy tắc xác thực:
    1. Parse JSON và validate model NormalizedDraftModel.
    2. quotation_id khớp với package.json.
    3. supplier_code khớp với package.json nếu package có thông tin này, ngược lại phải là null.
    4. quotation_date khớp với package.json nếu package có thông tin này, ngược lại phải là null.
    5. Tệp parsed/item_candidates.json nguồn tồn tại thực tế.
    6. source_sha256 khớp chuẩn xác SHA256 của item_candidates.json.
    7. draft_item_id là duy nhất và tuân thủ định dạng {QUOTATION_ID}_DRAFTITEM_{SEQ}.
    8. Đối chiếu chéo với item_candidates.json:
       - source_item_candidate_id tồn tại thực tế.
       - Các trường định vị (source_row_id, page_number, start_line_number, end_line_number, offsets, raw_evidence_text)
         phải khớp chuẩn xác với item candidate nguồn.
    9. Đọc file Markdown text/quotation.md và so khớp:
       - markdown_content[start_offset:end_offset] == raw_evidence_text.
    10. item_count == len(items).
    11. review_required_count == số draft items có review_status = needs_review.
    12. review_status thuộc tập giá trị hợp lệ.
    13. amount đúng nếu quantity và unit_price đều có, ngược lại amount là null.
    14. Không tạo mới, ghi đè hoặc sửa đổi normalized/normalized.json.
    """
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    # 1. Parse JSON và validate Pydantic
    if not manifest_path.exists():
        raise ValueError(f"Normalized draft manifest file does not exist: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from normalized draft manifest: {e}")

    try:
        manifest = NormalizedDraftModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Normalized draft manifest failed Pydantic validation: {e}")

    # 2. Load package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. supplier_code khớp package.json
    expected_supplier = pkg.supplier.code if pkg.supplier else None
    if manifest.supplier_code != expected_supplier:
        raise ValueError(
            f"supplier_code mismatch: manifest has '{manifest.supplier_code}', "
            f"but package.json expected '{expected_supplier}'"
        )

    # 4. quotation_date khớp package.json
    expected_date = pkg.quotation_date
    if manifest.quotation_date != expected_date:
        raise ValueError(
            f"quotation_date mismatch: manifest has '{manifest.quotation_date}', "
            f"but package.json expected '{expected_date}'"
        )

    # 5. Tệp item_candidates.json nguồn tồn tại
    item_candidates_path = package_path / manifest.source_item_candidates
    if not item_candidates_path.exists():
        raise ValueError(f"Source item candidates file not found: {item_candidates_path}")

    # 6. source_sha256 khớp SHA256 của item_candidates.json
    actual_sha256 = calculate_sha256(item_candidates_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256 mismatch: manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of item_candidates.json is '{actual_sha256}'"
        )

    # 10. item_count == len(items)
    if manifest.item_count != len(manifest.items):
        raise ValueError(
            f"item_count ({manifest.item_count}) does not match actual items size ({len(manifest.items)})"
        )

    # Đọc nội dung Markdown
    md_path = package_path / "text" / "quotation.md"
    if not md_path.exists():
        raise ValueError(f"Markdown file not found: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Nạp item candidates để đối chiếu chéo
    with open(item_candidates_path, "r", encoding="utf-8") as f:
        try:
            cand_data = json.load(f)
            cand_manifest = ItemCandidateManifestModel(**cand_data)
            cand_map = {item.item_candidate_id: item for item in cand_manifest.items}
        except Exception as e:
            raise ValueError(f"Failed to load item candidates: {e}")

    item_ids = set()
    needs_review_count = 0
    allowed_statuses = {"auto_ready", "needs_review", "rejected_candidate"}

    # Xác thực từng draft item
    for item in manifest.items:
        # 7. draft_item_id unique và đúng định dạng
        if item.draft_item_id in item_ids:
            raise ValueError(f"Duplicate draft_item_id found: '{item.draft_item_id}'")
        item_ids.add(item.draft_item_id)

        id_pattern = rf"^{re.escape(pkg.quotation_id)}_DRAFTITEM_\d{{4}}$"
        if not re.match(id_pattern, item.draft_item_id):
            raise ValueError(
                f"draft_item_id '{item.draft_item_id}' does not match format "
                f"'{pkg.quotation_id}_DRAFTITEM_XXXX'"
            )

        # 12. review_status thuộc allowed values
        if item.review_status not in allowed_statuses:
            raise ValueError(
                f"Item {item.draft_item_id}: invalid review_status '{item.review_status}'"
            )
        
        if item.review_status == "needs_review":
            needs_review_count += 1

        # 8. Đối chiếu chéo với item_candidates.json
        if item.source_item_candidate_id not in cand_map:
            raise ValueError(
                f"Item {item.draft_item_id}: source_item_candidate_id '{item.source_item_candidate_id}' "
                f"does not exist in item_candidates.json"
            )

        cand_src = cand_map[item.source_item_candidate_id]

        if item.source_row_id != cand_src.source_row_id:
            raise ValueError(f"Item {item.draft_item_id}: source_row_id mismatch.")
        if item.page_number != cand_src.page_number:
            raise ValueError(f"Item {item.draft_item_id}: page_number mismatch.")
        if item.start_line_number != cand_src.start_line_number:
            raise ValueError(f"Item {item.draft_item_id}: start_line_number mismatch.")
        if item.end_line_number != cand_src.end_line_number:
            raise ValueError(f"Item {item.draft_item_id}: end_line_number mismatch.")
        if item.evidence.start_offset != cand_src.start_offset:
            raise ValueError(f"Item {item.draft_item_id}: start_offset mismatch.")
        if item.evidence.end_offset != cand_src.end_offset:
            raise ValueError(f"Item {item.draft_item_id}: end_offset mismatch.")
        if item.evidence.raw_evidence_text != cand_src.raw_evidence_text:
            raise ValueError(f"Item {item.draft_item_id}: raw_evidence_text mismatch.")

        # 9. So khớp evidence raw_evidence_text với lát cắt Markdown
        slice_text = markdown_content[item.evidence.start_offset:item.evidence.end_offset]
        if slice_text != item.evidence.raw_evidence_text:
            raise ValueError(
                f"Item {item.draft_item_id}: slice from Markdown content at "
                f"[{item.evidence.start_offset}:{item.evidence.end_offset}] does not match raw_evidence_text."
            )

        # 13. amount xác thực
        if item.quantity is not None and item.unit_price is not None:
            expected_amount = item.quantity * item.unit_price
            if item.amount is None:
                raise ValueError(f"Item {item.draft_item_id}: amount is None but quantity and price are both provided.")
            if abs(item.amount - expected_amount) > 1e-4:
                raise ValueError(
                    f"Item {item.draft_item_id}: amount {item.amount} does not equal quantity * price ({expected_amount})."
                )
        else:
            if item.amount is not None:
                raise ValueError(
                    f"Item {item.draft_item_id}: amount must be None when quantity or price is missing."
                )

    # 11. review_required_count == số draft items có status needs_review
    if manifest.review_required_count != needs_review_count:
        raise ValueError(
            f"review_required_count ({manifest.review_required_count}) "
            f"does not match actual needs_review count ({needs_review_count})"
        )
