from __future__ import annotations

from typing import Any


def normalize_interval(interval: str) -> str:
    if interval in ("1m", "1min"):
        return "1min"
    return interval


def normalize_coinalyze_1m_payload(
    payload: list[dict[str, Any]] | None,
    symbol: str,
) -> list[dict[str, Any]]:
    if not payload:
        return []

    # Aggregate duplicate symbol + bar_start_ms rows by sum.
    aggregated: dict[int, dict[str, float]] = {}

    history_rows: list[dict[str, Any]] = []
    for row in payload:
        if isinstance(row, dict) and isinstance(row.get("history"), list):
            history_rows.extend(item for item in row["history"] if isinstance(item, dict))
        elif isinstance(row, dict):
            history_rows.append(row)

    for row in history_rows:
        t_value = row.get("t")
        if t_value in (None, ""):
            continue

        t_sec = int(t_value)
        bar_start_ms = t_sec * 1000

        long_liq = float(row.get("l") or 0.0)
        short_liq = float(row.get("s") or 0.0)

        if bar_start_ms not in aggregated:
            aggregated[bar_start_ms] = {
                "long": 0.0,
                "short": 0.0,
            }
        aggregated[bar_start_ms]["long"] += long_liq
        aggregated[bar_start_ms]["short"] += short_liq

    normalized: list[dict[str, Any]] = []
    for ms, vals in aggregated.items():
        long_liq = vals["long"]
        short_liq = vals["short"]
        total_liq = long_liq + short_liq

        normalized.append(
            {
                "symbol": symbol,
                "bar_start_ms": ms,
                "long_liquidation_notional_1m_usdt": long_liq,
                "short_liquidation_notional_1m_usdt": short_liq,
                "total_liquidation_notional_1m_usdt": total_liq,
                "source_namespace": "liquidation_shock_event_study",
            }
        )

    return normalized
