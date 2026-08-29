import json
import sys

from scripts.external_signal_shadow.review_stage1_5g_live_depth_evidence import main
from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import (
    make_stage1_5f_fixture_root,
)


def test_stage1_5g_cli_writes_summary_and_review(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path)
    output_root = tmp_path / "stage1_5g_review"
    summary_out = output_root / "stage1_5g_summary.json"
    review_out = output_root / "stage1_5g_review.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
            "--output-summary",
            str(summary_out),
            "--output-review",
            str(review_out),
        ],
    )

    assert main() == 0
    assert summary_out.exists()
    assert review_out.exists()

    data = json.loads(summary_out.read_text(encoding="utf-8"))
    assert "schema_version" in data
    assert data["trade_signal_allowed"] is False
    assert "Stage 1.5G" in review_out.read_text(encoding="utf-8")


def test_cli_does_not_write_inside_stage1_5f_output_root_by_default(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path / "stage1_5f_root")
    output_root = tmp_path / "stage1_5g" / "reviews" / "run1"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
        ],
    )

    assert main() == 0
    assert (output_root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
    assert not (root / "stage1_5g_live_depth_evidence_review_summary.json").exists()
    # review markdown must also land inside out_root, never in docs/reviews/
    review_files = list(output_root.glob("*-review_CN.md"))
    assert len(review_files) == 1, f"Expected 1 review markdown in out_root, got: {review_files}"



def test_stage1_5g_cli_returns_nonzero_for_missing_output_root(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            "/nonexistent_path_abc_123",
        ],
    )
    assert main() != 0


def test_cli_does_not_write_quarantine_artifacts_for_clean_pass(tmp_path, monkeypatch):
    from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import (
        make_stage1_5f_fixture_root,
    )

    root = make_stage1_5f_fixture_root(tmp_path)
    output_root = tmp_path / "review_out"
    monkeypatch.setattr("sys.argv", [
        "review_stage1_5g_live_depth_evidence.py",
        "--stage1-5f-output-root", str(root),
        "--output-root", str(output_root),
    ])

    assert main() == 0
    assert not (output_root / "quarantined_invalid_book_rows.jsonl").exists()
    assert not (output_root / "depth_quality_input_rows.jsonl").exists()
    assert not (output_root / "stage1_5g_quarantine_summary.json").exists()


def test_cli_writes_quarantine_artifacts_for_quarantine_pass(tmp_path, monkeypatch):
    from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_loader import (
        _write_source_manifest,
    )

    root = make_stage1_5f_fixture_root(tmp_path)
    snap_dir = root / "depth_snapshots" / "20260706"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_file = snap_dir / "es1.jsonl"

    event_file = root / "events_accepted" / "20260706.jsonl"
    event = {
        "event_symbol_id": "es1",
        "symbol": "BTC/USDT",
        "evidence_label": "announcement_and_launch_time",
        "watermark_version": 1,
        "watermark_max_seen_detected_at_ms": 1000,
        "symbol_effective_launch_times_ms": {"BTC/USDT": 1000000},
    }
    event_file.write_text(json.dumps(event) + "\n", encoding="utf-8")

    state_file = root / "observer_state.jsonl"
    state = {
        "event_symbol_id": "es1",
        "symbol": "BTC/USDT",
        "status": "completed",
        "depth_snapshot_count": 718,
        "max_gap_ms": 60000,
        "observation_started_at_ms": 1000000,
    }
    state_file.write_text(json.dumps(state) + "\n", encoding="utf-8")

    summary_file = root / "live_depth_observer_summary.json"
    summary = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "completed_observation_count": 1,
        "observation_window_ms": 43200000,
        "snapshot_interval_ms": 60000,
        "min_snapshot_count_required": 684,
        "total_snapshots_collected": 718,
        "request_success_rate": 1.0,
        "total_requests_made": 718,
        "failed_requests_count": 0,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 0,
        "last_heartbeat_at_ms": 10000,
        "heartbeat_count": 1,
    }
    summary_file.write_text(json.dumps(summary), encoding="utf-8")

    snapshots = []
    launch_ms = 1000000
    for i in range(718):
        ts = launch_ms + i * 60000
        if i < 11 or i == 320:
            s = {
                "event_symbol_id": "es1",
                "symbol": "BTC/USDT",
                "fetched_at_ms": ts,
                "best_bid": None,
                "best_ask": None,
                "mid_price": None,
                "spread_bps": None,
                "depth_status": "invalid",
                "slippage_status": "invalid_depth",
                "top_bid_depth_usdt": 0.0,
                "top_ask_depth_usdt": 0.0,
                "buy_slippage_bps": None,
                "sell_slippage_bps": None,
            }
        else:
            s = {
                "event_symbol_id": "es1",
                "symbol": "BTC/USDT",
                "fetched_at_ms": ts,
                "best_bid": 100.0,
                "best_ask": 100.1,
                "mid_price": 100.05,
                "spread_bps": 10.0,
                "buy_slippage_bps": 5.0,
                "sell_slippage_bps": 5.0,
                "top_bid_depth_usdt": 1000.0,
                "top_ask_depth_usdt": 1000.0,
            }
        snapshots.append(s)

    snap_file.write_text("\n".join(json.dumps(s) for s in snapshots) + "\n", encoding="utf-8")

    manifest_file = root / "request_manifest" / "20260706.jsonl"
    manifest_rows = [{"event_symbol_id": "es1", "symbol": "BTC/USDT", "http_status": 200} for _ in range(718)]
    manifest_file.write_text("\n".join(json.dumps(r) for r in manifest_rows) + "\n", encoding="utf-8")
    _write_source_manifest(root)

    output_root = tmp_path / "review_out"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
        ],
    )

    assert main() == 0
    assert (output_root / "quarantined_invalid_book_rows.jsonl").exists()
    assert (output_root / "depth_quality_input_rows.jsonl").exists()
    assert (output_root / "stage1_5g_quarantine_summary.json").exists()
    quarantine_summary = json.loads((output_root / "stage1_5g_quarantine_summary.json").read_text(encoding="utf-8"))
    assert quarantine_summary["invalid_book_by_phase"] == {
        "launch_warmup": 11,
        "observation_initial": 0,
        "midrun": 1,
    }
    assert quarantine_summary["invalid_book_by_reason"]["launch_warmup_empty_book"] == 11
    assert quarantine_summary["first_valid_book_latency_ms"] == 11 * 60_000
    assert quarantine_summary["max_consecutive_invalid"] == 11
    assert quarantine_summary["max_consecutive_invalid_after_warmup"] == 1

    manifest_path = output_root / "stage1_5g_review_manifest.json"
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["schema_version"] == 2
    assert "stage1_5g_review_id" in manifest_data
    assert "artifacts" in manifest_data
    for art_name in ("summary", "quarantine_summary", "quarantined_invalid_book_rows", "depth_quality_input_rows"):
        assert art_name in manifest_data["artifacts"]
        art_path = output_root / manifest_data["artifacts"][art_name]["relative_path"]
        assert art_path.exists()


def test_cli_rejects_preexisting_output_root(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path)
    output_root = tmp_path / "existing_review_out"
    output_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
        ],
    )

    assert main() != 0


def test_cli_rejects_output_paths_outside_fresh_review_root(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path / "source")
    output_root = tmp_path / "review_out"
    external_summary = tmp_path / "outside_summary.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
            "--output-summary",
            str(external_summary),
        ],
    )

    assert main() != 0
    assert not external_summary.exists()


def test_cli_rejects_output_root_inside_stage1_5f_source(tmp_path, monkeypatch):
    root = make_stage1_5f_fixture_root(tmp_path / "source")
    output_root = root / "derived_review"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "review_stage1_5g_live_depth_evidence.py",
            "--stage1-5f-output-root",
            str(root),
            "--output-root",
            str(output_root),
        ],
    )

    assert main() != 0
    assert not output_root.exists()
