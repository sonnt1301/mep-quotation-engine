import json
import re
from pathlib import Path

from mep_quotation.spec.models import RowCandidateManifestModel, TextAssemblyManifestModel, LineCandidatesManifestModel
from mep_quotation.package.loader import load_package_json
from mep_quotation.pdf.checksum import calculate_sha256


def write_row_candidates_manifest(path: Path, data: RowCandidateManifestModel) -> None:
    """Ghi RowCandidateManifestModel xuống file JSON dạng deterministic."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry_dict = data.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def validate_row_candidates_file(manifest_path: Path, package_path: Path) -> None:
    """
    Xác thực toàn diện tệp row_candidates.json và các hàng ứng viên ghép.

    Các quy tắc xác thực:
    1. Parse JSON và validate Pydantic model RowCandidateManifestModel.
    2. quotation_id khớp với package.json.
    3. Tệp parsed/line_candidates.json nguồn tồn tại thực tế.
    4. Tệp text/quotation_text.json nguồn tồn tại thực tế.
    5. source_sha256 khớp chuẩn xác mã băm SHA256 của line_candidates.json.
    6. row_count == len(rows).
    7. row_id là duy nhất và tuân thủ định dạng {QUOTATION_ID}_ROWCAND_{SEQ}.
    8. Đọc file line_candidates.json để đối chiếu:
       - Các source_candidate_ids của từng row đều phải tồn tại trong line_candidates.json.
       - Tất cả các source candidates trong một row phải có chung page_number và khớp với row.page_number.
    9. Đọc file Markdown text/quotation.md và so khớp:
       - markdown_content[start_offset:end_offset] == evidence_text.
    10. page_number trong dải 1..page_count.
    11. start_line_number <= end_line_number.
    12. confidence trong dải 0.0..1.0.
    13. unit_price_candidate >= 0 nếu không null.
    14. quantity_candidate > 0 nếu không null.

    Raises:
        ValueError: Nếu bất kỳ quy tắc nào bị vi phạm.
    """
    manifest_path = Path(manifest_path)
    package_path = Path(package_path)

    # 1. Parse JSON và validate Pydantic
    if not manifest_path.exists():
        raise ValueError(f"Row candidates manifest file does not exist: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from row candidates manifest: {e}")

    try:
        manifest = RowCandidateManifestModel(**manifest_data)
    except Exception as e:
        raise ValueError(f"Row candidates manifest failed Pydantic validation: {e}")

    # 2. quotation_id khớp package.json
    pkg = load_package_json(package_path)
    if manifest.quotation_id != pkg.quotation_id:
        raise ValueError(
            f"quotation_id mismatch: manifest has '{manifest.quotation_id}', "
            f"but package.json has '{pkg.quotation_id}'"
        )

    # 3. Tệp line_candidates.json tồn tại
    line_candidates_path = package_path / manifest.source_line_candidates
    if not line_candidates_path.exists():
        raise ValueError(f"Source line candidates file not found: {line_candidates_path}")

    # 4. Tệp text_manifest tồn tại
    text_manifest_path = package_path / manifest.source_text_manifest
    if not text_manifest_path.exists():
        raise ValueError(f"Source text manifest file not found: {text_manifest_path}")

    # 5. source_sha256 khớp SHA256 của line_candidates.json
    actual_sha256 = calculate_sha256(line_candidates_path)
    if manifest.source_sha256 != actual_sha256:
        raise ValueError(
            f"source_sha256 mismatch: manifest has '{manifest.source_sha256}', "
            f"but actual SHA256 of line_candidates.json is '{actual_sha256}'"
        )

    # 6. row_count == len(rows)
    if manifest.row_count != len(manifest.rows):
        raise ValueError(
            f"row_count ({manifest.row_count}) "
            f"does not match actual rows size ({len(manifest.rows)})"
        )

    # Đọc nội dung Markdown
    md_path = package_path / "text" / "quotation.md"
    if not md_path.exists():
        raise ValueError(f"Markdown file not found: {md_path}")
    with open(md_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # Nạp text manifest để xem page_count
    with open(text_manifest_path, "r", encoding="utf-8") as f:
        try:
            text_manifest_data = json.load(f)
            text_manifest = TextAssemblyManifestModel(**text_manifest_data)
            page_count = text_manifest.page_count
        except Exception as e:
            raise ValueError(f"Failed to load text manifest: {e}")

    # Nạp line candidates manifest để đối chiếu chéo
    with open(line_candidates_path, "r", encoding="utf-8") as f:
        try:
            line_cand_data = json.load(f)
            line_manifest = LineCandidatesManifestModel(**line_cand_data)
            line_cand_map = {lc.candidate_id: lc for lc in line_manifest.candidates}
        except Exception as e:
            raise ValueError(f"Failed to load line candidates: {e}")

    row_ids = set()

    # Xác thực từng row candidate
    for row in manifest.rows:
        # 7. row_id unique và đúng định dạng
        if row.row_id in row_ids:
            raise ValueError(f"Duplicate row_id found: '{row.row_id}'")
        row_ids.add(row.row_id)

        id_pattern = rf"^{re.escape(pkg.quotation_id)}_ROWCAND_\d{{4}}$"
        if not re.match(id_pattern, row.row_id):
            raise ValueError(
                f"row_id '{row.row_id}' does not match format "
                f"'{pkg.quotation_id}_ROWCAND_XXXX'"
            )

        # 8. Đối chiếu chéo source_candidate_ids với line_candidates.json
        if not row.source_candidate_ids:
            raise ValueError(f"Row {row.row_id} has empty source_candidate_ids.")

        for lc_id in row.source_candidate_ids:
            if lc_id not in line_cand_map:
                raise ValueError(
                    f"Row {row.row_id}: source_candidate_id '{lc_id}' "
                    f"does not exist in line_candidates.json"
                )
            
            # Kiểm tra tất cả source candidates phải cùng page_number với row.page_number
            lc_obj = line_cand_map[lc_id]
            if lc_obj.page_number != row.page_number:
                raise ValueError(
                    f"Row {row.row_id}: source candidate '{lc_id}' has page_number {lc_obj.page_number} "
                    f"which is different from row page_number {row.page_number}."
                )

        # 9. So khớp evidence_text
        slice_text = markdown_content[row.start_offset:row.end_offset]
        if slice_text != row.evidence_text:
            raise ValueError(
                f"Row {row.row_id}: slice from Markdown content at "
                f"[{row.start_offset}:{row.end_offset}] does not match evidence_text."
            )

        # 10. page_number trong range hợp lệ
        if row.page_number < 1 or row.page_number > page_count:
            raise ValueError(
                f"Row {row.row_id}: page_number {row.page_number} "
                f"is out of valid range (1..{page_count})"
            )

        # 11. start_line_number <= end_line_number
        if row.start_line_number > row.end_line_number:
            raise ValueError(
                f"Row {row.row_id}: start_line_number {row.start_line_number} "
                f"cannot be greater than end_line_number {row.end_line_number}"
            )

        # 12. confidence trong range 0..1
        if row.confidence < 0.0 or row.confidence > 1.0:
            raise ValueError(
                f"Row {row.row_id}: confidence {row.confidence} "
                f"is out of valid range (0.0..1.0)"
            )

        # 13. unit_price_candidate >= 0
        if row.unit_price_candidate is not None and row.unit_price_candidate < 0:
            raise ValueError(
                f"Row {row.row_id}: unit_price_candidate "
                f"{row.unit_price_candidate} cannot be negative"
            )

        # 14. quantity_candidate > 0
        if row.quantity_candidate is not None and row.quantity_candidate <= 0:
            raise ValueError(
                f"Row {row.row_id}: quantity_candidate "
                f"{row.quantity_candidate} must be greater than zero"
            )
