#!/usr/bin/env python3
"""
scripts/screen_route_a_complete_quarters.py

Route A pre-screening for complete-quarter BTC/ETH/SOL proxy validation.

This script is intentionally narrower than the full event-study pipeline:
  1. Probe Binance Vision availability for one natural quarter
  2. Download quarter files into quarter-scoped directories
  3. Audit symbol-month continuity
  4. Build a lightweight shock-density summary
  5. Decide whether any candidate quarter is complete enough to justify
     a fresh Route A proxy validation branch

Outputs:
  - reports/liquidation_shock_event_study/route_a_quarter_screening_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg

sys.path.insert(0, str(Path(__file__).parent))
import audit_binance_liquidation_snapshot_continuity as continuity_mod
import build_binance_liquidation_snapshot_event_dataset as dataset_mod
import fetch_binance_liquidation_snapshot_history as fetch_mod
import probe_binance_liquidation_snapshot_manifest as manifest_mod
import review_binance_liquidation_snapshot_event_study as review_mod

from src.research.liquidation_shock_event_study.shock_detection import deduplicate_events

REPORT_PATH = Path("reports/liquidation_shock_event_study/route_a_quarter_screening_summary.json")

CANDIDATE_QUARTERS = ("2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4", "2024-Q1")
REQUIRED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def quarter_to_months(quarter: str) -> list[str]:
    year = int(quarter[:4])
    q = quarter[-2:]
    if q == "Q1":
        start = 1
    elif q == "Q2":
        start = 4
    elif q == "Q3":
        start = 7
    elif q == "Q4":
        start = 10
    else:
        raise ValueError(f"Unsupported quarter: {quarter}")
    return [f"{year}-{month:02d}" for month in range(start, start + 3)]


def evaluate_quarter(
    quarter: str,
    required_symbols: list[str],
    months: list[str],
    continuity_results: dict,
    density: dict,
    min_total_events: int,
    min_events_per_month: int,
    min_events_per_symbol: int,
) -> dict:
    available_symbol_months = 0
    price_continuity_pass_symbol_months = 0
    liq_file_pass_symbol_months = 0
    continuity_pass_symbol_months = 0
    fail_reasons: list[str] = []

    for symbol in required_symbols:
        for month in months:
            month_data = continuity_results.get(symbol, {}).get(month, {})
            if month_data.get("price_rows", 0) > 0 and month_data.get("liquidation_files_found", 0) > 0:
                available_symbol_months += 1
            if (
                month_data.get("price_coverage_ratio", 0.0) >= cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO
                and month_data.get("price_max_gap_minutes", 9999) <= cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES
            ):
                price_continuity_pass_symbol_months += 1
            if month_data.get("liquidation_file_coverage_ratio", 0.0) >= 1.0:
                liq_file_pass_symbol_months += 1
            if month_data.get("passes_continuity_gate", False):
                continuity_pass_symbol_months += 1

    quarter_universe_integrity_ok = continuity_pass_symbol_months == len(required_symbols) * len(months)
    if not quarter_universe_integrity_ok:
        fail_reasons.append("universe_integrity_failed")

    total_events = density.get("total_events", 0)
    events_per_month = density.get("events_per_month", {})
    events_by_symbol = density.get("events_by_symbol", {})

    event_density_ok = True
    if total_events < min_total_events:
        event_density_ok = False
        fail_reasons.append("total_event_density_failed")

    if any(events_per_month.get(month, 0) < min_events_per_month for month in months):
        event_density_ok = False
        fail_reasons.append("monthly_event_density_failed")

    if any(events_by_symbol.get(symbol, 0) < min_events_per_symbol for symbol in required_symbols):
        event_density_ok = False
        fail_reasons.append("symbol_event_density_failed")

    passes_screening = quarter_universe_integrity_ok and event_density_ok

    return {
        "quarter": quarter,
        "months": months,
        "available_symbol_months": available_symbol_months,
        "price_continuity_pass_symbol_months": price_continuity_pass_symbol_months,
        "liq_file_pass_symbol_months": liq_file_pass_symbol_months,
        "continuity_pass_symbol_months": continuity_pass_symbol_months,
        "quarter_universe_integrity_ok": quarter_universe_integrity_ok,
        "total_events": total_events,
        "events_per_month": events_per_month,
        "events_by_symbol": events_by_symbol,
        "event_density_ok": event_density_ok,
        "passes_screening": passes_screening,
        "fail_reasons": fail_reasons,
    }


def compute_screening_decision(quarter_results: list[dict]) -> dict:
    passing = [q for q in quarter_results if q.get("passes_screening")]
    if not passing:
        return {
            "decision": "route_a_quarter_not_found",
            "selected_quarter": None,
        }

    passing.sort(
        key=lambda q: (
            q.get("available_symbol_months", 0),
            q.get("total_events", 0),
        )
    )
    selected = passing[-1]
    return {
        "decision": "route_a_quarter_found",
        "selected_quarter": selected["quarter"],
    }


def _load_kline_rows_from_dir(kline_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not kline_dir.exists():
        return rows
    for csv_file in sorted(kline_dir.glob("*.csv")):
        rows.extend(continuity_mod._load_kline_csv(csv_file))
    return rows


def _load_liq_rows_from_dir(liq_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not liq_dir.exists():
        return rows
    for csv_file in sorted(liq_dir.glob("*.csv")):
        rows.extend(dataset_mod._load_liquidation_csv(csv_file))
    return rows


def _daily_files_found_for_month(liq_dir: Path, month: str) -> list[str]:
    found: set[str] = set()
    if not liq_dir.exists():
        return []
    prefix = f"{month}-"
    for csv_file in liq_dir.glob("*.csv"):
        stem = csv_file.stem
        parts = stem.split("-")
        if len(parts) >= 3:
            date_part = "-".join(parts[-3:])
            if date_part.startswith(prefix):
                found.add(date_part)
    return sorted(found)


def build_quarter_continuity_summary(extracted_dir: Path, symbols: list[str], months: list[str]) -> dict:
    results: dict = {}
    for symbol in symbols:
        results[symbol] = {}
        for month in months:
            kline_dir = extracted_dir / "klines" / symbol / month
            liq_dir = extracted_dir / "liquidationSnapshot" / symbol / month
            price_rows = _load_kline_rows_from_dir(kline_dir)
            liq_rows = _load_liq_rows_from_dir(liq_dir)
            files_found = _daily_files_found_for_month(liq_dir, month)
            results[symbol][month] = continuity_mod.audit_symbol_month(
                symbol=symbol,
                month=month,
                price_rows=price_rows,
                liquidation_files_found=files_found,
                liquidation_rows=liq_rows,
            )
    return {
        "results": results,
        "all_symbol_months_pass": all(
            results[sym][month].get("passes_continuity_gate", False)
            for sym in symbols
            for month in months
        ),
    }


def build_quarter_density_summary(extracted_dir: Path, continuity_summary: dict, symbols: list[str], months: list[str]) -> dict:
    aligned_rows: list[dict] = []
    for symbol in symbols:
        passed_months = [
            month
            for month in months
            if continuity_summary.get("results", {}).get(symbol, {}).get(month, {}).get("passes_continuity_gate", False)
        ]
        month_data: dict[str, dict] = {}
        for month in passed_months:
            kline_dir = extracted_dir / "klines" / symbol / month
            liq_dir = extracted_dir / "liquidationSnapshot" / symbol / month
            month_data[month] = {
                "price_rows": _load_kline_rows_from_dir(kline_dir),
                "liq_rows": _load_liq_rows_from_dir(liq_dir),
            }
        aligned_rows.extend(
            dataset_mod.build_dataset(
                symbol=symbol,
                month_data=month_data,
                passed_months=passed_months,
            )
        )

    raw_events = review_mod.detect_shocks_with_gap_resets(aligned_rows)
    dedup_events = deduplicate_events(raw_events)
    event_dicts = []
    for event in dedup_events:
        month = review_mod._month_for_ms(event.shock_bar_start_ms, months)
        event_dicts.append(
            {
                "symbol": event.symbol,
                "shock_bar_start_ms": event.shock_bar_start_ms,
                "dominant_liquidation_side": event.dominant_liquidation_side,
                "shock_notional_usdt": event.shock_notional_usdt,
                "month": month,
            }
        )
    return review_mod.compute_event_density(event_dicts, months)


def run_quarter_probe(
    quarter: str,
    symbols: list[str],
    root_data_dir: Path,
    skip_existing: bool = True,
    dry_run: bool = False,
) -> dict:
    months = quarter_to_months(quarter)
    raw_dir = root_data_dir / quarter / "raw"
    extracted_dir = root_data_dir / quarter / "extracted"

    manifest = manifest_mod.probe_manifest(
        symbols=symbols,
        months=months,
        sleep_between_checks=0.0,
        um_to_cm_map=manifest_mod.UM_TO_CM_SYMBOL,
    )
    if manifest.get("decision") == "data_unavailable":
        empty_density = review_mod.compute_event_density([], months)
        return evaluate_quarter(
            quarter=quarter,
            required_symbols=symbols,
            months=months,
            continuity_results={},
            density=empty_density,
            min_total_events=120,
            min_events_per_month=25,
            min_events_per_symbol=20,
        ) | {
            "manifest_decision": manifest.get("decision"),
            "manifest_missing_symbol_months": manifest.get("missing_symbol_months", []),
        }

    resolved = fetch_mod.resolve_download_config(
        manifest=manifest,
        cli_symbols=symbols,
        cli_months=months,
        cli_liquidation_mode="auto",
    )
    plan = fetch_mod.build_download_plan(
        resolved["symbols"],
        resolved["months"],
        liquidation_mode=resolved["liquidation_mode"],
    )
    fetch_mod.execute_download_plan(
        plan=plan,
        raw_dir=raw_dir,
        extracted_dir=extracted_dir,
        skip_existing=skip_existing,
        dry_run=dry_run,
        sleep_sec=0.0,
    )

    if dry_run:
        empty_density = review_mod.compute_event_density([], months)
        return evaluate_quarter(
            quarter=quarter,
            required_symbols=symbols,
            months=months,
            continuity_results={},
            density=empty_density,
            min_total_events=120,
            min_events_per_month=25,
            min_events_per_symbol=20,
        ) | {
            "manifest_decision": manifest.get("decision"),
            "manifest_missing_symbol_months": manifest.get("missing_symbol_months", []),
            "dry_run": True,
        }

    continuity_summary = build_quarter_continuity_summary(
        extracted_dir=extracted_dir,
        symbols=symbols,
        months=months,
    )
    density = build_quarter_density_summary(
        extracted_dir=extracted_dir,
        continuity_summary=continuity_summary,
        symbols=symbols,
        months=months,
    )

    return evaluate_quarter(
        quarter=quarter,
        required_symbols=symbols,
        months=months,
        continuity_results=continuity_summary["results"],
        density=density,
        min_total_events=120,
        min_events_per_month=25,
        min_events_per_symbol=20,
    ) | {
        "manifest_decision": manifest.get("decision"),
        "manifest_missing_symbol_months": manifest.get("missing_symbol_months", []),
        "density": density,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen Route A candidate quarters.")
    parser.add_argument("--quarters", nargs="+", default=list(CANDIDATE_QUARTERS))
    parser.add_argument("--symbols", nargs="+", default=list(REQUIRED_SYMBOLS))
    parser.add_argument(
        "--data-root",
        default="data/binance_liquidation_snapshot/route_a_screening",
        help="Quarter-scoped raw/extracted root",
    )
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    quarter_results = []
    for quarter in args.quarters:
        logger.info(f"[{quarter}] screening start")
        quarter_results.append(
            run_quarter_probe(
                quarter=quarter,
                symbols=args.symbols,
                root_data_dir=Path(args.data_root),
                skip_existing=args.skip_existing,
                dry_run=args.dry_run,
            )
        )

    decision = compute_screening_decision(quarter_results)
    summary = {
        "required_symbols": args.symbols,
        "candidate_quarters": args.quarters,
        "quarter_results": quarter_results,
        **decision,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Quarter screening summary written to: {REPORT_PATH}")
    logger.info(f"Decision: {decision['decision']} selected_quarter={decision['selected_quarter']}")


if __name__ == "__main__":
    main()
