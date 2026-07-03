# Batch Technical Notes - BTB / ETINCO

## Batch Info

- Batch name: BTB / ETINCO
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\BTB`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `Bao-gia-ETINCO-2026.4.pdf` | PDF | 3,951,854 bytes | Native text layer exists. 30 pages. Price list PDF; table extraction works on representative data pages. |
| `1779329644890_2834687793224201685_g6872404581050533084_619c3ff58e78151ca4ae5b8b0cfa52b1.jpg` | JPG | 130,137 bytes | Image source. 814 x 507 RGB JPEG. Requires OCR/image adapter in future. |

## Important Priority Rule

Do not prioritize sources by file type alone.

- Business priority should come from effective date, issue date, received date, or explicit user selection.
- Technical confidence should describe how easy/reliable the file is to extract.
- A newer PDF may have higher business priority than an older Excel file even if the Excel file is technically easier.

For this batch, `Bao-gia-ETINCO-2026.4.pdf` appears to be a 2026.4 price list, so it may be the active business source if the user confirms it is the latest.

## PDF Price List Findings

### File

`Bao-gia-ETINCO-2026.4.pdf`

### Structure

- Page count: 30
- Native text layer: yes
- Extracted text characters: approximately 71,901
- Representative page: page 24
- Default text extraction shows line-based table content.
- `pdfplumber.extract_tables()` successfully detected representative tables on data pages.

Representative text pattern:

```text
Cầu dao điện loại tép MCB (gắn trên thanh ray)
Tên hàng
In (A)
Icu (KA)
Giá bán
LA63N 1P
6-10-16-20-25-32A
6KA
115,000
LA63N 1P
40-50-63A
6KA
121,000
```

Representative pdfplumber table on page 24:

```text
['Cầu dao điện loại tép MCB (gắn trên thanh ray)', None, None, None]
['Tên hàng', 'In (A)', 'Icu (KA)', 'Giá bán']
['LA63N 1P', '6-10-16-20-25-32A', '6KA', '115,000']
['LA63N 1P', '40-50-63A', '6KA', '121,000']
['LA63N 2P', '6-10-16-20-25-32A', '6KA', '254,000']
```

Recommended profile id:

```text
generic_pdf_table_price_list
```

or more specifically:

```text
etinco_ls_like_pdf_table_price_list
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `description` / `model_name` | `Tên hàng` |
| `rated_current_candidate` | `In (A)` |
| `breaking_capacity_candidate` | `Icu (KA)` |
| `unit_price` | `Giá bán` |
| `currency` | inferred from document/profile if VND is confirmed |
| `product_group` | table title row, e.g. `Cầu dao điện loại tép MCB (gắn trên thanh ray)` |

Guardrails:

- Do not treat `In (A)` as quantity.
- Do not treat `Icu (KA)` as price.
- Price values use comma thousand separators, e.g. `115,000`.
- Product group/title row should be carried forward as context, not emitted as an item.
- If currency is not explicit on the current page/table, infer only from document-level signal or user/source metadata, and record evidence/warning.

## Image Source Findings

### File

`1779329644890_2834687793224201685_g6872404581050533084_619c3ff58e78151ca4ae5b8b0cfa52b1.jpg`

### Structure

- Format: JPEG
- Mode: RGB
- Dimensions: 814 x 507

Recommended classification:

```text
image_source_ocr_required
```

Guardrails:

- Do not attempt OCR in Phase 14 unless explicitly scoped.
- Phase 14 should capture image metadata only:
  - file name
  - size
  - sha256
  - dimensions
  - image format
  - source_type = image
  - profile_status = ocr_required or unsupported_in_current_phase
- Do not generate item candidates directly from image without OCR + review.

## Data Contract / Phase Design Implications

This batch adds a required source type beyond PDF/Excel:

```text
image
```

For Phase 14, source types should likely include:

```text
pdf
excel
image
unsupported
```

Source role examples from this batch:

```text
price_list
image_ocr_required
```

Phase 14 should capture business vs technical metadata separately:

```text
business_effective_date_candidate
business_issue_date_candidate
business_received_date
business_priority_source
technical_confidence
profile_status
```

The ETINCO PDF is a positive example where PDF table extraction can work well. It should not be downgraded just because it is PDF.

## Recommended Profile Signals

### generic_pdf_table_price_list / etinco_ls_like_pdf_table_price_list

```text
Tên hàng
In (A)
Icu (KA)
Giá bán
Cầu dao điện loại tép MCB
LA63N
```

### image_source_ocr_required

```text
.jpg
.jpeg
image dimensions available
no native text layer
```

## Risks / Guardrails

- Business priority must not be determined by extension.
- A current PDF can be more important than an older Excel file.
- Table title rows should not become item candidates.
- Technical columns such as `In (A)` and `Icu (KA)` must not be parsed as quantity/price.
- Image files must be metadata-only in Phase 14 unless OCR phase is explicitly implemented.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Add `image` as a supported source type for metadata/profiling, even if OCR is deferred.
- Add `business_priority` / `effective_date_candidate` fields separate from `technical_confidence`.
- Add warning codes:
  - `ocr_required`
  - `image_source_not_extracted`
  - `table_title_context_not_item`
  - `technical_column_not_quantity`
  - `currency_inferred_from_document`
- PDF table extraction should be attempted as a profiling signal, but Phase 14 should not produce final item extraction unless scoped.
