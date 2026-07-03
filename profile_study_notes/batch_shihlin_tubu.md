# Batch Technical Notes - Shihlin / Tu Bu Image

## Batch Info

- Batch name: Shihlin and Tu Bu image sources
- Source root: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy`
- Folders analyzed:
  - `THAY ĐỔI BẢNG GIÁ SHIHLIN`
  - `Tụ Bù`
- Analysis date: 2026-07-02

## Important Priority Rule

Business priority is based on effective date, issue date, received date, or explicit user selection. Technical confidence is separate.

Adjustment notices can be newer and business-relevant, but they are not direct item price lists unless a later workflow applies them explicitly.

---

# Shihlin

## Files

| File | Type | Size | Finding |
|---|---:|---:|---|
| `BẢNG GIÁ SHIHLIN 01032026.pdf` | PDF | 2,078,448 bytes | Native text layer exists. 18 pages. Item price list. Layout partly table/line hybrid. |
| `THÔNG BÁO ĐIỀU CHỈNH BẢNG GIÁ SHIHLIN 01032026.pdf` | PDF | 650,518 bytes | Native text layer exists. 2 pages. Vietnamese adjustment notice. |
| `BSE26008N-1_CN_越南牌價調漲銷售通訊.pdf` | PDF | 1,522,307 bytes | Native text layer exists. 1 page. Chinese adjustment notice. |

## Price List PDF

### File

`BẢNG GIÁ SHIHLIN 01032026.pdf`

### Structure

- Page count: 18
- Native text layer: yes
- Extracted text chars: approx. 28,359
- Representative page: page 7
- Contains item price list sections and accessory sections.
- Default table extraction finds some tables, but not necessarily clean item tables on the best text page.

Representative text pattern:

```text
MCCB (Aptomat) 2P Tiêu chuẩn IEC60947-2
Mã hàng
P
Dòng định mức (A)
kA
Đơn giá (VND)
BM 30-CN
2P
3.5.10.15.20.30A
1.5
583,000
BM 50-CN
2P
10.15.20.30.40.50A
2.5
735,000
BM 100-MN
2P
10.15.20.30.40.50A
10
1,013,000
60.75.100A
1,065,000
```

Accessory section pattern:

```text
PHỤ KIỆN MCCB – BỘ KHỞI ĐỘNG ON/OFF MCCB
Mã hàng
Đơn giá (VND)
MT-100N
BM/BL 50-CN/100-MN.SN
9,073,000
```

Recommended profile id:

```text
shihlin_pdf_price_list_hybrid
```

Suggested mapping for main breaker rows:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | `Mã hàng` |
| `pole_count_candidate` | `P` |
| `rated_current_candidate` | `Dòng định mức (A)` |
| `breaking_capacity_candidate` | `kA` |
| `unit_price` | `Đơn giá (VND)` |
| `product_group` | section title, e.g. `MCCB (Aptomat) 2P...` |

Suggested mapping for accessory rows:

| Target candidate field | Source column/context |
|---|---|
| `material_code` | accessory code, e.g. `MT-100N` |
| `compatible_model_candidate` | compatible model line, e.g. `BM/BL 50-CN/100-MN.SN` |
| `unit_price` | `Đơn giá (VND)` |
| `product_group` | accessory section title |

Guardrails:

- Some item codes may have multiple current ranges and prices under one model. Do not collapse them incorrectly.
- Do not treat `kA`, `P`, current ratings, or section numbers as price.
- Accessory rows may have a code + compatible model + price pattern, not the same as breaker rows.
- Table extraction may include comparison/specification pages that are not price tables; profile must identify price sections.

## Adjustment Notices

### Vietnamese notice

`THÔNG BÁO ĐIỀU CHỈNH BẢNG GIÁ SHIHLIN 01032026.pdf`

- Page count: 2
- Native text layer: yes
- Text chars: approx. 2,096
- Effective date: 01/03/2026
- Business meaning: price policy changed from VAT-included to VAT-excluded.

Representative text:

```text
Giá bán được điều chỉnh từ BẢNG GIÁ 01022026 ĐÃ BAO GỒM 10% VAT
thành CHƯA BAO GỒM VAT
Bảng giá mới 01032026 chính thức áp dụng từ ngày 01/03/2026
```

### Chinese notice

`BSE26008N-1_CN_越南牌價調漲銷售通訊.pdf`

- Page count: 1
- Native text layer: yes
- Text chars: approx. 333
- Effective date: 2026/03/01
- Business meaning: Shihlin Vietnam 2026 price adjustment; price changed from tax-included to tax-excluded.

Recommended profile id:

```text
shihlin_price_adjustment_notice
```

Guardrails:

- Adjustment notices are not item-level price sources.
- Do not auto-apply VAT policy changes without explicit workflow.
- Store as business metadata/evidence for active price list selection.
- May affect interpretation of `BẢNG GIÁ SHIHLIN 01032026.pdf` as VAT-excluded.

---

# Tụ Bù / Nuintek Image

## File

| File | Type | Size | Finding |
|---|---:|---:|---|
| `BG_HVC_Tu bu nuitek 2025 ck 50.jpg` | JPG | 91,071 bytes | Image source. 722 x 509 RGB JPEG. OCR required. |

## Image Findings

- Format: JPEG
- Mode: RGB
- Dimensions: 722 x 509

Recommended classification:

```text
image_source_ocr_required
```

Guardrails:

- Phase 14 should capture metadata only.
- Do not generate item candidates without OCR and review.
- File name contains `ck 50`, but discount should not be applied automatically.

---

# Phase 14 Implications

New/confirmed source roles:

```text
price_list
price_adjustment_notice
image_ocr_required
```

Useful warnings:

```text
price_adjustment_notice_not_item_source
vat_policy_notice_requires_business_rule
image_source_not_extracted
ocr_required
discount_in_filename_not_applied
hybrid_price_layout_requires_profile
```

Key design implication:

- Phase 14 should record business notes/signals from adjustment notices separately from item extraction readiness.
- A source may be business-critical but not directly extractable as item rows.
