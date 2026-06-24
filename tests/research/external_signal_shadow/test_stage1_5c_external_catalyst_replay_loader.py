import json

import pytest

from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_loader import (
    assert_stage1_5b_ready,
    load_price_bars,
    load_stage1_5b_symbol_events,
)


def test_assert_stage1_5b_ready_rejects_non_ready_summary(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({
        "decision": "stage1_5b_event_table_failed",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    with pytest.raises(ValueError, match="stage1_5b_event_table_ready"):
        assert_stage1_5b_ready(path)


def test_load_stage1_5b_symbol_events_requires_1_5c_pending_not_candidate_allowed(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 1710000000000,
        "available_at_ms": 1710000900000,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "directional_hypothesis": "undefined",
        "signed_direction": None,
    }) + "\n")
    rows = load_stage1_5b_symbol_events(path)
    assert len(rows) == 1
    assert rows[0]["stage1_5b_replay_candidate_allowed_upstream"] is False


def test_load_stage1_5b_symbol_events_rejects_replay_allowed_true(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 1710000000000,
        "available_at_ms": 1710000900000,
        "stage1_5c_review_pending": True,
        "price_coverage_gate_passed": True,
        "candidate_allowed_for_close_price_replay": True,
        "replay_allowed": True,
    }) + "\n")
    with pytest.raises(ValueError, match="Stage 1.5B must not pre-allow replay"):
        load_stage1_5b_symbol_events(path)


def test_load_price_bars_normalizes_jsonl(tmp_path):
    path = tmp_path / "price.jsonl"
    path.write_text(json.dumps({
        "symbol": "ABCUSDT",
        "open_time": 1710000000000,
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100.5",
        "quote_volume": "1234567",
    }) + "\n")
    rows = load_price_bars(path)
    assert rows[0]["symbol"] == "ABCUSDT"
    assert rows[0]["bar_start_ms"] == 1710000000000
    assert rows[0]["bar_end_ms"] == 1710000900000
    assert rows[0]["close"] == 100.5


def test_stage1_5c_uses_coverage_pass_event_table_for_rerun(tmp_path):
    # Verify we can load standard event objects that contain the stage1_5c1 normalized headers
    path = tmp_path / "pass_events.jsonl"
    path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "available_at_ms": 1710000900000,
        "stage1_5c_rerun_candidate": True,
        "replay_price_source_allowed": "futures_only",
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
    }) + "\n")
    rows = load_stage1_5b_symbol_events(path)
    assert len(rows) == 1
    assert rows[0]["symbol_event_id"] == "s1"


def test_spot_proxy_archive_is_not_accepted_as_replay_price_source(tmp_path):
    path = tmp_path / "price.jsonl"
    path.write_text("\n".join([
        json.dumps({
            "symbol": "ABCUSDT",
            "bar_start_ms": 1710000000000,
            "open": "100",
            "high": "101",
            "low": "99",
            "close": "100.5",
            "quote_volume": "100000",
            "source": "binance_spot_15m_proxy",
        }),
        json.dumps({
            "symbol": "XYZUSDT",
            "bar_start_ms": 1710000000000,
            "open": "100",
            "high": "101",
            "low": "99",
            "close": "100.5",
            "quote_volume": "100000",
            "source": "binance_um_futures_15m",
        })
    ]) + "\n")
    rows = load_price_bars(path)
    # The spot proxy bar (ABCUSDT) must be discarded, only futures bar (XYZUSDT) should remain
    assert len(rows) == 1
    assert rows[0]["symbol"] == "XYZUSDT"
    assert rows[0]["source"] == "binance_um_futures_15m"

