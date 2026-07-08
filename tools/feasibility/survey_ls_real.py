import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf")
    output_file = Path("D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v0/survey_dump_ls_real.txt")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    if not pdf_path.exists():
        print("Error: Real LS PDF file not found")
        return
        
    print("Surveying real LS PDF file...")
    
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        print(f"Page Count of LS Real: {page_count}")
        
        with open(output_file, "w", encoding="utf-8") as f:
            for i in range(page_count):
                text = pdf.pages[i].extract_text()
                f.write(f"=== Page {i+1} (Length: {len(text) if text else 0}) ===\n")
                if text:
                    f.write(text)
                f.write("\n\n")
                
    print(f"Dumped real LS page texts to: {output_file}")

if __name__ == "__main__":
    main()
