import json
from datetime import datetime, timezone
from pathlib import Path

from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.audit import log_event
from mep_quotation.spec.models import ItemCandidateManifestModel
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.normalized_draft.builder import convert_manifest_to_draft
from mep_quotation.normalized_draft.manifest import write_normalized_draft, validate_normalized_draft_file


def build_normalized_draft(
    package_path: Path,
    overwrite: bool = False
) -> Path:
    """
    Điều phối việc xây dựng bản nháp chuẩn hóa (normalized draft) từ item candidates.

    Flow:
    1. Load package.json và kiểm duyệt tệp tin đầu vào
    2. Overwrite check -> fail nếu normalized_draft.json đã tồn tại và overwrite=False
    3. Ghi log audit: normalized_draft_build_started
    4. Ghi nhận trạng thái normalized.json ban đầu (tồn tại và SHA256)
    5. Đọc item candidates và chuyển đổi sang NormalizedDraftModel
    6. Ghi log audit: normalized_draft_built
    7. Ghi tệp normalized/normalized_draft.json
    8. Ghi log audit: normalized_draft_written
    9. Validate tệp tin normalized_draft.json sau ghi
    10. Cập nhật package.json
    11. Chạy validate_package_integrity
    12. Hậu kiểm tra tính toàn vẹn của tệp normalized.json (SHA256 không đổi, không tự sinh)
    13. Ghi log audit: normalized_draft_build_completed

    Nếu lỗi: Ghi log audit normalized_draft_build_failed và re-raise.
    """
    package_path = Path(package_path).resolve()
    if not package_path.exists():
        raise FileNotFoundError(f"Package directory not found: {package_path}")

    # 1. Load package.json
    package = load_package_json(package_path)

    # Thư mục normalized/ phải tồn tại trước khi ghi file
    normalized_dir = package_path / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    items_input_path = package_path / "parsed" / "item_candidates.json"
    draft_output_path = normalized_dir / "normalized_draft.json"
    official_norm_path = normalized_dir / "normalized.json"

    # Ghi nhận trạng thái normalized.json ban đầu
    norm_exists_initially = official_norm_path.exists()
    norm_sha256_initial = calculate_sha256(official_norm_path) if norm_exists_initially else None

    try:
        # Ghi log audit bắt đầu
        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_draft_build_started",
            quotation_id=package.quotation_id,
            details={"overwrite": overwrite}
        )

        # Kiểm duyệt đầu vào
        if not items_input_path.exists():
            raise FileNotFoundError(f"Item candidates file not found: {items_input_path}")

        # 2. Overwrite check (Atomic check)
        if not overwrite and draft_output_path.exists():
            raise ValueError(
                f"Normalized draft file already exists at {draft_output_path}. "
                "Set overwrite=True to replace it."
            )

        # Đọc dữ liệu item candidates
        with open(items_input_path, "r", encoding="utf-8") as f:
            cand_data = json.load(f)
        cand_manifest = ItemCandidateManifestModel(**cand_data)

        # 5. Thực hiện dựng draft
        item_candidates_sha256 = calculate_sha256(items_input_path)
        draft_model = convert_manifest_to_draft(cand_manifest, package, item_candidates_sha256)

        # 6. Log built
        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_draft_built",
            quotation_id=package.quotation_id,
            details={
                "item_count": draft_model.item_count,
                "review_required_count": draft_model.review_required_count
            }
        )

        # 7. Ghi tệp
        write_normalized_draft(draft_output_path, draft_model)

        # 8. Log written
        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_draft_written",
            quotation_id=package.quotation_id,
            details={"normalized_draft_path": "normalized/normalized_draft.json"}
        )

        # 9. Validate sau ghi
        validate_normalized_draft_file(draft_output_path, package_path)

        # 10. Cập nhật package.json
        package.files.normalized_draft = "normalized/normalized_draft.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 11. Kiểm tra toàn vẹn package
        validate_package_integrity(package_path)

        # 12. Hậu kiểm tra đối với normalized.json chính thức
        # Case A: Nếu ban đầu normalized.json đã có -> SHA256 phải tuyệt đối không đổi
        if norm_exists_initially:
            if not official_norm_path.exists():
                raise ValueError("Integrity violated: normalized/normalized.json was deleted during Phase 9.")
            norm_sha256_after = calculate_sha256(official_norm_path)
            if norm_sha256_initial != norm_sha256_after:
                raise ValueError(
                    f"Integrity violated: normalized/normalized.json SHA256 changed from "
                    f"'{norm_sha256_initial}' to '{norm_sha256_after}' during Phase 9."
                )
        else:
            # Case B: Nếu ban đầu normalized.json không có -> Đảm bảo Phase 9 không tự tạo nó
            if official_norm_path.exists():
                raise ValueError("Integrity violated: Phase 9 created a new normalized/normalized.json which did not exist initially.")

        # 13. Log completed
        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_draft_build_completed",
            quotation_id=package.quotation_id,
            details={
                "item_count": draft_model.item_count,
                "review_required_count": draft_model.review_required_count
            }
        )

        return package_path

    except Exception as e:
        # Ghi log audit thất bại
        try:
            log_event(
                package_path=package_path,
                level="ERROR",
                event="normalized_draft_build_failed",
                quotation_id=package.quotation_id,
                details={"error": str(e)}
            )
        except Exception:
            pass
        raise e
