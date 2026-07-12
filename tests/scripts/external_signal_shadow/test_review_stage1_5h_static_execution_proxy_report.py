import json
import sys

from scripts.external_signal_shadow.review_stage1_5h_static_execution_proxy_report import main
from tests.research.external_signal_shadow.test_stage1_5h_read_only_report_generator import (
    make_stage1_5h_fixture,
)


def test_stage1_5h_cli_writes_summary_and_review(tmp_path, monkeypatch):
    paths = make_stage1_5h_fixture(tmp_path)
    output_root = tmp_path / "stage1_5h" / "reports" / "run1"
    summary_out = output_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_out = tmp_path / "docs" / "reviews" / "stage1_5h_report.md"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(paths[0]),
        "--stage1-5g-quarantine-summary", str(paths[1]),
        "--depth-quality-input-rows", str(paths[2]),
        "--quarantined-invalid-book-rows", str(paths[3]),
        "--governance-review", str(paths[4]),
        "--output-root", str(output_root),
        "--output-summary", str(summary_out),
        "--output-review", str(review_out),
    ])

    assert main() == 0
    assert summary_out.exists()
    assert review_out.exists()
    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    assert summary["decision"] == "stage1_5h_single_event_static_proxy_report_generated"
    assert summary["implementation_plan_allowed"] is False
    assert summary["implementation_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert "不能作为 paper/live" in review_out.read_text(encoding="utf-8")


def test_stage1_5h_cli_returns_nonzero_for_missing_required_input(tmp_path, monkeypatch):
    output_root = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(tmp_path / "missing.json"),
        "--stage1-5g-quarantine-summary", str(tmp_path / "missing_quarantine.json"),
        "--depth-quality-input-rows", str(tmp_path / "missing_valid.jsonl"),
        "--quarantined-invalid-book-rows", str(tmp_path / "missing_invalid.jsonl"),
        "--governance-review", str(tmp_path / "missing_review.md"),
        "--output-root", str(output_root),
    ])

    assert main() == 1


def test_cli_does_not_write_normal_review_markdown_when_governance_rejected(tmp_path, monkeypatch):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    output_root = tmp_path / "stage1_5h" / "reports" / "rejected"
    summary_out = output_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_out = tmp_path / "docs" / "reviews" / "stage1_5h_report.md"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(paths[0]),
        "--stage1-5g-quarantine-summary", str(paths[1]),
        "--depth-quality-input-rows", str(paths[2]),
        "--quarantined-invalid-book-rows", str(paths[3]),
        "--governance-review", str(paths[4]),
        "--output-root", str(output_root),
        "--output-summary", str(summary_out),
        "--output-review", str(review_out),
    ])

    assert main() == 1
    assert summary_out.exists()
    assert not review_out.exists()
