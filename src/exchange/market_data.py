"""
exchange/market_data.py — Minimal market data fetch layer.

Extracted from my-bitcoin-project/src/exchange/market_data.py (lines 39-121, 553-764).
Retained: error classification, retry logic, spot tickers, funding rates (Binance + OKX).
Removed: deep_check_candidates, estimate_impact_cost, fetch_ohlcv, open_interest, orderbook depth.

Dependency closure:
  External: ccxt.async_support, loguru, asyncio
  Internal: exchange.client.create_exchange
  Config:   configs.base.MARKET_DATA_MIN_24H_VOLUME_USDT
"""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

import ccxt.async_support as ccxt
from loguru import logger

from exchange.client import create_exchange

try:
    from configs.base import MARKET_DATA_MIN_24H_VOLUME_USDT
except ModuleNotFoundError:
    from configs.base import MARKET_DATA_MIN_24H_VOLUME_USDT  # type: ignore[no-redef]

# Alias for clarity in fetch functions below
_MIN_24H_VOLUME = MARKET_DATA_MIN_24H_VOLUME_USDT


# ─── Error Classification ───────────────────────────────────────────────────────

class _FetchErrorDict(dict):
    """Dict subclass that carries a fetch_error_code for upstream observability."""
    def __init__(self, *args, fetch_error_code: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetch_error_code = fetch_error_code


class _FetchErrorList(list):
    """List subclass that carries a fetch_error_code for upstream observability."""
    def __init__(self, *args, fetch_error_code: str | None = None):
        super().__init__(*args)
        self.fetch_error_code = fetch_error_code


_RETRYABLE_FETCH_EXCEPTION_TYPES = {
    "RequestTimeout",
    "NetworkError",
    "ExchangeNotAvailable",
    "RateLimitExceeded",
    "DDoSProtection",
}


def _is_retryable_fetch_exception(exc: Exception) -> bool:
    return type(exc).__name__ in _RETRYABLE_FETCH_EXCEPTION_TYPES


def _classify_fetch_error_code(*, stage: str, exc: Exception | None = None, empty: bool = False) -> str:
    if empty:
        return f"{stage}_empty"
    exc_type = type(exc).__name__ if exc is not None else ""
    if exc_type == "RequestTimeout":
        kind = "timeout"
    elif exc_type in {"ExchangeNotAvailable", "NetworkError", "RateLimitExceeded", "DDoSProtection"}:
        kind = "unavailable"
    else:
        kind = "unavailable"
    return f"{stage}_{kind}"


def _format_fetch_exception(*, operation: str, exc: Exception) -> str:
    """Return a compact, single-line error description."""
    exc_type = type(exc).__name__
    retryable = "yes" if exc_type in _RETRYABLE_FETCH_EXCEPTION_TYPES else "unknown"
    status = None
    for attr in ("http_status", "status", "status_code"):
        value = getattr(exc, attr, None)
        if value is not None:
            status = value
            break
    detail = str(exc).replace("\n", " ").strip()
    parts = [f"type={exc_type}", f"op={operation}", f"retryable={retryable}"]
    if status is not None:
        parts.append(f"status={status}")
    parts.append(f"detail={detail}")
    return " ".join(parts)


async def _run_fetch_with_single_retry(fetch_coro_factory):
    """Run a fetch coroutine with one automatic retry on retryable errors."""
    attempts = 2
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await fetch_coro_factory()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or not _is_retryable_fetch_exception(exc):
                raise
    assert last_exc is not None
    raise last_exc


# ─── Core Fetch Functions ───────────────────────────────────────────────────────

async def fetch_spot_tickers_safe(
    exchange_id: str,
    exchange_client: Optional[ccxt.Exchange] = None,
) -> Dict[str, dict]:
    """Fetch spot ticker data safely with error classification.

    Returns a dict of {symbol: {price, volume, bid, ask, last}}.
    On failure, returns a _FetchErrorDict with fetch_error_code set.

    Args:
        exchange_id: ccxt exchange id (e.g. "binance", "okx")
        exchange_client: Optional persistent client. If None, creates and closes one.
    """
    should_close = False
    exchange = None
    try:
        if exchange_client:
            exchange = exchange_client
        else:
            exchange = await create_exchange(exchange_id, market_type="spot")
            should_close = True
            await exchange.load_markets()

        tickers = await _run_fetch_with_single_retry(exchange.fetch_tickers)

        data = {}
        for symbol, ticker in tickers.items():
            if "/USDT" in symbol and "USDT" in symbol.split("/")[1]:
                base = symbol.split("/")[0]
                quote_volume = ticker.get("quoteVolume") or 0
                if ticker.get("ask"):
                    data[f"{base}USDT"] = {
                        "price": float(ticker["ask"]),
                        "volume": float(quote_volume),
                        "bid": float(ticker.get("bid", 0)),
                        "ask": float(ticker.get("ask", 0)),
                        "last": float(ticker.get("last", 0)),
                    }

        logger.info(f"[{exchange_id}] spot tickers fetched: {len(data)} symbols")
        return data

    except Exception as e:
        logger.error(
            f"[{exchange_id}] spot fetch failed: "
            f"{_format_fetch_exception(operation='fetch_spot_tickers', exc=e)}"
        )
        return _FetchErrorDict(fetch_error_code=_classify_fetch_error_code(stage="spot", exc=e))
    finally:
        if should_close and exchange:
            await exchange.close()


async def fetch_binance_funding_data(
    spot_data: Dict[str, dict],
    exchange_client: Optional[ccxt.Exchange] = None,
) -> Tuple[List[dict], Dict[str, float]]:
    """Fetch Binance perpetual funding rates filtered by spot volume.

    Returns (results, prices) where:
      - results: list of {symbol, funding_rate, spot_ask, perp_bid, volume_24h}
      - prices: dict of {symbol: perp_bid}
    On failure, returns (_FetchErrorList, {}).

    Args:
        spot_data: Output of fetch_spot_tickers_safe — used to filter by volume.
        exchange_client: Optional persistent Binance swap client.
    """
    should_close = False
    exchange = None
    results = []
    prices = {}

    try:
        if exchange_client:
            exchange = exchange_client
        else:
            exchange = await create_exchange("binance", market_type="swap")
            should_close = True
            await exchange.load_markets()

        async def _fetch():
            return await asyncio.gather(
                exchange.fapiPublicGetPremiumIndex(),
                exchange.fetch_tickers(),
            )

        premium_index, tickers = await _run_fetch_with_single_retry(_fetch)

        perp_bids = {}
        for symbol, ticker in tickers.items():
            if "/USDT:USDT" in symbol and ticker.get("bid"):
                base = symbol.split("/")[0]
                perp_bids[f"{base}USDT"] = float(ticker["bid"])

        filtered_count = 0
        for item in premium_index:
            symbol = item.get("symbol", "")
            if not symbol.endswith("USDT"):
                continue
            funding_rate = float(item.get("lastFundingRate", 0))
            mark_price = float(item.get("markPrice", 0))
            spot_info = spot_data.get(symbol)
            if not spot_info:
                continue
            if spot_info["volume"] < _MIN_24H_VOLUME:
                filtered_count += 1
                continue
            perp_bid = perp_bids.get(symbol, mark_price)
            results.append({
                "symbol": symbol,
                "funding_rate": funding_rate,
                "spot_ask": spot_info["price"],
                "perp_bid": perp_bid,
                "volume_24h": spot_info["volume"],
            })
            prices[symbol] = perp_bid

        if filtered_count > 0:
            logger.info(f"[binance] filtered {filtered_count} low-liquidity symbols")
        logger.info(f"[binance] funding data fetched: {len(results)} symbols")
        return results, prices

    except Exception as e:
        logger.error(
            "[binance] funding fetch failed: "
            f"{_format_fetch_exception(operation='fetch_binance_funding', exc=e)}"
        )
        return _FetchErrorList(fetch_error_code=_classify_fetch_error_code(stage="funding", exc=e)), {}
    finally:
        if should_close and exchange:
            await exchange.close()


async def fetch_okx_funding_data(
    spot_data: Dict[str, dict],
    exchange_client: Optional[ccxt.Exchange] = None,
) -> Tuple[List[dict], Dict[str, float]]:
    """Fetch OKX perpetual funding rates filtered by spot volume.

    Returns (results, prices) — same schema as fetch_binance_funding_data.
    On failure, returns (_FetchErrorList, {}).

    Args:
        spot_data: Output of fetch_spot_tickers_safe.
        exchange_client: Optional persistent OKX swap client.
    """
    should_close = False
    exchange = None
    results = []
    prices = {}

    try:
        if exchange_client:
            exchange = exchange_client
        else:
            exchange = await create_exchange("okx", market_type="swap")
            should_close = True
            await exchange.load_markets()

        tickers = await _run_fetch_with_single_retry(exchange.fetch_tickers)

        candidate_symbols = []
        perp_bids = {}

        for symbol, ticker in tickers.items():
            if "/USDT:USDT" in symbol and ticker.get("bid"):
                base = symbol.split("/")[0]
                spot_symbol = f"{base}USDT"
                spot_info = spot_data.get(spot_symbol)
                if spot_info and spot_info["volume"] >= _MIN_24H_VOLUME:
                    candidate_symbols.append(symbol)
                    perp_bids[spot_symbol] = float(ticker["bid"])

        logger.info(f"[okx] querying funding rates for {len(candidate_symbols)} active contracts")

        batch_size = 20
        all_rates: list = []
        for i in range(0, len(candidate_symbols), batch_size):
            batch = candidate_symbols[i : i + batch_size]
            tasks = [exchange.fetch_funding_rate(sym) for sym in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            all_rates.extend(batch_results)
            await asyncio.sleep(0.1)

        for res in all_rates:
            if isinstance(res, dict):
                symbol_ccxt = res["symbol"]
                base = symbol_ccxt.split("/")[0]
                spot_symbol = f"{base}USDT"
                funding_rate = res.get("fundingRate")
                spot_info = spot_data.get(spot_symbol)
                perp_bid = perp_bids.get(spot_symbol)
                if funding_rate is not None and spot_info and perp_bid:
                    results.append({
                        "symbol": spot_symbol,
                        "funding_rate": float(funding_rate),
                        "spot_ask": spot_info["price"],
                        "perp_bid": perp_bid,
                        "volume_24h": spot_info["volume"],
                    })
                    prices[spot_symbol] = perp_bid

        logger.info(f"[okx] funding data fetched: {len(results)} symbols")
        return results, prices

    except Exception as e:
        logger.error(
            "[okx] funding fetch failed: "
            f"{_format_fetch_exception(operation='fetch_okx_funding', exc=e)}"
        )
        return _FetchErrorList(fetch_error_code=_classify_fetch_error_code(stage="funding", exc=e)), {}
    finally:
        if should_close and exchange:
            await exchange.close()
