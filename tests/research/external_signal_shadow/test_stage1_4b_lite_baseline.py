from research.external_signal_shadow.stage1_4b_lite_baseline import (
    compute_price_move_1h_baseline,
    sample_symbol_hour_matched_random_baseline,
)
from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent


def test_random_baseline_matches_event_count_and_symbol_distribution():
    candidates = [
        CandidateEvent("oi_expansion_trend_confirmation", "BTCUSDT", 3600000, 4500000, 5400000, 1, {}),
        CandidateEvent("oi_expansion_trend_confirmation", "BTCUSDT", 7200000, 8100000, 9000000, 1, {}),
        CandidateEvent("oi_expansion_trend_confirmation", "ETHUSDT", 10800000, 11700000, 12600000, -1, {}),
    ]

    # eligible times for BTCUSDT and ETHUSDT.
    # Hour bucket for event 1 (3600000 ms = 1h): hour is 1.
    # Hour bucket for event 2 (7200000 ms = 2h): hour is 2.
    # Hour bucket for event 3 (10800000 ms = 3h): hour is 3.
    eligible = {
        "BTCUSDT": [
            3600000 + 86400000,  # hour 1 next day
            7200000 + 86400000,  # hour 2 next day
            3600000 + 2*86400000,
        ],
        "ETHUSDT": [
            10800000 + 86400000, # hour 3 next day
        ]
    }

    trials = sample_symbol_hour_matched_random_baseline(
        candidates,
        eligible_times_by_symbol=eligible,
        trials=5,
        random_seed=42
    )

    assert len(trials) == 5
    for trial in trials:
        assert len(trial) == 3
        # Match symbol distribution
        btc_events = [e for e in trial if e.symbol == "BTCUSDT"]
        eth_events = [e for e in trial if e.symbol == "ETHUSDT"]
        assert len(btc_events) == 2
        assert len(eth_events) == 1

        # Verify exact hour matching
        # btc_events[0] should match hour 1
        assert (btc_events[0].event_time_ms // 3600000) % 24 == 1
        # btc_events[1] should match hour 2
        assert (btc_events[1].event_time_ms // 3600000) % 24 == 2
        # eth_events[0] should match hour 3
        assert (eth_events[0].event_time_ms // 3600000) % 24 == 3


def test_price_move_1h_baseline_computation():
    # We will build a series of price bars where there is a 1h price move of 2%
    # 15m = 900000 ms. 1h = 4 bars.
    price_bars = []
    for i in range(30):
        t = i * 900000
        # price goes up by 2% from i=4 to i=8
        c = 102.0 if i >= 8 else 100.0
        price_bars.append({
            "symbol": "BTCUSDT",
            "bar_start_ms": t,
            "close_price": c,
            "quote_volume": 10000.0,
        })

    baseline_events = compute_price_move_1h_baseline(price_bars, default_symbols=["BTCUSDT"])
    # There should be an event detected around index 8
    assert len(baseline_events) > 0
    assert baseline_events[0].symbol == "BTCUSDT"
    assert baseline_events[0].signed_direction == 1
