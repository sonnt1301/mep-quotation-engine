import re
from typing import List, Optional
from mep_quotation.spec.models import (
    RowCandidateModel,
    ItemCandidateModel,
    ParserWarningModel
)


def map_unit_alias(unit: Optional[str]) -> Optional[str]:
    """Map alias đơn vị tính thô ở mức candidate-level rất hạn chế."""
    if not unit:
        return None
    
    clean_unit = unit.strip().lower()
    if clean_unit in ("pcs", "piece", "cái"):
        return "cái"
    elif clean_unit in ("m", "meter", "met"):
        return "m"
    elif clean_unit in ("bộ", "set"):
        return "bộ"
    
    return unit.strip()


def detect_currency(row: RowCandidateModel) -> Optional[str]:
    """
    Xác định currency_candidate.
    - Lấy từ row.currency_candidate nếu có.
    - Nếu có unit_price_candidate nhưng currency_candidate null, chỉ gán VND khi trong
      evidence_text thể hiện rõ từ khóa liên quan đến VND (VND, VNĐ, đ, đồng).
    - Ngược lại trả về null.
    """
    if row.currency_candidate:
        return row.currency_candidate

    if row.unit_price_candidate is not None:
        text = row.evidence_text.lower()
        # Tìm kiếm các marker tiền tệ VND
        if any(marker in text for marker in ("vnd", "vnđ", " đồng", "đồng", "đ/")):
            return "VND"
        # Kiểm tra ký tự đơn lẻ 'đ' đứng riêng biệt hoặc ở cuối số
        if re.search(r'\bđ\b|\d\s*đ', text):
            return "VND"

    return None


def convert_row_to_item(
    row: RowCandidateModel,
    quotation_id: str,
    item_seq: int
) -> ItemCandidateModel:
    """Chuyển đổi một RowCandidateModel thành ItemCandidateModel."""
    # 1. Chuẩn hóa nhẹ các thuộc tính candidate
    description = row.description_candidate.strip() if row.description_candidate else None
    material_code = row.material_code_candidate.strip() if row.material_code_candidate else None
    brand = row.brand_candidate.strip() if row.brand_candidate else None
    
    # Map unit alias cơ bản
    unit = map_unit_alias(row.unit_candidate)
    
    quantity = row.quantity_candidate
    unit_price = row.unit_price_candidate
    
    # Xác định currency có điều kiện
    currency = detect_currency(row)

    # Tính amount_candidate khi có đủ đơn giá và số lượng
    amount = None
    if quantity is not None and unit_price is not None:
        amount = quantity * unit_price

    # 2. Tính toán confidence deterministic
    confidence = 0.0
    if description:
        confidence += 0.25
    if material_code:
        confidence += 0.15
    if brand:
        confidence += 0.10
    if unit:
        confidence += 0.10
    if unit_price:
        confidence += 0.20
    if quantity:
        confidence += 0.10
    if row.start_offset >= 0 and row.end_offset > row.start_offset:
        confidence += 0.10

    confidence = min(1.0, round(confidence, 2))

    # Gộp warnings
    warnings_map = {w.code: w.message for w in row.warnings}
    if confidence < 0.5:
        warnings_map["low_confidence"] = "Item candidate has low confidence."

    warnings = [
        ParserWarningModel(code=code, message=msg)
        for code, msg in warnings_map.items()
    ]

    item_candidate_id = f"{quotation_id}_ITEMCAND_{item_seq:04d}"

    return ItemCandidateModel(
        item_candidate_id=item_candidate_id,
        source_row_id=row.row_id,
        page_number=row.page_number,
        start_line_number=row.start_line_number,
        end_line_number=row.end_line_number,
        description_candidate=description,
        material_code_candidate=material_code,
        brand_candidate=brand,
        unit_candidate=unit,
        quantity_candidate=quantity,
        unit_price_candidate=unit_price,
        currency_candidate=currency,
        amount_candidate=amount,
        raw_evidence_text=row.evidence_text,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        confidence=confidence,
        warnings=warnings
    )
