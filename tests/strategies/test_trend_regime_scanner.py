import pytest

from src.strategies.base import SignalCandidate
from src.strategies.trend_regime.scanner import (
    TrendRegimeObservationStrategy,
    TrendRegimeWatchEvent,
    classify_trend_regime_snapshot,
    symbol_tier,
)


def _snapshot(**overrides):
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


def test_symbol_tier_classifies_major_and_large_alt():
    assert symbol_tier("BTC/USDT") == "major"
    assert symbol_tier("SOL/USDT") == "large_alt"
    assert symbol_tier("UNKNOWN/USDT") == "unsupported"


def test_classifies_vol_breakout_long():
    result = classify_trend_regime_snapshot(_snapshot())
    assert result.event is not None
    assert isinstance(result.event, TrendRegimeWatchEvent)
    assert result.event.regime == "vol_breakout_long"
    assert result.event.direction == "long"
    assert result.event.executable is False


def test_classifies_vol_breakout_short_with_stricter_short_metadata():
    result = classify_trend_regime_snapshot(_snapshot(return_1h_pct=-2.5, oi_change_1h_pct=3.0))
    assert result.event is not None
    assert result.event.regime == "vol_breakout_short"
    assert result.event.direction == "short"
    assert result.event.metadata["funding_state"] == "neutral"


def test_classifies_alt_liquidation_cascade_with_alt_threshold():
    result = classify_trend_regime_snapshot(
        _snapshot(
            symbol="DOGE/USDT",
            return_1h_pct=3.0,
            vol_1h_pct=4.0,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=-3.0,
            liquidation_notional_1h_usdt=3_500_000.0,
        )
    )
    assert result.event is not None
    assert result.event.regime == "liquidation_cascade_long"
    assert result.event.direction == "long"
    assert result.event.metadata["symbol_tier"] == "large_alt"


def test_rejects_unsupported_symbol_stale_and_illiquid_rows():
    unsupported = classify_trend_regime_snapshot(_snapshot(symbol="PEPE/USDT"))
    assert unsupported.reject_reason == "symbol_not_in_watchlist"

    stale = classify_trend_regime_snapshot(_snapshot(data_age_sec=120.0))
    assert stale.reject_reason == "api_stale"

    illiquid = classify_trend_regime_snapshot(_snapshot(volume_24h_usdt=100_000_000.0))
    assert illiquid.reject_reason == "volume_below_min"


def test_rejects_when_vol_or_return_is_not_large_enough():
    low_vol = classify_trend_regime_snapshot(_snapshot(vol_1h_pct=2.0, vol_baseline_30d_pct=1.0))
    assert low_vol.reject_reason == "vol_breakout_below_threshold"

    low_return = classify_trend_regime_snapshot(_snapshot(return_1h_pct=1.0))
    assert low_return.reject_reason == "return_below_min"


@pytest.mark.asyncio
async def test_observation_strategy_scan_returns_observation_signal_candidate():
    strategy = TrendRegimeObservationStrategy()
    signals = await strategy.scan(_snapshot())

    assert len(signals) == 1
    signal = signals[0]
    assert isinstance(signal, SignalCandidate)
    assert signal.strategy_type == "trend_regime"
    assert signal.direction == "long"
    assert signal.expected_edge_bps == 0.0
    assert signal.metadata["mode"] == "observation"
    assert signal.metadata["executable"] is False
    assert signal.metadata["edge_status"] == "unknown_until_shadow"
    assert signal.metadata["past_move_bps"] == 250.0


def test_should_exit_on_stop_loss_or_time_limit():
    strategy = TrendRegimeObservationStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=0.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=12.0,
        stop_loss_pct=1.5,
        suggested_notional_usdt=500.0,
        metadata={"entry_price": 100000.0},
    )
    assert strategy.should_exit(signal, {}, 1.0, -1.6) == (True, "stop_loss_hit")
    assert strategy.should_exit(signal, {}, 13.0, 0.1) == (True, "max_holding_time_reached")
    assert strategy.should_exit(signal, {}, 1.0, 0.1) == (False, "hold")


def test_risk_check_blocks_execution_even_for_valid_observation_signal():
    strategy = TrendRegimeObservationStrategy()
    signal = SignalCandidate(
        strategy_type="trend_regime",
        symbol="BTC/USDT",
        direction="long",
        confidence=0.55,
        expected_edge_bps=0.0,
        entry_exchange="binance",
        hedge_exchange="binance",
        trigger_reason="vol_breakout_long",
        invalidation_reason="stop_loss_or_time_limit",
        max_holding_hours=12.0,
        stop_loss_pct=1.5,
        suggested_notional_usdt=500.0,
        metadata={"mode": "observation", "executable": False},
    )
    assert strategy.risk_check(signal) == (False, "observation_only")


def test_live_scanner_still_rejects_stale_rows():
    stale = classify_trend_regime_snapshot(_snapshot(data_age_sec=999999.0))
    assert stale.reject_reason == "api_stale"
