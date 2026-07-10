# Hướng Dẫn Sử Dụng Workspace Review Trực Quan – Phase 2A.5

Tài liệu này hướng dẫn cách chạy ứng dụng và thực hiện review trực quan dữ liệu bóc tách từ Integration Bridge bằng Streamlit UI, bao gồm luồng nhập và xử lý tệp PDF mới (PDF Intake & Processing Flow), hiển thị trang PDF gốc đối chiếu (PDF Page Preview) và Checklist kiểm thử thực tế.

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc ở Phase này chỉ phục vụ mục tiêu **Chuyển đổi khô (Dry-run Bridge) & Visual Human Review**.
> * **Không ghi dữ liệu vào main pipeline chính và không sửa đổi giao diện Streamlit UI cũ.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Ready for Production).

---

## 1. Cách Chạy Ứng Dụng Streamlit (Tránh Mojibake trên Windows)

Chạy lệnh sau tại thư mục gốc của dự án `D:\mep_quotation_pipeline` để ép Python dùng encoding UTF-8 và tránh lỗi hiển thị tiếng Việt trên Windows console:

* **Trong PowerShell**:
  ```powershell
  $env:PYTHONUTF8=1; python -m streamlit run tools/profile_bridge_review_app.py --browser.gatherUsageStats false
  ```
* **Trong Command Prompt (cmd)**:
  ```cmd
  set PYTHONUTF8=1
  python -m streamlit run tools/profile_bridge_review_app.py --browser.gatherUsageStats false
  ```

Streamlit sẽ tự động mở giao diện ứng dụng trên trình duyệt web mặc định (thông thường là `http://localhost:8501`).

---

## 2. Quy Trình Sử Dụng PDF Intake & Processing

Để xử lý một tệp PDF báo giá mới, người dùng thao tác tại vùng **📥 Thêm & Xử lý PDF mới (PDF Intake & Processing Flow)** ở đầu trang:

1. **Chọn Supplier / Profile Config**: Chọn một trong ba nhà cung cấp đã có cấu hình (`ABB`, `LS`, `CHINT`).
2. **Phương pháp nhập tệp PDF**:
   - **Upload tệp PDF**: Kéo thả tệp PDF báo giá từ máy tính vào giao diện Streamlit.
   - **Đường dẫn file trên máy (Local Path)**: Nhập đường dẫn tuyệt đối của tệp PDF (Ví dụ: `F:\00.HVC\Bang gia\LS\Bang gia LS ap dung ngay 15-04-2026.pdf`).
3. **Bắt đầu xử lý**: Nhấn nút **🚀 Bắt đầu xử lý PDF**.
   - Hệ thống sẽ tự động sao chép tệp PDF vào thư mục session riêng biệt dạng: `feasibility_outputs/profile_visual_review_sessions/{timestamp}_{SUPPLIER}/`
   - Gọi Profile Parser tương ứng bóc tách và chạy cầu nối chuyển đổi dry-run.
   - Tự động chuyển đổi sang chế độ review dữ liệu của session vừa chạy, nạp 100% dữ liệu vào workspace.
4. **Xem kết quả tóm tắt (Session Summary)**: Sau khi xử lý hoàn tất, giao diện hiển thị bảng tóm tắt kết quả (tên file, số dòng valid/invalid, đường dẫn session) và trạng thái sẵn sàng review.

---

## 3. PDF Page Preview & Độ Thu Phóng (Zoom)

Ở cột bên trái **Nguồn Đối Chiếu & Bằng Chứng**, giao diện sẽ tự động render trang PDF gốc tương ứng với thiết bị đang được chọn review:
1. **Độ thu phóng (Zoom)**: Sử dụng thanh trượt (slider) **Độ thu phóng PDF Preview (Zoom)** ngay trên hình ảnh để tăng giảm tỷ lệ phóng to (hỗ trợ scale từ 1.0 đến 3.0). Hình ảnh được render sắc nét qua PyMuPDF.
2. **Cache render tự động**: Các trang PDF đã render sẽ được lưu trữ trong cache LRU cục bộ để tránh việc render lại liên tục khi chuyển đổi qua lại giữa các dòng cùng trang.
3. **Chế độ fallback**: Trong trường hợp không tìm thấy tệp PDF (như chế độ benchmark mặc định không cấu hình đường dẫn tuyệt đối), hệ thống tự động fallback về văn bản bằng chứng dạng thô (Source Evidence Text) và hiển thị cảnh báo rõ ràng, không gây crash ứng dụng.

---

## 4. Các Chế Độ Review (Review Modes)

Trong sidebar bên trái, chọn **Chế độ review** phù hợp:
1. **Sample Review**: Tập trung kiểm tra tệp tin mẫu 73 dòng đại diện chứa các lỗi regression, giá lớn của ACB và các dòng known limitations phụ kiện.
2. **Duplicate Code Review**: Đánh giá các nhóm trùng mã hàng (tự động tính toán động từ tệp session nếu đang xem session).
3. **All Bridged Items**: Duyệt qua toàn bộ dòng dữ liệu (Cho phép đổi nguồn dữ liệu giữa **Dữ liệu Benchmark mặc định** và **Phiên xử lý PDF vừa chạy**).

---

## 5. Checklist Kiểm Thử Thực Tế (Human Test Checklist)

Người dùng (Reviewer) thực hiện kiểm thử thật theo các bước sau để nghiệm thu chất lượng hệ thống trước khi quyết định chuyển sang Phase 2B:

- [ ] **Bước 1: Chạy ứng dụng**
  - Khởi chạy Streamlit ứng dụng theo lệnh ở mục 1.
  - Xác nhận giao diện hiển thị tiếng Việt chuẩn, không còn mojibake.
- [ ] **Bước 2: Xử lý PDF CHINT thật**
  - Chọn Supplier là `CHINT`.
  - Chọn nhập bằng `Đường dẫn file trên máy (Local Path)`.
  - Nhập đường dẫn tuyệt đối của tệp CHINT:
    `F:\00.HVC\Bang gia\Bang gia VT Tu dien\Chint\Bảng giá Chint 1-3-2023 ck 50.pdf`
  - Nhấn nút **🚀 Bắt đầu xử lý PDF**.
- [ ] **Bước 3: Xác nhận Dashboard & Session Summary**
  - Xác nhận Dashboard hiển thị đúng **45** dòng cần review của session (thay vì 73 dòng mặc định của sample benchmark).
  - Giao diện tự động chuyển `review_mode` sang **All Bridged Items** và nạp nguồn dữ liệu là **Phiên xử lý PDF vừa chạy**.
  - Xác nhận bảng tóm tắt phiên xử lý hiển thị đúng: Trang 3 `PASS`, Trang 4 `PASS`, Trang 5 `PARTIAL`.
- [ ] **Bước 4: Xác nhận PDF Page Preview hoạt động trực quan**
  - Chọn một dòng thuộc trang 3: Xác nhận cột bên trái hiển thị ảnh chụp bản vẽ trang 3 của tệp PDF.
  - Chuyển sang chọn một dòng thuộc trang 4: Xác nhận ảnh cột bên trái tự động cập nhật sang trang 4.
  - Sử dụng slider Zoom kéo lên mức 2.0: Xác nhận hình ảnh trang PDF được phóng to rõ nét.
- [ ] **Bước 5: Thực hiện Quyết Định Review trên vật tư**
  - Chọn dòng đầu tiên, nhấn **APPROVE**. Hệ thống lưu thành công và tự động nhảy sang dòng kế tiếp.
  - Chọn dòng tiếp theo, sửa đổi mô tả hoặc mã chuẩn hóa, nhập ghi chú lý do sửa đổi vào ô ghi chú, sau đó bấm **EDIT & APPROVE**. Xác nhận lưu thành công.
  - Chọn một dòng khác, nhập lý do nghi vấn vào ô ghi chú, sau đó bấm **NEEDS INVESTIGATION**. Xác nhận hệ thống hiển thị cảnh báo Warning đỏ trên Dashboard do có dòng cần kiểm tra lại.
- [ ] **Bước 6: Kiểm chứng tệp quyết định lưu vết**
  - Mở thư mục `feasibility_outputs/profile_bridge_human_review/` trên máy tính.
  - Xác nhận các quyết định đã được ghi nhận đầy đủ vào tệp `profile_bridge_review_decisions.json` và `profile_bridge_review_decisions.csv`.
- [ ] **Bước 7: Kiểm tra Duplicate Review của Session**
  - Chuyển `review_mode` sang **Duplicate Code Review**.
  - Xác nhận các nhóm trùng mã hiển thị được tính toán động dựa trên 45 dòng của CHINT vừa chạy.
- [ ] **Bước 8: Kiểm thử khả năng chịu lỗi (Fault-tolerance)**
  - Nhập một đường dẫn tệp PDF không tồn tại và nhấn xử lý.
  - Xác nhận Streamlit hiển thị thông báo lỗi rõ ràng bên dưới nút xử lý, và ứng dụng **không bị crash hay sập server**.

---

## 6. Điều Kiện Để Chuyển Phase 2B (Write Adapter)
* Tỷ lệ duyệt (`APPROVE` hoặc `ACCEPT_WITH_LIMITATION`) trên tệp sample `>= 95%`.
* Không còn bất kỳ dòng nào ở trạng thái `NEEDS_INVESTIGATION` hoặc `REJECT` chưa được xử lý (Hệ thống sẽ hiển thị cảnh báo Warning trên Dashboard nếu còn tồn tại).
