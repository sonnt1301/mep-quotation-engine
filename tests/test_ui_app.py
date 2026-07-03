import os
import json
import pytest
from pathlib import Path
from tools.ui_helpers import (
    sanitize_filename,
    safe_load_json,
    run_cli_command,
    resolve_artifact_paths
)
from mep_quotation.spec.models import QuotationPackageModel

def test_sanitize_filename():
    assert sanitize_filename("test.pdf") == "test.pdf"
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("test space file.pdf") == "test_space_file.pdf"
    assert sanitize_filename(".hidden.pdf") == "safe_.hidden.pdf"
    assert sanitize_filename("invalid/char*?.pdf") == "char__.pdf"

def test_safe_load_json(tmp_path):
    # 1. File missing
    data, err = safe_load_json(tmp_path / "missing.json")
    assert data is None
    assert "File not found" in err
    
    # 2. Invalid JSON
    bad_json = tmp_path / "bad.json"
    with open(bad_json, "w", encoding="utf-8") as f:
        f.write("{ invalid json")
    data, err = safe_load_json(bad_json)
    assert data is None
    assert "Invalid JSON" in err
    
    # 3. Success
    good_json = tmp_path / "good.json"
    with open(good_json, "w", encoding="utf-8") as f:
        f.write('{"hello": "world"}')
    data, err = safe_load_json(good_json)
    assert data == {"hello": "world"}
    assert err is None

def test_run_cli_command():
    # 1. Lệnh thành công
    code, stdout, stderr = run_cli_command(["python", "-c", "print('hello world')"])
    assert code == 0
    assert "hello world" in stdout
    
    # 2. Lệnh thất bại
    code, stdout, stderr = run_cli_command(["python", "-c", "import sys; print('error output', file=sys.stderr); sys.exit(5)"])
    assert code == 5
    assert "error output" in stderr
    
    # 3. Hết thời gian chờ (Timeout)
    code, stdout, stderr = run_cli_command(["python", "-c", "import time; time.sleep(5)"], timeout=1)
    assert code == -1
    assert "timed out" in stderr

def test_resolve_artifact_paths(tmp_path):
    package_path = tmp_path / "package"
    package_path.mkdir()
    
    # 1. Trường hợp package.json chưa tồn tại -> Nhận default paths
    paths = resolve_artifact_paths(package_path)
    assert paths["package_json"] == package_path / "package.json"
    assert paths["source_pdf"] == package_path / "source" / "original.pdf"
    assert paths["metadata"] == package_path / "source" / "metadata.json"
    
    # 2. Có package.json nhưng trống hoặc lỗi
    package_json = package_path / "package.json"
    with open(package_json, "w", encoding="utf-8") as f:
        f.write("{}")
    paths = resolve_artifact_paths(package_path)
    assert paths["source_pdf"] == package_path / "source" / "original.pdf"
    
    # 3. Có package.json hợp lệ với các đường dẫn tùy biến
    pkg_data = {
        "quotation_id": "TEST_20260620_001",
        "supplier": {"code": "TEST", "name": "Test Supplier"},
        "quotation_date": "2026-06-20",
        "sequence": 1,
        "files": {
            "source_pdf": "custom_source/input.pdf",
            "pdf_metadata": "custom_source/meta.json",
            "page_manifest": "custom_source/pages.json",
            "raw_text": "source/raw_text.json",
            "text_markdown": "text/quotation.md",
            "text_manifest": "text/quotation_text.json",
            "line_candidates": "parsed/line_candidates.json",
            "row_candidates": "parsed/row_candidates.json",
            "item_candidates": "parsed/item_candidates.json",
            "parsed_json": "parsed/quotation.json",
            "parsed_markdown": "parsed/quotation.md",
            "normalized_json": "normalized/normalized.json",
            "normalized_draft": "normalized/normalized_draft.json",
            "review_decisions": "review/review_decisions.json",
            "corrections_json": "corrections/corrections.json",
            "logs_jsonl": "logs/processing.log.jsonl",
            "excel_export": "exports/quotation.xlsx",
            "excel_export_manifest": "exports/export_manifest.json"
        },
        "created_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-06-20T00:00:00Z"
    }
    with open(package_json, "w", encoding="utf-8") as f:
        json.dump(pkg_data, f)
        
    paths = resolve_artifact_paths(package_path)
    assert paths["source_pdf"] == package_path / "custom_source" / "input.pdf"
    assert paths["metadata"] == package_path / "custom_source" / "meta.json"
    assert paths["page_manifest"] == package_path / "custom_source" / "pages.json"
    # Các trường khác vẫn fallback mặc định
    assert paths["raw_text"] == package_path / "source" / "raw_text.json"
