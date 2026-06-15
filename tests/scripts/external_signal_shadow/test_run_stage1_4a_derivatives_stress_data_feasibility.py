"""
tests/scripts/external_signal_shadow/test_run_stage1_4a_derivatives_stress_data_feasibility.py
"""

import json
import urllib.error
from unittest.mock import patch

import pytest

from scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility import main


@pytest.fixture(autouse=True)
def mock_sleep():
    with patch("time.sleep", return_value=None):
        yield



def test_cli_rejects_fixture_and_live_flag_together(tmp_path):
    output = tmp_path / "summary.json"
    rc = main(["--fixture-summary-input", "some_path.json", "--live-public-readonly", "--output-summary", str(output)])
    assert rc == 1


def test_cli_requires_live_fixture_or_local_archive(tmp_path):
    output = tmp_path / "summary.json"
    # Neither live, nor fixture, nor local archive -> outcome should be stage1_4_data_unavailable
    rc = main(["--output-summary", str(output)])
    assert rc == 0
    assert output.exists()

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["outcome"] == "stage1_4_data_unavailable"
    assert summary["primary_blocker"] == "insufficient_usable_symbols"


def test_cli_fixture_summary_round_trip_marks_research_invalid(tmp_path):
    fixture_input = tmp_path / "fixture_input.json"
    fixture_input.write_text(json.dumps({
        "fixture_run": False,  # intentionally False to test overwrite
        "research_result_valid": True,  # intentionally True to test overwrite
    }), encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--fixture-summary-input", str(fixture_input), "--output-summary", str(output)])
    assert rc == 0
    assert output.exists()

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["fixture_run"] is True
    assert summary["research_result_valid"] is False
    assert summary["outcome"] == "stage1_4_data_degraded"


def test_cli_accepts_local_oi_archive_path(tmp_path):
    archive_dir = tmp_path / "oi_archive"
    archive_dir.mkdir()
    archive_file = archive_dir / "oi_data.jsonl"
    archive_file.write_text(json.dumps({
        "symbol": "BTCUSDT",
        "sumOpenInterest": "100.0",
        "sumOpenInterestValue": "1000.0",
        "timestamp": 0
    }) + "\n", encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--local-oi-archive", str(archive_file), "--output-summary", str(output)])
    assert rc == 0
    assert output.exists()

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["local_oi_archive_found"] is True


def test_cli_accepts_local_force_order_archive_path(tmp_path):
    archive_file = tmp_path / "force_orders.jsonl"
    archive_file.write_text(json.dumps({
        "symbol": "BTCUSDT",
        "side": "SELL",
        "price": 50000.0,
        "origQty": 1.0,
        "time": 0
    }) + "\n", encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--local-force-order-archive", str(archive_file), "--output-summary", str(output)])
    assert rc == 0
    assert output.exists()

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["local_force_order_archive_found"] is True


def test_cli_parses_self_collected_websocket_force_order_schema(tmp_path):
    archive_file = tmp_path / "force_orders.jsonl"
    archive_file.write_text(json.dumps({
        "symbol": "BTC/USDT",
        "side": "SELL",
        "price": 73856.2,
        "quantity": 0.029,
        "trade_time_ms": 1780218438514,
    }) + "\n", encoding="utf-8")

    output = tmp_path / "summary.json"
    rc = main(["--local-force-order-archive", str(archive_file), "--output-summary", str(output)])
    assert rc == 0
    assert output.exists()

    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["local_force_order_archive_found"] is True
    assert summary["liquidation_unknown_schema_count"] == 0



def test_live_public_readonly_path_does_not_read_env(tmp_path, monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "LEAK_CHECK")
    monkeypatch.setenv("BINANCE_SECRET", "SECRET_LEAK_CHECK")

    output = tmp_path / "summary.json"
    # Patch urlopen to raise error to exit safely without actually connecting to public internet
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network offline mock")):
        rc = main(["--live-public-readonly", "--output-summary", str(output)])
        assert rc == 0

    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "LEAK_CHECK" not in text
    assert "SECRET_LEAK_CHECK" not in text
    assert json.loads(text).get("live_trading_allowed", False) is False


def test_live_probe_network_error_writes_failure_summary(tmp_path):
    output = tmp_path / "summary.json"
    # Force URLError to simulate offline/network error
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("mock network error")):
        rc = main(["--live-public-readonly", "--output-summary", str(output)])
        assert rc == 0

    assert output.exists()
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["outcome"] == "stage1_4_data_unavailable"
    assert summary["primary_blocker"] == "network_probe_error"
    assert "mock network error" in summary["failure_reason"]
    assert summary["usable"] is False


def test_live_manifest_probe_uses_binance_vision_cm_path(tmp_path):
    output = tmp_path / "summary.json"
    probed_urls = []

    def fake_head(url):
        probed_urls.append(url)
        return False

    with (
        patch(
            "scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get",
            return_value=b"[]",
        ),
        patch(
            "scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_head",
            side_effect=fake_head,
        ),
    ):
        rc = main(["--live-public-readonly", "--output-summary", str(output)])

    assert rc == 0
    assert any("/data/futures/cm/daily/liquidationSnapshot/" in url for url in probed_urls)
    assert all("/data/futures/coinM/" not in url for url in probed_urls)


def test_live_manifest_probe_does_not_inject_synthetic_liquidation_row(tmp_path):
    output = tmp_path / "summary.json"

    with (
        patch(
            "scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get",
            return_value=b"[]",
        ),
        patch(
            "scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_head",
            return_value=True,
        ),
    ):
        rc = main(["--live-public-readonly", "--output-summary", str(output)])

    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    btc_liquidation = summary["symbol_audits"]["BTCUSDT"]["liquidation"]
    assert btc_liquidation["liquidation_field_coverage_ratio"] == 0.0
    assert btc_liquidation["liquidation_nonzero_window_count"] == 0


def test_live_funding_probe_paginates_requested_history(tmp_path):
    from scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility import (
        fetch_funding_history_pages,
    )

    # Mock safe_http_get to return paginated funding pages
    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        # return dummy page 1 or page 2
        if "startTime=1000" in url:
            return b'[{"symbol": "BTCUSDT", "fundingRate": "0.001", "fundingTime": 2000}]'
        elif "startTime=2001" in url:
            return b"[]"
        return b"[]"

    with patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get", side_effect=fake_get):
        res = fetch_funding_history_pages("BTCUSDT", start_ms=1000, end_ms=5000)

    assert len(res) == 1
    assert res[0]["fundingTime"] == 2000
    assert any("startTime=1000" in u for u in requested_urls)


def test_funding_pagination_dedupes_and_stops_on_stall():
    from scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility import (
        fetch_funding_history_pages,
    )

    calls = 0
    def fake_get(url):
        nonlocal calls
        calls += 1
        # Repeatedly return same record to simulate a stall (startTime doesn't advance)
        return b'[{"symbol": "BTCUSDT", "fundingRate": "0.001", "fundingTime": 1000}]'

    with patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get", side_effect=fake_get):
        res = fetch_funding_history_pages("BTCUSDT", start_ms=1000, end_ms=5000)

    # Should stop on stall (since fundingTime + 1 is 1001, but next query gets fundingTime=1000 which is <= 1001)
    # Actually if it gets 1000, max fundingTime is 1000. Next start will be 1001. If next query returns 1000, next_start <= current_start (1001 <= 1001).
    assert len(res) == 1
    assert calls <= 3


def test_funding_pagination_filters_records_after_end_ms():
    from scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility import (
        fetch_funding_history_pages,
    )

    def fake_get(url):
        return b'[{"symbol": "BTCUSDT", "fundingRate": "0.001", "fundingTime": 2000}, {"symbol": "BTCUSDT", "fundingRate": "0.001", "fundingTime": 6000}]'

    with patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get", side_effect=fake_get):
        res = fetch_funding_history_pages("BTCUSDT", start_ms=1000, end_ms=5000)

    # 6000 is > end_ms (5000) and must be filtered out
    assert len(res) == 1
    assert res[0]["fundingTime"] == 2000


def test_live_futures_kline_probe_paginates_requested_history(tmp_path):
    from scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility import (
        fetch_futures_kline_pages,
    )

    requested_urls = []

    def fake_get(url):
        requested_urls.append(url)
        if "startTime=1000" in url:
            # 15m kline row (open_time, open, high, low, close, volume, close_time, quote_asset_volume, ...)
            return b'[[2000, "50000", "51000", "49000", "50500", "100", 2899999, "5000000", 10, "10", "10", "10"]]'
        return b"[]"

    with patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get", side_effect=fake_get):
        res = fetch_futures_kline_pages("BTCUSDT", start_ms=1000, end_ms=5000)

    assert len(res) == 1
    assert res[0][0] == 2000


def test_liquidation_manifest_audit_reports_available_days_by_symbol(tmp_path):
    output = tmp_path / "summary.json"

    # Mock HEAD for BTCUSD_PERP: available on 2 of 3 requested dates
    call_count = 0
    def fake_head(url):
        nonlocal call_count
        call_count += 1
        # Let's say it returns True for the first 2 calls, False for others
        return call_count <= 2

    # Override REAL_AUDIT_HISTORY_DAYS to 3 to keep it fast
    with (
        patch("configs.base.EXTERNAL_SIGNAL_STAGE1_4_REAL_AUDIT_HISTORY_DAYS", 3),
        patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_get", return_value=b"[]"),
        patch("scripts.external_signal_shadow.run_stage1_4a_derivatives_stress_data_feasibility.safe_http_head", side_effect=fake_head),
    ):
        rc = main(["--live-public-readonly", "--output-summary", str(output)])

    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))

    # We requested 3 days
    assert summary["liquidation_manifest_requested_days"] == 3
    # First symbol probed is BTCUSDT (CM maps to BTCUSD_PERP). The fake_head returned True twice.
    # Because there are 5 symbols in the whitelist, and the date loop is inside the symbols loop,
    # the first symbol BTCUSDT gets the first 3 date HEAD calls. The first 2 calls return True, 3rd returns False.
    # So avail_count for BTCUSDT should be 2.
    assert summary["liquidation_manifest_available_days_by_symbol"]["BTCUSDT"] == 2
    assert summary["liquidation_manifest_coverage_ratio_by_symbol"]["BTCUSDT"] == pytest.approx(2 / 3)


