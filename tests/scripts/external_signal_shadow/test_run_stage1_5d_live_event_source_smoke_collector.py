import json
from unittest.mock import patch

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
                        "releaseDate": 1710000000000,
                    },
                    {
                        "code": "tradfi",
                        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                        "releaseDate": 1710000000001,
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
    exchange_info = {"symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL"}]}
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
            return {"ok": False, "payload": None, "final_url": url, "http_status": 500, "error": "persistent_error"}
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
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
        {"symbol": "ETHUUSDT", "status": "TRADING", "contractType": "PERPETUAL"}
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

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
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
    assert events[0]["symbols"] == ["BTCUUSDT", "ETHUUSDT"]
    assert events[0]["symbol_extraction_source"] == "detail_base_asset_derived"
    assert events[0]["symbol_derivation_method"] == "base_asset_plus_quote"
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

    with patch("configs.base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 1):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
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
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_html = "<html><body>Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts.</body></html>"
    exchange_info = {"symbols": [
        {"symbol": "BTCUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
        {"symbol": "ETHUUSDT", "status": "TRADING", "contractType": "PERPETUAL"}
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
    assert events[0]["symbols"] == ["BTCUUSDT", "ETHUUSDT"]

    manifest_files = list((output_root / "request_manifest").glob("*.jsonl"))
    assert len(manifest_files) == 1
    manifest_rows = [json.loads(line) for line in manifest_files[0].read_text().strip().splitlines()]
    detail_row = next((r for r in manifest_rows if r.get("source_type") == "announcement_detail"), None)
    assert detail_row is not None
    assert detail_row["payload_path"].endswith(".html")


def test_announcement_list_fetch_still_uses_fetch_public_json_not_raw_payload(tmp_path):
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
        {"symbol": "BTCUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
        {"symbol": "ETHUUSDT", "status": "TRADING", "contractType": "PERPETUAL"}
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
                    "releaseDate": 1710000000000,
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
        return {"ok": False, "payload": None, "final_url": url, "http_status": 500, "error": "persistent_error"}

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
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
                    "releaseDate": 1782821102782,
                }]
            }]
        }
    }
    detail_payload = "Binance Futures will launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts."
    exchange_info = {"symbols": [
        {"symbol": "BTCUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
        {"symbol": "ETHUUSDT", "status": "TRADING", "contractType": "PERPETUAL"}
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

    assert "BTCUUSDT" in ev["symbols"]
    assert "ETHUUSDT" in ev["symbols"]
    assert ev["symbol_extraction_source"] == "detail_base_asset_derived"
    assert ev["symbol_derivation_method"] == "base_asset_plus_quote"
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
        {"symbol": "BTCUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
        {"symbol": "ETHUUSDT", "status": "TRADING", "contractType": "PERPETUAL"},
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








