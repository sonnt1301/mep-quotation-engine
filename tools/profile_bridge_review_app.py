# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import datetime
from pathlib import Path
import json
import shutil

from tools.profile_bridge_review_helpers import (
    load_bridge_items,
    load_review_sample,
    load_duplicate_review,
    build_review_item_key,
    compute_default_amount,
    validate_decision_reason,
    validate_duplicate_group_decision,
    load_review_decisions,
    save_review_decisions,
    summarize_review_progress,
    filter_items,
    # Các helper mới
    resolve_selected_profile_config,
    create_review_session_folder,
    validate_pdf_input,
    run_parser_on_pdf,
    run_bridge_on_session,
    build_duplicate_review_rows,
    resolve_session_pdf_path,
    validate_pdf_page_number,
    render_pdf_page_to_image
)

# Cấu hình trang Streamlit
st.set_page_config(layout="wide", page_title="Profile Bridge Review Workspace", page_icon="⚙️")

# --- Path Configurations for Benchmark ---
PDF_PATHS = {
    "ABB": Path("D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf"),
    "LS": Path("F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf")
}

# Dò tìm file CHINT động
chint_pdf = None
for p in [Path("F:/00.HVC/Bang gia/Bang gia VT Tu dien/Chint"), Path("F:/00.HVC/Bang gia/Bang gia VT Tu dien - Copy/Chint")]:
    if p.exists():
        for f in p.glob("*.pdf"):
            if "1-3-2023" in f.name:
                chint_pdf = f
                break
    if chint_pdf:
        break
if chint_pdf:
    PDF_PATHS["CHINT"] = chint_pdf

# 1. Đường dẫn tệp tin
ITEMS_JSON = Path("feasibility_outputs/profile_bridge_dry_run/profile_bridge_items.json")
SAMPLE_CSV = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_review_sample.csv")
DUPLICATE_CSV = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_duplicate_code_review.csv")
SUMMARY_JSON = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_human_review_summary.json")

DECISIONS_JSON = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_review_decisions.json")
DECISIONS_CSV = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_review_decisions.csv")
SESSION_JSON = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_review_session_summary.json")
SESSION_MD = Path("feasibility_outputs/profile_bridge_human_review/profile_bridge_review_session_summary.md")

# Khởi tạo session_state
if "decisions" not in st.session_state:
    st.session_state.decisions = load_review_decisions(DECISIONS_JSON)
if "selected_item_index" not in st.session_state:
    st.session_state.selected_item_index = 0
if "selected_dup_index" not in st.session_state:
    st.session_state.selected_dup_index = 0
if "session_bridge_items_path" not in st.session_state:
    st.session_state.session_bridge_items_path = None
if "session_summary" not in st.session_state:
    st.session_state.session_summary = None
if "data_source" not in st.session_state:
    st.session_state.data_source = "Dữ liệu Benchmark mặc định"

def save_all_decisions(decisions_dict):
    save_review_decisions(DECISIONS_JSON, DECISIONS_CSV, decisions_dict)
    # Cập nhật session summary
    progress_stats = summarize_review_progress(st.session_state.current_list, decisions_dict)
    
    # Save session summary json
    session_summary = {
        "generated_at": datetime.datetime.now().isoformat() + "Z",
        "total_items": progress_stats["total_rows"],
        "reviewed_items": progress_stats["reviewed"],
        "unreviewed_items": progress_stats["unreviewed"],
        "progress_percent": progress_stats["progress_percent"],
        "counts": progress_stats["counts"],
        "proposed_status": "READY_FOR_HUMAN_REVIEW",
        "ready_for_write_to_main_pipeline": False
    }
    
    with open(SESSION_JSON, "w", encoding="utf-8") as f:
        json.dump(session_summary, f, ensure_ascii=False, indent=2)
        
    # Save session summary md
    md_text = f"""# Báo Cáo Tiến Độ Review – Session Summary

Báo cáo tiến độ cập nhật thực tế từ phiên làm việc của Human Reviewer.

---

## 1. Thống Kê Tiến Độ Review

* **Thời Gian Cập Nhật**: {session_summary["generated_at"]}
* **Tổng Số Vật Tư Cần Review**: {session_summary["total_items"]}
* **Đã Review**: {session_summary["reviewed_items"]} ({session_summary["progress_percent"]}%)
* **Chưa Review**: {session_summary["unreviewed_items"]}
* **Quyết Định Chi Tiết**:
  * **APPROVE**: {session_summary["counts"]["APPROVE"]}
  * **EDIT_AND_APPROVE**: {session_summary["counts"]["EDIT_AND_APPROVE"]}
  * **REJECT**: {session_summary["counts"]["REJECT"]}
  * **NEEDS_INVESTIGATION**: {session_summary["counts"]["NEEDS_INVESTIGATION"]}
  * **ACCEPT_WITH_LIMITATION**: {session_summary["counts"]["ACCEPT_WITH_LIMITATION"]}

---

## 2. Trạng Thái Tiếp Theo Đề Xuất

* **Trạng thái đề xuất**: **`READY_FOR_HUMAN_REVIEW`**
* **Sẵn sàng ghi trực tiếp vào main pipeline**: **`FALSE`**
"""
    with open(SESSION_MD, "w", encoding="utf-8") as f:
        f.write(md_text.strip())

st.title("⚙️ Profile Bridge Review Workspace")
st.caption("Giao diện review dữ liệu cầu nối Integration Bridge phục vụ đánh giá tính khả thi (Feasibility Reset)")

# ========================================================
# Giao diện PDF Intake & Processing Expander
# ========================================================
st.markdown("---")
with st.expander("📥 Thêm & Xử lý PDF mới (PDF Intake & Processing Flow)", expanded=st.session_state.session_bridge_items_path is None):
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        selected_supplier = st.selectbox(
            "Chọn Supplier / Profile Config",
            ["ABB", "LS", "CHINT"],
            help="Chỉ hỗ trợ bóc tách các hãng đã cấu hình profile."
        )
        input_method = st.radio(
            "Phương pháp nhập tệp PDF",
            ["Upload tệp PDF", "Đường dẫn file trên máy (Local Path)"]
        )
    with col_in2:
        uploaded_file = None
        local_path_str = ""
        if input_method == "Upload tệp PDF":
            uploaded_file = st.file_uploader("Kéo thả hoặc chọn tệp PDF", type=["pdf"])
        else:
            local_path_str = st.text_input("Nhập đường dẫn tuyệt đối tới tệp PDF trên máy", value="")
            st.caption("Ví dụ: `F:\\00.HVC\\Bang gia\\Bang gia VT Tu dien\\Chint\\Bảng giá Chint 1-3-2023 ck 50.pdf`")
            
    btn_process = st.button("🚀 Bắt đầu xử lý PDF", type="primary")
    
    if btn_process:
        # Xử lý PDF Intake
        st.info("Đang kiểm tra tệp đầu vào...")
        is_valid = True
        err_msg = ""
        pdf_file_path = None
        pdf_display_name = ""
        
        if input_method == "Upload tệp PDF":
            if uploaded_file is None:
                is_valid = False
                err_msg = "Vui lòng chọn tệp PDF tải lên."
            else:
                pdf_display_name = uploaded_file.name
        else:
            is_valid, err_msg = validate_pdf_input(local_path_str)
            if is_valid:
                pdf_file_path = Path(local_path_str)
                pdf_display_name = pdf_file_path.name
                
        if not is_valid:
            st.error(f"❌ Kiểm tra tệp đầu vào thất bại: {err_msg}")
        else:
            # Tạo thư mục session riêng
            try:
                with st.spinner("Đang khởi tạo thư mục làm việc session..."):
                    session_dir = create_review_session_folder(selected_supplier)
                    
                # Save file PDF
                if input_method == "Upload tệp PDF":
                    pdf_file_path = session_dir / uploaded_file.name
                    with open(pdf_file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                else:
                    # Copy file local vào session folder
                    dest_path = session_dir / pdf_file_path.name
                    shutil.copy(str(pdf_file_path), str(dest_path))
                    pdf_file_path = dest_path
                    
                # Lấy config tương ứng
                config_path = resolve_selected_profile_config(selected_supplier)
                
                with st.spinner(f"Đang thực thi bóc tách PDF bằng Supplier Profile Parser ({selected_supplier})..."):
                    parse_res = run_parser_on_pdf(selected_supplier, pdf_file_path, config_path, session_dir)
                    
                with st.spinner("Đang chạy cầu nối chuyển đổi trung gian (Bridge Dry-run)..."):
                    session_bridge_path = run_bridge_on_session(selected_supplier, session_dir, pdf_file_path)
                    
                # Lưu vào state
                st.session_state.session_bridge_items_path = str(session_bridge_path.resolve())
                st.session_state.session_summary = parse_res
                st.session_state.session_supplier = selected_supplier
                st.session_state.session_pdf_name = pdf_display_name
                st.session_state.data_source = "Phiên xử lý PDF vừa chạy"
                st.session_state.review_mode = "All Bridged Items"
                st.session_state.selected_item_index = 0
                st.session_state.selected_dup_index = 0
                
                st.success("🎉 Xử lý PDF thành công! Dữ liệu của phiên chạy đã được nạp tự động vào giao diện review bên dưới.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Đã xảy ra lỗi trong quá trình xử lý: {str(e)}")

    # Hiển thị summary sau xử lý nếu có
    if st.session_state.session_summary:
        st.markdown("---")
        st.markdown("### 📊 Kết Quả Phiên Xử Lý Vừa Chạy (Session Summary)")
        col_sum1, col_sum2, col_sum3 = st.columns(3)
        with col_sum1:
            st.markdown(f"**Supplier**: `{st.session_state.session_supplier}`")
            st.markdown(f"**File PDF**: `{st.session_state.session_pdf_name}`")
        with col_sum2:
            st.markdown(f"**Số dòng hợp lệ (Valid)**: `{st.session_state.session_summary['valid_count']}`")
            st.markdown(f"**Số dòng lỗi (Invalid)**: `{st.session_state.session_summary['invalid_count']}`")
        with col_sum3:
            st.markdown(f"**Vị trí lưu Session**: `{st.session_state.session_bridge_items_path}`")
            st.markdown("**Trạng thái**: `Sẵn sàng review` | `ready_for_write_to_main_pipeline = FALSE`")
            
        if st.button("🗑️ Xóa phiên session (Quay lại Benchmark)"):
            st.session_state.session_bridge_items_path = None
            st.session_state.session_summary = None
            st.session_state.data_source = "Dữ liệu Benchmark mặc định"
            st.session_state.review_mode = "Sample Review"
            st.session_state.selected_item_index = 0
            st.session_state.selected_dup_index = 0
            st.rerun()

st.markdown("---")

# Sidebar lọc dữ liệu
st.sidebar.header("🔍 Bộ Lọc Review")

# Cho phép chuyển đổi nguồn dữ liệu
data_source_options = ["Dữ liệu Benchmark mặc định"]
if st.session_state.session_bridge_items_path:
    data_source_options.append("Phiên xử lý PDF vừa chạy")
    
st.session_state.data_source = st.sidebar.radio(
    "Nguồn dữ liệu review",
    data_source_options,
    index=1 if st.session_state.session_bridge_items_path and st.session_state.data_source == "Phiên xử lý PDF vừa chạy" else 0
)

# Đăng ký mặc định review_mode trong session_state
if "review_mode" not in st.session_state:
    st.session_state.review_mode = "Sample Review"

# Xác định index mặc định cho selectbox
review_mode_options = ["Sample Review", "Duplicate Code Review", "All Bridged Items"]
try:
    default_index = review_mode_options.index(st.session_state.review_mode)
except ValueError:
    default_index = 0

review_mode = st.sidebar.selectbox(
    "Chế độ review",
    review_mode_options,
    index=default_index
)
st.session_state.review_mode = review_mode

supplier_filter = st.sidebar.selectbox(
    "Nhà cung cấp (Supplier)",
    ["ALL", "ABB", "LS", "CHINT"]
)

page_filter = st.sidebar.text_input("Source Page (Ví dụ: 3, 5, hoặc ALL)", value="ALL")

status_filter = st.sidebar.selectbox(
    "Trạng thái review",
    ["ALL", "UNREVIEWED", "APPROVE", "EDIT_AND_APPROVE", "REJECT", "NEEDS_INVESTIGATION", "ACCEPT_WITH_LIMITATION"]
)

risk_filter = "ALL"
if review_mode == "Duplicate Code Review":
    risk_filter = st.sidebar.selectbox(
        "Mức độ rủi ro trùng mã (Risk)",
        ["ALL", "HIGH", "MEDIUM", "LOW"]
    )

search_query = st.sidebar.text_input("Tìm kiếm (Mã vật tư / Mô tả)")

# Nạp dữ liệu nguồn
if review_mode == "Sample Review":
    st.session_state.current_list = load_review_sample(SAMPLE_CSV)
elif review_mode == "Duplicate Code Review":
    if st.session_state.data_source == "Phiên xử lý PDF vừa chạy" and st.session_state.session_bridge_items_path:
        session_items = load_bridge_items(Path(st.session_state.session_bridge_items_path))
        st.session_state.current_list = build_duplicate_review_rows(session_items)
    else:
        st.session_state.current_list = load_duplicate_review(DUPLICATE_CSV)
else:
    if st.session_state.data_source == "Phiên xử lý PDF vừa chạy" and st.session_state.session_bridge_items_path:
        st.session_state.current_list = load_bridge_items(Path(st.session_state.session_bridge_items_path))
    else:
        st.session_state.current_list = load_bridge_items(ITEMS_JSON)

# Lọc danh sách hiển thị
if review_mode == "Duplicate Code Review":
    # Lọc cho duplicate review
    items_to_show = []
    for it in st.session_state.current_list:
        if supplier_filter != "ALL" and it["supplier_code"] != supplier_filter:
            continue
        if risk_filter != "ALL" and it["risk_level"] != risk_filter:
            continue
        if search_query:
            q = search_query.lower()
            code = it["normalized_material_code"].lower()
            if q not in code:
                continue
        items_to_show.append(it)
else:
    # Lọc cho sample hoặc all bridged items
    items_to_show = filter_items(
        st.session_state.current_list,
        supplier_filter,
        page_filter,
        status_filter,
        search_query,
        st.session_state.decisions
    )

# Dashboard Tiến Độ
progress_data = summarize_review_progress(st.session_state.current_list, st.session_state.decisions)
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
with col_stat1:
    st.metric("Tổng vật tư cần review", progress_data["total_rows"])
with col_stat2:
    st.metric("Đã review", progress_data["reviewed"])
with col_stat3:
    st.metric("Tiến độ", f"{progress_data['progress_percent']}%")
with col_stat4:
    st.metric("Chưa review", progress_data["unreviewed"])

if progress_data["has_warning"]:
    st.warning("⚠️ Đang tồn tại dòng có trạng thái REJECT hoặc NEEDS_INVESTIGATION. Không được phép chuyển sang Phase 2B Write Adapter khi chưa xử lý hết cảnh báo.")

if st.session_state.data_source == "Phiên xử lý PDF vừa chạy" and st.session_state.session_bridge_items_path:
    st.info(f"ℹ️ Đang review phiên PDF vừa xử lý: {st.session_state.session_supplier} / {st.session_state.session_pdf_name} ({st.session_state.session_bridge_items_path})")

# Phân chia bố cục làm việc chính: 2 Cột
col_left, col_right = st.columns([1, 1])

# CHẾ ĐỘ 1 & 3: REVIEW TỪNG DÒNG (SAMPLE HOẶC ALL BRIDGED ITEMS)
if review_mode != "Duplicate Code Review":
    if not items_to_show:
        st.info("Không có dòng nào thỏa mãn bộ lọc hiện tại.")
    else:
        # Đảm bảo index được chọn không vượt quá độ dài danh sách lọc
        if st.session_state.selected_item_index >= len(items_to_show):
            st.session_state.selected_item_index = 0
            
        selected_item = items_to_show[st.session_state.selected_item_index]
        item_key = build_review_item_key(selected_item)
        existing_decision = st.session_state.decisions.get(item_key, {})
        
        # ------------------------------------------------
        # CỘT TRÁI: THÔNG TIN GỐC & EVIDENCE (TÍCH HỢP PDF PREVIEW)
        # ------------------------------------------------
        with col_left:
            st.subheader("📄 Nguồn Đối Chiếu & Bằng Chứng")
            
            # Xác định đường dẫn file PDF để preview
            pdf_path = None
            if st.session_state.data_source == "Phiên xử lý PDF vừa chạy" and st.session_state.session_bridge_items_path:
                try:
                    session_dir = Path(st.session_state.session_bridge_items_path).parent
                    pdf_path = resolve_session_pdf_path(session_dir)
                except Exception:
                    pdf_path = None
            else:
                supplier_code = selected_item.get("supplier_code")
                pdf_path = PDF_PATHS.get(supplier_code)

            # Thực hiện render preview nếu file PDF tồn tại và trang hợp lệ
            preview_rendered = False
            source_page = selected_item.get("source_page", 1)
            
            if pdf_path and pdf_path.exists():
                ok, err = validate_pdf_page_number(pdf_path, source_page)
                if ok:
                    try:
                        zoom_scale = st.slider("Độ thu phóng PDF Preview (Zoom)", 1.0, 3.0, 1.5, 0.5, key="zoom_scale_slider")
                        with st.spinner("Đang render trang PDF preview..."):
                            img_bytes = render_pdf_page_to_image(pdf_path, source_page, scale=zoom_scale)
                        st.image(img_bytes, caption=f"Trang PDF gốc: trang {source_page}", use_column_width=True)
                        preview_rendered = True
                    except Exception as e:
                        st.warning(f"⚠️ Render PDF preview thất bại: {str(e)}")
                else:
                    st.warning(f"⚠️ Kiểm tra số trang PDF thất bại: {err}")
            
            if not preview_rendered:
                st.warning("⚠️ Không thể render PDF preview hoặc không có tệp PDF gốc. Hiển thị bằng chứng dạng văn bản dưới đây.")
            
            st.text_input("Nhà cung cấp gốc (Supplier)", selected_item.get("supplier_code"), disabled=True)
            st.text_input("Trang PDF gốc (Source Page)", str(selected_item.get("source_page")), disabled=True)
            st.text_input("Tên Layout nhận dạng", selected_item.get("source_layout_name", "N/A"), disabled=True)
            
            st.markdown("**Văn bản bằng chứng (Source Evidence Text)**:")
            st.code(selected_item.get("source_evidence_text", "N/A"), language="text")
            
            st.markdown("**Đường dẫn nguồn gốc (Provenance)**:")
            st.caption(selected_item.get("provenance", "N/A"))
            
            st.info("💡 Nguyên tắc: Đối chiếu mã vật tư và đơn giá hiển thị trong evidence text hoặc ảnh PDF trước khi quyết định APPROVE.")
            
        # ------------------------------------------------
        # CỘT PHẢI: FORM CHỈNH SỬA & QUYẾT ĐỊNH
        # ------------------------------------------------
        with col_right:
            st.subheader("✏️ Chỉnh Sửa & Quyết Định")
            
            # Form chỉnh sửa
            with st.form("edit_form"):
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    reviewed_code = st.text_input(
                        "Mã vật tư chuẩn hóa (normalized_material_code)", 
                        value=existing_decision.get("normalized_material_code_reviewed", selected_item.get("normalized_material_code"))
                    )
                    reviewed_unit = st.text_input(
                        "Đơn vị tính (unit)", 
                        value=existing_decision.get("unit_reviewed", selected_item.get("unit", "cái"))
                    )
                    reviewed_qty = st.number_input(
                        "Số lượng (quantity)", 
                        value=float(existing_decision.get("quantity_reviewed", 1.0)),
                        step=1.0
                    )
                with col_form2:
                    reviewed_price = st.number_input(
                        "Đơn giá (unit_price)", 
                        value=int(existing_decision.get("unit_price_reviewed", selected_item.get("unit_price"))),
                        step=1000
                    )
                    reviewed_currency = st.text_input(
                        "Tiền tệ (currency)", 
                        value=existing_decision.get("currency_reviewed", "VND")
                    )
                    reviewed_amount = st.number_input(
                        "Thành tiền (amount)", 
                        value=int(existing_decision.get("amount_reviewed", compute_default_amount(reviewed_qty, reviewed_price))),
                        step=1000
                    )
                    
                reviewed_desc = st.text_area(
                    "Mô tả thiết bị (description)", 
                    value=existing_decision.get("description_reviewed", selected_item.get("description"))
                )
                
                col_tech1, col_tech2, col_tech3 = st.columns(3)
                with col_tech1:
                    tech_family = st.text_input("Product Family", value=selected_item.get("product_family", ""))
                with col_tech2:
                    tech_current = st.text_input("Rated Current", value=selected_item.get("rated_current", ""))
                with col_tech3:
                    tech_breaking = st.text_input("Breaking Capacity", value=selected_item.get("breaking_capacity", ""))
                    
                tech_pole = st.text_input("Pole", value=selected_item.get("pole", ""))
                
                human_note = st.text_area(
                    "Ghi chú review / Lý do điều chỉnh (Bắt buộc nếu EDIT/REJECT/NEEDS_INVESTIGATION)",
                    value=existing_decision.get("human_note", "")
                )
                
                st.markdown("---")
                st.markdown("**Hành động quyết định (Decision Actions)**:")
                
                col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns(5)
                
                # Biến kiểm soát nút
                submitted_decision = None
                
                with col_btn1:
                    if st.form_submit_button("APPROVE", type="primary"):
                        submitted_decision = "APPROVE"
                with col_btn2:
                    if st.form_submit_button("EDIT & APPROVE"):
                        submitted_decision = "EDIT_AND_APPROVE"
                with col_btn3:
                    if st.form_submit_button("REJECT"):
                        submitted_decision = "REJECT"
                with col_btn4:
                    if st.form_submit_button("NEEDS INVESTIGATION"):
                        submitted_decision = "NEEDS_INVESTIGATION"
                with col_btn5:
                    if st.form_submit_button("LIMITATION"):
                        submitted_decision = "ACCEPT_WITH_LIMITATION"
                        
                if submitted_decision:
                    # Validate lý do
                    is_ok, err_msg = validate_decision_reason(submitted_decision, human_note)
                    if not is_ok:
                        st.error(err_msg)
                    else:
                        decision_record = {
                            "review_decision_id": f"DEC_{item_key}_{int(datetime.datetime.now().timestamp())}",
                            "review_item_key": item_key,
                            "review_mode": review_mode,
                            "supplier_code": selected_item.get("supplier_code"),
                            "source_page": int(selected_item.get("source_page")),
                            "normalized_material_code_original": selected_item.get("normalized_material_code"),
                            "normalized_material_code_reviewed": reviewed_code,
                            "description_original": selected_item.get("description"),
                            "description_reviewed": reviewed_desc,
                            "unit_original": selected_item.get("unit"),
                            "unit_reviewed": reviewed_unit,
                            "quantity_reviewed": float(reviewed_qty),
                            "unit_price_original": int(selected_item.get("unit_price")),
                            "unit_price_reviewed": int(reviewed_price),
                            "amount_reviewed": int(reviewed_amount),
                            "currency_original": selected_item.get("currency"),
                            "currency_reviewed": reviewed_currency,
                            "decision": submitted_decision,
                            "human_note": human_note,
                            "reviewer": "human_reviewer",
                            "reviewed_at": datetime.datetime.now().isoformat() + "Z",
                            "provenance": selected_item.get("provenance"),
                            "source_evidence_text": selected_item.get("source_evidence_text")
                        }
                        # Lưu vào state
                        st.session_state.decisions[item_key] = decision_record
                        save_all_decisions(st.session_state.decisions)
                        st.success(f"Đã lưu quyết định: {submitted_decision} cho {reviewed_code}")
                        
                        # Tự động nhảy sang dòng tiếp theo
                        if st.session_state.selected_item_index < len(items_to_show) - 1:
                            st.session_state.selected_item_index += 1
                        else:
                            st.session_state.selected_item_index = 0
                        st.rerun()

        # Nút chuyển dòng thủ công
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("⬅️ Dòng trước (Previous)"):
                if st.session_state.selected_item_index > 0:
                    st.session_state.selected_item_index -= 1
                    st.rerun()
        with col_nav2:
            if st.button("➡️ Dòng tiếp theo (Next)"):
                if st.session_state.selected_item_index < len(items_to_show) - 1:
                    st.session_state.selected_item_index += 1
                    st.rerun()

        # Hiển thị danh sách bảng items
        st.markdown("---")
        st.subheader("📋 Bảng danh sách vật tư bóc tách")
        
        table_rows = []
        for idx, it in enumerate(items_to_show):
            key = build_review_item_key(it)
            status = st.session_state.decisions.get(key, {}).get("decision", "UNREVIEWED")
            table_rows.append({
                "STT": idx,
                "Status": status,
                "Supplier": it.get("supplier_code"),
                "Page": it.get("source_page"),
                "Material Code": it.get("normalized_material_code"),
                "Description": it.get("description"),
                "Unit Price": it.get("unit_price")
            })
            
        df = pd.DataFrame(table_rows)
        st.dataframe(df, use_container_width=True)

# CHẾ ĐỘ 2: REVIEW NHÓM TRÙNG MÃ (DUPLICATE CODE REVIEW)
else:
    if not items_to_show:
        st.info("Không có nhóm trùng mã nào thỏa mãn bộ lọc hiện tại.")
    else:
        if st.session_state.selected_dup_index >= len(items_to_show):
            st.session_state.selected_dup_index = 0
            
        selected_dup = items_to_show[st.session_state.selected_dup_index]
        supplier = selected_dup["supplier_code"]
        code = selected_dup["normalized_material_code"]
        risk_level = selected_dup["risk_level"]
        
        # Load tất cả các item thuộc nhóm trùng mã này từ file items gốc hoặc session items
        if st.session_state.data_source == "Phiên xử lý PDF vừa chạy" and st.session_state.session_bridge_items_path:
            all_items = load_bridge_items(Path(st.session_state.session_bridge_items_path))
        else:
            all_items = load_bridge_items(ITEMS_JSON)
        group_items = [ it for it in all_items if it["supplier_code"] == supplier and it["normalized_material_code"] == code ]
        
        item_key = f"DUP_GROUP_{supplier}_{code}"
        existing_decision = st.session_state.decisions.get(item_key, {})
        
        # ------------------------------------------------
        # CỘT TRÁI: THÔNG TIN NHÓM & GỢI Ý KHÓA GHI DUY NHẤT
        # ------------------------------------------------
        with col_left:
            st.subheader("⚠️ Nhóm Trùng Mã Cần Review")
            st.warning(f"Mức độ rủi ro của nhóm: **{risk_level}**")
            
            st.text_input("Nhà cung cấp", supplier, disabled=True)
            st.text_input("Mã hàng chuẩn hóa", code, disabled=True)
            st.text_input("Khóa ghi duy nhất khuyến nghị (recommended_write_key)", selected_dup["recommended_write_key"], disabled=True)
            
            st.markdown("**Lưu ý kỹ thuật**:")
            st.info("👉 Tuyệt đối không dùng 'supplier_code + normalized_material_code' làm khóa ghi dữ liệu duy nhất cho Phase 2B Write Adapter để tránh việc các dòng trùng mã ghi đè sai giá trị của nhau.")
            
            st.markdown("**Mẫu văn bản bằng chứng của nhóm**:")
            st.code(selected_dup["evidence_sample"], language="text")
            
        # ------------------------------------------------
        # CỘT PHẢI: DANH SÁCH DÒNG CON & QUYẾT ĐỊNH CẤP NHÓM
        # ------------------------------------------------
        with col_right:
            st.subheader("📋 Các Dòng Thuộc Nhóm Trùng Mã")
            
            dup_table_rows = []
            for it in group_items:
                dup_table_rows.append({
                    "Page": it.get("source_page"),
                    "Description": it.get("description"),
                    "Unit Price": it.get("unit_price"),
                    "Unit": it.get("unit"),
                    "Evidence Text": it.get("evidence_text")
                })
            st.dataframe(pd.DataFrame(dup_table_rows), use_container_width=True)
            
            # Form quyết định nhóm
            with st.form("dup_group_form"):
                human_note = st.text_area(
                    "Ghi chú lý do review nhóm (Bắt buộc nếu nhóm rủi ro HIGH)",
                    value=existing_decision.get("human_note", "")
                )
                
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                submitted_decision = None
                
                with col_btn1:
                    if st.form_submit_button("APPROVE GROUP", type="primary"):
                        submitted_decision = "APPROVE_GROUP"
                with col_btn2:
                    if st.form_submit_button("REJECT GROUP"):
                        submitted_decision = "REJECT_GROUP"
                with col_btn3:
                    if st.form_submit_button("NEEDS INVESTIGATION"):
                        submitted_decision = "NEEDS_INVESTIGATION"
                with col_btn4:
                    if st.form_submit_button("LIMITATION GROUP"):
                        submitted_decision = "ACCEPT_WITH_LIMITATION"
                        
                if submitted_decision:
                    # Validate lý do nhóm rủi ro HIGH
                    is_ok, err_msg = validate_duplicate_group_decision(submitted_decision, human_note, risk_level)
                    if not is_ok:
                        st.error(err_msg)
                    else:
                        decision_record = {
                            "review_decision_id": f"DEC_GROUP_{item_key}_{int(datetime.datetime.now().timestamp())}",
                            "review_item_key": item_key,
                            "review_mode": review_mode,
                            "supplier_code": supplier,
                            "source_page": 0, # Cấp nhóm
                            "normalized_material_code_original": code,
                            "normalized_material_code_reviewed": code,
                            "decision": submitted_decision,
                            "human_note": human_note,
                            "reviewer": "human_reviewer",
                            "reviewed_at": datetime.datetime.now().isoformat() + "Z",
                            "provenance": f"Group of {len(group_items)} items for code {code}",
                            "source_evidence_text": selected_dup["evidence_sample"]
                        }
                        
                        st.session_state.decisions[item_key] = decision_record
                        save_all_decisions(st.session_state.decisions)
                        st.success(f"Đã lưu quyết định nhóm: {submitted_decision}")
                        
                        if st.session_state.selected_dup_index < len(items_to_show) - 1:
                            st.session_state.selected_dup_index += 1
                        else:
                            st.session_state.selected_dup_index = 0
                        st.rerun()

        # Nút chuyển dòng thủ công
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("⬅️ Nhóm trước"):
                if st.session_state.selected_dup_index > 0:
                    st.session_state.selected_dup_index -= 1
                    st.rerun()
        with col_nav2:
            if st.button("➡️ Nhóm tiếp theo"):
                if st.session_state.selected_dup_index < len(items_to_show) - 1:
                    st.session_state.selected_dup_index += 1
                    st.rerun()

        # Bảng nhóm trùng mã
        st.markdown("---")
        st.subheader("📋 Bảng các nhóm trùng mã")
        
        dup_table_summary = []
        for idx, it in enumerate(items_to_show):
            key = f"DUP_GROUP_{it['supplier_code']}_{it['normalized_material_code']}"
            status = st.session_state.decisions.get(key, {}).get("decision", "UNREVIEWED")
            dup_table_summary.append({
                "STT": idx,
                "Status": status,
                "Supplier": it["supplier_code"],
                "Material Code": it["normalized_material_code"],
                "Risk Level": it["risk_level"],
                "Occurrence Count": it["occurrence_count"],
                "Distinct Price Count": it["distinct_price_count"],
                "Prices List": it["prices"],
                "Recommended Write Key": it["recommended_write_key"]
            })
        st.dataframe(pd.DataFrame(dup_table_summary), use_container_width=True)

# Tải xuống kết quả review
st.markdown("---")
st.subheader("💾 Lưu & Tải Xuất Quyết Định")

col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    st.info("ℹ️ Quyết định review được lưu tự động xuống tệp tin cục bộ trong thư mục: `feasibility_outputs/profile_bridge_human_review/profile_bridge_review_decisions.json` và `.csv`.")
    if st.button("🔄 Đồng bộ lại tệp tin"):
        save_all_decisions(st.session_state.decisions)
        st.success("Đã đồng bộ hóa thành công và cập nhật session summary.")
with col_exp2:
    # Cho phép tải xuống CSV qua browser
    try:
        if DECISIONS_CSV.exists():
            with open(DECISIONS_CSV, "rb") as f:
                st.download_button(
                    label="📥 Tải xuống CSV Quyết Định",
                    data=f,
                    file_name="profile_bridge_review_decisions.csv",
                    mime="text/csv"
                )
        else:
            st.warning("Chưa có quyết định nào được lưu để tải xuống.")
    except Exception as e:
        st.error(f"Lỗi khi đọc tệp download: {str(e)}")
