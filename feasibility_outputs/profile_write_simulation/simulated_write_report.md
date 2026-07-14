# Controlled Write Simulation Report – Phase 2E

Báo cáo kết quả chạy sandbox write simulation đối với các write candidates đã được duyệt qua Commit Gate.

---

> [!WARNING]
> **CẢNH BÁO AN TOÀN GIẢ LẬP**
> * Toàn bộ các hành động trong báo cáo này đều là **GIẢ LẬP (WOULD_INSERT/WOULD_SKIP)**.
> * Hệ thống **CHƯA** thực hiện ghi bất kỳ dữ liệu nào vào database hoặc main production pipeline của dự án.
> * Trạng thái an toàn: `ready_for_real_write = FALSE` và `ready_for_write_to_main_pipeline = FALSE`.

---

## 1. Trạng Thái Sandbox Simulation (Simulation Status)

* Trạng thái mô phỏng: `SIMULATION_READY_FOR_REVIEW`
* Lý do chưa thể ghi thật:
  - Chưa chuyển đổi biến môi trường và chưa kích hoạt lệnh ghi thật của Phase 2F.

## 2. Thống Kê Sandbox Commit

* Tổng số candidates: `3`
* Số lượng giả lập ghi mới (would_insert_count): `3`
* Số lượng giả lập cập nhật (would_update_count): `0`
* Số lượng giả lập bỏ qua (would_skip_count): `0`
* Số lượng giả lập bị chặn (blocked_count): `0`

---

## 3. Danh Sách Tệp Tin Kết Xuất Cục Bộ
* Simulated Material Records: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_simulation\simulated_material_records.json`
* Simulated Commit Log: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_simulation\simulated_commit_log.json`
* Simulated Rollback Plan: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_simulation\simulated_rollback_plan.json`
* Excel Review Workbook: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_simulation\simulated_write_review.xlsx`
