# Batch Technical Notes - ABB

## Batch Info

- Batch name: ABB
- Source folder: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy\ABB`
- Analysis date: 2026-07-02
- Purpose: Profile study for future Phase 14/15 multi-source quotation intake and extraction.

## Files Found

| File | Type | Size | Notes |
|---|---:|---:|---|
| `BG_ABB FULL.pdf` | PDF | 6,134,652 bytes | Native text layer exists. 139 pages. PDF layout is complex; default table extraction did not detect representative tables in early pages. |
| `ABB 2022 Official ABB ELSP ELSB Price List_2022.07 Update_Final.xlsx` | Excel | 660,093 bytes | Clean workbook. Main data sheet: `PL 2022`. |
| `ABB PL 2024.11.xlsx` | Excel | 1,421,467 bytes | Clean workbook. Main data sheet: `PL 2024`. Has auxiliary comparison sheet `SO SAnh Tang Gia`. |

## Overall Finding

ABB has both PDF and Excel sources. For ABB price list extraction, Excel should be preferred when available because it is much cleaner and more structured than the PDF.

Recommended source priority for ABB:

1. Valid ABB Excel price list workbook.
2. ABB PDF only if no Excel source is available.
3. If only PDF is available, mark as requiring a dedicated PDF profile; do not guess item extraction from raw PDF text.

## Excel Workbook Findings

### Workbook: ABB 2022 Official ABB ELSP ELSB Price List_2022.07 Update_Final.xlsx

- Sheet count: 2
- Sheets:
  - `Applicable PG`
  - `PL 2022`
- Main data sheet: `PL 2022`
- Header row observed: row 9
- Data begins: row 10

Observed header fields:

```text
ORDER CODE
DESCRIPTION (ENG)
DESCRIPTION (VNM)
PRICE LIST 2022 (VND)
CO
MINIMUM ORDER (PC)
BU
Remark
Abbr
Country
Thang 3/202
Ty le
```

Representative data row:

```text
ORDER CODE: 1SAM250000R1001
DESCRIPTION (ENG): MS116-0.16 Manual Motor Starter
DESCRIPTION (VNM): Aptomat khoi dong dong co loai MS116-0.16
PRICE LIST 2022 (VND): 1173000
CO: CN
MINIMUM ORDER (PC): 1
BU: ELSP-CP
Abbr: CN
Country: China
```

### Workbook: ABB PL 2024.11.xlsx

- Sheet count: 4
- Sheets:
  - `Kangatang`
  - `Applicable PG`
  - `PL 2024`
  - `SO SAnh Tang Gia`
- Main data sheet: `PL 2024`
- Header row observed: row 12
- Data begins: row 13

Observed header fields:

```text
ORDER CODE
DESCRIPTION (ENG)
DESCRIPTION (VNM)
PRICE LIST 2024 (VND)
CO
MINIMUM ORDER (PC)
BU
PRODUCT FAMILY
Remark
Abbr
Country
```

Representative data row:

```text
ORDER CODE: 1SAM250000R1001
DESCRIPTION (ENG): MS116-0.16 Manual Motor Starter
DESCRIPTION (VNM): Aptomat khoi dong dong co loai MS116-0.16
PRICE LIST 2024 (VND): 1390000
CO: CN
MINIMUM ORDER (PC): 1
BU: ELSP-CP
PRODUCT FAMILY: CONTROL
Abbr: CN
Country: China
```

### Sheet: SO SAnh Tang Gia

- This sheet appears to be a price comparison / price increase analysis sheet.
- It contains formulas such as lookup/comparison columns.
- It should not be used as the primary quotation source for item extraction.
- It may be useful in future analytics, but not for the initial extraction profile.

## Proposed ABB Excel Profile

Suggested profile id:

```text
abb_excel_price_list
```

Detection signals:

```text
ABB - EL DIVISION - ELSP & ELSB
PRICE LIST 2022
PRICE LIST 2024
ORDER CODE
DESCRIPTION (ENG)
DESCRIPTION (VNM)
PRICE LIST ... (VND)
MINIMUM ORDER (PC)
```

Header detection rule:

- Do not hard-code a fixed row number.
- Detect the header row dynamically using required markers:
  - `ORDER CODE`
  - `DESCRIPTION (ENG)` or `DESCRIPTION`
  - `DESCRIPTION (VNM)` if present
  - `PRICE LIST` and `(VND)`
- Header row varies by workbook:
  - 2022 workbook: row 9
  - 2024 workbook: row 12

Recommended field mapping:

| Target candidate field | ABB source column |
|---|---|
| `material_code` | `ORDER CODE` |
| `description_en` | `DESCRIPTION (ENG)` |
| `description_vi` | `DESCRIPTION (VNM)` |
| `unit_price` | `PRICE LIST 2022 (VND)` or `PRICE LIST 2024 (VND)` |
| `currency` | constant `VND`, derived from header only |
| `minimum_order_qty` | `MINIMUM ORDER (PC)` |
| `business_unit` | `BU` |
| `product_family` | `PRODUCT FAMILY` if present |
| `origin_code_candidate` | `CO` or `Abbr` |
| `origin_country_candidate` | `Country` |
| `remark` | `Remark` |

Important interpretation rule:

- Do not assume `CO` means certificate of origin.
- Treat `CO`, `Abbr`, and `Country` as origin/country candidate fields until a formal normalized field is defined.

## PDF Findings

### File: BG_ABB FULL.pdf

- Page count: 139
- Native text layer: yes
- Total extracted text characters: approximately 260,653
- Metadata title observed: `Price List Phan 1 font Verdana 16-4`
- Default pdfplumber table extraction did not find representative tables in the first 8 pages.

Representative text pattern from page 32:

```text
May cat khong khi ACB - Loai Emax2
San xuat tai Y, bao ve qua tai, ngan mach
Chinh dong qua tai voi trip dien tu: tu 0.4 - 1In
Dac diem
42KA
E1.2B
630
1SDA070701R1
1SDA071331R1
800
1SDA070741R1
1SDA071371R1
1000
1SDA070781R1
1SDA071411R1
```

PDF extraction risk:

- Many technical numbers appear near item/order codes.
- Raw line-based extraction can confuse technical ratings, frame sizes, current ratings, and order codes.
- ABB PDF should require a dedicated PDF layout profile if used.
- If ABB Excel exists, use Excel as preferred source and avoid PDF extraction for official item candidates.

## Data Contract / Phase Design Implications

This batch supports the need for a multi-source intake foundation:

```text
PDF / Excel
-> source_metadata.json
-> source_profile.json
-> future table/record candidates
```

For Phase 14 specifically:

- Detect source type: PDF or Excel.
- For Excel:
  - capture sheet list
  - capture used range / dimensions
  - detect likely data sheet candidates
  - detect possible header rows by markers
  - do not extract final items yet unless Phase 14 scope is expanded
- For PDF:
  - capture page count
  - detect text layer availability
  - capture simple text/page statistics
  - do not infer ABB item rows from complex PDF text yet

For later extraction phases:

- Implement `abb_excel_price_list` as a high-confidence Excel profile.
- Use Excel profile before ABB PDF profile when both source types are present.
- Add regression tests using ABB 2022 and ABB 2024 workbook structures.

## Risks / Guardrails

- Do not hard-code header row numbers.
- Do not use comparison sheet `SO SAnh Tang Gia` as main item source.
- Do not interpret `CO` as certificate of origin without explicit business rule.
- Do not parse technical numeric values from ABB PDF as prices.
- Do not treat PDF text sequence as reliable table order without layout-aware profile.

## Recommended Next Notes To Merge Into Phase 14 Prompt

- Phase 14 must support both PDF and Excel source profiling.
- Excel source profiling must scan dynamically from the top of each sheet to find header candidates.
- Repeated objects with known structure must have Pydantic models, not raw `dict[str, Any]`.
- ABB is a strong example where Excel should be preferred over PDF.
- `source_profile.json` should include detected source type, candidate data sheets, candidate header rows, profile status, confidence, signals, and warnings.
