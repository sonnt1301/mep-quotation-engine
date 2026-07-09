# Kế Hoạch Triển Khai – Milestone H – Profile Run Manifest / Integration-Ready Packaging

Kế hoạch này onboard nhà cung cấp thứ 3 (**CHINT**) theo mô hình **Khảo sát trước - Quyết định sau (Survey-First Workflow)**, thực hiện tinh chỉnh chất lượng ở Milestone G, và đóng gói kết quả nghiệm thu (Packaging) ở Milestone H.

---

> [warning]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * **Không hardcode dữ liệu đầu ra chỉ để pass test.**
> * **Không sửa đổi ABB/LS parser nếu không phát hiện bug thật.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Quy Trình Khảo Sát & criteria Nghiệm Thu Chính Thức

### A. Nhà cung cấp mục tiêu
* **Tên nhà cung cấp**: CHINT
* **File đầu vào thực tế**: [Bảng giá Chint 1-3-2023 ck 50.pdf](file:///F:/00.HVC/Bang gia/Bang gia VT Tu dien/Chint/Bảng giá Chint 1-3-2023 ck 50.pdf)

### B. Tiêu chí Acceptance chính thức sau thực tế (Hướng B)
* **valid_items** >= 20
* **invalid_items** <= 15
* **Tổng số trang benchmark chạy** = 3 trang (Trang 3, 4, 5)
* **pass_pages** >= 1 (Trang 4 đạt PASS)
* **partial_pages** <= 2 (Trang 3 và 5 đạt PARTIAL)
* **Known Limitations bắt buộc**: Phải ghi rõ Page 3 và Page 5 còn PARTIAL và cần tinh chỉnh profile trong tương lai.
* **Trạng thái nghiệm thu mong đợi**: `ACCEPTED_WITH_KNOWN_LIMITATIONS` mức thấp.

---

## 2. Kế Hoạch Đóng Gói Nghiệm Thu – Milestone H

### A. Mục tiêu
* Đóng gói toàn bộ kết quả bóc tách và nghiệm thu Feasibility thành cấu trúc máy đọc (JSON) và người đọc (Markdown) chuẩn hóa.
* Thiết lập cầu nối (Integration Readiness) ghi nhận trạng thái và định hình các bước triển khai của phase Integration Bridge sau này.

### B. Thành phần manifest
* **JSON Schema Contract**: [profile_run_manifest_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_run_manifest_contract.json)
* **Script xuất Manifest**: [export_profile_run_manifest.py](file:///D:/mep_quotation_pipeline/tools/feasibility/export_profile_run_manifest.py)
* **Tệp đầu ra đóng gói**:
  - [profile_run_manifest.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_run_manifest/profile_run_manifest.json)
  - [profile_run_manifest.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_run_manifest/profile_run_manifest.md)

---

## 3. Kịch Bản Thực Hiện & Xác Minh

1. Thực thi chạy bóc tách và nghiệm thu cho cả 3 hãng.
2. Thực thi script đóng gói manifest:
   ```powershell
   python tools/feasibility/export_profile_run_manifest.py
   ```
3. Chạy unit tests kiểm thử bảo vệ manifest:
   ```powershell
   python -m pytest -q
   ```
