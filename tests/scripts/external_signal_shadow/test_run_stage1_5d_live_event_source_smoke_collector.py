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
    assert s["symbol_parse_failed_count"] == 2
    assert s["deduped_new_event_count"] == 2
    assert s["new_futures_launch_event_count"] == 2
    event_files = list((output_root / "events").glob("*.jsonl"))
    assert len(event_files) == 1
    assert len(event_files[0].read_text().strip().splitlines()) == 2
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
