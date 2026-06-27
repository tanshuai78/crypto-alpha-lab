import json
import sys

from scripts.external_signal_shadow.review_stage1_5f_live_depth_observer import main


def test_review_contains_decision_and_safety_flags(tmp_path):
    summary_path = tmp_path / "live_depth_observer_summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "stage1_5f_observer_running_no_new_event",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "dummy_d",
        "stage1_5e_summary_path": "dummy_e",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 123456789,
        "pre_watermark_events_ignored": 10,
        "post_watermark_events_accepted": 2,
        "active_observation_count": 0,
        "completed_observation_count": 0,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 576,
        "total_snapshots_collected": 0,
        "request_success_rate": 0.99,
        "total_requests_made": 100,
        "failed_requests_count": 1,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 2,
        "last_heartbeat_at_ms": 123456000,
        "heartbeat_count": 50,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "research_result_valid": False,
        "blocker": None,
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    args = [
        "review_stage1_5f_live_depth_observer.py",
        "--summary", str(summary_path),
        "--output-review", str(review_path),
    ]

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    assert review_path.exists()
    content = review_path.read_text(encoding="utf-8")

    assert "stage1_5f_observer_running_no_new_event" in content
    assert "execution_feasibility_claim_allowed" in content
    assert "trade_signal_allowed" in content
    assert "paper_trading_allowed" in content
    assert "live_trading_allowed" in content
    assert "execution_engine_allowed" in content
    assert "alpha_interpretation_allowed" in content


def test_review_states_close_price_replay_execution_feasibility_still_unproven(tmp_path):
    summary_path = tmp_path / "live_depth_observer_summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "dummy_d",
        "stage1_5e_summary_path": "dummy_e",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 123456789,
        "pre_watermark_events_ignored": 10,
        "post_watermark_events_accepted": 2,
        "active_observation_count": 0,
        "completed_observation_count": 2,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 576,
        "total_snapshots_collected": 1200,
        "request_success_rate": 0.99,
        "total_requests_made": 100,
        "failed_requests_count": 1,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 2,
        "last_heartbeat_at_ms": 123456000,
        "heartbeat_count": 50,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "research_result_valid": True,
        "blocker": None,
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    args = [
        "review_stage1_5f_live_depth_observer.py",
        "--summary", str(summary_path),
        "--output-review", str(review_path),
    ]

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    content = review_path.read_text(encoding="utf-8")
    assert "execution feasibility" in content.lower() or "执行可行性" in content
    assert "未被证明" in content or "still not proven" in content.lower() or "未证明" in content


def test_review_has_no_placeholders(tmp_path):
    summary_path = tmp_path / "live_depth_observer_summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "dummy_d",
        "stage1_5e_summary_path": "dummy_e",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 123456789,
        "pre_watermark_events_ignored": 10,
        "post_watermark_events_accepted": 2,
        "active_observation_count": 0,
        "completed_observation_count": 2,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 576,
        "total_snapshots_collected": 1200,
        "request_success_rate": 0.99,
        "total_requests_made": 100,
        "failed_requests_count": 1,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 2,
        "last_heartbeat_at_ms": 123456000,
        "heartbeat_count": 50,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "research_result_valid": True,
        "blocker": None,
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    args = [
        "review_stage1_5f_live_depth_observer.py",
        "--summary", str(summary_path),
        "--output-review", str(review_path),
    ]

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    content = review_path.read_text(encoding="utf-8")
    for ph in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert ph not in content


def test_review_reports_watermark_and_snapshot_coverage(tmp_path):
    summary_path = tmp_path / "live_depth_observer_summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "dummy_d",
        "stage1_5e_summary_path": "dummy_e",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 123456789,
        "pre_watermark_events_ignored": 123,
        "post_watermark_events_accepted": 456,
        "active_observation_count": 1,
        "completed_observation_count": 2,
        "expired_observation_count": 3,
        "failed_observation_count": 4,
        "min_snapshot_count_required": 576,
        "total_snapshots_collected": 1200,
        "request_success_rate": 0.99,
        "total_requests_made": 100,
        "failed_requests_count": 1,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 2,
        "last_heartbeat_at_ms": 123456000,
        "heartbeat_count": 50,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "research_result_valid": True,
        "blocker": None,
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    # Write dummy states
    state_path = tmp_path / "observer_state.jsonl"
    with open(state_path, "w") as f:
        f.write(json.dumps({
            "event_symbol_id": "dummy_es_id_1",
            "symbol": "BTCUSDT",
            "status": "completed",
            "depth_snapshot_count": 600,
            "max_gap_ms": 60000,
            "max_gap_pass": True,
            "coverage_ratio_pass": True,
            "research_result_valid": True
        }) + "\n")

    # Write dummy snapshots
    snapshots_dir = tmp_path / "depth_snapshots" / "20260626"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    with open(snapshots_dir / "dummy_es_id_1.jsonl", "w") as f:
        f.write(json.dumps({
            "event_symbol_id": "dummy_es_id_1",
            "symbol": "BTCUSDT",
            "fetched_at_ms": 1000,
            "spread_bps": 1.5,
            "buy_slippage_bps": 2.5,
            "sell_slippage_bps": 3.5,
            "top_bid_depth_usdt": 10000.0,
            "top_ask_depth_usdt": 20000.0,
        }) + "\n")

    args = [
        "review_stage1_5f_live_depth_observer.py",
        "--summary", str(summary_path),
        "--output-review", str(review_path),
    ]

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    content = review_path.read_text(encoding="utf-8")
    assert "BTCUSDT" in content
    assert "123" in content
    assert "456" in content
    assert "completed" in content
    assert "Median: 1.5" in content or "1.50" in content
    assert "Median: 2.5" in content or "2.50" in content
    assert "Median: 10000.0" in content or "10000.00" in content or "10000" in content


def test_review_reports_allowed_next_action_stage1_5g_only_when_depth_evidence_collected(tmp_path):
    # Scenario A: decision is depth_evidence_collected
    summary_path = tmp_path / "live_depth_observer_summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": True,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "dummy_d",
        "stage1_5e_summary_path": "dummy_e",
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 123456789,
        "pre_watermark_events_ignored": 10,
        "post_watermark_events_accepted": 2,
        "active_observation_count": 0,
        "completed_observation_count": 2,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 576,
        "total_snapshots_collected": 1200,
        "request_success_rate": 0.99,
        "total_requests_made": 100,
        "failed_requests_count": 1,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 2,
        "last_heartbeat_at_ms": 123456000,
        "heartbeat_count": 50,
        "execution_feasibility_claim_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "research_result_valid": True,
        "blocker": None,
    }

    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    args = [
        "review_stage1_5f_live_depth_observer.py",
        "--summary", str(summary_path),
        "--output-review", str(review_path),
    ]

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    content = review_path.read_text(encoding="utf-8")
    assert "stage1_5g_write_depth_evidence_review_plan" in content

    # Scenario B: decision is in progress
    summary_data["decision"] = "stage1_5f_observer_event_observation_in_progress"
    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    orig_argv = sys.argv
    try:
        sys.argv = args
        assert main() == 0
    finally:
        sys.argv = orig_argv

    content2 = review_path.read_text(encoding="utf-8")
    assert "continue_server_observer" in content2
    assert "stage1_5g_write_depth_evidence_review_plan" not in content2
