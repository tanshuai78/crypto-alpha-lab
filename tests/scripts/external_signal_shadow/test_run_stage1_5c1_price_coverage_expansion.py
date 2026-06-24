import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5c1_price_coverage_expansion import main


def test_runner_requires_live_flag_for_network(tmp_path):
    events = tmp_path / "events.jsonl"
    summary = tmp_path / "stage1_5b_summary.json"
    output = tmp_path / "futures.jsonl"
    report = tmp_path / "report.jsonl"
    out_summary = tmp_path / "summary.json"
    manifest = tmp_path / "manifest.jsonl"
    pass_events = tmp_path / "pass_events.jsonl"

    events.write_text(json.dumps({
        "symbol_event_id": "e1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }) + "\n")
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))

    args = [
        "run_stage1_5c1_price_coverage_expansion.py",
        "--events-jsonl", str(events),
        "--stage1-5b-summary", str(summary),
        "--output-futures-jsonl", str(output),
        "--output-event-report-jsonl", str(report),
        "--output-summary", str(out_summary),
        "--output-request-manifest-jsonl", str(manifest),
        "--output-futures-coverage-pass-events-jsonl", str(pass_events),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 2


def test_runner_with_mock_exchange_info_and_klines_writes_outputs(tmp_path):
    events = tmp_path / "events.jsonl"
    summary = tmp_path / "stage1_5b_summary.json"
    output = tmp_path / "futures.jsonl"
    report = tmp_path / "report.jsonl"
    out_summary = tmp_path / "summary.json"
    manifest = tmp_path / "manifest.jsonl"
    pass_events = tmp_path / "pass_events.jsonl"
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()

    events.write_text(json.dumps({
        "symbol_event_id": "e1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 0,
    }) + "\n")
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    (mock_dir / "futures_exchange_info.json").write_text(json.dumps({
        "symbols": [{"symbol": "ABCUSDT", "contractType": "PERPETUAL", "status": "TRADING", "quoteAsset": "USDT"}]
    }))
    (mock_dir / "spot_exchange_info.json").write_text(json.dumps({
        "symbols": [{"symbol": "ABCUSDT", "status": "TRADING", "quoteAsset": "USDT"}]
    }))
    (mock_dir / "futures_ABCUSDT_0_136800000.json").write_text(json.dumps([
        [0, "1", "1", "1", "1", "1", 899999, "1000"],
        [900000, "1", "1", "1", "1", "1", 1799999, "1000"],
        [3600000, "1", "1", "1", "1", "1", 4499999, "1000"],
        [90000000, "1", "1", "1", "1", "1", 90899999, "1000"],
    ]))

    args = [
        "run_stage1_5c1_price_coverage_expansion.py",
        "--events-jsonl", str(events),
        "--stage1-5b-summary", str(summary),
        "--output-futures-jsonl", str(output),
        "--output-event-report-jsonl", str(report),
        "--output-summary", str(out_summary),
        "--output-request-manifest-jsonl", str(manifest),
        "--output-futures-coverage-pass-events-jsonl", str(pass_events),
        "--mock-response-dir", str(mock_dir),
    ]
    with patch("sys.argv", args):
        rc = main()
    assert rc == 0
    assert output.exists()
    assert report.exists()
    assert manifest.exists()
    assert pass_events.exists()
    s = json.loads(out_summary.read_text())
    assert s["api_key_used"] is False
    assert s["private_endpoint_used"] is False
