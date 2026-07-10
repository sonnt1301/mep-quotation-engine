import json
import csv
import re
import pytest
import sys
import subprocess
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def test_bridge_human_review_package_generation():
    # 1. Thực thi chạy script xuất gói human review
    script_path = Path("tools/feasibility/export_profile_bridge_human_review.py")
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, cwd=str(project_root))
    assert res.returncode == 0, f"Human review script failed with error: {res.stderr}"
    
    # 2. Định nghĩa thư mục đầu ra
    out_dir = Path("feasibility_outputs/profile_bridge_human_review")
    sample_csv = out_dir / "profile_bridge_review_sample.csv"
    dup_csv = out_dir / "profile_bridge_duplicate_code_review.csv"
    checklist_md = out_dir / "profile_bridge_human_review_checklist.md"
    summary_json = out_dir / "profile_bridge_human_review_summary.json"
    summary_md = out_dir / "profile_bridge_human_review_summary.md"
    
    assert sample_csv.exists(), "Sample CSV file not found."
    assert dup_csv.exists(), "Duplicate CSV file not found."
    assert checklist_md.exists(), "Checklist MD file not found."
    assert summary_json.exists(), "Summary JSON file not found."
    assert summary_md.exists(), "Summary MD file not found."
    
    # 3. Kiểm tra số dòng và nhà cung cấp trong sample CSV
    with open(sample_csv, "r", encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
        
    num_rows = len(reader)
    # Phải có ít nhất 60 dòng và nhỏ hơn hoặc bằng 80 dòng (theo yêu cầu mẫu khoảng 60-80 dòng)
    assert num_rows >= 60, f"Expected at least 60 sample rows, but got {num_rows}"
    assert num_rows <= 80, f"Expected at most 80 sample rows, but got {num_rows}"
    
    suppliers = set(r["supplier_code"] for r in reader)
    assert "ABB" in suppliers
    assert "LS" in suppliers
    assert "CHINT" in suppliers
    
    # 4. Kiểm tra sự hiện diện các trang known limitations trong sample
    ls_pages = set(int(r["source_page"]) for r in reader if r["supplier_code"] == "LS")
    chint_pages = set(int(r["source_page"]) for r in reader if r["supplier_code"] == "CHINT")
    
    assert 2 in ls_pages, "LS page 2 is missing from sample."
    assert 5 in ls_pages, "LS page 5 is missing from sample."
    assert 3 in chint_pages, "CHINT page 3 is missing from sample."
    assert 5 in chint_pages, "CHINT page 5 is missing from sample."
    
    # 5. Kiểm tra duplicate review có ít nhất 1 nhóm HIGH risk
    with open(dup_csv, "r", encoding="utf-8-sig") as f:
        dup_reader = list(csv.DictReader(f))
        
    high_risks = [r for r in dup_reader if r["risk_level"] == "HIGH"]
    assert len(high_risks) >= 1, "Expected at least 1 HIGH risk duplicate group."
    
    # 6. Kiểm tra cấu trúc summary JSON
    with open(summary_json, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
        
    assert summary_data["proposed_status"] == "READY_FOR_HUMAN_REVIEW"
    assert summary_data["ready_for_write_to_main_pipeline"] is False
    
    # 7. Kiểm tra các từ khóa overclaim không được phép xuất hiện trong báo cáo MD và checklist MD
    with open(summary_md, "r", encoding="utf-8") as f:
        summary_text = f.read()
        
    with open(checklist_md, "r", encoding="utf-8") as f:
        checklist_text = f.read()
        
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
        
    clean_summary = remove_accents(summary_text).lower()
    clean_checklist = remove_accents(checklist_text).lower()
    
    for kw in overclaim_keywords:
        clean_kw = remove_accents(kw).lower()
        assert clean_kw not in clean_summary, f"Found overclaiming keyword '{kw}' in summary MD."
        assert clean_kw not in clean_checklist, f"Found overclaiming keyword '{kw}' in checklist MD."
