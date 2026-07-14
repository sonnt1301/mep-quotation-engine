# Kế Hoạch Triển Khai – Phase 2J – Final Business Sign-off Package

Kế hoạch này triển khai gói Business Sign-off cuối cùng của MEP Quotation Pipeline để người có thẩm quyền phê duyệt/nghiệp thu từng vật tư có planned action insert/update/skip trên tệp Excel (tích hợp dropdown validation) trước khi chuyển sang Phase tiếp theo.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Final Business Sign-off Package**.
> * **Không ghi dữ liệu vào database và không thực thi lệnh ghi thật.**
> * **Không set ready_for_execution = True hoặc ready_for_write_to_main_pipeline = True.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Thiết Kế Final Business Sign-off Package

### A. Giao diện & Kết xuất
* **Sign-off script**: [export_profile_final_business_signoff.py](file:///D:/mep_quotation_pipeline/tools/feasibility/export_profile_final_business_signoff.py) (Đọc dữ liệu Final Write Plan và sinh template sign-off).
* **Ràng buộc an toàn & Logic**:
  - Không đọc trực tiếp từ raw bridge items hay tệp blocked của adapter.
  - Chỉ lọc các plan items có `final_planned_action != "PLAN_BLOCKED"`.
  - Mặc định quyết định phê duyệt là `PENDING`.
  - Dropdown phân xử hợp lệ: `PENDING`, `APPROVE_FOR_EXECUTOR_DESIGN`, `REJECT`, `NEEDS_CORRECTION`, `NEEDS_SOURCE_REVIEW`.
  - REJECT, NEEDS_* bắt buộc điền Human Note.
  - Lưu mã băm SHA-256 của các tệp nguồn để phát hiện STALE thay đổi.
  - **Sửa nóng bảo vệ Read-Only**: Tuyệt đối không import/call/run bất kỳ script phase upstream nào. Tính toán mã băm SHA-256 của 7 tệp nguồn trước và sau khi chạy; nếu phát hiện thay đổi bất kỳ byte nào sẽ tự động ném ra lỗi `RuntimeError` để ngăn chặn rủi ro ghi đè file.
* **Sản phẩm xuất bản tại `feasibility_outputs/profile_final_business_signoff/`**:
  - `final_business_signoff_items.json`: Các dòng sign-off chi tiết.
  - `final_business_signoff_summary.json`: Tóm tắt metrics.
  - `final_business_signoff_template.csv`: Template phẳng.
  - `final_business_signoff_template.xlsx`: Excel Workbook 5 sheet (`Summary`, `Sign-off Items` có dropdown, `Decision Options`, `Source Evidence`, `Approval Preconditions`) định dạng chuyên nghiệp.
  - `final_business_signoff_guide.md` và `final_business_signoff_report.md`.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện chạy đóng gói business signoff:
   ```powershell
   python tools/feasibility/export_profile_final_business_signoff.py
   ```
2. Chạy unit tests bảo vệ:
   ```powershell
   & .venv\Scripts\pytest tests/test_profile_final_business_signoff.py -q
   ```
