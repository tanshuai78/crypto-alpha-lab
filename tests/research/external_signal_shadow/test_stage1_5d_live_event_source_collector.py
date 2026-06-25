from src.research.external_signal_shadow.stage1_5d_live_event_source_collector import (
    run_one_poll_cycle,
)


def test_poll_cycle_parses_futures_launch_and_queues_first_bar():
    payload = {
        "data": {
            "catalogs": [{
                "articles": [{
                    "code": "abc",
                    "title": "Binance Futures Will Launch USDⓈ-Margined ABCUSDT Perpetual Contract",
                    "releaseDate": 1710000000000,
                }]
            }]
        }
    }
    result = run_one_poll_cycle(
        payload=payload,
        detected_at_ms=1710000060000,
        source_parent_url="https://www.binance.com/en/support/announcement",
        first_bar_queue=[],
    )
    assert len(result["events"]) == 1
    assert result["events"][0]["event_type"] == "futures_contract_launch"
    assert len(result["first_bar_queue"]) == 1
    assert result["heartbeat"]["poll_success"] is True


def test_poll_cycle_zero_events_still_heartbeat_success():
    payload = {"data": {"catalogs": [{"articles": []}]}}
    result = run_one_poll_cycle(payload=payload, detected_at_ms=1710000060000, source_parent_url="https://www.binance.com", first_bar_queue=[])
    assert result["events"] == []
    assert result["heartbeat"]["poll_success"] is True


def test_poll_cycle_schema_drift_is_not_clean_zero_events():
    payload = {"data": {"items": []}}
    result = run_one_poll_cycle(payload=payload, detected_at_ms=1710000060000, source_parent_url="https://www.binance.com", first_bar_queue=[])
    assert result["events"] == []
    assert result["heartbeat"]["poll_success"] is False
    assert result["heartbeat"]["source_format_drift"] is True
