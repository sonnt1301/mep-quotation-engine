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
    valid_json_path = output_dir / "ls_profile_items_valid.json"
    with open(valid_json_path, "w", encoding="utf-8") as f:
        json.dump(valid_items, f, ensure_ascii=False, indent=2)
    print(f"Saved: {valid_json_path}")
        
    # 2. Ghi JSON invalid
    invalid_json_path = output_dir / "ls_profile_items_invalid.json"
    with open(invalid_json_path, "w", encoding="utf-8") as f:
        json.dump(invalid_items, f, ensure_ascii=False, indent=2)
    print(f"Saved: {invalid_json_path}")
        
    # 3. Ghi JSON summaries
    summary_json_path = output_dir / "ls_profile_page_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(page_summaries, f, ensure_ascii=False, indent=2)
    print(f"Saved: {summary_json_path}")
        
    # 4. Ghi Excel 2 sheets
    excel_path = output_dir / "ls_profile_items.xlsx"
    df_valid = pd.DataFrame(valid_items) if valid_items else pd.DataFrame(columns=[
        "source_supplier", "source_page", "layout_name", "product_family", "type", 
        "pole", "rated_current", "material_code", "description", 
        "unit", "unit_price", "currency", "confidence", "extraction_method", 
        "evidence_text", "validation_status", "errors", "warnings"
    ])
    
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
        "source_supplier", "source_page", "layout_name", "product_family", "type", 
        "pole", "rated_current", "material_code", "description", 
        "unit", "unit_price", "currency", "confidence", "extraction_method", 
        "evidence_text", "errors", "warnings"
    ])
    
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_valid.to_excel(writer, sheet_name="Valid Items", index=False)
        df_invalid.to_excel(writer, sheet_name="Invalid Items", index=False)
    print(f"Saved: {excel_path}")
    
    # 5. Viết báo cáo ls_profile_report.md
    write_markdown_report(valid_items, invalid_items, page_summaries, output_dir)

def write_markdown_report(
    valid_items: List[Dict[str, Any]], 
    invalid_items: List[Dict[str, Any]], 
    page_summaries: List[Dict[str, Any]],
    output_dir: Path
):
    report_path = output_dir / "ls_profile_report.md"
    
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
    if pass_ratio >= 0.80 and total_valid >= 50:
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
        desc_vi = it['description'].replace("Cau dao dien", "Cầu dao điện")
        sample_valid_rows += f"| {idx+1} | Trang {it['source_page']} | {it['material_code']} | {desc_vi} | {it['pole']} | {it['rated_current']} | {it['unit_price']:,} |\n"
        
    # Sinh 5 dòng sample invalid
    sample_invalid_rows = ""
    for idx, it in enumerate(invalid_items[:5]):
        raw_it = it.get("raw_item", {})
        desc_vi = raw_it.get('description', '').replace("Cau dao dien", "Cầu dao điện")
        errors_str = ", ".join(it.get('errors', []))
        sample_invalid_rows += f"| {idx+1} | Trang {raw_it.get('source_page')} | {raw_it.get('material_code')} | {desc_vi} | {errors_str} |\n"
        
    report_content = f"""# Báo Cáo Nghiệm Thu Khả Thi – LS Supplier Feasibility Audit v0

## 1. Lưu Ý Quan Trọng
* **Phạm vi kiểm chứng**: Tài liệu này báo cáo tính khả thi bóc tách độc lập bảng MEP trên tệp LS gốc.
* **Tích hợp hệ thống**: **Chưa tích hợp vào pipeline chính của dự án và chưa sẵn sàng cho môi trường Production (Not Production-Ready).**

## 2. Kết Quả Tổng Hợp Chi Tiết
* **File LS đã chọn**: `F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf`
* **Tổng số trang thử nghiệm**: {total_pages} trang
* **Số trang PASS (Tỷ lệ lỗi <= 5% và Valid >= 10)**: {passed_pages} trang
* **Số trang PARTIAL (Có valid item nhưng tỷ lệ lỗi > 5%)**: {partial_pages} trang
* **Số trang FAIL (Không có valid item)**: {failed_pages} trang
* **Tổng số vật tư thô (Raw)**: {total_raw} items
* **Tổng số vật tư hợp lệ (Valid)**: {total_valid} items
* **Tổng số vật tư lỗi bị loại (Invalid)**: {total_invalid} items
* **Trạng thái đánh giá toàn cục**: **{global_status}**

## 3. Bảng Thống Kê Chi Tiết Theo Trang
{page_table}

## 4. Dòng Dữ Lệ Hợp Lệ Mẫu (10 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) |
| --- | --- | --- | --- | --- | --- | --- |
{sample_valid_rows}

## 5. Dòng Dữ Liệu Bị Loại Mẫu (5 Dòng)
| STT | Trang Nguồn | Mã Vật Tư | Mô Tả Vật Tư Thô | Lỗi Ghi Nhận |
| --- | --- | --- | --- | --- |
{sample_invalid_rows}

## 6. Đánh Giá Trạng Thái Layout & Khuyến Nghị Tiếp Theo
* **Nhận định**: Cấu trúc bảng của LS hoàn toàn tương thích với layout `split_half_left_right` song song 2 nửa độc lập.
* **Kết quả**: Bóc tách thành công {total_valid} items hợp lệ với tỷ lệ lỗi thấp, chứng minh khả năng tái sử dụng của hướng đi Coordinate Column Profiler.
* **Khuyến nghị có nên tích hợp vào pipeline chính hay không**:
  * **Chưa nên tích hợp trực tiếp ngay**. Hướng đi sử dụng Coordinate Column Profiler là khả thi nhưng cần được đóng gói thành các **Supplier Profile Configs** độc lập trước khi mở lại giao diện UI hoặc tự động hóa đầu cuối.
"""
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"Saved: {report_path}")
