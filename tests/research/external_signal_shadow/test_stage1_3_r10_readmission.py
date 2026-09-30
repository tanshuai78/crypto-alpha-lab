from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_r10_readmission import (
    APPROVED_DESIGN_PATH,
    APPROVED_DESIGN_SHA256,
    APPROVED_PLAN_PATH,
    APPROVED_PLAN_SHA256,
    STAGE1_3_R10_SYMBOLS,
    EventLedgerSnapshot,
    HistoricalManifestSnapshot,
    StructuralBarsSnapshot,
    build_r10_receipt_dict,
    classify_r10_root,
    load_local_published_r10_receipt,
    parse_event_ledger,
    publish_r10_receipt,
    read_historical_manifest_from_git,
    read_structural_bars,
    reduce_r10_readmission,
    validate_r10_receipt_dict,
    verify_authorities,
    verify_source_code_integrity,
)


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _create_synthetic_bar_row(
    symbol: str,
    bar_start_ms: int,
    bar_end_ms: int | None = None,
    open_price: float = 100.0,
    high_price: float = 105.0,
    low_price: float = 95.0,
    close_price: float = 102.0,
    quote_volume: float = 1000.0,
) -> dict:
    if bar_end_ms is None:
        bar_end_ms = bar_start_ms + 15 * 60 * 1000
    bar = HistoricalBar(
        symbol=symbol,
        bar_start_ms=bar_start_ms,
        bar_end_ms=bar_end_ms,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        quote_volume=quote_volume,
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


def _create_valid_bars_file(tmp_path: Path, count_per_symbol: int = 17280) -> Path:
    # 5 symbols * 17280 = 86400 bars (180 days of 15m bars: 180 * 96 = 17280)
    bars_file = tmp_path / "test_bars.jsonl"
    start_base = 1700000000000
    interval = 15 * 60 * 1000
    with open(bars_file, "w", encoding="utf-8") as f:
        for symbol in STAGE1_3_R10_SYMBOLS:
            for i in range(count_per_symbol):
                t_start = start_base + i * interval
                row = _create_synthetic_bar_row(symbol, t_start)
                f.write(json.dumps(row) + "\n")
    return bars_file


def test_verify_authorities_success():
    # Calling with frozen approved values must succeed
    result = verify_authorities(
        approved_design_path=APPROVED_DESIGN_PATH,
        approved_design_sha256=APPROVED_DESIGN_SHA256,
        approved_plan_path=APPROVED_PLAN_PATH,
        approved_plan_sha256=APPROVED_PLAN_SHA256,
    )
    assert result is True


def test_verify_authorities_design_sha_mismatch():
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_design_approval_mismatch"):
        verify_authorities(
            approved_design_path=APPROVED_DESIGN_PATH,
            approved_design_sha256="0" * 64,
            approved_plan_path=APPROVED_PLAN_PATH,
            approved_plan_sha256=APPROVED_PLAN_SHA256,
        )


def test_verify_authorities_plan_sha_mismatch():
    with pytest.raises(RuntimeError, match="STOP=approved_authority_mismatch"):
        verify_authorities(
            approved_design_path=APPROVED_DESIGN_PATH,
            approved_design_sha256=APPROVED_DESIGN_SHA256,
            approved_plan_path=APPROVED_PLAN_PATH,
            approved_plan_sha256="0" * 64,
        )


def test_read_structural_bars_positive(tmp_path: Path):
    bars_file = _create_valid_bars_file(tmp_path)
    snapshot = read_structural_bars(bars_file)
    assert isinstance(snapshot, StructuralBarsSnapshot)
    assert snapshot.bar_count == 86400
    assert snapshot.bars_byte_length == os.path.getsize(bars_file)
    with open(bars_file, "rb") as f:
        assert snapshot.bars_sha256 == _sha256_bytes(f.read())
    assert set(snapshot.symbol_coverage.keys()) == set(STAGE1_3_R10_SYMBOLS)
    for cov in snapshot.symbol_coverage.values():
        assert cov >= 0.98

    # Ensure snapshot contains NO OHLCV or path fields
    for field_name in snapshot.__dataclass_fields__:
        assert field_name in {"bars_sha256", "bars_byte_length", "bar_count", "symbol_coverage", "time_index"}


def test_read_structural_bars_symlink_rejected(tmp_path: Path):
    bars_file = _create_valid_bars_file(tmp_path, count_per_symbol=10)
    symlink_file = tmp_path / "bars_symlink.jsonl"
    os.symlink(bars_file, symlink_file)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid:symlink_detected"):
        read_structural_bars(symlink_file)


def test_read_structural_bars_wrong_duration(tmp_path: Path):
    bars_file = tmp_path / "wrong_duration.jsonl"
    row = {
        "symbol": "BTCUSDT",
        "bar_start_ms": 1700000000000,
        "bar_end_ms": 1700000000000 + 5 * 60 * 1000,
        "open_price": 100.0,
        "high_price": 105.0,
        "low_price": 95.0,
        "close_price": 102.0,
        "quote_volume": 1000.0,
    }
    bars_file.write_text(json.dumps(row) + "\n")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid"):
        read_structural_bars(bars_file)


def test_read_structural_bars_duplicate_start(tmp_path: Path):
    bars_file = tmp_path / "dup_bars.jsonl"
    r1 = _create_synthetic_bar_row("BTCUSDT", 1700000000000)
    r2 = _create_synthetic_bar_row("BTCUSDT", 1700000000000)
    bars_file.write_text(json.dumps(r1) + "\n" + json.dumps(r2) + "\n")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid:duplicate_bar_start"):
        read_structural_bars(bars_file)


def test_read_structural_bars_wrong_symbols(tmp_path: Path):
    bars_file = tmp_path / "wrong_syms.jsonl"
    # Using ADAUSDT which is not in STAGE1_3_R10_SYMBOLS
    r = _create_synthetic_bar_row("ADAUSDT", 1700000000000)
    bars_file.write_text(json.dumps(r) + "\n")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid:symbol_universe_mismatch"):
        read_structural_bars(bars_file)


def test_read_structural_bars_wrong_total_count(tmp_path: Path):
    # Only 5 bars instead of 86400
    bars_file = tmp_path / "short_bars.jsonl"
    with open(bars_file, "w") as f:
        for sym in STAGE1_3_R10_SYMBOLS:
            f.write(json.dumps(_create_synthetic_bar_row(sym, 1700000000000)) + "\n")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid:bar_count_mismatch"):
        read_structural_bars(bars_file)


def test_read_structural_bars_malformed_json(tmp_path: Path):
    bars_file = tmp_path / "malformed.jsonl"
    bars_file.write_text("{\"symbol\": \"BTCUSDT\", invalid json\n")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid:bars_parse_failed"):
        read_structural_bars(bars_file)


def test_read_structural_bars_insufficient_coverage(tmp_path: Path):
    # If a gap is introduced so coverage < 0.98
    bars_file = tmp_path / "gap_bars.jsonl"
    start_base = 1700000000000
    interval = 15 * 60 * 1000
    with open(bars_file, "w", encoding="utf-8") as f:
        for symbol in STAGE1_3_R10_SYMBOLS:
            # Drop 500 bars for BTCUSDT to make coverage < 0.98
            skip = 500 if symbol == "BTCUSDT" else 0
            for i in range(17280):
                if skip > 0 and 1000 <= i < 1500:
                    continue
                t_start = start_base + i * interval
                row = _create_synthetic_bar_row(symbol, t_start)
                f.write(json.dumps(row) + "\n")
    # Will fail either on count or coverage
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_input_invalid"):
        read_structural_bars(bars_file)


def test_verify_source_code_integrity_clean():
    clean_code = """
import hashlib
import json
from pathlib import Path
from research.external_signal_shadow.stage1_3_models import HistoricalBar
def my_func(x):
    return x
"""
    assert verify_source_code_integrity(clean_code) is True


def test_verify_source_code_integrity_forbidden_import():
    bad_code = """
from research.external_signal_shadow.stage1_3_orchestrator import run_orchestrator
"""
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:stage1_3_orchestrator"):
        verify_source_code_integrity(bad_code)


def test_verify_source_code_integrity_forbidden_function_reference():
    bad_code = """
def compute():
    return compute_forward_metrics_from_entry_index()
"""
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:compute_forward_metrics_from_entry_index"):
        verify_source_code_integrity(bad_code)


def test_verify_source_code_integrity_forbidden_network_client():
    bad_code = """
import urllib.request
"""
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_outcome_path_detected:forbidden_reference:urllib.request"):
        verify_source_code_integrity(bad_code)


# ─── TASK 2 CANONICAL FIXTURE FACTORY & TESTS ─────────────────────────────

def _make_valid_manifest_dict(
    bars_sha: str = "a" * 64,
    bars_len: int = 1000,
    ledger_sha: str = "b" * 64,
    ledger_len: int = 500,
) -> dict[str, Any]:
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


def _create_canonical_git_fixture(
    tmp_path: Path,
    manifest_dict: dict[str, Any] | None = None,
    corrupt_review_blob: bool = False,
    corrupt_summary_blob: bool = False,
) -> dict[str, str]:
    repo_dir = tmp_path / "fixture_git_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=repo_dir, check=True, capture_output=True)

    # 1. Commit 1: Historical manifest
    manifest_path_rel = "artifacts/historical_manifest.json"
    full_manifest_path = repo_dir / manifest_path_rel
    full_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    m_dict = manifest_dict or _make_valid_manifest_dict()
    full_manifest_path.write_text(json.dumps(m_dict), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: historical manifest"], cwd=repo_dir, check=True, capture_output=True)
    manifest_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    # 2. Commit 2: Boundary commit with exact review and summary bytes
    project_root = Path.cwd()
    review_src = project_root / "docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"
    summary_src = project_root / "reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"

    review_dest = repo_dir / "docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md"
    summary_dest = repo_dir / "reports/external_signal_shadow/stage1_3_candidate_signal_discovery_summary.json"
    review_dest.parent.mkdir(parents=True, exist_ok=True)
    summary_dest.parent.mkdir(parents=True, exist_ok=True)

    review_bytes = review_src.read_bytes()
    if corrupt_review_blob:
        review_bytes += b"X"
    review_dest.write_bytes(review_bytes)

    summary_bytes = summary_src.read_bytes()
    if corrupt_summary_blob:
        summary_bytes += b"X"
    summary_dest.write_bytes(summary_bytes)

    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: historical boundary"], cwd=repo_dir, check=True, capture_output=True)
    boundary_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    return {
        "repo_dir": str(repo_dir),
        "manifest_commit": manifest_commit,
        "manifest_path": manifest_path_rel,
        "boundary_commit": boundary_commit,
    }


def test_read_historical_manifest_both_absent():
    res = read_historical_manifest_from_git(None, None)
    assert res is None


def test_read_historical_manifest_partial_flags():
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:partial_manifest_flags"):
        read_historical_manifest_from_git("a" * 40, None)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:partial_manifest_flags"):
        read_historical_manifest_from_git(None, "manifest.json")


def test_read_historical_manifest_positive(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path)
    res = read_historical_manifest_from_git(
        fixture["manifest_commit"],
        fixture["manifest_path"],
        boundary_commit=fixture["boundary_commit"],
        repo_root=Path(fixture["repo_dir"]),
    )
    assert isinstance(res, HistoricalManifestSnapshot)
    assert res.manifest_git_commit == fixture["manifest_commit"]
    assert res.manifest_git_path == fixture["manifest_path"]
    assert res.historical_run_identity == "test_historical_run_001"
    assert res.bars_sha256 == "a" * 64
    assert res.bars_byte_length == 1000
    assert res.event_ledger_sha256 == "b" * 64
    assert res.event_ledger_byte_length == 500


def test_read_historical_manifest_boundary_corrupted(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path, corrupt_review_blob=True)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_authority_mismatch:boundary_review_blob_mismatch"):
        read_historical_manifest_from_git(
            fixture["manifest_commit"],
            fixture["manifest_path"],
            boundary_commit=fixture["boundary_commit"],
            repo_root=Path(fixture["repo_dir"]),
        )


def test_read_historical_manifest_commit_equals_boundary(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_commit_equals_boundary"):
        read_historical_manifest_from_git(
            fixture["boundary_commit"],
            fixture["manifest_path"],
            boundary_commit=fixture["boundary_commit"],
            repo_root=Path(fixture["repo_dir"]),
        )


def test_read_historical_manifest_not_an_ancestor(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path)
    # Create an independent branch/commit that is not ancestor of boundary
    repo_dir = Path(fixture["repo_dir"])
    subprocess.run(["git", "checkout", "--orphan", "orphan_branch"], cwd=repo_dir, check=True, capture_output=True)
    (repo_dir / "other.txt").write_text("other")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "orphan commit"], cwd=repo_dir, check=True, capture_output=True)
    orphan_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:not_an_ancestor_of_boundary"):
        read_historical_manifest_from_git(
            orphan_commit,
            fixture["manifest_path"],
            boundary_commit=fixture["boundary_commit"],
            repo_root=repo_dir,
        )


def test_read_historical_manifest_invalid_commit_format(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path)
    repo_dir = Path(fixture["repo_dir"])
    for invalid_ref in ["main", "HEAD", "HEAD~1", fixture["manifest_commit"][:7], fixture["manifest_commit"].upper(), "not-a-hash"]:
        with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:invalid_commit_format"):
            read_historical_manifest_from_git(
                invalid_ref,
                fixture["manifest_path"],
                boundary_commit=fixture["boundary_commit"],
                repo_root=repo_dir,
            )


def test_read_historical_manifest_unreadable_path(tmp_path: Path):
    fixture = _create_canonical_git_fixture(tmp_path)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:git_show_failed"):
        read_historical_manifest_from_git(
            fixture["manifest_commit"],
            "nonexistent/manifest.json",
            boundary_commit=fixture["boundary_commit"],
            repo_root=Path(fixture["repo_dir"]),
        )


def test_read_historical_manifest_extra_or_missing_keys(tmp_path: Path):
    # Missing key
    m_missing = _make_valid_manifest_dict()
    del m_missing["interval"]
    fix1 = _create_canonical_git_fixture(tmp_path / "sub1", manifest_dict=m_missing)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid"):
        read_historical_manifest_from_git(
            fix1["manifest_commit"],
            fix1["manifest_path"],
            boundary_commit=fix1["boundary_commit"],
            repo_root=Path(fix1["repo_dir"]),
        )

    # Extra key
    m_extra = _make_valid_manifest_dict()
    m_extra["extra_key"] = "forbidden"
    fix2 = _create_canonical_git_fixture(tmp_path / "sub2", manifest_dict=m_extra)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid"):
        read_historical_manifest_from_git(
            fix2["manifest_commit"],
            fix2["manifest_path"],
            boundary_commit=fix2["boundary_commit"],
            repo_root=Path(fix2["repo_dir"]),
        )


def test_read_historical_manifest_wrong_types(tmp_path: Path):
    m_wrong = _make_valid_manifest_dict()
    m_wrong["venue_proxy_used"] = 1  # Should be bool True, not int 1
    fix = _create_canonical_git_fixture(tmp_path, manifest_dict=m_wrong)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:manifest_schema_invalid"):
        read_historical_manifest_from_git(
            fix["manifest_commit"],
            fix["manifest_path"],
            boundary_commit=fix["boundary_commit"],
            repo_root=Path(fix["repo_dir"]),
        )


# ─── TASK 3 EVENT LEDGER & REDUCER TESTS ─────────────────────────────────

def _make_valid_event_row(
    candidate_name: str = "volume_spike_1h",
    symbol: str = "BTCUSDT",
    start_ms: int = 1700000000000,
) -> dict[str, Any]:
    end_ms = start_ms + 15 * 60 * 1000
    avail_ms = end_ms + 60000
    return {
        "candidate_name": candidate_name,
        "symbol": symbol,
        "source_bar_start_ms": start_ms,
        "source_bar_end_ms": end_ms,
        "event_available_at_ms": avail_ms,
    }


def _create_event_ledger_file(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    ledger_file = tmp_path / "event_ledger.jsonl"
    with open(ledger_file, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return ledger_file


def test_parse_event_ledger_none():
    snap = StructuralBarsSnapshot("a" * 64, 100, 10, {}, ())
    assert parse_event_ledger(None, snap) is None


def test_parse_event_ledger_positive(tmp_path: Path):
    start = 1700000000000
    end = start + 900000
    time_index = (
        ("BTCUSDT", start, end),
        ("ETHUSDT", start, end),
    )
    snap = StructuralBarsSnapshot("a" * 64, 100, 2, {}, time_index)

    rows = [
        _make_valid_event_row("relative_strength_vs_btc", "ETHUSDT", start),
        _make_valid_event_row("volume_spike_1h", "BTCUSDT", start),
    ]
    # Sorted by (candidate_name, symbol, event_available_at_ms)
    rows_sorted = sorted(rows, key=lambda r: (r["candidate_name"], r["symbol"], r["event_available_at_ms"]))
    ledger_file = _create_event_ledger_file(tmp_path, rows_sorted)

    res = parse_event_ledger(ledger_file, snap)
    assert isinstance(res, EventLedgerSnapshot)
    assert res.event_count == 2
    assert res.ledger_byte_length == os.path.getsize(ledger_file)
    assert res.ledger_sha256 == _sha256_bytes(ledger_file.read_bytes())


def test_parse_event_ledger_extra_key(tmp_path: Path):
    start = 1700000000000
    end = start + 900000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", start, end),))
    row = _make_valid_event_row("volume_spike_1h", "BTCUSDT", start)
    row["forward_return"] = 0.05
    ledger_file = _create_event_ledger_file(tmp_path, [row])
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:forbidden_or_extra_keys"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_unknown_candidate(tmp_path: Path):
    start = 1700000000000
    end = start + 900000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", start, end),))
    row = _make_valid_event_row("unknown_candidate", "BTCUSDT", start)
    ledger_file = _create_event_ledger_file(tmp_path, [row])
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:unknown_candidate_name"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_btc_relative_strength_rejected(tmp_path: Path):
    start = 1700000000000
    end = start + 900000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", start, end),))
    row = _make_valid_event_row("relative_strength_vs_btc", "BTCUSDT", start)
    ledger_file = _create_event_ledger_file(tmp_path, [row])
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:btc_cannot_emit_relative_strength"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_unsorted(tmp_path: Path):
    start1 = 1700000000000
    start2 = start1 + 900000
    snap = StructuralBarsSnapshot("a" * 64, 100, 2, {}, (("BTCUSDT", start1, start1 + 900000), ("BTCUSDT", start2, start2 + 900000)))
    rows = [
        _make_valid_event_row("volume_spike_1h", "BTCUSDT", start2),
        _make_valid_event_row("volume_spike_1h", "BTCUSDT", start1),
    ]
    ledger_file = _create_event_ledger_file(tmp_path, rows)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:not_strictly_ordered_or_duplicate"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_duplicate(tmp_path: Path):
    start = 1700000000000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", start, start + 900000),))
    rows = [
        _make_valid_event_row("volume_spike_1h", "BTCUSDT", start),
        _make_valid_event_row("volume_spike_1h", "BTCUSDT", start),
    ]
    ledger_file = _create_event_ledger_file(tmp_path, rows)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:not_strictly_ordered_or_duplicate"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_wrong_lag(tmp_path: Path):
    start = 1700000000000
    end = start + 900000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", start, end),))
    row = _make_valid_event_row("volume_spike_1h", "BTCUSDT", start)
    row["event_available_at_ms"] = end + 30000  # wrong lag (should be 60000)
    ledger_file = _create_event_ledger_file(tmp_path, [row])
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:availability_lag_mismatch"):
        parse_event_ledger(ledger_file, snap)


def test_parse_event_ledger_no_matching_bar(tmp_path: Path):
    start = 1700000000000
    snap = StructuralBarsSnapshot("a" * 64, 100, 1, {}, (("BTCUSDT", 1800000000000, 1800000000000 + 900000),))
    row = _make_valid_event_row("volume_spike_1h", "BTCUSDT", start)
    ledger_file = _create_event_ledger_file(tmp_path, [row])
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_event_ledger_invalid:no_matching_bar_in_snapshot"):
        parse_event_ledger(ledger_file, snap)


# Reducer tests
def test_reduce_r10_readmission_both_absent():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    res = reduce_r10_readmission(bars_snap, None, None)
    assert res.readmission_status == "evidence_gap"
    assert res.evidence_gap_reasons == ("event_ledger_absent", "historical_anchor_absent")
    assert res.bars_provided is True
    assert res.bars_matches_historical_manifest is False
    assert res.event_ledger_provided is False
    assert res.historical_anchor_status == "absent"


def test_reduce_r10_readmission_anchor_absent_ledger_present():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    ledger_snap = EventLedgerSnapshot("b" * 64, 500, 10, ())
    res = reduce_r10_readmission(bars_snap, None, ledger_snap)
    assert res.readmission_status == "evidence_gap"
    assert res.evidence_gap_reasons == ("historical_anchor_absent",)
    assert res.bars_matches_historical_manifest is False
    assert res.event_ledger_provided is True
    assert res.event_ledger_matches_historical_manifest is False
    assert res.historical_anchor_status == "absent"


def test_reduce_r10_readmission_anchor_present_ledger_absent():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    res = reduce_r10_readmission(bars_snap, manifest_snap, None)
    assert res.readmission_status == "evidence_gap"
    assert res.evidence_gap_reasons == ("event_ledger_absent",)
    assert res.bars_matches_historical_manifest is True
    assert res.event_ledger_provided is False
    assert res.historical_anchor_status == "anchored"


def test_reduce_r10_readmission_eligible():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    ledger_snap = EventLedgerSnapshot("b" * 64, 500, 10, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    res = reduce_r10_readmission(bars_snap, manifest_snap, ledger_snap)
    assert res.readmission_status == "eligible_for_exploratory_expectancy_design"
    assert res.evidence_gap_reasons == ()
    assert res.bars_matches_historical_manifest is True
    assert res.event_ledger_matches_historical_manifest is True
    assert res.historical_anchor_status == "anchored"


def test_reduce_r10_readmission_bars_hash_mismatch():
    bars_snap = StructuralBarsSnapshot("0" * 64, 1000, 86400, {}, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:bars_manifest_hash_or_length_mismatch"):
        reduce_r10_readmission(bars_snap, manifest_snap, None)


def test_reduce_r10_readmission_ledger_hash_mismatch():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    ledger_snap = EventLedgerSnapshot("0" * 64, 500, 10, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_historical_anchor_invalid:event_ledger_manifest_hash_or_length_mismatch"):
        reduce_r10_readmission(bars_snap, manifest_snap, ledger_snap)


# ─── TASK 4 RECEIPT, PUBLICATION & LOADER TESTS ───────────────────────────

VALID_TEST_RUN_ID = "stage1_3_r10_readmission_20260929T120000Z"


def test_build_and_validate_receipt_eligible():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    ledger_snap = EventLedgerSnapshot("b" * 64, 500, 10, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    red = reduce_r10_readmission(bars_snap, manifest_snap, ledger_snap)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)
    assert validate_r10_receipt_dict(receipt) is True
    assert receipt["readmission_status"] == "eligible_for_exploratory_expectancy_design"
    assert receipt["authority_flags"]["RISK_LIVE_TRADING_ENABLED"] is False
    assert len(receipt["authority_flags"]) == 19
    for v in receipt["authority_flags"].values():
        assert v is False


def test_validate_receipt_deny_vector_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # 1. Missing deny vector key
    r_missing = json.loads(json.dumps(receipt))
    del r_missing["authority_flags"]["live_trading_allowed"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:deny_vector_keys_mismatch"):
        validate_r10_receipt_dict(r_missing)

    # 2. Extra deny vector key
    r_extra = json.loads(json.dumps(receipt))
    r_extra["authority_flags"]["extra_flag"] = False
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:deny_vector_keys_mismatch"):
        validate_r10_receipt_dict(r_extra)

    # 3. True deny vector key
    r_true = json.loads(json.dumps(receipt))
    r_true["authority_flags"]["alpha_interpretation_allowed"] = True
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:deny_vector_flag_must_be_false"):
        validate_r10_receipt_dict(r_true)


def test_validate_receipt_cross_field_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    ledger_snap = EventLedgerSnapshot("b" * 64, 500, 10, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    red = reduce_r10_readmission(bars_snap, manifest_snap, ledger_snap)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Violate §8.2.1: eligible status but bars.matches_historical_manifest is False
    r_mut = json.loads(json.dumps(receipt))
    r_mut["input_identities"]["bars"]["matches_historical_manifest"] = False
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:cross_field_mismatch"):
        validate_r10_receipt_dict(r_mut)


def test_validate_receipt_nested_authority_packet_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # 1. Extra authority_packet key
    r1 = json.loads(json.dumps(receipt))
    r1["authority_packet"]["extra_key"] = "extra_value"
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:authority_packet_mismatch"):
        validate_r10_receipt_dict(r1)

    # 2. Missing authority_packet key
    r2 = json.loads(json.dumps(receipt))
    del r2["authority_packet"]["approved_design_sha256"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:authority_packet_mismatch"):
        validate_r10_receipt_dict(r2)

    # 3. Forged authority hash
    for key in (
        "approved_design_sha256",
        "historical_audit_sha256",
        "stage1_3_review_sha256",
        "stage1_3_summary_sha256",
        "stage1_3_summary_code_sha256",
        "stage1_3_candidates_code_sha256",
        "stage1_3_runner_sha256",
        "l2_sha256",
        "historical_review_commit",
    ):
        r_forged = json.loads(json.dumps(receipt))
        r_forged["authority_packet"][key] = "f" * len(r_forged["authority_packet"][key])
        with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:(authority_packet_mismatch|boundary_commit_mismatch)"):
            validate_r10_receipt_dict(r_forged)


def test_validate_receipt_nested_historical_anchor_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Extra key
    r1 = json.loads(json.dumps(receipt))
    r1["historical_anchor"]["extra_key"] = "extra"
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch"):
        validate_r10_receipt_dict(r1)

    # Missing key
    r2 = json.loads(json.dumps(receipt))
    del r2["historical_anchor"]["manifest_git_commit"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch"):
        validate_r10_receipt_dict(r2)

    # Absent status but fields are not null
    r3 = json.loads(json.dumps(receipt))
    r3["historical_anchor"]["manifest_git_commit"] = "0" * 40
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch"):
        validate_r10_receipt_dict(r3)

    # Anchored status with null fields
    ledger_snap = EventLedgerSnapshot("b" * 64, 500, 10, ())
    manifest_snap = HistoricalManifestSnapshot("c" * 40, "p.json", "d" * 64, "run1", "a" * 64, 1000, "b" * 64, 500)
    red_anchored = reduce_r10_readmission(bars_snap, manifest_snap, ledger_snap)
    receipt_anchored = build_r10_receipt_dict(VALID_TEST_RUN_ID, red_anchored)

    r4 = json.loads(json.dumps(receipt_anchored))
    r4["historical_anchor"]["manifest_git_commit"] = None
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:historical_anchor_mismatch"):
        validate_r10_receipt_dict(r4)


def test_validate_receipt_nested_input_identities_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Extra key in input_identities
    r1 = json.loads(json.dumps(receipt))
    r1["input_identities"]["extra_input"] = {}
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch"):
        validate_r10_receipt_dict(r1)

    # Extra key in bars
    r2 = json.loads(json.dumps(receipt))
    r2["input_identities"]["bars"]["extra_key"] = 123
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch"):
        validate_r10_receipt_dict(r2)

    # Extra key in event_ledger
    r3 = json.loads(json.dumps(receipt))
    r3["input_identities"]["event_ledger"]["extra_key"] = 123
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:input_identities_mismatch"):
        validate_r10_receipt_dict(r3)


def test_validate_receipt_nested_candidate_scope_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Extra candidate
    r1 = json.loads(json.dumps(receipt))
    r1["candidate_scope"].append("forged_candidate")
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:candidate_scope_mismatch"):
        validate_r10_receipt_dict(r1)

    # Missing candidate
    r2 = json.loads(json.dumps(receipt))
    r2["candidate_scope"] = ["volume_spike_1h"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:candidate_scope_mismatch"):
        validate_r10_receipt_dict(r2)

    # Permuted candidate order
    r3 = json.loads(json.dumps(receipt))
    r3["candidate_scope"] = ["relative_strength_vs_btc", "volume_spike_1h"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:candidate_scope_mismatch"):
        validate_r10_receipt_dict(r3)


def test_validate_receipt_nested_fixed_rule_identity_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Extra key
    r1 = json.loads(json.dumps(receipt))
    r1["fixed_rule_identity"]["extra_rule"] = "fake"
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch"):
        validate_r10_receipt_dict(r1)

    # Mutated parameter (e.g. volume_spike_threshold changed from 3 to 2)
    r2 = json.loads(json.dumps(receipt))
    r2["fixed_rule_identity"]["volume_spike_threshold"] = 2
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch"):
        validate_r10_receipt_dict(r2)

    # Mutated symbol universe
    r3 = json.loads(json.dumps(receipt))
    r3["fixed_rule_identity"]["symbol_universe"] = ["BTCUSDT"]
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:fixed_rule_identity_mismatch"):
        validate_r10_receipt_dict(r3)


def test_validate_receipt_nested_pit_checks_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Extra key
    r1 = json.loads(json.dumps(receipt))
    r1["pit_checks"]["extra_check"] = True
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:pit_checks_mismatch"):
        validate_r10_receipt_dict(r1)

    # Forged outcome accessed
    r2 = json.loads(json.dumps(receipt))
    r2["pit_checks"]["post_event_outcome_accessed"] = True
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:outcome_accessed_must_be_false"):
        validate_r10_receipt_dict(r2)

    # Forged PIT status when event ledger absent
    r3 = json.loads(json.dumps(receipt))
    r3["pit_checks"]["event_identity_status"] = "valid"
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:pit_checks_mismatch"):
        validate_r10_receipt_dict(r3)


def test_validate_receipt_created_at_utc_mutations():
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    # Invalid timestamp
    r1 = json.loads(json.dumps(receipt))
    r1["created_at_utc"] = "2026-09-29 12:00:00"
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:invalid_created_at_utc"):
        validate_r10_receipt_dict(r1)


def test_publish_and_load_r10_receipt_lifecycle(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    final_root = parent_dir / VALID_TEST_RUN_ID
    assert classify_r10_root(final_root) == "before_start"

    # Publish
    pub_root = publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir)
    assert pub_root == final_root
    assert classify_r10_root(final_root) == "receipt_published"

    # Files must be exactly two
    files = sorted(p.name for p in final_root.iterdir())
    assert files == ["SHA256SUMS", "r10_readmission_receipt.json"]

    # Load
    loaded = load_local_published_r10_receipt(final_root)
    assert loaded["run_id"] == VALID_TEST_RUN_ID
    assert loaded["readmission_status"] == "evidence_gap"


def test_publish_r10_receipt_invalid_run_id(tmp_path: Path):
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:invalid_run_id"):
        publish_r10_receipt("invalid_run_id", receipt, parent_dir=tmp_path)


def test_publish_r10_receipt_preexisting_final_root(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    final_root = parent_dir / VALID_TEST_RUN_ID
    final_root.mkdir(parents=True)
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)
    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists"):
        publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir)


def test_publish_r10_receipt_crash_before_rename(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    def hook_before():
        raise RuntimeError("Crash before rename")

    with pytest.raises(RuntimeError, match="Crash before rename"):
        publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir, hook_before_rename=hook_before)

    final_root = parent_dir / VALID_TEST_RUN_ID
    assert classify_r10_root(final_root) == "before_start"
    assert not final_root.exists()


def test_publish_r10_receipt_crash_after_rename(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    def hook_after():
        raise RuntimeError("Crash after rename")

    with pytest.raises(RuntimeError, match="Crash after rename"):
        publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir, hook_after_rename=hook_after)

    final_root = parent_dir / VALID_TEST_RUN_ID
    # Final root was already renamed before hook_after, so state is receipt_published!
    assert classify_r10_root(final_root) == "receipt_published"


def test_load_local_published_r10_receipt_future_consumer_fail_closed(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)
    final_root = publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir)

    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_future_consumer_binding_missing"):
        load_local_published_r10_receipt(final_root, future_consumer_allowed=True)


def test_classify_r10_root_broken_symlink(tmp_path: Path):
    broken_symlink = tmp_path / "broken_link"
    os.symlink(tmp_path / "nonexistent_target", broken_symlink)
    assert broken_symlink.is_symlink()
    assert not broken_symlink.exists()
    assert classify_r10_root(broken_symlink) == "corrupt_or_unknown"


def test_publish_r10_receipt_fsyncs_parent_dir_before_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    parent_dir = tmp_path / "receipts"
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    staging_created_at_fsync = []
    real_fsync = os.fsync

    def spy_fsync(fd):
        staging_exists = any(p.name.startswith(f".{VALID_TEST_RUN_ID}.staging") for p in parent_dir.iterdir()) if parent_dir.exists() else False
        staging_created_at_fsync.append(staging_exists)
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", spy_fsync)
    publish_r10_receipt(VALID_TEST_RUN_ID, receipt, parent_dir=parent_dir)

    assert len(staging_created_at_fsync) >= 1
    assert staging_created_at_fsync[0] is False, "Parent dir must be fsynced before staging_root is created"


def test_publish_r10_receipt_collision_probe_hook_rejects(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    final_root = parent_dir / VALID_TEST_RUN_ID
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    def hook_create_competing_final_root():
        final_root.mkdir(parents=True)
        (final_root / "competitor_marker.txt").write_text("competitor", encoding="utf-8")

    with pytest.raises(RuntimeError, match="STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists"):
        publish_r10_receipt(
            VALID_TEST_RUN_ID,
            receipt,
            parent_dir=parent_dir,
            hook_before_rename=hook_create_competing_final_root,
        )

    # Prove that final_root was NOT overwritten by publish_r10_receipt
    assert (final_root / "competitor_marker.txt").exists()
    assert (final_root / "competitor_marker.txt").read_text(encoding="utf-8") == "competitor"
    assert not (final_root / "r10_readmission_receipt.json").exists()


def test_publish_r10_receipt_competing_concurrent_writer_rejected(tmp_path: Path):
    parent_dir = tmp_path / "receipts"
    final_root = parent_dir / VALID_TEST_RUN_ID
    bars_snap = StructuralBarsSnapshot("a" * 64, 1000, 86400, {}, ())
    red = reduce_r10_readmission(bars_snap, None, None)
    receipt = build_r10_receipt_dict(VALID_TEST_RUN_ID, red)

    competing_writer_exception = None

    def hook_spawn_competing_writer():
        nonlocal competing_writer_exception
        try:
            publish_r10_receipt(
                VALID_TEST_RUN_ID,
                receipt,
                parent_dir=parent_dir,
            )
        except Exception as exc:
            competing_writer_exception = exc

    # First writer publishes
    pub_root = publish_r10_receipt(
        VALID_TEST_RUN_ID,
        receipt,
        parent_dir=parent_dir,
        hook_before_rename=hook_spawn_competing_writer,
    )
    assert pub_root == final_root
    assert classify_r10_root(final_root) == "receipt_published"

    # Competing writer was rejected while first writer was in flight
    assert competing_writer_exception is not None
    assert "STOP=stage1_3_r10_readmission_receipt_invalid:final_root_preexists" in str(competing_writer_exception)
