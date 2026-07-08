import pdfplumber
from pathlib import Path

pdf_path = Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf")
output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs")
output_dir.mkdir(exist_ok=True)

target_pages = [18, 19, 20, 21, 32, 33, 34, 41, 42, 52, 53, 54, 61]

with pdfplumber.open(pdf_path) as pdf:
    for page_num in target_pages:
        idx = page_num - 1
        if idx >= len(pdf.pages):
            continue
        page = pdf.pages[idx]
        text = page.extract_text()
        
        # Ghi văn bản thô ra file khảo sát
        survey_file = output_dir / f"survey_page_{page_num}_text.txt"
        with open(survey_file, "w", encoding="utf-8") as f:
            f.write(text if text else "")
            
        print(f"Page {page_num}: size={round(page.width)}x{round(page.height)}, text length={len(text) if text else 0}")
