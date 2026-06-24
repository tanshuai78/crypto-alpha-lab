import json

from src.research.external_signal_shadow.stage1_5c1_price_coverage_loader import (
    build_event_request_window,
    load_stage1_5b_events,
    merge_symbol_windows,
)


def test_load_stage1_5b_events_keeps_allowed_event_types(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join([
        json.dumps({"symbol_event_id": "a", "event_type": "futures_contract_launch", "symbol": "ABCUSDT", "available_at_ms": 1}),
        json.dumps({"symbol_event_id": "b", "event_type": "unknown", "symbol": "XYZUSDT", "available_at_ms": 2}),
    ]) + "\n")
    rows = load_stage1_5b_events(path)
    assert [r["symbol_event_id"] for r in rows] == ["a"]


def test_delisting_window_requires_pre_event_history():
    event = {
        "symbol_event_id": "d1",
        "event_type": "exchange_delisting_notice",
        "symbol": "ABCUSDT",
        "available_at_ms": 100 * 24 * 3600_000,
    }
    w = build_event_request_window(event, now_ms=200 * 24 * 3600_000)
    assert w["start_ms"] < event["available_at_ms"] - 30 * 24 * 3600_000 + 1
    assert w["end_ms"] > event["available_at_ms"] + 36 * 3600_000


def test_futures_launch_window_starts_at_available_at_not_30d_before():
    event = {
        "symbol_event_id": "f1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 100 * 24 * 3600_000,
    }
    w = build_event_request_window(event, now_ms=200 * 24 * 3600_000)
    assert w["start_ms"] == event["available_at_ms"]
    assert w["event_type"] == "futures_contract_launch"


def test_merge_symbol_windows_merges_overlapping_ranges():
    windows = [
        {"source_type": "futures", "symbol": "ABCUSDT", "start_ms": 0, "end_ms": 1000},
        {"source_type": "futures", "symbol": "ABCUSDT", "start_ms": 1001, "end_ms": 2000},
        {"source_type": "futures", "symbol": "XYZUSDT", "start_ms": 0, "end_ms": 1000},
    ]
    merged = merge_symbol_windows(windows, merge_gap_ms=10)
    assert len(merged) == 2
    abc = [w for w in merged if w["symbol"] == "ABCUSDT"][0]
    assert abc["start_ms"] == 0
    assert abc["end_ms"] == 2000
