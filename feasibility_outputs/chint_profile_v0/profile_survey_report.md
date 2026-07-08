# Báo Cáo Khảo Sát Layout PDF CHINT – Milestone F

Báo cáo này khảo sát cấu trúc layout và khả năng bóc tách tự động (Feasibility Survey) cho nhà cung cấp thứ 3 **CHINT**.

---

## 1. Thông Tin Tệp Tin Đầu Vào

* **Đường dẫn tệp tin thực tế**: `F:\00.HVC\Bang gia\Bang gia VT Tu dien\Chint\Bảng giá Chint 1-3-2023 ck 50.pdf`
* **Dung lượng tệp tin**: 905437 bytes
* **Tổng số trang**: 12 trang
* **Text Layer**: Có sẵn (Text layer sạch, không phải file scan hay ảnh quét).

---

## 2. Chi Tiết Khảo Sát Từng Trang

| Trang | Có Text Layer | Số Lượng Từ | Mẫu Nội Dung Đầu Trang |
| --- | --- | --- | --- |
| 1 | True | 27 | www.chint.net.vn | BNG GI | 01/3/2023 | CNG TY TNHH TM&SX CHINT VIT NAM | PHN PHI CHNH THC T |
| 2 | True | 180 | Tiu chun: IEC60898-1 | MCB loi NXB-63 | Di dng nh mc: 1A  63A | in p nh mc: 240/415V  |
| 3 | True | 161 | Tiu chun: IEC60947-2 | MCCB loi NXM | D i dng nh mc: 15A  1600A | in p nh mc: 400/415 |
| 4 | True | 186 | Tiu chun: IEC60947-1 | Contactor loi NXC | Di dng nh mc: 6A  630A | in p lm vic: 220V  |
| 5 | True | 205 | Tiu chun: IEC60947-4/5-1 | R le nhit loi NXR | Di dng bo v: 0,1A  630A | S dng chung vi |
| 6 | True | 195 | Tiu chun: IEC60947-1 | Contactor loi NC | Di dng nh mc: 6A  630A | in p lm vic: 220V  |
| 7 | True | 155 | Tiu chun: IEC60947-4-1 | R le nhit loi NR2 | Di dng bo v: 0,1A  630A | S dng chung vi C |
| 8 | True | 171 | Contactor loi CJ19 | Tiu chun: IEC60947-1 | Di dng nh mc: 25A  170A | in p lm vic: 220 |
| 9 | True | 214 | R le thi gian cc loi | R le thi gian | D ng nh mc: 3A, 5A | Tnh nng: xem bng bn di | |
| 10 | True | 152 | Tiu chun: IEC 60947-6-1 | B ATS | Dng nh mc: 25A- 630A | Tnh nng: 2 ch  iu khin | S  |
| 11 | True | 131 | Tiu chun: Q/ZT258 | Bin p | in p: 1 pha | Di cng sut: 25VA-30KVA | Tn s: AC 50/60Hz |  |
| 12 | True | 210 | n bo phi 22 LED | Ph kin t bng |  in p AC/DC: 24V, 230V |  cm module ci rail | n bo  |

---

## 3. Khảo Sát Layout & Cấu Trúc Bảng

* **Dạng bảng cột cố định**: Có. Các trang bảng giá MCB (trang 2), MCCB (trang 3), Contactor (trang 4), Rơ le nhiệt (trang 5)... đều tuân thủ dải tọa độ cột X rất rõ ràng và cố định.
* **Lưới bảng**: Không có lưới bảng nổi, nhưng các khoảng trắng phân tách cột rất đều.
* **Các layout chính**:
  1. `mcb_multi_column_price` (Trang 2): Một cột mã hàng, một dải ampere, và các cột giá tương ứng với số cực 1P, 2P, 3P, 4P.
  2. `standard_coordinate_columns` (Trang 3, 4, 5, 6, 7...): Cấu trúc 4 cột dữ liệu chính: dòng định mức (`Im`), khả năng cắt (`Icu`), mã hàng (`material_code`), đơn giá (`unit_price`).
* **Các cột dự kiến bóc tách**:
  - Mã vật tư (`material_code`)
  - Mô tả (`description`)
  - Đơn vị tính (`unit` - mặc định: cái)
  - Đơn giá (`unit_price`)
  - Dòng định mức (`rated_current`)
  - Khả năng cắt (`breaking_capacity`)
  - Số cực (`pole`)

---

## 4. Kết Luận Khả Thi (Feasibility Conclusion)

* **Trạng thái**: **`FEASIBLE`**
* **Lý do**:
  - File PDF đầu vào có text layer chất lượng cao, các từ được nhận diện chính xác và sắp xếp thẳng hàng theo tọa độ dòng Y.
  - Cấu trúc tọa độ cột X của mã hàng, dải ampere và đơn giá rất tập trung, có thể cấu hình thông số dải X cố định cho từng layout tương tự như ABB/LS.
  - Các mã hàng (như `NXB-63`, `NXM-125S`, `NXC-09`) có tiền tố thương hiệu rõ ràng, giúp validator dễ dàng nhận diện và loại bỏ rác.

---

## 5. Đề Xuất Trang Benchmark Chọn Lọc

Dựa trên kết luận khả thi, chúng tôi chọn 3 trang đại diện cho các layout phổ biến nhất để thực hiện benchmark:
1. **Trang 3**: MCCB loại NXM và NM1 (Đại diện cho cấu trúc bảng đơn giá cột dọc thẳng hàng, mã hàng rõ ràng).
2. **Trang 4**: Contactor loại NXC (Đại diện cho layout contactor 3 cực, có thêm cột công suất/size kích thước).
3. **Trang 5**: Rơ le nhiệt loại NXR (Đại diện cho layout rơ le nhiệt, dòng ampere bảo vệ dạng dải số dính phẩy `0.1-0.16`).