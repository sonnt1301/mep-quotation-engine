import os
import json
import pytest
from pathlib import Path
from tools.review_ui_helpers import (
    safe_number,
    classify_draft_item,
    format_warnings_vietnamese,
    get_dashboard_stats,
    filter_and_sort_items,
    diagnose_read_results,
    resolve_item_evidence,
    build_review_command,
    build_export_preview_rows
)

@pytest.fixture
def sample_items():
    return [
        {
            "draft_item_id": "ABB_20260620_001_001_0001",
            "description": "Contactor 3P 9A ABB",
            "unit": "Cái",
            "quantity": 10.0,
            "unit_price": 150000.0,
            "amount": 1500000.0,
            "confidence": 0.9,
            "evidence_text": "Trang 1: Contactor 3P 9A qty 10 price 150.000",
            "page_number": 1,
            "warnings": []
        },
        {
            "draft_item_id": "ABB_20260620_001_001_0002",
            "description": "MCB 2P 16A Schneider",
            "unit": "",
            "quantity": 5.0,
            "unit_price": 85000.0,
            "amount": 425000.0,
            "confidence": 0.7,
            "evidence_text": "MCB 2P 16A 5 pcs",
            "page_number": 2,
            "warnings": ["missing_unit"]
        },
        {
            "draft_item_id": "ABB_20260620_001_001_0003",
            "description": "Cáp đồng CV 2.5",
            "unit": "M",
            "quantity": 0.0,
            "unit_price": 0.0,
            "amount": 0.0,
            "confidence": 0.5,
            "evidence_text": "Cáp đồng CV 2.5 giá liên hệ",
            "page_number": None,
            "warnings": ["missing_price", "missing_qty"]
        },
        {
            "draft_item_id": "ABB_20260620_001_001_0004",
            "description": "Bảng tổng hợp vật tư 2026",
            "unit": None,
            "quantity": None,
            "unit_price": None,
            "amount": 0.0,
            "confidence": 0.3,
            "evidence_text": "BẢNG TỔNG HỢP VẬT TƯ",
            "page_number": 3,
            "warnings": []
        },
        {
            "draft_item_id": "ABB_20260620_001_001_0005",
            "description": "Tổng cộng",
            "unit": None,
            "quantity": None,
            "unit_price": None,
            "amount": 1925000.0,
            "confidence": 0.6,
            "evidence_text": "Tổng cộng tiền vật tư",
            "page_number": 3,
            "warnings": []
        }
    ]

@pytest.fixture
def sample_decisions():
    return {
        "ABB_20260620_001_001_0001": {
            "draft_item_id": "ABB_20260620_001_001_0001",
            "decision_type": "approved",
            "reviewer": "admin"
        },
        "ABB_20260620_001_001_0002": {
            "draft_item_id": "ABB_20260620_001_001_0002",
            "decision_type": "edited",
            "reviewer": "admin",
            "reason": "Sửa lại đơn vị",
            "field_overrides": {
                "unit": "Bộ",
                "quantity": 6.0,
                "amount": 510000.0
            }
        }
    }

def test_safe_number():
    """Kiểm tra helper safe_number xử lý ép kiểu số an toàn."""
    assert safe_number(None) == 0.0
    assert safe_number("") == 0.0
    assert safe_number("None") == 0.0
    assert safe_number("12.34") == 12.34
    assert safe_number(15) == 15.0
    assert safe_number("invalid", 5.5) == 5.5

def test_classify_draft_item(sample_items):
    """Kiểm tra heuristics phân loại draft items thành các nhóm vật tư/tiêu đề/rác."""
    # likely_item
    assert classify_draft_item(sample_items[0]) == "likely_item"
    
    # weak_item (thiếu unit)
    assert classify_draft_item(sample_items[1]) == "weak_item"
    
    # incomplete_candidate
    assert classify_draft_item(sample_items[2]) == "incomplete_candidate"
    
    # title_or_header (chứa "bảng tổng hợp vật tư")
    assert classify_draft_item(sample_items[3]) == "title_or_header"
    
    # section_or_note (chứa "Tổng cộng")
    assert classify_draft_item(sample_items[4]) == "section_or_note"

def test_format_warnings_vietnamese():
    """Kiểm tra dịch cảnh báo sang Tiếng Việt sạch bóng JSON thô."""
    raw_warns = ["missing_unit", "low_confidence", {"code": "missing_quantity", "message": "error"}]
    translated = format_warnings_vietnamese(raw_warns)
    assert "Thiếu đơn vị" in translated
    assert "Độ tin cậy thấp" in translated
    assert "Thiếu số lượng" in translated
    
    # Kiểm tra fallback an toàn
    assert format_warnings_vietnamese(["unknown_error"]) == ["unknown_error"]

def test_filter_and_sort_items_noise_exclusion(sample_items, sample_decisions):
    """Kiểm tra bộ lọc mặc định loại trừ dòng nhiễu/tiêu đề thành công."""
    # 1. show_hidden = False (Mặc định ẩn) -> Chỉ hiện 3 dòng likely/weak/incomplete
    default_list = filter_and_sort_items(sample_items, sample_decisions, "Tất cả", "Thứ tự xuất hiện", show_hidden=False)
    assert len(default_list) == 3
    # Xác nhận dòng tiêu đề và ghi chú tổng cộng không xuất hiện
    ids = [item["draft_item_id"] for item in default_list]
    assert "ABB_20260620_001_001_0004" not in ids # title
    assert "ABB_20260620_001_001_0005" not in ids # section/note
    
    # 2. show_hidden = True -> Hiện đầy đủ cả 5 dòng
    full_list = filter_and_sort_items(sample_items, sample_decisions, "Tất cả", "Thứ tự xuất hiện", show_hidden=True)
    assert len(full_list) == 5

def test_build_review_command_quick_reject(tmp_path):
    """Kiểm tra sinh CLI command record-review cho nút Không phải vật tư."""
    package_path = tmp_path / "pkg"
    cmd = build_review_command(
        package_path=package_path,
        draft_item_id="ABB-001",
        decision_type="rejected",
        reviewer="tester",
        reason="Không phải dòng vật tư"
    )
    assert "rejected" in cmd
    assert "Không phải dòng vật tư" in cmd
    assert "--draft-item-id" in cmd
    assert "ABB-001" in cmd

def test_build_export_preview_rows(sample_items, sample_decisions):
    """Kiểm tra logic lọc dữ liệu xem trước xuất bản (Export Preview)."""
    preview_rows = build_export_preview_rows(sample_items, sample_decisions)
    assert len(preview_rows) == 2
    
    row_1 = next(r for r in preview_rows if r["Mã nháp"] == "ABB_20260620_001_001_0001")
    assert row_1["Mô tả"] == "Contactor 3P 9A ABB"
    
    row_2 = next(r for r in preview_rows if r["Mã nháp"] == "ABB_20260620_001_001_0002")
    assert row_2["Đơn vị"] == "Bộ"
    assert row_2["Số lượng"] == 6.0

def test_classify_draft_item_abb_mismatch():
    """Kiểm tra logic classify_draft_item đối với trường hợp bắt nhầm số năm 2020 thành đơn giá."""
    item = {
      "draft_item_id": "ABB_20200101_001_DRAFTITEM_0001",
      "description": "Bảng Dự Toán",
      "unit": None,
      "quantity": None,
      "unit_price": 2020.0,
      "amount": None,
      "currency": "VND",
      "confidence": 0.65,
      "warnings": [
        {"code": "missing_unit", "message": "Item needs review due to: missing_unit"},
        {"code": "missing_quantity", "message": "Item needs review due to: missing_quantity"}
      ]
    }
    
    assert classify_draft_item(item) == "title_or_header"
    
    # Kiểm tra filter mặc định (show_hidden = False) ẩn dòng này khỏi danh sách rà soát chính
    filtered = filter_and_sort_items([item], {}, "Tất cả", "Thứ tự xuất hiện", show_hidden=False)
    assert len(filtered) == 0
    
    # Kiểm tra khi bật hiển thị dòng bị ẩn (show_hidden = True) thì xuất hiện lại
    filtered_shown = filter_and_sort_items([item], {}, "Tất cả", "Thứ tự xuất hiện", show_hidden=True)
    assert len(filtered_shown) == 1
