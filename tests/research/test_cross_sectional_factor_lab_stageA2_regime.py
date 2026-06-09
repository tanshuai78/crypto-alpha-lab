from datetime import date, timedelta

import pandas as pd

from research.cross_sectional_factor_lab.regime import (
    compute_alt_universe_20d_return_regime,
    compute_btc_ma20_regime,
    decide_stageA2_regime_exposure,
)


def _daily_row(symbol: str, dt: date, close: float) -> dict:
    return {
        "symbol": symbol,
        "date_utc": pd.Timestamp(dt),
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "base_volume": 1_000_000.0,
        "quote_volume": 50_000_000.0,
    }


def _alt_rows(symbols: list[str], start: date, days: int, start_close: float, end_close: float) -> list[dict]:
    rows = []
    for i in range(days):
        dt = start + timedelta(days=i)
        close = start_close
        if dt == date(2026, 1, 30):
            close = end_close
        for symbol in symbols:
            rows.append(_daily_row(symbol, dt, close))
    return rows


def test_btc_ma20_uses_t_minus_1_and_excludes_rebalance_day_close():
    start = date(2026, 1, 1)
    rows = []
    for i in range(31):
        dt = start + timedelta(days=i)
        close = 100.0
        if dt == date(2026, 1, 30):
            close = 150.0  # t-1, should make regime true
        if dt == date(2026, 1, 31):
            close = 1.0  # rebalance day, must be ignored
        rows.append(_daily_row("BTCUSDT", dt, close))
    panel = pd.DataFrame(rows)

    assert compute_btc_ma20_regime(panel, pd.Timestamp("2026-01-31")) is True


def test_btc_ma20_returns_false_when_required_history_missing():
    panel = pd.DataFrame([_daily_row("BTCUSDT", date(2026, 1, 30), 150.0)])

    assert compute_btc_ma20_regime(panel, pd.Timestamp("2026-01-31")) is False


def test_alt_universe_20d_return_returns_true_with_valid_positive_coverage():
    symbols = [f"ALT{i:02d}USDT" for i in range(10)]
    panel = pd.DataFrame(_alt_rows(symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=symbols,
    )

    assert result.allow_exposure is True
    assert result.eligible_symbols_count == 10
    assert result.symbols_with_valid_20d_return == 10
    assert result.coverage_ratio == 1.0


def test_alt_universe_regime_returns_false_when_coverage_below_min():
    valid_symbols = [f"ALT{i:02d}USDT" for i in range(7)]
    all_symbols = valid_symbols + ["MISS1USDT", "MISS2USDT", "MISS3USDT"]
    panel = pd.DataFrame(_alt_rows(valid_symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=all_symbols,
    )

    assert result.allow_exposure is False
    assert result.symbols_with_valid_20d_return == 7
    assert result.coverage_ratio == 0.7


def test_alt_universe_regime_requires_min_valid_symbol_count():
    symbols = [f"ALT{i:02d}USDT" for i in range(9)]
    panel = pd.DataFrame(_alt_rows(symbols, date(2026, 1, 10), 22, 100.0, 120.0))

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=symbols,
    )

    assert result.allow_exposure is False
    assert result.symbols_with_valid_20d_return == 9


def test_alt_universe_20d_return_ignores_rebalance_day_pump():
    rows = []
    for i in range(22):
        dt = date(2026, 1, 10) + timedelta(days=i)
        close = 100.0
        if dt == date(2026, 1, 30):
            close = 90.0
        if dt == date(2026, 1, 31):
            close = 999.0
        for symbol in [f"ALT{j:02d}USDT" for j in range(10)]:
            rows.append(_daily_row(symbol, dt, close))
    panel = pd.DataFrame(rows)

    result = compute_alt_universe_20d_return_regime(
        panel,
        pd.Timestamp("2026-01-31"),
        eligible_symbols=[f"ALT{j:02d}USDT" for j in range(10)],
    )

    assert result.allow_exposure is False


def test_decide_stageA2_regime_exposure_rejects_unknown_variant():
    panel = pd.DataFrame([_daily_row("BTCUSDT", date(2026, 1, 1), 100.0)])

    try:
        decide_stageA2_regime_exposure(
            "volume_filter",
            panel,
            pd.Timestamp("2026-01-31"),
            eligible_symbols=("AAAUSDT",),
        )
    except ValueError as exc:
        assert "unsupported Stage A2 variant" in str(exc)
    else:
        raise AssertionError("unknown variant should raise ValueError")
