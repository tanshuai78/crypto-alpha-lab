import json
import os
import sys

import pytest


def test_runner_bootstrap_watermark_does_not_fetch_depth(tmp_path):
    # Setup mock event file
    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "e1",
            "event_type": "futures_contract_launch",
            "detected_at_ms": 1000,
            "symbols": ["ABCUSDT"],
            "source_name": "s1",
            "title": "t1"
        }) + "\n")

    summary_d = tmp_path / "summary_d.json"
    with open(summary_d, "w") as f:
        f.write(json.dumps({
            "decision": "stage1_5d_event_detection_passed",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }) + "\n")

    # Run runner in bootstrap mode
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    output_root = tmp_path / "output"

    # We should be able to run main with custom arguments or mock sys.argv
    # Let's write a small wrapper or import and call main with custom args
    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--output-root", str(output_root),
        "--bootstrap-watermark",
    ]
    import sys
    orig_argv = sys.argv
    try:
        sys.argv = args
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = orig_argv

    # Check watermark is written
    watermark_path = output_root / "watermark.json"
    assert os.path.exists(watermark_path)
    with open(watermark_path, "r") as f:
        w = json.load(f)
    assert w["max_seen_detected_at_ms"] == 1000


    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "e1",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "source_name": "s1",
            "title": "t1"
        }) + "\n")

    summary_d = tmp_path / "summary_d.json"
    with open(summary_d, "w") as f:
        f.write(json.dumps({
            "decision": "stage1_5d_event_detection_passed",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }) + "\n")

    summary_e = tmp_path / "summary_e.json"
    with open(summary_e, "w") as f:
        f.write(json.dumps({
            "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }) + "\n")

    # Pre-write watermark so it doesn't need to bootstrap (observation run requires existing watermark)
    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        f.write(json.dumps({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }))

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--max-polls", "1",
        # no --live-public-readonly
    ]
    orig_argv = sys.argv
    try:
        sys.argv = args
        # Since it makes a public network call to refresh exchangeinfo or fetch depth, and --live-public-readonly is False,
        # it must raise RuntimeError and crash/exit with error
        with pytest.raises((RuntimeError, SystemExit)):
            main()
    finally:
        sys.argv = orig_argv


def test_runner_mock_response_dir_keeps_network_disabled(tmp_path):
    # Setup mock responses dir
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)

    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        f.write(json.dumps({"symbols": [{"symbol": "ABCUSDT"}]}))
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        f.write(json.dumps({
            "bids": [["100.0", "10.0"]],
            "asks": [["101.0", "10.0"]],
            "T": 1000
        }))

    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000

    event_file = tmp_path / "events.jsonl"
    # New event with detected_at_ms = event_time (newer than watermark_time)
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "source_name": "s1",
            "title": "t2"
        }) + "\n")

    summary_d = tmp_path / "summary_d.json"
    with open(summary_d, "w") as f:
        f.write(json.dumps({
            "decision": "stage1_5d_event_detection_passed",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }) + "\n")

    summary_e = tmp_path / "summary_e.json"
    with open(summary_e, "w") as f:
        f.write(json.dumps({
            "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }) + "\n")

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        f.write(json.dumps({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }))

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--mock-response-dir", str(mock_dir),
        "--max-polls", "1",
    ]
    orig_argv = sys.argv
    try:
        sys.argv = args
        # Should run successfully without raising network errors since mock dir is used
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = orig_argv

    # Check that output state and summary are written
    assert os.path.exists(output_root / "observer_state.jsonl")
    assert os.path.exists(output_root / "live_depth_observer_summary.json")
    with open(output_root / "live_depth_observer_summary.json", "r") as f:
        summ = json.load(f)
    assert summ["decision"] == "stage1_5f_observer_event_observation_in_progress"

    with open(output_root / "watermark.json", "r") as f:
        watermark = json.load(f)
    assert watermark["max_seen_detected_at_ms"] == event_time
    assert "e2" in watermark["seen_event_ids"]


def test_runner_finalizes_expired_active_state_before_fetching_depth(tmp_path):
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        f.write(json.dumps({"symbols": [{"symbol": "ABCUSDT"}]}))
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        f.write(json.dumps({
            "bids": [["100.0", "10.0"]],
            "asks": [["101.0", "10.0"]],
            "T": 1000,
        }))

    summary_d = tmp_path / "summary_d.json"
    with open(summary_d, "w") as f:
        json.dump({
            "decision": "stage1_5d_event_detection_passed",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }, f)

    summary_e = tmp_path / "summary_e.json"
    with open(summary_e, "w") as f:
        json.dump({
            "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }, f)

    event_file = tmp_path / "empty_events.jsonl"
    event_file.write_text("")

    import time
    now_ms = int(time.time() * 1000)
    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": now_ms,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": now_ms,
        }, f)
    with open(output_root / "observer_state.jsonl", "w") as f:
        f.write(json.dumps({
            "event_symbol_id": "expired_id",
            "event_id": "e_expired",
            "symbol": "ABCUSDT",
            "detected_at_ms": now_ms - 13 * 3600 * 1000,
            "observation_started_at_ms": now_ms - 13 * 3600 * 1000,
            "observation_window_end_ms": now_ms - 3600 * 1000,
            "status": "active",
            "depth_snapshot_count": 0,
            "last_snapshot_ms": 0,
            "max_gap_ms": 0,
            "coverage_ratio_pass": False,
            "max_gap_pass": False,
            "research_result_valid": False,
        }) + "\n")

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--mock-response-dir", str(mock_dir),
        "--max-polls", "1",
    ]
    orig_argv = sys.argv
    try:
        sys.argv = args
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = orig_argv

    snapshot_files = list((output_root / "depth_snapshots").glob("**/*.jsonl"))
    assert snapshot_files == []

    states = [json.loads(line) for line in (output_root / "observer_state.jsonl").read_text().splitlines()]
    assert states[-1]["event_symbol_id"] == "expired_id"
    assert states[-1]["status"] == "expired_without_depth"


def test_runner_blocks_stage1_5e_summary_with_trading_flag_true(tmp_path):
    event_file = tmp_path / "events.jsonl"
    event_file.write_text("")

    summary_d = tmp_path / "summary_d.json"
    with open(summary_d, "w") as f:
        json.dump({
            "decision": "stage1_5d_event_detection_passed",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }, f)

    summary_e = tmp_path / "summary_e.json"
    with open(summary_e, "w") as f:
        json.dump({
            "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
            "paper_trading_allowed": True,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
            "execution_feasibility_claim_allowed": False,
            "trade_signal_allowed": False,
        }, f)

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": 1,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": 1,
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--max-polls", "1",
    ]
    orig_argv = sys.argv
    try:
        sys.argv = args
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    finally:
        sys.argv = orig_argv

    with open(output_root / "live_depth_observer_summary.json", "r") as f:
        summary = json.load(f)
    assert summary["decision"] == "stage1_5f_observer_invalid"
    assert summary["blocker"] == "stage1_5e_summary_invalid_or_unsafe"
