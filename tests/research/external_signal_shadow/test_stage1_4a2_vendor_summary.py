"""
tests/research/external_signal_shadow/test_stage1_4a2_vendor_summary.py
"""
from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    build_vendor_feasibility_summary,
)
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import (
    base_vendor_audit_payload,
)


def _audit(vendor: str, **updates):
    payload = base_vendor_audit_payload()
    payload["vendor"] = vendor
    payload.update(updates)
    return VendorLiquidationAudit.from_dict(payload)


def test_summary_outputs_recommended_vendor_order_and_safety_flags() -> None:
    summary = build_vendor_feasibility_summary([
        _audit("tardis_dev"),
        _audit("coinglass", evidence_level="official_api_docs", sample_file_available=False),
    ])
    assert summary["recommended_vendor_order"][:2] == ["tardis_dev", "coinglass"]
    assert summary["best_vendor"] == "tardis_dev"
    assert summary["purchase_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["stage1_4b_candidate_replay_allowed"] is False


def test_summary_degraded_when_no_vendor_feasible() -> None:
    summary = build_vendor_feasibility_summary([
        _audit("coinglass", evidence_level="official_api_docs", sample_file_available=False),
    ])
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["feasible_vendor_count"] == 0
    assert summary["primary_blocker"] == "no_feasible_vendor_sample"


def test_summary_next_action_is_precise_for_paid_only_promising_vendor() -> None:
    summary = build_vendor_feasibility_summary([
        _audit(
            "tardis_dev",
            sample_access_type="paid_plan_required",
            payment_required_before_sample=True,
            explicit_user_approval_for_paid_sample=False,
            cost_tier="medium",
            personal_investor_feasible_cost=False,
        ),
    ])
    assert summary["decision"] == "vendor_liquidation_source_degraded"
    assert summary["next_action"] == "user_cost_decision_required"
