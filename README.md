# MEP Quotation Pipeline - Foundation and PDF Intake

Dự án này là nền tảng (Foundation và PDF Intake) của hệ thống MEP Quotation Pipeline, được xây dựng theo hướng **Specification-First** sử dụng Python 3.12+, Pydantic v2 và Pytest.

## Release Scope

- `v0.2.0 PDF Intake Core` không rasterize các trang PDF và không sinh page images.
- Rasterization/page image generation được hoãn có chủ đích sang `v0.3.0 PDF Page Preparation`.

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

2. **Chuẩn Bị Ảnh Các Trang PDF (Page Image Preparation):**
   ```bash
   python -m mep_quotation.cli.main prepare-pages data/suppliers/AUT/2026/2026-06-20_001
   
   # Tùy chọn DPI, định dạng và ghi đè:
   python -m mep_quotation.cli.main prepare-pages data/suppliers/AUT/2026/2026-06-20_001 --dpi 150 --format png --overwrite
   ```

3. **Trích Xuất Văn Bản Gốc (Native PDF Text Extraction):**
   ```bash
   python -m mep_quotation.cli.main extract-text data/suppliers/AUT/2026/2026-06-20_001
   
   # Tùy chọn cho phép ghi đè:
   python -m mep_quotation.cli.main extract-text data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```

4. **Lắp Ghép Văn Bản Đầu Vào Cho Parser (Text Assembly):**
   ```bash
   python -m mep_quotation.cli.main assemble-text data/suppliers/AUT/2026/2026-06-20_001
   
   # Tùy chọn cho phép ghi đè:
   python -m mep_quotation.cli.main assemble-text data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```

5. **Trích Xuất Dòng Ứng Viên Báo Giá MEP (Rule-based Line Candidate Extraction):**
   ```bash
   python -m mep_quotation.cli.main parse-line-candidates data/suppliers/AUT/2026/2026-06-20_001
   
   # Tùy chọn cho phép ghi đè:
   python -m mep_quotation.cli.main parse-line-candidates data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```

6. **Gom Nhóm Hàng Ứng Viên Ghép (Row Candidate Assembly):**
   ```bash
   python -m mep_quotation.cli.main assemble-rows data/suppliers/AUT/2026/2026-06-20_001
   
   # Tùy chọn cho phép ghi đè và điều chỉnh gap dòng cho đơn giá:
   python -m mep_quotation.cli.main assemble-rows data/suppliers/AUT/2026/2026-06-20_001 --overwrite --max-line-gap-for-price 6
   ```

7. **Chuyển Đổi Hàng Ứng Viên Thành Ứng Viên Vật Tư Có Cấu Trúc (Structured Item Candidate Layer):**
   ```bash
   python -m mep_quotation.cli.main build-item-candidates data/suppliers/AUT/2026/2026-06-20_001

   # Tùy chọn cho phép ghi đè:
   python -m mep_quotation.cli.main build-item-candidates data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```

8. **Chuyển Đổi Các Ứng Viên Vật Tư Thành Bản Nháp Chuẩn Hóa (Normalized Draft Layer):**
   ```bash
   python -m mep_quotation.cli.main build-normalized-draft data/suppliers/AUT/2026/2026-06-20_001

   # Tùy chọn cho phép ghi đè:
   python -m mep_quotation.cli.main build-normalized-draft data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```

 9. **Ghi Nhận Quyết Định Phê Duyệt / Rà Soát (Human Review Decisions Layer):**
    *Khởi tạo file review trống:*
    ```bash
    python -m mep_quotation.cli.main create-review-file data/suppliers/AUT/2026/2026-06-20_001 --reviewer "human" --overwrite
    ```
    *Ghi nhận quyết định phê duyệt (approved):*
    ```bash
    python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0001 --decision approved --reason "Dữ liệu khớp chuẩn"
    ```
    *Ghi nhận quyết định từ chối (rejected):*
    ```bash
    python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0002 --decision rejected --reason "Dòng vật tư rác"
    ```
    *Ghi nhận quyết định chỉnh sửa (edited) với các trường ghi đè:*
    ```bash
    python -m mep_quotation.cli.main record-review data/suppliers/AUT/2026/2026-06-20_001 --draft-item-id AUT_20260620_001_DRAFTITEM_0003 --decision edited --reason "Sai đơn giá thực tế" --unit-price 150000 --currency VND --amount 750000
    ```
    *Xem thống kê các quyết định rà soát:*
    ```bash
    python -m mep_quotation.cli.main list-review data/suppliers/AUT/2026/2026-06-20_001
    ```

 10. **Xuất Bản Tệp Báo Giá Chuẩn Hóa Chính Thức (Official Normalized Export Layer):**
     *Chạy xuất bản tệp normalized.json từ draft và review decisions:*
     ```bash
     python -m mep_quotation.cli.main export-normalized data/suppliers/AUT/2026/2026-06-20_001
     ```
     *Tùy chọn ghi đè tệp normalized.json hiện hữu:*
     ```bash
     python -m mep_quotation.cli.main export-normalized data/suppliers/AUT/2026/2026-06-20_001 --overwrite
     ```

 11. **Xuất Bản Tệp Excel Báo Giá Chính Thức (Excel Export Layer):**
     *Chạy xuất bản tệp Excel quotation.xlsx và manifest đi kèm từ normalized.json:*
     ```bash
     python -m mep_quotation.cli.main export-excel data/suppliers/AUT/2026/2026-06-20_001
     ```
     *Tùy chọn ghi đè tệp Excel và manifest hiện hữu:*
     ```bash
     python -m mep_quotation.cli.main export-excel data/suppliers/AUT/2026/2026-06-20_001 --overwrite
     ```

 12. **Tạo Gói Báo Giá Mới (Khởi tạo package rỗng):**
     ```bash
     python -m mep_quotation.cli.main create-package --supplier AUT --date 2026-05-20
     ```

13. **Kiểm Tra Tính Hợp Lệ Của Gói:**
    ```bash
    python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-05-20_001
    ```

 14. **Ghi Nhận Chỉnh Sửa Dữ Liệu:**
      ```bash
      python -m mep_quotation.cli.main record-correction data/suppliers/AUT/2026/2026-05-20_001 --field "items[0].unit_price" --old 18500 --new 19200 --reason "Supplier revised quotation"
      ```

 15. **Xây Dựng Lại Chỉ Mục Vật Tư:**
      ```bash
      python -m mep_quotation.cli.main build-index
    
      # Hoặc chạy ở chế độ nghiêm ngặt (dừng và báo lỗi ngay khi có file normalized lỗi):
      python -m mep_quotation.cli.main build-index --strict
      ```

 16. **Tìm Kiếm Vật Tư:**
     ```bash
     python -m mep_quotation.cli.main search-material "CV-3X2.5"
     ```

## Hướng Dẫn Sử Dụng Giao Diện Rà Soát Báo Giá MEP (Local UI)

Hệ thống cung cấp một giao diện web cục bộ đơn giản giúp nhân sự MEP điều khiển quy trình xử lý và rà soát chất lượng dữ liệu báo giá một cách trực quan.

1. **Khởi chạy ứng dụng (Chỉ dành cho kỹ thuật viên setup):**
   ```bash
   python -m streamlit run tools/local_review_app.py --browser.gatherUsageStats false
   ```

2. **Mở giao diện trên trình duyệt:**
   Truy cập đường dẫn sau: [http://localhost:8501](http://localhost:8501)

3. **Quy trình làm việc 4 bước dành cho nhân viên báo giá:**
   * **Bước 1: Chọn báo giá**:
     * Chọn tải tệp PDF báo giá lên trực tiếp hoặc nhập đường dẫn file PDF trên máy.
     * Nhập thông số cơ bản: Mã nhà cung cấp, Ngày báo giá, Số thứ tự báo giá.
   * **Bước 2: Xử lý báo giá**:
     * Bấm nút **Xử lý báo giá** ở Sidebar. Hệ thống sẽ tự động phân tích và tạo bản nháp dữ liệu.
   * **Bước 3: Rà soát dữ liệu**:
     * Bảng dữ liệu nháp sẽ hiển thị. Bạn chọn từng dòng vật tư cần rà soát ở bộ chọn.
     * Đối chiếu với văn bản gốc hiển thị bên cạnh và đưa ra quyết định: **Chấp nhận**, **Từ chối** hoặc **Chỉnh sửa** (cho phép ghi đè mô tả, đơn vị, đơn giá, số lượng...).
     * Bấm nút **Lưu quyết định** để ghi nhận kết quả.
   * **Bước 4: Xuất kết quả**:
     * Khi đã rà soát xong ít nhất một dòng, bấm nút **Xuất Excel** ở chân trang.
     * Hệ thống tự động biên dịch, chuẩn hóa và chuẩn bị tệp Excel. Sau khi xuất thành công, nút **Tải file Excel báo giá** xuất hiện để bạn tải tệp Excel hoàn chỉnh về máy sử dụng.

*Lưu ý: Đối với lập trình viên hoặc khi cần sửa lỗi sâu, bạn có thể tích chọn **Hiển thị chế độ nâng cao** ở cuối Sidebar để mở khóa các tính năng kỹ thuật nâng cao (Ghi đè, Xem log chi tiết, Chạy từng bước đơn lẻ, Kiểm tra toàn vẹn).*

## Chạy Bộ Kiểm Thử (Tests)

Chạy tất cả các test cases bằng `pytest`:
```bash
pytest -v
```
