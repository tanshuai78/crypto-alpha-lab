import json
import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path(tmp_path: Path) -> Path:
    p = tmp_path / "data" / "external_signal_shadow"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _make_f_storage_guard(output_root):
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    return StorageGuard(output_root=output_root, stage="1.5F")


def _formal_event(row: dict) -> dict:
    symbols = [str(s).strip().upper() for s in row.get("symbols", [])]
    if not symbols:
        raise AssertionError("formal event fixture requires symbols")
    effective = dict(row.get("symbol_effective_launch_times_ms") or {})
    missing = [s for s in symbols if not isinstance(effective.get(s), int) or effective.get(s) <= 0]
    if missing:
        raise AssertionError(f"formal event fixture missing launch anchors: {missing}")
    article_id = row.setdefault("source_article_id", f"article-{symbols[0].lower()}")
    row.setdefault("event_id", f"{article_id}-event")
    row.setdefault("stable_event_key", f"binance_{article_id}_{symbols[0] if len(symbols) == 1 else 'MULTI'}")
    row.setdefault("detected_at_ms", min(effective.values()))
    row["formal_event_contract_version"] = 1
    row["formal_event_consumable_by_stage1_5f"] = True
    row["source_contract_status"] = "formal_v1_valid"
    row["symbol_identity_validation_status"] = "validated_by_exchangeinfo"
    row["symbol_launch_time_candidates_ms"] = {s: effective[s] for s in symbols}
    row["symbol_effective_launch_time_sources"] = {s: "detail_symbol_launch_time" for s in symbols}
    row.setdefault("symbol_onboard_times_ms", {})
    row["launch_anchor_validation_status"] = "valid"
    row["launch_anchor_disagreement_ms"] = None
    row["launch_anchor_comparison_status"] = "single_source_detail"
    row["launch_anchor_evidence_level"] = "detail_confirmed"
    row["detail_fetch_attempted"] = True
    row["detail_fetch_status"] = "success"
    row.setdefault("detail_fetch_variant", "bapi_article_detail_query")
    row["detail_confirmation_missing"] = False
    row.setdefault("parser_version", "stage1_5d_symbol_extraction_v3")
    row.setdefault("symbol_extraction_version", 3)
    return row


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

    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000
    with open(mock_dir / "binance_exchangeinfo_payload.json", "w") as f:
        f.write(json.dumps({"symbols": [{
            "symbol": "ABCUSDT",
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "onboardDate": event_time,
        }]}))
    with open(mock_dir / "binance_depth_payload_healthy.json", "w") as f:
        f.write(json.dumps({
            "bids": [["100.0", "10.0"]],
            "asks": [["101.0", "10.0"]],
            "T": 1000
        }))

    event_file = tmp_path / "events.jsonl"
    # New event with detected_at_ms = event_time (newer than watermark_time)
    with open(event_file, "w") as f:
        f.write(json.dumps(_formal_event({
            "event_id": "e2",
            "source_article_id": "article-e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
            "source_name": "s1",
            "title": "t2"

        })) + "\n")

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
        f.write(json.dumps(_formal_event({
            "event_id": "ethusd1-event",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        })) + "\n")

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
        f.write(json.dumps(_formal_event({
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
        })) + "\n")

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
        f.write(json.dumps(_formal_event({
            "event_id": "ethusd1-event",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        })) + "\n")

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
        f.write(json.dumps(_formal_event({
            "event_id": "spcxusd1-event",
            "event_type": "futures_contract_launch",
            "source_article_id": "6cbb1b11a9c843949624cf2eacaac8b4",
            "detected_at_ms": detected_at_ms,
            "symbols": ["SPCXUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"SPCXUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"SPCXUSD1": launch_time_ms},
        })) + "\n")

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
        f.write(json.dumps(_formal_event({
            "event_id": "ethusd1-event-rejected",
            "event_type": "futures_contract_launch",
            "detected_at_ms": detected_at_ms,
            "symbols": ["ETHUSD1"],
            "symbol_extraction_source": "title_contract_symbol",
            "symbol_validation_status": "validated",
            "symbol_effective_launch_times_ms": {"ETHUSD1": launch_time_ms},
            "symbol_onboard_times_ms": {"ETHUSD1": launch_time_ms},
        })) + "\n")

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
        f.write(json.dumps(_formal_event({
            "event_id": "e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
            "source_name": "s1",
            "title": "t2"

        })) + "\n")

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

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        load_all_jsonl_from_subdirs,
        main,
    )

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
        f.write(json.dumps(_formal_event({
            "event_id": "e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
            "source_name": "s1",
            "title": "t2"

        })) + "\n")

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

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        load_all_jsonl_from_subdirs,
        main,
    )

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


def test_live_depth_manifest_row_written_exactly_once(tmp_path):
    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000
    mock_dir = tmp_path / "mock_responses"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({"symbols": [{"symbol": "ABCUSDT"}]}))
    (mock_dir / "binance_depth_payload_healthy.json").write_text(json.dumps({
        "bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": now_ms,
    }))

    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps(_formal_event({
            "event_id": "e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
            "source_name": "s1",
            "title": "t2"

        })) + "\n")

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

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        load_all_jsonl_from_subdirs,
        main,
    )

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


def test_exchangeinfo_manifest_row_is_not_depth_symbol_specific(monkeypatch, tmp_path):
    def mock_fetch_public_json(url, live_public_readonly=False):
        requested_path = "/fapi/v1/exchangeInfo" if "exchangeInfo" in url else "/fapi/v1/depth"
        return {
            "ok": True,
            "data": (
                {"symbols": [{"symbol": "ABCUSDT"}]}
                if "exchangeInfo" in url
                else {"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}
            ),
            "manifest_row": {
                "requested_host": "fapi.binance.com",
                "requested_path": requested_path,
                "requested_url_hash": "mock",
                "final_url_hash": "mock",
                "http_status": 200,
                "payload_size_bytes": 100,
                "response_payload_hash": "mock",
                "retry_count": 0,
                "error": None,
                "fetched_at_ms": 1000,
            },
        }

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5f_live_depth_observer_client.fetch_public_json",
        mock_fetch_public_json,
    )
    monkeypatch.setattr(
        "scripts.external_signal_shadow.run_stage1_5f_live_depth_observer.time.sleep",
        lambda _: None,
    )

    import time
    now_ms = int(time.time() * 1000)
    event_time = now_ms - 5000
    watermark_time = now_ms - 10000
    event_file = tmp_path / "events.jsonl"
    with open(event_file, "w") as f:
        f.write(json.dumps(_formal_event({
            "event_id": "e2",
            "event_type": "futures_contract_launch",
            "detected_at_ms": event_time,
            "symbols": ["ABCUSDT"],
            "symbol_effective_launch_times_ms": {"ABCUSDT": event_time},
            "source_name": "s1",
            "title": "t2",
        })) + "\n")

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

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        load_all_jsonl_from_subdirs,
        main,
    )

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
        f.write(json.dumps(_formal_event({
            "event_id": "exchangeinfo-anchor-event",
            "event_type": "futures_contract_launch",
            "source_article_id": "article-exinfo-anchor",
            "detected_at_ms": now_ms - 60_000,
            "symbols": ["XYZUSDT"],
            "symbol_extraction_source": "bapi_article_body",
            "symbol_validation_status": "validated_by_exchangeinfo",
            "formal_event_contract_version": 1,
            "formal_event_consumable_by_stage1_5f": True,
            "source_contract_status": "formal_v1_valid",
            "symbol_identity_validation_status": "validated_by_exchangeinfo",
            "launch_anchor_validation_status": "valid",
            "symbol_effective_launch_times_ms": {"XYZUSDT": launch_time_ms},
        })) + "\n")

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
    assert row["observation_anchor_basis"] in ("symbol_effective_launch_time", "exchangeinfo_current_onboard_time")
    assert row["observation_anchor_confidence"] in ("high", "medium")


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
    storage_guard = _make_f_storage_guard(output_root)

    reconcile_missing_accepted_rows(str(output_root), {"es1": state}, watermark, now_ms=20_200, storage_guard=storage_guard)
    rows_again = reconcile_missing_accepted_rows(str(output_root), {"es1": state}, watermark, now_ms=20_300, storage_guard=storage_guard)

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
    storage_guard = _make_f_storage_guard(output_root)

    rows = reconcile_missing_terminal_ignored_rows(str(output_root), {"volatile-id": state}, now_ms=1784850000000, storage_guard=storage_guard)
    rows_again = reconcile_missing_terminal_ignored_rows(str(output_root), {"volatile-id": state}, now_ms=1784851000000, storage_guard=storage_guard)

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
    storage_guard = _make_f_storage_guard(output_root)

    rows = reconcile_missing_terminal_ignored_rows(str(output_root), {"capped-id": state}, now_ms=1784850000000, storage_guard=storage_guard)

    assert rows == []
    assert list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl")) == []


def test_terminal_hygiene_diagnostic_sample_counts_load_existing_rows(tmp_path, monkeypatch):
    from configs import base
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        emit_sample_capped_diagnostic,
        load_terminal_hygiene_diagnostic_sample_counts,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
        append_jsonl,
        build_daily_path,
    )

    output_root = tmp_path / "output"
    output_root.mkdir()
    storage_guard = _make_f_storage_guard(output_root)
    monkeypatch.setattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_REJECTION_HYGIENE_DIAGNOSTIC_SAMPLES_PER_TYPE", 2)
    for idx in range(2):
        append_jsonl(
            build_daily_path(str(output_root), "historical_anchor_hygiene_diagnostics", 1784850000000 + idx),
            {
                "diagnostic_type": "historical_anchor_pre_bootstrap_ignored",
                "terminal_hygiene_id": f"term-{idx}",
            },
            storage_guard=storage_guard,
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
        storage_guard=storage_guard,
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
    storage_guard = _make_f_storage_guard(output_root)
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
    append_jsonl(
        build_daily_path(str(output_root), "historical_anchor_hygiene_diagnostics", 1784850000000),
        diag_row,
        storage_guard=storage_guard,
    )

    states = {}
    result = reconcile_terminal_hygiene_artifacts(
        str(output_root), str(state_file), states, now_ms=1784851000000, storage_guard=storage_guard
    )

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
    storage_guard = _make_f_storage_guard(output_root)
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
    append_jsonl(
        build_daily_path(str(output_root), "events_rejected", 1784850000000),
        rejected_row,
        storage_guard=storage_guard,
    )

    states = {}
    result = reconcile_terminal_hygiene_artifacts(
        str(output_root), str(state_file), states, now_ms=1784851000000, storage_guard=storage_guard
    )

    assert result["rejected_state_rebuilt_count"] == 1
    rows = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"
    assert rows[0]["terminal_hygiene_id"] == "term-rejected"
    assert rows[0]["terminal_audit_type"] == "events_rejected"


def test_bootstrap_watermark_writes_schema_v2_immutable_bootstrap_fields(tmp_path, monkeypatch):
    import json
    import sys
    import time
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
    root_contract = json.loads((output_root / "observer_root_contract.json").read_text())
    assert root_contract["root_mode"] == "v2_production"
    assert root_contract["formal_event_contract_versions_allowed"] == [2]


def test_historical_anchor_pre_bootstrap_writes_terminal_ignored_state_not_events_rejected(tmp_path, monkeypatch):
    import json
    import sys
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "stable_event_key": "binance_f598_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["EBAYUSDT"],
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    })) + "\n")
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
    import json
    import sys
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "event-ebay",
        "event_type": "futures_contract_launch",
        "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
        "stable_event_key": "binance_f598_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["EBAYUSDT"],
        "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
    })) + "\n")
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
    import json
    import sys
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "event-gate-test",
        "event_type": "futures_contract_launch",
        "source_article_id": "art_gate_test",
        "stable_event_key": "binance_art_gate_MULTI",
        "detected_at_ms": 1784822376255,
        "symbols": ["GATEUSDT"],
        "symbol_effective_launch_times_ms": {"GATEUSDT": 1780995600000},
    })) + "\n")

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
    import json
    import sys
    import time

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
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "event-pending-gate",
        "event_type": "futures_contract_launch",
        "source_article_id": "article-pending-gate",
        "stable_event_key": "binance_article_pending_gate_MULTI",
        "detected_at_ms": now_ms - 20_000,
        "symbols": ["GATEUSDT"],
        "symbol_effective_launch_times_ms": {"GATEUSDT": now_ms - 1000},
    })) + "\n")

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


def test_batch_registry_records_started_and_all_durable(tmp_path):
    import time
    now_ms = int(time.time() * 1000)
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({
        "symbols": [
            {"symbol": "BTCUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": now_ms - 1000},
            {"symbol": "ETHUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": now_ms - 1000},
        ]
    }))
    (mock_dir / "binance_depth_payload_healthy.json").write_text(json.dumps({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}))

    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "multi1",
        "source_article_id": "art_multi1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": now_ms - 2000,
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "symbol_effective_launch_times_ms": {"BTCUSDT": now_ms - 1000, "ETHUSDT": now_ms - 1000},
    })) + "\n")

    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False}))

    output_root = tmp_path / "output"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps({
        "watermark_version": 1,
        "max_seen_detected_at_ms": now_ms - 5000,
        "seen_event_ids": [],
        "seen_source_article_ids": [],
        "seen_stable_event_keys": [],
    }))

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    old_argv = sys.argv
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

    registry_path = output_root / "event_batch_registry.jsonl"
    assert registry_path.exists()
    rows = [json.loads(line) for line in registry_path.read_text().splitlines() if line.strip()]
    statuses = [r["status"] for r in rows]
    assert "batch_started" in statuses
    assert "siblings_all_durable" in statuses
    assert "watermark_committed" in statuses


def test_three_staggered_symbols_promote_at_their_own_anchor(tmp_path, monkeypatch):
    import time
    base_time_ms = 1784800000000
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({
        "symbols": [
            {"symbol": "SYM1USDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": base_time_ms},
            {"symbol": "SYM2USDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": base_time_ms + 300000},
            {"symbol": "SYM3USDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": base_time_ms + 600000},
        ]
    }))
    (mock_dir / "binance_depth_payload_healthy.json").write_text(json.dumps({"bids": [["100.0", "10.0"]], "asks": [["101.0", "10.0"]], "T": 1000}))

    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps(_formal_event({
        "event_id": "staggered1",
        "source_article_id": "art_staggered",
        "event_type": "futures_contract_launch",
        "detected_at_ms": base_time_ms - 1000,
        "symbols": ["SYM1USDT", "SYM2USDT", "SYM3USDT"],
        "symbol_effective_launch_times_ms": {
            "SYM1USDT": base_time_ms,
            "SYM2USDT": base_time_ms + 300000,
            "SYM3USDT": base_time_ms + 600000,
        },
    })) + "\n")

    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({"decision": "stage1_5d_event_detection_passed", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False}))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({"decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer", "paper_trading_allowed": False, "live_trading_allowed": False, "execution_engine_allowed": False, "alpha_interpretation_allowed": False}))

    output_root = tmp_path / "output"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps({
        "watermark_version": 1,
        "max_seen_detected_at_ms": base_time_ms - 5000,
        "seen_event_ids": [],
        "seen_source_article_ids": [],
        "seen_stable_event_keys": [],
    }))

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main

    def run_poll(fake_now_ms: int):
        monkeypatch.setattr(time, "time", lambda: fake_now_ms / 1000.0)
        old_argv = sys.argv
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

    # Poll 1: SYM1 active, SYM2 & SYM3 pending
    run_poll(base_time_ms)
    accepted1 = [json.loads(line) for p in (output_root / "events_accepted").glob("**/*.jsonl") for line in p.read_text().splitlines() if line.strip()]
    accepted_symbols1 = {r["symbol"] for r in accepted1}
    assert "SYM1USDT" in accepted_symbols1
    assert "SYM2USDT" not in accepted_symbols1
    assert "SYM3USDT" not in accepted_symbols1

    # Poll 2: SYM2 promoted
    run_poll(base_time_ms + 300000)
    accepted2 = [json.loads(line) for p in (output_root / "events_accepted").glob("**/*.jsonl") for line in p.read_text().splitlines() if line.strip()]
    accepted_symbols2 = {r["symbol"] for r in accepted2}
    assert "SYM2USDT" in accepted_symbols2

    # Poll 3: SYM3 promoted
    run_poll(base_time_ms + 600000)
    accepted3 = [json.loads(line) for p in (output_root / "events_accepted").glob("**/*.jsonl") for line in p.read_text().splitlines() if line.strip()]
    accepted_symbols3 = {r["symbol"] for r in accepted3}
    assert "SYM3USDT" in accepted_symbols3


def test_v2_root_writes_observer_root_contract_before_watermark(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        write_observer_root_contract_atomically,
    )
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    output_root = tmp_path / "test_root"
    write_observer_root_contract_atomically(
        str(output_root),
        "v2_production",
        reason="test",
        storage_guard=StorageGuard(output_root=output_root, stage="1.5F"),
    )

    root_contract_file = output_root / "observer_root_contract.json"
    assert root_contract_file.exists()
    saved = json.loads(root_contract_file.read_text())
    assert saved["root_mode"] == "v2_production"
    assert saved["formal_event_contract_versions_allowed"] == [2]
    assert not (output_root / "observer_root_contract.json.tmp").exists()


def test_v1_compatibility_root_requires_valid_suffix(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        validate_root_mode_and_suffix,
    )

    # Invalid suffix for v1 compatibility -> raises ValueError
    with pytest.raises(ValueError, match="v1_compatibility_diagnostic_only"):
        validate_root_mode_and_suffix(str(tmp_path / "invalid_root_name"), allow_v1_compat=True)

    # Valid suffix for v1 compatibility -> passes
    valid_root = str(tmp_path / "my_root_v1_compatibility_diagnostic_only")
    mode = validate_root_mode_and_suffix(valid_root, allow_v1_compat=True)
    assert mode == "v1_compatibility_diagnostic_only"


def test_build_accepted_row_from_state_preserves_anchor_contract_lineage():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        build_accepted_row_from_state,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
        Watermark,
    )

    state = EventSymbolState(
        event_symbol_id="es-v2",
        event_id="ev-v2",
        symbol="GIGADEVUSDT",
        detected_at_ms=1_000,
        status="active",
        observation_anchor_ms=10_000,
        observation_anchor_basis="official_schedule_anchor",
        observation_anchor_confidence="high",
        source_article_id="307687ad279e42e6909ee1be8c472b50",
        formal_event_contract_version=2,
        source_contract_status="formal_v2_valid",
        launch_anchor_evidence_level="official_schedule",
        effective_observation_anchor_source="official_schedule_anchor",
        source_anchor_contract_hash="source-hash",
        admission_anchor_contract_hash="admission-hash",
        latest_anchor_contract_hash="latest-hash",
        anchor_contract_version=2,
        anchor_precedence_policy="official_schedule_priority_v1",
        anchor_contract_decision_at_ms=2_000,
        admission_anchor_evidence_level="official_schedule",
        latest_anchor_evidence_level="official_schedule",
        admission_max_evidence_class="clean_or_recovery",
        latest_max_evidence_class="clean_or_recovery",
        anchor_contract_revision_count=1,
        applied_schedule_revision_ids=["rev-app-1"],
    )
    row = build_accepted_row_from_state(
        state,
        Watermark(max_seen_detected_at_ms=500),
        now_ms=10_200,
    )

    assert row["source_article_id"] == "307687ad279e42e6909ee1be8c472b50"
    assert row["formal_event_contract_version"] == 2
    assert row["source_contract_status"] == "formal_v2_valid"
    assert row["launch_anchor_evidence_level"] == "official_schedule"
    assert row["effective_observation_anchor_source"] == "official_schedule_anchor"
    assert row["source_anchor_contract_hash"] == "source-hash"
    assert row["admission_anchor_contract_hash"] == "admission-hash"
    assert row["latest_anchor_contract_hash"] == "latest-hash"
    assert row["anchor_contract_version"] == 2
    assert row["anchor_precedence_policy"] == "official_schedule_priority_v1"
    assert row["admission_max_evidence_class"] == "clean_or_recovery"
    assert row["anchor_contract_revision_count"] == 1
    assert row["applied_schedule_revision_ids"] == ["rev-app-1"]


def test_runner_active_state_selector_keeps_contaminated_active_collecting():
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        select_completed_observation_states,
        select_depth_collection_active_states,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    states = {
        "active": EventSymbolState(event_symbol_id="active", status="active", symbol="AUSDT"),
        "contaminated": EventSymbolState(
            event_symbol_id="contaminated",
            status="active_anchor_revision_contaminated",
            symbol="BUSDT",
        ),
        "completed": EventSymbolState(event_symbol_id="completed", status="completed", symbol="CUSDT"),
        "completed_contaminated": EventSymbolState(
            event_symbol_id="completed_contaminated",
            status="completed_anchor_revision_contaminated",
            symbol="DUSDT",
        ),
    }

    assert {s.event_symbol_id for s in select_depth_collection_active_states(states)} == {"active", "contaminated"}
    assert {s.event_symbol_id for s in select_completed_observation_states(states)} == {"completed", "completed_contaminated"}


def test_schedule_revision_event_updates_matching_pending_state_and_registry(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        process_schedule_revision_event,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    state = EventSymbolState(
        event_symbol_id="es-gigadev",
        event_id="launch-1",
        symbol="GIGADEVUSDT",
        source_article_id="orig-article",
        stable_event_symbol_key="futures_contract_launch|orig-article|GIGADEVUSDT",
        status="pending_launch_time_in_future",
        observation_anchor_ms=1_000,
        latest_anchor_contract_hash="latest-before",
    )
    states = {state.event_symbol_id: state}
    state_file = tmp_path / "observer_state.jsonl"
    registry_file = tmp_path / "schedule_revision_registry.jsonl"
    revision = {
        "event_type": "futures_contract_launch_schedule_revision",
        "formal_schedule_revision_contract_version": 1,
        "source_article_id": "revision-article",
        "supersedes_source_article_id": "orig-article",
        "stable_schedule_identity": "binance|futures_contract_launch|orig-article|GIGADEVUSDT",
        "symbols": ["GIGADEVUSDT"],
        "symbol_revised_anchor_ms": {"GIGADEVUSDT": 2_000},
        "revision_id": "rev-1",
        "revision_payload_hash": "hash-1",
    }

    res = process_schedule_revision_event(
        revision,
        states=states,
        state_file=str(state_file),
        registry_file=registry_file,
        now_ms=1_500,
        storage_guard=_make_f_storage_guard(tmp_path),
    )

    assert res["status"] == "revision_applied"
    assert states["es-gigadev"].observation_anchor_ms == 2_000
    assert states["es-gigadev"].anchor_contract_revision_count == 1
    rows = [json.loads(line) for line in registry_file.read_text().splitlines()]
    assert [r["status"] for r in rows] == ["revision_received", "revision_applied"]

    replay_res = process_schedule_revision_event(
        revision,
        states=states,
        state_file=str(state_file),
        registry_file=registry_file,
        now_ms=1_600,
        storage_guard=_make_f_storage_guard(tmp_path),
    )
    assert replay_res["status"] == "revision_replay_noop"
    assert states["es-gigadev"].anchor_contract_revision_count == 1


def test_v2_schedule_revision_uses_producer_application_id_verbatim(tmp_path):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_schedule_revision_row,
    )
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        process_schedule_revision_event,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    state = EventSymbolState(
        event_symbol_id="es-v2",
        event_id="launch-v2",
        symbol="GIGADEVUSDT",
        source_article_id="orig-article",
        stable_event_symbol_key="futures_contract_launch|orig-article|GIGADEVUSDT",
        status="pending_launch_time_in_future",
        observation_anchor_ms=1_000,
    )
    revision = build_formal_schedule_revision_row(
        source_article_id="revision-article",
        supersedes_source_article_id="orig-article",
        symbol="GIGADEVUSDT",
        revised_anchor_ms=2_000,
        revision_id="producer-id",
        revision_semantic_id="producer-id",
        revision_application_id="producer-id",
        revision_payload_version_id="payload-v1",
        revision_observation_id="observation-v1",
        revision_payload_hash="payload-hash",
        revision_available_at_ms=1_500,
        provenance={"payload_sha256": "payload-hash", "parser_version": "test"},
    )
    registry_file = tmp_path / "schedule_revision_registry.jsonl"
    states = {state.event_symbol_id: state}

    result = process_schedule_revision_event(
        revision,
        states=states,
        state_file=str(tmp_path / "observer_state.jsonl"),
        registry_file=registry_file,
        now_ms=1_600,
        storage_guard=_make_f_storage_guard(tmp_path),
    )

    assert result == {"status": "revision_applied", "revision_application_id": "producer-id"}
    registry_rows = [json.loads(line) for line in registry_file.read_text().splitlines()]
    assert {row["revision_application_id"] for row in registry_rows} == {"producer-id"}


def test_schedule_revision_arriving_before_launch_is_orphaned(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        process_schedule_revision_event,
    )

    registry_file = tmp_path / "schedule_revision_registry.jsonl"
    revision = {
        "event_type": "futures_contract_launch_schedule_revision",
        "formal_schedule_revision_contract_version": 1,
        "supersedes_source_article_id": "missing-article",
        "stable_schedule_identity": "binance|futures_contract_launch|missing-article|ABCUSDT",
        "symbols": ["ABCUSDT"],
        "symbol_revised_anchor_ms": {"ABCUSDT": 2_000},
        "revision_id": "rev-orphan",
        "revision_payload_hash": "hash-orphan",
    }

    res = process_schedule_revision_event(
        revision,
        states={},
        state_file=str(tmp_path / "observer_state.jsonl"),
        registry_file=registry_file,
        now_ms=1_500,
        storage_guard=_make_f_storage_guard(tmp_path),
    )

    assert res["status"] == "revision_orphaned"
    rows = [json.loads(line) for line in registry_file.read_text().splitlines()]
    assert rows[-1]["status"] == "revision_orphaned"

    replay_res = process_schedule_revision_event(
        revision,
        states={},
        state_file=str(tmp_path / "observer_state.jsonl"),
        registry_file=registry_file,
        now_ms=1_600,
        storage_guard=_make_f_storage_guard(tmp_path),
    )
    replay_rows = [json.loads(line) for line in registry_file.read_text().splitlines()]
    assert replay_res["status"] == "revision_orphaned_replay_noop"
    assert len(replay_rows) == len(rows)


def test_ambiguous_schedule_revision_does_not_mutate_state(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        process_schedule_revision_event,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    states = {
        "es-a": EventSymbolState(
            event_symbol_id="es-a",
            symbol="ABCUSDT",
            source_article_id="orig-article",
            status="active",
            observation_anchor_ms=1_000,
        ),
        "es-b": EventSymbolState(
            event_symbol_id="es-b",
            symbol="ABCUSDT",
            source_article_id="orig-article",
            status="pending_launch_time_in_future",
            observation_anchor_ms=1_100,
        ),
    }
    revision = {
        "event_type": "futures_contract_launch_schedule_revision",
        "formal_schedule_revision_contract_version": 1,
        "supersedes_source_article_id": "orig-article",
        "symbols": ["ABCUSDT"],
        "symbol_revised_anchor_ms": {"ABCUSDT": 2_000},
        "revision_id": "rev-ambiguous",
        "revision_payload_hash": "hash-ambiguous",
    }

    res = process_schedule_revision_event(
        revision,
        states=states,
        state_file=str(tmp_path / "observer_state.jsonl"),
        registry_file=tmp_path / "schedule_revision_registry.jsonl",
        now_ms=1_500,
        storage_guard=_make_f_storage_guard(tmp_path),
    )

    assert res["status"] == "revision_ambiguous"
    assert states["es-a"].observation_anchor_ms == 1_000
    assert states["es-b"].observation_anchor_ms == 1_100

    registry_file = tmp_path / "schedule_revision_registry.jsonl"
    row_count = len([line for line in registry_file.read_text().splitlines() if line.strip()])
    replay_res = process_schedule_revision_event(
        revision,
        states=states,
        state_file=str(tmp_path / "observer_state.jsonl"),
        registry_file=registry_file,
        now_ms=1_600,
        storage_guard=_make_f_storage_guard(tmp_path),
    )
    replay_row_count = len([line for line in registry_file.read_text().splitlines() if line.strip()])
    assert replay_res["status"] == "revision_ambiguous_replay_noop"
    assert replay_row_count == row_count


def test_schedule_revision_event_is_not_admitted_as_new_launch_by_runner(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )

    now_ms = 2_000_000
    output_root = tmp_path / "output"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps({
        "watermark_version": 1,
        "max_seen_detected_at_ms": 1_000_000,
        "seen_event_ids": [],
        "seen_source_article_ids": [],
        "seen_stable_event_keys": [],
        "updated_at_ms": 1_000_000,
    }))
    pending = EventSymbolState(
        event_symbol_id="es-abc",
        event_id="launch-abc",
        symbol="ABCUSDT",
        source_article_id="orig-article",
        stable_event_symbol_key="futures_contract_launch|orig-article|ABCUSDT",
        status="pending_launch_time_in_future",
        observation_anchor_ms=now_ms + 60_000,
        latest_anchor_contract_hash="latest-before",
    )
    (output_root / "observer_state.jsonl").write_text(json.dumps(pending.to_dict()) + "\n")

    event_file = tmp_path / "events.jsonl"
    event_file.write_text(json.dumps({
        "event_type": "futures_contract_launch_schedule_revision",
        "formal_schedule_revision_contract_version": 1,
        "source_article_id": "revision-article",
        "supersedes_source_article_id": "orig-article",
        "stable_schedule_identity": "binance|futures_contract_launch|orig-article|ABCUSDT",
        "symbols": ["ABCUSDT"],
        "symbol_revised_anchor_ms": {"ABCUSDT": now_ms + 120_000},
        "revision_id": "rev-runner",
        "revision_payload_hash": "hash-runner",
    }) + "\n")
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({
        "decision": "stage1_5d_event_detection_passed",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({"symbols": []}))

    orig_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", str(event_file),
            "--stage1-5d-summary", str(summary_d),
            "--stage1-5e-summary", str(summary_e),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "1",
            "--live-public-readonly",
        ]
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0
    finally:
        sys.argv = orig_argv

    assert not (output_root / "event_batch_registry.jsonl").exists()
    assert not list((output_root / "events_accepted").glob("*.jsonl"))
    registry_rows = [
        json.loads(line)
        for line in (output_root / "schedule_revision_registry.jsonl").read_text().splitlines()
        if line.strip()
    ]
    assert registry_rows[-1]["status"] == "revision_applied"
    summary = json.loads((output_root / "live_depth_observer_summary.json").read_text())
    assert summary["schedule_revision_registry_orphan_count"] == 0
    assert summary["schedule_revision_registry_ambiguous_count"] == 0
    assert summary["anchor_contract_revision_count"] == 1


def test_task1_root_contract_signature_and_safety_baseline_preflight(tmp_path):
    import inspect

    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        write_observer_root_contract_atomically,
    )

    sig = inspect.signature(write_observer_root_contract_atomically)
    params = list(sig.parameters.values())
    assert [p.name for p in params[:3]] == ["output_root", "root_mode", "reason"]

    assert sig.parameters["reason"].default == ""
    assert sig.parameters["storage_guard"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["storage_guard"].default is inspect.Parameter.empty
    assert sig.parameters["source_binding_facts"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["source_binding_facts"].default is None


    out = tmp_path / "out_v2"
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard

    contract = write_observer_root_contract_atomically(
        str(out), "v2_production", storage_guard=StorageGuard(output_root=out, stage="1.5F")
    )
    assert contract["formal_event_contract_versions_allowed"] == [2]
    assert contract["formal_schedule_revision_contract_versions_allowed"] == [1, 2]


def test_task5_consumer_summary_models_and_atomic_writer(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        write_live_depth_observer_summary_atomically,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        LiveDepthObserverSummary,
    )

    old_dict = {
        "decision": "stage1_5f_live_depth_observation_passed",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "d.json",
        "stage1_5e_summary_path": None,
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 100,
        "pre_watermark_events_ignored": 0,
        "post_watermark_events_accepted": 1,
        "active_observation_count": 1,
        "completed_observation_count": 0,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 5,
        "total_snapshots_collected": 10,
        "request_success_rate": 1.0,
        "total_requests_made": 10,
        "failed_requests_count": 0,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 0,
        "last_heartbeat_at_ms": 1_000,
        "heartbeat_count": 1,
    }

    # Deserializes legacy summary without new fields
    obj = LiveDepthObserverSummary.from_dict(old_dict)
    assert obj.consumer_process_instance_id == ""
    assert obj.consumer_static_attestation_verified is False

    # Serializes new fields
    d = obj.to_dict()
    d["consumer_process_instance_id"] = "proc-123"
    d["consumer_static_attestation_verified"] = True
    new_obj = LiveDepthObserverSummary.from_dict(d)
    assert new_obj.consumer_process_instance_id == "proc-123"
    assert new_obj.consumer_static_attestation_verified is True

    # Atomic summary writer
    sum_file = tmp_path / "summary.json"
    write_live_depth_observer_summary_atomically(
        sum_file,
        d,
        storage_guard=_make_f_storage_guard(tmp_path),
    )
    assert sum_file.exists()
    assert not sum_file.with_suffix(".json.tmp").exists()
    saved = json.loads(sum_file.read_text())
    assert saved["consumer_process_instance_id"] == "proc-123"


def test_live_depth_summary_writer_requires_guard_and_reserves_storage_blocker_terminally(tmp_path):
    from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import (
        write_live_depth_observer_summary_atomically,
    )

    class CapturingGuard:
        def __init__(self):
            self.artifact_classes = []

        def reserve_and_write(self, *, artifact_class, transient_peak_bytes, persistent_delta_bytes, write_func):
            self.artifact_classes.append(artifact_class)
            return {"status": "ready", "written": True, "write_result": write_func()}

    with pytest.raises(TypeError, match="storage_guard_required"):
        write_live_depth_observer_summary_atomically(tmp_path / "missing-guard.json", {}, storage_guard=None)

    guard = CapturingGuard()
    write_live_depth_observer_summary_atomically(tmp_path / "ordinary.json", {}, storage_guard=guard)
    write_live_depth_observer_summary_atomically(
        tmp_path / "terminal.json",
        {"storage_blocker": "root_budget_exceeded_for_normal_data"},
        storage_guard=guard,
    )
    assert guard.artifact_classes == ["ordinary_control_plane", "terminal_control_plane"]


def test_startup_storage_block_writes_terminal_f_summary(tmp_path, monkeypatch):
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner

    class BlockedStartupGuard:
        instances = []

        def __init__(self, output_root, stage, terminal_write_set_peak_bytes):
            self.output_root = output_root
            self.artifact_classes = []
            self.terminal_write_set_peak_bytes = terminal_write_set_peak_bytes
            self.__class__.instances.append(self)

        def cleanup_owned_temp_files(self, _process_instance_id):
            return None

        def validate_startup(self):
            return {"status": "blocked_start_free_space", "storage_blocker": "storage_start_free_space"}

        def reserve_and_write(self, *, artifact_class, transient_peak_bytes, persistent_delta_bytes, write_func):
            self.artifact_classes.append(artifact_class)
            return {"status": "ready", "written": True, "write_result": write_func()}

    monkeypatch.setattr(
        "src.research.external_signal_shadow.stage1_5_storage_guard.StorageGuard",
        BlockedStartupGuard,
    )
    output_root = tmp_path / "out"
    old_argv = sys.argv
    try:
        sys.argv = ["run_stage1_5f_live_depth_observer.py", "--output-root", str(output_root)]
        with pytest.raises(SystemExit) as exc:
            runner.main()
    finally:
        sys.argv = old_argv

    assert exc.value.code == 1
    summary_path = output_root / "live_depth_observer_summary.json"
    diagnostic_path = output_root / "storage_failure_diagnostic.json"
    summary = json.loads(summary_path.read_text())
    assert summary["storage_blocker"] == "storage_start_free_space"
    assert summary["block_new_event_admission"] is True
    from configs import base

    assert summary_path.stat().st_size <= base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
    assert diagnostic_path.exists()
    assert BlockedStartupGuard.instances[0].artifact_classes == ["terminal_control_plane", "terminal_control_plane"]
    assert BlockedStartupGuard.instances[0].terminal_write_set_peak_bytes <= base.EXTERNAL_SIGNAL_STAGE1_5F_TERMINAL_WRITE_SET_MAX_PEAK_BYTES


def test_f_constructs_storage_guard_before_output_root_creation(tmp_path, monkeypatch):
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner

    class StartupGuard:
        def __init__(self, output_root, stage, terminal_write_set_peak_bytes):
            assert not Path(output_root).exists()
            self.output_root = Path(output_root)

        def cleanup_owned_temp_files(self, _process_instance_id):
            return None

        def validate_startup(self):
            return {"status": "blocked_start_free_space", "storage_blocker": "storage_start_free_space"}

        def reserve_and_write(self, *, artifact_class, transient_peak_bytes, persistent_delta_bytes, write_func):
            return {"status": "ready", "written": True, "write_result": write_func()}

    monkeypatch.setattr("src.research.external_signal_shadow.stage1_5_storage_guard.StorageGuard", StartupGuard)
    output_root = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", ["run_stage1_5f_live_depth_observer.py", "--output-root", str(output_root)])

    with pytest.raises(SystemExit) as exc:
        runner.main()

    assert exc.value.code == 1


def test_runtime_storage_block_writes_terminal_f_summary(tmp_path, monkeypatch):
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageWriteBlocked

    class TerminalGuard:
        def __init__(self, output_root, stage):
            self.output_root = Path(output_root)
            self.stage = stage

        def reserve_and_write(self, *, artifact_class, transient_peak_bytes, persistent_delta_bytes, write_func):
            return {"status": "ready", "written": True, "write_result": write_func()}

    output_root = tmp_path / "out"
    guard = TerminalGuard(output_root, "1.5F")
    monkeypatch.setattr(runner, "_main", lambda: (_ for _ in ()).throw(StorageWriteBlocked(guard, {"storage_blocker": "root_budget_exceeded_for_normal_data"})))

    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 1
    summary = json.loads((output_root / "live_depth_observer_summary.json").read_text())
    assert summary["storage_blocker"] == "root_budget_exceeded_for_normal_data"
    assert summary["block_new_event_admission"] is True
    assert json.loads((output_root / "storage_failure_diagnostic.json").read_text())["diagnostic_type"] == "storage_write_blocked"


def test_runtime_main_publishes_bound_consumer_proof_atomically(tmp_path, monkeypatch):
    """The production loop, not a helper-only test, publishes F proof facts."""
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner

    d_root = tmp_path / "stage1_5d"
    events_dir = d_root / "events"
    events_dir.mkdir(parents=True)
    (events_dir / "2026-08-10.jsonl").write_text("")
    now_ms = int(__import__("time").time() * 1000)
    gate_path = d_root / "live_safety_gate_summary.json"
    gate_path.write_text(json.dumps({
        "runtime_gate_schema_version": 1,
        "decision": "stage1_5d_runtime_gate_ready",
        "status": "READY",
        "consumable_by_stage1_5f": True,
        "fatal_blockers": [],
        "source_root": str(d_root.resolve()),
        "generated_at_ms": now_ms,
        "live_trading_enabled": False,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))
    stage1_5e_summary = tmp_path / "stage1_5e.json"
    stage1_5e_summary.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
    }))
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({"symbols": []}))
    output_root = tmp_path / "stage1_5f"
    output_root.mkdir()
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark
    (output_root / "watermark.json").write_text(json.dumps(Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=now_ms - 1,
        updated_at_ms=now_ms,
    ).to_dict()))
    writes = []
    original_atomic_write = runner.write_live_depth_observer_summary_atomically
    bound_contract_hashes = []
    original_contract_write = runner.write_observer_root_contract_atomically

    monkeypatch.setattr(
        runner,
        "verify_consumer_static_proof",
        lambda _repo_root: {
            "valid": True,
            "startup_head_sha": "a" * 40,
            "manifest_sha256": runner.canonical_manifest_sha256("1.5F_v1", runner.CONSUMER_RUNTIME_MANIFEST),
        },
    )
    monkeypatch.setattr(
        runner,
        "verify_consumer_runtime_proof",
        lambda *_args: {"valid": True},
    )

    def capture_atomic_write(path, data, *, storage_guard):
        writes.append(dict(data))
        original_atomic_write(path, data, storage_guard=storage_guard)

    def capture_contract_write(*args, **kwargs):
        contract = original_contract_write(*args, **kwargs)
        if contract.get("source_stage1_5d_output_root_id"):
            bound_contract_hashes.append(runner.canonical_root_contract_sha256(contract))
        return contract

    monkeypatch.setattr(runner, "write_live_depth_observer_summary_atomically", capture_atomic_write)
    monkeypatch.setattr(runner, "write_observer_root_contract_atomically", capture_contract_write)
    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--stage1-5d-events-glob", str(events_dir / "*.jsonl"),
            "--stage1-5d-runtime-gate", str(gate_path),
            "--stage1-5e-summary", str(stage1_5e_summary),
            "--output-root", str(output_root),
            "--mock-response-dir", str(mock_dir),
            "--max-polls", "2",
            "--live-public-readonly",
        ]
        with pytest.raises(SystemExit) as exc:
            runner.main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    contract = json.loads((output_root / "observer_root_contract.json").read_text())
    expected_d_root_id = runner.canonical_root_id(d_root)
    assert contract["source_stage1_5d_output_root_id"] == expected_d_root_id
    assert contract["source_stage1_5d_events_root_id"] == expected_d_root_id
    assert contract["source_stage1_5d_runtime_gate_root_id"] == expected_d_root_id
    assert contract["consumer_static_attestation_verified"] is True
    assert len(bound_contract_hashes) == 1
    assert writes
    summary = json.loads((output_root / "live_depth_observer_summary.json").read_text())
    assert summary["consumer_static_attestation_verified"] is True
    assert summary["consumer_runtime_attestation_verified"] is True
    assert summary["consumer_root_id"] == contract["consumer_root_id"]
    assert summary["consumer_startup_commit_sha"] == contract["consumer_startup_commit_sha"]
    assert summary["storage_guard_status"] == "ready"
    assert summary["storage_blocker"] is None
    assert summary["storage_root_bytes"] >= 0
    assert summary["storage_root_max_bytes"] > summary["storage_root_bytes"]
    assert summary["storage_terminal_write_set_peak_bytes"] > 0
    assert summary["storage_emergency_blocker_reserve_bytes"] > 0
    assert summary["consumer_runtime_manifest_sha256"] == contract["consumer_runtime_manifest_sha256"]


def test_pending_anchor_deadline_state_semantics_fixture_provenance():
    import json
    from pathlib import Path
    fixture_dir = Path("tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics")
    metadata = json.loads((fixture_dir / "metadata.json").read_text(encoding="utf-8"))
    launch = json.loads((fixture_dir / "launch_event.json").read_text(encoding="utf-8"))

    assert metadata["fixture_provenance"] == "synthetic_offline_fixture_derived_from_server_evidence"
    assert metadata["raw_bapi_payload_available"] is False
    assert launch["source_contract_status"] == "formal_v2_valid"
    assert set(launch["symbols"]) == {
        "KUAISHOUUSDT", "MEITUANUSDT", "CSOPSKHYNIX2LUSDT", "CSOPSAMSUNG2LUSDT",
    }


def test_same_poll_launch_plus_postponed_without_anchor(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_summary import (
        build_live_depth_observer_summary,
    )

    states = {
        "es_postponed": EventSymbolState(
            event_symbol_id="es_postponed",
            event_id="e1",
            symbol="KUAISHOUUSDT",
            detected_at_ms=1000,
            status="pending_launch_anchor_missing",
            pending_reason="postponed_without_anchor",
        )
    }
    # Pending cancelled state must be excluded from pending_launch_observation_count
    cancelled_state = EventSymbolState(
        event_symbol_id="es_cancel",
        event_id="e2",
        symbol="CANCELUSDT",
        detected_at_ms=1000,
        status="pending_cancelled",
        pending_reason="official_schedule_cancelled",
    )

    filtered_pending = [s for s in list(states.values()) + [cancelled_state] if s.status.startswith("pending_") and s.status != "pending_cancelled"]

    summary = build_live_depth_observer_summary(
        decision="stage1_5f_observer_active",
        bootstrap_watermark_allowed=True,
        live_depth_observation_allowed=True,
        stage1_5d_summary_path="s_d",
        stage1_5e_summary_path="s_e",
        stage1_5e_context_missing=False,
        stage1_5e_context_suspicious=False,
        watermark_present=True,
        watermark_version=1,
        max_seen_detected_at_ms=1000,
        pre_watermark_events_ignored=0,
        post_watermark_events_accepted=1,
        active_states=[],
        completed_states=[],
        expired_states=[],
        failed_states=[],
        request_manifest_rows=[],
        heartbeat_rows=[],
        pending_states=filtered_pending,
    )
    summary_dict = summary.to_dict()
    assert summary_dict["pending_launch_observation_count"] == 1
    assert summary_dict["active_observation_count"] == 0


def test_four_symbol_staggered_long_lead_integration_matrix():
    import json
    from pathlib import Path

    from configs import base
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
        re_resolve_pending_anchor,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        create_pending_observation_state,
    )

    fixture_dir = Path("tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics")
    launch_event = json.loads((fixture_dir / "launch_event.json").read_text(encoding="utf-8"))

    first_seen_ms = launch_event["first_seen_at_ms"]  # 1_000_000
    exchangeinfo_state = {
        "available": True,
        "symbols": set(launch_event["symbols"]),
        "symbol_rows": {},
    }
    # Create 4 states
    states = {}
    for sym in launch_event["symbols"]:
        sym_row = {
            **launch_event,
            "symbol": sym,
            "event_symbol_id": f"es_{sym}",
            "observation_anchor_ms": launch_event["symbol_effective_observation_anchor_ms"][sym],
        }
        states[sym] = create_pending_observation_state(
            event_symbol_row=sym_row,
            status="pending_launch_time_in_future",
            diagnostics={"observation_anchor_ms": sym_row["observation_anchor_ms"], "source_contract_status": "formal_v2_valid"},
            now_ms=first_seen_ms,
        )

    # 1. Assert all 4 symbols have status == pending_launch_time_in_future and anchor_resolution_deadline_ms is None
    for sym, st in states.items():
        assert st.status == "pending_launch_time_in_future"
        assert st.anchor_resolution_deadline_ms is None

    # 2. At first_seen + 6h + 1ms (1,000,000 + 6*3600*1000 + 1 = 22,600,001 ms), re-resolve all states
    # Note: earliest anchor is at 58,600,000 ms, so 22,600,001 ms is still before anchor
    now_past_6h = first_seen_ms + 6 * 60 * 60 * 1000 + 1
    for sym, st in states.items():
        updated = re_resolve_pending_anchor(st, [launch_event], exchangeinfo_state=exchangeinfo_state, now_ms=now_past_6h)
        assert updated.status == "pending_launch_time_in_future", f"{sym} should survive 6h deadline"
        assert updated.anchor_resolution_deadline_ms is None
        assert updated.pending_terminal_reason == ""

    # 3. Each Symbol becomes ready only at its own anchor plus the launch guard.
    for sym, state in states.items():
        ready_at_ms = launch_event["symbol_effective_observation_anchor_ms"][sym] + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
        updated = re_resolve_pending_anchor(state, [launch_event], exchangeinfo_state=exchangeinfo_state, now_ms=ready_at_ms)
        assert updated.status == "pending_ready_for_admission", f"{sym} should become ready at its own anchor"
        for sibling, sibling_state in states.items():
            if sibling == sym:
                continue
            sibling_ready_at_ms = launch_event["symbol_effective_observation_anchor_ms"][sibling] + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS
            if ready_at_ms < sibling_ready_at_ms:
                sibling_updated = re_resolve_pending_anchor(
                    sibling_state, [launch_event], exchangeinfo_state=exchangeinfo_state, now_ms=ready_at_ms,
                )
                assert sibling_updated.status == "pending_launch_time_in_future", f"{sibling} promoted early"



def test_four_symbol_fixture_cancelled_state_is_excluded_by_runner_summary(tmp_path, monkeypatch):
    from pathlib import Path

    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark

    fixture_dir = Path("tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics")
    launch = json.loads((fixture_dir / "launch_event.json").read_text(encoding="utf-8"))
    revisions = json.loads((fixture_dir / "revisions.json").read_text(encoding="utf-8"))
    now_ms = 5_000_000
    event_file = tmp_path / "events.jsonl"
    event_file.write_text("".join(json.dumps(row) + "\n" for row in [launch, *revisions]))
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({
        "decision": "stage1_5d_event_detection_passed",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
    }))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
    }))
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({"symbols": [
        {
            "symbol": symbol,
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "onboardDate": launch["symbol_effective_observation_anchor_ms"][symbol],
        }
        for symbol in launch["symbols"]
    ]}))
    (mock_dir / "binance_depth_payload_healthy.json").write_text(json.dumps({
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
        "T": now_ms,
    }))
    output_root = tmp_path / "out"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps(Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=0,
        updated_at_ms=0,
    ).to_dict()))

    monkeypatch.setattr(runner.time, "time", lambda: now_ms / 1000)
    old_argv = sys.argv
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
            runner.main()
        assert exc.value.code == 0
    finally:
        sys.argv = old_argv

    latest_states = {}
    for line in (output_root / "observer_state.jsonl").read_text().splitlines():
        row = json.loads(line)
        latest_states[row["symbol"]] = row
    summary = json.loads((output_root / "live_depth_observer_summary.json").read_text())

    assert latest_states["CSOPSKHYNIX2LUSDT"]["status"] == "pending_cancelled"
    assert summary["pending_launch_observation_count"] == 3
    assert summary["active_observation_count"] == 0


@pytest.mark.parametrize(
    ("case", "expected_status"),
    [
        ("same_poll_postpone", "pending_launch_anchor_missing"),
        ("same_poll_advance_future", "pending_launch_time_in_future"),
        ("same_poll_advance_due", "active"),
        ("same_poll_advance_due_capacity", "pending_observation_capacity"),
        ("same_poll_advance_due_exchange_hidden", "pending_exchangeinfo_symbol_not_visible_after_anchor"),
        ("same_poll_advance_due_runtime_gate", None),
        ("same_poll_cancel", "pending_cancelled"),
        ("same_poll_equal_available_at_conflict", "pending_anchor_conflict"),
    ],
)
@pytest.mark.parametrize("reverse_input_order", [False, True])
def test_same_poll_schedule_revision_prevents_stale_launch_admission(
    tmp_path, monkeypatch, case, expected_status, reverse_input_order,
):
    from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
        build_formal_event_anchor_contract_row,
        build_formal_schedule_revision_row,
        build_symbol_anchor_contract,
    )
    from scripts.external_signal_shadow import run_stage1_5f_live_depth_observer as runner
    from src.research.external_signal_shadow import stage1_5f_live_depth_observer_budget as budget
    from src.research.external_signal_shadow import stage1_5f_live_depth_observer_loader as loader
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark

    now_ms = 2_000_000
    symbol = "CANCELUSDT"
    source_article_id = "launch-cancelled-same-poll"
    provenance = {
        "payload_sha256": "a" * 64,
        "parser_version": "test",
        "raw_time_text": "1970-01-01 00:33 UTC",
        "timezone_text": "UTC",
        "node_path": "body[0]",
        "logical_block_id": "launch-cancelled-same-poll",
        "schedule_text_context": "Launch Time",
        "mapping_method": "single_symbol_article_unique_futures_launch_time",
    }
    launch = build_formal_event_anchor_contract_row(
        base_event={
            "event_id": "launch-cancelled-same-poll-event",
            "event_type": "futures_contract_launch",
            "source_article_id": source_article_id,
            "stable_event_key": f"binance_{source_article_id}_{symbol}",
            "detected_at_ms": now_ms - 2_000,
            "symbols": [symbol],
            "formal_event_consumable_by_stage1_5f": True,
        },
        symbol_contracts={
            symbol: build_symbol_anchor_contract(
                symbol=symbol,
                official_schedule_anchor_ms=now_ms - 1_000,
                exchangeinfo_onboard_date_ms=now_ms - 1_000,
                anchor_contract_decision_at_ms=now_ms - 1_000,
                official_schedule_revision_id="launch-revision-id",
                official_schedule_available_at_ms=now_ms - 1_000,
                mapping_confidence="exact_single_symbol",
                provenance=provenance,
            ),
        },
    )
    revision_common = {
        "supersedes_source_article_id": source_article_id,
        "symbol": symbol,
        "revision_available_at_ms": now_ms - 500,
        "producer_decision_at_ms": now_ms - 500,
        "linking_index_as_of_ms": now_ms - 500,
        "revision_payload_version_id": "revision-payload-v1",
        "revision_observation_id": "revision-observation-v1",
        "provenance": provenance,
    }
    if case == "same_poll_postpone":
        revisions = [build_formal_schedule_revision_row(
            source_article_id="postponed-revision-article",
            revision_intent="postponed_without_anchor",
            revision_id="postponed-revision-id",
            revision_semantic_id="postponed-revision-id",
            revision_application_id="postponed-revision-id",
            revision_payload_hash="b" * 64,
            **revision_common,
        )]
    elif case in {
        "same_poll_advance_future",
        "same_poll_advance_due",
        "same_poll_advance_due_capacity",
        "same_poll_advance_due_exchange_hidden",
        "same_poll_advance_due_runtime_gate",
    }:
        revisions = [build_formal_schedule_revision_row(
            source_article_id="advanced-revision-article",
            revision_intent="rescheduled_with_new_anchor",
            revised_anchor_ms=now_ms + (60_000 if case.endswith("future") else -500),
            revision_id="advanced-revision-id",
            revision_semantic_id="advanced-revision-id",
            revision_application_id="advanced-revision-id",
            revision_payload_hash="c" * 64,
            **revision_common,
        )]
    elif case == "same_poll_cancel":
        revisions = [build_formal_schedule_revision_row(
            source_article_id="cancelled-revision-article",
            revision_intent="cancelled",
            revision_id="cancelled-revision-id",
            revision_semantic_id="cancelled-revision-id",
            revision_application_id="cancelled-revision-id",
            revision_payload_hash="d" * 64,
            **revision_common,
        )]
    else:
        revisions = [
            build_formal_schedule_revision_row(
                source_article_id="conflict-a-revision-article",
                revision_intent="rescheduled_with_new_anchor",
                revised_anchor_ms=now_ms + 60_000,
                revision_id="conflict-a-revision-id",
                revision_semantic_id="conflict-a-revision-id",
                revision_application_id="conflict-a-revision-id",
                revision_payload_hash="e" * 64,
                **revision_common,
            ),
            build_formal_schedule_revision_row(
                source_article_id="conflict-b-revision-article",
                revision_intent="rescheduled_with_new_anchor",
                revised_anchor_ms=now_ms + 120_000,
                revision_id="conflict-b-revision-id",
                revision_semantic_id="conflict-b-revision-id",
                revision_application_id="conflict-b-revision-id",
                revision_payload_hash="f" * 64,
                **revision_common,
            ),
        ]

    rows = [launch, *revisions]
    if reverse_input_order:
        rows.reverse()
    event_file = tmp_path / "events.jsonl"
    event_file.write_text("".join(json.dumps(row) + "\n" for row in rows))
    summary_d = tmp_path / "summary_d.json"
    summary_d.write_text(json.dumps({
        "decision": "stage1_5d_event_detection_passed",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
    }))
    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
    }))
    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    exchangeinfo_symbols = [] if case == "same_poll_advance_due_exchange_hidden" else [{
        "symbol": symbol,
        "status": "TRADING",
        "contractType": "PERPETUAL",
        "quoteAsset": "USDT",
        "marginAsset": "USDT",
        "onboardDate": now_ms - 1_000,
    }]
    (mock_dir / "binance_exchangeinfo_payload.json").write_text(json.dumps({"symbols": exchangeinfo_symbols}))
    (mock_dir / "binance_depth_payload_healthy.json").write_text(json.dumps({
        "bids": [["100.0", "10.0"]],
        "asks": [["101.0", "10.0"]],
        "T": now_ms,
    }))
    output_root = tmp_path / "out"
    output_root.mkdir()
    (output_root / "watermark.json").write_text(json.dumps(Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=now_ms - 10_000,
        updated_at_ms=now_ms - 10_000,
    ).to_dict()))

    runtime_gate_path = None
    if case == "same_poll_advance_due_runtime_gate":
        runtime_gate_path = tmp_path / "live_safety_gate_summary.json"
        runtime_gate_path.write_text(json.dumps({
            "runtime_gate_schema_version": 1,
            "decision": "stage1_5d_runtime_gate_initializing",
            "source_root": str(tmp_path),
            "events_stream_relative_path": "events/*.jsonl",
            "generated_at_ms": now_ms,
        }))

    monkeypatch.setattr(runner.time, "time", lambda: now_ms / 1000)
    if case == "same_poll_advance_due_capacity":
        monkeypatch.setattr(budget, "can_start_new_observation", lambda *_args: False)

    re_resolve_call_count = 0
    original_re_resolve = loader.re_resolve_pending_anchor

    def counting_re_resolve(*args, **kwargs):
        nonlocal re_resolve_call_count
        re_resolve_call_count += 1
        return original_re_resolve(*args, **kwargs)

    monkeypatch.setattr(loader, "re_resolve_pending_anchor", counting_re_resolve)

    def run_one_poll():
        old_argv = sys.argv
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
            if runtime_gate_path is not None:
                sys.argv.extend(["--stage1-5d-runtime-gate", str(runtime_gate_path)])
            with pytest.raises(SystemExit) as exc:
                runner.main()
            assert exc.value.code == 0
        finally:
            sys.argv = old_argv

    run_one_poll()

    state_file = output_root / "observer_state.jsonl"
    states = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()] if state_file.exists() else []
    if expected_status is None:
        assert not any(state["status"] == "active" for state in states)
        assert not list((output_root / "events_accepted").glob("**/*.jsonl"))
        assert not list((output_root / "depth_snapshots").glob("**/*.jsonl"))
        return

    assert states[-1]["status"] == expected_status
    if expected_status == "active":
        assert list((output_root / "events_accepted").glob("**/*.jsonl"))
        assert list((output_root / "depth_snapshots").glob("**/*.jsonl"))
    else:
        assert not list((output_root / "events_accepted").glob("**/*.jsonl"))
        assert not list((output_root / "depth_snapshots").glob("**/*.jsonl"))

    if case == "same_poll_cancel":
        summary = json.loads((output_root / "live_depth_observer_summary.json").read_text())
        assert summary["pending_launch_observation_count"] == 0
        assert summary["active_observation_count"] == 0
        assert re_resolve_call_count == 0

        run_one_poll()
        states = [json.loads(line) for line in (output_root / "observer_state.jsonl").read_text().splitlines() if line.strip()]
        assert states[-1]["status"] == "pending_cancelled"
        registry_rows = [
            json.loads(line)
            for line in (output_root / "schedule_revision_registry.jsonl").read_text().splitlines()
            if line.strip()
        ]
        assert sum(row["status"] == "revision_applied" for row in registry_rows) == 1
        assert not list((output_root / "events_accepted").glob("**/*.jsonl"))

    if case == "same_poll_postpone":
        first_deadline_ms = states[-1]["anchor_resolution_deadline_ms"]
        run_one_poll()
        reloaded_states = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
        assert reloaded_states[-1]["status"] == "pending_launch_anchor_missing"
        assert reloaded_states[-1]["anchor_resolution_deadline_ms"] == first_deadline_ms
        assert not list((output_root / "events_accepted").glob("**/*.jsonl"))


def test_stage1_5f_same_root_resume_without_bootstrap(tmp_path, monkeypatch):
    import time

    from scripts.external_signal_shadow import (
        run_stage1_5f_live_depth_observer as runner,
    )
    from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import (
        EventSymbolState,
    )
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_state import (
        load_latest_state_by_event_symbol_id,
    )

    now_ms = int(time.time() * 1000)
    output_root = tmp_path / "f_out"
    output_root.mkdir(parents=True, exist_ok=True)
    d_root = tmp_path / "d_out"
    events_dir = d_root / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    (events_dir / "2026-08-17.jsonl").write_text("")
    gate_path = d_root / "live_safety_gate_summary.json"
    gate_path.write_text(json.dumps({
        "runtime_gate_schema_version": 1,
        "decision": "stage1_5d_runtime_gate_ready",
        "status": "READY",
        "consumable_by_stage1_5f": True,
        "fatal_blockers": [],
        "source_root": str(d_root.resolve()),
        "generated_at_ms": now_ms,
        "live_trading_enabled": False,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    summary_e = tmp_path / "summary_e.json"
    summary_e.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer",
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    # Seed watermark
    watermark_data = {
        "watermark_version": 1,
        "max_seen_detected_at_ms": now_ms - 100_000,
        "seen_event_ids": ["seeded_event_1"],
        "seen_source_article_ids": ["seeded_article_1"],
        "seen_stable_event_keys": ["seeded_key_1"],
        "updated_at_ms": now_ms - 100_000,
    }
    watermark_path = output_root / "watermark.json"
    watermark_path.write_text(json.dumps(watermark_data))
    seeded_watermark_bytes = watermark_path.read_bytes()

    seeded_state = EventSymbolState(
        event_symbol_id="seeded_event_symbol",
        event_id="seeded_event",
        symbol="BTCUSDT",
        status="completed",
        source_article_id="seeded_article",
    )
    state_path = output_root / "observer_state.jsonl"
    state_path.write_text(json.dumps(seeded_state.to_dict()) + "\n")

    # Seed a B-era contract/summary. C must reuse this root rather than bootstrap it.
    runner.write_observer_root_contract_atomically(
        str(output_root),
        "v2_production",
        reason="initial_test_setup",
        storage_guard=StorageGuard(output_root=output_root, stage="1.5F"),
        source_binding_facts={
            "source_stage1_5d_output_root_id": str(d_root.resolve()),
            "source_stage1_5d_events_root_id": str(d_root.resolve()),
            "source_stage1_5d_runtime_gate_root_id": str(d_root.resolve()),
        },
    )
    (output_root / "live_depth_observer_summary.json").write_text(json.dumps({
        "consumer_process_instance_id": "old_process_b",
        "consumer_root_id": runner.canonical_root_id(output_root),
    }))

    # Mock response dir for network-free run
    mock_dir = tmp_path / "mock_responses"
    mock_dir.mkdir(parents=True, exist_ok=True)
    with open(mock_dir / "exchangeinfo.json", "w") as f:
        json.dump({"symbols": []}, f)

    args = [
        "run_stage1_5f_live_depth_observer.py",
        "--stage1-5d-events-glob", str(events_dir / "*.jsonl"),
        "--stage1-5d-runtime-gate", str(gate_path),
        "--stage1-5e-summary", str(summary_e),
        "--output-root", str(output_root),
        "--mock-response-dir", str(mock_dir),
        "--max-polls", "1",
    ]
    assert "--bootstrap-watermark" not in args
    monkeypatch.setattr(
        runner,
        "verify_consumer_static_proof",
        lambda _repo_root: {
            "valid": True,
            "startup_head_sha": "commit_c",
            "manifest_sha256": runner.canonical_manifest_sha256(
                "1.5F_v1", runner.CONSUMER_RUNTIME_MANIFEST
            ),
        },
    )
    monkeypatch.setattr(runner, "verify_consumer_runtime_proof", lambda *_args: {"valid": True})

    orig_argv = sys.argv
    try:
        sys.argv = args
        with pytest.raises(SystemExit) as exc:
            runner.main()
        assert exc.value.code == 0
    finally:
        sys.argv = orig_argv

    # Same root resumes its durable B state without a bootstrap rewrite.
    assert watermark_path.read_bytes() == seeded_watermark_bytes
    reloaded_states = load_latest_state_by_event_symbol_id(state_path)
    assert reloaded_states[seeded_state.event_symbol_id] == seeded_state

    summary_path = output_root / "live_depth_observer_summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["block_new_event_admission"] is False
    assert summary["consumer_root_id"] == runner.canonical_root_id(output_root)
    assert summary["consumer_process_instance_id"] != "old_process_b"
    assert summary["consumer_startup_commit_sha"] == "commit_c"
    assert summary["consumer_runtime_attestation_verified"] is True
    assert summary["consumer_runtime_attestation_compromised"] is False

    root_contract = json.loads((output_root / "observer_root_contract.json").read_text())
    expected_d_root_id = runner.canonical_root_id(d_root)
    assert root_contract["consumer_root_id"] == runner.canonical_root_id(output_root)
    assert root_contract["source_stage1_5d_output_root_id"] == expected_d_root_id
    assert root_contract["source_stage1_5d_events_root_id"] == expected_d_root_id
    assert root_contract["source_stage1_5d_runtime_gate_root_id"] == expected_d_root_id
