import pytest

from scripts.run_trend_regime_watchlist import build_snapshot, run_trend_regime_poll_once
from src.strategies.base import SignalCandidate
from src.strategies.trend_regime.scanner import TrendRegimeObservationStrategy


@pytest.mark.asyncio
async def test_run_poll_once_returns_signals_and_rejects():
    strategy = TrendRegimeObservationStrategy()
    rows = [
        {
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
            "apiKey": "must_not_leak",
        },
        {
            "timestamp_ms": 1710000000000,
            "exchange": "binance",
            "symbol": "PEPE/USDT",
            "close_price": 1.0,
            "return_1h_pct": 10.0,
            "vol_1h_pct": 10.0,
            "vol_baseline_30d_pct": 1.0,
            "open_interest": 1000000.0,
            "oi_change_1h_pct": 10.0,
            "liquidation_notional_1h_usdt": 10000000.0,
            "volume_24h_usdt": 1000000000.0,
            "estimated_spread_bps": 4.0,
            "estimated_slippage_bps": 2.0,
            "funding_state": "neutral",
            "data_age_sec": 5.0,
        },
    ]

    result = await run_trend_regime_poll_once(rows=rows, strategy=strategy)

    assert len(result["signals"]) == 1
    assert isinstance(result["signals"][0], SignalCandidate)
    assert result["reject_reasons"] == ["symbol_not_in_watchlist"]
    assert len(result["snapshots"]) == 2


def test_build_snapshot_whitelists_public_fields_only():
    raw = {
        "symbol": "BTC/USDT",
        "exchange": "binance",
        "timestamp_ms": 1710000000000,
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
        "secret": "drop",
    }

    snapshot = build_snapshot(raw)

    assert snapshot["symbol"] == "BTC/USDT"
    assert "secret" not in snapshot
