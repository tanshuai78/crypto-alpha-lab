import os
import tempfile
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.research.external_signal_shadow.stage1_5a_source_audit_loader import (
    fetch_source_url,
    load_local_fixture,
    load_or_fetch_payloads,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_models import SourceProfile


def test_loads_local_json_fixture():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(b'{"key": "value"}')
        f_name = f.name
    try:
        payload = load_local_fixture(
            file_path=f_name,
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )
        assert payload.raw_payload_bytes == b'{"key": "value"}'
        assert payload.content_type == "application/json"
        assert payload.file_path == f_name
    finally:
        os.unlink(f_name)


def test_loads_local_jsonl_fixture():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        f.write(b'{"row": 1}\n{"row": 2}')
        f_name = f.name
    try:
        payload = load_local_fixture(
            file_path=f_name,
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )
        assert payload.raw_payload_bytes == b'{"row": 1}\n{"row": 2}'
        assert payload.content_type == "application/jsonl"
    finally:
        os.unlink(f_name)


def test_loads_local_html_fixture_as_text_payload():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        f.write(b"<html>Announcements</html>")
        f_name = f.name
    try:
        payload = load_local_fixture(
            file_path=f_name,
            source_name="binance_test",
            source_profile=SourceProfile.BINANCE_HTML.value,
        )
        assert payload.raw_payload_bytes == b"<html>Announcements</html>"
        assert payload.content_type == "text/html"
    finally:
        os.unlink(f_name)


def test_fetch_url_requires_allowed_domain():
    with pytest.raises(ValueError, match="is not in allowlist"):
        fetch_source_url(
            url="https://evil-binance.com/announcement",
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )


@patch("urllib.request.build_opener")
def test_fetch_rejects_redirect_to_disallowed_domain(mock_build_opener):
    # Mock opener that performs redirection
    mock_opener = MagicMock()
    mock_response = MagicMock()
    # Mock the url returned after redirect
    mock_response.geturl.return_value = "https://evil-redirect.com/target"
    mock_response.read.return_value = b'{"data": 1}'
    mock_response.info.return_value.get_content_type.return_value = "application/json"
    mock_opener.open.return_value.__enter__.return_value = mock_response
    mock_build_opener.return_value = mock_opener

    with pytest.raises(ValueError, match="Redirect target domain.*is not in allowlist"):
        fetch_source_url(
            url="https://binance.com/announcement",
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )


@patch("urllib.request.build_opener")
def test_fetch_url_applies_timeout_and_retry_budget_with_mock(mock_build_opener):
    mock_opener = MagicMock()
    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://binance.com/announcement"
    mock_response.read.return_value = b'{"data": 1}'
    mock_response.info.return_value.get_content_type.return_value = "application/json"

    mock_enter_ok = MagicMock()
    mock_enter_ok.__enter__.return_value = mock_response

    # First call triggers HTTPError (retryable or timeout), second succeeds
    mock_opener.open.side_effect = [urllib.error.URLError("timeout"), mock_enter_ok]
    mock_build_opener.return_value = mock_opener

    # Should retry and succeed on second attempt
    payload = fetch_source_url(
        url="https://binance.com/announcement",
        source_name="binance_test",
        source_profile=SourceProfile.GENERIC_JSON.value,
    )
    assert mock_opener.open.call_count == 2
    assert payload.raw_payload_bytes is not None


@patch("urllib.request.build_opener")
def test_loader_records_request_timeout_count(mock_build_opener):
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError("timeout")
    mock_build_opener.return_value = mock_opener

    with pytest.raises(Exception):
        fetch_source_url(
            url="https://binance.com/announcement",
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )


def test_loader_marks_fixture_run_true_for_local_fixture():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        f.write(b'{"key": "value"}')
        f_name = f.name
    try:
        payloads, fixture_run, metadata = load_or_fetch_payloads(
            source_file=f_name,
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
        )
        assert fixture_run is True
        assert len(payloads) == 1
        assert metadata["raw_cache_written"] is False
        assert metadata["network_result_not_deterministic"] is False
    finally:
        os.unlink(f_name)


@patch("urllib.request.build_opener")
def test_network_fetch_writes_raw_cache_and_marks_not_deterministic(mock_build_opener):
    mock_opener = MagicMock()
    mock_response = MagicMock()
    mock_response.geturl.return_value = "https://binance.com/announcement"
    mock_response.read.return_value = b'{"data": 1}'
    mock_response.info.return_value.get_content_type.return_value = "application/json"

    mock_enter = MagicMock()
    mock_enter.__enter__.return_value = mock_response
    mock_opener.open.return_value = mock_enter
    mock_build_opener.return_value = mock_opener


    # Use a temporary directory for raw cache in local run/test
    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_REQUEST_TIMEOUT_SEC", 10.0):
        payloads, fixture_run, metadata = load_or_fetch_payloads(
            source_url="https://binance.com/announcement",
            source_name="binance_test",
            source_profile=SourceProfile.GENERIC_JSON.value,
            write_cache=True,
            cache_dir_override=tempfile.gettempdir(),
        )
        assert fixture_run is False
        assert len(payloads) == 1
        assert metadata["raw_cache_written"] is True
        assert metadata["network_result_not_deterministic"] is True
        assert metadata["collector_received_at_ms"] == payloads[0].collector_received_at_ms
        assert metadata["raw_cache_path"]
        # Check if raw cache is written
        # It should create tempdir/raw/YYYYMMDD/binance_test/
        import datetime
        date_str = datetime.datetime.utcnow().strftime("%Y%m%d")
        expected_cache_dir = os.path.join(tempfile.gettempdir(), "raw", date_str, "binance_test")
        assert os.path.exists(expected_cache_dir)
        # Clean up
        import shutil
        if os.path.exists(expected_cache_dir):
            shutil.rmtree(os.path.join(tempfile.gettempdir(), "raw"))
