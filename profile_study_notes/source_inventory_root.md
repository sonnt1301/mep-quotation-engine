# Source Repository Inventory - Bang gia VT Tu dien Copy

## Inventory Info

- Source root: `F:\00.HVC\Bang gia\Bang gia VT Tu dien - Copy`
- Inventory date: 2026-07-02
- Purpose: Top-level inventory before deeper profile study for Phase 14/15.

## Current Scope Observed

Total files under this source root:

```text
67 files
530.11 MB total
```

By extension:

| Extension | Count | Size MB | Notes |
|---|---:|---:|---|
| `.pdf` | 49 | 504.08 | Dominant source type. Includes price lists, catalogues, adjustment notices, and technical catalogues. |
| `.xlsx` | 11 | 21.74 | Includes price lists, internal calculation sheets, temp lock files, and support tables. |
| `.xls` | 6 | 4.21 | Legacy Excel files, including calculations and price lists. |
| `.jpg` | 1 | 0.09 | Image source requiring OCR/image adapter later. |

## Existing Batch Notes Already Created

The following source study notes already exist:

```text
profile_study_notes/batch_abb.md
profile_study_notes/batch_mitsu.md
profile_study_notes/batch_schneider.md
profile_study_notes/batch_btb.md
profile_study_notes/batch_chint.md
profile_study_notes/batch_emic.md
```

Important correction applied after user feedback:

```text
Do not prioritize source by file type alone.
Business priority must be based on effective date, issue date, received date, or explicit user selection.
Technical confidence is separate from business priority.
```

## Top-Level Files In Root

The root contains direct files that are not under a supplier folder. These need separate classification because some are price lists, some are catalogues, and some are internal calculation tools.

### Direct PDF files

```text
2018-Andeli-Catalogue.pdf
2023-Andeli-Catalogue tất cả các sp andeli.pdf
Bảng giá PLC Rockwell micro800_HVC.pdf
bảng giá Siemens.pdf
Bang-gia-Thiet-bi-dien-2022_original Siemens.pdf
Báo giá etinco 31_12_24 nuintek ck 50%.pdf
Catalog Contactor LS.pdf
Catalog MCB.pdf
Catalog MCCB LS.pdf
Catalog PLC S7-1200.pdf
Catalog-bien-tan-Fuji-Ace.pdf
LEIPOLE_FB98.pdf
LEIPOLE_FKL66.pdf
Price List 072025.pdf
```

Initial source-role expectation:

- Some are likely catalog references, not direct item price lists.
- Siemens and ETINCO files may be price lists.
- LS/Contactor/MCB/MCCB catalogues may be technical references.
- `Price List 072025.pdf` needs inspection because name suggests price list but source/manufacturer is unclear from filename alone.

### Direct Excel / legacy Excel files

```text
1. Tinh toan Cu-Cable.xls
1402 Hợp Lực.xls
2.CÔNG THỨC TÍNH QUẠT GIÓ.xls
3. MSB-MDB-DB-OD (1).xls
3. Dinh muc nhan cong bao gia.xlsx
Bảng tính vỏ tủ điện_HVC 2020 (Ver 01) pass.xlsx
PRICELIST 2025 _SI EP_SINOVA_ CUSTOMER.xlsx
Tinh toan vat tu phu tai trong tu dien.xlsx
Tinh toan vat tu phu trong tu dien.xlsx
```

Initial source-role expectation:

- Several are internal calculation sheets, not supplier price lists.
- `PRICELIST 2025 _SI EP_SINOVA_ CUSTOMER.xlsx` likely price list and should be profiled.
- Internal calculation tools should be classified as `internal_calculation_tool`, not quotation source.

### Direct temporary Excel lock files

```text
~$Bảng tính vỏ tủ điện_HVC 2020 (Ver 01) pass.xlsx
~$Giá Sp cho HVC ok .xlsx
```

Classification:

```text
excel_temp_lock_file
```

Guardrail:

- Ignore/flag these. Do not attempt extraction.

## Top-Level Directories

| Folder | Files | Size MB | Initial Notes |
|---|---:|---:|---|
| `FUJI` | 1 | 0.89 | One PDF price list likely. Needs profiling. |
| `Hanyoung` | 2 | 2.70 | One price notice and one 2026 price publication PDF. Needs business-role distinction. |
| `Himel` | 2 | 86.47 | Large 2026 price PDF and adjustment notice. Needs profiling; large PDF may be active business source. |
| `Huyndai` | 2 | 1.28 | 2024/2026 PDFs. Business priority likely newer 2026 unless user overrides. |
| `IDEC` | 17 | 136.85 | Mixed folder with many brands/suppliers: Trường Phát, Fuji, Hanyoung, Hạo Phương, IDEC, MiTEX, Giga, Mikro, Selec, LS, KDE, TPME, and Excel support files. Folder name is not supplier truth. |
| `LS` | 3 | 4.22 | Contains LS PDF, ETINCO PDF, and an MCB Rogy/JVC Excel. Mixed folder. |
| `New folder` | 8 | 68.97 | Mixed sources: Vitzro, ABB PDF, BEST, Kripsol, ME catalog, BT price list Excel, FATA Excel. Needs classification. |
| `Sino` | 3 | 19.89 | Three Sino PDFs, likely price lists. Needs profiling. |
| `THAY ĐỔI BẢNG GIÁ SHIHLIN` | 3 | 4.05 | Shihlin price list and price adjustment notices. Needs business-role distinction. |
| `Tụ Bù` | 1 | 0.09 | One JPG price image. OCR/image adapter required later. |

## Key Findings From Inventory

1. Folder names are not reliable supplier/manufacturer truth.

Examples:

```text
IDEC folder contains Trường Phát, Fuji, Hanyoung, Hạo Phương, IDEC, MiTEX, Giga, Mikro, Selec, LS, KDE, TPME.
LS folder contains LS, ETINCO, Rogy/JVC.
New folder contains Vitzro, ABB, BEST, Kripsol, BT, FATA.
```

Therefore Phase 14 must detect source identity/signals from file content and metadata, not folder path alone.

2. Source role is as important as source type.

Expected roles include:

```text
price_list
price_adjustment_notice
catalog_reference
technical_catalog
internal_calculation_tool
internal_inventory_or_material_master
auxiliary_coefficient_table
image_ocr_required
excel_temp_lock_file
unknown
```

3. Business priority must be separate from technical confidence.

Examples:

```text
A newer PDF may be the active business price list even if a cleaner older Excel exists.
An adjustment notice may be newer but not a direct item price source.
An internal calculation sheet may be Excel but not a supplier price list.
```

4. Phase 14 should not try to extract all items yet.

It should create a reliable intake/profiling layer:

```text
source_metadata.json
source_profile.json
```

with fields such as:

```text
source_type
source_role
business_effective_date_candidate
business_issue_date_candidate
received_date / file_modified_date
technical_confidence
profile_status
signals
warnings
candidate_sheets
candidate_pages
table_extraction_quality
text_layer_status
ocr_required
```

## Recommended Next Profiling Order

Given current inventory, recommended next deep-profile batches:

1. `Himel` because large 2026 price PDF + adjustment notice.
2. `Hanyoung` because it has 2026 price publication and price adjustment notice.
3. `Huyndai` because only two PDFs and likely easy to classify.
4. `Sino` because three PDFs likely direct price lists.
5. `FUJI` because one PDF, quick to profile.
6. `THAY ĐỔI BẢNG GIÁ SHIHLIN` because it combines price list and adjustment notices.
7. Root direct files, especially Siemens / Sinova / ETINCO / Andeli / Rockwell.
8. `IDEC`, `LS`, and `New folder` because they are mixed-brand folders and should be split by file identity rather than folder.
9. Image-only folders/sources for OCR backlog.

## Phase 14 Prompt Implications

Phase 14 should be named something like:

```text
Phase 14 - Multi-Source Intake & Source Profiling Foundation
```

It should support at least:

```text
pdf
excel_xlsx
excel_xls
image
unsupported
```

It should not implement full OCR, AI, parser, normalized output, or final item extraction.

Main scope:

- copy/import arbitrary source file into package
- detect source type
- compute hash/metadata
- profile PDF/Excel/Image shallowly
- classify source role
- separate business priority candidates from technical confidence
- generate schemas from Pydantic models
- expose CLI/UI hooks for source profiling

Guardrails:

- Do not hard-code folder name as supplier.
- Do not use file type as business priority.
- Do not parse all numeric values as prices.
- Do not generate item candidates from catalog/reference/internal files.
- Do not use temp lock files.
- Do not OCR images in Phase 14.
