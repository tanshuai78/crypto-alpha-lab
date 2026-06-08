from __future__ import annotations

import configs.base as cfg


def test_factor_lab_stageA_core_config_exists() -> None:
    assert cfg.FACTOR_LAB_STAGEA_HISTORY_DAYS == 540
    assert cfg.FACTOR_LAB_STAGEA_MOMENTUM_LOOKBACK_DAYS == 30
    assert cfg.FACTOR_LAB_STAGEA_SKIP_RECENT_DAYS == 1
    assert cfg.FACTOR_LAB_STAGEA_REBALANCE_WEEKDAY_UTC == 0
    assert cfg.FACTOR_LAB_STAGEA_PRIMARY_TOP_N == 10
    assert cfg.FACTOR_LAB_STAGEA_DIAGNOSTIC_TOP_N == 5


def test_factor_lab_stageA_cost_config_matches_design() -> None:
    assert cfg.FACTOR_LAB_STAGEA_COST_SCENARIOS_ROUND_TRIP_BPS == (30.0, 50.0, 80.0)
    assert cfg.FACTOR_LAB_STAGEA_OPTIMISTIC_DIAGNOSTIC_PER_LEG_BPS == 10.0


def test_factor_lab_stageA_decision_gates_exist() -> None:
    assert cfg.FACTOR_LAB_STAGEA_MIN_REBALANCE_COUNT == 50
    assert cfg.FACTOR_LAB_STAGEA_MAX_DRAWDOWN_VS_EW_MULTIPLIER == 1.25
    assert cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_SYMBOL_PNL_CONTRIBUTION_SHARE == 0.35
    assert cfg.FACTOR_LAB_STAGEA_MAX_SINGLE_MONTH_PNL_CONTRIBUTION_SHARE == 0.30
    assert cfg.FACTOR_LAB_STAGEA_MAX_INSUFFICIENT_UNIVERSE_RATIO == 0.10
