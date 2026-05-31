#!/usr/bin/env python3
"""
scripts/review_binance_liquidation_snapshot_event_study.py

Runs event density gating and produces the final Phase 1 review for the
Binance liquidation snapshot event study.

Reuses:
  - src/research/liquidation_shock_event_study/shock_detection.detect_shocks
  - src/research/liquidation_shock_event_study/shock_detection.deduplicate_events
  - src/research/liquidation_shock_event_study/response_map.build_response_map

Outputs:
  - reports/liquidation_shock_event_study/2026-05-31_binance_snapshot_event_study_summary.json
  - docs/reviews/2026-05-31-binance-liquidation-snapshot-event-study-review.md

Decision states (must be one of ALLOWED_DECISIONS):
  - binance_snapshot_data_failed            — no events produced from dataset
  - binance_snapshot_event_density_failed   — events < threshold
  - binance_snapshot_structure_not_confirmed — density ok but directional bias absent
  - binance_snapshot_structure_confirmed_for_q1_2024_only — density + bias present

Usage:
    PYTHONPATH=src uv run python scripts/review_binance_liquidation_snapshot_event_study.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg
from src.research.liquidation_shock_event_study.shock_detection import (
    deduplicate_events,
    detect_shocks,
)
from src.research.liquidation_shock_event_study.response_map import build_response_map

DATASET_JSONL = Path(cfg.BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR) / "binance_snapshot_dataset.jsonl"
CONTINUITY_REPORT = Path("reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json")
SUMMARY_JSON = Path("reports/liquidation_shock_event_study/2026-05-31_binance_snapshot_event_study_summary.json")
REVIEW_MD = Path("docs/reviews/2026-05-31-binance-liquidation-snapshot-event-study-review.md")

ALLOWED_DECISIONS = (
    "binance_snapshot_data_failed",
    "binance_snapshot_event_density_failed",
    "binance_snapshot_structure_not_confirmed",
    "binance_snapshot_structure_confirmed_for_q1_2024_only",
)

_MS_PER_MIN = 60_000


# ---------------------------------------------------------------------------
# Event density computation (pure — testable without I/O)
# ---------------------------------------------------------------------------


def compute_event_density(events: list[dict], months: list[str]) -> dict:
    """
    Compute event density views from a list of event dicts.

    Event dicts must have:
        symbol, dominant_liquidation_side, shock_bar_start_ms, month (optional)

    Returns dict with:
        total_events, events_per_month, events_by_symbol,
        events_by_side, events_by_symbol_month, events_by_symbol_side
    """
    total = len(events)

    events_per_month: dict[str, int] = {m: 0 for m in months}
    events_by_symbol: dict[str, int] = {}
    events_by_side: dict[str, int] = {}
    events_by_symbol_month: dict[str, dict[str, int]] = {}
    events_by_symbol_side: dict[str, dict[str, int]] = {}

    for ev in events:
        sym = ev.get("symbol", "UNKNOWN")
        side = ev.get("dominant_liquidation_side", "unknown")
        month = ev.get("month", "unknown")

        # Per-month
        if month in events_per_month:
            events_per_month[month] += 1
        else:
            events_per_month.setdefault(month, 0)
            events_per_month[month] += 1

        # By symbol
        events_by_symbol[sym] = events_by_symbol.get(sym, 0) + 1

        # By side
        events_by_side[side] = events_by_side.get(side, 0) + 1

        # By symbol-month
        events_by_symbol_month.setdefault(sym, {})
        events_by_symbol_month[sym][month] = events_by_symbol_month[sym].get(month, 0) + 1

        # By symbol-side
        events_by_symbol_side.setdefault(sym, {})
        events_by_symbol_side[sym][side] = events_by_symbol_side[sym].get(side, 0) + 1

    return {
        "total_events": total,
        "events_per_month": events_per_month,
        "events_by_symbol": events_by_symbol,
        "events_by_side": events_by_side,
        "events_by_symbol_month": events_by_symbol_month,
        "events_by_symbol_side": events_by_symbol_side,
    }


# ---------------------------------------------------------------------------
# Decision logic (pure)
# ---------------------------------------------------------------------------


def compute_review_decision(
    density: dict,
    months: list[str],
    min_total_events: int,
    min_events_per_month: int,
    directional_bias_results: dict | None = None,
) -> str:
    """
    Determine the final review decision state.

    Args:
        density:                 Output of compute_event_density.
        months:                  List of month strings being evaluated.
        min_total_events:        Minimum total events to pass density gate.
        min_events_per_month:    Minimum events per calendar month.
        directional_bias_results: Optional dict with per-horizon directional bias
                                  ratios. If None, defaults to structure_not_confirmed.

    Returns:
        One of ALLOWED_DECISIONS.
    """
    total = density.get("total_events", 0)

    # Gate 1: data availability
    if total == 0:
        return "binance_snapshot_data_failed"

    # Gate 2: total event density
    if total < min_total_events:
        return "binance_snapshot_event_density_failed"

    # Gate 3: per-month density
    events_per_month = density.get("events_per_month", {})
    for month in months:
        if events_per_month.get(month, 0) < min_events_per_month:
            return "binance_snapshot_event_density_failed"

    # Gate 4: directional bias (optional — requires response map results)
    if directional_bias_results is None:
        return "binance_snapshot_structure_not_confirmed"

    # Check if at least min_adjacent_horizons pass the directional bias threshold
    min_bias = cfg.LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS
    min_adjacent = cfg.LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT
    horizons = sorted(cfg.LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES)
    passing_horizons = sum(
        1
        for h in horizons
        if directional_bias_results.get(h, {}).get("directional_ratio", 0) >= min_bias
    )
    if passing_horizons >= min_adjacent:
        return "binance_snapshot_structure_confirmed_for_q1_2024_only"

    return "binance_snapshot_structure_not_confirmed"


# ---------------------------------------------------------------------------
# Response map aggregation helper
# ---------------------------------------------------------------------------


def _compute_response_stats(
    events: list,
    aligned_rows: list[dict],
) -> dict:
    """
    Build price_map and compute directional bias stats across all events.
    """
    # Build price_map: {open_time_ms: {open_price, close_price}}
    price_map: dict[int, dict] = {}
    for row in aligned_rows:
        price_map[row["bar_start_ms"]] = {
            "open_price": row.get("open_price", 0.0),
            "close_price": row.get("close_price", 0.0),
        }

    horizons = list(cfg.LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES)
    horizon_results: dict[int, list] = {h: [] for h in horizons}

    for ev in events:
        resp = build_response_map(ev, price_map)
        if resp is None:
            continue
        for h in horizons:
            horizon_results[h].append(resp["sign_directions"].get(h, 0))

    directional_bias: dict[int, dict] = {}
    for h in horizons:
        signs = horizon_results[h]
        if signs:
            positive = sum(1 for s in signs if s == 1)
            directional_bias[h] = {
                "n": len(signs),
                "positive": positive,
                "directional_ratio": positive / len(signs),
            }
        else:
            directional_bias[h] = {"n": 0, "positive": 0, "directional_ratio": 0.0}

    return directional_bias


# ---------------------------------------------------------------------------
# Markdown review writer
# ---------------------------------------------------------------------------


def _write_review_md(
    path: Path,
    decision: str,
    density: dict,
    directional_bias: dict,
    months: list[str],
    continuity_summary: dict,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Binance Liquidation Snapshot Event Study — Phase 1 Review",
        "",
        f"**Generated:** {ts}",
        "",
        "---",
        "",
        "## Data Source Semantics",
        "",
        "| Field | Value |",
        "| ----- | ----- |",
        "| `data_source` | `binance_vision_liquidation_snapshot` |",
        "| `liquidation_data_semantics` | `binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms` |",
        "| `not_complete_liquidation_tape` | `true` |",
        "| `notional_interpretation` | `snapshot_notional_proxy_not_total_market_liquidation` |",
        "| `sample_window` | `2024-01_to_2024-03` |",
        "| `known_window_bias` | `Q1_2024_trending_crypto_market` |",
        "| `generalization_allowed` | `false` |",
        "",
        "---",
        "",
        "## Purpose",
        "",
        "This is a **data-source replacement validation study**, not a live strategy promotion decision.",
        "It evaluates whether Binance Vision historical `liquidationSnapshot` data can replace",
        "Coinalyze 1m liquidation data for the purposes of the existing shock event-study pipeline,",
        "within the Q1 2024 sample window only.",
        "",
        "---",
        "",
        "## Continuity Gate",
        "",
    ]

    results = continuity_summary.get("results", {})
    lines.append("| Symbol | Month | Price Coverage | Max Gap (min) | Liq File Coverage | PASS/FAIL |")
    lines.append("| ------ | ----- | -------------- | ------------- | ----------------- | --------- |")
    for sym, months_data in results.items():
        for month, data in months_data.items():
            gate = "✅ PASS" if data.get("passes_continuity_gate") else "❌ FAIL"
            lines.append(
                f"| {sym} | {month} | {data.get('price_coverage_ratio', 0):.4f} | "
                f"{data.get('price_max_gap_minutes', '?')} | "
                f"{data.get('liquidation_file_coverage_ratio', 0):.4f} | {gate} |"
            )

    lines += [
        "",
        "---",
        "",
        "## Event Density Summary",
        "",
        f"**Total shock events (deduplicated):** {density['total_events']}",
        "",
        "### By Month",
        "",
        "| Month | Events |",
        "| ----- | ------ |",
    ]
    for month in months:
        count = density["events_per_month"].get(month, 0)
        lines.append(f"| {month} | {count} |")

    lines += [
        "",
        "### By Symbol",
        "",
        "| Symbol | Events |",
        "| ------ | ------ |",
    ]
    for sym, count in sorted(density["events_by_symbol"].items()):
        lines.append(f"| {sym} | {count} |")

    lines += [
        "",
        "### By Side",
        "",
        "| Side | Events |",
        "| ---- | ------ |",
    ]
    for side, count in sorted(density["events_by_side"].items()):
        lines.append(f"| {side} | {count} |")

    if directional_bias:
        lines += [
            "",
            "---",
            "",
            "## Directional Bias (Response Map)",
            "",
            "| Horizon (min) | N | Positive | Directional Ratio |",
            "| ------------- | - | -------- | ----------------- |",
        ]
        for h in sorted(directional_bias.keys()):
            d = directional_bias[h]
            lines.append(f"| {h} | {d['n']} | {d['positive']} | {d['directional_ratio']:.3f} |")

    lines += [
        "",
        "---",
        "",
        "## Final Decision",
        "",
        f"**`{decision}`**",
        "",
    ]

    if decision == "binance_snapshot_structure_confirmed_for_q1_2024_only":
        lines += [
            "> **Note:** This positive result is valid **only for Q1 2024**.",
            "> It cannot be generalized to other windows or market regimes.",
            "> This was a data-source replacement validation study.",
            "> The liquidation data is a snapshot proxy, not a complete liquidation tape.",
        ]
    else:
        lines += [
            f"> Decision: `{decision}`. See density and continuity tables above for root cause.",
        ]

    path.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _month_for_ms(ts_ms: int, months: list[str]) -> str:
    """Map a UTC ms timestamp to a YYYY-MM month string."""
    import datetime as dt
    d = dt.datetime.utcfromtimestamp(ts_ms / 1000)
    candidate = f"{d.year:04d}-{d.month:02d}"
    if candidate in months:
        return candidate
    return "unknown"


def main() -> None:
    months = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS)

    # Load continuity summary
    continuity_summary: dict = {}
    if CONTINUITY_REPORT.exists():
        with open(CONTINUITY_REPORT) as f:
            continuity_summary = json.load(f)
    else:
        logger.warning(f"Continuity report not found: {CONTINUITY_REPORT}")

    # Load dataset
    aligned_rows: list[dict] = []
    if DATASET_JSONL.exists():
        with open(DATASET_JSONL) as f:
            for line in f:
                line = line.strip()
                if line:
                    aligned_rows.append(json.loads(line))
    else:
        logger.error(f"Dataset JSONL not found: {DATASET_JSONL}")

    logger.info(f"Loaded {len(aligned_rows)} aligned rows from dataset")

    # Detect shocks using existing pipeline
    raw_events = detect_shocks(aligned_rows)
    dedup_events = deduplicate_events(raw_events)
    logger.info(f"Raw events: {len(raw_events)}, deduplicated: {len(dedup_events)}")

    # Annotate events with month label for density grouping
    event_dicts = []
    for ev in dedup_events:
        month = _month_for_ms(ev.shock_bar_start_ms, months)
        event_dicts.append(
            {
                "symbol": ev.symbol,
                "shock_bar_start_ms": ev.shock_bar_start_ms,
                "dominant_liquidation_side": ev.dominant_liquidation_side,
                "shock_notional_usdt": ev.shock_notional_usdt,
                "month": month,
            }
        )

    density = compute_event_density(event_dicts, months=months)

    # Compute response stats (directional bias)
    directional_bias: dict | None = None
    if aligned_rows and dedup_events:
        directional_bias = _compute_response_stats(dedup_events, aligned_rows)

    decision = compute_review_decision(
        density=density,
        months=months,
        min_total_events=cfg.BINANCE_LIQUIDATION_SNAPSHOT_MIN_TOTAL_EVENTS,
        min_events_per_month=cfg.BINANCE_LIQUIDATION_SNAPSHOT_MIN_EVENTS_PER_MONTH,
        directional_bias_results=directional_bias,
    )

    logger.info(f"Decision: {decision}")

    # Build full summary
    summary = {
        "data_source": "binance_vision_liquidation_snapshot",
        "liquidation_data_semantics": "binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms",
        "not_complete_liquidation_tape": True,
        "notional_interpretation": "snapshot_notional_proxy_not_total_market_liquidation",
        "sample_window": "2024-01_to_2024-03",
        "known_window_bias": "Q1_2024_trending_crypto_market",
        "generalization_allowed": False,
        "raw_events": len(raw_events),
        "deduplicated_events": len(dedup_events),
        "density": density,
        "directional_bias": directional_bias,
        "decision": decision,
    }

    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Summary written to: {SUMMARY_JSON}")

    _write_review_md(
        path=REVIEW_MD,
        decision=decision,
        density=density,
        directional_bias=directional_bias or {},
        months=months,
        continuity_summary=continuity_summary,
    )
    logger.info(f"Review written to: {REVIEW_MD}")

    # Write event density summary separately
    density_summary_path = Path(
        "reports/liquidation_shock_event_study/binance_snapshot_event_density_summary.json"
    )
    density_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(density_summary_path, "w") as f:
        json.dump({"density": density, "decision": decision}, f, indent=2)
    logger.info(f"Event density summary written to: {density_summary_path}")


if __name__ == "__main__":
    main()
