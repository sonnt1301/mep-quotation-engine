import json
import pytest
import sys
import subprocess
import re
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path để tránh lỗi import
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

def test_manifest_generation_execution():
    # 1. Chạy script sinh manifest
    script_path = Path("tools/feasibility/export_profile_run_manifest.py")
    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, cwd=str(project_root))
    assert res.returncode == 0, f"Script failed with output: {res.stderr}"
    
    # 2. Kiểm tra sự tồn tại của tệp Manifest JSON và Markdown
    out_dir = Path("feasibility_outputs/profile_run_manifest")
    manifest_json_path = out_dir / "profile_run_manifest.json"
    manifest_md_path = out_dir / "profile_run_manifest.md"
    
    assert manifest_json_path.exists(), "Manifest JSON file not found."
    assert manifest_md_path.exists(), "Manifest Markdown file not found."
    
    # 3. Load và kiểm tra cấu trúc JSON
    with open(manifest_json_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["benchmark_status"] == "PASS"
    assert manifest["integration_readiness"]["ready_for_main_pipeline"] is False
    
    # 4. Kiểm tra có đủ 3 nhà cung cấp ABB/LS/CHINT
    suppliers = {s["supplier_code"]: s for s in manifest["suppliers"]}
    assert "ABB" in suppliers
    assert "LS" in suppliers
    assert "CHINT" in suppliers
    
    # 5. Kiểm tra các known limitations không bị mất
    ls_limits = " ".join(suppliers["LS"]["known_limitations"])
    chint_limits = " ".join(suppliers["CHINT"]["known_limitations"])
    
    assert "Trang 2" in ls_limits or "Page 2" in ls_limits or "accessories" in ls_limits.lower() or "phụ kiện" in ls_limits.lower()
    assert "Trang 5" in ls_limits or "Page 5" in ls_limits or "accessories" in ls_limits.lower() or "phụ kiện" in ls_limits.lower()
    assert "Trang 5" in chint_limits or "Page 5" in chint_limits or "rơ le nhiệt" in chint_limits.lower()
    
    # 6. Đảm bảo không còn stale text về Chint Page 3 và Page 5 đều PARTIAL
    assert "Page 3 and Page 5 remain PARTIAL" not in chint_limits
    assert "Trang 3 và Trang 5 vẫn ở trạng thái PARTIAL" not in chint_limits
    
    # 7. Kiểm tra các từ khóa overclaim không được xuất hiện
    with open(manifest_md_path, "r", encoding="utf-8") as f:
        md_text = f.read()
        
    overclaim_keywords = [
        "chứng minh tính tổng quát",
        "sẵn sàng production",
        "tự động xử lý mọi pdf",
        "generic parser đã hoàn thiện"
    ]
    
    # Chuẩn hóa văn bản không dấu để kiểm tra cho chắc chắn
    import unicodedata
    def remove_accents(input_str):
        nfkd_form = unicodedata.normalize('NFKD', input_str)
        return u''.join([c for c in nfkd_form if not unicodedata.combining(c)])
        
    clean_md = remove_accents(md_text).lower()
    clean_json = remove_accents(json.dumps(manifest)).lower()
    
    for kw in overclaim_keywords:
        clean_kw = remove_accents(kw).lower()
        assert clean_kw not in clean_md, f"Found overclaiming keyword '{kw}' in manifest MD."
        assert clean_kw not in clean_json, f"Found overclaiming keyword '{kw}' in manifest JSON."

def test_manifest_contract_schema_types_lowercase():
    # Kiểm tra JSON Schema contract type phải viết thường (lowercase)
    contract_path = Path("tools/feasibility/profile_run_manifest_contract.json")
    assert contract_path.exists(), "Manifest JSON Schema contract file not found."
    
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = json.load(f)
        
    # Đọc raw text của file để check xem có chứa type viết hoa không
    with open(contract_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    # Tìm kiếm các mẫu '"type": "WRITE_UPPERCASE"'
    uppercase_types = re.findall(r'"type":\s*"([A-Z]+)"', raw_text)
    assert not uppercase_types, f"Found uppercase schema types in contract: {uppercase_types}"
