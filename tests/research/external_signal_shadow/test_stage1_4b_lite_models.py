from dataclasses import FrozenInstanceError

import pytest

from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent


def test_candidate_event_dataclass_fields():
    event = CandidateEvent(
        candidate_name="oi_expansion_trend_confirmation",
        symbol="BTCUSDT",
        event_time_ms=1718000000000,
        event_available_at_ms=1718000900000,
        entry_bar_start_ms=1718001800000,
        signed_direction=1,
        metadata={"foo": "bar"}
    )

    assert event.candidate_name == "oi_expansion_trend_confirmation"
    assert event.symbol == "BTCUSDT"
    assert event.event_time_ms == 1718000000000
    assert event.event_available_at_ms == 1718000900000
    assert event.entry_bar_start_ms == 1718001800000
    assert event.signed_direction == 1
    assert event.metadata == {"foo": "bar"}


def test_candidate_event_is_frozen():
    event = CandidateEvent(
        candidate_name="oi_expansion_trend_confirmation",
        symbol="BTCUSDT",
        event_time_ms=1718000000000,
        event_available_at_ms=1718000900000,
        entry_bar_start_ms=1718001800000,
        signed_direction=1,
        metadata={}
    )
    with pytest.raises(FrozenInstanceError):
        event.symbol = "ETHUSDT" # type: ignore
