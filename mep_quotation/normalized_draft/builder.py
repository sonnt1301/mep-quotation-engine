from typing import List, Optional
from datetime import datetime, timezone
from mep_quotation.spec.models import (
    ItemCandidateManifestModel,
    ItemCandidateModel,
    NormalizedDraftModel,
    NormalizedDraftItemModel,
    NormalizedDraftEvidenceModel,
    ParserWarningModel,
    QuotationPackageModel
)


def determine_manifest_currency(
    items: List[ItemCandidateModel],
    package: Optional[QuotationPackageModel] = None
) -> Optional[str]:
    """
    Xác định đơn vị tiền tệ chung cấp Manifest.
    - Lấy từ package metadata nếu có trường currency rõ ràng (hiện tại SupplierModel/QuotationPackageModel chưa có field này).
    - Lấy từ currency chiếm đa số (quá bán > 50%) của các item candidates có currency khác null.
    - Nếu không chắc thì trả về None.
    """
    # Ta chưa có trường currency trong package, nên duyệt đa số item candidates
    currencies = [it.currency_candidate for it in items if it.currency_candidate]
    if not currencies:
        return None

    counts = {}
    for c in currencies:
        counts[c] = counts.get(c, 0) + 1

    total_cands_with_currency = len(currencies)
    for c, count in counts.items():
        if count > total_cands_with_currency / 2:
            return c

    return None


def build_draft_item(
    item: ItemCandidateModel,
    quotation_id: str,
    seq: int,
    manifest_currency: Optional[str]
) -> NormalizedDraftItemModel:
    """Chuyển đổi một ItemCandidateModel thành NormalizedDraftItemModel."""
    draft_item_id = f"{quotation_id}_DRAFTITEM_{seq:04d}"
    
    # 1. Thu thập thông tin thô
    description = item.description_candidate.strip() if item.description_candidate else None
    material_code = item.material_code_candidate.strip() if item.material_code_candidate else None
    brand = item.brand_candidate.strip() if item.brand_candidate else None
    unit = item.unit_candidate
    quantity = item.quantity_candidate
    unit_price = item.unit_price_candidate
    
    # 2. Xử lý currency cấp item
    currency = item.currency_candidate
    if not currency:
        currency = manifest_currency

    # 3. Tính toán và validate amount
    amount = None
    warnings = [ParserWarningModel(code=w.code, message=w.message) for w in item.warnings]
    review_reasons = []

    if quantity is not None and unit_price is not None:
        amount = quantity * unit_price
        if item.amount_candidate is not None:
            if abs(item.amount_candidate - amount) > 1e-4:
                warnings.append(ParserWarningModel(
                    code="amount_mismatch_recomputed",
                    message=f"Amount mismatch: source had {item.amount_candidate}, recomputed to {amount}."
                ))
                review_reasons.append("amount_mismatch_recomputed")
    else:
        amount = None

    # 4. Kiểm thử evidence hợp lệ
    evidence_valid = item.start_offset >= 0 and item.end_offset > item.start_offset

    # 5. Phân tích các lý do cần review hoặc reject
    if not description:
        review_reasons.append("missing_description")
    
    # Reject candidate rules
    is_rejected = False
    if not description and not material_code and not unit_price:
        is_rejected = True
        review_reasons.append("rejected_weak_candidate")
    
    if not is_rejected:
        if not unit:
            review_reasons.append("missing_unit")
        if unit_price is None:
            review_reasons.append("missing_unit_price")
        # missing_quantity: chỉ cảnh báo nếu có unit_price và amount cần tính mà quantity bị khuyết
        if unit_price is not None and quantity is None:
            review_reasons.append("missing_quantity")

    if not currency:
        review_reasons.append("currency_uncertain")
        
    if not evidence_valid:
        review_reasons.append("evidence_invalid")

    # 6. Điều chỉnh Confidence
    base_confidence = item.confidence
    # Trừ điểm
    if not description:
        base_confidence -= 0.20
    if unit_price is None:
        base_confidence -= 0.20
    if not evidence_valid:
        base_confidence -= 0.20
    # low_confidence từ source (nếu có warning low_confidence)
    if any(w.code == "low_confidence" for w in item.warnings):
        base_confidence -= 0.10

    # Cộng điểm
    if description and unit_price is not None and evidence_valid:
        base_confidence += 0.10
    if amount is not None:
        base_confidence += 0.05

    confidence = min(1.0, max(0.0, round(base_confidence, 2)))

    if confidence < 0.20:
        is_rejected = True
        if "rejected_weak_candidate" not in review_reasons:
            review_reasons.append("rejected_weak_candidate")

    if confidence < 0.5:
        if "low_confidence" not in review_reasons:
            review_reasons.append("low_confidence")

    # 7. Quyết định review_status
    if is_rejected:
        review_status = "rejected_candidate"
    elif (description and unit_price is not None and unit and quantity is not None and currency and
          confidence >= 0.75 and evidence_valid and
          not any(w.code == "low_confidence" for w in item.warnings)):
        review_status = "auto_ready"
    else:
        review_status = "needs_review"

    # Gộp các warnings từ review_reasons vào warning list nếu chưa có
    warnings_codes = {w.code for w in warnings}
    for reason in review_reasons:
        if reason not in warnings_codes:
            warnings.append(ParserWarningModel(code=reason, message=f"Item needs review due to: {reason}"))
            warnings_codes.add(reason)

    evidence = NormalizedDraftEvidenceModel(
        raw_evidence_text=item.raw_evidence_text,
        start_offset=item.start_offset,
        end_offset=item.end_offset
    )

    return NormalizedDraftItemModel(
        draft_item_id=draft_item_id,
        source_item_candidate_id=item.item_candidate_id,
        source_row_id=item.source_row_id,
        page_number=item.page_number,
        start_line_number=item.start_line_number,
        end_line_number=item.end_line_number,
        material_code=material_code,
        description=description,
        brand=brand,
        unit=unit,
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
        amount=amount,
        review_status=review_status,
        review_reasons=review_reasons,
        confidence=confidence,
        warnings=warnings,
        evidence=evidence
    )


def convert_manifest_to_draft(
    candidate_manifest: ItemCandidateManifestModel,
    package: Optional[QuotationPackageModel] = None,
    item_candidates_sha256: Optional[str] = None
) -> NormalizedDraftModel:
    """Chuyển đổi ItemCandidateManifestModel thành NormalizedDraftModel."""
    # 1. Xác định currency chung của manifest
    manifest_currency = determine_manifest_currency(candidate_manifest.items, package)

    # 2. Dựng các items
    items = []
    for seq, item in enumerate(candidate_manifest.items, start=1):
        draft_item = build_draft_item(item, candidate_manifest.quotation_id, seq, manifest_currency)
        items.append(draft_item)

    # 3. Đếm review_required_count
    review_required_count = len([it for it in items if it.review_status == "needs_review"])

    # 4. Lấy supplier_code và quotation_date từ package.json
    supplier_code = None
    quotation_date = None
    if package:
        # Nếu package có supplier và quotation_date
        supplier_code = package.supplier.code if package.supplier else None
        quotation_date = package.quotation_date

    return NormalizedDraftModel(
        schema_version="1.0",
        quotation_id=candidate_manifest.quotation_id,
        supplier_code=supplier_code,
        quotation_date=quotation_date,
        currency=manifest_currency,
        source_item_candidates="parsed/item_candidates.json",
        source_sha256=item_candidates_sha256 if item_candidates_sha256 else candidate_manifest.source_sha256,
        draft_builder_name="rule_based_normalized_draft_builder",
        draft_builder_version="1.0",
        item_count=len(items),
        review_required_count=review_required_count,
        items=items,
        warnings=[],
        generated_at=datetime.now(timezone.utc)
    )
