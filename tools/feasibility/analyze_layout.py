import pdfplumber
from pathlib import Path
from collections import defaultdict

pdf_path = Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf")
output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs")
output_dir.mkdir(exist_ok=True)

with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[17]
    words = page.extract_words()
    
    rows = defaultdict(list)
    for w in words:
        top = round(w["top"], 1)
        found = False
        for existing_top in rows:
            if abs(existing_top - w["top"]) < 2.0:
                rows[existing_top].append(w)
                found = True
                break
        if not found:
            rows[w["top"]].append(w)
            
    sorted_tops = sorted(rows.keys())
    
    output_file = output_dir / "page18_layout_analysis.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for top in sorted_tops:
            line_words = sorted(rows[top], key=lambda x: x["x0"])
            line_str = " | ".join([f"'{w['text']}'({round(w['x0'], 1)}-{round(w['x1'], 1)})" for w in line_words])
            f.write(f"Top {round(top, 1)}: {line_str}\n")
            
    print(f"Layout analysis saved to {output_file}")
