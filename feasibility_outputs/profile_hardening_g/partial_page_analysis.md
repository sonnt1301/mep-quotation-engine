# Báo Cáo Phân Tích Các Trang PARTIAL – Milestone G

Báo cáo này tập trung rà soát, phân tích sâu nguyên nhân kỹ thuật (Root Cause) khiến các trang của hãng **LS** và **CHINT** bị đánh giá là `PARTIAL` trong quá trình chạy nghiệm thu Acceptance Benchmark.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Phân Tích Chi Tiết Từng Trang PARTIAL

### A. Hãng LS – Trang 2 (Phụ kiện MCCB/ELCB)
* **Số lượng Valid**: 36
* **Số lượng Invalid**: 6
* **Tỷ lệ lỗi (Invalid Ratio)**: 14.3%
* **Ví dụ dòng lỗi**:
  * Dòng evidence: `Cuộn đóng ngắt SHT for ABN100c~ABH250c 930,000` $\rightarrow$ material_code bị trích xuất thành `"CUỘN"`.
  * Dòng evidence: `Under Vol. Trip UVT for ABN403c~803c 1,380,000` $\rightarrow$ material_code bị trích xuất thành `"UNDER"`.
* **Nguyên nhân kỹ thuật (Root Cause)**:
  * Dải cột `"ma"` bên trái được định nghĩa là `[35.0, 120.0]`. Tuy nhiên, do phần tên mô tả tiếng Việt/tiếng Anh của phụ kiện ở đầu dòng khá dài, các mã phụ kiện viết tắt như `SHT`, `UVT`, `AX`, `AL` bị đẩy sang tọa độ X0 từ `120.8` trở đi, khiến chúng bị lọt vào cột `"in_a"` (`[121.0, 215.0]`).
  * Hệ quả là cột `"ma"` chỉ nhận được các từ mô tả chữ đầu dòng, và parser fallback lấy token đầu tiên làm `material_code` (như `"CUỘN"`, `"UNDER"`, `"TIẾP"`, `"AUXILIARY"`), dẫn đến lỗi validation (`material_code_invalid_prefix`).
* **Độ tin cậy của phân tích (Confidence)**: **HIGH**
* **Đề xuất xử lý**:
  * **Giữ nguyên Known Limitation**. Cấu trúc phụ kiện (Accessories) có sự chồng lấn tọa độ phức tạp với các thiết bị chính (MCCB/ELCB) trên cùng layout `split_half_left_right`. Nếu nới rộng cột `"ma"` sang bên phải để nhận diện mã phụ kiện viết tắt, các trang MCCB chính sẽ bị lọt danh sách dòng định mức (ampere list) vào cột `"ma"`, dẫn đến sai lệch nghiêm trọng cho thiết bị chính.

---

### B. Hãng LS – Trang 5 (Phụ kiện ACB)
* **Số lượng Valid**: 50
* **Số lượng Invalid**: 6
* **Tỷ lệ lỗi (Invalid Ratio)**: 10.7%
* **Ví dụ dòng lỗi**:
  * Dòng evidence: `Bộ bảo vệ thấp áp UVT coil 2,700,000` $\rightarrow$ material_code bị trích xuất thành `"BỘ"`.
  * Dòng evidence: `Khóa liên động 2-way (dùng cho 2 ACB) 12,000,000` $\rightarrow$ material_code bị trích xuất thành `"KHÓA"`.
* **Nguyên nhân kỹ thuật (Root Cause)**:
  * Tương tự Trang 2, các dòng phụ kiện ACB có mô tả dài khiến các mã viết tắt phụ kiện (`UVT`, `IB`, `Motor`) nằm ngoài dải cột `"ma"`, dẫn đến việc parser fallback lấy token mô tả tiếng Việt đầu tiên làm mã hàng và bị loại bỏ bởi validator.
* **Độ tin cậy của phân tích (Confidence)**: **HIGH**
* **Đề xuất xử lý**:
  * **Giữ nguyên Known Limitation**. Phần bóc tách các thiết bị chính ACB ở nửa trên Trang 5 hoạt động rất tốt. Việc sửa đổi parser/config để phục vụ riêng các dòng phụ kiện ACB chưa có quy luật tọa độ đủ ổn định, dễ gây regression (lỗi hồi quy) cho ACB chính.

---

### C. Hãng CHINT – Trang 3 (MCCB NXM/NM1)
* **Số lượng Valid**: 15
* **Số lượng Invalid**: 6
* **Tỷ lệ lỗi (Invalid Ratio)**: 28.6%
* **Ví dụ dòng lỗi**:
  * Dòng evidence: `Iđm (A) Icu (kA) Mã 2P 3P 4P` $\rightarrow$ trích xuất thành `"MÃ"`.
  * Dòng evidence: `Dải dòng định mức: 25A ÷ 1250A` $\rightarrow$ trích xuất thành `"DẢI"`.
* **Nguyên nhân kỹ thuật (Root Cause)**:
  * Trang 3 của CHINT chứa 2 bảng: nửa trên là NXM, nửa dưới là NM1. NM1 bắt đầu từ tọa độ Y ~`390.0`, lặp lại các dòng tiêu đề và chú thích kỹ thuật của bảng.
  * Các dòng tiêu đề và chú thích này nằm trọn trong dải quét Y hợp lệ `[140.0, 700.0]`, nên bị parser đưa vào bóc tách sản phẩm và bị validator loại bỏ dưới dạng invalid items.
* **Độ tin cậy của phân tích (Confidence)**: **HIGH**
* **Đề xuất xử lý**:
  * **Cần sửa đổi parser**. Bổ sung các từ khóa tiếng Việt đặc trưng của tiêu đề bảng (`"tiêu chuẩn:"`, `"định mức:"`, `"số pha:"`, `"đơn giá"`, `"iđm (a)"`) vào bộ lọc rác chung của parser để loại bỏ sớm các dòng rác tiêu đề trước khi đưa vào bóc tách và validate.

---

### D. Hãng CHINT – Trang 5 (Rơ le nhiệt NXR)
* **Số lượng Valid**: 7
* **Số lượng Invalid**: 0
* **Tỷ lệ lỗi (Invalid Ratio)**: 0.0%
* **Ví dụ dòng lỗi**: Không có dòng lỗi nào.
* **Nguyên nhân kỹ thuật (Root Cause)**:
  * Trang 5 của Chint thực tế chỉ chứa đúng 7 dòng thiết bị rơ le nhiệt NXR hợp lệ. Các dòng khác ở dưới là dòng phụ kiện không có mã hàng đi kèm.
  * Parser đã bóc tách đúng 100% (7/7 dòng thiết bị). Tuy nhiên, do quy tắc đánh giá trang `PASS` yêu cầu số lượng dòng thiết bị hợp lệ tối thiểu trên trang phải `>= 10`, trang này bị đánh giá là `PARTIAL`.
* **Độ tin cậy của phân tích (Confidence)**: **HIGH**
* **Đề xuất xử lý**:
  * **Giữ nguyên Known Limitation**. Không được hạ ngưỡng số lượng thiết bị tối thiểu (10 dòng) để làm đẹp báo cáo. Kết quả bóc tách thực tế đã đúng hoàn toàn, trạng thái `PARTIAL` do số dòng thực tế ít là một giới hạn định lượng khách quan.

---

## 2. Kết Luận & Phương Án Triển Khai

* Đối với **LS Page 2 & Page 5** và **CHINT Page 5**: Giữ nguyên `Known Limitations` là giải pháp an toàn và bảo vệ tính ổn định cao nhất của parser cho thiết bị chính.
* Đối với **CHINT Page 3**: Triển khai sửa đổi bộ lọc tiêu đề rác trong `profile_runner.py` để nâng chất lượng trang này lên `PASS`.
