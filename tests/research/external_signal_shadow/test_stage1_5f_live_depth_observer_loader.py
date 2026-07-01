import json

import pytest

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import (
    classify_event_symbol_eligibility,
    flatten_event_symbols,
    iter_stage1_5d_event_rows,
    make_event_symbol_id,
    validate_stage1_5d_summary,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark


def test_only_futures_contract_launch_is_eligible():
    event = {
        "event_id": "e1",
        "event_type": "spot_listing",  # Wrong type
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    # mock exchangeinfo_state (available=True, symbols=["ABCUSDT"])
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    # Classify
    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "wrong_event_type"


def test_event_age_gate_skips_old_event():
    # Age exceeds 15min (900_000 ms)
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    # now is 1000 + 15*60*1000 + 1 = 901001
    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000 + 15 * 60 * 1000 + 1, w, exinfo, {})
    assert status == "rejected"
    assert reason == "age_exceeded"


def test_symbol_not_in_current_exchangeinfo_is_skipped_not_failed():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"XYZUSDT"}}  # ABCUSDT missing

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "symbol_not_in_exchangeinfo"


def test_exchangeinfo_unavailable_keeps_event_pending_not_symbol_not_found():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": False, "symbols": set()}  # exchangeInfo unavailable

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "pending"
    assert reason == "exchangeinfo_unavailable"


def test_multiple_symbols_are_flattened_to_event_symbol_rows():
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT", "XYZUSDT"],
    }
    rows = list(flatten_event_symbols(event))
    assert len(rows) == 2
    assert rows[0]["symbol"] == "ABCUSDT"
    assert rows[1]["symbol"] == "XYZUSDT"


def test_event_symbol_id_is_stable():
    event = {"event_id": "e1"}
    h1 = make_event_symbol_id(event, "ABCUSDT")
    h2 = make_event_symbol_id(event, "ABCUSDT")
    assert h1 == h2
    assert len(h1) == 64
    assert h1.lower() == h1


def test_event_symbol_id_is_stable_across_restarts_with_same_input():
    event = {"event_id": "e1"}
    h1 = make_event_symbol_id(event, "ABCUSDT")

    # Re-run
    h2 = make_event_symbol_id({"event_id": "e1"}, "ABCUSDT")
    assert h1 == h2


def test_event_symbol_id_fallback_is_stable_when_event_id_missing():
    event = {
        "source_name": "s1",
        "source_article_id": "art1",
        "source_detail_url": "https://binance.com/announcement/123/",
        "source_published_at_ms": 1000,
    }
    h1 = make_event_symbol_id(event, "ABCUSDT")

    event2 = {
        "source_name": "s1",
        "source_article_id": "art1",
        "source_detail_url": "https://binance.com/announcement/123",  # slightly different trailing slash
        "source_published_at_ms": 1000,
    }
    h2 = make_event_symbol_id(event2, "ABCUSDT")
    # Due to URL normalization (Advisory A), they should produce the exact same ID
    assert h1 == h2


def test_stage1_5f_rejects_invalid_stage1_5d_summary(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_data = {
        "decision": "stage1_5d_smoke_invalid",  # invalid decision
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    with pytest.raises(ValueError) as exc:
        validate_stage1_5d_summary(str(summary_path))
    assert "invalid" in str(exc.value)


def test_stage1_5f_rejects_stage1_5d_summary_with_trading_flag_true(tmp_path):
    summary_path = tmp_path / "summary.json"
    summary_data = {
        "decision": "stage1_5d_event_detection_passed",
        "paper_trading_allowed": True,  # should be False
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }
    with open(summary_path, "w") as f:
        json.dump(summary_data, f)

    with pytest.raises(ValueError) as exc:
        validate_stage1_5d_summary(str(summary_path))
    assert "safety" in str(exc.value) or "trading" in str(exc.value)


def test_rejected_event_rows_include_rejection_reason():
    event = {
        "event_id": "e1",
        "event_type": "spot_listing",
        "detected_at_ms": 1000,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, [], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "wrong_event_type"


def test_pre_watermark_rejection_reason_is_ignored_not_failure():
    # event is pre-watermark
    event = {
        "event_id": "e1",
        "event_type": "futures_contract_launch",
        "detected_at_ms": 400,
        "symbols": ["ABCUSDT"],
    }
    w = Watermark(1, 500, ["e1"], [], [], 500)
    exinfo = {"available": True, "symbols": {"ABCUSDT"}}

    status, reason = classify_event_symbol_eligibility(event, "ABCUSDT", 1000, w, exinfo, {})
    assert status == "rejected"
    assert reason == "pre_watermark"


def test_stage1_5f_loader_accepts_legacy_1_5d_event_rows_without_symbol_extraction_diagnostics(tmp_path):
    events = tmp_path / "events.jsonl"
    events.write_text(json.dumps({
        "event_id": "legacy-event",
        "event_type": "futures_contract_launch",
        "symbols": ["ABCUSDT"],
        "detected_at_ms": 1_000,
        "source_article_id": "abc",
    }) + "\n")

    rows = list(iter_stage1_5d_event_rows(str(events)))
    flattened = list(flatten_event_symbols(rows[0]))

    assert flattened[0]["symbol"] == "ABCUSDT"
    assert make_event_symbol_id(rows[0], "ABCUSDT")

