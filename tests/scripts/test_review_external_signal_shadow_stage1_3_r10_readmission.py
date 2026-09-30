from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_r10_readmission import (
    APPROVED_DESIGN_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_PATH,
    APPROVED_PLAN_SHA256,
    STAGE1_3_R10_SYMBOLS,
    classify_r10_root,
    load_local_published_r10_receipt,
    verify_cli_source_code_integrity,
)
from scripts.review_external_signal_shadow_stage1_3_r10_readmission import (
    main as cli_main,
)


def _make_valid_manifest_dict(
    bars_sha: str = "a" * 64,
    bars_len: int = 1000,
    ledger_sha: str = "b" * 64,
    ledger_len: int = 500,
) -> dict:
    return {
        "schema_version": 1,
        "historical_run_identity": "test_historical_run_001",
        "historical_venue": "binance_proxy",
        "venue_proxy_used": True,
        "symbols": list(STAGE1_3_R10_SYMBOLS),
        "interval": "15m",
        "history_days": 180,
        "bar_count": 86400,
        "bars_sha256": bars_sha,
        "bars_byte_length": bars_len,
        "event_ledger_sha256": ledger_sha,
        "event_ledger_byte_length": ledger_len,
    }


def _create_canonical_git_fixture(tmp_path: Path, manifest_dict: dict | None = None) -> dict[str, str]:
    repo_dir = tmp_path / "fixture_git_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=repo_dir, check=True, capture_output=True)

    manifest_path_rel = "artifacts/historical_manifest.json"
    full_manifest_path = repo_dir / manifest_path_rel
    full_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    m_dict = manifest_dict or _make_valid_manifest_dict()
    full_manifest_path.write_text(json.dumps(m_dict), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: historical manifest"], cwd=repo_dir, check=True, capture_output=True)
    manifest_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    project_root = Path.cwd()
    review_src = project_root / "docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"
    summary_src = project_root / "reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"

    review_dest = repo_dir / "docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"
    summary_dest = repo_dir / "reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"
    review_dest.parent.mkdir(parents=True, exist_ok=True)
    summary_dest.parent.mkdir(parents=True, exist_ok=True)

    review_dest.write_bytes(review_src.read_bytes())
    summary_dest.write_bytes(summary_src.read_bytes())

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: historical boundary"], cwd=repo_dir, check=True, capture_output=True)
    boundary_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    return {
        "repo_dir": str(repo_dir),
        "manifest_commit": manifest_commit,
        "manifest_path": manifest_path_rel,
        "boundary_commit": boundary_commit,
    }


def _create_synthetic_bar_row(symbol: str, bar_start_ms: int) -> dict:
    bar = HistoricalBar(
        symbol=symbol,
        bar_start_ms=bar_start_ms,
        bar_end_ms=bar_start_ms + 15 * 60 * 1000,
        open_price=100.0,
        high_price=105.0,
        low_price=95.0,
        close_price=102.0,
        quote_volume=1000.0,
    )
    return {
        "symbol": bar.symbol,
        "bar_start_ms": bar.bar_start_ms,
        "bar_end_ms": bar.bar_end_ms,
        "open_price": bar.open_price,
        "high_price": bar.high_price,
        "low_price": bar.low_price,
        "close_price": bar.close_price,
        "quote_volume": bar.quote_volume,
    }


def _create_valid_bars_file(tmp_path: Path) -> Path:
    bars_file = tmp_path / "valid_bars.jsonl"
    start_base = 1700000000000
    interval = 15 * 60 * 1000
    with open(bars_file, "w", encoding="utf-8") as f:
        for symbol in STAGE1_3_R10_SYMBOLS:
            for i in range(17280):
                t_start = start_base + i * interval
                row = _create_synthetic_bar_row(symbol, t_start)
                f.write(json.dumps(row) + "\n")
    return bars_file


def _create_valid_ledger_file(tmp_path: Path) -> Path:
    ledger_file = tmp_path / "valid_ledger.jsonl"
    start_ms = 1700000000000
    end_ms = start_ms + 900000
    avail_ms = end_ms + 60000
    row = {
        "candidate_name": "volume_spike_1h",
        "symbol": "BTCUSDT",
        "source_bar_start_ms": start_ms,
        "source_bar_end_ms": end_ms,
        "event_available_at_ms": avail_ms,
    }
    ledger_file.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return ledger_file


def test_cli_evidence_gap_both_absent(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T130000Z"

    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--run-id", run_id,
        "--approved-design-path", APPROVED_DESIGN_PATH,
        "--approved-design-sha256", APPROVED_DESIGN_SHA256,
        "--approved-plan-path", APPROVED_PLAN_PATH,
        "--approved-plan-sha256", APPROVED_PLAN_SHA256,
    ])
    assert rc == 0

    final_root = parent_dir / run_id
    assert classify_r10_root(final_root) == "receipt_published"
    receipt = load_local_published_r10_receipt(final_root)
    assert receipt["readmission_status"] == "evidence_gap"
    assert sorted(receipt["evidence_gap_reasons"]) == ["event_ledger_absent", "historical_anchor_absent"]


def test_cli_prohibited_flag_rejected(tmp_path: Path):
    bars_file = _create_valid_bars_file(tmp_path)
    with pytest.raises(SystemExit):
        cli_main([
            "--bars-jsonl", str(bars_file),
            "--output", str(tmp_path / "out"),
        ])


def test_cli_open_spy_single_bars_open(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    ledger_file = _create_valid_ledger_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T140000Z"

    # Track opens of bars_file
    orig_open = open
    open_counts = {"bars": 0}

    def spy_open(file, *args, **kwargs):
        if str(file) == str(bars_file):
            open_counts["bars"] += 1
        return orig_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy_open)

    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--event-ledger-jsonl", str(ledger_file),
        "--run-id", run_id,
    ])
    assert rc == 0
    # Must be opened exactly once in read_structural_bars
    assert open_counts["bars"] == 1


def test_verify_cli_source_code_integrity():
    cli_path = Path("scripts/review_external_signal_shadow_stage1_3_r10_readmission.py")
    assert cli_path.is_file()
    source = cli_path.read_text(encoding="utf-8")
    assert verify_cli_source_code_integrity(source) is True


def test_cli_eligible_full_anchored(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    import hashlib
    bars_sha = hashlib.sha256(bars_file.read_bytes()).hexdigest()
    bars_len = os.path.getsize(bars_file)

    ledger_file = _create_valid_ledger_file(tmp_path)
    ledger_sha = hashlib.sha256(ledger_file.read_bytes()).hexdigest()
    ledger_len = os.path.getsize(ledger_file)

    manifest_dict = _make_valid_manifest_dict(
        bars_sha=bars_sha,
        bars_len=bars_len,
        ledger_sha=ledger_sha,
        ledger_len=ledger_len,
    )
    fixture = _create_canonical_git_fixture(tmp_path, manifest_dict=manifest_dict)

    fixture_repo_dir = Path(fixture["repo_dir"])
    monkeypatch.setattr(cli_mod, "_GIT_DIR", fixture_repo_dir)
    monkeypatch.setattr(cli_mod, "_BOUNDARY_COMMIT", fixture["boundary_commit"])

    run_id = "stage1_3_r10_readmission_20260929T150000Z"
    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--historical-manifest-git-commit", fixture["manifest_commit"],
        "--historical-manifest-git-path", fixture["manifest_path"],
        "--event-ledger-jsonl", str(ledger_file),
        "--run-id", run_id,
    ])
    assert rc == 0

    final_root = parent_dir / run_id
    assert classify_r10_root(final_root) == "receipt_published"
    receipt = load_local_published_r10_receipt(final_root)
    assert receipt["readmission_status"] == "eligible_for_exploratory_expectancy_design"
    assert receipt["evidence_gap_reasons"] == []
    assert receipt["input_identities"]["bars"]["matches_historical_manifest"] is True
    assert receipt["input_identities"]["event_ledger"]["matches_historical_manifest"] is True


def test_cli_partial_manifest_flags_fails(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T160000Z"

    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--historical-manifest-git-commit", "a" * 40,
        "--run-id", run_id,
    ])
    assert rc == 1
    assert not (parent_dir / run_id).exists()


def test_cli_corrupted_authority_fails(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T170000Z"

    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--run-id", run_id,
        "--approved-design-sha256", "0" * 64,
    ])
    assert rc == 1
    assert not (parent_dir / run_id).exists()


def test_cli_duplicate_final_root_fails(tmp_path: Path, monkeypatch):
    parent_dir = tmp_path / "receipts"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "DEFAULT_PARENT_DIR", parent_dir)

    bars_file = _create_valid_bars_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T180000Z"

    rc1 = cli_main([
        "--bars-jsonl", str(bars_file),
        "--run-id", run_id,
    ])
    assert rc1 == 0

    # Second invocation with same run_id must fail
    rc2 = cli_main([
        "--bars-jsonl", str(bars_file),
        "--run-id", run_id,
    ])
    assert rc2 == 1


def test_cli_output_root_anchored_regardless_of_caller_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    test_parent = tmp_path / "custom_parent"
    import scripts.review_external_signal_shadow_stage1_3_r10_readmission as cli_mod
    monkeypatch.setattr(cli_mod, "_TEST_PARENT_DIR", test_parent)

    bars_file = _create_valid_bars_file(tmp_path)
    run_id = "stage1_3_r10_readmission_20260929T190000Z"

    rc = cli_main([
        "--bars-jsonl", str(bars_file),
        "--run-id", run_id,
    ])
    assert rc == 0
    assert (test_parent / run_id / "r10_readmission_receipt.json").exists()
    # Confirm it did NOT write to tmp_path / data / ...
    assert not (tmp_path / "data").exists()
