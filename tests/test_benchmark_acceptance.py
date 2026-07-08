import json
import pytest
import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

def test_benchmark_outputs_exist():
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    
    # Kiểm tra sự tồn tại của 5 file output bắt buộc
    assert (out_dir / "benchmark_acceptance_summary.json").exists()
    assert (out_dir / "benchmark_acceptance_report.md").exists()
    assert (out_dir / "abb_acceptance.json").exists()
    assert (out_dir / "ls_acceptance.json").exists()
    assert (out_dir / "chint_acceptance.json").exists()

def test_benchmark_statuses():
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    
    with open(out_dir / "abb_acceptance.json", "r", encoding="utf-8") as f:
        abb = json.load(f)
    with open(out_dir / "ls_acceptance.json", "r", encoding="utf-8") as f:
        ls = json.load(f)
    with open(out_dir / "chint_acceptance.json", "r", encoding="utf-8") as f:
        chint = json.load(f)
    with open(out_dir / "benchmark_acceptance_summary.json", "r", encoding="utf-8") as f:
        summary = json.load(f)
        
    # ABB status = PASS
    assert abb["status"] == "PASS"
    
    # LS status = ACCEPTED_WITH_KNOWN_LIMITATIONS
    assert ls["status"] == "ACCEPTED_WITH_KNOWN_LIMITATIONS"
    
    # CHINT status = ACCEPTED_WITH_KNOWN_LIMITATIONS hoặc FAIL tùy thực tế (ở đây là ACCEPTED_WITH_KNOWN_LIMITATIONS)
    assert chint["status"] in ["ACCEPTED_WITH_KNOWN_LIMITATIONS", "FAIL"]
    
    # Summary status = PASS hoặc FAIL
    assert summary["benchmark_status"] in ["PASS", "FAIL"]

def test_benchmark_items_integrity():
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    
    # Load kết quả chi tiết
    abb_run_path = Path("feasibility_outputs/abb_profile_config_run/profile_items_valid.json")
    ls_run_path = Path("feasibility_outputs/ls_profile_config_run/profile_items_valid.json")
    
    if abb_run_path.exists():
        with open(abb_run_path, "r", encoding="utf-8") as f:
            abb_items = json.load(f)
        for it in abb_items:
            # Không có item valid nào thiếu material_code
            assert it.get("material_code", "").strip() != ""
            # Không có item valid nào unit_price <= 0
            assert it.get("unit_price", 0) > 0
            # Không có item valid nào thiếu evidence_text
            assert it.get("evidence_text", "").strip() != ""
            
    if ls_run_path.exists():
        with open(ls_run_path, "r", encoding="utf-8") as f:
            ls_items = json.load(f)
        for it in ls_items:
            assert it.get("material_code", "").strip() != ""
            assert it.get("unit_price", 0) > 0
            assert it.get("evidence_text", "").strip() != ""

def test_ls_price_regression_in_benchmark():
    # Regression check trực tiếp trong các checks của LS benchmark
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    with open(out_dir / "ls_acceptance.json", "r", encoding="utf-8") as f:
        ls = json.load(f)
        
    # Regression test status phải PASS
    reg_check = next((c for c in ls["checks"] if c["check_name"] == "ls_price_regression_protection"), None)
    assert reg_check is not None
    assert reg_check["status"] == "PASS"
    
    # Large price protection status phải PASS
    large_check = next((c for c in ls["checks"] if c["check_name"] == "ls_large_price_protection"), None)
    assert large_check is not None
    assert large_check["status"] == "PASS"
    
    # 10x ratio check status phải PASS
    ratio_check = next((c for c in ls["checks"] if c["check_name"] == "ls_no_10x_price_mismatch"), None)
    assert ratio_check is not None
    assert ratio_check["status"] == "PASS"

def test_report_contains_not_production_ready():
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    with open(out_dir / "benchmark_acceptance_report.md", "r", encoding="utf-8") as f:
        report = f.read()
        
    # Phải ghi rõ Not Production-Ready
    assert "Not Production-Ready" in report
    assert "Feasibility Reset" in report

def test_chint_benchmark_integrity():
    out_dir = Path("feasibility_outputs/benchmark_acceptance")
    with open(out_dir / "chint_acceptance.json", "r", encoding="utf-8") as f:
        chint = json.load(f)
        
    # Nếu CHINT được onboard thành công thì phải có valid_items > 0 và known_limitations không rỗng
    if chint["status"] == "ACCEPTED_WITH_KNOWN_LIMITATIONS":
        assert chint["valid_items"] >= 20
        assert chint["invalid_items"] <= 15
        assert chint["pass_pages"] >= 1
        assert chint["partial_pages"] <= 2
        assert chint["total_pages"] == 3
        
        # Bắt buộc phải ghi nhận limitations của Page 3 và Page 5
        limits_text = " ".join(chint["known_limitations"])
        assert "Page 3" in limits_text
        assert "Page 5" in limits_text
        
        # Kiểm tra contract compliance check
        schema_check = next((c for c in chint["checks"] if c["check_name"] == "output_contract_compliance"), None)
        assert schema_check is not None
        assert schema_check["status"] == "PASS"
        
        # Kiểm tra các check criteria chính thức khác
        assert next((c for c in chint["checks"] if c["check_name"] == "chint_valid_items_count"), None)["status"] == "PASS"
        assert next((c for c in chint["checks"] if c["check_name"] == "chint_invalid_items_count"), None)["status"] == "PASS"
        assert next((c for c in chint["checks"] if c["check_name"] == "chint_total_pages_count"), None)["status"] == "PASS"
        assert next((c for c in chint["checks"] if c["check_name"] == "chint_pass_pages_count"), None)["status"] == "PASS"
        assert next((c for c in chint["checks"] if c["check_name"] == "chint_partial_pages_count"), None)["status"] == "PASS"
