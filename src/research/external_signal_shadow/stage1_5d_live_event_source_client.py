import json
import time
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
