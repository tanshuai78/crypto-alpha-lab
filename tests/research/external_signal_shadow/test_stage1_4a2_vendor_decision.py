"""
tests/research/external_signal_shadow/test_stage1_4a2_vendor_decision.py
"""
from research.external_signal_shadow.stage1_4a2_vendor import (
    VendorLiquidationAudit,
    decide_vendor_audit,
)
from tests.research.external_signal_shadow.stage1_4a2_vendor_fixtures import (
    base_vendor_audit_payload,
)


def _audit(**updates):
    payload = base_vendor_audit_payload()
    payload.update(updates)
    return VendorLiquidationAudit.from_dict(payload)


def test_docs_only_can_only_be_degraded_even_when_fields_look_good() -> None:
    decision = decide_vendor_audit(
        _audit(evidence_level="official_api_docs", sample_file_available=False)
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "sample_not_available"
    assert decision.next_action == "request_sample_or_trial"


def test_no_sample_means_no_feasible() -> None:
    decision = decide_vendor_audit(_audit(sample_file_available=False))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "sample_not_available"


def test_license_unknown_blocks_feasible() -> None:
    decision = decide_vendor_audit(_audit(license_status="unknown"))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "license_unclear_or_restricted"


def test_missing_side_mapping_confidence_blocks_feasible() -> None:
    decision = decide_vendor_audit(_audit(side_mapping_confidence="unknown"))
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "side_mapping_uncertain"


def test_medium_cost_requires_user_decision() -> None:
    decision = decide_vendor_audit(
        _audit(
            cost_tier="medium",
            personal_investor_feasible_cost=False,
            estimated_cost_usd_per_month=120.0,
            explicit_user_cost_approval=False,
        )
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "user_cost_decision_required"


def test_paid_plan_required_needs_explicit_user_approval() -> None:
    decision = decide_vendor_audit(
        _audit(
            sample_access_type="paid_plan_required",
            payment_required_before_sample=True,
            explicit_user_approval_for_paid_sample=False,
        )
    )
    assert decision.decision == "vendor_liquidation_source_degraded"
    assert decision.primary_blocker == "user_cost_decision_required"


def test_valid_sample_can_be_feasible() -> None:
    decision = decide_vendor_audit(_audit())
    assert decision.decision == "vendor_liquidation_source_feasible"
    assert decision.primary_blocker is None
    assert decision.next_action == "write_stage1_4a3_vendor_sample_parser_plan"
