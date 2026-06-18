from research.external_signal_shadow.stage1_4b_lite_signals import build_candidate_definitions


def test_build_candidate_definitions_freezes_three_families():
    defs = build_candidate_definitions()
    assert set(defs.keys()) == {
        "oi_expansion_trend_confirmation",
        "funding_oi_crowding_unwind",
        "oi_contraction_after_price_flush",
    }

    # Check deleveraging_proxy_only flag
    assert defs["oi_contraction_after_price_flush"]["deleveraging_proxy_only"] is True
    assert defs["funding_oi_crowding_unwind"].get("signed_replay_only") is True

    assert defs["oi_expansion_trend_confirmation"]["long"]["price_4h_return_gte"] == 0.015
    assert defs["funding_oi_crowding_unwind"]["long_crowded_unwind"]["signed_direction"] == -1
    assert defs["oi_contraction_after_price_flush"]["down_flush"]["liquidation_observed"] is False


def test_funding_state_at_event():
    from research.external_signal_shadow.stage1_4b_lite_signals import funding_state_at_event
    rows = [
        {"symbol": "BTCUSDT", "fundingTime": 1000, "fundingRate": 0.0001},
        {"symbol": "BTCUSDT", "fundingTime": 2000, "fundingRate": 0.0002},
        {"symbol": "BTCUSDT", "fundingTime": 3000, "fundingRate": 0.0003},
    ]
    # event_available_at_ms = 2500, lag = 500
    # eligible <= 2500 - 500 = 2000
    # latest eligible is 2000
    res = funding_state_at_event(rows, 2500, 500)
    assert res is not None
    assert res["fundingTime"] == 2000
    assert res["fundingRate"] == 0.0002


def test_funding_percentile_at_event():
    from research.external_signal_shadow.stage1_4b_lite_signals import funding_percentile_at_event
    # 29 points -> insufficient history
    rows = [{"symbol": "BTCUSDT", "fundingTime": i * 1000, "fundingRate": 0.0001} for i in range(29)]
    res = funding_percentile_at_event(rows, 50000, 500)
    assert res is None

    # 30 points
    # let's set rates to 1, 2, ..., 30.
    # The last one at time 29000 has rate 30.
    # Available at 31000, lag 1000 -> target <= 30000. So all 30 points are eligible.
    # Sorted: 1, 2, ..., 30. The last eligible rate is 30.
    # Percentile of 30 in [1..30]: (count <= 30) / 30 * 100 = 100.0
    rows_30 = [{"symbol": "BTCUSDT", "fundingTime": i * 1000, "fundingRate": float(i + 1)} for i in range(30)]
    res_30 = funding_percentile_at_event(rows_30, 31000, 1000)
    assert res_30 == 100.0


def test_oi_state_at_or_before():
    from research.external_signal_shadow.stage1_4b_lite_signals import oi_state_at_or_before
    rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": 1000, "sumOpenInterest": 100.0},
        {"symbol": "BTCUSDT", "timestamp_ms": 2000, "sumOpenInterest": 200.0},
    ]
    # exact match
    res1 = oi_state_at_or_before(rows, 2000, max_staleness_ms=5000)
    assert res1 is not None
    assert res1["timestamp_ms"] == 2000

    # closest before
    res2 = oi_state_at_or_before(rows, 2500, max_staleness_ms=5000)
    assert res2 is not None
    assert res2["timestamp_ms"] == 2000

    # stale
    res3 = oi_state_at_or_before(rows, 8000, max_staleness_ms=5000)
    assert res3 is None


def test_price_bar_at_or_after_event():
    from research.external_signal_shadow.stage1_4b_lite_signals import price_bar_at_or_after_event
    bars = [
        {"symbol": "BTCUSDT", "bar_start_ms": 1000, "open_price": 49900.0, "close_price": 50000.0, "quote_volume": 10.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 2000, "open_price": 50000.0, "close_price": 50100.0, "quote_volume": 10.0},
        {"symbol": "BTCUSDT", "bar_start_ms": 3000, "open_price": 50100.0, "close_price": 50200.0, "quote_volume": 10.0},
    ]
    # available at 1500, entry_delay = 1
    # first at/after 1500 is 2000 and should be selected
    res = price_bar_at_or_after_event(bars, 1500, entry_delay_bars=1)
    assert res is not None
    assert res["bar_start_ms"] == 2000


def test_compute_price_4h_return_pct_uses_window_open_and_current_close():
    from research.external_signal_shadow.stage1_4b_lite_signals import compute_price_4h_return_pct
    bars = []
    for i in range(16):
        bars.append({
            "symbol": "BTCUSDT",
            "bar_start_ms": i * 900000,
            "open_price": 100.0 if i == 0 else 105.0,
            "close_price": 106.0 if i < 15 else 110.0,
            "quote_volume": 10.0,
        })

    result = compute_price_4h_return_pct(bars, end_index=15)
    assert round(result, 6) == 0.10


def test_detect_candidate_events_all():
    from research.external_signal_shadow.stage1_4b_lite_signals import detect_candidate_events
    # We will build a 25-bar series of 15m data to test detection after 30 funding rate points
    base_time = 864000000

    # 1. Price bars
    price_bars = []
    for i in range(25):
        t = base_time + i * 900000
        c = 102.0 if i >= 17 else 100.0
        price_bars.append({
            "symbol": "BTCUSDT",
            "bar_start_ms": t,
            "open_price": 100.0,
            "close_price": c,
            "quote_volume": 10000.0,
        })

    # 2. OI rows
    oi_rows = []
    for i in range(25):
        t = base_time + i * 900000 + 900000
        oi = 102.0 if t >= 880200000 else 100.0
        oi_rows.append({
            "symbol": "BTCUSDT",
            "timestamp_ms": t,
            "sumOpenInterest": oi,
        })

    # 3. Funding rows
    funding_rows = []
    for i in range(31):
        t = i * 8 * 3600 * 1000
        if i < 15:
            rate = 0.0001
        elif i == 30:
            rate = 0.0002
        else:
            rate = 0.0003
        funding_rows.append({
            "symbol": "BTCUSDT",
            "fundingTime": t,
            "fundingRate": rate
        })

    # Run detector
    events = detect_candidate_events(
        symbol="BTCUSDT",
        funding_rows=funding_rows,
        oi_rows=oi_rows,
        price_bars=price_bars,
    )

    # Should detect oi_expansion_trend_confirmation long event
    assert len(events) > 0
    expansion_events = [e for e in events if e.candidate_name == "oi_expansion_trend_confirmation"]
    assert len(expansion_events) == 1
    assert expansion_events[0].signed_direction == 1
    assert expansion_events[0].event_time_ms == base_time + 17 * 900000



def test_detect_candidate_events_cooldown():
    from research.external_signal_shadow.stage1_4b_lite_signals import detect_candidate_events
    # Test that cooldown prevents repeating events of same symbol + candidate + direction within 4h
    price_bars = []
    for i in range(30):
        t = i * 900000
        # price flush: -2.1% at index 17 and index 19 (which is within 4h cooldown)
        # index 17 vs index 1: 97.9 vs 100 (-2.1%)
        # index 19 vs index 3: 97.9 vs 100 (-2.1%)
        c = 97.9 if i >= 17 else 100.0
        price_bars.append({
            "symbol": "BTCUSDT",
            "bar_start_ms": t,
            "open_price": 100.0,
            "close_price": c,
            "quote_volume": 10000.0,
        })

    oi_rows = []
    for i in range(30):
        t = i * 900000 + 900000
        # contraction of -2.5% at T17 close (16200000) and T19 close (18000000)
        oi = 97.5 if t >= 16200000 else 100.0
        oi_rows.append({
            "symbol": "BTCUSDT",
            "timestamp_ms": t,
            "sumOpenInterest": oi,
        })

    funding_rows = [
        {"symbol": "BTCUSDT", "fundingTime": i * 8 * 3600 * 1000, "fundingRate": 0.0001}
        for i in range(35)
    ]

    events = detect_candidate_events(
        symbol="BTCUSDT",
        funding_rows=funding_rows,
        oi_rows=oi_rows,
        price_bars=price_bars,
    )

    # There are price flushes at index 17, 18, 19...
    # But cooldown of 4h (16 bars of 15m) should deduplicate them, leaving only the first one!
    flush_events = [e for e in events if e.candidate_name == "oi_contraction_after_price_flush"]
    assert len(flush_events) == 1
    assert flush_events[0].event_time_ms == 17 * 900000
