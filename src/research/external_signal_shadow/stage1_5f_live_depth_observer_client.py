import hashlib
import json
import time
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

from loguru import logger

from configs import base


def build_binance_fapi_url(path: str, params: dict) -> str:
    base_url = base.EXTERNAL_SIGNAL_STAGE1_5F_BINANCE_FAPI_BASE_URL.rstrip("/")
    path_cleaned = path.lstrip("/")
    url = f"{base_url}/{path_cleaned}"
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"
    return url


def build_depth_url(symbol: str, limit: int = 100) -> str:
    return build_binance_fapi_url(base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH, {"symbol": symbol, "limit": limit})


def build_exchangeinfo_url() -> str:
    return build_binance_fapi_url(base.EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH, {})


def is_allowed_public_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            return False
        if parsed.hostname != "fapi.binance.com":
            return False
        path = parsed.path
        if path not in (
            base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_PATH,
            base.EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH,
        ):
            return False
        return True
    except Exception:
        return False


def _sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_public_json(url: str, live_public_readonly: bool = False) -> dict:
    if not live_public_readonly:
        raise RuntimeError("Live public network calls are disabled without live_public_readonly flag.")

    fetched_at = int(time.time() * 1000)
    parsed = urllib.parse.urlparse(url)
    manifest = {
        "requested_host": parsed.hostname or "",
        "requested_path": parsed.path or "",
        "requested_url_hash": _sha256_str(url),
        "final_url_hash": "",
        "http_status": 0,
        "payload_size_bytes": 0,
        "response_payload_hash": "",
        "retry_count": 0,
        "error": None,
        "fetched_at_ms": fetched_at,
    }

    if not is_allowed_public_url(url):
        manifest["error"] = "url_not_allowed"
        return {
            "ok": False,
            "error": "url_not_allowed",
            "message": f"URL host, scheme, or path is not allowed: {url}",
            "manifest_row": manifest,
        }

    timeout = base.EXTERNAL_SIGNAL_STAGE1_5F_HTTP_TIMEOUT_SEC
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CryptoDepthObserver/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            final_url = response.url
            manifest["final_url_hash"] = _sha256_str(final_url)

            if not is_allowed_public_url(final_url):
                manifest["error"] = "redirect_final_host_not_allowed"
                return {
                    "ok": False,
                    "error": "redirect_final_host_not_allowed",
                    "manifest_row": manifest,
                }

            status = response.status if hasattr(response, "status") else 200
            manifest["http_status"] = status

            if status != 200:
                manifest["error"] = f"http_error_code_{status}"
                return {
                    "ok": False,
                    "error": f"http_error_code_{status}",
                    "manifest_row": manifest,
                }

            content = response.read()
            manifest["payload_size_bytes"] = len(content)
            manifest["response_payload_hash"] = _sha256_bytes(content)

            try:
                data = json.loads(content.decode("utf-8"))
                return {"ok": True, "data": data, "manifest_row": manifest}
            except json.JSONDecodeError as jde:
                manifest["error"] = "json_decode_error"
                return {
                    "ok": False,
                    "error": "json_decode_error",
                    "message": str(jde),
                    "manifest_row": manifest,
                }
    except HTTPError as he:
        manifest["http_status"] = he.code
        manifest["error"] = f"http_error_{he.code}"
        return {"ok": False, "error": f"http_error_{he.code}", "message": str(he), "manifest_row": manifest}
    except URLError as ue:
        manifest["error"] = "url_error"
        return {"ok": False, "error": "url_error", "message": str(ue), "manifest_row": manifest}
    except Exception as e:
        manifest["error"] = "unexpected_error"
        return {"ok": False, "error": "unexpected_error", "message": str(e), "manifest_row": manifest}


def parse_exchangeinfo_symbols(payload: dict) -> set:
    symbols, _ = parse_exchangeinfo_symbols_and_rows(payload)
    return symbols


def parse_exchangeinfo_symbols_and_rows(payload: dict) -> tuple[set, dict]:
    symbols = set()
    symbol_rows = {}
    if not payload or "symbols" not in payload:
        return symbols, symbol_rows
    for s in payload["symbols"]:
        if isinstance(s, dict) and "symbol" in s:
            sym = s["symbol"]
            symbols.add(sym)
            symbol_rows[sym] = dict(s)
    return symbols, symbol_rows


def refresh_exchangeinfo_cache(
    now_ms: int,
    previous_cache: dict | None,
    live_public_readonly: bool = False,
    mock_exchangeinfo_payload: dict | None = None,
    raw_payload_root: str | None = None,
) -> dict:
    if previous_cache:
        last_refreshed = previous_cache.get("last_refreshed_ms", 0)
        refresh_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_REFRESH_SEC * 1000
        if (now_ms - last_refreshed) < refresh_interval_ms:
            cache_hit = dict(previous_cache)
            cache_hit["manifest_row"] = None
            return cache_hit

    old_symbols = previous_cache.get("symbols", set()) if previous_cache else set()
    old_rows = previous_cache.get("symbol_rows", {}) if previous_cache else {}

    if mock_exchangeinfo_payload is not None:
        symbols, symbol_rows = parse_exchangeinfo_symbols_and_rows(mock_exchangeinfo_payload)
        payload_bytes = json.dumps(mock_exchangeinfo_payload, sort_keys=True).encode("utf-8")
        payload_sha256 = _sha256_bytes(payload_bytes)
        return {
            "last_refreshed_ms": now_ms,
            "fetched_at_ms": now_ms,
            "symbols": symbols,
            "symbol_rows": symbol_rows,
            "available": True,
            "payload_sha256": payload_sha256,
            "raw_payload_path": "mock_exchangeinfo.jsonl",
            "manifest_row": None,
        }

    url = build_exchangeinfo_url()
    try:
        res = fetch_public_json(url, live_public_readonly=live_public_readonly)
        if res["ok"]:
            symbols, symbol_rows = parse_exchangeinfo_symbols_and_rows(res["data"])
            manifest = res.get("manifest_row") or {}
            payload_sha256 = manifest.get("response_payload_hash") or ""
            return {
                "last_refreshed_ms": now_ms,
                "fetched_at_ms": manifest.get("fetched_at_ms", now_ms),
                "symbols": symbols,
                "symbol_rows": symbol_rows,
                "available": True,
                "payload_sha256": payload_sha256,
                "raw_payload_path": "",
                "manifest_row": manifest,
            }
        else:
            logger.warning(f"Failed to refresh exchangeInfo: {res.get('error')}")
            return {
                "last_refreshed_ms": previous_cache.get("last_refreshed_ms", 0) if previous_cache else 0,
                "fetched_at_ms": previous_cache.get("fetched_at_ms", 0) if previous_cache else 0,
                "symbols": old_symbols,
                "symbol_rows": old_rows,
                "available": False,
                "payload_sha256": previous_cache.get("payload_sha256", "") if previous_cache else "",
                "raw_payload_path": previous_cache.get("raw_payload_path", "") if previous_cache else "",
                "manifest_row": res.get("manifest_row"),
            }
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise e
        logger.error(f"Error during exchangeInfo refresh: {e}")
        return {
            "last_refreshed_ms": previous_cache.get("last_refreshed_ms", 0) if previous_cache else 0,
            "fetched_at_ms": previous_cache.get("fetched_at_ms", 0) if previous_cache else 0,
            "symbols": old_symbols,
            "symbol_rows": old_rows,
            "available": False,
            "payload_sha256": previous_cache.get("payload_sha256", "") if previous_cache else "",
            "raw_payload_path": previous_cache.get("raw_payload_path", "") if previous_cache else "",
            "manifest_row": None,
        }



def fetch_depth_snapshot(symbol: str, live_public_readonly: bool = False) -> dict:
    url = build_depth_url(symbol, base.EXTERNAL_SIGNAL_STAGE1_5F_DEPTH_LIMIT)
    return fetch_public_json(url, live_public_readonly=live_public_readonly)
