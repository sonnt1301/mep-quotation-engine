# Kế Hoạch Triển Khai – Milestone F – Third Supplier Profile Onboarding / Benchmark Expansion (Hướng B)

Kế hoạch này onboard nhà cung cấp thứ 3 (**CHINT**) theo mô hình **Khảo sát trước - Quyết định sau (Survey-First Workflow)** và chuẩn hóa các tiêu chí nghiệm thu chính thức sau thực tế.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * **Không hardcode dữ liệu đầu ra chỉ để pass test.**
> * **Không sửa đổi ABB/LS parser nếu không phát hiện bug thật.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Quy Trình Khảo Sát & criteria Nghiệm Thu Chính Thức (Hướng B)

### A. Nhà cung cấp mục tiêu
* **Tên nhà cung cấp**: CHINT
* **File đầu vào thực tế**: [Bảng giá Chint 1-3-2023 ck 50.pdf](file:///F:/00.HVC/Bang gia/Bang gia VT Tu dien/Chint/Bảng giá Chint 1-3-2023 ck 50.pdf)

### B. Tiêu chí Acceptance chính thức sau thực tế (Chỉ áp dụng nếu Khảo sát FEASIBLE)
Chúng tôi chọn **Hướng B** với các tiêu chí chính thức nhất quán để đánh giá nghiệm thu đối với CHINT:
* **valid_items** >= 20
* **invalid_items** <= 15
* **Tổng số trang benchmark chạy** = 3 trang (Trang 3, 4, 5)
* **pass_pages** >= 1 (Trang 4 đạt PASS)
* **partial_pages** <= 2 (Trang 3 và 5 đạt PARTIAL)
* **Known Limitations bắt buộc**: Phải ghi rõ Page 3 và Page 5 còn PARTIAL và cần tinh chỉnh profile trong tương lai.
* **Trạng thái nghiệm thu mong đợi**: `ACCEPTED_WITH_KNOWN_LIMITATIONS` mức thấp, chưa đạt profile chất lượng cao.
* **Đánh giá mở rộng**: Kết quả chỉ mang ý nghĩa **"có tín hiệu khả thi ban đầu cho supplier thứ 3"**, tránh khẳng định quá mạnh về tính tổng quát.

---

## 2. Kịch Bản Thực Hiện & Xác Minh

1. Thực hiện khảo sát layout và sinh survey report.
2. Tạo file cấu hình JSON [chint_profile_v1.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/chint_profile_v1.json).
3. Thực thi chạy bóc tách và benchmark nghiệm thu:
   ```powershell
   python tools/feasibility/run_profile_from_config.py --profile ABB --version v1
   python tools/feasibility/run_profile_from_config.py --profile LS --version v1
   python tools/feasibility/run_profile_from_config.py --profile CHINT --version v1
   python tools/feasibility/run_benchmark_acceptance.py
   ```
4. Kiểm tra báo cáo acceptance sinh ra trong `feasibility_outputs/benchmark_acceptance/`.
5. Chạy unit tests:
   ```powershell
   python -m pytest -q
   ```
