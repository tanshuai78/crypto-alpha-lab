import pytest

from scripts.run_trend_regime_watchlist import (
    apply_liquidation_notional_from_cache,
    build_snapshot,
    estimate_liquidation_notional_usdt,
    load_rows_tail_from_jsonl,
    run_trend_regime_poll_once,
    select_latest_rows_per_symbol,
)
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


@pytest.mark.asyncio
async def test_run_poll_once_uses_liquidation_cache_for_missing_notional():
    strategy = TrendRegimeObservationStrategy()
    rows = [
        {
            "timestamp_ms": 1710000000000,
            "exchange": "binance",
            "symbol": "DOGE/USDT",
            "close_price": 0.1,
            "return_1h_pct": 3.0,
            "vol_1h_pct": 4.0,
            "vol_baseline_30d_pct": 1.0,
            "open_interest": 100000000.0,
            "oi_change_1h_pct": -3.0,
            "liquidation_notional_1h_usdt": None,
            "volume_24h_usdt": 1000000000.0,
            "estimated_spread_bps": 4.0,
            "estimated_slippage_bps": 6.0,
            "funding_state": "neutral",
            "data_age_sec": 5.0,
        },
    ]

    result = await run_trend_regime_poll_once(
        rows=rows,
        strategy=strategy,
        liquidation_notional_by_symbol={"DOGEUSDT": 4_000_000.0},
    )

    assert len(result["signals"]) == 1
    assert result["signals"][0].metadata["regime"] == "liquidation_cascade_long"


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


def test_apply_liquidation_notional_from_cache_fills_missing_value():
    row = {
        "symbol": "DOGE/USDT",
        "liquidation_notional_1h_usdt": None,
    }

    filled = apply_liquidation_notional_from_cache(
        row,
        {"DOGEUSDT": 3_500_000.0},
    )

    assert filled["liquidation_notional_1h_usdt"] == 3_500_000.0


def test_estimate_liquidation_notional_usdt_sums_force_orders():
    payload = [
        {"executedQty": "2", "averagePrice": "100"},
        {"executedQty": "1.5", "avragePrice": "120"},
        {"origQty": "3", "price": "10"},
    ]

    notional = estimate_liquidation_notional_usdt(payload)

    assert notional == 410.0


def test_select_latest_rows_per_symbol_dedups_history():
    rows = [
        {"symbol": "BTC/USDT", "timestamp_ms": 1000, "value": "old"},
        {"symbol": "ETH/USDT", "timestamp_ms": 1000, "value": "old"},
        {"symbol": "BTC/USDT", "timestamp_ms": 2000, "value": "new"},
        {"symbol": "ETH/USDT", "timestamp_ms": 1500, "value": "new"},
    ]

    latest = select_latest_rows_per_symbol(rows)
    by_symbol = {item["symbol"]: item for item in latest}

    assert set(by_symbol) == {"BTC/USDT", "ETH/USDT"}
    assert by_symbol["BTC/USDT"]["value"] == "new"
    assert by_symbol["ETH/USDT"]["value"] == "new"


def test_load_rows_tail_from_jsonl_reads_tail_only(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text(
        "\n".join(
            [
                '{"symbol":"BTC/USDT","timestamp_ms":1}',
                '{"symbol":"ETH/USDT","timestamp_ms":2}',
                '{"symbol":"DOGE/USDT","timestamp_ms":3}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_rows_tail_from_jsonl(str(path), tail_lines=2)

    assert len(rows) == 2
    assert rows[0]["symbol"] == "ETH/USDT"
    assert rows[1]["symbol"] == "DOGE/USDT"
