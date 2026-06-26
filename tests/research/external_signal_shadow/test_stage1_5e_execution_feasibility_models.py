from src.research.external_signal_shadow.stage1_5e_execution_feasibility_models import (
    ExecutionFeasibilityCandidate,
    ExecutionFeasibilityDecision,
)


def test_decision_enum_values_are_fixed():
    assert ExecutionFeasibilityDecision.READY_FOR_LIVE_DEPTH_OBSERVER.value == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    assert ExecutionFeasibilityDecision.PROXY_FAILED.value == "stage1_5e_execution_feasibility_proxy_failed"
    assert ExecutionFeasibilityDecision.INCONCLUSIVE_DEPTH_MISSING.value == "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    assert ExecutionFeasibilityDecision.INCONCLUSIVE_PENDING_STAGE1_5D.value == "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"
    assert ExecutionFeasibilityDecision.INVALID.value == "stage1_5e_execution_feasibility_invalid"


def test_candidate_defaults_do_not_allow_execution():
    row = ExecutionFeasibilityCandidate(
        symbol="ABCUSDT",
        symbol_event_id="evt-1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        entry_delay_hours=12,
        filter_group="G1_source_event_after_first_hour_delay",
        entry_time_ms=1_700_000_000_000,
    ).to_dict()

    assert row["execution_engine_allowed"] is False
    assert row["paper_trading_allowed"] is False
    assert row["live_trading_allowed"] is False
    assert row["alpha_interpretation_allowed"] is False
    assert row["execution_feasibility_proven"] is False
