import os
import sys
# Tự động chèn thư mục gốc của dự án vào sys.path để tránh lỗi ModuleNotFoundError
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import argparse
from pathlib import Path
import pdfplumber
from tools.feasibility.abb_profile.parser import parse_page
from tools.feasibility.abb_profile.validator import validate_extracted_item
from tools.feasibility.abb_profile.export import export_results

def main():
    parser = argparse.ArgumentParser(description="Run ABB Supplier Profile Parser v0.")
    parser.add_argument(
        "--pdf-path", 
        default="D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf",
        help="Path to the original PDF file"
    )
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    output_dir = Path("D:/mep_quotation_pipeline/feasibility_outputs/abb_profile_v0")
    
    if not pdf_path.exists():
        print(f"Error: PDF file does not exist at: {pdf_path}")
        sys.exit(1)
        
    target_pages = [18, 19, 20, 21, 32, 33, 34, 41, 42, 52, 53, 54, 61]
    
    print(f"Executing ABB Supplier Profile Parser v0 on {len(target_pages)} pages...")
    
    valid_extracted_items = []
    invalid_extracted_items = []
    page_summaries = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in target_pages:
            idx = page_num - 1
            if idx >= len(pdf.pages):
                print(f"Warning: Page {page_num} is out of range.")
                continue
                
            page = pdf.pages[idx]
            
            try:
                raw_items, pf, layout = parse_page(page, page_num)
                
                page_valid_items = []
                page_invalid_items = []
                page_errors_sample = []
                
                for item in raw_items:
                    is_valid, errors, warnings = validate_extracted_item(item)
                    item_dict = item.to_dict()
                    
                    if is_valid:
                        item.validation_status = "valid"
                        page_valid_items.append(item_dict)
                    else:
                        item.validation_status = "invalid"
                        item.errors = errors
                        item.warnings = warnings
                        
                        invalid_record = {
                            "source_page": page_num,
                            "raw_item": item_dict,
                            "errors": errors,
                            "warnings": warnings
                        }
                        page_invalid_items.append(invalid_record)
                        page_errors_sample.extend(errors)
                        
                raw_count = len(raw_items)
                valid_count = len(page_valid_items)
                invalid_count = len(page_invalid_items)
                
                invalid_ratio = (invalid_count / raw_count) if raw_count > 0 else 0.0
                
                # Page Status Rule
                status = "FAIL"
                if valid_count >= 10 and invalid_ratio <= 0.05:
                    status = "PASS"
                elif valid_count > 0:
                    status = "PARTIAL"
                    
                page_summaries.append({
                    "page": page_num,
                    "status": status,
                    "items_count": raw_count,
                    "valid_items_count": valid_count,
                    "invalid_items_count": invalid_count,
                    "invalid_ratio": round(invalid_ratio * 100, 1),
                    "errors_sample": list(set(page_errors_sample))[:5],
                    "detected_table_type": layout,
                    "notes": [f"Product family: {pf}"]
                })
                
                valid_extracted_items.extend(page_valid_items)
                invalid_extracted_items.extend(page_invalid_items)
                
                print(f"Page {page_num}: status={status}, raw={raw_count}, valid={valid_count}, invalid={invalid_count} ({round(invalid_ratio*100, 1)}% error)")
            except Exception as e:
                page_summaries.append({
                    "page": page_num,
                    "status": "FAIL",
                    "items_count": 0,
                    "valid_items_count": 0,
                    "invalid_items_count": 0,
                    "invalid_ratio": 0.0,
                    "errors_sample": [str(e)],
                    "detected_table_type": "unknown",
                    "notes": []
                })
                print(f"Page {page_num}: status=FAIL, error={e}")

    # Xuất kết quả
    export_results(valid_extracted_items, invalid_extracted_items, page_summaries, output_dir)
    
    total_valid = len(valid_extracted_items)
    passed_pages = sum(1 for p in page_summaries if p["status"] == "PASS")
    total_pages = len(page_summaries)
    
    global_status = "FAIL"
    pass_ratio = passed_pages / total_pages if total_pages > 0 else 0.0
    if pass_ratio >= 0.80 and total_valid >= 100:
        global_status = "PASS"
    elif total_valid > 0:
        global_status = "PARTIAL"
        
    print(f"Global Evaluation Status: {global_status} (Valid items: {total_valid})")

if __name__ == "__main__":
    main()
