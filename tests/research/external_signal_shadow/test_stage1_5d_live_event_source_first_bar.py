from src.research.external_signal_shadow.stage1_5d_live_event_source_first_bar import (
    check_first_bar_for_event,
    fetch_first_bar_status_for_event,
    process_first_bar_queue,
)


def test_first_bar_found_at_or_after_detection():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    bars = {"ABCUSDT": [{"bar_start_ms": 900}, {"bar_start_ms": 1_800}]}
    updated = check_first_bar_for_event(event, bars, now_ms=2_000)
    assert updated["first_futures_bar_status"] == "found"
    assert updated["first_futures_bar_start_ms"] == 1_800


def test_first_bar_not_yet_available_before_timeout():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    updated = check_first_bar_for_event(event, {}, now_ms=2_000, timeout_ms=24 * 3600_000)
    assert updated["first_futures_bar_status"] == "not_yet_available"


def test_first_bar_all_bars_before_detection_is_not_yet_available():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    bars = {"ABCUSDT": [{"bar_start_ms": 100}, {"bar_start_ms": 900}]}
    updated = check_first_bar_for_event(event, bars, now_ms=2_000, timeout_ms=24 * 3600_000)
    assert updated["first_futures_bar_status"] == "not_yet_available"
    assert updated["first_futures_bar_start_ms"] is None


def test_first_bar_observer_budget_does_not_process_entire_queue():
    queue = [{"event_id": f"e{i}", "symbols": ["ABCUSDT"], "detected_at_ms": 0} for i in range(5)]
    processed, remaining = process_first_bar_queue(queue, bars_by_symbol={}, now_ms=1_000, budget=2)
    assert len(processed) == 2
    assert len(remaining) == 3


def test_first_bar_network_error_keeps_event_observable_without_blocking():
    event = {"event_id": "e1", "symbols": ["ABCUSDT"], "detected_at_ms": 1_000}
    result = fetch_first_bar_status_for_event(
        event=event,
        fetch_result={"ok": False, "error": "timeout", "request_manifest_row": {"error": "timeout"}},
        now_ms=2_000,
    )
    assert result["first_futures_bar_status"] == "network_error"
    assert result["request_manifest_rows"][0]["error"] == "timeout"
