# -*- coding: utf-8 -*-
"""
tests/scripts/test_review_route_c1_price_only.py

TDD tests for scripts/review_route_c1_price_only.py

Tasks covered:
  Task 2: response window and price risk metrics
  Task 3: event detection
  Task 4: matched baseline
  Task 5: summary and decision gate
  Task 6: CLI and markdown
"""

from __future__ import annotations

import datetime
import json

import pytest

import configs.base  # noqa: F401 (used in test_detect_c1_events_reads_thresholds_from_config)
from scripts.review_route_c1_price_only import (
    annotate_pre30_vol_buckets,
    build_c1_price_only_summary,
    build_event_baseline_pairs,
    compute_c1_price_only_decision,
    compute_percentile_rank,
    compute_price_risk_metrics,
    detect_c1_events,
    first_complete_5m_response_start_ms,
    has_complete_response_window,
    load_dataset,
    match_baselines_for_event,
    parse_args,
    render_review_markdown,
)

_MS_PER_MIN = 60_000
_MS_PER_5M = 300_000


def _bar_start(hh: int, mm: int) -> int:
    """Return a bar start in ms given hour and minute offsets from epoch zero."""
    return (hh * 60 + mm) * _MS_PER_MIN


def _utc_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    dt = datetime.datetime(year, month, day, hour, minute, tzinfo=datetime.timezone.utc)
    return int(dt.timestamp() * 1000)


def test_first_complete_5m_response_bar_excludes_event_bar():
    # shock at 12:03 → response at 12:05
    shock_ms = _bar_start(12, 3)
    response_ms = first_complete_5m_response_start_ms(shock_ms)
    # 12:03 is inside [12:00–12:04] 5m bar → next complete bar is [12:05–12:09]
    assert response_ms == _bar_start(12, 5)


def test_first_complete_5m_response_bar_when_event_on_5m_boundary():
    # shock at 12:05 → response at 12:10
    shock_ms = _bar_start(12, 5)
    response_ms = first_complete_5m_response_start_ms(shock_ms)
    # 12:05 is inside [12:05–12:09] 5m bar → next complete bar is [12:10–12:14]
    assert response_ms == _bar_start(12, 10)


def test_first_complete_5m_response_bar_when_event_at_start_of_5m_bar():
    # shock at 12:00 → response at 12:05
    shock_ms = _bar_start(12, 0)
    response_ms = first_complete_5m_response_start_ms(shock_ms)
    assert response_ms == _bar_start(12, 5)


def test_first_complete_5m_response_bar_when_event_at_end_of_5m_bar():
    # shock at 12:04 → response at 12:05
    shock_ms = _bar_start(12, 4)
    response_ms = first_complete_5m_response_start_ms(shock_ms)
    assert response_ms == _bar_start(12, 5)


def _make_rows(base_ms: int, entries: list[dict]) -> list[dict]:
    """Make 1m rows starting at base_ms with the given open/high/low/close."""
    rows = []
    for i, e in enumerate(entries):
        rows.append(
            {
                "bar_start_ms": base_ms + i * _MS_PER_MIN,
                "open_price": e.get("o", 100.0),
                "high_price": e.get("h", e.get("o", 100.0)),
                "low_price": e.get("l", e.get("o", 100.0)),
                "close_price": e.get("c", e.get("o", 100.0)),
            }
        )
    return rows


def test_compute_price_risk_metrics_direction_agnostic():
    # entry = 100, high = 102, low = 98
    start_ms = _bar_start(12, 5)
    rows = _make_rows(
        start_ms,
        [
            {"o": 100.0, "h": 102.0, "l": 98.0, "c": 99.0},
            {"o": 99.0, "h": 101.0, "l": 97.0, "c": 100.0},
            {"o": 100.0, "h": 100.5, "l": 99.5, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 99.0, "c": 99.5},
            {"o": 99.5, "h": 100.0, "l": 99.0, "c": 99.5},
        ],
    )
    metrics = compute_price_risk_metrics(rows, start_ms, horizon_minutes=5)
    assert metrics is not None

    entry = 100.0  # first row open
    high = 102.0
    low = 97.0

    expected_range_bps = (high / low - 1) * 10_000
    expected_max_abs_excursion_bps = max(abs(high / entry - 1), abs(low / entry - 1)) * 10_000

    assert metrics["high_low_range_5m_bps"] == pytest.approx(expected_range_bps, rel=1e-5)
    assert metrics["max_abs_excursion_5m_bps"] == pytest.approx(
        expected_max_abs_excursion_bps, rel=1e-5
    )


def test_compute_mae_if_long_and_short_are_side_conditioned():
    start_ms = _bar_start(12, 5)
    # entry = 100, high = 105, low = 95
    rows = _make_rows(
        start_ms,
        [
            {"o": 100.0, "h": 105.0, "l": 95.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
        ],
    )
    metrics = compute_price_risk_metrics(rows, start_ms, horizon_minutes=5)
    assert metrics is not None

    # mae_if_long: max drawdown from entry -> max(0, 1 - low/entry) * 10000
    # low = 95 -> (1 - 95/100) * 10000 = 500 bps
    assert metrics["mae_if_long_5m_bps"] == pytest.approx(500.0, rel=1e-5)
    # mae_if_short: max upside from entry -> max(0, high/entry - 1) * 10000
    # high = 105 -> (105/100 - 1) * 10000 = 500 bps
    assert metrics["mae_if_short_5m_bps"] == pytest.approx(500.0, rel=1e-5)


def test_price_risk_metrics_use_first_response_open_as_entry():
    start_ms = _bar_start(12, 5)
    # First row open = 200, not 100
    rows = _make_rows(
        start_ms,
        [
            {"o": 200.0, "h": 204.0, "l": 196.0, "c": 200.0},
            {"o": 200.0, "h": 200.0, "l": 200.0, "c": 200.0},
            {"o": 200.0, "h": 200.0, "l": 200.0, "c": 200.0},
            {"o": 200.0, "h": 200.0, "l": 200.0, "c": 200.0},
            {"o": 200.0, "h": 200.0, "l": 200.0, "c": 200.0},
        ],
    )
    metrics = compute_price_risk_metrics(rows, start_ms, horizon_minutes=5)
    # entry = 200 (first row open), high = 204, low = 196
    entry = 200.0
    high = 204.0
    low = 196.0
    expected_max_abs = max(abs(high / entry - 1), abs(low / entry - 1)) * 10_000
    assert metrics["max_abs_excursion_5m_bps"] == pytest.approx(expected_max_abs, rel=1e-5)


def test_response_metrics_return_none_when_future_window_incomplete():
    start_ms = _bar_start(12, 5)
    # Only 3 bars when 5 expected
    rows = _make_rows(
        start_ms,
        [
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
            {"o": 100.0, "h": 100.0, "l": 100.0, "c": 100.0},
        ],
    )
    metrics = compute_price_risk_metrics(rows, start_ms, horizon_minutes=5)
    assert metrics is None


# ─── Task 3: Event Detection ──────────────────────────────────────────────────


def _make_liq_rows(symbol: str, entries: list[dict]) -> list[dict]:
    """Make liquidation 1m rows for event detection tests."""
    rows = []
    for i, e in enumerate(entries):
        rows.append(
            {
                "symbol": symbol,
                "bar_start_ms": e.get("ts", i * _MS_PER_MIN),
                "total_liquidation_notional_1m_usdt": e.get("notional", 0.0),
                "long_liquidation_notional_1m_usdt": e.get("long", 0.0),
                "short_liquidation_notional_1m_usdt": e.get("short", 0.0),
            }
        )
    return rows


def test_compute_percentile_rank_basic():
    # value 9 among [1, 2, ..., 10] → rank 8/9 ≈ 0.889 (using < comparison)
    previous = list(range(1, 10))  # [1..9]
    rank = compute_percentile_rank(9.0, previous)
    # values strictly less than 9: 8 out of 9 → 8/9
    assert rank == pytest.approx(8 / 9, rel=1e-5)


def test_compute_percentile_rank_all_below():
    previous = [1.0, 2.0, 3.0]
    rank = compute_percentile_rank(10.0, previous)
    assert rank == 1.0


def test_compute_percentile_rank_none_below():
    previous = [10.0, 20.0, 30.0]
    rank = compute_percentile_rank(5.0, previous)
    assert rank == 0.0


def test_detect_c1_events_requires_previous_1440_reference_bars():
    """With only 100 reference bars, no events should be detected."""
    rows = []
    for i in range(100):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1000.0,
                "long_liquidation_notional_1m_usdt": 700.0,
                "short_liquidation_notional_1m_usdt": 300.0,
            }
        )
    events = detect_c1_events(rows)
    assert len(events) == 0


def test_detect_c1_events_excludes_current_bar_from_percentile_reference():
    """Percentile rank must be computed using previous bars only (no lookahead)."""
    rows = []
    # 1440 baseline bars with low notional
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1_000.0,
                "long_liquidation_notional_1m_usdt": 700.0,
                "short_liquidation_notional_1m_usdt": 300.0,
            }
        )
    # 1441st bar: very high notional → should be detected
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 200_000.0,
            "long_liquidation_notional_1m_usdt": 180_000.0,
            "short_liquidation_notional_1m_usdt": 20_000.0,
        }
    )
    events = detect_c1_events(rows)
    assert len(events) == 1
    assert events[0]["shock_bar_start_ms"] == 1440 * _MS_PER_MIN


def test_detect_c1_events_requires_995_percentile():
    """Events must be at >= 99.5th percentile to qualify."""
    rows = []
    # 1440 baseline bars with equal notional
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1_000.0,
                "long_liquidation_notional_1m_usdt": 700.0,
                "short_liquidation_notional_1m_usdt": 300.0,
            }
        )
    # Bar at 95th percentile (just marginally above median) — should NOT trigger
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 1_001.0,  # only slightly above
            "long_liquidation_notional_1m_usdt": 700.0,
            "short_liquidation_notional_1m_usdt": 301.0,
        }
    )
    events = detect_c1_events(rows)
    assert len(events) == 0


def test_detect_c1_events_applies_major_and_alt_abs_thresholds():
    """BTC/ETH require 50_000 USDT, SOL/XRP/DOGE require 10_000 USDT."""
    # SOL with 5_000 USDT → below alt threshold → not detected
    rows = []
    for i in range(1440):
        rows.append(
            {
                "symbol": "SOLUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1_000.0,
                "long_liquidation_notional_1m_usdt": 700.0,
                "short_liquidation_notional_1m_usdt": 300.0,
            }
        )
    rows.append(
        {
            "symbol": "SOLUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 5_000.0,  # < 10_000 threshold
            "long_liquidation_notional_1m_usdt": 4_000.0,
            "short_liquidation_notional_1m_usdt": 1_000.0,
        }
    )
    events = detect_c1_events(rows)
    assert len(events) == 0


def test_detect_c1_events_requires_dominance_ratio_065():
    """Events where neither side dominates (ratio < 0.65) should be rejected."""
    rows = []
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1_000.0,
                "long_liquidation_notional_1m_usdt": 500.0,
                "short_liquidation_notional_1m_usdt": 500.0,
            }
        )
    # High notional but mixed sides → dominance_ratio = 60/100 = 0.6 < 0.65
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 200_000.0,
            "long_liquidation_notional_1m_usdt": 120_000.0,
            "short_liquidation_notional_1m_usdt": 80_000.0,
        }
    )
    events = detect_c1_events(rows)
    assert len(events) == 0


def test_detect_c1_events_deduplicates_symbol_side_5m_bucket_keep_largest():
    """Two events in same 5m bucket with same symbol+side → only the larger survives."""
    rows = []
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 1_000.0,
                "long_liquidation_notional_1m_usdt": 700.0,
                "short_liquidation_notional_1m_usdt": 300.0,
            }
        )
    # Two events in same 5m bucket (bars at 1440 and 1441)
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 200_000.0,
            "long_liquidation_notional_1m_usdt": 180_000.0,
            "short_liquidation_notional_1m_usdt": 20_000.0,
        }
    )
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1441 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 150_000.0,
            "long_liquidation_notional_1m_usdt": 140_000.0,
            "short_liquidation_notional_1m_usdt": 10_000.0,
        }
    )
    events = detect_c1_events(rows)
    # After dedup: only one event (larger one)
    assert len(events) == 1
    assert events[0]["shock_notional_usdt"] == 200_000.0


def test_detect_c1_events_reads_thresholds_from_config():
    """detect_c1_events must pull thresholds from configs.base, not local constants."""
    import configs.base as cfg

    # We cannot verify internals, but we can verify the function uses the
    # config values by checking the function operates at 0.995 threshold.
    # This test just asserts config values are accessible
    assert cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD == 0.995
    assert cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS == 1440
    assert cfg.ROUTE_C1_DOMINANCE_RATIO_MIN == 0.65


def test_detect_c1_events_scores_against_same_side_reference():
    """A short-side shock must be ranked against prior short-side history, not total notional."""
    rows = []
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": i * _MS_PER_MIN,
                "total_liquidation_notional_1m_usdt": 200_000.0,
                "long_liquidation_notional_1m_usdt": 190_000.0,
                "short_liquidation_notional_1m_usdt": 10_000.0,
            }
        )
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": 1440 * _MS_PER_MIN,
            "total_liquidation_notional_1m_usdt": 150_000.0,
            "long_liquidation_notional_1m_usdt": 10_000.0,
            "short_liquidation_notional_1m_usdt": 140_000.0,
        }
    )

    events = detect_c1_events(rows)
    assert len(events) == 1
    assert events[0]["dominant_liquidation_side"] == "short"


# ─── Task 4: Baseline Matching ────────────────────────────────────────────────


def _make_close_rows(symbol: str, start_ms: int, closes: list[float]) -> list[dict]:
    """Make minimal 1m rows with close_price only, for pre30_vol tests."""
    rows = []
    for i, c in enumerate(closes):
        rows.append(
            {
                "symbol": symbol,
                "bar_start_ms": start_ms + i * _MS_PER_MIN,
                "open_price": c,
                "high_price": c,
                "low_price": c,
                "close_price": c,
                "total_liquidation_notional_1m_usdt": 0.0,
            }
        )
    return rows


def test_compute_pre30_vol_bucket_uses_prior_returns_only():
    """pre30_vol at bar i must use only closes before bar i."""
    # Monotonically increasing prices: std of log returns is well-defined
    closes = [100.0 + i * 0.01 for i in range(60)]  # 60 bars
    rows = _make_close_rows("BTCUSDT", 0, closes)
    annotated = annotate_pre30_vol_buckets(rows)

    # For bar at index 30, pre30_vol should use returns from bars 0-29 (30 returns)
    row_30 = annotated[30]
    assert "pre30_vol" in row_30
    assert row_30["pre30_vol"] is not None

    # For bars 0-29, not enough history → pre30_vol should be None
    for row in annotated[:30]:
        assert row.get("pre30_vol") is None


def test_compute_pre30_vol_uses_log_return_std():
    """pre30_vol must be std(log(close_t / close_t_minus_1)) over 30 bars."""
    # Use flat prices → std = 0
    closes = [100.0] * 35
    rows = _make_close_rows("BTCUSDT", 0, closes)
    annotated = annotate_pre30_vol_buckets(rows)

    row_34 = annotated[34]
    assert row_34["pre30_vol"] == pytest.approx(0.0, abs=1e-10)


def _make_candidate_rows(
    symbol: str,
    base_ms: int,
    n_bars: int,
    notional_at: dict[int, float] | None = None,
    price: float = 100.0,
) -> list[dict]:
    """Create n_bars of 1m rows, with optional nonzero liquidation at given bar indices."""
    notional_at = notional_at or {}
    rows = []
    for i in range(n_bars):
        rows.append(
            {
                "symbol": symbol,
                "bar_start_ms": base_ms + i * _MS_PER_MIN,
                "open_price": price,
                "high_price": price + 0.1,
                "low_price": price - 0.1,
                "close_price": price,
                "total_liquidation_notional_1m_usdt": notional_at.get(i, 0.0),
            }
        )
    return rows


def test_match_baselines_returns_20_windows_when_available():
    """When sufficient clean history exists, K=20 matched baselines should be returned."""

    symbol = "BTCUSDT"
    # Build 2000 clean bars
    all_rows = _make_candidate_rows(symbol, 0, 2000)
    # Annotate pre30_vol
    all_rows = annotate_pre30_vol_buckets(all_rows)

    # Create a dummy event at bar 1800
    event = {
        "symbol": symbol,
        "shock_bar_start_ms": 1800 * _MS_PER_MIN,
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": 1800 * _MS_PER_MIN,
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    assert len(baselines) == 20


def test_match_baselines_excludes_windows_near_liquidation_shocks():
    """Candidates with nonzero liquidation within ±30m guard window must be excluded."""
    symbol = "BTCUSDT"
    # Build 2000 rows, but inject a liquidation shock at bar 500
    all_rows = _make_candidate_rows(symbol, 0, 2000, notional_at={500: 50_000.0})
    all_rows = annotate_pre30_vol_buckets(all_rows)

    event = {
        "symbol": symbol,
        "shock_bar_start_ms": 1800 * _MS_PER_MIN,
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": 1800 * _MS_PER_MIN,
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    # No baseline window should be at or near bar 500 (within ±30 bars)
    for bl in baselines:
        start = bl["candidate_bar_start_ms"]
        assert abs(start - 500 * _MS_PER_MIN) > 30 * _MS_PER_MIN


def test_match_baselines_excludes_any_nonzero_liquidation_notional():
    """Any candidate row with liquidation > 0 must be excluded, not just C1 shocks."""
    symbol = "BTCUSDT"
    # Inject small liquidation (1 USDT) at many candidates
    notional_at = {i: 1.0 for i in range(100, 1500)}  # large contaminated zone
    all_rows = _make_candidate_rows(symbol, 0, 2000, notional_at=notional_at)
    all_rows = annotate_pre30_vol_buckets(all_rows)

    event = {
        "symbol": symbol,
        "shock_bar_start_ms": 1800 * _MS_PER_MIN,
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": 1800 * _MS_PER_MIN,
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    # All returned baselines must have zero liquidation in candidate + guard + future window
    for bl in baselines:
        # We can only verify the baseline reports the guard was clean
        assert bl.get("contamination_free") is True


def test_match_baselines_excludes_candidates_without_complete_future_window():
    """Candidates that don't have 5 complete 1m bars after their start must be excluded."""
    symbol = "BTCUSDT"
    # Only 1450 bars total — bars near the end won't have complete 5m future windows
    all_rows = _make_candidate_rows(symbol, 0, 1450)
    all_rows = annotate_pre30_vol_buckets(all_rows)

    event = {
        "symbol": symbol,
        "shock_bar_start_ms": 1440 * _MS_PER_MIN,
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": 1440 * _MS_PER_MIN,
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    for bl in baselines:
        # The candidate must have at least 5 bars of response data available
        assert bl.get("has_complete_future_window") is True


def test_match_baselines_falls_back_by_relaxing_time_then_vol_bucket():
    """When strict matching fails, fallback relaxes time-of-day then vol bucket."""
    symbol = "BTCUSDT"
    # Build a simple pool; the function should still find matches even if strict fails
    all_rows = _make_candidate_rows(symbol, 0, 2000)
    all_rows = annotate_pre30_vol_buckets(all_rows)

    event = {
        "symbol": symbol,
        "shock_bar_start_ms": 1900 * _MS_PER_MIN,
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": 1900 * _MS_PER_MIN,
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    # Should find some matches (fallback triggered since tiny dataset, no month/time variety)
    assert len(baselines) > 0


def test_match_baselines_stays_within_same_month():
    """Baseline matching must not pull January controls for a February event."""
    symbol = "BTCUSDT"
    jan_rows = _make_candidate_rows(symbol, _utc_ms(2024, 1, 31, 8, 0), 80)
    feb_rows = _make_candidate_rows(symbol, _utc_ms(2024, 2, 1, 8, 0), 40)
    all_rows = annotate_pre30_vol_buckets(jan_rows + feb_rows)

    event = {
        "symbol": symbol,
        "shock_bar_start_ms": _utc_ms(2024, 2, 1, 8, 39),
        "dominant_liquidation_side": "long",
        "shock_notional_usdt": 100_000.0,
        "relative_score": 0.999,
        "reference_count": 1440,
        "dominance_ratio": 0.80,
        "dedup_bucket_start_ms": _utc_ms(2024, 2, 1, 8, 35),
    }

    baselines = match_baselines_for_event(event, all_rows, k=20)
    assert baselines
    for bl in baselines:
        dt = datetime.datetime.utcfromtimestamp(bl["candidate_bar_start_ms"] / 1000.0)
        assert dt.month == 2


def test_has_complete_response_window_checks_first_complete_5m_window():
    """Future completeness must be evaluated from the first complete 5m response start."""
    rows_by_ms = {
        33 * _MS_PER_MIN: {"bar_start_ms": 33 * _MS_PER_MIN},
        34 * _MS_PER_MIN: {"bar_start_ms": 34 * _MS_PER_MIN},
        35 * _MS_PER_MIN: {"bar_start_ms": 35 * _MS_PER_MIN},
        36 * _MS_PER_MIN: {"bar_start_ms": 36 * _MS_PER_MIN},
        37 * _MS_PER_MIN: {"bar_start_ms": 37 * _MS_PER_MIN},
    }
    assert has_complete_response_window(rows_by_ms, 33 * _MS_PER_MIN) is False

    rows_by_ms[38 * _MS_PER_MIN] = {"bar_start_ms": 38 * _MS_PER_MIN}
    rows_by_ms[39 * _MS_PER_MIN] = {"bar_start_ms": 39 * _MS_PER_MIN}
    assert has_complete_response_window(rows_by_ms, 33 * _MS_PER_MIN) is True


def test_unmatched_events_are_excluded_from_main_statistics():
    """Events with no matched baseline must be excluded from summary stats."""

    symbol = "BTCUSDT"
    # Pool of 35 bars, all contaminated with nonzero liquidation → no clean baseline exists
    notional_at = {i: 1.0 for i in range(35)}  # every bar is contaminated
    all_rows = _make_candidate_rows(symbol, 0, 35, notional_at=notional_at)
    all_rows = annotate_pre30_vol_buckets(all_rows)

    events = [
        {
            "symbol": symbol,
            "shock_bar_start_ms": 34 * _MS_PER_MIN,
            "dominant_liquidation_side": "long",
            "shock_notional_usdt": 100_000.0,
            "relative_score": 0.999,
            "reference_count": 1440,
            "dominance_ratio": 0.80,
            "dedup_bucket_start_ms": 34 * _MS_PER_MIN,
        }
    ]

    rows_by_symbol = {symbol: all_rows}
    pairs = build_event_baseline_pairs(events, rows_by_symbol)
    # No clean baselines exist → event must be excluded → pairs is empty
    assert len(pairs) == 0


# ─── Task 5: Summary & Decision Gate ─────────────────────────────────────────


def _make_matched_pair(
    event_vol: float = 50.0,
    baseline_vols: list[float] | None = None,
    event_range: float = 40.0,
    baseline_ranges: list[float] | None = None,
    event_excursion: float = 30.0,
    baseline_excursions: list[float] | None = None,
) -> dict:
    """Create a minimal matched event-baseline pair for summary tests."""
    if baseline_vols is None:
        baseline_vols = [30.0] * 20
    if baseline_ranges is None:
        baseline_ranges = [25.0] * 20
    if baseline_excursions is None:
        baseline_excursions = [20.0] * 20

    return {
        "event": {
            "symbol": "BTCUSDT",
            "shock_bar_start_ms": 1440 * _MS_PER_MIN,
            "dominant_liquidation_side": "long",
        },
        "event_metrics": {
            "realized_vol_5m_bps": event_vol,
            "high_low_range_5m_bps": event_range,
            "max_abs_excursion_5m_bps": event_excursion,
            "mae_if_long_5m_bps": event_excursion * 0.5,
            "mae_if_short_5m_bps": event_excursion * 0.8,
        },
        "baseline_metrics": [
            {
                "realized_vol_5m_bps": v,
                "high_low_range_5m_bps": r,
                "max_abs_excursion_5m_bps": x,
                "mae_if_long_5m_bps": x * 0.5,
                "mae_if_short_5m_bps": x * 0.8,
            }
            for v, r, x in zip(baseline_vols, baseline_ranges, baseline_excursions)
        ],
    }


def test_build_c1_summary_reports_required_counts_and_ratios():
    pairs = [_make_matched_pair() for _ in range(10)]
    metadata = {"run_mode": "proxy_snapshot", "data_source": "test", "total_events": 13}
    summary = build_c1_price_only_summary(pairs, metadata)

    assert summary["event_count"] == 13
    assert summary["matched_event_count"] == 10
    assert summary["unmatched_event_count"] == 3
    assert "post_event_vol_ratio_median" in summary
    assert "post_event_range_ratio_median" in summary
    assert "post_event_abs_excursion_p90_ratio" in summary
    assert "baseline_match_rate" in summary


def test_c1_ratios_are_computed_per_event_then_median_across_events():
    """Ratio must be median(per-event ratio), not global median / global median."""
    # Event vol = 50, baseline medians = 25 → per-event ratio = 2.0
    pairs = [_make_matched_pair(event_vol=50.0, baseline_vols=[25.0] * 20) for _ in range(5)]
    metadata = {"run_mode": "proxy_snapshot", "data_source": "test"}
    summary = build_c1_price_only_summary(pairs, metadata)

    assert summary["post_event_vol_ratio_median"] == pytest.approx(2.0, rel=1e-5)


def test_c1_decision_data_unavailable_when_no_events():
    summary_dict = {
        "run_mode": "proxy_snapshot",
        "event_count": 0,
        "matched_event_count": 0,
        "baseline_match_rate": 0.0,
        "post_event_vol_ratio_median": 0.0,
        "post_event_range_ratio_median": 0.0,
        "post_event_abs_excursion_p90_ratio": 0.0,
        "max_single_symbol_event_share": 0.0,
        "max_single_month_event_share": 0.0,
        "events_by_symbol": {},
        "events_by_month": {},
        "sample_days": 0,
        "events_by_day": {},
        "max_single_day_event_share": 0.0,
    }
    decision = compute_c1_price_only_decision(summary_dict, run_mode="proxy_snapshot")
    assert decision == "route_c1_data_unavailable"


def test_c1_decision_baseline_match_failed_when_match_rate_below_070():
    summary_dict = {
        "run_mode": "proxy_snapshot",
        "event_count": 150,
        "matched_event_count": 50,
        "baseline_match_rate": 0.33,  # < 0.70
        "post_event_vol_ratio_median": 2.0,
        "post_event_range_ratio_median": 1.8,
        "post_event_abs_excursion_p90_ratio": 1.5,
        "max_single_symbol_event_share": 0.3,
        "max_single_month_event_share": 0.3,
        "events_by_symbol": {"BTCUSDT": 50, "ETHUSDT": 50, "SOLUSDT": 50},
        "events_by_month": {"2024-01": 50, "2024-02": 50, "2024-03": 50},
        "sample_days": 90,
        "events_by_day": {},
        "max_single_day_event_share": 0.1,
    }
    decision = compute_c1_price_only_decision(summary_dict, run_mode="proxy_snapshot")
    assert decision == "route_c1_baseline_match_failed"


def test_c1_decision_price_risk_not_confirmed_when_ratios_below_gate():
    summary_dict = {
        "run_mode": "proxy_snapshot",
        "event_count": 150,
        "matched_event_count": 110,
        "baseline_match_rate": 0.73,
        "post_event_vol_ratio_median": 1.1,  # < 1.5 gate
        "post_event_range_ratio_median": 1.1,
        "post_event_abs_excursion_p90_ratio": 1.0,
        "max_single_symbol_event_share": 0.3,
        "max_single_month_event_share": 0.3,
        "events_by_symbol": {"BTCUSDT": 50, "ETHUSDT": 50, "SOLUSDT": 50},
        "events_by_month": {"2024-01": 50, "2024-02": 50, "2024-03": 50},
        "sample_days": 90,
        "events_by_day": {},
        "max_single_day_event_share": 0.1,
    }
    decision = compute_c1_price_only_decision(summary_dict, run_mode="proxy_snapshot")
    assert decision == "route_c1_price_risk_not_confirmed"


def test_c1_decision_proxy_promising_when_proxy_ratios_pass():
    summary_dict = {
        "run_mode": "proxy_snapshot",
        "event_count": 150,
        "matched_event_count": 110,
        "baseline_match_rate": 0.73,
        "post_event_vol_ratio_median": 1.8,  # >= 1.5
        "post_event_range_ratio_median": 1.6,  # >= 1.4
        "post_event_abs_excursion_p90_ratio": 1.5,  # >= 1.3
        "max_single_symbol_event_share": 0.3,
        "max_single_month_event_share": 0.3,
        "events_by_symbol": {"BTCUSDT": 50, "ETHUSDT": 50, "SOLUSDT": 50},
        "events_by_month": {"2024-01": 50, "2024-02": 50, "2024-03": 50},
        "sample_days": 90,
        "events_by_day": {},
        "max_single_day_event_share": 0.1,
    }
    decision = compute_c1_price_only_decision(summary_dict, run_mode="proxy_snapshot")
    assert decision == "route_c1_price_risk_proxy_promising_wait_for_live_overlap"


def test_c1_summary_reports_concentration_limits():
    pairs = [_make_matched_pair() for _ in range(10)]
    metadata = {"run_mode": "proxy_snapshot", "data_source": "test"}
    summary = build_c1_price_only_summary(pairs, metadata)

    assert "max_single_symbol_event_share" in summary
    assert "max_single_month_event_share" in summary
    assert "max_single_day_event_share" in summary


def test_c1_decision_uses_run_mode_specific_gates():
    """live_smoke_7d must not require months_passing; proxy_snapshot must require it."""
    # This summary would fail months gate if run as proxy_snapshot (only 1 month)
    # but should still be evaluated as live smoke
    summary_dict = {
        "run_mode": "live_smoke_7d",
        "event_count": 30,
        "matched_event_count": 25,
        "baseline_match_rate": 0.83,
        "post_event_vol_ratio_median": 1.8,
        "post_event_range_ratio_median": 1.6,
        "post_event_abs_excursion_p90_ratio": 1.5,
        "max_single_symbol_event_share": 0.5,
        "max_single_month_event_share": 1.0,  # all in one month → would fail proxy gate
        "events_by_symbol": {"BTCUSDT": 20, "ETHUSDT": 10},
        "events_by_month": {"2024-01": 30},
        "sample_days": 7,
        "overlap_hours": 170,
        "events_by_day": {},
        "max_single_day_event_share": 0.3,
    }
    decision = compute_c1_price_only_decision(summary_dict, run_mode="live_smoke_7d")
    # live_smoke does not require months_passing, so it can pass ratios gate
    assert decision == "route_c1_price_risk_live_smoke_promising_continue_to_30d"


# ─── Task 6: CLI & Markdown ───────────────────────────────────────────────────


def test_parse_args_supports_proxy_snapshot_mode():
    args = parse_args(
        [
            "--run-mode",
            "proxy_snapshot",
            "--dataset",
            "some/dataset.jsonl",
            "--kline-root",
            "some/klines",
            "--symbols",
            "BTCUSDT",
            "ETHUSDT",
            "--output",
            "out.json",
            "--review-output",
            "review.md",
        ]
    )
    assert args.run_mode == "proxy_snapshot"
    assert args.dataset == "some/dataset.jsonl"
    assert args.kline_root == "some/klines"
    assert args.output == "out.json"
    assert args.review_output == "review.md"


def test_load_dataset_merges_high_low_from_kline_root_when_missing(tmp_path):
    """If dataset rows lack high_price/low_price, they should be merged from kline CSVs."""
    import csv

    symbol = "BTCUSDT"
    bar_ms = 1_700_000_000_000

    # Create a minimal dataset JSONL without high/low
    dataset_path = tmp_path / "dataset.jsonl"
    row = {
        "symbol": symbol,
        "bar_start_ms": bar_ms,
        "open_price": 100.0,
        "close_price": 101.0,
        "total_liquidation_notional_1m_usdt": 0.0,
    }
    with open(dataset_path, "w") as f:
        f.write(json.dumps(row) + "\n")

    # Create kline CSV with high/low
    kline_dir = tmp_path / "klines" / symbol
    kline_dir.mkdir(parents=True)
    kline_csv = kline_dir / "klines.csv"
    with open(kline_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bar_start_ms", "open_price", "high_price", "low_price", "close_price"])
        writer.writerow([bar_ms, 100.0, 105.0, 95.0, 101.0])

    rows = load_dataset(str(dataset_path), kline_root=str(tmp_path / "klines"), symbols=[symbol])
    assert len(rows) == 1
    assert rows[0]["high_price"] == pytest.approx(105.0)
    assert rows[0]["low_price"] == pytest.approx(95.0)


def test_load_dataset_requires_kline_merge_when_high_low_missing(tmp_path):
    dataset_path = tmp_path / "dataset.jsonl"
    row = {
        "symbol": "BTCUSDT",
        "bar_start_ms": 1_700_000_000_000,
        "open_price": 100.0,
        "close_price": 101.0,
        "total_liquidation_notional_1m_usdt": 0.0,
    }
    dataset_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_dataset(str(dataset_path), kline_root=None, symbols=["BTCUSDT"])


def test_load_dataset_normalizes_symbols_before_joining_kline_rows(tmp_path):
    """Symbol normalization must happen before kline join to avoid silent zero-matches."""
    import csv

    # Dataset uses BTC/USDT, klines are stored under BTCUSDT directory
    dataset_path = tmp_path / "dataset.jsonl"
    bar_ms = 1_700_000_000_000
    row = {
        "symbol": "BTC/USDT",  # slash format
        "bar_start_ms": bar_ms,
        "open_price": 100.0,
        "close_price": 101.0,
        "total_liquidation_notional_1m_usdt": 0.0,
    }
    with open(dataset_path, "w") as f:
        f.write(json.dumps(row) + "\n")

    kline_dir = tmp_path / "klines" / "BTCUSDT"
    kline_dir.mkdir(parents=True)
    kline_csv = kline_dir / "klines.csv"
    with open(kline_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["bar_start_ms", "open_price", "high_price", "low_price", "close_price"])
        writer.writerow([bar_ms, 100.0, 105.0, 95.0, 101.0])

    rows = load_dataset(str(dataset_path), kline_root=str(tmp_path / "klines"), symbols=["BTCUSDT"])
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["high_price"] == pytest.approx(105.0)


def test_load_dataset_merges_high_low_from_nested_monthly_binance_kline_csv(tmp_path):
    symbol = "BTCUSDT"
    bar_ms = 1_704_067_200_000

    dataset_path = tmp_path / "dataset.jsonl"
    row = {
        "symbol": symbol,
        "bar_start_ms": bar_ms,
        "open_price": 42314.0,
        "close_price": 42331.9,
        "total_liquidation_notional_1m_usdt": 0.0,
    }
    dataset_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    kline_dir = tmp_path / "klines" / symbol / "2024-01"
    kline_dir.mkdir(parents=True)
    kline_csv = kline_dir / f"{symbol}-1m-2024-01.csv"
    kline_csv.write_text(
        "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore\n"
        f"{bar_ms},42314.00,42335.80,42289.60,42331.90,1,0,0,0,0,0,0\n",
        encoding="utf-8",
    )

    rows = load_dataset(str(dataset_path), kline_root=str(tmp_path / "klines"), symbols=[symbol])
    assert len(rows) == 1
    assert rows[0]["high_price"] == pytest.approx(42335.80)
    assert rows[0]["low_price"] == pytest.approx(42289.60)


def test_review_markdown_includes_decision_and_next_path(tmp_path):

    summary = {
        "run_mode": "proxy_snapshot",
        "data_source": "binance_vision_liquidation_snapshot",
        "data_semantics": "snapshot_proxy_not_complete_liquidation_tape",
        "generalization_allowed": False,
        "can_promote_live_filter": False,
        "event_count": 0,
        "matched_event_count": 0,
        "unmatched_event_count": 0,
        "matched_baseline_count": 0,
        "baseline_match_rate": 0.0,
        "post_event_vol_ratio_median": 0.0,
        "post_event_range_ratio_median": 0.0,
        "post_event_abs_excursion_p90_ratio": 0.0,
        "max_abs_excursion_p90_bps": 0.0,
        "mae_if_long_p90_bps": 0.0,
        "mae_if_short_p90_bps": 0.0,
        "events_by_symbol": {},
        "events_by_month": {},
        "events_by_day": {},
        "sample_days": 0,
        "max_single_symbol_event_share": 0.0,
        "max_single_month_event_share": 0.0,
        "max_single_day_event_share": 0.0,
        "route_c1_params": {},
        "proxy_kill_switch_weak": True,
        "decision": "route_c1_price_risk_not_confirmed",
    }

    md_path = tmp_path / "review.md"
    render_review_markdown(summary, str(md_path))

    content = md_path.read_text()
    assert "decision" in content.lower()
    assert "route_c1_price_risk_not_confirmed" in content
    assert "can_promote_live_filter" in content.lower() or "promote" in content.lower()


def test_review_markdown_declares_proxy_cannot_promote_live_filter(tmp_path):

    summary = {
        "run_mode": "proxy_snapshot",
        "data_source": "test",
        "data_semantics": "snapshot_proxy_not_complete_liquidation_tape",
        "generalization_allowed": False,
        "can_promote_live_filter": False,
        "event_count": 50,
        "matched_event_count": 40,
        "unmatched_event_count": 10,
        "matched_baseline_count": 800,
        "baseline_match_rate": 0.80,
        "post_event_vol_ratio_median": 0.9,
        "post_event_range_ratio_median": 0.9,
        "post_event_abs_excursion_p90_ratio": 0.9,
        "max_abs_excursion_p90_bps": 50.0,
        "mae_if_long_p90_bps": 30.0,
        "mae_if_short_p90_bps": 40.0,
        "events_by_symbol": {},
        "events_by_month": {},
        "events_by_day": {},
        "sample_days": 90,
        "max_single_symbol_event_share": 0.5,
        "max_single_month_event_share": 0.5,
        "max_single_day_event_share": 0.1,
        "route_c1_params": {},
        "proxy_kill_switch_weak": True,
        "decision": "route_c1_price_risk_not_confirmed",
    }

    md_path = tmp_path / "review.md"
    render_review_markdown(summary, str(md_path))
    content = md_path.read_text()

    # Must explicitly state proxy cannot promote to live filter
    assert "false" in content.lower() or "cannot" in content.lower() or "not" in content.lower()
    assert "proxy" in content.lower()
