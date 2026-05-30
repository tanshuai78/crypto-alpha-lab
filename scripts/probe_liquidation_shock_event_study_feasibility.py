from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from scripts.fetch_third_party_liquidation_history import (
    fetch_historical_liquidations,
    symbol_to_coinalyze_contract,
)

logger = logging.getLogger(__name__)

# Feasibility thresholds
LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO = 0.80
LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES = 180
LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS = 24.0

REQUIRED_REFERENCE_BARS = 1440  # 24 hours
EVALUATION_BARS = 1440          # 24 hours


def determine_decision(
    symbol_stats: dict[str, dict[str, Any]],
    requested_symbols: list[str],
    api_status: str,
) -> str:
    if api_status not in ("api_ok_non_empty_rows", "api_ok_empty_rows"):
        return "api_unavailable"

    qualified_count = sum(
        1 for sym in requested_symbols if symbol_stats.get(sym, {}).get("qualified", False)
    )

    if qualified_count == len(requested_symbols):
        return "proceed"
    elif qualified_count > 0:
        return "partial_symbol_support"
    else:
        return "insufficient_1m_data_depth"


def probe_feasibility(
    symbols: list[str],
    lookback_days: float = 2.5,
) -> dict[str, Any]:
    api_key = os.environ.get("COINALYZE_API_KEY", "")
    to_ts_sec = int(time.time())
    from_ts_sec = to_ts_sec - int(lookback_days * 86400)

    symbol_stats = {}
    api_status = "no_api_key" if not api_key else "api_ok_empty_rows"

    for idx, symbol in enumerate(symbols):
        # Strictly enforce rate limiting between symbols to prevent 429
        if idx > 0 and api_key:
            time.sleep(1.0)

        logger.info(f"Probing 1m feasibility for {symbol}...")
        payload, status = fetch_historical_liquidations(
            symbol=symbol,
            from_ts_sec=from_ts_sec,
            to_ts_sec=to_ts_sec,
            interval="1min",
            api_key=api_key,
        )

        if status == "api_ok_non_empty_rows":
            api_status = "api_ok_non_empty_rows"
        elif status != "api_ok_empty_rows" and api_status == "api_ok_empty_rows":
            api_status = status

        # Parse history
        history_rows = []
        if payload:
            for row in payload:
                if isinstance(row, dict) and isinstance(row.get("history"), list):
                    history_rows.extend(
                        item for item in row["history"] if isinstance(item, dict)
                    )
                elif isinstance(row, dict):
                    history_rows.append(row)

        unique_ts = sorted(list(set(int(item["t"]) for item in history_rows if "t" in item)))

        if not unique_ts:
            symbol_stats[symbol] = {
                "qualified": False,
                "rows_per_symbol": 0,
                "min_bar_start_ms": 0,
                "max_bar_start_ms": 0,
                "span_hours_per_symbol": 0.0,
                "expected_1m_bars": 0,
                "actual_1m_bars": 0,
                "coverage_ratio": 0.0,
                "max_gap_minutes": 0,
                "usable_eval_hours_after_lookback": 0.0,
            }
            continue

        min_ts = unique_ts[0]
        max_ts = unique_ts[-1]

        min_bar_start_ms = min_ts * 1000
        max_bar_start_ms = max_ts * 1000
        span_hours = (max_bar_start_ms - min_bar_start_ms) / 3600000.0
        expected_1m_bars = int((max_bar_start_ms - min_bar_start_ms) / 60000) + 1
        actual_1m_bars = expected_1m_bars  # Count based on padded timeline

        coverage_ratio = span_hours / (lookback_days * 24.0) if lookback_days > 0 else 0.0

        gaps = [(unique_ts[i] - unique_ts[i - 1]) // 60 for i in range(1, len(unique_ts))]
        max_gap = max(gaps) if gaps else 0

        usable_eval_hours = max(0.0, span_hours - 24.0)

        # Check qualification
        actual_padded_bars_ok = actual_1m_bars >= (REQUIRED_REFERENCE_BARS + EVALUATION_BARS)
        coverage_ratio_ok = coverage_ratio >= LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO
        max_gap_ok = max_gap <= LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES
        eval_hours_ok = usable_eval_hours >= LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS

        qualified = actual_padded_bars_ok and coverage_ratio_ok and max_gap_ok and eval_hours_ok

        symbol_stats[symbol] = {
            "qualified": qualified,
            "rows_per_symbol": len(history_rows),
            "min_bar_start_ms": min_bar_start_ms,
            "max_bar_start_ms": max_bar_start_ms,
            "span_hours_per_symbol": round(span_hours, 2),
            "expected_1m_bars": expected_1m_bars,
            "actual_1m_bars": actual_1m_bars,
            "coverage_ratio": round(coverage_ratio, 4),
            "max_gap_minutes": max_gap,
            "usable_eval_hours_after_lookback": round(usable_eval_hours, 2),
        }

    qualified_symbols = [sym for sym, stats in symbol_stats.items() if stats["qualified"]]
    decision = determine_decision(symbol_stats, symbols, api_status)
    supports_24h_lookback = len(qualified_symbols) > 0

    # Aggregate stats
    avg_coverage_ratio = 0.0
    max_gap_all = 0
    min_usable_eval_hours = 0.0
    if symbol_stats:
        avg_coverage_ratio = sum(s["coverage_ratio"] for s in symbol_stats.values()) / len(symbol_stats)
        max_gap_all = max(s["max_gap_minutes"] for s in symbol_stats.values())
        min_usable_eval_hours = min(s["usable_eval_hours_after_lookback"] for s in symbol_stats.values())

    return {
        "vendor": "coinalyze",
        "interval": "1min",
        "symbols_requested": symbols,
        "supports_24h_lookback": supports_24h_lookback,
        "decision": decision,
        "coverage_ratio": round(avg_coverage_ratio, 4),
        "max_gap_minutes": max_gap_all,
        "usable_eval_hours_after_lookback": round(min_usable_eval_hours, 2),
        "qualified_symbols": qualified_symbols,
        "symbol_stats": symbol_stats,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
    
    # Run the probe with 2.5 days lookback to check compatibility
    res = probe_feasibility(symbols, lookback_days=2.5)
    
    output_path = "reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_feasibility.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(res, f, indent=2)
        
    logger.info(f"Feasibility report written to {output_path}")
    logger.info(f"Decision: {res['decision']}, Qualified Symbols: {res['qualified_symbols']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
