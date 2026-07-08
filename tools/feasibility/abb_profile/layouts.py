import re
from typing import List, Dict, Any, Tuple

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

# Các định cấu hình dải cột tọa độ X của các layout
LAYOUT_COLS = {
    "double_column_3p_4p": {
        "khi_nang_cat": (150.0, 200.0),
        "loai": (210.0, 250.0),
        "in_a": (255.0, 290.0),
        "ma_3p": (300.0, 380.0),
        "gia_3p": (381.0, 435.0),
        "ma_4p": (440.0, 505.0),
        "gia_4p": (506.0, 570.0)
    },
    "three_cutoff_groups_page21": {
        "loai": (140.0, 160.0),
        "in_a": (165.0, 195.0),
        "poles": (196.0, 215.0),
        "ma_36": (220.0, 280.0),
        "gia_36": (281.0, 332.0),
        "ma_50": (333.0, 395.0),
        "gia_50": (396.0, 442.0),
        "ma_70": (443.0, 505.0),
        "gia_70": (506.0, 560.0)
    },
    "split_half_left_right": {
        # Nửa trái
        "in_a": (40.0, 120.0),
        "khi_nang_cat": (121.0, 150.0),
        "loai": (151.0, 200.0),
        "ma_3p": (201.0, 270.0),
        "gia_3p": (271.0, 311.0),
        # Nửa phải
        "vi_tri": (312.0, 335.0),
        "tiep_diem": (336.0, 385.0),
        "loai_r": (386.0, 425.0),
        "ma_r": (426.0, 500.0),
        "gia_r": (501.0, 570.0)
    },
    "single_column_right": {
        "desc_left": (0.0, 319.9),
        "ma": (320.0, 470.0),
        "gia": (471.0, 570.0)
    },
    "four_columns_ot_page41": {
        "ith": (150.0, 319.9),
        "in_a": (320.0, 419.9),
        "ma": (420.0, 499.9),
        "gia": (500.0, 580.0)
    }
}

