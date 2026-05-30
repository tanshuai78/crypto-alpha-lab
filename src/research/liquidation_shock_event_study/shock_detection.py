from __future__ import annotations

from typing import Any

from configs.base import (
    LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS,
)
from src.research.liquidation_shock_event_study.event_contract import (
    LiquidationShockEvent,
    classify_liquidation_shock_event,
)


def detect_shocks(aligned_rows: list[dict[str, Any]]) -> list[LiquidationShockEvent]:
    # Group rows by symbol
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for r in aligned_rows:
        by_symbol.setdefault(r["symbol"], []).append(r)

    events: list[LiquidationShockEvent] = []
    lookback = LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS  # 1440

    for sym, sym_rows in by_symbol.items():
        # Sort by timestamp ascending
        sym_rows.sort(key=lambda x: x["bar_start_ms"])

        long_liq_history = []
        short_liq_history = []

        for i, row in enumerate(sym_rows):
            long_liq = row["long_liquidation_notional_1m_usdt"]
            short_liq = row["short_liquidation_notional_1m_usdt"]

            if i >= lookback:
                # Exclude current bar from reference window
                ref_long = long_liq_history[-lookback:]
                ref_short = short_liq_history[-lookback:]

                # Compute percentile rank (fraction of ref window strictly less than current value)
                score_long = sum(1 for x in ref_long if x < long_liq) / lookback
                score_short = sum(1 for x in ref_short if x < short_liq) / lookback

                # Determine dominant side
                dominant_side = "long" if long_liq >= short_liq else "short"
                dominant_score = score_long if dominant_side == "long" else score_short

                event = classify_liquidation_shock_event(
                    symbol=sym,
                    bar_start_ms=row["bar_start_ms"],
                    long_liq=long_liq,
                    short_liq=short_liq,
                    relative_score=dominant_score,
                    reference_count=lookback,
                )

                if event:
                    events.append(event)

            long_liq_history.append(long_liq)
            short_liq_history.append(short_liq)

    # Sort events chronologically by symbol and timestamp
    events.sort(key=lambda e: (e.symbol, e.shock_bar_start_ms))
    return events


def deduplicate_events(events: list[LiquidationShockEvent]) -> list[LiquidationShockEvent]:
    # Group by (symbol, liquidated_position_side, dedup_bucket_start_ms)
    groups: dict[tuple[str, str, int], list[LiquidationShockEvent]] = {}
    for ev in events:
        key = (ev.symbol, ev.liquidated_position_side, ev.dedup_bucket_start_ms)
        groups.setdefault(key, []).append(ev)

    survivors: list[LiquidationShockEvent] = []
    for key, group_events in groups.items():
        # Keep the event with the maximum shock_notional_usdt.
        # Order-invariant tie breaker: earliest shock_bar_start_ms.
        best_ev = max(
            group_events,
            key=lambda e: (e.shock_notional_usdt, -e.shock_bar_start_ms),
        )
        survivors.append(best_ev)

    # Sort survivors by symbol and shock_bar_start_ms
    survivors.sort(key=lambda e: (e.symbol, e.shock_bar_start_ms))
    return survivors
