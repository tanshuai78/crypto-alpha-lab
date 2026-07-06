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


def test_runner_accepts_delayed_launch_event_using_effective_launch_time(tmp_path, monkeypatch):
    import time
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({"symbols": [{"symbol": "ETHUSD1"}]}, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}, f)

    now_ms = 1783069534532
    watermark_time = 1783009167053
    detected_at_ms = 1783023648791
    launch_time_ms = 1783069200000

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "ethusd1-event",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        }) + "\n")

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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time,
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    monkeypatch.setattr(time, "time", lambda: now_ms / 1000.0)

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

    # Assert ETHUSD1 accepted and diagnostic basis logged
    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    accepted_rows = []
    with open(accepted_files[0], "r") as f:
        for line in f:
            if line.strip():
                accepted_rows.append(json.loads(line))
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["symbol"] == "ETHUSD1"
    assert accepted_rows[0]["observation_age_basis"] == "symbol_effective_launch_time"

    # Assert no ETHUSD1 rejected
    rejected_files = list((output_root / "events_rejected").glob("**/*.jsonl"))
    assert len(rejected_files) == 0


def test_runner_future_launch_pending_does_not_write_rejected_row_and_retries_later(tmp_path, monkeypatch):
    import time
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({"symbols": [{"symbol": "ETHUSD1"}]}, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}, f)

    now_ms = 1783069200000
    watermark_time = 1783000000000
    detected_at_ms = now_ms - 60_000
    launch_time_ms = now_ms + 10 * 60 * 1000

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "ethusd1-event",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        }) + "\n")

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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time,
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    def run_poll(fake_now_ms: int):
        monkeypatch.setattr(time, "time", lambda: fake_now_ms / 1000.0)
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

    # Poll 1: before launch. Expected: stays pending, watermark not advanced, not accepted or rejected
    run_poll(now_ms)

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 0
    rejected_files = list((output_root / "events_rejected").glob("**/*.jsonl"))
    assert len(rejected_files) == 0

    with open(output_root / "watermark.json", "r") as f:
        w_after = json.load(f)
    assert w_after["max_seen_detected_at_ms"] == watermark_time

    # Poll 2: at/after launch. Expected: accepted
    run_poll(launch_time_ms)

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    accepted_rows = []
    with open(accepted_files[0], "r") as f:
        for line in f:
            if line.strip():
                accepted_rows.append(json.loads(line))
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["symbol"] == "ETHUSD1"

    with open(output_root / "watermark.json", "r") as f:
        w_final = json.load(f)
    assert w_final["max_seen_detected_at_ms"] == detected_at_ms
    assert "ethusd1-event" in w_final["seen_event_ids"]


def test_runner_rejected_age_exceeded_row_includes_age_and_watermark_diagnostics(tmp_path, monkeypatch):
    import time

    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({"symbols": [{"symbol": "ETHUSD1"}]}, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}, f)

    launch_time_ms = 1783069200000
    now_ms = launch_time_ms + 15 * 60 * 1000 + 1_000
    watermark_time = 1783009167053
    detected_at_ms = 1783023648791

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "ethusd1-event-rejected",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        }) + "\n")

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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time,
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    monkeypatch.setattr(time, "time", lambda: now_ms / 1000.0)
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

    rejected_files = list((output_root / "events_rejected").glob("**/*.jsonl"))
    assert len(rejected_files) == 1
    rejected_rows = []
    with open(rejected_files[0], "r") as f:
        for line in f:
            if line.strip():
                rejected_rows.append(json.loads(line))

    assert len(rejected_rows) == 1
    row = rejected_rows[0]
    assert row["symbol"] == "ETHUSD1"
    assert row["rejection_reason"] == "age_exceeded"
    assert row["observation_age_base_ms"] == launch_time_ms
    assert row["observation_age_basis"] == "symbol_effective_launch_time"
    assert row["event_age_ms"] == 15 * 60 * 1000 + 1_000
    assert row["max_event_age_ms"] == 15 * 60 * 1000
    assert row["watermark_max_seen_detected_at_ms"] == watermark_time
    assert row["watermark_version"] == 1


def test_enrich_depth_request_manifest_row_adds_event_symbol_context_without_mutating_input():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    original = {
        "requested_host": "fapi.binance.com",
        "requested_path": "/fapi/v1/depth",
        "http_status": 200,
    }

    enriched = enrich_depth_request_manifest_row(
        original,
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert enriched["request_type"] == "depth_snapshot"
    assert enriched["audit_metadata_version"] == 1
    assert enriched["event_symbol_id"] == "es1"
    assert enriched["event_id"] == "ev1"
    assert enriched["symbol"] == "ETHUSD1"
    assert enriched["requested_path"] == "/fapi/v1/depth"
    assert "event_symbol_id" not in original


def test_enrich_depth_request_manifest_row_preserves_existing_core_manifest_fields():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    enriched = enrich_depth_request_manifest_row(
        {
            "requested_host": "fapi.binance.com",
            "requested_path": "/fapi/v1/depth",
            "http_status": 500,
            "error": "http_error_500",
        },
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert enriched["http_status"] == 500
    assert enriched["error"] == "http_error_500"
    assert enriched["request_type"] == "depth_snapshot"
    assert enriched["audit_metadata_version"] == 1
    assert enriched["event_symbol_id"] == "es1"
    assert enriched["event_id"] == "ev1"
    assert enriched["symbol"] == "ETHUSD1"


def test_enrich_depth_request_manifest_row_rejects_missing_event_symbol_id():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    with pytest.raises(ValueError, match="event_symbol_id_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="",
            event_id="ev1",
            symbol="ETHUSD1",
        )


def test_enrich_depth_request_manifest_row_rejects_missing_event_id():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    with pytest.raises(ValueError, match="event_id_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="es1",
            event_id="",
            symbol="ETHUSD1",
        )


def test_enrich_depth_request_manifest_row_rejects_missing_symbol():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    with pytest.raises(ValueError, match="symbol_required"):
        enrich_depth_request_manifest_row(
            {"requested_path": "/fapi/v1/depth", "http_status": 200},
            event_symbol_id="es1",
            event_id="ev1",
            symbol="",
        )


def test_depth_manifest_row_written_for_active_state_contains_symbol_keys(tmp_path):
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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main, load_all_jsonl_from_subdirs

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

    rows = load_all_jsonl_from_subdirs(str(output_root), "request_manifest")
    depth_rows = [r for r in rows if r.get("request_type") == "depth_snapshot"]
    assert len(depth_rows) == 1
    row = depth_rows[0]
    assert row["request_type"] == "depth_snapshot"
    assert row["audit_metadata_version"] == 1
    assert len(row["event_symbol_id"]) == 64
    assert row["event_id"] == "e2"
    assert row["symbol"] == "ABCUSDT"


def test_failed_depth_manifest_row_contains_event_symbol_context():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        enrich_depth_request_manifest_row,
    )
    row = enrich_depth_request_manifest_row(
        {
            "requested_host": "fapi.binance.com",
            "requested_path": "/fapi/v1/depth",
            "http_status": 500,
            "error": "http_error_500",
        },
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ETHUSD1",
    )

    assert row["request_type"] == "depth_snapshot"
    assert row["audit_metadata_version"] == 1
    assert row["event_symbol_id"] == "es1"
    assert row["event_id"] == "ev1"
    assert row["symbol"] == "ETHUSD1"
    assert row["http_status"] == 500
    assert row["error"] == "http_error_500"


def test_mock_depth_manifest_row_written_exactly_once(tmp_path):
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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main, load_all_jsonl_from_subdirs

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

    rows = load_all_jsonl_from_subdirs(str(output_root), "request_manifest")
    depth_rows = [r for r in rows if r.get("request_type") == "depth_snapshot"]

    keys = [(r.get("event_symbol_id"), r.get("fetched_at_ms"), r.get("requested_path")) for r in depth_rows]
    assert len(keys) == len(set(keys))
    assert len(depth_rows) == 1


def test_live_depth_manifest_row_written_exactly_once(monkeypatch, tmp_path):
    def mock_fetch_public_json(url, live_public_readonly=False):
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "data": {"symbols": [{"symbol": "ABCUSDT"}]},
                "manifest_row": {
                    "requested_host": "fapi.binance.com",
                    "requested_path": "/fapi/v1/exchangeInfo",
                    "requested_url_hash": "mock_exinfo",
                    "final_url_hash": "mock_exinfo",
                    "http_status": 200,
                    "payload_size_bytes": 100,
                    "response_payload_hash": "mock_exinfo",
                    "retry_count": 0,
                    "error": None,
                    "fetched_at_ms": 1000,
                }
            }
        elif "depth" in url:
            return {
                "ok": True,
                "data": {
                    "bids": [["100.0", "10.0"]],
                    "asks": [["101.0", "10.0"]],
                    "T": 1000
                },
                "manifest_row": {
                    "requested_host": "fapi.binance.com",
                    "requested_path": "/fapi/v1/depth",
                    "requested_url_hash": "mock_depth",
                    "final_url_hash": "mock_depth",
                    "http_status": 200,
                    "payload_size_bytes": 100,
                    "response_payload_hash": "mock_depth",
                    "retry_count": 0,
                    "error": None,
                    "fetched_at_ms": 1000,
                }
            }
        return {"ok": False, "error": "unknown_url"}

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5f_live_depth_observer_client.fetch_public_json",
        mock_fetch_public_json
    )

    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000

    event_file = tmp_path / "events.jsonl"
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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main, load_all_jsonl_from_subdirs

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--live-public-readonly",
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

    rows = load_all_jsonl_from_subdirs(str(output_root), "request_manifest")
    depth_rows = [r for r in rows if r.get("request_type") == "depth_snapshot"]

    keys = [(r.get("event_symbol_id"), r.get("fetched_at_ms"), r.get("requested_path")) for r in depth_rows]
    assert len(keys) == len(set(keys))
    assert len(depth_rows) == 1


def test_exchangeinfo_manifest_row_is_not_depth_symbol_specific(monkeypatch, tmp_path):
    def mock_fetch_public_json(url, live_public_readonly=False):
        if "exchangeInfo" in url:
            return {
                "ok": True,
                "data": {"symbols": [{"symbol": "ABCUSDT"}]},
                "manifest_row": {
                    "requested_host": "fapi.binance.com",
                    "requested_path": "/fapi/v1/exchangeInfo",
                    "requested_url_hash": "mock_exinfo",
                    "final_url_hash": "mock_exinfo",
                    "http_status": 200,
                    "payload_size_bytes": 100,
                    "response_payload_hash": "mock_exinfo",
                    "retry_count": 0,
                    "error": None,
                    "fetched_at_ms": 1000,
                }
            }
        elif "depth" in url:
            return {
                "ok": True,
                "data": {
                    "bids": [["100.0", "10.0"]],
                    "asks": [["101.0", "10.0"]],
                    "T": 1000
                },
                "manifest_row": {
                    "requested_host": "fapi.binance.com",
                    "requested_path": "/fapi/v1/depth",
                    "requested_url_hash": "mock_depth",
                    "final_url_hash": "mock_depth",
                    "http_status": 200,
                    "payload_size_bytes": 100,
                    "response_payload_hash": "mock_depth",
                    "retry_count": 0,
                    "error": None,
                    "fetched_at_ms": 1000,
                }
            }
        return {"ok": False, "error": "unknown_url"}

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5f_live_depth_observer_client.fetch_public_json",
        mock_fetch_public_json
    )

    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000

    event_file = tmp_path / "events.jsonl"
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

    output_root = tmp_path / "output"
    os.makedirs(output_root, exist_ok=True)
    with open(output_root / "watermark.json", "w") as f:
        json.dump({
            "watermark_version": 1,
            "max_seen_detected_at_ms": watermark_time,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": watermark_time
        }, f)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main, load_all_jsonl_from_subdirs

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--live-public-readonly",
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

    rows = load_all_jsonl_from_subdirs(str(output_root), "request_manifest")
    exinfo_rows = [r for r in rows if r.get("requested_path") == "/fapi/v1/exchangeInfo"]
    assert len(exinfo_rows) == 1
    exinfo_row = exinfo_rows[0]
    assert exinfo_row.get("event_symbol_id") is None
    assert exinfo_row.get("symbol") is None
    assert exinfo_row.get("request_type") is None
