import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

def safe_number(value: Any, default: float = 0.0) -> float:
    """
    Ép kiểu dữ liệu số an toàn, chống crash khi gặp giá trị None, trống hoặc lỗi ép kiểu.
    """
    try:
        if value is None or str(value).strip() == "" or str(value).lower() == "none":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default

def classify_draft_item(item: Dict[str, Any]) -> str:
    """
    Phân loại draft item thành các nhóm: likely_item, weak_item, title_or_header, section_or_note, incomplete_candidate, rejected_noise.
    """
    desc = str(item.get("description", "")).strip()
    if not desc:
        return "rejected_noise"
        
    desc_lower = desc.lower()
    unit = item.get("unit")
    qty = item.get("quantity")
    price = item.get("unit_price")
    amount = item.get("amount")
    
    # Đánh giá tín hiệu vật tư thực tế
    has_real_unit = unit is not None and str(unit).strip() != "" and str(unit).lower() != "none"
    has_real_qty = qty is not None and safe_number(qty) > 0
    has_real_amount = amount is not None and safe_number(amount) > 0
    
    # Từ khóa tiêu đề mạnh (Strong Title Keywords)
    strong_title_keywords = [
        "bảng dự toán", "bảng giá", "báo giá", "dự toán", "phụ lục", 
        "quotation", "price list"
    ]
    
    # Heuristics 1: Bắt tiêu đề mạnh trước nếu thiếu toàn bộ unit, quantity, amount
    if not has_real_unit and not has_real_qty and not has_real_amount:
        for kw in strong_title_keywords:
            if kw in desc_lower:
                return "title_or_header"
                
    # Heuristics 2: Xử lý số năm (1900 - 2100) bị bắt nhầm thành đơn giá
    has_price_is_year = False
    if price is not None:
        val = safe_number(price)
        if 1900.0 <= val <= 2100.0:
            # Từ khóa tiêu đề chung
            general_title_keywords = strong_title_keywords + [
                "chương", "mục", "trang", "danh mục", "phạm vi", "hiệu lực", "bảng kê",
                "tên chương", "tên hạng mục", "hạng mục", "bảng tổng hợp", "tổng hợp", "bảng"
            ]
            if not has_real_unit and not has_real_qty and not has_real_amount:
                for kw in general_title_keywords:
                    if kw in desc_lower:
                        has_price_is_year = True
                        break
                        
    # Xác định các tín hiệu số liệu sau khi loại trừ năm
    has_price = price is not None and safe_number(price) > 0 and not has_price_is_year
    has_qty = qty is not None and safe_number(qty) > 0
    has_unit = has_real_unit
    
    # Từ khóa tiêu đề chương/mục/bảng biểu chung
    title_keywords = [
        "bảng dự toán", "bảng giá", "báo giá", "phụ lục", "chương", "mục", 
        "trang", "danh mục", "phạm vi", "hiệu lực", "bảng kê", "quotation", 
        "tên chương", "tên hạng mục", "hạng mục", "bảng tổng hợp", "tổng hợp", "bảng", "dự toán", "price list"
    ]
    # Từ khóa ghi chú, tổng hợp thanh toán hoặc thông tin phụ
    section_keywords = [
        "ghi chú", "tổng cộng", "cộng", "thanh toán", "bảo hành", 
        "thời gian", "địa điểm", "giá trị", "vat", "thuế", "tổng tiền", 
        "chuyển khoản", "tạm ứng", "phạt", "giao hàng", "bằng chữ"
    ]
    
    # 1. Nếu không có số lượng và đơn giá thực tế
    if not has_price and not has_qty:
        for kw in title_keywords:
            if kw in desc_lower:
                return "title_or_header"
        for kw in section_keywords:
            if kw in desc_lower:
                return "section_or_note"
        if len(desc) < 15 and not has_unit:
            return "rejected_noise"
            
        return "incomplete_candidate"
        
    # 2. Nếu có giá trị số liệu cụ thể
    if has_price and has_qty and has_unit:
        return "likely_item"
        
    if has_price or has_qty:
        for kw in ["tổng cộng", "cộng", "tổng tiền"]:
            if kw in desc_lower:
                return "section_or_note"
        return "weak_item"
        
    return "incomplete_candidate"

def format_warnings_vietnamese(warnings: List[Any]) -> List[str]:
    """
    Dịch mã cảnh báo kỹ thuật sang tiếng Việt thân thiện.
    Không dump JSON thô hoặc dict kỹ thuật.
    """
    if not warnings:
        return []
        
    mapping = {
        "missing_unit": "Thiếu đơn vị",
        "missing_quantity": "Thiếu số lượng",
        "missing_unit_price": "Thiếu đơn giá",
        "missing_description": "Thiếu mô tả",
        "low_confidence": "Độ tin cậy thấp",
        "rejected_weak_candidate": "Ứng viên yếu, cần kiểm tra",
        "amount_mismatch_recomputed": "Thành tiền không khớp số lượng x đơn giá"
    }
    
    translated = []
    for w in warnings:
        code = ""
        if isinstance(w, dict):
            code = w.get("code", "")
        elif isinstance(w, str):
            code = w
            
        if code in mapping:
            translated.append(mapping[code])
        else:
            if isinstance(w, dict) and w.get("message"):
                translated.append(str(w["message"]))
            else:
                translated.append(str(w))
                
    return translated

def get_dashboard_stats(items: List[Dict[str, Any]], decisions_map: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """
    Tính toán các chỉ số dashboard tóm tắt kết quả đọc và tiến trình rà soát (Đã tối ưu hóa phản ánh thật).
    """
    stats = {
        "total": len(items),
        "likely_item": 0,
        "weak_item": 0,
        "noise_or_title": 0,
        "approved": 0,
        "edited": 0,
        "rejected": 0,
        "unreviewed": 0,
        "exportable": 0
    }
    
    for item in items:
        d_id = item.get("draft_item_id")
        dec = decisions_map.get(d_id, {})
        dec_type = dec.get("decision_type", "unreviewed")
        
        # Thống kê rà soát
        if dec_type == "approved":
            stats["approved"] += 1
            stats["exportable"] += 1
        elif dec_type == "edited":
            stats["edited"] += 1
            stats["exportable"] += 1
        elif dec_type == "rejected":
            stats["rejected"] += 1
        else:
            stats["unreviewed"] += 1
            
        # Phân loại theo heuristics
        cls = classify_draft_item(item)
        if cls == "likely_item":
            stats["likely_item"] += 1
        elif cls == "weak_item":
            stats["weak_item"] += 1
        elif cls in ["title_or_header", "section_or_note", "rejected_noise"]:
            stats["noise_or_title"] += 1
            
    return stats

def filter_and_sort_items(
    items: List[Dict[str, Any]], 
    decisions_map: Dict[str, Dict[str, Any]], 
    filter_type: str, 
    sort_by: str,
    show_hidden: bool = False
) -> List[Dict[str, Any]]:
    """
    Lọc và sắp xếp danh sách items hỗ trợ bộ lọc ẩn dòng tiêu đề/rác theo mặc định.
    """
    filtered = []
    for item in items:
        # Bộ lọc rác mặc định
        cls = classify_draft_item(item)
        if not show_hidden:
            if cls in ["title_or_header", "section_or_note", "rejected_noise"]:
                continue
                
        d_id = item.get("draft_item_id")
        dec = decisions_map.get(d_id, {})
        dec_type = dec.get("decision_type", "unreviewed")
        
        unit = item.get("unit")
        qty = item.get("quantity")
        price = item.get("unit_price")
        conf = item.get("confidence", 1.0)
        warnings = item.get("warnings", [])
        
        # Lọc nâng cao
        if filter_type == "Tất cả":
            pass
        elif filter_type == "Chưa rà soát":
            if dec_type != "unreviewed": continue
        elif filter_type == "Đã chấp nhận":
            if dec_type != "approved": continue
        elif filter_type == "Đã chỉnh sửa":
            if dec_type != "edited": continue
        elif filter_type == "Đã từ chối":
            if dec_type != "rejected": continue
        elif filter_type == "Thiếu đơn giá":
            if price is not None and price > 0: continue
        elif filter_type == "Thiếu đơn vị":
            if unit is not None and str(unit).strip() != "" and str(unit).lower() != "none": continue
        elif filter_type == "Thiếu số lượng":
            if qty is not None and qty > 0: continue
        elif filter_type == "Độ tin cậy thấp":
            if conf >= 0.6: continue
        elif filter_type == "Có cảnh báo":
            if not warnings: continue
        elif filter_type == "Có giá":
            if price is None or price <= 0: continue
            
        filtered.append(item)
        
    # Sắp xếp
    if sort_by == "Độ tin cậy tăng dần":
        filtered.sort(key=lambda x: x.get("confidence", 1.0))
    elif sort_by == "Có giá trước":
        filtered.sort(key=lambda x: (x.get("unit_price") or 0.0) <= 0.0)
    elif sort_by == "Chưa rà soát trước":
        filtered.sort(key=lambda x: decisions_map.get(x.get("draft_item_id"), {}).get("decision_type", "unreviewed") != "unreviewed")
    elif sort_by == "Thứ tự xuất hiện":
        filtered.sort(key=lambda x: x.get("draft_item_id", ""))
        
    return filtered

def diagnose_read_results(items: List[Dict[str, Any]], decisions_map: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Phân loại chẩn đoán kết quả đọc thành 3 nhóm: đọc tốt, thiếu dữ liệu, nghi rác/tiêu đề.
    """
    groups = {
        "good": [],
        "missing_data": [],
        "suspected_trash": []
    }
    
    for item in items:
        cls = classify_draft_item(item)
        if cls in ["title_or_header", "section_or_note", "rejected_noise"]:
            groups["suspected_trash"].append(item)
        elif cls in ["weak_item", "incomplete_candidate"]:
            groups["missing_data"].append(item)
        else:
            groups["good"].append(item)
            
    return groups

def resolve_item_evidence(
    item: Dict[str, Any], 
    package_path: Optional[Path] = None, 
    artifact_paths: Optional[Dict[str, Path]] = None
) -> Tuple[Optional[Path], Optional[int], str]:
    """
    Phân giải bằng chứng trực quan cho dòng vật tư.
    Trả về (image_path_on_disk, page_number_resolved, text_evidence_resolved).
    """
    if artifact_paths is None:
        artifact_paths = {}

    # 1. Trích xuất text evidence từ item
    evidence_field = item.get("evidence_text") or item.get("evidence")
    text_evidence = None
    
    def extract_text_from_obj(obj: Any) -> Optional[str]:
        if not obj:
            return None
        if isinstance(obj, str):
            return obj.strip()
        if isinstance(obj, dict):
            for key in ["raw_evidence_text", "evidence_text", "text"]:
                if key in obj and obj[key]:
                    return str(obj[key]).strip()
            return json.dumps(obj, ensure_ascii=False)
        if isinstance(obj, list):
            parts = []
            for sub_obj in obj:
                part = extract_text_from_obj(sub_obj)
                if part:
                    parts.append(part)
            if parts:
                return "\n".join(parts)
        return str(obj).strip()

    text_evidence = extract_text_from_obj(evidence_field)
    
    # 2. Cố gắng fallback sang row_candidates / item_candidates nếu text_evidence trống/mặc định
    if (not text_evidence or text_evidence == "Không tìm thấy bằng chứng text cho dòng này.") and package_path:
        row_id = item.get("source_row_candidate_id") or item.get("row_candidate_id")
        item_cand_id = item.get("source_item_candidate_id") or item.get("item_candidate_id")
        
        if item_cand_id and "item_candidates" in artifact_paths and artifact_paths["item_candidates"].exists():
            try:
                with open(artifact_paths["item_candidates"], "r", encoding="utf-8") as f:
                    cand_data = json.load(f)
                cands = cand_data.get("candidates", []) if isinstance(cand_data, dict) else cand_data
                for cand in cands:
                    if cand.get("item_candidate_id") == item_cand_id:
                        cand_ev = cand.get("evidence") or cand.get("evidence_text")
                        cand_txt = extract_text_from_obj(cand_ev)
                        if cand_txt:
                            text_evidence = cand_txt
                            break
            except Exception:
                pass
                
        if (not text_evidence or text_evidence == "Không tìm thấy bằng chứng text cho dòng này.") and row_id and "row_candidates" in artifact_paths and artifact_paths["row_candidates"].exists():
            try:
                with open(artifact_paths["row_candidates"], "r", encoding="utf-8") as f:
                    row_data = json.load(f)
                rows = row_data.get("candidates", []) if isinstance(row_data, dict) else row_data
                for row in rows:
                    if row.get("row_candidate_id") == row_id:
                        row_ev = row.get("evidence") or row.get("evidence_text")
                        row_txt = extract_text_from_obj(row_ev)
                        if row_txt:
                            text_evidence = row_txt
                            break
            except Exception:
                pass

    if not text_evidence:
        text_evidence = "Không tìm thấy bằng chứng text cho dòng này."

    # 3. Phân giải page_number
    page_number = None
    if "page_number" in item and item["page_number"] is not None:
        try:
            page_number = int(item["page_number"])
        except ValueError:
            pass
            
    if page_number is None and text_evidence:
        match = re.search(r"\b(?:trang|page)\s*(\d+)\b", text_evidence.lower())
        if match:
            page_number = int(match.group(1))
            
    if page_number is None:
        d_id = item.get("draft_item_id", "")
        parts = d_id.split("_")
        if len(parts) >= 5:
            try:
                page_number = int(parts[3])
            except ValueError:
                pass

    # 4. Định vị tệp ảnh
    image_path = None
    if package_path:
        pages_dir = package_path / "source" / "pages"
        
        if page_number is not None:
            possible_filename = f"page_{page_number:04d}.png"
            img_file = pages_dir / possible_filename
            if img_file.exists():
                image_path = img_file
                
        if image_path is None:
            if pages_dir.exists() and pages_dir.is_dir():
                all_pages = sorted(list(pages_dir.glob("page_*.png")))
                if all_pages:
                    image_path = all_pages[0]
                    name_match = re.search(r"page_(\d+)\.png", image_path.name)
                    if name_match:
                        page_number = int(name_match.group(1))

    return image_path, page_number, text_evidence

def build_review_command(
    package_path: Path, 
    draft_item_id: str, 
    decision_type: str, 
    reviewer: str, 
    reason: Optional[str] = None, 
    field_overrides: Optional[Dict[str, Any]] = None,
    overwrite: bool = True
) -> List[str]:
    """
    Sinh CLI command record-review cho Streamlit thực thi.
    """
    cmd = [
        "python", "-m", "mep_quotation.cli.main", "record-review", 
        str(package_path),
        "--draft-item-id", draft_item_id,
        "--decision", decision_type,
        "--reviewer", reviewer
    ]
    
    if reason:
        cmd.extend(["--reason", reason])
        
    if overwrite:
        cmd.append("--overwrite")
        
    if decision_type == "edited" and field_overrides:
        for k, v in field_overrides.items():
            if v is not None and str(v).strip() != "":
                cli_arg = f"--{k.replace('_', '-')}"
                cmd.extend([cli_arg, str(v)])
                
    return cmd

def build_export_preview_rows(
    draft_items: List[Dict[str, Any]], 
    decisions_map: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Xây dựng danh sách dòng xem trước dữ liệu xuất Excel (Export Preview).
    Chỉ gồm approved và edited.
    """
    preview_rows = []
    for item in draft_items:
        d_id = item.get("draft_item_id")
        dec = decisions_map.get(d_id, {})
        dec_type = dec.get("decision_type")
        
        if dec_type in ["approved", "edited"]:
            overrides = dec.get("field_overrides", {})
            
            preview_rows.append({
                "Mã nháp": d_id,
                "Quyết định": "Chấp nhận" if dec_type == "approved" else "Chỉnh sửa",
                "Mô tả": overrides.get("description") or item.get("description") or "",
                "Thương hiệu": overrides.get("brand") or item.get("brand") or "",
                "Đơn vị": overrides.get("unit") or item.get("unit") or "",
                "Số lượng": overrides.get("quantity") if overrides.get("quantity") is not None else item.get("quantity", 0.0),
                "Đơn giá": overrides.get("unit_price") if overrides.get("unit_price") is not None else item.get("unit_price", 0.0),
                "Thành tiền": overrides.get("amount") if overrides.get("amount") is not None else item.get("amount", 0.0),
                "Tiền tệ": overrides.get("currency") or item.get("currency") or ""
            })
            
    return preview_rows
