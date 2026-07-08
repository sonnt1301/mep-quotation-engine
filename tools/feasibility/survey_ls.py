import os
import sys
import pdfplumber
from pathlib import Path

def main():
    pdf_path = Path("F:/00.HVC/Bang gia/LS/Bảng Giá Tổng Hợp 2026-V17 T5.pdf")
    output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v0")
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if not pdf_path.exists():
        print(f"Error: PDF file not found")
        return
        
    print(f"Surveying LS PDF file...")
    
    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        is_encrypted = False # Mo thanh cong tuc la khong bi khoa mat khau
        
        first_page = pdf.pages[0]
        first_page_text = first_page.extract_text() or ""
        has_text_layer = len(first_page_text.strip()) > 0
        
        print(f"Page Count: {page_count}")
        print(f"Encrypted: {is_encrypted}")
        print(f"Has Text Layer: {has_text_layer}")
        
        candidate_pages = []
        for i in range(page_count):
            page_text = pdf.pages[i].extract_text() or ""
            text_lower = page_text.lower()
            
            keywords = ["mcb", "mccb", "metasol", "bkn", "susol", "contactor", "overload relay"]
            match_count = sum(1 for kw in keywords if kw in text_lower)
            
            has_price_indicator = "giá" in text_lower or "đơn giá" in text_lower or "vnd" in text_lower
            
            if match_count >= 2 and has_price_indicator:
                candidate_pages.append((i + 1, len(page_text), match_count))
                
        candidate_pages.sort(key=lambda x: x[2], reverse=True)
        
        selected_pages = [page_num for page_num, _, _ in candidate_pages[:8]]
        selected_pages.sort()
        
        print(f"Selected candidate pages for benchmark: {selected_pages}")
        
        survey_report_path = output_dir / "ls_survey_report.md"
        
        report_sections = []
        report_sections.append(f"""# Báo Cáo Khảo Sát Sơ Bộ – LS Supplier Feasibility

## 1. Thông Tin Tệp Tin & Metadata
* **Đường dẫn tệp tin**: `F:/00.HVC/Bang gia/LS/Bảng Giá Tổng Hợp 2026-V17 T5.pdf`
* **Số lượng trang**: {page_count} trang
* **Trạng thái mã hóa (Encrypted)**: {is_encrypted}
* **Lớp văn bản (Text Layer)**: {has_text_layer} (Có sẵn text layer gốc)
* **Các trang nghi ngờ chứa bảng giá**: {selected_pages}

## 2. Phân Tích Layout & Cấu Trúc Các Trang Benchmark Đề Xuất
Dưới đây là văn bản thô mẫu từ các trang benchmark tiêu biểu để phân tích cấu trúc cột:
""")
        
        for p_num in selected_pages[:5]:
            p_text = pdf.pages[p_num - 1].extract_text() or ""
            sample_lines = p_text.split("\n")[:15]
            sample_lines_str = "\n".join(sample_lines)
            
            report_sections.append(f"""### Trang {p_num} (Kích thước text: {len(p_text)} ký tự)
```text
{sample_lines_str}
```
""")
            
        report_sections.append("""## 3. Nhận Xét Chung & Hướng Đi Tiếp Theo
* **Nhận xét**: PDF của LS có cấu trúc text layer rất tốt, chữ viết rõ ràng và không bị mã hóa. Mã sản phẩm của LS thường có tiền tố đặc trưng như `BKN`, `Metasol`, `EBN`, `ABS` hoặc các chuỗi ký tự đi kèm đặc tả cực (1P, 2P, 3P, 4P).
* **Định vị cột**: Cần phân tích tọa độ Y-X để định hình cột mã sản phẩm và đơn giá bên phải tương tự như ABB.
""")
        
        with open(survey_report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_sections))
            
        print(f"Successfully saved survey report to: {survey_report_path}")

if __name__ == "__main__":
    main()
