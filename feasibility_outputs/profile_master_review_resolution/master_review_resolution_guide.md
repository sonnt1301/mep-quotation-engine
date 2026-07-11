# Hướng Dẫn Phân Xử Master Review – Phase 2G

Tài liệu này hướng dẫn cách thức mở và xử lý các vấn đề trùng lặp dữ liệu master của resolution package.

---

> [!WARNING]
> **CẢNH BÁO AN TOÀN DRY-RUN**
> * Resolution Package này **CHƯA** thực hiện ghi bất kỳ dữ liệu nào vào cơ sở dữ liệu thật.
> * Trạng thái an toàn: `ready_for_write_plan = FALSE` và `ready_for_write_to_main_pipeline = FALSE`.

---

## 1. Cách Thức Tiến Hành Phân Xử

1. **Bước 1**: Mở file Excel [master_review_resolution_template.xlsx](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_master_review_resolution/master_review_resolution_template.xlsx) hoặc CSV [master_review_resolution_template.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_master_review_resolution/master_review_resolution_template.csv).
2. **Bước 2**: Chuyển sang sheet `Resolution Items`.
3. **Bước 3**: Tìm đến cột `human_resolution_decision` (Cột R trong Excel) và chọn một quyết định từ dropdown:
   - **CONFIRM_INSERT**: Duyệt tạo mới hoàn toàn bản ghi vật tư này trong master index.
   - **CONFIRM_UPDATE**: Chấp thuận cập nhật đè thông tin mới (ví dụ: thay đổi mô tả/đơn vị).
   - **CONFIRM_SKIP**: Bỏ qua dòng này vì dữ liệu master đã đầy đủ.
   - **MARK_DUPLICATE**: Đánh dấu dòng là trùng lặp lỗi cần loại bỏ.
   - **NEEDS_MORE_INFO**: Chưa đủ cơ sở phân xử, cần truy vấn thêm.
   - **REJECT_CANDIDATE**: Từ chối ghi nhận dòng này.
4. **Bước 4**: Ghi chú lý do vào cột `human_resolution_note`.

## 2. Tiêu Chí Để Sang Phase 2H (Write Plan)

- [ ] Không còn dòng nào ở trạng thái quyết định `PENDING`.
- [ ] Không còn dòng nào ở trạng thái quyết định `NEEDS_MORE_INFO`.
- [ ] Đã điền đầy đủ tên người duyệt `resolved_by` và ngày duyệt `resolved_at`.
- [ ] Chạy lại lệnh đóng gói để kiểm chứng trạng thái chuyển sang `MASTER_REVIEW_RESOLUTION_READY`.
