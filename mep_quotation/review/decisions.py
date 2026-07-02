import json
import os
import re
from pathlib import Path
from mep_quotation.spec.models import ReviewDecisionsFileModel, NormalizedDraftModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_review_decisions(path: Path, data: ReviewDecisionsFileModel) -> None:
    """Ghi ReviewDecisionsFileModel xuống file JSON dạng deterministic bằng atomic write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Ghi dữ liệu ra tệp tạm thời
    tmp_path = path.with_suffix(".tmp")
    entry_dict = data.model_dump(mode="json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    
    # 2. Đổi tên tệp tạm sang tệp chính thức (atomic replace)
    os.replace(tmp_path, path)


def load_review_decisions(path: Path) -> ReviewDecisionsFileModel:
    """Nạp tệp review_decisions.json và trả về ReviewDecisionsFileModel."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Review decisions file not found at: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return ReviewDecisionsFileModel(**data)


def validate_review_decisions_file(review_file_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp review_decisions.json.
    
    Các quy tắc xác thực:
    1. Parse JSON và validate model ReviewDecisionsFileModel.
    2. quotation_id khớp với package.json.
    3. source_normalized_draft tồn tại thực tế.
    4. source_sha256 khớp chuẩn xác SHA256 của normalized_draft.json. Nếu bị lệch -> ném lỗi source_sha256_mismatch.
    5. decision_count == len(decisions).
    6. decision_id duy nhất và tuân thủ định dạng {QUOTATION_ID}_REVIEW_{SEQ}.
    7. draft_item_id duy nhất (mỗi item có tối đa 1 decision) và tồn tại thực tế trong normalized_draft.json.
    8. Quyết định (approved/rejected/edited) tuân thủ quy tắc dữ liệu riêng biệt.
    9. field_overrides chỉ tồn tại khi decision_type = edited và không chứa trường ngoài whitelist.
    10. reason được trim trước khi kiểm thử, không rỗng đối với rejected và edited.
    11. quantity, unit_price, amount không âm nếu có. description và unit không rỗng sau trim. currency thuộc VND/USD/null.
    12. Không được phép chỉnh sửa hoặc tạo mới normalized/normalized.json và normalized/normalized_draft.json.
    """
    review_file_path = Path(review_file_path)
    package_path = Path(package_path)

    # 1. Parse JSON và Pydantic validate
    if not review_file_path.exists():
        raise ValueError(f"Review decisions file does not exist: {review_file_path}")

    with open(review_file_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from review decisions: {e}")

    try:
        manifest = ReviewDecisionsFileModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Review decisions manifest failed Pydantic validation: {e}")

    # 2. Load package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: review manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. source_normalized_draft tồn tại
    draft_path = package_path / manifest.source_normalized_draft
    if not draft_path.exists():
        raise ValueError(f"Source normalized draft file not found: {draft_path}")

    # 4. source_sha256 khớp SHA256 của normalized_draft.json
    actual_sha256 = calculate_sha256(draft_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256_mismatch: review manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of normalized_draft.json is '{actual_sha256}'"
        )

    # 5. decision_count == len(decisions)
    if manifest.decision_count != len(manifest.decisions):
        raise ValueError(
            f"decision_count ({manifest.decision_count}) does not match actual decisions size ({len(manifest.decisions)})"
        )

    # Load normalized_draft.json để đối chiếu chéo
    with open(draft_path, "r", encoding="utf-8") as f:
        try:
            draft_data = json.load(f)
            draft_manifest = NormalizedDraftModel(**draft_data)
            draft_items_set = {item.draft_item_id for item in draft_manifest.items}
        except Exception as e:
            raise ValueError(f"Failed to load normalized draft: {e}")

    decision_ids = set()
    draft_item_ids = set()
    allowed_types = {"approved", "rejected", "edited"}
    allowed_currencies = {"VND", "USD", None}

    # Xác thực từng decision
    for dec in manifest.decisions:
        # 6. decision_id unique và đúng định dạng
        if dec.decision_id in decision_ids:
            raise ValueError(f"Duplicate decision_id found: '{dec.decision_id}'")
        decision_ids.add(dec.decision_id)

        id_pattern = rf"^{re.escape(pkg.quotation_id)}_REVIEW_\d{{4}}$"
        if not re.match(id_pattern, dec.decision_id):
            raise ValueError(
                f"decision_id '{dec.decision_id}' does not match format "
                f"'{pkg.quotation_id}_REVIEW_XXXX'"
            )

        # 7. draft_item_id unique và tồn tại trong draft
        if dec.draft_item_id in draft_item_ids:
            raise ValueError(f"Duplicate decision for draft_item_id: '{dec.draft_item_id}'")
        draft_item_ids.add(dec.draft_item_id)

        if dec.draft_item_id not in draft_items_set:
            raise ValueError(
                f"Decision {dec.decision_id}: draft_item_id '{dec.draft_item_id}' "
                f"does not exist in normalized_draft.json"
            )

        # 8. Kiểu quyết định
        if dec.decision_type not in allowed_types:
            raise ValueError(
                f"Decision {dec.decision_id}: invalid decision_type '{dec.decision_type}'"
            )

        # Trim reason trước khi validate
        trimmed_reason = dec.reason.strip() if dec.reason else None

        # Quy tắc theo loại
        if dec.decision_type == "approved":
            if dec.field_overrides is not None:
                raise ValueError(f"Decision {dec.decision_id}: approved decision must not have field overrides.")
        
        elif dec.decision_type == "rejected":
            if dec.field_overrides is not None:
                raise ValueError(f"Decision {dec.decision_id}: rejected decision must not have field overrides.")
            if not trimmed_reason:
                raise ValueError(f"Decision {dec.decision_id}: rejected decision must have a non-empty reason.")

        elif dec.decision_type == "edited":
            if dec.field_overrides is None:
                raise ValueError(f"Decision {dec.decision_id}: edited decision must have field overrides.")
            
            # Kiểm duyệt xem có ít nhất một trường ghi đè phi-null không
            overrides = dec.field_overrides
            override_dict = overrides.model_dump()
            if all(v is None for v in override_dict.values()):
                raise ValueError(f"Decision {dec.decision_id}: edited decision overrides must contain at least one non-null field.")
            
            if not trimmed_reason:
                raise ValueError(f"Decision {dec.decision_id}: edited decision must have a non-empty reason.")

            # Validate overrides dữ liệu cụ thể
            if overrides.quantity is not None and overrides.quantity < 0:
                raise ValueError(f"Decision {dec.decision_id}: override quantity must be non-negative.")
            if overrides.unit_price is not None and overrides.unit_price < 0:
                raise ValueError(f"Decision {dec.decision_id}: override unit_price must be non-negative.")
            if overrides.amount is not None and overrides.amount < 0:
                raise ValueError(f"Decision {dec.decision_id}: override amount must be non-negative.")
            
            if overrides.description is not None and not overrides.description.strip():
                raise ValueError(f"Decision {dec.decision_id}: override description must not be empty.")
            if overrides.unit is not None and not overrides.unit.strip():
                raise ValueError(f"Decision {dec.decision_id}: override unit must not be empty.")

            if overrides.currency is not None and overrides.currency not in allowed_currencies:
                raise ValueError(f"Decision {dec.decision_id}: override currency must be VND, USD or null.")
