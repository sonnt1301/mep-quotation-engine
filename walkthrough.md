# Walkthrough – Phase 2J – Final Business Sign-off Package (Sửa nóng)

Tất cả các mục tiêu phát triển Final Business Sign-off Package tích hợp dropdown validation trên Excel, kiểm chứng an toàn QA workbook, và đặc biệt là **bảo vệ tính Read-Only tuyệt đối cho các tệp upstream** đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Final Business Sign-off Package**.
> * **Không ghi dữ liệu vào database và không thực hiện ghi thật.**
> * **Không set ready_for_execution = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Sửa Nóng Bảo Vệ Read-Only

1. **Tuyệt đối không thực thi các phase upstream**:
   - Loại bỏ hoàn toàn mọi dòng import, gọi hàm hoặc chạy subprocess của các script phase trước.
   - Chỉ đọc JSON upstream bằng `read_text`/`json.load`.

2. **Cơ chế so khớp mã băm SHA-256 động**:
   - Tự động tính toán mã băm SHA-256 của 7 tệp nguồn trước khi chạy:
     * `profile_commit_gate_manifest.json`
     * `simulated_write_summary.json`
     * `simulated_material_records.json`
     * `master_match_summary.json`
     * `final_write_plan_summary.json`
     * `final_write_plan_items.json`
     * `approval_chain_status.json`
   - Tính toán lại mã băm sau khi thực thi và so sánh.
   - Ném lỗi `RuntimeError` ngay lập tức nếu phát hiện bất kỳ sự thay đổi nào đối với các file nguồn upstream, ngăn chặn việc vô tình ghi đè.

3. **Báo cáo và Excel tại `feasibility_outputs/profile_final_business_signoff/`**:
   - Ghi nhận đầy đủ thông tin an toàn: ready flags luôn là `FALSE`.

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 232 unit tests đã vượt qua thành công: **232/232 passed** (tỷ lệ 100%).
* Tạo tệp unit test bảo vệ regression: [test_profile_final_business_signoff.py](file:///D:/mep_quotation_pipeline/tests/test_profile_final_business_signoff.py)
  - Xác minh `test_signoff_read_only_regression` chặn đứng mọi subprocess, os.system call.
  - Đảm bảo mã băm SHA-256 của 7 tệp nguồn trước và sau khi chạy không hề thay đổi dù chỉ 1 byte.
  - Xác minh tạo chính xác 3 PENDING sign-off items khi nguồn sạch.

---

> [!IMPORTANT]
> **BƯỚC TIẾP THEO SAU PHASE 2J**
> * Bước tiếp theo chỉ được bắt đầu khi đã có **target contract thật** của main pipeline/database.
