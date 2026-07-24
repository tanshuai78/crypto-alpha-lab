import json
import os
import sys
import pytest

from scripts.external_signal_shadow.run_stage1_5f_live_depth_observer import main


def test_end_to_end_historical_anchor_rejection_hygiene_flow(tmp_path):
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(
        json.dumps({
            "event_id": "event-ebay",
            "event_type": "futures_contract_launch",
            "source_article_id": "f598c7bb87d74b8c995b9f67bf210be1",
            "stable_event_key": "binance_f598_MULTI",
            "detected_at_ms": 1784822376255,
            "symbols": ["EBAYUSDT"],
            "symbol_effective_launch_times_ms": {"EBAYUSDT": 1780995600000},
        }) + "\n"
    )
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
    output_root = tmp_path / "out"

    # Step 1: Bootstrap watermark v2
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

    w = json.loads((output_root / "watermark.json").read_text())
    assert w["watermark_schema_version"] == 2
    assert w["bootstrap_root_id"]

    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{
            "symbol": "EBAYUSDT",
            "status": "TRADING",
            "contractType": "TRADIFI_PERPETUAL",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "onboardDate": 1780996800000,
        }]
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

    # Assertion 1: events_rejected folder is EMPTY (no historical anchor pre-bootstrap events)
    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []

    # Assertion 2: observer_state.jsonl contains terminal ignored state with consumable_by_stage1_5g = False
    state_file = output_root / "observer_state.jsonl"
    states = [json.loads(line) for line in state_file.read_text().splitlines() if line.strip()]
    assert len(states) == 1
    assert states[0]["status"] == "ignored_historical_anchor_pre_bootstrap"
    assert states[0]["terminal_hygiene_id"]
    assert states[0]["consumable_by_stage1_5g"] is False

    # Assertion 3: historical_anchor_hygiene_diagnostics folder contains diagnostic file
    diag_files = list((output_root / "historical_anchor_hygiene_diagnostics").glob("**/*.jsonl"))
    assert len(diag_files) == 1
    diags = [json.loads(line) for line in diag_files[0].read_text().splitlines() if line.strip()]
    assert len(diags) == 1
    assert diags[0]["diagnostic_type"] == "historical_anchor_pre_bootstrap_ignored"
    assert diags[0]["consumable_by_stage1_5g"] is False


def test_end_to_end_rejection_hygiene_malformed_rows(tmp_path):
    fixture_path = "tests/fixtures/external_signal_shadow/stage1_5f/rejected_hygiene/malformed_historical_rejected_rows.jsonl"
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
    output_root = tmp_path / "out"

    old_argv = sys.argv
    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", fixture_path,
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
        "symbols": [{"symbol": "POPMARTUSDT", "status": "TRADING", "contractType": "PERPETUAL", "quoteAsset": "USDT", "marginAsset": "USDT", "onboardDate": 1780996800000}]
    }))

    try:
        sys.argv = [
            "run_stage1_5f_live_depth_observer.py",
            "--fixture-events-jsonl", fixture_path,
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

    # Malformed row must NOT enter events_rejected or observer_state
    assert list((output_root / "events_rejected").glob("**/*.jsonl")) == []

    # Diagnostics should contain malformed_source_identity diagnostic
    diag_files = list((output_root / "rejection_hygiene_diagnostics").glob("**/*.jsonl"))
    assert len(diag_files) == 1
    diags = [json.loads(line) for line in diag_files[0].read_text().splitlines() if line.strip()]
    assert len(diags) >= 1
    assert diags[0]["diagnostic_type"] == "malformed_source_identity"


def test_end_to_end_genuine_rejection_retains_identity(tmp_path):
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(
        json.dumps({
            "event_id": "event-post-wt",
            "event_type": "futures_contract_launch",
            "source_article_id": "art-post-wt",
            "stable_event_key": "binance_art_post_wt",
            "detected_at_ms": 1784830000000,
            "symbols": ["LATEUSDT"],
            "symbol_effective_launch_times_ms": {"LATEUSDT": 1780000000000},
        }) + "\n"
    )
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
    output_root = tmp_path / "out"

    # Bootstrap watermark before detected_at_ms
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

    # Set watermark max_seen_detected_at_ms to 1784820000000 so detected_at_ms (1784830000000) is post-watermark
    w_path = output_root / "watermark.json"
    w_data = json.loads(w_path.read_text())
    w_data["max_seen_detected_at_ms"] = 1784820000000
    w_data["bootstrap_max_seen_detected_at_ms"] = 1784820000000
    w_path.write_text(json.dumps(w_data))

    mock_dir = tmp_path / "mock"
    mock_dir.mkdir()
    (mock_dir / "exchangeinfo.json").write_text(json.dumps({
        "symbols": [{
            "symbol": "LATEUSDT",
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "marginAsset": "USDT",
            "onboardDate": 1780000000000,
        }]
    }))

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

    rejected_files = list((output_root / "events_rejected").glob("**/*.jsonl"))
    assert len(rejected_files) == 1
    rejected_rows = [json.loads(line) for line in rejected_files[0].read_text().splitlines() if line.strip()]
    assert len(rejected_rows) == 1
    r = rejected_rows[0]
    assert r["rejected_reason"] == "rejected_launch_anchor_age_exceeded"
    assert r["rejection_reason"] == "rejected_launch_anchor_age_exceeded"
    assert r["event_id"] == "event-post-wt"
    assert r["source_article_id"] == "art-post-wt"
    assert r["symbol"] == "LATEUSDT"
    assert r["detected_at_ms"] == 1784830000000
    assert r["consumable_by_stage1_5g"] is True
    assert r["terminal_hygiene_id"]
