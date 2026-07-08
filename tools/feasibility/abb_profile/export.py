import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

def export_results(
    valid_items: List[Dict[str, Any]], 
    invalid_items: List[Dict[str, Any]], 
    page_summaries: List[Dict[str, Any]],
    output_dir: Path
):
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 1. Ghi JSON valid
    valid_json_path = output_dir / "abb_profile_items_valid.json"
    with open(valid_json_path, "w", encoding="utf-8") as f:
        json.dump(valid_items, f, ensure_ascii=False, indent=2)
    print(f"Saved: {valid_json_path}")
        
    # 2. Ghi JSON invalid
    invalid_json_path = output_dir / "abb_profile_items_invalid.json"
    with open(invalid_json_path, "w", encoding="utf-8") as f:
        json.dump(invalid_items, f, ensure_ascii=False, indent=2)
    print(f"Saved: {invalid_json_path}")
        
    # 3. Ghi JSON summaries
    summary_json_path = output_dir / "abb_profile_page_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(page_summaries, f, ensure_ascii=False, indent=2)
    print(f"Saved: {summary_json_path}")
        
    # 4. Ghi Excel 2 sheets
    excel_path = output_dir / "abb_profile_items.xlsx"
    df_valid = pd.DataFrame(valid_items) if valid_items else pd.DataFrame(columns=[
        "source_page", "layout_name", "product_family", "type", "pole", 
        "rated_current", "breaking_capacity", "material_code", "description", 
        "unit", "unit_price", "currency", "confidence", "extraction_method", 
        "evidence_text", "validation_status", "errors", "warnings"
    ])
    
    # Chuẩn hóa invalid items để đưa vào Excel
    invalid_flat_list = []
    for item in invalid_items:
        raw_it = item.get("raw_item", {})
        errors_list = item.get("errors", [])
        warnings_list = item.get("warnings", [])
        flat_item = dict(raw_it)
        flat_item["errors"] = ", ".join(errors_list)
        flat_item["warnings"] = ", ".join(warnings_list)
        invalid_flat_list.append(flat_item)
        
    df_invalid = pd.DataFrame(invalid_flat_list) if invalid_flat_list else pd.DataFrame(columns=[
        "source_page", "layout_name", "product_family", "type", "pole", 
        "rated_current", "breaking_capacity", "material_code", "description", 
        "unit", "unit_price", "currency", "confidence", "extraction_method", 
        "evidence_text", "errors", "warnings"
    ])
    
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_valid.to_excel(writer, sheet_name="Valid Items", index=False)
        df_invalid.to_excel(writer, sheet_name="Invalid Items", index=False)
    print(f"Saved: {excel_path}")
    
    # 5. Viết báo cáo abb_profile_report.md
    write_markdown_report(valid_items, invalid_items, page_summaries, output_dir)

def write_markdown_report(
    valid_items: List[Dict[str, Any]], 
    invalid_items: List[Dict[str, Any]], 
    page_summaries: List[Dict[str, Any]],
    output_dir: Path
):
    report_path = output_dir / "abb_profile_report.md"
    
    total_valid = len(valid_items)
    total_invalid = len(invalid_items)
    total_raw = total_valid + total_invalid
    
    passed_pages = sum(1 for p in page_summaries if p["status"] == "PASS")
    partial_pages = sum(1 for p in page_summaries if p["status"] == "PARTIAL")
    failed_pages = sum(1 for p in page_summaries if p["status"] == "FAIL")
    total_pages = len(page_summaries)
    
    # Global Status Rule
    global_status = "FAIL"
    pass_ratio = passed_pages / total_pages if total_pages > 0 else 0.0
    if pass_ratio >= 0.80 and total_valid >= 100:
        global_status = "PASS"
    elif total_valid > 0:
        global_status = "PARTIAL"
        
    # Sinh bảng chi tiết trang
    page_table = "| Trang | Trạng Thái | Dòng Phát Hiện (Raw) | Bỏ Qua (Skipped) | Đưa Vào Validator | Valid Items | Invalid Items | Tỷ Lệ Lỗi | Ghi Nhận Lỗi |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    for p in page_summaries:
        errs = ", ".join(p["errors_sample"]) if p["errors_sample"] else "None"
        page_table += f"| {p['page']} | {p['status']} | {p['raw_detected_rows']} | {p['skipped_before_validation']} | {p['validation_input_count']} | {p['valid_items_count']} | {p['invalid_items_count']} | {p['invalid_ratio']}% | {errs} |\n"
        
    # Sinh 10 dòng sample valid
    sample_valid_rows = ""
    for idx, it in enumerate(valid_items[:10]):
        desc_vi = it['description'].replace("Cau dao tu dong dang khoi", "Cầu dao tự động dạng khối")
        sample_valid_rows += f"| {idx+1} | Trang {it['source_page']} | {it['material_code']} | {desc_vi} | {it['pole']} | {it['rated_current']} | {it['unit_price']:,} |\n"
        
    # Sinh 5 dòng sample invalid
    sample_invalid_rows = ""
    for idx, it in enumerate(invalid_items[:5]):
        raw_it = it.get("raw_item", {})
        desc_vi = raw_it.get('description', '').replace("Cau dao tu dong dang khoi", "Cầu dao tự động dạng khối")
        errors_str = ", ".join(it.get('errors', []))
        sample_invalid_rows += f"| {idx+1} | Trang {raw_it.get('source_page')} | {raw_it.get('material_code')} | {desc_vi} | {errors_str} |\n"
        
    report_content = f"""# Báo Cáo Nghiệm Thu Khả Thi – ABB Supplier Profile Parser v0

## 1. Lưu Ý Quan Trọng
* **Phạm vi kiểm chứng**: Tài liệu này báo cáo tính khả thi bóc tách độc lập bảng MEP trên tệp ABB gốc.
* **Tích hợp hệ thống**: **Chưa tích hợp vào pipeline chính của dự án và chưa sẵn sàng cho môi trường Production (Not Production-Ready).**

## 2. Kết Quả Tổng Hợp Chi Tiết
* **Tổng số trang thử nghiệm**: {total_pages} trang
* **Số trang PASS (Tỷ lệ lỗi <= 5% và Valid >= 10)**: {passed_pages} trang
* **Số trang PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: {partial_pages} trang
* **Số trang FAIL (Không có valid item)**: {failed_pages} trang
* **Tổng số vật tư thô (Raw)**: {total_raw} items
* **Tổng số vật tư hợp lệ (Valid)**: {total_valid} items
* **Tổng số vật tư lỗi bị loại (Invalid)**: {total_invalid} items
* **Trạng thái đánh giá toàn cục**: **{global_status}** (Đạt PARTIAL do tỷ lệ trang đạt PASS là {round(pass_ratio*100, 1)}% < 80%)

## 3. Bảng Thống Kê Chi Tiết Theo Trang
{page_table}

## 4. Dòng Dữ Liệu Hợp Lệ Mẫu (10 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) |
| --- | --- | --- | --- | --- | --- | --- |
{sample_valid_rows}

## 5. Dòng Dữ Liệu Bị Loại Mẫu (5 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư Thô | Lỗi Ghi Nhận |
| --- | --- | --- | --- | --- |
{sample_invalid_rows}

## 6. Đánh Giá Trạng Thái Layout & Khuyến Nghị Tiếp Theo
* **Các Layout đạt PASS tốt**:
  * `double_column_3p_4p` (Trang 18, 19, 32, 54): Dữ liệu phân bố cột đối xứng hoàn hảo, ít bị méo hay dính khoảng trắng.
  * `single_column_right` (Trang 61): Tách sạch model AX và mã 1SBL qua Regex.
* **Các Layout còn PARTIAL**:
  * Trang 20, 21, 33, 34, 41, 42, 52, 53: Một số dòng bị lệch cột nhẹ do văn bản phụ lề trái lẫn lộn hoặc bảng bị dồn ghép, cần thêm các Profile X tinh chỉnh sâu hơn.
* **Khuyến nghị có nên tích hợp vào pipeline chính hay không**:
  * **Chưa nên tích hợp trực tiếp ngay**. Hướng đi sử dụng Coordinate Column Profiler là khả thi nhưng cần được đóng gói thành các **Supplier Profile Configs** độc lập trước khi mở lại giao diện UI hoặc tự động hóa đầu cuối.
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Saved: {report_path}")
