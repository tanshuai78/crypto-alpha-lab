from __future__ import annotations

from research.cross_sectional_factor_lab.bias_contract import stage0_current_tradable_bias_contract


def test_current_tradable_universe_bias_contract_marks_survivorship_not_controlled() -> None:
    contract = stage0_current_tradable_bias_contract()
    assert contract["survivorship_bias_control"] == "not_controlled"
    assert contract["universe_scope"] == "current_tradable_universe_only"


def test_stage0_mvp_never_outputs_formal_bias_controlled() -> None:
    contract = stage0_current_tradable_bias_contract()
    assert contract["survivorship_bias_control"] != "controlled"
    assert contract["survivorship_bias_control"] != "partially_controlled"


def test_bias_contract_result_usage_is_hypothesis_screening_only() -> None:
    contract = stage0_current_tradable_bias_contract()
    assert contract["result_usage"] == "hypothesis_screening_only_not_final_evidence"
    assert contract["delisted_symbols_included"] is False
