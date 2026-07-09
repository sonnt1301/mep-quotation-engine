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

def detect_partial_pages(summary_path: Path) -> list:
    if not summary_path.exists():
        return []
    pages_data = load_json(summary_path)
    partials = []
    for p in pages_data:
        if p.get("status") == "PARTIAL":
            partials.append(p.get("page"))
    return sorted(partials)

def main():
    print("Generating Profile Run Manifest...")
    
    # 1. Đọc dữ liệu nghiệm thu tổng hợp
    accept_summary_path = Path("feasibility_outputs/benchmark_acceptance/benchmark_acceptance_summary.json")
    if not accept_summary_path.exists():
        print(f"Error: Acceptance summary not found at {accept_summary_path}. Please run benchmark acceptance first.")
        sys.exit(1)
    
    accept_summary = load_json(accept_summary_path)
    
    # 2. Quét động các trang partial
    ls_partials = detect_partial_pages(Path("feasibility_outputs/ls_profile_config_run/profile_page_summary.json"))
    chint_partials = detect_partial_pages(Path("feasibility_outputs/chint_profile_config_run/profile_page_summary.json"))
    abb_partials = detect_partial_pages(Path("feasibility_outputs/abb_profile_config_run/profile_page_summary.json"))
    
    # 3. Định nghĩa known limitations và hardening notes
    ls_limits = []
    if ls_partials:
        ls_limits.append(f"Trang {', '.join(map(str, ls_partials))} vẫn ở trạng thái PARTIAL và cần tiếp tục tinh chỉnh trong tương lai.")
    ls_limits.append("Các dòng phụ kiện (accessories) bị chồng lấn tọa độ với layout MCCB chính trên cùng layout split_half_left_right, chưa harden để tránh regression cho thiết bị chính.")
    
    chint_limits = []
    if chint_partials:
        chint_limits.append(f"Trang {', '.join(map(str, chint_partials))} vẫn ở trạng thái PARTIAL và cần tiếp tục tinh chỉnh trong tương lai.")
    chint_limits.append("Trang 5 rơ le nhiệt chỉ có 7 dòng thiết bị hợp lệ thực tế, thấp hơn ngưỡng PASS tối thiểu (10 dòng); không hạ tiêu chí threshold để làm đẹp báo cáo.")

    hardening_notes = {
        "ABB": "N/A - Bóc tách chính xác 100% các dòng dữ liệu thiết bị.",
        "LS": "Giữ nguyên known limitation cho phụ kiện MCCB (Trang 2) và phụ kiện ACB (Trang 5) để tránh regression cho thiết bị chính.",
        "CHINT": "Bổ sung bộ lọc tiêu đề rác tiếng Việt ('tiêu chuẩn:', 'định mức:', 'số pha:', 'đơn giá', 'iđm (a)', 'icu:') giúp nâng chất lượng Trang 3 từ PARTIAL lên PASS (0% lỗi)."
    }

    # 4. Xây dựng manifest JSON
    manifest = {
      "manifest_version": "1.0.0",
      "generated_at": datetime.datetime.now().isoformat() + "Z",
      "phase": "Feasibility Reset",
      "benchmark_status": accept_summary.get("benchmark_status", "FAIL"),
      "suppliers": [
        {
          "supplier_code": "ABB",
          "profile_status": accept_summary.get("abb", {}).get("status", "FAIL"),
          "valid_items_count": accept_summary.get("abb", {}).get("valid_items", 0),
          "invalid_items_count": accept_summary.get("abb", {}).get("invalid_items", 0),
          "pass_pages": accept_summary.get("abb", {}).get("pass_pages", 0),
          "partial_pages": accept_summary.get("abb", {}).get("partial_pages", 0),
          "total_pages": accept_summary.get("abb", {}).get("total_pages", 0),
          "known_limitations": accept_summary.get("abb", {}).get("known_limitations", []),
          "output_files": {
            "valid_items_json": "feasibility_outputs/abb_profile_config_run/profile_items_valid.json",
            "invalid_items_json": "feasibility_outputs/abb_profile_config_run/profile_items_invalid.json",
            "page_summary_json": "feasibility_outputs/abb_profile_config_run/profile_page_summary.json",
            "items_xlsx": "feasibility_outputs/abb_profile_config_run/profile_items.xlsx"
          },
          "source_profile_config": "tools/feasibility/profile_configs/abb_profile_v1.json",
          "acceptance_file": "feasibility_outputs/benchmark_acceptance/abb_acceptance.json",
          "hardening_notes": hardening_notes["ABB"]
        },
        {
          "supplier_code": "LS",
          "profile_status": accept_summary.get("ls", {}).get("status", "FAIL"),
          "valid_items_count": accept_summary.get("ls", {}).get("valid_items", 0),
          "invalid_items_count": accept_summary.get("ls", {}).get("invalid_items", 0),
          "pass_pages": accept_summary.get("ls", {}).get("pass_pages", 0),
          "partial_pages": accept_summary.get("ls", {}).get("partial_pages", 0),
          "total_pages": accept_summary.get("ls", {}).get("total_pages", 0),
          "known_limitations": ls_limits,
          "output_files": {
            "valid_items_json": "feasibility_outputs/ls_profile_config_run/profile_items_valid.json",
            "invalid_items_json": "feasibility_outputs/ls_profile_config_run/profile_items_invalid.json",
            "page_summary_json": "feasibility_outputs/ls_profile_config_run/profile_page_summary.json",
            "items_xlsx": "feasibility_outputs/ls_profile_config_run/profile_items.xlsx"
          },
          "source_profile_config": "tools/feasibility/profile_configs/ls_profile_v1.json",
          "acceptance_file": "feasibility_outputs/benchmark_acceptance/ls_acceptance.json",
          "hardening_notes": hardening_notes["LS"]
        },
        {
          "supplier_code": "CHINT",
          "profile_status": accept_summary.get("chint", {}).get("status", "FAIL"),
          "valid_items_count": accept_summary.get("chint", {}).get("valid_items", 0),
          "invalid_items_count": accept_summary.get("chint", {}).get("invalid_items", 0),
          "pass_pages": accept_summary.get("chint", {}).get("pass_pages", 0),
          "partial_pages": accept_summary.get("chint", {}).get("partial_pages", 0),
          "total_pages": accept_summary.get("chint", {}).get("total_pages", 0),
          "known_limitations": chint_limits,
          "output_files": {
            "valid_items_json": "feasibility_outputs/chint_profile_config_run/profile_items_valid.json",
            "invalid_items_json": "feasibility_outputs/chint_profile_config_run/profile_items_invalid.json",
            "page_summary_json": "feasibility_outputs/chint_profile_config_run/profile_page_summary.json",
            "items_xlsx": "feasibility_outputs/chint_profile_config_run/profile_items.xlsx"
          },
          "source_profile_config": "tools/feasibility/profile_configs/chint_profile_v1.json",
          "acceptance_file": "feasibility_outputs/benchmark_acceptance/chint_acceptance.json",
          "hardening_notes": hardening_notes["CHINT"]
        }
      ],
      "integration_readiness": {
        "ready_for_main_pipeline": False,
        "reason": "Vẫn còn các giới hạn đã biết (known limitations) về các trang PARTIAL (LS Trang 2 & 5, CHINT Trang 5) và chưa xây dựng/kiểm thử mô-đun cầu nối tích hợp (Integration Bridge).",
        "required_next_phase": "Thiết kế mô-đun cầu nối tích hợp (Integration Bridge) để chuyển đổi dữ liệu từ Coordinate Column Profiler sang pipeline chuẩn hóa chính, đồng thời tiếp tục tinh chỉnh layout nếu cần."
      },
      "non_goals": [
        "Không sửa đổi Streamlit UI trong phase hiện tại",
        "Không tích hợp trực tiếp vào main pipeline hiện tại khi chưa được kiểm thử",
        "Không bổ sung thêm nhà cung cấp mới",
        "Không sử dụng OCR, AI/LLM hay parse Excel",
        "Không tuyên bố hệ thống đã sẵn sàng vận hành thực tế (Not Ready for Production)"
      ]
    }

    # Ghi tệp JSON manifest
    out_dir = Path("feasibility_outputs/profile_run_manifest")
    save_json(out_dir / "profile_run_manifest.json", manifest)
    
    # 5. Xây dựng manifest Markdown
    md_content = f"""# Báo Cáo Profile Run Manifest – Milestone H

Báo cáo này tổng hợp kết quả chạy bóc tách (Profile Run Manifest) và đánh giá độ sẵn sàng tích hợp (Integration Readiness) cho cả ba nhà cung cấp **ABB**, **LS** và **CHINT**.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thông Tin Chung

* **Trạng Thái Benchmark**: `{manifest["benchmark_status"]}`
* **Thời Gian Khởi Tạo**: `{manifest["generated_at"]}`
* **Giai Đoạn Dự Án**: `{manifest["phase"]}`

---

## 2. Kết Quả Nghiệm Thu Chi Tiết Theo Nhà Cung Cấp

| Nhà Cung Cấp | Trạng Thái | Số Vật Tư Hợp Lệ | Số Vật Tư Bị Loại | Trang PASS | Trang PARTIAL | Tổng Số Trang |
| --- | --- | --- | --- | --- | --- | --- |
"""
    for s in manifest["suppliers"]:
        md_content += f"| **{s['supplier_code']}** | `{s['profile_status']}` | {s['valid_items_count']} | {s['invalid_items_count']} | {s['pass_pages']} | {s['partial_pages']} | {s['total_pages']} |\n"
        
    md_content += """
---

## 3. Các Giới Hạn Đã Biết (Known Limitations) & Ghi Chú Tinh Chỉnh

"""
    for s in manifest["suppliers"]:
        md_content += f"### Hãng {s['supplier_code']}\n"
        md_content += f"* **Tinh chỉnh chất lượng**: {s['hardening_notes']}\n"
        md_content += "* **Giới hạn kỹ thuật**:\n"
        if s["known_limitations"]:
            for lim in s["known_limitations"]:
                md_content += f"  * {lim}\n"
        else:
            md_content += "  * Không có giới hạn nghiêm trọng.\n"
        md_content += "\n"
        
    md_content += f"""---

## 4. Đánh Giá Độ Sẵn Sàng Tích Hợp (Integration Readiness)

* **Sẵn sàng tích hợp vào main pipeline**: **`{str(manifest["integration_readiness"]["ready_for_main_pipeline"]).upper()}`**
* **Lý do**: {manifest["integration_readiness"]["reason"]}
* **Công việc yêu cầu cho phase tiếp theo**: {manifest["integration_readiness"]["required_next_phase"]}

---

## 5. Danh Sách Không Thực Hiện Ở Giai Đoạn Này (Non-Goals)

"""
    for ng in manifest["non_goals"]:
        md_content += f"* {ng}\n"
        
    # Ghi tệp Markdown manifest
    with open(out_dir / "profile_run_manifest.md", "w", encoding="utf-8") as f:
        f.write(md_content.strip())
        
    print(f"Manifest JSON saved at: {out_dir / 'profile_run_manifest.json'}")
    print(f"Manifest Markdown saved at: {out_dir / 'profile_run_manifest.md'}")
    print("Profile run manifest generation completed successfully.")

if __name__ == "__main__":
    main()
