import configs.base as cfg
from research.cross_sectional_factor_lab.summary import (
    decide_stageA2_round1,
    decide_stageA2_variant,
)


def _variant(
    variant: str,
    drawdown_reduction: float,
    strategy_return: float,
    rebalance_count: int | None = None,
    ew_return: float = -20.0,
    btc_return: float = -10.0,
    eth_return: float = -15.0,
    cash_days_share: float = 0.40,
    month_share: float = 0.20,
) -> dict:
    return {
        "variant": variant,
        "regime_filter": {
            "cash_days_share": cash_days_share,
            "mostly_cash_strategy": cash_days_share > 0.60,
        },
        "performance": {
            "base_30bps_total_return_pct": strategy_return,
            "max_drawdown_vs_v1_reduction_pct": drawdown_reduction,
        },
        "benchmarks": {
            "btc_buy_and_hold_net_pct": btc_return,
            "eth_buy_and_hold_net_pct": eth_return,
            "universe_equal_weight_pct": ew_return,
        },
        "concentration": {
            "max_single_month_positive_pnl_share": month_share,
        },
        "rebalance_quality": {
            "rebalance_count": rebalance_count if rebalance_count is not None else cfg.FACTOR_LAB_STAGEA2_MIN_REBALANCE_COUNT,
            "insufficient_universe_count": 0,
            "insufficient_universe_ratio": 0.0,
            "median_selected_symbol_count": 10.0,
            "turnover_median": 0.5,
        },
    }


def test_stageA2_variant_data_insufficient_when_rebalance_count_below_gate():
    variant = _variant("btc_ma20_cash", 35.0, -5.0, rebalance_count=10)

    assert decide_stageA2_variant(variant) == "regime_filter_data_insufficient"


def test_stageA2_variant_promising_requires_all_gates():
    variant = _variant("btc_ma20_cash", 35.0, -5.0)

    assert decide_stageA2_variant(variant) == "regime_filter_promising"


def test_stageA2_variant_reduces_damage_but_no_alpha_when_benchmark_gate_fails():
    variant = _variant("btc_ma20_cash", 35.0, -30.0, ew_return=-40.0, btc_return=-10.0, eth_return=-15.0)

    assert decide_stageA2_variant(variant) == "regime_filter_reduces_damage_but_no_alpha"


def test_stageA2_variant_reduces_damage_but_no_alpha_when_mostly_cash():
    variant = _variant("alt_universe_20d_return_cash", 40.0, -5.0, cash_days_share=0.75)

    assert decide_stageA2_variant(variant) == "regime_filter_reduces_damage_but_no_alpha"


def test_stageA2_variant_failed_when_drawdown_reduction_is_too_small():
    variant = _variant("alt_universe_20d_return_cash", 20.0, -5.0)

    assert decide_stageA2_variant(variant) == "regime_filter_failed"


def test_stageA2_round1_cannot_unlock_round2_with_insufficient_rebalances():
    variants = [
        {**_variant("btc_ma20_cash", 35.0, -5.0, rebalance_count=10), "decision": "regime_filter_data_insufficient"},
    ]

    decision = decide_stageA2_round1(variants)

    assert decision["winner_variant"] is None
    assert decision["can_enter_stageA2_round2"] is False


def test_stageA2_round1_unlocks_round2_only_for_non_baseline_promising_variant():
    variants = [
        {**_variant("regime_none", 0.0, -84.0), "decision": "regime_filter_failed"},
        {**_variant("btc_ma20_cash", 35.0, -5.0), "decision": "regime_filter_promising"},
    ]

    decision = decide_stageA2_round1(variants)

    assert decision["winner_variant"] == "btc_ma20_cash"
    assert decision["can_enter_stageA2_round2"] is True
