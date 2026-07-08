import re
import pdfplumber
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional
from tools.feasibility.ls_profile.models import ExtractedItem
from tools.feasibility.ls_profile.layouts import (
    split_dirty_merged_code,
    split_merged_words_by_coordinates,
    LS_COLS
)
from tools.feasibility.ls_profile.validator import is_valid_ls_code

def clean_code(code: str) -> str:
    return re.sub(r"\s+", "", code).upper()
    
def clean_price(price_str: str) -> int:
    clean_str = re.sub(r"[^\d]", "", price_str)
    return int(clean_str) if clean_str else 0

def extract_pole_from_text(text: str) -> str:
    text_lower = text.lower()
    if "4 pha" in text_lower or "4 cực" in text_lower or "4p" in text_lower:
        return "4P"
    elif "3 pha" in text_lower or "3 cực" in text_lower or "3p" in text_lower:
        return "3P"
    elif "2 pha" in text_lower or "2 cực" in text_lower or "2p" in text_lower:
        return "2P"
    elif "1 pha" in text_lower or "1 cực" in text_lower or "1p" in text_lower:
        return "1P"
    return ""

def parse_page(page, page_num: int) -> Tuple[List[ExtractedItem], int, int]:
    words = page.extract_words()
    words = split_merged_words_by_coordinates(words)
    
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
    
    pf_left = "Thiết bị LS"
    pf_right = "Thiết bị LS"
    pole_left = "3P"
    pole_right = "3P"
    
    extracted_items = []
    raw_detected_total = 0
    skipped_total = 0
    
    for top in sorted_tops:
        if not (70.0 <= top <= 820.0):
            continue
            
        line_words = sorted(rows[top], key=lambda x: x["x0"])
        evidence_text = " ".join([w["text"] for w in line_words])
        
        line_lower = evidence_text.lower()
        is_header = ("cầu dao" in line_lower or "mccb" in line_lower or "elcb" in line_lower or "mcb" in line_lower or "phụ kiện" in line_lower or "khởi động từ" in line_lower or "rơ le" in line_lower or "thiết bị" in line_lower) and not ("," in evidence_text and re.search(r"\d{3}", evidence_text))
        
        if is_header:
            left_header_words = [w["text"] for w in line_words if w["x0"] < 290.0]
            right_header_words = [w["text"] for w in line_words if w["x0"] >= 290.0]
            
            l_hdr = " ".join(left_header_words).strip()
            r_hdr = " ".join(right_header_words).strip()
            
            if l_hdr and len(l_hdr) > 5:
                pf_left = l_hdr
                p_l = extract_pole_from_text(l_hdr)
                if p_l: pole_left = p_l
            if r_hdr and len(r_hdr) > 5:
                pf_right = r_hdr
                p_r = extract_pole_from_text(r_hdr)
                if p_r: pole_right = p_r
            continue
            
        left_words = [w for w in line_words if w["x0"] < 290.0]
        right_words = [w for w in line_words if w["x0"] >= 290.0]
        
        def process_half(half_words: List[Dict[str, Any]], pf_curr: str, pole_curr: str, is_left: bool) -> Tuple[Optional[ExtractedItem], bool, bool]:
            if not half_words:
                return None, False, False
                
            cols = defaultdict(list)
            side = "left" if is_left else "right"
            x_ma_min, x_ma_max = LS_COLS[side]["ma"]
            x_in_min, x_in_max = LS_COLS[side]["in_a"]
            x_icu_min, x_icu_max = LS_COLS[side]["icu"]
            x_gia_min, x_gia_max = LS_COLS[side]["gia"]
            
            for w in half_words:
                x0 = w["x0"]
                t = w["text"].strip()
                if not t: continue
                
                is_price = "," in t and re.search(r"\d{3}", t) and not re.search(r"[a-zA-Z]", t)
                
                if x_ma_min <= x0 <= x_ma_max:
                    if is_price:
                        cols["gia"].append(t)
                    else:
                        cols["ma"].append(t)
                elif x_in_min <= x0 <= x_in_max:
                    if is_price:
                        cols["gia"].append(t)
                    else:
                        cols["in_a"].append(t)
                elif x_icu_min <= x0 <= x_icu_max:
                    if is_price:
                        cols["gia"].append(t)
                    else:
                        cols["icu"].append(t)
                elif x_gia_min <= x0 <= x_gia_max:
                    cols["gia"].append(t)
                    
            ma_str = " ".join(cols["ma"]).strip()
            in_a_str = " ".join(cols["in_a"]).strip()
            icu_str = " ".join(cols["icu"]).strip()
            gia_str = "".join(cols["gia"]).strip()
            
            is_detected = bool(ma_str or in_a_str or gia_str)
            if not is_detected:
                return None, False, False
                
            c_gia = clean_price(gia_str)
            if not ma_str or c_gia == 0:
                return None, True, True
                
            tokens = ma_str.split(" ")
            material_code = ""
            for tok in tokens:
                tok_clean = re.sub(r"[^\w\-\~]", "", tok).upper()
                if is_valid_ls_code(tok_clean):
                    material_code = tok_clean
                    break
            if not material_code and tokens:
                material_code = re.sub(r"[^\w\-\~]", "", tokens[0]).upper()
                
            model = ma_str.replace(material_code, "").strip()
            
            desc = f"{pf_curr} {ma_str}".strip()
            if in_a_str:
                desc += f" In={in_a_str}"
            if icu_str:
                desc += f" Icu={icu_str}"
                
            final_pole = pole_curr
            pole_match = re.search(r"\b(\d)P\b", ma_str.upper())
            if pole_match:
                final_pole = pole_match.group(1) + "P"
            elif "1P" in ma_str.upper():
                final_pole = "1P"
            elif "2P" in ma_str.upper():
                final_pole = "2P"
            elif "3P" in ma_str.upper():
                final_pole = "3P"
            elif "4P" in ma_str.upper():
                final_pole = "4P"
                
            rated_current = in_a_str
            if not rated_current:
                in_match = re.search(r"\b(\d+(?:\.\d+)?\s*(?:A|A~|~))\b", desc)
                if in_match:
                    rated_current = in_match.group(1)
                    
            item = ExtractedItem(
                source_page=page_num,
                layout_name="split_half_left_right",
                product_family=pf_curr,
                type=model or pf_curr,
                pole=final_pole,
                rated_current=rated_current,
                breaking_capacity=icu_str,
                material_code=material_code,
                description=desc,
                unit="cái",
                unit_price=c_gia,
                currency="VND",
                confidence=0.92,
                extraction_method="coordinate_column_profiler",
                evidence_text=" ".join([w["text"] for w in half_words])
            )
            return item, True, False

        res_l, det_l, skip_l = process_half(left_words, pf_left, pole_left, is_left=True)
        res_r, det_r, skip_r = process_half(right_words, pf_right, pole_right, is_left=False)
        
        if det_l:
            raw_detected_total += 1
        if skip_l:
            skipped_total += 1
        if res_l:
            extracted_items.append(res_l)
            
        if det_r:
            raw_detected_total += 1
        if skip_r:
            skipped_total += 1
        if res_r:
            extracted_items.append(res_r)
            
    return extracted_items, raw_detected_total, skipped_total
