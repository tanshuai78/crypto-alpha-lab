import json

from scripts.build_trend_regime_market_rows import (
    build_market_rows_from_payloads,
    build_symbol_market_rows,
    write_rows_jsonl,
)


def _kline(ts_close: int, close: float, quote_volume: float) -> list:
    return [
        ts_close - 3_600_000,
        "0",
        "0",
        "0",
        str(close),
        "0",
        ts_close,
        str(quote_volume),
        0,
        "0",
        "0",
        "0",
    ]


def _symbol_payload(close_start: float, symbol_key: str):
    klines = []
    base_ts = 1_710_000_000_000
    for idx in range(0, 40):
        close = close_start + idx * 0.5
        ts_close = base_ts + idx * 3_600_000
        klines.append(_kline(ts_close, close, 1_000_000.0 + idx * 1000.0))

    oi_hist = []
    for idx in range(0, 40):
        ts_close = base_ts + idx * 3_600_000
        oi_hist.append(
            {
                "symbol": symbol_key,
                "sumOpenInterest": str(100_000 + idx * 100),
                "timestamp": ts_close,
            }
        )

    premium = {
        "symbol": symbol_key,
        "lastFundingRate": "0.0001",
    }
    book = {
        "symbol": symbol_key,
        "bidPrice": str(close_start),
        "askPrice": str(close_start + 0.1),
    }
    return {
        "klines": klines,
        "oi_hist": oi_hist,
        "premium": premium,
        "book_ticker": book,
    }


def test_build_symbol_market_rows_has_required_fields():
    payload = _symbol_payload(close_start=100.0, symbol_key="BTCUSDT")
    rows = build_symbol_market_rows(
        pair="BTC/USDT",
        symbol_payload=payload,
        now_ms=1_710_000_000_000 + 40 * 3_600_000,
    )

    assert rows
    sample = rows[-1]
    required = {
        "timestamp_ms",
        "exchange",
        "symbol",
        "close_price",
        "return_1h_pct",
        "vol_1h_pct",
        "vol_baseline_30d_pct",
        "open_interest",
        "oi_change_1h_pct",
        "liquidation_notional_1h_usdt",
        "volume_24h_usdt",
        "estimated_spread_bps",
        "estimated_slippage_bps",
        "funding_state",
        "data_age_sec",
    }
    assert required.issubset(sample.keys())


def test_build_market_rows_from_payloads_keeps_symbol_isolation():
    rows = build_market_rows_from_payloads(
        {
            "BTC/USDT": _symbol_payload(close_start=100.0, symbol_key="BTCUSDT"),
            "ETH/USDT": _symbol_payload(close_start=200.0, symbol_key="ETHUSDT"),
        },
        now_ms=1_710_000_000_000 + 40 * 3_600_000,
    )

    symbols = {row["symbol"] for row in rows}
    assert symbols == {"BTC/USDT", "ETH/USDT"}


def test_build_symbol_market_rows_marks_stale_data_age_sec():
    payload = _symbol_payload(close_start=100.0, symbol_key="BTCUSDT")
    rows = build_symbol_market_rows(
        pair="BTC/USDT",
        symbol_payload=payload,
        now_ms=1_710_000_000_000 + 40 * 3_600_000 + 120_000,
    )

    assert rows[-1]["data_age_sec"] >= 120.0


def test_write_rows_jsonl_outputs_stable_sorted_rows(tmp_path):
    rows = [
        {"timestamp_ms": 2, "symbol": "BTC/USDT", "x": 2},
        {"timestamp_ms": 1, "symbol": "ETH/USDT", "x": 1},
    ]
    output = tmp_path / "rows.jsonl"

    write_rows_jsonl(output, rows)

    lines = output.read_text(encoding="utf-8").splitlines()
    decoded = [json.loads(line) for line in lines]
    assert decoded[0]["timestamp_ms"] == 1
    assert decoded[1]["timestamp_ms"] == 2
