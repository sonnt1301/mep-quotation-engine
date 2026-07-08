# Walkthrough – Milestone E – Supplier Profile Output Contract / Benchmark Acceptance Harness

Tất cả các mục tiêu của **Milestone E** đã hoàn thành xuất sắc. Bộ kiểm định tự động (Acceptance Harness) đã kiểm chứng dữ liệu bóc tách của cả ABB và LS dựa trên các tiêu chí nghiêm ngặt, cho thấy mức độ sẵn sàng và độ tin cậy của giải pháp feasibility hiện tại.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Tổng Hợp

### ABB Profile (Khớp tuyệt đối)
* **Valid items**: **743 items** (Tiêu chí: exact 743 - **PASS**)
* **Invalid items**: **2 items** (Tiêu chí: exact 2 - **PASS**)
* **Số trang đạt PASS**: **13 / 13 trang** (Tiêu chí: 13/13 - **PASS**)
* **Trạng thái nghiệm thu**: **PASS**

### LS Profile (Khớp tốt, cải tiến hơn v1)
* **Valid items**: **284 items** (Tiêu chí: >= 282 - **PASS**)
* **Invalid items**: **16 items** (Tiêu chí: <= 19 - **PASS**)
* **Số trang đạt PASS**: **3 / 5 trang** (Tiêu chí: >= 3/5 - **PASS**)
* **Số trang đạt PARTIAL**: **2 / 5 trang** (Trang 2 và Trang 5)
* **Trạng thái nghiệm thu**: **ACCEPTED_WITH_KNOWN_LIMITATIONS**

---

## 2. Các Bài Kiểm Thử Hồi Quy & Bảo Vệ Giá Lớn (LS)

* **Regression fixed** (Đã kiểm chứng thành công):
  * `ABN104C` (trang 1) = `1850000` (đúng giá gốc baseline, không dính ampere)
  * `ABS203C` (trang 1) = `3350000`
  * `EBS204C` (trang 2) = `9500000`
  * `EBN404C` (trang 2) = `16600000`
* **Large price protected** (Bảo vệ giá lớn hợp lệ):
  * `AS-25E3-25H` (trang 5) = `135,000,000` hoặc `118,000,000`
  * `AS-63G3-63H` (trang 5) = `460,000,000` hoặc `438,000,000`
* **Delta check**: Không còn bất kỳ dòng LS nào lệch `unit_price` > 10x so với baseline v1.

---

## 3. Đầu Ra Của Milestone E

Toàn bộ các tệp kết quả và contract được sinh đầy đủ tại các đường dẫn:
1. **JSON Output Contract**: [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json)
2. **Thư mục Nghiệm thu**: `feasibility_outputs/benchmark_acceptance/`
   - [benchmark_acceptance_summary.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/benchmark_acceptance/benchmark_acceptance_summary.json) (Tổng hợp máy đọc được)
   - [benchmark_acceptance_report.md](file:///D:/mep_quotation_pipeline/feasibility_outputs/benchmark_acceptance/benchmark_acceptance_report.md) (Báo cáo con người đọc được)
   - [abb_acceptance.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/benchmark_acceptance/abb_acceptance.json) (Acceptance ABB với status = `PASS`)
   - [ls_acceptance.json](file:///D:/mep_quotation_pipeline/feasibility_outputs/benchmark_acceptance/ls_acceptance.json) (Acceptance LS với status = `ACCEPTED_WITH_KNOWN_LIMITATIONS`)
3. **Bộ Kiểm thử Acceptance**: [test_benchmark_acceptance.py](file:///D:/mep_quotation_pipeline/tests/test_benchmark_acceptance.py)
   - Tất cả unit tests đều chạy thành công: **168/168 passed** (đạt tỷ lệ 100%).
