import pdfplumber
import re
import json
from pathlib import Path
from collections import defaultdict

pdf_path = Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf")

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[17]
    words = page.extract_words()
    
    # Nhóm các word theo dòng (tọa độ top xấp xỉ nhau)
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
    
    khi_nang_cat_current = ""
    loai_current = ""
    
    items = []
    
    for top in sorted_tops:
        # Chỉ xử lý phần bảng dữ liệu thực tế (Y từ 270 đến 820)
        if not (270.0 <= top <= 820.0):
            continue
            
        line_words = sorted(rows[top], key=lambda x: x["x0"])
        
        # Tạo cấu trúc các cột
        cols = {
            "khi_nang_cat": [],
            "loai": [],
            "in_a": [],
            "ma_3p": [],
            "gia_3p": [],
            "ma_4p": [],
            "gia_4p": []
        }
        
        for w in line_words:
            x0 = w["x0"]
            text = w["text"].strip()
            if not text:
                continue
                
            if 150.0 <= x0 <= 200.0:
                cols["khi_nang_cat"].append(text)
            elif 210.0 <= x0 <= 250.0:
                cols["loai"].append(text)
            elif 255.0 <= x0 <= 290.0:
                cols["in_a"].append(text)
            elif 300.0 <= x0 <= 380.0:
                cols["ma_3p"].append(text)
            elif 381.0 <= x0 <= 435.0:
                cols["gia_3p"].append(text)
            elif 440.0 <= x0 <= 505.0:
                cols["ma_4p"].append(text)
            elif 506.0 <= x0 <= 570.0:
                cols["gia_4p"].append(text)
                
        # Ghép text trong từng cột
        khi_nang_cat = "".join(cols["khi_nang_cat"]).strip()
        loai = "".join(cols["loai"]).strip()
        in_a = "".join(cols["in_a"]).strip()
        ma_3p = "".join(cols["ma_3p"]).strip()
        gia_3p = "".join(cols["gia_3p"]).strip()
        ma_4p = "".join(cols["ma_4p"]).strip()
        gia_4p = "".join(cols["gia_4p"]).strip()
        
        # Cập nhật trạng thái kế thừa
        if khi_nang_cat:
            khi_nang_cat_current = khi_nang_cat
        if loai:
            loai_current = loai
            
        # Dòng text thô của dòng này để làm bằng chứng
        evidence_text = " ".join([w["text"] for w in line_words])
        
        # Bắt đầu trích xuất
        if in_a:
            # Clean mã sản phẩm
            def clean_code(code: str) -> str:
                return re.sub(r"\s+", "", code).upper()
                
            def clean_price(price_str: str) -> int:
                clean_str = re.sub(r"[^\d]", "", price_str)
                return int(clean_str) if clean_str else 0
                
            # Trích xuất 3P
            c_ma_3p = clean_code(ma_3p)
            c_gia_3p = clean_price(gia_3p)
            if c_ma_3p.startswith("1SDA") and len(c_ma_3p) == 12 and c_gia_3p > 0:
                items.append({
                    "source_page": 18,
                    "product_family": "MCCB Tmax",
                    "type": loai_current,
                    "pole": "3P",
                    "rated_current": in_a,
                    "material_code": c_ma_3p,
                    "description": f"Cầu dao tự động dạng khối MCCB Tmax {loai_current} 3P {in_a}A {khi_nang_cat_current}",
                    "unit": "cái",
                    "unit_price": c_gia_3p,
                    "currency": "VND",
                    "extraction_method": "table_coordinates_probe",
                    "evidence_text": evidence_text
                })
                
            # Trích xuất 4P
            c_ma_4p = clean_code(ma_4p)
            c_gia_4p = clean_price(gia_4p)
            if c_ma_4p.startswith("1SDA") and len(c_ma_4p) == 12 and c_gia_4p > 0:
                items.append({
                    "source_page": 18,
                    "product_family": "MCCB Tmax",
                    "type": loai_current,
                    "pole": "4P",
                    "rated_current": in_a,
                    "material_code": c_ma_4p,
                    "description": f"Cầu dao tự động dạng khối MCCB Tmax {loai_current} 4P {in_a}A {khi_nang_cat_current}",
                    "unit": "cái",
                    "unit_price": c_gia_4p,
                    "currency": "VND",
                    "extraction_method": "table_coordinates_probe",
                    "evidence_text": evidence_text
                })

print(f"Extracted {len(items)} items.")
for it in items[:5]:
    print(it)
