# Tài Liệu Nghiệm Thu Walkthrough – ABB & LS Supplier Profile Hardening v1 & Milestone C

Tài liệu này ghi nhận kết quả nâng cấp bóc tách khả thi (Hardening v1) và chuẩn hóa cấu trúc tệp cấu hình nhà cung cấp (Milestone C) độc lập của hai hãng benchmark là ABB và LS.

---

## 1. Kết Quả Chạy Kiểm Chứng Thực Tế (Hardening v1)

Các tệp runner mới:
* `tools/feasibility/abb_profile/run_abb_profile_v1.py`
* `tools/feasibility/ls_profile/run_ls_profile_v1.py`

Các thư mục kết quả v1 mới độc lập:
* [abb_profile_v1 (D:/mep_quotation_pipeline/feasibility_outputs/abb_profile_v1/)](file:///D:/mep_quotation_pipeline/feasibility_outputs/abb_profile_v1/):
  * Vật tư hợp lệ (JSON): [abb_profile_items_valid.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/abb_profile_v1/abb_profile_items_valid.json)
  * Báo cáo nghiệm thu Markdown: [abb_profile_report.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/abb_profile_v1/abb_profile_report.md)
* [ls_profile_v1 (D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v1/)](file:///D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v1/):
  * Vật tư hợp lệ (JSON): [ls_profile_items_valid.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v1/ls_profile_items_valid.json)
  * Báo cáo nghiệm thu Markdown: [ls_profile_report.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/ls_profile_v1/ls_profile_report.md)

---

## 2. Chuẩn Hóa Config Format & Loader (Milestone C)

Các tệp cấu hình mới:
* Thư mục cấu hình JSON: [profile_configs (D:/mep_quotation_pipeline/tools/feasibility/profile_configs/)](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/)
  * Tệp cấu hình hãng ABB: [abb_profile_v1.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/abb_profile_v1.json)
  * Tệp cấu hình hãng LS: [ls_profile_v1.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/ls_profile_v1.json)
  * JSON Schema định nghĩa cấu trúc: [profile_config_schema.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/profile_config_schema.json)
  * Tài liệu hướng dẫn cấu hình: [README.md](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_configs/README.md)
* Module nạp và kiểm định cấu hình: [profile_config_loader.py (D:/mep_quotation_pipeline/tools/feasibility/profile_config_loader.py)](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_config_loader.py)
* Tệp unit tests: [test_profile_config_loader.py (D:/mep_quotation_pipeline/tests/test_profile_config_loader.py)](file:///D:/mep_quotation_pipeline/tests/test_profile_config_loader.py)

---

## 3. Hệ Thống Metric Bóc Tách Minh Bạch
Hệ thống báo cáo v1 đã bổ sung các chỉ số rõ ràng theo từng trang:
1. **Dòng Phát Hiện (Raw)**: Số lượng dòng vật tư tiềm năng bóc được từ PDF.
2. **Bỏ Qua (Skipped)**: Số lượng dòng bị bỏ qua trước khi gửi vào validator do không có mã hoặc đơn giá bằng 0.
3. **Đưa Vào Validator**: Số lượng vật tư thực tế gửi vào kiểm định chất lượng.
4. **Valid Items**: Số lượng vật tư đạt chuẩn.
5. **Invalid Items**: Số lượng vật tư bị validator loại bỏ (chuyển sang sheet Loại Bỏ).

---

## 4. Bộ Kiểm Thử Pytest Suite
Tôi đã thực hiện chạy kiểm thử toàn cục:
```bash
python -m pytest -q
```
* **Kết quả**: 158/158 tests đã vượt qua (PASSED). Không xảy ra lỗi hồi quy đối với hệ thống.
* **Các test cases mới kiểm định thành công**:
  * Nạp thành công tệp cấu hình ABB và LS hợp lệ.
  * Tự động trả về layout tương ứng cho trang 18, 41 của ABB và trang 1 của LS.
  * Nhận dạng đúng các cấu hình bị lỗi (thiếu trường, sai dải tọa độ cột...) và từ chối nạp (ValueError).
