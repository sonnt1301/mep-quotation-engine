# Walkthrough – Milestone F – Third Supplier Profile Onboarding / Benchmark Expansion

Tất cả các mục tiêu của **Milestone F** đã hoàn thành xuất sắc. Framework bóc tách cấu hình động và nghiệm thu tự động (acceptance harness) đã có **tín hiệu khả thi ban đầu cho supplier thứ 3** (**CHINT**) một cách quy chuẩn.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * **Không hardcode dữ liệu đầu ra chỉ để pass test.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Tổng Hợp

### ABB Profile (PASS)
* **Valid items**: **743 items** (Baseline v1: 743 - Khớp **100%**)
* **Invalid items**: **2 items** (Baseline v1: 2 - Khớp **100%**)
* **Số trang đạt PASS**: **13 / 13 trang**
* **Trạng thái nghiệm thu**: **PASS**

### LS Profile (ACCEPTED_WITH_KNOWN_LIMITATIONS)
* **Valid items**: **284 items** (Cải tiến hơn v1 gốc là 282)
* **Invalid items**: **16 items** (Giảm lỗi so với v1 gốc là 19)
* **Số trang đạt PASS**: **3 / 5 trang**
* **Số trang đạt PARTIAL**: **2 / 5 trang** (Trang 2 và 5)
* **Trạng thái nghiệm thu**: **ACCEPTED_WITH_KNOWN_LIMITATIONS**

### CHINT Profile (ACCEPTED_WITH_KNOWN_LIMITATIONS - Mức thấp)
* **Valid items**: **45 items** (Tiêu chí chính thức: >= 20 - **PASS**)
* **Invalid items**: **6 items** (Tiêu chí chính thức: <= 15 - **PASS**)
* **Số trang benchmark chạy**: **3 trang** (Trang 3, 4, 5 - **PASS**)
* **Số trang đạt PASS**: **1 / 3 trang** (Trang 4 đạt PASS - Tiêu chí chính thức: >= 1 - **PASS**)
* **Số trang đạt PARTIAL**: **2 / 3 trang** (Trang 3 và Trang 5 - Tiêu chí chính thức: <= 2 - **PASS**)
* **Trạng thái nghiệm thu**: **ACCEPTED_WITH_KNOWN_LIMITATIONS**

---

## 2. Quy Trình Khảo Sát & Onboard

1. **Khảo sát file đầu vào thực tế**:
   - Định vị thành công tệp: `F:\00.HVC\Bang gia\Bang gia VT Tu dien\Chint\Bảng giá Chint 1-3-2023 ck 50.pdf`
   - Đã sinh báo cáo khảo sát layout và text layer tại: [profile_survey_report.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/chint_profile_v0/profile_survey_report.md) kết luận **`FEASIBLE`**.
   - Thiết lập trang benchmark: [profile_page_selection.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/chint_profile_v0/profile_page_selection.json) (Trang 3, 4, 5).

2. **Cấu hình layout & Runner**:
   - Thiết lập dải cột X riêng biệt cho Chint trong [chint_profile_v1.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/chint_profile_v1.json).
   - Tích hợp Chint vào runner chung [profile_runner.py](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_runner.py) để bóc tách động mà không làm ảnh hưởng (regression) tới ABB/LS.
   - Chạy config-run bóc được 45 valid items sạch tuân thủ nghiêm ngặt Output Contract.

3. **Mở rộng Acceptance Harness (Hướng B)**:
   - Cập nhật [run_benchmark_acceptance.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_benchmark_acceptance.py) kiểm định Chint dựa trên các tiêu chí chính thức đã khóa của Hướng B:
     - `valid_items` >= 20, `invalid_items` <= 15
     - `total_pages` == 3, `pass_pages` >= 1, `partial_pages` <= 2
     - `known_limitations` bắt buộc ghi nhận: **Page 3 và Page 5 vẫn còn PARTIAL** do có một số dòng tiêu đề hoặc dòng text thông số phụ bị validator loại thành invalid.
   - Trình bày đầy đủ báo cáo Markdown [benchmark_acceptance_report.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/benchmark_acceptance/benchmark_acceptance_report.md).

---

## 3. Xác Minh Chất Lượng & Tests

* Không có regression đối với ABB (status PASS) và LS (status ACCEPTED_WITH_KNOWN_LIMITATIONS).
* Tất cả 169 unit tests đã vượt qua thành công: **169/169 passed** (tỷ lệ 100%).
