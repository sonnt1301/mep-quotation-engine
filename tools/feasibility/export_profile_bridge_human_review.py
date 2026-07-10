import json
import csv
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
    print("Generating Human Review Package...")
    
    items_path = Path("feasibility_outputs/profile_bridge_dry_run/profile_bridge_items.json")
    summary_path = Path("feasibility_outputs/profile_bridge_dry_run/profile_bridge_summary.json")
    
    if not items_path.exists() or not summary_path.exists():
        print("Error: Bridge outputs not found. Please run bridge dry-run first.")
        sys.exit(1)
        
    items = load_json(items_path)
    summary = load_json(summary_path)
    
    out_dir = Path("feasibility_outputs/profile_bridge_human_review")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------
    # 1. Tạo file duplicate review: profile_bridge_duplicate_code_review.csv
    # ----------------------------------------------------
    groups = {}
    for it in items:
        key = (it["supplier_code"], it["normalized_material_code"])
        if key not in groups:
            groups[key] = []
        groups[key].append(it)
        
    dup_rows = []
    for (supplier, code), group_items in groups.items():
        if len(group_items) > 1:
            occurrence_count = len(group_items)
            prices = sorted(list(set(it["unit_price"] for it in group_items)))
            distinct_price_count = len(prices)
            pages = sorted(list(set(it["source_page"] for it in group_items)))
            descriptions = [it["description"] for it in group_items]
            evidences = [it["source_evidence_text"] for it in group_items]
            
            # Phân loại risk level
            if distinct_price_count > 1:
                risk_level = "HIGH"
            elif len(set(descriptions)) > 1 or len(set(pages)) > 1:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
                
            # Gợi ý khóa duy nhất (write key) để ghi nhận
            recommended_write_key = "supplier_code + normalized_material_code"
            if risk_level == "HIGH":
                recommended_write_key += " + source_page + unit_price + description"
            elif risk_level == "MEDIUM":
                recommended_write_key += " + source_page + description"
                
            dup_rows.append({
                "supplier_code": supplier,
                "normalized_material_code": code,
                "occurrence_count": occurrence_count,
                "distinct_price_count": distinct_price_count,
                "prices": "; ".join(map(str, prices)),
                "source_pages": "; ".join(map(str, pages)),
                "descriptions_sample": " | ".join(list(set(descriptions))[:3]),
                "evidence_sample": " | ".join(list(set(evidences))[:2]),
                "risk_level": risk_level,
                "recommended_write_key": recommended_write_key,
                "human_decision": "PENDING",
                "human_note": ""
            })
            
    # Sắp xếp duplicate groups theo risk level HIGH -> MEDIUM -> LOW
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    dup_rows.sort(key=lambda x: (risk_order[x["risk_level"]], x["supplier_code"], x["normalized_material_code"]))
    
    dup_headers = [
        "supplier_code", "normalized_material_code", "occurrence_count", 
        "distinct_price_count", "prices", "source_pages", "descriptions_sample", 
        "evidence_sample", "risk_level", "recommended_write_key", "human_decision", "human_note"
    ]
    
    dup_csv_path = out_dir / "profile_bridge_duplicate_code_review.csv"
    with open(dup_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dup_headers)
        writer.writeheader()
        writer.writerows(dup_rows)
        
    # ----------------------------------------------------
    # 2. Tạo file sample review: profile_bridge_review_sample.csv
    # ----------------------------------------------------
    # Chúng ta gom chọn lọc có chủ đích khoảng 60-80 dòng
    sample_items = []
    seen_ids = set()
    
    def add_to_sample(it, group_name, question, action):
        item_id = (it["supplier_code"], it["normalized_material_code"], it["source_page"], it["unit_price"])
        if item_id not in seen_ids:
            seen_ids.add(item_id)
            sample_items.append({
                "review_group": group_name,
                "supplier_code": it["supplier_code"],
                "source_page": it["source_page"],
                "normalized_material_code": it["normalized_material_code"],
                "description": it["description"],
                "unit": it["unit"],
                "unit_price": it["unit_price"],
                "currency": it["currency"],
                "product_family": it["product_family"],
                "rated_current": it["rated_current"],
                "breaking_capacity": it["breaking_capacity"],
                "pole": it["pole"],
                "source_evidence_text": it["source_evidence_text"],
                "provenance": it["provenance"],
                "review_question": question,
                "suggested_review_action": action,
                "human_decision": "PENDING",
                "human_note": ""
            })
            
    # Điều kiện A: LS Page 2 và LS Page 5 (known limitations của LS)
    count_ls_p2 = 0
    count_ls_p5 = 0
    for it in items:
        if it["supplier_code"] == "LS":
            if it["source_page"] == 2 and count_ls_p2 < 10:
                add_to_sample(it, "LS_PAGE_LIMITATION", 
                              "Kiểm tra xem mã phụ kiện và tên mô tả phụ kiện có bị cắt dính chữ không?", 
                              "Đối chiếu với bản cứng PDF Trang 2")
                count_ls_p2 += 1
            elif it["source_page"] == 5 and count_ls_p5 < 10:
                add_to_sample(it, "LS_PAGE_LIMITATION", 
                              "Kiểm tra xem mã phụ kiện và tên mô tả phụ kiện có bị cắt dính chữ không?", 
                              "Đối chiếu với bản cứng PDF Trang 5")
                count_ls_p5 += 1
            
    # Điều kiện B: CHINT Page 3 và CHINT Page 5 (known limitations và hardening của Chint)
    count_chint_p3 = 0
    count_chint_p5 = 0
    for it in items:
        if it["supplier_code"] == "CHINT":
            if it["source_page"] == 3 and count_chint_p3 < 10:
                add_to_sample(it, "CHINT_PAGE_LIMITATION", 
                              "Kiểm tra xem dòng bóc tách thiết bị rơ le hoặc MCCB đã đúng thông số chưa?", 
                              "Đối chiếu với bản cứng PDF Trang 3")
                count_chint_p3 += 1
            elif it["source_page"] == 5 and count_chint_p5 < 10:
                add_to_sample(it, "CHINT_PAGE_LIMITATION", 
                              "Kiểm tra xem dòng bóc tách thiết bị rơ le hoặc MCCB đã đúng thông số chưa?", 
                              "Đối chiếu với bản cứng PDF Trang 5")
                count_chint_p5 += 1
            
    # Điều kiện C: Các dòng ABB giá lớn (ACB Emax2)
    count_abb_large = 0
    for it in items:
        if it["supplier_code"] == "ABB" and it["unit_price"] >= 10000000 and count_abb_large < 10:
            add_to_sample(it, "ABB_LARGE_PRICE", 
                          "Kiểm tra xem giá trị tiền hàng tỷ lệ lớn của ACB Emax2 có chính xác?", 
                          "Xác minh đơn vị tiền tệ và số chữ số không.")
            count_abb_large += 1
            
    # Điều kiện D: LS regression/protection
    ls_reg_codes = ["ABN104C", "ABS203C", "EBS204C", "EBN404C", "AS-25E3-25H", "AS-63G3-63H"]
    for it in items:
        if it["supplier_code"] == "LS" and it["normalized_material_code"] in ls_reg_codes:
            add_to_sample(it, "LS_REGRESSION_PROTECTION", 
                          "Kiểm tra xem đơn giá của thiết bị chính có bị dính ampere list hay không?", 
                          "Xác nhận đơn giá đúng baseline.")
            
    # Điều kiện E: CHINT specific items
    chint_specifics = ["NXM-63S", "NM1-125C", "NXR-25", "F5-D2"]
    count_chint_spec = 0
    for it in items:
        if it["supplier_code"] == "CHINT" and any(x in it["normalized_material_code"] for x in chint_specifics) and count_chint_spec < 10:
            add_to_sample(it, "CHINT_SPECIFIC", 
                          "Kiểm tra xem mã hàng Chint chuẩn hóa đã chính xác chưa?", 
                          "Xác minh tiền tố/hậu tố cấu hình.")
            count_chint_spec += 1
            
    # Điều kiện F: Các nhóm trùng mã nhưng khác giá (HIGH risk)
    # Lấy đại diện 2 dòng cho mỗi nhóm trùng mã khác giá
    high_risk_keys = [ (r["supplier_code"], r["normalized_material_code"]) for r in dup_rows if r["risk_level"] == "HIGH" ]
    for supplier, code in high_risk_keys[:10]: # Giới hạn 10 nhóm đầu để tránh phình to sample
        group_its = [ it for it in items if it["supplier_code"] == supplier and it["normalized_material_code"] == code ]
        for it in group_its[:2]:
            add_to_sample(it, "DUPLICATE_CODE_DIFFERENT_PRICE", 
                          "Mã hàng trùng nhưng có nhiều giá khác nhau. Xác minh xem đây là phụ kiện khác loại hay do phân trang?", 
                          "So sánh description và evidence của các dòng trùng.")
            
    # Thêm một số dòng ABB thường để đảm bảo phân bổ mẫu cân đối nếu cần
    for it in items:
        if len(sample_items) >= 72:
            break
        if it["supplier_code"] == "ABB" and it["unit_price"] < 1000000:
            add_to_sample(it, "ABB_NORMAL_PRICE", 
                          "Kiểm tra dòng bóc tách thông thường của ABB.", 
                          "Xác minh mô tả thiết bị.")

    sample_headers = [
        "review_group", "supplier_code", "source_page", "normalized_material_code",
        "description", "unit", "unit_price", "currency", "product_family",
        "rated_current", "breaking_capacity", "pole", "source_evidence_text",
        "provenance", "review_question", "suggested_review_action", "human_decision", "human_note"
    ]
    
    sample_csv_path = out_dir / "profile_bridge_review_sample.csv"
    with open(sample_csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_headers)
        writer.writeheader()
        writer.writerows(sample_items)
        
    # ----------------------------------------------------
    # 3. Tạo checklist human review: profile_bridge_human_review_checklist.md
    # ----------------------------------------------------
    checklist_content = f"""# Quy Trình & Checklist Human Review – Phase 2A.1

Tài liệu này hướng dẫn người đánh giá (Human Reviewer) thực hiện kiểm định chất lượng dữ liệu bóc tách được chuyển đổi qua mô hình cầu nối Integration Bridge trước khi xây dựng Write Adapter.

---

> [!WARNING]
> **PHẠM VI REVIEW**
> * Dữ liệu bóc tách phục vụ phase khảo sát khả thi (Feasibility Reset), chưa tích hợp vào pipeline chính.
> * **Không sửa Streamlit UI, không ghi đè cơ sở dữ liệu thực.**

---

## 1. Hướng Dẫn Đọc Các Tệp Đánh Giá

* **Tệp mẫu review**: [profile_bridge_review_sample.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_review_sample.csv) chứa {len(sample_items)} dòng mẫu đại diện cho các trường hợp đặc thù, giá lớn, rủi ro trùng lặp hoặc known limitations của ABB, LS, CHINT.
* **Tệp đánh giá mã trùng**: [profile_bridge_duplicate_code_review.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_duplicate_code_review.csv) liệt kê toàn bộ các nhóm trùng mã hàng trên cùng nhà cung cấp và phân loại rủi ro (HIGH / MEDIUM / LOW).

---

## 2. Tiêu Chí Đánh Dấu Quyết Định (human_decision)

Người review điền vào cột `human_decision` một trong các giá trị sau:
1. **`APPROVE`**: Dòng bóc tách chính xác hoàn toàn về mã hàng, đơn giá, đơn vị tính.
2. **`REJECT`**: Dòng bóc tách sai lệch nghiêm trọng không thể sử dụng.
3. **`NEEDS_INVESTIGATION`**: Dòng nghi ngờ sai lệch, cần lập trình viên kiểm tra lại cấu hình tọa độ cột.
4. **`ACCEPT_WITH_LIMITATION`**: Dòng bóc tách chấp nhận được dù chưa tối ưu (ví dụ: dòng phụ kiện bị dính từ mô tả ngắn ở đầu).

---

## 3. Checklist Các Điểm Cần Kiểm Tra

- [ ] **Mã vật tư chuẩn hóa (`normalized_material_code`)**: Có bị cắt dính chữ hay thiếu ký tự quan trọng không? (Đặc biệt xem nhóm `LS_PAGE_LIMITATION`).
- [ ] **Đơn giá (`unit_price`)**: Đơn giá có đúng thực tế không? Có bị dính dòng định mức ampere list hay ghép sai cột không? (Đặc biệt xem nhóm `LS_REGRESSION_PROTECTION`).
- [ ] **Mã trùng nhiều giá (`DUPLICATE_CODE_DIFFERENT_PRICE`)**: Nhóm rủi ro HIGH này có thực sự là các phụ kiện khác dòng hay là lỗi phân trang? Khóa ghi dữ liệu đề xuất (`recommended_write_key`) đã đủ phân biệt để tránh ghi đè đè giá của nhau chưa?
- [ ] **Thông tin truy vết (`provenance`)**: Nguồn gốc PDF, số trang, layout có rõ ràng và chính xác không?

---

## 4. Điều Kiện Chốt Để Triển Khai Tiếp

* **ĐẠT (PASS)**: Nếu tệp sample review đạt tỷ lệ duyệt (`APPROVE` hoặc `ACCEPT_WITH_LIMITATION`) `>= 95%` và không có lỗi blocker rủi ro HIGH nào trong tệp duplicate review chưa được xử lý $\rightarrow$ Cho phép chuyển sang thiết kế **Phase 2B Write Adapter**.
* **KHÔNG ĐẠT (FAIL)**: Quay lại tinh chỉnh cấu hình layout profile hoặc lọc dữ liệu rác của Integration Bridge.
"""
    with open(out_dir / "profile_bridge_human_review_checklist.md", "w", encoding="utf-8") as f:
        f.write(checklist_content.strip())
        
    # ----------------------------------------------------
    # 4. Tạo summary human review: JSON & Markdown
    # ----------------------------------------------------
    high_risk_count = sum(1 for r in dup_rows if r["risk_level"] == "HIGH")
    medium_risk_count = sum(1 for r in dup_rows if r["risk_level"] == "MEDIUM")
    low_risk_count = sum(1 for r in dup_rows if r["risk_level"] == "LOW")
    
    review_summary = {
        "total_bridged_items": len(items),
        "total_sample_rows": len(sample_items),
        "total_duplicate_code_groups": len(dup_rows),
        "duplicate_groups_by_risk": {
            "HIGH": high_risk_count,
            "MEDIUM": medium_risk_count,
            "LOW": low_risk_count
        },
        "known_limitations": summary.get("suppliers", []),
        "proposed_status": "READY_FOR_HUMAN_REVIEW",
        "ready_for_write_to_main_pipeline": False
    }
    
    save_json(out_dir / "profile_bridge_human_review_summary.json", review_summary)
    
    summary_md = f"""# Summary Human Review Package – Phase 2A.1

Báo cáo tóm tắt gói tài liệu Human Review phục vụ đánh giá chất lượng cầu nối dữ liệu Integration Bridge.

---

## 1. Số Liệu Thống Kê Tổng Quan

* **Tổng Số Vật Tư Đã Bridged**: {review_summary["total_bridged_items"]} dòng thiết bị
* **Tổng Số Vật Tư Được Lấy Mẫu (Sample)**: {review_summary["total_sample_rows"]} dòng đại diện
* **Tổng Số Nhóm Mã Trùng (Duplicate Code Groups)**: {review_summary["total_duplicate_code_groups"]} nhóm
  * Nhóm rủi ro **HIGH** (Trùng mã hàng nhưng khác đơn giá): **{high_risk_count}** nhóm
  * Nhóm rủi ro **MEDIUM** (Trùng mã hàng cùng giá nhưng khác trang/mô tả): **{medium_risk_count}** nhóm
  * Nhóm rủi ro **LOW** (Trùng hoàn toàn): **{low_risk_count}** nhóm

---

## 2. Đánh Giá Độ Sẵn Sàng Tích Hợp (Integration Readiness)

* **Trạng thái đề xuất**: **`READY_FOR_HUMAN_REVIEW`**
* **Sẵn sàng ghi trực tiếp vào main pipeline**: **`FALSE`**
* **Lưu ý kỹ thuật**: Cần hoàn tất quy trình phê duyệt thủ công (Human Review) trên tệp CSV mẫu và chốt phương án khóa ghi dữ liệu để tránh ghi đè giá trị của các mã trùng rủi ro HIGH trước khi bắt đầu Phase 2B.

---

## 3. Danh Sách Tệp Tài Liệu Đóng Gói

1. Tệp CSV mẫu review: [profile_bridge_review_sample.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_review_sample.csv)
2. Tệp CSV đánh giá mã trùng: [profile_bridge_duplicate_code_review.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_duplicate_code_review.csv)
3. Hướng dẫn & Checklist review: [profile_bridge_human_review_checklist.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_human_review_checklist.md)
"""
    with open(out_dir / "profile_bridge_human_review_summary.md", "w", encoding="utf-8") as f:
        f.write(summary_md.strip())
        
    print(f"Duplicate CSV saved at: {dup_csv_path}")
    print(f"Sample CSV saved at: {sample_csv_path}")
    print(f"Checklist MD saved at: {out_dir / 'profile_bridge_human_review_checklist.md'}")
    print(f"Summary JSON saved at: {out_dir / 'profile_bridge_human_review_summary.json'}")
    print(f"Summary MD saved at: {out_dir / 'profile_bridge_human_review_summary.md'}")
    print("Human review package generation completed successfully.")

if __name__ == "__main__":
    main()
