# Kế Hoạch Triển Khai – Phase 2A.5 – PDF Page Preview for Human Review

Kế hoạch này triển khai giao diện PDF Page Preview trực quan kèm tính năng Zoom co giãn để hỗ trợ reviewer đối chiếu trực tiếp bản vẽ gốc khi thực hiện duyệt vật tư.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **PDF Page Preview for Human Review**.
> * **Không ghi dữ liệu vào main pipeline chính và không sửa đổi giao diện Streamlit UI cũ.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế PDF Page Preview & Cache Render

### A. Giao diện & Helper
* **UI App**: [profile_bridge_review_app.py](file:///D:/mep_quotation_pipeline/tools/profile_bridge_review_app.py) (Bổ sung hiển thị ảnh chụp PDF ở cột trái, slider Zoom từ 1.0 đến 3.0).
* **Helper**: [profile_bridge_review_helpers.py](file:///D:/mep_quotation_pipeline/tools/profile_bridge_review_helpers.py) (Bổ sung `render_pdf_page_to_image` có lru_cache, `resolve_session_pdf_path`, `validate_pdf_page_number`).
* **Fallback an toàn**: Nếu tệp PDF không tồn tại (chế độ benchmark mặc định không cấu hình hoặc máy chấm không có file), ứng dụng tự động hiển thị warning và fallback về Source Evidence Text, tuyệt đối không crash.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Khởi chạy Streamlit ứng dụng review:
   ```powershell
   $env:PYTHONUTF8=1; python -m streamlit run tools/profile_bridge_review_app.py --browser.gatherUsageStats false
   ```
2. Chọn dòng vật tư bất kỳ, xác nhận ảnh chụp trang tương ứng xuất hiện sắc nét.
3. Chạy unit tests kiểm định:
  ```powershell
  & .venv\Scripts\pytest tests/test_profile_bridge_pdf_preview.py -q
  ```

---

# Ke hoach trien khai - Phase 2B - Controlled Write Adapter Dry-run

Phase 2B bat dau lop chuyen tiep tu du lieu Profile Bridge da duoc human review sang dang normalized preview. Pham vi hien tai chi la dry-run an toan, khong ghi vao main pipeline, khong database, khong sua package normalized chinh thuc.

## Muc tieu

1. Doc `profile_bridge_items.json` va `profile_bridge_review_decisions.json`.
2. Chi cho phep cac dong co decision hop le di tiep:
   - `APPROVE`
   - `EDIT_AND_APPROVE`
   - `ACCEPT_WITH_LIMITATION`
3. Chan cac dong:
   - `REJECT`
   - `NEEDS_INVESTIGATION`
   - chua co human decision
4. Sinh output reviewable tai `feasibility_outputs/profile_write_adapter_dry_run/`.
5. Giu `ready_for_write_to_main_pipeline = false`.

## Artifact

- `tools/feasibility/profile_write_adapter_contract.json`
- `tools/feasibility/run_profile_write_adapter_dry_run.py`
- `tests/test_profile_write_adapter_dry_run.py`
- `feasibility_outputs/profile_write_adapter_dry_run/normalized_items_preview.json`
- `feasibility_outputs/profile_write_adapter_dry_run/blocked_items.json`
- `feasibility_outputs/profile_write_adapter_dry_run/profile_write_adapter_summary.json`
- `feasibility_outputs/profile_write_adapter_dry_run/profile_write_adapter_report.md`

## Lenh chay

```powershell
python tools/feasibility/run_profile_write_adapter_dry_run.py
```

## Nguyen tac an toan

- Khong write main pipeline.
- Khong ghi database.
- Khong su dung moi `supplier_code + material_code` lam write key.
- Khong export dong `NEEDS_INVESTIGATION`.
- Khong export dong chua duoc human review.
