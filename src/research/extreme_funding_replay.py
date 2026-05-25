from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class SettledFundingRow:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    annualized_pct: float
    mark_price: float | None = None
    coverage_quality: str = "funding_only_insufficient_for_basis"


def load_settled_funding_rows(path: str | Path) -> list[SettledFundingRow]:
    rows: list[SettledFundingRow] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            rows.append(
                SettledFundingRow(
                    symbol=str(raw["symbol"]),
                    funding_time_ms=int(raw["funding_time_ms"]),
                    funding_rate=float(raw["funding_rate"]),
                    annualized_pct=float(raw["annualized_pct"]),
                    mark_price=float(raw["mark_price"]) if raw.get("mark_price") is not None else None,
                )
            )
    return rows


def _as_dict(row: SettledFundingRow | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, SettledFundingRow):
        return {
            "symbol": row.symbol,
            "funding_time_ms": row.funding_time_ms,
            "funding_rate": row.funding_rate,
            "annualized_pct": row.annualized_pct,
            "mark_price": row.mark_price,
            "coverage_quality": row.coverage_quality,
        }
    return row


def detect_extreme_funding_segments(
    rows: Iterable[SettledFundingRow | dict[str, Any]],
    *,
    threshold_pct: float,
) -> list[dict[str, Any]]:
    sorted_rows = sorted(
        (_as_dict(row) for row in rows),
        key=lambda item: (str(item["symbol"]), int(item["funding_time_ms"])),
    )
    segments: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_symbol: str | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        annualized_values = [float(item["annualized_pct"]) for item in current]
        funding_income_bps = sum(float(item["funding_rate"]) * 10_000.0 for item in current)
        segments.append(
            {
                "symbol": str(current[0]["symbol"]),
                "start_ms": int(current[0]["funding_time_ms"]),
                "end_ms": int(current[-1]["funding_time_ms"]),
                "row_count": len(current),
                "max_annualized_pct": max(annualized_values),
                "median_annualized_pct": sorted(annualized_values)[len(annualized_values) // 2],
                "funding_income_bps": funding_income_bps,
                "settlement_persistence": 1.0,
                "coverage_quality": "funding_only_insufficient_for_basis",
            }
        )
        current = []

    for row in sorted_rows:
        symbol = str(row["symbol"])
        if symbol != current_symbol:
            flush()
            current_symbol = symbol
        if float(row["annualized_pct"]) >= threshold_pct:
            current.append(row)
        else:
            flush()
    flush()
    return segments
