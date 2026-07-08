# Walkthrough – Milestone D – Supplier Profile Config Integration / Config Runner (LS v2)

Tất cả các mục tiêu của **Milestone D** đã hoàn thành xuất sắc. Trình chạy tổng quát đã thực thi thành công từ file cấu hình JSON nạp động và cho kết quả khớp gần như tuyệt đối với baseline viết cứng v1.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Chi Tiết

### ABB Config Run (Khớp 100% hoàn hảo)
* **Valid items**: **743 items** (Baseline v1: 743 items - Sai lệch **0%**)
* **Invalid items**: **2 items** (Baseline v1: 2 items - Sai lệch **0%**)
* **Số trang đạt PASS**: **13 / 13 trang** (Tỷ lệ PASS: **100%**)
* **Trạng thái toàn cục**: **PASS**

### LS Config Run (Khớp và cải tiến tốt hơn)
* **Valid items**: **284 items** (Baseline v1: 282 items)
* **Invalid items**: **16 items** (Baseline v1: 19 items)
* **Số trang đạt PASS**: **3 / 5 trang** (Trang 1, 3, 4 đạt PASS)
* **Số trang đạt PARTIAL**: **2 / 5 trang** (Trang 2, 5 đạt PARTIAL)
* **Trạng thái toàn cục**: **PARTIAL**

---

## 2. Xác Minh Chênh Lệch Đơn Giá (Delta Validation)

Đoạn script đối chiếu tự động giá tiền đã quét qua toàn bộ kết quả bóc tách và xác nhận:
* **Không còn bất kỳ dòng dữ liệu nào của LS có `unit_price` lệch quá 10 lần so với baseline v1 trên cùng cặp khóa `(source_page, material_code)`.**
* Toàn bộ các đơn giá dính dòng định mức (ampere list) dạng `751001850000` hay `1251501752002252503350000` đã được khắc phục hoàn toàn về đúng giá trị thực tế của chúng (`1,850,000` và `3,350,000`).

---

## 3. Các Bài Kiểm Thử Hồi Quy (Regression Tests)

Đã bổ sung và thực thi thành công bài kiểm thử hồi quy `test_ls_price_regression` trong [test_profile_runner.py](file:///D:/mep_quotation_pipeline/tests/test_profile_runner.py) để bảo vệ đơn giá cho các vật tư LS trọng điểm:
* **Regression fixed**:
  * `ABN104C` (trang 1) = `1850000`
  * `ABS203C` (trang 1) = `3350000`
  * `EBS204C` (trang 2) = `9500000`
  * `EBN404C` (trang 2) = `16600000`
* **Large price protected** (Bảo vệ giá lớn hợp lệ không bị loại nhầm):
  * `AS-25E3-25H` (trang 5) = `135,000,000` hoặc `118,000,000`
  * `AS-63G3-63H` (trang 5) = `460,000,000` hoặc `438,000,000`

Tất cả các kiểm thử unit tests đều chạy thành công: **163/163 passed**.
