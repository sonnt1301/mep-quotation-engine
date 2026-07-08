import pytest
from pathlib import Path
from tools.feasibility.profile_config_loader import (
    load_profile_config,
    validate_profile_config,
    get_layout_for_page
)

def test_load_configs_success():
    base_dir = Path(__file__).parent / "../tools/feasibility/profile_configs"
    
    # 1. Load ABB config
    abb_path = base_dir / "abb_profile_v1.json"
    abb_config = load_profile_config(str(abb_path.resolve()))
    assert abb_config["profile_id"] == "abb_profile_v1"
    assert abb_config["supplier_code"] == "ABB"
    
    # 2. Load LS config
    ls_path = base_dir / "ls_profile_v1.json"
    ls_config = load_profile_config(str(ls_path.resolve()))
    assert ls_config["profile_id"] == "ls_profile_v1"
    assert ls_config["supplier_code"] == "LS"

def test_get_layout_for_page():
    base_dir = Path(__file__).parent / "../tools/feasibility/profile_configs"
    abb_config = load_profile_config(str((base_dir / "abb_profile_v1.json").resolve()))
    ls_config = load_profile_config(str((base_dir / "ls_profile_v1.json").resolve()))
    
    # ABB Page 18 -> double_column_3p_4p
    layout_18 = get_layout_for_page(abb_config, 18)
    assert layout_18 is not None
    assert layout_18["layout_name"] == "double_column_3p_4p"
    
    # ABB Page 41 -> four_columns_ot_page41
    layout_41 = get_layout_for_page(abb_config, 41)
    assert layout_41 is not None
    assert layout_41["layout_name"] == "four_columns_ot_page41"
    
    # LS Page 1 -> split_half_left_right
    layout_ls1 = get_layout_for_page(ls_config, 1)
    assert layout_ls1 is not None
    assert layout_ls1["layout_name"] == "split_half_left_right"
    
    # Trang không tồn tại -> None
    layout_none = get_layout_for_page(ls_config, 99)
    assert layout_none is None

def test_validate_config_failures():
    # Thiếu layouts
    invalid_config_1 = {
      "profile_id": "test_profile",
      "supplier_code": "TEST",
      "profile_version": "1.0",
      "status": "feasibility",
      "source_type": "pdf",
      "global_rules": {
        "currency": "VND",
        "default_unit": "cái",
        "min_unit_price": 1
      },
      "material_code_patterns": [".*"],
      "validation": {
        "allowed_material_code_prefixes": ["A"]
      }
    }
    with pytest.raises(ValueError, match="Layouts list cannot be empty"):
        validate_profile_config(invalid_config_1)
        
    # Column range sai: min_x > max_x
    invalid_config_2 = {
      "profile_id": "test_profile",
      "supplier_code": "TEST",
      "profile_version": "1.0",
      "status": "feasibility",
      "source_type": "pdf",
      "global_rules": {
        "currency": "VND",
        "default_unit": "cái",
        "min_unit_price": 1
      },
      "material_code_patterns": [".*"],
      "layouts": [
        {
          "layout_name": "test_layout",
          "pages": [1],
          "parser_type": "coordinate_column_profiler",
          "columns": {
            "ma": [300.0, 200.0]  # Sai: 300 > 200
          }
        }
      ],
      "validation": {
        "allowed_material_code_prefixes": ["A"]
      }
    }
    with pytest.raises(ValueError, match="Invalid column range for column: ma = \\[300.0, 200.0\\]"):
        validate_profile_config(invalid_config_2)
