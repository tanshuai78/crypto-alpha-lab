import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_daily_path,
    build_detail_payload_path,
    build_stream_paths,
    enforce_payload_budget,
    load_payload_version_first_observed,
    record_payload_version_first_observed,
    write_detail_payload,
    write_detail_payload_append_only,
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


def test_payload_version_first_observed_survives_reload(tmp_path):
    registry = tmp_path / "revision_payload_versions.jsonl"
    first = record_payload_version_first_observed(
        registry, source_article_id="a" * 32, payload_sha256="hash-a", observed_at_ms=1_000
    )
    second = record_payload_version_first_observed(
        registry, source_article_id="a" * 32, payload_sha256="hash-a", observed_at_ms=2_000
    )

    assert first == second == 1_000
    assert load_payload_version_first_observed(registry)[("a" * 32, "hash-a")] == 1_000


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


def test_write_detail_payload_append_only_includes_variant_timestamp_hash(tmp_path):
    result1 = write_detail_payload_append_only(
        root=tmp_path,
        timestamp_ms=1710000000000,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SHAZUSDT"}}',
        parsed_payload={"data": {"body": "SHAZUSDT"}},
        content_type="application/json",
        http_status=200,
    )
    result2 = write_detail_payload_append_only(
        root=tmp_path,
        timestamp_ms=1710000060000,
        source_article_id="f43403ef11974998bc0f46420826577a",
        detail_fetch_variant="bapi_article_detail_query",
        raw_bytes=b'{"data":{"body":"SOFIUSDT"}}',
        parsed_payload={"data": {"body": "SOFIUSDT"}},
        content_type="application/json",
        http_status=200,
    )
    assert result1["payload_path"] != result2["payload_path"]
    assert "f43403ef11974998bc0f46420826577a" in result1["payload_path"]
    assert "bapi_article_detail_query" in result1["payload_path"]
    assert (tmp_path / result1["payload_path"]).exists()
    assert (tmp_path / result2["payload_path"]).exists()


def test_write_detail_payload_append_only_rejects_bad_variant(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="detail_fetch_variant_invalid"):
        write_detail_payload_append_only(
            root=tmp_path,
            timestamp_ms=1710000000000,
            source_article_id="abc",
            detail_fetch_variant="../bad",
            raw_bytes=b'{"x":1}',
            parsed_payload={"x": 1},
            content_type="application/json",
            http_status=200,
        )
