import pytest
import sys
from pathlib import Path

# Thêm project root vào sys.path để test import được mep_quotation
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

@pytest.fixture
def temp_project_dir(tmp_path):
    """Fixture tạo cấu trúc project giả lập trong thư mục tạm thời."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "suppliers").mkdir()
    (data_dir / "indexes").mkdir()
    
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    
    return tmp_path
