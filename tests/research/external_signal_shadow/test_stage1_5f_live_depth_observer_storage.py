import shutil

import pytest

from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_storage import (
    append_jsonl,
    build_daily_path,
    read_jsonl,
    write_json,
)


def create_test_guard(root):
    return StorageGuard(
        output_root=root,
        stage="1.5F",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
    )


def test_build_daily_path_uses_utc_date():
    # 1719416400000 ms is 2024-06-26 15:40:00 UTC
    root = "/tmp/data"
    path = build_daily_path(root, "events_accepted", 1719416400000)
    assert path == "/tmp/data/events_accepted/20240626.jsonl"


def test_append_jsonl_preserves_existing_rows(tmp_path):
    target = tmp_path / "test.jsonl"
    guard = create_test_guard(tmp_path)
    append_jsonl(str(target), {"a": 1}, storage_guard=guard)
    append_jsonl(str(target), {"b": 2}, storage_guard=guard)

    rows = read_jsonl(str(target))
    assert len(rows) == 2
    assert rows[0] == {"a": 1}
    assert rows[1] == {"b": 2}


def test_write_json_requires_explicit_storage_guard(tmp_path):
    with pytest.raises(TypeError, match="storage_guard_required"):
        write_json(str(tmp_path / "summary.json"), {"a": 1}, storage_guard=None)


def test_depth_snapshot_path_is_per_event_symbol_id():
    root = "/tmp/data"
    path = build_daily_path(root, "depth_snapshots", 1719416400000, event_symbol_id="abc123id")
    assert path == "/tmp/data/depth_snapshots/20240626/abc123id.jsonl"


def test_storage_does_not_write_outside_output_root(tmp_path):
    # Try to write with directory traversal
    root = str(tmp_path / "root")
    # If build_daily_path tries directory traversal, it should raise ValueError
    with pytest.raises(ValueError):
        build_daily_path(root, "../outside", 1719416400000)
