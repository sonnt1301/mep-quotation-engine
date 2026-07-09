# Danh sách công việc ABB + LS + CHINT Profile Onboarding & Milestone G

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

## Milestone D – Supplier Profile Config Integration / Config Runner (Đã hoàn thành)
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

## Milestone E – Supplier Profile Output Contract / Benchmark Acceptance Harness (Đã hoàn thành)
- `[x]` Tạo tệp mô tả contract đầu ra chuẩn cho extracted items tại `tools/feasibility/profile_output_contract.json`
- `[x]` Sửa đổi `ExtractedItem` và bộ bóc tách để tích hợp đầy đủ trường `supplier_code` theo contract
- `[x]` Tạo kịch bản chạy acceptance benchmark nghiệm tự động tại `tools/feasibility/run_benchmark_acceptance.py`
- `[x]` Thực thi và kiểm định ABB (PASS) và LS (ACCEPTED_WITH_KNOWN_LIMITATIONS) thành công
- `[x]` Sinh thư mục nghiệm thu `feasibility_outputs/benchmark_acceptance/` chứa các tệp JSON và Markdown report
- `[x]` Thêm unit tests và chạy toàn suite `pytest` vượt qua 168/168 passed thành công

## Milestone F – Third Supplier Profile Onboarding / Benchmark Expansion (Đã hoàn thành)
- `[x]` Khảo sát tệp PDF Chint thật sự tồn tại tại: `F:\00.HVC\Bang gia\Bang gia VT Tu dien\Chint\Bảng giá Chint 1-3-2023 ck 50.pdf`
- `[x]` Viết báo cáo khảo sát layout `feasibility_outputs/chint_profile_v0/profile_survey_report.md` kết luận `FEASIBLE`
- `[x]` Tạo tệp cấu hình lựa chọn trang benchmark `feasibility_outputs/chint_profile_v0/profile_page_selection.json` (Trang 3, 4, 5)
- `[x]` Tạo tệp cấu hình layout riêng biệt `tools/feasibility/profile_configs/chint_profile_v1.json` tuân thủ JSON Schema
- `[x]` Cập nhật runner chung `profile_runner.py` để hỗ trợ bóc tách các layout Chint mà không làm ảnh hưởng (regression) tới ABB/LS
- `[x]` Thực thi chạy bóc tách config-run cho Chint và xuất kết quả ra `feasibility_outputs/chint_profile_config_run/` tuân thủ Output Contract
- `[x]` Cập nhật Acceptance Harness `run_benchmark_acceptance.py` đồng bộ criteria Hướng B cho Chint
- `[x]` Thêm/cập nhật unit tests trong `tests/test_benchmark_acceptance.py`
- `[x]` Chạy toàn bộ pytest suite đảm bảoPassed: **169/169 passed**
- `[x]` Đồng bộ hóa tất cả các tài liệu root tại project root

## Milestone G – Profile Quality Hardening / Raise Partial Pages (Đã hoàn thành)
- `[x]` Phân tích nguyên nhân sâu (Root Cause) của các trang PARTIAL: LS page 2, LS page 5, CHINT page 3, CHINT page 5
- `[x]` Sinh tệp kết quả phân tích kỹ thuật:
  - `feasibility_outputs/profile_hardening_g/partial_page_analysis.md`
  - `feasibility_outputs/profile_hardening_g/partial_page_analysis.json`
- `[x]` Hardening parser trong `profile_runner.py`: bổ sung các từ khóa tiếng Việt đặc trưng của tiêu đề bảng vào bộ lọc rác đầu vào
- `[x]` Nâng thành công CHINT Page 3 từ PARTIAL lên PASS (0 invalid items)
- `[x]` Giữ nguyên Known Limitations cho LS Page 2, LS Page 5 và CHINT Page 5 để bảo vệ tính ổn định của parser
- `[x]` Chạy lại benchmark acceptance và unit tests pytest (169/169 passed)
- `[x]` Đồng bộ các tệp tài liệu báo cáo nghiệm thu tại project root

---
> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * **Không hardcode dữ liệu đầu ra chỉ để pass test.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).
