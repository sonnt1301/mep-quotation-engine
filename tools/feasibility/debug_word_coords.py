import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf")
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        words = page.extract_words()
        
        # Tìm các từ ở dòng chứa ABN52c
        # Tọa độ Y khoảng 100 - 150
        abn_words = [w for w in words if abs(w["top"] - 110.0) < 50.0]
        
        # Nhóm theo dòng
        from collections import defaultdict
        rows = defaultdict(list)
        for w in abn_words:
            found = False
            for r_top in rows:
                if abs(r_top - w["top"]) < 3.0:
                    rows[r_top].append(w)
                    found = True
                    break
            if not found:
                rows[w["top"]].append(w)
                
        for r_top in sorted(rows.keys()):
            line_words = sorted(rows[r_top], key=lambda x: x["x0"])
            line_str = " ".join([w["text"] for w in line_words])
            if "ABN52c" in line_str:
                print(f"Row top: {r_top}")
                for w in line_words:
                    print(f"  {w['text']}: x0={round(w['x0'], 2)}, x1={round(w['x1'], 2)}, top={round(w['top'], 2)}, bottom={round(w['bottom'], 2)}")

if __name__ == "__main__":
    main()
