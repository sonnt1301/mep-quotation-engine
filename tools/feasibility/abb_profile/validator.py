import re
from typing import List, Dict, Any, Tuple
from tools.feasibility.abb_profile.models import ExtractedItem

def safe_number(value, default=0.0):
    try:
        if value is None or str(value).strip() == "" or str(value).lower() == "none":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def is_valid_material_code(code: str) -> bool:
    code = code.strip().upper()
    if not code:
        return False
    if re.match(r"^\d+$", code):
        return False
    if len(code) < 5:
        return False
    if "KA" in code or code == "VND" or code == "3P" or code == "4P":
        return False
    # Loại bỏ các tiêu đề
    if code in ["MÃSẢNPHẨM", "MÃVẬTTƯ"]:
        return False
        
    prefixes = ["1SDA", "1SAM", "1SBL", "1SFL", "OT", "OTM", "AX", "HK", "SK", "AA", "UA", "E1", "E2", "E4", "OXP", "OETL"]
    for p in prefixes:
        if code.startswith(p):
            return True
            
    if re.search(r"[A-Z]", code) and re.search(r"\d", code) and len(code) >= 6:
        return True
    return False

def validate_extracted_item(item: ExtractedItem) -> Tuple[bool, List[str], List[str]]:
    errors = []
    warnings = []
    
    code = item.material_code.strip()
    desc = item.description.strip()
    qty = item.rated_current.strip()
    price = item.unit_price
    item_type = item.type.strip()
    
    # 1. Validate material_code
    if not code:
        errors.append("material_code_empty")
    else:
        if " " in code:
            errors.append("material_code_contains_space")
        if len(code) > 15:
            errors.append("material_code_too_long_merged")
        if not is_valid_material_code(code):
            errors.append("material_code_invalid_format")
        if code in ["18KA", "630A", "2020"]:
            errors.append("material_code_cannot_be_technical_spec_or_year")
            
    # 2. Validate type
    if item_type:
        item_type_upper = item_type.upper().strip()
        # Chặn các mã sản phẩm 1S... điển hình không được rơi vào type
        if re.match(r"^1S[DABMF]\w+", item_type_upper):
            errors.append("type_cannot_be_material_code")
        if "," in item_type and re.search(r"\d{3}", item_type):
            errors.append("type_cannot_be_price")
        if re.match(r"^\d+$", item_type_upper.replace(".", "")):
            val = safe_number(item_type_upper.replace(".", ""))
            if val > 1000:
                errors.append("type_cannot_be_price_or_large_number")
                
    # 3. Validate rated_current
    if qty:
        if "," in qty and re.search(r"\d{3}", qty):
            errors.append("rated_current_cannot_be_price")
        if code and code in qty:
            errors.append("rated_current_cannot_contain_material_code")
        if "..." not in qty:
            if re.search(r"\d{6,}", qty.replace(",", "").replace(".", "")):
                errors.append("rated_current_too_large")
            
    # 4. Validate unit_price
    if price is None:
        errors.append("unit_price_empty")
    else:
        p_val = int(price)
        if p_val <= 0:
            errors.append("unit_price_zero_or_negative")
        if p_val == 2020:
            errors.append("unit_price_is_year_2020")
        # Kiểm tra nếu giá nhầm là các trị số A hoặc KA
        price_str = str(p_val)
        if price_str in ["18", "36", "50", "70", "3", "4"]:
            errors.append("unit_price_cannot_be_technical_spec")
            
    # 5. Validate description
    if desc:
        if re.search(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?A\b", desc):
            errors.append("description_contains_price_with_A")
        price_matches = re.findall(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", desc)
        for pm in price_matches:
            val = int(pm.replace(",", ""))
            if val > 50000:
                errors.append("description_contains_large_price_noise")
        if re.search(r"(1SDA|1SBL|1SAM|1SFL)\w{8,}", desc):
            errors.append("description_contains_merged_material_code")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings
