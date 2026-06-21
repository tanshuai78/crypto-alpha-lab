from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    CANDIDATE_15M,
    EVENT_DOWN_FLUSH,
    EVENT_UP_SQUEEZE,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_signals import (
    detect_deleveraging_proxy_events,
    find_closest_row,
)

# 1600000200000 is a multiple of 900000 (15m).
# 1600000200000 / 900000 = 1777778.
T_START = 1600000200000
T_END = T_START + 900000


def test_oi_lookup_is_asof_and_never_uses_future_row():
    rows = [
        {"timestamp_ms": 1000, "sumOpenInterest": 100.0},
        {"timestamp_ms": 2000, "sumOpenInterest": 90.0},
    ]

    row = find_closest_row(rows, "timestamp_ms", target_ms=1800, max_staleness=1000)

    assert row is not None
    assert row["timestamp_ms"] == 1000

def test_uses_sum_open_interest_not_sum_open_interest_value_for_trigger():
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0, "sumOpenInterestValue": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 95.0, "sumOpenInterestValue": 110.0},
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.0, "close": 97.0},
    ]
    source_quality = {
        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: {"BTCUSDT": True}
        }
    }
    events, _ = detect_deleveraging_proxy_events(
        oi_rows=oi_rows,
        price_rows=price_rows,
        candidate_name=CANDIDATE_15M,
        source_quality=source_quality,
        expected_symbols=("BTCUSDT",)
    )
    assert len(events) == 1
    assert events[0].event_label == EVENT_DOWN_FLUSH
    assert events[0].signed_direction == 1

def test_down_flush_proxy_signed_long():
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0, "sumOpenInterestValue": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 96.0, "sumOpenInterestValue": 96.0},
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.0, "close": 97.9},
    ]
    source_quality = {
        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: {"BTCUSDT": True}
        }
    }
    events, _ = detect_deleveraging_proxy_events(
        oi_rows=oi_rows,
        price_rows=price_rows,
        candidate_name=CANDIDATE_15M,
        source_quality=source_quality,
        expected_symbols=("BTCUSDT",)
    )
    assert len(events) == 1
    assert events[0].event_label == EVENT_DOWN_FLUSH
    assert events[0].signed_direction == 1

def test_up_squeeze_proxy_signed_short_but_no_short_execution_intent():
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0, "sumOpenInterestValue": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 96.0, "sumOpenInterestValue": 96.0},
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 103.0, "low": 100.0, "close": 102.5},
    ]
    source_quality = {
        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: {"BTCUSDT": True}
        }
    }
    events, _ = detect_deleveraging_proxy_events(
        oi_rows=oi_rows,
        price_rows=price_rows,
        candidate_name=CANDIDATE_15M,
        source_quality=source_quality,
        expected_symbols=("BTCUSDT",)
    )
    assert len(events) == 1
    assert events[0].event_label == EVENT_UP_SQUEEZE
    assert events[0].signed_direction == -1

def test_configured_data_lag_applied_to_available_at():
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 96.0},
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.0, "close": 97.9},
    ]
    source_quality = {
        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: {"BTCUSDT": True}
        }
    }
    events, _ = detect_deleveraging_proxy_events(
        oi_rows=oi_rows,
        price_rows=price_rows,
        candidate_name=CANDIDATE_15M,
        source_quality=source_quality,
        expected_symbols=("BTCUSDT",)
    )
    assert len(events) == 1
    assert events[0].event_available_at_ms == T_END + 300000

def test_event_cooldown_deduplicates_cluster():
    # Cooldown for 15m is 1h (3600000 ms).
    # First event ends at T_END.
    # Second event ends at T_END + 900000 (T=30m), which is within 1h. It should be skipped.
    oi_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": T_START, "sumOpenInterest": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": T_END, "sumOpenInterest": 96.0},

        {"symbol": "BTCUSDT", "timestamp_ms": T_END + 900000, "sumOpenInterest": 92.0},
    ]
    price_rows = [
        {"symbol": "BTCUSDT", "bar_start_ms": T_START, "open": 100.0, "high": 100.0, "low": 97.0, "close": 97.9},
        {"symbol": "BTCUSDT", "bar_start_ms": T_END, "open": 97.9, "high": 97.9, "low": 95.0, "close": 95.5},
    ]
    source_quality = {
        "candidate_window_supported_by_symbol": {
            CANDIDATE_15M: {"BTCUSDT": True}
        }
    }
    events, _ = detect_deleveraging_proxy_events(
        oi_rows=oi_rows,
        price_rows=price_rows,
        candidate_name=CANDIDATE_15M,
        source_quality=source_quality,
        expected_symbols=("BTCUSDT",)
    )
    assert len(events) == 1
