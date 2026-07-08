# Báo Cáo Tính Khả Thi Bóc Tách Bảng – ABB Page 18

## 1. Thông Tin Chung
* **Trang kiểm chứng**: Trang 18 (PDF gốc)
* **Tổng số vật tư bóc được**: 92
* **Số lượng vật tư 3 Cực (3P)**: 46
* **Số lượng vật tư 4 Cực (4P)**: 46
* **Kết quả đánh giá chung**: **PASS**

## 2. Dòng Dữ Liệu Mẫu (10 Dòng Đầu)
| STT | Mã Vật Tư | Mô Tả Vật Tư | Số Cực | Dòng Định Mức | Đơn Giá (VND) | Đơn Vị | Tiền Tệ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1SDA066799R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 3P 16A 18KA | 3P | 16A | 2,584,800 | cái | VND |
| 2 | 1SDA066810R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 4P 16A 18KA | 4P | 16A | 3,362,400 | cái | VND |
| 3 | 1SDA066800R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 3P 20A 18KA | 3P | 20A | 2,584,800 | cái | VND |
| 4 | 1SDA066811R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 4P 20A 18KA | 4P | 20A | 3,362,400 | cái | VND |
| 5 | 1SDA066801R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 3P 25A 18KA | 3P | 25A | 2,584,800 | cái | VND |
| 6 | 1SDA066812R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 4P 25A 18KA | 4P | 25A | 3,362,400 | cái | VND |
| 7 | 1SDA066802R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 3P 32A 18KA | 3P | 32A | 2,584,800 | cái | VND |
| 8 | 1SDA066813R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 4P 32A 18KA | 4P | 32A | 3,362,400 | cái | VND |
| 9 | 1SDA066803R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 3P 40A 18KA | 3P | 40A | 2,584,800 | cái | VND |
| 10 | 1SDA066814R1 | Cầu dao tự động dạng khối MCCB Tmax XT1B 4P 40A 18KA | 4P | 40A | 3,362,400 | cái | VND |

## 3. Các Lỗi & Hạn Chế
* **Tự động detect_table**: pdfplumber không tự động phát hiện được bảng do lưới vẽ của ABB quá mảnh hoặc không có viền. Do đó, phải sử dụng phương pháp bóc tách phân dải tọa độ cột X cứng.
* **Gộp khoảng trắng**: Đối với một số dòng, bộ sinh PDF bóc tách chữ bị phân mảnh (ví dụ: `1` và `SDA066810R1` bị chia cắt), hệ thống phải tiến hành dọn dẹp khoảng trắng để khôi phục mã đầy đủ.

## 4. Kết Luận
* Kết quả bóc tách đạt trạng thái **PASS** do vượt qua ngưỡng tối thiểu 20 dòng, bóc tách chính xác cấu trúc cột 3P và 4P, loại bỏ sạch dòng nhiễu tiêu đề và năm 2020.
* Khuyến nghị tiếp theo: Hướng tiếp cận phân tích tọa độ cột (Coordinate Column Profiler) là khả thi đối với các bảng giá PDF có cấu trúc cột cố định nhưng không có viền kẻ.
