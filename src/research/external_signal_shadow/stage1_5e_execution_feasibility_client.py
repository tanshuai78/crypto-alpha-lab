import json
import urllib.parse
import urllib.request
from typing import Any, Dict
from urllib.error import HTTPError, URLError

from loguru import logger

from configs import base


def build_depth_url(symbol: str, limit: int = 100) -> str:
    """
    Construct the public Binance FAPI depth URL for a given symbol and limit.
    """
    base_url = base.EXTERNAL_SIGNAL_STAGE1_5E_BINANCE_FAPI_BASE_URL.rstrip("/")
    path = base.EXTERNAL_SIGNAL_STAGE1_5E_DEPTH_PATH.lstrip("/")
    url = f"{base_url}/{path}"

    params = {"symbol": symbol, "limit": limit}
    query = urllib.parse.urlencode(params)
    return f"{url}?{query}"


def is_allowed_public_url(url: str) -> bool:
    """
    Validate that the URL points only to fapi.binance.com with HTTPS.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            return False
        # The hostname must be exactly fapi.binance.com
        if parsed.hostname != "fapi.binance.com":
            return False
        return True
    except Exception:
        return False


def fetch_public_json(url: str, live_public_readonly: bool = False) -> Dict[str, Any]:
    """
    Fetch JSON from a public URL using standard urllib.
    Only allows calls if live_public_readonly is True.
    Protects against non-allowed redirect targets.
    """
    if not live_public_readonly:
        return {
            "ok": False,
            "error": "live_network_disabled",
            "message": "Live public network calls are disabled without live_public_readonly flag."
        }

    if not is_allowed_public_url(url):
        return {
            "ok": False,
            "error": "url_not_allowed",
            "message": f"URL host or scheme is not allowed: {url}"
        }

    timeout = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5E_REQUEST_TIMEOUT_SEC", 10.0)

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "CryptoFeasibilityAudit/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            final_url = response.url
            if not is_allowed_public_url(final_url):
                logger.error(f"Redirect final URL not allowed: {final_url}")
                return {
                    "ok": False,
                    "error": "redirect_final_host_not_allowed"
                }

            status = response.status if hasattr(response, "status") else 200
            if status != 200:
                return {
                    "ok": False,
                    "error": f"http_error_code_{status}"
                }

            content = response.read()
            try:
                data = json.loads(content.decode("utf-8"))
                return {"ok": True, "data": data}
            except json.JSONDecodeError as jde:
                return {
                    "ok": False,
                    "error": "json_decode_error",
                    "message": str(jde)
                }

    except HTTPError as he:
        logger.error(f"HTTP error fetching URL: {url} -> {he}")
        return {"ok": False, "error": f"http_error_{he.code}", "message": str(he)}
    except URLError as ue:
        logger.error(f"URL error fetching URL: {url} -> {ue}")
        return {"ok": False, "error": "url_error", "message": str(ue)}
    except Exception as e:
        logger.error(f"Unexpected error fetching URL: {url} -> {e}")
        return {"ok": False, "error": "unexpected_error", "message": str(e)}
