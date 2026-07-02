import json
import os
from datetime import datetime, timezone
from pathlib import Path
from mep_quotation.package.loader import load_package_json
from mep_quotation.package.writer import write_json_file
from mep_quotation.package.integrity import validate_package_integrity
from mep_quotation.pdf.checksum import calculate_sha256
from mep_quotation.audit import log_event
from mep_quotation.spec.models import (
    NormalizedDraftModel,
    ReviewDecisionsFileModel,
    NormalizedQuotationModel
)
from mep_quotation.review.decisions import validate_review_decisions_file, load_review_decisions
from mep_quotation.normalized_export.exporter import build_official_normalized


def export_normalized(package_path: Path, overwrite: bool = False) -> Path:
    """
    Thực hiện xuất bản tệp normalized.json chính thức từ tệp nháp chuẩn hóa và các quyết định review.
    
    Yêu cầu:
    1. Kiểm định chéo chữ ký băm SHA256 của normalized_draft.json và validate review decisions.
    2. Cản ghi đè nếu overwrite=False và file đã tồn tại.
    3. Atomic Write khi ghi tệp normalized.json.
    4. Cập nhật package.json và chạy kiểm duyệt toàn gói.
    5. Ghi audit logs đầy đủ.
    """
    package_path = Path(package_path).resolve()
    package = load_package_json(package_path)

    log_event(
        package_path=package_path,
        level="INFO",
        event="normalized_export_started",
        quotation_id=package.quotation_id,
        details={"overwrite": overwrite}
    )

    try:
        # Đường dẫn các file đầu vào
        draft_path = package_path / "normalized" / "normalized_draft.json"
        review_path = package_path / "review" / "review_decisions.json"
        export_path = package_path / "normalized" / "normalized.json"

        # 1. Kiểm tra sự tồn tại của các file đầu vào
        if not draft_path.exists():
            raise FileNotFoundError(f"Normalized draft file not found at: {draft_path}")
        if not review_path.exists():
            raise FileNotFoundError(f"Review decisions file not found at: {review_path}")

        # 2. Kiểm định chéo chữ ký băm và validate tệp review
        # validate_review_decisions_file sẽ tự động ném source_sha256_mismatch nếu SHA256 lệch
        validate_review_decisions_file(review_path, package_path)

        # 3. Kiểm tra file output hiện có
        if not overwrite and export_path.exists():
            raise ValueError(
                f"Official normalized file already exists at {export_path}. "
                "Set overwrite=True to replace it."
            )

        # 4. Nạp dữ liệu đầu vào
        with open(draft_path, "r", encoding="utf-8") as f:
            draft_data = json.load(f)
        draft_manifest = NormalizedDraftModel(**draft_data)

        review_manifest = load_review_decisions(review_path)

        # 5. Build official normalized model
        official_manifest = build_official_normalized(package, draft_manifest, review_manifest)

        # Điền SHA256 của các file nguồn tại thời điểm export
        draft_sha256 = calculate_sha256(draft_path)
        review_sha256 = calculate_sha256(review_path)
        official_manifest.source_normalized_draft_sha256 = draft_sha256
        official_manifest.source_review_decisions_sha256 = review_sha256

        # Validate cấu trúc model trước khi ghi
        # Điều này đảm bảo model hợp lệ và khớp schema hoàn toàn
        NormalizedQuotationModel.model_validate(official_manifest.model_dump())

        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_export_built",
            quotation_id=package.quotation_id,
            details={"exported_item_count": official_manifest.item_count}
        )

        # 6. Atomic Write tệp normalized.json
        export_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = export_path.with_suffix(".tmp")
        
        manifest_dict = official_manifest.model_dump(mode="json")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        
        os.replace(tmp_path, export_path)

        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_export_written",
            quotation_id=package.quotation_id,
            details={"export_path": "normalized/normalized.json"}
        )

        # 7. Cập nhật package.json
        package.files.normalized_json = "normalized/normalized.json"
        package.updated_at = datetime.now(timezone.utc)
        write_json_file(package_path / "package.json", package)

        # 8. Gọi validate package toàn vẹn
        validate_package_integrity(package_path)

        log_event(
            package_path=package_path,
            level="INFO",
            event="normalized_export_completed",
            quotation_id=package.quotation_id,
            details={
                "export_summary": official_manifest.export_summary.model_dump() if official_manifest.export_summary else None
            }
        )

        return export_path

    except Exception as e:
        log_event(
            package_path=package_path,
            level="ERROR",
            event="normalized_export_failed",
            quotation_id=package.quotation_id,
            details={"error": str(e)}
        )
        raise e
