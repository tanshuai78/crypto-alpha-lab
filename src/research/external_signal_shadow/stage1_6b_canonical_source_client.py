"""Standard-library HTTPS public-web client for Stage 1.6B canonical official source capture."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from configs import base
from src.research.external_signal_shadow.stage1_6b_canonical_source_models import (
    ALLOWED_FINAL_HOST,
    BASE_URL,
    CANONICAL_HEADERS,
    DETAIL_PATH,
    DETAIL_QUERY_TEMPLATE,
    INDEX_PATH,
    INDEX_QUERY_TEMPLATE,
)


class ClientValidationError(ValueError):
    """Raised when request URL or header validation fails."""
    pass


class ClientNetworkError(RuntimeError):
    """Raised on network or transport failure."""
    pass


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    final_url: str
    http_status: int
    content_type: str
    raw_payload_bytes: int
    raw_payload: bytes
    t_receive_ms: int
    trust_validation_status: str
    error_message: Optional[str] = None


def validate_request_url_and_headers(
    url: str,
    headers: Dict[str, str],
) -> urllib.request.Request:
    """Strict validation of request scheme, host, and forbidden headers."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise ClientValidationError(f"https_required: scheme={parsed.scheme}")

    if parsed.netloc != ALLOWED_FINAL_HOST:
        raise ClientValidationError(f"disallowed_host: {parsed.netloc} != {ALLOWED_FINAL_HOST}")

    # Forbid credentials, cookies, authorization
    for forbidden in ["cookie", "authorization", "proxy-authorization"]:
        for h_key in headers.keys():
            if h_key.lower() == forbidden:
                raise ClientValidationError(f"forbidden_header:{h_key}")

    req = urllib.request.Request(url, headers=headers, method="GET")
    return req


class Stage16BCanonicalClient:
    """Public-web read-only client for Binance CMS announcement endpoints."""

    def __init__(
        self,
        live_public_readonly: bool = False,
        opener: Optional[Callable[..., Any]] = None,
        timeout_sec: Optional[float] = None,
    ):
        if not live_public_readonly:
            raise ValueError("live_public_readonly_required: must explicitly specify live_public_readonly=True")

        self.opener = opener or urllib.request.urlopen
        self.timeout_sec = timeout_sec or base.EXTERNAL_SIGNAL_STAGE1_6B_HTTP_TIMEOUT_SEC
        self.max_payload_bytes = base.EXTERNAL_SIGNAL_STAGE1_6B_MAX_RAW_PAYLOAD_BYTES

    def _execute_get(self, url: str) -> FetchResult:
        req = validate_request_url_and_headers(url, CANONICAL_HEADERS)

        try:
            resp = self.opener(req, timeout=self.timeout_sec)
            t_receive = int(time.time() * 1000)
            status = getattr(resp, "status", getattr(resp, "code", 200))
            final_url = resp.geturl() if hasattr(resp, "geturl") else url
            content_type = resp.getheader("Content-Type", "") if hasattr(resp, "getheader") else ""

            # Validate final redirect URL
            parsed_final = urllib.parse.urlparse(final_url)
            if parsed_final.scheme != "https" or parsed_final.netloc != ALLOWED_FINAL_HOST:
                return FetchResult(
                    requested_url=url,
                    final_url=final_url,
                    http_status=status,
                    content_type=content_type,
                    raw_payload_bytes=0,
                    raw_payload=b"",
                    t_receive_ms=t_receive,
                    trust_validation_status="disallowed_redirect",
                    error_message=f"Redirect to {final_url} rejected",
                )

            body = resp.read()
            payload_len = len(body)

            if payload_len == 0:
                return FetchResult(
                    requested_url=url,
                    final_url=final_url,
                    http_status=status,
                    content_type=content_type,
                    raw_payload_bytes=0,
                    raw_payload=b"",
                    t_receive_ms=t_receive,
                    trust_validation_status="empty_payload",
                    error_message="Empty response body",
                )

            if payload_len > self.max_payload_bytes:
                return FetchResult(
                    requested_url=url,
                    final_url=final_url,
                    http_status=status,
                    content_type=content_type,
                    raw_payload_bytes=payload_len,
                    raw_payload=body[:1024],  # truncate
                    t_receive_ms=t_receive,
                    trust_validation_status="payload_size_exceeded",
                    error_message=f"Payload size {payload_len} > cap {self.max_payload_bytes}",
                )

            # Check WAF HTML signature
            if "text/html" in content_type or b"<html" in body.lower() or b"cloudflare" in body.lower() or b"waf" in body.lower():
                return FetchResult(
                    requested_url=url,
                    final_url=final_url,
                    http_status=status,
                    content_type=content_type,
                    raw_payload_bytes=payload_len,
                    raw_payload=body,
                    t_receive_ms=t_receive,
                    trust_validation_status="waf_rejected",
                    error_message="WAF or HTML payload detected",
                )

            # Verify JSON parseability
            try:
                json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return FetchResult(
                    requested_url=url,
                    final_url=final_url,
                    http_status=status,
                    content_type=content_type,
                    raw_payload_bytes=payload_len,
                    raw_payload=body,
                    t_receive_ms=t_receive,
                    trust_validation_status="malformed_json",
                    error_message=f"JSON decode failed: {exc}",
                )

            return FetchResult(
                requested_url=url,
                final_url=final_url,
                http_status=status,
                content_type=content_type,
                raw_payload_bytes=payload_len,
                raw_payload=body,
                t_receive_ms=t_receive,
                trust_validation_status="trusted",
            )

        except urllib.error.HTTPError as exc:
            t_receive = int(time.time() * 1000)
            err_body = exc.read() if hasattr(exc, "read") else b""
            return FetchResult(
                requested_url=url,
                final_url=exc.geturl() if hasattr(exc, "geturl") else url,
                http_status=exc.code,
                content_type=exc.headers.get("Content-Type", "") if hasattr(exc, "headers") and exc.headers else "",
                raw_payload_bytes=len(err_body),
                raw_payload=err_body,
                t_receive_ms=t_receive,
                trust_validation_status="http_error",
                error_message=f"HTTP {exc.code}: {exc.reason}",
            )
        except Exception as exc:
            t_receive = int(time.time() * 1000)
            return FetchResult(
                requested_url=url,
                final_url=url,
                http_status=0,
                content_type="",
                raw_payload_bytes=0,
                raw_payload=b"",
                t_receive_ms=t_receive,
                trust_validation_status="network_error",
                error_message=f"Network error: {exc}",
            )

    def fetch_index_page(
        self,
        page_no: int,
        run_id: str,
        request_class: str,
        monotonic_request_seq: int,
    ) -> FetchResult:
        """Fetch one announcement list index page."""
        query = INDEX_QUERY_TEMPLATE.format(page_no=page_no)
        url = f"{BASE_URL}{INDEX_PATH}?{query}"
        res = self._execute_get(url)

        if res.trust_validation_status == "trusted":
            # Semantic verification of index payload structure
            try:
                data = json.loads(res.raw_payload.decode("utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("data"), dict) or not isinstance(data["data"].get("articles"), list):
                    return FetchResult(
                        requested_url=res.requested_url,
                        final_url=res.final_url,
                        http_status=res.http_status,
                        content_type=res.content_type,
                        raw_payload_bytes=res.raw_payload_bytes,
                        raw_payload=res.raw_payload,
                        t_receive_ms=res.t_receive_ms,
                        trust_validation_status="malformed_index_schema",
                        error_message="Index payload missing data.articles list",
                    )
            except Exception as exc:
                return FetchResult(
                    requested_url=res.requested_url,
                    final_url=res.final_url,
                    http_status=res.http_status,
                    content_type=res.content_type,
                    raw_payload_bytes=res.raw_payload_bytes,
                    raw_payload=res.raw_payload,
                    t_receive_ms=res.t_receive_ms,
                    trust_validation_status="malformed_json",
                    error_message=str(exc),
                )

        return res

    def fetch_article_detail(
        self,
        article_code: str,
        run_id: str,
        request_class: str,
        monotonic_request_seq: int,
    ) -> FetchResult:
        """Fetch one announcement detail page."""
        query = DETAIL_QUERY_TEMPLATE.format(article_code=article_code)
        url = f"{BASE_URL}{DETAIL_PATH}?{query}"
        res = self._execute_get(url)

        if res.trust_validation_status == "trusted":
            # Semantic verification of detail payload structure
            try:
                data = json.loads(res.raw_payload.decode("utf-8"))
                if not isinstance(data, dict) or not isinstance(data.get("data"), dict) or not isinstance(data["data"].get("body"), str):
                    return FetchResult(
                        requested_url=res.requested_url,
                        final_url=res.final_url,
                        http_status=res.http_status,
                        content_type=res.content_type,
                        raw_payload_bytes=res.raw_payload_bytes,
                        raw_payload=res.raw_payload,
                        t_receive_ms=res.t_receive_ms,
                        trust_validation_status="malformed_detail_schema",
                        error_message="Detail payload missing data.body string",
                    )
            except Exception as exc:
                return FetchResult(
                    requested_url=res.requested_url,
                    final_url=res.final_url,
                    http_status=res.http_status,
                    content_type=res.content_type,
                    raw_payload_bytes=res.raw_payload_bytes,
                    raw_payload=res.raw_payload,
                    t_receive_ms=res.t_receive_ms,
                    trust_validation_status="malformed_json",
                    error_message=str(exc),
                )

        return res
