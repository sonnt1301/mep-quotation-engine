import json
import pytest
import sys
import subprocess
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def test_bridge_dry_run_execution():
    # 1. Chạy script bridge dry-run
    script_path = Path("tools/feasibility/run_profile_bridge_dry_run.py")
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, cwd=str(project_root))
    assert res.returncode == 0, f"Bridge dry-run script failed: {res.stderr}"
    
    # 2. Kiểm tra các tệp đầu ra được sinh ra
    out_dir = Path("feasibility_outputs/profile_bridge_dry_run")
    items_json_path = out_dir / "profile_bridge_items.json"
    summary_json_path = out_dir / "profile_bridge_summary.json"
    report_md_path = out_dir / "profile_bridge_report.md"
    
    assert items_json_path.exists(), "Bridge items JSON not found."
    assert summary_json_path.exists(), "Bridge summary JSON not found."
    assert report_md_path.exists(), "Bridge report Markdown not found."
    
    # 3. Đọc dữ liệu summary
    with open(summary_json_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
        
    assert summary["bridge_version"] == "1.0.0"
    assert summary["mode"] == "dry_run"
    assert summary["bridge_status"] == "PASS"
    assert summary["integration_readiness"]["ready_for_write_to_main_pipeline"] is False
    
    # 4. Kiểm tra có đủ 3 nhà cung cấp
    suppliers = {s["supplier_code"]: s for s in summary["suppliers"]}
    assert "ABB" in suppliers
    assert "LS" in suppliers
    assert "CHINT" in suppliers
    
    # 5. Đọc danh sách items
    with open(items_json_path, "r", encoding="utf-8") as f:
        items = json.load(f)
        
    # Bridged item count bằng tổng valid items hiện tại: 743 + 284 + 45 = 1072
    assert len(items) == 1072, f"Expected 1072 bridged items, but got {len(items)}"
    
    # 6. Kiểm tra cấu trúc dữ liệu từng item
    for it in items:
        assert it["supplier_code"] in ["ABB", "LS", "CHINT"]
        assert isinstance(it["source_page"], int) and it["source_page"] >= 1
        assert "provenance" in it and it["provenance"] != ""
        assert it["currency"] == "VND"
        assert isinstance(it["unit_price"], int) and it["unit_price"] > 0
        assert it["normalized_material_code"] != ""
        assert "bridge_status" in it and it["bridge_status"] == "bridged"
        
    # 7. Kiểm tra các từ khóa overclaim không xuất hiện trong báo cáo MD
    with open(report_md_path, "r", encoding="utf-8") as f:
        report_text = f.read()
        
    overclaim_keywords = [
        "production-ready",
        "sẵn sàng production",
        "tự động xử lý mọi pdf",
        "chứng minh tính tổng quát",
        "tích hợp thành công vào pipeline chính"
    ]
    
    import unicodedata
    def remove_accents(input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        
    clean_report = remove_accents(report_text).lower()
    
    for kw in overclaim_keywords:
        clean_kw = remove_accents(kw).lower()
        assert clean_kw not in clean_report, f"Found overclaiming keyword '{kw}' in bridge report."
