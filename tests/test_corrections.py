import pytest
from datetime import datetime, timedelta
from mep_quotation.package.builder import create_empty_package
from mep_quotation.corrections.recorder import record_correction
from mep_quotation.package.loader import load_corrections_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.spec.models import CorrectionEntryModel, CorrectionsFileModel

def test_record_correction_flow(temp_project_dir):
    data_root = temp_project_dir / "data"
    supplier = "AUT"
    date_str = "2026-05-20"
    
    # 1. Khởi tạo package
    package_dir = create_empty_package(data_root, supplier, date_str, 1)
    
    # 2. Ghi nhận correction thứ nhất
    corr1 = record_correction(
        package_dir,
        field_path="items[0].unit_price",
        old_value=18500,
        new_value=19200,
        reason="Revised price",
        correction_type="price_update"
    )
    
    assert corr1.correction_id == "corr_001"
    
    # 3. Ghi nhận correction thứ hai
    corr2 = record_correction(
        package_dir,
        field_path="items[0].unit",
        old_value="m",
        new_value="cuộn",
        reason="Wrong unit in pdf",
        correction_type="unit_update"
    )
    
    assert corr2.correction_id == "corr_002"
    
    # 4. Load lại để kiểm tra
    corr_file = load_corrections_json(package_dir)
    assert len(corr_file.corrections) == 2
    assert corr_file.corrections[0].correction_id == "corr_001"
    assert corr_file.corrections[1].correction_id == "corr_002"

def test_deterministic_sorting_corrections(temp_project_dir):
    data_root = temp_project_dir / "data"
    package_dir = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    
    # Sửa đổi trực tiếp file corrections.json với dữ liệu không được sắp xếp
    t1 = datetime(2026, 6, 29, 10, 0, 0)
    t2 = t1 + timedelta(minutes=5)
    
    # Tạo các correction entry ngược thứ tự thời gian
    c2 = CorrectionEntryModel(
        correction_id="corr_002",
        timestamp=t2,
        user="human",
        field_path="field2",
        old_value="old2",
        new_value="new2",
        reason="reason2",
        correction_type="type"
    )
    
    c1 = CorrectionEntryModel(
        correction_id="corr_001",
        timestamp=t1,
        user="human",
        field_path="field1",
        old_value="old1",
        new_value="new1",
        reason="reason1",
        correction_type="type"
    )
    
    # Hai correction có cùng timestamp nhưng ID khác nhau để test sort theo ID
    c3_b = CorrectionEntryModel(
        correction_id="corr_004",
        timestamp=t2,  # Trùng timestamp với c2 nhưng id lớn hơn
        user="human",
        field_path="field4",
        old_value="old4",
        new_value="new4",
        reason="reason4",
        correction_type="type"
    )
    
    c3_a = CorrectionEntryModel(
        correction_id="corr_003",
        timestamp=t2,  # Trùng timestamp với c2
        user="human",
        field_path="field3",
        old_value="old3",
        new_value="new3",
        reason="reason3",
        correction_type="type"
    )

    corr_file = CorrectionsFileModel(
        quotation_id="AUT_20260520_001",
        # Để lộn xộn thứ tự
        corrections=[c3_b, c1, c3_a, c2]
    )
    
    write_json_file(package_dir / "corrections" / "corrections.json", corr_file)
    
    # Ghi nhận correction mới qua recorder để kích hoạt bộ sắp xếp
    record_correction(
        package_dir,
        field_path="field5",
        old_value="old5",
        new_value="new5",
        reason="reason5"
    )
    
    # Load lại để xem thứ tự
    loaded = load_corrections_json(package_dir)
    
    # Thứ tự mong đợi sau khi sort:
    # 1. c1 (timestamp t1 nhỏ nhất) -> corr_001
    # 2. c2, c3_a, c3_b (cùng timestamp t2) -> sắp xếp theo ID: corr_002, corr_003, corr_004
    # 3. entry mới (timestamp hiện tại lớn nhất) -> corr_005
    ids = [entry.correction_id for entry in loaded.corrections]
    assert ids == ["corr_001", "corr_002", "corr_003", "corr_004", "corr_005"]
