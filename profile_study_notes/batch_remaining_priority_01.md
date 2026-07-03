# Batch Technical Notes - Remaining Priority Folders 01

## Batch Info

- Batch name: Remaining priority folders 01
- Source root: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy`
- Folders analyzed deeply in this note:
  - `Himel`
  - `Hanyoung`
  - `Huyndai`
  - `Sino`
  - `FUJI`
- Analysis date: 2026-07-02
- Purpose: Continue source profiling for Phase 14/15 multi-source intake.

## Important Priority Rule

Business priority is based on effective date, issue date, received date, or explicit user selection. Technical confidence is separate.

Do not select a source only because it is PDF/Excel, and do not reject a newer PDF merely because it is harder to extract.

---

# Himel

## Files

| File | Type | Size | Finding |
|---|---:|---:|---|
| `Bang Gia Himel 2026_NEW TG.pdf` | PDF | 90,410,196 bytes | Native text layer exists. 33 pages. Large price list. Table extraction works on representative pages. |
| `THÔNG BÁO ĐIỀU CHỈNH GIÁ HIMEL 3-2026.pdf` | PDF | 255,991 bytes | No text layer detected. Likely scanned/image notice. OCR required later. |

## Price PDF Findings

`Bang Gia Himel 2026_NEW TG.pdf`:

- Page count: 33
- Text chars: approx. 22,665
- Text layer: yes
- Metadata title: `Bang Gia Himel 2026_NEW`
- Representative table detected on page 23.

Representative table:

```text
Hình Ảnh | Mô tả | Mã hàng | Đơn giá (VNĐ)
Biến dòng 30/5 cl.0,5 | MSQ-30. 10x30,30 | 115,000
Biến dòng 50/5 cl.0,5 | MSQ-30. 10x30,50 | null/blank price in table extraction
```

Recommended profile id:

```text
himel_pdf_table_price_list
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `description` | `Mô tả` |
| `material_code` | `Mã hàng` |
| `unit_price` | `Đơn giá (VNĐ)` |
| `currency` | VND from header |
| `product_group` | nearby section/page title if available |

Guardrails:

- Some price cells may appear blank due to merged/repeated visual layout; profile needs carry-forward or layout validation.
- Do not parse current transformer ratios such as `30/5`, `1000/5`, `cl.0,5` as prices.
- Very large PDF should be allowed but may trigger `large_source_file` warning.

## Adjustment Notice

`THÔNG BÁO ĐIỀU CHỈNH GIÁ HIMEL 3-2026.pdf`:

- Page count: 1
- Text chars: 0
- Text layer: no
- Classification: `image_or_scan_pdf_ocr_required`

Guardrail:

- Do not process this notice in Phase 14 except metadata/profiling.

---

# Hanyoung / Giga Electric

## Files

| File | Type | Size | Finding |
|---|---:|---:|---|
| `THONG BAO PHAT HANH BANG GIA 2026.pdf` | PDF | 2,606,762 bytes | No text layer detected. OCR required. |
| `THÔNG BÁO ĐIỀU CHỈNH GIÁ GIGA ELECTRIC.pdf` | PDF | 221,523 bytes | No text layer detected. OCR required. |

## Findings

Both PDFs have zero extracted text. They appear to be scanned/image PDFs or otherwise not text-extractable.

Recommended classifications:

```text
pdf_scan_ocr_required
price_publication_or_adjustment_notice_unknown
```

Guardrails:

- Do not attempt item extraction in Phase 14.
- Capture metadata only: page count, file size, sha256, source_type=pdf, text_layer=false, ocr_required=true.
- Business role may be important because filenames suggest 2026 price publication / adjustment notice, but direct extraction must wait for OCR or user-provided structured source.

---

# Huyndai / Hyundai

## Files

| File | Type | Size | Finding |
|---|---:|---:|---|
| `BẢNG GIÁ TBĐ HYUNDAI _ 2026.pdf` | PDF | 536,255 bytes | Native text layer exists. 11 pages. Table extraction works. Effective date appears 20/04/2026. |
| `Final BG 2024.pdf` | PDF | 810,977 bytes | Native text layer exists. 14 pages. Table extraction works. Effective date appears 01/06/2024. |

## PDF Findings

Common structure:

```text
BẢNG GIÁ THIẾT BỊ ĐIỆN
Áp dụng từ ngày ...
Mã hàng
Số cực
Dòng định mức In (A)
Icu (kA)
Đơn giá (VND)
```

Representative code/price sequence from 2026:

```text
HGS06A3HM0C0S051T | 36,500,000
HGS06A4HM0C0S051T | 45,000,000
HGS08A3HM0C0S051H | 42,500,000
```

Representative extracted table on page 2:

```text
Mã hàng | Số cực | Dòng định mức In (A) | Icu (kA) | Đơn giá (VND)
MCCB 2P Chỉnh dòng nhiệt ... section row
```

Recommended profile id:

```text
hyundai_pdf_table_price_list
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | `Mã hàng` |
| `pole_count_candidate` | `Số cực` |
| `rated_current_candidate` | `Dòng định mức In (A)` |
| `breaking_capacity_candidate` | `Icu (kA)` |
| `unit_price` | `Đơn giá (VND)` |
| `currency` | VND from header |
| `effective_date_candidate` | from title text |

Business priority:

- 2026 file likely supersedes 2024 file if user confirms latest active source.

Guardrails:

- Do not parse `In (A)` or `Icu (kA)` as quantity/price.
- Section rows such as MCCB type descriptions are context, not items.

---

# Sino

## Files

| File | Type | Size | Finding |
|---|---:|---:|---|
| `BG Sino - Tu dien 12042022 Ck 33%.pdf` | PDF | 6,092,943 bytes | No text layer detected. OCR required. |
| `BG_HVC_MCB SINO(ck 32%).pdf` | PDF | 7,447,874 bytes | No text layer detected. OCR required. Metadata title indicates CDR export. |
| `BG_HVC_MCCB SINO(ck 30%).pdf` | PDF | 7,320,412 bytes | No text layer detected. OCR required. Metadata title indicates CDR export. |

## Findings

All Sino PDFs have zero extracted text. They are likely image/visual PDFs generated from CorelDRAW or scanned content.

Recommended classification:

```text
sino_pdf_scan_or_visual_price_list_ocr_required
```

Guardrails:

- Do not attempt Phase 14 item extraction.
- Record technical_confidence low for native extraction.
- Keep business metadata from filename, e.g. CK rates, but do not apply CK automatically.
- OCR/Image layout phase required for direct extraction.

---

# FUJI / Hạo Phương Fuji

## File

| File | Type | Size | Finding |
|---|---:|---:|---|
| `ck 52% Bảng Giá Biến Tần Fuji 20_03_2025.pdf` | PDF | 936,335 bytes | Native text layer exists. 8 pages. Table extraction works. Price list from Hạo Phương/Fuji context. |

## PDF Findings

- Page count: 8
- Text chars: approx. 12,063
- Text layer: yes
- Metadata title: `BẢNG GIÁ HẠO PHƯƠNG 2024 TỔNG HỢP`
- Representative page: page 4
- `pdfplumber` table extraction works on data pages.

Representative structure:

```text
Bảng giá FUJI ELECTRIC - www.haophuong.com
Price excludes VAT - Bảng giá trên chưa bao gồm thuế VAT
BIẾN TẦN
MÃ HÀNG
CÔNG SUẤT
ĐƠN GIÁ (VNĐ)
TÍNH NĂNG RIÊNG
FRENIC-MEGA G2 SERIES
FRN0002G2S-4G | 0,4 | 17.871.000
FRN0003G2S-4G | 0,75 | 14.180.000
```

Recommended profile id:

```text
fuji_haophuong_pdf_table_price_list
```

Suggested mapping:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | `MÃ HÀNG` |
| `power_candidate` | `CÔNG SUẤT MOTOR (KW)` / `CÔNG SUẤT` |
| `unit_price` | `ĐƠN GIÁ (VNĐ)` |
| `currency` | VND from header |
| `vat_included_candidate` | false if document text says price excludes VAT |
| `product_group` | section such as `FRENIC ACE SERIES`, `FRENIC-MEGA G2 SERIES` |
| `feature_notes` | `TÍNH NĂNG RIÊNG` if table structure supports it |

Guardrails:

- File name includes `ck 52%`, but CK should not be applied automatically.
- Metadata title mentions Hạo Phương 2024 while filename says Fuji 2025; business date should require file/document evidence or user confirmation.
- Decimal power values like `0,4`, `0,75`, `1,5` are not prices.
- Price separator uses dot thousands, e.g. `17.871.000`.

---

# Phase 14 Implications From This Batch

New/confirmed source roles:

```text
price_list
price_adjustment_notice
scan_pdf_ocr_required
visual_pdf_ocr_required
large_pdf_price_list
```

Useful warning codes:

```text
large_source_file
scan_pdf_ocr_required
visual_pdf_no_text_layer
section_row_context_not_item
technical_column_not_price
discount_in_filename_not_applied
business_date_conflict_requires_confirmation
price_cell_missing_due_to_layout
```

Key design rule:

- Phase 14 should classify extraction readiness. It should not fail just because OCR is needed; it should produce metadata/profile output with `profile_status=ocr_required` or similar.
