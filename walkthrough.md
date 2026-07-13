# Walkthrough – Phase 2H – Final Write Plan Draft

Tất cả các mục tiêu phát triển Final Write Plan Draft tổng hợp đa nguồn và kết xuất Excel 5 sheet có QA workbook tự động đã hoàn thành xuất sắc và vượt qua 100% các bài kiểm thử tự động.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Final Write Plan Draft**.
> * **Không ghi dữ liệu vào database và không thay đổi dữ liệu thật.**
> * **Không set ready_for_execution = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Kết Quả Kế Hoạch Final Write Plan

1. **Safety Lọc & Trích xuất**:
   - Tổng hợp kế hoạch hoàn toàn từ candidates, simulation records, match results và review resolutions. Tuyệt đối không đọc trực tiếp từ raw bridge hay adapter blocked items.
   - Trạng thái an toàn: `ready_for_execution = FALSE` và `ready_for_write_to_main_pipeline = FALSE`.

2. **Quy Tắc Match & Action Mapping**:
   - `PLAN_INSERT`: Khi master match đề xuất WOULD_INSERT, hoặc resolution CONFIRM_INSERT.
   - `PLAN_UPDATE`: Khi master match đề xuất WOULD_UPDATE, hoặc resolution CONFIRM_UPDATE.
   - `PLAN_SKIP`: Khi master match đề xuất WOULD_SKIP, hoặc resolution CONFIRM_SKIP/REJECT_CANDIDATE.
   - `PLAN_BLOCKED`: Khi có unresolved resolution (`PENDING`, `NEEDS_MORE_INFO`), hoặc đề xuất `NEEDS_MASTER_REVIEW` / `BLOCKED`.

3. **Risk Analysis & Register**:
   - `HIGH`: Khi kế hoạch bị chặn `PLAN_BLOCKED`, có unresolved resolution, hoặc có match warnings.
   - `MEDIUM`: Khi trùng lặp đã được giải quyết qua resolution gate, hoặc được duyệt kèm limit ở visual review.
   - `LOW`: Khớp sạch hoàn toàn.
   - Toàn bộ lỗi được đưa vào `final_write_plan_risk_register.json` để quản trị rủi ro.

4. **Tự Động QA Workbook bằng openpyxl**:
   - Xây dựng bài kiểm tra tự động QA Workbook trực tiếp trong pytest: kiểm tra workbook mở được, đủ 5 sheet (`Summary`, `Final Write Plan`, `Blocked Items`, `Risk Register`, `Source Trace`), dòng header hợp lệ, freeze panes dòng 1, và tự động bật autofilter.

5. **Báo cáo và Excel tại `feasibility_outputs/profile_final_write_plan_draft/`**:
   - Sinh đầy đủ các file JSON (items, summary, risk register).
   - CSV `final_write_plan_review.csv`.
   - Excel `final_write_plan_review.xlsx` định dạng màu chuyên nghiệp.
   - `final_write_plan.md` báo cáo tổng kết và điều kiện đi tiếp.

---

## 2. Xác Minh Chất Lượng & Tests

* Tất cả 223 unit tests đã vượt qua thành công: **223/223 passed** (tỷ lệ 100%).
* Tạo tệp unit test bảo vệ: [test_profile_final_write_plan_draft.py](file:///D:/mep_quotation_pipeline/tests/test_profile_final_write_plan_draft.py)
  - Xác minh input candidates rỗng trả về `FINAL_WRITE_PLAN_EMPTY`.
  - Xác minh PENDING resolution đề xuất `PLAN_BLOCKED` và gán HIGH risk.
  - Xác minh `CONFIRM_INSERT`/`CONFIRM_UPDATE` đề xuất đúng planned action.
  - Tự động chạy QA workbook bằng openpyxl xác minh 5 sheet, freeze panes, autofilter và đếm dòng khớp tóm tắt.
