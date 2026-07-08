import re
import pdfplumber
from collections import defaultdict
from typing import List, Dict, Any, Tuple
from tools.feasibility.abb_profile.models import ExtractedItem
from tools.feasibility.abb_profile.layouts import (
    split_dirty_merged_code,
    split_merged_words_by_coordinates
)

def clean_code(code: str) -> str:
    return re.sub(r"\s+", "", code).upper()
    
def clean_price(price_str: str) -> int:
    clean_str = re.sub(r"[^\d]", "", price_str)
    return int(clean_str) if clean_str else 0

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

def parse_page(page, page_num: int) -> Tuple[List[ExtractedItem], str, str]:
    words = page.extract_words()
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
    elif page_num in [41, 42]:
        layout_type = "four_columns_ot_page41"
    elif "mccb" in text_lower or "acb" in text_lower or "mccb 3p" in text_lower or "acb 3p" in text_lower or "xt1" in text_lower or "emax" in text_lower:
        layout_type = "double_column_3p_4p"
    elif "cầu dao tự động khởi động động cơ" in text_lower or "ms116" in text_lower or "tiếp điểm phụ" in text_lower or "ms132" in text_lower:
        layout_type = "split_half_left_right"
        
    extracted_items = []
    raw_detected = 0
    skipped = 0
    
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

        # --- A. LAYOUT DOUBLE COLUMN 3P/4P ---
        if layout_type == "double_column_3p_4p":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
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
                raw_detected += 1
                c_ma_3p = clean_code(ma_3p)
                if c_ma_3p.startswith("MP1SDA") or c_ma_3p.startswith("FP1SDA"):
                    c_ma_3p = c_ma_3p[2:]
                c_gia_3p = clean_price(gia_3p)
                if c_gia_3p > 0 and c_ma_3p != "":
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai_current,
                        pole="3P",
                        rated_current=in_a,
                        breaking_capacity=khi_nang_cat_current,
                        material_code=c_ma_3p,
                        description=f"{pf} {loai_current} 3P {in_a}A {khi_nang_cat_current}".strip(),
                        unit="cái",
                        unit_price=c_gia_3p,
                        currency="VND",
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                # 4P
                raw_detected += 1
                c_ma_4p = clean_code(ma_4p)
                if c_ma_4p.startswith("MP1SDA") or c_ma_4p.startswith("FP1SDA"):
                    c_ma_4p = c_ma_4p[2:]
                c_gia_4p = clean_price(gia_4p)
                if c_gia_4p > 0 and c_ma_4p != "":
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai_current,
                        pole="4P",
                        rated_current=in_a,
                        breaking_capacity=khi_nang_cat_current,
                        material_code=c_ma_4p,
                        description=f"{pf} {loai_current} 4P {in_a}A {khi_nang_cat_current}".strip(),
                        unit="cái",
                        unit_price=c_gia_4p,
                        currency="VND",
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1

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
                # Nửa phải (Giới hạn x0 >= 312)
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
            ma_3p_clean, model_left = split_dirty_merged_code(ma_3p)
            
            left_prices = [w["text"] for w in line_words if 271.0 <= w["x0"] <= 311.0 or (201.0 <= w["x0"] <= 270.0 and "," in w["text"])]
            gia_3p = "".join(left_prices).strip()
            
            vi_tri = " ".join(cols["vi_tri"]).strip()
            tiep_diem = " ".join(cols["tiep_diem"]).strip()
            loai_r = "".join(cols["loai_r"]).strip()
            ma_r = "".join(cols["ma_r"]).strip()
            ma_r_clean, model_right = split_dirty_merged_code(ma_r)
            
            right_prices = [w["text"] for w in line_words if 501.0 <= w["x0"] <= 570.0 or (426.0 <= w["x0"] <= 500.0 and "," in w["text"])]
            gia_r = "".join(right_prices).strip()
            
            if in_a:
                raw_detected += 1
                c_ma_3p = clean_code(ma_3p_clean)
                c_gia_3p = clean_price(gia_3p)
                if c_gia_3p > 0 and c_ma_3p != "":
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai or model_left,
                        pole="3P",
                        rated_current=in_a,
                        breaking_capacity=khi_nang_cat,
                        material_code=c_ma_3p,
                        description=f"{pf} {loai} {in_a}A {khi_nang_cat}".strip(),
                        unit="cái",
                        unit_price=c_gia_3p,
                        currency="VND",
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
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=f"Phụ kiện {pf}",
                        type=final_model_right,
                        pole="",
                        rated_current="",
                        breaking_capacity="",
                        material_code=c_ma_r,
                        description=f"Phụ kiện {pf} {final_model_right} {tiep_diem} {vi_tri}".strip(),
                        unit="cái",
                        unit_price=c_gia_r,
                        currency="VND",
                        confidence=0.90,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1

        # --- C. LAYOUT THREE CUTOFF GROUPS PAGE 21 ---
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
                raw_detected += 1
                ma_36 = "".join(cols["ma_36"])
                gia_36 = "".join(cols["gia_36"])
                c_ma_36, model_36 = split_dirty_merged_code(ma_36)
                c_gia_36 = clean_price(gia_36)
                c_ma_36_clean = clean_code(c_ma_36)
                if c_ma_36_clean and c_gia_36 > 0:
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai_current or model_36,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="36KA",
                        material_code=c_ma_36_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 36KA".strip(),
                        unit="cái",
                        unit_price=c_gia_36,
                        currency="VND",
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
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai_current or model_50,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="50KA",
                        material_code=c_ma_50_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 50KA".strip(),
                        unit="cái",
                        unit_price=c_gia_50,
                        currency="VND",
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
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=loai_current or model_70,
                        pole=f"{poles_current}P",
                        rated_current=in_a,
                        breaking_capacity="70KA",
                        material_code=c_ma_70_clean,
                        description=f"{pf} {loai_current} {poles_current}P {in_a}A 70KA".strip(),
                        unit="cái",
                        unit_price=c_gia_70,
                        currency="VND",
                        confidence=0.94,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1

        # --- E. LAYOUT SINGLE COLUMN RIGHT ---
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
            
            if clean_ma or c_gia > 0:
                raw_detected += 1
                if clean_ma and c_gia > 0:
                    desc_left = " ".join(left_words).strip()
                    
                    rated_current = ""
                    pole = "3P"
                    if "4p" in desc_left.lower():
                        pole = "4P"
                    
                    in_match = re.search(r"\b(\d+(?:\.\d+)?)\s*a\b", desc_left.lower())
                    if in_match:
                        rated_current = in_match.group(1)
                        
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=model or pf,
                        pole=pole,
                        rated_current=rated_current,
                        breaking_capacity="",
                        material_code=clean_ma,
                        description=f"{pf} {desc_left} {model}".strip(),
                        unit="cái",
                        unit_price=c_gia,
                        currency="VND",
                        confidence=0.92,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1

        # --- F. LAYOUT FOUR COLUMNS OT PAGE 41/42 ---
        elif layout_type == "four_columns_ot_page41":
            cols = defaultdict(list)
            for w in line_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                is_price = "," in t and re.search(r"\d{3}", t)
                
                if 150.0 <= x0 <= 319.9:
                    cols["ith"].append(t)
                elif 320.0 <= x0 <= 419.9:
                    cols["in_a"].append(t)
                elif 420.0 <= x0 <= 499.9:
                    if is_price:
                        cols["gia"].append(t)
                    else:
                        cols["ma"].append(t)
                elif 500.0 <= x0 <= 580.0:
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
                    if "F4" in clean_ma or "04P" in clean_ma:
                        pole = "4P"
                    
                    desc = f"{pf} {clean_ma} Ith={ith} In={in_a}".strip()
                    extracted_items.append(ExtractedItem(
                        source_page=page_num,
                        layout_name=layout_type,
                        product_family=pf,
                        type=clean_ma,
                        pole=pole,
                        rated_current=in_a or ith,
                        breaking_capacity="",
                        material_code=clean_ma,
                        description=desc,
                        unit="cái",
                        unit_price=c_gia,
                        currency="VND",
                        confidence=0.95,
                        extraction_method="coordinate_column_profiler",
                        evidence_text=evidence_text
                    ))
                else:
                    skipped += 1
                
    return extracted_items, pf, layout_type, raw_detected, skipped
