import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.spec.models import (
    ReviewDecisionsFileModel,
    ReviewDecisionModel,
    ReviewFieldOverridesModel,
    NormalizedDraftModel
)
from mep_quotation.review.decisions import (
    write_review_decisions,
    load_review_decisions,
    validate_review_decisions_file
)


def create_empty_review_file(
    package_path: Path,
    reviewer: str = "human",
    overwrite: bool = False
) -> Path:
    """Tạo tệp review_decisions.json rỗng và cập nhật package.json."""
    package_path = Path(package_path).resolve()
    package = load_package_json(package_path)
    
    review_dir = package_path / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_file = review_dir / "review_decisions.json"
    
    # Kiểm tra tồn tại và overwrite check
    if not overwrite and review_file.exists():
        raise ValueError(
            f"Review decisions file already exists at {review_file}. "
            "Set overwrite=True to replace it."
        )

    # Đảm bảo normalized_draft.json tồn tại
    draft_path = package_path / "normalized" / "normalized_draft.json"
    if not draft_path.exists():
        raise FileNotFoundError(f"Normalized draft file not found: {draft_path}")
    source_sha256 = calculate_sha256(draft_path)

    # Tạo manifest rỗng
    now = datetime.now(timezone.utc)
    manifest = ReviewDecisionsFileModel(
        schema_version="1.0",
        quotation_id=package.quotation_id,
        source_normalized_draft="normalized/normalized_draft.json",
        source_sha256=source_sha256,
        reviewer=reviewer,
        decision_count=0,
        decisions=[],
        warnings=[],
        created_at=now,
        updated_at=now
    )

    try:
        # Atomic write
        write_review_decisions(review_file, manifest)

        # Cập nhật package.json
        package.files.review_decisions = "review/review_decisions.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # Gọi validate package
        validate_package_integrity(package_path)

        # Ghi log audit
        log_event(
            package_path=package_path,
            level="INFO",
            event="review_file_created",
            quotation_id=package.quotation_id,
            details={"overwrite": overwrite, "reviewer": reviewer}
        )

        return review_file
    except Exception as e:
        log_event(
            package_path=package_path,
            level="ERROR",
            event="review_operation_failed",
            quotation_id=package.quotation_id,
            details={"operation": "create_empty_review_file", "error": str(e)}
        )
        raise e


def record_review_decision(
    package_path: Path,
    draft_item_id: str,
    decision_type: str,
    reviewer: str = "human",
    reason: Optional[str] = None,
    field_overrides: Optional[ReviewFieldOverridesModel] = None,
    overwrite: bool = False
) -> Path:
    """Ghi nhận hoặc thay thế quyết định review của người dùng đối với một draft item."""
    package_path = Path(package_path).resolve()
    package = load_package_json(package_path)
    
    review_file = package_path / "review" / "review_decisions.json"
    
    # 1. Tạo tệp review nếu chưa tồn tại
    if not review_file.exists():
        create_empty_review_file(package_path, reviewer=reviewer, overwrite=True)

    # 2. Nạp dữ liệu
    manifest = load_review_decisions(review_file)

    # Đọc tệp nháp để kiểm chứng sự tồn tại của draft_item_id
    draft_path = package_path / "normalized" / "normalized_draft.json"
    with open(draft_path, "r", encoding="utf-8") as f:
        draft_data = json.load(f)
    draft_manifest = NormalizedDraftModel(**draft_data)
    draft_items_set = {item.draft_item_id for item in draft_manifest.items}

    if draft_item_id not in draft_items_set:
        raise ValueError(
            f"draft_item_id '{draft_item_id}' does not exist in normalized_draft.json"
        )

    # Trim reason
    reason = reason.strip() if reason else None

    # Validate input rules trước khi ghi file
    allowed_currencies = {"VND", "USD", None}
    if decision_type == "approved":
        if field_overrides is not None:
            raise ValueError("Approved decision must not have field overrides.")
    elif decision_type == "rejected":
        if field_overrides is not None:
            raise ValueError("Rejected decision must not have field overrides.")
        if not reason:
            raise ValueError("Rejected decision must have a non-empty reason.")
    elif decision_type == "edited":
        if field_overrides is None:
            raise ValueError("Edited decision must have field overrides.")
        
        override_dict = field_overrides.model_dump()
        if all(v is None for v in override_dict.values()):
            raise ValueError("Edited decision overrides must contain at least one non-null field.")
        
        if not reason:
            raise ValueError("Edited decision must have a non-empty reason.")

        # Validate override values
        if field_overrides.quantity is not None and field_overrides.quantity < 0:
            raise ValueError("Override quantity must be non-negative.")
        if field_overrides.unit_price is not None and field_overrides.unit_price < 0:
            raise ValueError("Override unit_price must be non-negative.")
        if field_overrides.amount is not None and field_overrides.amount < 0:
            raise ValueError("Override amount must be non-negative.")
        
        if field_overrides.description is not None and not field_overrides.description.strip():
            raise ValueError("Override description must not be empty.")
        if field_overrides.unit is not None and not field_overrides.unit.strip():
            raise ValueError("Override unit must not be empty.")

        if field_overrides.currency is not None and field_overrides.currency not in allowed_currencies:
            raise ValueError("Override currency must be VND, USD or null.")
    else:
        raise ValueError(f"Invalid decision_type: {decision_type}")

    # Tìm xem draft_item_id đã có decision chưa
    existing_idx = None
    for idx, dec in enumerate(manifest.decisions):
        if dec.draft_item_id == draft_item_id:
            existing_idx = idx
            break

    now = datetime.now(timezone.utc)
    is_replaced = False
    target_decision_id = None

    try:
        if existing_idx is not None:
            # Nếu đã có và overwrite=False -> ném lỗi
            if not overwrite:
                raise ValueError(
                    f"Decision for draft_item_id '{draft_item_id}' already exists. "
                    "Set overwrite=True to replace it."
                )
            
            # Thay thế decision cũ: giữ nguyên decision_id cũ, created_at cũ.
            # Cập nhật reviewer mới, decision_type/reason/overrides mới và updated_at mới.
            old_dec = manifest.decisions[existing_idx]
            target_decision_id = old_dec.decision_id
            
            updated_dec = ReviewDecisionModel(
                decision_id=old_dec.decision_id,
                draft_item_id=draft_item_id,
                decision_type=decision_type,
                reviewer=reviewer,  # Cập nhật reviewer mới
                reason=reason,
                field_overrides=field_overrides,
                created_at=old_dec.created_at,
                updated_at=now
            )
            manifest.decisions[existing_idx] = updated_dec
            is_replaced = True
        else:
            # Thêm mới: Tính toán sequence ID tăng dần theo quy tắc: max(seq) + 1
            max_seq = 0
            for dec in manifest.decisions:
                match = re.search(r"_REVIEW_(\d+)$", dec.decision_id)
                if match:
                    seq_val = int(match.group(1))
                    if seq_val > max_seq:
                        max_seq = seq_val
            
            new_seq = max_seq + 1
            target_decision_id = f"{package.quotation_id}_REVIEW_{new_seq:04d}"
            
            new_dec = ReviewDecisionModel(
                decision_id=target_decision_id,
                draft_item_id=draft_item_id,
                decision_type=decision_type,
                reviewer=reviewer,
                reason=reason,
                field_overrides=field_overrides,
                created_at=now,
                updated_at=now
            )
            manifest.decisions.append(new_dec)

        # Cập nhật manifest metadata
        manifest.decision_count = len(manifest.decisions)
        manifest.updated_at = now

        # Atomic write
        write_review_decisions(review_file, manifest)

        # Validate file sau ghi
        validate_review_decisions_file(review_file, package_path)

        # Cập nhật package.json
        package.files.review_decisions = "review/review_decisions.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # Gọi validate package chéo
        validate_package_integrity(package_path)

        # Ghi audit log
        log_event(
            package_path=package_path,
            level="INFO",
            event="review_decision_replaced" if is_replaced else "review_decision_recorded",
            quotation_id=package.quotation_id,
            details={
                "decision_id": target_decision_id,
                "draft_item_id": draft_item_id,
                "decision_type": decision_type,
                "reviewer": reviewer
            }
        )

        return review_file

    except Exception as e:
        log_event(
            package_path=package_path,
            level="ERROR",
            event="review_operation_failed",
            quotation_id=package.quotation_id,
            details={"operation": "record_review_decision", "error": str(e)}
        )
        raise e


def list_review_decisions(package_path: Path) -> ReviewDecisionsFileModel:
    """Nạp tệp review_decisions.json và trả về danh sách quyết định."""
    package_path = Path(package_path).resolve()
    review_file = package_path / "review" / "review_decisions.json"
    
    if not review_file.exists():
        raise FileNotFoundError(f"Review decisions file not found at: {review_file}")
        
    return load_review_decisions(review_file)
