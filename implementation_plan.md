# Kế Hoạch Triển Khai – Phase 2E – Write Simulation / Sandbox Commit

Kế hoạch này triển khai sandbox write simulation để giả lập ghi dữ liệu từ candidates và kết xuất các báo cáo an toàn preview, commit log, rollback plan trước khi có bất kỳ tác vụ ghi thật nào vào database/pipeline chính thức.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Sandbox Write Simulation**.
> * **Không ghi dữ liệu vào database và không thay đổi production pipeline.**
> * **Không set ready_for_write_to_main_pipeline = True hoặc ready_for_real_write = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Sandbox Write Simulation

### A. Giao diện & Kết xuất
* **Simulation script**: [run_profile_write_simulation.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_profile_write_simulation.py) (Đóng vai trò là sandbox mô phỏng ghi nhận và sinh các tệp tin log, rollback, preview).
* **Ràng buộc an toàn & Logic**:
  - Không đọc trực tiếp từ raw bridge items hay tệp blocked của adapter. Chỉ nhận đầu vào từ candidates đã lọc và manifest của gate.
  - Simulation chỉ được thông qua và ghi nhận thành công (`simulation_status = SIMULATION_READY_FOR_REVIEW`) khi Commit Gate đã chuyển trạng thái duyệt (`APPROVED_FOR_NEXT_PHASE_DESIGN_ONLY`).
  - Nếu gate chưa duyệt, simulation tự động trả về `BLOCKED_BY_COMMIT_GATE` mà không crash hệ thống.
  - Ghi nhận warning `"not_checked_against_master_database"` khi chưa có master database để đối chiếu.
* **Sản phẩm xuất bản tại `feasibility_outputs/profile_write_simulation/`**:
  - `simulated_material_records.json`: danh sách các bản ghi dự kiến.
  - `simulated_commit_log.json`: nhật ký sandbox ghi nhận các hashes nguồn và các bước.
  - `simulated_rollback_plan.json`: phương án rollback sandbox.
  - `simulated_write_summary.json`: tóm tắt metadata.
  - `simulated_write_review.xlsx`: Excel có 4 sheet (`Summary`, `Simulated Records`, `Commit Log`, `Rollback Plan`).
  - `simulated_write_report.md`: báo cáo markdown mô phỏng.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy sandbox simulation:
   ```powershell
   python tools/feasibility/run_profile_write_simulation.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_write_simulation.py -q
   ```
