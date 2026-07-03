# Batch Technical Notes - Emic

## Batch Info

- Batch name: Emic
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\Emic`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `BẢNG GIÁ EMIC 2025.pdf` | PDF | 133,768 bytes | Native text layer exists. 1 page. Table extraction works. Effective date in document: 01/10/2025. |
| `BẢNG GIÁ EMIC ÁP DỤNG 15-03-2024.pdf` | PDF | 126,495 bytes | Native text layer exists. 1 page. Table extraction works. Effective date in file/document: 15/03/2024. |
| `giá kiểm định.jpg` | JPG | 126,308 bytes | Image source. 691 x 539 RGB JPEG. Requires OCR/image adapter in future. |

## Important Priority Rule

Business priority should be based on effective date, issue date, received date, or explicit user selection, not file type.

For this batch:

- `BẢNG GIÁ EMIC 2025.pdf` appears newer/effective from 01/10/2025.
- `BẢNG GIÁ EMIC ÁP DỤNG 15-03-2024.pdf` is older/effective 15/03/2024.
- If both are available and user does not override, the 2025 PDF is likely the active business candidate.

Technical confidence is high for both PDFs because table extraction works.

## PDF Table Price List Findings

### Common Structure

Both Emic PDFs are one-page price tables with the following columns:

```text
STT
Tên gọi, quy cách sản phẩm
ĐVT
Giá nhà máy
VAT 8%
Đơn giá có VAT (8%) / Đơn giá bao gồm VAT (8%)
```

They include section/group rows such as:

```text
I | CÔNG TƠ ĐIỆN TỬ 1 PHA 220V CCX0.5;1
II | CÔNG TƠ ĐIỆN TỬ 3 PHA 220V CCX0.5;1
III | Đồng hồ Vol, Ampe các loại
IV | Biến dòng hạ thế...
```

Group rows should become context, not item rows.

### File: BẢNG GIÁ EMIC 2025.pdf

- Page count: 1
- Native text layer: yes
- Extracted text characters: approximately 4,471
- `pdfplumber.extract_tables()` detects one representative table.
- Table dimensions observed: 51 rows x 6 columns
- Effective date text: `ÁP DỤNG TỪ NGÀY 01/10/2025`

Representative rows:

```text
STT | Tên gọi, quy cách sản phẩm | ĐVT | Giá nhà máy | VAT 8% | Đơn giá có VAT (8%)
I | CÔNG TƠ ĐIỆN TỬ 1 PHA 220V CCX0.5;1
1 | CTĐT 1 pha 1 giá 5(80)A; 220-230V ; C1 (CE38) | Cái | 360.000 | 28.800 | 388.800
2 | CTĐT 1 pha 1 giá 10(80)A; 220-230V ; C1 (CE18, module RF-MESH) | Cái | 610.000 | 48.800 | 658.800
```

Extraction issue observed:

- In pdfplumber table output, some 2025 base price cells are split with spaces:

```text
3 60.000
6 10.000
9 65.000
2 .800.000
```

This should be normalized carefully only for numeric price fields, with validation against VAT and final price when possible.

### File: BẢNG GIÁ EMIC ÁP DỤNG 15-03-2024.pdf

- Page count: 1
- Native text layer: yes
- Extracted text characters: approximately 2,621
- `pdfplumber.extract_tables()` detects one representative table.
- Table dimensions observed: 38 rows x 6 columns
- Effective date: 15/03/2024

Representative rows:

```text
STT | Tên gọi, quy cách sản phẩm | ĐVT | Giá nhà máy | VAT 8% | Đơn giá bao gồm VAT (8%)
1 | CTĐT 1 pha 1 giá 5(80)A; 220-230V ; C1 (CE38) | Cái | 360,000 | 28,800 | 388,800
2 | CTĐT 1 pha 1 giá 10(80)A; 220-230V ; C1 (CE18, module RF-MESH) | Cái | 610,000 | 48,800 | 658,800
```

This older file uses comma thousand separators; 2025 file uses dot thousand separators in extracted text.

## Recommended Profile

Suggested profile id:

```text
emic_pdf_table_price_list
```

Detection signals:

```text
EMIC
STT
Tên gọi, quy cách sản phẩm
ĐVT
Giá nhà máy
VAT 8%
Đơn giá có VAT
Đơn giá bao gồm VAT
CÔNG TƠ ĐIỆN TỬ
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `line_no_candidate` | `STT` for numeric rows |
| `description` | `Tên gọi, quy cách sản phẩm` |
| `unit` | `ĐVT` |
| `factory_price_candidate` | `Giá nhà máy` |
| `vat_amount_candidate` | `VAT 8%` |
| `unit_price_with_vat_candidate` | `Đơn giá có VAT (8%)` / `Đơn giá bao gồm VAT (8%)` |
| `vat_rate_candidate` | 0.08, derived from header only |
| `product_group` | Roman numeral section rows |
| `currency` | VND, inferred from context/header if confirmed |
| `effective_date_candidate` | from title/file name, e.g. 2025-10-01 or 2024-03-15 |

Guardrails:

- Do not emit section rows (`I`, `II`, `III`, `IV`) as item candidates.
- Do not parse rating/spec numbers such as `5(80)A`, `220-230V`, `0,5S`, `3x5(10)A` as prices.
- Normalize numeric price cells only in price columns.
- If price cleanup changes `3 60.000` to `360.000`, record a warning/evidence or validate using VAT/final price:
  - `factory_price + vat_amount = unit_price_with_vat`
  - `vat_amount ~= factory_price * 0.08`
- Preserve both factory price and final VAT-included price as separate candidates until business rule chooses official price.
- Do not assume VAT rate globally; derive only from header/document evidence.

## Image Source Findings

### File

`giá kiểm định.jpg`

### Structure

- Format: JPEG
- Mode: RGB
- Dimensions: 691 x 539

Recommended classification:

```text
image_source_ocr_required
```

Role:

- Likely an image price/fee notice or inspection price image.
- Phase 14 should capture metadata only.
- OCR should be deferred to a later OCR/image adapter phase.

Guardrails:

- Do not generate item candidates from image without OCR and review.
- Capture image metadata: dimensions, format, file size, sha256, source_type=image.

## Data Contract / Phase Design Implications

This batch adds a high-confidence example of one-page PDF table price lists.

Useful source roles:

```text
price_list
image_ocr_required
```

Useful source/profile fields:

```text
business_effective_date_candidate
technical_confidence
profile_status
source_role
vat_rate_candidate
price_column_cleanup_warnings
```

Recommended warning codes:

```text
image_source_not_extracted
ocr_required
section_row_context_not_item
price_cell_spacing_normalized
vat_cross_check_available
mixed_thousand_separator_style
```

## Risks / Guardrails

- Emic price files are technically easy but still require careful numeric cleanup.
- 2025 and 2024 use different thousand separator styles in extraction (`.` vs `,`).
- Some descriptions contain many technical numbers that must not be parsed as prices.
- Final VAT-included price and factory price should remain separate candidates until official business rule is defined.
- Image source requires OCR; do not mix into Phase 14 extraction.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Phase 14 profiling should detect effective date candidates from file name and document title but not treat them as final truth without confirmation.
- Phase 15+ extraction should include table-level context rows and exclude section rows from item candidates.
- Numeric cleanup should be column-aware and evidence-backed.
- Add support for VAT candidate fields and multiple price candidates, not a single forced `unit_price` during early profiling.
