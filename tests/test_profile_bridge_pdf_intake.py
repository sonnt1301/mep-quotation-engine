import json
import pytest
import shutil
from pathlib import Path
from tools.profile_bridge_review_helpers import (
    resolve_selected_profile_config,
    create_review_session_folder,
    validate_pdf_input,
    run_parser_on_pdf,
    run_bridge_on_session
)

def test_resolve_selected_profile_config_valid():
    # Kiểm tra config hợp lệ cho 3 supplier chính thức
    config_abb = resolve_selected_profile_config("ABB")
    config_ls = resolve_selected_profile_config("LS")
    config_chint = resolve_selected_profile_config("CHINT")
    
    assert config_abb.name == "abb_profile_v1.json"
    assert config_ls.name == "ls_profile_v1.json"
    assert config_chint.name == "chint_profile_v1.json"

def test_resolve_selected_profile_config_invalid():
    # Kiểm tra không cho phép supplier lạ ngoài ABB/LS/CHINT
    with pytest.raises(ValueError) as excinfo:
        resolve_selected_profile_config("SCHNEIDER")
    assert "Chỉ hỗ trợ nhà cung cấp ABB, LS, CHINT" in str(excinfo.value)

def test_create_review_session_folder():
    # Kiểm tra session folder được tạo trong thư mục sessions riêng biệt
    session_dir = create_review_session_folder("LS")
    assert session_dir.exists()
    assert "profile_visual_review_sessions" in str(session_dir)
    assert "LS" in session_dir.name
    
    # Dọn dẹp thư mục tạm sau test
    shutil.rmtree(session_dir)

def test_validate_pdf_input():
    # Kiểm tra lỗi khi missing PDF
    ok, err = validate_pdf_input("")
    assert ok is False
    assert "đường dẫn tệp pdf trống" in err.lower()
    
    # Kiểm tra lỗi khi file không tồn tại
    ok, err = validate_pdf_input("nonexistent_file_path.pdf")
    assert ok is False
    assert "không tồn tại" in err.lower()
    
    # Kiểm tra lỗi định dạng đuôi file
    dummy_txt = Path("dummy_text_file.txt")
    with open(dummy_txt, "w") as f:
        f.write("test content")
        
    ok, err = validate_pdf_input(str(dummy_txt))
    assert ok is False
    assert "định dạng tệp không hợp lệ" in err.lower()
    
    dummy_txt.unlink()

def test_session_output_does_not_overwrite_benchmark():
    # Đảm bảo session output được ghi vào session folder, không ghi đè benchmark
    session_dir = create_review_session_folder("ABB")
    
    # Cấu hình file valid items JSON mẫu
    sample_valid_items = [
        {
            "supplier_code": "ABB",
            "source_page": 18,
            "layout_name": "double_column_3p_4p",
            "material_code": "1SDA066925R1",
            "description": "XT1B 160 TMD 63-630 3p F F",
            "unit": "cái",
            "unit_price": 1850000,
            "currency": "VND",
            "extraction_method": "coordinate_column_profiler"
        }
    ]
    
    valid_json_path = session_dir / "profile_items_valid.json"
    with open(valid_json_path, "w", encoding="utf-8") as f:
        json.dump(sample_valid_items, f)
        
    # Chạy bridge trên session
    original_pdf_fake = Path("test_original_doc.pdf")
    bridge_json_path = run_bridge_on_session("ABB", session_dir, original_pdf_fake)
    
    assert bridge_json_path.exists()
    assert bridge_json_path.parent == session_dir
    
    # Kiểm tra summary session không được set ready_for_write_to_main_pipeline = true
    summary_path = session_dir / "profile_bridge_summary.json"
    assert summary_path.exists()
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_data = json.load(f)
    assert summary_data["integration_readiness"]["ready_for_write_to_main_pipeline"] is False
    
    # Đảm bảo benchmark output thực tế không bị ảnh hưởng/ghi đè
    benchmark_dir = Path("feasibility_outputs/profile_bridge_dry_run")
    benchmark_items_path = benchmark_dir / "profile_bridge_items.json"
    if benchmark_items_path.exists():
        with open(benchmark_items_path, "r", encoding="utf-8") as f:
            bench_items = json.load(f)
        # Đảm bảo số lượng items benchmark gốc vẫn đầy đủ (1072 items)
        assert len(bench_items) == 1072
        
    # Dọn dẹp
    shutil.rmtree(session_dir)
