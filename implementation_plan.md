# Kế Hoạch Triển Khai – Milestone E – Supplier Profile Output Contract / Benchmark Acceptance Harness

Kế hoạch này thiết lập khung chuẩn hóa đầu ra dữ liệu (Output Contract) và xây dựng bộ kiểm định nghiệm thu tự động (Benchmark Acceptance Harness) cho các parser profile.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Thiết Kế Các Thành Phần Kỹ Thuật

### A. Supplier Profile Output Contract
Tạo tệp mô tả contract đầu ra chuẩn cho các extracted items:
* [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json)
Quy định kiểu dữ liệu và định dạng bắt buộc cho một extracted item tối thiểu (ví dụ: `supplier_code`, `source_page`, `material_code`, `unit_price` > 0, `currency` = "VND", `validation_status` = "valid" hoặc "invalid"...).

### B. Benchmark Acceptance Harness
Tạo tệp Python:
* [run_benchmark_acceptance.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_benchmark_acceptance.py)
Bộ công cụ này tự động đọc output config-run của ABB/LS và đối chiếu với bộ chỉ tiêu acceptance cứng:

#### ABB Acceptance Criteria (Trạng thái mong muốn: `PASS`)
- `valid_items` = 743, `invalid_items` = 2
- `pass_pages` = 13, `total_pages` = 13
- Không có valid item nào thiếu `material_code`.
- Không có valid item nào `unit_price` <= 0.
- Không có valid item nào thiếu `evidence_text`.
- Khớp baseline v1 theo (`source_page`, `material_code`, `unit_price`).

#### LS Acceptance Criteria (Trạng thái mong muốn: `ACCEPTED_WITH_KNOWN_LIMITATIONS`)
- `valid_items` >= 282, `invalid_items` <= 19
- `pass_pages` >= 3, `total_pages` = 5
- Không có valid item nào thiếu `material_code`.
- Không có valid item nào `unit_price` <= 0.
- Không có valid item nào thiếu `evidence_text`.
- Không còn dòng nào có `unit_price` lệch quá 10 lần baseline v1 trên cùng cặp (`source_page`, `material_code`).
- Kiểm tra các regression price bắt buộc: `ABN104C` = 1850000, `ABS203C` = 3350000, `EBS204C` = 9500000, `EBN404C` = 16600000.
- Bảo vệ các giá lớn hợp lệ ở trang 5: `AS-25E3-25H` (135,000,000 hoặc 118,000,000) và `AS-63G3-63H` (460,000,000 hoặc 438,000,000).

### C. Acceptance Output Files
Tạo thư mục mới:
* `feasibility_outputs/benchmark_acceptance/`
Trong đó có:
* `benchmark_acceptance_summary.json` (Tổng hợp máy đọc được)
* `benchmark_acceptance_report.md` (Báo cáo con người đọc được, ghi rõ scope, known limitations, checks table...)
* `abb_acceptance.json` (Acceptance của ABB với status = `PASS`)
* `ls_acceptance.json` (Acceptance của LS với status = `ACCEPTED_WITH_KNOWN_LIMITATIONS`)

---

## 2. Kịch Bản Thực Hiện & Kiểm Thử

1. Xây dựng tệp JSON Contract [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json).
2. Xây dựng kịch bản chạy benchmark [run_benchmark_acceptance.py](file:///D:/mep_quotation_pipeline/tools/feasibility/run_benchmark_acceptance.py).
3. Thực thi bóc tách và chạy acceptance benchmark:
   ```powershell
   python tools/feasibility/run_profile_from_config.py --profile ABB --version v1
   python tools/feasibility/run_profile_from_config.py --profile LS --version v1
   python tools/feasibility/run_benchmark_acceptance.py
   ```
4. Kiểm tra các báo cáo kết xuất trong `feasibility_outputs/benchmark_acceptance/`.
5. Bổ sung unit tests trong `tests/test_benchmark_acceptance.py`.
6. Chạy toàn bộ pytest suite đảm bảo **163+ passed**.
