import pytest

from configs.base import (
    TREND_REGIME_OBSERVATION_COST_BPS,
    TREND_REGIME_STRESS_COST_BPS,
)
from scripts.replay_trend_regime_shadow import (
    build_dual_cost_summary,
    build_shadow_summary,
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
        _row(
            timestamp_ms=1000,
            data_age_sec=999999.0,
            close_price=100000.0,
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
        _row(
            timestamp_ms=2000,
            data_age_sec=999999.0,
            close_price=101000.0,
            return_1h_pct=2.4,
            vol_1h_pct=2.8,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=2.0,
            volume_24h_usdt=30_000_000_000.0,
            estimated_slippage_bps=2.0,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["historical_mode"] is True
    assert summary["historical_freshness_normalized_count"] == 2
    assert summary["rows_originally_api_stale_count"] == 2
    assert summary["entry_event_count"] == 1


def test_historical_replay_outputs_classification_reject_counts():
    rows = [
        _row(timestamp_ms=1000, vol_1h_pct=1.0, vol_baseline_30d_pct=1.0),
        _row(timestamp_ms=2000, return_1h_pct=0.5),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert "classification_reject_counts" in summary
    assert "vol_breakout_below_threshold" in summary["classification_reject_counts"]
    assert "reject_counts_by_symbol" in summary
    assert "BTC/USDT" in summary["reject_counts_by_symbol"]


def test_historical_replay_reports_liquidation_coverage_gap():
    rows = [
        _row(timestamp_ms=1000, liquidation_notional_1h_usdt=None),
        _row(timestamp_ms=2000, liquidation_notional_1h_usdt=4_000_000.0),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["rows_missing_liquidation_notional_count"] == 1
    assert summary["rows_with_liquidation_notional_count"] == 1
    assert summary["liquidation_coverage_ratio"] == 0.5


def test_historical_replay_outputs_symbol_and_regime_breakdown_fields():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT"),
        _row(
            timestamp_ms=2000,
            symbol="BTC/USDT",
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
        _row(
            timestamp_ms=3000,
            symbol="DOGE/USDT",
            return_1h_pct=-3.0,
            vol_1h_pct=4.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=-3.0,
            liquidation_notional_1h_usdt=4_000_000.0,
        ),
        _row(
            timestamp_ms=4000,
            symbol="DOGE/USDT",
            return_1h_pct=0.1,
            vol_1h_pct=1.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=0.1,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["input_row_count"] == 4
    assert summary["symbol_count"] == 2
    assert summary["symbols"] == ["BTC/USDT", "DOGE/USDT"]
    assert summary["time_span_hours"] > 0
    assert "vol_breakout_long" in summary["entry_event_count_by_regime"]
    assert "liquidation_cascade_short" in summary["entry_event_count_by_regime"]


def test_historical_replay_splits_missing_symbol_from_non_watchlist_rows():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT"),
        _row(timestamp_ms=2000, symbol="ADA/USDT"),
        _row(timestamp_ms=3000, symbol=""),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["missing_symbol_row_count"] == 1
    assert summary["non_watchlist_row_count"] == 1
    assert summary["non_watchlist_symbols"] == ["ADA/USDT"]


def test_apply_hourly_liquidation_history_joins_by_hour_bucket():
    """apply_hourly_liquidation_history must join by (symbol, hour_bucket_utc)."""
    from scripts.replay_trend_regime_shadow import apply_hourly_liquidation_history

    rows = [
        _row(timestamp_ms=1716804000000, symbol="BTC/USDT"),  # 2024-05-27 10:00 UTC
        _row(timestamp_ms=1716807600000, symbol="BTC/USDT"),  # 2024-05-27 11:00 UTC
    ]
    hourly = [
        {
            "symbol": "BTC/USDT",
            "hour_bucket_utc": "2024-05-27T10:00",
            "total_liquidation_notional_usdt": 5_000_000.0,
        },
    ]
    result = apply_hourly_liquidation_history(rows, hourly)
    assert result[0]["liquidation_notional_1h_usdt"] == pytest.approx(5_000_000.0)
    assert result[1]["liquidation_notional_1h_usdt"] is None  # no match for hour 11


def test_build_shadow_summary_reports_liquidation_coverage_ratio():
    """build_shadow_summary must include liquidation_coverage_ratio in summary."""
    rows = [
        _row(timestamp_ms=1000, liquidation_notional_1h_usdt=5_000_000.0),
        _row(timestamp_ms=2000, liquidation_notional_1h_usdt=None),
        _row(timestamp_ms=3000, liquidation_notional_1h_usdt=3_000_000.0),
    ]
    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)
    assert "liquidation_coverage_ratio" in summary
    assert summary["liquidation_coverage_ratio"] == pytest.approx(2 / 3)


def test_load_optional_jsonl_returns_empty_when_file_missing():
    """load_optional_jsonl must return [] when path does not exist."""
    from scripts.replay_trend_regime_shadow import load_optional_jsonl

    result = load_optional_jsonl("/tmp/nonexistent_file_xyz_123.jsonl")
    assert result == []
