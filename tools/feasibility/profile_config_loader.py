import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

def validate_column_range(range_val: Any) -> bool:
    if not isinstance(range_val, list) or len(range_val) != 2:
        return False
    min_x, max_x = range_val
    if not isinstance(min_x, (int, float)) or not isinstance(max_x, (int, float)):
        return False
    return min_x < max_x

def validate_profile_config(config: Dict[str, Any]) -> bool:
    if not config:
        raise ValueError("Config cannot be empty")
        
    # Validation tối thiểu theo yêu cầu
    if "profile_id" not in config or not config["profile_id"]:
        raise ValueError("Missing or empty 'profile_id'")
        
    if "supplier_code" not in config or not config["supplier_code"]:
        raise ValueError("Missing or empty 'supplier_code'")
        
    if "profile_version" not in config or not config["profile_version"]:
        raise ValueError("Missing or empty 'profile_version'")
        
    if "status" not in config or not config["status"]:
        raise ValueError("Missing or empty 'status'")
        
    if "source_type" not in config or not config["source_type"]:
        raise ValueError("Missing or empty 'source_type'")
        
    # global_rules
    global_rules = config.get("global_rules")
    if not global_rules or not isinstance(global_rules, dict):
        raise ValueError("Missing or invalid 'global_rules'")
    if "currency" not in global_rules or not global_rules["currency"]:
        raise ValueError("Missing 'global_rules.currency'")
        
    # material_code_patterns
    patterns = config.get("material_code_patterns")
    if not patterns or not isinstance(patterns, list):
        raise ValueError("Missing or invalid 'material_code_patterns'")
        
    # layouts
    layouts = config.get("layouts")
    if not layouts or not isinstance(layouts, list) or len(layouts) == 0:
        raise ValueError("Layouts list cannot be empty")
        
    for layout in layouts:
        if "layout_name" not in layout or not layout["layout_name"]:
            raise ValueError("Missing 'layout_name' in layouts")
        if "pages" not in layout or not isinstance(layout["pages"], list) or len(layout["pages"]) == 0:
            raise ValueError("Pages list cannot be empty in layouts")
        if "parser_type" not in layout or not layout["parser_type"]:
            raise ValueError("Missing 'parser_type' in layouts")
            
        # validate column ranges
        columns = layout.get("columns", {})
        for col_name, col_val in columns.items():
            if isinstance(col_val, dict):
                for sub_col, sub_val in col_val.items():
                    if not validate_column_range(sub_val):
                        raise ValueError(f"Invalid column range for nested column: {col_name}.{sub_col} = {sub_val}")
            else:
                if not validate_column_range(col_val):
                    raise ValueError(f"Invalid column range for column: {col_name} = {col_val}")
                    
    # validation
    validation = config.get("validation")
    if not validation or not isinstance(validation, dict):
        raise ValueError("Missing or invalid 'validation' rules")
    if "allowed_material_code_prefixes" not in validation or not isinstance(validation["allowed_material_code_prefixes"], list):
        raise ValueError("Missing 'validation.allowed_material_code_prefixes'")
        
    return True

def load_profile_config(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found at: {path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    validate_profile_config(config)
    return config

def get_layout_for_page(config: Dict[str, Any], page_number: int) -> Optional[Dict[str, Any]]:
    layouts = config.get("layouts", [])
    for layout in layouts:
        if page_number in layout.get("pages", []):
            return layout
    return None

if __name__ == "__main__":
    # Demo script để tự kiểm chứng
    try:
        base_dir = Path(__file__).parent / "profile_configs"
        abb_config = load_profile_config(str(base_dir / "abb_profile_v1.json"))
        print(f"ABB Config successfully loaded. ID: {abb_config['profile_id']}")
        
        ls_config = load_profile_config(str(base_dir / "ls_profile_v1.json"))
        print(f"LS Config successfully loaded. ID: {ls_config['profile_id']}")
    except Exception as e:
        print(f"Self-verification failed: {e}")
