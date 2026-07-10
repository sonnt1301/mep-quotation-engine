# -*- coding: utf-8 -*-
import json
import csv
import datetime
import pdfplumber
import shutil
import fitz
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Tuple

from tools.feasibility.profile_config_loader import load_profile_config
from tools.feasibility.profile_runner import (
    parse_page_from_config,
    validate_extracted_item
)

def load_bridge_items(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_review_sample(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["source_page"] = int(row["source_page"])
            row["unit_price"] = int(float(row["unit_price"]))
            items.append(dict(row))
    return items

def load_duplicate_review(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["occurrence_count"] = int(row["occurrence_count"])
            row["distinct_price_count"] = int(row["distinct_price_count"])
            items.append(dict(row))
    return items

def build_review_item_key(item: Dict[str, Any]) -> str:
    """Tạo khóa duy nhất và ổn định cho item review."""
    supplier = item.get("supplier_code", "").strip()
    page = item.get("source_page", 1)
    code = item.get("normalized_material_code", "").strip()
    price = item.get("unit_price", 0)
    return f"{supplier}_P{page}_{code}_{price}"

def compute_default_amount(quantity: Any, unit_price: Any) -> int:
    """Tính amount = quantity * unit_price."""
    try:
        qty = float(quantity)
        price = int(float(unit_price))
        return int(qty * price)
    except (ValueError, TypeError):
        return 0

def validate_decision_reason(decision: str, human_note: str) -> Tuple[bool, str]:
    """Validate lý do/note của quyết định."""
    note_clean = (human_note or "").strip()
    if decision in ["REJECT", "EDIT_AND_APPROVE", "NEEDS_INVESTIGATION"]:
        if not note_clean:
            return False, f"Nút '{decision}' yêu cầu ghi chú giải trình lý do (human_note) không được rỗng."
    return True, ""

def validate_duplicate_group_decision(decision: str, human_note: str, risk_level: str) -> Tuple[bool, str]:
    """Validate lý do đối với quyết định cấp nhóm trùng mã."""
    note_clean = (human_note or "").strip()
    if risk_level == "HIGH" and not note_clean:
        return False, "Nhóm trùng mã rủi ro HIGH bắt buộc phải ghi chú lý do hành động review."
    return True, ""

def load_review_decisions(path: Path) -> Dict[str, Dict[str, Any]]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_review_decisions(json_path: Path, csv_path: Path, decisions: Dict[str, Dict[str, Any]]):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
        
    if not decisions:
        return
        
    headers = [
        "review_decision_id", "review_item_key", "review_mode", "supplier_code", 
        "source_page", "normalized_material_code_original", "normalized_material_code_reviewed", 
        "description_original", "description_reviewed", "unit_original", "unit_reviewed", 
        "quantity_reviewed", "unit_price_original", "unit_price_reviewed", "amount_reviewed", 
        "currency_original", "currency_reviewed", "decision", "human_note", "reviewer", 
        "reviewed_at", "provenance", "source_evidence_text"
    ]
    
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for key, dec in decisions.items():
            writer.writerow({h: dec.get(h, "") for h in headers})

def summarize_review_progress(items: List[Dict[str, Any]], decisions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Tổng hợp tiến độ review phục vụ dashboard."""
    total = len(items)
    reviewed = 0
    unreviewed = 0
    counts = {
        "APPROVE": 0,
        "EDIT_AND_APPROVE": 0,
        "REJECT": 0,
        "NEEDS_INVESTIGATION": 0,
        "ACCEPT_WITH_LIMITATION": 0
    }
    
    for it in items:
        key = build_review_item_key(it)
        if key in decisions:
            reviewed += 1
            dec = decisions[key].get("decision", "")
            if dec in counts:
                counts[dec] += 1
        else:
            unreviewed += 1
            
    progress = (reviewed / total * 100) if total > 0 else 0.0
    has_warning = counts["NEEDS_INVESTIGATION"] > 0 or counts["REJECT"] > 0
    
    return {
        "total_rows": total,
        "reviewed": reviewed,
        "unreviewed": unreviewed,
        "progress_percent": round(progress, 2),
        "counts": counts,
        "has_warning": has_warning
    }

def filter_items(items: List[Dict[str, Any]], 
                 supplier: str, 
                 page: str, 
                 status_filter: str, 
                 search_query: str, 
                 decisions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bộ lọc danh sách item phục vụ giao diện hiển thị."""
    filtered = []
    for it in items:
        if supplier != "ALL" and it.get("supplier_code") != supplier:
            continue
            
        if page != "ALL":
            try:
                if int(it.get("source_page")) != int(page):
                    continue
            except (ValueError, TypeError):
                continue
                
        key = build_review_item_key(it)
        dec_info = decisions.get(key, {})
        current_status = dec_info.get("decision", "UNREVIEWED")
        if status_filter != "ALL" and current_status != status_filter:
            continue
            
        q = (search_query or "").strip().lower()
        if q:
            code = it.get("normalized_material_code", "").lower()
            desc = it.get("description", "").lower()
            if q not in code and q not in desc:
                continue
                
        filtered.append(it)
    return filtered

# ========================================================
# CÁC HELPER MỚI CHO PHASE 2A.3
# ========================================================

def resolve_selected_profile_config(supplier_code: str) -> Path:
    """Trả về đường dẫn tệp JSON cấu hình tương ứng."""
    supplier_clean = (supplier_code or "").strip().upper()
    if supplier_clean not in ["ABB", "LS", "CHINT"]:
        raise ValueError(f"Chỉ hỗ trợ nhà cung cấp ABB, LS, CHINT. Không hỗ trợ: '{supplier_code}'")
    
    config_path = Path("tools/feasibility/profile_configs") / f"{supplier_clean.lower()}_profile_v1.json"
    return config_path

def create_review_session_folder(supplier_code: str) -> Path:
    """Tạo thư mục session có định dạng: feasibility_outputs/profile_visual_review_sessions/{timestamp}_{supplier}."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = Path("feasibility_outputs/profile_visual_review_sessions") / f"{timestamp}_{supplier_code.upper()}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

def validate_pdf_input(pdf_path_str: str) -> Tuple[bool, str]:
    """Kiểm tra đường dẫn file PDF tồn tại và đúng định dạng."""
    if not pdf_path_str:
        return False, "Đường dẫn tệp PDF trống."
        
    p = Path(pdf_path_str)
    if not p.exists():
        return False, f"Tệp tin không tồn tại tại đường dẫn: '{pdf_path_str}'"
    if p.suffix.lower() != ".pdf":
        return False, f"Định dạng tệp không hợp lệ: '{pdf_path_str}'. Phải là tệp .pdf"
        
    return True, ""

def run_parser_on_pdf(supplier_code: str, pdf_path: Path, config_path: Path, output_dir: Path) -> Dict[str, Any]:
    """Chạy parser bóc tách PDF sử dụng file config được chỉ định và ghi kết quả vào output_dir."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
    # Nạp cấu hình JSON profile
    config = load_profile_config(str(config_path.resolve()))
    
    valid_extracted_items = []
    invalid_extracted_items = []
    page_summaries = []
    
    global_rules = config["global_rules"]
    validation = config["validation"]
    patterns = config["material_code_patterns"]
    
    # Thực hiện bóc tách PDF
    with pdfplumber.open(pdf_path) as pdf:
        for layout in config.get("layouts", []):
            layout_name = layout["layout_name"]
            for page_num in layout.get("pages", []):
                idx = page_num - 1
                if idx < 0 or idx >= len(pdf.pages):
                    continue
                    
                page = pdf.pages[idx]
                try:
                    raw_items, pf, l_name, raw_detected, skipped = parse_page_from_config(
                        page, page_num, layout, global_rules, validation, supplier_code
                    )
                    
                    page_valid_items = []
                    page_invalid_items = []
                    page_errors_sample = []
                    
                    for item in raw_items:
                        is_valid, errors, warnings = validate_extracted_item(item, validation, patterns)
                        
                        if is_valid:
                            item.validation_status = "valid"
                            item.errors = errors
                            item.warnings = warnings
                            page_valid_items.append(item.to_dict())
                        else:
                            item.validation_status = "invalid"
                            item.errors = errors
                            item.warnings = warnings
                            
                            invalid_record = {
                                "source_page": page_num,
                                "raw_item": item.to_dict(),
                                "errors": errors,
                                "warnings": warnings
                            }
                            page_invalid_items.append(invalid_record)
                            page_errors_sample.extend(errors)
                            
                    raw_count = len(raw_items)
                    valid_count = len(page_valid_items)
                    invalid_count = len(page_invalid_items)
                    invalid_ratio = (invalid_count / raw_count) if raw_count > 0 else 0.0
                    
                    status = "FAIL"
                    if valid_count >= 10 and invalid_ratio <= 0.05:
                        status = "PASS"
                    elif valid_count > 0:
                        status = "PARTIAL"
                        
                    page_summaries.append({
                        "page": page_num,
                        "status": status,
                        "raw_detected_rows": raw_detected,
                        "skipped_before_validation": skipped,
                        "validation_input_count": raw_count,
                        "valid_items_count": valid_count,
                        "invalid_items_count": invalid_count,
                        "invalid_ratio": round(invalid_ratio * 100, 1),
                        "errors_sample": list(set(page_errors_sample))[:5],
                        "detected_table_type": l_name
                    })
                    
                    valid_extracted_items.extend(page_valid_items)
                    invalid_extracted_items.extend(page_invalid_items)
                except Exception as e:
                    page_summaries.append({
                        "page": page_num,
                        "status": "FAIL",
                        "raw_detected_rows": 0,
                        "skipped_before_validation": 0,
                        "validation_input_count": 0,
                        "valid_items_count": 0,
                        "invalid_items_count": 0,
                        "invalid_ratio": 0.0,
                        "errors_sample": [str(e)],
                        "detected_table_type": layout_name
                    })
                    
    # Lưu các file JSON đầu ra của parser
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "profile_items_valid.json", "w", encoding="utf-8") as f:
        json.dump(valid_extracted_items, f, ensure_ascii=False, indent=2)
    with open(output_dir / "profile_items_invalid.json", "w", encoding="utf-8") as f:
        json.dump(invalid_extracted_items, f, ensure_ascii=False, indent=2)
    with open(output_dir / "profile_page_summary.json", "w", encoding="utf-8") as f:
        json.dump(page_summaries, f, ensure_ascii=False, indent=2)
        
    return {
        "valid_count": len(valid_extracted_items),
        "invalid_count": len(invalid_extracted_items),
        "page_summaries": page_summaries
    }

def run_bridge_on_session(supplier_code: str, session_dir: Path, original_pdf_path: Path) -> Path:
    """Chạy cầu nối (bridge dry-run) trên dữ liệu của session và lưu tệp bridged items JSON."""
    valid_json_path = session_dir / "profile_items_valid.json"
    if not valid_json_path.exists():
        raise FileNotFoundError(f"Session valid items JSON not found at: {valid_json_path}")
        
    with open(valid_json_path, "r", encoding="utf-8") as f:
        valid_items = json.load(f)
        
    bridged_items = []
    for it in valid_items:
        mat_code = it.get("material_code", "").strip()
        unit_price = it.get("unit_price", 0)
        desc = it.get("description", "").strip()
        unit = it.get("unit", "cái").strip()
        
        provenance = f"Source PDF: {original_pdf_path.name}, Page: {it.get('source_page')}, Layout: {it.get('layout_name')}, Method: {it.get('extraction_method')}"
        
        bridged_it = {
            "supplier_code": supplier_code.upper(),
            "source_page": it.get("source_page"),
            "source_layout_name": it.get("layout_name"),
            "source_material_code": it.get("material_code"),
            "normalized_material_code": mat_code.upper(),
            "description": desc,
            "unit": unit,
            "unit_price": int(unit_price),
            "currency": "VND",
            "product_family": it.get("product_family"),
            "rated_current": it.get("rated_current"),
            "breaking_capacity": it.get("breaking_capacity"),
            "pole": it.get("pole"),
            "source_extraction_method": it.get("extraction_method"),
            "source_evidence_text": it.get("evidence_text"),
            "provenance": provenance,
            "bridge_status": "bridged",
            "bridge_warnings": []
        }
        bridged_items.append(bridged_it)
        
    # Ghi tệp JSON cầu nối cục bộ cho session
    session_bridge_items_path = session_dir / "profile_bridge_items.json"
    with open(session_bridge_items_path, "w", encoding="utf-8") as f:
        json.dump(bridged_items, f, ensure_ascii=False, indent=2)
        
    # Tạo Summary JSON cho session
    groups = {}
    for it in bridged_items:
        key = (it["supplier_code"], it["normalized_material_code"])
        if key not in groups:
            groups[key] = []
        groups[key].append(it["unit_price"])
        
    duplicate_code_group_count = 0
    duplicate_code_with_different_price_count = 0
    for key, prices in groups.items():
        if len(prices) > 1:
            duplicate_code_group_count += 1
            if len(set(prices)) > 1:
                duplicate_code_with_different_price_count += 1
                
    session_bridge_summary = {
        "bridge_version": "1.0.0",
        "generated_at": datetime.datetime.now().isoformat() + "Z",
        "mode": "dry_run",
        "source_pdf": str(original_pdf_path.resolve()),
        "bridge_status": "PASS",
        "total_bridged_items": len(bridged_items),
        "duplicate_code_group_count": duplicate_code_group_count,
        "duplicate_code_with_different_price_count": duplicate_code_with_different_price_count,
        "integration_readiness": {
            "ready_for_write_to_main_pipeline": False,
            "reason": "Đây mới là phase Integration Bridge Dry-run (Chạy cầu nối khô). Toàn bộ dữ liệu chưa được phép ghi đè hay đẩy trực tiếp vào cơ sở dữ liệu hoặc main pipeline chính của dự án."
        }
    }
    
    with open(session_dir / "profile_bridge_summary.json", "w", encoding="utf-8") as f:
        json.dump(session_bridge_summary, f, ensure_ascii=False, indent=2)
        
    return session_bridge_items_path

def build_duplicate_review_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tạo danh sách nhóm trùng mã động từ danh sách items."""
    groups = {}
    for it in items:
        key = (it.get("supplier_code", "").strip(), it.get("normalized_material_code", "").strip())
        if key not in groups:
            groups[key] = []
        groups[key].append(it)
        
    dup_rows = []
    for (supplier, code), group_items in groups.items():
        if len(group_items) > 1:
            occurrence_count = len(group_items)
            prices = sorted(list(set(it.get("unit_price", 0) for it in group_items)))
            distinct_price_count = len(prices)
            pages = sorted(list(set(it.get("source_page", 1) for it in group_items)))
            descriptions = [it.get("description", "") for it in group_items]
            evidences = [it.get("source_evidence_text", "") for it in group_items]
            
            if distinct_price_count > 1:
                risk_level = "HIGH"
            elif len(set(descriptions)) > 1 or len(set(pages)) > 1:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
                
            recommended_write_key = "supplier_code + normalized_material_code"
            if risk_level == "HIGH":
                recommended_write_key += " + source_page + unit_price + description"
            elif risk_level == "MEDIUM":
                recommended_write_key += " + source_page + description"
                
            dup_rows.append({
                "supplier_code": supplier,
                "normalized_material_code": code,
                "occurrence_count": occurrence_count,
                "distinct_price_count": distinct_price_count,
                "prices": "; ".join(map(str, prices)),
                "source_pages": "; ".join(map(str, pages)),
                "descriptions_sample": " | ".join(list(set(descriptions))[:3]),
                "evidence_sample": " | ".join(list(set(evidences))[:2]),
                "risk_level": risk_level,
                "recommended_write_key": recommended_write_key,
                "human_decision": "PENDING",
                "human_note": ""
            })
            
    risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    dup_rows.sort(key=lambda x: (risk_order[x["risk_level"]], x["supplier_code"], x["normalized_material_code"]))
    return dup_rows

@lru_cache(maxsize=128)
def _render_pdf_page_to_image_cached(pdf_path_str: str, page_number: int, scale: float = 1.5) -> bytes:
    doc = fitz.open(pdf_path_str)
    total_pages = len(doc)
    if page_number < 1 or page_number > total_pages:
        doc.close()
        raise ValueError(f"Page number {page_number} out of range [1, {total_pages}]")
    page = doc.load_page(page_number - 1)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return img_bytes

def render_pdf_page_to_image(pdf_path: Path, page_number: int, scale: float = 1.5) -> bytes:
    """Render một trang PDF thành ảnh PNG dạng bytes có sử dụng cache."""
    return _render_pdf_page_to_image_cached(str(pdf_path.resolve()), page_number, scale)

def resolve_session_pdf_path(session_dir_path: Path) -> Path:
    """Tìm kiếm tệp PDF duy nhất trong thư mục session."""
    if not session_dir_path.exists():
        raise FileNotFoundError(f"Thư mục session không tồn tại: {session_dir_path}")
    pdf_files = list(session_dir_path.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"Không tìm thấy file PDF nào trong thư mục session: {session_dir_path}")
    return pdf_files[0]

def validate_pdf_page_number(pdf_path: Path, page_number: int) -> Tuple[bool, str]:
    """Kiểm tra xem số trang có hợp lệ trong file PDF không."""
    if not pdf_path.exists():
        return False, f"File PDF không tồn tại tại: {pdf_path}"
    try:
        doc = fitz.open(str(pdf_path.resolve()))
        total_pages = len(doc)
        doc.close()
        if page_number < 1 or page_number > total_pages:
            return False, f"Số trang {page_number} vượt ngoài phạm vi [1, {total_pages}] của file PDF."
        return True, ""
    except Exception as e:
        return False, f"Lỗi khi mở file PDF để kiểm tra số trang: {str(e)}"
