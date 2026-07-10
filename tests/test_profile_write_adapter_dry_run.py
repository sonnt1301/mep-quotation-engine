import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tools.feasibility.run_profile_write_adapter_dry_run import (  # noqa: E402
    build_review_item_key,
    convert_reviewed_items,
    run_adapter,
)


def sample_bridge_item(code="NXM-63S", price=800000, page=3):
    return {
        "supplier_code": "CHINT",
        "source_page": page,
        "source_layout_name": "chint_mccb_nxm_nm1",
        "source_material_code": code,
        "normalized_material_code": code,
        "description": f"MCCB Chint {code} 3P",
        "unit": "cái",
        "unit_price": price,
        "currency": "VND",
        "product_family": "MCCB Chint",
        "rated_current": "25÷63",
        "breaking_capacity": "25",
        "pole": "3P",
        "source_extraction_method": "coordinate_column_profiler",
        "source_evidence_text": f"25 ÷ 63 25 {code} {price:,}",
        "provenance": "Source PDF: test.pdf, Page: 3",
        "bridge_status": "bridged",
        "bridge_warnings": [],
    }


def decision_for(item, decision="APPROVE", **overrides):
    key = build_review_item_key(item)
    record = {
        "review_decision_id": f"DEC_{key}_1",
        "review_item_key": key,
        "review_mode": "All Bridged Items",
        "supplier_code": item["supplier_code"],
        "source_page": item["source_page"],
        "normalized_material_code_original": item["normalized_material_code"],
        "normalized_material_code_reviewed": item["normalized_material_code"],
        "description_original": item["description"],
        "description_reviewed": item["description"],
        "unit_original": item["unit"],
        "unit_reviewed": item["unit"],
        "quantity_reviewed": 1,
        "unit_price_original": item["unit_price"],
        "unit_price_reviewed": item["unit_price"],
        "amount_reviewed": item["unit_price"],
        "currency_original": item["currency"],
        "currency_reviewed": item["currency"],
        "decision": decision,
        "human_note": "test note" if decision != "APPROVE" else "",
        "reviewer": "human_reviewer",
        "reviewed_at": "2026-07-10T00:00:00Z",
        "provenance": item["provenance"],
        "source_evidence_text": item["source_evidence_text"],
    }
    record.update(overrides)
    return record


def test_convert_reviewed_items_exports_only_allowed_decisions():
    approved = sample_bridge_item("NXM-63S", 800000, 3)
    edited = sample_bridge_item("NXM-125S", 860000, 3)
    rejected = sample_bridge_item("NXM-250S", 1400000, 3)
    investigate = sample_bridge_item("NXM-400S", 4200000, 3)
    unreviewed = sample_bridge_item("NXM-630S", 6200000, 3)
    items = [approved, edited, rejected, investigate, unreviewed]

    decisions = {
        build_review_item_key(approved): decision_for(approved, "APPROVE"),
        build_review_item_key(edited): decision_for(
            edited,
            "EDIT_AND_APPROVE",
            unit_price_reviewed=900000,
            amount_reviewed=900000,
            human_note="Corrected price after PDF review",
        ),
        build_review_item_key(rejected): decision_for(rejected, "REJECT", human_note="Wrong row"),
        build_review_item_key(investigate): decision_for(
            investigate,
            "NEEDS_INVESTIGATION",
            human_note="Needs another reviewer",
        ),
    }

    exported, blocked, counts = convert_reviewed_items(items, decisions, "CHINT_20230301_001")

    assert len(exported) == 2
    assert len(blocked) == 3
    assert counts["approved_count"] == 1
    assert counts["edited_count"] == 1
    assert counts["rejected_count"] == 1
    assert counts["needs_investigation_count"] == 1
    assert counts["unreviewed_count"] == 1
    assert exported[1]["unit_price"] == 900000
    assert exported[1]["amount"] == 900000
    assert {b["block_reason"] for b in blocked} == {
        "human_rejected",
        "needs_investigation",
        "missing_human_approval",
    }


def test_write_key_is_not_supplier_plus_code_only():
    first = sample_bridge_item("NM1-125C", 800000, 3)
    second = sample_bridge_item("NM1-125C", 860000, 3)
    first_decision = decision_for(first, "APPROVE")
    second_decision = decision_for(second, "APPROVE")

    exported, _blocked, _counts = convert_reviewed_items(
        [first, second],
        {
            build_review_item_key(first): first_decision,
            build_review_item_key(second): second_decision,
        },
        "CHINT_20230301_001",
    )

    assert exported[0]["write_key"] != exported[1]["write_key"]
    assert exported[0]["write_key"].startswith("CHINT|NM1-125C|P3|800000|")
    assert exported[1]["write_key"].startswith("CHINT|NM1-125C|P3|860000|")


def make_tmp_dir(name):
    candidates = [
        Path(os.environ["MEP_TEST_TMP"]) if os.environ.get("MEP_TEST_TMP") else None,
        Path("C:/tmp"),
        Path.home() / "Documents" / "Codex" / "tmp",
        project_root / "scratch" / "pytest_tmp",
    ]
    dirname = f"mep_profile_write_adapter_{name}_{uuid.uuid4().hex}"
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


def test_run_adapter_writes_preview_outputs_and_keeps_write_disabled():
    tmp_path = make_tmp_dir("unit")
    approved = sample_bridge_item("NXM-63S", 800000, 3)
    blocked = sample_bridge_item("NXM-125S", 860000, 3)
    bridge_path = tmp_path / "profile_bridge_items.json"
    decisions_path = tmp_path / "profile_bridge_review_decisions.json"
    out_dir = tmp_path / "out"

    bridge_path.write_text(json.dumps([approved, blocked], ensure_ascii=False), encoding="utf-8")
    decisions_path.write_text(
        json.dumps(
            {
                build_review_item_key(approved): decision_for(approved, "APPROVE"),
                build_review_item_key(blocked): decision_for(
                    blocked,
                    "NEEDS_INVESTIGATION",
                    human_note="Need PDF check",
                ),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    try:
        manifest = run_adapter(bridge_path, decisions_path, out_dir, "CHINT_20230301_001")

        assert manifest["mode"] == "dry_run"
        assert manifest["ready_for_write_to_main_pipeline"] is False
        assert manifest["write_target"] == "normalized_json_preview_only"
        assert manifest["summary"]["exportable_items_count"] == 1
        assert manifest["summary"]["blocked_items_count"] == 1
        assert manifest["summary"]["proposed_status"] == "BLOCKED_NEEDS_HUMAN_REVIEW"
        assert (out_dir / "normalized_items_preview.json").exists()
        assert (out_dir / "blocked_items.json").exists()
        assert (out_dir / "profile_write_adapter_summary.json").exists()
        assert (out_dir / "profile_write_adapter_report.md").exists()
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_script_runs_with_missing_default_decisions_file():
    script = Path("tools/feasibility/run_profile_write_adapter_dry_run.py")
    out_dir = make_tmp_dir("script")
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", str(out_dir)],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        summary_path = out_dir / "profile_write_adapter_summary.json"
        assert summary_path.exists()
        data = json.loads(summary_path.read_text(encoding="utf-8"))
        assert data["ready_for_write_to_main_pipeline"] is False
        assert data["summary"]["input_bridge_items_count"] >= 0
        assert data["summary"]["exportable_items_count"] >= 0
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def test_contract_requires_write_disabled():
    contract = json.loads(
        Path("tools/feasibility/profile_write_adapter_contract.json").read_text(encoding="utf-8")
    )
    assert contract["properties"]["ready_for_write_to_main_pipeline"]["const"] is False
    assert "dry_run" in contract["properties"]["mode"]["enum"]
