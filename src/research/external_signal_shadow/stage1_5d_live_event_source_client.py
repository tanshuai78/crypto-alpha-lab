import ipaddress
import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

from configs import base


def host_allowed(host: str, allowed_domains: tuple[str, ...]) -> bool:
    host = host.lower()
    for domain in allowed_domains:
        domain = domain.lower()
        if host == domain or host.endswith("." + domain):
            return True
    return False


def validate_url_allowlist(url: str, allowed_domains: tuple[str, ...]) -> None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname
    if not host or not host_allowed(host, allowed_domains):
        raise ValueError("domain_not_allowed")


def validate_announcement_detail_url(url: str, allowed_domains: tuple[str, ...] | None = None) -> None:
    if not url:
        raise ValueError("detail_url_missing")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("detail_url_scheme_not_allowed")

    host = parsed.hostname
    if not host:
        raise ValueError("domain_not_allowed")

    host = host.lower()

    # Check localhost
    if host in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("domain_not_allowed")

    # Check IP literal for private IP
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None and (ip.is_private or ip.is_loopback):
        raise ValueError("domain_not_allowed")

    if allowed_domains is None:
        allowed_domains = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS", ("binance.com", "www.binance.com"))

    if not host_allowed(host, allowed_domains):
        raise ValueError("domain_not_allowed")

    if "/support/announcement/" not in parsed.path:
        raise ValueError("path_not_allowed")

    query_params = urllib.parse.parse_qs(parsed.query)
    for key in query_params:
        if key.lower() in ("redirect", "url", "next"):
            raise ValueError("detail_url_query_not_allowed")



def build_announcement_list_url(base_url: str, path: str, query_params: dict[str, str]) -> str:
    b_url = base_url.rstrip("/")
    p_path = path.lstrip("/")
    query_string = urllib.parse.urlencode(query_params)
    return f"{b_url}/{p_path}?{query_string}"


def fetch_public_json(url: str, live_public_readonly: bool, timeout_sec: float = 10.0, retry_budget: int = 2) -> dict:
    if not live_public_readonly:
        raise PermissionError("explicit --live-public-readonly flag required for network calls")

    allowed_domains = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS", ("binance.com", "www.binance.com"))
    validate_url_allowlist(url, allowed_domains)

    headers = {
        "User-Agent": "Antigravity-Crypto-Alpha-Lab-Stage1.5D-Client/1.0"
    }
    req = urllib.request.Request(url, headers=headers)

    parsed_req = urllib.parse.urlparse(url)
    requested_host = parsed_req.hostname or ""

    last_error = None
    redirect_count = 0

    for attempt in range(retry_budget + 1):
        if attempt > 0:
            time.sleep(0.2)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                final_url = response.geturl()
                parsed_final = urllib.parse.urlparse(final_url)
                final_host = parsed_final.hostname or ""

                if not final_host or not host_allowed(final_host, allowed_domains):
                    raise ValueError("redirect_final_domain_not_allowed")

                status_code = getattr(response, "status", 200)
                raw_bytes = response.read()
                content = raw_bytes.decode("utf-8")
                payload = json.loads(content)

                if final_url != url:
                    redirect_count = 1

                row_count = None
                if isinstance(payload, dict):
                    data = payload.get("data", {})
                    if isinstance(data, dict):
                        catalogs = data.get("catalogs", [])
                        if isinstance(catalogs, list) and len(catalogs) > 0:
                            articles = catalogs[0].get("articles", [])
                            if isinstance(articles, list):
                                row_count = len(articles)
                elif isinstance(payload, list):
                    row_count = len(payload)

                return {
                    "ok": True,
                    "payload": payload,
                    "requested_url": url,
                    "final_url": final_url,
                    "requested_host": requested_host,
                    "final_host": final_host,
                    "redirect_count": redirect_count,
                    "http_status": status_code,
                    "payload_size_bytes": len(raw_bytes),
                    "row_count": row_count,
                    "error": None,
                }
        except ValueError as e:
            raise e
        except Exception as e:
            last_error = e

    err_status = getattr(last_error, "code", None)
    return {
        "ok": False,
        "payload": None,
        "requested_url": url,
        "final_url": url,
        "requested_host": requested_host,
        "final_host": requested_host,
        "redirect_count": 0,
        "http_status": err_status,
        "payload_size_bytes": 0,
        "row_count": None,
        "error": str(last_error),
    }


def fetch_public_payload(url: str, live_public_readonly: bool, timeout_sec: float = 10.0, retry_budget: int = 0) -> dict:
    """Fetch public readonly payload as raw text, without forcing JSON parse."""
    if not live_public_readonly:
        raise PermissionError("explicit --live-public-readonly flag required for network calls")

    allowed_domains = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS", ("binance.com", "www.binance.com"))
    validate_announcement_detail_url(url, allowed_domains)

    headers = {
        "User-Agent": "Antigravity-Crypto-Alpha-Lab-Stage1.5D-Client/1.0"
    }
    req = urllib.request.Request(url, headers=headers)

    parsed_req = urllib.parse.urlparse(url)
    requested_host = parsed_req.hostname or ""

    last_error = None
    redirect_count = 0

    for attempt in range(retry_budget + 1):
        if attempt > 0:
            time.sleep(0.2)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                final_url = response.geturl()
                validate_announcement_detail_url(final_url, allowed_domains)

                status_code = getattr(response, "status", 200)
                raw_bytes = response.read()

                if status_code != 200:
                    return {
                        "ok": False,
                        "payload": None,
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": len(raw_bytes),
                        "row_count": None,
                        "error": f"detail_payload_http_status_{status_code}",
                    }

                if len(raw_bytes) == 0:
                    return {
                        "ok": False,
                        "payload": None,
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": 0,
                        "row_count": None,
                        "error": "empty_detail_payload",
                    }

                content = raw_bytes.decode("utf-8")

                if final_url != url:
                    redirect_count = 1

                return {
                    "ok": True,
                    "payload": content,
                    "requested_url": url,
                    "final_url": final_url,
                    "requested_host": requested_host,
                    "final_host": urllib.parse.urlparse(final_url).hostname or "",
                    "redirect_count": redirect_count,
                    "http_status": status_code,
                    "payload_size_bytes": len(raw_bytes),
                    "row_count": None,
                    "error": None,
                }
        except ValueError as e:
            raise e
        except Exception as e:
            last_error = e

    err_status = getattr(last_error, "code", None)
    return {
        "ok": False,
        "payload": None,
        "requested_url": url,
        "final_url": url,
        "requested_host": requested_host,
        "final_host": requested_host,
        "redirect_count": 0,
        "http_status": err_status,
        "payload_size_bytes": 0,
        "row_count": None,
        "error": str(last_error),
    }


def build_announcement_detail_fallback_urls(url: str) -> list[str]:
    validate_announcement_detail_url(url)
    parsed = urllib.parse.urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    code = parts[-1]
    candidates = [
        url,
        f"https://www.binance.com/en/support/announcement/detail/{code}",
        f"https://www.binance.com/en/support/announcement/{code}",
    ]
    unique = []
    for candidate in candidates:
        if candidate not in unique:
            validate_announcement_detail_url(candidate)
            unique.append(candidate)
    return unique


def build_bapi_article_detail_url(article_code: str) -> str:
    pattern = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$")
    if not article_code or not re.match(pattern, article_code):
        raise ValueError("bapi_article_code_invalid")
    base_url = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL", "https://www.binance.com")
    path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH", "/bapi/composite/v1/public/cms/article/detail/query")
    return build_announcement_list_url(base_url, path, {"articleCode": article_code})


def validate_bapi_article_detail_url(url: str, allowed_domains: tuple[str, ...] | None = None) -> None:
    if not url:
        raise ValueError("bapi_detail_url_missing")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("bapi_detail_url_scheme_not_allowed")
    if parsed.username or parsed.password:
        raise ValueError("bapi_detail_url_userinfo_not_allowed")
    if parsed.port is not None and parsed.port != 443:
        raise ValueError("bapi_detail_url_port_not_allowed")
    if parsed.fragment:
        raise ValueError("bapi_detail_url_fragment_not_allowed")

    host = parsed.hostname
    if not host:
        raise ValueError("domain_not_allowed")

    host = host.lower()
    if host != "www.binance.com":
        raise ValueError("domain_not_allowed")
    if host in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("domain_not_allowed")

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None and (ip.is_private or ip.is_loopback):
        raise ValueError("domain_not_allowed")

    expected_path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_DETAIL_PATH", "/bapi/composite/v1/public/cms/article/detail/query")
    if parsed.path != expected_path:
        raise ValueError("bapi_detail_path_not_allowed")

    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if len(query_items) != 1 or query_items[0][0] != "articleCode":
        raise ValueError("bapi_article_code_missing")
    code = query_items[0][1]

    pattern = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$")
    if not re.match(pattern, code):
        raise ValueError("bapi_article_code_invalid")


def fetch_public_bapi_article_detail(
    article_code: str,
    live_public_readonly: bool,
    timeout_sec: float = 10.0,
    retry_budget: int = 0,
) -> dict:
    if not live_public_readonly:
        raise PermissionError("explicit --live-public-readonly flag required for network calls")

    url = build_bapi_article_detail_url(article_code)
    allowed_domains = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_DOMAINS", ("binance.com", "www.binance.com"))
    validate_bapi_article_detail_url(url, allowed_domains)

    headers = {
        "User-Agent": "Antigravity-Crypto-Alpha-Lab-Stage1.5D-Client/1.0",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    req = urllib.request.Request(url, headers=headers)

    parsed_req = urllib.parse.urlparse(url)
    requested_host = parsed_req.hostname or ""

    max_bytes = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_DETAIL_MAX_RESPONSE_BYTES", 2_000_000)

    last_error = None
    redirect_count = 0

    for attempt in range(retry_budget + 1):
        if attempt > 0:
            time.sleep(0.2)
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                final_url = response.geturl()
                validate_bapi_article_detail_url(final_url, allowed_domains)

                status_code = getattr(response, "status", 200)
                raw_bytes = response.read(max_bytes + 1)

                if len(raw_bytes) > max_bytes:
                    return {
                        "ok": False,
                        "payload": None,
                        "raw_bytes": b"",
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": len(raw_bytes),
                        "error": "bapi_response_too_large",
                    }

                if status_code != 200:
                    return {
                        "ok": False,
                        "payload": None,
                        "raw_bytes": raw_bytes,
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": len(raw_bytes),
                        "error": f"bapi_http_non_{status_code}",
                    }

                if len(raw_bytes) == 0:
                    return {
                        "ok": False,
                        "payload": None,
                        "raw_bytes": b"",
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": 0,
                        "error": "empty_bapi_payload",
                    }

                try:
                    payload = json.loads(raw_bytes.decode("utf-8"))
                except Exception as e:
                    return {
                        "ok": False,
                        "payload": None,
                        "raw_bytes": raw_bytes,
                        "requested_url": url,
                        "final_url": final_url,
                        "requested_host": requested_host,
                        "final_host": urllib.parse.urlparse(final_url).hostname or "",
                        "redirect_count": redirect_count,
                        "http_status": status_code,
                        "payload_size_bytes": len(raw_bytes),
                        "error": f"bapi_json_parse_failed: {e}",
                    }

                if final_url != url:
                    redirect_count = 1

                return {
                    "ok": True,
                    "payload": payload,
                    "raw_bytes": raw_bytes,
                    "requested_url": url,
                    "final_url": final_url,
                    "requested_host": requested_host,
                    "final_host": urllib.parse.urlparse(final_url).hostname or "",
                    "redirect_count": redirect_count,
                    "http_status": status_code,
                    "payload_size_bytes": len(raw_bytes),
                    "error": None,
                }
        except ValueError as e:
            raise e
        except Exception as e:
            last_error = e

    err_status = getattr(last_error, "code", None)
    return {
        "ok": False,
        "payload": None,
        "raw_bytes": b"",
        "requested_url": url,
        "final_url": url,
        "requested_host": requested_host,
        "final_host": requested_host,
        "redirect_count": 0,
        "http_status": err_status,
        "payload_size_bytes": 0,
        "error": str(last_error),
    }


def normalize_title_for_match(title: str) -> str:
    text = html.unescape(title or "")
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("–", "-").replace("—", "-")
    return " ".join(text.casefold().split())


def validate_bapi_article_detail_payload(
    payload: object,
    *,
    requested_article_code: str,
    catalog_title: str | None = None,
) -> dict:
    if not isinstance(payload, dict):
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if payload.get("code") != "000000":
        return {"payload_trusted": False, "error": "bapi_api_code_non_000000"}
    data = payload.get("data")
    if not isinstance(data, dict):
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if data.get("code") != requested_article_code:
        return {"payload_trusted": False, "error": "bapi_article_identity_mismatch"}
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return {"payload_trusted": False, "error": "bapi_payload_schema_invalid"}
    if catalog_title and normalize_title_for_match(title) != normalize_title_for_match(catalog_title):
        return {
            "payload_trusted": False,
            "error": "bapi_article_title_mismatch",
            "fallback_to_support_detail": True,
        }
    body = data.get("body") or data.get("contentJson")
    if body is None:
        return {"payload_trusted": False, "error": "bapi_body_missing"}
    if isinstance(body, str) and any(marker in body.lower() for marker in ("just a moment", "captcha", "login", "cloudflare")):
        return {"payload_trusted": False, "error": "bapi_waf_or_login_shell"}
    return {"payload_trusted": True, "error": None, "data": data}
