# Tài Liệu Cấu Hình Nhà Cung Cấp (Supplier Profile Config Format)

Thư mục này chứa các tệp cấu hình JSON khai báo các thông số dải cột, Regex và validation đặc thù của từng nhà cung cấp phục vụ bóc tách MEP độc lập.

---

> [!WARNING]
> **CẢNH BÁO QUAN TRỌNG**
> Các tệp cấu hình này hiện đang ở trạng thái **Feasibility (Khảo sát khả thi)**. 
> Chúng **chưa sẵn sàng cho môi trường Production (Not Production-Ready)** và chưa được tích hợp vào pipeline bóc tách chính cũng như giao diện Streamlit UI của dự án.

---

## 1. Vai Trò Của Profile Config
Thay vì lập trình cứng (hardcode) các dải tọa độ cột X, Regex tiền tố mã hàng, và các luật validate trong mã nguồn Python (như trong các mô-đun bóc tách v0/v1 trước đó), cấu hình profile giúp:
* **Tách cấu hình ra khỏi code logic**: Dễ dàng chỉnh sửa dải tọa độ cột khi nhà cung cấp thay đổi nhẹ layout mà không cần sửa đổi mã nguồn.
* **Tự động hóa Router**: Giúp bộ định tuyến (Profile Router) sau này nhận diện supplier, tự động nạp tệp JSON cấu hình tương ứng và bóc tách tự động.

---

## 2. Ý Nghĩa Các Trường Trường Trong Config JSON

### Metadata chung
* `profile_id`: Định danh duy nhất cho bộ cấu hình (ví dụ: `abb_profile_v1`).
* `supplier_code`: Mã nhà cung cấp viết tắt (`ABB`, `LS`).
* `profile_version`: Phiên bản cấu hình (ví dụ: `1.0`).
* `status`: Trạng thái thử nghiệm (`feasibility`, `candidate`, `production`).
* `source_type`: Loại tệp nguồn hỗ trợ (`pdf`, `excel`, `csv`).

### `global_rules` (Luật toàn cục)
* `currency`: Đơn vị tiền tệ mặc định (`VND`).
* `default_unit`: Đơn vị tính mặc định (`cái`).
* `min_unit_price`: Đơn giá tối thiểu được chấp nhận.
* `reject_year_as_price`: Tự động loại bỏ nếu đơn giá dính lỗi trùng với năm (ví dụ: `2020` hoặc `2026`).

### `layouts` (Danh sách bố cục bảng của NCC)
Mỗi NCC có thể có nhiều layout bảng khác nhau tùy theo nhóm trang:
* `layout_name`: Tên layout (`double_column_3p_4p`, `split_half_left_right`...).
* `pages`: Danh sách trang áp dụng layout này.
* `parser_type`: Thuật toán bóc tách áp dụng (`coordinate_column_profiler`).
* `columns`: Dải tọa độ cột X dưới dạng `[min_x, max_x]` của từng cột trong layout.
* `row_detection`: Cấu hình nhận diện dòng (y-range, row_tolerance).
* `special_rules`: Các quy tắc đặc thù (ví dụ: `"clean_acb_mp_fp_prefixes"` để loại MP/FP ở ACB).

### `validation` (Luật kiểm định)
* `allowed_material_code_prefixes`: Danh sách tiền tố mã hàng hợp lệ được chấp nhận (ví dụ: `1SDA`, `ABN`...).
* `allow_ampere_list_patterns`: Regex chấp nhận các dòng định mức đặc biệt dính phẩy (ví dụ: danh sách dòng định mức LS).
* `reject_description_price_noise`: Bật/tắt việc loại bỏ các dòng mô tả có chứa giá tiền gây loãng thông tin.

---

## 3. Quy Trình Thêm Nhà Cung Cấp Mới (Supplier)
1. **Khảo sát PDF**: Trích xuất tọa độ word thực tế của PDF hãng mới bằng script debug.
2. **Khai báo JSON**: Tạo tệp `<supplier>_profile_v1.json` trong thư mục này.
3. **Khai báo Layout**: Xác định tọa độ X của các cột (mã, giá, dòng định mức) và khai báo vào trường `layouts`.
4. **Khai báo prefix**: Điền tiền tố mã hàng đặc trưng của hãng vào `allowed_material_code_prefixes` để validator lọc sạch tiêu đề rác.
5. **Nạp thử**: Dùng module `profile_config_loader.py` để validate tính hợp lệ của tệp JSON vừa tạo.
