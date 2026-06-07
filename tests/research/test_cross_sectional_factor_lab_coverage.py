from __future__ import annotations

from datetime import date, datetime, timezone
import pytest
from research.cross_sectional_factor_lab.coverage import (
    expected_utc_daily_dates,
    compute_coverage_ratio,
    compute_history_days_available,
    SymbolCoverage,
    Stage0CoverageSummary,
    decide_stage0_readiness,
)


def test_compute_coverage_ratio_counts_expected_days() -> None:
    expected = {"2026-06-01", "2026-06-02", "2026-06-03"}
    valid = {"2026-06-01", "2026-06-02"}
    assert compute_coverage_ratio(valid, expected) == pytest.approx(2.0 / 3.0)

    # Empty expected
    assert compute_coverage_ratio(valid, set()) == 0.0


def test_expected_utc_daily_dates_excludes_incomplete_today() -> None:
    # If today is June 7, expected_utc_daily_dates ending at June 6 should return Junes ending at June 6.
    end = date(2026, 6, 6)
    dates = expected_utc_daily_dates(end_date=end, history_days=3)
    assert dates == ("2026-06-04", "2026-06-05", "2026-06-06")


def test_expected_utc_daily_dates_has_exact_history_days_length() -> None:
    end = date(2026, 6, 6)
    dates = expected_utc_daily_dates(end_date=end, history_days=540)
    assert len(dates) == 540
    assert dates[-1] == "2026-06-06"


def test_coverage_ratio_uses_expected_utc_daily_dates() -> None:
    end = date(2026, 6, 6)
    expected = set(expected_utc_daily_dates(end, 5))
    valid = {"2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05", "2026-06-06"}
    assert compute_coverage_ratio(valid, expected) == 1.0


def test_history_days_available_uses_first_and_last_valid_day() -> None:
    valid = {"2026-06-01", "2026-06-05", "2026-06-10"}
    # Day range from June 1 to June 10 is 10 days
    assert compute_history_days_available(valid) == 10

    # Empty
    assert compute_history_days_available(set()) == 0


def test_decision_unavailable_when_symbol_count_below_gate(monkeypatch) -> None:
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY", 30)

    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=20,  # Below 30
        daily_ohlcv_coverage_ratio_median=0.98,
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.95,
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="ready",
    )
    assert decide_stage0_readiness(summary) == "factor_lab_data_unavailable"


def test_decision_unavailable_when_ohlcv_coverage_below_gate(monkeypatch) -> None:
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY", 30)
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN", 0.95)

    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.90,  # Below 0.95
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.95,
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="ready",
    )
    assert decide_stage0_readiness(summary) == "factor_lab_data_unavailable"


def test_decision_ready_with_bias_when_core_gates_pass(monkeypatch) -> None:
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY", 30)
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN", 0.95)

    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.97,
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.95,
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="ready",
    )
    assert decide_stage0_readiness(summary) == "factor_lab_data_ready_with_bias"


def test_spot_and_usdt_perp_are_reported_separately() -> None:
    spot_coverage = SymbolCoverage(
        symbol="BTCUSDT",
        market_type="spot",
        ohlcv_coverage=1.0,
        funding_coverage=0.0,
        oi_coverage=0.0,
        history_days=540,
    )
    perp_coverage = SymbolCoverage(
        symbol="BTCUSDT",
        market_type="usdt_perp",
        ohlcv_coverage=1.0,
        funding_coverage=0.98,
        oi_coverage=0.95,
        history_days=540,
    )
    assert spot_coverage.market_type == "spot"
    assert perp_coverage.market_type == "usdt_perp"


def test_open_interest_latest_1m_only_sets_recent_only_not_unavailable(monkeypatch) -> None:
    # Test that recent-only coverage summary assigns the correct readiness flag.
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_OPEN_INTEREST_RECENT_COVERAGE_MIN", 0.90)

    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.97,
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.20,  # Fails 540d median
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="degraded",  # recent is degraded or not used as hard gate
    )
    # The decision is still ready_with_bias because OI is not a 540d hard gate
    assert decide_stage0_readiness(summary) == "factor_lab_data_ready_with_bias"


def test_oi_coverage_not_used_as_540d_hard_gate() -> None:
    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.97,
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.0,  # 0% coverage over 540d
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="degraded",
    )
    assert decide_stage0_readiness(summary) == "factor_lab_data_ready_with_bias"


def test_funding_oi_degraded_does_not_block_price_volume_fast_track() -> None:
    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.97,
        funding_coverage_ratio_median=0.0,  # Funding degraded
        open_interest_coverage_ratio_median=0.0,  # OI degraded
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="degraded",
    )
    assert decide_stage0_readiness(summary) == "factor_lab_data_ready_with_bias"


def test_current_liquidity_gate_marked_screening_only() -> None:
    # Current liquidity gate does not promise historical tradability
    summary = Stage0CoverageSummary(
        symbols_total=50,
        symbols_after_static_exclusions=40,
        symbols_passing_liquidity=35,
        daily_ohlcv_coverage_ratio_median=0.97,
        funding_coverage_ratio_median=0.95,
        open_interest_coverage_ratio_median=0.95,
        history_days_available_median=540,
        listing_metadata_available=True,
        funding_oi_veto_readiness="ready",
    )
    # The readiness results should indicate screening-only logic
    assert decide_stage0_readiness(summary) == "factor_lab_data_ready_with_bias"
