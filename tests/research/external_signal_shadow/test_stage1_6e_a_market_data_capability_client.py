import io
import urllib.error
import urllib.request

from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_models import (
    PROFILE_CORES,
)


class DummyHTTPResponse:
    def __init__(self, status: int, body: bytes, headers: dict[str, str] | None = None):
        self.status = status
        self.code = status
        self._body_io = io.BytesIO(body)
        self.headers = headers or {}

    def read(self, amt: int | None = None) -> bytes:
        return self._body_io.read(amt)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockOpener:
    def __init__(self, handler):
        self.handler = handler
        self.call_count = 0
        self.last_request = None

    def open(self, req: urllib.request.Request, timeout: float = 10.0):
        self.call_count += 1
        self.last_request = req
        return self.handler(req, timeout)


def test_client_fetch_success_200():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]
    response_body = b'{"lastUpdateId":100,"E":1700000000100,"T":1700000000000,"bids":[],"asks":[]}'

    def handle(req, timeout):
        assert req.full_url == "https://fapi.binance.com/fapi/v1/depth?limit=100&symbol=BTCUSDT"
        assert req.get_method() == "GET"
        assert req.get_header("Accept-encoding") == "identity"
        assert req.data is None
        assert timeout == 10.0
        return DummyHTTPResponse(
            status=200,
            body=response_body,
            headers={"Content-Type": "application/json", "Date": "Mon, 31 Aug 2026 08:00:00 GMT"},
        )

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert opener.call_count == 1
    assert res.http_status == 200
    assert res.raw_body == response_body
    assert res.observed_bytes_lower_bound == len(response_body)
    assert res.is_timeout is False
    assert res.transport_error is False
    assert res.body_too_large is False
    assert res.is_redirect is False
    assert res.non_identity_encoding is False
    assert res.headers["content-type"] == "application/json"
    assert res.headers["date"] == "Mon, 31 Aug 2026 08:00:00 GMT"
    assert res.headers["content-encoding"] is None


def test_client_fetch_timeout():
    import socket

    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]

    def handle(req, timeout):
        raise urllib.error.URLError(socket.timeout("timed out"))

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert res.is_timeout is True
    assert res.raw_body is None
    assert res.observed_bytes_lower_bound == 0


def test_client_fetch_transport_error():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]

    def handle(req, timeout):
        raise urllib.error.URLError("Connection refused")

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert res.transport_error is True
    assert res.raw_body is None
    assert res.observed_bytes_lower_bound == 0


def test_client_fetch_http_429():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]
    error_body = b'{"code":-1003,"msg":"Too much request weight"}'

    def handle(req, timeout):
        fp = io.BytesIO(error_body)
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=429,
            msg="Too Many Requests",
            hdrs={"Retry-After": "60", "Content-Type": "application/json"},
            fp=fp,
        )

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert res.http_status == 429
    assert res.raw_body == error_body
    assert res.observed_bytes_lower_bound == len(error_body)
    assert res.headers["retry-after"] == "60"


def test_client_fetch_body_too_large():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]
    oversized = b"x" * 2_000_005

    def handle(req, timeout):
        return DummyHTTPResponse(status=200, body=oversized)

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert res.body_too_large is True
    assert res.raw_body is None
    assert res.observed_bytes_lower_bound >= 2_000_001


def test_client_fetch_non_identity_encoding():
    from src.research.external_signal_shadow.stage1_6e_a_market_data_capability_client import (
        Stage16EACapabilityClient,
    )

    core = PROFILE_CORES["binance_usdm_rest_depth_v1"]

    def handle(req, timeout):
        return DummyHTTPResponse(
            status=200,
            body=b"fake gzip bytes",
            headers={"Content-Encoding": "gzip"},
        )

    opener = MockOpener(handle)
    client = Stage16EACapabilityClient(opener=opener)
    res = client.fetch(core, request_seq=1)

    assert res.non_identity_encoding is True
    assert res.raw_body == b"fake gzip bytes"
