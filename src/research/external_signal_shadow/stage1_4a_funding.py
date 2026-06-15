"""
src/research/external_signal_shadow/stage1_4a_funding.py
"""

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_FUNDING_INTERVAL_MS,
    EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN,
)
from research.external_signal_shadow.stage1_4a_coverage import compute_time_coverage


def audit_funding_history_rows(rows: list[dict], expected_symbol: str) -> dict:
    """
    Audits the funding history rows for the expected symbol.
    """
    symbol_rows = [r for r in rows if r.get("symbol") == expected_symbol]
    record_count = len(symbol_rows)

    if record_count == 0:
        return {
            "funding_source": "binance_fapi_fundingRate",
            "funding_record_count": 0,
            "funding_history_days": 0.0,
            "funding_field_coverage_ratio": 0.0,
            "funding_settlement_coverage_ratio": 0.0,
            "missing_settlement_count": 0,
            "max_settlement_gap_ms": 0,
            "source_quality": "public_settled_funding_history",
            "usable": False,
        }

    # Field coverage: fields must be symbol, fundingRate, fundingTime
    valid_field_count = 0
    timestamps = []
    for r in symbol_rows:
        is_valid = (
            r.get("symbol") == expected_symbol
            and r.get("fundingRate") is not None
            and r.get("fundingTime") is not None
        )
        if is_valid:
            valid_field_count += 1
            timestamps.append(int(r["fundingTime"]))

    field_coverage_ratio = float(valid_field_count / record_count)

    # Compute time coverage using unique fundingTime timestamps
    coverage = compute_time_coverage(
        timestamps, EXTERNAL_SIGNAL_STAGE1_4_EXPECTED_FUNDING_INTERVAL_MS
    )

    funding_history_days = coverage["history_days"]
    settlement_coverage = coverage["time_coverage_ratio"]
    missing_settlement_count = max(
        0, coverage["expected_bucket_count"] - coverage["actual_unique_bucket_count"]
    )
    max_settlement_gap = coverage["max_gap_ms"]

    usable = (
        funding_history_days >= EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN
        and settlement_coverage >= EXTERNAL_SIGNAL_STAGE1_4_FUNDING_SETTLEMENT_COVERAGE_MIN_RATIO
        and field_coverage_ratio >= EXTERNAL_SIGNAL_STAGE1_4_FUNDING_FIELD_COVERAGE_MIN_RATIO
    )

    return {
        "funding_source": "binance_fapi_fundingRate",
        "funding_record_count": record_count,
        "funding_history_days": funding_history_days,
        "funding_field_coverage_ratio": field_coverage_ratio,
        "funding_settlement_coverage_ratio": settlement_coverage,
        "missing_settlement_count": missing_settlement_count,
        "max_settlement_gap_ms": max_settlement_gap,
        "source_quality": "public_settled_funding_history",
        "usable": usable,
    }


def funding_state_at_event(
    rows: list[dict], event_available_at_ms: int, funding_publish_lag_ms: int
) -> dict | None:
    """
    Finds the latest funding record available before the event time minus publish lag.
    """
    eligible_rows = []
    for r in rows:
        funding_time = r.get("fundingTime")
        if funding_time is not None:
            # Row is available at: funding_time + funding_publish_lag_ms
            # Must be <= event_available_at_ms
            if int(funding_time) + funding_publish_lag_ms <= event_available_at_ms:
                eligible_rows.append(r)

    if not eligible_rows:
        return None

    # Return the one with maximum fundingTime
    return max(eligible_rows, key=lambda x: int(x["fundingTime"]))
