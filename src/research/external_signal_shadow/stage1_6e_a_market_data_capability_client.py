import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from configs import base


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return None


def _build_default_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(
        _NoRedirectHandler(),
        urllib.request.ProxyHandler({}),
    )


@dataclass(frozen=True)
class TransportResult:
    http_status: int | None
    headers: dict[str, str | None]
    raw_body: bytes | None
    observed_bytes_lower_bound: int
    is_timeout: bool = False
    transport_error: bool = False
    body_too_large: bool = False
    is_redirect: bool = False
    non_identity_encoding: bool = False


class Stage16EACapabilityClient:
    def __init__(
        self,
        opener: urllib.request.OpenerDirector | Any | None = None,
        timeout_sec: float | None = None,
        max_raw_bytes: int | None = None,
    ):
        self._opener = opener if opener is not None else _build_default_opener()
        self._timeout_sec = (
            timeout_sec
            if timeout_sec is not None
            else base.EXTERNAL_SIGNAL_STAGE1_6E_A_HTTP_TIMEOUT_SEC
        )
        self._max_raw_bytes = (
            max_raw_bytes
            if max_raw_bytes is not None
            else base.EXTERNAL_SIGNAL_STAGE1_6E_A_MAX_RAW_PAYLOAD_BYTES
        )

    def _extract_headers_subset(self, hdrs: Any) -> tuple[dict[str, str | None], bool]:
        subset: dict[str, str | None] = {
            "content-type": None,
            "content-length": None,
            "content-encoding": None,
            "date": None,
            "retry-after": None,
        }
        if hdrs is None:
            return subset, False

        # Support mapping or email.message
        for key in subset.keys():
            val = hdrs.get(key)
            if val is None:
                # case insensitive lookup
                val = hdrs.get(key.title()) or hdrs.get(key.upper())
            if val is not None:
                subset[key] = str(val).strip()

        ce = subset.get("content-encoding")
        non_identity = False
        if ce is not None and ce.lower() != "identity":
            non_identity = True

        return subset, non_identity

    def fetch(self, profile_core: dict[str, Any], request_seq: int) -> TransportResult:
        scheme = profile_core["scheme"]
        host = profile_core["host"]
        path = profile_core["path"]
        query = profile_core["canonical_query"]
        url = f"{scheme}://{host}{path}?{query}"

        req = urllib.request.Request(
            url=url,
            headers={"Accept-Encoding": "identity"},
            method="GET",
        )

        try:
            resp = self._opener.open(req, timeout=self._timeout_sec)
            status_code = getattr(resp, "status", getattr(resp, "code", 200))
            hdrs = getattr(resp, "headers", None)
            headers_subset, non_identity = self._extract_headers_subset(hdrs)

            # Read bounded body up to max_raw_bytes + 1
            read_limit = self._max_raw_bytes + 1
            raw_chunk = resp.read(read_limit)
            if hasattr(resp, "close"):
                resp.close()

            if len(raw_chunk) > self._max_raw_bytes:
                return TransportResult(
                    http_status=status_code,
                    headers=headers_subset,
                    raw_body=None,
                    observed_bytes_lower_bound=len(raw_chunk),
                    body_too_large=True,
                    is_redirect=(300 <= status_code < 400),
                    non_identity_encoding=non_identity,
                )

            return TransportResult(
                http_status=status_code,
                headers=headers_subset,
                raw_body=raw_chunk,
                observed_bytes_lower_bound=len(raw_chunk),
                body_too_large=False,
                is_redirect=(300 <= status_code < 400),
                non_identity_encoding=non_identity,
            )

        except urllib.error.HTTPError as exc:
            headers_subset, non_identity = self._extract_headers_subset(exc.headers)
            body_bytes = b""
            if exc.fp is not None:
                body_bytes = exc.fp.read(self._max_raw_bytes + 1)

            if len(body_bytes) > self._max_raw_bytes:
                return TransportResult(
                    http_status=exc.code,
                    headers=headers_subset,
                    raw_body=None,
                    observed_bytes_lower_bound=len(body_bytes),
                    body_too_large=True,
                    is_redirect=(300 <= exc.code < 400),
                    non_identity_encoding=non_identity,
                )

            return TransportResult(
                http_status=exc.code,
                headers=headers_subset,
                raw_body=body_bytes,
                observed_bytes_lower_bound=len(body_bytes),
                body_too_large=False,
                is_redirect=(300 <= exc.code < 400),
                non_identity_encoding=non_identity,
            )

        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)) or "timed out" in str(exc.reason):
                return TransportResult(
                    http_status=None,
                    headers={
                        "content-type": None,
                        "content-length": None,
                        "content-encoding": None,
                        "date": None,
                        "retry-after": None,
                    },
                    raw_body=None,
                    observed_bytes_lower_bound=0,
                    is_timeout=True,
                )
            return TransportResult(
                http_status=None,
                headers={
                    "content-type": None,
                    "content-length": None,
                    "content-encoding": None,
                    "date": None,
                    "retry-after": None,
                },
                raw_body=None,
                observed_bytes_lower_bound=0,
                transport_error=True,
            )
        except (socket.timeout, TimeoutError):
            return TransportResult(
                http_status=None,
                headers={
                    "content-type": None,
                    "content-length": None,
                    "content-encoding": None,
                    "date": None,
                    "retry-after": None,
                },
                raw_body=None,
                observed_bytes_lower_bound=0,
                is_timeout=True,
            )
        except Exception:
            return TransportResult(
                http_status=None,
                headers={
                    "content-type": None,
                    "content-length": None,
                    "content-encoding": None,
                    "date": None,
                    "retry-after": None,
                },
                raw_body=None,
                observed_bytes_lower_bound=0,
                transport_error=True,
            )
