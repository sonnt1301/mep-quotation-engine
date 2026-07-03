# Batch Technical Notes - Schneider Electric

## Batch Info

- Batch name: Schneider Electric
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\Bảng giá Schneider`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `[SMALL SIZE] BANG GIA DAI LY 2026 áp dụng 13.3.pdf` | PDF | 26,798,370 bytes | Native text layer exists. 60 pages. Price list PDF, but layout is column/visual-table oriented and not extracted cleanly by default table extraction. |
| `2023 VN Pricelist effective 12 Jan 2023 REV.xlsx` | XLSX | 493,335 bytes | Clean one-sheet official price list. Good primary source. |
| `HỆ SỐ PNB 2025.xlsx` | XLSX | 12,508 bytes | Discount/coefficient table by product group. Auxiliary source, not item price list. |
| `Quản lý nhập - xuất - tồn T1 - HàngSchneider.xlsx` | XLSX | 35,124 bytes | Inventory/material tracking workbook. Not a supplier price list. |

## Overall Finding

Schneider batch contains one clean Excel price list, one PDF price list, and two auxiliary/non-price-list workbooks.

Recommended extraction priority:

1. Official Excel price list if available.
2. PDF price list only with a dedicated Schneider PDF profile.
3. PNB coefficient workbook as auxiliary discount/coefficient metadata, not as item price source.
4. Inventory workbook should be excluded from quotation-price extraction.

## Clean Excel Price List

### File

`2023 VN Pricelist effective 12 Jan 2023 REV.xlsx`

### Structure

- Sheet count: 1
- Sheet: `2023`
- Dimensions observed: 6741 rows x 9 columns
- Header row observed: row 2
- Data begins: row 3
- Formula sample detected in comparison column `Chênh lệch`.

Observed header fields:

```text
Reference
Description
2023 Unit Price List [VND with VAT]
PMs in charge
Product Group Description
Old MPG
Note
2022 Unit Price List [VND with VAT]
Chênh lệch
```

Representative rows:

```text
Reference: 28900
Description: NON-AUTOMATIC MOLDED CASE SWITCH 690V
2023 Unit Price List [VND with VAT]: 2293500
PMs in charge: Truc
Product Group Description: 4.3 CCB Optimum
Old MPG: 4.3 CCB Optimum
2022 Unit Price List [VND with VAT]: 2161500
Chênh lệch: 0.06106870229007644
```

```text
Reference: 28901
Description: INS40 4P 40A - SWITCH DISCONNECTOR
2023 Unit Price List [VND with VAT]: 2832500
Product Group Description: 4.3 CCB Optimum
```

Recommended profile id:

```text
schneider_excel_price_list
```

Suggested mapping:

| Target candidate field | Source column |
|---|---|
| `material_code` | `Reference` |
| `description` | `Description` |
| `unit_price` | `2023 Unit Price List [VND with VAT]` |
| `currency` | constant `VND`, derived from header |
| `vat_included_candidate` | true, derived from `with VAT` in header |
| `product_group` | `Product Group Description` |
| `old_product_group` | `Old MPG` |
| `pm_in_charge` | `PMs in charge` |
| `remark` | `Note` |
| `previous_unit_price_candidate` | `2022 Unit Price List [VND with VAT]` |
| `price_change_ratio_candidate` | `Chênh lệch` |

Guardrails:

- `Reference` may be numeric. Preserve as identifier/string in candidate output, not numeric quantity.
- Do not treat `Chênh lệch` as discount or final price. It is a comparison/change ratio.
- Header row should be detected dynamically using `Reference`, `Description`, and `Unit Price List` markers; do not hard-code row 2.
- Since the price header says `with VAT`, preserve `vat_included_candidate=true` but do not normalize tax policy yet.

## Auxiliary Coefficient Workbook

### File

`HỆ SỐ PNB 2025.xlsx`

### Structure

- Sheet count: 1
- Sheet: `Sheet1`
- Dimensions observed: 44 rows x 6 columns
- Main title row: row 1
- Header row observed: row 2
- Data begins: row 4

Observed title:

```text
Hệ số SE PNB -2025
(Áp dụng chung cho mọi thời điểm đặt hàng trong năm 2025)
(Với các sản phẩm tồn kho có thể có giá tốt hơn)
```

Observed header fields:

```text
Collection
Sub-collection
Product Group Description
HSCB
```

Representative rows:

```text
Collection: 1. General Purpose
Sub-collection: 1- Residential
Product Group Description: 1.1 FD Easy9
HSCB: 0.54
```

```text
Product Group Description: 2.2 MCCB EASYPACT UP TO 250A AND ACCESSORIES
HSCB: 0.46
```

Recommended profile id:

```text
schneider_pnb_coefficient_table
```

Role:

- Auxiliary coefficient/discount source.
- Not a quotation item price list.
- Should not generate item candidates directly.
- May be useful later for discount/net price workflows.

Guardrails:

- Do not merge this into official unit price without a business rule.
- Do not treat `HSCB` as VAT or exchange rate.
- Phase 14 should classify it as auxiliary/coefficient table.

## Inventory / Internal Tracking Workbook

### File

`Quản lý nhập - xuất - tồn T1 - HàngSchneider.xlsx`

### Structure

- Sheet count: 2
- Sheets:
  - `Tong hop  `
  - `Du_lieu_ma_vat_tu`

`Tong hop` is an inventory movement/tracking sheet with formulas.

`Du_lieu_ma_vat_tu` contains internal material master-like data:

```text
Mã Vật tư
Tên Vật tư
Đơn vị
```

Representative rows:

```text
VT01 | MCCB 3P 125A 25kA | Cái | 6
VT02 | MCB 3P 50A 6kA | Cái | 31
VT03 | MCB 3P 40A 10kA | Cái | 1
```

Recommended classification:

```text
internal_inventory_or_material_master
```

Role:

- Not a supplier price list.
- Should not be used to generate quotation item candidates.
- Could be useful later for internal material code mapping, but it is outside Phase 14 price-source scope.

Guardrails:

- Do not confuse internal material code `VT01`, `VT02`, etc. with supplier material code.
- Do not use stock/inventory quantity as quotation quantity.
- Do not treat this file as a supplier quotation source.

## PDF Price List Findings

### File

`[SMALL SIZE] BANG GIA DAI LY 2026 áp dụng 13.3.pdf`

### Structure

- Page count: 60
- Native text layer: yes
- Total extracted text characters: approximately 67,066
- Metadata title observed: `BANG GIA DAI LY TRANG 1-20 Bleed - xfont`
- Default pdfplumber table extraction did not produce good structured tables in the first 12 pages.

Representative text pattern from page 39:

```text
EZC100N1015
EZC100N1016
EZC100N1020
EZC100N1025
...
EZC100H2100
2.679.600
2.679.600
2.679.600
...
EZC100H1015
EZC100H1016
...
1.520.200
1.520.200
```

Finding:

- The PDF text layer exists, but text order groups codes and prices in separate blocks.
- A naive line-based parser can mismatch codes and prices.
- This requires a dedicated Schneider PDF layout profile using page layout/coordinates, not just raw text order.

Recommended profile id for later:

```text
schneider_pdf_price_list_layout
```

Guardrails:

- Do not pair codes and prices purely by text sequence unless layout evidence confirms alignment.
- Do not treat all numeric blocks as prices; technical ratings may exist elsewhere.
- If Excel price list exists, prefer Excel over PDF.

## Data Contract / Phase Design Implications

This batch supports Phase 14 multi-source profiling with file role classification, not just file type detection.

Required classifications:

```text
price_list
auxiliary_coefficient_table
internal_inventory_or_material_master
catalog_or_pdf_reference
unsupported_or_ocr_required
```

For Phase 14:

- Detect source type: PDF/XLSX.
- Detect source role:
  - official price list
  - auxiliary coefficient table
  - inventory/material master
  - PDF price list requiring profile
- For Excel:
  - sheet list
  - dimensions
  - candidate header rows
  - header signals
  - formula presence
  - likely role/profile id
- For PDF:
  - page count
  - text layer flag
  - extracted text char count
  - table extraction quality signal if possible
  - warning when text order is not enough for safe extraction

## Recommended Profile Signals

### schneider_excel_price_list

```text
Reference
Description
Unit Price List
VND with VAT
Product Group Description
Old MPG
```

### schneider_pnb_coefficient_table

```text
Hệ số SE PNB
Collection
Sub-collection
Product Group Description
HSCB
```

### internal_inventory_or_material_master

```text
QUẢN LÝ XUẤT NHẬP VẬT TƯ
Mã Vật tư
Tên Vật tư
Đơn vị
Du_lieu_ma_vat_tu
```

### schneider_pdf_price_list_layout

```text
BANG GIA DAI LY
EZC100
Schneider price blocks
native text layer exists
```

## Risks / Guardrails

- Schneider batch contains both official price sources and non-price auxiliary/internal files.
- File role detection is necessary; extension alone is not enough.
- PDF has text but raw order is not reliable for item/price pairing.
- Excel `Reference` can be numeric; preserve as text identifier.
- Price list may include VAT; preserve VAT inclusion metadata but do not normalize tax rules yet.
- PNB coefficient table should not generate item candidates.
- Internal inventory workbook should not generate supplier item candidates.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Phase 14 source profiling should include `source_role`, not only `source_type`.
- Add roles: `price_list`, `auxiliary_coefficient_table`, `inventory_or_material_master`, `catalog_reference`, `ocr_required`, `unknown`.
- Add warnings such as `text_order_not_table_safe`, `auxiliary_not_price_source`, `internal_inventory_file`, `numeric_identifier_preserved_as_text`, `vat_included_price_header`.
- Excel profiling must detect formula columns and preserve candidate meaning without applying business rules.
