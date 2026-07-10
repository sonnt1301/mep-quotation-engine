# -*- coding: utf-8 -*-
import json
import pytest
from pathlib import Path
from tools.profile_bridge_review_helpers import build_duplicate_review_rows

def test_no_mojibake_in_source_files():
    # Rà soát tĩnh các file code UI và Helper chống mojibake tiếng Việt phổ biến
    targets = [
        Path("tools/profile_bridge_review_app.py"),
        Path("tools/profile_bridge_review_helpers.py")
    ]
    
    mojibake_patterns = ["Chá»", "Ä", "âš", "ðŸ"]
    
    for t in targets:
        assert t.exists(), f"File {t} không tồn tại!"
        with open(t, "r", encoding="utf-8") as f:
            content = f.read()
            for pattern in mojibake_patterns:
                assert pattern not in content, f"Phát hiện chuỗi mojibake '{pattern}' trong file: {t.name}"

def test_dependencies_configured():
    # Kiểm tra pyproject.toml có đủ streamlit và pdfplumber
    toml_path = Path("pyproject.toml")
    assert toml_path.exists()
    
    with open(toml_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    assert "streamlit" in content.lower()
    assert "pdfplumber" in content.lower()

def test_ready_for_write_to_main_pipeline_always_false():
    # Kiểm tra các summary và manifest không bao giờ được set ready = True
    paths = [
        Path("feasibility_outputs/profile_run_manifest/profile_run_manifest.json"),
        Path("feasibility_outputs/profile_bridge_dry_run/profile_bridge_summary.json"),
        Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_human_review_summary.json")
    ]
    
    for p in paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Đệ quy tìm key
            def check_ready(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == "ready_for_write_to_main_pipeline":
                            assert v is False, f"ready_for_write_to_main_pipeline bị set thành True tại: {p.name}"
                        elif k == "ready_for_main_pipeline":
                            assert v is False, f"ready_for_main_pipeline bị set thành True tại: {p.name}"
                        else:
                            check_ready(v)
                elif isinstance(obj, list):
                    for item in obj:
                        check_ready(item)
            check_ready(data)

def test_build_duplicate_review_rows():
    # Kiểm tra tính toán duplicate group động
    items = [
        {"supplier_code": "LS", "normalized_material_code": "ABC", "unit_price": 100, "source_page": 1, "description": "Desc1", "source_evidence_text": "Ev1"},
        {"supplier_code": "LS", "normalized_material_code": "ABC", "unit_price": 200, "source_page": 2, "description": "Desc2", "source_evidence_text": "Ev2"},
        {"supplier_code": "ABB", "normalized_material_code": "XYZ", "unit_price": 500, "source_page": 3, "description": "Desc3", "source_evidence_text": "Ev3"}
    ]
    
    dup_groups = build_duplicate_review_rows(items)
    # LS ABC xuất hiện 2 lần -> là duplicate group
    # ABB XYZ xuất hiện 1 lần -> không phải duplicate group
    assert len(dup_groups) == 1
    assert dup_groups[0]["supplier_code"] == "LS"
    assert dup_groups[0]["normalized_material_code"] == "ABC"
    assert dup_groups[0]["risk_level"] == "HIGH"  # Vì có 2 mức giá khác nhau (100 và 200)

def test_benchmark_outputs_not_overwritten():
    # Đảm bảo benchmark output thực tế không bị sửa đổi
    benchmark_items_path = Path("feasibility_outputs/profile_bridge_dry_run/profile_bridge_items.json")
    if benchmark_items_path.exists():
        with open(benchmark_items_path, "r", encoding="utf-8") as f:
            bench_items = json.load(f)
        assert len(bench_items) == 1072
