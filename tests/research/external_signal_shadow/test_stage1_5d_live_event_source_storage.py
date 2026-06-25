import json

from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_daily_path,
    build_stream_paths,
    enforce_payload_budget,
)


def test_build_daily_path_includes_utc_date(tmp_path):
    path = build_daily_path(tmp_path, "events", 1710000000000)
    assert "events" in str(path)
    assert path.name.endswith(".jsonl")


def test_build_stream_paths_under_output_root(tmp_path):
    paths = build_stream_paths(tmp_path, timestamp_ms=1710000000000)
    assert paths["events"].parent.parent == tmp_path
    assert "events" in str(paths["events"])
    assert "raw_payloads" in str(paths["raw_payloads"])
    assert paths["summary"].name == "binance_futures_launch_smoke_summary.json"


def test_append_jsonl_writes_one_row(tmp_path):
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"a": 1})
    assert json.loads(path.read_text().strip()) == {"a": 1}


def test_enforce_payload_budget_blocks_large_day(tmp_path):
    path = tmp_path / "raw.jsonl"
    path.write_text("x" * 101)
    result = enforce_payload_budget(path, max_bytes=100)
    assert result["storage_budget_passed"] is False
    assert result["blocker"] == "max_raw_payload_bytes_per_day_exceeded"
