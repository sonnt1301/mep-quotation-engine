import os
import json
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timezone

import fitz  # PyMuPDF
import openpyxl
from PIL import Image

from mep_quotation.spec.models import (
    QuotationPackageModel,
    SourceProfileModel,
    SourceRole,
    RecommendedNextAction,
    WarningModel
)
from mep_quotation.intake.profiler import (
    resolve_source_file,
    detect_mime_and_type,
    parse_date_candidates,
    heuristic_source_role,
    profile_source_file
)
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.cli.main import handle_profile_source

@pytest.fixture
def temp_package(tmp_path):
    """Fixture tạo package cấu trúc chuẩn tạm thời phục vụ kiểm thử."""
    package_dir = tmp_path / "AUT_20260620_001"
    package_dir.mkdir()
    (package_dir / "source").mkdir()
    
    # Tạo file package.json giả lập
    pkg_data = {
        "quotation_id": "AUT_20260620_001",
        "supplier": {"code": "AUT", "name": "AUT supplier"},
        "quotation_date": "2026-06-20",
        "sequence": 1,
        "files": {
            "source_pdf": "source/original.pdf",
            "pdf_metadata": "source/metadata.json",
            "page_manifest": "source/page_manifest.json",
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
        }
    }
    
    with open(package_dir / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg_data, f, indent=2)
        
    return package_dir

def test_models_and_enums():
    """Xác thực các định nghĩa enums và Pydantic models mới."""
    assert SourceRole.supplier_quotation_candidate == "supplier_quotation_candidate"
    assert RecommendedNextAction.run_pdf_native_pipeline == "run_pdf_native_pipeline"
    
    # Test valid model dump/load
    profile_json = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "source_file": "source/original.pdf",
        "source_sha256": "abcdef123456",
        "file_name": "original.pdf",
        "file_extension": ".pdf",
        "detected_file_type": "pdf",
        "detected_mime_type": "application/pdf",
        "file_size_bytes": 1024,
        "source_role": "supplier_quotation_candidate",
        "source_role_confidence": 0.85,
        "technical_readability": {
            "is_supported_file_type": True,
            "has_native_text": True,
            "native_text_probe_char_count": 200,
            "text_density_level": "low",
            "is_scanned_candidate": False,
            "requires_ocr": False
        },
        "date_candidates": [
            {
                "date": "2026-06-20",
                "date_type": "quotation_date_candidate",
                "source": "text_probe",
                "confidence": 0.8,
                "evidence": "ngày báo giá: 2026-06-20"
            }
        ],
        "recommended_next_action": "run_pdf_native_pipeline",
        "requires_human_profile_review": False,
        "warnings": [],
        "created_at": "2026-07-03T10:00:00Z",
        "updated_at": "2026-07-03T10:00:00Z"
    }
    
    model = SourceProfileModel.model_validate(profile_json)
    assert model.quotation_id == "AUT_20260620_001"
    assert model.source_role == SourceRole.supplier_quotation_candidate

def test_source_resolver(temp_package):
    """Test tính năng phân giải tệp nguồn theo thứ tự ưu tiên và guardrail."""
    from mep_quotation.package.loader import load_package_json
    pkg = load_package_json(temp_package)
    
    # 1. source_pdf khai báo nhưng tệp chưa tồn tại -> Thử scan source/original.*
    # Không có file nào -> ValueError
    with pytest.raises(ValueError, match="Không tìm thấy tệp source/original.*"):
        resolve_source_file(temp_package, pkg)

    # 2. Tạo đúng 1 tệp source/original.xlsx
    excel_file = temp_package / "source" / "original.xlsx"
    excel_file.write_text("dummy")
    
    resolved = resolve_source_file(temp_package, pkg)
    assert resolved == excel_file

    # 3. Tạo thêm tệp original.pdf -> Có 2 tệp nguồn xung đột mà metadata không chỉ rõ -> ValueError
    pdf_file = temp_package / "source" / "original.pdf"
    pdf_file.write_text("dummy")
    
    # Lúc này pkg.files.source_pdf trỏ đến "source/original.pdf" và file này tồn tại thực tế
    # Nên resolver sẽ ưu tiên dùng files.source_pdf
    resolved_priority = resolve_source_file(temp_package, pkg)
    assert resolved_priority == pdf_file

    # 4. Nếu metadata trỏ file không tồn tại, và trong source/ có nhiều original.* -> ValueError
    # Sửa metadata trỏ sang file không tồn tại
    with open(temp_package / "package.json", "r", encoding="utf-8") as f:
        pkg_raw = json.load(f)
    pkg_raw["files"]["source_pdf"] = "source/missing.pdf"
    with open(temp_package / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg_raw, f)
        
    pkg_updated = load_package_json(temp_package)
    with pytest.raises(ValueError, match="Tìm thấy nhiều tệp source/original.*"):
        resolve_source_file(temp_package, pkg_updated)

def test_pdf_profiling(temp_package):
    """Test profiling tệp PDF native (chứa văn bản gốc)."""
    # Tạo PDF native thật bằng fitz
    pdf_path = temp_package / "source" / "original.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Báo giá thiết bị đóng cắt ABB năm 2026. Ngày báo giá: 20/06/2026. Hiệu lực: 31-12-2026.")
    doc.save(pdf_path)
    doc.close()
    
    from mep_quotation.package.loader import load_package_json
    pkg = load_package_json(temp_package)
    
    profile = profile_source_file(temp_package, pkg)
    
    assert profile.detected_file_type == "pdf"
    assert profile.technical_readability.is_supported_file_type is True
    assert profile.technical_readability.has_native_text is True
    assert profile.technical_readability.requires_ocr is False
    assert profile.source_role == SourceRole.supplier_quotation_candidate
    assert profile.recommended_next_action == RecommendedNextAction.run_pdf_native_pipeline
    
    # Kiểm tra date candidates
    dates = [d.date for d in profile.date_candidates]
    assert "2026-06-20" in dates
    assert "2026-12-31" in dates

def test_excel_xlsx_profiling(temp_package):
    """Test profiling tệp Excel XLSX hợp lệ."""
    # Sửa package metadata trỏ source_pdf sang empty để scan auto
    with open(temp_package / "package.json", "r", encoding="utf-8") as f:
        pkg_raw = json.load(f)
    pkg_raw["files"]["source_pdf"] = ""
    with open(temp_package / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg_raw, f)
        
    # Tạo XLSX thật bằng openpyxl
    xlsx_path = temp_package / "source" / "original.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bảng giá 2026"
    ws.append(["Mã hàng", "Mô tả sản phẩm", "Đơn giá niêm yết"])
    ws.append(["ABB-01", "MCB 1P 16A 6kA", 85000])
    wb.save(xlsx_path)
    wb.close()
    
    from mep_quotation.package.loader import load_package_json
    pkg = load_package_json(temp_package)
    
    profile = profile_source_file(temp_package, pkg)
    
    assert profile.detected_file_type == "excel_xlsx"
    assert profile.technical_readability.sheet_count == 1
    assert profile.source_role == SourceRole.supplier_price_list_candidate
    assert profile.recommended_next_action == RecommendedNextAction.run_excel_intake_pipeline_later

def test_image_profiling(temp_package):
    """Test profiling tệp hình ảnh PNG/JPG."""
    # Sửa package metadata
    with open(temp_package / "package.json", "r", encoding="utf-8") as f:
        pkg_raw = json.load(f)
    pkg_raw["files"]["source_pdf"] = ""
    with open(temp_package / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg_raw, f)
        
    # Tạo tệp ảnh thật bằng Pillow
    img_path = temp_package / "source" / "original.png"
    img = Image.new("RGB", (300, 200), color="white")
    img.save(img_path)
    
    from mep_quotation.package.loader import load_package_json
    pkg = load_package_json(temp_package)
    
    profile = profile_source_file(temp_package, pkg)
    
    assert profile.detected_file_type == "image"
    assert profile.technical_readability.image_width == 300
    assert profile.technical_readability.image_height == 200
    assert profile.technical_readability.requires_ocr is True
    assert profile.recommended_next_action == RecommendedNextAction.manual_profile_required

def test_unsupported_and_limited_file_types(temp_package):
    """Test giới hạn hỗ trợ cho các tệp XLS, CSV, WEBP."""
    from mep_quotation.package.loader import load_package_json
    pkg = load_package_json(temp_package)
    
    # 1. CSV (limited support)
    csv_path = temp_package / "source" / "original.csv"
    csv_path.write_text("Col1,Col2\nVal1,Val2")
    profile = profile_source_file(temp_package, pkg)
    assert profile.detected_file_type == "csv"
    assert profile.technical_readability.is_supported_file_type is False
    assert profile.recommended_next_action == RecommendedNextAction.unsupported_file_type
    assert any(w.code == "limited_support" for w in profile.warnings)
    
    # Clean file
    csv_path.unlink()
    
    # 2. WEBP (limited support)
    webp_path = temp_package / "source" / "original.webp"
    webp_path.write_text("fake webp data")
    profile_webp = profile_source_file(temp_package, pkg)
    assert profile_webp.detected_file_type == "webp"
    assert profile_webp.technical_readability.is_supported_file_type is False
    assert profile_webp.recommended_next_action == RecommendedNextAction.unsupported_file_type
    assert any(w.code == "limited_support" for w in profile_webp.warnings)
    assert profile_webp.technical_readability.image_width is None
    assert profile_webp.technical_readability.image_height is None
    assert profile_webp.technical_readability.requires_ocr is False
    webp_path.unlink()
    
    # 3. Định dạng hoàn toàn không hỗ trợ (ví dụ .txt)
    txt_path = temp_package / "source" / "original.txt"
    txt_path.write_text("text")
    profile_txt = profile_source_file(temp_package, pkg)
    assert profile_txt.detected_file_type == "unsupported"
    assert any(w.code == "unsupported_file_type" for w in profile_txt.warnings)

def test_cli_profile_source(temp_package):
    """Test CLI subcommand profile-source và atomic write."""
    # Tạo PDF thật
    pdf_path = temp_package / "source" / "original.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Báo giá Schneider 2026")
    doc.save(pdf_path)
    doc.close()
    
    class Args:
        package_path = str(temp_package)
        overwrite = False

    # 1. Chạy CLI lần đầu -> Tạo file thành công
    handle_profile_source(Args())
    profile_file = temp_package / "source" / "source_profile.json"
    assert profile_file.exists()
    
    # Kiểm tra cấu trúc lưu trữ và atomic write (không tồn tại file .tmp thừa)
    assert not profile_file.with_suffix(".tmp").exists()
    
    # Kiểm tra package.json được cập nhật trường source_profile
    with open(temp_package / "package.json", "r", encoding="utf-8") as f:
        pkg_json = json.load(f)
    assert pkg_json["files"]["source_profile"] == "source/source_profile.json"

    # 2. Chạy lại khi file đã tồn tại và overwrite = False -> Lỗi SystemExit
    with pytest.raises(SystemExit):
        handle_profile_source(Args())

    # 3. Chạy lại khi overwrite = True -> Ghi đè thành công
    class ArgsOverwrite:
        package_path = str(temp_package)
        overwrite = True
    handle_profile_source(ArgsOverwrite())
    assert profile_file.exists()
    assert not profile_file.with_suffix(".tmp").exists()
    
    # Kiểm tra JSON valid
    with open(profile_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["detected_file_type"] == "pdf"

def test_integrity_and_backward_compatibility(temp_package):
    """Test kiểm định package_integrity và tính tương thích ngược (Backward Compatibility)."""
    # 1. Tương thích ngược: package chưa chạy profile-source (chưa có tệp và chưa khai báo)
    # Vì package này cũng chưa có normalized.json hay corrections.json thật, ta mock hàm load để tránh crash các bước trước
    # Hoặc ta ghi đè hàm load trong test
    
    # Hãy tạo các file trống hợp lệ để validate_package_integrity vượt qua các bước check trước
    # 1.1. Tạo normalized.json giả lập
    norm_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "supplier_code": "AUT",
        "quotation_date": "2026-06-20",
        "currency": "VND",
        "source_normalized_draft": "normalized/normalized_draft.json",
        "source_normalized_draft_sha256": "",
        "source_review_decisions": "review/review_decisions.json",
        "source_review_decisions_sha256": "",
        "item_count": 0,
        "export_summary": {
            "draft_item_count": 0,
            "approved_count": 0,
            "edited_count": 0,
            "rejected_count": 0,
            "unreviewed_count": 0,
            "exported_item_count": 0
        },
        "warnings": [],
        "items": [],
        "created_at": "2026-07-03T10:00:00Z",
        "updated_at": "2026-07-03T10:00:00Z"
    }
    (temp_package / "normalized").mkdir(exist_ok=True)
    with open(temp_package / "normalized" / "normalized.json", "w", encoding="utf-8") as f:
        json.dump(norm_data, f)
        
    # 1.2. Tạo corrections.json giả lập
    corr_data = {
        "schema_version": "1.0",
        "quotation_id": "AUT_20260620_001",
        "corrections": []
    }
    (temp_package / "corrections").mkdir(exist_ok=True)
    with open(temp_package / "corrections" / "corrections.json", "w", encoding="utf-8") as f:
        json.dump(corr_data, f)
        
    # Chạy validate_package_integrity khi chưa có source_profile -> Phải pass (tương thích ngược)
    validate_package_integrity(temp_package) # Nếu pass thì không raise exception

    # 2. Có khai báo source_profile trong package.json nhưng file thực tế không tồn tại -> ValueError
    with open(temp_package / "package.json", "r", encoding="utf-8") as f:
        pkg_raw = json.load(f)
    pkg_raw["files"]["source_profile"] = "source/source_profile.json"
    with open(temp_package / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg_raw, f)
        
    with pytest.raises(ValueError, match="source_profile is declared in package metadata.*but the file does not exist"):
        validate_package_integrity(temp_package)

    # 3. Tạo file source_profile.json hợp lệ
    # Cần tạo cả file original.pdf thật
    pdf_path = temp_package / "source" / "original.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Schneider")
    doc.save(pdf_path)
    doc.close()
    
    class Args:
        package_path = str(temp_package)
        overwrite = True
    handle_profile_source(Args()) # Sinh file source_profile.json và update package.json tự động
    
    # Chạy validate_package_integrity với profile đầy đủ -> Phải pass
    validate_package_integrity(temp_package)

    # 4. Thử nghiệm SHA256 mismatch -> ValueError
    # Sửa SHA256 trong file source_profile.json thành sai lệch
    profile_file = temp_package / "source" / "source_profile.json"
    with open(profile_file, "r", encoding="utf-8") as f:
        prof_data = json.load(f)
    prof_data["source_sha256"] = "wronghash123"
    with open(profile_file, "w", encoding="utf-8") as f:
        json.dump(prof_data, f)
        
    with pytest.raises(ValueError, match="source_profile.source_sha256.*does not match actual source file sha256"):
        validate_package_integrity(temp_package)
