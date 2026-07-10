# Quy Trình & Checklist Human Review – Phase 2A.1

Tài liệu này hướng dẫn người đánh giá (Human Reviewer) thực hiện kiểm định chất lượng dữ liệu bóc tách được chuyển đổi qua mô hình cầu nối Integration Bridge trước khi xây dựng Write Adapter.

---

> [!WARNING]
> **PHẠM VI REVIEW**
> * Dữ liệu bóc tách phục vụ phase khảo sát khả thi (Feasibility Reset), chưa tích hợp vào pipeline chính.
> * **Không sửa Streamlit UI, không ghi đè cơ sở dữ liệu thực.**

---

## 1. Hướng Dẫn Đọc Các Tệp Đánh Giá

* **Tệp mẫu review**: [profile_bridge_review_sample.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_review_sample.csv) chứa 72 dòng mẫu đại diện cho các trường hợp đặc thù, giá lớn, rủi ro trùng lặp hoặc known limitations của ABB, LS, CHINT.
* **Tệp đánh giá mã trùng**: [profile_bridge_duplicate_code_review.csv](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_bridge_human_review/profile_bridge_duplicate_code_review.csv) liệt kê toàn bộ các nhóm trùng mã hàng trên cùng nhà cung cấp và phân loại rủi ro (HIGH / MEDIUM / LOW).

---

## 2. Tiêu Chí Đánh Dấu Quyết Định (human_decision)

Người review điền vào cột `human_decision` một trong các giá trị sau:
1. **`APPROVE`**: Dòng bóc tách chính xác hoàn toàn về mã hàng, đơn giá, đơn vị tính.
2. **`REJECT`**: Dòng bóc tách sai lệch nghiêm trọng không thể sử dụng.
3. **`NEEDS_INVESTIGATION`**: Dòng nghi ngờ sai lệch, cần lập trình viên kiểm tra lại cấu hình tọa độ cột.
4. **`ACCEPT_WITH_LIMITATION`**: Dòng bóc tách chấp nhận được dù chưa tối ưu (ví dụ: dòng phụ kiện bị dính từ mô tả ngắn ở đầu).

---

## 3. Checklist Các Điểm Cần Kiểm Tra

- [ ] **Mã vật tư chuẩn hóa (`normalized_material_code`)**: Có bị cắt dính chữ hay thiếu ký tự quan trọng không? (Đặc biệt xem nhóm `LS_PAGE_LIMITATION`).
- [ ] **Đơn giá (`unit_price`)**: Đơn giá có đúng thực tế không? Có bị dính dòng định mức ampere list hay ghép sai cột không? (Đặc biệt xem nhóm `LS_REGRESSION_PROTECTION`).
- [ ] **Mã trùng nhiều giá (`DUPLICATE_CODE_DIFFERENT_PRICE`)**: Nhóm rủi ro HIGH này có thực sự là các phụ kiện khác dòng hay là lỗi phân trang? Khóa ghi dữ liệu đề xuất (`recommended_write_key`) đã đủ phân biệt để tránh ghi đè đè giá của nhau chưa?
- [ ] **Thông tin truy vết (`provenance`)**: Nguồn gốc PDF, số trang, layout có rõ ràng và chính xác không?

---

## 4. Điều Kiện Chốt Để Triển Khai Tiếp

* **ĐẠT (PASS)**: Nếu tệp sample review đạt tỷ lệ duyệt (`APPROVE` hoặc `ACCEPT_WITH_LIMITATION`) `>= 95%` và không có lỗi blocker rủi ro HIGH nào trong tệp duplicate review chưa được xử lý $ightarrow$ Cho phép chuyển sang thiết kế **Phase 2B Write Adapter**.
* **KHÔNG ĐẠT (FAIL)**: Quay lại tinh chỉnh cấu hình layout profile hoặc lọc dữ liệu rác của Integration Bridge.