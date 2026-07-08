# Kế Hoạch Triển Khai Feasibility Reset & Chuẩn Hóa Cấu Hình (Milestone C)

Kế hoạch này định hình lại phương pháp bóc tách dữ liệu báo giá MEP dựa trên hướng đi mới **Coordinate Column Profiler** (Supplier Profile Parser), thay thế hoàn toàn pipeline cũ.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không mở lại giao diện Streamlit UI cũ.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## Các Cột Mốc Triển Khai (Milestones)

### 1. Milestone A: ABB Profile Hardening (Đã hoàn thành)
* Tinh chỉnh dải cột, Regex, loại bỏ tiền tố MP/FP dính ACB để tối ưu hóa hiệu năng bóc tách ABB.
* Kết quả: 13/13 trang thử nghiệm đạt PASS feasibility.

### 2. Milestone B: LS Profile Hardening (Đã hoàn thành)
* Nới rộng dải cột mã hàng lề phải, nới lỏng validator đối với danh sách dòng định mức dính phẩy (như EBS104c).
* Kết quả: 3/5 trang thử nghiệm đạt PASS feasibility, 2 trang đạt PARTIAL.

### 3. Milestone C: Supplier Profile Config Format (Đã hoàn thành)
* Tách biệt dải tọa độ cột X, Regex tiền tố mã hàng và các validation rules của hãng ra các tệp JSON cấu hình độc lập (`profile_configs/`).
* Xây dựng mô-đun nạp cấu hình `profile_config_loader.py` và viết unit tests kiểm chứng.

### 4. Milestone D: Supplier Profile Config Integration (Kế hoạch tiếp theo)
* Refactor lại parser của ABB và LS để nạp trực tiếp tọa độ dải cột và rules từ tệp JSON cấu hình thông qua loader thay vì viết cứng trong code Python.
