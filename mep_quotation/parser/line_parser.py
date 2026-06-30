import re
from typing import Optional, List, Tuple
from mep_quotation.spec.models import (
    LineCandidateModel,
    LineCandidateEvidenceModel,
    ParserWarningModel,
    TextAssemblyManifestModel
)

# Cấu hình danh sách thương hiệu MEP cứng nội bộ
MEP_BRANDS = [
    "CADIVI", "LS", "SCHNEIDER", "PANASONIC", "SINO",
    "DAPHACO", "TRẦN PHÚ", "TRAN PHU", "HAGER", "ABB", "SIEMENS"
]

BRAND_MAP = {
    "CADIVI": "Cadivi",
    "LS": "LS",
    "SCHNEIDER": "Schneider",
    "PANASONIC": "Panasonic",
    "SINO": "Sino",
    "DAPHACO": "Daphaco",
    "TRẦN PHÚ": "Trần Phú",
    "TRAN PHU": "Trần Phú",
    "HAGER": "Hager",
    "ABB": "ABB",
    "SIEMENS": "Siemens"
}


# Các từ khóa MEP phổ biến
MEP_KEYWORDS = [
    "cáp", "dây", "ống", "tủ", "cb", "mccb", "mcb", "rccb", "rcbo", "đèn", "công tắc", "ổ cắm"
]

# Các đơn vị tính phổ biến
COMMON_UNITS = [
    "m", "mét", "cuộn", "cái", "bộ", "pcs", "set", "kg", "box"
]


def extract_unit_price(line: str) -> Tuple[Optional[float], List[ParserWarningModel]]:
    """
    Trích xuất đơn giá thô từ dòng văn bản thô, tránh bắt nhầm các thông số kỹ thuật.

    Quy tắc:
    - Loại trừ các số đi liền với suffix kỹ thuật: mm2, mm², A, kA, P, D, DN, PN, phi, Ø, V, W, kW, Hz, v.v.
    - Ưu tiên trích xuất số đứng trước hoặc gần các marker tiền tệ/đơn giá: VND, VNĐ, đ, đồng, /m, /cái, /bộ, /set, /pcs, /kg, /cuộn.
    - Nếu không có marker: Nhận diện số là token cuối hoặc gần cuối dòng nếu giá trị >= 1000.
    """
    warnings = []
    
    # 1. Chuẩn hóa dòng để dễ phân tích
    cleaned = line.strip()
    
    # 2. Xóa các cụm số gắn liền với technical suffixes để tránh bắt nhầm
    # Ví dụ: 1.5mm2 -> xóa 1.5mm2; 100A -> xóa 100A; D25 -> xóa D25
    tech_pattern = re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:mm2|mm²|a|ka|p|pn|dn|hz|v|w|kw)\b"
        r"|(?:\b[dpd]n|\bphi|Ø|ø)\s*\d+\b",
        re.IGNORECASE
    )
    temp_line = tech_pattern.sub(" ", cleaned)

    # 3. Quét tìm số tiền đi kèm marker tiền tệ / đơn giá
    price_marker_pattern = re.compile(
        r"(\d+(?:[\.,]\d+)*)\s*(?:vnd|vnđ|đ|đồng|/m|/cái|/bộ|/set|/pcs|/kg|/cuộn)\b",
        re.IGNORECASE
    )
    marker_match = price_marker_pattern.search(temp_line)
    if marker_match:
        price_str = marker_match.group(1).replace(".", "").replace(",", "")
        try:
            return float(price_str), warnings
        except ValueError:
            pass

    # 4. Nếu không có marker, tìm token số cuối cùng hoặc gần cuối dòng
    # Tách dòng thành các token chữ số (cho phép dấu phân cách hàng nghìn)
    tokens = re.findall(r"\b\d+(?:[\.,]\d+)*\b", temp_line)
    if tokens:
        # Lấy token cuối cùng
        last_token = tokens[-1]
        
        # Kiểm tra xem token này có nằm ở nửa cuối của dòng văn bản không
        pos = temp_line.rfind(last_token)
        if pos >= len(temp_line) * 0.4:
            val_str = last_token.replace(".", "").replace(",", "")
            try:
                val = float(val_str)
                if val >= 1000:
                    return val, warnings
            except ValueError:
                pass

    return None, warnings


def extract_brand(line: str) -> Optional[str]:
    """Nhận diện thương hiệu từ config nội bộ nhỏ."""
    upper_line = line.upper()
    for brand in MEP_BRANDS:
        if re.search(r"\b" + re.escape(brand) + r"\b", upper_line):
            return BRAND_MAP[brand]
    return None


def extract_unit(line: str) -> Optional[str]:
    """Nhận diện đơn vị tính phổ biến."""
    for unit in COMMON_UNITS:
        pattern = r"\b" + re.escape(unit) + r"\b"
        if re.search(pattern, line, re.IGNORECASE):
            return unit.lower()
    return None


def extract_quantity(line: str) -> Optional[float]:
    """Trích xuất số lượng nếu có cấu trúc rõ ràng."""
    qty_patterns = [
        r"(?:số\s*lượng|soluong|qty|sl)\s*[:\-=\s]\s*(\d+(?:\.\d+)?)",
        r"\b(?:sl|qty)\b\s*(\d+(?:\.\d+)?)"
    ]
    for pat in qty_patterns:
        match = re.search(pat, line, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
    return None


def extract_material_code(line: str) -> Optional[str]:
    """Tìm mã vật tư dạng chữ + số (ví dụ: CV-1.5, DVV-2x4, MCCB-3P, M30)."""
    # Pattern phổ biến: chữ cái kèm số nối nhau, hoặc có gạch nối
    code_pattern = re.compile(
        r"\b(?:[a-z]{1,6}-\d+(?:\.\d+)?(?:[a-z]{1,2})?|\b[a-z]{2,5}\d{2,4}\b)\b",
        re.IGNORECASE
    )
    match = code_pattern.search(line)
    if match:
        return match.group(0)
    return None


def parse_markdown_line(
    raw_line: str,
    line_number: int,
    page_number: int,
    start_offset: int,
    end_offset: int,
    quotation_id: str
) -> Optional[LineCandidateModel]:
    """
    Phân tích một dòng văn bản và xác định xem có phải là line candidate hay không.

    Quy tắc nhận diện candidate:
    - Có ít nhất một dấu hiệu: có đơn giá, có đơn vị tính, có mã vật tư dạng chữ+số, hoặc chứa từ khóa MEP.
    """
    cleaned_line = raw_line.strip()
    if not cleaned_line:
        return None

    # Trích xuất các thuộc tính
    unit_price, price_warnings = extract_unit_price(raw_line)
    unit = extract_unit(raw_line)
    brand = extract_brand(raw_line)
    quantity = extract_quantity(raw_line)
    material_code = extract_material_code(raw_line)

    # Kiểm tra từ khóa MEP
    has_mep_keyword = any(
        re.search(r"\b" + re.escape(kw) + r"\b", raw_line, re.IGNORECASE)
        for kw in MEP_KEYWORDS
    )

    # Đánh giá xem có phải candidate hay không
    is_candidate = (
        unit_price is not None or
        unit is not None or
        material_code is not None or
        has_mep_keyword
    )

    if not is_candidate:
        return None

    # Tính toán độ tin cậy (Confidence)
    confidence = 0.3
    if unit_price is not None:
        confidence += 0.2
    if unit is not None:
        confidence += 0.15
    if brand is not None:
        confidence += 0.15
    if material_code is not None:
        confidence += 0.10
    if quantity is not None:
        confidence += 0.10

    confidence = min(1.0, round(confidence, 2))

    # Xây dựng danh sách warnings
    warnings = list(price_warnings)
    if confidence < 0.5:
        warnings.append(ParserWarningModel(
            code="low_confidence",
            message=f"Dòng ứng viên có độ tin cậy thấp ({confidence})"
        ))

    # Cảnh báo thiếu số lượng (chỉ khi có cấu trúc đầy đủ nhưng thiếu quantity)
    # Cấu trúc đầy đủ thô: có mô tả thô (tương ứng có mep keyword hoặc code), có đơn giá thô, có đơn vị thô nhưng thiếu quantity
    if quantity is None and unit_price is not None and unit is not None and (has_mep_keyword or material_code is not None):
        warnings.append(ParserWarningModel(
            code="quantity_missing",
            message="Thiếu thông tin số lượng thô trên dòng ứng viên"
        ))

    # Xác định mô tả vật tư thô ứng viên
    # Rule thô: cắt bỏ đơn giá và đơn vị tính ở cuối dòng nếu có để lấy mô tả
    description_candidate = cleaned_line
    if unit_price is not None:
        # Xóa cụm số tiền khỏi mô tả thô
        price_pattern = re.compile(rf"\b{re.escape(str(int(unit_price)))}\b|\b{re.escape(str(unit_price))}\b")
        description_candidate = price_pattern.sub("", description_candidate).strip()

    # Evidence
    evidence = LineCandidateEvidenceModel(
        source_path="text/quotation.md",
        start_offset=start_offset,
        end_offset=end_offset,
        text=raw_line
    )

    # candidate_id định dạng tạm thời, sẽ được gán chuỗi tuần tự bởi service sau
    return LineCandidateModel(
        candidate_id="",
        line_number=line_number,
        page_number=page_number,
        raw_line=raw_line,
        description_candidate=description_candidate or cleaned_line,
        material_code_candidate=material_code,
        brand_candidate=brand,
        unit_candidate=unit,
        quantity_candidate=quantity,
        unit_price_candidate=unit_price,
        currency_candidate="VND" if unit_price is not None else None,
        confidence=confidence,
        warnings=warnings,
        evidence=evidence
    )


def scan_markdown_lines(
    markdown_content: str,
    assembly_manifest: TextAssemblyManifestModel,
    quotation_id: str
) -> List[LineCandidateModel]:
    """
    Quét từng dòng file Markdown, ánh xạ offset sang trang và lọc candidates.
    """
    candidates = []
    
    # Chia dòng giữ nguyên ký tự newline để tính offset chính xác
    lines = markdown_content.splitlines(keepends=True)
    
    current_offset = 0
    line_number = 0

    for raw_line in lines:
        line_number += 1
        start_offset = current_offset
        end_offset = current_offset + len(raw_line)
        current_offset = end_offset

        # Bỏ qua dòng trống hoặc chỉ có whitespace
        stripped = raw_line.strip()
        if not stripped:
            continue

        # Bỏ qua headings/separators của Markdown
        if stripped == "# Quotation Text" or stripped.startswith("## Page") or stripped == "---":
            continue

        # Bỏ qua các dòng metadata đầu file Markdown
        if (
            stripped.startswith("Quotation ID:") or
            stripped.startswith("Source PDF:") or
            stripped.startswith("Page Count:") or
            stripped.startswith("Generated At:")
        ):
            continue

        # Ánh xạ page_number từ offset
        page_number = None
        for page in assembly_manifest.pages:
            if start_offset >= page.start_offset and start_offset < page.end_offset:
                page_number = page.page_number
                break

        if page_number is None:
            raise ValueError(
                f"Line offset [{start_offset}:{end_offset}] does not map to any page "
                f"defined in TextAssemblyManifestModel."
            )

        candidate = parse_markdown_line(
            raw_line=raw_line,
            line_number=line_number,
            page_number=page_number,
            start_offset=start_offset,
            end_offset=end_offset,
            quotation_id=quotation_id
        )
        if candidate:
            candidates.append(candidate)

    # Đánh ID tuần tự cho các candidates
    for idx, cand in enumerate(candidates, 1):
        cand.candidate_id = f"{quotation_id}_LINECAND_{idx:04d}"

    return candidates
