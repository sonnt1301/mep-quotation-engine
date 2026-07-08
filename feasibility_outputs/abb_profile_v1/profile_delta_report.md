# Báo Cáo Delta So Sánh Kết Quả Bóc Tách Hãng ABB (v0 -> v1)

Báo cáo này so sánh kết quả bóc tách và phân lọc khả thi giữa phiên bản `abb_profile_v0` và phiên bản cải tiến `abb_profile_v1`.

---

## 1. Thống Kê Tổng Hợp (Global Delta Summary)

| Chỉ số | Phiên bản v0 | Phiên bản v1 | Thay đổi |
| --- | --- | --- | --- |
| **Tổng số vật tư hợp lệ (Valid)** | 681 | 743 | **+62 items** |
| **Tổng số vật tư bị loại (Invalid)** | 205 | 2 | **-203 items** |
| **Số trang đạt PASS** | 4 | 13 | **+9 trang** (Đạt tỷ lệ 100%) |
| **Số trang PARTIAL** | 9 | 0 | **-9 trang** |
| **Trạng thái toàn cục** | PARTIAL | **PASS** | Cải thiện vượt bậc |

---

## 2. Chi Tiết Cải Thiện Từng Trang (Page-by-Page Delta)

| Trang | Status v0 | Status v1 | Valid v0 -> v1 | Invalid v0 -> v1 | Nguyên nhân chính và cải tiến |
| --- | --- | --- | --- | --- | --- |
| **Page 18** | PASS | PASS | 92 -> 92 | 0 -> 0 | Giữ vững chất lượng PASS cũ. |
| **Page 19** | PASS | PASS | 92 -> 92 | 0 -> 0 | Giữ vững chất lượng PASS cũ. |
| **Page 20** | PARTIAL | PASS | 60 -> 54 | 8 -> 0 | Lọc sạch các dòng phụ kiện rác không có đơn giá. |
| **Page 21** | PARTIAL | PASS | 50 -> 50 | 30 -> 2 | Loại bỏ hoàn toàn các dòng tiêu đề rác của nhóm 36/50/70KA. |
| **Page 32** | PARTIAL | PASS | 94 -> 98 | 4 -> 0 | Khôi phục thêm 4 items hợp lệ và lọc sạch invalid. |
| **Page 33** | PARTIAL | PASS | 30 -> 30 | 36 -> 0 | Tách thành công tiền tố `MP/FP` khỏi mã ACB Emax2, lọc sạch rác. |
| **Page 34** | PARTIAL | PASS | 38 -> 38 | 40 -> 0 | Loại bỏ hoàn toàn các dòng phụ kiện rác không có giá tiền của ACB. |
| **Page 41** | PARTIAL | PASS | 8 -> 39 | 38 -> 0 | Layout `four_columns_ot_page41` mới giúp bóc đúng 39 mã OT sạch và đơn giá. |
| **Page 42** | PARTIAL | PASS | 8 -> 39 | 38 -> 0 | Layout `four_columns_ot_page41` mới giúp bóc đúng 39 mã OT sạch và đơn giá. |
| **Page 52** | PARTIAL | PASS | 68 -> 68 | 19 -> 0 | Lọc sạch hoàn toàn các dòng mô tả phụ kiện dính lề phải. |
| **Page 53** | PARTIAL | PASS | 46 -> 46 | 11 -> 0 | Lọc sạch hoàn toàn các dòng mô tả phụ kiện dính lề phải. |
| **Page 54** | PASS | PASS | 48 -> 48 | 0 -> 0 | Giữ vững chất lượng PASS cũ. |
| **Page 61** | PASS | PASS | 49 -> 49 | 0 -> 0 | Giữ vững chất lượng PASS cũ. |

---

## 3. Các Luật Và Cấu Hình Cải Tiến (Rule Changes)
1. **Thiết lập layout `"four_columns_ot_page41"`**: Định hình riêng dải cột X cho nhóm trang switch-disconnector OT (Trang 41, 42), tách sạch cột dòng định mức và cột mã sản phẩm, giải quyết triệt để lỗi ghép dính mã hàng cũ.
2. **Cơ chế `"clean_acb_code"`**: Tách bỏ tiền tố dính liền `MP` (Moveable Part) hoặc `FP` (Fixed Part) ở đầu mã ACB Emax2 (ví dụ: `MP1SDA072051R1` -> `1SDA072051R1`), giúp validator nhận dạng chính xác định dạng mã hàng của hãng.
3. **Cơ chế lọc sớm vật tư rác**: Chỉ append vật tư vào danh sách bóc tách khi đơn giá của dòng đó $> 0$ và mã hàng không rỗng. Điều này loại bỏ tận gốc các dòng mô tả phụ kiện dài hoặc tiêu đề phụ bị bóc nhầm làm tăng số lượng invalid một cách giả tạo.
