#!/usr/bin/env python3
"""
scripts/build_binance_liquidation_snapshot_event_dataset.py

Adapts extracted Binance Vision CSVs into the same aligned-row format
consumed by the existing liquidation_shock_event_study pipeline.

Row shape (compatible with detect_shocks / response_map):
    {
        symbol:                           str,
        bar_start_ms:                     int,   # 1m bar open-time UTC ms
        long_liquidation_notional_1m_usdt: float,
        short_liquidation_notional_1m_usdt: float,
        open_price:                        float,
        close_price:                       float,
    }

Cross-month design:
  - All month slices for a symbol are concatenated into one continuous time
    series before shock detection.
  - Symbol-months that fail the continuity gate (per the continuity summary
    JSON) are excluded.
  - The first 24h of any month is preserved; no artificial truncation at
    month boundaries.
  - Liquidation minutes with zero activity are zero-filled.

Output:
  data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl
  reports/liquidation_shock_event_study/binance_snapshot_dataset_summary.json

Usage:
    PYTHONPATH=src uv run python scripts/build_binance_liquidation_snapshot_event_dataset.py
"""

import csv
import json
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg

_MS_PER_MIN = 60_000

CONTINUITY_REPORT = Path(
    "reports/liquidation_shock_event_study/binance_snapshot_continuity_summary.json"
)
DATASET_JSONL = Path(cfg.BINANCE_LIQUIDATION_SNAPSHOT_PROCESSED_DIR) / "binance_snapshot_dataset.jsonl"
DATASET_SUMMARY = Path(
    "reports/liquidation_shock_event_study/binance_snapshot_dataset_summary.json"
)


# ---------------------------------------------------------------------------
# Core row-building functions (pure — no I/O, fully testable)
# ---------------------------------------------------------------------------


def build_aligned_rows(
    symbol: str,
    price_rows: list[dict],
    liquidation_rows: list[dict],
) -> list[dict]:
    """
    Align price and liquidation rows onto the price grid.

    Price rows must have: open_time_ms, open_price, close_price.
    Liquidation rows must have: timestamp_ms, side ('long'|'short'), notional_usdt.

    Minutes with no liquidation events are zero-filled.

    Returns list of aligned dicts sorted ascending by bar_start_ms.
    """
    # Index price rows by open_time_ms
    price_by_ts: dict[int, dict] = {}
    for row in price_rows:
        price_by_ts[row["open_time_ms"]] = row

    # Bucket liquidation rows by 1m bar (floor to nearest minute)
    liq_long: dict[int, float] = {}
    liq_short: dict[int, float] = {}
    for row in liquidation_rows:
        bucket_ms = (row["timestamp_ms"] // _MS_PER_MIN) * _MS_PER_MIN
        notional = float(row.get("notional_usdt", 0))
        if row.get("side") == "long":
            liq_long[bucket_ms] = liq_long.get(bucket_ms, 0.0) + notional
        else:
            liq_short[bucket_ms] = liq_short.get(bucket_ms, 0.0) + notional

    # Build aligned rows over the price grid (preserves exact minute coverage)
    aligned: list[dict] = []
    for ts in sorted(price_by_ts.keys()):
        price = price_by_ts[ts]
        aligned.append(
            {
                "symbol": symbol,
                "bar_start_ms": ts,
                "long_liquidation_notional_1m_usdt": liq_long.get(ts, 0.0),
                "short_liquidation_notional_1m_usdt": liq_short.get(ts, 0.0),
                "open_price": float(price.get("open_price", price.get("open", 0.0))),
                "close_price": float(price.get("close_price", price.get("close", 0.0))),
            }
        )

    return aligned


def build_dataset(
    symbol: str,
    month_data: dict[str, dict],
    passed_months: list[str],
) -> list[dict]:
    """
    Build the cross-month continuous time series for one symbol.

    Args:
        symbol: Binance symbol string.
        month_data: {month: {"price_rows": [...], "liq_rows": [...]}}
        passed_months: List of months that passed the continuity gate.

    Returns:
        Sorted list of aligned rows from all passed months concatenated.
    """
    all_rows: list[dict] = []

    for month in passed_months:
        if month not in month_data:
            logger.warning(f"[{symbol}] {month} passed but has no data — skipping")
            continue
        data = month_data[month]
        rows = build_aligned_rows(
            symbol=symbol,
            price_rows=data["price_rows"],
            liquidation_rows=data.get("liq_rows", []),
        )
        all_rows.extend(rows)

    # Sort by bar_start_ms ascending (cross-month join)
    all_rows.sort(key=lambda r: r["bar_start_ms"])
    return all_rows


# ---------------------------------------------------------------------------
# CSV loaders (adapted for Binance Vision format)
# ---------------------------------------------------------------------------


def _load_kline_csv(csv_path: Path) -> list[dict]:
    """
    Load Binance 1m kline CSV (no header).
    Columns: open_time, open, high, low, close, volume, close_time, ...
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for line in reader:
            if not line or not line[0].strip().isdigit():
                continue
            try:
                rows.append(
                    {
                        "open_time_ms": int(line[0]),
                        "open_price": float(line[1]),
                        "close_price": float(line[4]),
                    }
                )
            except (ValueError, IndexError):
                continue
    return rows


def _load_liquidation_csv(csv_path: Path) -> list[dict]:
    """
    Load Binance liquidationSnapshot CSV (with header).
    Side mapping: BUY → exchange buys to close shorts → short liq
                  SELL → exchange sells long positions → long liq
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts_ms = int(row.get("time", row.get("Time", 0)) or 0)
                side_raw = (row.get("side", row.get("Side", "")) or "").strip().upper()
                side = "short" if side_raw == "BUY" else "long"
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


def _ccxt_to_binance(sym: str) -> str:
    return sym.replace("/", "")


def main() -> None:
    extracted_dir = Path(cfg.BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR)
    symbols_raw = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS)
    months = list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS)
    binance_symbols = [_ccxt_to_binance(s) for s in symbols_raw]

    # Load continuity report to determine passed symbol-months
    passed_by_symbol: dict[str, list[str]] = {}
    if CONTINUITY_REPORT.exists():
        with open(CONTINUITY_REPORT) as f:
            continuity = json.load(f)
        for sym in binance_symbols:
            passed_months = []
            for month in months:
                sym_data = continuity.get("results", {}).get(sym, {}).get(month, {})
                if sym_data.get("passes_continuity_gate", False):
                    passed_months.append(month)
            passed_by_symbol[sym] = passed_months
    else:
        # If no continuity report, treat all months as passed (dev / dry-run mode)
        logger.warning(f"Continuity report not found at {CONTINUITY_REPORT} — treating all months as passed")
        for sym in binance_symbols:
            passed_by_symbol[sym] = months

    all_rows: list[dict] = []
    summary: dict = {
        "data_source": "binance_vision_liquidation_snapshot",
        "liquidation_data_semantics": "binance_forceorder_largest_order_snapshot_per_symbol_per_1000ms",
        "not_complete_liquidation_tape": True,
        "notional_interpretation": "snapshot_notional_proxy_not_total_market_liquidation",
        "sample_window": "2024-01_to_2024-03",
        "known_window_bias": "Q1_2024_trending_crypto_market",
        "generalization_allowed": False,
        "symbols": {},
    }

    for sym in binance_symbols:
        passed_months = passed_by_symbol.get(sym, [])
        if not passed_months:
            logger.warning(f"[{sym}] No months passed continuity gate — excluded from dataset")
            summary["symbols"][sym] = {"passed_months": [], "total_rows": 0}
            continue

        month_data: dict[str, dict] = {}
        for month in passed_months:
            kline_dir = extracted_dir / "klines" / sym / month
            liq_dir = extracted_dir / "liquidationSnapshot" / sym / month

            price_rows: list[dict] = []
            if kline_dir.exists():
                for csv_file in sorted(kline_dir.glob("*.csv")):
                    price_rows.extend(_load_kline_csv(csv_file))

            liq_rows: list[dict] = []
            if liq_dir.exists():
                for csv_file in sorted(liq_dir.glob("*.csv")):
                    liq_rows.extend(_load_liquidation_csv(csv_file))

            month_data[month] = {"price_rows": price_rows, "liq_rows": liq_rows}
            logger.info(f"[{sym}/{month}] price_rows={len(price_rows)} liq_rows={len(liq_rows)}")

        sym_rows = build_dataset(
            symbol=sym,
            month_data=month_data,
            passed_months=passed_months,
        )
        all_rows.extend(sym_rows)
        summary["symbols"][sym] = {
            "passed_months": passed_months,
            "total_rows": len(sym_rows),
        }
        logger.info(f"[{sym}] built {len(sym_rows)} rows across {passed_months}")

    # Write JSONL
    DATASET_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(DATASET_JSONL, "w") as f:
        for row in all_rows:
            f.write(json.dumps(row) + "\n")
    logger.info(f"Dataset JSONL: {len(all_rows)} total rows → {DATASET_JSONL}")

    summary["total_rows"] = len(all_rows)

    DATASET_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with open(DATASET_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Dataset summary written to: {DATASET_SUMMARY}")


if __name__ == "__main__":
    main()
