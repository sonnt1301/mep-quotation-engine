import os
import sys
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict
import pdfplumber
import pandas as pd
from typing import List, Dict, Any, Tuple

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
        
    prefixes = ["1SDA", "1SAM", "1SBL", "1SFL", "OT", "OTM", "AX", "HK", "SK", "AA", "UA", "E1", "E2", "E4"]
    for p in prefixes:
        if code.startswith(p):
            return True
            
    if re.search(r"[A-Z]", code) and re.search(r"\d", code) and len(code) >= 6:
        return True
    return False

def split_dirty_merged_code(merged: str) -> Tuple[str, str]:
    """
    Tách model/type và mã sản phẩm ABB ra riêng nếu bị dính nhau.
    Ví dụ: 'AX50-30-00-801SBL351074R8000' -> ('1SBL351074R8000', 'AX50-30-00-80')
    """
    merged = merged.strip()
    match = re.search(r"(1SDA\d{6}R\d+|1SBL\d{6}R\d+|1SAM\d{6}R\d+|1SFL\d{6}R\d+)", merged, re.IGNORECASE)
    if match:
        code = match.group(1).upper()
        model = merged.replace(match.group(1), "").strip()
        model = re.sub(r"^[-\s]+|[-\s]+$", "", model)
        return code, model
    return merged, ""

def split_merged_words_by_coordinates(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Tách các word bị dính khoảng trắng do bộ đọc PDF không phân tách tốt.
    """
    new_words = []
    for w in words:
        text = w["text"]
        if " " in text and len(text) > 3:
            parts = text.split(" ")
            parts = [p for p in parts if p.strip()]
            if len(parts) <= 1:
                new_words.append(w)
                continue
                
            total_len = len(text)
            w_width = w["x1"] - w["x0"]
            char_width = w_width / total_len if total_len > 0 else 0
            
            current_x0 = w["x0"]
            for part in parts:
                part_len = len(part)
                part_width = part_len * char_width
                part_x1 = current_x0 + part_width
                
                new_words.append({
                    "text": part,
                    "x0": current_x0,
                    "x1": part_x1,
                    "top": w["top"],
                    "bottom": w["bottom"]
                })
                current_x0 = part_x1 + char_width
        else:
            new_words.append(w)
    return new_words

def validate_extracted_item(item: Dict[str, Any], layout_type: str) -> Tuple[bool, List[str], List[str]]:
    errors = []
    warnings = []
    
    code = item.get("material_code", "").strip()
    desc = item.get("description", "").strip()
    qty = item.get("rated_current", "").strip()
    price = item.get("unit_price")
    item_type = item.get("type", "").strip()
    
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
            
    # 2. Validate type (Chỉ chặn mã sản phẩm 1S... thực tế)
    if item_type:
        item_type_upper = item_type.upper().strip()
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
        # Không chặn dải dòng định mức của rơ le chứa dấu "..." (ví dụ: 0.10...0.16)
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
            
    # 5. Validate description
    if desc:
        if re.search(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?A\b", desc):
            errors.append("description_contains_price_with_A")
        price_matches = re.findall(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b", desc)
        for pm in price_matches:
            val = int(pm.replace(",", ""))
            if val > 50000: # Lọc giá tiền lớn trong description
                errors.append("description_contains_large_price_noise")
        if re.search(r"(1SDA|1SBL|1SAM|1SFL)\w{8,}", desc):
            errors.append("description_contains_merged_material_code")

    is_valid = len(errors) == 0
    return is_valid, errors, warnings

def get_product_family(rows_dict) -> str:
    sorted_tops = sorted(rows_dict.keys())
    for top in sorted_tops:
        if 50.0 <= top <= 160.0:
            words = sorted(rows_dict[top], key=lambda x: x["x0"])
            line_str = " ".join([w["text"] for w in words])
            line_str = re.sub(r"\b\d+\b", "", line_str)
            line_str = line_str.replace("BAN CÔNG NGHỆ ĐIỆN", "").replace("2020", "").replace("BẢNG DỰ TOÁN", "").strip()
            line_str = re.sub(r"^[-\s]+|[-\s]+$", "", line_str)
            if line_str and len(line_str) > 3:
                return line_str
    return "Thiết bị đóng cắt ABB"

def parse_single_page(page, page_num) -> Tuple[List[Dict[str, Any]], str, str]:
    words = page.extract_words()
    
    # Tiền xử lý chia tách các từ bị dính khoảng trắng
    words = split_merged_words_by_coordinates(words)
    
    text_lower = (page.extract_text() or "").lower()
    
    rows = defaultdict(list)
    for w in words:
        found = False
        for existing_top in rows:
            if abs(existing_top - w["top"]) < 3.0:
                rows[existing_top].append(w)
                found = True
                break
        if not found:
            rows[w["top"]].append(w)
            
    sorted_tops = sorted(rows.keys())
    pf = get_product_family(rows)
    
    layout_type = "single_column_right"
    if page_num == 21:
        layout_type = "three_cutoff_groups_page21"
    elif "mccb" in text_lower or "acb" in text_lower or "mccb 3p" in text_lower or "acb 3p" in text_lower or "xt1" in text_lower or "emax" in text_lower:
        layout_type = "double_column_3p_4p"
    elif "cầu dao tự động khởi động động cơ" in text_lower or "ms116" in text_lower or "tiếp điểm phụ" in text_lower or "ms132" in text_lower:
        layout_type = "split_half_left_right"
        
    page_items = []
    
    khi_nang_cat_current = ""
    loai_current = ""
    poles_current = "3"
    
    for top in sorted_tops:
        if not (240.0 <= top <= 820.0):
            continue
            
        line_words = sorted(rows[top], key=lambda x: x["x0"])
        evidence_text = " ".join([w["text"] for w in line_words])
        
        desc_line = evidence_text.lower()
        if "bảng dự toán" in desc_line or "ghi chú:" in desc_line or "sản phẩm khả năng" in desc_line:
            continue
            
        def clean_code(code: str) -> str:
            return re.sub(r"\s+", "", code).upper()
            
        def clean_price(price_str: str) -> int:
            clean_str = re.sub(r"[^\d]", "", price_str)
            return int(clean_str) if clean_str else 0

        # --- A. LAYOUT DOUBLE COLUMN 3P/4P ---
        if layout_type == "double_column_3p_4p":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                
                # Check Heuristics giá tiền
                is_price = "," in t and re.search(r"\d{3}", t)
                
                if 150.0 <= x0 <= 200.0:
                    cols["khi_nang_cat"].append(t)
                elif 210.0 <= x0 <= 250.0:
                    cols["loai"].append(t)
                elif 255.0 <= x0 <= 290.0:
                    cols["in_a"].append(t)
                elif 300.0 <= x0 <= 380.0:
                    if is_price:
                        cols["gia_3p"].append(t)
                    else:
                        cols["ma_3p"].append(t)
                elif 381.0 <= x0 <= 435.0:
                    cols["gia_3p"].append(t)
                elif 440.0 <= x0 <= 505.0:
                    if is_price:
                        cols["gia_4p"].append(t)
                    else:
                        cols["ma_4p"].append(t)
                elif 506.0 <= x0 <= 570.0:
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
                c_ma_3p = clean_code(ma_3p)
                c_gia_3p = clean_price(gia_3p)
                page_items.append({
                    "source_page": page_num,
                    "product_family": pf,
                    "type": loai_current,
                    "pole": "3P",
                    "rated_current": in_a,
                    "material_code": c_ma_3p,
                    "description": f"{pf} {loai_current} 3P {in_a}A {khi_nang_cat_current}".strip(),
                    "unit": "cái",
                    "unit_price": c_gia_3p,
                    "currency": "VND",
                    "extraction_method": "coordinate_column_profiler",
                    "confidence": 0.95,
                    "evidence_text": evidence_text
                })
                # 4P
                c_ma_4p = clean_code(ma_4p)
                c_gia_4p = clean_price(gia_4p)
                page_items.append({
                    "source_page": page_num,
                    "product_family": pf,
                    "type": loai_current,
                    "pole": "4P",
                    "rated_current": in_a,
                    "material_code": c_ma_4p,
                    "description": f"{pf} {loai_current} 4P {in_a}A {khi_nang_cat_current}".strip(),
                    "unit": "cái",
                    "unit_price": c_gia_4p,
                    "currency": "VND",
                    "extraction_method": "coordinate_column_profiler",
                    "confidence": 0.95,
                    "evidence_text": evidence_text
                })

        # --- B. LAYOUT SPLIT HALF LEFT/RIGHT ---
        elif layout_type == "split_half_left_right":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                
                is_price = "," in t and re.search(r"\d{3}", t)
                
                # Nửa trái
                if 40.0 <= x0 <= 120.0:
                    cols["in_a"].append(t)
                elif 121.0 <= x0 <= 150.0:
                    cols["khi_nang_cat"].append(t)
                elif 151.0 <= x0 <= 200.0:
                    cols["loai"].append(t)
                elif 201.0 <= x0 <= 270.0:
                    if is_price:
                        cols["gia_3p"].append(t)
                    else:
                        cols["ma_3p"].append(t)
                elif 271.0 <= x0 <= 311.0:
                    cols["gia_3p"].append(t)
                # Nửa phải (Giới hạn x0 >= 312 nghiêm ngặt)
                elif 312.0 <= x0 <= 335.0:
                    if not is_price:
                        cols["vi_tri"].append(t)
                elif 336.0 <= x0 <= 385.0:
                    cols["tiep_diem"].append(t)
                elif 386.0 <= x0 <= 425.0:
                    cols["loai_r"].append(t)
                elif 426.0 <= x0 <= 500.0:
                    if is_price:
                        cols["gia_r"].append(t)
                    else:
                        cols["ma_r"].append(t)
                elif 501.0 <= x0 <= 570.0:
                    cols["gia_r"].append(t)
                    
            in_a = "".join(cols["in_a"]).strip()
            khi_nang_cat = "".join(cols["khi_nang_cat"]).strip()
            loai = "".join(cols["loai"]).strip()
            ma_3p = "".join(cols["ma_3p"]).strip()
            # Tách riêng model và code cho MS116
            ma_3p_clean, model_left = split_dirty_merged_code(ma_3p)
            
            # Tìm giá trị đơn giá thực tế
            left_prices = [w["text"] for w in line_words if 271.0 <= w["x0"] <= 311.0 or (201.0 <= w["x0"] <= 270.0 and "," in w["text"])]
            gia_3p = "".join(left_prices).strip()
            
            vi_tri = " ".join(cols["vi_tri"]).strip()
            tiep_diem = " ".join(cols["tiep_diem"]).strip()
            loai_r = "".join(cols["loai_r"]).strip()
            ma_r = "".join(cols["ma_r"]).strip()
            # Tách riêng model và code cho phụ kiện
            ma_r_clean, model_right = split_dirty_merged_code(ma_r)
            
            right_prices = [w["text"] for w in line_words if 501.0 <= w["x0"] <= 570.0 or (426.0 <= w["x0"] <= 500.0 and "," in w["text"])]
            gia_r = "".join(right_prices).strip()
            
            if in_a:
                c_ma_3p = clean_code(ma_3p_clean)
                c_gia_3p = clean_price(gia_3p)
                page_items.append({
                    "source_page": page_num,
                    "product_family": pf,
                    "type": loai or model_left,
                    "pole": "3P",
                    "rated_current": in_a,
                    "material_code": c_ma_3p,
                    "description": f"{pf} {loai} {in_a}A {khi_nang_cat}".strip(),
                    "unit": "cái",
                    "unit_price": c_gia_3p,
                    "currency": "VND",
                    "extraction_method": "coordinate_column_profiler",
                    "confidence": 0.90,
                    "evidence_text": evidence_text
                })
            if loai_r or model_right:
                c_ma_r = clean_code(ma_r_clean)
                c_gia_r = clean_price(gia_r)
                final_model_right = loai_r or model_right
                page_items.append({
                    "source_page": page_num,
                    "product_family": f"Phụ kiện {pf}",
                    "type": final_model_right,
                    "pole": "",
                    "rated_current": "",
                    "material_code": c_ma_r,
                    "description": f"Phụ kiện {pf} {final_model_right} {tiep_diem} {vi_tri}".strip(),
                    "unit": "cái",
                    "unit_price": c_gia_r,
                    "currency": "VND",
                    "extraction_method": "coordinate_column_profiler",
                    "confidence": 0.90,
                    "evidence_text": evidence_text
                })

        # --- D. LAYOUT THREE CUTOFF GROUPS PAGE 21 ---
        elif layout_type == "three_cutoff_groups_page21":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                
                is_price = "," in t and re.search(r"\d{3}", t)
                
                if 140.0 <= x0 <= 160.0:
                    cols["loai"].append(t)
                elif 165.0 <= x0 <= 195.0:
                    cols["in_a"].append(t)
                elif 196.0 <= x0 <= 215.0:
                    cols["poles"].append(t)
                # Nhóm 36KA
                elif 220.0 <= x0 <= 280.0:
                    if is_price:
                        cols["gia_36"].append(t)
                    else:
                        cols["ma_36"].append(t)
                elif 281.0 <= x0 <= 332.0:
                    cols["gia_36"].append(t)
                # Nhóm 50KA
                elif 333.0 <= x0 <= 395.0:
                    if is_price:
                        cols["gia_50"].append(t)
                    else:
                        cols["ma_50"].append(t)
                elif 396.0 <= x0 <= 442.0:
                    cols["gia_50"].append(t)
                # Nhóm 70KA
                elif 443.0 <= x0 <= 505.0:
                    if is_price:
                        cols["gia_70"].append(t)
                    else:
                        cols["ma_70"].append(t)
                elif 506.0 <= x0 <= 560.0:
                    cols["gia_70"].append(t)
                    
            loai = "".join(cols["loai"]).strip()
            in_a = "".join(cols["in_a"]).strip()
            poles = "".join(cols["poles"]).strip()
            
            if loai: loai_current = loai
            if poles: poles_current = poles
            
            if in_a:
                # 36KA
                ma_36 = "".join(cols["ma_36"])
                gia_36 = "".join(cols["gia_36"])
                c_ma_36, model_36 = split_dirty_merged_code(ma_36)
                c_gia_36 = clean_price(gia_36)
                if c_ma_36:
                    page_items.append({
                        "source_page": page_num,
                        "product_family": pf,
                        "type": loai_current or model_36,
                        "pole": f"{poles_current}P",
                        "rated_current": in_a,
                        "material_code": clean_code(c_ma_36),
                        "description": f"{pf} {loai_current} {poles_current}P {in_a}A 36KA".strip(),
                        "unit": "cái",
                        "unit_price": c_gia_36,
                        "currency": "VND",
                        "extraction_method": "coordinate_column_profiler",
                        "confidence": 0.94,
                        "evidence_text": evidence_text
                    })
                # 50KA
                ma_50 = "".join(cols["ma_50"])
                gia_50 = "".join(cols["gia_50"])
                c_ma_50, model_50 = split_dirty_merged_code(ma_50)
                c_gia_50 = clean_price(gia_50)
                if c_ma_50:
                    page_items.append({
                        "source_page": page_num,
                        "product_family": pf,
                        "type": loai_current or model_50,
                        "pole": f"{poles_current}P",
                        "rated_current": in_a,
                        "material_code": clean_code(c_ma_50),
                        "description": f"{pf} {loai_current} {poles_current}P {in_a}A 50KA".strip(),
                        "unit": "cái",
                        "unit_price": c_gia_50,
                        "currency": "VND",
                        "extraction_method": "coordinate_column_profiler",
                        "confidence": 0.94,
                        "evidence_text": evidence_text
                    })
                # 70KA
                ma_70 = "".join(cols["ma_70"])
                gia_70 = "".join(cols["gia_70"])
                c_ma_70, model_70 = split_dirty_merged_code(ma_70)
                c_gia_70 = clean_price(gia_70)
                if c_ma_70:
                    page_items.append({
                        "source_page": page_num,
                        "product_family": pf,
                        "type": loai_current or model_70,
                        "pole": f"{poles_current}P",
                        "rated_current": in_a,
                        "material_code": clean_code(c_ma_70),
                        "description": f"{pf} {loai_current} {poles_current}P {in_a}A 70KA".strip(),
                        "unit": "cái",
                        "unit_price": c_gia_70,
                        "currency": "VND",
                        "extraction_method": "coordinate_column_profiler",
                        "confidence": 0.94,
                        "evidence_text": evidence_text
                    })

        # --- F. LAYOUT SINGLE COLUMN RIGHT ---
        elif layout_type == "single_column_right":
            cols = defaultdict(list)
            left_words = []
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                
                is_price = "," in t and re.search(r"\d{3}", t)
                
                if x0 < 320.0:
                    if not is_price:
                        left_words.append(t)
                elif 320.0 <= x0 <= 470.0:
                    if is_price:
                        cols["gia"].append(t)
                    else:
                        cols["ma"].append(t)
                elif 471.0 <= x0 <= 570.0:
                    cols["gia"].append(t)
                    
            ma_str = "".join(cols["ma"]).strip()
            gia = "".join(cols["gia"]).strip()
            
            clean_ma, model = split_dirty_merged_code(ma_str)
            c_gia = clean_price(gia)
            
            if clean_ma:
                desc_left = " ".join(left_words).strip()
                
                rated_current = ""
                pole = "3P"
                if "4p" in desc_left.lower():
                    pole = "4P"
                
                in_match = re.search(r"\b(\d+(?:\.\d+)?)\s*a\b", desc_left.lower())
                if in_match:
                    rated_current = in_match.group(1)
                    
                page_items.append({
                    "source_page": page_num,
                    "product_family": pf,
                    "type": model or pf,
                    "pole": pole,
                    "rated_current": rated_current,
                    "material_code": clean_ma,
                    "description": f"{pf} {desc_left} {model}".strip(),
                    "unit": "cái",
                    "unit_price": c_gia,
                    "currency": "VND",
                    "extraction_method": "coordinate_column_profiler",
                    "confidence": 0.92,
                    "evidence_text": evidence_text
                })
                
    return page_items, pf, layout_type

def main():
    parser = argparse.ArgumentParser(description="Feasibility batch extraction on multiple ABB pages with Validation Hardening.")
    parser.add_argument(
        "--pdf-path", 
        default="D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf",
        help="Path to the original PDF file"
    )
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs")
    output_dir.mkdir(exist_ok=True)
    
    if not pdf_path.exists():
        print(f"Error: PDF file does not exist at: {pdf_path}")
        sys.exit(1)
        
    target_pages = [18, 19, 20, 21, 32, 33, 34, 41, 42, 52, 53, 54, 61]
    
    print(f"Starting batch extraction on {len(target_pages)} pages with Validation Hardening...")
    
    valid_extracted_items = []
    invalid_extracted_items = []
    page_summaries = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in target_pages:
            idx = page_num - 1
            if idx >= len(pdf.pages):
                print(f"Warning: Page {page_num} is out of range.")
                continue
                
            page = pdf.pages[idx]
            
            try:
                raw_items, pf, layout = parse_single_page(page, page_num)
                
                page_valid_items = []
                page_invalid_items = []
                page_errors_sample = []
                
                for item in raw_items:
                    is_valid, errors, warnings = validate_extracted_item(item, layout)
                    if is_valid:
                        page_valid_items.append(item)
                    else:
                        invalid_record = {
                            "source_page": page_num,
                            "raw_item": item,
                            "errors": errors,
                            "warnings": warnings
                        }
                        page_invalid_items.append(invalid_record)
                        page_errors_sample.extend(errors)
                        
                raw_count = len(raw_items)
                valid_count = len(page_valid_items)
                invalid_count = len(page_invalid_items)
                
                invalid_ratio = (invalid_count / raw_count) if raw_count > 0 else 0.0
                
                status = "FAIL"
                if valid_count >= 10 and invalid_ratio <= 0.05:
                    status = "PASS"
                elif valid_count > 0:
                    status = "PARTIAL"
                    
                page_summaries.append({
                    "page": page_num,
                    "status": status,
                    "items_count": raw_count,
                    "valid_items_count": valid_count,
                    "invalid_items_count": invalid_count,
                    "invalid_ratio": round(invalid_ratio * 100, 1),
                    "errors_sample": list(set(page_errors_sample))[:5],
                    "detected_table_type": layout,
                    "notes": [f"Product family: {pf}"]
                })
                
                valid_extracted_items.extend(page_valid_items)
                invalid_extracted_items.extend(page_invalid_items)
                
                print(f"Page {page_num}: status={status}, raw={raw_count}, valid={valid_count}, invalid={invalid_count} ({round(invalid_ratio*100, 1)}% error)")
            except Exception as e:
                page_summaries.append({
                    "page": page_num,
                    "status": "FAIL",
                    "items_count": 0,
                    "valid_items_count": 0,
                    "invalid_items_count": 0,
                    "invalid_ratio": 0.0,
                    "errors_sample": [str(e)],
                    "detected_table_type": "unknown",
                    "notes": []
                })
                print(f"Page {page_num}: status=FAIL, error={e}")

    items_json_path = output_dir / "abb_batch_items.json"
    with open(items_json_path, "w", encoding="utf-8") as f:
        json.dump(valid_extracted_items, f, ensure_ascii=False, indent=2)
    print(f"Saved valid batch items JSON to: {items_json_path}")
    
    df = pd.DataFrame(valid_extracted_items)
    items_excel_path = output_dir / "abb_batch_items.xlsx"
    df.to_excel(items_excel_path, index=False)
    print(f"Saved valid batch items Excel to: {items_excel_path}")
    
    invalid_json_path = output_dir / "abb_batch_invalid_items.json"
    with open(invalid_json_path, "w", encoding="utf-8") as f:
        json.dump(invalid_extracted_items, f, ensure_ascii=False, indent=2)
    print(f"Saved invalid batch items JSON to: {invalid_json_path}")
    
    summary_json_path = output_dir / "abb_batch_page_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(page_summaries, f, ensure_ascii=False, indent=2)
    print(f"Saved page summary JSON to: {summary_json_path}")
    
    total_raw_items = len(valid_extracted_items) + len(invalid_extracted_items)
    total_valid_items = len(valid_extracted_items)
    total_invalid_items = len(invalid_extracted_items)
    
    passed_pages = sum(1 for p in page_summaries if p["status"] == "PASS")
    partial_pages = sum(1 for p in page_summaries if p["status"] == "PARTIAL")
    failed_pages = sum(1 for p in page_summaries if p["status"] == "FAIL")
    
    batch_status = "FAIL"
    if passed_pages >= 3 and total_valid_items >= 100:
        if partial_pages > 0 or failed_pages > 0:
            batch_status = "PARTIAL"
        else:
            batch_status = "PASS"
    elif total_valid_items > 0:
        batch_status = "PARTIAL"
        
    print(f"Batch evaluation status: {batch_status} (Valid items: {total_valid_items}, Raw: {total_raw_items})")
    
    report_path = output_dir / "abb_batch_report.md"
    
    page_table_str = "| Trang | Trạng Thái | Raw Items | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Lý Do / Lỗi Ghi Nhận |\n| --- | --- | --- | --- | --- | --- | --- |\n"
    for p in page_summaries:
        errors_str = ", ".join(p["errors_sample"]) if p["errors_sample"] else "None"
        page_table_str += f"| {p['page']} | {p['status']} | {p['items_count']} | {p['valid_items_count']} | {p['invalid_items_count']} | {p['invalid_ratio']}% | {errors_str} |\n"
        
    sample_rows_str = ""
    for idx, it in enumerate(valid_extracted_items[:20]):
        desc_vi = it['description'].replace("Cau dao tu dong dang khoi", "Cầu dao tự động dạng khối")
        sample_rows_str += f"| {idx+1} | Trang {it['source_page']} | {it['material_code']} | {desc_vi} | {it['pole']} | {it['rated_current']} | {it['unit_price']:,} | {it['unit']} |\n"
        
    report_content = f"""# Báo Cáo Tính Khả Thi Bóc Tách Bảng Hệ Thống – ABB Batch Benchmark

## 1. Kết Quả Tổng Hợp Chân Thực
* **Tổng số trang thử nghiệm**: {len(target_pages)} trang
* **Số trang đạt trạng thái PASS (Valid >= 10 và Tỷ Lệ Lỗi <= 5%)**: {passed_pages} trang
* **Số trang đạt trạng thái PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: {partial_pages} trang
* **Số trang thất bại (FAIL / Lỗi)**: {failed_pages} trang
* **Tổng số vật tư thô (Raw)**: {total_raw_items} items
* **Tổng số vật tư hợp lệ (Valid)**: {total_valid_items} items
* **Tổng số vật tư lỗi (Invalid)**: {total_invalid_items} items
* **Trạng thái đánh giá toàn cục**: **{batch_status}**

## 2. Bảng Thống Kê Chi Tiết Theo Trang
{page_table_str}

## 3. Dòng Dữ Liệu Hợp Lệ Mẫu (20 Dòng Đầu)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) | Đơn Vị |
| --- | --- | --- | --- | --- | --- | --- | --- |
{sample_rows_str}

## 4. Các Lỗi Mapping Đã Phát Hiện & Cách Khắc Phục
* **Lệch cột trang 21**: Trang 21 có cấu trúc 3 cột khả năng cắt song song (N, S, H) độc lập thay vì cột 3P/4P của dòng XT Tmax thông dụng. Đã khắc phục bằng cách thiết lập cấu hình tọa độ `three_cutoff_groups_page21` riêng biệt.
* **Ghép bẩn AX trang 61**: Do khoảng cách quá hẹp, model AX50... bị dính liền vào mã sản phẩm `1SBL...`. Đã viết hàm `split_dirty_merged_code` tách model và mã sạch qua Regex.
* **Lẫn lộn cột giá/mô tả trang 52**: Dòng giá của bảng trái bị tràn sang cột lề trái của bảng phải. Đã xử lý bằng cách siết chặt tọa độ X0 nửa phải (`x0 >= 312`) và loại trừ số tiền chứa dấu phẩy ra khỏi description.

## 5. Kết Luận & Khuyến Nghị
* **Độ tin cậy của Coordinate Column Profiler**: Hướng đi bóc tách theo tọa độ word có tính khả thi cao, nhưng đòi hỏi phải thiết kế các **Supplier Profiles** chặt chẽ chứa cấu hình tọa độ X riêng cho từng nhóm trang layout.
* **Đề xuất tiếp theo**: Đánh giá toàn cục ở trạng thái **{batch_status}** phản ánh trung thực rằng một số trang vẫn tồn tại tỷ lệ lỗi mapping cột nhất định và cần bổ sung thêm các bộ profile tinh chỉnh.
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Successfully saved batch report to: {report_path}")

if __name__ == "__main__":
    main()
