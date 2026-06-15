"""
tests/research/external_signal_shadow/test_stage1_4a_orchestrator.py
"""

from research.external_signal_shadow.stage1_4a_orchestrator import run_stage1_4a_feasibility_audit


def _generate_perfect_rows(syms, funding_days=180, oi_days=180, price_days=180):
    funding_interval = 8 * 60 * 60 * 1000
    oi_interval = 60 * 60 * 1000
    price_interval = 15 * 60 * 1000

    funding_rows = {}
    oi_rows = {}
    liq_rows = {}
    price_rows = {}

    for sym in syms:
        # Funding rate rows
        funding_rows[sym] = [
            {"symbol": sym, "fundingRate": "0.0001", "fundingTime": i * funding_interval}
            for i in range(funding_days * 3)
        ]
        # OI rows
        oi_rows[sym] = [
            {"symbol": sym, "sumOpenInterest": "100.0", "sumOpenInterestValue": "1000.0", "timestamp": i * oi_interval}
            for i in range(oi_days * 24)
        ]
        # Liquidation rows (exact forceOrder archive rows for simplicity)
        liq_rows[sym] = [
            {"symbol": sym, "side": "SELL", "price": 50000.0, "origQty": 1.0, "time": i * 12 * oi_interval}
            for i in range(funding_days * 2)
        ]
        # Price rows
        price_rows[sym] = [
            {"symbol": sym, "close_price": 50000.0, "bar_start_ms": i * price_interval}
            for i in range(price_days * 96)
        ]

    return funding_rows, oi_rows, liq_rows, price_rows


def test_orchestrator_uses_price_history_days_not_stub():
    # 180 days price history
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    funding, oi, liq, price = _generate_perfect_rows(syms, funding_days=180, oi_days=180, price_days=180)

    preview_counts = {"composite_overlap_window_count": 100, "composite_overlap_event_days": 30}
    global_metadata = {"fixture_run": False, "live_trading_allowed": False, "liquidation_source_type": "force_order_archive"}

    res = run_stage1_4a_feasibility_audit(
        symbol_funding_rows=funding,
        symbol_oi_rows=oi,
        symbol_liquidation_rows=liq,
        symbol_price_rows=price,
        preview_counts=preview_counts,
        global_metadata=global_metadata,
        liquidation_proxy_accepted_for_full_replay=True,
    )

    assert res["outcome"] == "stage1_4_data_feasible"
    btc_price_audit = res["symbol_audits"]["BTCUSDT"]["price"]
    # Check that price_history_days is computed and around 180 days
    assert 179.0 < btc_price_audit["price_history_days"] < 180.0


def test_orchestrator_marks_preview_not_alpha_and_no_replay():
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    # 80 days OI history (below 90) -> will be degraded
    funding, oi, liq, price = _generate_perfect_rows(syms, funding_days=180, oi_days=80, price_days=180)

    preview_counts = {"composite_overlap_window_count": 100, "composite_overlap_event_days": 30}
    global_metadata = {"fixture_run": False, "live_trading_allowed": False, "liquidation_source_type": "force_order_archive"}

    res = run_stage1_4a_feasibility_audit(
        symbol_funding_rows=funding,
        symbol_oi_rows=oi,
        symbol_liquidation_rows=liq,
        symbol_price_rows=price,
        preview_counts=preview_counts,
        global_metadata=global_metadata,
        liquidation_proxy_accepted_for_full_replay=True,
    )

    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["stage1_4b_candidate_replay_allowed"] is False
    assert res["composite_replay_allowed"] is False


def test_orchestrator_degraded_when_oi_blocks_full_composite():
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    funding, oi, liq, price = _generate_perfect_rows(syms, funding_days=180, oi_days=180, price_days=180)
    # Make OI time coverage poor for one symbol (drop a middle chunk of OI)
    oi_interval = 60 * 60 * 1000
    for idx in range(100, 1000):
        # Remove matching rows
        ts = idx * oi_interval
        oi["BTCUSDT"] = [r for r in oi["BTCUSDT"] if r["timestamp"] != ts]

    preview_counts = {"composite_overlap_window_count": 100, "composite_overlap_event_days": 30}
    global_metadata = {"fixture_run": False, "live_trading_allowed": False, "liquidation_source_type": "force_order_archive"}

    res = run_stage1_4a_feasibility_audit(
        symbol_funding_rows=funding,
        symbol_oi_rows=oi,
        symbol_liquidation_rows=liq,
        symbol_price_rows=price,
        preview_counts=preview_counts,
        global_metadata=global_metadata,
        liquidation_proxy_accepted_for_full_replay=True,
    )

    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "oi_time_coverage_insufficient"


def test_orchestrator_degraded_when_preview_density_below_min():
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    funding, oi, liq, price = _generate_perfect_rows(syms, funding_days=180, oi_days=180, price_days=180)

    # Low preview counts
    preview_counts = {"composite_overlap_window_count": 40, "composite_overlap_event_days": 10}
    global_metadata = {"fixture_run": False, "live_trading_allowed": False, "liquidation_source_type": "force_order_archive"}

    res = run_stage1_4a_feasibility_audit(
        symbol_funding_rows=funding,
        symbol_oi_rows=oi,
        symbol_liquidation_rows=liq,
        symbol_price_rows=price,
        preview_counts=preview_counts,
        global_metadata=global_metadata,
        liquidation_proxy_accepted_for_full_replay=True,
    )

    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "insufficient_preview_density"
