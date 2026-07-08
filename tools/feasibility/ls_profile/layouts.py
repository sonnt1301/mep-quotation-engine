import re
from typing import List, Dict, Any, Tuple

def split_dirty_merged_code(merged: str) -> Tuple[str, str]:
    """
    Tách model/type và mã sản phẩm LS ra riêng nếu bị dính nhau.
    """
    merged = merged.strip()
    match = re.search(r"([A-Z]{2,}\d+[A-Z]*|\d{2,}[A-Z]{2,}\w*)", merged)
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

# Tọa độ cột X của LS được tối ưu hóa theo kết quả chẩn đoán thực tế
LS_COLS = {
    "left": {
        "ma": (35.0, 120.0),
        "in_a": (121.0, 215.0),
        "icu": (216.0, 260.0),
        "gia": (261.0, 315.0)
    },
    "right": {
        "ma": (291.0, 385.0),
        "in_a": (386.0, 480.0),
        "icu": (481.0, 515.0),
        "gia": (516.0, 580.0)
    }
}
