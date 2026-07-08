import pdfplumber
import json
from pathlib import Path

pdf_path = Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf")
output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs")
output_dir.mkdir(exist_ok=True)

print(f"Loading PDF: {pdf_path}")
with pdfplumber.open(pdf_path) as pdf:
    # Trang 18 tương ứng index 17
    page = pdf.pages[17]
    print(f"Page size: width={page.width}, height={page.height}")
    
    # 1. Trích xuất text thô để khảo sát
    text = page.extract_text()
    with open(output_dir / "survey_page18_raw_text.txt", "w", encoding="utf-8") as f:
        f.write(text if text else "")
    print("Raw text saved to survey_page18_raw_text.txt")
    
    # 2. Trích xuất các bảng biểu tự động bằng pdfplumber
    tables = page.extract_tables()
    print(f"Found {len(tables)} tables automatically.")
    for idx, table in enumerate(tables):
        print(f"Table {idx} has {len(table)} rows and {len(table[0]) if table else 0} columns.")
        # Lưu mẫu 5 hàng đầu
        print("Sample rows:")
        for row in table[:10]:
            print(row)
        with open(output_dir / f"survey_page18_table_{idx}.json", "w", encoding="utf-8") as f:
            json.dump(table, f, ensure_ascii=False, indent=2)
            
    # 3. Trích xuất words để phân tích tọa độ nếu cần
    words = page.extract_words()
    print(f"Found {len(words)} words.")
    with open(output_dir / "survey_page18_words.json", "w", encoding="utf-8") as f:
        json.dump(words[:200], f, ensure_ascii=False, indent=2)
