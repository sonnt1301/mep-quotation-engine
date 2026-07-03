import os
import re
import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Tuple, Dict
from mep_quotation.spec.models import QuotationPackageModel

PROJECT_ROOT = Path(__file__).parent.parent.resolve()

def sanitize_filename(filename: str) -> str:
    """Lọc sạch tên file upload để loại bỏ path traversal và ký tự nguy hiểm."""
    # Chỉ giữ lại chữ cái, số, dấu gạch dưới, gạch ngang và dấu chấm
    name = Path(filename).name
    name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)
    # Loại bỏ các dấu chấm liên tiếp hoặc bắt đầu bằng dấu chấm để tránh ẩn file
    name = re.sub(r'\.+', '.', name)
    if name.startswith('.'):
        name = 'safe_' + name
    return name

def safe_load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    """Đọc tệp JSON an toàn, trả về (dữ liệu, thông báo lỗi)."""
    if not path.exists():
        return None, f"File not found: {path.name}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in {path.name}: {str(e)}"
    except Exception as e:
        return None, f"Error reading {path.name}: {str(e)}"

def run_cli_command(args: list, timeout: int = 600) -> Tuple[int, str, str]:
    """Chạy một lệnh CLI thông qua subprocess với các ràng buộc an toàn.
    
    Trả về: (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            args,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        # Nếu hết thời gian chờ, trả về stdout/stderr đã capture được kèm exit_code = -1
        stdout = e.stdout if e.stdout else ""
        stderr = e.stderr if e.stderr else f"Command timed out after {timeout} seconds."
        return -1, stdout, stderr
    except Exception as e:
        return -2, "", f"Failed to execute command: {str(e)}"

def resolve_artifact_paths(package_path: Path) -> Dict[str, Path]:
    """Phân giải đường dẫn artifacts.
    
    Ưu tiên đọc từ package.json.
    Nếu thiếu hoặc package.json chưa tồn tại, fallback về đường dẫn mặc định theo convention.
    """
    package_json_path = package_path / "package.json"
    
    # 1. Fallback Defaults
    paths = {
        "package_json": package_path / "package.json",
        "source_pdf": package_path / "source" / "original.pdf",
        "metadata": package_path / "source" / "metadata.json",
        "page_manifest": package_path / "source" / "page_manifest.json",
        "raw_text": package_path / "source" / "raw_text.json",
        "text_markdown": package_path / "text" / "quotation.md",
        "text_manifest": package_path / "text" / "quotation_text.json",
        "line_candidates": package_path / "parsed" / "line_candidates.json",
        "row_candidates": package_path / "parsed" / "row_candidates.json",
        "item_candidates": package_path / "parsed" / "item_candidates.json",
        "normalized_draft": package_path / "normalized" / "normalized_draft.json",
        "review_decisions": package_path / "review" / "review_decisions.json",
        "normalized_json": package_path / "normalized" / "normalized.json",
        "excel_export": package_path / "exports" / "quotation.xlsx",
        "excel_export_manifest": package_path / "exports" / "export_manifest.json",
    }
    
    # 2. Đọc từ package.json nếu có
    if package_json_path.exists():
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pkg = QuotationPackageModel.model_validate(data)
            
            # Map các trường từ files sang path cụ thể
            if pkg.files.source_pdf:
                paths["source_pdf"] = package_path / pkg.files.source_pdf
            if pkg.files.pdf_metadata:
                paths["metadata"] = package_path / pkg.files.pdf_metadata
            if pkg.files.page_manifest:
                paths["page_manifest"] = package_path / pkg.files.page_manifest
            if pkg.files.raw_text:
                paths["raw_text"] = package_path / pkg.files.raw_text
            if pkg.files.text_markdown:
                paths["text_markdown"] = package_path / pkg.files.text_markdown
            if pkg.files.text_manifest:
                paths["text_manifest"] = package_path / pkg.files.text_manifest
            if pkg.files.line_candidates:
                paths["line_candidates"] = package_path / pkg.files.line_candidates
            if pkg.files.row_candidates:
                paths["row_candidates"] = package_path / pkg.files.row_candidates
            if pkg.files.item_candidates:
                paths["item_candidates"] = package_path / pkg.files.item_candidates
            if pkg.files.normalized_draft:
                paths["normalized_draft"] = package_path / pkg.files.normalized_draft
            if pkg.files.review_decisions:
                paths["review_decisions"] = package_path / pkg.files.review_decisions
            if pkg.files.normalized_json:
                paths["normalized_json"] = package_path / pkg.files.normalized_json
            if pkg.files.excel_export:
                paths["excel_export"] = package_path / pkg.files.excel_export
            if pkg.files.excel_export_manifest:
                paths["excel_export_manifest"] = package_path / pkg.files.excel_export_manifest
        except Exception:
            # Nếu parse lỗi, giữ nguyên fallback defaults
            pass
            
    return paths
