import json
import shutil
from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_5_storage_guard import StorageGuard
from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_daily_path,
    build_detail_payload_path,
    build_stream_paths,
    enforce_payload_budget,
    load_payload_version_first_observed,
    record_payload_version_first_observed,
    write_detail_payload_append_only,
)


def create_test_guard(root: Path) -> StorageGuard:
    return StorageGuard(
        output_root=root,
        stage="1.5D",
        disk_usage_func=lambda path: shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3),
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
    guard = create_test_guard(tmp_path)
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"a": 1}, storage_guard=guard)
    assert json.loads(path.read_text().strip()) == {"a": 1}


def test_payload_version_first_observed_survives_reload(tmp_path):
    guard = create_test_guard(tmp_path)
    registry = tmp_path / "revision_payload_versions.jsonl"
    first = record_payload_version_first_observed(
        registry, source_article_id="a" * 32, payload_sha256="hash-a", observed_at_ms=1_000, storage_guard=guard
    )
    second = record_payload_version_first_observed(
        registry, source_article_id="a" * 32, payload_sha256="hash-a", observed_at_ms=2_000, storage_guard=guard
    )

    assert first == second == 1_000
    assert load_payload_version_first_observed(registry)[("a" * 32, "hash-a")] == 1_000



def test_enforce_payload_budget_blocks_large_raw_directory(tmp_path):
    raw_dir = tmp_path / "raw_payloads" / "announcement_detail" / "article1"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "test.bin").write_bytes(b"x" * 101)

    result = enforce_payload_budget(tmp_path, max_bytes=100)
    assert result["storage_budget_passed"] is False
    assert result["blocker"] == "max_raw_payload_bytes_exceeded"


def test_build_detail_payload_path_under_announcement_detail(tmp_path):
    path = build_detail_payload_path(
        tmp_path,
        source_article_id="abc123",
        detail_fetch_variant="bapi_article_detail_query",
        raw_payload_sha256="1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    )
    assert path.name == "bapi_article_detail_query.1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef.bin"
    assert path.parent.name == "abc123"
    assert path.parent.parent.name == "announcement_detail"
    assert path.parent.parent.parent.name == "raw_payloads"


def test_write_detail_payload_append_only_content_addressed(tmp_path):
    guard = create_test_guard(tmp_path)
    res1 = write_detail_payload_append_only(
        root=tmp_path,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SHAZUSDT"}}',
        storage_guard=guard,
        parsed_payload={"data": {"body": "SHAZUSDT"}},
    )
    assert res1["raw_payload_persisted"] is True
    assert res1["payload_path"].endswith(".bin")
    assert (tmp_path / res1["payload_path"]).exists()

    # Retry same article, variant, raw_bytes -> returns same file path
    res2 = write_detail_payload_append_only(
        root=tmp_path,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SHAZUSDT"}}',
        storage_guard=guard,
        parsed_payload={"data": {"body": "SHAZUSDT"}},
    )
    assert res2["payload_path"] == res1["payload_path"]


def test_content_addressed_writer_requires_guard(tmp_path):
    with pytest.raises(TypeError, match="storage_guard_required"):
        write_detail_payload_append_only(
            root=tmp_path,
            source_article_id="abc",
            detail_fetch_variant="bapi_article_detail_query",
            raw_bytes=b'{"x":1}',
            storage_guard=None,  # Should fail
        )
