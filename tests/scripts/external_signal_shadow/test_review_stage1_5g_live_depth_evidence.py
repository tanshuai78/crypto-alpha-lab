import json
import sys
from pathlib import Path
from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import (
    make_stage1_5f_fixture_root,
)
from scripts.external_signal_shadow.review_stage1_5g_live_depth_evidence import main


def test_stage1_5g_cli_writes_summary_and_review(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path)
    summary_out = tmp_path / "stage1_5g_summary.json"
    review_out = tmp_path / "stage1_5g_review.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-summary",
            str(summary_out),
            "--output-review",
            str(review_out),
        ],
    )

    assert main() == 0
    assert summary_out.exists()
    assert review_out.exists()

    data = json.loads(summary_out.read_text(encoding="utf-8"))
    assert "schema_version" in data
    assert data["trade_signal_allowed"] is False
    assert "Stage 1.5G" in review_out.read_text(encoding="utf-8")


def test_cli_does_not_write_inside_stage1_5f_output_root_by_default(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path / "stage1_5f_root")
    output_root = tmp_path / "stage1_5g" / "reviews" / "run1"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
        ],
    )

    assert main() == 0
    assert (output_root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
    assert not (root / "stage1_5g_live_depth_evidence_review_summary.json").exists()


def test_stage1_5g_cli_returns_nonzero_for_missing_output_root(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            "/nonexistent_path_abc_123",
        ],
    )
    assert main() != 0
