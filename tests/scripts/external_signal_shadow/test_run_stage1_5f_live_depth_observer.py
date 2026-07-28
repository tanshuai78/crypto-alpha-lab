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
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
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
    assert accepted_rows[0]["observation_anchor_basis"] == "symbol_effective_launch_time"


    # Assert no ETHUSD1 rejected
    rejected_files = list((output_root / "events_rejected").glob("**/*.jsonl"))
    assert len(rejected_files) == 0


def test_runner_accepts_post_watermark_bapi_confirmed_1_5d_event(tmp_path, monkeypatch):
    import time
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({"symbols": [{"symbol": "XYZUSDT"}]}, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}, f)

    now_ms = 1784644200000
    watermark_time = now_ms - 60 * 60 * 1000
    detected_at_ms = now_ms - 60_000
    launch_time_ms = now_ms - 30_000

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "bapi-post-watermark-event",
            "event_type": "futures_contract_launch",
            "source_article_id": "d0833b3a6eb64132a00c6d7a46abf434",
            "detected_at_ms": detected_at_ms,
            "symbols": ["XYZUSDT"],
            "symbol_extraction_source": "bapi_article_body",
            "symbol_validation_status": "validated_by_exchangeinfo",
            "evidence_source": "official_article_body_confirmed",
            "detail_transport": "bapi_article_detail_query",
            "content_provenance": "binance_official_announcement",
            "source_transport": "binance_first_party_public_web_bapi_undocumented",
            "symbol_effective_launch_times_ms": {"XYZUSDT": launch_time_ms},
            "symbol_onboard_times_ms": {"XYZUSDT": launch_time_ms},
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

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    accepted_rows = [
        json.loads(line)
        for line in accepted_files[0].read_text().splitlines()
        if line.strip()
    ]
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["symbol"] == "XYZUSDT"
    assert accepted_rows[0]["live_depth_evidence_basis"] == "announcement_and_launch_time"


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


def test_runner_accepts_delayed_launch_when_detected_time_is_before_running_watermark(tmp_path, monkeypatch):
    import time
    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({"symbols": [{"symbol": "SPCXUSD1"}]}, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}, f)

    detected_at_ms = 1784370927741
    watermark_time = detected_at_ms + 60 * 60 * 1000
    launch_time_ms = 1784538000000

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "spcxusd1-event",
            "event_type": "futures_contract_launch",
            "source_article_id": "6cbb1b11a9c843949624cf2eacaac8b4",
            "detected_at_ms": detected_at_ms,
            "symbols": ["SPCXUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"SPCXUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"SPCXUSD1": launch_time_ms},
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
            "seen_event_ids": ["newer-event"],
            "seen_source_article_ids": ["newer-article"],
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

    run_poll(launch_time_ms - 5 * 60_000)

    assert list((output_root / "events_accepted").glob("**/*.jsonl")) == []
    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []

    run_poll(launch_time_ms)

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    accepted_rows = []
    with open(accepted_files[0], "r") as f:
        for line in f:
            if line.strip():
                accepted_rows.append(json.loads(line))

    assert accepted_rows[0]["symbol"] == "SPCXUSD1"
    assert accepted_rows[0]["observation_anchor_basis"] == "symbol_effective_launch_time"
    assert accepted_rows[0]["announcement_time_capture_evidence_allowed"] is False
    assert accepted_rows[0]["launch_time_depth_evidence_allowed"] is True
    assert accepted_rows[0]["live_depth_evidence_basis"] == "launch_time_only"


    with open(output_root / "watermark.json", "r") as f:
        w_final = json.load(f)
    assert w_final["max_seen_detected_at_ms"] == watermark_time
    assert "newer-event" in w_final["seen_event_ids"]
    assert "newer-article" in w_final["seen_source_article_ids"]


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
    assert row["rejection_reason"] == "rejected_launch_anchor_age_exceeded"
    assert row["observation_age_base_ms"] == launch_time_ms
    assert row["observation_anchor_basis"] == "symbol_effective_launch_time"
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
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
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
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
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
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
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


def test_runner_can_accept_with_exchangeinfo_onboard_anchor_when_event_launch_time_missing(tmp_path, monkeypatch):
    import time

    mock_dir = tmp_path / "mock_responses"
    os.makedirs(mock_dir, exist_ok=True)
    now_ms = 1784644200000
    launch_time_ms = now_ms - 30_000
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        json.dump({
            "symbols": [{
                "symbol": "XYZUSDT",
                "status": "TRADING",
                "contractType": "PERPETUAL",
                "quoteAsset": "USDT",
                "marginAsset": "USDT",
                "onboardDate": launch_time_ms,
            }]
        }, f)
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        json.dump({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": now_ms}, f)

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps({
            "event_id": "exchangeinfo-anchor-event",
            "event_type": "futures_contract_launch",
            "source_article_id": "article-exinfo-anchor",
            "detected_at_ms": now_ms - 60_000,
            "symbols": ["XYZUSDT"],
            "symbol_extraction_source": "bapi_article_body",
            "symbol_validation_status": "validated_by_exchangeinfo",
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
            "max_seen_detected_at_ms": now_ms - 120_000,
            "seen_event_ids": [],
            "seen_source_article_ids": [],
            "seen_stable_event_keys": [],
            "updated_at_ms": now_ms - 120_000,
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

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    row = json.loads(accepted_files[0].read_text().strip())
    assert row["symbol"] == "XYZUSDT"
    assert row["observation_anchor_ms"] == launch_time_ms
    assert row["observation_anchor_basis"] == "exchangeinfo_current_onboard_time"
    assert row["observation_anchor_confidence"] == "medium"


def test_reconcile_missing_accepted_row_backfills_active_state_once(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        reconcile_missing_accepted_rows,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
        Watermark,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    state = EventSymbolState(
        event_symbol_id="es1",
        event_id="ev1",
        symbol="ABCUSDT",
        detected_at_ms=10_000,
        status="active",
        observation_anchor_ms=20_000,
        observation_anchor_basis="symbol_effective_launch_time",
        observation_anchor_confidence="high",
        observation_window_start_ms=20_000,
        observation_window_end_ms=20_000 + 12 * 60 * 60 * 1000,
        observation_admitted_at_ms=20_100,
        acceptance_id="acceptance-1",
        evidence_start_class="clean_start",
        source_article_id="article1",
        stable_event_key="stable1",
        bootstrap_watermark_max_seen_detected_at_ms=5_000,
        admission_watermark_at_first_seen_ms=15_000,
        announcement_capture_post_bootstrap_watermark=True,
        launch_anchor_post_bootstrap_watermark=True,
    )
    watermark = Watermark(1, 5_000, [], [], [], 5_000)

    rows = reconcile_missing_accepted_rows(str(output_root), {"es1": state}, watermark, now_ms=20_200)
    rows_again = reconcile_missing_accepted_rows(str(output_root), {"es1": state}, watermark, now_ms=20_300)

    accepted_files = list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert len(accepted_files) == 1
    accepted_rows = [json.loads(line) for line in accepted_files[0].read_text().splitlines() if line.strip()]
    assert len(accepted_rows) == 1
    assert accepted_rows[0]["observation_anchor_ms"] == 20_000
    assert accepted_rows[0]["live_depth_evidence_basis"] == "announcement_and_launch_time"
    assert rows_again == []


def test_reconcile_missing_terminal_ignored_rows_backfills_once(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        reconcile_missing_terminal_ignored_rows,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    state = EventSymbolState(
        event_symbol_id="volatile-id",
        event_id="event-ebay",
        source_article_id="article-ebay",
        symbol="EBAYUSDT",
        detected_at_ms=1784822376255,
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="term-hygiene-1",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_at_ms=1784850000000,
        consumable_by_stage1_5g=False,
    )

    rows = reconcile_missing_terminal_ignored_rows(str(output_root), {"volatile-id": state}, now_ms=1784850000000)
    rows_again = reconcile_missing_terminal_ignored_rows(str(output_root), {"volatile-id": state}, now_ms=1784851000000)

    diag_files = list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl"))
    assert len(diag_files) == 1
    diags = [json.loads(line) for line in diag_files[0].read_text().splitlines() if line.strip()]
    assert len(diags) == 1
    assert diags[0]["diagnostic_type"] == "historical_anchor_pre_bootstrap_ignored"
    assert diags[0]["terminal_hygiene_id"] == "term-hygiene-1"
    assert len(rows) == 1
    assert rows_again == []


def test_capped_terminal_state_does_not_trigger_diagnostic_backfill(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        reconcile_missing_terminal_ignored_rows,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    state = EventSymbolState(
        event_symbol_id="capped-id",
        event_id="event-capped",
        source_article_id="article-capped",
        symbol="CAPUSDT",
        detected_at_ms=1784822376255,
        status="ignored_historical_anchor_pre_bootstrap",
        terminal_hygiene_id="term-capped",
        terminal_status="ignored_historical_anchor_pre_bootstrap",
        terminal_reason="historical_anchor_pre_bootstrap",
        terminal_at_ms=1784850000000,
        consumable_by_stage1_5g=False,
        terminal_audit_type="historical_anchor_hygiene_diagnostics",
        diagnostic_expected=False,
        diagnostic_sample_reserved=False,
        diagnostic_emitted=False,
    )

    rows = reconcile_missing_terminal_ignored_rows(str(output_root), {"capped-id": state}, now_ms=1784850000000)

    assert rows == []
    assert list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl")) == []


def test_terminal_hygiene_diagnostic_sample_counts_load_existing_rows(tmp_path, monkeypatch):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        emit_sample_capped_diagnostic,
        load_terminal_hygiene_diagnostic_sample_counts,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )
    from configs import base

    output_root = tmp_path / "output"
    output_root.mkdir()
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_REJECTION_HYGIENE_DIAGNOSTIC_SAMPLES_PER_TYPE", 2)
    for idx in range(2):
        append_jsonl(
            build_daily_path(str(output_root), "historical_anchor_hygiene_diagnostics", 1784850000000 + idx),
            {
                "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
                "terminal_hygiene_id": f"term-{idx}",
            },
        )

    counts = load_terminal_hygiene_diagnostic_sample_counts(str(output_root))
    emitted = emit_sample_capped_diagnostic(
        str(output_root),
        "historical_anchor_hygiene_diagnostics",
        {
            "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
            "terminal_hygiene_id": "term-new",
        },
        "historical_anchor_pre_bootstrap_ignored",
        1784851000000,
        counts,
    )

    assert emitted is False


def test_terminal_hygiene_reconciliation_rebuilds_state_from_diagnostic_artifact(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        reconcile_terminal_hygiene_artifacts,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    state_file = output_root / "observer_state.jsonl"
    diag_row = {
        "audit_metadata_version": 2,
        "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
        "terminal_hygiene_id": "term-from-diag",
        "event_symbol_id": "diag-event-symbol",
        "event_id": "diag-event",
        "source_article_id": "diag-article",
        "stable_event_symbol_key": "futures_contract_launch|diag-article|DIAGUSDT",
        "stable_event_key": "binance_diag",
        "symbol": "DIAGUSDT",
        "detected_at_ms": 1784822376255,
        "terminal_status": "ignored_historical_anchor_pre_bootstrap",
        "terminal_reason": "historical_anchor_pre_bootstrap",
        "terminal_at_ms": 1784850000000,
        "diagnostic_at_ms": 1784850000000,
        "observation_anchor_candidates": {"symbol_effective_launch_time": 1780995600000},
        "bootstrap_watermark_max_seen_detected_at_ms": 1784822376255,
        "consumable_by_stage1_5g": False,
    }
    append_jsonl(build_daily_path(str(output_root), "historical_anchor_hygiene_diagnostics", 1784850000000), diag_row)

    states = {}
    result = reconcile_terminal_hygiene_artifacts(str(output_root), str(state_file), states, now_ms=1784851000000)

    assert result["terminal_ignored_state_rebuilt_count"] == 1
    rows = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "ignored_historical_anchor_pre_bootstrap"
    assert rows[0]["terminal_hygiene_id"] == "term-from-diag"
    assert rows[0]["diagnostic_emitted"] is True


def test_terminal_hygiene_reconciliation_rebuilds_rejected_state_from_audit_artifact(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        reconcile_terminal_hygiene_artifacts,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    state_file = output_root / "observer_state.jsonl"
    rejected_row = {
        "audit_metadata_version": 2,
        "event_symbol_id": "rejected-event-symbol",
        "event_id": "rejected-event",
        "source_article_id": "rejected-article",
        "stable_event_key": "binance_rejected",
        "stable_event_symbol_key": "futures_contract_launch|rejected-article|REJUSDT",
        "symbol": "REJUSDT",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1784830000000,
        "rejected_reason": "rejected_launch_anchor_age_exceeded",
        "rejection_reason": "rejected_launch_anchor_age_exceeded",
        "status": "rejected",
        "rejected_at_ms": 1784850000000,
        "terminal_hygiene_id": "term-rejected",
        "consumable_by_stage1_5g": True,
    }
    append_jsonl(build_daily_path(str(output_root), "events_rejected", 1784850000000), rejected_row)

    states = {}
    result = reconcile_terminal_hygiene_artifacts(str(output_root), str(state_file), states, now_ms=1784851000000)

    assert result["rejected_state_rebuilt_count"] == 1
    rows = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"
    assert rows[0]["terminal_hygiene_id"] == "term-rejected"
    assert rows[0]["terminal_audit_type"] == "events_rejected"


def test_bootstrap_watermark_writes_schema_v2_immutable_bootstrap_fields(tmp_path, monkeypatch):
    import sys, time, json
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "old-event",
        "event_type": "futures_contract_launch",
        "source_article_id": "old-article",
        "stable_event_key": "binance_old",
        "detected_at_ms": 1000,
        "symbols": ["OLDUSDT"],
    }) + "\n")
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    output_root = tmp_path / "out"
    monkeypatch.setattr(time, "time", lambda: 2000 / 1000.0)

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    argv = [
        "run_stage1_5f_live_depth_observer.py",
        "--fixture-events-jsonl", str(event_file),
        "--stage1-5d-summary", str(summary_d),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--bootstrap-watermark",
    ]
    old = sys.argv
    try:
        sys.argv = argv
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old

    w = json.loads((output_root / "watermark.json").read_text())
    assert w["watermark_schema_version"] == 2
    assert w["bootstrap_max_seen_detected_at_ms"] == 1000
    assert w["bootstrap_created_at_ms"] == 2000
    assert w["bootstrap_source_root"]
    assert w["bootstrap_root_id"]


def test_historical_anchor_pre_bootstrap_writes_terminal_ignored_state_not_events_rejected(tmp_path, monkeypatch):
    import sys, time, json
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "stable_event_key": "binance_f598_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["EBAYUSDT"],
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }) + "\n")
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    output_root = tmp_path / "out"

    # Step 1: Bootstrap watermark v2
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--bootstrap-watermark",
        ]
        with pytest.raises(SystemExit):
            main()
    finally:
        sys.argv = old_argv

    # Mock exchangeinfo response
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}]
    }))

    # Step 2: Run poll
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "1",
        ]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []
    state_file = output_root / "observer_state.jsonl"
    assert state_file.exists()
    states = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert len(states) == 1
    assert states[0]["status"] == "ignored_historical_anchor_pre_bootstrap"
    assert states[0]["consumable_by_stage1_5g"] is False

    diag_files = list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl"))
    assert len(diag_files) == 1
    diags = [json.loads(line) for line in diag_files[0].read_text().splitlines() if line.strip()]
    assert len(diags) == 1
    assert diags[0]["diagnostic_type"] == "historical_anchor_pre_bootstrap_ignored"
    assert diags[0]["consumable_by_stage1_5g"] is False


def test_historical_anchor_pre_bootstrap_is_idempotent_across_polls(tmp_path, monkeypatch):
    import sys, time, json
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "stable_event_key": "binance_f598_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["EBAYUSDT"],
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    }) + "\n")
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    output_root = tmp_path / "out"

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--bootstrap-watermark",
        ]
        with pytest.raises(SystemExit):
            main()
    finally:
        sys.argv = old_argv

    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{"symbol": "EBAYUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}]
    }))

    # Run max-polls=2
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "2",
        ]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []
    diag_files = list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl"))
    diags = [json.loads(line) for f in diag_files for line in f.read_text().splitlines() if line.strip()]
    assert len(diags) == 1


def test_1_5f_runner_blocks_events_when_runtime_gate_initializing(tmp_path):
    import sys, json
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "event-gate-test",
        "event_type": "futures_contract_launch",
        "source_article_id": "art_gate_test",
        "stable_event_key": "binance_art_gate_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["GATEUSDT"],
        "symbol_effective_launch_times_ms": {"GATEUSDT": 1780995600000},
    }) + "\n")

    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))

    # Initializing gate file
    gate_dir = tmp_path / "gate_dir"
    gate_dir.mkdir()
    (gate_dir / "live_safety_gate_summary.json").write_text(json.dumps({
        "gate_version": 1,
        "status": "INITIALIZING",
        "consumable_by_stage1_5f": False,
        "fatal_blockers": [],
        "live_trading_enabled": False,
    }))

    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{"symbol": "GATEUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}]
    }))

    output_root = tmp_path / "out"
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--bootstrap-watermark",
        ]
        with pytest.raises(SystemExit):
            main()

        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--stage1-5d-runtime-gate", str(gate_dir / "live_safety_gate_summary.json"),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "1",
        ]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    state_file = output_root / "observer_state.jsonl"
    assert not state_file.exists() or len(state_file.read_text().strip()) == 0


def test_1_5f_runtime_gate_invalid_preserves_pending_without_promoting(tmp_path):
    import sys, json, time
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark

    now_ms = int(time.time() * 1000)
    output_root = tmp_path / "out"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps(Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=now_ms - 10_000,
        updated_at_ms=now_ms - 10_000,
    ).to_dict()))

    state_file = output_root / "observer_state.jsonl"
    state_file.write_text(json.dumps({
        "event_symbol_id": "pending-gate-symbol",
        "event_id": "event-pending-gate",
        "symbol": "GATEUSDT",
        "detected_at_ms": now_ms - 20_000,
        "status": "pending_launch_time_in_future",
        "source_article_id": "article-pending-gate",
        "stable_event_key": "binance_article_pending_gate_MULTI",
        "stable_event_symbol_key": "binance_article_pending_gate_MULTI_GATEUSDT",
        "observation_anchor_ms": now_ms - 1000,
        "next_admission_check_at_ms": now_ms - 1000,
        "first_seen_at_ms": now_ms - 20_000,
    }) + "\n")

    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_id": "event-pending-gate",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-pending-gate",
        "stable_event_key": "binance_article_pending_gate_MULTI",
        "detected_at_ms": now_ms - 20_000,
        "symbols": ["GATEUSDT"],
        "symbol_effective_launch_times_ms": {"GATEUSDT": now_ms - 1000},
    }) + "\n")

    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False, "trade_signal_allowed": False}))

    gate_dir = tmp_path / "gate_dir"
    gate_dir.mkdir()
    (gate_dir / "live_safety_gate_summary.json").write_text(json.dumps({
        "runtime_gate_schema_version": 1,
        "decision": "stage1_5d_runtime_gate_initializing",
        "source_root": str(tmp_path.resolve()),
        "events_stream_relative_path": "events/*.jsonl",
        "generated_at_ms": now_ms,
        "fatal_blockers": [],
        "consumable_by_stage1_5f": False,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{"symbol": "GATEUSDT", "status": "TRADING", "contractType": "TRADIFI_PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": now_ms - 1000}]
    }))

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--stage1-5d-runtime-gate", str(gate_dir / "live_safety_gate_summary.json"),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "1",
        ]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    rows = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert rows[-1]["status"].startswith("pending_")
    assert not list((output_root / "events_accepted").glob("**/*.jsonl"))
    assert not list((output_root / "depth_snapshots").glob("**/*.jsonl"))
