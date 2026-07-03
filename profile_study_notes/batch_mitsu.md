# Batch Technical Notes - Mitsubishi / Mitsu

## Batch Info

- Batch name: Mitsubishi / Mitsu
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\Bang gia Mitsu`
- Original folder name contains Vietnamese accents: `Bảng giá Mitsu`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `catalog-thiet-bi-dong-cat-ha-the-mitsubishi.pdf` | PDF | 13,000,609 bytes | Native text layer exists. 245 pages. Looks like product catalog, not clean price list. |
| `DUYHUNG-THONG BAO CKTC LVS 2022.pdf` | PDF | 366,861 bytes | 1 page. No native text layer detected. Likely scanned/image PDF. |
| `BANG GIA LIST MCB MITSUBISHI 2023.xls` | XLS | 93,184 bytes | Legacy Excel `.xls`. Clean one-sheet table. Readable with xlrd. |
| `2026_ final Tong_hop price list (...).xlsx` | XLSX | 322,160 bytes | Very clean one-sheet flat price list. Strong candidate for generic Excel flat table extraction. |
| `29.03.2023.xlsx` | XLSX | 11,009,598 bytes | Large multi-sheet formatted catalogue price list. Many sheets, repeated table blocks, formulas. |
| `LVS price list 2025 (...).xlsx` | XLSX | 8,152,996 bytes | Large multi-sheet formatted catalogue price list. Similar Mitsubishi structured workbook. |
| `LVS price list 2025.xlsx` | XLSX | 8,154,556 bytes | Large multi-sheet workbook variant. Similar profile family. |
| `Mitsu 2022 Tong hop Pricelist 2022 MEVN-send to Distributor.xlsx` | XLSX | 11,029,439 bytes | Large multi-sheet formatted catalogue price list. Similar to 2023/2025 files. |

## Overall Finding

Mitsubishi data contains multiple source/layout types:

1. Clean flat Excel tables.
2. Legacy `.xls` flat table.
3. Large formatted multi-sheet Excel catalogue workbooks.
4. Product catalog PDF with text layer but not a clean price source.
5. Scanned/image PDF with no text layer.

For Mitsubishi, Excel should generally be preferred over PDF when available.

Recommended extraction priority:

1. Clean flat Excel price list if available.
2. Multi-sheet Mitsubishi price workbook profile.
3. Legacy `.xls` adapter for simple flat table.
4. PDF catalog only for reference, not as primary price source.
5. Scan/image PDF requires OCR later; do not attempt in Phase 14.

## Clean Flat Excel - 2026 Price List

### File

`2026_ final Tong_hop price list (ACB 60, MCCB, Contactor, rơ le nhiệt 55, MCB, RCBO, RCCB 50).xlsx`

### Structure

- Sheet count: 1
- Sheet: `Sheet1`
- Dimensions observed: 8979 rows x 5 columns
- Header row: row 1

Observed header fields:

```text
Material Code
Material Name
Special Spec1
2026 Market Price list (VND)
```

Representative rows:

```text
14JB01A0001PU | WB6-CP | 196000
160001A00001L | AE630-SW 3P 630A | FIX;IEC;40C;WS1NA-P1;BA | 65046000
```

Recommended profile id:

```text
mitsubishi_excel_flat_price_list
```

Suggested mapping:

| Target candidate field | Source column |
|---|---|
| `material_code` | `Material Code` |
| `description` | `Material Name` |
| `special_spec` | `Special Spec1` |
| `unit_price` | `2026 Market Price list (VND)` |
| `currency` | constant `VND`, derived from price header |

Notes:

- This is the easiest and highest-confidence Mitsu source.
- Header starts at row 1 in this workbook, but profile must still detect header dynamically.
- `Special Spec1` can be retained as candidate/spec metadata, not merged blindly into description unless profile rule says so.

## Legacy XLS - MCB Mitsubishi 2023

### File

`BANG GIA LIST MCB MITSUBISHI 2023.xls`

### Structure

- Legacy `.xls` format.
- Readable with `xlrd` in current environment.
- Sheet count: 1
- Sheet: `Sheet1`
- Dimensions observed: 445 rows x 6 columns
- Header row: row 1

Observed header fields:

```text
Golfa Code
Model DUYHUNG
Material Group
2023 Price list (VND)
CKTC
```

Representative row:

```text
Golfa Code: D1P-0.5C6M
Model DUYHUNG: BH-D6 1P 0.5A C N
Material Group: MCB
2023 Price list (VND): 280000
CKTC: 0.45
Net/derived value: 154000
```

Recommended profile id:

```text
mitsubishi_excel_legacy_mcb_price_list
```

Suggested mapping:

| Target candidate field | Source column |
|---|---|
| `material_code` | `Golfa Code` |
| `description` | `Model DUYHUNG` |
| `product_group` | `Material Group` |
| `unit_price` | `2023 Price list (VND)` |
| `discount_rate_candidate` | `CKTC` |
| `net_price_candidate` | unnamed calculated/value column if present |
| `currency` | constant `VND`, derived from price header |

Guardrail:

- Do not treat the unnamed final column as official unit price unless business rule confirms it. It appears to be derived from price list and CKTC.
- Phase 14 can profile this file, but official extraction should preserve both list price and discount/net candidate separately.

## Large Multi-Sheet Mitsubishi Workbooks

### Files

- `Mitsu 2022 Tong hop Pricelist 2022 MEVN-send to Distributor.xlsx`
- `29.03.2023.xlsx`
- `LVS price list 2025.xlsx`
- `LVS price list 2025 (ACB ck 60, MCCB, Khởi ELCB ck 55, MCB, RCBO, RCCB ck 50).xlsx`

### Common Structure

These workbooks are formatted catalogue price lists with many product-family sheets.

Common sheet examples:

```text
ACB
ACB acc
MCCB
MCCB Motor
MCCB Adjustable
ELCB
ELCB CE
MCCB acc / MCCB Accessory
MCCB MDU
MCB China
MCB India
CP
S-TN / S-T S-N
TH-TN / TH-T TH-N
ME96
EcoMonitor
EcoWebserver
VCB
MV / MV Relays
Relays
```

Observed table header patterns:

```text
Dòng định mức / Rating (A)
Tên sản phẩm / Model name
Mã sản phẩm / Material code
Đơn giá / Unit price (VND)
```

Accessory sheet pattern:

```text
Thông số kỹ thuật / Specifications
Tương thích với MCCB & ELCB / Compatible with MCCB & ELCB
Tên sản phẩm / Model name
Mã sản phẩm / Material code
Đơn giá / Unit price (VND)
```

MDU / technical breaker pattern:

```text
Dòng định mức / Rating (A)
Dòng ngắn mạch / Breaking Capacity / Icu (kA) @415VAC
Tên sản phẩm / Model name
Mã sản phẩm / Material code
Đơn giá / Unit price (VND)
```

### Important Layout Issue

Many sheets contain repeated table blocks and paired columns, usually 3P and 4P side by side:

```text
Rating (A) | Model name | Material code | Unit price | Model name | Material code | Unit price
```

Therefore the extractor cannot assume one simple table per sheet. It must support:

- repeated header rows within the same sheet
- multiple table blocks in one sheet
- paired product columns in the same row
- group headers above each block
- formulas in older workbooks, e.g. VLOOKUP returning unit price

### Recommended profile id

```text
mitsubishi_excel_catalogue_workbook
```

Suggested candidate extraction model for later phases:

- Each workbook sheet is a product family context.
- Each detected table block has a local header row.
- Each data row may produce one or more item candidates if the row contains paired product groups.
- Carry sheet name and nearest section title as context/evidence.
- Preserve rating/current/breaking-capacity/spec columns as candidate attributes.

Suggested mapping for standard table blocks:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | `Mã sản phẩm / Material code` |
| `description` | `Tên sản phẩm / Model name` |
| `unit_price` | `Đơn giá / Unit price (VND)` |
| `currency` | constant `VND`, derived from header |
| `rating_current` | `Dòng định mức / Rating (A)` if present |
| `breaking_capacity` | `Dòng ngắn mạch / Icu` if present |
| `specification` | `Thông số kỹ thuật / Specifications` if present |
| `compatible_model` | `Tương thích... / Compatible...` if present |
| `product_family` | sheet name and/or section title |
| `origin_candidate` | section note such as `Made in Japan`, `Made in Vietnam`, if available |

Guardrails:

- Do not hard-code sheet names because names differ by year/version.
- Do not assume header appears only once per sheet.
- Do not assume row has only one item candidate.
- Do not drop formulas; use cached values/data_only when extracting price, but record that price may come from formula.
- Do not confuse ratings such as `630A`, `65kA`, `Icu`, `0.5-1` with price.
- Preserve technical specs separately rather than forcing them into normalized official fields too early.

## PDF Findings

### PDF: catalog-thiet-bi-dong-cat-ha-the-mitsubishi.pdf

- Page count: 245
- Native text layer: yes
- Total extracted text characters: approximately 772,467
- Metadata title observed: `FA PRODUCT CATALOG`
- Looks like a product catalog / technical catalog, not a clean price list.

Representative text pattern:

```text
Low-Voltage Power Distribution Product
Molded Case Circuit Breakers
Earth Leakage Circuit Breakers
UL 489 Listed Circuit Breakers
...
Notes...
M5 / M6 / M8
AMP #322870
JST 38-S8
```

Finding:

- This PDF has text, but it contains many technical dimensions/specifications.
- It should not be treated as a primary price source without a dedicated catalogue profile.
- It may be useful for future product metadata enrichment, but not initial price extraction.

### PDF: DUYHUNG-THONG BAO CKTC LVS 2022.pdf

- Page count: 1
- Native text layer: no
- Extracted text chars: 0
- Likely scanned/image PDF.

Finding:

- Requires OCR if it must be processed.
- Phase 14 should detect and report `text_layer=false` / `ocr_required`.
- Do not attempt OCR in Phase 14 unless explicitly scoped.

## Data Contract / Phase Design Implications

This batch strongly supports a multi-source foundation with source profiling before extraction:

```text
PDF / XLS / XLSX
-> source_metadata.json
-> source_profile.json
-> later table/record candidates
```

For Phase 14:

- Support `.xlsx`, `.xls`, and `.pdf` as source types.
- For Excel:
  - sheet list
  - dimensions / used range
  - candidate header rows
  - likely profile id
  - confidence/signals/warnings
- For PDF:
  - page count
  - text layer flag
  - extracted text char count
  - scan/OCR-required warning if no text layer
- Do not extract official items yet.

For later extraction phases:

- Implement `mitsubishi_excel_flat_price_list` first because it is simple and high-confidence.
- Implement `mitsubishi_excel_legacy_mcb_price_list` for `.xls` files.
- Implement `mitsubishi_excel_catalogue_workbook` for multi-sheet formatted catalogues.
- Treat Mitsubishi technical PDF catalog separately from price list extraction.

## Recommended Profile Signals

### mitsubishi_excel_flat_price_list

```text
Material Code
Material Name
Special Spec1
Market Price list (VND)
```

### mitsubishi_excel_legacy_mcb_price_list

```text
Golfa Code
Model DUYHUNG
Material Group
Price list (VND)
CKTC
```

### mitsubishi_excel_catalogue_workbook

```text
MÁY CẮT KHÔNG KHÍ
AIR CIRCUIT BREAKER
MCCB
ELCB
Dòng định mức / Rating (A)
Tên sản phẩm / Model name
Mã sản phẩm / Material code
Đơn giá / Unit price (VND)
```

### mitsubishi_pdf_catalog_reference

```text
FA PRODUCT CATALOG
Low-Voltage Power Distribution Product
Molded Case Circuit Breakers
Earth Leakage Circuit Breakers
```

## Risks / Guardrails

- Mitsubishi workbooks are not one uniform structure.
- Some sources are clean flat price lists; others are complex formatted catalogues.
- Some sheets contain multiple table blocks and paired columns.
- Some values are formulas; extraction should use cached value but preserve source evidence.
- PDF product catalog should not be used as price source by default.
- Scan/image PDF must be detected as OCR-required and left for a later OCR phase.
- Header detection must be dynamic from the top of each sheet; never hard-code row starts.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Phase 14 must profile Excel files at sheet level, not only workbook level.
- Source profile should include candidate sheets, candidate header rows, detected layout family, and confidence.
- Support legacy `.xls` intake/profiling if dependencies allow; otherwise fail clearly with `unsupported_excel_legacy` warning.
- Do not treat PDF text layer presence as enough for price extraction. Catalog PDF and price-list PDF are different layout families.
- Add warning model entries such as `ocr_required`, `catalog_reference_pdf`, `multi_block_sheet`, `formula_prices_detected`, `legacy_xls_source`.
