import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("F:/00.HVC/Bang gia/LS/Bảng Giá Tổng Hợp 2026-V17 T5.pdf")
    output_file = Path("D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v0/survey_dump.txt")
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    with pdfplumber.open(pdf_path) as pdf:
        with open(output_file, "w", encoding="utf-8") as f:
            for i in range(len(pdf.pages)):
                text = pdf.pages[i].extract_text()
                f.write(f"=== Page {i+1} (Length: {len(text) if text else 0}) ===\n")
                if text:
                    f.write(text)
                f.write("\n\n")
    print(f"Dumped all page texts to: {output_file}")

if __name__ == "__main__":
    main()
