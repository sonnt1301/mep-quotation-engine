# Walkthrough – Phase 2A.5 – PDF Page Preview for Human Review

Tất cả các mục tiêu phát triển giao diện PDF Page Preview trực quan kèm tính năng Zoom co giãn hỗ trợ rà soát thực tế đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Visual Human Review Workspace**.
> * **Không ghi dữ liệu vào main pipeline chính và không sửa đổi giao diện Streamlit UI cũ.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Triển Khai PDF Page Preview

1. **PDF Page Preview Trực Quan**:
   - Sử dụng PyMuPDF (`fitz`) để render cực nhanh trang PDF của mỗi vật tư đang được chọn review thành ảnh PNG.
   - Hình ảnh hiển thị trực quan ở cột bên trái **📄 Nguồn Đối Chiếu & Bằng Chứng** ngay phía trên thông tin metadata và văn bản bằng chứng thô.
   - Tự động thay đổi trang hiển thị tương ứng theo `source_page` của vật tư đang được kích hoạt.

2. **Thanh trượt điều chỉnh Zoom (scale/DPI)**:
   - Tích hợp thanh trượt `st.slider` hỗ trợ phóng to bản vẽ trang PDF (từ 1.0 đến 3.0) trực tiếp trên UI.
   - Sử dụng `lru_cache` để tối ưu hóa hiệu năng, giảm thiểu tối đa việc render lại trang PDF cũ khi thay đổi độ thu phóng hoặc chuyển dòng.

3. **Fallback & Khả năng chịu lỗi**:
   - Nếu tệp PDF không tồn tại (chế độ benchmark mặc định không cấu hình hoặc không tìm thấy tệp) hoặc gặp sự cố render, hệ thống tự động fallback hiển thị **Source Evidence Text** thô kèm theo thông báo warning, hoàn toàn không gây crash ứng dụng.

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 195 unit tests đã vượt qua thành công: **195/195 passed** (tỷ lệ 100%).
* Đã tạo tệp unit test bảo vệ preview: [test_profile_bridge_pdf_preview.py](file:///D:/mep_quotation_pipeline/tests/test_profile_bridge_pdf_preview.py)
  - Xác minh chức năng render trang PDF thành ảnh PNG bytes hợp lệ.
  - Kiểm thử số trang vượt phạm vi ném lỗi ValueError an toàn.
  - Kiểm thử `validate_pdf_page_number` và `resolve_session_pdf_path` hoạt động chính xác.
  - Rà soát tĩnh chống mojibake tiếng Việt.
# Walkthrough - Phase 2B - Controlled Write Adapter Dry-run

Phase 2B tao lop adapter an toan de bien cac dong Profile Bridge da duoc human review thanh normalized preview. Day chua phai write adapter that vao main pipeline.

## Cach chay

```powershell
cd D:\mep_quotation_pipeline
python tools/feasibility/run_profile_write_adapter_dry_run.py
```

Neu can chi dinh decisions/session rieng:

```powershell
python tools/feasibility/run_profile_write_adapter_dry_run.py `
  --bridge-items feasibility_outputs/profile_bridge_dry_run/profile_bridge_items.json `
  --decisions feasibility_outputs/profile_bridge_human_review/profile_bridge_review_decisions.json `
  --output-dir feasibility_outputs/profile_write_adapter_dry_run
```

## Output

- `normalized_items_preview.json`: cac dong du dieu kien export preview.
- `blocked_items.json`: cac dong bi chan do reject, needs investigation, hoac chua review.
- `profile_write_adapter_summary.json`: manifest tong hop dry-run.
- `profile_write_adapter_report.md`: bao cao doc nhanh.

## Dieu kien duoc export preview

- `APPROVE`
- `EDIT_AND_APPROVE`
- `ACCEPT_WITH_LIMITATION`

## Dieu kien bi chan

- `REJECT`
- `NEEDS_INVESTIGATION`
- Chua co human decision

## Safety

- `ready_for_write_to_main_pipeline = false`
- Khong ghi database.
- Khong sua normalized/package chinh thuc.
- Khong dung moi `supplier_code + normalized_material_code` lam write key.
