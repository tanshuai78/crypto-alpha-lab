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
                    "title": "Binance Futures Will Launch USDⓈ-Margined BTCU and ETHU Perpetual Contracts (2026-07-01)",
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
        and r.get("error") == "empty_detail_payload"
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
        "--max-polls", "3",
        "--poll-interval-sec", "0",
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
    terminal_rows = [
        row for row in events
        if row.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
        and row.get("symbol_parse_status") == "terminal_failed"
    ]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["symbols"] == []
    assert terminal_rows[0]["detail_fetch_status"] == "detail_payload_http_status_404"
    assert terminal_rows[0]["symbol_parse_failed_reason"] == "detail_payload_http_status_404"

    summary_data = json.loads(summary.read_text())
    assert summary_data["detail_fetch_failed_count"] == 3
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
                    "releaseDate": 1782830702782,
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
                    "releaseDate": 1782830702782,
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











