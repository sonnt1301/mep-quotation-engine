import json
from mep_quotation.package.builder import create_empty_package
from mep_quotation.package.writer import write_json_file
from mep_quotation.indexer.material_indexer import build_material_index
from mep_quotation.indexer.search import search_materials
from mep_quotation.spec.models import NormalizedQuotationModel, NormalizedItemModel, EvidenceModel

def create_fake_normalized_file(package_dir, supplier, date_str, seq, items):
    quotation_id = f"{supplier}_{date_str.replace('-', '')}_{seq:03d}"
    
    norm_items = []
    for i, item in enumerate(items, 1):
        norm_items.append(NormalizedItemModel(
            item_id=f"{quotation_id}_{i:04d}",
            source_draft_item_id=f"{quotation_id}_DRAFTITEM_{i:04d}",
            source_review_decision_id=f"{quotation_id}_REVIEW_{i:04d}",
            description=item["name"],
            currency="VND",
            material_code=item["code"],
            material_name=item["name"],
            category=item.get("category", "Cable"),
            unit=item.get("unit", "m"),
            unit_price=item["price"],
            vat_rate=0.1,
            brand=item.get("brand", "CADIVI"),
            origin="Vietnam",
            raw_text=item["name"],
            evidence=EvidenceModel(source_pdf="source/original.pdf")
        ))
        
    from datetime import datetime, timezone
    from mep_quotation.spec.models import ExportSummaryModel
    now = datetime.now(timezone.utc)
    
    norm_quot = NormalizedQuotationModel(
        quotation_id=quotation_id,
        supplier_code=supplier,
        quotation_date=date_str,
        currency="VND",
        source_normalized_draft="normalized/normalized_draft.json",
        source_normalized_draft_sha256="",
        source_review_decisions="review/review_decisions.json",
        source_review_decisions_sha256="",
        item_count=len(norm_items),
        export_summary=ExportSummaryModel(
            draft_item_count=len(norm_items),
            approved_count=len(norm_items),
            edited_count=0,
            rejected_count=0,
            unreviewed_count=0,
            exported_item_count=len(norm_items)
        ),
        warnings=[],
        items=norm_items,
        created_at=now,
        updated_at=now
    )
    
    write_json_file(package_dir / "normalized" / "normalized.json", norm_quot)

def test_indexer_and_search_flow(temp_project_dir):
    data_root = temp_project_dir / "data"
    project_root = temp_project_dir
    
    # 1. Tạo 3 package báo giá giả lập
    # Package 1: CADIVI ngày 2026-05-20
    pkg1 = create_empty_package(data_root, "CADIVI", "2026-05-20", 1)
    create_fake_normalized_file(pkg1, "CADIVI", "2026-05-20", 1, [
        {"code": "CV-3X2.5", "name": "Cáp đồng CV 3x2.5", "price": 18500},
        {"code": "CV-3X4.0", "name": "Cáp đồng CV 3x4.0", "price": 27000}
    ])
    
    # Package 2: AUT ngày 2026-05-20
    pkg2 = create_empty_package(data_root, "AUT", "2026-05-20", 1)
    create_fake_normalized_file(pkg2, "AUT", "2026-05-20", 1, [
        {"code": "VALVE-DN50", "name": "Van cổng DN50", "price": 1250000}
    ])
    
    # Package 3: CADIVI ngày 2026-05-21 (ngày mới hơn)
    pkg3 = create_empty_package(data_root, "CADIVI", "2026-05-21", 1)
    create_fake_normalized_file(pkg3, "CADIVI", "2026-05-21", 1, [
        {"code": "CV-3X2.5", "name": "Cáp đồng CV 3x2.5 (mới)", "price": 19000}
    ])
    
    # 2. Chạy Build Index
    index_file, skipped = build_material_index(data_root, project_root)
    assert index_file.exists()
    assert len(skipped) == 0
    
    # Đọc index file và kiểm tra cấu trúc
    with open(index_file, "r", encoding="utf-8") as f:
        index_data = json.load(f)
        
    assert "CV-3X2.5" in index_data["materials"]
    assert "CV-3X4.0" in index_data["materials"]
    assert "VALVE-DN50" in index_data["materials"]
    
    # Kiểm tra việc sắp xếp tăng dần theo date
    cv_entries = index_data["materials"]["CV-3X2.5"]
    assert len(cv_entries) == 2
    # Entry 1 phải là ngày 2026-05-20
    assert cv_entries[0]["quotation_date"] == "2026-05-20"
    # Entry 2 phải là ngày 2026-05-21
    assert cv_entries[1]["quotation_date"] == "2026-05-21"
    
    # 3. Thử tìm kiếm vật tư
    # Khớp chính xác (exact match)
    res1 = search_materials(index_file, "CV-3X2.5")
    assert "CV-3X2.5" in res1
    assert len(res1) == 1
    
    # Tìm kiếm case-insensitive contains trên code
    res2 = search_materials(index_file, "cv-3x")
    assert "CV-3X2.5" in res2
    assert "CV-3X4.0" in res2
    assert len(res2) == 2
    
    # Tìm kiếm contains trên name
    res3 = search_materials(index_file, "Van cổng")
    assert "VALVE-DN50" in res3
    assert len(res3) == 1
    
    # Tìm kiếm không khớp
    res4 = search_materials(index_file, "NON-EXISTENT")
    assert len(res4) == 0
