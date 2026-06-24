from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
    ExternalCatalystReplayCellDecision,
    ExternalCatalystReplayResult,
    ExternalCatalystReplayTopLevelDecision,
)


def test_replay_candidate_safety_defaults():
    candidate = ExternalCatalystReplayCandidate(
        symbol_event_id="s1",
        event_type="exchange_delisting_notice",
        signed_mode="delisting_avoid_long_or_signed_short_diagnostic",
        signed_direction=-1,
        symbol="ABCUSDT",
        event_time_ms=1710000000000,
        available_at_ms=1710000900000,
        entry_delay_hours=1,
        entry_candidate_time_ms=1710004500000,
        entry_bar_start_ms=1710004500000,
        entry_price=1.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    assert candidate.replay_allowed is True
    assert candidate.paper_trading_allowed is False
    assert candidate.live_trading_allowed is False
    assert candidate.short_execution_intent_allowed is False
    assert candidate.execution_engine_allowed is False


def test_replay_result_cost_fields():
    result = ExternalCatalystReplayResult(
        symbol_event_id="s1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="ABCUSDT",
        entry_delay_hours=1,
        forward_window_hours=4,
        cost_bps=50,
        entry_price=100.0,
        exit_price=101.0,
        long_gross_return_bps=100.0,
        signed_gross_return_bps=100.0,
        net_return_bps=50.0,
        forward_window_complete=True,
    )
    assert result.net_return_bps == 50.0


def test_decision_enum_values():
    assert ExternalCatalystReplayTopLevelDecision.COMPLETED.value == "stage1_5c_replay_completed"
    assert ExternalCatalystReplayTopLevelDecision.INVALID.value == "stage1_5c_replay_invalid"
    assert ExternalCatalystReplayCellDecision.PROMISING.value == "stage1_5c_cell_promising"
    assert ExternalCatalystReplayCellDecision.SPARSE.value == "stage1_5c_cell_sparse_inconclusive"
    assert ExternalCatalystReplayCellDecision.FAILED.value == "stage1_5c_cell_failed"
    assert ExternalCatalystReplayCellDecision.INVALID.value == "stage1_5c_cell_invalid"
