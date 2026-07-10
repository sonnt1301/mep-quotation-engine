import json
import datetime
import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Running Profile Bridge Dry-run...")
    
    manifest_path = Path("feasibility_outputs/profile_run_manifest/profile_run_manifest.json")
    if not manifest_path.exists():
        print(f"Error: Manifest not found at {manifest_path}. Please run manifest generator first.")
        sys.exit(1)
        
    manifest = load_json(manifest_path)
    
    bridged_items = []
    skipped_items = []
    suppliers_summary = []
    
    total_input_valid = 0
    total_bridged_count = 0
    total_skipped_count = 0
    
    # Duyệt qua từng supplier trong manifest
    for s in manifest.get("suppliers", []):
        supplier_code = s["supplier_code"]
        profile_status = s["profile_status"]
        valid_items_file = Path(s["output_files"]["valid_items_json"])
        
        # Chỉ include các supplier có status PASS hoặc ACCEPTED_WITH_KNOWN_LIMITATIONS
        included = profile_status in ["PASS", "ACCEPTED_WITH_KNOWN_LIMITATIONS"]
        inclusion_reason = ""
        warnings = []
        
        input_count = 0
        bridged_count = 0
        skipped_count = 0
        
        if not included:
            inclusion_reason = f"Supplier profile status is {profile_status}, not accepted for integration."
        else:
            inclusion_reason = f"Supplier profile status is {profile_status}, accepted with known limitations."
            if profile_status == "PASS":
                inclusion_reason = "Supplier profile status is PASS, fully accepted for integration."
                
            # Đọc các valid items trích xuất được
            if not valid_items_file.exists():
                warnings.append(f"Valid items output file not found at {valid_items_file}")
            else:
                items_data = load_json(valid_items_file)
                input_count = len(items_data)
                total_input_valid += input_count
                
                # Chuyển đổi từng item
                for idx, it in enumerate(items_data):
                    mat_code = it.get("material_code", "").strip()
                    unit_price = it.get("unit_price", 0)
                    desc = it.get("description", "").strip()
                    unit = it.get("unit", "cái").strip()
                    
                    # Kiểm tra các trường bắt buộc tối thiểu
                    skip_reason = []
                    if not mat_code:
                        skip_reason.append("material_code_empty")
                    if not desc:
                        skip_reason.append("description_empty")
                    if not isinstance(unit_price, int) or unit_price <= 0:
                        skip_reason.append("unit_price_must_be_positive_integer")
                        
                    # Thông tin truy vết nguồn gốc (provenance)
                    source_pdf_name = "original.pdf"
                    if supplier_code == "LS":
                        source_pdf_name = "Bang gia LS ap dung ngay 15-04-2026.pdf"
                    elif supplier_code == "CHINT":
                        source_pdf_name = "Bảng giá Chint 1-3-2023 ck 50.pdf"
                        
                    provenance = f"Source PDF: {source_pdf_name}, Page: {it.get('source_page')}, Layout: {it.get('layout_name')}, Method: {it.get('extraction_method')}"
                    
                    bridged_it = {
                        "supplier_code": supplier_code,
                        "source_page": it.get("source_page"),
                        "source_layout_name": it.get("layout_name"),
                        "source_material_code": it.get("material_code"),
                        "normalized_material_code": mat_code.upper(),
                        "description": desc,
                        "unit": unit,
                        "unit_price": int(unit_price),
                        "currency": "VND",
                        "product_family": it.get("product_family"),
                        "rated_current": it.get("rated_current"),
                        "breaking_capacity": it.get("breaking_capacity"),
                        "pole": it.get("pole"),
                        "source_extraction_method": it.get("extraction_method"),
                        "source_evidence_text": it.get("evidence_text"),
                        "provenance": provenance
                    }
                    
                    if skip_reason:
                        bridged_it["bridge_status"] = "skipped"
                        bridged_it["bridge_warnings"] = skip_reason
                        skipped_items.append(bridged_it)
                        skipped_count += 1
                    else:
                        bridged_it["bridge_status"] = "bridged"
                        bridged_it["bridge_warnings"] = []
                        bridged_items.append(bridged_it)
                        bridged_count += 1
                        
            # Ghi nhận warnings của LS/CHINT partial pages
            if supplier_code == "LS":
                warnings.append("LS Page 2 và Trang 5 ở trạng thái PARTIAL do dòng phụ kiện (accessories) chưa được gộp.")
            elif supplier_code == "CHINT":
                warnings.append("CHINT Page 5 ở trạng thái PARTIAL do số lượng sản phẩm ít hơn 10 dòng.")
                
        total_bridged_count += bridged_count
        total_skipped_count += skipped_count

        suppliers_summary.append({
            "supplier_code": supplier_code,
            "source_profile_status": profile_status,
            "included": included,
            "inclusion_reason": inclusion_reason,
            "input_valid_items_count": input_count,
            "bridged_items_count": bridged_count,
            "skipped_items_count": skipped_count,
            "warnings": warnings
        })
        
    # Tính toán các nhóm mã hàng bị trùng
    groups = {}
    for it in bridged_items:
        key = (it["supplier_code"], it["normalized_material_code"])
        if key not in groups:
            groups[key] = []
        groups[key].append(it["unit_price"])
        
    duplicate_code_group_count = 0
    duplicate_code_with_different_price_count = 0
    for key, prices in groups.items():
        if len(prices) > 1:
            duplicate_code_group_count += 1
            if len(set(prices)) > 1:
                duplicate_code_with_different_price_count += 1

    # 5. Xây dựng kết quả bridge tổng quát
    bridge_output = {
        "bridge_version": "1.0.0",
        "generated_at": datetime.datetime.now().isoformat() + "Z",
        "mode": "dry_run",
        "source_manifest": "feasibility_outputs/profile_run_manifest/profile_run_manifest.json",
        "bridge_status": "PASS" if total_skipped_count == 0 else "FAIL",
        "suppliers": suppliers_summary,
        "total_input_valid_items": total_input_valid,
        "total_bridged_items": total_bridged_count,
        "total_skipped_items": total_skipped_count,
        "duplicate_code_group_count": duplicate_code_group_count,
        "duplicate_code_with_different_price_count": duplicate_code_with_different_price_count,
        "integration_readiness": {
            "ready_for_write_to_main_pipeline": False,
            "reason": "Đây mới là phase Integration Bridge Dry-run (Chạy cầu nối khô). Toàn bộ dữ liệu chưa được phép ghi đè hay đẩy trực tiếp vào cơ sở dữ liệu hoặc main pipeline chính của dự án."
        },
        "output_files": {
            "bridged_items_json": "feasibility_outputs/profile_bridge_dry_run/profile_bridge_items.json",
            "bridge_summary_json": "feasibility_outputs/profile_bridge_dry_run/profile_bridge_summary.json",
            "bridge_report_md": "feasibility_outputs/profile_bridge_dry_run/profile_bridge_report.md"
        }
    }
    
    # Ghi tệp JSON kết quả chuyển đổi
    out_dir = Path("feasibility_outputs/profile_bridge_dry_run")
    save_json(out_dir / "profile_bridge_items.json", bridged_items)
    save_json(out_dir / "profile_bridge_summary.json", bridge_output)
    
    # 6. Xây dựng báo cáo Markdown cho người review
    md_content = f"""# Báo Cáo Chuyển Đổi Integration Bridge – Phase 2A (Dry-run)

Báo cáo này tổng hợp kết quả chạy thử nghiệm cầu nối tích hợp (Integration Bridge Dry-run) chuyển đổi dữ liệu từ lớp Feasibility sang schema trung gian chuẩn bị cho main pipeline.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Chuyển đổi khô (Dry-run Bridge)**.
> * **Không ghi dữ liệu vào main pipeline chính, không sửa đổi Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thông Tin Chung

* **Trạng Thái Cầu Nối**: `{bridge_output["bridge_status"]}`
* **Chế Độ Chạy**: `{bridge_output["mode"]}`
* **Thời Gian Khởi Tạo**: `{bridge_output["generated_at"]}`
* **Tổng Số Vật Tư Đầu Vào (Valid)**: {total_input_valid}
* **Tổng Số Vật Tư Chuyển Đổi Thành Công**: {total_bridged_count}
* **Tổng Số Vật Tư Bị Loại Bỏ (Skip)**: {total_skipped_count}

---

## 2. Kết Quả Theo Nhà Cung Cấp

| Nhà Cung Cấp | Trạng Thái Profile | Tích Hợp | Số Vật Tư Đầu Vào | Vật Tư Bridged | Vật Tư Skipped | Ghi Chú Cảnh Báo |
| --- | --- | --- | --- | --- | --- | --- |
"""
    for s in bridge_output["suppliers"]:
        inc_str = "YES" if s["included"] else "NO"
        warn_str = "; ".join(s["warnings"]) if s["warnings"] else "Không"
        md_content += f"| **{s['supplier_code']}** | `{s['source_profile_status']}` | **{inc_str}** | {s['input_valid_items_count']} | {s['bridged_items_count']} | {s['skipped_items_count']} | {warn_str} |\n"
        
    md_content += f"""
---

## 3. Đánh Giá Độ Sẵn Sàng Tích Hợp (Integration Readiness)

* **Sẵn sàng ghi trực tiếp vào main pipeline**: **`{str(bridge_output["integration_readiness"]["ready_for_write_to_main_pipeline"]).upper()}`**
* **Lý do**: {bridge_output["integration_readiness"]["reason"]}

---

## 4. Gợi Ý Các Bước Triển Khai Tiếp Theo

1. **Khảo sát chất lượng dry-run**: Đánh giá cấu trúc JSON trung gian đã đảm bảo đầy đủ thông tin xuất bản hay chưa.
2. **Phase 2B (Write Adapter)**: Sau khi dry-run hoạt động tốt, tiến hành thiết kế và phát triển mô-đun ghi adapter có kiểm soát, trước khi chính thức kết nối vào pipeline chính.
"""
    with open(out_dir / "profile_bridge_report.md", "w", encoding="utf-8") as f:
        f.write(md_content.strip())
        
    print(f"Bridge Items JSON saved at: {out_dir / 'profile_bridge_items.json'}")
    print(f"Bridge Summary JSON saved at: {out_dir / 'profile_bridge_summary.json'}")
    print(f"Bridge Report Markdown saved at: {out_dir / 'profile_bridge_report.md'}")
    print("Profile run bridge dry-run completed successfully.")

if __name__ == "__main__":
    main()
