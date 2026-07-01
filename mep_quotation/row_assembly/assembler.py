from typing import List, Optional
from mep_quotation.spec.models import (
    LineCandidateModel,
    RowCandidateModel,
    ParserWarningModel
)


def has_strong_description(lc: LineCandidateModel) -> bool:
    """Kiểm tra xem line candidate có chứa mô tả vật tư thô mạnh không."""
    return lc.description_candidate is not None and len(lc.description_candidate.strip()) > 0


def is_price_only(lc: LineCandidateModel) -> bool:
    """Kiểm tra xem line candidate chỉ chứa đơn giá thô không."""
    return (
        lc.unit_price_candidate is not None and
        lc.description_candidate is None and
        lc.brand_candidate is None and
        lc.material_code_candidate is None and
        lc.unit_candidate is None
    )


def assemble_elements_to_row(
    elements: List[LineCandidateModel],
    markdown_content: str,
    quotation_id: str,
    row_seq: int
) -> RowCandidateModel:
    """Gộp danh sách các line candidates liên kết thành một RowCandidateModel."""
    # Sắp xếp các candidates theo line_number tăng dần
    elements = sorted(elements, key=lambda x: x.line_number)
    
    first_lc = elements[0]
    last_lc = elements[-1]

    # Tính toán start/end line_number và offset
    start_line = min(lc.line_number for lc in elements)
    end_line = max(lc.line_number for lc in elements)
    
    start_offset = min(lc.evidence.start_offset for lc in elements)
    end_offset = max(lc.evidence.end_offset for lc in elements)
    evidence_text = markdown_content[start_offset:end_offset]

    # Nối mô tả của các candidates
    desc_parts = []
    for lc in elements:
        if lc.description_candidate:
            part = lc.description_candidate.strip()
            if part and part not in desc_parts:
                desc_parts.append(part)
    description = " ".join(desc_parts) if desc_parts else None

    # Lấy các trường thông tin đầu tiên không Null
    material_code = next((lc.material_code_candidate for lc in elements if lc.material_code_candidate), None)
    brand = next((lc.brand_candidate for lc in elements if lc.brand_candidate), None)
    unit = next((lc.unit_candidate for lc in elements if lc.unit_candidate), None)
    quantity = next((lc.quantity_candidate for lc in elements if lc.quantity_candidate is not None), None)
    unit_price = next((lc.unit_price_candidate for lc in elements if lc.unit_price_candidate is not None), None)
    currency = "VND" if unit_price is not None else None

    # Thu thập tất cả warnings từ candidates con
    warnings_map = {}
    for lc in elements:
        for w in lc.warnings:
            # Loại bỏ các warnings trùng mã lỗi cấp candidate con
            warnings_map[w.code] = w.message

    # Tính toán confidence
    confidence = 0.0
    if description:
        confidence += 0.3
    if material_code:
        confidence += 0.15
    if brand:
        confidence += 0.1
    if unit_price:
        confidence += 0.25
    if unit or currency:
        confidence += 0.1

    # Kiểm tra tính liên tục của các candidates trong row
    # Nếu hiệu line_number giữa các candidates kề nhau luôn là 1 (không có gap)
    is_sequential = True
    for i in range(len(elements) - 1):
        if elements[i+1].line_number - elements[i].line_number != 1:
            is_sequential = False
            break
    if is_sequential:
        confidence += 0.1

    confidence = min(1.0, round(confidence, 2))

    if confidence < 0.5:
        warnings_map["low_confidence"] = "Row candidate has low confidence."

    warnings = [
        ParserWarningModel(code=code, message=msg)
        for code, msg in warnings_map.items()
    ]

    row_id = f"{quotation_id}_ROWCAND_{row_seq:04d}"

    return RowCandidateModel(
        row_id=row_id,
        page_number=first_lc.page_number,
        start_line_number=start_line,
        end_line_number=end_line,
        source_candidate_ids=[lc.candidate_id for lc in elements],
        description_candidate=description,
        material_code_candidate=material_code,
        brand_candidate=brand,
        unit_candidate=unit,
        quantity_candidate=quantity,
        unit_price_candidate=unit_price,
        currency_candidate=currency,
        evidence_text=evidence_text,
        start_offset=start_offset,
        end_offset=end_offset,
        confidence=confidence,
        warnings=warnings
    )


def group_candidates_to_rows(
    line_candidates: List[LineCandidateModel],
    markdown_content: str,
    quotation_id: str,
    max_line_gap_for_price: int = 6
) -> List[RowCandidateModel]:
    """
    Gom các line candidates thành các row candidates theo các nguyên tắc nghiệp vụ.
    """
    if not line_candidates:
        return []

    # 1. Phân nhóm candidates theo page_number
    pages_map = {}
    for lc in line_candidates:
        pages_map.setdefault(lc.page_number, []).append(lc)

    rows = []
    row_seq = 1

    # Duyệt từng trang
    for page_num in sorted(pages_map.keys()):
        page_candidates = sorted(pages_map[page_num], key=lambda x: x.line_number)
        
        current_row_elements = []

        for lc in page_candidates:
            if not current_row_elements:
                current_row_elements.append(lc)
                continue

            # Các phần tử hiện tại trong hàng đang ghép
            last_element = current_row_elements[-1]
            gap = lc.line_number - last_element.line_number

            # Kiểm tra xem hàng hiện tại đã có description mạnh hoặc giá chưa
            row_has_strong_desc = any(has_strong_description(item) for item in current_row_elements)
            row_has_price = any(item.unit_price_candidate is not None for item in current_row_elements)

            # A. Kiểm tra khoảng cách dòng tối đa
            if gap > max_line_gap_for_price:
                # Quá xa -> Đóng hàng cũ, tạo hàng mới
                row_obj = assemble_elements_to_row(current_row_elements, markdown_content, quotation_id, row_seq)
                rows.append(row_obj)
                row_seq += 1
                current_row_elements = [lc]
                continue

            # B. Nếu candidate mới có description mạnh
            if has_strong_description(lc):
                if row_has_strong_desc:
                    # Đã có description mạnh -> Tách hàng
                    row_obj = assemble_elements_to_row(current_row_elements, markdown_content, quotation_id, row_seq)
                    rows.append(row_obj)
                    row_seq += 1
                    current_row_elements = [lc]
                else:
                    # Gộp vào hàng hiện tại
                    current_row_elements.append(lc)
                continue

            # C. Nếu candidate mới chỉ chứa giá (price-only)
            if is_price_only(lc):
                if row_has_price:
                    # Tránh gộp 2 đơn giá riêng biệt -> Tách hàng
                    row_obj = assemble_elements_to_row(current_row_elements, markdown_content, quotation_id, row_seq)
                    rows.append(row_obj)
                    row_seq += 1
                    current_row_elements = [lc]
                else:
                    # Gộp vào hàng hiện tại (liên kết giá)
                    current_row_elements.append(lc)
                continue

            # D. Nếu candidate mới là thông số phụ trợ (chỉ chứa code/brand/unit/quantity)
            # Chỉ gộp nếu khoảng cách rất gần (gap <= 3)
            if gap <= 3:
                current_row_elements.append(lc)
            else:
                # Tách hàng
                row_obj = assemble_elements_to_row(current_row_elements, markdown_content, quotation_id, row_seq)
                rows.append(row_obj)
                row_seq += 1
                current_row_elements = [lc]

        # Lưu hàng cuối cùng của trang
        if current_row_elements:
            row_obj = assemble_elements_to_row(current_row_elements, markdown_content, quotation_id, row_seq)
            rows.append(row_obj)
            row_seq += 1

    return rows
