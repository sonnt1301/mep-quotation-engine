# Báo Cáo Nghiệm Thu Phase 11 – Official Normalized Export Layer

Báo cáo tóm tắt quá trình triển khai, kết quả chạy kiểm thử tự động và thủ công cho Phase 11.

## Kết quả đạt được

1. **Ràng buộc Schema Thắt Chặt (Model-level Enforcement)**:
   - Cập nhật mô hình `NormalizedItemModel` trong [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) để thắt chặt kiểm định bắt buộc các trường `item_id`, `source_draft_item_id`, `source_review_decision_id`, `description` (phi-rỗng), `unit_price`, và `currency` ở cấp độ Pydantic.
   - Thêm model thống kê [ExportSummaryModel (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) để kiểm soát thống kê kết quả xuất bản.
   - Mở rộng [NormalizedQuotationModel (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) để thắt chặt các trường manifest, source hashes, summary, items, warnings, created_at, updated_at thành **required** ở cả cấp độ Pydantic model-level và JSON Schema (thông qua cấu hình `json_schema_extra` và cung cấp default value tương thích ngược).
   - Bảo đảm khả năng tương thích ngược hoàn hảo với các package rỗng của Phase trước (khi items rỗng hoặc load tệp tin kiểu cũ).

2. **Xử Lý Nghiệp Vụ Xuất Bản (exporter.py)**:
   - Lọc và sắp xếp vật tư theo đúng thứ tự xuất hiện của draft items trong `normalized_draft.json`.
   - Chỉ xuất bản các item có trạng thái rà soát là `approved` hoặc `edited`. Bỏ qua các item `rejected` hoặc chưa được review.
   - Áp dụng đè giá trị đối với quyết định `edited` (giữ nguyên giá trị gốc nếu trường override là null, không xóa trường).
   - Thiết lập `item_id` tuần tự tăng dần: `{QUOTATION_ID}_ITEM_{SEQ:04d}` (bắt đầu từ 0001).
   - **Legacy Fields Protection**: Không tự ý gán category hay vat_rate nếu không có nguồn dữ liệu chính thức (gán bằng `None` thay vì gán cứng `"electrical"` hay `0.1`). Trường `material_name` được gán bằng `description` và được note rõ ràng bằng comment chỉ dùng cho tương thích ngược.
   - **Amount Rule**: Tự động tính lại `amount = quantity * unit_price` khi có đủ dữ liệu, ghi nhận cảnh báo `amount_recomputed_from_quantity_and_unit_price` nếu có sự chênh lệch.
   - **Currency Rule**: Chuẩn hóa chữ in hoa (uppercase). Kế thừa quotation-level currency và ghi nhận cảnh báo `currency_inherited_from_quotation` nếu item-level bị null. Dừng báo lỗi nếu thiếu cả hai currency hoặc currency không thuộc whitelist VND/USD.

3. **Điều Phối Dịch Vụ & Atomic Write (export_service.py)**:
   - Tích hợp kiểm định chéo: Gọi hàm validate review decisions kiểm tra chữ ký băm `source_sha256` của `normalized_draft.json` để ngăn dữ liệu lỗi.
   - Thực thi cơ chế ghi tệp tin an toàn (Atomic Write): Ghi ra tệp tạm `.tmp` trong thư mục `normalized/` rồi đổi tên nguyên tử (`os.replace`) để tránh hỏng tệp tin đích.
   - Cập nhật tự động đường dẫn `normalized_json` vào `package.json`.

4. **Kiểm Định Chéo Toàn Gói Sâu (Integrity Validation)**:
   - Cập nhật hàm `validate_package_integrity` tại [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py) thực thi kiểm định sâu đối với tệp `normalized.json` chính thức (kiểm tra IDs, hashes, counts, amount recompute và cấm item rejected/unreviewed).
   - Chỉ thực hiện kiểm tra chéo băm khi tệp tin nguồn tồn tại trên đĩa và trường băm phi-rỗng để tương thích ngược hoàn hảo với package rỗng ban đầu.

5. **CLI Integration**:
   - Tích hợp thành công subcommand CLI `export-normalized` tại [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py).

6. **Tự động sinh Schema**:
   - Sinh thành công tệp JSON Schema đồng bộ và thắt chặt hoàn toàn: [normalized.schema.json (D:/mep_quotation_pipeline/schemas/normalized.schema.json)](file:///D:/mep_quotation_pipeline/schemas/normalized.schema.json).

7. **Bộ Kiểm Thử Hoàn Chỉnh**:
   - Xây dựng mới tệp kiểm thử [test_normalized_export.py (D:/mep_quotation_pipeline/tests/test_normalized_export.py)](file:///D:/mep_quotation_pipeline/tests/test_normalized_export.py).
   - Vượt qua toàn bộ **131/131 tests** tự động của toàn bộ hệ thống (đạt 100% passed).

---

## Xác nhận kiểm thử tự động (Pytest)
```bash
python -m pytest -v
```
Kết quả thực tế:
```text
tests/test_normalized_export.py::test_export_normalized_success PASSED
tests/test_normalized_export.py::test_export_no_approved_or_edited_items PASSED
tests/test_normalized_export.py::test_export_required_field_missing_description PASSED
tests/test_normalized_export.py::test_export_currency_inheritance_and_validation PASSED
tests/test_normalized_export.py::test_export_amount_recompute_and_warning PASSED
tests/test_normalized_export.py::test_export_overwrite_check PASSED
tests/test_normalized_export.py::test_cli_export_normalized PASSED

============================= 131 passed in 8.98s =============================
```

---

## Kiểm thử thủ công trên gói thực tế
Chạy kiểm duyệt trên gói `data/suppliers/AUT/2026/2026-06-20_001`:
1. **Xuất bản tệp báo giá chính thức**:
   ```bash
   python -m mep_quotation.cli.main export-normalized data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
   *Kết quả in*:
   ```text
   Successfully exported official normalized quotation.
     Quotation ID          : AUT_20260620_001
     Supplier Code         : AUT
     Quotation Date        : 2026-06-20
     Exported Item Count   : 1
     Draft Item Count      : 287
     Approved Count        : 0
     Edited Count          : 1
     Rejected Count        : 0
     Unreviewed Count      : 286
     Warnings Count        : 0
     Normalized JSON Path  : data/suppliers/AUT/2026/2026-06-20_001/normalized/normalized.json
   ```

2. **Xác thực toàn vẹn gói**:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
   *Kết quả in*:
   ```text
   Package is valid.
     Quotation ID : AUT_20260620_001
     Supplier     : AUT
     Items Count  : 1
     Corrections  : 0
   ```

3. **Nhật ký Audit Log (logs/processing.log.jsonl)**:
   ```json
   {"details": {"overwrite": true}, "event": "normalized_export_started", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T04:26:53Z"}
   {"details": {"exported_item_count": 1}, "event": "normalized_export_built", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T04:26:54Z"}
   {"details": {"export_path": "normalized/normalized.json"}, "event": "normalized_export_written", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T04:26:54Z"}
   {"details": {"export_summary": {"approved_count": 0, "draft_item_count": 287, "edited_count": 1, "exported_item_count": 1, "rejected_count": 0, "unreviewed_count": 286}}, "event": "normalized_export_completed", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T04:26:55Z"}
   {"details": {"status": "valid"}, "event": "package_validated", "level": "INFO", "quotation_id": "AUT_20260620_001", "timestamp": "2026-07-02T04:26:59Z"}
   ```
   Toàn bộ tiến trình diễn ra suôn sẻ, tuyệt đối không có tệp tin nguồn của các Phase trước bị thay đổi.
