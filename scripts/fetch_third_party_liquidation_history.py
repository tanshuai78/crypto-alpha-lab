from __future__ import annotations

import os
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def load_feasibility_audit() -> dict[str, Any]:
    # Check if API key is present in environment to decide api_access state
    api_key = os.environ.get("COINGLASS_API_KEY", "")
    api_access = "available" if api_key else "unavailable"

    return {
        "vendor_candidates": [
            {
                "vendor": "coinglass",
                "api_access": api_access,
                "requires_paid_plan": True,
                "granularity": "1h",
                "exchange_coverage": ["binance", "okx", "bybit"],
                "symbol_coverage": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
                "historical_depth_days": 365,
                "can_support_replay": True,
                "blocker": "" if api_key else "requires_paid_developer_api_plan_and_key",
            }
        ]
    }


def fetch_historical_liquidations(
    symbol: str,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    api_key = os.environ.get("COINGLASS_API_KEY", "")
    if not api_key:
        logger.warning("COINGLASS_API_KEY missing from environment. Gracefully degrading to empty payload.")
        return []

    # Spike request implementation placeholder (mock-driven for tests, no live HTTP requests during pytest)
    # In real use case, this fetches from Coinglass API endpoints
    return []


def normalize_coinglass_payload(
    payload: list[dict[str, Any]],
    symbol: str,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in payload:
        time_ms = int(row.get("time") or 0)
        dt = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
        hour_bucket_utc = dt.strftime("%Y-%m-%dT%H:00")

        # buyVolUsd is the short liquidation (buying to cover shorts)
        # sellVolUsd is the long liquidation (selling to cover longs)
        long_liq = float(row.get("sellVolUsd") or 0.0)
        short_liq = float(row.get("buyVolUsd") or 0.0)
        total_liq = long_liq + short_liq

        normalized.append({
            "symbol": symbol,
            "long_liquidation_notional_1h_usdt": long_liq,
            "short_liquidation_notional_1h_usdt": short_liq,
            "total_liquidation_notional_1h_usdt": total_liq,
            "liquidation_source": "third_party_historical",
            "liquidation_source_quality": "historical_vendor_dataset",
            "vendor_name": "coinglass",
            "vendor_granularity": "1h",
            "hour_bucket_ms": time_ms,
            "hour_bucket_utc": hour_bucket_utc,
        })
    return normalized
