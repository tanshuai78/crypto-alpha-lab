"""
exchange/client.py — Exchange client factory.

Adapted from my-bitcoin-project/src/exchange/client.py.
Dependency on config_views removed; reads directly from configs.base.
"""
from __future__ import annotations

import ccxt.async_support as ccxt

try:
    from configs.base import EXCHANGE_TIMEOUT_MS, EXCHANGES
except ModuleNotFoundError:
    from configs.base import EXCHANGE_TIMEOUT_MS, EXCHANGES  # type: ignore[no-redef]


async def create_exchange(exchange_id: str, market_type: str = "swap") -> ccxt.Exchange:
    """Create an async exchange instance from configs.base.EXCHANGES."""
    exchange_config = EXCHANGES.get(exchange_id)
    if not exchange_config:
        raise ValueError(f"Unsupported exchange: {exchange_id}. Add it to configs/base.py → EXCHANGES.")

    exchange_class = getattr(ccxt, exchange_config["id"])
    options = exchange_config.get("options", {}).copy()
    options["defaultType"] = market_type

    exchange_params: dict = {
        "enableRateLimit": True,
        "timeout": EXCHANGE_TIMEOUT_MS,
        "options": options,
    }

    if "apiKey" in exchange_config:
        exchange_params["apiKey"] = exchange_config["apiKey"]
    if "secret" in exchange_config:
        exchange_params["secret"] = exchange_config["secret"]
    if "password" in exchange_config:
        exchange_params["password"] = exchange_config["password"]
    if "hostname" in exchange_config:
        exchange_params["hostname"] = exchange_config["hostname"]
    if "proxy" in exchange_config:
        exchange_params["proxies"] = {
            "http": exchange_config["proxy"],
            "https": exchange_config["proxy"],
        }
        exchange_params["aiohttp_proxy"] = exchange_config["proxy"]

    return exchange_class(exchange_params)
