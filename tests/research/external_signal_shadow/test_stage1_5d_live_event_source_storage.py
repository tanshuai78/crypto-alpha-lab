import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_daily_path,
    build_detail_payload_path,
    build_stream_paths,
    enforce_payload_budget,
    write_detail_payload,
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


def test_build_detail_payload_path_under_announcement_detail(tmp_path):
    path = build_detail_payload_path(tmp_path, timestamp_ms=1710000000000, source_article_id="abc123", suffix="json")
    assert path.parent.name == "2024-03-09"
    assert path.parent.parent.name == "announcement_detail"
    assert path.parent.parent.parent.name == "raw_payloads"
    assert path.name == "abc123.json"


def test_write_detail_payload_persists_payload_and_returns_hash(tmp_path):
    result = write_detail_payload(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="abc123",
        payload={"data": {"body": "ABCUSDT"}},
    )

    assert result["payload_size_bytes"] > 0
    assert len(result["payload_sha256"]) == 64
    path = result["payload_path"]
    assert path.endswith("abc123.json")
    assert (tmp_path / path).exists() or Path(path).exists()


def test_write_detail_payload_handles_bytes_payload(tmp_path):
    result = write_detail_payload(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="abc123",
        payload=b"AMDUSDT QCOMUSDT",
    )

    assert result["payload_path"].endswith("abc123.txt")
    assert len(result["payload_sha256"]) == 64


