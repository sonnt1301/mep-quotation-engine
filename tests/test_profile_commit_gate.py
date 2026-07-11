import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import openpyxl


project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools.feasibility.export_profile_commit_gate import (  # noqa: E402
    APPROVAL_PHRASE,
    build_gate_manifest,
    export_commit_gate,
)


def make_tmp_dir(name):
    candidates = [
        Path(os.environ["MEP_TEST_TMP"]) if os.environ.get("MEP_TEST_TMP") else None,
        Path("C:/tmp"),
        Path.home() / "Documents" / "Codex" / "tmp",
        project_root / "scratch" / "pytest_tmp",
    ]
    dirname = f"mep_profile_commit_gate_{name}_{uuid.uuid4().hex}"
    last_error = None
    for base in candidates:
        if base is None:
            continue
        try:
            path = base / dirname
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as exc:
            last_error = exc
    raise last_error or OSError("No writable temporary directory found.")


def write_candidate_fixture(candidate_dir, summary_overrides=None, items=None):
    summary = {
        "candidate_version": "1.0.0",
        "generated_at": "2026-07-10T00:00:00Z",
        "mode": "dry_run",
        "ready_for_write_to_main_pipeline": False,
        "summary": {
            "candidate_items_count": 1,
            "skipped_items_count": 0,
            "duplicate_write_key_count": 0,
            "duplicate_material_code_count": 0,
            "proposed_status": "READY_FOR_HUMAN_COMMIT_REVIEW",
            "ready_for_write_to_main_pipeline": False,
            "reasons_not_ready_for_write": ["Manual approval required"],
        },
        "candidates": [],
        "warnings": [],
    }
    if summary_overrides:
        summary["summary"].update(summary_overrides)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "write_candidate_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False),
        encoding="utf-8",
    )
    (candidate_dir / "write_candidate_items.json").write_text(
        json.dumps(items if items is not None else [{"write_candidate_id": "WRITE_CANDIDATE_0001"}], ensure_ascii=False),
        encoding="utf-8",
    )
    for name in [
        "write_candidate_review.csv",
        "write_candidate_review.xlsx",
        "write_candidate_commit_plan.md",
    ]:
        (candidate_dir / name).write_text("fixture", encoding="utf-8")


def test_commit_gate_pending_for_ready_candidates_without_approval():
    tmp = make_tmp_dir("pending")
    try:
        candidate_dir = tmp / "candidate"
        write_candidate_fixture(candidate_dir)
        manifest = build_gate_manifest(candidate_dir)

        assert manifest["commit_gate_status"] == "PENDING_HUMAN_APPROVAL"
        assert manifest["ready_for_write_to_main_pipeline"] is False
        assert manifest["approval"]["approved"] is False
        assert manifest["blocking_reasons"] == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_commit_gate_blocks_empty_candidate_package():
    tmp = make_tmp_dir("blocked")
    try:
        candidate_dir = tmp / "candidate"
        write_candidate_fixture(
            candidate_dir,
            {
                "candidate_items_count": 0,
                "proposed_status": "BLOCKED_NEEDS_REVIEW",
            },
            items=[],
        )
        manifest = build_gate_manifest(candidate_dir)

        assert manifest["commit_gate_status"] == "BLOCKED_NEEDS_REVIEW"
        assert manifest["ready_for_write_to_main_pipeline"] is False
        assert "no_write_candidates" in manifest["blocking_reasons"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_commit_gate_approval_requires_exact_phrase_and_reviewer():
    tmp = make_tmp_dir("approval")
    try:
        candidate_dir = tmp / "candidate"
        write_candidate_fixture(candidate_dir)

        wrong = build_gate_manifest(
            candidate_dir,
            approve=True,
            approved_by="owner",
            approval_phrase="APPROVE",
        )
        assert wrong["commit_gate_status"] == "PENDING_HUMAN_APPROVAL"
        assert wrong["approval"]["approved"] is False

        approved = build_gate_manifest(
            candidate_dir,
            approve=True,
            approved_by="owner",
            approval_note="Reviewed candidate workbook",
            approval_phrase=APPROVAL_PHRASE,
        )
        assert approved["commit_gate_status"] == "APPROVED_FOR_NEXT_PHASE_DESIGN_ONLY"
        assert approved["approval"]["approved"] is True
        assert approved["ready_for_write_to_main_pipeline"] is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_export_commit_gate_outputs_manifest_csv_xlsx_md():
    tmp = make_tmp_dir("export")
    try:
        candidate_dir = tmp / "candidate"
        output_dir = tmp / "out"
        write_candidate_fixture(candidate_dir)
        manifest = export_commit_gate(candidate_dir, output_dir)

        assert manifest["ready_for_write_to_main_pipeline"] is False
        assert (output_dir / "profile_commit_gate_manifest.json").exists()
        assert (output_dir / "commit_gate_summary.csv").exists()
        assert (output_dir / "profile_commit_gate_review.xlsx").exists()
        assert (output_dir / "profile_commit_gate_checklist.md").exists()

        wb = openpyxl.load_workbook(output_dir / "profile_commit_gate_review.xlsx", read_only=True)
        assert set(wb.sheetnames) == {"Gate Summary", "Artifact Hashes", "Manual Checklist"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_script_runs_with_custom_output_dir():
    tmp = make_tmp_dir("script")
    try:
        candidate_dir = tmp / "candidate"
        output_dir = tmp / "out"
        write_candidate_fixture(candidate_dir)
        script = Path("tools/feasibility/export_profile_commit_gate.py")
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--candidate-dir",
                str(candidate_dir),
                "--output-dir",
                str(output_dir),
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        data = json.loads((output_dir / "profile_commit_gate_manifest.json").read_text(encoding="utf-8"))
        assert data["ready_for_write_to_main_pipeline"] is False
        assert data["commit_gate_status"] == "PENDING_HUMAN_APPROVAL"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_contract_requires_write_disabled():
    contract = json.loads(
        Path("tools/feasibility/profile_commit_gate_contract.json").read_text(encoding="utf-8")
    )
    assert contract["properties"]["ready_for_write_to_main_pipeline"]["const"] is False
    assert "APPROVED_FOR_NEXT_PHASE_DESIGN_ONLY" in contract["properties"]["commit_gate_status"]["enum"]
