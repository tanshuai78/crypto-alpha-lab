from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_candidates import (
    allowed_filter_groups,
    apply_event_cooldown,
    build_replay_candidates,
    event_direction_modes,
)


def test_event_direction_modes_are_frozen():
    assert event_direction_modes("exchange_delisting_notice") == [
        ("delisting_avoid_long_or_signed_short_diagnostic", -1)
    ]
    assert event_direction_modes("futures_contract_launch") == [
        ("futures_launch_long_attention_diagnostic", 1),
        ("futures_launch_short_access_diagnostic", -1),
    ]


def test_filter_group_semantics_make_first_hour_delay_mandatory():
    # There is no no-delay Group 0 in Stage 1.5C v1.
    assert "G1_source_event_after_first_hour_delay" in allowed_filter_groups()
    assert "G0_event_only" not in allowed_filter_groups()


def test_event_cooldown_keeps_earliest_same_symbol_type_mode():
    events = [
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "m", "event_time_ms": 0},
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "m", "event_time_ms": 1_000},
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "other", "event_time_ms": 1_000},
    ]
    kept = apply_event_cooldown(events, cooldown_hours=24)
    assert len(kept) == 2
    assert kept[0]["event_time_ms"] == 0


def test_build_replay_candidates_expands_futures_launch_two_modes():
    event = {
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 0,
        "available_at_ms": 0,
    }
    coverage = {
        "price_coverage_gate_passed": True,
        "candidate_allowed_for_close_price_replay": True,
        "entry_candidate_time_ms": 3_600_000,
        "entry_bar_start_ms": 3_600_000,
        "entry_price": 100.0,
        "price_history_coverage_verified": True,
        "market_pair_existence_verified": True,
        "liquidity_proxy_verified": False,
        "close_price_replay_only": True,
        "execution_feasibility_unknown": True,
    }
    candidates = build_replay_candidates([event], {("s1", 1): coverage}, entry_delay_hours=1)
    assert {c.signed_direction for c in candidates} == {1, -1}
    assert all(c.paper_trading_allowed is False for c in candidates)


def test_build_replay_candidates_skips_failed_price_coverage():
    event = {
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 0,
        "available_at_ms": 0,
    }
    coverage = {
        "price_coverage_gate_passed": False,
        "candidate_allowed_for_close_price_replay": False,
        "coverage_reject_reason": "missing_price_history",
    }
    candidates = build_replay_candidates([event], {("s1", 1): coverage}, entry_delay_hours=1)
    assert candidates == []
