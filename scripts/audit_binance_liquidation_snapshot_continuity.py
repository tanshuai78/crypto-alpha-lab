#!/usr/bin/env python3
"""
scripts/audit_binance_liquidation_snapshot_continuity.py

Validates continuity of Binance Vision extracted data before event-study.

Continuity gates (per symbol-month):
  Price side:
    - coverage_ratio >= BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO (0.99)
    - max_gap_minutes <= BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES (1)
  Liquidation side:
    - liquidation file coverage ratio must be 1.0 (all daily files present)
    - sparse liquidation rows (many zero minutes) do NOT fail the gate

Zero-fill semantics:
  After joining onto the continuous price grid, any minute without a liquidation
  event gets long_liq_usdt=0 and short_liq_usdt=0. This matches the existing
  aggregate_trend_regime_liquidations.py convention.

Output:
  reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json

Usage:
    PYTHONPATH=src uv run python scripts/audit_binance_liquidation_snapshot_continuity.py
"""

import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg

REPORT_PATH = Path("reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json")

# UM futures opened in 2019; UTC epoch for 2024-01-01 00:00:00
_JAN_2024_EPOCH_MS = 1_704_067_200_000
_MS_PER_MINUTE = 60_000


# ---------------------------------------------------------------------------
# Minute grid builder
# ---------------------------------------------------------------------------


def build_expected_minute_grid(month: str) -> list[int]:
    """
    Return a list of UTC epoch millisecond timestamps for every 1m bar
    open-time in the given YYYY-MM month.

    The grid runs from YYYY-MM-01 00:00:00 UTC to the last minute of the month.
    """
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, mon + 1, 1)
    month_start = date(year, mon, 1)
    days = (next_month_start - month_start).days
    total_minutes = days * 1440

    # Epoch ms for the first minute of the month (UTC midnight)
    import calendar
    first_ms = int(calendar.timegm(date(year, mon, 1).timetuple())) * 1000

    return [first_ms + i * _MS_PER_MINUTE for i in range(total_minutes)]


# ---------------------------------------------------------------------------
# Price continuity auditor
# ---------------------------------------------------------------------------


def audit_price_continuity(price_rows: list[dict], month: str) -> dict:
    """
    Audit 1m price row continuity against the expected minute grid.

    Args:
        price_rows: list of dicts with at least 'open_time_ms' key.
        month: YYYY-MM string.

    Returns:
        dict with keys:
            price_rows, price_coverage_ratio, price_missing_bucket_count,
            price_max_gap_minutes
    """
    grid = build_expected_minute_grid(month)
    expected_set = set(grid)
    actual_timestamps = sorted(r["open_time_ms"] for r in price_rows)
    actual_set = set(actual_timestamps)

    missing = expected_set - actual_set
    present = expected_set & actual_set
    coverage_ratio = len(present) / len(expected_set) if expected_set else 0.0

    # Compute max gap in minutes using sorted grid positions
    # Walk the expected grid and find longest run of consecutive missing minutes
    max_gap = 0
    current_gap = 0
    for ts in grid:
        if ts not in actual_set:
            current_gap += 1
            max_gap = max(max_gap, current_gap)
        else:
            current_gap = 0

    return {
        "price_rows": len(price_rows),
        "price_coverage_ratio": round(coverage_ratio, 6),
        "price_missing_bucket_count": len(missing),
        "price_max_gap_minutes": max_gap,
    }


# ---------------------------------------------------------------------------
# Liquidation file coverage auditor
# ---------------------------------------------------------------------------


def audit_liquidation_file_coverage(files_found: list[str], month: str) -> dict:
    """
    Audit daily liquidation file availability.

    Args:
        files_found: List of YYYY-MM-DD date strings for which daily files exist.
        month: YYYY-MM string.

    Returns:
        dict with keys:
            liquidation_files_found, liquidation_files_expected,
            liquidation_file_coverage_ratio
    """
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, mon + 1, 1)
    days_in_month = (next_month_start - date(year, mon, 1)).days

    coverage_ratio = len(files_found) / days_in_month if days_in_month > 0 else 0.0

    return {
        "liquidation_files_found": len(files_found),
        "liquidation_files_expected": days_in_month,
        "liquidation_file_coverage_ratio": round(coverage_ratio, 6),
    }


# ---------------------------------------------------------------------------
# Integrated symbol-month auditor
# ---------------------------------------------------------------------------


def audit_symbol_month(
    symbol: str,
    month: str,
    price_rows: list[dict],
    liquidation_files_found: list[str],
    liquidation_rows: list[dict],
) -> dict:
    """
    Full continuity audit for one symbol-month.

    Liquidation rows are dicts with at least 'timestamp_ms' key.
    Sparse liquidation (few or zero rows) is NOT a failure condition.

    Returns:
        dict with all required continuity fields + passes_continuity_gate.
    """
    price_audit = audit_price_continuity(price_rows, month)
    file_audit = audit_liquidation_file_coverage(liquidation_files_found, month)

    grid = build_expected_minute_grid(month)
    grid_set = set(grid)

    # Index liquidation rows by their 1m bucket (floor to nearest minute)
    liq_by_minute: dict[int, list[dict]] = {}
    for row in liquidation_rows:
        bucket_ms = (row["timestamp_ms"] // _MS_PER_MINUTE) * _MS_PER_MINUTE
        liq_by_minute.setdefault(bucket_ms, []).append(row)

    # Build joined dataset (zero-fill missing liquidation minutes)
    joined: list[dict] = []
    zero_filled_count = 0
    for ts in grid:
        if ts in liq_by_minute:
            rows = liq_by_minute[ts]
            long_liq = sum(r.get("notional_usdt", 0) for r in rows if r.get("side") == "long")
            short_liq = sum(r.get("notional_usdt", 0) for r in rows if r.get("side") == "short")
        else:
            long_liq = 0.0
            short_liq = 0.0
            zero_filled_count += 1
        joined.append(
            {
                "open_time_ms": ts,
                "long_liq_usdt": long_liq,
                "short_liq_usdt": short_liq,
            }
        )

    # Gate logic:
    # Price gate: coverage_ratio >= threshold AND max_gap <= max_gap_threshold
    price_ok = (
        price_audit["price_coverage_ratio"] >= cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MIN_COVERAGE_RATIO
        and price_audit["price_max_gap_minutes"] <= cfg.BINANCE_LIQUIDATION_SNAPSHOT_CONTINUITY_MAX_GAP_MINUTES
    )
    # Liquidation file gate: all daily files must be present
    liq_file_ok = file_audit["liquidation_file_coverage_ratio"] >= 1.0
    passes_gate = price_ok and liq_file_ok

    return {
        # Price side
        "price_coverage_ratio": price_audit["price_coverage_ratio"],
        "price_missing_bucket_count": price_audit["price_missing_bucket_count"],
        "price_max_gap_minutes": price_audit["price_max_gap_minutes"],
        "price_rows": price_audit["price_rows"],
        # Liquidation file side
        "liquidation_files_found": file_audit["liquidation_files_found"],
        "liquidation_files_expected": file_audit["liquidation_files_expected"],
        "liquidation_file_coverage_ratio": file_audit["liquidation_file_coverage_ratio"],
        # Liquidation data side
        "liquidation_snapshot_rows": len(liquidation_rows),
        "zero_filled_liquidation_minutes": zero_filled_count,
        # Joined dataset
        "dataset_rows": len(joined),
        "joined_rows": len(joined),
        # Gate
        "passes_continuity_gate": passes_gate,
    }


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------


def _load_kline_csv(csv_path: Path) -> list[dict]:
    """
    Load a Binance 1m kline CSV.
    Binance kline CSV columns (no header on Vision files):
    open_time, open, high, low, close, volume, close_time, ...
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for line in reader:
            if not line or line[0].startswith("#"):
                continue
            try:
                open_time_ms = int(line[0])
                close = float(line[4])
                rows.append({"open_time_ms": open_time_ms, "close": close})
            except (ValueError, IndexError):
                continue
    return rows


def _load_liquidation_csv(csv_path: Path) -> list[dict]:
    """
    Load a Binance liquidationSnapshot CSV.
    Columns (with header): symbol,side,order_type,time_in_force,
    original_quantity,price,average_price,order_status,last_filled_quantity,
    accumulated_filled_quantity,time,update_time
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts_ms = int(row.get("time", row.get("Time", 0)))
                side_raw = row.get("side", row.get("Side", "")).strip().lower()
                # Map BUY → short liq (exchange buys to cover shorts)
                # Map SELL → long liq (exchange sells long positions)
                if side_raw in ("buy", "short"):
                    side = "short"
                else:
                    side = "long"
                avg_price = float(row.get("average_price", row.get("averagePrice", 0)) or 0)
                qty = float(row.get("last_filled_quantity", row.get("lastFilledQty", 0)) or 0)
                notional = avg_price * qty
                rows.append({"timestamp_ms": ts_ms, "side": side, "notional_usdt": notional})
            except (ValueError, KeyError):
                continue
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    extracted_dir = Path(cfg.BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR)
    symbols_raw = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS)
    months = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS)

    # Normalise symbols
    binance_symbols = [s.replace("/", "") for s in symbols_raw]
    ccxt_to_binance = dict(zip(symbols_raw, binance_symbols))

    summary: dict = {
        "data_source": "binance_vision_liquidation_snapshot",
        "liquidation_data_semantics": "binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms",
        "not_complete_liquidation_tape": True,
        "sample_window": "2024-01_to_2024-03",
        "results": {},
    }

    all_pass = True

    for sym_raw in symbols_raw:
        sym = ccxt_to_binance[sym_raw]
        summary["results"][sym] = {}

        for month in months:
            logger.info(f"Auditing {sym} / {month} ...")

            # Load price rows
            kline_dir = extracted_dir / "klines" / sym / month
            price_rows: list[dict] = []
            if kline_dir.exists():
                for csv_file in sorted(kline_dir.glob("*.csv")):
                    price_rows.extend(_load_kline_csv(csv_file))
            else:
                logger.warning(f"No kline data found for {sym}/{month} in {kline_dir}")

            # Find liquidation daily files
            liq_dir = extracted_dir / "liquidationSnapshot" / sym / month
            liq_files_found: list[str] = []
            liq_rows: list[dict] = []
            if liq_dir.exists():
                for csv_file in sorted(liq_dir.glob("*.csv")):
                    # Extract date from filename: BTCUSDT-liquidationSnapshot-2024-01-15.csv
                    parts = csv_file.stem.split("-")
                    if len(parts) >= 4:
                        date_str = "-".join(parts[-3:])
                        liq_files_found.append(date_str)
                    liq_rows.extend(_load_liquidation_csv(csv_file))
            else:
                logger.warning(f"No liquidation data found for {sym}/{month} in {liq_dir}")

            result = audit_symbol_month(
                symbol=sym,
                month=month,
                price_rows=price_rows,
                liquidation_files_found=liq_files_found,
                liquidation_rows=liq_rows,
            )
            summary["results"][sym][month] = result

            status = "PASS" if result["passes_continuity_gate"] else "FAIL"
            logger.info(
                f"{sym}/{month}: {status} | "
                f"price_coverage={result['price_coverage_ratio']:.4f} "
                f"liq_file_coverage={result['liquidation_file_coverage_ratio']:.4f} "
                f"liq_rows={result['liquidation_snapshot_rows']} "
                f"zero_filled={result['zero_filled_liquidation_minutes']}"
            )
            if not result["passes_continuity_gate"]:
                all_pass = False

    summary["all_symbol_months_pass"] = all_pass

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Continuity summary written to: {REPORT_PATH}")
    if not all_pass:
        logger.warning("One or more symbol-months failed the continuity gate. Check report.")


if __name__ == "__main__":
    main()
