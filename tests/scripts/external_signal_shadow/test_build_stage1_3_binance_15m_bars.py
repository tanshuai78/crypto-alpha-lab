from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.external_signal_shadow.build_stage1_3_binance_15m_bars import (
    INTERVAL_15M_MS,
    build_klines_url,
    collect_symbol_bars,
    main,
    parse_spot_kline_row,
)


def _row(open_ms: int, *, quote_volume: str = "12345.67") -> list[object]:
    return [
        open_ms,
        "100.0",
        "110.0",
        "90.0",
        "105.0",
        "12.34",
        open_ms + INTERVAL_15M_MS - 1,
        quote_volume,
        42,
        "6.0",
        "600.0",
        "0",
    ]


def test_build_klines_url_uses_public_spot_endpoint() -> None:
    url = build_klines_url(
        base_url="https://data-api.binance.vision",
        symbol="BTCUSDT",
        start_ms=1_000,
        end_ms=2_000,
        limit=1000,
    )

    assert url.startswith("https://data-api.binance.vision/api/v3/klines?")
    assert "symbol=BTCUSDT" in url
    assert "interval=15m" in url
    assert "startTime=1000" in url
    assert "endTime=2000" in url
    assert "limit=1000" in url
    assert "apiKey" not in url


def test_parse_spot_kline_row_uses_raw_quote_asset_volume() -> None:
    parsed = parse_spot_kline_row("BTCUSDT", _row(10_000, quote_volume="999.123"))

    assert parsed == {
        "symbol": "BTCUSDT",
        "bar_start_ms": 10_000,
        "bar_end_ms": 10_000 + INTERVAL_15M_MS,
        "open_price": 100.0,
        "high_price": 110.0,
        "low_price": 90.0,
        "close_price": 105.0,
        "quote_volume": 999.123,
    }


def test_parse_spot_kline_row_rejects_inconsistent_close_time() -> None:
    bad = _row(10_000)
    bad[6] = 10_000 + INTERVAL_15M_MS

    with pytest.raises(ValueError, match="close time"):
        parse_spot_kline_row("BTCUSDT", bad)


def test_collect_symbol_bars_pages_until_end_without_duplicate_open_times() -> None:
    calls: list[str] = []

    def fetch_json(url: str) -> list[list[object]]:
        calls.append(url)
        if len(calls) == 1:
            return [_row(0), _row(INTERVAL_15M_MS)]
        if len(calls) == 2:
            return [_row(2 * INTERVAL_15M_MS)]
        return []

    bars = collect_symbol_bars(
        symbol="BTCUSDT",
        start_ms=0,
        end_ms=3 * INTERVAL_15M_MS,
        fetch_json=fetch_json,
        base_url="https://data-api.binance.vision",
        limit=2,
        request_sleep_sec=0.0,
    )

    assert [bar["bar_start_ms"] for bar in bars] == [0, INTERVAL_15M_MS, 2 * INTERVAL_15M_MS]
    assert len(calls) == 2


def test_cli_writes_stage1_3_jsonl_from_mock_fetcher(tmp_path: Path) -> None:
    output = tmp_path / "bars.jsonl"
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "BTCUSDT": [_row(0), _row(INTERVAL_15M_MS)],
        "ETHUSDT": [_row(0), _row(INTERVAL_15M_MS)],
    }))

    result = main([
        "--symbols",
        "BTCUSDT,ETHUSDT",
        "--start-ms",
        "0",
        "--end-ms",
        str(2 * INTERVAL_15M_MS),
        "--output",
        str(output),
        "--mock-klines-json",
        str(fixture),
    ])

    assert result == 0
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 4
    assert {row["symbol"] for row in rows} == {"BTCUSDT", "ETHUSDT"}


def test_cli_rejects_network_without_live_public_readonly_flag(tmp_path: Path) -> None:
    output = tmp_path / "bars.jsonl"

    result = main([
        "--symbols",
        "BTCUSDT",
        "--start-ms",
        "0",
        "--end-ms",
        str(INTERVAL_15M_MS),
        "--output",
        str(output),
    ])

    assert result != 0
    assert not output.exists()
