# Kế hoạch điều chỉnh Phase 5 – Sửa lỗi audit failure path

## Mô tả
Trong quá trình nghiệm thu Phase 5, phát hiện một số kiểm tra nghiệp vụ và validation nằm ngoài khối `try-except` của hàm `assemble_package_text()` trong tệp `assembly_service.py`. Nếu xảy ra lỗi ở các bước này (ví dụ: PDF bị mã hóa, thiếu tệp `raw_text.json`, hoặc vi phạm quy tắc cản ghi đè khi `overwrite=False`), hệ thống sẽ crash và ném lỗi ngay mà không ghi nhận sự kiện kiểm toán lỗi `text_assembly_failed`.

Bản sửa đổi này sẽ:
1. Đưa toàn bộ các khối kiểm duyệt validation sau khi nạp `package.json` vào trong khối `try`.
2. Bảo đảm mọi ngoại lệ ném ra trong luồng đều được ghi nhận sự kiện `text_assembly_failed` kèm chi tiết lỗi và cấp độ `"ERROR"`.
3. Bổ sung hoặc cập nhật các bài unit test để kiểm thử hành vi ghi log lỗi kiểm toán khi thiếu file hoặc trùng đè.

## Phạm vi (Scope Confirmation)
- Chỉ điều chỉnh luồng `assemble_package_text` trong `mep_quotation/text_assembly/assembly_service.py`.
- Chỉ cập nhật/thêm các test case trong `tests/test_text_assembly.py`.
- Cập nhật số lượng test thực tế trong các tệp tài liệu.
- Tuyệt đối không mở rộng scope, không OCR, không AI, không parser.

---

## Proposed Changes

### Component 1 – Text Assembly Service

#### [MODIFY] [assembly_service.py](file:///D:/mep_quotation_pipeline/mep_quotation/text_assembly/assembly_service.py)
- Di chuyển toàn bộ các đoạn check từ dòng 54 đến dòng 87 vào bên trong khối `try` (bắt đầu từ sau dòng 88 hiện tại).
- Cấu trúc mới:
  ```python
  def assemble_package_text(package_path: Path, overwrite: bool = False) -> Path:
      # load package.json ...
      try:
          # 2. Kiểm tra encrypted ...
          # 3. Kiểm tra file raw_text.json tồn tại ...
          # 4. Overwrite check ...
          # 5. Ghi log text_assembly_started ...
          # 6. Ghép văn bản ...
      except Exception as e:
          # Ghi log text_assembly_failed và re-raise
  ```

---

### Component 2 – Tests

#### [MODIFY] [test_text_assembly.py](file:///D:/mep_quotation_pipeline/tests/test_text_assembly.py)
Cập nhật hoặc viết thêm các test cases để kiểm tra sự tồn tại của sự kiện `text_assembly_failed` trong nhật ký log:
- Cập nhật `test_missing_raw_text_fail`: Ngoài kiểm tra ném lỗi `FileNotFoundError`, cần mở file log kiểm toán kiểm tra sự tồn tại của sự kiện `text_assembly_failed` chứa thông tin chi tiết lỗi.
- Cập nhật `test_overwrite_protection`: Kiểm tra khi vi phạm cản ghi đè (ném lỗi `ValueError`), tệp log kiểm toán ghi nhận sự kiện `text_assembly_failed`.
- Thêm `test_encrypted_package_assembly_fail` (nếu phù hợp): Nạp một package có PDF bị mã hóa (cờ `encrypted: true` trong `metadata.json`), chạy dịch vụ ghép văn bản → kiểm tra ném lỗi và ghi nhận sự kiện `text_assembly_failed`.

---

## Verification Plan

### Automated Tests
1. Sinh các JSON Schema:
   ```bash
   python scripts/generate_schemas.py
   ```
2. Chạy toàn bộ các bài kiểm thử unit tests:
   ```bash
   python -m pytest -v
   ```
Mục tiêu: Đạt **70 tests pass, 0 failed.**

### Manual Verification
1. Sử dụng một package thật đã qua Phase 4.
2. Tạo tình huống lỗi bằng cách xoá tệp `source/raw_text.json` và chạy lệnh:
   ```bash
   python -m mep_quotation.cli.main assemble-text data/suppliers/CADIVI/2026/2026-06-25_002
   ```
3. Mở file log kiểm toán `logs/processing.log.jsonl`, kiểm tra xem dòng log cuối cùng có ghi nhận sự kiện `text_assembly_failed` với level `"ERROR"` không.
