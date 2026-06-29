import json
from mep_quotation.package.builder import create_empty_package
from mep_quotation.audit.event_logger import log_event
from mep_quotation.package.loader import load_package_json

def test_event_logger_flow(temp_project_dir):
    data_root = temp_project_dir / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Ghi log các sự kiện
    log_event(package_dir, "INFO", "start_parsing", "AUT_20260520_001", {"file": "original.pdf"})
    log_event(package_dir, "WARN", "missing_vat", "AUT_20260520_001", {"item_idx": 5})
    log_event(package_dir, "ERROR", "parsing_failed", "AUT_20260520_001", {"reason": "timeout"})
    
    # Kiểm tra nội dung file log
    pkg = load_package_json(package_dir)
    log_file_path = package_dir / pkg.files.logs_jsonl
    
    assert log_file_path.exists()
    
    with open(log_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 3
    
    # Parse thử từng dòng JSON
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])
    entry3 = json.loads(lines[2])
    
    assert entry1["event"] == "start_parsing"
    assert entry1["level"] == "INFO"
    assert entry1["details"]["file"] == "original.pdf"
    
    assert entry2["event"] == "missing_vat"
    assert entry2["level"] == "WARN"
    
    assert entry3["event"] == "parsing_failed"
    assert entry3["level"] == "ERROR"
    
    # Kiểm tra tính deterministic: đảm bảo các trường trong JSON được sort_keys
    # Chuỗi JSON được dump ra phải khớp chính xác với key đã sort
    for line in lines:
        data = json.loads(line)
        expected_line = json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n"
        assert line == expected_line
