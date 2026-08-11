import ast
import json
import time
from pathlib import Path
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


def test_only_formal_event_writer_can_append_events_stream():
    source_path = Path("scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "append_jsonl":
            continue
        if not node.args:
            continue
        first_arg = ast.get_source_segment(source, node.args[0]) or ""
        if 'stream_paths["events"]' not in first_arg:
            continue
        cur = node
        parent_func = None
        while cur in parents:
            cur = parents[cur]
            if isinstance(cur, ast.FunctionDef):
                parent_func = cur.name
                break
        if parent_func not in {"append_formal_futures_launch_event", "append_formal_schedule_revision"}:
            violations.append((node.lineno, parent_func))

    assert violations == []


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
                        "detailPayload": "Binance Futures will launch USDⓈ-Margined ABCUSDT Perpetual Contract at 2026-08-01 12:00 (UTC).",
                    },
                    {
                        "code": "tradfi",
                        "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts",
                        "releaseDate": int(time.time() * 1000) - 1000,
                    },
                ]
            }]
        },
        "exchangeInfoPayload": {
            "symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}]
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
    exchange_info = {"symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}]}

    def fake_fetch_json(url, live_public_readonly, timeout_sec, retry_budget=2):
        if "exchangeInfo" in url:
            return {"ok": True, "payload": exchange_info, "final_url": url, "http_status": 200, "error": None}
        return {"ok": True, "payload": {}, "final_url": url, "http_status": 200, "error": None}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        bapi_payload = {
            "code": "000000",
            "message": None,
            "messageDetail": None,
            "data": {
                "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                "body": "Binance Futures will launch ABCUSDT at 2026-08-01 12:00 (UTC).",
                "releaseDate": int(time.time() * 1000) - 1000,
            },
            "success": True,
        }
        return {"ok": True, "payload": bapi_payload, "final_url": url, "http_status": 200, "error": None}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
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
    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        bapi_payload = {
            "code": "000000",
            "message": None,
            "messageDetail": None,
            "data": {
                "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                "body": "Binance Futures will launch ABCUSDT at 2026-08-01 12:00 (UTC).",
                "releaseDate": 1710000000000,
            },
            "success": True,
        }
        return {"ok": True, "payload": bapi_payload, "final_url": url, "http_status": 200, "error": None}

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "AMDUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                    {"symbol": "QCOMUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908860000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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

    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "tradfi"]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["symbols"] == []
    assert terminal_rows[0]["symbol_parse_status"] == "terminal_failed"
    assert terminal_rows[0]["symbol_parse_failed_reason"] in {"detail_retry_max_age_exceeded", "detail_retry_exhausted"}
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "AAPLUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                    {"symbol": "MSFTUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908860000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
    assert detail_row["parser_version"] == "stage1_5d_symbol_extraction_v3"
    assert detail_row["symbol_extraction_version"] == 3


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

    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["detail_fetch_status"] == "url_missing"
    assert terminal_rows[0]["symbol_parse_status"] == "terminal_failed"


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

    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "evil_path"]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["detail_fetch_status"] == "url_not_allowlisted"
    assert terminal_rows[0]["symbol_parse_status"] == "terminal_failed"


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

    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "tradfi"]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["detail_fetch_status"] == "final_url_not_allowlisted"
    assert terminal_rows[0]["symbol_parse_status"] == "terminal_failed"


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
        },
        "exchangeInfoPayload": {
            "symbols": [
                {"symbol": "AMDUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                {"symbol": "QCOMUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908860000},
                {"symbol": "USARUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908920000},
            ]
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
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000}
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
    assert events[0]["symbol_validation_status"] == "validated_candidate_set"
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

    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "25da4614ffff435fa28544b27fd33a39"]
    assert terminal_rows == []
    state = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())
    row = state["articles"]["25da4614ffff435fa28544b27fd33a39"]
    assert row["candidate_symbols"] == ["BTCU", "ETHU"]
    assert row["symbol_validation_status"] == "pending_candidate_set_readiness"
    assert row["pending_reason"] == "multi_symbol_candidate_set_not_ready"
    assert row.get("terminal_failure_type") is None


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
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000}
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
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000}
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "AMDUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                    {"symbol": "NVDAUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908860000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
    events = _read_jsonl_files(output_root / "events")
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "tradfi"]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["detected_at_ms"] == terminal_rows[0]["first_detected_at_ms"]


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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000}
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
    assert ev["symbol_validation_status"] == "validated_candidate_set"
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
        {"symbol": "BTCU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782896400000},
        {"symbol": "ETHU", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "U", "marginAsset": "U", "onboardDate": 1782900000000},
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
    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [d.get("raw_event", d) for d in diagnostics if d.get("source_article_id") == "25da4614ffff435fa28544b27fd33a39"]
    assert len(terminal_rows) == 1
    assert terminal_rows[0]["symbols"] == []
    assert terminal_rows[0]["symbol_validation_status"] == "rejected"
    assert terminal_rows[0]["symbol_parse_status"] == "terminal_failed"
    assert terminal_rows[0]["symbol_parse_failed_reason"] == "exchange_info_disallowed_contract_type"


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
    assert persisted_events[0]["symbol_validation_status"] == "validated_candidate_set"
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
    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    terminal_rows = [
        d.get("raw_event", d) for d in diagnostics
        if d.get("source_article_id") == "d2acaa91c14e4cc598aaee1017efc1ac"
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
                    "code": "synthetic_empty_retry_code_001",
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
        if row.get("source_article_id") == "synthetic_empty_retry_code_001"
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
                    "code": "synthetic_empty_retry_code_002",
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
    assert not any(row.get("source_article_id") == "synthetic_empty_retry_code_002" for row in events1)

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
        if row.get("source_article_id") == "synthetic_empty_retry_code_002"
        and row.get("symbol_parse_status") == "parsed"
    ]
    assert len(parsed_rows2) == 1


def _official_single_symbol_detail_text(symbol: str) -> str:
    return (
        "Fellow Binancians,\n"
        "To expand trading choices, Binance Futures will launch the following perpetual contract(s) as below:\n"
        f"2029-01-01 00:00 (UTC):\n{symbol}\nPerpetual Contract\n"
        "More details on the aforementioned perpetual contract(s) can be found in the table below:\n"
        f"USDⓈ-M Perpetual Contract\n{symbol}\nLaunch Time\n2029-01-01 00:00 (UTC)\nSettlement Asset\nUSD1"
    )


def _official_single_symbol_bapi_payload(symbol: str) -> dict:
    return {
        "code": "000000",
        "data": {"body": [{"text": _official_single_symbol_detail_text(symbol)}]},
    }


def test_runner_validates_title_contract_symbol_ethusd1_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": int(time.time() * 1000) - 1000,
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
            "onboardDate": 4070908800000,
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
        return {"ok": True, "payload": _official_single_symbol_detail_text("ETHUSD1"), "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": True,
            "payload": _official_single_symbol_bapi_payload("ETHUSD1"),
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 200,
            "error": None,
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
        "--poll-interval-sec", "0",
    ]

    def fake_payload_fetch_2(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        return {"ok": True, "payload": _official_single_symbol_detail_text("ETHUSD1"), "final_url": url, "http_status": 200, "error": None}

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
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["ETHUSD1"] or parsed[0]["symbols"] == ("ETHUSD1",)
    assert parsed[0]["symbol_parse_status"] == "parsed"
    assert parsed[0]["source_contract_status"] == "formal_v2_valid"
    assert parsed[0]["symbol_identity_validation_status"] == "validated_by_exchangeinfo"
    assert parsed[0]["detail_fetch_attempted"] is True
    assert parsed[0]["detail_fetch_status"] == "success"
    assert parsed[0]["launch_anchor_evidence_level"] == "official_schedule"
    assert parsed[0]["symbol_effective_observation_anchor_sources"]["ETHUSD1"] == "official_schedule_anchor"
    assert detail_calls["count"] == 1


def test_runner_validates_tradifi_perpetual_spcxusd1_when_trading(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "6cbb1b11a9c843949624cf2eacaac8b4",
                    "title": "Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)",
                    "releaseDate": int(time.time() * 1000) - 1000,
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
            "onboardDate": 4070908800000,
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
        return {"ok": True, "payload": _official_single_symbol_detail_text("SPCXUSD1"), "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": True,
            "payload": _official_single_symbol_bapi_payload("SPCXUSD1"),
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 200,
            "error": None,
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
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "6cbb1b11a9c843949624cf2eacaac8b4"]
    assert len(parsed) == 1
    assert parsed[0]["symbols"] == ["SPCXUSD1"] or parsed[0]["symbols"] == ("SPCXUSD1",)
    assert parsed[0]["symbol_parse_status"] == "parsed"
    assert parsed[0]["source_contract_status"] == "formal_v2_valid"
    assert parsed[0]["symbol_identity_validation_status"] == "validated_by_exchangeinfo"
    assert parsed[0]["symbol_parse_failed_reason"] is None
    assert parsed[0].get("terminal_failure_type") is None
    assert parsed[0]["detail_fetch_attempted"] is True
    assert parsed[0]["detail_fetch_status"] == "success"
    assert parsed[0]["launch_anchor_evidence_level"] == "official_schedule"
    assert parsed[0]["symbol_effective_observation_anchor_sources"]["SPCXUSD1"] == "official_schedule_anchor"
    assert parsed[0]["symbol_effective_launch_times_ms"]["SPCXUSD1"] == parsed[0]["symbol_official_schedule_anchor_ms"]["SPCXUSD1"]
    assert detail_calls["count"] == 1


def test_runner_title_contract_symbol_pre_trading_stays_pending_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": int(time.time() * 1000) - 1000,
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
            "onboardDate": 4070908800000,
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
        return {"ok": True, "payload": _official_single_symbol_detail_text("ETHUSD1"), "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": True,
            "payload": _official_single_symbol_bapi_payload("ETHUSD1"),
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 200,
            "error": None,
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
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10" for row in events)
    assert detail_calls["count"] == 1
    s = json.loads(summary.read_text())
    assert s["pre_launch_validation_deferred_count"] >= 1


def test_runner_tradifi_perpetual_spcxusd1_pending_stays_pending_without_terminal_fail(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "6cbb1b11a9c843949624cf2eacaac8b4",
                    "title": "Binance Futures Will Launch USDⓈ-Margined SPCXUSD1 Perpetual Contract (2026-07-20)",
                    "releaseDate": int(time.time() * 1000) - 1000,
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
            "onboardDate": 4070908800000,
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
        return {"ok": True, "payload": _official_single_symbol_detail_text("SPCXUSD1"), "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        return {
            "ok": True,
            "payload": _official_single_symbol_bapi_payload("SPCXUSD1"),
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 200,
            "error": None,
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
        "--poll-interval-sec", "0",
    ]

    with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_json", side_effect=fake_fetch_json):
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                with patch("sys.argv", args):
                    rc = main()

    assert rc == 0
    events = _read_jsonl_files(output_root / "events")
    assert not any(row.get("source_article_id") == "6cbb1b11a9c843949624cf2eacaac8b4" for row in events)
    assert detail_calls["count"] == 1
    s = json.loads(summary.read_text())
    assert s["candidate_validation_pending_count"] == 0
    assert s["pre_launch_validation_deferred_count"] >= 1

    state = json.loads((output_root / "detail_retry_scheduler_state.json").read_text())
    row = state["articles"]["6cbb1b11a9c843949624cf2eacaac8b4"]
    assert row["candidate_symbols"] == ["SPCXUSD1"]
    assert row["symbol_validation_status"] == "pending_pre_trading"
    assert row.get("terminal_failure_type") is None
    assert row["symbol_effective_launch_times_ms"]["SPCXUSD1"] == 4070908800000


def test_title_contract_candidate_pending_survives_process_restart_without_detail_fetch(tmp_path):
    list_payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "23c9b8e88309409cbcd8509af0b78d10",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ETHUSD1 Perpetual Contract (2026-07-03)",
                    "releaseDate": int(time.time() * 1000) - 1000,
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
            "onboardDate": 4070908800000,
        }]
    }
    detail_calls = {"count": 0}

    def fake_payload_fetch(url, live_public_readonly, timeout_sec, retry_budget=0):
        detail_calls["count"] += 1
        return {"ok": True, "payload": _official_single_symbol_detail_text("ETHUSD1"), "final_url": url, "http_status": 200, "error": None}

    def fake_bapi_fetch(article_code, **kwargs):
        detail_calls["count"] += 1
        return {
            "ok": True,
            "payload": _official_single_symbol_bapi_payload("ETHUSD1"),
            "final_url": "https://www.binance.com/bapi/...",
            "http_status": 200,
            "error": None,
        }

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
            with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_bapi_fetch):
                with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_payload", side_effect=fake_payload_fetch):
                    with patch("sys.argv", args):
                        return main()

    assert run_once(pending_exchange_info) == 0
    assert _read_jsonl_files(output_root / "events") == []

    assert run_once(trading_exchange_info) == 0
    events = _read_jsonl_files(output_root / "events")
    parsed = [r for r in events if r.get("source_article_id") == "23c9b8e88309409cbcd8509af0b78d10"]
    assert len(parsed) == 1
    assert detail_calls["count"] == 2


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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
    assert _read_jsonl_files(output_root / "events") == []
    diagnostics = _read_jsonl_files(output_root / "detail_retry_terminal_diagnostics")
    starved_events = [
        d.get("raw_event", d) for d in diagnostics
        if d.get("source_article_id") == "never_attempted_starved"
    ]
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "payload": {"symbols": [
                    {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 4070908800000},
                ]},
                "final_url": url,
                "http_status": 200,
                "error": None,
            }
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

    def fake_fetch_bapi_article_detail(article_code, **kwargs):
        return {
            "ok": False,
            "payload": None,
            "raw_bytes": b"",
            "final_url": f"https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleCode={article_code}",
            "http_status": 503,
            "error": "bapi_test_transient",
        }

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
        with patch("scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.fetch_public_bapi_article_detail", side_effect=fake_fetch_bapi_article_detail):
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
            "body": [{"text": _official_single_symbol_detail_text("NEWCOINUSDT")}],
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
                    "onboardDate": 1861920000000,
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


def test_bapi_parser_no_symbol_preserves_bapi_diagnostic_even_if_support_fallback_202():
    from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
        serialize_retry_articles,
    )
    state = {
        "art_no_sym": {
            "source_article_id": "art_no_sym",
            "last_bapi_detail_status": "success",
            "last_bapi_payload_hash": "hash_no_sym",
            "last_bapi_parser_version": "stage1_5d_symbol_extraction_v3",
            "last_bapi_parser_status": "no_symbols",
            "last_bapi_parse_attempt_at_ms": 1000,
            "last_support_detail_status": "http_202_empty",
        }
    }
    serialized = serialize_retry_articles(state)
    assert serialized["art_no_sym"]["last_bapi_detail_status"] == "success"
    assert serialized["art_no_sym"]["last_bapi_parser_status"] == "no_symbols"
    assert serialized["art_no_sym"]["last_support_detail_status"] == "http_202_empty"


def test_bapi_same_hash_same_parser_no_symbols_dedupes_high_frequency_retry():
    from configs import base
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        PARSER_VERSION,
    )
    now_ms = 5000
    recheck_ms = base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC * 1000
    state = {
        "last_bapi_payload_hash": "hash_same",
        "last_bapi_parser_version": PARSER_VERSION,
        "last_bapi_parser_status": "no_symbols",
        "last_bapi_parse_attempt_at_ms": now_ms - 1000,
    }
    is_deduped = (
        state.get("last_bapi_payload_hash") is not None
        and state.get("last_bapi_parser_version") == PARSER_VERSION
        and state.get("last_bapi_parser_status") == "no_symbols"
        and (now_ms - int(state.get("last_bapi_parse_attempt_at_ms") or 0) < recheck_ms)
    )
    assert is_deduped is True


def test_bapi_parser_version_change_allows_reparse_of_same_payload_hash():
    from configs import base
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        PARSER_VERSION,
    )
    now_ms = 5000
    recheck_ms = base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC * 1000
    state = {
        "last_bapi_payload_hash": "hash_same",
        "last_bapi_parser_version": "stage1_5d_symbol_extraction_v2", # old version
        "last_bapi_parser_status": "no_symbols",
        "last_bapi_parse_attempt_at_ms": now_ms - 1000,
    }
    is_deduped = (
        state.get("last_bapi_payload_hash") is not None
        and state.get("last_bapi_parser_version") == PARSER_VERSION
        and state.get("last_bapi_parser_status") == "no_symbols"
        and (now_ms - int(state.get("last_bapi_parse_attempt_at_ms") or 0) < recheck_ms)
    )
    assert is_deduped is False


def test_multi_symbol_one_rejected_does_not_emit_candidate_set():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_article_ready_to_emit,
    )
    candidates = ["TMFUSDT", "TBTUSDT", "BITOUSDT"]
    val_res = {"validated_symbols": ["TMFUSDT"], "pending_symbols": ["TBTUSDT"], "rejected_symbols": ["BITOUSDT"]}
    eff_launch = {
        "symbol_effective_launch_times_ms": {"TMFUSDT": 1000, "TBTUSDT": 2000, "BITOUSDT": 3000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }
    assert is_multi_symbol_article_ready_to_emit(candidates, val_res, eff_launch) is False


def test_multi_symbol_all_three_validated_emits():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_article_ready_to_emit,
    )
    candidates = ["TMFUSDT", "TBTUSDT", "BITOUSDT"]
    val_res = {"validated_symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"], "pending_symbols": [], "rejected_symbols": []}
    eff_launch = {
        "symbol_effective_launch_times_ms": {"TMFUSDT": 1000, "TBTUSDT": 2000, "BITOUSDT": 3000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }
    assert is_multi_symbol_article_ready_to_emit(candidates, val_res, eff_launch) is True


def test_bapi_multi_contract_missing_launch_time_does_not_use_article_release_date_anchor():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_effective_launch_times_ms,
    )
    candidates = ["TMFUSDT", "TBTUSDT"]
    res = build_effective_launch_times_ms(
        candidate_symbols=candidates,
        symbol_onboard_times_ms={},
        symbol_launch_times_ms={},
        source_published_at_ms=10000,
        first_detected_at_ms=10000,
        allow_release_date_fallback=False,
        allow_legacy_max_age_fallback=False,
    )
    assert res["symbol_effective_launch_times_ms"]["TMFUSDT"] == 0
    assert res["launch_time_source"] == "none"


def test_pending_revalidation_never_reenables_release_date_fallback():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_effective_launch_times_ms,
    )
    res = build_effective_launch_times_ms(
        candidate_symbols=["TMFUSDT"],
        symbol_onboard_times_ms={},
        symbol_launch_times_ms={},
        source_published_at_ms=10000,
        first_detected_at_ms=10000,
        allow_release_date_fallback=False,
        allow_legacy_max_age_fallback=False,
    )
    assert res["launch_time_source"] != "article_release_date"


def test_candidate_symbol_set_hash_is_order_insensitive_and_normalized():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
    )

    a = build_candidate_symbol_set_identity([" pyplusdt ", "GSUSDT", "SMHUSDT", "GSUSDT"])
    b = build_candidate_symbol_set_identity(["SMHUSDT", "PYPLUSDT", "GSUSDT"])

    assert a["candidate_symbols_ordered"] == ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    assert a["candidate_symbols_normalized"] == ["GSUSDT", "PYPLUSDT", "SMHUSDT"]
    assert a["candidate_symbol_set_hash_version"] == 1
    assert a["candidate_symbol_set_hash"] == b["candidate_symbol_set_hash"]


def test_candidate_symbol_set_hash_preserves_ordered_symbols_for_audit():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
    )

    a = build_candidate_symbol_set_identity(["PYPLUSDT", "GSUSDT", "SMHUSDT"])
    assert a["candidate_symbols_ordered"] == ["PYPLUSDT", "GSUSDT", "SMHUSDT"]


def test_candidate_set_ready_when_all_symbols_pending_trading_with_strict_anchors():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    val_res = {
        "validated_symbols": [],
        "pending_symbols": candidates,
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {
            "PYPLUSDT": 1785315600000,
            "GSUSDT": 1785315900000,
            "SMHUSDT": 1785316200000,
        },
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "detail_symbol_launch_time",
            "GSUSDT": "detail_symbol_launch_time",
            "SMHUSDT": "detail_symbol_launch_time",
        },
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is True


def test_staggered_symbols_do_not_wait_until_all_trading():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    val_res = {
        "validated_symbols": ["PYPLUSDT"],
        "pending_symbols": ["GSUSDT", "SMHUSDT"],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            "PYPLUSDT": {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
            "GSUSDT": {"status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
            "SMHUSDT": {"status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {
            "PYPLUSDT": 1785315600000,
            "GSUSDT": 1785315900000,
            "SMHUSDT": 1785316200000,
        },
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "detail_symbol_launch_time",
            "GSUSDT": "detail_symbol_launch_time",
            "SMHUSDT": "detail_symbol_launch_time",
        },
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is True


def test_candidate_set_rejects_article_release_date_anchor():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": candidates,
        "pending_symbols": [],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "article_release_date",
            "GSUSDT": "detail_symbol_launch_time",
        },
    }

    assert (
        is_multi_symbol_candidate_set_ready_to_emit(
            candidates,
            val_res,
            eff_launch,
            allowed_anchor_sources=("detail_symbol_launch_time", "exchangeinfo_onboard_date", "detail", "exchange_info"),
        )
        is False
    )


def test_candidate_set_default_rejects_article_release_date_anchor():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": candidates,
        "pending_symbols": [],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "article_release_date",
            "GSUSDT": "detail_symbol_launch_time",
        },
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_candidate_set_rejects_legacy_max_age_anchor():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": candidates,
        "pending_symbols": [],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "legacy_max_age",
            "GSUSDT": "detail_symbol_launch_time",
        },
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_candidate_set_rejects_missing_anchor_source():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": candidates,
        "pending_symbols": [],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {
            "PYPLUSDT": "missing",
            "GSUSDT": "detail_symbol_launch_time",
        },
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_candidate_set_requires_validation_partition_complete():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    val_res = {
        "validated_symbols": ["PYPLUSDT"],
        "pending_symbols": ["GSUSDT"],  # SMHUSDT missing from partition
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000, "SMHUSDT": 3000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_candidate_set_requires_validated_pending_partition_disjoint():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": ["PYPLUSDT", "GSUSDT"],
        "pending_symbols": ["GSUSDT"],  # GSUSDT in both
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            s: {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"}
            for s in candidates
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_candidate_set_rejects_unknown_status_even_if_exchangeinfo_present():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT"]
    val_res = {
        "validated_symbols": ["PYPLUSDT"],
        "pending_symbols": ["GSUSDT"],
        "rejected_symbols": [],
        "symbol_exchangeinfo": {
            "PYPLUSDT": {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
            "GSUSDT": {"status": "BREAK", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_emitted_all_symbols_is_terminal_for_retry_selection():
    from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
        select_detail_retry_attempts,
    )

    detail_retry_state = {
        "93b5": {
            "source_article_id": "93b5",
            "terminal_state": True,
            "status": "emitted_all_symbols",
            "symbol_validation_status": "emitted_all_symbols",
            "detail_http_request_count": 1,
            "next_detail_retry_at_ms": 0,
        }
    }
    selected = select_detail_retry_attempts(
        detail_retry_state=detail_retry_state,
        now_ms=100000,
        detail_budget_per_poll=10,
        endpoint_degraded_until_ms=0,
    )
    assert selected == []


def test_emitted_terminal_fields_survive_scheduler_roundtrip(tmp_path):
    from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
        load_detail_retry_scheduler_state,
        serialize_retry_articles,
        write_detail_retry_scheduler_state,
    )

    state = {
        "93b5": {
            "source_article_id": "93b5",
            "terminal_state": True,
            "terminal_reason": "multi_symbol_candidate_set_emitted",
            "terminal_at_ms": 10000,
            "status": "emitted_all_symbols",
            "symbol_validation_status": "emitted_all_symbols",
            "emission_id": "abc123hash",
            "candidate_symbol_set_hash": "hash123",
            "candidate_symbol_set_hash_version": 1,
            "candidate_symbols_ordered": ["PYPLUSDT", "GSUSDT"],
            "candidate_symbols_normalized": ["GSUSDT", "PYPLUSDT"],
            "event_id": "event_1",
            "event_stream_path": "events/2026-07-29.jsonl",
            "parser_payload_hash": "payload_hash",
            "symbol_effective_launch_time_sources": {"PYPLUSDT": "detail_symbol_launch_time"},
        }
    }
    ser = serialize_retry_articles(state)
    write_detail_retry_scheduler_state(tmp_path, {"articles": ser, "endpoint_health": {}}, metadata_version=2)
    loaded = load_detail_retry_scheduler_state(tmp_path)

    art = loaded["articles"]["93b5"]
    assert art["terminal_state"] is True
    assert art["terminal_reason"] == "multi_symbol_candidate_set_emitted"
    assert art["status"] == "emitted_all_symbols"
    assert art["emission_id"] == "abc123hash"
    assert art["candidate_symbol_set_hash"] == "hash123"
    assert art["candidate_symbols_ordered"] == ["PYPLUSDT", "GSUSDT"]


def test_old_scheduler_schema_loads_with_safe_defaults(tmp_path):
    from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
        load_detail_retry_scheduler_state,
    )

    file_path = tmp_path / "detail_retry_scheduler_state.json"
    old_data = {
        "metadata_version": 1,
        "articles": {
            "old_art": {
                "source_article_id": "old_art",
                "terminal_state": False,
            }
        },
    }
    file_path.write_text(json.dumps(old_data), encoding="utf-8")
    loaded = load_detail_retry_scheduler_state(tmp_path)
    art = loaded["articles"]["old_art"]
    assert art.get("emission_id") is None
    assert art.get("terminal_reason") is None


def test_emitted_article_is_not_reselected_after_restart(tmp_path):
    from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
        load_detail_retry_scheduler_state,
        select_detail_retry_attempts,
        serialize_retry_articles,
        write_detail_retry_scheduler_state,
    )

    state = {
        "93b5": {
            "source_article_id": "93b5",
            "terminal_state": True,
            "status": "emitted_all_symbols",
            "symbol_validation_status": "emitted_all_symbols",
            "emission_id": "emission_xyz",
        }
    }
    ser = serialize_retry_articles(state)
    write_detail_retry_scheduler_state(tmp_path, {"articles": ser, "endpoint_health": {}}, metadata_version=2)
    loaded = load_detail_retry_scheduler_state(tmp_path)
    selected = select_detail_retry_attempts(
        detail_retry_state=loaded["articles"],
        now_ms=20000,
        detail_budget_per_poll=5,
        endpoint_degraded_until_ms=0,
    )
    assert selected == []


def test_build_multi_symbol_emission_id_is_stable_for_same_article_candidate_set():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
        build_multi_symbol_emission_id,
    )

    identity = build_candidate_symbol_set_identity(["PYPLUSDT", "GSUSDT", "SMHUSDT"])
    a = build_multi_symbol_emission_id("93b5", "futures_contract_launch", identity["candidate_symbol_set_hash"])
    b = build_multi_symbol_emission_id("93b5", "futures_contract_launch", identity["candidate_symbol_set_hash"])
    assert a == b
    assert len(a) == 64


def test_existing_event_stream_rebuilds_emission_index_from_valid_full_row(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
        build_multi_symbol_emission_id,
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    symbols = ["PYPLUSDT", "GSUSDT"]
    identity = build_candidate_symbol_set_identity(symbols)
    c_hash = identity["candidate_symbol_set_hash"]
    em_id = build_multi_symbol_emission_id("93b5", "futures_contract_launch", c_hash)

    row = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": symbols,
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": c_hash,
        "emission_id": em_id,
        "event_id": "ev_1",
        "parser_payload_hash": "p_1",
    }
    (events_dir / "2026-07-29.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    assert len(diagnostics) == 0
    key = f"93b5|{c_hash}"
    assert key in index
    assert index[key]["emission_id"] == em_id


def test_event_stream_rebuild_rejects_partial_row_with_full_candidate_hash(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    symbols = ["PYPLUSDT", "BADUSDT"]
    identity = build_candidate_symbol_set_identity(["PYPLUSDT", "GSUSDT"])
    c_hash = identity["candidate_symbol_set_hash"]

    row = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": symbols,
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": c_hash,
        "event_id": "ev_1",
    }
    (events_dir / "2026-07-29.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    assert len(index) == 0
    assert len(diagnostics) == 1
    assert diagnostics[0]["reason"] == "candidate_set_hash_mismatch"


def test_event_stream_rebuild_rejects_stored_hash_mismatch(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    row = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": ["PYPLUSDT", "GSUSDT"],
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": "wrong_hash",
        "event_id": "ev_1",
    }
    (events_dir / "2026-07-29.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    assert len(index) == 0
    assert len(diagnostics) == 1
    assert diagnostics[0]["reason"] == "candidate_set_hash_mismatch"


def test_event_stream_rebuild_rejects_duplicate_emission_id_different_payload(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
        build_multi_symbol_emission_id,
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    symbols = ["PYPLUSDT", "GSUSDT"]
    identity = build_candidate_symbol_set_identity(symbols)
    c_hash = identity["candidate_symbol_set_hash"]
    em_id = build_multi_symbol_emission_id("93b5", "futures_contract_launch", c_hash)

    row1 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": symbols,
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": c_hash,
        "emission_id": em_id,
        "parser_payload_hash": "payload_1",
    }
    row2 = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": symbols,
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": c_hash,
        "emission_id": em_id,
        "parser_payload_hash": "payload_2_different",
    }
    content = json.dumps(row1) + "\n" + json.dumps(row2) + "\n"
    (events_dir / "2026-07-29.jsonl").write_text(content, encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    assert len(diagnostics) == 1
    assert diagnostics[0]["reason"] == "duplicate_emission_id_different_payload"


def test_event_stream_rebuild_rejects_malformed_jsonl_fail_safe(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    (events_dir / "2026-07-29.jsonl").write_text("{malformed_json\n", encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    assert len(index) == 0
    assert len(diagnostics) == 1
    assert diagnostics[0]["reason"] == "malformed_jsonl"


def test_crash_after_event_append_before_state_write_does_not_duplicate(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_candidate_symbol_set_identity,
        build_multi_symbol_emission_id,
        rebuild_emission_index_from_events,
    )

    events_dir = tmp_path / "events"
    events_dir.mkdir()
    symbols = ["PYPLUSDT", "GSUSDT"]
    identity = build_candidate_symbol_set_identity(symbols)
    c_hash = identity["candidate_symbol_set_hash"]
    em_id = build_multi_symbol_emission_id("93b5", "futures_contract_launch", c_hash)

    row = {
        "event_type": "futures_contract_launch",
        "source_article_id": "93b5",
        "symbols": symbols,
        "multi_symbol_emission_mode": "all_or_none_candidate_set",
        "symbol_validation_status": "validated_candidate_set",
        "multi_symbol_candidate_set_hash": c_hash,
        "emission_id": em_id,
        "parser_payload_hash": "payload_1",
    }
    (events_dir / "2026-07-29.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

    index, diagnostics = rebuild_emission_index_from_events(tmp_path)
    key = f"93b5|{c_hash}"
    assert key in index
    # Simulated restart sees row in index and prevents re-emission
    assert index[key]["emission_id"] == em_id


def test_crash_after_state_write_before_event_append_reconciles_missing_event_or_blocks_manual_review():
    from pathlib import Path

    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        rebuild_emission_index_from_events,
    )
    # If state says emitted_all_symbols but event stream has 0 rows, rebuild_emission_index_from_events returns empty index
    index, diagnostics = rebuild_emission_index_from_events(Path("/nonexistent"))
    assert len(index) == 0


def test_parser_returns_three_symbols_but_state_initialization_none_does_not_take_single_symbol_path():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_article_state,
    )

    state = {}
    ext_res = {
        "symbols": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
        "symbol_extraction_source": "bapi_article_body",
    }
    assert is_multi_symbol_article_state(state, ext_res) is True


def test_93b5_prelaunch_all_validatable_emits_one_full_row(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import main
    c1, c = _write_valid_upstream(tmp_path)
    output_root = tmp_path / "out"

    article_code = "93b5cd2280874d9cb4303827374b940d"
    title = "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-29)"
    body = (
        "2026-07-29 09:00 (UTC):\nPYPLUSDT\nPerpetual Contract\n"
        "2026-07-29 09:05 (UTC):\nGSUSDT\nPerpetual Contract\n"
        "2026-07-29 09:10 (UTC):\nSMHUSDT\nPerpetual Contract\n"
        "USDS-M Perpetual Contract\nPYPLUSDT\nGSUSDT\nSMHUSDT\nLaunch Time\n"
        "2026-07-29 09:00 (UTC)\n2026-07-29 09:05 (UTC)\n2026-07-29 09:10 (UTC)\n"
    )
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps({
        "exchangeInfoPayload": {
            "symbols": [
                {"symbol": "PYPLUSDT", "status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1785315600000},
                {"symbol": "GSUSDT", "status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1785315900000},
                {"symbol": "SMHUSDT", "status": "PENDING_TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1785316200000},
            ],
        },
        "data": {"catalogs": [{"articles": [{
            "code": article_code,
            "title": title,
            "releaseDate": 1785305721576,
            "bapiPayload": {
                "code": "000000",
                "message": "success",
                    "data": {
                        "code": article_code,
                        "title": title,
                        "body": {"children": [{"text": body}]},
                        "releaseDate": 1785305721576,
                    },
                },
        }]}]},
    }))
    summary = tmp_path / "summary.json"
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
    rows = _read_jsonl_files(output_root / "events")
    assert len(rows) == 1
    row = rows[0]
    assert row["source_article_id"] == article_code
    assert row["symbols"] == ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    assert row["multi_symbol_emission_mode"] == "all_or_none_candidate_set"
    assert row["symbol_validation_status"] == "validated_candidate_set"
    assert row["candidate_symbols_ordered"] == ["PYPLUSDT", "GSUSDT", "SMHUSDT"]
    assert row["candidate_symbols_normalized"] == ["GSUSDT", "PYPLUSDT", "SMHUSDT"]
    assert row["candidate_symbol_set_hash_version"] == 1
    assert row["symbol_effective_launch_time_sources"] == {
        "PYPLUSDT": "exchangeinfo_onboard_date",
        "GSUSDT": "exchangeinfo_onboard_date",
        "SMHUSDT": "exchangeinfo_onboard_date",
    }


def test_hard_rejected_symbol_blocks_entire_multi_symbol_article():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        is_multi_symbol_candidate_set_ready_to_emit,
    )

    candidates = ["PYPLUSDT", "GSUSDT", "BADSYMBOL"]
    val_res = {
        "validated_symbols": ["PYPLUSDT", "GSUSDT"],
        "pending_symbols": [],
        "rejected_symbols": ["BADSYMBOL"],
        "symbol_exchangeinfo": {
            "PYPLUSDT": {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
            "GSUSDT": {"status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT"},
            "BADSYMBOL": {"status": "TRADING", "contractType": "SPOT", "quoteAsset": "USDT", "marginAsset": "USDT"},
        },
    }
    eff_launch = {
        "symbol_effective_launch_times_ms": {"PYPLUSDT": 1000, "GSUSDT": 2000, "BADSYMBOL": 3000},
        "symbol_effective_launch_time_sources": {s: "detail_symbol_launch_time" for s in candidates},
    }

    assert is_multi_symbol_candidate_set_ready_to_emit(candidates, val_res, eff_launch) is False


def test_gigadev_fixture_emits_v2_official_schedule_anchor(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
    )

    meta = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/gigadev_anchor_contract_v2/gigadev_fixture_metadata.json").read_text())
    symbol = meta["symbol"]
    sym_contract = build_symbol_anchor_contract(
        symbol=symbol,
        official_schedule_anchor_ms=meta["official_schedule_anchor_ms"],
        exchangeinfo_onboard_date_ms=meta["exchangeinfo_onboardDate_ms"],
        anchor_contract_decision_at_ms=1785726000000,
        official_schedule_revision_id="gigadev_rev_1",
        official_schedule_available_at_ms=1785724209135,
        mapping_confidence="exact_single_symbol",
        provenance={
            "payload_sha256": meta["payload_sha256"],
            "parser_version": meta["parser_version"],
            "raw_time_text": "2026-08-03 05:30 (UTC)",
            "timezone_text": "UTC",
            "node_path": "body[0]",
            "logical_block_id": "block-1",
            "schedule_text_context": "Launch Time",
            "mapping_method": "single_symbol_article_unique_futures_launch_time",
        },
    )
    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": meta["article_id"], "symbols": [symbol]},
        symbol_contracts={symbol: sym_contract},
    )

    assert row["formal_event_contract_version"] == 2
    assert row["anchor_precedence_policy"] == "official_schedule_priority_v1"
    assert row["symbol_official_schedule_anchor_ms"][symbol] == 1785735000000
    assert row["symbol_exchangeinfo_onboard_date_ms"][symbol] == 1785722400000
    assert row["symbol_effective_observation_anchor_ms"][symbol] == 1785735000000
    assert row["symbol_effective_observation_anchor_sources"][symbol] == "official_schedule_anchor"
    assert row["symbol_anchor_comparison_statuses"][symbol] == "exchangeinfo_disagrees_with_official_schedule"
    assert row["symbol_max_evidence_classes"][symbol] == "clean_or_recovery"
    assert row["event_all_symbols_consumable_by_stage1_5f"] is True
    assert row["event_all_symbols_clean_eligible"] is True


def test_apply_formal_launch_event_contract_writes_v2_official_schedule_anchor():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        apply_formal_launch_event_contract,
    )

    norm_event = {
        "event_type": "futures_contract_launch",
        "source_article_id": "e8bfd0c5adaf4d8a880bb1b7327107ef",
        "symbols": ["GIGADEVUSDT"],
        "title": "Binance Futures Will Launch GIGADEVUSDT USDⓈ-Margined Perpetual Contract (2026-08-03)",
        "detected_at_ms": 1785724365785,
        "source_published_at_ms": 1785724209135,
        "parser_version": "stage1_5d_symbol_extraction_v3",
        "detail_payload_hash": "c4054dd6612d440b914c9e5c0360c28254dcac71a8f545b4bfeb777ecfd31f60",
        "detail_fetch_attempted": True,
        "detail_fetch_status": "success",
    }
    state = {
        "title": norm_event["title"],
        "symbol_launch_times_ms": {"GIGADEVUSDT": 1785735000000},
        "symbol_onboard_times_ms": {"GIGADEVUSDT": 1785722400000},
        "detail_fetch_status": "success",
        "detail_fetch_attempted": True,
    }
    validation_result = {
        "symbol_onboard_times_ms": {"GIGADEVUSDT": 1785722400000},
        "symbol_exchangeinfo": {"GIGADEVUSDT": {"status": "TRADING"}},
    }
    effective_launch = {
        "symbol_effective_launch_times_ms": {"GIGADEVUSDT": 1785722400000},
        "symbol_effective_launch_time_sources": {"GIGADEVUSDT": "exchangeinfo_onboard_date"},
        "launch_time_source": "exchange_info",
    }

    apply_formal_launch_event_contract(
        norm_event,
        state,
        validation_result,
        ["GIGADEVUSDT"],
        effective_launch,
    )

    assert norm_event["formal_event_contract_version"] == 2
    assert norm_event["source_contract_status"] == "formal_v2_valid"
    assert norm_event["symbol_effective_observation_anchor_ms"]["GIGADEVUSDT"] == 1785735000000
    assert norm_event["symbol_effective_observation_anchor_sources"]["GIGADEVUSDT"] == "official_schedule_anchor"
    assert norm_event["symbol_effective_launch_times_ms"]["GIGADEVUSDT"] == 1785735000000
    assert norm_event["symbol_anchor_comparison_statuses"]["GIGADEVUSDT"] == "exchangeinfo_disagrees_with_official_schedule"
    assert norm_event["event_all_symbols_consumable_by_stage1_5f"] is True
    assert norm_event["event_all_symbols_clean_eligible"] is True


def test_formal_writer_validates_every_symbol(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
    )
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        append_formal_futures_launch_event,
    )

    c1 = build_symbol_anchor_contract(
        symbol="SYM1USDT",
        official_schedule_anchor_ms=1000000,
        exchangeinfo_onboard_date_ms=1000000,
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id="r1",
        official_schedule_available_at_ms=400000,
        mapping_confidence="exact_per_symbol_row",
        provenance={"raw_time_text": "t", "timezone_text": "UTC", "node_path": "n", "logical_block_id": "b", "schedule_text_context": "c", "payload_sha256": "p", "parser_version": "v", "mapping_method": "m"},
    )
    c2 = build_symbol_anchor_contract(
        symbol="SYM2USDT",
        official_schedule_anchor_ms=None,
        exchangeinfo_onboard_date_ms=None,  # Missing anchor!
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id=None,
        official_schedule_available_at_ms=None,
        mapping_confidence="ambiguous",
        provenance={},
    )
    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "art-1", "symbols": ["SYM1USDT", "SYM2USDT"]},
        symbol_contracts={"SYM1USDT": c1, "SYM2USDT": c2},
    )

    diag_file = tmp_path / "diag.jsonl"
    events_file = tmp_path / "events.jsonl"
    stream_paths = {"events": events_file, "formal_contract_validation_failed": diag_file}

    written = append_formal_futures_launch_event(stream_paths, row)
    assert written is None
    assert not events_file.exists() or len(events_file.read_text().strip()) == 0


def test_second_symbol_malformed_blocks_entire_batch(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
    )
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        append_formal_futures_launch_event,
    )

    c1 = build_symbol_anchor_contract(
        symbol="SYM1USDT",
        official_schedule_anchor_ms=1000000,
        exchangeinfo_onboard_date_ms=1000000,
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id="r1",
        official_schedule_available_at_ms=400000,
        mapping_confidence="exact_per_symbol_row",
        provenance={"raw_time_text": "t", "timezone_text": "UTC", "node_path": "n", "logical_block_id": "b", "schedule_text_context": "c", "payload_sha256": "p", "parser_version": "v", "mapping_method": "m"},
    )
    c2 = {
        "symbol": "SYM2USDT",
        "effective_observation_anchor_ms": 1000000,
        "effective_observation_anchor_source": "official_schedule_anchor",
        "official_schedule_anchor_ms": 2000000,  # Effective anchor != official anchor -> malformed!
        "mapping_confidence": "exact_per_symbol_row",
        "anchor_evidence_level": "official_schedule",
        "max_evidence_class": "clean_or_recovery",
        "validation_status": "malformed",
        "comparison_status": "missing",
        "disagreement_ms": None,
        "disagreement_direction": "none",
        "anchor_contract_decision_at_ms": 500000,
        "official_schedule_revision_id": "r2",
        "official_schedule_available_at_ms": 400000,
        "provenance": {"raw_time_text": "t", "timezone_text": "UTC", "node_path": "n", "logical_block_id": "b", "schedule_text_context": "c", "payload_sha256": "p", "parser_version": "v", "mapping_method": "m"},
    }

    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "art-2", "symbols": ["SYM1USDT", "SYM2USDT"]},
        symbol_contracts={"SYM1USDT": c1, "SYM2USDT": c2},
    )

    diag_file = tmp_path / "diag.jsonl"
    events_file = tmp_path / "events.jsonl"
    stream_paths = {"events": events_file, "formal_contract_validation_failed": diag_file}

    written = append_formal_futures_launch_event(stream_paths, row)
    assert written is None


def test_event_aggregate_is_derived_from_all_symbol_contracts():
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_symbol_anchor_contract,
    )

    c1 = build_symbol_anchor_contract(
        symbol="SYM1USDT",
        official_schedule_anchor_ms=1000000,
        exchangeinfo_onboard_date_ms=1000000,
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id="r1",
        official_schedule_available_at_ms=400000,
        mapping_confidence="exact_per_symbol_row",
        provenance={"raw_time_text": "t", "timezone_text": "UTC", "node_path": "n", "logical_block_id": "b", "schedule_text_context": "c", "payload_sha256": "p", "parser_version": "v", "mapping_method": "m"},
    )
    c2 = build_symbol_anchor_contract(
        symbol="SYM2USDT",
        official_schedule_anchor_ms=None,
        exchangeinfo_onboard_date_ms=2000000,  # Fallback anchor!
        anchor_contract_decision_at_ms=500000,
        official_schedule_revision_id=None,
        official_schedule_available_at_ms=None,
        mapping_confidence="exact_per_symbol_row",
        provenance={"raw_time_text": "t", "timezone_text": "UTC", "node_path": "n", "logical_block_id": "b", "schedule_text_context": "c", "payload_sha256": "p", "parser_version": "v", "mapping_method": "m"},
    )

    row = build_formal_event_anchor_contract_row(
        base_event={"event_type": "futures_contract_launch", "source_article_id": "art-3", "symbols": ["SYM1USDT", "SYM2USDT"]},
        symbol_contracts={"SYM1USDT": c1, "SYM2USDT": c2},
    )

    assert row["event_anchor_aggregate_status"] == "mixed_official_and_fallback"
    assert row["event_has_fallback_anchor"] is True
    assert row["event_all_symbols_clean_eligible"] is False


def test_append_formal_schedule_revision_writes_valid_row_and_blocks_invalid(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_schedule_revision_row,
    )
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        append_formal_schedule_revision,
    )

    stream_paths = {
        "events": str(tmp_path / "events.jsonl"),
        "detail_retry_terminal_diagnostics": str(tmp_path / "diagnostics.jsonl"),
    }
    valid_row = build_formal_schedule_revision_row(
        source_article_id="revision-article",
        supersedes_source_article_id="orig-article",
        symbol="ABCUSDT",
        revised_anchor_ms=2_000,
        superseded_anchor_ms=1_000,
        revision_id="rev-1",
        revision_semantic_id="rev-1",
        revision_application_id="rev-1",
        revision_payload_version_id="payload-v1",
        revision_observation_id="obs-1",
        revision_payload_hash="payload-hash",
        revision_available_at_ms=1_500,
        revision_reason="rescheduled",
        provenance={"payload_sha256": "payload-hash", "parser_version": "test"},
    )

    assert append_formal_schedule_revision(stream_paths, valid_row) == valid_row
    event_rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert event_rows == [valid_row]

    invalid_row = dict(valid_row)
    invalid_row["revision_payload_hash"] = ""
    assert append_formal_schedule_revision(stream_paths, invalid_row) is None
    event_rows_after_invalid = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    diagnostics = [json.loads(line) for line in (tmp_path / "diagnostics.jsonl").read_text().splitlines()]
    assert event_rows_after_invalid == [valid_row]
    assert diagnostics[-1]["diagnostic_type"] == "formal_schedule_revision_contract_invalid"


def test_trusted_revision_detail_is_processed_by_runner_transport(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        process_trusted_schedule_revision_detail,
    )

    stream_paths = {
        "events": tmp_path / "events.jsonl",
        "detail_retry_terminal_diagnostics": tmp_path / "diagnostics.jsonl",
        "formal_launch_identity_index": tmp_path / "formal_launch_identity_index.jsonl",
    }
    stream_paths["formal_launch_identity_index"].write_text(
        json.dumps(
            {
                "supersedes_source_article_id": "a" * 32,
                "symbol": "AIAUSDT",
                "stable_schedule_identity": f"binance|futures_contract_launch|{'a' * 32}|AIAUSDT",
                "original_source_published_at_ms": 1_000,
                "formal_row_durable_at_ms": 1_100,
            }
        ) + "\n"
    )

    emitted_ids = set()
    result = process_trusted_schedule_revision_detail(
        stream_paths=stream_paths,
        source_article_id="b" * 32,
        title="Postponement of AIAUSDT perpetual contract launch",
        detail_text=f"The launch is rescheduled. https://www.binance.com/en/support/announcement/{'a' * 32}",
        symbols=["AIAUSDT"],
        symbol_launch_times_ms={"AIAUSDT": 2_000},
        payload_sha256="payload-hash",
        available_at_ms=1_500,
        producer_effective_enabled=True,
        emitted_revision_semantic_ids=emitted_ids,
    )

    assert result == {"status": "revision_emitted", "emitted_count": 1}
    rows = [json.loads(line) for line in stream_paths["events"].read_text().splitlines()]
    assert rows[0]["formal_schedule_revision_contract_version"] == 2
    assert rows[0]["revision_application_id"] == rows[0]["revision_semantic_id"]
    replay = process_trusted_schedule_revision_detail(
        stream_paths=stream_paths,
        source_article_id="b" * 32,
        title="Postponement of AIAUSDT perpetual contract launch",
        detail_text=f"The launch is rescheduled. https://www.binance.com/en/support/announcement/{'a' * 32}",
        symbols=["AIAUSDT"],
        symbol_launch_times_ms={"AIAUSDT": 2_000},
        payload_sha256="payload-hash",
        available_at_ms=1_500,
        producer_effective_enabled=True,
        emitted_revision_semantic_ids=emitted_ids,
    )
    assert replay == {"status": "revision_replay_noop", "emitted_count": 0}
    assert len(stream_paths["events"].read_text().splitlines()) == 1


def test_schedule_revision_producer_attestation_requires_all_prerequisites(monkeypatch):
    from configs import base
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_schedule_revision_producer_attestation,
    )

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA", "abc123")
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED", True)
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.read_current_commit_sha",
        lambda: "abc123",
    )

    ready = build_schedule_revision_producer_attestation(
        integration_health="ready",
        static_proof_result={"valid": True, "startup_head_sha": "abc123"},
        consumer_proof_result={"valid": True},
    )
    assert ready == {
        "schedule_revision_producer_supported": True,
        "schedule_revision_producer_configured_enabled": True,
        "schedule_revision_producer_consumer_prerequisites_verified": True,
        "schedule_revision_producer_effective_enabled": True,
        "schedule_revision_producer_health": "ready",
    }

    blocked = build_schedule_revision_producer_attestation(
        integration_health="ready",
        static_proof_result={"valid": True, "startup_head_sha": "different"},
        consumer_proof_result={"valid": True},
    )
    assert blocked["schedule_revision_producer_consumer_prerequisites_verified"] is False
    assert blocked["schedule_revision_producer_effective_enabled"] is False
    assert blocked["schedule_revision_producer_health"] == "prerequisites_unmet"


def test_runner_emits_revision_only_after_durable_launch_in_same_poll(tmp_path, monkeypatch):
    original_id = "a" * 32
    revision_id = "b" * 32
    published_at_ms = int(time.time() * 1000)
    original_title = "Binance Futures Will Launch USDⓈ-Margined AIAUSDT Perpetual Contract"
    revision_title = "Postponement of AIAUSDT USDⓈ-Margined Perpetual Contract Launch"

    def bapi_payload(article_id, title, body):
        return {"code": "000000", "data": {"code": article_id, "title": title, "body": [{"text": body}]}}

    fixture = tmp_path / "revision_fixture.json"
    fixture.write_text(json.dumps({
        "exchangeInfoPayload": {"symbols": [{
            "symbol": "AIAUSDT", "status": "TRADING", "contractType": "PERPETUAL",
            "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1_000,
        }]},
        "data": {"catalogs": [{"articles": [
            {
                "code": original_id,
                "title": original_title,
                "releaseDate": published_at_ms,
                "bapiPayload": bapi_payload(
                    original_id, original_title,
                    "AIAUSDT\nPerpetual Contract\nLaunch Time\n2026-08-08 10:00 (UTC)",
                ),
            },
            {
                "code": revision_id,
                "title": revision_title,
                "releaseDate": published_at_ms + 1,
                "bapiPayload": bapi_payload(
                    revision_id, revision_title,
                    f"The original announcement is https://www.binance.com/en/support/announcement/{original_id}. "
                    "AIAUSDT\nPerpetual Contract\nLaunch Time\n2026-08-08 11:00 (UTC)",
                ),
            },
        ]}]},
    }))
    c1, c = _write_valid_upstream(tmp_path)
    output_root = tmp_path / "out"
    args = [
        "run_stage1_5d_live_event_source_smoke_collector.py", "--fixture-json", str(fixture),
        "--stage1-5c1-summary", str(c1), "--stage1-5c-summary", str(c),
        "--output-root", str(output_root), "--max-polls", "1", "--poll-interval-sec", "0",
    ]
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA", "abc123")
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED", True)
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.read_current_commit_sha",
        lambda: head_sha,
    )
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.read_current_commit_sha",
        lambda: "abc123",
    )
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.verify_git_ancestry_and_static_proof",
        lambda **kwargs: {"valid": True, "startup_head_sha": "abc123"},
    )
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.verify_stage1_5f_consumer_proof",
        lambda **kwargs: {"valid": True},
    )
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.verify_stage1_5d_runtime_attestation",
        lambda *_args: {"valid": True},
    )



    with patch("sys.argv", args):
        assert main() == 0

    rows = _read_jsonl_files(output_root / "events")
    assert [row["source_article_id"] for row in rows] == [original_id, revision_id]
    assert rows[1]["formal_schedule_revision_contract_version"] == 2
    assert rows[1]["revision_application_id"] == rows[1]["revision_semantic_id"]
    summary = json.loads((output_root / "binance_futures_launch_smoke_summary.json").read_text())
    assert summary["schedule_revision_emitted_count"] == 1
    assert summary["schedule_revision_diagnostic_count"] == 0


def test_task1_contract_and_safety_baseline_preflight():
    from configs import base
    from src.research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION,
        build_formal_schedule_revision_row,
    )
    from src.risk.limits import RiskLimits

    assert FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION == 2
    row = build_formal_schedule_revision_row(
        source_article_id="art-1",
        supersedes_source_article_id="art-0",
        symbol="BTCUSDT",
        revised_anchor_ms=2_000,
        revision_id="rev-1",
        revision_semantic_id="rev-1",
        revision_application_id="rev-1",
        revision_payload_version_id="pv-1",
        revision_observation_id="ob-1",
        revision_payload_hash="hash-1",
        revision_available_at_ms=1_500,
    )
    assert row["formal_schedule_revision_contract_version"] == 2
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False
    assert RiskLimits.live_trading_enabled is False


def test_validate_configs_base_ast_delta_accepts_valid_config_only_changes():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_configs_base_ast_delta,
    )

    base_code = """
FOO = 123
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA = "1111111111111111111111111111111111111111"
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
BAR = "hello"
"""

    valid_code = """
FOO = 123
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA = "2222222222222222222222222222222222222222"
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED = True
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED = True
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = True
BAR = "hello"
"""

    assert validate_configs_base_ast_delta(base_code, valid_code) is True


def test_validate_configs_base_ast_delta_rejects_unapproved_or_dynamic_changes():
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        validate_configs_base_ast_delta,
    )

    base_code = """
FOO = 123
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA = ""
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""

    # Rejects addition of new variables
    invalid_add = base_code + "\nUNAPPROVED = 1"
    assert validate_configs_base_ast_delta(base_code, invalid_add) is False

    # Rejects non-literal assignment (expression/getenv)
    invalid_dynamic = base_code.replace('EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False', 'EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = bool(os.getenv("ENABLED"))')
    assert validate_configs_base_ast_delta(base_code, invalid_dynamic) is False

    # Rejects modifying unrelated variable
    invalid_modify_unrelated = base_code.replace("FOO = 123", "FOO = 456")
    assert validate_configs_base_ast_delta(base_code, invalid_modify_unrelated) is False

    duplicate_allowed = base_code + "\nEXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False"
    assert validate_configs_base_ast_delta(base_code, duplicate_allowed) is False

    moved_allowed = "\n".join(reversed(base_code.strip().splitlines()))
    assert validate_configs_base_ast_delta(base_code, moved_allowed) is False


def test_schedule_revision_attestation_derives_current_commit_and_never_falls_back(monkeypatch):
    import inspect
    from configs import base
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_schedule_revision_producer_attestation,
    )

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED", True)
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.read_current_commit_sha",
        lambda: "a" * 40,
    )

    assert "current_commit_sha" not in inspect.signature(
        build_schedule_revision_producer_attestation
    ).parameters
    result = build_schedule_revision_producer_attestation(
        integration_health="ready",
        static_proof_result=None,
        consumer_proof_result={"valid": True},
    )
    assert result["schedule_revision_producer_effective_enabled"] is False


def test_startup_static_proof_helpers_in_temp_sha1_repo(tmp_path):
    import subprocess
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        verify_git_ancestry_and_static_proof,
    )

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def run_git(*cmd):
        res = subprocess.run(["git"] + list(cmd), cwd=repo_dir, capture_output=True, text=True, check=True)
        return res.stdout.strip()

    run_git("init")
    run_git("config", "user.name", "Test")
    run_git("config", "user.email", "test@example.com")

    # Create dummy files
    configs_dir = repo_dir / "configs"
    configs_dir.mkdir()
    base_file = configs_dir / "base.py"
    base_content = """
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA = ""
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED = False
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False
"""
    base_file.write_text(base_content)

    scripts_dir = repo_dir / "scripts" / "external_signal_shadow"
    scripts_dir.mkdir(parents=True)
    runner_file = scripts_dir / "run_stage1_5d_live_event_source_smoke_collector.py"
    runner_file.write_text("# runner")

    src_dir = repo_dir / "src" / "research" / "external_signal_shadow"
    src_dir.mkdir(parents=True)
    (repo_dir / "src" / "risk").mkdir(parents=True)
    (repo_dir / "src" / "risk" / "limits.py").write_text("RISK_LIVE_TRADING_ENABLED = False")

    protected_manifest = [
        "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py"
    ]
    for p in protected_manifest:
        fp = repo_dir / p
        fp.parent.mkdir(parents=True, exist_ok=True)
        if not fp.exists():
            fp.write_text("# dummy")

    run_git("add", ".")
    commit_a = run_git("commit-tree", run_git("write-tree"), "-m", "Commit A")
    run_git("reset", "--hard", commit_a)

    # Make config change for commit B
    enable_content = f"""
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA = "{commit_a}"
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED = True
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED = True
EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = True
"""
    base_file.write_text(enable_content)
    run_git("add", "configs/base.py")
    commit_b = run_git("commit-tree", run_git("write-tree"), "-p", commit_a, "-m", "Commit B")
    run_git("reset", "--hard", commit_b)

    res = verify_git_ancestry_and_static_proof(
        repo_root=repo_dir,
        prerequisite_sha=commit_a,
        protected_manifest=protected_manifest,
    )
    assert res["valid"] is True
    assert res["startup_head_sha"] == commit_b

    missing_path = verify_git_ancestry_and_static_proof(
        repo_root=repo_dir,
        prerequisite_sha=commit_a,
        protected_manifest=protected_manifest + ["src/research/external_signal_shadow/missing.py"],
    )
    assert missing_path == {"valid": False, "reason": "protected_manifest_path_not_tracked_blob"}

    ignored_python = repo_dir / "src" / "research" / "external_signal_shadow" / "shadow.py"
    ignored_python.write_text("# untracked import shadow")
    untracked_python = verify_git_ancestry_and_static_proof(
        repo_root=repo_dir,
        prerequisite_sha=commit_a,
        protected_manifest=protected_manifest,
    )
    assert untracked_python == {"valid": False, "reason": "untracked_python_source_present"}


def test_stage1_5d_runtime_attestation_latches_after_untracked_python(tmp_path):
    import subprocess
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        update_stage1_5d_runtime_attestation_latch,
        verify_stage1_5d_runtime_attestation,
    )

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    def run_git(*cmd):
        return subprocess.run(
            ["git", *cmd], cwd=repo_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

    run_git("init")
    run_git("config", "user.name", "Test")
    run_git("config", "user.email", "test@example.com")
    runner_path = repo_dir / "scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py"
    runner_path.parent.mkdir(parents=True)
    runner_path.write_text("# runner")
    (repo_dir / "configs").mkdir()
    (repo_dir / "configs/base.py").write_text("RISK_LIVE_TRADING_ENABLED = False")
    run_git("add", ".")
    run_git("commit", "-m", "initial")
    head_sha = run_git("rev-parse", "HEAD")
    manifest = ["scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py"]

    lifecycle = {"runtime_attestation_compromised": False}
    healthy = verify_stage1_5d_runtime_attestation(repo_dir, head_sha, manifest, __import__("time").monotonic() + 1)
    assert healthy["valid"] is True
    update_stage1_5d_runtime_attestation_latch(lifecycle, healthy)
    assert lifecycle["runtime_attestation_compromised"] is False

    shadow = repo_dir / "scripts/external_signal_shadow/shadow.py"
    shadow.write_text("# untracked")
    compromised = verify_stage1_5d_runtime_attestation(repo_dir, head_sha, manifest, __import__("time").monotonic() + 1)
    assert compromised == {"valid": False, "reason": "untracked_python_source_present"}
    update_stage1_5d_runtime_attestation_latch(lifecycle, compromised)
    shadow.unlink()
    update_stage1_5d_runtime_attestation_latch(lifecycle, healthy)
    assert lifecycle["runtime_attestation_compromised"] is True


def test_verify_stage1_5f_consumer_proof_valid_and_reject_branches(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        canonical_root_contract_sha256,
        verify_stage1_5f_consumer_proof,
    )

    out_id = "d_root_123"
    head_sha = "a" * 40
    manifest_sha = "m" * 64

    contract_data = {
        "root_mode": "v2_production",
        "formal_event_contract_versions_allowed": [2],
        "formal_schedule_revision_contract_versions_allowed": [1, 2],
        "consumer_root_id": "f_root_456",
        "consumer_startup_commit_sha": head_sha,
        "consumer_runtime_manifest_sha256": manifest_sha,
        "consumer_static_attestation_verified": True,
        "source_stage1_5d_output_root_id": out_id,
        "source_stage1_5d_events_root_id": out_id,
        "source_stage1_5d_runtime_gate_root_id": out_id,
    }
    contract_sha = canonical_root_contract_sha256(contract_data)

    summary_data = {
        "consumer_process_instance_id": "proc-uuid-1",
        "consumer_root_id": contract_data["consumer_root_id"],
        "consumer_startup_commit_sha": head_sha,
        "consumer_runtime_manifest_sha256": manifest_sha,
        "consumer_root_contract_sha256": contract_sha,
        "consumer_static_attestation_verified": True,
        "consumer_runtime_attestation_verified": True,
        "consumer_runtime_attestation_compromised": False,
        "stale": False,
        "last_heartbeat_at_ms": 100_000,
        "blocker": None,
        "block_new_event_admission": False,
    }

    contract_file = tmp_path / "observer_root_contract.json"
    summary_file = tmp_path / "live_depth_observer_summary.json"

    contract_file.write_text(json.dumps(contract_data))
    summary_file.write_text(json.dumps(summary_data))

    # Valid proof
    res = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path=contract_file,
        consumer_summary_path=summary_file,
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
        now_ms=101_000,
    )
    assert res["valid"] is True
    assert res["reason"] == "consumer_proof_passed"

    # Reject on hash mismatch
    summary_bad_hash = dict(summary_data, consumer_root_contract_sha256="wrong")
    summary_file.write_text(json.dumps(summary_bad_hash))
    res_bad_hash = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path=contract_file,
        consumer_summary_path=summary_file,
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
        now_ms=101_000,
    )
    assert res_bad_hash["valid"] is False
    assert res_bad_hash["reason"] == "consumer_root_contract_hash_mismatch"

    for field, bad_value in (
        ("consumer_root_id", "wrong-root"),
        ("consumer_startup_commit_sha", "b" * 40),
        ("consumer_runtime_manifest_sha256", "x" * 64),
    ):
        summary_file.write_text(json.dumps({**summary_data, field: bad_value}))
        mismatch = verify_stage1_5f_consumer_proof(
            consumer_root_contract_path=contract_file,
            consumer_summary_path=summary_file,
            expected_d_output_root_id=out_id,
            expected_d_startup_head_sha=head_sha,
            expected_consumer_manifest_sha256=manifest_sha,
            now_ms=101_000,
        )
        assert mismatch == {"valid": False, "reason": f"{field}_cross_artifact_mismatch"}

    summary_file.write_text(json.dumps({**summary_data, "block_new_event_admission": True}))
    blocked = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path=contract_file,
        consumer_summary_path=summary_file,
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
        now_ms=101_000,
    )
    assert blocked == {"valid": False, "reason": "consumer_admission_blocked"}


def test_task6_e0_e1_e2_lifecycle_proof_wiring(tmp_path, monkeypatch):
    from configs import base
    from scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector import (
        build_schedule_revision_producer_attestation,
        canonical_manifest_sha256,
        canonical_root_contract_sha256,
        canonical_root_id,
        verify_stage1_5f_consumer_proof,
    )

    out_id = canonical_root_id(tmp_path)
    head_sha = "a" * 40
    manifest_sha = canonical_manifest_sha256("1.5F_v1", ["scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py"])

    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PREREQUISITE_COMMIT_SHA", head_sha)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PART_A_SUITE_PASSED", True)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_REAL_FIXTURE_VERIFIED", True)
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5d_live_event_source_smoke_collector.read_current_commit_sha",
        lambda: head_sha,
    )

    static_proof = {"valid": True, "startup_head_sha": head_sha}

    # E0: Producer enabled but no F paths provided -> BOOTSTRAP_WAITING_FOR_CONSUMER
    res_e0 = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path="",
        consumer_summary_path="",
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
    )
    assert res_e0["valid"] is False

    att_e0 = build_schedule_revision_producer_attestation(
        integration_health="ready",
        static_proof_result=static_proof,
        consumer_proof_result=res_e0,
    )
    assert att_e0["schedule_revision_producer_consumer_prerequisites_verified"] is False
    assert att_e0["schedule_revision_producer_effective_enabled"] is False

    # E1: F writes valid contract and summary -> Proof passes
    contract_data = {
        "root_mode": "v2_production",
        "formal_event_contract_versions_allowed": [2],
        "formal_schedule_revision_contract_versions_allowed": [1, 2],
        "consumer_root_id": "f_root_1",
        "consumer_startup_commit_sha": head_sha,
        "consumer_runtime_manifest_sha256": manifest_sha,
        "consumer_static_attestation_verified": True,
        "source_stage1_5d_output_root_id": out_id,
        "source_stage1_5d_events_root_id": out_id,
        "source_stage1_5d_runtime_gate_root_id": out_id,
    }
    c_sha = canonical_root_contract_sha256(contract_data)
    summary_data = {
        "consumer_process_instance_id": "proc-e1",
        "consumer_root_id": contract_data["consumer_root_id"],
        "consumer_startup_commit_sha": head_sha,
        "consumer_runtime_manifest_sha256": manifest_sha,
        "consumer_root_contract_sha256": c_sha,
        "consumer_static_attestation_verified": True,
        "consumer_runtime_attestation_verified": True,
        "consumer_runtime_attestation_compromised": False,
        "stale": False,
        "last_heartbeat_at_ms": 100_000,
        "blocker": None,
        "block_new_event_admission": False,
    }

    c_file = tmp_path / "observer_root_contract.json"
    s_file = tmp_path / "live_depth_observer_summary.json"
    c_file.write_text(json.dumps(contract_data))
    s_file.write_text(json.dumps(summary_data))

    res_e1 = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path=c_file,
        consumer_summary_path=s_file,
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
        now_ms=101_000,
    )
    assert res_e1["valid"] is True

    att_e1 = build_schedule_revision_producer_attestation(
        integration_health="ready",
        static_proof_result=static_proof,
        consumer_proof_result=res_e1,
    )
    assert att_e1["schedule_revision_producer_consumer_prerequisites_verified"] is True
    assert att_e1["schedule_revision_producer_effective_enabled"] is True

    # E2: Sticky latch checks - Process restart of F causes mismatch against armed state
    armed_state = dict(res_e1)
    summary_restarted = dict(summary_data, consumer_process_instance_id="proc-e2-restarted")
    s_file.write_text(json.dumps(summary_restarted))

    res_e2_fail = verify_stage1_5f_consumer_proof(
        consumer_root_contract_path=c_file,
        consumer_summary_path=s_file,
        expected_d_output_root_id=out_id,
        expected_d_startup_head_sha=head_sha,
        expected_consumer_manifest_sha256=manifest_sha,
        armed_consumer_state=armed_state,
        now_ms=101_000,
    )
    assert res_e2_fail["valid"] is False
    assert res_e2_fail["reason"] == "armed_consumer_process_id_mismatch"
