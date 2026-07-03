# Batch Technical Notes - Chint / KDE

## Batch Info

- Batch name: Chint / KDE
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\Chint`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `Bang gia  KDE 2024 ck 35%.pdf` | PDF | 3,604,491 bytes | Native text layer exists. 22 pages. Table extraction works well; KDE price list, not necessarily Chint. |
| `Bảng giá Chint 1-3-2023 ck 50.pdf` | PDF | 905,437 bytes | Native text layer exists. 12 pages. Matrix/cross-tab style price list. |
| `Bang-gia-Thiet-bi-dien-CHINT-2021.pdf` | PDF | 10,508,686 bytes | Very low usable extracted text; likely encoded/visual PDF. Table extraction poor. |
| `Notice on Price Adjustment_Vietnam_2026.pdf` | PDF | 234,661 bytes | Native text layer exists. 4 pages. Price adjustment notice, not item price list. |
| `2024 New Price - REV2 - to Sales.xlsx` | XLSX | 308,162 bytes | Clean one-sheet Chint 2024 price list. |
| `CHINT Prise list 20.04.2025 GỬI KINH DOANH.xlsx` | XLSX | 449,497 bytes | Clean Chint 2025 price list workbook. Main sheet: `Prise list 2025`. |
| `~$CHINT Prise list 20.04.2025 GỬI KINH DOANH.xlsx` | XLSX temp | 165 bytes | Excel temporary lock file. Should be ignored/flagged abnormal. |

## Important Priority Rule

Do not prioritize sources by file type alone.

- Business priority should come from effective date, issue date, received date, or explicit user selection.
- Technical confidence describes extraction reliability only.
- A newer PDF notice or price list may have higher business priority than an older Excel file, but may not be directly extractable as item prices.

For this batch:

- `CHINT Prise list 20.04.2025...xlsx` is technically clean and likely a strong 2025 item price source.
- `Notice on Price Adjustment_Vietnam_2026.pdf` is newer but is an adjustment notice, not a direct item price list. It should not replace a price list unless a later phase applies adjustment rules explicitly.

## Clean Excel Price Lists

### File: 2024 New Price - REV2 - to Sales.xlsx

- Sheet count: 1
- Sheet: `2024 CEV price `
- Dimensions observed: 5090 rows x 9 columns
- Header row observed: row 2
- Data begins: row 3
- Formula columns detected.

Observed header fields:

```text
Product Line
SKU Code
Model Description(EN)
2024 List Price (with VAT)
Qty/CTN
2024 List Price (without VAT)
CKTC
```

Representative row:

```text
Product Line: ACB
SKU Code: 937048
Model Description(EN): NA1-1000X-630M/3P MO-WD AC220/230 TP
2024 List Price (with VAT): 87832800
Qty/CTN: 1
2024 List Price (without VAT): formula/value D3/1.1
CKTC: 0.605
Net/derived price: formula/value F3*(1-G3)
```

### File: CHINT Prise list 20.04.2025 GỬI KINH DOANH.xlsx

- Sheet count: 2
- Sheets:
  - `Kangatang` empty/placeholder
  - `Prise list 2025`
- Main sheet: `Prise list 2025`
- Dimensions observed: 8041 rows x 11 columns
- Header row observed: row 2
- Data begins: row 3
- Formula columns detected.

Observed header fields:

```text
Product Line
SKU Code
Model Description(EN)
2025 List Price (with VAT)
Qty/CTN
2025 List Price (without VAT)
CKTC
ĐƠN GIÁ
```

Representative row:

```text
Product Line: MCB
SKU Code: 814008
Model Description(EN): NXB-63 1P C1 6kA
2025 List Price (with VAT): 132000
Qty/CTN: 180
2025 List Price (without VAT): 120000
CKTC: 0.52
ĐƠN GIÁ: formula/value F3*(1-G3)
```

Recommended profile id:

```text
chint_excel_price_list
```

Suggested mapping:

| Target candidate field | Source column |
|---|---|
| `product_line` | `Product Line` |
| `material_code` | `SKU Code` |
| `description` | `Model Description(EN)` |
| `list_price_with_vat_candidate` | `2024/2025 List Price (with VAT)` |
| `list_price_without_vat_candidate` | `2024/2025 List Price (without VAT)` |
| `discount_rate_candidate` | `CKTC` |
| `unit_price_candidate` | `ĐƠN GIÁ` if present / formula-derived |
| `qty_per_carton_candidate` | `Qty/CTN` |
| `currency` | VND, derived from context/header if confirmed |

Guardrails:

- `SKU Code` may be numeric. Preserve it as identifier/text, not numeric quantity.
- Do not decide whether official unit price is with VAT, without VAT, or discounted `ĐƠN GIÁ` unless business rule confirms.
- Preserve all price candidates separately.
- Formula-derived values should be marked as formula/cached-value source.
- Ignore Excel temp lock file beginning with `~$` or very small abnormal workbook.

## PDF: KDE 2024 Price List

### File

`Bang gia  KDE 2024 ck 35%.pdf`

### Structure

- Page count: 22
- Native text layer: yes
- Extracted text characters: approximately 21,597
- Metadata title: `Báo giá - KD3.cdr`
- `pdfplumber.extract_tables()` finds representative tables successfully.

Representative table:

```text
BẢNG GIÁ THIẾT BỊ ĐIỆN NHÃN HIỆU KDE (áp dụng từ tháng 6 năm 2024)
Hình Ảnh | Mã Hàng | Thông Số Kỹ Thuật | Giá list đã có VAT (10%) | Xuất xứ
ĐỒNG HỒ KIM
KDE-96AM-1 (96x96) | technical description | 184,000 | Trung Quốc
KDE-96 (96x96) | technical description | 244,000 | Việt Nam
```

Recommended profile id:

```text
kde_pdf_table_price_list
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | `Mã Hàng` |
| `description` / `technical_spec` | `Thông Số Kỹ Thuật` |
| `list_price_with_vat_candidate` | `Giá list đã có VAT (10%)` |
| `origin_country_candidate` | `Xuất xứ` |
| `product_group` | section row such as `ĐỒNG HỒ KIM` |
| `currency` | VND inferred from context if confirmed |

Guardrails:

- This appears to be KDE, not Chint, even though it is stored in Chint folder.
- Do not use folder name as supplier/manufacturer truth.
- Product group rows should become context, not item rows.

## PDF: Chint 2023 Matrix Price List

### File

`Bảng giá Chint 1-3-2023 ck 50.pdf`

### Structure

- Page count: 12
- Native text layer: yes
- Extracted text characters: approximately 12,942
- Contains both matrix/cross-tab price sections and line-style product sections.

Representative matrix table:

```text
MCB 1-63A
NXB-63
Icu (A)
1P | 2P | 3P | 4P
6000 | 50,000 | 100,000 | 140,000 | ...
```

Representative line-style section:

```text
BỘ KHỞI ĐỘNG MỀM NJR2
Động cơ (KW)
Iđm (A)
Mã
Đơn giá
7,5/11/15KW
15/22/29A
NJR2-7,5D/11D/15D 16,800,000
```

Recommended profile id:

```text
chint_pdf_matrix_and_line_price_list
```

Guardrails:

- Matrix sections require cross-tab expansion. One row/column intersection can represent an item/price.
- Do not parse `Icu`, `Iđm`, `KW`, `A`, `P` values as prices.
- A single table may produce many item candidates by combining model family + pole/count + rating + price.
- Some rows contain code and price on same line; others split across lines.

## PDF: CHINT 2021 Encoded/Visual PDF

### File

`Bang-gia-Thiet-bi-dien-CHINT-2021.pdf`

### Structure

- Page count: 52
- Extracted text characters: only approximately 1,247
- Text layer technically exists but appears mostly encoded/garbled.
- Representative extraction contains broken glyph-like text such as:

```text
3UJ[RGX */4 8GOR 6XUJ[IZY
7UDQJ ...
```

Finding:

- Treat as low-quality/garbled text PDF.
- May require OCR or visual/layout extraction later.
- Do not attempt item extraction from raw text in Phase 14.

Recommended classification:

```text
pdf_text_garbled_or_ocr_required
```

## PDF: 2026 Price Adjustment Notice

### File

`Notice on Price Adjustment_Vietnam_2026.pdf`

### Structure

- Page count: 4
- Native text layer: yes
- Extracted text characters: approximately 6,958
- Contains adjustment percentages by product category/series.
- `pdfplumber` detects a table with columns like product category, subcategory, series, adjustment range.

Representative data:

```text
ACB | NXA, NA8 and others | +11.0%
MCCB | NXM, NXMS, NM8N | +11.0%
MCB | NXB, NB1, NBP and others | +12.0%
Relay | JZX-22F, NXJ, XJ3, JSZ... | +15.5%
```

Recommended profile id:

```text
chint_price_adjustment_notice
```

Role:

- Business-effective adjustment notice.
- Not an item-level price list.
- Should not generate item candidates directly in Phase 14/15.
- May be used later to adjust an older price list if user/business rule explicitly selects it.

Guardrails:

- Newer date does not automatically mean direct item source.
- It may have high business relevance but low direct item-extraction role.
- Do not apply percentages automatically to existing prices without explicit workflow and audit trail.

## Data Contract / Phase Design Implications

This batch strongly reinforces the need to separate:

```text
business_priority / effective date / user selection
from
technical_confidence / extraction readiness
```

Also reinforces need for `source_role` beyond `source_type`:

```text
price_list
price_adjustment_notice
catalog_reference
pdf_text_garbled_or_ocr_required
excel_temp_lock_file
```

For Phase 14:

- Detect and ignore/flag Excel temp lock files (`~$...xlsx`, tiny size).
- Capture candidate effective date from filename/title when possible, but do not rely on it as final truth.
- Profile both source type and source role.
- Keep price candidates separate if workbook contains with-VAT, without-VAT, discount, and formula-derived unit price.

## Recommended Profile Signals

### chint_excel_price_list

```text
Product Line
SKU Code
Model Description(EN)
List Price (with VAT)
List Price (without VAT)
Qty/CTN
CKTC
ĐƠN GIÁ
2024 NEW PRICE LIST
2025 PRICE LIST
```

### kde_pdf_table_price_list

```text
BẢNG GIÁ THIẾT BỊ ĐIỆN NHÃN HIỆU KDE
Mã Hàng
Thông Số Kỹ Thuật
Giá list đã có VAT (10%)
Xuất xứ
```

### chint_pdf_matrix_and_line_price_list

```text
NXB-63
MCB 1-63A
Icu (A)
1P
2P
3P
4P
Đơn giá
NJR2
```

### chint_price_adjustment_notice

```text
Notice on Price Adjustment
Adjustment Range
+11.0%
+12.0%
+15.5%
```

### pdf_text_garbled_or_ocr_required

```text
very low usable extracted text
broken/garbled glyphs
no reliable table extraction
```

## Risks / Guardrails

- Folder name is not reliable supplier/manufacturer truth. KDE file is in Chint folder.
- Business recency is not the same as direct item price list usability.
- Adjustment notice must not be auto-applied to item prices without explicit user/business workflow.
- Numeric identifiers such as SKU Code must be preserved as text.
- With-VAT, without-VAT, discount, and formula-derived price should be preserved separately until business rule selects official price.
- Matrix PDF tables need dedicated cross-tab expansion rules.
- Garbled text PDFs should be flagged and deferred to OCR/visual extraction.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Add `source_role` values: `price_list`, `price_adjustment_notice`, `catalog_reference`, `excel_temp_lock_file`, `pdf_text_garbled_or_ocr_required`.
- Add fields for multiple price candidates rather than one forced `unit_price` during profiling.
- Add warning codes:
  - `excel_temp_lock_file`
  - `price_adjustment_notice_not_item_source`
  - `business_priority_requires_user_confirmation`
  - `pdf_text_garbled`
  - `matrix_table_requires_cross_tab_profile`
  - `folder_name_not_supplier_truth`
  - `multiple_price_candidates`
- Phase 14 should not apply price adjustment notices automatically.
