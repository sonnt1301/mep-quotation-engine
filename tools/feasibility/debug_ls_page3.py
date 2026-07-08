import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf")
    output_file = Path("D:/mep_quotation_pipeline/feasibility_outputs/ls_page3_dump.txt")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[2] # Trang 3 là index 2
        words = page.extract_words()
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("--- LS Page 3 Word Coords ---\n")
            for w in words:
                f.write(f"  {w['text']}: x0={round(w['x0'], 2)}, x1={round(w['x1'], 2)}, top={round(w['top'], 2)}, bottom={round(w['bottom'], 2)}\n")
                
    print("Dumped LS Page 3 successfully")

if __name__ == "__main__":
    main()
