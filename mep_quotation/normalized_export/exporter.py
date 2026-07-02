from datetime import datetime, timezone
from typing import Optional, List, Dict
from mep_quotation.spec.models import (
    QuotationPackageModel,
    NormalizedDraftModel,
    ReviewDecisionsFileModel,
    NormalizedQuotationModel,
    NormalizedItemModel,
    ExportSummaryModel,
    ParserWarningModel
)


def build_official_normalized(
    package: QuotationPackageModel,
    normalized_draft: NormalizedDraftModel,
    review_decisions: ReviewDecisionsFileModel
) -> NormalizedQuotationModel:
    """
    Xây dựng mô hình dữ liệu NormalizedQuotationModel chính thức.
    
    Quy trình:
    1. Sắp xếp items theo đúng thứ tự trong draft.
    2. Đối chiếu quyết định review (approved/edited) để lọc và ánh xạ.
    3. Áp dụng đè giá trị đối với quyết định edited (null override giữ nguyên gốc).
    4. Tính toán lại Amount, thừa kế Currency từ quotation-level và validate dữ liệu bắt buộc.
    5. Thiết lập ID tuần tự deterministic và lưu trữ thông tin tóm tắt xuất bản.
    """
    # Bản đồ các quyết định rà soát để truy cập nhanh O(1)
    decisions_map = {dec.draft_item_id: dec for dec in review_decisions.decisions}

    exported_items: List[NormalizedItemModel] = []
    
    # Bộ đếm thống kê
    draft_item_count = len(normalized_draft.items)
    approved_count = 0
    edited_count = 0
    rejected_count = 0
    unreviewed_count = 0

    # Lấy quotation-level currency từ draft
    quotation_currency = normalized_draft.currency.strip().upper() if normalized_draft.currency else None

    # Duyệt draft items theo đúng thứ tự xuất hiện
    for idx, draft_item in enumerate(normalized_draft.items):
        decision = decisions_map.get(draft_item.draft_item_id)
        
        if decision is None:
            unreviewed_count += 1
            continue
            
        if decision.decision_type == "rejected":
            rejected_count += 1
            continue
            
        if decision.decision_type not in ("approved", "edited"):
            # Bỏ qua các loại không hợp lệ (nếu có)
            continue

        item_warnings: List[ParserWarningModel] = []

        # Khởi tạo các giá trị từ draft item gốc
        material_code = draft_item.material_code
        description = draft_item.description
        brand = draft_item.brand
        unit = draft_item.unit
        quantity = draft_item.quantity
        unit_price = draft_item.unit_price
        currency = draft_item.currency
        amount = draft_item.amount
        evidence_text = draft_item.evidence.raw_evidence_text if draft_item.evidence else None
        page_number = draft_item.page_number
        confidence = draft_item.confidence
        reviewer = decision.reviewer

        # Áp dụng overrides nếu quyết định là edited
        if decision.decision_type == "edited":
            edited_count += 1
            overrides = decision.field_overrides
            if overrides:
                # Chỉ override khi giá trị khác null
                if overrides.material_code is not None:
                    material_code = overrides.material_code
                if overrides.description is not None:
                    description = overrides.description
                if overrides.brand is not None:
                    brand = overrides.brand
                if overrides.unit is not None:
                    unit = overrides.unit
                if overrides.quantity is not None:
                    quantity = overrides.quantity
                if overrides.unit_price is not None:
                    unit_price = overrides.unit_price
                if overrides.currency is not None:
                    currency = overrides.currency
                if overrides.amount is not None:
                    amount = overrides.amount
        else:
            approved_count += 1

        # --- Validate description phi-rỗng ---
        if not description or not description.strip():
            raise ValueError(
                f"Validation error: Item '{draft_item.draft_item_id}' approved/edited "
                "but description is missing or empty."
            )
        description = description.strip()

        # --- Validate unit_price phi-null ---
        if unit_price is None:
            raise ValueError(
                f"Validation error: Item '{draft_item.draft_item_id}' approved/edited "
                "but unit_price is missing."
            )

        # --- Xử lý Currency (uppercase và inherit) ---
        if currency:
            currency = currency.strip().upper()
        else:
            # Kế thừa quotation-level currency nếu item-level null
            if quotation_currency in ("VND", "USD"):
                currency = quotation_currency
                item_warnings.append(
                    ParserWarningModel(
                        code="currency_inherited_from_quotation",
                        message=f"Currency was inherited from quotation-level currency: {currency}"
                    )
                )
            else:
                raise ValueError(
                    f"Validation error: Item '{draft_item.draft_item_id}' lacks both item-level "
                    "and valid quotation-level currency."
                )

        if currency not in ("VND", "USD"):
            raise ValueError(
                f"Validation error: Item '{draft_item.draft_item_id}' has invalid currency "
                f"'{currency}'. Must be VND or USD."
            )

        # --- Tính toán lại Amount (Amount Rule) ---
        if quantity is not None and unit_price is not None:
            recomputed_amount = quantity * unit_price
            if amount is not None and abs(amount - recomputed_amount) > 1e-4:
                item_warnings.append(
                    ParserWarningModel(
                        code="amount_recomputed_from_quantity_and_unit_price",
                        message=f"Amount was recomputed from quantity and unit_price. Expected: {recomputed_amount}, Original: {amount}"
                    )
                )
            amount = recomputed_amount
        else:
            # Nếu quantity hoặc unit_price bị null -> giữ amount override nếu có, không tự tính
            pass

        # Sinh item_id tuần tự: {QUOTATION_ID}_ITEM_{SEQ:04d}
        seq = len(exported_items) + 1
        item_id = f"{package.quotation_id}_ITEM_{seq:04d}"

        # Tạo Official Item Model
        official_item = NormalizedItemModel(
            item_id=item_id,
            source_draft_item_id=draft_item.draft_item_id,
            source_review_decision_id=decision.decision_id,
            description=description,
            unit_price=unit_price,
            currency=currency,
            brand=brand,
            unit=unit,
            quantity=quantity,
            amount=amount,
            page_number=page_number,
            evidence_text=evidence_text,
            confidence=confidence,
            reviewer=reviewer,
            warnings=item_warnings,
            material_code=material_code,
            material_name=description,  # Giữ material_name = description chỉ để tương thích ngược với Phase 1, không dùng làm dữ liệu nghiệp vụ chính
            category=None,              # Không tự ý gán category nếu không có nguồn chính thức
            vat_rate=None               # Không tự ý gán vat_rate nếu không có nguồn chính thức
        )
        exported_items.append(official_item)

    # Xử lý warnings file-level
    file_warnings: List[ParserWarningModel] = []
    if len(exported_items) == 0:
        file_warnings.append(
            ParserWarningModel(
                code="no_approved_or_edited_items",
                message="No items were approved or edited for export."
            )
        )

    # Tạo thống kê xuất bản
    summary = ExportSummaryModel(
        draft_item_count=draft_item_count,
        approved_count=approved_count,
        edited_count=edited_count,
        rejected_count=rejected_count,
        unreviewed_count=unreviewed_count,
        exported_item_count=len(exported_items)
    )

    now = datetime.now(timezone.utc)
    
    # Tạo manifest
    manifest = NormalizedQuotationModel(
        schema_version="1.0",
        quotation_id=package.quotation_id,
        supplier_code=package.supplier.code,
        quotation_date=package.quotation_date,
        currency=quotation_currency or "VND",
        source_normalized_draft="normalized/normalized_draft.json",
        source_review_decisions="review/review_decisions.json",
        item_count=len(exported_items),
        export_summary=summary,
        warnings=file_warnings,
        items=exported_items,
        created_at=now,
        updated_at=now
    )

    return manifest
