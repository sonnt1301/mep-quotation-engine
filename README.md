# MEP Quotation Pipeline - Foundation and PDF Intake

Dự án này là nền tảng (Foundation và PDF Intake) của hệ thống MEP Quotation Pipeline, được xây dựng theo hướng **Specification-First** sử dụng Python 3.12+, Pydantic v2 và Pytest.

## Cấu Trúc Thư Mục Dữ Liệu

Dữ liệu được lưu trữ một cách deterministic trong thư mục `data/` theo định dạng:
```
data/
  suppliers/
    {SUPPLIER_CODE}/
      {YEAR}/
        {YYYY-MM-DD}_{SEQ}/
          source/               # Chứa các file PDF gốc đầu vào
          parsed/               # Chứa kết quả phân tích thô (quotation.json, quotation.md)
          normalized/           # Chứa file chuẩn hóa (normalized.json)
          corrections/          # Chứa các hiệu chỉnh thủ công (corrections.json)
          logs/                 # Nhật ký kiểm toán (processing.log.jsonl)
          package.json          # Metadata của toàn bộ gói báo giá
  indexes/
    material_index.json         # Chỉ mục trung tâm của toàn bộ vật tư
```

## Quy ước Đường dẫn (Path Conventions)

- Mọi đường dẫn thư mục trong tệp metadata `package.json` đều là đường dẫn tương đối tính từ thư mục gốc của package.
- Đường dẫn `package_path` trong tệp chỉ mục trung tâm `data/indexes/material_index.json` là **đường dẫn tương đối tính từ thư mục gốc của dự án (Project Root)**, ví dụ: `data/suppliers/AUT/2026/2026-05-20_001`.

## Cài Đặt

1. **Tạo Môi Trường Ảo (Virtual Environment):**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Cài Đặt Các Thư Viện Phụ Thuộc:**
   ```bash
   pip install -e .[dev]
   ```

## Sử Dụng CLI

CLI cung cấp các câu lệnh sau để vận hành hệ thống:

1. **Import Tệp PDF Báo Giá (PDF Intake):**
   ```bash
   python -m mep_quotation.cli.main import-pdf --supplier AUT --date 2026-06-20 --file quotation.pdf
   
   # Tùy chọn sequence cố định và giới hạn kích thước cảnh báo (mặc định 50MB):
   python -m mep_quotation.cli.main import-pdf --supplier AUT --date 2026-06-20 --file quotation.pdf --seq 1 --max-size-mb 10
   ```

1. **Tạo Gói Báo Giá Mới (Khởi tạo package rỗng):**
   ```bash
   python -m mep_quotation.cli.main create-package --supplier AUT --date 2026-05-20
   ```

1. **Kiểm Tra Tính Hợp Lệ Của Gói:**
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-05-20_001
   ```

1. **Ghi Nhận Chỉnh Sửa Dữ Liệu:**
   ```bash
   python -m mep_quotation.cli.main record-correction data/suppliers/AUT/2026/2026-05-20_001 --field "items[0].unit_price" --old 18500 --new 19200 --reason "Supplier revised quotation"
   ```

1. **Xây Dựng Lại Chỉ Mục Vật Tư:**
   ```bash
   python -m mep_quotation.cli.main build-index
 
   # Hoặc chạy ở chế độ nghiêm ngặt (dừng và báo lỗi ngay khi có file normalized lỗi):
   python -m mep_quotation.cli.main build-index --strict
   ```

1. **Tìm Kiếm Vật Tư:**
   ```bash
   python -m mep_quotation.cli.main search-material "CV-3X2.5"
   ```

## Chạy Bộ Kiểm Thử (Tests)

Chạy tất cả các test cases bằng `pytest`:
```bash
pytest -v
```
