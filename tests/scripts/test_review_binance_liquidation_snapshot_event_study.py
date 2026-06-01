"""
Tests for review_binance_liquidation_snapshot_event_study.py

All tests use synthetic in-memory data. No file I/O in unit tests.
"""

import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "review_binance_liquidation_snapshot_event_study.py"
)


def _load_review_module():
    spec = importlib.util.spec_from_file_location(
        "review_binance_liquidation_snapshot_event_study", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# -------------------------------------------------------------------------
# Synthetic event factories
# -------------------------------------------------------------------------

_MS_PER_MIN = 60_000
_JAN_2024_START_MS = 1_704_067_200_000


def _make_event(
    symbol: str = "BTCUSDT",
    shock_ms: int = _JAN_2024_START_MS,
    side: str = "long",
    notional: float = 5_000_000.0,
    month: str = "2024-01",
) -> dict:
    """
    Minimal event dict compatible with review density functions.
    Mirrors keys from LiquidationShockEvent + month label.
    """
    return {
        "symbol": symbol,
        "shock_bar_start_ms": shock_ms,
        "dominant_liquidation_side": side,
        "shock_notional_usdt": notional,
        "month": month,
    }


def _make_events(n: int, base_ms: int = _JAN_2024_START_MS) -> list[dict]:
    return [_make_event(shock_ms=base_ms + i * _MS_PER_MIN * 120) for i in range(n)]


# -------------------------------------------------------------------------
# Module structure
# -------------------------------------------------------------------------


def test_review_module_imports():
    mod = _load_review_module()
    assert hasattr(mod, "compute_event_density"), "Must export compute_event_density"
    assert hasattr(mod, "compute_review_decision"), "Must export compute_review_decision"
    assert hasattr(mod, "ALLOWED_DECISIONS"), "Must export ALLOWED_DECISIONS"


# -------------------------------------------------------------------------
# compute_event_density
# -------------------------------------------------------------------------


def test_compute_event_density_total_count():
    mod = _load_review_module()
    events = _make_events(25)
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    assert density["total_events"] == 25


def test_compute_event_density_per_month():
    mod = _load_review_module()
    # 10 events in Jan, 8 in Feb, 7 in Mar
    events = (
        [_make_event(symbol="BTCUSDT", shock_ms=_JAN_2024_START_MS + i * _MS_PER_MIN * 60, **{"month": "2024-01"}) for i in range(10)]
        + [_make_event(symbol="BTCUSDT", shock_ms=_JAN_2024_START_MS + i * _MS_PER_MIN * 60, **{"month": "2024-02"}) for i in range(8)]
        + [_make_event(symbol="BTCUSDT", shock_ms=_JAN_2024_START_MS + i * _MS_PER_MIN * 60, **{"month": "2024-03"}) for i in range(7)]
    )
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    assert density["events_per_month"]["2024-01"] == 10
    assert density["events_per_month"]["2024-02"] == 8
    assert density["events_per_month"]["2024-03"] == 7


def test_compute_event_density_by_symbol():
    mod = _load_review_module()
    events = (
        [_make_event(symbol="BTCUSDT") for _ in range(15)]
        + [_make_event(symbol="ETHUSDT") for _ in range(10)]
    )
    density = mod.compute_event_density(events, months=["2024-01"])
    assert density["events_by_symbol"]["BTCUSDT"] == 15
    assert density["events_by_symbol"]["ETHUSDT"] == 10


def test_compute_event_density_by_side():
    mod = _load_review_module()
    events = (
        [_make_event(side="long") for _ in range(20)]
        + [_make_event(side="short") for _ in range(5)]
    )
    density = mod.compute_event_density(events, months=["2024-01"])
    assert density["events_by_side"]["long"] == 20
    assert density["events_by_side"]["short"] == 5


def test_compute_event_density_by_symbol_month():
    mod = _load_review_module()
    events = [
        _make_event(symbol="BTCUSDT", **{"month": "2024-01"}),
        _make_event(symbol="BTCUSDT", **{"month": "2024-01"}),
        _make_event(symbol="ETHUSDT", **{"month": "2024-02"}),
    ]
    density = mod.compute_event_density(events, months=["2024-01", "2024-02"])
    assert density["events_by_symbol_month"]["BTCUSDT"]["2024-01"] == 2
    assert density["events_by_symbol_month"]["ETHUSDT"]["2024-02"] == 1


def test_compute_event_density_by_symbol_side():
    mod = _load_review_module()
    events = [
        _make_event(symbol="BTCUSDT", side="long"),
        _make_event(symbol="BTCUSDT", side="long"),
        _make_event(symbol="BTCUSDT", side="short"),
    ]
    density = mod.compute_event_density(events, months=["2024-01"])
    assert density["events_by_symbol_side"]["BTCUSDT"]["long"] == 2
    assert density["events_by_symbol_side"]["BTCUSDT"]["short"] == 1


# -------------------------------------------------------------------------
# compute_review_decision
# -------------------------------------------------------------------------


def test_compute_review_decision_allowed_states():
    mod = _load_review_module()
    allowed = set(mod.ALLOWED_DECISIONS)
    assert "binance_snapshot_data_failed" in allowed
    assert "binance_snapshot_event_density_failed" in allowed
    assert "binance_snapshot_structure_not_confirmed" in allowed
    assert "binance_snapshot_structure_confirmed_for_q1_2024_only" in allowed


def test_compute_review_decision_data_failed_when_no_events():
    mod = _load_review_module()
    density = mod.compute_event_density([], months=["2024-01", "2024-02", "2024-03"])
    decision = mod.compute_review_decision(
        density=density,
        months=["2024-01", "2024-02", "2024-03"],
        min_total_events=10,
        min_events_per_month=1,
    )
    assert decision == "binance_snapshot_data_failed"


def test_compute_review_decision_density_failed_when_below_threshold():
    mod = _load_review_module()
    # Only 5 events, below min_total_events=10
    events = _make_events(5)
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    decision = mod.compute_review_decision(
        density=density,
        months=["2024-01", "2024-02", "2024-03"],
        min_total_events=10,
        min_events_per_month=1,
    )
    assert decision == "binance_snapshot_event_density_failed"


def test_compute_review_decision_density_failed_when_month_too_sparse():
    mod = _load_review_module()
    # 20 total but 0 in one month
    events = [
        _make_event(**{"month": "2024-01"}) for _ in range(10)
    ] + [
        _make_event(**{"month": "2024-02"}) for _ in range(10)
    ]
    # 2024-03 has 0 events
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    decision = mod.compute_review_decision(
        density=density,
        months=["2024-01", "2024-02", "2024-03"],
        min_total_events=10,
        min_events_per_month=1,
    )
    assert decision == "binance_snapshot_event_density_failed"


def test_compute_review_decision_structure_confirmed():
    mod = _load_review_module()
    events = (
        [_make_event(**{"month": "2024-01"}) for _ in range(20)]
        + [_make_event(**{"month": "2024-02"}) for _ in range(15)]
        + [_make_event(**{"month": "2024-03"}) for _ in range(10)]
    )
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    decision = mod.compute_review_decision(
        density=density,
        months=["2024-01", "2024-02", "2024-03"],
        min_total_events=10,
        min_events_per_month=1,
    )
    assert decision in (
        "binance_snapshot_structure_confirmed_for_q1_2024_only",
        "binance_snapshot_structure_not_confirmed",
    )


def test_compute_review_decision_returns_allowed_state():
    mod = _load_review_module()
    allowed = set(mod.ALLOWED_DECISIONS)
    for n_events in [0, 5, 30, 50]:
        events = _make_events(n_events)
        for ev in events:
            ev["month"] = "2024-01"
        density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
        decision = mod.compute_review_decision(
            density=density,
            months=["2024-01", "2024-02", "2024-03"],
            min_total_events=10,
            min_events_per_month=1,
        )
        assert decision in allowed, f"Unexpected decision '{decision}' for {n_events} events"


def test_compute_review_decision_downgrades_when_universe_integrity_fails():
    mod = _load_review_module()
    events = (
        [_make_event(**{"month": "2024-01"}) for _ in range(20)]
        + [_make_event(**{"month": "2024-02"}) for _ in range(20)]
        + [_make_event(**{"month": "2024-03"}) for _ in range(20)]
    )
    density = mod.compute_event_density(events, months=["2024-01", "2024-02", "2024-03"])
    directional_bias = {
        5: {"directional_ratio": 0.60},
        10: {"directional_ratio": 0.61},
        15: {"directional_ratio": 0.40},
    }
    decision = mod.compute_review_decision(
        density=density,
        months=["2024-01", "2024-02", "2024-03"],
        min_total_events=10,
        min_events_per_month=1,
        directional_bias_results=directional_bias,
        universe_integrity_ok=False,
    )
    assert decision == "binance_snapshot_structure_not_confirmed"


def test_detect_shocks_with_gap_resets_does_not_leak_prior_segment_lookback():
    mod = _load_review_module()
    jan_start = _JAN_2024_START_MS
    mar_start = _JAN_2024_START_MS + 60 * 1440 * _MS_PER_MIN

    rows = []
    for i in range(1440):
        rows.append(
            {
                "symbol": "BTCUSDT",
                "bar_start_ms": jan_start + i * _MS_PER_MIN,
                "long_liquidation_notional_1m_usdt": 0.0,
                "short_liquidation_notional_1m_usdt": 0.0,
                "open_price": 50000.0,
                "close_price": 50000.0,
            }
        )
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": jan_start + 1440 * _MS_PER_MIN,
            "long_liquidation_notional_1m_usdt": 100000.0,
            "short_liquidation_notional_1m_usdt": 0.0,
            "open_price": 50000.0,
            "close_price": 49900.0,
        }
    )
    rows.append(
        {
            "symbol": "BTCUSDT",
            "bar_start_ms": mar_start,
            "long_liquidation_notional_1m_usdt": 100000.0,
            "short_liquidation_notional_1m_usdt": 0.0,
            "open_price": 48000.0,
            "close_price": 47900.0,
        }
    )

    events = mod.detect_shocks_with_gap_resets(rows)
    assert len(events) == 1
    assert events[0].shock_bar_start_ms == jan_start + 1440 * _MS_PER_MIN
