from scripts.replay_trend_regime_shadow import (
    build_dual_cost_summary,
    build_shadow_summary,
)
from configs.base import (
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STRESS_COST_BPS,
)


def _row(**overrides):
    row = {
        "timestamp_ms": 1710000000000,
        "exchange": "binance",
        "symbol": "BTC/USDT",
        "close_price": 100000.0,
        "return_1h_pct": 2.5,
        "vol_1h_pct": 3.0,
        "vol_baseline_30d_pct": 1.0,
        "open_interest": 100000000.0,
        "oi_change_1h_pct": 3.0,
        "liquidation_notional_1h_usdt": 0.0,
        "volume_24h_usdt": 1000000000.0,
        "estimated_spread_bps": 4.0,
        "estimated_slippage_bps": 6.0,
        "funding_state": "neutral",
        "data_age_sec": 5.0,
    }
    row.update(overrides)
    return row


def test_replay_discovers_entry_from_raw_rows():
    rows = [
        _row(timestamp_ms=1000, close_price=100000.0),
        _row(
            timestamp_ms=2000,
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["entry_event_count"] == 1
    assert summary["shadow_trade_count"] == 1
    assert summary["results"][0]["entry_price"] == 100000.0


def test_replay_does_not_cross_symbols():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(
            timestamp_ms=2000,
            symbol="ETH/USDT",
            close_price=100.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
        _row(
            timestamp_ms=3000,
            symbol="BTC/USDT",
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["shadow_trade_count"] == 1
    assert summary["results"][0]["exit_price"] == 101000.0


def test_replay_uses_only_future_rows():
    rows = [
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=100000.0),
        _row(
            timestamp_ms=1500,
            symbol="BTC/USDT",
            close_price=90000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
        _row(
            timestamp_ms=2500,
            symbol="BTC/USDT",
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["shadow_trade_count"] == 1
    assert summary["results"][0]["exit_price"] == 101000.0


def test_replay_outputs_grouped_summary_by_regime_direction_and_tier():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(
            timestamp_ms=2000,
            symbol="BTC/USDT",
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
        _row(
            timestamp_ms=3000,
            symbol="DOGE/USDT",
            close_price=0.1,
            return_1h_pct=-3.0,
            vol_1h_pct=4.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=-3.0,
            liquidation_notional_1h_usdt=4_000_000.0,
        ),
        _row(
            timestamp_ms=4000,
            symbol="DOGE/USDT",
            close_price=0.095,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    groups = summary["grouped_summary"]
    assert "vol_breakout_long|long|major" in groups
    assert "liquidation_cascade_short|short|large_alt" in groups


def test_replay_outputs_base_and_stress_cost_summaries():
    rows = [
        _row(timestamp_ms=1000, close_price=100000.0),
        _row(
            timestamp_ms=2000,
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    dual = build_dual_cost_summary(rows)

    assert dual["base_cost_bps"] == TREND_REGIME_OBSERVATION_COST_BPS
    assert dual["stress_cost_bps"] == TREND_REGIME_STRESS_COST_BPS
    assert dual["base"]["shadow_trade_count"] == 1
    assert dual["stress"]["shadow_trade_count"] == 1


def test_historical_replay_normalizes_stale_rows_before_classification():
    rows = [
        _row(timestamp_ms=1000, data_age_sec=999999.0, close_price=100000.0),
        _row(
            timestamp_ms=2000,
            data_age_sec=999999.0,
            close_price=101000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["historical_mode"] is True
    assert summary["stale_rows_normalized_count"] == 2
    assert summary["entry_event_count"] == 1


def test_historical_replay_outputs_classification_reject_counts():
    rows = [
        _row(timestamp_ms=1000, vol_1h_pct=1.0, vol_baseline_30d_pct=1.0),
        _row(timestamp_ms=2000, return_1h_pct=0.5),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert "classification_reject_counts" in summary
    assert "vol_breakout_below_threshold" in summary["classification_reject_counts"]


def test_historical_replay_reports_liquidation_coverage_gap():
    rows = [
        _row(timestamp_ms=1000, liquidation_notional_1h_usdt=None),
        _row(timestamp_ms=2000, liquidation_notional_1h_usdt=4_000_000.0),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["rows_missing_liquidation_notional_count"] == 1
    assert summary["rows_with_liquidation_notional_count"] == 1
