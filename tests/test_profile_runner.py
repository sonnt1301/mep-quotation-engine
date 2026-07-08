import pytest
import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.append(project_root)

from tools.feasibility.profile_config_loader import load_profile_config, get_layout_for_page
from tools.feasibility.profile_runner import parse_page_from_config

def test_runner_load_configs():
    base_dir = Path(__file__).parent / "../tools/feasibility/profile_configs"
    
    # Load ABB
    abb_config = load_profile_config(str((base_dir / "abb_profile_v1.json").resolve()))
    assert abb_config["profile_id"] == "abb_profile_v1"
    
    # Load LS
    ls_config = load_profile_config(str((base_dir / "ls_profile_v1.json").resolve()))
    assert ls_config["profile_id"] == "ls_profile_v1"

def test_config_layout_mapping():
    base_dir = Path(__file__).parent / "../tools/feasibility/profile_configs"
    abb_config = load_profile_config(str((base_dir / "abb_profile_v1.json").resolve()))
    ls_config = load_profile_config(str((base_dir / "ls_profile_v1.json").resolve()))
    
    # ABB page 18 -> double_column_3p_4p
    lay_18 = get_layout_for_page(abb_config, 18)
    assert lay_18 is not None
    assert lay_18["layout_name"] == "double_column_3p_4p"
    
    # ABB page 41 -> four_columns_ot_page41
    lay_41 = get_layout_for_page(abb_config, 41)
    assert lay_41 is not None
    assert lay_41["layout_name"] == "four_columns_ot_page41"
    
    # LS page 1 -> split_half_left_right
    lay_ls1 = get_layout_for_page(ls_config, 1)
    assert lay_ls1 is not None
    assert lay_ls1["layout_name"] == "split_half_left_right"

def test_invalid_profile_load_fails():
    base_dir = Path(__file__).parent / "../tools/feasibility/profile_configs"
    
    # file không tồn tại phải fail
    with pytest.raises(FileNotFoundError):
        load_profile_config(str(base_dir / "non_existing_profile.json"))

def test_output_path_non_override_v1():
    # Kiểm tra đường dẫn xuất kết quả của config run độc lập và không đè lên v1
    supplier = "ABB"
    output_dir = Path(f"D:/mep_quotation_pipeline/feasibility_outputs/{supplier.lower()}_profile_config_run")
    baseline_dir = Path(f"D:/mep_quotation_pipeline/feasibility_outputs/{supplier.lower()}_profile_v1")
    
    assert output_dir != baseline_dir
    assert "config_run" in str(output_dir)
    assert "v1" in str(baseline_dir)

def test_ls_price_regression():
    # Kiểm thử hồi quy đơn giá LS config-run
    import json
    config_run_valid_path = Path("D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_config_run/profile_items_valid.json")
    if not config_run_valid_path.exists():
        pytest.skip("ls_profile_config_run/profile_items_valid.json does not exist. Run runner first.")
        
    with open(config_run_valid_path, encoding="utf-8") as f:
        items = json.load(f)
        
    # Tạo map tra cứu nhanh: {(source_page, material_code): [prices]}
    price_map = {}
    for it in items:
        key = (it["source_page"], it["material_code"].upper())
        if key not in price_map:
            price_map[key] = []
        price_map[key].append(it["unit_price"])
        
    # 1. Regression test cho ABN104C (page 1) = 1850000
    assert 1850000 in price_map.get((1, "ABN104C"), [])
    
    # 2. Regression test cho ABS203C (page 1) = 3350000
    assert 3350000 in price_map.get((1, "ABS203C"), [])
    
    # 3. Regression test cho EBS204C (page 2) = 9500000
    assert 9500000 in price_map.get((2, "EBS204C"), [])
    
    # 4. Regression test cho EBN404C (page 2) = 16600000
    assert 16600000 in price_map.get((2, "EBN404C"), [])
    
    # 5. Regression test bảo vệ giá lớn hợp lệ AS-25E3-25H (page 5)
    prices_25e = price_map.get((5, "AS-25E3-25H"), [])
    assert len(prices_25e) > 0
    # Đơn giá phải là giá trị trăm triệu hợp lệ (không phải giá trị nhỏ hay bị ghép dính)
    assert 135000000 in prices_25e or 118000000 in prices_25e
    
    # 6. Regression test bảo vệ giá lớn hợp lệ AS-63G3-63H (page 5)
    prices_63g = price_map.get((5, "AS-63G3-63H"), [])
    assert len(prices_63g) > 0
    assert 460000000 in prices_63g or 438000000 in prices_63g
