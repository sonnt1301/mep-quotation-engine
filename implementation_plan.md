# Kế Hoạch Triển Khai – Milestone D – Supplier Profile Config Integration (Sửa đổi & Tối ưu hóa LS v2)

Kế hoạch này tập trung khắc phục hoàn toàn lỗi ghép dính danh sách định mức ampere vào đơn giá (`unit_price`) của hãng LS, tinh chỉnh bộ lọc đơn giá thông minh, thiết lập các bài kiểm thử hồi quy và đối chiếu delta chặt chẽ.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Các Thay Đổi Kỹ Thuật Chi Tiết

### Bộ lọc Price Token hợp lệ tối thiểu
Hàm lọc price token hợp lệ tối thiểu sẽ được xây dựng để kiểm tra một token `t`:
- Không chứa chữ `A` hoặc `a` (loại trừ các thông số dòng định mức dạng `2500A`, `4000A`).
- Không phải danh sách định mức: nhận diện qua việc chứa nhiều dấu phẩy (như `15,20,30,40...`) hoặc là chuỗi số phân tách bằng dấu phẩy nhưng các số đều nhỏ hơn `1000` và phần tử cuối không phải là `"000"`.
- Không phải thông số kỹ thuật đơn lẻ hay số nhỏ như `85`, `100` (loại bỏ qua việc kiểm tra giá trị thực tế sau khi parse hoặc định dạng).
- Phải thỏa mãn định dạng:
  - Dạng số có phân tách hàng nghìn bằng dấu phẩy (ví dụ: `1,850,000`).
  - Hoặc số nguyên `>= 1000` (đã loại bỏ ký tự nhiễu).

### Trích xuất Đơn Giá cuối cùng hợp lệ
Trong `profile_runner.py` của LS:
- Đối với `cols["gia"]`, ta không ghép dính mù quáng toàn bộ và cũng không chỉ lấy phần tử cuối cùng `cols["gia"][-1]`.
- Thay vào đó, ta duyệt qua tất cả các token đã thu thập được trong `cols["gia"]`, lọc ra danh sách các price token hợp lệ (thỏa mãn Bộ lọc Price Token ở trên), sau đó lấy **price token cuối cùng hợp lệ** trong danh sách đó làm đơn giá chính thức.

---

## 2. Kiểm Thử Hồi Quy (Regression Tests)

Thêm các ca kiểm thử hồi quy bắt buộc trong `tests/test_profile_runner.py` để xác minh đơn giá cho các vật tư LS trọng điểm:
- `ABN104C`: `unit_price` phải bằng `1850000` (Không được ghép dính `751001850000`).
- `ABS203C`: `unit_price` phải bằng `3350000` (Không được ghép dính `1251501752002252503350000`).
- `EBS204C`: `unit_price` phải bằng `9500000` (Không được ghép dính `1251501752002252509500000`).
- `EBN404C`: `unit_price` phải bằng `16600000`.
- Bảo vệ các mã hàng giá trị lớn, không được loại nhầm hoặc parse sai giá:
  - `AS-25E3-25H` (hoặc model ACB tương đương ở trang 3): đơn giá đúng trong khoảng trăm triệu (ví dụ `135,000,000` hoặc tương đương theo báo giá).
  - `AS-63G3-63H` (hoặc model ACB tương đương ở trang 3): đơn giá đúng trong khoảng trăm triệu (ví dụ `460,000,000` hoặc tương đương theo báo giá).

---

## 3. Xác Minh Delta và Ngưỡng Chấp Nhận

1. Thực hiện chạy bóc tách hai hãng:
   ```powershell
   python tools/feasibility/run_profile_from_config.py --profile ABB --version v1
   python tools/feasibility/run_profile_from_config.py --profile LS --version v1
   ```
2. So sánh đối chiếu delta của LS dựa trên cặp khóa `(source_page, material_code)`:
   - **Tuyệt đối không được còn dòng nào có `unit_price` lệch quá 10 lần so với baseline v1.**
   - Nếu còn dù chỉ một dòng lệch giá quá 10 lần, Milestone D sẽ được coi là **FAIL**.
3. Đảm bảo toàn bộ suite kiểm thử `pytest` đạt kết quả **Passed** thành công.
