from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any
import urllib.request
import urllib.parse
import json

logger = logging.getLogger(__name__)


def symbol_to_coinalyze_contract(symbol: str) -> dict[str, Any]:
    # Mapping for symbols
    mapping = {
        "BTC/USDT": "BTCUSDT_PERP.A",
        "ETH/USDT": "ETHUSDT_PERP.A",
        "SOL/USDT": "SOLUSDT_PERP.A",
        "XRP/USDT": "XRPUSDT_PERP.A",
        "DOGE/USDT": "DOGEUSDT_PERP.A",
    }
    coinalyze_symbol = mapping.get(symbol)
    if not coinalyze_symbol:
        clean = symbol.replace("/", "")
        coinalyze_symbol = f"{clean}_PERP.A"

    parts = symbol.split("/")
    base = parts[0] if len(parts) > 0 else ""
    quote = parts[1] if len(parts) > 1 else ""

    return {
        "input_symbol": symbol,
        "coinalyze_symbol": coinalyze_symbol,
        "exchange": "binance",
        "symbol_on_exchange": coinalyze_symbol.split("_")[0] if "_" in coinalyze_symbol else coinalyze_symbol,
        "base_asset": base,
        "quote_asset": quote,
        "is_perpetual": True,
        "margined": "STABLE",
        "mapping_source": "supported_future_markets|static_fallback",
    }


def normalize_interval(interval: str) -> str:
    if interval in ("1h", "1hour"):
        return "1hour"
    return interval


def load_feasibility_audit() -> dict[str, Any]:
    # Check if API key is present in environment to decide api_access state
    api_key = os.environ.get("COINALYZE_API_KEY", "")
    api_access = "available" if api_key else "unavailable"

    return {
        "vendor_candidates": [
            {
                "vendor": "coinalyze",
                "api_access": api_access,
                "requires_paid_plan": False,
                "granularity": "1hour",
                "exchange_coverage": ["binance", "okx", "bybit"],
                "symbol_coverage": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
                "historical_depth_days": 80,
                "can_support_replay": True,
                "blocker": "" if api_key else "requires_coinalyze_api_key",
            }
        ]
    }


def fetch_historical_liquidations(
    symbol: str,
    from_ts_sec: int,
    to_ts_sec: int,
    interval: str = "1hour",
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    if not api_key:
        api_key = os.environ.get("COINALYZE_API_KEY", "")
    if not api_key:
        logger.warning("COINALYZE_API_KEY missing from environment. Gracefully degrading to empty payload.")
        return []

    coinalyze_symbol_info = symbol_to_coinalyze_contract(symbol)
    coinalyze_symbol = coinalyze_symbol_info["coinalyze_symbol"]

    base_url = "https://api.coinalyze.net/v1/liquidation-history"
    params = {
        "symbols": coinalyze_symbol,
        "interval": normalize_interval(interval),
        "from": str(from_ts_sec),
        "to": str(to_ts_sec),
        "convert_to_usd": "true",
        "api_key": api_key,
    }

    query_string = urllib.parse.urlencode(params)
    url = f"{base_url}?{query_string}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Antigravity/1.0"})
        with urllib.request.urlopen(req) as response:
            # urlopen in Python stdlib returns HTTPResponse
            # we check status code via getcode() or status
            status_code = response.getcode()
            if status_code == 200:
                data = json.loads(response.read().decode("utf-8"))
                return data
            else:
                logger.error(f"Failed to fetch liquidations, status code: {status_code}")
                return []
    except Exception as e:
        logger.error(f"Error fetching historical liquidations from Coinalyze: {e}")
        return []


def normalize_coinalyze_payload(
    payload: list[dict[str, Any]] | None,
    symbol: str,
) -> list[dict[str, Any]]:
    if not payload:
        return []

    coinalyze_symbol_info = symbol_to_coinalyze_contract(symbol)
    coinalyze_symbol = coinalyze_symbol_info["coinalyze_symbol"]

    # We need to aggregate duplicate symbol + hour_bucket_ms rows by sum.
    aggregated: dict[int, dict[str, Any]] = {}

    for row in payload:
        t_sec = int(row.get("t") or 0)
        hour_bucket_ms = t_sec * 1000

        long_liq = float(row.get("l") or 0.0)
        short_liq = float(row.get("s") or 0.0)

        if hour_bucket_ms not in aggregated:
            aggregated[hour_bucket_ms] = {
                "long": 0.0,
                "short": 0.0,
            }
        aggregated[hour_bucket_ms]["long"] += long_liq
        aggregated[hour_bucket_ms]["short"] += short_liq

    normalized: list[dict[str, Any]] = []
    for bucket_ms, vals in aggregated.items():
        dt = datetime.fromtimestamp(bucket_ms / 1000, tz=timezone.utc)
        hour_bucket_utc = dt.strftime("%Y-%m-%dT%H:00")

        long_liq = vals["long"]
        short_liq = vals["short"]
        total_liq = long_liq + short_liq

        normalized.append({
            "symbol": symbol,
            "vendor_symbol": coinalyze_symbol,
            "hour_bucket_ms": bucket_ms,
            "hour_bucket_utc": hour_bucket_utc,
            "long_liquidation_notional_1h_usdt": long_liq,
            "short_liquidation_notional_1h_usdt": short_liq,
            "total_liquidation_notional_1h_usdt": total_liq,
            "liquidation_notional_1h_usdt": total_liq,
            "liquidation_source": "third_party_historical",
            "liquidation_source_quality": "historical_vendor_dataset",
            "vendor_name": "coinalyze",
            "vendor_granularity": "1hour",
            "normalized_granularity": "1h",
            "convert_to_usd": True,
            "timestamp_unit_source": "seconds",
        })

    return normalized
