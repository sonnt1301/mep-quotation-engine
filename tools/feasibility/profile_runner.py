import json
import re
import sys
import pdfplumber
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = str(Path(__file__).parent.parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

from tools.feasibility.profile_config_loader import load_profile_config, get_layout_for_page

# --- ExtractedItem Dataclass ---
class ExtractedItem:
    def __init__(
        self,
        source_page: int,
        layout_name: str,
        product_family: str,
        type: str,
        pole: str,
        rated_current: str,
        breaking_capacity: str,
        material_code: str,
        description: str,
        unit: str,
        unit_price: int,
        currency: str,
        confidence: float,
        extraction_method: str,
        evidence_text: str,
        supplier_code: str = "",
        validation_status: str = "unchecked",
        errors: List[str] = None,
        warnings: List[str] = None
    ):
        self.source_page = source_page
        self.layout_name = layout_name
        self.product_family = product_family
        self.type = type
        self.pole = pole
        self.rated_current = rated_current
        self.breaking_capacity = breaking_capacity
        self.material_code = material_code
        self.description = description
        self.unit = unit
        self.unit_price = unit_price
        self.currency = currency
        self.confidence = confidence
        self.extraction_method = extraction_method
        self.evidence_text = evidence_text
        self.supplier_code = supplier_code
        self.validation_status = validation_status
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "supplier_code": self.supplier_code,
            "source_page": self.source_page,
            "layout_name": self.layout_name,
            "product_family": self.product_family,
            "type": self.type,
            "pole": self.pole,
            "rated_current": self.rated_current,
            "breaking_capacity": self.breaking_capacity,
            "material_code": self.material_code,
            "description": self.description,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "currency": self.currency,
            "confidence": self.confidence,
            "extraction_method": self.extraction_method,
            "evidence_text": self.evidence_text,
            "validation_status": self.validation_status,
            "errors": self.errors,
            "warnings": self.warnings
        }

# --- Helper Functions ---
def clean_price(text: str) -> int:
    text = re.sub(r"[^\d]", "", text)
    return int(text) if text else 0

def clean_code(text: str) -> str:
    return re.sub(r"[^\w\-\~]", "", text).strip().upper()

def split_dirty_merged_code(text: str) -> Tuple[str, str]:
    text_clean = text.strip()
    match = re.search(r"(1SDA\d{6}R\d+|1SBL\d{6}R\d+|1SAM\d{6}R\d+|1SFL\d{6}R\d+)", text_clean, re.IGNORECASE)
    if match:
        ma = match.group(1).upper()
        model = text_clean.replace(match.group(1), "").strip()
        model = re.sub(r"^[-\s]+|[-\s]+$", "", model)
        return ma, model
        
    ot_match = re.search(r"(OT[M]?\d+[a-zA-Z0-9\-\_]*)", text_clean, re.IGNORECASE)
    if ot_match:
        ma = ot_match.group(1).upper()
        model = text_clean.replace(ot_match.group(1), "").strip()
        model = re.sub(r"^[-\s]+|[-\s]+$", "", model)
        return ma, model
        
    return text_clean, ""

def is_valid_ls_code(code: str, prefixes: List[str], min_fallback_len: int = 5) -> bool:
    code = code.strip().upper()
    if not code:
        return False
    if re.match(r"^\d+$", code):
        return False
    if len(code) < 3:
        return False
    if code in ["6KA", "10KA", "40A", "2026", "VND", "3P", "4P", "1P", "2P"]:
        return False
    for p in prefixes:
        if code.startswith(p.upper()):
            return True
    if re.search(r"[A-Z]", code) and re.search(r"\d", code) and len(code) >= min_fallback_len:
        return True
    return False

def is_valid_price_token(t: str) -> bool:
    t_clean = t.strip().upper()
    if not t_clean:
        return False
    # Không chứa chữ A (loại trừ các thông số dòng định mức dạng 2500A, 4000A)
    if "A" in t_clean:
        return False
        
    if "," in t_clean:
        parts = t_clean.split(",")
        if parts[-1].strip() != "000":
            try:
                nums = [int(p) for p in parts if p.strip().isdigit()]
                if nums and all(n < 1000 for n in nums):
                    return False
            except ValueError:
                pass
    else:
        # Nếu không có dấu phẩy, nó phải đại diện cho số nguyên >= 1000
        # (loại bỏ các số nhỏ nhiễu thông số như 85, 100)
        try:
            val = int(re.sub(r"[^\d]", "", t_clean))
            if val < 1000:
                return False
        except ValueError:
            return False
            
    try:
        val_clean = re.sub(r"[^\d]", "", t_clean)
        if not val_clean:
            return False
        return int(val_clean) >= 1000
    except ValueError:
        return False

def split_merged_words_by_coordinates(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Bước 1: Tách các từ chứa khoảng trắng " " (logic của LS v1 gốc)
    step1_words = []
    for w in words:
        text = w["text"]
        if " " in text and len(text) > 3:
            parts = text.split(" ")
            parts = [p for p in parts if p.strip()]
            if len(parts) <= 1:
                step1_words.append(w)
                continue
                
            total_len = len(text)
            w_width = w["x1"] - w["x0"]
            char_width = w_width / total_len if total_len > 0 else 0
            
            current_x0 = w["x0"]
            for part in parts:
                part_len = len(part)
                part_width = part_len * char_width
                part_x1 = current_x0 + part_width
                
                step1_words.append({
                    "text": part,
                    "x0": current_x0,
                    "x1": part_x1,
                    "top": w["top"],
                    "bottom": w["bottom"]
                })
                current_x0 = part_x1 + char_width
        else:
            step1_words.append(w)
            
    # Bước 2: Tách các từ chứa cả chữ cái và giá tiền dính nhau (logic của ABB v1 gốc)
    result = []
    for w in step1_words:
        text = w["text"]
        if len(text) > 8 and "," in text and re.search(r"[a-zA-Z]", text) and re.search(r"\d", text):
            match = re.search(r"(\d{1,3}(?:,\d{3})+)", text)
            if match and is_valid_price_token(match.group(1)):
                price_str = match.group(1)
                start_idx = match.start()
                end_idx = match.end()
                
                left_text = text[:start_idx].strip()
                right_text = text[end_idx:].strip()
                
                width = w["x1"] - w["x0"]
                char_width = width / len(text) if len(text) > 0 else 0
                
                if left_text:
                    result.append({
                        "text": left_text,
                        "x0": w["x0"],
                        "x1": w["x0"] + char_width * len(left_text),
                        "top": w["top"],
                        "bottom": w["bottom"]
                    })
                result.append({
                    "text": price_str,
                    "x0": w["x0"] + char_width * start_idx,
                    "x1": w["x0"] + char_width * end_idx,
                    "top": w["top"],
                    "bottom": w["bottom"]
                })
                if right_text:
                    result.append({
                        "text": right_text,
                        "x0": w["x0"] + char_width * end_idx,
                        "x1": w["x1"],
                        "top": w["top"],
                        "bottom": w["bottom"]
                    })
                continue
        result.append(w)
    return result

# --- Validator ---
def validate_extracted_item(item: ExtractedItem, validation: Dict[str, Any], patterns: List[str]) -> Tuple[bool, List[str], List[str]]:
    errors = []
    warnings = []
    
    if item.unit_price <= 0:
        errors.append("unit_price_must_be_positive")
        
    if not item.material_code:
        errors.append("material_code_missing")
    else:
        prefixes = validation.get("allowed_material_code_prefixes", [])
        code_upper = item.material_code.upper()
        
        # Một số mã đặc biệt cần loại bỏ
        if code_upper in ["MÃSẢNPHẨM", "MÃVẬTTƯ", "18KA", "630A", "2020"]:
            errors.append("material_code_invalid_format")
        elif " " in code_upper:
            errors.append("material_code_invalid_format")
        else:
            matched_prefix = False
            for p in prefixes:
                if code_upper.startswith(p.upper()):
                    matched_prefix = True
                    break
            
            # Luật fallback của baseline v1: chứa cả chữ và số, chiều dài >= min_fallback_length
            min_fallback_len = validation.get("min_fallback_length", 5)
            is_fallback_valid = bool(re.search(r"[A-Z]", code_upper) and re.search(r"\d", code_upper) and len(code_upper) >= min_fallback_len)
            
            if not matched_prefix and not is_fallback_valid:
                errors.append("material_code_invalid_prefix")
                
            matched_pattern = False
            for pat in patterns:
                if re.match(pat, item.material_code, re.IGNORECASE):
                    matched_pattern = True
                    break
            if not matched_pattern and patterns and not is_fallback_valid:
                errors.append("material_code_invalid_format")
                
    if validation.get("reject_description_price_noise", True) and item.description:
        price_matches = re.findall(r"\b\d{1,3}(?:,\d{3})+\b", item.description)
        if price_matches:
            is_noise = True
            allowed_patterns = validation.get("allow_ampere_list_patterns", [])
            for pat in allowed_patterns:
                for m in re.finditer(pat, item.description):
                    for pm in price_matches:
                        if pm in m.group(0):
                            is_noise = False
            if is_noise:
                errors.append("description_contains_price_noise")
                
    is_valid = len(errors) == 0
    return is_valid, errors, warnings

# --- Layout Parser Engine ---
def parse_page_from_config(
    page, 
    page_num: int, 
    layout: Dict[str, Any], 
    global_rules: Dict[str, Any], 
    validation: Dict[str, Any],
    supplier_code: str = ""
) -> Tuple[List[ExtractedItem], str, str, int, int]:
    
    layout_name = layout["layout_name"]
    pf = layout.get("product_family", "Thiết bị")
    cols_config = layout["columns"]
    row_det = layout.get("row_detection", {})
    
    min_y = row_det.get("min_y", 70.0)
    max_y = row_det.get("max_y", 820.0)
    row_tol = row_det.get("row_tolerance", 3.0)
    
    words = page.extract_words()
    words = split_merged_words_by_coordinates(words)
    
    rows = defaultdict(list)
    for w in words:
        found = False
        for existing_top in rows:
            if abs(existing_top - w["top"]) < row_tol:
                rows[existing_top].append(w)
                found = True
                break
        if not found:
            rows[w["top"]].append(w)
            
    sorted_tops = sorted(rows.keys())
    
    extracted_items = []
    raw_detected = 0
    skipped = 0
    
    # State tracking variables for single-column page scanning (like ABB MCCB)
    khi_nang_cat_current = ""
    loai_current = ""
    poles_current = "3"
    
    # LS Page state
    pf_left = pf
    pf_right = pf
    pole_left = "3P"
    pole_right = "3P"
    
    for top in sorted_tops:
        if not (min_y <= top <= max_y):
            continue
            
        line_words = sorted(rows[top], key=lambda x: x["x0"])
        evidence_text = " ".join([w["text"] for w in line_words])
        desc_line = evidence_text.lower()
        
        # Lọc bỏ tiêu đề trang rác
        if "bảng dự toán" in desc_line or "ghi chú:" in desc_line or "sản phẩm khả năng" in desc_line:
            continue
            
        # --- 1. double_column_3p_4p (ABB) ---
        if layout_name == "double_column_3p_4p":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                is_price = "," in t and re.search(r"\d{3}", t)
                
                # Nạp dải cột từ JSON config
                x_knc_min, x_knc_max = cols_config["khi_nang_cat"]
                x_l_min, x_l_max = cols_config["loai"]
                x_in_min, x_in_max = cols_config["in_a"]
                x_m3_min, x_m3_max = cols_config["ma_3p"]
                x_g3_min, x_g3_max = cols_config["gia_3p"]
                x_m4_min, x_m4_max = cols_config["ma_4p"]
                x_g4_min, x_g4_max = cols_config["gia_4p"]
                
                if x_knc_min <= x0 <= x_knc_max:
                    cols["khi_nang_cat"].append(t)
                elif x_l_min <= x0 <= x_l_max:
                    cols["loai"].append(t)
                elif x_in_min <= x0 <= x_in_max:
                    cols["in_a"].append(t)
                elif x_m3_min <= x0 <= x_m3_max:
                    if is_price: cols["gia_3p"].append(t)
                    else: cols["ma_3p"].append(t)
                elif x_g3_min <= x0 <= x_g3_max:
                    cols["gia_3p"].append(t)
                elif x_m4_min <= x0 <= x_m4_max:
                    if is_price: cols["gia_4p"].append(t)
                    else: cols["ma_4p"].append(t)
                elif x_g4_min <= x0 <= x_g4_max:
                    cols["gia_4p"].append(t)
                    
            khi_nang_cat = "".join(cols["khi_nang_cat"]).strip()
            loai = "".join(cols["loai"]).strip()
            in_a = "".join(cols["in_a"]).strip()
            ma_3p = "".join(cols["ma_3p"]).strip()
            gia_3p = "".join(cols["gia_3p"]).strip()
            ma_4p = "".join(cols["ma_4p"]).strip()
            gia_4p = "".join(cols["gia_4p"]).strip()
            
            if khi_nang_cat: khi_nang_cat_current = khi_nang_cat
            if loai: loai_current = loai
            
            if in_a:
                # 3P
                raw_detected += 1
                c_ma_3p = clean_code(ma_3p)
                # Apply special rule: clean ACB prefix MP/FP
                if "clean_acb_mp_fp_prefixes" in layout.get("special_rules", []):
                    if c_ma_3p.startswith("MP1SDA") or c_ma_3p.startswith("FP1SDA"):
                        c_ma_3p = c_ma_3p[2:]
                c_gia_3p = clean_price(gia_3p)
                if c_gia_3p > 0 and c_ma_3p != "":
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=loai_current,
                        pole="3P",
                        rated_current=in_a,
                        breaking_capacity=khi_nang_cat_current,
                        material_code=c_ma_3p,
                        description=f"{pf} {loai_current} 3P {in_a}A {khi_nang_cat_current}".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia_3p,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
                # 4P
                raw_detected += 1
                c_ma_4p = clean_code(ma_4p)
                if "clean_acb_mp_fp_prefixes" in layout.get("special_rules", []):
                    if c_ma_4p.startswith("MP1SDA") or c_ma_4p.startswith("FP1SDA"):
                        c_ma_4p = c_ma_4p[2:]
                c_gia_4p = clean_price(gia_4p)
                if c_gia_4p > 0 and c_ma_4p != "":
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=loai_current,
                        pole="4P",
                        rated_current=in_a,
                        breaking_capacity=khi_nang_cat_current,
                        material_code=c_ma_4p,
                        description=f"{pf} {loai_current} 4P {in_a}A {khi_nang_cat_current}".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia_4p,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
        # --- 2. three_cutoff_groups_page21 (ABB) ---
        elif layout_name == "three_cutoff_groups_page21":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                is_price = "," in t and re.search(r"\d{3}", t)
                
                x_l_min, x_l_max = cols_config["loai"]
                x_in_min, x_in_max = cols_config["in_a"]
                x_p_min, x_p_max = cols_config["poles"]
                x_m36_min, x_m36_max = cols_config["ma_36"]
                x_g36_min, x_g36_max = cols_config["gia_36"]
                x_m50_min, x_m50_max = cols_config["ma_50"]
                x_g50_min, x_g50_max = cols_config["gia_50"]
                x_m70_min, x_m70_max = cols_config["ma_70"]
                x_g70_min, x_g70_max = cols_config["gia_70"]
                
                if x_l_min <= x0 <= x_l_max:
                    cols["loai"].append(t)
                elif x_in_min <= x0 <= x_in_max:
                    cols["in_a"].append(t)
                elif x_p_min <= x0 <= x_p_max:
                    cols["poles"].append(t)
                elif x_m36_min <= x0 <= x_m36_max:
                    if is_price: cols["gia_36"].append(t)
                    else: cols["ma_36"].append(t)
                elif x_g36_min <= x0 <= x_g36_max:
                    cols["gia_36"].append(t)
                elif x_m50_min <= x0 <= x_m50_max:
                    if is_price: cols["gia_50"].append(t)
                    else: cols["ma_50"].append(t)
                elif x_g50_min <= x0 <= x_g50_max:
                    cols["gia_50"].append(t)
                elif x_m70_min <= x0 <= x_m70_max:
                    if is_price: cols["gia_70"].append(t)
                    else: cols["ma_70"].append(t)
                elif x_g70_min <= x0 <= x_g70_max:
                    cols["gia_70"].append(t)
                    
            loai = "".join(cols["loai"]).strip()
            in_a = "".join(cols["in_a"]).strip()
            poles = "".join(cols["poles"]).strip()
            
            if loai: loai_current = loai
            if poles: poles_current = poles
            
            if in_a:
                # 36KA
                raw_detected += 1
                ma_36 = "".join(cols["ma_36"])
                gia_36 = "".join(cols["gia_36"])
                c_ma_36, model_36 = split_dirty_merged_code(ma_36)
                c_gia_36 = clean_price(gia_36)
                c_ma_36_clean = clean_code(c_ma_36)
                if c_ma_36_clean and c_gia_36 > 0:
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=loai_current or model_36,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="36KA",
                        material_code=c_ma_36_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 36KA".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia_36,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.94,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
                # 50KA
                raw_detected += 1
                ma_50 = "".join(cols["ma_50"])
                gia_50 = "".join(cols["gia_50"])
                c_ma_50, model_50 = split_dirty_merged_code(ma_50)
                c_gia_50 = clean_price(gia_50)
                c_ma_50_clean = clean_code(c_ma_50)
                if c_ma_50_clean and c_gia_50 > 0:
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=loai_current or model_50,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="50KA",
                        material_code=c_ma_50_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 50KA".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia_50,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.94,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
                # 70KA
                raw_detected += 1
                ma_70 = "".join(cols["ma_70"])
                gia_70 = "".join(cols["gia_70"])
                c_ma_70, model_70 = split_dirty_merged_code(ma_70)
                c_gia_70 = clean_price(gia_70)
                c_ma_70_clean = clean_code(c_ma_70)
                if c_ma_70_clean and c_gia_70 > 0:
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=loai_current or model_70,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="70KA",
                        material_code=c_ma_70_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 70KA".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia_70,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.94,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
        # --- 3. split_half_left_right (ABB / LS) ---
        elif layout_name == "split_half_left_right":
            # Phân biệt LS (nested dict columns) hay ABB (cột trực tiếp)
            is_ls_style = isinstance(cols_config.get("left"), dict)
            
            if is_ls_style:
                # LS Style: Split half và bóc theo dải cột con
                left_words = [w for w in line_words if w["x0"] < 290.0]
                right_words = [w for w in line_words if w["x0"] >= 290.0]
                
                # Phát hiện Title thay đổi Product Family hoặc Poles
                line_text_upper = evidence_text.upper()
                if "PHỤ KIỆN" in line_text_upper or "ACCESSORIES" in line_text_upper:
                    pf_left = "Phụ kiện LS"
                    pf_right = "Phụ kiện LS"
                elif "BẢNG GIÁ" in line_text_upper or "CHỈ SỐ" in line_text_upper:
                    pass
                else:
                    # Detect Product Family
                    if "MÀNG" in line_text_upper or "KHỞI ĐỘNG TỪ" in line_text_upper or "CONTACTOR" in line_text_upper:
                        pf_left = "Contactor LS"
                        pf_right = "Contactor LS"
                    elif "CẦU DAO TỰ ĐỘNG" in line_text_upper or "MCCB" in line_text_upper:
                        pf_left = "MCCB LS"
                        pf_right = "MCCB LS"
                        
                    # Detect Poles
                    if "1P" in line_text_upper:
                        pole_left = "1P"
                        pole_right = "1P"
                    elif "2P" in line_text_upper:
                        pole_left = "2P"
                        pole_right = "2P"
                    elif "3P" in line_text_upper:
                        pole_left = "3P"
                        pole_right = "3P"
                    elif "4P" in line_text_upper:
                        pole_left = "4P"
                        pole_right = "4P"
                        
                def process_ls_half(half_words: List[Dict[str, Any]], pf_curr: str, pole_curr: str, is_left: bool) -> Tuple[Optional[ExtractedItem], bool, bool]:
                    if not half_words:
                        return None, False, False
                        
                    cols = defaultdict(list)
                    side = "left" if is_left else "right"
                    
                    x_ma_min, x_ma_max = cols_config[side]["ma"]
                    x_in_min, x_in_max = cols_config[side]["in_a"]
                    x_icu_min, x_icu_max = cols_config[side]["icu"]
                    x_gia_min, x_gia_max = cols_config[side]["gia"]
                    
                    for w in half_words:
                        x0 = w["x0"]
                        t = w["text"].strip()
                        if not t: continue
                        is_price = "," in t and re.search(r"\d{3}", t) and not re.search(r"[a-zA-Z]", t)
                        if is_price and not is_valid_price_token(t):
                            is_price = False
                        
                        if x_ma_min <= x0 <= x_ma_max:
                            if is_price: cols["gia"].append(t)
                            else: cols["ma"].append(t)
                        elif x_in_min <= x0 <= x_in_max:
                            if is_price: cols["gia"].append(t)
                            else: cols["in_a"].append(t)
                        elif x_icu_min <= x0 <= x_icu_max:
                            if is_price: cols["gia"].append(t)
                            else: cols["icu"].append(t)
                        elif x_gia_min <= x0 <= x_gia_max:
                            cols["gia"].append(t)
                            
                    ma_str = " ".join(cols["ma"]).strip()
                    in_a_str = " ".join(cols["in_a"]).strip()
                    icu_str = " ".join(cols["icu"]).strip()
                    
                    # Lọc các price token hợp lệ trong cols["gia"] và lấy token cuối cùng hợp lệ
                    valid_prices = [p for p in cols["gia"] if is_valid_price_token(p)]
                    if valid_prices:
                        gia_str = valid_prices[-1].strip()
                    else:
                        gia_str = ""
                    
                    is_detected = bool(ma_str or in_a_str or gia_str)
                    if not is_detected:
                        return None, False, False
                        
                    c_gia = clean_price(gia_str)
                    if not ma_str or c_gia == 0:
                        return None, True, True
                        
                    tokens = ma_str.split(" ")
                    material_code = ""
                    prefixes_list = validation.get("allowed_material_code_prefixes", [])
                    min_fallback_len = validation.get("min_fallback_length", 5)
                    for tok in tokens:
                        tok_clean = re.sub(r"[^\w\-\~]", "", tok).upper()
                        if is_valid_ls_code(tok_clean, prefixes_list, min_fallback_len):
                            material_code = tok_clean
                            break
                    if not material_code and tokens:
                        material_code = re.sub(r"[^\w\-\~]", "", tokens[0]).upper()
                        
                    model = ma_str.replace(material_code, "").strip()
                    
                    desc = f"{pf_curr} {ma_str}".strip()
                    if in_a_str: desc += f" In={in_a_str}"
                    if icu_str: desc += f" Icu={icu_str}"
                    
                    final_pole = pole_curr
                    pole_match = re.search(r"\b(\d)P\b", ma_str.upper())
                    if pole_match:
                        final_pole = pole_match.group(1) + "P"
                    elif "1P" in ma_str.upper(): final_pole = "1P"
                    elif "2P" in ma_str.upper(): final_pole = "2P"
                    elif "3P" in ma_str.upper(): final_pole = "3P"
                    elif "4P" in ma_str.upper(): final_pole = "4P"
                    
                    rated_current = in_a_str
                    if not rated_current:
                        in_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:A|A~|~))\b", desc)
                        if in_match:
                            rated_current = in_match.group(1)
                            
                    item = ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf_curr,
                        type=model or pf_curr,
                        pole=final_pole,
                        rated_current=rated_current,
                        breaking_capacity=icu_str,
                        material_code=material_code,
                        description=desc,
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.92,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=" ".join([w["text"] for w in half_words])
                    )
                    return item, True, False

                res_l, det_l, skip_l = process_ls_half(left_words, pf_left, pole_left, is_left=True)
                res_r, det_r, skip_r = process_ls_half(right_words, pf_right, pole_right, is_left=False)
                
                if det_l: raw_detected += 1
                if skip_l: skipped += 1
                if res_l: extracted_items.append(res_l)
                
                if det_r: raw_detected += 1
                if skip_r: skipped += 1
                if res_r: extracted_items.append(res_r)
                
            else:
                # ABB Style: Split half bằng cột trực tiếp
                left_words_list = []
                right_words_list = []
                cols = defaultdict(list)
                
                for w in line_words:
                    x0 = w["x0"]
                    t = w["text"].strip()
                    if not t: continue
                    is_price = "," in t and re.search(r"\d{3}", t)
                    
                    x_in_min, x_in_max = cols_config["in_a"]
                    x_knc_min, x_knc_max = cols_config["khi_nang_cat"]
                    x_l_min, x_l_max = cols_config["loai"]
                    x_m3_min, x_m3_max = cols_config["ma_3p"]
                    x_g3_min, x_g3_max = cols_config["gia_3p"]
                    x_vt_min, x_vt_max = cols_config["vi_tri"]
                    x_td_min, x_td_max = cols_config["tiep_diem"]
                    x_lr_min, x_lr_max = cols_config["loai_r"]
                    x_mr_min, x_mr_max = cols_config["ma_r"]
                    x_gr_min, x_gr_max = cols_config["gia_r"]
                    
                    if x_in_min <= x0 <= x_in_max:
                        cols["in_a"].append(t)
                    elif x_knc_min <= x0 <= x_knc_max:
                        cols["khi_nang_cat"].append(t)
                    elif x_l_min <= x0 <= x_l_max:
                        cols["loai"].append(t)
                    elif x_m3_min <= x0 <= x_m3_max:
                        if is_price: cols["gia_3p"].append(t)
                        else: cols["ma_3p"].append(t)
                    elif x_g3_min <= x0 <= x_g3_max:
                        cols["gia_3p"].append(t)
                    elif x_vt_min <= x0 <= x_vt_max:
                        cols["vi_tri"].append(t)
                    elif x_td_min <= x0 <= x_td_max:
                        cols["tiep_diem"].append(t)
                    elif x_lr_min <= x0 <= x_lr_max:
                        cols["loai_r"].append(t)
                    elif x_mr_min <= x0 <= x_mr_max:
                        if is_price: cols["gia_r"].append(t)
                        else: cols["ma_r"].append(t)
                    elif x_gr_min <= x0 <= x_gr_max:
                        cols["gia_r"].append(t)
                        
                in_a = "".join(cols["in_a"]).strip()
                khi_nang_cat = "".join(cols["khi_nang_cat"]).strip()
                loai = "".join(cols["loai"]).strip()
                ma_3p = "".join(cols["ma_3p"]).strip()
                gia_3p = "".join(cols["gia_3p"]).strip()
                
                ma_3p_clean, model_left = split_dirty_merged_code(ma_3p)
                
                # Nửa phải phụ kiện
                vi_tri = "".join(cols["vi_tri"]).strip()
                tiep_diem = "".join(cols["tiep_diem"]).strip()
                loai_r = "".join(cols["loai_r"]).strip()
                ma_r = "".join(cols["ma_r"]).strip()
                ma_r_clean, model_right = split_dirty_merged_code(ma_r)
                
                right_prices = [w["text"] for w in line_words if x_gr_min <= w["x0"] <= x_gr_max or (x_mr_min <= w["x0"] <= x_mr_max and "," in w["text"])]
                gia_r = "".join(right_prices).strip()
                
                if in_a:
                    raw_detected += 1
                    c_ma_3p = clean_code(ma_3p_clean)
                    c_gia_3p = clean_price(gia_3p)
                    if c_gia_3p > 0 and c_ma_3p != "":
                        extracted_items.append(ExtractedItem(
                            source_page=page_num, supplier_code=supplier_code,
                            layout_name=layout_name,
                            product_family=pf,
                            type=loai or model_left,
                            pole="3P",
                            rated_current=in_a,
                            breaking_capacity=khi_nang_cat,
                            material_code=c_ma_3p,
                            description=f"{pf} {loai} {in_a}A {khi_nang_cat}".strip(),
                            unit=global_rules.get("default_unit", "cái"),
                            unit_price=c_gia_3p,
                            currency=global_rules.get("currency", "VND"),
                            confidence=0.90,
                            extraction_method="coordinate_column_profiler",
                            evidence_text=evidence_text
                        ))
                    else:
                        skipped += 1
                if loai_r or model_right:
                    raw_detected += 1
                    c_ma_r = clean_code(ma_r_clean)
                    c_gia_r = clean_price(gia_r)
                    if c_gia_r > 0 and c_ma_r != "":
                        final_model_right = loai_r or model_right
                        extracted_items.append(ExtractedItem(
                            source_page=page_num, supplier_code=supplier_code,
                            layout_name=layout_name,
                            product_family=f"Phụ kiện {pf}",
                            type=final_model_right,
                            pole="",
                            rated_current="",
                            breaking_capacity="",
                            material_code=c_ma_r,
                            description=f"Phụ kiện {pf} {final_model_right} {tiep_diem} {vi_tri}".strip(),
                            unit=global_rules.get("default_unit", "cái"),
                            unit_price=c_gia_r,
                            currency=global_rules.get("currency", "VND"),
                            confidence=0.90,
                            extraction_method="coordinate_column_profiler",
                            evidence_text=evidence_text
                        ))
                    else:
                        skipped += 1
                        
        # --- 4. single_column_right (ABB) ---
        elif layout_name == "single_column_right":
            cols = defaultdict(list)
            left_words = []
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                is_price = "," in t and re.search(r"\d{3}", t)
                
                x_dl_min, x_dl_max = cols_config["desc_left"]
                x_ma_min, x_ma_max = cols_config["ma"]
                x_g_min, x_g_max = cols_config["gia"]
                
                if x_dl_min <= x0 < x_dl_max:
                    if not is_price: left_words.append(t)
                elif x_ma_min <= x0 <= x_ma_max:
                    if is_price: cols["gia"].append(t)
                    else: cols["ma"].append(t)
                elif x_g_min <= x0 <= x_g_max:
                    cols["gia"].append(t)
                    
            ma_str = "".join(cols["ma"]).strip()
            gia = "".join(cols["gia"]).strip()
            
            clean_ma, model = split_dirty_merged_code(ma_str)
            c_gia = clean_price(gia)
            
            if clean_ma or c_gia > 0:
                raw_detected += 1
                if clean_ma and c_gia > 0:
                    desc_left = " ".join(left_words).strip()
                    rated_current = ""
                    pole = "3P"
                    if "4p" in desc_left.lower(): pole = "4P"
                    in_match = re.search(r"\b(\d+(?:\.\d+)?)\s*a\b", desc_left.lower())
                    if in_match: rated_current = in_match.group(1)
                    
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=model or pf,
                        pole=pole,
                        rated_current=rated_current,
                        breaking_capacity="",
                        material_code=clean_ma,
                        description=f"{pf} {desc_left} {model}".strip(),
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.92,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
        # --- 5. four_columns_ot_page41 (ABB) ---
        elif layout_name == "four_columns_ot_page41":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                is_price = "," in t and re.search(r"\d{3}", t)
                
                x_ith_min, x_ith_max = cols_config["ith"]
                x_in_min, x_in_max = cols_config["in_a"]
                x_ma_min, x_ma_max = cols_config["ma"]
                x_g_min, x_g_max = cols_config["gia"]
                
                if x_ith_min <= x0 <= x_ith_max:
                    cols["ith"].append(t)
                elif x_in_min <= x0 <= x_in_max:
                    cols["in_a"].append(t)
                elif x_ma_min <= x0 <= x_ma_max:
                    if is_price: cols["gia"].append(t)
                    else: cols["ma"].append(t)
                elif x_g_min <= x0 <= x_g_max:
                    cols["gia"].append(t)
                    
            ma_str = "".join(cols["ma"]).strip()
            gia = "".join(cols["gia"]).strip()
            in_a = "".join(cols["in_a"]).strip()
            ith = "".join(cols["ith"]).strip()
            
            clean_ma, model = split_dirty_merged_code(ma_str)
            c_gia = clean_price(gia)
            
            if clean_ma or c_gia > 0:
                raw_detected += 1
                if clean_ma and c_gia > 0:
                    pole = "3P"
                    if "F4" in clean_ma or "04P" in clean_ma: pole = "4P"
                    desc = f"{pf} {clean_ma} Ith={ith} In={in_a}".strip()
                    
                    extracted_items.append(ExtractedItem(
                        source_page=page_num, supplier_code=supplier_code,
                        layout_name=layout_name,
                        product_family=pf,
                        type=clean_ma,
                        pole=pole,
                        rated_current=in_a or ith,
                        breaking_capacity="",
                        material_code=clean_ma,
                        description=desc,
                        unit=global_rules.get("default_unit", "cái"),
                        unit_price=c_gia,
                        currency=global_rules.get("currency", "VND"),
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                    
    return extracted_items, pf, layout_name, raw_detected, skipped
