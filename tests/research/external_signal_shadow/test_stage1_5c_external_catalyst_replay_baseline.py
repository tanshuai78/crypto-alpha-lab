from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_baseline import (
    compute_price_move_baseline_events,
    sample_symbol_hour_event_type_matched_random_baseline,
)


def _bar(symbol, t, open_price, close_price):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": open_price,
        "close": close_price,
        "quote_volume": 10_000_000,
    }


def test_price_move_baseline_respects_signed_direction():
    price_index = {"ABCUSDT": [
        _bar("ABCUSDT", 0, 100, 100),
        _bar("ABCUSDT", 900_000, 100, 102),
        _bar("ABCUSDT", 1_800_000, 102, 102),
        _bar("ABCUSDT", 2_700_000, 102, 102),
        _bar("ABCUSDT", 3_600_000, 102, 102),
    ]}
    events = compute_price_move_baseline_events(
        price_index=price_index,
        symbol="ABCUSDT",
        signed_direction=1,
        threshold_bps=150,
    )
    assert events


def test_price_move_baseline_excludes_candidate_cooldown_windows():
    price_index = {"ABCUSDT": [_bar("ABCUSDT", i * 900_000, 100, 102 if i == 4 else 100) for i in range(20)]}
    events = compute_price_move_baseline_events(
        price_index=price_index,
        symbol="ABCUSDT",
        signed_direction=1,
        threshold_bps=150,
        excluded_event_times_ms=[0],
        cooldown_hours=24,
    )
    assert events == []


def test_random_baseline_matches_symbol_event_type_direction_distribution():
    candidates = [
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_direction": 1, "entry_delay_hours": 1, "event_time_ms": 0},
        {"symbol": "XYZUSDT", "event_type": "exchange_delisting_notice", "signed_direction": -1, "entry_delay_hours": 1, "event_time_ms": 3_600_000},
    ]
    price_index = {
        "ABCUSDT": [_bar("ABCUSDT", i * 900_000, 100, 100) for i in range(100)],
        "XYZUSDT": [_bar("XYZUSDT", i * 900_000, 100, 100) for i in range(100)],
    }
    trials = sample_symbol_hour_event_type_matched_random_baseline(
        candidates=candidates,
        price_index=price_index,
        trials=5,
        random_seed=42,
    )
    assert len(trials) == 5
    assert all(len(trial) == 2 for trial in trials)
