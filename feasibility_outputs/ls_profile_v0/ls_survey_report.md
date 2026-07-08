# Báo Cáo Khảo Sát Sơ Bộ – LS Supplier Feasibility

## 1. Thông Tin Tệp Tin & Metadata
* **File được chọn**: `F:/00.HVC/Bang gia/LS/Bang gia LS ap dung ngay 15-04-2026.pdf` (Tệp tổng hợp 2026 không chứa hãng LS, do đó đã chọn tệp báo giá LS gốc này để khảo sát trung thực)
* **Số lượng trang**: 8 trang
* **Trạng thái mã hóa (Encrypted)**: False
* **Lớp văn bản (Text Layer)**: True (Có sẵn text layer gốc bóc được bằng pdfplumber)
* **Các trang nghi ngờ chứa bảng giá**: Trang 1, 2, 3, 4, 5, 6, 7, 8 (Toàn bộ tệp 8 trang đều chứa các bảng thiết bị đóng cắt và phụ kiện của LS)

## 2. Phân Tích Layout & Cấu Trúc Các Trang Benchmark Đề Xuất
Dưới đây là văn bản thô mẫu từ 5 trang benchmark đầu tiên:

### Trang 1 (MCCB 2P, 3P, 4P & ELCB 2P, 3P)
```text
Cầu dao điện MCCB (APTOMAT) loại khối 2 Pha | Cầu dao điện MCCB (APTOMAT) loại khối 4 Pha
Tên hàng | In (A) | Icu(KA) | Giá bán | Tên hàng | In (A) | Icu(KA) | Giá bán
ABN52c | 15-20-30-40-50A | 30 | 990,000 | ABN54c | 15-20-30-40-50A | 18 | 1,500,000
ABN62c | 60A | 30 | 1,100,000 | ABN104c | 15,20,30,40,50,60,75,100A | 22 | 1,850,000
```

### Trang 2 (MCCB Chỉnh Dòng & Phụ Kiện MCCB)
```text
MCCB 3 Pha loại khối chỉnh dòng | Cầu dao điện ELCB 4 cực loại khối chống rò điện
ABS103c FMU | 20-25-32-40-50-63-80-100-125A | 37 | 2,500,000
Cuộn đóng ngắt SHT for ABN100c~ABH250c | 930,000 | DH100-S for ABN103c | 670,000
```

### Trang 3 (MCB, RCBO, RCCB, SPD & Phụ Kiện MCB)
```text
Cầu dao điện loại tép MCB (gắn trên thanh ray) | Cầu dao điện loại tép bảo vệ quá tải RCBO
LA63N 1P | 6-10-16-20-25-32A | 6KA | 115,000 | LB63N 1P+N | 3-6-10-16-20-25-32A | 6KA | 596,000
LA63N 1P | 40-50-63A | 6KA | 121,000
```

### Trang 4 (Contactor, Rơ Le Nhiệt, Phụ Kiện Contactor & Cuộn Hút)
```text
KHỞI ĐỘNG TỪ 3 PHA (CONTACTOR 3 POLES) | RƠ LE NHIỆT
MC-6a (1) | 6A (1a) | 420,000 | MT-12 (1) | 0.63~18A | 470,000
MC-9a (1) | 9A (1a) | 440,000
```

### Trang 5 (ACB Metasol 3P & 4P Cố Định / Rút Kéo & Phụ Kiện ACB)
```text
Cầu dao điện ACB METASOL 3 Pha (loại cố định) | ACB METASOL 3 Pha loại cố định - chưa có Motor
AN-06D3-06H AH6 | 630A | 65 | 58,500,000 | AN-08D3-08H AH6 | 800A | 65 | 62,800,000
```

## 3. Nhận Xét Chung & Layout Đề Xuất
* **Nhận xét**: Cấu trúc bảng của LS chia rõ rệt làm 2 nửa trái và phải song song nhau. Tọa độ X0 của các cột được định vị cố định cho từng trang.
* **Mã sản phẩm (material_code)**: Thường bắt đầu bằng prefix của hãng LS như `ABN`, `ABS`, `EBS`, `EBN`, `LA`, `LB`, `LC`, `MC`, `MT`, `GMP`, `BK`, `AN`, `AS`, `TS`... đi kèm thông số cực và dòng định mức.
* **Mẫu Layout**:
  * Áp dụng bố cục **Split Half Left/Right** cho hầu hết cả 5 trang benchmark, trong đó chia ranh giới X0 tại tọa độ khoảng `290.0` đến `300.0`.
  * Nửa trái: chứa Mô tả/Mã sản phẩm, Dòng định mức, Giá bán.
  * Nửa phải: chứa Mô tả/Mã sản phẩm, Dòng định mức, Giá bán độc lập.
