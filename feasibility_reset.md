# Tài Liệu Đánh Giá Tính Khả Thi – Feasibility Reset (ABB Benchmark)

## 1. Tuyên Bố Reset & Đóng Băng Pipeline
* **Tình trạng hiện tại**: Pipeline hiện tại đọc được text PDF nhưng chưa bóc tách một cách đáng tin cậy cấu trúc bảng giá MEP tiếng Việt thành dữ liệu vật tư có thể sử dụng trực tiếp cho báo giá MEP.
* **Đánh giá độ tin cậy**: Các file trung gian được tạo ra trước đây bao gồm `line_candidates.json`, `row_candidates.json`, `item_candidates.json` và `normalized_draft.json` hiện **không được coi là dữ liệu đáng tin cậy** trong việc bóc tách cấu trúc bảng.
* **Quyết định đóng băng**: Dừng toàn bộ việc mở rộng Phase sản phẩm mới, không chỉnh sửa UI chính, không sửa đổi parser hiện tại của pipeline chính, không chỉnh sửa các tệp tin lưu trữ và phê duyệt cũ. Việc tiếp tục triển khai Phase/UI chỉ được xem xét sau khi bài kiểm tra tính khả thi này vượt qua (PASS).

## 2. Benchmark Trang 18 PDF ABB
* **Tệp nguồn**: `D:/mep_quotation_pipeline/data/suppliers/ABB/2020/2020-01-01_001/source/original.pdf`
* **Mục tiêu**: Bóc tách chính xác bảng thiết bị đóng cắt trên trang số 18.
* **Tiêu chí Đánh giá (Pass/Fail Criteria)**:
  * **PASS (Đạt)**:
    * Trích xuất được ít nhất 20 vật tư thực tế (item) từ trang 18.
    * Có đầy đủ cả hai loại thiết bị 3 cực (3P) và 4 cực (4P).
    * Các mã vật tư trích xuất bắt đầu bằng mã ABB chính xác (ví dụ: `1SDA...`).
    * Có đơn giá VND tương ứng khớp chính xác.
    * File Excel kết xuất mở ra hiển thị các hàng cột rõ ràng, có ý nghĩa.
    * Không chứa các dòng rác, tiêu đề bảng biểu hay năm 2020 bị nhận diện nhầm làm đơn giá.
  * **PARTIAL (Đạt một phần)**:
    * Trích xuất được một phần dữ liệu nhưng đòi hỏi cấu hình tọa độ hoặc profile phức tạp hơn.
  * **FAIL (Thất bại)**:
    * Không bóc tách được dòng vật tư có cấu trúc bảng biểu nào.
