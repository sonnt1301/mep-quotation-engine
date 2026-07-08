# Báo Cáo Delta So Sánh Kết Quả Bóc Tách Hãng LS (v0 -> v1)

Báo cáo này so sánh kết quả bóc tách và phân lọc khả thi giữa phiên bản `ls_profile_v0` và phiên bản cải tiến `ls_profile_v1`.

---

## 1. Thống Kê Tổng Hợp (Global Delta Summary)

| Chỉ số | Phiên bản v0 | Phiên bản v1 | Thay đổi |
| --- | --- | --- | --- |
| **Tổng số vật tư hợp lệ (Valid)** | 224 | 282 | **+58 items** |
| **Tổng số vật tư bị loại (Invalid)** | 81 | 19 | **-62 items** |
| **Số trang đạt PASS** | 2 | 3 | **+1 trang** (Trang 3 đạt PASS) |
| **Số trang PARTIAL** | 3 | 2 | **-1 trang** |
| **Trạng thái toàn cục** | PARTIAL | PARTIAL | Cải thiện chất lượng bóc tách |

---

## 2. Chi Tiết Cải Thiện Từng Trang (Page-by-Page Delta)

| Trang | Status v0 | Status v1 | Valid v0 -> v1 | Invalid v0 -> v1 | Nguyên nhân chính và cải tiến |
| --- | --- | --- | --- | --- | --- |
| **Page 1** | PASS | PASS | 67 -> 67 | 0 -> 0 | Giữ vững chất lượng PASS cũ. |
| **Page 2** | PARTIAL | PARTIAL | 32 -> 33 | 11 -> 10 | Bóc tách thành công mã dòng định mức dính phẩy của EBS104c. |
| **Page 3** | PARTIAL | PASS | 36 -> 69 | 35 -> 2 | Mở rộng dải cột `ma` lề phải giúp khôi phục 33 items MCB/RCBO lề phải. |
| **Page 4** | PASS | PASS | 63 -> 63 | 1 -> 1 | Giữ vững chất lượng PASS cũ. |
| **Page 5** | PARTIAL | PARTIAL | 26 -> 50 | 30 -> 6 | Bóc tách đúng toàn bộ 24 items ACB Metasol lề phải. |

---

## 3. Các Luật Và Cấu Hình Cải Tiến (Rule Changes)
1. **Mở rộng dải cột mã hàng lề phải (`right` `ma`)**: Điều chỉnh dải tọa độ X của cột mã hàng lề phải sang `(291.0, 385.0)` thay vì `(316.0, 385.0)`. Điều này giúp bao quát đúng các dòng MCB (`LB63N`) và ACB Metasol (`AN-06D3-06H`) có mã hàng bắt đầu sớm hơn, cứu sống 57 items valid trước đó bị bóc lệch cột.
2. **Nới lỏng validator cho danh sách dòng định mức trong mô tả**: Cập nhật hàm `is_ampere_list` trong validator của LS để tự động nhận dạng các dãy định mức dính phẩy nằm trong mô tả bằng Regex `\b\d{1,3}(?:,\d{1,3})+A\b`. Nhờ đó, loại bỏ hoàn toàn các cảnh báo dính giá tiền giả tạo cho mã `EBS104c`.
3. **Cơ chế lọc sớm vật tư rác**: Tương tự như ABB, loại bỏ sớm các dòng phụ kiện mô tả dài tiếng Việt không có đơn giá thực sự ngay từ parser để làm sạch tệp invalid json.
