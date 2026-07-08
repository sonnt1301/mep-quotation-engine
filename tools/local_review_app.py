import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
from PIL import Image

# Thêm PROJECT_ROOT vào sys.path để import các module của dự án
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.ui_helpers import (
    sanitize_filename,
    safe_load_json,
    run_cli_command,
    resolve_artifact_paths
)
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
from mep_quotation.package.paths import get_package_dir, generate_quotation_id
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple

class PipelineStepStatusModel(BaseModel):
    step_id: str
    step_name: str
    phase_number: str
    status: str = "pending"
    output_paths: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: float = 0.0
    message: str = ""
    error: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

# Thiết lập cấu hình trang
st.set_page_config(
    page_title="Hệ thống rà soát báo giá MEP trực quan",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border-radius: 8px;
        padding: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card h3 {
        margin: 0;
        font-size: 13px;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card p {
        margin: 5px 0 0 0;
        font-size: 22px;
        font-weight: bold;
        color: #0f172a;
    }
    .warning-box {
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo st.session_state
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = {}
if "selected_draft_item_id" not in st.session_state:
    st.session_state.selected_draft_item_id = None
if "last_stdout" not in st.session_state:
    st.session_state.last_stdout = ""
if "last_stderr" not in st.session_state:
    st.session_state.last_stderr = ""
if "processing_msg" not in st.session_state:
    st.session_state.processing_msg = ""
if "processing_error" not in st.session_state:
    st.session_state.processing_error = ""

PIPELINE_STEPS = {
    "import-pdf": {
        "name": "Nhập PDF (Phase 2 - import-pdf)",
        "phase": "Phase 2",
        "inputs": [],
        "command": ["python", "-m", "mep_quotation.cli.main", "import-pdf"]
    },
    "validate-package": {
        "name": "Kiểm tra gói báo giá (Check - validate-package)",
        "phase": "Kiểm tra",
        "inputs": ["package_json"],
        "command": ["python", "-m", "mep_quotation.cli.main", "validate-package"]
    },
    "prepare-pages": {
        "name": "Chuẩn bị các trang PDF (Phase 3 - prepare-pages)",
        "phase": "Phase 3",
        "inputs": ["source_pdf"],
        "command": ["python", "-m", "mep_quotation.cli.main", "prepare-pages"]
    },
    "extract-text": {
        "name": "Trích xuất văn bản PDF (Phase 4 - extract-text)",
        "phase": "Phase 4",
        "inputs": ["page_manifest"],
        "command": ["python", "-m", "mep_quotation.cli.main", "extract-text"]
    },
    "assemble-text": {
        "name": "Lắp ghép văn bản (Phase 5 - assemble-text)",
        "phase": "Phase 5",
        "inputs": ["raw_text"],
        "command": ["python", "-m", "mep_quotation.cli.main", "assemble-text"]
    },
    "parse-line-candidates": {
        "name": "Trích xuất dòng ứng viên (Phase 6 - parse-line-candidates)",
        "phase": "Phase 6",
        "inputs": ["text_manifest"],
        "command": ["python", "-m", "mep_quotation.cli.main", "parse-line-candidates"]
    },
    "assemble-rows": {
        "name": "Gom hàng ứng viên (Phase 7 - assemble-rows)",
        "phase": "Phase 7",
        "inputs": ["line_candidates"],
        "command": ["python", "-m", "mep_quotation.cli.main", "assemble-rows"]
    },
    "build-item-candidates": {
        "name": "Tạo ứng viên vật tư (Phase 8 - build-item-candidates)",
        "phase": "Phase 8",
        "inputs": ["row_candidates"],
        "command": ["python", "-m", "mep_quotation.cli.main", "build-item-candidates"]
    },
    "build-normalized-draft": {
        "name": "Tạo bản nháp chuẩn hóa (Phase 9 - build-normalized-draft)",
        "phase": "Phase 9",
        "inputs": ["item_candidates"],
        "command": ["python", "-m", "mep_quotation.cli.main", "build-normalized-draft"]
    },
    "create-review-file": {
        "name": "Tạo/Tải lại file rà soát (Phase 10 - create-review-file)",
        "phase": "Phase 10",
        "inputs": ["normalized_draft"],
        "command": ["python", "-m", "mep_quotation.cli.main", "create-review-file"]
    },
    "export-normalized": {
        "name": "Xuất dữ liệu chuẩn chính thức (Phase 11 - export-normalized)",
        "phase": "Phase 11",
        "inputs": ["normalized_draft", "review_decisions"],
        "command": ["python", "-m", "mep_quotation.cli.main", "export-normalized"]
    },
    "export-excel": {
        "name": "Xuất file Excel báo giá (Phase 12 - export-excel)",
        "phase": "Phase 12",
        "inputs": ["normalized_json"],
        "command": ["python", "-m", "mep_quotation.cli.main", "export-excel"]
    }
}

# --- SIDEBAR: CHỌN BÁO GIÁ ---
st.sidebar.header("📂 Chọn báo giá")

# PDF Input
pdf_source = st.sidebar.radio("Nguồn PDF báo giá", ["Tải file lên (Upload)", "Đường dẫn file trên máy (Local Path)"])
pdf_path_str = ""

if pdf_source == "Tải file lên (Upload)":
    uploaded_file = st.sidebar.file_uploader("Chọn tệp PDF báo giá", type=["pdf"])
    if uploaded_file is not None:
        temp_dir = PROJECT_ROOT / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)
        safe_name = sanitize_filename(uploaded_file.name)
        temp_pdf_path = temp_dir / safe_name
        with open(temp_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        pdf_path_str = str(temp_pdf_path)
else:
    pdf_path_str = st.sidebar.text_input("Đường dẫn file PDF trên máy", "")

# Package Parameters
supplier_code = st.sidebar.text_input("Mã nhà cung cấp", "AUT").strip().upper()
quotation_date_val = st.sidebar.date_input("Ngày báo giá", datetime(2026, 6, 20))
quotation_date = quotation_date_val.strftime("%Y-%m-%d")
seq = st.sidebar.number_input("Số thứ tự báo giá", min_value=1, value=1, step=1)
max_size_mb = 50

# --- CHẾ ĐỘ NÂNG CAO ---
st.sidebar.markdown("---")
show_advanced = st.sidebar.checkbox("Hiển thị chế độ nâng cao", value=False)

overwrite_intermediate = False
overwrite_review_decisions = False
overwrite_normalized = False
overwrite_excel = False
timeout_sec = 600
project_root = PROJECT_ROOT

# Chế độ xử lý đơn giản cho người dùng thường
process_mode = "Sử dụng dữ liệu cũ nếu đã có"
if not show_advanced:
    process_mode = st.sidebar.radio("Chế độ xử lý dữ liệu", ["Sử dụng dữ liệu cũ nếu đã có", "Xử lý mới hoàn toàn (Ghi đè)"])
    overwrite_intermediate = (process_mode == "Xử lý mới hoàn toàn (Ghi đè)")
else:
    st.sidebar.subheader("⚙️ Cấu Hình Nâng Cao")
    project_root_input = st.sidebar.text_input("Thư mục dự án", str(PROJECT_ROOT))
    project_root = Path(project_root_input).resolve()
    
    max_size_mb = st.sidebar.number_input("Ngưỡng dung lượng cảnh báo (MB)", min_value=1, value=50)
    timeout_sec = st.sidebar.number_input("Thời gian chờ chạy xử lý (Giây)", min_value=10, value=600)
    
    st.sidebar.subheader("🔄 Lựa chọn ghi đè (Overwrite)")
    overwrite_intermediate = st.sidebar.checkbox("Ghi đè dữ liệu trung gian (Phase 3-9)", value=False)
    overwrite_review_decisions = st.sidebar.checkbox("Ghi đè quyết định rà soát (Phase 10)", value=False)
    overwrite_normalized = st.sidebar.checkbox("Ghi đè dữ liệu chuẩn (Phase 11)", value=False)
    overwrite_excel = st.sidebar.checkbox("Ghi đè file Excel (Phase 12)", value=False)

# Resolve package paths
data_root = project_root / "data"
package_path = Path()
quotation_id = ""
if supplier_code and quotation_date:
    try:
        package_path = get_package_dir(data_root, supplier_code, quotation_date, seq)
        quotation_id = generate_quotation_id(supplier_code, quotation_date, seq)
    except Exception as e:
        if show_advanced:
            st.sidebar.error(f"Lỗi tính toán package path: {e}")

# Resolve artifact paths
artifact_paths = {}
if package_path:
    artifact_paths = resolve_artifact_paths(package_path)

def check_inputs_exist(step_id: str) -> Tuple[bool, list]:
    needed = PIPELINE_STEPS[step_id]["inputs"]
    missing = []
    for item in needed:
        path = artifact_paths.get(item)
        if not path or not path.exists():
            missing.append(item)
    return len(missing) == 0, missing

def run_single_step(step_id: str) -> bool:
    step_info = PIPELINE_STEPS[step_id]
    command = list(step_info["command"])
    
    if step_id == "import-pdf":
        if not pdf_path_str:
            st.session_state.pipeline_status[step_id] = {
                "status": "fail", "error": "Chưa chọn hoặc tải lên tệp PDF đầu vào.", "stdout": "", "stderr": ""
            }
            return False
        command.extend([
            "--supplier", supplier_code,
            "--date", quotation_date,
            "--file", pdf_path_str,
            "--seq", str(seq),
            "--max-size-mb", str(max_size_mb)
        ])
    elif step_id == "validate-package":
        command.append(str(package_path))
    elif step_id in ["create-review-file", "export-normalized", "export-excel"]:
        command.append(str(package_path))
        if step_id == "create-review-file" and (overwrite_review_decisions or not show_advanced):
            if show_advanced and overwrite_review_decisions:
                command.append("--overwrite")
        elif step_id == "export-normalized" and (overwrite_normalized or not show_advanced):
            command.append("--overwrite")
        elif step_id == "export-excel" and (overwrite_excel or not show_advanced):
            command.append("--overwrite")
    else:
        command.append(str(package_path))
        if overwrite_intermediate:
            command.append("--overwrite")
            
    st.session_state.pipeline_status[step_id] = {
        "status": "running", "started_at": datetime.now().strftime("%H:%M:%S"), "stdout": "", "stderr": ""
    }
    
    code, stdout, stderr = run_cli_command(command, timeout=timeout_sec)
    
    st.session_state.last_stdout = stdout
    st.session_state.last_stderr = stderr
    
    if code == 0:
        st.session_state.pipeline_status[step_id] = {
            "status": "pass", "stdout": stdout, "stderr": stderr
        }
        return True
    else:
        st.session_state.pipeline_status[step_id] = {
            "status": "fail", "stdout": stdout, "stderr": stderr,
            "error": stderr or f"CLI exited with code {code}"
        }
        return False

# --- SIDEBAR ACTIONS ---
st.sidebar.subheader("⚙️ Hành động")

if st.sidebar.button("Xử lý báo giá", use_container_width=True):
    st.session_state.pipeline_status = {}
    st.session_state.processing_msg = ""
    st.session_state.processing_error = ""
    
    steps_to_run = [
        "import-pdf", "validate-package", "prepare-pages", "extract-text",
        "assemble-text", "parse-line-candidates", "assemble-rows",
        "build-item-candidates", "build-normalized-draft"
    ]
    
    success = True
    for step in steps_to_run:
        if not overwrite_intermediate:
            if step == "import-pdf" and artifact_paths.get("source_pdf") and artifact_paths["source_pdf"].exists():
                continue
            if step == "validate-package":
                continue
            if step == "prepare-pages" and artifact_paths.get("page_manifest") and artifact_paths["page_manifest"].exists():
                continue
            if step == "extract-text" and artifact_paths.get("raw_text") and artifact_paths["raw_text"].exists():
                continue
            if step == "assemble-text" and artifact_paths.get("text_markdown") and artifact_paths["text_markdown"].exists():
                continue
            if step == "parse-line-candidates" and artifact_paths.get("line_candidates") and artifact_paths["line_candidates"].exists():
                continue
            if step == "assemble-rows" and artifact_paths.get("row_candidates") and artifact_paths["row_candidates"].exists():
                continue
            if step == "build-item-candidates" and artifact_paths.get("item_candidates") and artifact_paths["item_candidates"].exists():
                continue
            if step == "build-normalized-draft" and artifact_paths.get("normalized_draft") and artifact_paths["normalized_draft"].exists():
                continue

        ok, missing = check_inputs_exist(step)
        if not ok:
            st.session_state.processing_error = f"Thiếu đầu vào cho bước {step}: {', '.join(missing)}. Vui lòng kiểm tra cấu hình."
            success = False
            break
            
        step_ok = run_single_step(step)
        artifact_paths = resolve_artifact_paths(package_path)
        if not step_ok:
            st.session_state.processing_error = f"Lỗi thực thi bước {step}. Vui lòng kiểm tra log kỹ thuật."
            success = False
            break
            
    if success:
        st.session_state.processing_msg = "Xử lý báo giá thành công! Dữ liệu nháp đã sẵn sàng để rà soát."
        review_file = artifact_paths.get("review_decisions")
        if review_file and not review_file.exists():
            run_single_step("create-review-file")
            artifact_paths = resolve_artifact_paths(package_path)

if show_advanced:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ Thao tác nâng cao")
    
    if st.sidebar.button("Tải lại gói báo giá (Refresh Package)"):
        st.session_state.pipeline_status = {}
        st.session_state.selected_draft_item_id = None
        st.sidebar.info("Đã reload trạng thái gói từ đĩa.")
        
    if st.sidebar.button("Tạo file rà soát trống (Create Review File)"):
        ok, missing = check_inputs_exist("create-review-file")
        if not ok:
            st.sidebar.error(f"Thiếu đầu vào: {', '.join(missing)}")
        else:
            step_ok = run_single_step("create-review-file")
            artifact_paths = resolve_artifact_paths(package_path)
            if step_ok:
                st.sidebar.success("Đã khởi tạo review_decisions.json trống!")
                st.rerun()
            else:
                st.sidebar.error("Khởi tạo review_decisions.json thất bại!")
                
    selected_step_id = st.sidebar.selectbox(
        "Chạy riêng từng bước",
        list(PIPELINE_STEPS.keys()),
        format_func=lambda x: PIPELINE_STEPS[x]["name"]
    )
    
    if st.sidebar.button("Kích hoạt bước chọn"):
        ok, missing = check_inputs_exist(selected_step_id)
        if not ok:
            st.sidebar.error(f"Thiếu đầu vào: {', '.join(missing)}")
        else:
            step_ok = run_single_step(selected_step_id)
            artifact_paths = resolve_artifact_paths(package_path)
            if step_ok:
                st.sidebar.success("Chạy thành công bước được chọn!")
                st.rerun()
            else:
                st.sidebar.error("Chạy thất bại bước được chọn!")
                
    if st.sidebar.button("Kiểm tra toàn vẹn gói"):
        step_ok = run_single_step("validate-package")
        if step_ok:
            st.sidebar.success("Gói báo giá hợp lệ và toàn vẹn!")
        else:
            st.sidebar.error("Kiểm định package thất bại!")

# --- LOAD DATA FOR DASHBOARD AND REVIEW ---
draft_path = artifact_paths.get("normalized_draft")
review_path = artifact_paths.get("review_decisions")
profile_path = package_path / "source" / "source_profile.json" if package_path else None

draft_data = None
review_data = None
profile_data = None

if draft_path and draft_path.exists():
    draft_data, _ = safe_load_json(draft_path)
if review_path and review_path.exists():
    review_data, _ = safe_load_json(review_path)
if profile_path and profile_path.exists():
    profile_data, _ = safe_load_json(profile_path)

# --- REGION 2: DASHBOARD THỐNG KÊ ---
if draft_data and "items" in draft_data and len(draft_data["items"]) > 0:
    st.subheader("📊 Dashboard kết quả đọc báo giá")
    
    decision_map = {}
    if review_data and "decisions" in review_data:
        for dec in review_data["decisions"]:
            decision_map[dec["draft_item_id"]] = dec
            
    stats = get_dashboard_stats(draft_data["items"], decision_map)
    
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.markdown(f'<div class="metric-card"><h3>Tổng số dòng nháp</h3><p>{stats["total"]}</p></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><h3>Có thể là vật tư</h3><p style="color:#16a34a;">{stats["likely_item"]}</p></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><h3>Vật tư yếu/khuyết</h3><p style="color:#f59e0b;">{stats["weak_item"]}</p></div>', unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="metric-card"><h3>Nghi rác / Tiêu đề</h3><p style="color:#64748b;">{stats["noise_or_title"]}</p></div>', unsafe_allow_html=True)
    with m5:
        st.markdown(f'<div class="metric-card"><h3>Đã duyệt (Approve/Edit)</h3><p style="color:#16a34a;">{stats["approved"] + stats["edited"]}</p></div>', unsafe_allow_html=True)
    with m6:
        st.markdown(f'<div class="metric-card"><h3>Sẽ xuất Excel</h3><p style="color:#0284c7;">{stats["exportable"]}</p></div>', unsafe_allow_html=True)

    if profile_data:
        with st.expander("📄 Thông tin hồ sơ tệp tin nguồn (Source Profile)"):
            c_pf1, c_pf2 = st.columns(2)
            with c_pf1:
                st.markdown(f"- **Định dạng file**: `{profile_data.get('detected_file_type')}` ({profile_data.get('file_extension')})")
                st.markdown(f"- **Mime Type**: `{profile_data.get('detected_mime_type')}`")
                st.markdown(f"- **Dung lượng**: `{profile_data.get('file_size_bytes') / 1024 / 1024:.2f} MB`")
                st.markdown(f"- **Vai trò đề xuất**: `{profile_data.get('source_role')}` (Độ tự tin: `{profile_data.get('source_role_confidence')}`)")
            with c_pf2:
                st.markdown(f"- **Khuyến nghị tiếp theo**: `{profile_data.get('recommended_next_action')}`")
                st.markdown(f"- **Yêu cầu rà soát hồ sơ**: `{profile_data.get('requires_human_profile_review')}`")
                st.markdown(f"- **Số trang / Sheets**: `{profile_data.get('technical_readability', {}).get('page_count') or profile_data.get('technical_readability', {}).get('sheet_count') or 1}`")
                st.markdown(f"- **Có Text gốc (Native)**: `{profile_data.get('technical_readability', {}).get('has_native_text')}`")
            
            if profile_data.get("technical_readability", {}).get("requires_ocr"):
                st.markdown("""
                <div class="warning-box">
                    <strong>⚠️ Cảnh báo OCR:</strong> Tệp tin nguồn được nhận diện là dạng quét ảnh (Scanned PDF/Image). 
                    Hệ thống cần chạy OCR để trích xuất đầy đủ dữ liệu. Dữ liệu đọc hiện tại có thể bị thiếu sót.
                </div>
                """, unsafe_allow_html=True)

# --- REGION 3 & 4: REVIEW TABLE & DETAILED EVIDENCE VIEW ---
st.markdown("---")
st.subheader("🕵️ Rà soát và Duyệt báo giá")

if draft_data and "items" in draft_data and len(draft_data["items"]) > 0:
    items_list = draft_data["items"]
    
    col_filter, col_sort, col_checkbox = st.columns([2, 2, 2])
    with col_filter:
        filter_type = st.selectbox(
            "Filter bộ lọc dữ liệu",
            ["Tất cả", "Chưa rà soát", "Đã chấp nhận", "Đã chỉnh sửa", "Đã từ chối", "Thiếu đơn giá", "Thiếu đơn vị", "Thiếu số lượng", "Độ tin cậy thấp", "Có cảnh báo", "Có giá"]
        )
    with col_sort:
        sort_by = st.selectbox(
            "Sắp xếp dòng hiển thị",
            ["Thứ tự xuất hiện", "Độ tin cậy tăng dần", "Có giá trước", "Chưa rà soát trước"]
        )
    with col_checkbox:
        # Checkbox kiểm soát hiển thị dòng bị ẩn theo heuristics
        st.write("") # Dịch chuyển dọc cho thẳng hàng
        st.write("")
        show_hidden = st.checkbox("Hiển thị dòng bị ẩn / dòng nghi ngờ không phải vật tư", value=False)

    filtered_items = filter_and_sort_items(items_list, decision_map, filter_type, sort_by, show_hidden=show_hidden)
    
    table_rows = []
    for idx, item in enumerate(filtered_items):
        d_id = item.get("draft_item_id")
        dec = decision_map.get(d_id, {})
        status_eng = dec.get("decision_type", "unreviewed")
        
        status_vie = "⚪ Chưa rà soát"
        if status_eng == "approved":
            status_vie = "🟢 Chấp nhận"
        elif status_eng == "rejected":
            status_vie = "🔴 Từ chối"
        elif status_eng == "edited":
            status_vie = "🟡 Chỉnh sửa"
            
        cls = classify_draft_item(item)
        cls_vie = "Vật tư tốt"
        if cls == "likely_item":
            cls_vie = "🟢 Vật tư tốt"
        elif cls == "weak_item":
            cls_vie = "🟡 Vật tư yếu"
        elif cls == "incomplete_candidate":
            cls_vie = "🔵 Chờ bổ sung"
        elif cls == "title_or_header":
            cls_vie = "⚪ Tiêu đề/Bảng"
        elif cls == "section_or_note":
            cls_vie = "📝 Ghi chú/Cộng"
        elif cls == "rejected_noise":
            cls_vie = "❌ Rác/Trống"

        # Dịch warnings sang Tiếng Việt thân thiện
        raw_warns = item.get("warnings", [])
        vie_warns = ", ".join(format_warnings_vietnamese(raw_warns)) if raw_warns else "Bình thường"
            
        table_rows.append({
            "STT": idx + 1,
            "Mô tả": item.get("description", ""),
            "Đơn vị": item.get("unit", ""),
            "Số lượng": item.get("quantity", 0.0),
            "Đơn giá": item.get("unit_price", 0.0),
            "Thành tiền": item.get("amount", 0.0),
            "Phân loại dòng": cls_vie,
            "Cảnh báo": vie_warns,
            "Trạng thái": status_vie
        })
        
    df_items = pd.DataFrame(table_rows)
    st.markdown(f"**Danh sách dòng đang lọc ({len(filtered_items)} dòng):**")
    st.dataframe(df_items, use_container_width=True, hide_index=True)

    option_map = {}
    for idx, item in enumerate(filtered_items):
        d_id = item.get("draft_item_id")
        dec = decision_map.get(d_id, {})
        status_icon = "⚪"
        if dec.get("decision_type") == "approved": status_icon = "🟢"
        elif dec.get("decision_type") == "rejected": status_icon = "🔴"
        elif dec.get("decision_type") == "edited": status_icon = "🟡"
        
        label = f"{status_icon} Dòng {idx+1}: {item.get('description', '')[:50]}... ({d_id})"
        option_map[label] = d_id

    if option_map:
        default_idx = 0
        if st.session_state.selected_draft_item_id in option_map.values():
            default_idx = list(option_map.values()).index(st.session_state.selected_draft_item_id)
            
        selected_label = st.selectbox("Chọn dòng vật tư để xem bằng chứng và chỉnh sửa:", list(option_map.keys()), index=default_idx)
        selected_id = option_map[selected_label]
        st.session_state.selected_draft_item_id = selected_id
        
        selected_item = next((it for it in items_list if it.get("draft_item_id") == selected_id), None)
        
        if selected_item:
            existing_dec = decision_map.get(selected_id, {})
            
            # --- LAYOUT HAI CỘT BẮT BUỘC ---
            col_left, col_right = st.columns([6, 5])
            
            # --- CỘT TRÁI: EVIDENCE VIEWER ---
            with col_left:
                st.subheader("🔍 Bằng chứng trực quan (Evidence)")
                
                # Phân giải bằng chứng từ helper
                img_path, resolved_page_num, text_evidence = resolve_item_evidence(selected_item, package_path, artifact_paths)
                
                # A. Chọn trang PDF trước khi render ảnh
                pages_dir = package_path / "source" / "pages"
                all_pages_on_disk = []
                if pages_dir.exists() and pages_dir.is_dir():
                    all_pages_on_disk = sorted([int(re.search(r"page_(\d+)\.png", p.name).group(1)) for p in pages_dir.glob("page_*.png") if re.search(r"page_(\d+)\.png", p.name)])

                selected_page_key = f"page_sel_{selected_id}"
                if selected_page_key not in st.session_state:
                    st.session_state[selected_page_key] = resolved_page_num or (all_pages_on_disk[0] if all_pages_on_disk else 1)

                current_page_selection = st.session_state[selected_page_key]
                if all_pages_on_disk and current_page_selection not in all_pages_on_disk:
                    current_page_selection = all_pages_on_disk[0]
                    st.session_state[selected_page_key] = current_page_selection

                st.markdown(f"**📷 Định vị trang PDF: Trang `{current_page_selection}`**")
                
                # Render Selectbox Chọn Trang Trước
                if all_pages_on_disk:
                    curr_select_idx = all_pages_on_disk.index(current_page_selection) if current_page_selection in all_pages_on_disk else 0
                    manual_page = st.selectbox("Chọn trang hiển thị ảnh gốc", all_pages_on_disk, index=curr_select_idx)
                    
                    if manual_page != current_page_selection:
                        st.session_state[selected_page_key] = manual_page
                        current_page_selection = manual_page
                        
                    img_path = pages_dir / f"page_{current_page_selection:04d}.png"
                
                # Render ảnh trang PDF
                pdf_root_file = artifact_paths.get("source_pdf")
                if pdf_root_file and pdf_root_file.exists() and (not pages_dir.exists() or len(list(pages_dir.glob("page_*.png"))) == 0):
                    st.warning("⚠️ Thư mục ảnh trang PDF trống hoặc chưa được kết xuất.")
                    if st.button("📷 Tạo ảnh trang PDF (Prepare Pages)", use_container_width=True):
                        st.info("Đang chạy kết xuất ảnh từ PDF...")
                        run_single_step("prepare-pages")
                        st.rerun()
                
                if img_path and img_path.exists():
                    try:
                        image = Image.open(img_path)
                        st.image(image, caption=f"Trang {current_page_selection} - Đối chiếu hình ảnh gốc", use_container_width=True)
                    except Exception as e:
                        st.error(f"Lỗi hiển thị ảnh trang: {e}")
                else:
                    st.info("Không tìm thấy ảnh trang PDF gốc trên đĩa.")
                    
                if pdf_root_file and pdf_root_file.exists():
                    pdf_absolute_path = pdf_root_file.resolve().as_uri()
                    st.markdown(f"[📥 Mở tệp PDF gốc trực tiếp trong trình duyệt]({pdf_absolute_path})")

                # B. Text Evidence gốc
                st.markdown("**📝 Văn bản trích xuất gốc (Text Evidence):**")
                st.text_area("Bằng chứng chữ thô", text_evidence, height=180, disabled=True)
                
                # Hiển thị cảnh báo Việt hóa thân thiện dưới dạng text thông báo
                item_warns = selected_item.get("warnings", [])
                if item_warns:
                    vie_item_warns = format_warnings_vietnamese(item_warns)
                    st.warning(f"⚠️ Cảnh báo dòng vật tư: {', '.join(vie_item_warns)}")
                    
            # --- CỘT PHẢI: REVIEW FORM ---
            with col_right:
                st.subheader("✏️ Hiệu chỉnh & Phê duyệt (Review)")
                
                old_overrides = existing_dec.get("field_overrides", {})
                
                rev_desc = st.text_area("Mô tả vật tư", old_overrides.get("description") or selected_item.get("description") or "", height=80)
                rev_brand = st.text_input("Thương hiệu", old_overrides.get("brand") or selected_item.get("brand") or "")
                rev_unit = st.text_input("Đơn vị tính", old_overrides.get("unit") or selected_item.get("unit") or "")
                
                c_form1, c_form2 = st.columns(2)
                with c_form1:
                    saved_qty = old_overrides.get("quantity") if old_overrides.get("quantity") is not None else selected_item.get("quantity")
                    rev_qty = st.number_input("Số lượng", value=safe_number(saved_qty, 0.0), format="%.4f")
                    
                    saved_price = old_overrides.get("unit_price") if old_overrides.get("unit_price") is not None else selected_item.get("unit_price")
                    rev_price = st.number_input("Đơn giá", value=safe_number(saved_price, 0.0), format="%.2f")
                with c_form2:
                    auto_amt = rev_qty * rev_price
                    saved_amt = old_overrides.get("amount") if old_overrides.get("amount") is not None else selected_item.get("amount")
                    rev_amt = st.number_input("Thành tiền", value=safe_number(saved_amt, auto_amt), format="%.2f")
                    
                    currencies = ["VND", "USD", ""]
                    default_curr_idx = 0
                    saved_curr = old_overrides.get("currency") or selected_item.get("currency") or "VND"
                    if saved_curr in currencies:
                        default_curr_idx = currencies.index(saved_curr)
                    rev_curr = st.selectbox("Tiền tệ", currencies, index=default_curr_idx)

                st.markdown("---")
                
                auto_advance = st.checkbox("Tự động chuyển sang dòng chưa rà soát tiếp theo sau khi lưu", value=True)
                
                st.markdown("**Ý kiến và Quyết định:**")
                reviewer_name = st.text_input("Người rà soát (Reviewer)", existing_dec.get("reviewer", "tester"))
                
                reason_val = st.text_area("Lý do chỉnh sửa / Từ chối (Bắt buộc với Chỉnh sửa hoặc Từ chối thủ công)", existing_dec.get("reason", ""))
                
                quick_rejections = [
                    "Chọn lý do nhanh...",
                    "Dòng tiêu đề, không phải vật tư",
                    "Thiếu giá",
                    "Dữ liệu đọc sai",
                    "Dòng ghi chú",
                    "Trùng dòng khác",
                    "Không thuộc phạm vi báo giá"
                ]
                selected_quick = st.selectbox("Gợi ý lý do từ chối nhanh:", quick_rejections)
                if selected_quick != "Chọn lý do nhanh..." and not reason_val:
                    reason_val = selected_quick
                
                # Xử lý lưu quyết định rà soát
                def save_decision(decision_type: str, reason_text: str, overrides: dict = None):
                    # Guardrail: Bắt buộc lý do cho edited và rejected (trừ nút Không phải vật tư tự động)
                    if decision_type in ["rejected", "edited"] and not reason_text.strip():
                        st.error("Lỗi: Quyết định 'Từ chối' hoặc 'Chỉnh sửa' bắt buộc phải nhập lý do.")
                        return
                    
                    # 1. Phát hiện và tự động tạo file review_decisions.json nếu thiếu, kiểm tra chặt chẽ exit code
                    review_file_path = artifact_paths.get("review_decisions")
                    if review_file_path and not review_file_path.exists():
                        success_init = run_single_step("create-review-file")
                        if not success_init:
                            step_status = st.session_state.pipeline_status.get("create-review-file", {})
                            err_msg = step_status.get("error", "Lỗi không xác định khi tạo file rà soát")
                            st.error(f"Lỗi nghiêm trọng: Không thể khởi tạo tệp rà soát review_decisions.json. Chi tiết: {err_msg}")
                            return
                        
                    # 2. Xây dựng command CLI qua helper
                    cmd = build_review_command(
                        package_path=package_path,
                        draft_item_id=selected_id,
                        decision_type=decision_type,
                        reviewer=reviewer_name,
                        reason=reason_text,
                        field_overrides=overrides
                    )
                    
                    code, stdout, stderr = run_cli_command(cmd, timeout=timeout_sec)
                    if code == 0:
                        st.toast(f"Lưu quyết định {decision_type.upper()} thành công!")
                        
                        if auto_advance:
                            item_ids_list = [item.get("draft_item_id") for item in filtered_items]
                            try:
                                current_idx = item_ids_list.index(selected_id)
                                next_id = None
                                for idx_n in range(current_idx + 1, len(item_ids_list)):
                                    target_id = item_ids_list[idx_n]
                                    dec_type = decision_map.get(target_id, {}).get("decision_type", "unreviewed")
                                    if dec_type == "unreviewed":
                                        next_id = target_id
                                        break
                                if next_id is None:
                                    for idx_n in range(0, current_idx):
                                        target_id = item_ids_list[idx_n]
                                        dec_type = decision_map.get(target_id, {}).get("decision_type", "unreviewed")
                                        if dec_type == "unreviewed":
                                            next_id = target_id
                                            break
                                if next_id:
                                    st.session_state.selected_draft_item_id = next_id
                            except ValueError:
                                pass
                                
                        st.rerun()
                    else:
                        st.error(f"Lưu quyết định thất bại: {stderr}")

                # Render 4 nút bấm rà soát
                b_c1, b_c2, b_c3 = st.columns(3)
                with b_c1:
                    if st.button("🟢 Chấp nhận dòng", use_container_width=True):
                        save_decision("approved", reason_val or "Chấp nhận thông tin gốc")
                with b_c2:
                    if st.button("🟡 Chỉnh sửa & Chấp nhận", use_container_width=True):
                        overrides_data = {
                            "description": rev_desc,
                            "brand": rev_brand,
                            "unit": rev_unit,
                            "quantity": rev_qty,
                            "unit_price": rev_price,
                            "currency": rev_curr,
                            "amount": rev_amt
                        }
                        save_decision("edited", reason_val, overrides=overrides_data)
                with b_c3:
                    if st.button("🔴 Từ chối dòng", use_container_width=True):
                        save_decision("rejected", reason_val)

                # Nút quyết định nhanh "Không phải vật tư" dạng nút lớn riêng biệt
                st.markdown("")
                if st.button("🚫 Không phải vật tư (Loại bỏ nhanh)", use_container_width=True, type="secondary"):
                    save_decision("rejected", "Không phải dòng vật tư")
                        
else:
    st.info("Chưa có dữ liệu nháp để rà soát. Vui lòng chọn tệp PDF và bấm 'Xử lý báo giá' ở Sidebar.")

# --- REGION 5: CHẨN ĐOÁN KẾT QUẢ ĐỌC ---
if draft_data and "items" in draft_data and len(draft_data["items"]) > 0:
    st.markdown("---")
    st.subheader("🩺 Chẩn đoán kết quả đọc dữ liệu")
    
    diagnose_groups = diagnose_read_results(draft_data["items"], decision_map)
    
    diag_tab1, diag_tab2, diag_tab3 = st.tabs([
        f"🟢 Đọc tốt ({len(diagnose_groups['good'])} dòng)",
        f"🟡 Thiếu dữ liệu ({len(diagnose_groups['missing_data'])} dòng)",
        f"🔴 Nghi ngờ rác/tiêu đề ({len(diagnose_groups['suspected_trash'])} dòng)"
    ])
    
    with diag_tab1:
        st.markdown("**Các dòng có vẻ được nhận diện chính xác và đầy đủ thông tin:**")
        if diagnose_groups["good"]:
            st.dataframe(pd.DataFrame([{
                "Mã nháp": it.get("draft_item_id"), "Mô tả": it.get("description"), "Đơn vị": it.get("unit"),
                "Số lượng": it.get("quantity"), "Đơn giá": it.get("unit_price"), "Độ tin cậy": f"{it.get('confidence',0.0)*100:.1f}%"
            } for it in diagnose_groups["good"]]), use_container_width=True, hide_index=True)
        else:
            st.write("Không có dòng nào.")
            
    with diag_tab2:
        st.markdown("**Các dòng bị khuyết thiếu một số trường quan trọng (đơn vị, số lượng, giá) hoặc độ tin cậy thấp:**")
        if diagnose_groups["missing_data"]:
            st.dataframe(pd.DataFrame([{
                "Mã nháp": it.get("draft_item_id"), "Mô tả": it.get("description"), "Đơn vị": it.get("unit"),
                "Số lượng": it.get("quantity"), "Đơn giá": it.get("unit_price")
            } for it in diagnose_groups["missing_data"]]), use_container_width=True, hide_index=True)
        else:
            st.write("Không có dòng nào.")
            
    with diag_tab3:
        st.markdown("**Các dòng nghi là tiêu đề bảng biểu, thông tin rác hoặc dòng trống không phải vật tư:**")
        if diagnose_groups["suspected_trash"]:
            st.dataframe(pd.DataFrame([{
                "Mã nháp": it.get("draft_item_id"), "Mô tả": it.get("description"), "Đơn vị": it.get("unit"),
                "Số lượng": it.get("quantity"), "Đơn giá": it.get("unit_price")
            } for it in diagnose_groups["suspected_trash"]]), use_container_width=True, hide_index=True)
        else:
            st.write("Không có dòng nào.")

# --- REGION 6: EXPORT PREVIEW ---
st.markdown("---")
st.subheader("📤 Xem trước kết quả xuất bản (Export Preview)")

preview_rows = build_export_preview_rows(draft_data["items"], decision_map) if (draft_data and "items" in draft_data) else []

if preview_rows:
    df_preview = pd.DataFrame(preview_rows)
    st.markdown(f"**Các dòng sẽ được xuất Excel ({len(preview_rows)} dòng):**")
    st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    rejected_count = sum(1 for d in decision_map.values() if d.get("decision_type") == "rejected")
    unreviewed_count = len(draft_data["items"]) - len(preview_rows) - rejected_count
    
    st.info(f"💡 Thống kê xuất bản: Sẽ xuất `{len(preview_rows)}` dòng | Loại bỏ `{rejected_count}` dòng bị từ chối | `{unreviewed_count}` dòng chưa rà soát sẽ không được xuất.")
    
    if st.button("Xuất Excel", use_container_width=True):
        ok_norm, missing_norm = check_inputs_exist("export-normalized")
        if not ok_norm:
            st.error("Không thể xuất dữ liệu chuẩn. Thiếu file đầu vào.")
        else:
            cmd_norm = ["python", "-m", "mep_quotation.cli.main", "export-normalized", str(package_path), "--overwrite"]
            code_n, stdout_n, stderr_n = run_cli_command(cmd_norm, timeout=timeout_sec)
            
            if code_n == 0:
                artifact_paths = resolve_artifact_paths(package_path)
                ok_excel, missing_excel = check_inputs_exist("export-excel")
                if not ok_excel:
                    st.error("Không thể xuất Excel. Thiếu file normalized.json.")
                else:
                    cmd_excel = ["python", "-m", "mep_quotation.cli.main", "export-excel", str(package_path), "--overwrite"]
                    code_e, stdout_e, stderr_e = run_cli_command(cmd_excel, timeout=timeout_sec)
                    artifact_paths = resolve_artifact_paths(package_path)
                    
                    if code_e == 0:
                        st.success("Xuất Excel thành công!")
                        st.rerun()
                    else:
                        st.error(f"Xuất Excel thất bại: {stderr_e}")
            else:
                st.error(f"Xử lý chuẩn hóa thất bại trước khi xuất Excel: {stderr_n}")
else:
    st.warning("⚠️ Chưa có dòng vật tư nào được duyệt (Chấp nhận hoặc Chỉnh sửa) để xuất Excel.")

# Nút tải file Excel chính
excel_file_path = artifact_paths.get("excel_export")
if excel_file_path and excel_file_path.exists():
    with open(excel_file_path, "rb") as f:
        excel_bytes = f.read()
    st.download_button(
        label="📥 Tải file Excel báo giá chính thức",
        data=excel_bytes,
        file_name=f"{quotation_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# --- REGION 7: ADVANCED ARTIFACT VIEWER ---
if show_advanced:
    st.markdown("---")
    st.subheader("🔍 Trình xem các tệp tin Artifacts (Read-Only)")
    
    tab_pkg, tab_profile, tab_pdf, tab_raw, tab_md, tab_line, tab_row, tab_item, tab_draft, tab_rev, tab_final, tab_excel_manifest = st.tabs([
        "package.json",
        "Hồ sơ nguồn (Source Profile)",
        "Ảnh trang PDF (PDF Pages)",
        "Văn bản thô (Raw Text)",
        "Văn bản Markdown (Assembled Text)",
        "Dòng đề cử (Line Candidates)",
        "Hàng đề cử (Row Candidates)",
        "Ứng viên vật tư (Item Candidates)",
        "Dữ liệu nháp chuẩn hóa (Normalized Draft)",
        "Quyết định rà soát (Review Decisions)",
        "Dữ liệu chuẩn cuối cùng (Normalized Final)",
        "Thông tin xuất Excel (Excel Export Manifest)"
    ])
    
    def render_json_tab(path: Path):
        if not path or not path.exists():
            st.write("Tệp tin chưa được sinh ra (Not generated yet).")
            return
        data, err = safe_load_json(path)
        if err:
            st.error(err)
        else:
            st.json(data)
            
    with tab_pkg:
        render_json_tab(package_path / "package.json" if package_path else None)

    with tab_profile:
        render_json_tab(profile_path)
            
    with tab_pdf:
        manifest_path = artifact_paths.get("page_manifest")
        if manifest_path and manifest_path.exists():
            manifest_data, _ = safe_load_json(manifest_path)
            if manifest_data and "pages" in manifest_data:
                pages = manifest_data["pages"]
                page_numbers = [p["page_number"] for p in pages]
                selected_page_num = st.selectbox("Chọn trang xem ảnh (Advanced)", page_numbers)
                
                page_info = next((p for p in pages if p["page_number"] == selected_page_num), None)
                if page_info:
                    img_path_adv = package_path / page_info["image_path"]
                    if img_path_adv.exists():
                        try:
                            image = Image.open(img_path_adv)
                            st.image(image, caption=f"Trang {selected_page_num}", use_container_width=True)
                        except Exception as e:
                            st.error(f"Lỗi load ảnh: {e}")
                    else:
                        st.write(f"Không tìm thấy ảnh tại: {img_path_adv}")
            else:
                st.write("Không tìm thấy thông tin trang trong page_manifest.json.")
        else:
            st.write("Tệp tin page_manifest.json chưa được sinh ra.")
            
    with tab_raw:
        raw_path = artifact_paths.get("raw_text")
        if raw_path and raw_path.exists():
            raw_data, _ = safe_load_json(raw_path)
            if raw_data and "pages" in raw_data:
                pages = raw_data["pages"]
                page_nums = [p["page_number"] for p in pages]
                selected_raw_page = st.selectbox("Chọn trang xem văn bản thô (Advanced)", page_nums)
                
                raw_page_info = next((p for p in pages if p["page_number"] == selected_raw_page), None)
                if raw_page_info:
                    st.text_area("Văn bản thô (Advanced)", raw_page_info.get("text", ""), height=400)
        else:
            st.write("Tệp tin raw_text.json chưa được sinh ra.")
            
    with tab_md:
        md_path = artifact_paths.get("text_markdown")
        if md_path and md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            st.text_area("Markdown Content (Advanced)", md_content, height=400)
        else:
            st.write("Tệp tin Markdown chưa được sinh ra.")
            
    with tab_line:
        render_json_tab(artifact_paths.get("line_candidates"))
        
    with tab_row:
        render_json_tab(artifact_paths.get("row_candidates"))
        
    with tab_item:
        render_json_tab(artifact_paths.get("item_candidates"))
        
    with tab_draft:
        render_json_tab(artifact_paths.get("normalized_draft"))
        
    with tab_rev:
        render_json_tab(artifact_paths.get("review_decisions"))
        
    with tab_final:
        render_json_tab(artifact_paths.get("normalized_json"))
        
    with tab_excel_manifest:
        render_json_tab(artifact_paths.get("excel_export_manifest"))
