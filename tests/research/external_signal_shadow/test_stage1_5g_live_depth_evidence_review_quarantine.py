import hashlib
import json
import os
from pathlib import Path

import pytest

from src.research.external_signal_shadow.safety import canonical_json_dumps
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    compute_raw_snapshot_quarantine_metrics,
    verify_source_evidence_manifest,
)


def _valid_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    t = i * 60_000 if fetched_at_ms is None else fetched_at_ms
    return {
        "event_symbol_id": event_symbol_id,
        "symbol": symbol,
        "fetched_at_ms": t,
        "best_bid": 100.0,
        "best_ask": 100.1,
        "mid_price": 100.05,
        "spread_bps": 10.0,
        "buy_slippage_bps": 5.0,
        "sell_slippage_bps": 5.0,
        "top_bid_depth_usdt": 1000.0,
        "top_ask_depth_usdt": 1000.0,
    }


def _empty_snapshot(i: int, *, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=None):
    row = _valid_snapshot(i, event_symbol_id=event_symbol_id, symbol=symbol, fetched_at_ms=fetched_at_ms)
    row.update({
        "best_bid": None,
        "best_ask": None,
        "mid_price": None,
        "spread_bps": None,
        "depth_status": "invalid",
        "slippage_status": "invalid_depth",
        "top_bid_depth_usdt": 0.0,
        "top_ask_depth_usdt": 0.0,
        "buy_slippage_bps": None,
        "sell_slippage_bps": None,
    })
    return row


def test_source_manifest_accepts_absolute_self_entry_and_complete_file_set(tmp_path):
    source = tmp_path / "stage1_5f"
    source.mkdir()
    payload = source / "payload.json"
    payload.write_text('{"source":"fixture"}\n', encoding="utf-8")
    manifest = source / "SHA256SUMS"
    manifest.write_text(
        "\n".join(
            [
                f"{hashlib.sha256(payload.read_bytes()).hexdigest()}  {payload.resolve()}",
                f"{'0' * 64}  {manifest.resolve()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    ok, manifest_sha256, blockers = verify_source_evidence_manifest(source)

    assert ok is True
    assert manifest_sha256 == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert blockers == []


def test_source_manifest_rejects_extra_file(tmp_path):
    source = tmp_path / "stage1_5f"
    source.mkdir()
    payload = source / "payload.json"
    payload.write_text('{"source":"fixture"}\n', encoding="utf-8")
    manifest = source / "SHA256SUMS"
    manifest.write_text(
        "\n".join(
            [
                f"{hashlib.sha256(payload.read_bytes()).hexdigest()}  {payload.resolve()}",
                f"{'0' * 64}  {manifest.resolve()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source / "unexpected.json").write_text("{}\n", encoding="utf-8")

    ok, _, blockers = verify_source_evidence_manifest(source)

    assert ok is False
    assert blockers == ["source_evidence_manifest_missing_or_unreadable"]


def test_source_manifest_rejects_unsupported_file_type(tmp_path):
    source = tmp_path / "stage1_5f"
    source.mkdir()
    payload = source / "payload.json"
    payload.write_text('{"source":"fixture"}\n', encoding="utf-8")
    manifest = source / "SHA256SUMS"
    manifest.write_text(
        "\n".join(
            [
                f"{hashlib.sha256(payload.read_bytes()).hexdigest()}  {payload.resolve()}",
                f"{'0' * 64}  {manifest.resolve()}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    os.mkfifo(source / "unexpected.fifo")

    ok, _, blockers = verify_source_evidence_manifest(source)

    assert ok is False
    assert blockers == ["source_evidence_manifest_missing_or_unreadable"]


def test_warmup_phase_uses_launch_time_not_observation_start_when_available():
    launch_ms = 1_000_000
    observation_start_ms = launch_ms + 30 * 60_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["midrun_empty_book"] == 1
    assert result.invalid_book_by_reason["launch_warmup_empty_book"] == 0
    assert "launch_time_missing_warmup_anchor_degraded" not in result.warnings


def test_pre_launch_snapshot_is_not_launch_warmup_when_launch_time_available():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=launch_ms - 60_000),
        _valid_snapshot(1, fetched_at_ms=launch_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": launch_ms - 60_000}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["launch_warmup_empty_book"] == 0
    assert result.invalid_book_by_reason["midrun_empty_book"] == 1
    assert result.invalid_book_by_phase["midrun"] == 1


def test_missing_launch_time_uses_observation_initial_label_with_warning():
    observation_start_ms = 2_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=observation_start_ms),
        _valid_snapshot(1, fetched_at_ms=observation_start_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": observation_start_ms}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1
    assert result.invalid_book_by_phase["observation_initial"] == 1
    assert "launch_time_missing_warmup_anchor_degraded" in result.warnings


def test_invalid_book_reason_classification_precedence():
    snapshots = [
        {"event_symbol_id": None, "symbol": "SKHYUSDT", "fetched_at_ms": 0, "best_bid": None, "best_ask": -1, "spread_bps": -5},
        {"event_symbol_id": "es1", "symbol": "SKHYUSDT", "fetched_at_ms": 60_000, "best_bid": 101.0, "best_ask": 100.0, "spread_bps": -1},
        _empty_snapshot(2, fetched_at_ms=120_000),
        _valid_snapshot(3, fetched_at_ms=180_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.schema_invalid_count == 1
    assert result.crossed_or_negative_book_count == 1
    assert result.invalid_book_by_reason["observation_initial_empty_book"] == 1


def test_invalid_rows_and_minute_buckets_are_counted_separately():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(1, fetched_at_ms=launch_ms + 10_000),
        _valid_snapshot(2, fetched_at_ms=launch_ms + 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.invalid_book_row_count == 2
    assert result.invalid_book_minute_bucket_count == 1
    assert result.launch_warmup_invalid_row_count == 2
    assert result.launch_warmup_invalid_minute_bucket_count == 1


def test_book_availability_ratio_uses_expected_snapshot_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.valid_snapshot_count_after_quarantine == 706
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)
    assert round(result.book_unavailable_ratio, 4) == round(12 / 720, 4)


def test_invalid_book_ratio_uses_observed_snapshot_count_not_expected_count():
    snapshots = [_valid_snapshot(i) for i in range(706)] + [_empty_snapshot(706 + i) for i in range(12)]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed", "observation_started_at_ms": 0}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=720,
    )

    assert result.observed_snapshot_count == 718
    assert result.expected_snapshot_count == 720
    assert round(result.invalid_book_ratio, 4) == round(12 / 718, 4)
    assert round(result.invalid_book_ratio_observed, 4) == round(12 / 718, 4)
    assert round(result.book_availability_ratio, 4) == round(706 / 720, 4)


def test_first_valid_book_latency_above_threshold_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_empty_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(16)]
    snapshots.extend(_valid_snapshot(16 + i, fetched_at_ms=launch_ms + (16 + i) * 60_000) for i in range(700))

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert "first_valid_book_latency_too_high" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_midrun_invalid_count_two_blocks_quarantined_pass():
    launch_ms = 1_000_000
    snapshots = [_valid_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(718)]
    snapshots[30] = _empty_snapshot(30, fetched_at_ms=launch_ms + 30 * 60_000)
    snapshots[60] = _empty_snapshot(60, fetched_at_ms=launch_ms + 60 * 60_000)

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.midrun_invalid_book_count == 2
    assert "midrun_invalid_book_count_exceeded" in result.blockers
    assert result.quarantined_depth_evidence_pass is False


def test_max_consecutive_invalid_uses_fetched_at_ms_order_not_jsonl_order():
    launch_ms = 1_000_000
    snapshots = [
        _empty_snapshot(2, fetched_at_ms=launch_ms + 2 * 60_000),
        _valid_snapshot(0, fetched_at_ms=launch_ms),
        _empty_snapshot(3, fetched_at_ms=launch_ms + 3 * 60_000),
        _valid_snapshot(1, fetched_at_ms=launch_ms + 1 * 60_000),
        _empty_snapshot(4, fetched_at_ms=launch_ms + 4 * 60_000),
    ]

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
    )

    assert result.max_consecutive_invalid == 3


def test_quarantine_v2_single_symbol_golden():
    launch_ms = 1_000_000
    snapshots = [_valid_snapshot(i, fetched_at_ms=launch_ms + i * 60_000) for i in range(718)]
    snapshots.append(_empty_snapshot(718, fetched_at_ms=launch_ms + 718 * 60_000))

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{
            "event_symbol_id": "es1",
            "symbol": "SKHYUSDT",
            "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms},
        }],
        expected_snapshot_count=720,
        formal_completed_event_symbol_ids=["es1"],
    )

    assert result.formal_completed_symbol_count == 1
    assert result.eligible_event_symbol_ids == ["es1"]
    assert result.per_symbol_expected_snapshot_count == 720
    assert result.total_expected_snapshot_count == 720
    assert result.observed_snapshot_count == 719
    assert result.valid_snapshot_count_after_quarantine == 718
    assert result.invalid_book_row_count == 1
    assert result.book_availability_ratio == 718 / 720
    assert result.book_unavailable_ratio == 1 / 720
    assert result.invalid_book_ratio == 1 / 719
    assert "es1" in result.per_symbol_quarantine_metrics


def test_quarantine_v2_five_symbol_golden_arithmetic():
    launch_ms = 1_000_000
    symbols = ["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"]
    states = [{"event_symbol_id": f"es_{s}", "status": "completed"} for s in symbols]
    accepted_events = [
        {"event_symbol_id": f"es_{s}", "symbol": s, "symbol_effective_launch_times_ms": {s: launch_ms}}
        for s in symbols
    ]
    snapshots = []
    # Build 3546 snapshots: 3543 valid, 3 invalid
    # e.g., sym1: 710 valid, sym2: 710 valid, sym3: 710 valid, sym4: 710 valid, sym5: 703 valid + 3 invalid
    for s in symbols[:4]:
        for i in range(710):
            snapshots.append(_valid_snapshot(i, event_symbol_id=f"es_{s}", symbol=s, fetched_at_ms=launch_ms + i * 60_000))
    for i in range(703):
        snapshots.append(_valid_snapshot(i, event_symbol_id="es_SYM5", symbol="SYM5", fetched_at_ms=launch_ms + i * 60_000))
    for i in range(703, 706):
        snapshots.append(_empty_snapshot(i, event_symbol_id="es_SYM5", symbol="SYM5", fetched_at_ms=launch_ms + i * 60_000))

    assert len(snapshots) == 3546

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=states,
        accepted_events=accepted_events,
        expected_snapshot_count=720,
        formal_completed_event_symbol_ids=[f"es_{s}" for s in symbols],
    )

    assert result.formal_completed_symbol_count == 5
    assert result.per_symbol_expected_snapshot_count == 720
    assert result.total_expected_snapshot_count == 3600
    assert result.observed_snapshot_count == 3546
    assert result.valid_snapshot_count_after_quarantine == 3543
    assert result.invalid_book_row_count == 3
    assert result.book_availability_ratio == 3543 / 3600
    assert result.book_unavailable_ratio == 3 / 3600
    assert result.invalid_book_ratio == 3 / 3546
    assert 0.0 <= result.book_availability_ratio <= 1.0
    assert 0.0 <= result.book_unavailable_ratio <= 1.0
    assert 0.0 <= result.invalid_book_ratio <= 1.0


def test_quarantine_v2_nonformal_rows_ignored_in_ratios_and_counts():
    launch_ms = 1_000_000
    snapshots = [
        _valid_snapshot(i, event_symbol_id="es1", symbol="SKHYUSDT", fetched_at_ms=launch_ms + i * 60_000)
        for i in range(10)
    ]
    # Add nonformal row
    snapshots.append(_valid_snapshot(10, event_symbol_id="nonformal_es", symbol="OTHER", fetched_at_ms=launch_ms + 10 * 60_000))

    result = compute_raw_snapshot_quarantine_metrics(
        snapshots=snapshots,
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "symbol_effective_launch_times_ms": {"SKHYUSDT": launch_ms}}],
        expected_snapshot_count=720,
        formal_completed_event_symbol_ids=["es1"],
    )

    assert result.ignored_nonformal_snapshot_row_count == 1
    assert result.observed_snapshot_count == 10
    assert result.valid_snapshot_count_after_quarantine == 10
    assert result.total_expected_snapshot_count == 720


def test_quarantine_v2_invalid_denominators_and_ratios_fail_closed_without_clamping():
    # N = 0
    result_n0 = compute_raw_snapshot_quarantine_metrics(
        snapshots=[],
        states=[],
        accepted_events=[],
        expected_snapshot_count=720,
        formal_completed_event_symbol_ids=[],
    )
    assert "formal_completed_symbol_count_missing_or_zero" in result_n0.blockers

    # Nonpositive expected count
    result_neg = compute_raw_snapshot_quarantine_metrics(
        snapshots=[],
        states=[{"event_symbol_id": "es1", "status": "completed"}],
        accepted_events=[{"event_symbol_id": "es1", "symbol": "SKHYUSDT"}],
        expected_snapshot_count=0,
        formal_completed_event_symbol_ids=["es1"],
    )
    assert "authoritative_per_symbol_expected_snapshot_count_missing" in result_neg.blockers or "expected_snapshot_count_missing" in result_neg.blockers


def test_quarantine_v2_formal_id_hash_literal_golden_vector():
    import hashlib

    from src.research.external_signal_shadow.safety import canonical_json_dumps

    symbols = ["article-a", "article-b"]
    canonical_bytes = canonical_json_dumps(sorted(symbols)).encode("utf-8")
    assert canonical_bytes == b'["article-a","article-b"]'

    digest = hashlib.sha256(canonical_bytes).hexdigest()
    assert digest == "6db09e3b17ebe4d98e12c691c0e90a43b6444aefd7577e0d91863dbf8dfcdee3"


def test_quarantine_v2_5_symbol_mixed_valid_quarantined_pass_fixture():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )
    launch_ms = 1_000_000
    symbols = [f"SYM{i}" for i in range(5)]
    accepted_events = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {s: launch_ms},
        }
        for s in symbols
    ]
    states = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "status": "completed",
            "depth_snapshot_count": 718 if s == "SYM0" else 720,
            "max_gap_ms": 60_000,
            "observation_started_at_ms": launch_ms,
        }
        for s in symbols
    ]

    snapshots = []
    # SYM0 (SKHY-like): 718 snapshots, 11 warmup empty + 1 midrun empty at index 320
    for i in range(718):
        ts = launch_ms + i * 60_000
        if i < 11 or i == 320:
            snapshots.append(_empty_snapshot(i, event_symbol_id="es_SYM0", symbol="SYM0", fetched_at_ms=ts))
        else:
            snapshots.append(_valid_snapshot(i, event_symbol_id="es_SYM0", symbol="SYM0", fetched_at_ms=ts))

    # SYM1: 720 snapshots, 1 midrun empty at index 100
    for i in range(720):
        ts = launch_ms + i * 60_000
        if i == 100:
            snapshots.append(_empty_snapshot(i, event_symbol_id="es_SYM1", symbol="SYM1", fetched_at_ms=ts))
        else:
            snapshots.append(_valid_snapshot(i, event_symbol_id="es_SYM1", symbol="SYM1", fetched_at_ms=ts))

    # SYM2: 720 snapshots, 1 warmup empty at index 0
    for i in range(720):
        ts = launch_ms + i * 60_000
        if i == 0:
            snapshots.append(_empty_snapshot(i, event_symbol_id="es_SYM2", symbol="SYM2", fetched_at_ms=ts))
        else:
            snapshots.append(_valid_snapshot(i, event_symbol_id="es_SYM2", symbol="SYM2", fetched_at_ms=ts))

    # SYM3 & SYM4: 720 valid snapshots each
    for s in ("SYM3", "SYM4"):
        for i in range(720):
            ts = launch_ms + i * 60_000
            snapshots.append(_valid_snapshot(i, event_symbol_id=f"es_{s}", symbol=s, fetched_at_ms=ts))

    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(718 if s == "SYM0" else 720)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 5, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    assert result["decision"] == "stage1_5g_depth_evidence_quarantined_pass"
    assert result["allowed_next_action"] == "write_stage1_5h_design_only"
    assert result["quarantined_depth_evidence_pass"] is True
    assert result["clean_depth_evidence_pass"] is False

    quarantine = result["quarantine"]
    assert quarantine["formal_completed_symbol_count"] == 5
    assert quarantine["total_expected_snapshot_count"] == 3600
    assert quarantine["per_symbol_expected_snapshot_count"] == 720
    assert quarantine["aggregate_observed_snapshot_count"] == 718 + 720 * 4
    assert len(quarantine["per_symbol_quarantine_metrics"]) == 5
    assert quarantine["per_symbol_quarantine_metrics"]["es_SYM0"]["invalid_book_by_reason"] == {
        "crossed_or_negative_book": 0,
        "launch_warmup_empty_book": 11,
        "midrun_empty_book": 1,
        "observation_initial_empty_book": 0,
        "schema_invalid": 0,
    }

    for ambiguous_key in ("expected_snapshot_count", "observed_snapshot_count", "valid_snapshot_count_after_quarantine", "invalid_book_row_count"):
        assert ambiguous_key not in quarantine, f"{ambiguous_key} should not be in v2 quarantine summary"


def test_quarantine_v2_5_symbol_with_1_broken_symbol_fails_all_pass_gates():
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        build_stage1_5g_review_summary,
    )
    launch_ms = 1_000_000
    symbols = [f"SYM{i}" for i in range(5)]
    accepted_events = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
            "symbol_effective_launch_times_ms": {s: launch_ms},
        }
        for s in symbols
    ]
    states = [
        {
            "event_symbol_id": f"es_{s}",
            "symbol": s,
            "status": "completed",
            "depth_snapshot_count": 720,
            "max_gap_ms": 60_000,
            "observation_started_at_ms": launch_ms,
        }
        for s in symbols
    ]

    snapshots = []
    # SYM0..SYM3: valid
    for s in symbols[:4]:
        for i in range(720):
            ts = launch_ms + i * 60_000
            snapshots.append(_valid_snapshot(i, event_symbol_id=f"es_{s}", symbol=s, fetched_at_ms=ts))

    # SYM4: 2 midrun invalid books (index 100 and index 200)
    for i in range(720):
        ts = launch_ms + i * 60_000
        if i in (100, 200):
            snapshots.append(_empty_snapshot(i, event_symbol_id="es_SYM4", symbol="SYM4", fetched_at_ms=ts))
        else:
            snapshots.append(_valid_snapshot(i, event_symbol_id="es_SYM4", symbol="SYM4", fetched_at_ms=ts))

    request_rows = [
        {"request_type": "depth_snapshot", "event_symbol_id": f"es_{s}", "symbol": s, "http_status": 200}
        for s in symbols for _ in range(720)
    ]

    result = build_stage1_5g_review_summary(
        summary={"completed_observation_count": 5, "observation_window_ms": 43_200_000, "snapshot_interval_ms": 60_000},
        watermark={"watermark_version": 1, "max_seen_detected_at_ms": 1000},
        states=states,
        accepted_events=accepted_events,
        snapshots=snapshots,
        request_manifest_rows=request_rows,
    )

    assert result["decision"] == "stage1_5g_depth_evidence_invalid"
    assert "per_symbol_quarantine_gate_failed" in result["blockers"] or "midrun_invalid_book_count_exceeded" in result["blockers"]
    assert result.get("quarantined_depth_evidence_pass") is not True


EXPECTED_GATE_KEYS = {
    "schema_version",
    "source_runtime_attestation_gate_verified",
    "stage1_5g_review_id",
    "source_evidence_manifest_sha256",
    "consumer_process_instance_id",
    "consumer_root_id",
    "consumer_process_started_at_ms",
    "consumer_startup_commit_sha",
    "consumer_root_contract_sha256",
    "consumer_runtime_manifest_sha256",
    "consumer_static_attestation_verified",
    "consumer_runtime_attestation_verified",
    "consumer_runtime_attestation_compromised",
    "source_runtime_attestation_authority_sha256",
}


def _make_valid_task3_fixture_bundle(review_root: Path) -> tuple[dict, dict, dict, dict[str, Path]]:
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        validate_stage1_5f_source_runtime_authority,
        verify_source_evidence_manifest,
    )
    from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import (
        make_stage1_5f_fixture_root,
    )

    review_root.mkdir(parents=True, exist_ok=True)
    src_root = make_stage1_5f_fixture_root(review_root.parent / "stage1_5f_source")
    source_ok, src_manifest_sha, _ = verify_source_evidence_manifest(src_root)
    assert source_ok is True
    src_summary = json.loads((src_root / "live_depth_observer_summary.json").read_text(encoding="utf-8"))
    source_authority, auth_blockers = validate_stage1_5f_source_runtime_authority(
        stage1_5f_root=src_root,
        summary=src_summary,
        source_evidence_manifest_sha256=src_manifest_sha,
    )
    assert not auth_blockers and bool(source_authority)

    summary_file = review_root / "stage1_5g_live_depth_evidence_review_summary.json"
    quarantine_file = review_root / "stage1_5g_quarantine_summary.json"
    invalid_rows_file = review_root / "quarantined_invalid_book_rows.jsonl"
    valid_rows_file = review_root / "depth_quality_input_rows.jsonl"
    gate_file = review_root / "stage1_5g_runtime_attestation_gate.json"

    rev_id = "a" * 64

    summary_data = {
        "schema_version": 2,
        "stage1_5g_review_id": rev_id,
        "stage1_5f_output_root": str(src_root),
        "source_evidence_manifest_sha256": src_manifest_sha,
        "formal_completed_event_symbol_ids_sha256": "c" * 64,
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "clean_depth_evidence_pass": False,
        "quarantined_depth_evidence_pass": True,
    }
    quarantine_data = {
        "stage1_5g_review_id": rev_id,
        "source_evidence_manifest_sha256": src_manifest_sha,
        "formal_completed_event_symbol_ids_sha256": "c" * 64,
        "quarantined_depth_evidence_pass": True,
    }

    gate_payload_without_hash = {
        "schema_version": 1,
        "source_runtime_attestation_gate_verified": True,
        "stage1_5g_review_id": rev_id,
        "source_evidence_manifest_sha256": src_manifest_sha,
        **source_authority,
    }
    auth_sha = hashlib.sha256(canonical_json_dumps(gate_payload_without_hash).encode("utf-8")).hexdigest()
    gate_payload = {
        **gate_payload_without_hash,
        "source_runtime_attestation_authority_sha256": auth_sha,
    }

    summary_file.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    quarantine_file.write_text(json.dumps(quarantine_data, indent=2), encoding="utf-8")
    invalid_rows_file.write_text(json.dumps({"depth_status": "invalid"}) + "\n", encoding="utf-8")
    valid_rows_file.write_text(json.dumps({"best_bid": 100.0, "best_ask": 100.1}) + "\n", encoding="utf-8")
    gate_file.write_text(json.dumps(gate_payload, indent=2), encoding="utf-8")

    artifact_paths = {
        "summary": summary_file,
        "quarantine_summary": quarantine_file,
        "quarantined_invalid_book_rows": invalid_rows_file,
        "depth_quality_input_rows": valid_rows_file,
        "runtime_attestation_gate": gate_file,
    }
    return summary_data, source_authority, gate_payload, artifact_paths


def test_quarantine_v3_closed_artifact_bundle_round_trip(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
        write_stage1_5g_review_manifest,
    )

    review_root = tmp_path / "closed_review_run"
    summary_data, _, _, artifact_paths = _make_valid_task3_fixture_bundle(review_root)

    manifest_path = write_stage1_5g_review_manifest(review_root, summary_data, artifact_paths)
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["schema_version"] == 3
    assert set(manifest_data["artifacts"].keys()) == {
        "summary",
        "quarantine_summary",
        "quarantined_invalid_book_rows",
        "depth_quality_input_rows",
        "runtime_attestation_gate",
    }

    ok, blockers = verify_stage1_5g_review_manifest(review_root)
    assert ok is True
    assert blockers == []


def test_write_stage1_5g_runtime_attestation_gate_produces_exact_14_keys(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        write_stage1_5g_runtime_attestation_gate,
    )

    review_root = tmp_path / "gate_write_test"
    review_root.mkdir(parents=True, exist_ok=True)
    summary_data, source_authority, _, _ = _make_valid_task3_fixture_bundle(review_root)

    gate_path = write_stage1_5g_runtime_attestation_gate(
        review_root,
        summary=summary_data,
        source_authority=source_authority,
    )
    assert gate_path.is_file()
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert set(payload.keys()) == EXPECTED_GATE_KEYS
    assert payload["schema_version"] == 1
    assert payload["source_runtime_attestation_gate_verified"] is True
    assert payload["consumer_static_attestation_verified"] is True
    assert payload["consumer_runtime_attestation_verified"] is True
    assert payload["consumer_runtime_attestation_compromised"] is False
    assert payload["stage1_5g_review_id"] == summary_data["stage1_5g_review_id"]
    assert payload["source_evidence_manifest_sha256"] == summary_data["source_evidence_manifest_sha256"]

    # Verify authority self-hash
    payload_without_hash = {k: v for k, v in payload.items() if k != "source_runtime_attestation_authority_sha256"}
    expected_hash = hashlib.sha256(canonical_json_dumps(payload_without_hash).encode("utf-8")).hexdigest()
    assert payload["source_runtime_attestation_authority_sha256"] == expected_hash


def test_write_stage1_5g_runtime_attestation_gate_precondition_rejections(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        write_stage1_5g_runtime_attestation_gate,
    )

    review_root = tmp_path / "gate_precondition_test"
    summary_data, source_authority, _, _ = _make_valid_task3_fixture_bundle(review_root)

    # 1. Decision not quarantined pass
    bad_summary = dict(summary_data, decision="stage1_5g_depth_evidence_clean_pass")
    with pytest.raises(ValueError):
        write_stage1_5g_runtime_attestation_gate(review_root, summary=bad_summary, source_authority=source_authority)

    # 2. quarantined_depth_evidence_pass not True
    bad_summary2 = dict(summary_data, quarantined_depth_evidence_pass=False)
    with pytest.raises(ValueError):
        write_stage1_5g_runtime_attestation_gate(review_root, summary=bad_summary2, source_authority=source_authority)

    # 3. clean_depth_evidence_pass not False
    bad_summary3 = dict(summary_data, clean_depth_evidence_pass=True)
    with pytest.raises(ValueError):
        write_stage1_5g_runtime_attestation_gate(review_root, summary=bad_summary3, source_authority=source_authority)

    # 4. source_authority compromised
    bad_auth = dict(source_authority, consumer_runtime_attestation_compromised=True)
    with pytest.raises(ValueError):
        write_stage1_5g_runtime_attestation_gate(review_root, summary=summary_data, source_authority=bad_auth)

    # 5. source_authority missing required key
    bad_auth2 = {k: v for k, v in source_authority.items() if k != "consumer_process_instance_id"}
    with pytest.raises(ValueError):
        write_stage1_5g_runtime_attestation_gate(review_root, summary=summary_data, source_authority=bad_auth2)


def test_verify_manifest_rejects_v2_manifest(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
        write_stage1_5g_review_manifest,
    )

    review_root = tmp_path / "v2_manifest_test"
    summary_data, _, _, artifact_paths = _make_valid_task3_fixture_bundle(review_root)
    # Exclude gate proof so v2 is written
    v2_artifact_paths = {k: v for k, v in artifact_paths.items() if k != "runtime_attestation_gate"}
    write_stage1_5g_review_manifest(review_root, summary_data, v2_artifact_paths)

    ok, blockers = verify_stage1_5g_review_manifest(review_root)
    assert ok is False
    assert blockers == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]


def test_verify_manifest_rejects_missing_or_corrupt_manifest(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
    )

    review_root = tmp_path / "missing_manifest_test"
    review_root.mkdir(parents=True, exist_ok=True)
    ok, blockers = verify_stage1_5g_review_manifest(review_root)
    assert ok is False
    assert blockers == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]

    manifest_p = review_root / "stage1_5g_review_manifest.json"
    manifest_p.write_text("{corrupt_json\n", encoding="utf-8")
    ok2, blockers2 = verify_stage1_5g_review_manifest(review_root)
    assert ok2 is False
    assert blockers2 == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]


def test_verify_manifest_rejects_tampered_proof_self_hash(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
        write_stage1_5g_review_manifest,
    )

    review_root = tmp_path / "tampered_self_hash_test"
    summary_data, _, _, artifact_paths = _make_valid_task3_fixture_bundle(review_root)

    # Tamper with authority hash inside gate proof
    gate_file = artifact_paths["runtime_attestation_gate"]
    gate_data = json.loads(gate_file.read_text(encoding="utf-8"))
    gate_data["source_runtime_attestation_authority_sha256"] = "0" * 64
    gate_file.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")

    write_stage1_5g_review_manifest(review_root, summary_data, artifact_paths)
    ok, blockers = verify_stage1_5g_review_manifest(review_root)
    assert ok is False
    assert blockers == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]


def test_verify_manifest_rejects_unexpected_or_missing_proof_keys(tmp_path):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
        write_stage1_5g_review_manifest,
    )

    # Extra key
    review_root1 = tmp_path / "extra_key_test"
    summary_data1, _, _, artifact_paths1 = _make_valid_task3_fixture_bundle(review_root1)
    gate_file1 = artifact_paths1["runtime_attestation_gate"]
    gate_data1 = json.loads(gate_file1.read_text(encoding="utf-8"))
    gate_data1["unexpected_extra_key"] = "forbidden"
    gate_without_hash = {k: v for k, v in gate_data1.items() if k != "source_runtime_attestation_authority_sha256"}
    gate_data1["source_runtime_attestation_authority_sha256"] = hashlib.sha256(canonical_json_dumps(gate_without_hash).encode("utf-8")).hexdigest()
    gate_file1.write_text(json.dumps(gate_data1, indent=2), encoding="utf-8")
    write_stage1_5g_review_manifest(review_root1, summary_data1, artifact_paths1)

    ok1, blockers1 = verify_stage1_5g_review_manifest(review_root1)
    assert ok1 is False
    assert blockers1 == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]

    # Missing key
    review_root2 = tmp_path / "missing_key_test"
    summary_data2, _, _, artifact_paths2 = _make_valid_task3_fixture_bundle(review_root2)
    gate_file2 = artifact_paths2["runtime_attestation_gate"]
    gate_data2 = json.loads(gate_file2.read_text(encoding="utf-8"))
    del gate_data2["consumer_process_instance_id"]
    gate_without_hash2 = {k: v for k, v in gate_data2.items() if k != "source_runtime_attestation_authority_sha256"}
    gate_data2["source_runtime_attestation_authority_sha256"] = hashlib.sha256(canonical_json_dumps(gate_without_hash2).encode("utf-8")).hexdigest()
    gate_file2.write_text(json.dumps(gate_data2, indent=2), encoding="utf-8")
    write_stage1_5g_review_manifest(review_root2, summary_data2, artifact_paths2)

    ok2, blockers2 = verify_stage1_5g_review_manifest(review_root2)
    assert ok2 is False
    assert blockers2 == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]


@pytest.mark.parametrize(
    ("field", "mutated_value"),
    [
        ("consumer_process_instance_id", "99999999-9999-4999-8999-999999999999"),
        ("consumer_root_id", "9" * 64),
        ("consumer_process_started_at_ms", 1_799_999_999_000),
        ("consumer_startup_commit_sha", "9" * 40),
        ("consumer_root_contract_sha256", "9" * 64),
        ("consumer_runtime_manifest_sha256", "9" * 64),
        ("consumer_static_attestation_verified", False),
        ("consumer_runtime_attestation_verified", False),
        ("consumer_runtime_attestation_compromised", True),
        ("stage1_5g_review_id", "9" * 64),
        ("source_evidence_manifest_sha256", "9" * 64),
        ("consumer_process_instance_id", "not-a-valid-uuid"),
        ("consumer_root_id", "not-a-valid-hex-root-id"),
        ("consumer_process_started_at_ms", 0),
        ("consumer_startup_commit_sha", "short_sha"),
        ("consumer_root_contract_sha256", "invalid_sha256"),
        ("consumer_runtime_manifest_sha256", "invalid_manifest_sha"),
    ],
)
def test_verify_manifest_semantic_linkage_mutations_rejected(tmp_path, field, mutated_value):
    from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
        verify_stage1_5g_review_manifest,
        write_stage1_5g_review_manifest,
    )

    review_root = tmp_path / f"linkage_mut_{field}"
    summary_data, _, _, artifact_paths = _make_valid_task3_fixture_bundle(review_root)

    gate_file = artifact_paths["runtime_attestation_gate"]
    gate_data = json.loads(gate_file.read_text(encoding="utf-8"))
    gate_data[field] = mutated_value

    # (1) Recompute and rewrite proof self-hash
    payload_without_hash = {k: v for k, v in gate_data.items() if k != "source_runtime_attestation_authority_sha256"}
    gate_data["source_runtime_attestation_authority_sha256"] = hashlib.sha256(
        canonical_json_dumps(payload_without_hash).encode("utf-8")
    ).hexdigest()
    gate_file.write_text(json.dumps(gate_data, indent=2), encoding="utf-8")

    # (2), (3), (4) write_stage1_5g_review_manifest computes exact outer sha256 and byte_count
    manifest_path = write_stage1_5g_review_manifest(review_root, summary_data, artifact_paths)

    # (5) Assert manifest is structurally/hash/size valid on disk
    manifest_obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_obj["schema_version"] == 3
    for art_meta in manifest_obj["artifacts"].values():
        target = review_root / art_meta["relative_path"]
        raw = target.read_bytes()
        assert len(raw) == art_meta["byte_count"]
        assert hashlib.sha256(raw).hexdigest() == art_meta["sha256"]

    # Verify Stage 1.5H / manifest verifier rejects with exact blocker
    ok, blockers = verify_stage1_5g_review_manifest(review_root)
    assert ok is False
    assert blockers == ["stage1_5h_runtime_attestation_gate_missing_or_invalid"]
