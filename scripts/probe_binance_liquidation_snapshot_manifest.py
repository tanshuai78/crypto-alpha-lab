#!/usr/bin/env python3
"""
scripts/probe_binance_liquidation_snapshot_manifest.py

Probe Binance Vision to confirm real file availability before downloader
execution. Validates:
  - monthly 1m kline ZIPs (um/monthly/klines)
  - monthly liquidationSnapshot ZIPs (um/monthly/liquidationSnapshot)
  - daily liquidationSnapshot ZIPs (um/daily/liquidationSnapshot) as primary fallback

Outputs:
  - reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json

Usage:
    PYTHONPATH=src uv run python scripts/probe_binance_liquidation_snapshot_manifest.py
"""

import json
import os
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg

BINANCE_VISION_BASE = "https://data.binance.vision"

REPORT_PATH = Path("reports/liquidation_shock_event_study/binance_snapshot_manifest_probe.json")


# ---------------------------------------------------------------------------
# URL builders (pure functions — testable without network)
# ---------------------------------------------------------------------------


def _ccxt_to_binance_symbol(symbol: str) -> str:
    """Convert 'BTC/USDT' → 'BTCUSDT'."""
    return symbol.replace("/", "")


def build_kline_monthly_url(binance_symbol: str, month: str) -> str:
    """
    Build the Binance Vision URL for a monthly 1m kline ZIP.

    Example:
        https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip
    """
    fname = f"{binance_symbol}-1m-{month}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/monthly/klines/{binance_symbol}/1m/{fname}"


def build_liquidation_monthly_url(binance_symbol: str, month: str) -> str:
    """
    Build the Binance Vision URL for a monthly liquidationSnapshot ZIP.

    Example:
        https://data.binance.vision/data/futures/um/monthly/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2024-01.zip
    """
    fname = f"{binance_symbol}-liquidationSnapshot-{month}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/monthly/liquidationSnapshot/{binance_symbol}/{fname}"


def build_liquidation_daily_url(binance_symbol: str, date_str: str) -> str:
    """
    Build the Binance Vision URL for a daily liquidationSnapshot ZIP.

    Args:
        date_str: YYYY-MM-DD formatted date string.

    Example:
        https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2024-01-15.zip
    """
    fname = f"{binance_symbol}-liquidationSnapshot-{date_str}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/daily/liquidationSnapshot/{binance_symbol}/{fname}"


# ---------------------------------------------------------------------------
# Network HEAD check (default, replaceable in tests)
# ---------------------------------------------------------------------------


def _http_head_check(url: str) -> bool:
    """Return True if the URL responds with HTTP 200."""
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "Mozilla/5.0 (research-probe/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Month → list-of-dates helpers
# ---------------------------------------------------------------------------


def _month_dates(month: str) -> list[str]:
    """Return all YYYY-MM-DD date strings in a given YYYY-MM month."""
    year, mon = int(month[:4]), int(month[5:7])
    # Determine days in month
    if mon == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, mon + 1, 1)
    first = date(year, mon, 1)
    days = (next_month - first).days
    return [(first + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


# ---------------------------------------------------------------------------
# Core probe logic
# ---------------------------------------------------------------------------


def probe_manifest(
    symbols: list[str],
    months: list[str],
    url_head_fn: Callable[[str], bool] = _http_head_check,
    sleep_between_checks: float = 0.3,
) -> dict:
    """
    Probe Binance Vision for data availability and determine download mode.

    Args:
        symbols: List of Binance symbol strings (e.g. ["BTCUSDT"]).
                 Accepts either raw ("BTCUSDT") or ccxt ("BTC/USDT") format.
        months:  List of YYYY-MM month strings.
        url_head_fn: Callable(url) -> bool. Injected for testing.
        sleep_between_checks: Seconds to sleep between HTTP HEAD requests.

    Returns:
        dict with all required manifest keys and a final `decision`.
    """
    # Normalise symbols to Binance format
    binance_symbols = [_ccxt_to_binance_symbol(s) for s in symbols]

    kline_monthly_available: dict[str, dict[str, bool]] = {}
    liq_monthly_available: dict[str, dict[str, bool]] = {}
    liq_daily_available: dict[str, dict[str, bool]] = {}
    missing_symbol_months: list[dict] = []

    for sym in binance_symbols:
        kline_monthly_available[sym] = {}
        liq_monthly_available[sym] = {}
        liq_daily_available[sym] = {}

        for month in months:
            # 1. Probe monthly kline
            kline_url = build_kline_monthly_url(sym, month)
            kline_ok = url_head_fn(kline_url)
            kline_monthly_available[sym][month] = kline_ok
            if sleep_between_checks:
                time.sleep(sleep_between_checks)

            # 2. Probe monthly liquidation
            liq_monthly_url = build_liquidation_monthly_url(sym, month)
            liq_monthly_ok = url_head_fn(liq_monthly_url)
            liq_monthly_available[sym][month] = liq_monthly_ok
            if sleep_between_checks:
                time.sleep(sleep_between_checks)

            # 3. Probe daily liquidation (check first day of month as sample)
            first_day = _month_dates(month)[0]
            liq_daily_url = build_liquidation_daily_url(sym, first_day)
            liq_daily_ok = url_head_fn(liq_daily_url)
            liq_daily_available[sym][month] = liq_daily_ok
            if sleep_between_checks:
                time.sleep(sleep_between_checks)

            # Track missing combinations
            if not kline_ok:
                missing_symbol_months.append(
                    {"symbol": sym, "month": month, "missing": "kline_monthly"}
                )
            if not liq_monthly_ok and not liq_daily_ok:
                missing_symbol_months.append(
                    {"symbol": sym, "month": month, "missing": "liquidation_all"}
                )

    # Decide download mode for liquidation:
    # Prefer monthly if available for ALL symbol-month pairs; otherwise daily.
    all_monthly_liq_ok = all(
        liq_monthly_available[sym][month]
        for sym in binance_symbols
        for month in months
    )
    any_daily_liq_ok = any(
        liq_daily_available[sym][month]
        for sym in binance_symbols
        for month in months
    )

    if all_monthly_liq_ok:
        selected_mode = "monthly"
    else:
        selected_mode = "daily"

    # Decide overall readiness
    any_kline_ok = any(
        kline_monthly_available[sym][month]
        for sym in binance_symbols
        for month in months
    )
    any_liq_ok = all_monthly_liq_ok or any_daily_liq_ok

    if not any_kline_ok or not any_liq_ok:
        decision = "data_unavailable"
    elif selected_mode == "monthly":
        decision = "proceed_with_monthly_liquidation"
    else:
        decision = "proceed_with_daily_liquidation"

    return {
        "source": "binance_vision",
        "market": "futures_um",
        "symbols": binance_symbols,
        "months": months,
        "kline_monthly_available": kline_monthly_available,
        "liquidation_monthly_available": liq_monthly_available,
        "liquidation_daily_available": liq_daily_available,
        "selected_liquidation_download_mode": selected_mode,
        "missing_symbol_months": missing_symbol_months,
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    import configs.base as cfg

    symbols_raw = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS)
    months = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS)
    binance_symbols = [_ccxt_to_binance_symbol(s) for s in symbols_raw]

    logger.info(f"Probing Binance Vision manifest for {binance_symbols} × {months}")

    result = probe_manifest(
        symbols=binance_symbols,
        months=months,
        url_head_fn=_http_head_check,
        sleep_between_checks=0.5,
    )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Manifest probe complete. Decision: {result['decision']}")
    logger.info(f"Report written to: {REPORT_PATH}")

    if result["missing_symbol_months"]:
        logger.warning(f"Missing symbol-months: {result['missing_symbol_months']}")

    if result["decision"] == "data_unavailable":
        logger.error("Data unavailable — downloader cannot proceed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
