from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable

import pandas as pd

import configs.base as cfg
from research.cross_sectional_factor_lab.universe import normalize_symbol


@dataclass(frozen=True)
class AltUniverseRegimeResult:
    allow_exposure: bool
    eligible_symbols_count: int
    symbols_with_valid_20d_return: int
    coverage_ratio: float
    universe_return_20d: float | None
    included_btc_eth: bool


def _symbol_close_on(panel: pd.DataFrame, symbol: str, dt: pd.Timestamp) -> float | None:
    normalized = normalize_symbol(symbol)
    rows = panel[(panel["symbol"] == normalized) & (panel["date_utc"] == dt)]
    if rows.empty:
        return None
    close = float(rows["close"].iloc[0])
    return close if close > 0 else None


def compute_btc_ma20_regime(panel: pd.DataFrame, rebalance_date: pd.Timestamp) -> bool:
    signal_asof_date = rebalance_date - timedelta(days=1)
    ma_start = rebalance_date - timedelta(days=cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS)
    btc = panel[panel["symbol"] == "BTCUSDT"]
    window = btc[(btc["date_utc"] >= ma_start) & (btc["date_utc"] <= signal_asof_date)]
    if window["date_utc"].nunique() < cfg.FACTOR_LAB_STAGEA2_BTC_MA_DAYS:
        return False
    asof_close = _symbol_close_on(panel, "BTCUSDT", signal_asof_date)
    if asof_close is None:
        return False
    return asof_close > float(window["close"].mean())


def compute_alt_universe_20d_return_regime(
    panel: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    eligible_symbols: Iterable[str],
) -> AltUniverseRegimeResult:
    normalized_symbols = tuple(normalize_symbol(symbol) for symbol in eligible_symbols)
    eligible_count = len(normalized_symbols)
    included_btc_eth = "BTCUSDT" in normalized_symbols or "ETHUSDT" in normalized_symbols
    if eligible_count == 0:
        return AltUniverseRegimeResult(False, 0, 0, 0.0, None, included_btc_eth)

    signal_asof_date = rebalance_date - timedelta(days=1)
    lookback_start_date = rebalance_date - timedelta(days=cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_RETURN_DAYS + 1)
    returns: list[float] = []
    for symbol in normalized_symbols:
        start_close = _symbol_close_on(panel, symbol, lookback_start_date)
        asof_close = _symbol_close_on(panel, symbol, signal_asof_date)
        if start_close is None or asof_close is None:
            continue
        returns.append((asof_close / start_close) - 1.0)

    valid_count = len(returns)
    coverage_ratio = valid_count / eligible_count if eligible_count else 0.0
    universe_return = float(sum(returns) / valid_count) if valid_count else None
    coverage_ok = coverage_ratio >= cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_COVERAGE_RATIO
    count_ok = valid_count >= cfg.FACTOR_LAB_STAGEA2_ALT_UNIVERSE_MIN_SYMBOLS
    allow = bool(coverage_ok and count_ok and universe_return is not None and universe_return > 0.0)
    return AltUniverseRegimeResult(allow, eligible_count, valid_count, coverage_ratio, universe_return, included_btc_eth)


def decide_stageA2_regime_exposure(
    variant: str,
    panel: pd.DataFrame,
    rebalance_date: pd.Timestamp,
    eligible_symbols: Iterable[str],
) -> tuple[bool, AltUniverseRegimeResult | None]:
    if variant == "regime_none":
        return True, None
    if variant == "btc_ma20_cash":
        return compute_btc_ma20_regime(panel, rebalance_date), None
    if variant == "alt_universe_20d_return_cash":
        result = compute_alt_universe_20d_return_regime(panel, rebalance_date, eligible_symbols)
        return result.allow_exposure, result
    raise ValueError(f"unsupported Stage A2 variant: {variant}")
