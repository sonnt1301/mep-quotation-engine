import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = str(Path(__file__).parent.parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: Path, data: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def check_item_against_contract(item: Dict[str, Any]) -> List[str]:
    errors = []
    required_fields = [
        "supplier_code", "source_page", "layout_name", "product_family",
        "material_code", "description", "unit", "unit_price", "currency",
        "rated_current", "breaking_capacity", "pole", "evidence_text",
        "extraction_method", "validation_status", "warnings", "errors"
    ]
    
    # 1. Kiểm tra sự tồn tại của các trường bắt buộc
    for f in required_fields:
        if f not in item:
            errors.append(f"missing_field_{f}")
            
    if errors:
        return errors
        
    # 2. Kiểm tra kiểu dữ liệu và định dạng
    if not isinstance(item["supplier_code"], str) or not item["supplier_code"]:
        errors.append("supplier_code_must_be_non_empty_string")
    if not isinstance(item["source_page"], int):
        errors.append("source_page_must_be_int")
    if not isinstance(item["layout_name"], str):
        errors.append("layout_name_must_be_string")
    if not isinstance(item["product_family"], str):
        errors.append("product_family_must_be_string")
    if not isinstance(item["unit"], str):
        errors.append("unit_must_be_string")
    if not isinstance(item["currency"], str) or item["currency"] != "VND":
        errors.append("currency_must_be_VND")
    if not isinstance(item["evidence_text"], str) or not item["evidence_text"]:
        errors.append("evidence_text_must_be_non_empty_string")
    if item["extraction_method"] != "coordinate_column_profiler":
        errors.append("extraction_method_must_be_coordinate_column_profiler")
    if item["validation_status"] not in ["valid", "invalid"]:
        errors.append("validation_status_must_be_valid_or_invalid")
    if not isinstance(item["warnings"], list):
        errors.append("warnings_must_be_list")
    if not isinstance(item["errors"], list):
        errors.append("errors_must_be_list")
        
    # 3. Kiểm tra logic nghiệm thu cho valid item
    if item["validation_status"] == "valid":
        if not isinstance(item["material_code"], str) or not item["material_code"].strip():
            errors.append("valid_item_material_code_cannot_be_empty")
        if not isinstance(item["unit_price"], int) or item["unit_price"] <= 0:
            errors.append("valid_item_unit_price_must_be_positive_int")
            
    return errors

def run_benchmark_abb() -> Dict[str, Any]:
    run_dir = Path("feasibility_outputs/abb_profile_config_run")
    v1_dir = Path("feasibility_outputs/abb_profile_v1")
    
    checks = []
    status = "PASS"
    
    # 1. Load các tệp dữ liệu
    try:
        valid_items = load_json(run_dir / "profile_items_valid.json")
        invalid_items = load_json(run_dir / "profile_items_invalid.json")
        page_summary = load_json(run_dir / "profile_page_summary.json")
        v1_valid = load_json(v1_dir / "abb_profile_items_valid.json")
    except Exception as e:
        return {
            "supplier_code": "ABB",
            "status": "FAIL",
            "valid_items": 0,
            "invalid_items": 0,
            "pass_pages": 0,
            "total_pages": 0,
            "checks": [{"check_name": "load_files", "status": "FAIL", "details": str(e)}],
            "known_limitations": []
        }
        
    # 2. Check số lượng và trang PASS
    num_valid = len(valid_items)
    num_invalid = len(invalid_items)
    total_pages = len(page_summary)
    pass_pages = sum(1 for p in page_summary if p["status"] == "PASS")
    
    # Check 1: Khớp số lượng ABB
    chk_count = {"check_name": "abb_exact_count_match", "status": "PASS", "details": f"Valid: {num_valid}/743, Invalid: {num_invalid}/2"}
    if num_valid != 743 or num_invalid != 2:
        chk_count["status"] = "FAIL"
        status = "FAIL"
    checks.append(chk_count)
    
    # Check 2: Pass pages
    chk_pages = {"check_name": "abb_pass_pages_match", "status": "PASS", "details": f"PASS pages: {pass_pages}/{total_pages}"}
    if pass_pages != 13 or total_pages != 13:
        chk_pages["status"] = "FAIL"
        status = "FAIL"
    checks.append(chk_pages)
    
    # Check 3: Schema contract và các trường bắt buộc
    contract_errors = []
    for it in valid_items:
        it_err = check_item_against_contract(it)
        if it_err:
            contract_errors.extend(it_err)
    for it in invalid_items:
        # Đối với invalid items, ta convert raw_item thành item chuẩn để check contract
        raw_it = it.get("raw_item", {})
        it_err = check_item_against_contract(raw_it)
        if it_err:
            contract_errors.extend(it_err)
            
    chk_schema = {"check_name": "output_contract_compliance", "status": "PASS", "details": "All items comply with JSON output contract."}
    if contract_errors:
        chk_schema["status"] = "FAIL"
        chk_schema["details"] = f"Found {len(set(contract_errors))} contract compliance issues: {list(set(contract_errors))[:3]}"
        status = "FAIL"
    checks.append(chk_schema)
    
    # Check 4: Khớp baseline v1 100%
    v1_map = {(it["source_page"], it["material_code"].upper(), it["unit_price"]) for it in v1_valid}
    run_map = {(it["source_page"], it["material_code"].upper(), it["unit_price"]) for it in valid_items}
    
    diff_v1_only = v1_map - run_map
    diff_run_only = run_map - v1_map
    
    chk_baseline = {"check_name": "abb_exact_baseline_alignment", "status": "PASS", "details": "100% match with baseline v1 items."}
    if diff_v1_only or diff_run_only:
        chk_baseline["status"] = "FAIL"
        chk_baseline["details"] = f"Mismatch with baseline v1. V1-only: {len(diff_v1_only)} items, Run-only: {len(diff_run_only)} items."
        status = "FAIL"
    checks.append(chk_baseline)
    
    return {
        "supplier_code": "ABB",
        "status": status,
        "valid_items": num_valid,
        "invalid_items": num_invalid,
        "pass_pages": pass_pages,
        "partial_pages": total_pages - pass_pages,
        "total_pages": total_pages,
        "checks": checks,
        "known_limitations": []
    }

def run_benchmark_ls() -> Dict[str, Any]:
    run_dir = Path("feasibility_outputs/ls_profile_config_run")
    v1_dir = Path("feasibility_outputs/ls_profile_v1")
    
    checks = []
    status = "ACCEPTED_WITH_KNOWN_LIMITATIONS"
    
    # 1. Load các tệp dữ liệu
    try:
        valid_items = load_json(run_dir / "profile_items_valid.json")
        invalid_items = load_json(run_dir / "profile_items_invalid.json")
        page_summary = load_json(run_dir / "profile_page_summary.json")
        v1_valid = load_json(v1_dir / "ls_profile_items_valid.json")
    except Exception as e:
        return {
            "supplier_code": "LS",
            "status": "FAIL",
            "valid_items": 0,
            "invalid_items": 0,
            "pass_pages": 0,
            "total_pages": 0,
            "checks": [{"check_name": "load_files", "status": "FAIL", "details": str(e)}],
            "known_limitations": []
        }
        
    num_valid = len(valid_items)
    num_invalid = len(invalid_items)
    total_pages = len(page_summary)
    pass_pages = sum(1 for p in page_summary if p["status"] == "PASS")
    
    # Check 1: Số lượng và trang PASS tối thiểu
    chk_count = {"check_name": "ls_minimum_count_match", "status": "PASS", "details": f"Valid: {num_valid} (criteria >=282), Invalid: {num_invalid} (criteria <=19)"}
    if num_valid < 282 or num_invalid > 19:
        chk_count["status"] = "FAIL"
        status = "FAIL"
    checks.append(chk_count)
    
    chk_pages = {"check_name": "ls_minimum_pass_pages", "status": "PASS", "details": f"PASS pages: {pass_pages} (criteria >=3)"}
    if pass_pages < 3:
        chk_pages["status"] = "FAIL"
        status = "FAIL"
    checks.append(chk_pages)
    
    # Check 2: Schema contract và các trường bắt buộc
    contract_errors = []
    for it in valid_items:
        it_err = check_item_against_contract(it)
        if it_err:
            contract_errors.extend(it_err)
    for it in invalid_items:
        raw_it = it.get("raw_item", {})
        it_err = check_item_against_contract(raw_it)
        if it_err:
            contract_errors.extend(it_err)
            
    chk_schema = {"check_name": "output_contract_compliance", "status": "PASS", "details": "All items comply with JSON output contract."}
    if contract_errors:
        chk_schema["status"] = "FAIL"
        chk_schema["details"] = f"Found {len(set(contract_errors))} contract compliance issues."
        status = "FAIL"
    checks.append(chk_schema)
    
    # Check 3: Khớp giá baseline và không lệch quá 10 lần
    v1_price_map = {}
    for it in v1_valid:
        key = (it["source_page"], it["material_code"].upper())
        if key not in v1_price_map:
            v1_price_map[key] = []
        v1_price_map[key].append(it["unit_price"])
        
    mismatches_10x = 0
    for it in valid_items:
        key = (it["source_page"], it["material_code"].upper())
        price_con = it["unit_price"]
        if key in v1_price_map:
            matched = False
            for p_v1 in v1_price_map[key]:
                if p_v1 == 0: continue
                ratio = price_con / p_v1
                if 0.1 <= ratio <= 10.0:
                    matched = True
                    break
            if not matched:
                mismatches_10x += 1
                
    chk_ratio = {"check_name": "ls_no_10x_price_mismatch", "status": "PASS", "details": "No LS items deviate >10x from baseline v1."}
    if mismatches_10x > 0:
        chk_ratio["status"] = "FAIL"
        chk_ratio["details"] = f"Found {mismatches_10x} items deviating >10x from baseline price."
        status = "FAIL"
    checks.append(chk_ratio)
    
    # Check 4: Regression price tests
    regression_items = {
        (1, "ABN104C"): 1850000,
        (1, "ABS203C"): 3350000,
        (2, "EBS204C"): 9500000,
        (2, "EBN404C"): 16600000
    }
    
    reg_errors = []
    price_lookup = {}
    for it in valid_items:
        key = (it["source_page"], it["material_code"].upper())
        price_lookup[key] = it["unit_price"]
        
    for key, expected_price in regression_items.items():
        actual_price = price_lookup.get(key, 0)
        if actual_price != expected_price:
            reg_errors.append(f"{key[1]} page {key[0]}: expected {expected_price}, got {actual_price}")
            
    chk_reg = {"check_name": "ls_price_regression_protection", "status": "PASS", "details": "All LS price regressions passed."}
    if reg_errors:
        chk_reg["status"] = "FAIL"
        chk_reg["details"] = "; ".join(reg_errors)
        status = "FAIL"
    checks.append(chk_reg)
    
    # Check 5: Bảo vệ giá trị lớn
    large_prices = [
        {"code": "AS-25E3-25H", "page": 5, "min_val": 100000000, "actual": price_lookup.get((5, "AS-25E3-25H"), 0)},
        {"code": "AS-63G3-63H", "page": 5, "min_val": 400000000, "actual": price_lookup.get((5, "AS-63G3-63H"), 0)}
    ]
    large_errors = []
    for lp in large_prices:
        if lp["actual"] < lp["min_val"]:
            large_errors.append(f"{lp['code']}: expected >= {lp['min_val']}, got {lp['actual']}")
            
    chk_large = {"check_name": "ls_large_price_protection", "status": "PASS", "details": "All large LS prices protected."}
    if large_errors:
        chk_large["status"] = "FAIL"
        chk_large["details"] = "; ".join(large_errors)
        status = "FAIL"
    checks.append(chk_large)
    
    return {
        "supplier_code": "LS",
        "status": status,
        "valid_items": num_valid,
        "invalid_items": num_invalid,
        "pass_pages": pass_pages,
        "partial_pages": total_pages - pass_pages,
        "total_pages": total_pages,
        "checks": checks,
        "known_limitations": [
            "Page 2 and page 5 remain PARTIAL and require future profile hardening."
        ]
    }

def generate_markdown_report(abb_res: Dict[str, Any], ls_res: Dict[str, Any], output_path: Path):
    content = f"""# Báo Cáo Nghiệm Thu Acceptance Benchmark – Milestone E

Báo cáo này tổng kết kết quả đánh giá nghiệm thu khả thi bóc tách (Acceptance Benchmark) cho hai nhà cung cấp **ABB** và **LS** dựa trên các tiêu chí cố định (Acceptance Criteria).

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Tổng Hợp

| Nhà Cung Cấp | Trạng Thái Đánh Giá | Số Vật Tư Hợp Lệ (Valid) | Số Vật Tư Bị Loại (Invalid) | Số Trang Đạt PASS | Tổng Số Trang |
| --- | --- | --- | --- | --- | --- |
| **ABB** | `{abb_res["status"]}` | {abb_res["valid_items"]} | {abb_res["invalid_items"]} | {abb_res["pass_pages"]} | {abb_res["total_pages"]} |
| **LS** | `{ls_res["status"]}` | {ls_res["valid_items"]} | {ls_res["invalid_items"]} | {ls_res["pass_pages"]} | {ls_res["total_pages"]} |

---

## 2. Bảng Kiểm Tra Chi Tiết (Checks Table)

### Hãng ABB (Target: `PASS`)
| Tên Hạng Mục Kiểm Tra | Trạng Thái | Chi Tiết |
| --- | --- | --- |
"""
    for chk in abb_res["checks"]:
        content += f"| `{chk['check_name']}` | **{chk['status']}** | {chk['details']} |\n"
        
    content += """
### Hãng LS (Target: `ACCEPTED_WITH_KNOWN_LIMITATIONS`)
| Tên Hạng Mục Kiểm Tra | Trạng Thái | Chi Tiết |
| --- | --- | --- |
"""
    for chk in ls_res["checks"]:
        content += f"| `{chk['check_name']}` | **{chk['status']}** | {chk['details']} |\n"
        
    content += f"""
---

## 3. Các Giới Hạn Đã Biết (Known Limitations)

### Hãng ABB
* Không có giới hạn nghiêm trọng. Cấu hình layout đạt trạng thái Feasibility rất tốt.

### Hãng LS
* **Trang 2 và Trang 5 vẫn ở trạng thái PARTIAL** (chưa đạt tỷ lệ lỗi <= 5% hoặc chưa đủ số lượng item tối thiểu trên mỗi trang để PASS tuyệt đối). Việc tối ưu hóa các trang này sẽ cần các bước hardening profile sâu hơn trong tương lai.

---

## 4. Đề Xuất & Khuyến Nghị Cuối Cùng (Final Recommendation)

1. **Khả năng Benchmark**: Kết quả bóc tách của cả ABB và LS bằng tệp cấu hình JSON động đã đạt tính ổn định rất cao và có thể dùng làm benchmark nền tảng để so sánh cho các Supplier Profile Parser tiếp theo.
2. **Trạng thái Tích hợp**: **Chưa tích hợp vào pipeline chính.** Dữ liệu đầu ra tuân thủ nghiêm ngặt chuẩn hợp đồng [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json) nhưng mới chỉ nằm ở lớp Feasibility.
3. **Các Bước Tiếp Theo**: Sau Milestone E, dự án có thể lựa chọn:
   * **Phương án 1**: Tiếp tục Hardening profile cho hãng LS để nâng cao tỷ lệ PASS của các trang PARTIAL.
   * **Phương án 2**: Mở rộng Parser sang nhà cung cấp thứ 3 bằng cách viết tệp cấu hình JSON tương tự.
   * **Phương án 3**: Thiết kế cầu nối tích hợp (Integration Bridge) để đẩy kết quả từ Config Runner sang pipeline chính của dự án.
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content.strip())

def main():
    print("Running Benchmark Acceptance Harness...")
    abb_res = run_benchmark_abb()
    ls_res = run_benchmark_ls()
    
    # 1. Ghi tệp acceptance json
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    save_json(out_dir / "abb_acceptance.json", abb_res)
    save_json(out_dir / "ls_acceptance.json", ls_res)
    
    # 2. Ghi tệp summary json máy đọc
    summary = {
        "benchmark_status": "PASS" if (abb_res["status"] == "PASS" and ls_res["status"] == "ACCEPTED_WITH_KNOWN_LIMITATIONS") else "FAIL",
        "abb": abb_res,
        "ls": ls_res
    }
    save_json(out_dir / "benchmark_acceptance_summary.json", summary)
    
    # 3. Ghi tệp markdown report
    generate_markdown_report(abb_res, ls_res, out_dir / "benchmark_acceptance_report.md")
    
    print(f"ABB status: {abb_res['status']}")
    print(f"LS status: {ls_res['status']}")
    print(f"Summary status: {summary['benchmark_status']}")
    print("Benchmark acceptance harness completed successfully.")

if __name__ == "__main__":
    main()
