"""
src/research/external_signal_shadow/stage1_4a_public_client.py
"""

import urllib.parse

from configs.base import EXTERNAL_SIGNAL_STAGE1_4_BINANCE_FAPI_BASE_URL

ALLOWED_PATHS = {
    "/fapi/v1/fundingRate",
    "/futures/data/openInterestHist",
    "/fapi/v1/klines",
    "/fapi/v1/openInterest",
}

FORBIDDEN_SUBSTRINGS = {
    "/order",
    "/account",
    "/positionRisk",
    "/wallet",
    "/withdraw",
    "/sapi",
}

FORBIDDEN_HEADERS_OR_PARAMS = {
    "signature",
    "apikey",
    "x-mbx-apikey",
    "secret",
}


def build_binance_public_url(
    path: str, query_params: dict | None = None, headers: dict | None = None
) -> str:
    """
    Builds a public Binance URL for readonly endpoints.
    Strictly rejects any private paths, API keys, or signatures.
    """
    # Check headers for leak checks
    if headers:
        for k in headers.keys():
            if str(k).lower() in FORBIDDEN_HEADERS_OR_PARAMS:
                raise ValueError(f"Forbidden security header detected: {k}")

    # Check query params for leak checks
    if query_params:
        for k in query_params.keys():
            if str(k).lower() in FORBIDDEN_HEADERS_OR_PARAMS:
                raise ValueError(f"Forbidden security parameter detected: {k}")

    # Validate path
    normalized_path = path.strip()
    if not normalized_path.startswith("/"):
        normalized_path = "/" + normalized_path

    # Check for forbidden substrings
    for sub in FORBIDDEN_SUBSTRINGS:
        if sub in normalized_path:
            raise ValueError(f"Access to private/restricted path is forbidden: {path}")

    # Enforce exact allowed path list
    if normalized_path not in ALLOWED_PATHS:
        raise ValueError(f"Path is not in the allowed public endpoint list: {path}")

    # Build URL
    base_url = EXTERNAL_SIGNAL_STAGE1_4_BINANCE_FAPI_BASE_URL.rstrip("/")
    url = f"{base_url}{normalized_path}"

    if query_params:
        url = f"{url}?{urllib.parse.urlencode(query_params)}"

    return url
