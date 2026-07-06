import os
import sys
import json
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
    page_title="Hệ thống xử lý báo giá MEP",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# Tiêu đề giao diện chính
st.title("🏗️ Hệ thống xử lý & Rà soát báo giá MEP")
st.markdown("Hỗ trợ tự động hóa chuyển đổi PDF báo giá thành bảng Excel chuẩn hóa phục vụ báo giá.")

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

# --- CHẾ ĐỘ NÂNG CAO (Mặc định ẩn) ---
st.sidebar.markdown("---")
show_advanced = st.sidebar.checkbox("Hiển thị chế độ nâng cao", value=False)

overwrite_intermediate = False
overwrite_review_decisions = False
overwrite_normalized = False
overwrite_excel = False
timeout_sec = 600
project_root = PROJECT_ROOT

if show_advanced:
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
        if step_id == "create-review-file" and overwrite_review_decisions:
            command.append("--overwrite")
        elif step_id == "export-normalized" and overwrite_normalized:
            command.append("--overwrite")
        elif step_id == "export-excel" and overwrite_excel:
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
            "status": "pass",
            "stdout": stdout,
            "stderr": stderr
        }
        return True
    else:
        st.session_state.pipeline_status[step_id] = {
            "status": "fail",
            "stdout": stdout,
            "stderr": stderr,
            "error": stderr or f"CLI exited with code {code}"
        }
        return False

# --- SIDEBAR ACTIONS ---
st.sidebar.subheader("⚙️ Xử lý")

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
        ok, missing = check_inputs_exist(step)
        if not ok:
            st.session_state.processing_error = "Không xử lý được PDF. Vui lòng kiểm tra file đầu vào và cấu hình."
            success = False
            break
            
        step_ok = run_single_step(step)
        artifact_paths = resolve_artifact_paths(package_path)
        if not step_ok:
            st.session_state.processing_error = "Không xử lý được PDF. Vui lòng kiểm tra file đầu vào."
            success = False
            break
            
    if success:
        st.session_state.processing_msg = "Xử lý báo giá thành công! Dữ liệu nháp đã sẵn sàng để rà soát."
        # Tự động khởi tạo review decisions trống nếu chưa có
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

# --- MAIN AREA: STATUS MESSAGE ---
if st.session_state.processing_msg:
    st.success(st.session_state.processing_msg)
if st.session_state.processing_error:
    st.error(st.session_state.processing_error)

# --- MAIN AREA: ADVANCED PIPELINE STATUS ---
if show_advanced:
    st.subheader("📋 Trạng thái xử lý Pipeline")
    status_data = []
    for s_id, s_info in PIPELINE_STEPS.items():
        step_status = st.session_state.pipeline_status.get(s_id, {"status": "pending"})
        status_icon = "⚪ Đang chờ (Pending)"
        if step_status["status"] == "running":
            status_icon = "🔵 Đang chạy (Running)"
        elif step_status["status"] == "pass":
            status_icon = "🟢 Thành công (Pass)"
        elif step_status["status"] == "fail":
            status_icon = "🔴 Thất bại (Fail)"
            
        status_data.append({
            "Phân loại (Phase/Check)": s_info["phase"],
            "Tên bước (Step Name)": s_info["name"],
            "Trạng thái (Status)": status_icon,
            "Chi tiết lỗi (Error Details)": step_status.get("error", "")
        })
    df_status = pd.DataFrame(status_data)
    st.dataframe(df_status, use_container_width=True)
    
    with st.expander("🔍 Xem nhật ký chạy xử lý cuối cùng (Stdout/Stderr)"):
        col_out1, col_out2 = st.columns(2)
        with col_out1:
            st.markdown("**Đầu ra chuẩn (Stdout Output):**")
            st.text(st.session_state.last_stdout)
        with col_out2:
            st.markdown("**Đầu ra lỗi (Stderr Output):**")
            st.text(st.session_state.last_stderr)

# --- MAIN AREA: HUMAN REVIEW SECTION ---
st.markdown("---")
st.subheader("🕵️ Rà soát dữ liệu báo giá")

draft_path = artifact_paths.get("normalized_draft")
review_path = artifact_paths.get("review_decisions")

draft_data = None
review_data = None

if draft_path and draft_path.exists():
    draft_data, err_d = safe_load_json(draft_path)
if review_path and review_path.exists():
    review_data, err_r = safe_load_json(review_path)

if draft_data and "items" in draft_data and len(draft_data["items"]) > 0:
    items_list = draft_data["items"]
    
    # Map decision
    decision_map = {}
    if review_data and "decisions" in review_data:
        for dec in review_data["decisions"]:
            decision_map[dec["draft_item_id"]] = dec
            
    table_rows = []
    for item in items_list:
        d_id = item.get("draft_item_id")
        dec = decision_map.get(d_id, {})
        status_eng = dec.get("decision_type", "unreviewed")
        
        # Việt hóa trạng thái hiển thị
        status_vie = "Chưa rà soát"
        if status_eng == "approved":
            status_vie = "Chấp nhận"
        elif status_eng == "rejected":
            status_vie = "Từ chối"
        elif status_eng == "edited":
            status_vie = "Chỉnh sửa"
            
        table_rows.append({
            "Mã nháp": d_id,
            "Mô tả": item.get("description", ""),
            "Đơn vị": item.get("unit", ""),
            "Số lượng": item.get("quantity", 0.0),
            "Đơn giá": item.get("unit_price", 0.0),
            "Thành tiền": item.get("amount", 0.0),
            "Tiền tệ": item.get("currency", ""),
            "Độ tin cậy (%)": f"{item.get('confidence', 0.0)*100:.1f}%",
            "Trạng thái": status_vie,
            "Người thực hiện": dec.get("reviewer", "")
        })
        
    df_items = pd.DataFrame(table_rows)
    st.markdown("**Các dòng nháp cần rà soát:**")
    st.dataframe(df_items, use_container_width=True)
    
    st.markdown("### Thực hiện quyết định rà soát")
    item_ids = [row["Mã nháp"] for row in table_rows]
    selected_id = st.selectbox("Chọn dòng vật tư cần rà soát (Mã nháp)", item_ids)
    
    selected_item = next((it for it in items_list if it.get("draft_item_id") == selected_id), None)
    
    if selected_item:
        existing_dec = decision_map.get(selected_id, {})
        
        col_rev1, col_rev2 = st.columns(2)
        
        with col_rev1:
            st.markdown(f"**Thông tin gốc của dòng vật tư: {selected_id}**")
            st.markdown(f"- **Mô tả**: {selected_item.get('description')}")
            st.markdown(f"- **Đơn vị**: {selected_item.get('unit')}")
            st.markdown(f"- **Số lượng**: {selected_item.get('quantity')}")
            st.markdown(f"- **Đơn giá**: {selected_item.get('unit_price')}")
            st.markdown(f"- **Thành tiền**: {selected_item.get('amount')}")
            st.markdown(f"- **Tiền tệ**: {selected_item.get('currency')}")
            st.text_area("Văn bản gốc làm bằng chứng (Đọc hiểu)", selected_item.get("evidence_text", ""), disabled=True)
            st.text_area("Các cảnh báo hệ thống", str(selected_item.get("warnings", [])), disabled=True)
            
        with col_rev2:
            st.markdown("**Thiết lập rà soát**")
            
            # Map ngược nhãn hiển thị sang backend enum
            existing_type_eng = existing_dec.get("decision_type", "approved")
            default_index = 0
            if existing_type_eng == "rejected":
                default_index = 1
            elif existing_type_eng == "edited":
                default_index = 2
                
            decision_label = st.selectbox(
                "Quyết định rà soát",
                ["Chấp nhận", "Từ chối", "Chỉnh sửa"],
                index=default_index
            )
            
            # Chuyển đổi nhãn sang backend enum
            decision_type = "approved"
            if decision_label == "Từ chối":
                decision_type = "rejected"
            elif decision_label == "Chỉnh sửa":
                decision_type = "edited"
                
            reviewer = st.text_input("Người rà soát", existing_dec.get("reviewer", "tester"))
            reason = st.text_area("Lý do rà soát (Bắt buộc nếu Từ chối hoặc Chỉnh sửa)", existing_dec.get("reason", ""))
            
            field_overrides = {}
            if decision_type == "edited":
                st.markdown("⚙️ **Nhập các trường ghi đè giá trị:**")
                old_overrides = existing_dec.get("field_overrides", {})
                
                over_desc = st.text_input("Mô tả ghi đè", old_overrides.get("description") or selected_item.get("description") or "")
                over_brand = st.text_input("Thương hiệu ghi đè", old_overrides.get("brand") or selected_item.get("brand") or "")
                over_unit = st.text_input("Đơn vị ghi đè", old_overrides.get("unit") or selected_item.get("unit") or "")
                
                over_qty = st.number_input("Số lượng ghi đè", value=float(old_overrides.get("quantity") or selected_item.get("quantity") or 0.0))
                over_price = st.number_input("Đơn giá ghi đè", value=float(old_overrides.get("unit_price") or selected_item.get("unit_price") or 0.0))
                over_amt = st.number_input("Thành tiền ghi đè", value=float(old_overrides.get("amount") or selected_item.get("amount") or 0.0))
                over_curr = st.selectbox("Tiền tệ ghi đè", ["VND", "USD", ""], index=["VND", "USD", ""].index(old_overrides.get("currency") or selected_item.get("currency") or ""))
                
            if st.button("Lưu quyết định"):
                if decision_type in ["rejected", "edited"] and not reason.strip():
                    st.error("Lỗi: Quyết định 'Từ chối' hoặc 'Chỉnh sửa' bắt buộc phải nhập lý do.")
                else:
                    cmd = ["python", "-m", "mep_quotation.cli.main", "record-review", str(package_path),
                           "--draft-item-id", selected_id,
                           "--decision", decision_type,
                           "--reviewer", reviewer,
                           "--reason", reason]
                           
                    if overwrite_review_decisions:
                        cmd.append("--overwrite")
                        
                    if decision_type == "edited":
                        if over_desc:
                            cmd.extend(["--description", over_desc])
                        if over_brand:
                            cmd.extend(["--brand", over_brand])
                        if over_unit:
                            cmd.extend(["--unit", over_unit])
                        if over_qty is not None:
                            cmd.extend(["--quantity", str(over_qty)])
                        if over_price is not None:
                            cmd.extend(["--unit-price", str(over_price)])
                        if over_curr:
                            cmd.extend(["--currency", over_curr])
                        if over_amt is not None:
                            cmd.extend(["--amount", str(over_amt)])
                            
                    code, stdout, stderr = run_cli_command(cmd, timeout=timeout_sec)
                    if code == 0:
                        st.success("Lưu quyết định rà soát thành công!")
                        st.rerun()
                    else:
                        st.error(f"Lưu quyết định thất bại: {stderr}")
else:
    st.info("Chưa có dữ liệu nháp để rà soát. Vui lòng chọn tệp PDF và bấm 'Xử lý báo giá' ở Sidebar.")

# --- MAIN AREA: EXPORT SECTION ---
st.markdown("---")
st.subheader("📤 Xuất kết quả báo giá")

# Kiểm tra xem có bất kỳ quyết định rà soát nào hợp lệ chưa
has_decisions = False
if review_data and "decisions" in review_data and len(review_data["decisions"]) > 0:
    # Có ít nhất 1 dòng được approve hoặc edited
    has_decisions = any(d.get("decision_type") in ["approved", "edited"] for d in review_data["decisions"])

if st.button("Xuất Excel", use_container_width=True):
    if not has_decisions:
        st.error("Cần rà soát ít nhất một dòng trước khi xuất Excel.")
    else:
        # Tự động xuất Normalized Final trước
        ok_norm, missing_norm = check_inputs_exist("export-normalized")
        if not ok_norm:
            st.error("Không thể xuất dữ liệu chuẩn. Thiếu file đầu vào.")
        else:
            # Chạy Phase 11
            cmd_norm = ["python", "-m", "mep_quotation.cli.main", "export-normalized", str(package_path), "--overwrite"]
            code_n, stdout_n, stderr_n = run_cli_command(cmd_norm, timeout=timeout_sec)
            
            if code_n == 0:
                # Chạy Phase 12 Excel Export
                artifact_paths = resolve_artifact_paths(package_path)
                ok_excel, missing_excel = check_inputs_exist("export-excel")
                if not ok_excel:
                    st.error("Không thể xuất Excel. Thiếu file normalized.json.")
                else:
                    cmd_excel = ["python", "-m", "mep_quotation.cli.main", "export-excel", str(package_path), "--overwrite"]
                    code_e, stdout_e, stderr_e = run_cli_command(cmd_excel, timeout=timeout_sec)
                    artifact_paths = resolve_artifact_paths(package_path)
                    
                    if code_e == 0:
                        st.success("Xuất Excel thành công! Tệp tin Excel báo giá đã sẵn sàng để tải xuống.")
                        st.rerun()
                    else:
                        st.error(f"Xuất Excel thất bại: {stderr_e}")
            else:
                st.error(f"Xử lý chuẩn hóa thất bại trước khi xuất Excel: {stderr_n}")

# Nút tải file Excel
excel_file_path = artifact_paths.get("excel_export")
if excel_file_path and excel_file_path.exists():
    with open(excel_file_path, "rb") as f:
        excel_bytes = f.read()
    st.download_button(
        label="📥 Tải file Excel báo giá",
        data=excel_bytes,
        file_name=f"{quotation_id}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("Tệp Excel báo giá chưa được sinh ra.")

# --- MAIN AREA: ARTIFACTS VIEWER TABS (Nâng cao) ---
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
        st.markdown("**Hồ sơ phân tích nguồn (Source Profile):**")
        profile_rel_path = "source/source_profile.json"
        # Thử lấy động từ package.json nếu có khai báo
        pkg_json_file = package_path / "package.json" if package_path else None
        if pkg_json_file and pkg_json_file.exists():
            pkg_data, _ = safe_load_json(pkg_json_file)
            if pkg_data and "files" in pkg_data and "source_profile" in pkg_data["files"]:
                profile_rel_path = pkg_data["files"]["source_profile"]
        
        profile_path = package_path / profile_rel_path if package_path else None
        if profile_path and profile_path.exists():
            profile_data, err = safe_load_json(profile_path)
            if err:
                st.error(err)
            else:
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.markdown(f"- **Tên file**: `{profile_data.get('file_name')}`")
                    st.markdown(f"- **Định dạng**: `{profile_data.get('detected_file_type')}`")
                    st.markdown(f"- **Mime Type**: `{profile_data.get('detected_mime_type')}`")
                    st.markdown(f"- **Dung lượng**: `{profile_data.get('file_size_bytes')} bytes`")
                    st.markdown(f"- **Vai trò đề xuất**: `{profile_data.get('source_role')}` (Độ tự tin: `{profile_data.get('source_role_confidence')}`)")
                    st.markdown(f"- **Hành động tiếp theo**: `{profile_data.get('recommended_next_action')}`")
                    st.markdown(f"- **Cần OCR**: `{profile_data.get('technical_readability', {}).get('requires_ocr')}`")
                    st.markdown(f"- **Cần rà soát thủ công**: `{profile_data.get('requires_human_profile_review')}`")
                
                with col_p2:
                    st.markdown("**Ứng viên ngày tháng phát hiện:**")
                    dates = profile_data.get('date_candidates', [])
                    if dates:
                        df_dates = pd.DataFrame(dates)
                        st.dataframe(df_dates, use_container_width=True)
                    else:
                        st.write("Không phát hiện ngày tháng nào.")

                    st.markdown("**Các cảnh báo rủi ro (Warnings):**")
                    warns = profile_data.get('warnings', [])
                    if warns:
                        df_warns = pd.DataFrame(warns)
                        st.dataframe(df_warns, use_container_width=True)
                    else:
                        st.success("Không có cảnh báo nào.")
                        
                st.markdown("---")
                st.markdown("**Dữ liệu JSON thô:**")
                st.json(profile_data)
        else:
            st.info("Chưa có hồ sơ nguồn. Vui lòng chạy phân tích nguồn.")
            
    with tab_pdf:
        manifest_path = artifact_paths.get("page_manifest")
        if manifest_path and manifest_path.exists():
            manifest_data, _ = safe_load_json(manifest_path)
            if manifest_data and "pages" in manifest_data:
                pages = manifest_data["pages"]
                page_numbers = [p["page_number"] for p in pages]
                selected_page_num = st.selectbox("Chọn trang xem ảnh", page_numbers)
                
                page_info = next((p for p in pages if p["page_number"] == selected_page_num), None)
                if page_info:
                    img_path = package_path / page_info["image_path"]
                    if img_path.exists():
                        try:
                            image = Image.open(img_path)
                            st.image(image, caption=f"Trang {selected_page_num}", use_container_width=True)
                        except Exception as e:
                            st.error(f"Lỗi load ảnh: {e}")
                    else:
                        st.write(f"Không tìm thấy ảnh tại: {img_path}")
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
                selected_raw_page = st.selectbox("Chọn trang xem văn bản thô", page_nums)
                
                raw_page_info = next((p for p in pages if p["page_number"] == selected_raw_page), None)
                if raw_page_info:
                    st.markdown(f"**Has Text:** `{raw_page_info.get('has_text')}` | **Char Count:** `{raw_page_info.get('character_count')}`")
                    st.text_area("Văn bản thô", raw_page_info.get("text", ""), height=400)
            else:
                st.write("Không tìm thấy thông tin trang trong raw_text.json.")
        else:
            st.write("Tệp tin raw_text.json chưa được sinh ra.")
            
    with tab_md:
        md_path = artifact_paths.get("text_markdown")
        if md_path and md_path.exists():
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            st.text_area("Markdown Content", md_content, height=400)
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
