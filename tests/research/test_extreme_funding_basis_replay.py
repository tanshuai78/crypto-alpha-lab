from src.research.extreme_funding_basis_replay import (
    HistoricalBasisRow,
    basis_bps_from_prices,
    binance_symbol_from_pair,
    build_historical_basis_row,
    build_binance_basis_kline_urls,
    join_funding_rows_with_basis_prices,
    parse_kline_close,
    select_basis_replay_funding_rows,
)


def test_basis_bps_from_prices_uses_perp_over_spot() -> None:
    assert basis_bps_from_prices(spot_mid_price=100.0, perp_mid_price=101.0) == 100.0


def test_build_historical_basis_row_sets_proxy_lineage() -> None:
    row = build_historical_basis_row(
        symbol="DOGE/USDT",
        funding_time_ms=1000,
        funding_rate=0.008,
        annualized_pct=650.0,
        spot_mid_price=100.0,
        perp_mid_price=100.10,
        selected_price_time_ms=1000,
    )

    assert isinstance(row, HistoricalBasisRow)
    assert row.basis_bps == 10.0
    assert row.spot_price_time_ms == 1000
    assert row.perp_price_time_ms == 1000
    assert row.selected_price_time_ms == 1000
    assert row.price_time_diff_ms == 0
    assert row.basis_source == "spot_close_vs_futures_mark_close"
    assert row.depth_source == "static_min_capacity_proxy"
    assert row.coverage_quality == "historical_basis_proxy_not_depth_aware"


def test_binance_symbol_from_pair_removes_separator() -> None:
    assert binance_symbol_from_pair("DOGE/USDT") == "DOGEUSDT"


def test_build_binance_basis_kline_urls_uses_public_endpoints() -> None:
    urls = build_binance_basis_kline_urls(
        binance_symbol="DOGEUSDT",
        start_time_ms=1000,
        end_time_ms=2000,
    )
    assert urls["spot"].startswith("https://api.binance.com/api/v3/klines?")
    assert urls["futures_mark"].startswith("https://fapi.binance.com/fapi/v1/markPriceKlines?")
    assert "symbol=DOGEUSDT" in urls["spot"]
    assert "symbol=DOGEUSDT" in urls["futures_mark"]


def test_parse_kline_close_returns_close_time_and_price() -> None:
    close_time_ms, close_price = parse_kline_close([1000, "1", "2", "0.5", "1.5", "10", 1999])
    assert close_time_ms == 1999
    assert close_price == 1.5


def test_select_basis_replay_funding_rows_keeps_extreme_and_following_path_rows() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.001, "annualized_pct": 10.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 2, "funding_rate": 0.010, "annualized_pct": 1095.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.004, "annualized_pct": 438.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 4, "funding_rate": 0.0001, "annualized_pct": 10.95},
    ]
    selected = select_basis_replay_funding_rows(
        rows,
        threshold_pct=100.0,
        max_following_intervals=2,
    )
    assert [row["funding_time_ms"] for row in selected] == [2, 3, 4]


def test_select_basis_replay_funding_rows_does_not_cross_symbols() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.002, "annualized_pct": 200.0},
        {"symbol": "XRP/USDT", "funding_time_ms": 2, "funding_rate": 0.0001, "annualized_pct": 10.0},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.0005, "annualized_pct": 50.0},
    ]
    selected = select_basis_replay_funding_rows(
        rows,
        threshold_pct=100.0,
        max_following_intervals=1,
    )
    assert [row["symbol"] for row in selected] == ["DOGE/USDT", "DOGE/USDT"]
    assert [row["funding_time_ms"] for row in selected] == [1, 3]


def test_join_funding_rows_with_basis_prices_builds_rows_within_tolerance() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]
    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={10_000: 100.0},
        perp_prices={10_000: 101.0},
        tolerance_ms=120_000,
    )
    assert result["status"] == "ok"
    assert len(result["rows"]) == 1
    assert result["rows"][0].basis_bps == 100.0
    assert result["missing_basis_count"] == 0


def test_join_funding_rows_with_basis_prices_marks_missing_when_prices_absent() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]
    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={},
        perp_prices={},
        tolerance_ms=120_000,
    )
    assert result["status"] == "insufficient_basis_data"
    assert result["rows"] == []
    assert result["missing_basis_count"] == 1


def test_join_uses_latest_price_at_or_before_funding_time_not_future_price() -> None:
    funding_rows = [
        {
            "symbol": "DOGE/USDT",
            "funding_time_ms": 10_000,
            "funding_rate": 0.008,
            "annualized_pct": 650.0,
        }
    ]
    result = join_funding_rows_with_basis_prices(
        funding_rows,
        spot_prices={9_999: 100.0, 10_001: 200.0},
        perp_prices={9_999: 101.0, 10_001: 202.0},
        tolerance_ms=120_000,
    )
    assert result["rows"][0].spot_mid_price == 100.0
    assert result["rows"][0].perp_mid_price == 101.0
