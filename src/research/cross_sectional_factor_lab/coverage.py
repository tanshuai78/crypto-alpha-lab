from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

try:
    from configs.base import (
        FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN,
        FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED,
        FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY,
    )
except ImportError:
    # Fallback to defaults in case config fails to import under isolated test environments
    FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY = 30
    FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN = 0.95
    FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED = 540


@dataclass
class SymbolCoverage:
    symbol: str
    market_type: str  # "spot" or "usdt_perp"
    ohlcv_coverage: float
    funding_coverage: float
    oi_coverage: float
    history_days: int


@dataclass
class Stage0CoverageSummary:
    symbols_total: int
    symbols_after_static_exclusions: int
    symbols_passing_liquidity: int
    daily_ohlcv_coverage_ratio_median: float
    funding_coverage_ratio_median: float
    open_interest_coverage_ratio_median: float
    history_days_available_median: float
    listing_metadata_available: bool
    funding_oi_veto_readiness: str  # "ready" | "degraded" | "unavailable"


def expected_utc_daily_dates(end_date: date, history_days: int) -> tuple[str, ...]:
    """Calculate the tuple of expected daily UTC dates in YYYY-MM-DD format ending on end_date."""
    dates = []
    for i in range(history_days - 1, -1, -1):
        dt = end_date - timedelta(days=i)
        dates.append(dt.strftime("%Y-%m-%d"))
    return tuple(dates)


def compute_coverage_ratio(valid_days: set[str], expected_days: set[str]) -> float:
    """Calculate ratio of valid days present in expected days."""
    if not expected_days:
        return 0.0
    matching = valid_days.intersection(expected_days)
    return len(matching) / len(expected_days)


def compute_history_days_available(valid_days: set[str]) -> int:
    """Calculate the day range from earliest to latest valid day (inclusive)."""
    if not valid_days:
        return 0
    parsed = sorted([date.fromisoformat(d) for d in valid_days])
    return (parsed[-1] - parsed[0]).days + 1


def decide_stage0_readiness(summary: Stage0CoverageSummary) -> str:
    """Determine if data is ready for Stage A with bias or unavailable."""
    # Check if we meet the liquidity symbol count threshold
    if summary.symbols_passing_liquidity < FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY:
        return "factor_lab_data_unavailable"

    # Check if median daily OHLCV coverage is sufficient
    if summary.daily_ohlcv_coverage_ratio_median < FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN:
        return "factor_lab_data_unavailable"

    # Check if history days available is sufficient
    if summary.history_days_available_median < FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED:
        return "factor_lab_data_unavailable"

    return "factor_lab_data_ready_with_bias"
