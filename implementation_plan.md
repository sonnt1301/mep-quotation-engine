# Implementation Plan - Phase 12 – Excel Export Layer / Human Deliverable Export

Phase 12 chịu trách nhiệm xuất dữ liệu báo giá chính thức đã chuẩn hóa từ `normalized/normalized.json` thành tệp Excel `exports/quotation.xlsx` phục vụ người dùng, đi kèm với tệp `exports/export_manifest.json` ghi nhận metadata xuất bản.

## Critical Scope Guard
- **Không thay đổi dữ liệu nguồn**: Tuyệt đối không chỉnh sửa các tệp `normalized.json`, `normalized_draft.json`, `review_decisions.json`, hay các tệp trung gian của các phase trước.
- **Không tự ý tính toán lại nghiệp vụ**: Giữ nguyên dữ liệu từ `normalized.json` (bao gồm `amount`), không tự ý normalize lại hay chạy tính toán logic ngoài dữ liệu đã có.
- **Không làm ngoài scope**: Không tích hợp OCR, AI/LLM, BOQ matching, cơ sở dữ liệu, API, giao diện web, gửi mail hay sử dụng LibreOffice để chuyển đổi trong code.

---

## Vị trí trong Pipeline
```
[Official Normalized JSON (normalized.json)]
       ↓ (Phase 12 - excel_export / openpyxl)
[exports/quotation.xlsx] + [exports/export_manifest.json]
```

---

## Các Thay Đổi Đề Xuất (Proposed Changes)

### Component 1 – Spec & Models

#### [MODIFY] [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)
- **Cập nhật `FilePathsModel`**: Bổ sung hai trường đường dẫn xuất bản Excel dạng Optional (tương thích ngược):
  ```python
  excel_export: Optional[str] = Field("exports/quotation.xlsx", description="Đường dẫn file Excel xuất bản, tương đối từ package root")
  excel_export_manifest: Optional[str] = Field("exports/export_manifest.json", description="Đường dẫn file manifest Excel xuất bản, tương đối từ package root")
  ```
- **Định nghĩa các models mới**:
  - `ExcelExportSheetModel`: Lưu thông tin từng sheet dữ liệu Excel.
    ```python
    class ExcelExportSheetModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        name: str = Field(..., description="Tên worksheet")
        row_count: int = Field(..., description="Số dòng dữ liệu (không tính header row)")
    ```
  - `ExcelExportContextModel`: Context trung gian dùng khi xây dựng workbook trước khi có file hash.
    ```python
    class ExcelExportContextModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        source_normalized_sha256: str = Field(..., description="SHA256 của tệp normalized.json")
        exported_at: datetime = Field(..., description="Thời điểm xuất bản")
        exporter_name: str = Field("openpyxl_excel_exporter", description="Tên bộ xuất bản")
        exporter_version: str = Field("1.0", description="Phiên bản bộ xuất bản")
    ```
  - `ExcelExportManifestModel`: Manifest ghi nhận metadata xuất bản Excel chính thức.
    ```python
    class ExcelExportManifestModel(BaseModel):
        model_config = ConfigDict(extra="forbid")
        schema_version: str = Field("1.0", description="Phiên bản schema export manifest")
        quotation_id: str = Field(..., description="ID báo giá gốc")
        supplier_code: Optional[str] = Field(None, description="Mã nhà cung cấp")
        quotation_date: Optional[str] = Field(None, description="Ngày báo giá")
        source_normalized: str = Field("normalized/normalized.json", description="Đường dẫn tương đối tới file normalized")
        source_normalized_sha256: str = Field(..., description="SHA256 của file normalized")
        export_file: str = Field("exports/quotation.xlsx", description="Đường dẫn tương đối tới file Excel xuất bản")
        export_file_sha256: str = Field(..., description="SHA256 của file Excel xuất bản")
        sheet_count: int = Field(..., description="Số lượng worksheets")
        sheets: List[ExcelExportSheetModel] = Field(..., description="Danh sách chi tiết sheets")
        exported_at: datetime = Field(..., description="Thời điểm xuất bản")
        exporter_name: str = Field("openpyxl_excel_exporter", description="Tên bộ xuất bản")
        exporter_version: str = Field("1.0", description="Phiên bản bộ xuất bản")
        warnings: List[ParserWarningModel] = Field(default_factory=list, description="Danh sách các cảnh báo")

        @field_serializer("exported_at")
        def serialize_exported_at(self, dt: datetime) -> str:
            return serialize_dt(dt)
    ```

#### [MODIFY] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
- Export thêm `ExcelExportSheetModel`, `ExcelExportContextModel`, và `ExcelExportManifestModel`.

---

### Component 2 – Excel Export Module (MỚI)

#### [NEW] [__init__.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/__init__.py)
- Export các hàm API: `build_excel_workbook`, `build_excel_export_manifest`, và `export_excel`.

#### [NEW] [workbook_builder.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/workbook_builder.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/workbook_builder.py)
Triển khai hàm dựng workbook thuần túy (pure function):
`build_excel_workbook(normalized: NormalizedQuotationModel, export_context: ExcelExportContextModel) -> openpyxl.Workbook`
- **Quy tắc chung**:
  - Không đọc/ghi file. Chỉ nhận dữ liệu đầu vào và trả về workbook `openpyxl`.
  - Không thay đổi (mutate) đối tượng `normalized`.
  - Format Header in đậm (Bold).
  - Tự động điều chỉnh độ rộng cột (Auto-width) dựa trên nội dung, có giới hạn độ rộng tối đa (`max_width = 60` ký tự cho cột text dài như `evidence_text` để giao diện trực quan).
  - **Chống Formula Injection (Bảo vệ công thức)**: Mọi ô Text field có giá trị bắt đầu bằng các ký tự `=`, `+`, `-`, `@` phải được escape bằng cách thêm ký tự nháy đơn `'` ở đầu (ví dụ: `cell.value = f"'{value}"`). Điều này không áp dụng cho trường số thực tế.
  - **Khử ký tự control XML Excel**: Viết hàm helper loại bỏ các ký tự điều khiển ASCII không hợp lệ (`ASCII < 32` ngoại trừ `\n`, `\r`, `\t`) để tránh gây lỗi hỏng tệp Excel.
- **Sheet 1: Summary**
  - Cột A: Field, Cột B: Value.
  - Ghi các trường thông số tổng quan: Quotation ID, Supplier Code, Quotation Date, Currency, Item Count, Source Normalized Path, Source Normalized SHA256, Exported At, Exporter Name, Exporter Version.
  - Nếu `normalized` có `export_summary`, ghi thêm các thông tin phân tích review (Draft Item Count, Approved Count, Edited Count, Rejected Count, Unreviewed Count, Exported Item Count).
  - Quy tắc Currency: Lấy từ `normalized.currency` nếu có. Nếu thiếu, lấy unique currency từ items (nếu tất cả item cùng currency). Nếu có nhiều currency khác nhau ghi `"MULTIPLE"`. Nếu hoàn toàn không có ghi ô trống.
- **Sheet 2: Items**
  - Chứa danh sách các vật tư xuất bản (giữ nguyên thứ tự, không sort, không lọc).
  - Các cột: `item_id`, `material_code`, `description`, `brand`, `unit`, `quantity`, `unit_price`, `currency`, `amount`, `page_number`, `confidence`, `reviewer`, `source_draft_item_id`, `source_review_decision_id`, `warnings`.
  - Định dạng ô: Các trường số (`quantity`, `unit_price`, `amount`, `confidence`) ghi dưới dạng numeric của Excel, không dùng string. Các trường null ghi ô trống.
  - warnings: nối danh sách warning thành chuỗi `"[code] message; [code2] message2"`. Nếu chỉ có code ghi `[code]`, chỉ có message ghi `message`.
  - Bật tính năng Freeze panes cho dòng Header đầu tiên (`ws.freeze_panes = "A2"`).
  - Bật Auto filter cho toàn bộ bảng.
- **Sheet 3: Warnings**
  - Gom các cảnh báo cấp file và cấp item.
  - Các cột: `level`, `item_id`, `code`, `message`.
  - Cấp file ghi `level = "file"`, `item_id = ""`. Cấp item ghi `level = "item"`, `item_id = item.item_id`.
  - Nếu không có warning, vẫn tạo sheet Warnings chỉ có header và 0 dòng dữ liệu.
- **Sheet 4: Trace**
  - Chứa dữ liệu truy vết.
  - Các cột: `item_id`, `source_draft_item_id`, `source_review_decision_id`, `page_number`, `evidence_text`.

#### [NEW] [export_manifest.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/export_manifest.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/export_manifest.py)
Triển khai hàm dựng manifest:
`build_excel_export_manifest(package_path: Path, normalized_path: Path, export_path: Path, workbook_sheet_info: List[ExcelExportSheetModel], export_context: ExcelExportContextModel) -> ExcelExportManifestModel`
- Đọc `supplier_code` và `quotation_date` từ `normalized.json` nếu có, nếu thiếu lấy từ `package.json` nếu có, nếu không có để `None`. Không tự parse từ ID, không đọc `normalized_draft.json` hay `review_decisions.json`.
- `source_normalized_sha256` lấy từ context.
- `export_file_sha256` tính từ file Excel sau khi được ghi thành công.

#### [NEW] [export_service.py (D:/mep_quotation_pipeline/mep_quotation/excel_export/export_service.py)](file:///D:/mep_quotation_pipeline/mep_quotation/excel_export/export_service.py)
Triển khai logic điều phối:
`export_excel(package_path: Path, overwrite: bool = False) -> Path`
- Kiểm định chéo: nạp `normalized.json`, đối chiếu `normalized.item_count` khớp `len(normalized.items)` (nếu không khớp -> fail rõ ràng).
- Kiểm tra tồn tại file: Nếu `overwrite=False` và một trong hai file `quotation.xlsx` hoặc `export_manifest.json` đã tồn tại $\rightarrow$ fail rõ ràng.
- Ghi tệp tin Excel bằng **Atomic Write**: ghi ra file tạm trong thư mục `exports/` rồi replace sang `quotation.xlsx`.
- **Validation Workbook sau khi ghi**: Load lại `quotation.xlsx` bằng `openpyxl.load_workbook` để kiểm tra độ tin cậy:
  - File mở thành công.
  - Đầy đủ 4 worksheets với tên và thứ tự chính xác.
  - Số lượng dòng data ở sheet `Items` và sheet `Trace` khớp chuẩn xác với `item_count`.
- Tính `export_file_sha256` của file Excel vừa ghi thành công.
- Build và ghi tệp `export_manifest.json` bằng **Atomic Write** (file tạm rồi replace), sau đó validate bằng `ExcelExportManifestModel`.
- Cập nhật package.json (`files.excel_export` và `files.excel_export_manifest`).
- Ghi nhận Audit logs đầy đủ: `excel_export_started`, `excel_workbook_built`, `excel_workbook_written`, `excel_workbook_validated`, `excel_export_manifest_written`, `excel_export_completed` / `excel_export_failed`.

---

### Component 3 – Package Integrity

#### [MODIFY] [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
- Cập nhật hàm `validate_package_integrity` thực hiện kiểm định sâu bổ sung cho tệp manifest Excel nếu tệp `exports/export_manifest.json` tồn tại:
  - Validate manifest bằng `ExcelExportManifestModel`.
  - Khớp `source_normalized_sha256` với SHA256 thực tế của `normalized.json`.
  - Khớp `export_file_sha256` with SHA256 thực tế của `exports/quotation.xlsx`.
  - Khớp `sheet_count` và tên sheets: `Summary`, `Items`, `Warnings`, `Trace`.
  - Giữ tính tương thích ngược hoàn toàn (không bắt buộc các package cũ phải có manifest Excel).

---

### Component 4 – CLI Integration & Pyproject

#### [MODIFY] [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
- Đăng ký subcommand mới:
  `export-excel <package_path> [--overwrite]`
- In ra báo cáo tóm tắt xuất bản Excel.

#### [MODIFY] [pyproject.toml (D:/mep_quotation_pipeline/pyproject.toml)](file:///D:/mep_quotation_pipeline/pyproject.toml)
- Thêm `"openpyxl>=3.1.0"` vào `dependencies`.

---

### Component 5 – Schema Generation & Tests

#### [NEW] [tests/test_excel_export.py (D:/mep_quotation_pipeline/tests/test_excel_export.py)](file:///D:/mep_quotation_pipeline/tests/test_excel_export.py)
Tạo suite kiểm thử bao phủ toàn bộ:
- Export thành công tạo ra tệp Excel và manifest hợp lệ.
- Kiểm tra workbook có đúng 4 sheet, đúng thứ tự và đúng tên.
- Dòng dữ liệu Items sheet khớp và giữ đúng thứ tự.
- Định dạng numeric cho các cột số, blank cell cho null field.
- Warnings sheet ghi đúng định dạng file-level và item-level, vẫn có header khi không có warning.
- Trace sheet lưu evidence_text và được lọc sạch các ký tự điều khiển Excel-illegal.
- Kiểm thử cản ghi đè khi `overwrite=False` và ghi đè hoàn toàn khi `overwrite=True` mà không merge.
- Chống formula injection hoạt động chuẩn xác (escape các ô text bắt đầu bằng `=`, `+`, `-`, `@`).
- validate_package_integrity hoạt động chuẩn chỉ sau export.
- Các lỗi về mismatch item_count, invalid normalized.json, hay lỗi load workbook đều khiến export thất bại rõ ràng.
- Ghi nhận đầy đủ các audit events.

---

## Kế Hoạch Xác Thực (Verification Plan)

### Automated Tests
1. Cài đặt dependency `openpyxl` bằng pip.
2. Chạy sinh schemas mới:
   ```bash
   python scripts/generate_schemas.py
   ```
3. Chạy toàn bộ pytest suite:
   ```bash
   python -m pytest -v
   ```

### Manual Verification
1. Chạy xuất bản Excel trên gói AUT thực tế:
   ```bash
   python -m mep_quotation.cli.main export-excel data/suppliers/AUT/2026/2026-06-20_001 --overwrite
   ```
2. Chạy kiểm duyệt package chéo:
   ```bash
   python -m mep_quotation.cli.main validate-package data/suppliers/AUT/2026/2026-06-20_001
   ```
3. Mở tệp `data/suppliers/AUT/2026/2026-06-20_001/exports/quotation.xlsx` bằng phần mềm Excel hoặc LibreOffice, rà soát dữ liệu hiển thị và định dạng các sheet.
