from __future__ import annotations

import sys

import scripts.external_signal_shadow.review_stage1_5h_v2_event_bundle_per_symbol_report as cli_mod
import src.research.external_signal_shadow.stage1_5h_read_only_report_generator as gen_mod
from tests.research.external_signal_shadow.test_stage1_5h_v2_event_bundle_per_symbol_report import (
    make_v2_bundle_fixture,
)


def test_v2_cli_seals_only_under_explicit_fresh_output_root(tmp_path, monkeypatch):
    reports_root = tmp_path / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(gen_mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)

    bundle, ids = make_v2_bundle_fixture(tmp_path)
    output_root = reports_root / "fresh_run_cli"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_v2_event_bundle_per_symbol_report.py",
        "--stage1-5g-summary", str(bundle.stage1_5g_summary_path),
        "--stage1-5g-quarantine-summary", str(bundle.quarantine_summary_path),
        "--depth-quality-input-rows", str(bundle.depth_quality_input_rows_path),
        "--quarantined-invalid-book-rows", str(bundle.quarantined_invalid_book_rows_path),
        "--governance-review", str(bundle.governance_review_path),
        "--output-root", str(output_root),
    ])

    ret = cli_mod.main()
    assert ret == 0
    assert (output_root / "stage1_5h_event_bundle_manifest.json").is_file()
    assert (output_root / "event_directory.json").is_file()
    for s in ids:
        assert (output_root / "reports" / f"{s}.json").is_file()
        assert (output_root / "reports" / f"{s}.md").is_file()


def test_v2_cli_rejects_invalid_bundle_without_final_manifest(tmp_path, monkeypatch):
    reports_root = tmp_path / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(gen_mod, "_STAGE1_5H_V2_REPORTS_ROOT", reports_root)

    bundle, _ = make_v2_bundle_fixture(tmp_path, mutation="foreign_row")
    output_root = reports_root / "foreign_run_cli"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_v2_event_bundle_per_symbol_report.py",
        "--stage1-5g-summary", str(bundle.stage1_5g_summary_path),
        "--stage1-5g-quarantine-summary", str(bundle.quarantine_summary_path),
        "--depth-quality-input-rows", str(bundle.depth_quality_input_rows_path),
        "--quarantined-invalid-book-rows", str(bundle.quarantined_invalid_book_rows_path),
        "--governance-review", str(bundle.governance_review_path),
        "--output-root", str(output_root),
    ])

    ret = cli_mod.main()
    assert ret == 1
    assert not (output_root / "stage1_5h_event_bundle_manifest.json").exists()


def test_v2_cli_rejects_outside_reports_root_without_monkeypatch(tmp_path, monkeypatch):
    bundle, _ = make_v2_bundle_fixture(tmp_path)
    output_root = tmp_path / "unauthorized_reports_root" / "fresh_run_cli"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_v2_event_bundle_per_symbol_report.py",
        "--stage1-5g-summary", str(bundle.stage1_5g_summary_path),
        "--stage1-5g-quarantine-summary", str(bundle.quarantine_summary_path),
        "--depth-quality-input-rows", str(bundle.depth_quality_input_rows_path),
        "--quarantined-invalid-book-rows", str(bundle.quarantined_invalid_book_rows_path),
        "--governance-review", str(bundle.governance_review_path),
        "--output-root", str(output_root),
    ])

    ret = cli_mod.main()
    assert ret == 1
    assert not output_root.exists()
