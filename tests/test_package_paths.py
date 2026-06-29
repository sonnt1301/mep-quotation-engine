from pathlib import Path
from mep_quotation.package.paths import get_package_dir, get_next_sequence

def test_get_package_dir(temp_project_dir):
    data_root = temp_project_dir / "data"
    pkg_dir = get_package_dir(data_root, "AUT", "2026-05-20", 1)
    
    expected_path = data_root / "suppliers" / "AUT" / "2026" / "2026-05-20_001"
    assert pkg_dir == expected_path

def test_get_next_sequence(temp_project_dir):
    data_root = temp_project_dir / "data"
    supplier = "AUT"
    date_str = "2026-05-20"
    
    # Khi thư mục chưa tồn tại
    assert get_next_sequence(data_root, supplier, date_str) == 1
    
    # Tạo thư mục cho seq=1
    pkg_dir_1 = get_package_dir(data_root, supplier, date_str, 1)
    pkg_dir_1.mkdir(parents=True)
    assert get_next_sequence(data_root, supplier, date_str) == 2
    
    # Tạo thư mục cho seq=2 và một seq=5 nhảy cóc
    pkg_dir_2 = get_package_dir(data_root, supplier, date_str, 2)
    pkg_dir_2.mkdir(parents=True)
    pkg_dir_5 = get_package_dir(data_root, supplier, date_str, 5)
    pkg_dir_5.mkdir(parents=True)
    
    # Phải lấy max_seq + 1 (5 + 1 = 6)
    assert get_next_sequence(data_root, supplier, date_str) == 6
