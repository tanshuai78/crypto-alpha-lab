import json
import shutil
from pathlib import Path

from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    load_stage1_5g_inputs,
)
from tests.research.external_signal_shadow.test_stage1_5g_live_depth_evidence_review_decision import (
    make_canonical_stage1_5f_source_root,
    seal_disposable_stage1_5f_source_root,
)


def make_stage1_5f_fixture_root(tmp_path: Path) -> Path:
    return make_canonical_stage1_5f_source_root(tmp_path / "stage1_5f_root", seal=True)


def make_minimal_stage1_5f_fixture_root(tmp_path: Path) -> Path:
    root = make_canonical_stage1_5f_source_root(tmp_path / "stage1_5f_minimal", seal=False)
    shutil.rmtree(root / "events_rejected", ignore_errors=True)
    shutil.rmtree(root / "request_manifest", ignore_errors=True)
    seal_disposable_stage1_5f_source_root(root)
    return root


def make_stage1_5f_fixture_root_without_snapshot_file(tmp_path: Path) -> Path:
    root = make_stage1_5f_fixture_root(tmp_path)
    for f in (root / "depth_snapshots").rglob("*.jsonl"):
        f.unlink()
    seal_disposable_stage1_5f_source_root(root)
    return root


def make_stage1_5f_fixture_root_with_corrupt_snapshot_jsonl(tmp_path: Path) -> Path:
    root = make_stage1_5f_fixture_root(tmp_path)
    snap_file = next((root / "depth_snapshots").rglob("*.jsonl"))
    with snap_file.open("a", encoding="utf-8") as fh:
        fh.write("{invalid_json}\n")
    seal_disposable_stage1_5f_source_root(root)
    return root


def test_load_stage1_5g_inputs_reads_stage1_5f_output_root(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert bundle.summary["decision"] == "stage1_5f_observer_depth_evidence_collected"
    assert bundle.watermark["watermark_version"] == 1
    assert len(bundle.accepted_events) == 1
    assert len(bundle.snapshots) == 5
    assert len(bundle.states) == 1
    assert len(bundle.request_manifest_rows) == 5
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
    assert bundle.states[0]["depth_snapshot_count"] == 0
    assert bundle.snapshots == []
    assert bundle.loader_blockers == []


def test_loader_jsonl_parse_error_blocks_review(tmp_path):
    root = make_stage1_5f_fixture_root_with_corrupt_snapshot_jsonl(tmp_path)
    bundle = load_stage1_5g_inputs(root)

    assert "jsonl_parse_error" in bundle.loader_blockers
    assert bundle.parse_error_count == 1
    assert bundle.total_jsonl_line_count >= 6
    assert len(bundle.snapshots) == 5


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
    (root / "events_accepted" / "2026-09-08.jsonl").write_text(
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
    seal_disposable_stage1_5f_source_root(root)

    bundle = load_stage1_5g_inputs(root)

    assert "duplicate_stable_event_symbol_identity" in bundle.loader_blockers


def test_loader_missing_watermark_records_blocker_not_not_ready(tmp_path):
    root = make_stage1_5f_fixture_root(tmp_path)
    (root / "watermark.json").unlink()
    seal_disposable_stage1_5f_source_root(root)

    bundle = load_stage1_5g_inputs(root)

    assert bundle.watermark == {}
    assert "missing_or_unreadable_watermark" in bundle.loader_blockers
