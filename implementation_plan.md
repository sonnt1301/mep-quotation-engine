# Kế Hoạch Triển Khai – Phase 2H – Final Write Plan Draft

Kế hoạch này triển khai lớp lập kế hoạch ghi cuối cùng ở dạng nháp (Final Write Plan Draft) tổng hợp và đồng bộ hóa các metrics rủi ro, kết quả so khớp và phân xử master trước khi tiến hành thực thi thật.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Final Write Plan Draft**.
> * **Không ghi dữ liệu vào database và không thực thi lệnh ghi thật.**
> * **Không set ready_for_execution = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Final Write Plan Draft

### A. Giao diện & Kết xuất
* **Write Plan script**: [export_profile_final_write_plan_draft.py](file:///D:/mep_quotation_pipeline/tools/feasibility/export_profile_final_write_plan_draft.py) (Tổng hợp candidates, simulation, matching, và resolution).
* **Ràng buộc an toàn & Logic**:
  - Không đọc trực tiếp từ raw bridge items hay tệp blocked của adapter.
  - Phân loại hành động cuối cùng: `PLAN_INSERT`, `PLAN_UPDATE`, `PLAN_SKIP`, và `PLAN_BLOCKED` dựa trên matching rules và resolution decisions.
  - Phân tích mức độ rủi ro (`LOW`, `MEDIUM`, `HIGH`) chi tiết cho từng bản ghi.
  - Ghi nhận đầy đủ các cảnh báo lỗi vào `final_write_plan_risk_register.json`.
* **Sản phẩm xuất bản tại `feasibility_outputs/profile_final_write_plan_draft/`**:
  - `final_write_plan_items.json`: Danh sách các kế hoạch ghi chi tiết.
  - `final_write_plan_summary.json`: Tóm tắt các metrics counts và proposed status.
  - `final_write_plan_risk_register.json`: Báo cáo rủi ro.
  - `final_write_plan_review.csv` và `final_write_plan_review.xlsx`: Excel có 5 sheet (`Summary`, `Final Write Plan`, `Blocked Items`, `Risk Register`, `Source Trace`) được định dạng chuyên nghiệp.
  - `final_write_plan.md`: Báo cáo markdown kế hoạch.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy đóng gói write plan draft:
   ```powershell
   python tools/feasibility/export_profile_final_write_plan_draft.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_final_write_plan_draft.py -q
   ```
