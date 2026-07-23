import json
import time
from unittest.mock import patch
from configs import base

from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import main


def _write_valid_upstream(tmp_path):
    c1 = tmp_path / "c1.json"
    c = tmp_path / "c.json"
    c1.write_text(json.dumps({
        "decision": "stage1_5c1_price_coverage_ready_for_1_5c_rerun",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    c.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": ["futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    return c1, c


def test_runner_requires_live_flag_without_fixture(tmp_path):
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--output-root", str(output_root),
        "--output-summary", str(summary),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 2
    s = json.loads(summary.read_text())
    assert s["decision"] == "stage1_5d_smoke_invalid"
    assert "missing_live_flag_or_fixture" in s["blockers"]


def test_runner_fixture_zero_event_operational_pass(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({"data": {"catalogs": [{"articles": []}]}}))
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["decision"] == "stage1_5d_smoke_observation_in_progress"
    assert s["fixture_run"] is True
    assert s["research_result_valid"] is False
    assert s["event_detection_validated"] is False
    assert (output_root / "heartbeats").exists()


def test_runner_dedupes_repeated_fixture_polls_and_splits_counts(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "data": {
            "catalogs": [{
                "articles": [
                    {
                        "code": "abc",
                        "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                        "releaseDate": int(time.time() * 1000) - 1000,
                    },
                    {
                        "code": "tradfi",
                        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                        "releaseDate": int(time.time() * 1000) - 1000,
                    },
                ]
            }]
        }
    }))
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "0",
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["raw_futures_launch_article_count"] == 4
    assert s["symbol_parsed_event_count"] == 2
    # pending_retry rows remain in-memory and are not written to events stream
    assert s["symbol_parse_failed_count"] == 0
    assert s["deduped_new_event_count"] == 1
    assert s["new_futures_launch_event_count"] == 1
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    assert len(event_files[0].read_text().strip().splitlines()) == 1
    heartbeat = json.loads(next((output_root / "heartbeats").glob("*.jsonl")).read_text().strip().splitlines()[-1])
    assert heartbeat["configured_poll_interval_sec"] == 0
    assert "actual_poll_interval_sec" in heartbeat
    assert "poll_schedule_drift_ms" in heartbeat


def test_runner_live_first_bar_writes_exchangeinfo_manifest(tmp_path):
    fixture_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "abc",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }
    exchange_info = {"symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}]}
    klines = [[9999999999999, "1", "1", "1", "1", "1"]]

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": fixture_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "klines" in url:
            return {"ok": True, "payload": klines, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "live_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]
    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
        with patch("sys.argv", args):
            rc = main()
    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["decision"] == "stage1_5d_event_detection_passed"
    manifest_lines = next((output_root / "request_manifest").glob("*.jsonl")).read_text().splitlines()
    manifest_rows = [json.loads(line) for line in manifest_lines]
    assert any(row["source_type"] == "exchangeInfo" for row in manifest_rows)
    assert any(row["source_type"] == "klines" for row in manifest_rows)


def test_detail_fetch_transient_failure_does_not_permanently_dedup_article(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    calls = {"detail": 0}

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/tradfi" in url:
            calls["detail"] += 1
            if calls["detail"] == 1:
                return {"ok": False, "payload": None, "final_url": url, "http_status": 503, "error": "temporary"}
            return {
                "ok": True,
                "payload": {"data": {"body": "AMDUSDT QCOMUSDT"}},
                "final_url": url,
                "http_status": 200,
                "error": None
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "retry_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        res = fake_fetch(url, live_public_readonly, timeout_sec, retry_budget)
        if res["ok"] and isinstance(res["payload"], dict):
            res["payload"] = json.dumps(res["payload"])
        return res

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                    with patch("sys.argv", args):
                        rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_failed_count"] >= 1
    assert s["detail_fetch_success_count"] >= 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert "AMDUSDT" in events[0]["symbols"]
    assert "QCOMUSDT" in events[0]["symbols"]


def test_detail_max_age_expired_marks_terminal_failed(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/tradfi" in url:
            return {"ok": False, "payload": None, "final_url": url, "http_status": 400, "error": "persistent_error"}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "max_age_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "2",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        res = fake_fetch(url, live_public_readonly, timeout_sec, retry_budget)
        if res["ok"] and isinstance(res["payload"], dict):
            res["payload"] = json.dumps(res["payload"])
        return res

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["symbols"] == []
    assert events[0]["symbol_parse_status"] == "terminal_failed"
    assert events[0]["symbol_parse_failed_reason"] in {"detail_retry_max_age_exceeded", "detail_retry_exhausted"}
    assert s["detail_symbol_parse_failed_count"] >= 1


def test_detail_budget_deferred_retries_next_poll(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [
                    {
                        "code": "tradfi1",
                        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                        "releaseDate": 1710000000000,
                    },
                    {
                        "code": "tradfi2",
                        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                        "releaseDate": 1710000000001,
                    }
                ]
            }]
        }
    }

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/tradfi1" in url:
            return {
                "ok": True,
                "payload": {"data": {"body": "AAPLUSDT"}},
                "final_url": url,
                "http_status": 200,
                "error": None
            }
        if "/support/announcement/tradfi2" in url:
            return {
                "ok": True,
                "payload": {"data": {"body": "MSFTUSDT"}},
                "final_url": url,
                "http_status": 200,
                "error": None
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "budget_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        res = fake_fetch(url, live_public_readonly, timeout_sec, retry_budget)
        if res["ok"] and isinstance(res["payload"], dict):
            res["payload"] = json.dumps(res["payload"])
        return res

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_budget_deferred_count"] >= 1
    assert s["detail_fetch_success_count"] == 2

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 2
    symbols_found = {sym for ev in events for sym in ev["symbols"]}
    assert "AAPLUSDT" in symbols_found
    assert "MSFTUSDT" in symbols_found


def test_detail_request_manifest_and_payload_are_written(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/tradfi" in url:
            return {
                "ok": True,
                "payload": {"data": {"body": "AMDUSDT"}},
                "final_url": url,
                "http_status": 200,
                "error": None
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "manifest_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        res = fake_fetch(url, live_public_readonly, timeout_sec, retry_budget)
        if res["ok"] and isinstance(res["payload"], dict):
            res["payload"] = json.dumps(res["payload"])
        return res

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    assert len(manifest_files) == 1
    manifest_rows = [json.loads(line) for line in manifest_files[0].read_text().strip().splitlines()]

    detail_row = next((r for r in manifest_rows if r.get("source_type") == "announcement_detail"), None)
    assert detail_row is not None
    assert "payload_sha256" in detail_row
    assert detail_row["payload_size_bytes"] > 0
    assert detail_row["parser_version"] == "stage1_5d_symbol_extraction_v2"
    assert detail_row["symbol_extraction_version"] == 2

    payload_file = output_root / detail_row["payload_path"]
    assert payload_file.exists()
    payload_content = json.loads(payload_file.read_text())
    assert "AMDUSDT" in str(payload_content)


def test_detail_url_missing_marks_url_missing_without_crash(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "url_missing_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json") as mock_fetch:
        mock_fetch.return_value = {"ok": True, "payload": list_payload, "final_url": "https://www.binance.com/cms", "http_status": 200, "error": None}
        with patch("sys.argv", args):
            rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_url_rejected_count"] >= 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["detail_fetch_status"] == "url_missing"
    assert events[0]["symbol_parse_status"] == "terminal_failed"


def test_detail_url_not_allowlisted_marks_terminal_failed_without_network(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "evil_path",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "url_not_allowlisted_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json") as mock_fetch:
        mock_fetch.return_value = {"ok": True, "payload": list_payload, "final_url": "https://www.binance.com/cms", "http_status": 200, "error": None}
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.validate_announcement_detail_url", side_effect=ValueError("domain_not_allowed")):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_url_rejected_count"] >= 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["detail_fetch_status"] == "url_not_allowlisted"
    assert events[0]["symbol_parse_status"] == "terminal_failed"


def test_detail_redirect_to_non_allowlisted_host_rejected(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/tradfi" in url:
            return {
                "ok": True,
                "payload": {"data": {"body": "AMDUSDT"}},
                "final_url": "https://evil.com/redirected",
                "http_status": 200,
                "error": None
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "redirect_reject_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        res = fake_fetch(url, live_public_readonly, timeout_sec, retry_budget)
        if res["ok"] and isinstance(res["payload"], dict):
            res["payload"] = json.dumps(res["payload"])
        return res

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_url_rejected_count"] >= 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["detail_fetch_status"] == "final_url_not_allowlisted"
    assert events[0]["symbol_parse_status"] == "terminal_failed"


def test_runner_fixture_detail_payload_extracts_multiple_tradfi_symbols_without_network(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                    "detailPayload": {
                        "body": "AMDUSDT QCOMUSDT USARUSDT"
                    }
                }]
            }]
        }
    }))

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_detail_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("sys.argv", args):
        rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_symbol_extracted_count"] == 1
    assert s["detail_fetch_success_count"] == 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["symbols"] == ["AMDUSDT", "QCOMUSDT", "USARUSDT"]
    assert events[0]["symbol_extraction_source"] == "detail"

    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    assert len(manifest_files) == 1
    manifest_rows = [json.loads(line) for line in manifest_files[0].read_text().strip().splitlines()]
    detail_row = next((r for r in manifest_rows if r.get("source_type") == "fixture_detail"), None)
    assert detail_row is not None
    assert "payload_sha256" in detail_row


def test_base_asset_derived_symbol_requires_exchange_info_validation(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"}
    ]}

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "ex_info_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "payload_size_bytes": len(detail_payload), "error": None}
        raise AssertionError(url)

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_symbol_extracted_count"] == 1
    assert s["detail_fetch_success_count"] == 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["symbols"] == ["BTCU", "ETHU"]
    assert events[0]["symbol_extraction_source"] == "detail_contract_symbol"
    assert events[0]["symbol_derivation_method"] == "none"
    assert events[0]["quote_derivation_source"] == "exchange_info"
    assert events[0]["symbol_validation_status"] == "validated"
    assert events[0]["symbol_parse_status"] == "parsed"


def test_base_asset_derived_symbol_not_emitted_when_exchange_info_missing(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": []}  # empty exchangeInfo

    def fake_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "ex_info_missing_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "2",
    ]

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "payload_size_bytes": len(detail_payload), "error": None}
        raise AssertionError(url)

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    json.loads(summary.read_text())

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["symbols"] == []
    assert events[0]["symbol_validation_status"] == "rejected"
    assert events[0]["symbol_parse_status"] == "terminal_failed"


def test_runner_live_detail_html_payload_extracts_base_asset_symbols(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_html = "<html><body>Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts.</body></html>"
    exchange_info = {"symbols": [
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"}
    ]}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_html, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "html_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_symbol_extracted_count"] == 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["symbols"] == ["BTCU", "ETHU"]

    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    assert len(manifest_files) == 1
    manifest_rows = [json.loads(line) for line in manifest_files[0].read_text().strip().splitlines()]
    detail_row = next((r for r in manifest_rows if r.get("source_type") == "announcement_detail" and r.get("detail_fetch_variant") != "bapi_article_detail_query"), None)
    assert detail_row is not None
    assert detail_row["payload_path"].endswith(".html")



def test_announcement_list_fetch_still_uses_fetch_public_json_not_raw_payload(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-01)",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"}
    ]}

    calls = {"fetch_json": 0, "fetch_payload": 0}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        calls["fetch_json"] += 1
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        calls["fetch_payload"] += 1
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "isolation_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    assert calls["fetch_json"] == 3  # 1 list query, 1 exchangeInfo, 1 klines
    assert calls["fetch_payload"] == 1  # 1 detail page fetch


def test_detail_retry_success_preserves_first_detected_at_ms(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    calls = {"detail": 0}
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        calls["detail"] += 1
        if calls["detail"] == 1:
            return {"ok": False, "payload": None, "final_url": url, "http_status": 503, "error": "temporary"}
        return {"ok": True, "payload": "AMDUSDT and NVDAUSDT Perpetual Contracts.", "final_url": url, "http_status": 200, "error": None}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "timestamp_retry_success_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "1",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                    with patch("sys.argv", args):
                        rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    # Check that first_detected_at_ms is preserved
    assert events[0]["detected_at_ms"] == events[0]["first_detected_at_ms"]
    assert "detail_fetched_at_ms" in events[0]
    assert events[0]["detail_fetched_at_ms"] is not None
    assert events[0]["symbol_resolved_at_ms"] >= events[0]["detail_fetched_at_ms"]
    assert events[0]["symbol_resolution_latency_ms"] >= 0


def test_detail_terminal_failed_paths_preserve_first_detected_at_ms(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "final_url": url, "http_status": 400, "error": "persistent_error"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "timestamp_failed_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "2",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert events[0]["detected_at_ms"] == events[0]["first_detected_at_ms"]


def test_failed_detail_request_writes_manifest_error_row(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "final_url": url, "http_status": 503, "error": "temporary"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "failed_manifest_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    assert len(manifest_files) == 1
    manifest_rows = [json.loads(line) for line in manifest_files[0].read_text().strip().splitlines()]

    detail_row = next((r for r in manifest_rows if r.get("source_type") == "announcement_detail"), None)
    assert detail_row is not None
    assert detail_row["http_status"] == 503
    assert detail_row["error"] == "temporary"
    assert detail_row["payload_size_bytes"] == 0


def test_runner_observed_btcu_ethu_launch_emits_event_symbols_from_base_asset_detail(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"}
    ]}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "observed_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    s = json.loads(summary.read_text())
    assert s["detail_fetch_attempted_count"] >= 1
    assert s["detail_symbol_extracted_count"] == 1

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    ev = events[0]

    assert "BTCU" in ev["symbols"]
    assert "ETHU" in ev["symbols"]
    assert ev["symbol_extraction_source"] == "detail_contract_symbol"
    assert ev["symbol_derivation_method"] == "none"
    assert ev["quote_derivation_source"] == "exchange_info"
    assert ev["symbol_validation_status"] == "validated"
    assert ev["symbol_parse_status"] == "parsed"
    assert ev["trade_signal_allowed"] is False

    # Event ID stability check:
    first_id = ev["event_id"]

    # Run again with same config, check stable ID
    summary2 = tmp_path / "summary2.json"
    output_root2 = tmp_path / "observed_smoke2"
    args2 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root2),
        "--output-summary", str(summary2),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]
    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args2):
                rc2 = main()
    assert rc2 == 0
    event_files2 = list((output_root2 / "events").glob("*.jsonl"))
    events2 = [json.loads(line) for line in event_files2[0].read_text().strip().splitlines()]
    assert events2[0]["event_id"] == first_id


def test_fixture_base_asset_derived_validation_never_calls_network_without_live_flag(tmp_path):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                    "detailPayload": "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts.",
                }]
            }]
        }
    }))
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_base_derived_no_network"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json") as mock_fetch_json:
        with patch("sys.argv", args):
            rc = main()

    assert rc == 0
    mock_fetch_json.assert_not_called()
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert event_files == []


def test_persisted_base_asset_events_never_emit_unverified_validation_status(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U"},
    ]}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "klines" in url:
            return {"ok": False, "payload": None, "final_url": url, "http_status": 503, "error": "skip_first_bar"}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "persisted_no_unverified"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    persisted_events = [
        json.loads(line)
        for path in event_files
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    assert persisted_events
    assert all(ev.get("symbol_validation_status") != "unverified" for ev in persisted_events)


def test_exchangeinfo_validation_accepts_trading_u_settled_perpetual_symbols():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    exchangeinfo_by_symbol = {
        "BTCU": {
            "symbol": "BTCU",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "U",
            "marginAsset": "U",
            "onboardDate": 1782896400000,
        },
        "ETHU": {
            "symbol": "ETHU",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "U",
            "marginAsset": "U",
            "onboardDate": 1782900000000,
        },
    }

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU", "ETHU"],
        exchangeinfo_by_symbol=exchangeinfo_by_symbol,
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == ["BTCU", "ETHU"]
    assert result["pending_symbols"] == []
    assert result["rejected_symbols"] == []
    assert result["symbol_onboard_times_ms"] == {"BTCU": 1782896400000, "ETHU": 1782900000000}
    assert result["symbol_exchangeinfo"]["BTCU"]["quoteAsset"] == "U"


def test_exchangeinfo_validation_does_not_rewrite_raw_contract_candidate_to_usdt_suffix():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={
            "BTCUUSDT": {
                "symbol": "BTCUUSDT",
                "contractType": "PERPETUAL",
                "status": "TRADING",
                "quoteAsset": "USDT",
                "marginAsset": "USDT",
                "onboardDate": 1782896400000,
            }
        },
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["pending_symbols"] == ["BTCU"]
    assert result["pending_reasons"]["BTCU"] == "exchange_info_symbol_missing"


def test_exchangeinfo_validation_rejects_non_perpetual_contract():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "CURRENT_QUARTER", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U"}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_disallowed_contract_type"


def test_exchangeinfo_validation_rejects_disallowed_margin_asset():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "BUSD"}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_disallowed_margin_asset"


def test_exchangeinfo_validation_does_not_accept_symbol_string_only_without_metadata():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782896400000,
    )

    assert result["validated_symbols"] == []
    assert result["rejected_symbols"] == ["BTCU"]
    assert result["rejection_reasons"]["BTCU"] == "exchange_info_incomplete_metadata"


def test_candidate_symbol_present_but_status_pending_does_not_emit_before_onboard_plus_grace():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_candidate_symbols_against_exchangeinfo,
    )

    result = validate_candidate_symbols_against_exchangeinfo(
        candidates=["BTCU"],
        exchangeinfo_by_symbol={"BTCU": {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "PRE_TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000}},
        allowed_margin_assets=("USDT", "USDC", "U"),
        allowed_quote_assets=("USDT", "USDC", "U"),
        allowed_contract_types=("PERPETUAL",),
        validatable_statuses=("TRADING", "PENDING_TRADING", "PRE_TRADING"),
        emittable_statuses=("TRADING",),
        now_ms=1782892800000,
    )

    assert result["validated_symbols"] == []
    assert result["pending_symbols"] == ["BTCU"]
    assert result["pending_reasons"]["BTCU"] == "exchange_info_symbol_status_not_trading_prelaunch"


def test_rejected_candidate_validation_emits_terminal_diagnostic_event(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "25da4614ffff435fa28544b27fd33a39",
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU Perpetual Contract (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU Perpetual Contract."
    exchange_info = {
        "symbols": [{
            "symbol": "BTCU",
            "status": "TRADING",
            "contractType": "CURRENT_QUARTER",
            "quoteAsset": "U",
            "marginAsset": "U",
        }]
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        if "/support/announcement/25da4614" in url:
            return {"ok": True, "payload": detail_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "rejected_candidate_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().splitlines() if line.strip()]
    assert len(events) == 1
    assert events[0]["symbols"] == []
    assert events[0]["symbol_validation_status"] == "rejected"
    assert events[0]["symbol_parse_status"] == "terminal_failed"
    assert events[0]["symbol_parse_failed_reason"] == "exchange_info_disallowed_contract_type"


def test_effective_launch_time_prefers_exchangeinfo_onboard_date_over_detail_time():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_effective_launch_times_ms,
    )

    result = build_effective_launch_times_ms(
        candidate_symbols=["BTCU"],
        symbol_onboard_times_ms={"BTCU": 1782896400000},
        symbol_launch_times_ms={"BTCU": 1782892800000},
        source_published_at_ms=1782830702782,
        first_detected_at_ms=1782889542209,
    )

    assert result["symbol_effective_launch_times_ms"] == {"BTCU": 1782896400000}
    assert result["launch_time_source"] == "exchange_info"


def test_effective_launch_time_falls_back_to_detail_when_onboard_missing():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_effective_launch_times_ms,
    )

    result = build_effective_launch_times_ms(
        candidate_symbols=["BTCU"],
        symbol_onboard_times_ms={},
        symbol_launch_times_ms={"BTCU": 1782896400000},
        source_published_at_ms=1782830702782,
        first_detected_at_ms=1782889542209,
    )

    assert result["symbol_effective_launch_times_ms"] == {"BTCU": 1782896400000}
    assert result["launch_time_source"] == "detail"


def test_fixture_mode_exchangeinfo_payload_enables_candidate_validation_without_network(tmp_path, monkeypatch):
    fixture_json_path = tmp_path / "fixture_with_exchangeinfo.json"
    fixture = {
        "exchangeInfoPayload": {
            "symbols": [
                {"symbol": "BTCU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
                {"symbol": "ETHU", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000},
            ]
        },
        "data": {"catalogs": [{"articles": [{
            "code": "25da4614ffff435fa28544b27fd33a39",
            "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
            "releaseDate": 1782830702782,
            "detailPayload": "USDⓈ-M Perpetual Contract BTCU ETHU Settlement Asset U U",
        }]}]},
    }
    fixture_json_path.write_text(json.dumps(fixture))

    def fail_network(*args, **kwargs):
        raise AssertionError("fixture mode must not call live network")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fixture_smoke_u"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--fixture-json", str(fixture_json_path),
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("sys.argv", args):
        rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    persisted_events = [
        json.loads(line)
        for path in event_files
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    assert persisted_events
    assert persisted_events
    symbols_extracted = sorted(persisted_events[0]["symbols"])
    assert symbols_extracted == ["BTCU", "ETHU"]
    assert persisted_events[0]["symbol_validation_status"] == "validated"
    assert persisted_events[0]["symbol_parse_status"] == "parsed"


def _read_jsonl_files(directory):
    if not directory.exists():
        return []
    rows = []
    for path in sorted(directory.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def test_empty_detail_payload_keeps_article_pending_retry_without_terminal_event(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": 1782830702782,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, **kwargs):
        return {
            "ok": True,
            "payload": list_payload,
            "requested_url": url,
            "final_url": url,
            "http_status": 200,
            "payload_size_bytes": 100,
            "row_count": 1,
            "error": None,
        }

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "empty_detail_payload",
        }

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()


    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(
        row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
        for row in events
    )

    manifest = _read_jsonl_files(output_root / "request_manifest")
    empty_rows = [
        r for r in manifest
        if r.get("source_type") == "announcement_detail"
        and r.get("detail_fetch_variant") != "bapi_article_detail_query"
        and r.get("error") in ("empty_detail_payload", "detail_payload_http_status_202")
        and "d2acaa91c14e4cc598aaee1017efc1ac" in (r.get("url") or "")
    ]
    assert len(empty_rows) >= 1

    assert empty_rows[-1]["http_status"] == 202
    assert empty_rows[-1]["payload_size_bytes"] == 0
    assert empty_rows[-1]["response_payload_size_bytes"] == 0
    assert empty_rows[-1].get("payload_path") in (None, "")
    assert empty_rows[-1].get("payload_sha256") in (None, "")
    assert empty_rows[-1].get("payload_trusted") is False

    summary_data = json.loads(summary.read_text())
    assert summary_data["detail_fetch_attempted_count"] >= 1
    assert summary_data["detail_fetch_failed_count"] >= 1
    assert summary_data["detail_pending_retry_count"] >= 1
    assert summary_data["detail_empty_payload_count"] >= 1
    assert summary_data.get("symbol_empty_event_count", 0) == 0
    assert summary_data.get("symbol_parse_failed_count", 0) == 0


def test_detail_http_429_keeps_pending_retry_without_terminal_event(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": 1782830702782,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, **kwargs):
        return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 429, "payload_size_bytes": 17, "row_count": None, "error": "detail_payload_http_status_429"}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac" for row in events)


def test_detail_http_503_keeps_pending_retry_without_terminal_event(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": 1782830702782,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, **kwargs):
        return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 503, "payload_size_bytes": 19, "row_count": None, "error": "detail_payload_http_status_503"}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac" for row in events)


def test_detail_http_404_does_not_emit_success_or_persist_payload(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": 1782830702782,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, **kwargs):
        return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 404, "payload_size_bytes": 9, "row_count": None, "error": "detail_payload_http_status_404"}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    # For option A: max_retries limit is 3, first poll is retry_count=1, so no terminal event yet.
    assert not any(row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac" for row in events)


def test_detail_http_404_emits_terminal_failed_after_max_retries(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "3",
        "--poll-interval-sec", "0",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, **kwargs):
        return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 404, "payload_size_bytes": 9, "row_count": None, "error": "detail_payload_http_status_404"}

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_payload_fetch):
                        with patch("sys.argv", args):
                            rc = main()


    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    terminal_rows = [
        row for row in events
        if row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
    ]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["symbols"] == []
    assert terminal_rows[0]["detail_fetch_status"] in {"detail_payload_http_status_404", "retry_exhausted", "max_age_exceeded"}
    assert terminal_rows[0]["symbol_parse_failed_reason"] in {"detail_payload_http_status_404", "retry_exhausted", "detail_retry_exhausted", "max_age_exceeded", "detail_retry_max_age_exceeded"}



    summary_data = json.loads(summary.read_text())
    assert summary_data["detail_fetch_failed_count"] in {2, 3}
    assert summary_data["detail_terminal_failed_count"] == 1
    assert summary_data["symbol_parse_failed_count"] == 1
    assert summary_data["symbol_empty_event_count"] == 1


def test_empty_detail_payload_retries_and_success_later_emits_symbols_once(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    fixture_info = {
        "symbols": [
            {"symbol": "STRCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1782896400000},
            {"symbol": "CATUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1782896400000},
        ]
    }
    fixture_path = tmp_path / "exchangeInfo.json"
    fixture_path.write_text(json.dumps(fixture_info))

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "0",
    ]

    poll_num = 0

    def fake_list_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": fixture_info, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": len(fixture_info["symbols"]), "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        nonlocal poll_num
        poll_num += 1
        if poll_num == 1:
            return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 202, "payload_size_bytes": 0, "row_count": None, "error": "empty_detail_payload"}
        else:
            return {
                "ok": True,
                "payload": "2026-07-02 09:15 (UTC): STRCUSDT Perpetual Contract\n2026-07-02 09:20 (UTC): CATUSDT Perpetual Contract",
                "requested_url": url,
                "final_url": url,
                "http_status": 200,
                "payload_size_bytes": 100,
                "row_count": None,
                "error": None,
            }

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                    with patch("sys.argv", args):
                        rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed_rows = [
        row for row in events
        if row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "parsed"
    ]
    assert len(parsed_rows) == 1
    assert "STRCUSDT" in parsed_rows[0]["symbols"]
    assert "CATUSDT" in parsed_rows[0]["symbols"]


def test_empty_detail_retry_can_reprocess_after_restart_under_current_in_memory_seen_ids(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-02)",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    fixture_info = {
        "symbols": [
            {"symbol": "STRCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1782896400000},
            {"symbol": "CATUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1782896400000},
        ]
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)

    # Run 1: detail returns ok=False, empty_detail_payload
    args1 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": 1, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": fixture_info, "requested_url": url, "final_url": url, "http_status": 200, "payload_size_bytes": 100, "row_count": len(fixture_info["symbols"]), "error": None}
        raise AssertionError(url)

    def fake_payload_fetch1(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {"ok": False, "payload": None, "requested_url": url, "final_url": url, "http_status": 202, "payload_size_bytes": 0, "row_count": None, "error": "empty_detail_payload"}

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch1):
                    with patch("sys.argv", args1):
                        rc1 = main()

    assert rc1 == 0
    events1 = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac" for row in events1)

    # Run 2 (restart): detail returns ok=True
    args2 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_payload_fetch2(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": True,
            "payload": "2026-07-02 09:15 (UTC): STRCUSDT Perpetual Contract\n2026-07-02 09:20 (UTC): CATUSDT Perpetual Contract",
            "requested_url": url,
            "final_url": url,
            "http_status": 200,
            "payload_size_bytes": 100,
            "row_count": None,
            "error": None,
        }

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch2):
                    with patch("sys.argv", args2):
                        rc2 = main()

    assert rc2 == 0
    events2 = _read_jsonl_files(output_root / "events")
    parsed_rows2 = [
        row for row in events2
        if row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "parsed"
    ]
    assert len(parsed_rows2) == 1


def test_runner_validates_title_contract_symbol_ethusd1_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1782989000000,
        }]
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "klines" in url:
            return {"ok": True, "payload": [], "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("title contract symbol path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["ETHUSD1"] or parsed[0]["symbols"] == ("ETHUSD1",)
    assert parsed[0]["symbol_parse_status"] == "parsed"
    assert parsed[0]["symbol_extraction_source"] == "title_contract_symbol"
    assert parsed[0]["symbol_validation_status"] == "validated"
    assert parsed[0]["detail_fetch_attempted"] is False
    assert parsed[0]["detail_fetch_status"] == "not_needed"
    assert detail_calls["count"] == 0


def test_runner_validates_tradifi_perpetual_spcxusd1_when_trading(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "6cbb1b11a9c843949624cf2eacaac8b4",
                    "title": "Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)",
                    "releaseDate": 1784277011242,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "SPCXUSD1",
            "contractType": "TRADIFI_PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1784538000000,
        }]
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        if "klines" in url:
            return {"ok": True, "payload": [], "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("title contract symbol path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "6cbb1b11a9c843949624cf2eacaac8b4"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["SPCXUSD1"] or parsed[0]["symbols"] == ("SPCXUSD1",)
    assert parsed[0]["symbol_parse_status"] == "parsed"
    assert parsed[0]["symbol_extraction_source"] == "title_contract_symbol"
    assert parsed[0]["symbol_validation_status"] == "validated"
    assert parsed[0]["symbol_parse_failed_reason"] is None
    assert parsed[0].get("terminal_failure_type") is None
    assert parsed[0]["detail_fetch_attempted"] is False
    assert parsed[0]["detail_fetch_status"] == "not_needed"
    assert parsed[0]["symbol_effective_launch_times_ms"]["SPCXUSD1"] == 1784538000000
    assert detail_calls["count"] == 0


def test_runner_title_contract_symbol_pre_trading_stays_pending_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "PENDING_TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1783069200000,
        }]
    }

    detail_calls = {"count": 0}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("pending title candidate must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10" for row in events)
    assert detail_calls["count"] == 0
    s = json.loads(summary.read_text())
    assert s["detail_pending_retry_count"] == 0
    assert s["candidate_validation_pending_count"] == 0
    assert s["pre_launch_validation_deferred_count"] >= 1


def test_runner_tradifi_perpetual_spcxusd1_pending_stays_pending_without_terminal_fail(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "6cbb1b11a9c843949624cf2eacaac8b4",
                    "title": "Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)",
                    "releaseDate": 1784277011242,
                }]
            }]
        }
    }
    exchange_info = {
        "symbols": [{
            "symbol": "SPCXUSD1",
            "contractType": "TRADIFI_PERPETUAL",
            "status": "PENDING_TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1784538000000,
        }]
    }

    detail_calls = {"count": 0}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("pending title contract symbol path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "6cbb1b11a9c843949624cf2eacaac8b4" for row in events)
    assert detail_calls["count"] == 0
    s = json.loads(summary.read_text())
    assert s["candidate_validation_pending_count"] == 0
    assert s["pre_launch_validation_deferred_count"] >= 1

    state = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())
    row = state["articles"]["6cbb1b11a9c843949624cf2eacaac8b4"]
    assert row["candidate_symbols"] == ["SPCXUSD1"]
    assert row["symbol_validation_status"] == "pending_pre_trading"
    assert row.get("terminal_failure_type") is None
    assert row["symbol_effective_launch_times_ms"]["SPCXUSD1"] == 1784538000000


def test_title_contract_candidate_pending_survives_process_restart_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": 1782989104900,
                }]
            }]
        }
    }
    pending_exchange_info = {"symbols": []}
    trading_exchange_info = {
        "symbols": [{
            "symbol": "ETHUSD1",
            "contractType": "PERPETUAL",
            "status": "TRADING",
            "quoteAsset": "USD1",
            "marginAsset": "USD1",
            "onboardDate": 1782989000000,
        }]
    }
    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        raise AssertionError("title candidate restart path must not fetch detail")

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)

    def run_once(exchange_info):
        def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
            if "article/list/query" in url:
                return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
            if "exchangeInfo" in url:
                return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
            if "klines" in url:
                return {"ok": True, "payload": [], "final_url": url, "http_status": 200, "error": None}
            raise AssertionError(url)

        args = [
            "run_stage1_5d_live_event_source_smoke_collector.py",
            "--live-public-readonly",
            "--stage1-5c1-summary", str(c1),
            "--stage1-5c-summary", str(c),
            "--output-root", str(output_root),
            "--output-summary", str(summary),
            "--max-polls", "1",
            "--poll-interval-sec", "0",
        ]
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    return main()

    assert run_once(pending_exchange_info) == 0
    assert _read_jsonl_files(output_root / "events") == []

    assert run_once(trading_exchange_info) == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert detail_calls["count"] == 0


def test_transient_detail_http_202_does_not_terminal_fail_by_max_retries(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-02)",
                    "releaseDate": 1782980108049,
                }]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "detail_payload_http_status_202",
        }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "5",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(
        row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
        for row in events
    )
    s = json.loads(summary.read_text())
    assert s["detail_pending_retry_count"] >= 1
    assert s["detail_http_not_ready_count"] >= 1
    assert s["detail_terminal_failed_count"] == 0
    assert s["detail_transient_timeout_count"] == 0


def test_transient_detail_http_202_does_not_terminal_fail_after_backoff_retries_exceed_max_retries(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-02)",
                    "releaseDate": 1782980108049,
                }]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "detail_payload_http_status_202",
        }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "5",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
            with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
                    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                        with patch("sys.argv", args):
                            rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(
        row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
        for row in events
    )
    s = json.loads(summary.read_text())
    assert s["detail_terminal_failed_count"] == 0
    assert s.get("detail_symbol_parse_failed_count", 0) == 0
    assert s.get("symbol_empty_event_count", 0) == 0


def test_transient_detail_max_age_terminal_is_detail_unavailable_not_symbol_empty(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "d2acaa91c14e4cc598aaee1017efc1ac",
                    "title": "Binance Futures Will Launch USD-Margined Perpetual (2026-07-02)",
                    "releaseDate": 1782980108049,
                }]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "detail_payload_http_status_202",
        }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC", 0):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    terminal_rows = [
        r for r in events
        if r.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and r.get("symbol_parse_status") == "terminal_failed"
    ]
    assert terminal_rows == []
    terminal_diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    diagnostic_rows = [
        r for r in terminal_diagnostics
        if r.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and r.get("symbol_parse_status") == "terminal_failed"
    ]
    assert len(diagnostic_rows) == 1
    assert diagnostic_rows[0]["detail_fetch_status"] == "transient_detail_max_age_exceeded"
    assert diagnostic_rows[0]["symbol_parse_failed_reason"] == "transient_detail_max_age_exceeded"
    assert diagnostic_rows[0].get("terminal_failure_type") == "detail_unavailable_timeout"
    assert diagnostic_rows[0].get("consumable_by_stage1_5f") is False

    s = json.loads(summary.read_text())
    assert s["detail_terminal_failed_count"] == 1
    assert s["detail_transient_timeout_count"] == 1
    assert s.get("detail_symbol_parse_failed_count", 0) == 0
    assert s.get("symbol_empty_event_count", 0) == 0


def test_old_transient_detail_backlog_does_not_starve_new_article_first_attempt(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [
                    {"code": "old1", "title": "Binance Futures Will Launch USDⓈ-Margined Old1 Perpetual Contract", "releaseDate": 1710000000000},
                    {"code": "old2", "title": "Binance Futures Will Launch USDⓈ-Margined Old2 Perpetual Contract", "releaseDate": 1710000000001},
                    {"code": "old3", "title": "Binance Futures Will Launch USDⓈ-Margined Old3 Perpetual Contract", "releaseDate": 1710000000002},
                    {"code": "new_article_id", "title": "Binance Futures Will Launch USDⓈ-Margined New Perpetual Contract", "releaseDate": 1710000000003},
                ]
            }]
        }
    }

    # First poll: old1, old2, old3 return HTTP 202. new_article_id returns success.
    # detail budget = 3.
    # In old code: old1, old2, old3 fetched (budget exhausted), new_article_id starved.
    # In new code: never_attempted gets priority, so new_article_id must be fetched.
    calls = []

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        calls.append(url)
        if "new_article_id" in url:
            return {
                "ok": True,
                "payload": json.dumps({"data": {"body": "Binance Futures will launch ETHUSD1 Perpetual Contract"}}),
                "requested_url": url,
                "final_url": url,
                "http_status": 200,
                "payload_size_bytes": 100,
                "row_count": None,
                "error": None,
            }
        # old articles return HTTP 202
        return {
            "ok": False,
            "payload": None,
            "requested_url": url,
            "final_url": url,
            "http_status": 202,
            "payload_size_bytes": 0,
            "row_count": None,
            "error": "detail_payload_http_status_202",
        }

    # Mock exchangeInfo for symbol validation
    def fake_fetch_exchange_info(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [{"symbol": "ETHUSD1", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USD1", "marginAsset": "USD1"}]},
                "final_url": url,
                "http_status": 200,
                "error": None
            }
        return fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "starve_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 3):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_exchange_info):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    assert any("new_article_id" in c for c in calls)
    manifest_rows = _read_jsonl_files(output_root / "request_manifest")
    assert any(
        row.get("request_type") == "announcement_detail"
        and row.get("source_article_id") == "new_article_id"
        for row in manifest_rows
    )
    event_rows = _read_jsonl_files(output_root / "events")
    assert not any(
        row.get("source_article_id") == "new_article_id"
        and row.get("symbol_parse_status") == "terminal_failed"
        and row.get("detail_fetch_attempted") is False
        for row in event_rows
    )


def test_never_attempted_detail_article_does_not_terminal_fail_as_symbol_empty(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [
                    {"code": "never_attempted_starved", "title": "Binance Futures Will Launch USDⓈ-Margined Starved Perpetual Contract", "releaseDate": 1710000000000},
                ]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    # Budget = 0 to simulate starvation
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "protect_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "2",
        "--poll-interval-sec", "2",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 1):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    event_rows = _read_jsonl_files(output_root / "events")
    starved_events = [r for r in event_rows if r.get("source_article_id") == "never_attempted_starved"]
    assert len(starved_events) == 1
    event_row = starved_events[0]
    assert event_row["terminal_failure_type"] == "detail_never_attempted_budget_starved"
    assert event_row["detail_fetch_attempted"] is False
    assert event_row["detail_fetch_status"] == "budget_starved"
    assert event_row["symbol_parse_failed_reason"] == "detail_never_attempted_budget_starved"

    s = json.loads(summary.read_text())
    assert s["detail_budget_starved_count"] == 1
    assert s["detail_never_attempted_expired_count"] == 1
    assert s.get("symbol_empty_event_count", 0) == 0
    assert s.get("detail_symbol_parse_failed_count", 0) == 0


def test_detail_fetch_attempt_count_matches_announcement_detail_manifest_rows_for_transient_202(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        # Always return HTTP 202 empty
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "transient_202_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "3",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 1):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
                    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                        with patch("sys.argv", args):
                            rc = main()

    assert rc == 0
    state_path = output_root / "detail_retry_scheduler_state.json"
    assert state_path.exists()
    state = json.loads(state_path.read_text())
    article = state["articles"]["tradfi"]

    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    manifest_rows = []
    for f in manifest_files:
        for line in f.read_text().splitlines():
            row = json.loads(line)
            if row.get("source_article_id") == "tradfi":
                manifest_rows.append(row)

    assert article["detail_http_request_count"] == len(manifest_rows)
    assert article["detail_fetch_attempt_count"] == article["detail_http_request_count"]


def test_runner_wires_protected_recent_retry_config(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [
                    {
                        "code": "recent",
                        "title": "Binance Futures Will Launch USDⓈ-Margined RECENT Perpetual Contract",
                        "releaseDate": 1710000000000,
                    },
                    {
                        "code": "old",
                        "title": "Binance Futures Will Launch USDⓈ-Margined OLD Perpetual Contract",
                        "releaseDate": 1710000000000,
                    }
                ]
            }]
        }
    }

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    output_root = tmp_path / "wiring_smoke"
    output_root.mkdir(parents=True, exist_ok=True)

    now_ms = 4 * 60 * 60 * 1000
    state = {
        "articles": {
            "recent": {
                "source_article_id": "recent",
                "title": "Recent Article",
                "source_published_at_ms": 1710000000000,
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/recent",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "first_detected_at_ms": now_ms - 30 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_retry_cycle_count": 2,
                "transient_detail_error_count": 2,
                "next_detail_retry_at_ms": now_ms - 1,
                "last_retry_at_ms": now_ms - 11 * 60 * 1000,
            },
            "old": {
                "source_article_id": "old",
                "title": "Old Article",
                "source_published_at_ms": 1710000000000,
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/old",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "first_detected_at_ms": now_ms - 12 * 60 * 60 * 1000,
                "detail_http_request_count": 8,
                "detail_retry_cycle_count": 8,
                "transient_detail_error_count": 8,
                "next_detail_retry_at_ms": now_ms - 1,
                "last_retry_at_ms": now_ms - 11 * 60 * 1000,
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": now_ms + 60_000,
            "recent_detail_attempt_results": ["http_202_empty"] * 5,
        },
        "metadata_version": 1
    }

    state_file = output_root / "detail_retry_scheduler_state.json"
    state_file.write_text(json.dumps(state))

    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    fetched_urls = []
    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    with patch("time.time", return_value=now_ms / 1000.0):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    assert "https://www.binance.com/en/support/announcement/recent" in fetched_urls
    assert "https://www.binance.com/en/support/announcement/old" not in fetched_urls


def test_detail_fetch_fallback_detail_url_used_after_primary_http_202(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        if url.endswith("/support/announcement/tradfi"):
            return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}
        elif url.endswith("/support/announcement/detail/tradfi"):
            return {
                "ok": True,
                "payload": "<html>Binance Futures Will Launch USDⓈ-Margined ETHUSDT Perpetual Contract</html>",
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fallback_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC", 0):
        with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC", 0):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                    with patch("sys.argv", args):
                        rc = main()

    assert rc == 0
    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    manifest_rows = []
    for f in manifest_files:
        for line in f.read_text().splitlines():
            row = json.loads(line)
            if row.get("source_article_id") == "tradfi":
                manifest_rows.append(row)

    assert len(manifest_rows) == 2
    assert manifest_rows[0]["http_status"] == 202
    assert manifest_rows[0]["detail_fetch_variant"] == "primary"
    assert manifest_rows[1]["http_status"] == 200
    assert manifest_rows[1]["detail_fetch_variant"] == "detail_path_fallback"

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert len(events) == 1
    assert "ETHUSDT" in events[0]["symbols"]
    assert events[0]["detail_fetch_variant"] == "detail_path_fallback"
    assert events[0]["detail_payload_trusted"] is True
    assert events[0]["detail_payload_hash"] is not None


def test_detail_fetch_fallback_detail_url_used_after_primary_200_empty_untrusted_payload(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        if url.endswith("/support/announcement/tradfi"):
            return {
                "ok": True,
                "payload": "<html>Detail shell without symbols yet.</html>",
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
        if url.endswith("/support/announcement/detail/tradfi"):
            return {
                "ok": True,
                "payload": "<html>Binance Futures Will Launch USDⓈ-Margined ETHUSDT Perpetual Contract</html>",
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "fallback_200_empty_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    assert len(fetched_urls) == 2
    manifest_rows = []
    for f in (output_root / "request_manifest").glob("*.jsonl"):
        for line in f.read_text().splitlines():
            row = json.loads(line)
            if row.get("source_article_id") == "tradfi":
                manifest_rows.append(row)

    assert [row["detail_fetch_variant"] for row in manifest_rows] == ["primary", "detail_path_fallback"]
    assert manifest_rows[0]["payload_trusted"] is False
    assert manifest_rows[1]["payload_trusted"] is True

    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    events = [json.loads(line) for line in event_files[0].read_text().strip().splitlines()]
    assert events[0]["symbols"] == ["ETHUSDT"]
    assert events[0]["detail_fetch_variant"] == "detail_path_fallback"


def test_detail_fallback_requests_respect_total_http_request_budget_per_poll(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "budget_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    assert len(fetched_urls) == 1
    assert fetched_urls[0].endswith("/announcement/tradfi")


def test_detail_fallback_not_used_after_http_429(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        return {"ok": False, "payload": "", "final_url": url, "http_status": 429, "error": "Too Many Requests"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "429_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    assert len(fetched_urls) == 1


def test_detail_fallback_not_used_after_network_timeout(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        return {"ok": False, "payload": None, "final_url": url, "http_status": None, "error": "timeout"}

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "timeout_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    assert len(fetched_urls) == 1


def test_fallback_200_untrusted_payload_does_not_emit_parsed_event(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "tradfi",
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }

    fetched_urls = []
    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "article/list/query" in url:
            return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}
        raise AssertionError(url)

    def fake_fetch_payload(url, live_public_readonly, timeout_sec, retry_budget=0):
        fetched_urls.append(url)
        if url.endswith("/support/announcement/tradfi"):
            return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}
        elif url.endswith("/support/announcement/detail/tradfi"):
            return {
                "ok": True,
                "payload": "<html>Some announcement detail without margin assets or symbols.</html>",
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
        raise AssertionError(url)

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "untrusted_smoke"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 0


def test_overdue_attempted_detail_retry_gets_bounded_retry_slot(tmp_path):
    output_root = tmp_path / "overdue_smoke"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    import time
    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f43403ef11974998bc0f46420826577a": {
                "source_article_id": "f43403ef11974998bc0f46420826577a",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f43403ef11974998bc0f46420826577a",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 90 * 60 * 1000,
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
                "defer_count": 1,
                "pending_reason": "title_symbol_missing",
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": now_ms - 10 * 60 * 1000,
        },
    }
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        if "announcement" in url:
            payload = {
                "code": "000000",
                "data": {
                    "catalogs": [
                        {
                            "catalogId": 48,
                            "catalogName": "New Crypto Listing",
                            "articles": [
                                {
                                    "id": 9991,
                                    "code": "fresh1",
                                    "title": "Binance Futures Will Launch Fresh1 Perpetual Contract",
                                    "releaseDate": now_ms - 1000,
                                },
                            ],
                        }
                    ]
                },
            }
            return {"ok": True, "payload": payload, "final_url": url, "http_status": 200, "error": None}
        return {"ok": True, "payload": {"symbols": []}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    manifest_rows = _read_jsonl_files(output_root / "request_manifest")
    article_rows = [r for r in manifest_rows if r.get("source_article_id") == "f43403ef11974998bc0f46420826577a"]
    assert any(r.get("request_type") == "announcement_detail" for r in article_rows)
    assert any(r.get("http_status") == 202 for r in article_rows)

    state_after = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())["articles"]["f43403ef11974998bc0f46420826577a"]
    assert state_after["detail_http_request_count"] > 2
    assert state_after["terminal_failure_type"] is None


def test_overdue_retry_cycle_respects_total_detail_http_request_budget(tmp_path, monkeypatch):
    output_root = tmp_path / "budget_smoke"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL", 1)

    import time
    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f434": {
                "source_article_id": "f434",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f434",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 90 * 60 * 1000,
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        "endpoint_health": {},
    }
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        return {"ok": True, "payload": {"code": "000000", "data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    manifest_rows = _read_jsonl_files(output_root / "request_manifest")
    detail_rows = [r for r in manifest_rows if r.get("request_type") == "announcement_detail"]
    assert len(detail_rows) <= 1


def test_overdue_fallback_requests_each_increment_http_request_count_and_manifest_rows(tmp_path):
    output_root = tmp_path / "fallback_smoke"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    import time
    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f434": {
                "source_article_id": "f434",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f434",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 90 * 60 * 1000,
                "first_detected_at_ms": now_ms - 90 * 60 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "detail_retry_cycle_count": 1,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 80 * 60 * 1000,
                "next_detail_retry_at_ms": now_ms - 70 * 60 * 1000,
            }
        },
        "endpoint_health": {},
    }
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        return {"ok": True, "payload": {"code": "000000", "data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    manifest_rows = _read_jsonl_files(output_root / "request_manifest")
    detail_rows = [r for r in manifest_rows if r.get("request_type") == "announcement_detail"]
    assert len(detail_rows) == 2

    state_after = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())["articles"]["f434"]
    assert state_after["detail_http_request_count"] == 4
    assert state_after["detail_retry_cycle_count"] == 2


def test_http_202_remains_pending_before_transient_max_age(tmp_path):
    import time
    output_root = tmp_path / "out"
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f434": {
                "source_article_id": "f434",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f434",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 3600 * 1000,
                "first_detected_at_ms": now_ms - 3600 * 1000,
                "detail_http_request_count": 1,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 1800 * 1000,
                "next_detail_retry_at_ms": now_ms - 600 * 1000,
                "pending_reason": "title_symbol_missing",
            }
        },
        "endpoint_health": {},
    }
    (output_root / "detail_retry_scheduler_state.json").parent.mkdir(parents=True, exist_ok=True)
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        return {"ok": True, "payload": {"code": "000000", "data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    state_after = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())["articles"]["f434"]
    assert state_after["terminal_failure_type"] is None
    events = _read_jsonl_files(output_root / "events")
    assert not any(e.get("source_article_id") == "f434" for e in events)


def test_detail_unavailable_timeout_does_not_emit_stage1_5f_consumable_event(tmp_path):
    import time
    output_root = tmp_path / "out"
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f434": {
                "source_article_id": "f434",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f434",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 86401 * 1000,
                "first_detected_at_ms": now_ms - 86401 * 1000,
                "detail_http_request_count": 5,
                "detail_fetch_attempt_count": 5,
                "transient_detail_error_count": 5,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 1800 * 1000,
                "next_detail_retry_at_ms": now_ms - 600 * 1000,
                "pending_reason": "title_symbol_missing",
            }
        },
        "endpoint_health": {},
    }
    (output_root / "detail_retry_scheduler_state.json").parent.mkdir(parents=True, exist_ok=True)
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        return {"ok": True, "payload": {"code": "000000", "data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args):
                rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    timeout_events = [e for e in events if e.get("source_article_id") == "f434"]
    assert timeout_events == []

    terminal_rows = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    timeout_rows = [r for r in terminal_rows if r.get("source_article_id") == "f434"]
    assert len(timeout_rows) == 1
    assert timeout_rows[0].get("terminal_failure_type") == "detail_unavailable_timeout"
    assert timeout_rows[0].get("consumable_by_stage1_5f") is False


def test_overdue_attempted_row_survives_restart_and_is_selected_after_degraded_expiry(tmp_path):
    import time
    output_root = tmp_path / "restart_smoke"
    output_root.mkdir(parents=True, exist_ok=True)
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    state = {
        "articles": {
            "f434": {
                "source_article_id": "f434",
                "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-21)",
                "source_detail_url_normalized": "https://www.binance.com/en/support/announcement/f434",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 4 * 3600 * 1000,
                "first_detected_at_ms": now_ms - 4 * 3600 * 1000,
                "detail_http_request_count": 2,
                "detail_fetch_attempt_count": 2,
                "transient_detail_error_count": 1,
                "last_detail_failure_class": "http_202_empty",
                "detail_retryable": True,
                "last_retry_at_ms": now_ms - 3 * 3600 * 1000,
                "next_detail_retry_at_ms": now_ms - 2 * 3600 * 1000,
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": now_ms + 600 * 1000,
        },
    }
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(state))

    def fake_fetch_json(url, **kwargs):
        return {"ok": True, "payload": {"code": "000000", "data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_fetch_payload(url, **kwargs):
        return {"ok": False, "payload": "", "final_url": url, "http_status": 202, "error": "202 Empty"}

    # Poll 1: endpoint degraded active -> article deferred
    args1 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]
    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args1):
                assert main() == 0

    manifest_rows1 = _read_jsonl_files(output_root / "request_manifest")
    assert not any(r.get("source_article_id") == "f434" for r in manifest_rows1)

    # Simulate restart and time passing beyond degraded expiry
    state_file = output_root / "detail_retry_scheduler_state.json"
    persisted = json.loads(state_file.read_text())
    persisted["endpoint_health"]["detail_endpoint_degraded_until_ms"] = 0
    state_file.write_text(json.dumps(persisted))

    # Poll 2: degraded expired -> f434 gets slot and retry attempt
    args2 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
        "--poll-interval-sec", "0",
    ]
    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_fetch_payload):
            with patch("sys.argv", args2):
                assert main() == 0

    manifest_rows2 = _read_jsonl_files(output_root / "request_manifest")
    f434_rows = [r for r in manifest_rows2 if r.get("source_article_id") == "f434"]
    assert len(f434_rows) >= 1

    diagnostics = _read_jsonl_files(output_root / "detail_retry_scheduler_diagnostics")
    selected_rows = [
        row for row in diagnostics
        if "f434" in row.get("detail_retry_overdue_selected_article_ids", [])
    ]
    assert selected_rows

    s = json.loads(summary.read_text())
    assert s["detail_retry_overdue_selected_total"] >= 1
    assert s["detail_retry_overdue_retry_cycle_total"] >= 1


# ==============================================================================
# BAPI Hotfix Task 8 & Task 11 Integration and Cross-Stage Admission Tests
# ==============================================================================

def test_no_symbol_title_uses_bapi_detail_before_support_fallback(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": hex32,
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    bapi_payload = {
        "code": "000000",
        "data": {
            "code": hex32,
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
            "body": "<p>Binance Futures will launch XYZUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</p>",
        }
    }


    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {"ok": True, "payload": bapi_payload, "final_url": f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={article_code}", "http_status": 200, "error": None}

    support_called = []
    def fake_support_fetch(url, **kwargs):
        support_called.append(url)
        return {"ok": False, "payload": None, "final_url": url, "http_status": 404, "error": "not_found"}

    def fake_ex_fetch(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "XYZUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_fetch(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_support_fetch):
                with patch("sys.argv", args):
                    assert main() == 0

    assert len(support_called) == 0, "Support detail should not be called when BAPI succeeds"
    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 1
    assert events[0]["symbols"] == ["XYZUSDT"]
    detail_transport = events[0].get("detail_transport") or events[0].get("extraction_metadata", {}).get("detail_transport")
    assert detail_transport == "bapi_article_detail_query"



def test_bapi_detail_failure_falls_back_to_support_detail_paths(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": hex32,
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    support_html = "<html><body>Binance Futures will launch ABCUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</body></html>"
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {"ok": False, "payload": None, "final_url": "", "http_status": 500, "error": "bapi_500"}

    def fake_support_fetch(url, **kwargs):
        return {"ok": True, "payload": support_html, "final_url": url, "http_status": 200, "error": None}

    def fake_ex_fetch(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "ABCUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_fetch(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_support_fetch):
                with patch("sys.argv", args):
                    assert main() == 0

    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 1
    assert events[0]["symbols"] == ["ABCUSDT"]


def test_bapi_and_support_requests_each_write_manifest_rows(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": hex32,
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {"ok": False, "payload": None, "final_url": "https://www.binance.com/bapi/...", "http_status": 503, "error": "bapi_503"}

    def fake_support_fetch(url, **kwargs):
        return {"ok": False, "payload": None, "final_url": url, "http_status": 202, "error": "202 Empty"}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_support_fetch):
                with patch("sys.argv", args):
                    assert main() == 0

    manifest = _read_jsonl_files(output_root / "request_manifest")
    article_rows = [r for r in manifest if r.get("source_article_id") == hex32]
    assert len(article_rows) >= 2, "Must contain BAPI row + Support fallback row"
    bapi_row = next(r for r in article_rows if r.get("detail_fetch_variant") == "bapi_article_detail_query")
    assert bapi_row["source_transport"] == "binance_first_party_public_web_bapi_undocumented"
    assert bapi_row["content_provenance"] == "binance_official_announcement"
    assert bapi_row["http_status"] == 503


def test_bapi_failure_does_not_call_support_when_http_budget_exhausted(tmp_path, monkeypatch):
    hex32 = "f43403ef11974998bc0f46420826577a"
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": hex32,
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL", 1)
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": False,
            "payload": None,
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 503,
            "error": "bapi_503",
        }

    support_called = []

    def fake_support_fetch(url, **kwargs):
        support_called.append(url)
        return {"ok": False, "payload": None, "final_url": url, "http_status": 202, "error": "202 Empty"}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_list_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_support_fetch):
                with patch("sys.argv", args):
                    assert main() == 0

    assert support_called == []
    manifest = _read_jsonl_files(output_root / "request_manifest")
    article_rows = [r for r in manifest if r.get("source_article_id") == hex32]
    assert [r.get("detail_fetch_variant") for r in article_rows] == ["bapi_article_detail_query"]


def test_support_202_degraded_state_does_not_suppress_bapi_detail_in_runner(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    output_root = tmp_path / "out"
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    scheduler_state = {
        "articles": {
            hex32: {
                "source_article_id": hex32,
                "title": "Binance Futures Will Launch USDⓈ-Margined ABC Perpetual Contract",
                "source_detail_url_normalized": f"https://www.binance.com/en/support/announcement/{hex32}",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 5000,
                "first_detected_at_ms": now_ms - 5000,
                "detail_http_request_count": 0,
                "detail_retry_cycle_count": 0,
                "detail_fetch_attempt_count": 0,
            }
        },
        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": now_ms + 300000,
            "endpoint_health_by_source": {
                "bapi_article_detail_query": {"degraded_until_ms": 0, "recent_results": []},
                "support_article_detail": {"degraded_until_ms": now_ms + 300000, "recent_results": ["http_202_empty"]},
            }
        }
    }
    (output_root).mkdir(parents=True, exist_ok=True)
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(scheduler_state))

    bapi_payload = {
        "code": "000000",
        "data": {
            "code": hex32,
            "title": "Binance Futures Will Launch USDⓈ-Margined ABC Perpetual Contract",
            "body": "<p>Binance Futures will launch ABCUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</p>",
        }
    }


    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": {"data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {"ok": True, "payload": bapi_payload, "final_url": "https://www.binance.com/bapi/...", "http_status": 200, "error": None}

    def fake_ex_fetch(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "ABCUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_fetch(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("sys.argv", args):
                assert main() == 0

    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 1
    assert events[0]["symbols"] == ["ABCUSDT"]


def test_legacy_global_support_degraded_state_does_not_suppress_bapi_detail_in_runner(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    output_root = tmp_path / "out"
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    scheduler_state = {
        "articles": {
            hex32: {
                "source_article_id": hex32,
                "title": "Binance Futures Will Launch USDⓈ-Margined ABC Perpetual Contract",
                "source_detail_url_normalized": f"https://www.binance.com/en/support/announcement/{hex32}",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 5000,
                "first_detected_at_ms": now_ms - 5000,
                "detail_http_request_count": 0,
                "detail_retry_cycle_count": 0,
                "detail_fetch_attempt_count": 0,
            }
        },
        "endpoint_health": {"detail_endpoint_degraded_until_ms": now_ms + 300000},
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(scheduler_state))

    bapi_payload = {
        "code": "000000",
        "data": {
            "code": hex32,
            "title": "Binance Futures Will Launch USDⓈ-Margined ABC Perpetual Contract",
            "body": "<p>Binance Futures will launch ABCUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</p>",
        }
    }

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": {"data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": True,
            "payload": bapi_payload,
            "raw_bytes": json.dumps(bapi_payload).encode("utf-8"),
            "final_url": "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode=f43403ef11974998bc0f46420826577a",
            "http_status": 200,
            "error": None,
        }

    def fake_ex_fetch(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "ABCUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_fetch(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("sys.argv", args):
                assert main() == 0

    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 1
    assert events[0]["symbols"] == ["ABCUSDT"]


def test_bapi_degraded_state_does_not_disable_support_fallback_in_runner(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    output_root = tmp_path / "out"
    summary = tmp_path / "summary.json"
    c1, c = _write_valid_upstream(tmp_path)

    now_ms = int(time.time() * 1000)
    scheduler_state = {
        "articles": {
            hex32: {
                "source_article_id": hex32,
                "title": "Binance Futures Will Launch USDⓈ-Margined ABC Perpetual Contract",
                "source_detail_url_normalized": f"https://www.binance.com/en/support/announcement/{hex32}",
                "source_parent_url": "https://www.binance.com/en/support/announcement",
                "source_published_at_ms": now_ms - 5000,
                "first_detected_at_ms": now_ms - 5000,
                "detail_http_request_count": 0,
                "detail_retry_cycle_count": 0,
                "detail_fetch_attempt_count": 0,
            }
        },


        "endpoint_health": {
            "detail_endpoint_degraded_until_ms": 0,
            "endpoint_health_by_source": {
                "bapi_article_detail_query": {"degraded_until_ms": now_ms + 300000, "recent_results": ["http_500"]},
                "support_article_detail": {"degraded_until_ms": 0, "recent_results": []},
            }
        }
    }
    (output_root).mkdir(parents=True, exist_ok=True)
    (output_root / "detail_retry_scheduler_state.json").write_text(json.dumps(scheduler_state))

    support_html = "<html><body>Binance Futures will launch ABCUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</body></html>"

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": {"data": {"catalogs": [{"articles": []}]}}, "final_url": url, "http_status": 200, "error": None}

    bapi_called = []
    def fake_bapi_fetch(article_code, **kwargs):
        bapi_called.append(article_code)
        return {"ok": False, "payload": None, "final_url": "", "http_status": 500, "error": "bapi_degraded"}

    def fake_support_fetch(url, **kwargs):
        return {"ok": True, "payload": support_html, "final_url": url, "http_status": 200, "error": None}

    def fake_ex_fetch(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "ABCUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_fetch(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_support_fetch):
                with patch("sys.argv", args):
                    assert main() == 0

    assert len(bapi_called) == 0, "BAPI should be skipped when BAPI source is degraded"
    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 1
    assert events[0]["symbols"] == ["ABCUSDT"]


def test_detail_parsed_exchangeinfo_not_visible_enters_pending_validation_without_bapi_refetch(tmp_path):
    hex32 = "f43403ef11974998bc0f46420826577a"
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": hex32,
                    "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
                    "releaseDate": int(time.time() * 1000) - 1000,
                }]
            }]
        }
    }
    bapi_payload = {
        "code": "000000",
        "data": {
            "code": hex32,
            "title": "Binance Futures Will Launch Multiple USDⓈ-Margined Perpetual Contracts",
            "body": "<p>Binance Futures will launch NEWCOINUSDT Perpetual Contract at 2026-07-21 13:30 (UTC).</p>",
        }
    }

    summary = tmp_path / "summary.json"
    output_root = tmp_path / "out"
    c1, c = _write_valid_upstream(tmp_path)

    bapi_fetch_count = 0
    def fake_bapi_fetch(article_code, **kwargs):
        nonlocal bapi_fetch_count
        bapi_fetch_count += 1
        return {"ok": True, "payload": bapi_payload, "final_url": "https://www.binance.com/bapi/...", "http_status": 200, "error": None}

    def fake_list_fetch(url, **kwargs):
        return {"ok": True, "payload": list_payload, "final_url": url, "http_status": 200, "error": None}

    def fake_ex_empty(url, **kwargs):
        return {"ok": True, "payload": {"symbols": []}, "final_url": url, "http_status": 200, "error": None}

    # Poll 1: exchangeInfo missing NEWCOINUSDT -> enters pending validation
    args1 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_empty(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("sys.argv", args1):
                assert main() == 0

    assert bapi_fetch_count == 1
    events = _read_jsonl_files(output_root / "events")
    assert len(events) == 0, "No event emitted yet while exchangeInfo symbol is missing"

    # Set validation retry interval to 0 so Poll 2 re-evaluates exchangeInfo immediately
    state_file = output_root / "detail_retry_scheduler_state.json"
    persisted = json.loads(state_file.read_text())
    if hex32 in persisted.get("articles", {}):
        persisted["articles"][hex32]["next_exchangeinfo_validation_at_ms"] = 0
        state_file.write_text(json.dumps(persisted))

    # Poll 2: exchangeInfo now contains NEWCOINUSDT -> emits event WITHOUT refetching BAPI
    def fake_ex_ready(url, **kwargs):
        return {
            "ok": True,
            "payload": {
                "symbols": [{
                    "symbol": "NEWCOINUSDT",
                    "status": "TRADING",
                    "marginAsset": "USDT",
                    "quoteAsset": "USDT",
                    "contractType": "PERPETUAL",
                }]
            },
            "final_url": url,
            "http_status": 200,
            "error": None,
        }

    args2 = [
        "run_stage1_5d_live_event_source_smoke_collector.py",
        "--live-public-readonly",
        "--stage1-5c1-summary", str(c1),
        "--stage1-5c-summary", str(c),
        "--output-root", str(output_root),
        "--output-summary", str(summary),
        "--max-polls", "1",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=lambda url, **kw: fake_ex_ready(url) if "exchangeInfo" in url else fake_list_fetch(url)):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("sys.argv", args2):
                assert main() == 0

    assert bapi_fetch_count == 1, "BAPI detail should NOT be refetched while waiting for exchangeInfo visibility"
    events2 = _read_jsonl_files(output_root / "events")
    assert len(events2) == 1
    assert events2[0]["symbols"] == ["NEWCOINUSDT"]


def test_pre_hotfix_bapi_recovered_article_does_not_become_formal_1_5f_evidence(tmp_path):
    event = {
        "event_id": "ev_pre_hotfix_123",
        "source_article_id": "f43403ef11974998bc0f46420826577a",
        "symbols": ["ABCUSDT"],
        "source_published_at_ms": 1784640600000 - 10000,
        "detected_at_ms": 1784640600000 - 10000,
        "extraction_metadata": {
            "detail_transport": "bapi_article_detail_query",
            "content_provenance": "binance_official_announcement",
        }
    }
    assert event["source_published_at_ms"] < 1784640600000
    from src.risk.limits import RiskLimits
    assert RiskLimits.live_trading_enabled is False



def test_new_post_watermark_bapi_event_can_reach_1_5f_formal_acceptance(tmp_path):
    now_ms = 1784640600000 + 3600000
    event = {
        "event_id": "ev_post_hotfix_456",
        "source_article_id": "d0833b3a6eb64132a00c6d7a46abf434",
        "symbols": ["XYZUSDT"],
        "source_published_at_ms": now_ms,
        "detected_at_ms": now_ms,
        "extraction_metadata": {
            "evidence_source": "official_article_body_confirmed",
            "detail_transport": "bapi_article_detail_query",
            "content_provenance": "binance_official_announcement",
            "source_transport": "binance_first_party_public_web_bapi_undocumented",
            "symbol_validation_status": "validated_by_exchangeinfo",
        }
    }
    assert event["source_published_at_ms"] >= 1784640600000
    assert event["extraction_metadata"]["evidence_source"] == "official_article_body_confirmed"
