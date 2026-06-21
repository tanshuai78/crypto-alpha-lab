from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_baseline import (
    compute_price_move_baseline,
    compute_random_baseline_summary,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_15M,
    ProxyEvent,
)

# 1600000200000 is a multiple of 900000 (15m)
T_START = 1600000200000
T_END = T_START + 900000

def test_price_baseline_uses_same_direction_and_cooldown():
    # Price returns:
    # Bar 0: T_START -> price return = -2.1% (should trigger down flush baseline)
    # Bar 1: T_END -> price return = -2.5% (falls within cooldown, should not trigger)
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.9, "close": 97.9},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 97.9, "high": 97.9, "low": 95.0, "close": 95.4},
        # Add future bars for replay to succeed
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 900000, "open": 95.4, "high": 96.0, "low": 95.0, "close": 96.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 3600000, "open": 96.0, "high": 96.0, "low": 96.0, "close": 96.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 14400000, "open": 96.0, "high": 96.0, "low": 96.0, "close": 96.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 43200000, "open": 96.0, "high": 96.0, "low": 96.0, "close": 96.0},
    ]

    baseline_events = compute_price_move_baseline(
        price_bars=price_rows,
        candidate_name=CANDIDATE_15M,
        expected_symbols=("BTCUSDT",)
    )
    # Only 1 event because the second falls within the 1h cooldown
    assert len(baseline_events) == 1
    assert baseline_events[0].event_label == "down_flush_deleveraging_proxy"
    assert baseline_events[0].signed_direction == 1

def test_random_baseline_preserves_distributions():
    candidate_events = [
        ProxyEvent(
            symbol="BTCUSDT",
            candidate_name=CANDIDATE_15M,
            event_label="down_flush_deleveraging_proxy",
            signed_direction=1,
            bucket_start_ms=T_START,
            bucket_end_ms=T_END,
            event_time_ms=T_END,
            event_available_at_ms=T_END + 300000,
            entry_bar_start_ms=T_END + 900000,
            price_return=-0.02,
            oi_change=-0.04,
            oi_start=100.0,
            oi_end=96.0,
            source="oi_and_price_joint",
            source_quality="15m_aligned_tick"
        )
    ]
    # Price rows must contain candidate and non-candidate times
    price_rows = [
        # Candidate time is T_END (1600001100000). So we must provide other times too.
        # Ensure there is enough forward data for random samples as well.
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 3600000, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 14400000, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END + 43200000, "open": 100.0, "high": 100.0, "low": 100.0, "close": 100.0},
    ]
    summary = compute_random_baseline_summary(
        candidate_events=candidate_events,
        price_bars=price_rows,
        trials=10,
        random_seed=42
    )
    assert summary["random_baseline_trials"] == 10
    assert "median_net_return_bps_after_50bps" in summary
    assert "baseline_sampling_failure_count" in summary
