import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf")
    
    # Dump Page 52
    output_file_52 = Path("D:/mep_quotation_pipeline/feasibility_outputs/abb_page52_dump.txt")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[51] # Trang 52 là index 51
        words = page.extract_words()
        with open(output_file_52, "w", encoding="utf-8") as f:
            f.write("--- ABB Page 52 Word Coords ---\n")
            for w in words:
                f.write(f"  {w['text']}: x0={round(w['x0'], 2)}, x1={round(w['x1'], 2)}, top={round(w['top'], 2)}, bottom={round(w['bottom'], 2)}\n")
                
    print("Dumped ABB Page 52 successfully")

if __name__ == "__main__":
    main()
