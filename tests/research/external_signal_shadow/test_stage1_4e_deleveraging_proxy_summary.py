from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_models import (
    DECISION_FAILED,
    DECISION_INCONCLUSIVE,
    DECISION_SURVIVES,
    SECONDARY_NONE,
    SECONDARY_PROMISING_SPARSE,
)
from src.research.external_signal_shadow.stage1_4e_deleveraging_proxy_summary import (
    decide_stage1_4e_summary,
)


def test_sparse_positive_result_is_inconclusive_not_pass():
    # 50 events, 15 days (meets promising sparse count/days >= 30/10 but < 100/20)
    # Good performance: candidate median = 10 bps, random baseline = 1 bps, price baseline = -2 bps
    decision, secondary = decide_stage1_4e_summary(
        event_count=50,
        event_days=15,
        symbols_with_events=3,
        candidate_median_bps=10.0,
        random_baseline_median_bps=1.0,
        price_baseline_median_bps=-2.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=-10.0,
        top5_positive_gross_profit_share=0.20,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True,
    )
    assert decision == DECISION_INCONCLUSIVE
    assert secondary == SECONDARY_PROMISING_SPARSE

def test_failed_result_does_not_invalidate_real_liquidation_or_external_catalyst():
    # Weak performance: candidate median = -5 bps, baseline = 1 bps
    decision, secondary = decide_stage1_4e_summary(
        event_count=120,
        event_days=25,
        symbols_with_events=3,
        candidate_median_bps=-5.0,
        random_baseline_median_bps=1.0,
        price_baseline_median_bps=2.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=-10.0,
        top5_positive_gross_profit_share=0.20,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True,
    )
    assert decision == DECISION_FAILED
    assert secondary == SECONDARY_NONE

def test_unsupported_data_is_inconclusive():
    decision, secondary = decide_stage1_4e_summary(
        event_count=0,
        event_days=0,
        symbols_with_events=0,
        candidate_median_bps=0.0,
        random_baseline_median_bps=0.0,
        price_baseline_median_bps=0.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=0.0,
        top5_positive_gross_profit_share=0.0,
        max_single_day_event_share=0.0,
        max_single_symbol_event_share=0.0,
        data_supported=False,
    )
    assert decision == DECISION_INCONCLUSIVE
    assert secondary == SECONDARY_NONE

def test_passes_when_all_gates_met():
    # 120 events, 25 days, good return vs baseline
    decision, secondary = decide_stage1_4e_summary(
        event_count=120,
        event_days=25,
        symbols_with_events=3,
        candidate_median_bps=15.0,
        random_baseline_median_bps=2.0,
        price_baseline_median_bps=0.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=-10.0,
        top5_positive_gross_profit_share=0.20,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True
    )
    assert decision == DECISION_SURVIVES
    assert secondary == SECONDARY_NONE


def test_candidate_does_not_survive_when_symbol_coverage_is_too_thin():
    decision, secondary = decide_stage1_4e_summary(
        event_count=120,
        event_days=25,
        symbols_with_events=1,
        candidate_median_bps=15.0,
        random_baseline_median_bps=2.0,
        price_baseline_median_bps=0.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=-10.0,
        top5_positive_gross_profit_share=0.20,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True
    )
    assert decision == DECISION_INCONCLUSIVE
    assert secondary == SECONDARY_NONE


def test_candidate_does_not_survive_when_pnl_or_event_concentration_is_too_high():
    decision, secondary = decide_stage1_4e_summary(
        event_count=120,
        event_days=25,
        symbols_with_events=3,
        candidate_median_bps=15.0,
        random_baseline_median_bps=2.0,
        price_baseline_median_bps=0.0,
        candidate_left_tail_bps=0.0,
        random_baseline_left_tail_bps=-10.0,
        top5_positive_gross_profit_share=0.80,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True
    )
    assert decision == DECISION_INCONCLUSIVE
    assert secondary == SECONDARY_NONE


def test_candidate_does_not_survive_when_left_tail_is_worse_than_random():
    decision, secondary = decide_stage1_4e_summary(
        event_count=120,
        event_days=25,
        symbols_with_events=3,
        candidate_median_bps=15.0,
        random_baseline_median_bps=2.0,
        price_baseline_median_bps=0.0,
        candidate_left_tail_bps=-80.0,
        random_baseline_left_tail_bps=-40.0,
        top5_positive_gross_profit_share=0.20,
        max_single_day_event_share=0.20,
        max_single_symbol_event_share=0.50,
        data_supported=True
    )
    assert decision == DECISION_FAILED
    assert secondary == SECONDARY_NONE
