import json
import time
import urllib.error
import urllib.parse
import urllib.request

from configs import base


def public_get_json(
    url: str,
    live_public_readonly: bool,
    timeout_sec: float = 10.0,
    retry_budget: int = 2,
    sleep_sec: float = 0.2
) -> dict:
    if not live_public_readonly:
        raise PermissionError("explicit --live-public-readonly flag required for network calls")

    headers = {
        "User-Agent": "Antigravity-Crypto-Alpha-Lab-Stage1.5C.1-Client/1.0"
    }
    req = urllib.request.Request(url, headers=headers)

    last_error = None
    for attempt in range(retry_budget + 1):
        if attempt > 0:
            time.sleep(sleep_sec)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                status_code = response.getcode()
                content = response.read().decode("utf-8")
                payload = json.loads(content)
                return {
                    "ok": True,
                    "error": None,
                    "http_status": status_code,
                    "payload": payload
                }
        except urllib.error.HTTPError as e:
            last_error = e
            # If rate limited (429) or server error, we sleep longer
            if e.code == 429:
                time.sleep(sleep_sec * 5)
        except Exception as e:
            last_error = e

    err_status = getattr(last_error, "code", None)
    return {
        "ok": False,
        "error": str(last_error),
        "http_status": err_status,
        "payload": None
    }


def build_klines_url(
    base_url: str,
    path: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    limit: int = 1500
) -> str:
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit
    }
    query_string = urllib.parse.urlencode(params)
    # Ensure base_url has no trailing slash and path has leading slash
    b_url = base_url.rstrip("/")
    p_path = path.lstrip("/")
    return f"{b_url}/{p_path}?{query_string}"


def iter_kline_request_slices(start_ms: int, end_ms: int, interval_ms: int, limit: int) -> list[tuple[int, int]]:
    slices = []
    chunk_ms = limit * interval_ms
    current_start = start_ms
    while current_start < end_ms:
        current_end = min(current_start + chunk_ms, end_ms)
        slices.append((current_start, current_end))
        current_start = current_end
    return slices


def next_start_after_kline_batch(raw_rows: list[list], interval_ms: int) -> int | None:
    if not raw_rows:
        return None
    last_open_time = raw_rows[-1][0]
    return last_open_time + interval_ms


def filter_exchange_symbols(exchange_info: dict, market_type: str) -> set[str]:
    valid_symbols = set()
    symbols_list = exchange_info.get("symbols", [])
    allowed_quote_assets = set(base.EXTERNAL_SIGNAL_STAGE1_5C1_ALLOWED_FUTURES_QUOTE_ASSETS)

    for item in symbols_list:
        symbol = item.get("symbol")
        status = item.get("status")
        quote_asset = item.get("quoteAsset")

        if not symbol or status != "TRADING" or quote_asset not in allowed_quote_assets:
            continue

        if market_type == "futures":
            contract_type = item.get("contractType")
            if contract_type == "PERPETUAL":
                valid_symbols.add(symbol)
        elif market_type == "spot":
            valid_symbols.add(symbol)

    return valid_symbols


def parse_kline_array(raw: list, symbol: str, source: str) -> dict:
    # Binance kline item format:
    # 0: Open time (ms)
    # 1: Open price (str)
    # 2: High price (str)
    # 3: Low price (str)
    # 4: Close price (str)
    # 5: Volume (str)
    # 6: Close time (ms)
    # 7: Quote asset volume (str)
    # 8: Number of trades
    # 9: Taker buy base asset volume
    # 10: Taker buy quote asset volume
    # 11: Ignore
    bar_start_ms = raw[0]
    bar_end_ms = raw[6] + 1  # Standardize to make end_ms open boundary or close_ms + 1

    return {
        "symbol": symbol,
        "bar_start_ms": bar_start_ms,
        "bar_end_ms": bar_end_ms,
        "open": float(raw[1]),
        "high": float(raw[2]),
        "low": float(raw[3]),
        "close": float(raw[4]),
        "quote_volume": float(raw[7]),
        "source": source,
        "source_quality": "exchange_futures_kline_close_price_not_fill_price" if "futures" in source else "spot_price_proxy_report_only_not_futures_execution_price",
        "api_key_used": False,
        "private_endpoint_used": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False
    }


def build_request_manifest_row(
    request_id: str,
    source_type: str,
    symbol: str,
    url: str,
    start_ms: int,
    end_ms: int,
    http_status: int | None,
    row_count: int,
    retry_count: int,
    error: str | None
) -> dict:
    import hashlib
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return {
        "request_id": request_id,
        "source_type": source_type,
        "symbol": symbol,
        "url_hash": url_hash,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "http_status": http_status,
        "row_count": row_count,
        "retry_count": retry_count,
        "error": error,
        "fetched_at_ms": int(time.time() * 1000)
    }
