import hashlib
import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    load_stage1_5g_inputs,
)


def _write_source_manifest(root: Path) -> None:
    manifest = root / "SHA256SUMS"
    entries = [
        path.resolve()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest
    ]
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path}"
        for path in entries
    ]
    # The retained archive format has a stale self-entry; production verifies
    # the manifest bytes separately and excludes this one recursive digest.
    lines.append(f"{'0' * 64}  {manifest.resolve()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_stage1_5f_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "stage1_5f_root"
    root.mkdir(parents=True, exist_ok=True)

    # 1. Summary
    summary = {
        "decision": "stage1_5f_observer_depth_evidence_collected",
        "bootstrap_watermark_allowed": False,
        "live_depth_observation_allowed": True,
        "stage1_5d_summary_path": "a",
        "stage1_5e_summary_path": None,
        "stage1_5e_context_missing": False,
        "stage1_5e_context_suspicious": False,
        "watermark_present": True,
        "watermark_version": 1,
        "max_seen_detected_at_ms": 1000,
        "pre_watermark_events_ignored": 0,
        "post_watermark_events_accepted": 1,
        "active_observation_count": 0,
        "completed_observation_count": 1,
        "expired_observation_count": 0,
        "failed_observation_count": 0,
        "min_snapshot_count_required": 684,
        "total_snapshots_collected": 3,
        "request_success_rate": 1.0,
        "total_requests_made": 3,
        "failed_requests_count": 0,
        "consecutive_network_errors": 0,
        "max_consecutive_network_errors_seen": 0,
        "last_heartbeat_at_ms": 10000,
        "heartbeat_count": 1,
    }
    (root / "live_depth_observer_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    # 2. Watermark
    watermark = {
        "watermark_version": 1,
        "max_seen_detected_at_ms": 1000,
        "seen_event_ids": ["ev1"],
    }
    (root / "watermark.json").write_text(json.dumps(watermark), encoding="utf-8")

    # 3. Observer State
    state = {
        "event_symbol_id": "es1",
        "symbol": "BTC/USDT",
        "status": "completed",
        "depth_snapshot_count": 3,
    }
    (root / "observer_state.jsonl").write_text(json.dumps(state) + "\n", encoding="utf-8")

    # 4. Accepted Events
    (root / "events_accepted").mkdir(exist_ok=True)
    event = {
        "event_symbol_id": "es1",
        "symbol": "BTC/USDT",
        "evidence_label": "announcement_and_launch_time",
        "watermark_version": 1,
        "watermark_max_seen_detected_at_ms": 1000,
    }
    (root / "events_accepted" / "20260706.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")

    # 5. Snapshots
    (root / "depth_snapshots" / "20260706").mkdir(parents=True, exist_ok=True)
    s1 = {"event_symbol_id": "es1", "symbol": "BTC/USDT", "best_bid": 100.0, "best_ask": 101.0}
    s2 = {"event_symbol_id": "es1", "symbol": "BTC/USDT", "best_bid": 100.1, "best_ask": 101.1}
    s3 = {"event_symbol_id": "es1", "symbol": "BTC/USDT", "best_bid": 100.2, "best_ask": 101.2}
    snapshot_lines = "\n".join(json.dumps(s) for s in (s1, s2, s3)) + "\n"
    (root / "depth_snapshots" / "20260706" / "es1.jsonl").write_text(snapshot_lines, encoding="utf-8")

    # 6. Request Manifest
    (root / "request_manifest").mkdir(exist_ok=True)
    r1 = {"event_symbol_id": "es1", "http_status": 200}
    r2 = {"event_symbol_id": "es1", "http_status": 200}
    r3 = {"event_symbol_id": "es1", "http_status": 200}
    manifest_lines = "\n".join(json.dumps(r) for r in (r1, r2, r3)) + "\n"
    (root / "request_manifest" / "20260706.jsonl").write_text(manifest_lines, encoding="utf-8")

    # 7. Heartbeat
    (root / "heartbeat").mkdir(exist_ok=True)
    hb = {"poll_index": 1}
    (root / "heartbeat" / "20260706.jsonl").write_text(json.dumps(hb) + "\n", encoding="utf-8")

    _write_source_manifest(root)

    return root


def make_minimal_stage1_5f_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "stage1_5f_minimal"
    root.mkdir(parents=True, exist_ok=True)

    summary = {"decision": "stage1_5f_observer_depth_evidence_collected"}
    (root / "live_depth_observer_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    watermark = {"watermark_version": 1}
    (root / "watermark.json").write_text(json.dumps(watermark), encoding="utf-8")

    # Only observer_state is present, no accepted_events, snapshots etc.
    (root / "observer_state.jsonl").write_text("", encoding="utf-8")

    return root


def make_stage1_5f_fixture_root_without_snapshot_file(tmp_path: Path) -> Path:
    root = make_stage1_5f_fixture_root(tmp_path)
    # Delete the snapshot file for 'es1'
    (root / "depth_snapshots" / "20260706" / "es1.jsonl").unlink()
    return root


def make_stage1_5f_fixture_root_with_corrupt_snapshot_jsonl(tmp_path: Path) -> Path:
    root = make_stage1_5f_fixture_root(tmp_path)
    # Overwrite the snapshot file with a corrupt JSON line
    (root / "depth_snapshots" / "20260706" / "es1.jsonl").write_text(
        '{"event_symbol_id": "es1", "symbol": "BTC/USDT", "best_bid": 100.0, "best_ask": 101.0}\n{invalid_json}\n',
        encoding="utf-8",
    )
    return root


def test_load_stage1_5g_inputs_reads_stage1_5f_output_root(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert bundle.summary["decision"] == "stage1_5f_observer_depth_evidence_collected"
    assert bundle.watermark["watermark_version"] == 1
    assert len(bundle.accepted_events) == 1
    assert len(bundle.snapshots) == 3
    assert len(bundle.states) == 1
    assert len(bundle.request_manifest_rows) == 3
    assert bundle.parse_error_count == 0
    assert bundle.loader_blockers == []


def test_load_stage1_5g_inputs_tolerates_missing_rejected_and_manifest_dirs(tmp_path):
    root = make_minimal_stage1_5f_fixture_root(tmp_path)
    bundle = load_stage1_5g_inputs(root)
    assert bundle.rejected_events == []
    assert bundle.request_manifest_rows == []
    assert bundle.parse_error_count == 0


def test_loader_missing_snapshot_file_keeps_state_and_empty_snapshots(tmp_path):
    root = make_stage1_5f_fixture_root_without_snapshot_file(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert len(bundle.accepted_events) == 1
    assert len(bundle.states) == 1
    assert bundle.states[0]["event_symbol_id"] == "es1"
    # Note: loader reads the state from observer_state.jsonl where we set depth_snapshot_count=3,
    # but the physical files are loaded into bundle.snapshots. So states retains it, but snapshots becomes empty.
    # We should override depth_snapshot_count to 0 if the physical snapshot file is missing.
    assert bundle.states[0]["depth_snapshot_count"] == 0
    assert bundle.snapshots == []
    assert bundle.loader_blockers == []


def test_loader_jsonl_parse_error_blocks_review(tmp_path):
    root = make_stage1_5f_fixture_root_with_corrupt_snapshot_jsonl(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert "jsonl_parse_error" in bundle.loader_blockers
    assert bundle.parse_error_count == 1
    assert bundle.total_jsonl_line_count == 8
    # The valid line is still parsed
    assert len(bundle.snapshots) == 1


def test_loader_blocks_duplicate_stable_event_symbol_identity(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    stable_key = "binance_article_1_futures_contract_launch_BTCUSDT"
    accepted_rows = [
        {
            "event_symbol_id": "es1",
            "stable_event_symbol_key": stable_key,
            "source_article_id": "article_1",
            "event_type": "futures_contract_launch",
            "symbol": "BTCUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        },
        {
            "event_symbol_id": "es2",
            "stable_event_symbol_key": stable_key,
            "source_article_id": "article_1",
            "event_type": "futures_contract_launch",
            "symbol": "BTCUSDT",
            "evidence_label": "announcement_and_launch_time",
            "watermark_version": 1,
            "watermark_max_seen_detected_at_ms": 1000,
        },
    ]
    (root / "events_accepted" / "20260706.jsonl").write_text(
        "\n".join(json.dumps(row) for row in accepted_rows) + "\n",
        encoding="utf-8",
    )
    state_rows = [
        {
            "event_symbol_id": "es1",
            "stable_event_symbol_key": stable_key,
            "source_article_id": "article_1",
            "symbol": "BTCUSDT",
            "status": "completed",
            "depth_snapshot_count": 1,
        },
        {
            "event_symbol_id": "es2",
            "stable_event_symbol_key": stable_key,
            "source_article_id": "article_1",
            "symbol": "BTCUSDT",
            "status": "completed",
            "depth_snapshot_count": 1,
        },
    ]
    (root / "observer_state.jsonl").write_text(
        "\n".join(json.dumps(row) for row in state_rows) + "\n",
        encoding="utf-8",
    )

    bundle = load_stage1_5g_inputs(root)

    assert "duplicate_stable_event_symbol_identity" in bundle.loader_blockers


def test_loader_missing_watermark_records_blocker_not_not_ready(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    (root / "watermark.json").unlink()

    bundle = load_stage1_5g_inputs(root)

    assert bundle.watermark == {}
    assert "missing_or_unreadable_watermark" in bundle.loader_blockers
