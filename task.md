# Danh sách công việc ABB + LS Profile Hardening v1 & Milestone C & Milestone D (v2)

## Hardening v1 (Đã hoàn thành)
- `[x]` Khảo sát tọa độ chữ và chẩn đoán lỗi dính dải cột X của trang 41/42 ABB
- `[x]` Khảo sát dải cột X ACB Emax2 MP/FP trang 33 ABB và lỗi dính chữ
- `[x]` Khảo sát lỗi dải cột X_min lề phải trang 3/5 LS khiến bóc lệch mã hàng thành "1PN", "3PN", "NH5"
- `[x]` Thiết lập layout mới `"four_columns_ot_page41"` cho các trang OT Switch-disconnector ABB
- `[x]` Cập nhật logic tách tiền tố MP/FP cho ACB Emax2 của ABB
- `[x]` Nới rộng dải cột `"ma"` lề phải của LS từ `316.0` thành `291.0` trong `layouts.py`
- `[x]` Nới lỏng kiểm tra `is_ampere_list` trong validator LS để cho phép danh sách dòng định mức dính phẩy trong mô tả
- `[x]` Bổ sung cơ chế lọc sớm vật tư rác không có đơn giá (>0) trong cả hai parser ABB và LS
- `[x]` Viết kịch bản chạy mới `run_abb_profile_v1.py` và `run_ls_profile_v1.py` để xuất kết quả vào thư mục `v1`
- `[x]` Thực thi chạy thử nghiệm bóc tách và phân lọc v1 cho cả hai hãng
- `[x]` Xác minh kết quả valid/invalid và độ bao phủ PASS của các trang
- `[x]` Chạy pytest suite đảm bảo tính toàn vẹn hệ thống (155/155 passed)
- `[x]` Tạo tệp so sánh delta `profile_delta_report.md` cho cả ABB và LS
- `[x]` Đồng bộ hóa các tài liệu rà soát (`implementation_plan.md`, `task.md`, `walkthrough.md`)

## Milestone C – Supplier Profile Config Format (Đã hoàn thành)
- `[x]` Khai báo tệp JSON Schema `profile_config_schema.json` chuẩn hóa cấu trúc
- `[x]` Tách toàn bộ thông số tọa độ cột X, validation rule và page mapping của ABB sang `abb_profile_v1.json`
- `[x]` Tách toàn bộ thông số tọa độ cột X, validation rule và page mapping của LS sang `ls_profile_v1.json`
- `[x]` Tạo mô-đun nạp cấu hình `profile_config_loader.py` tích hợp bộ kiểm chứng (validator) đệ quy
- `[x]` Viết tệp hướng dẫn `README.md` chi tiết cấu hình và cảnh báo feasibility
- `[x]` Xây dựng tệp unit tests `test_profile_config_loader.py` và kiểm chứng các ca thành công/thất bại
- `[x]` Chạy kiểm thử pytest toàn dự án đạt 158/158 tests passed thành công

## Milestone D – Supplier Profile Config Integration / Config Runner v2 (Đã hoàn thành)
- `[x]` Tạo module bóc tách tổng quát `profile_runner.py` nạp hoàn toàn từ cấu hình JSON
- `[x]` Cập nhật hàm check prefix và format hỗ trợ luật fallback (chữ + số) trong `profile_runner.py`
- `[x]` Sửa đổi logic trích xuất đơn giá LS: chỉ lọc ra các price token hợp lệ tối thiểu và lấy token giá cuối cùng, không ghép dính ampere list (MT-225, ABN104C, ABS203C, EBS204C)
- `[x]` Gộp logic tách từ chứa khoảng trắng `" "` của LS và tách giá tiền dính chữ của ABB vào hàm `split_merged_words_by_coordinates`
- `[x]` Tạo kịch bản chạy chính `run_profile_from_config.py` hỗ trợ các tham số `--profile`, `--version` và `--config`
- `[x]` Thực thi chạy bóc tách config-run cho hãng ABB và xuất kết quả ra thư mục `abb_profile_config_run/`
- `[x]` Thực thi chạy bóc tách config-run cho hãng LS và xuất kết quả ra thư mục `ls_profile_config_run/`
- `[x]` So sánh delta tự động kết quả bóc tách config-run với baseline v1 cho cả 2 hãng
- `[x]` Xác minh giá trị đơn giá LS không lệch quá 10 lần so với baseline v1 trên cùng cặp (source_page, material_code)
- `[x]` Xây dựng unit tests `test_profile_runner.py` bổ sung các regression tests cho đơn giá LS (ABN104C, ABS203C, EBS204C, EBN404C) và bảo vệ các giá lớn hợp lệ (AS-25E3-25H, AS-63G3-63H)
- `[x]` Chạy bộ kiểm thử pytest toàn dự án đạt 163/163 tests passed thành công

---
> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).
