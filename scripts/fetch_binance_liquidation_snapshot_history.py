#!/usr/bin/env python3
"""
scripts/fetch_binance_liquidation_snapshot_history.py

Download Binance Vision historical files for the liquidation snapshot event study:
  - Monthly 1m kline ZIPs (um/monthly/klines)
  - Daily or monthly liquidationSnapshot ZIPs (um/daily or monthly/liquidationSnapshot)
  - Corresponding .CHECKSUM files for every downloaded ZIP

Checksum behavior:
  - If CHECKSUM is available and verification passes → status: checksum_verified
  - If CHECKSUM is missing → status: checksum_unverified (file NOT promoted silently)
  - If CHECKSUM verification fails → status: checksum_failed (quarantined)

Usage:
    PYTHONPATH=src uv run python scripts/fetch_binance_liquidation_snapshot_history.py [--dry-run]

CLI flags:
    --symbols         Override symbols (default: from configs/base.py)
    --months          Override months (default: from configs/base.py)
    --raw-dir         Override raw data dir
    --extracted-dir   Override extracted data dir
    --dry-run         Print plan without downloading
    --skip-existing   Skip already-downloaded files
    --liquidation-mode  daily | monthly (default: daily)
"""

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import configs.base as cfg

BINANCE_VISION_BASE = "https://data.binance.vision"
REPORT_PATH = Path("reports/liquidation_shock_event_study/binance_snapshot_fetch_summary.json")


# ---------------------------------------------------------------------------
# URL builders (pure — testable without network)
# ---------------------------------------------------------------------------


def build_um_monthly_kline_zip_url(binance_symbol: str, month: str) -> str:
    """
    Monthly 1m kline ZIP for a UM futures symbol.
    e.g. https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip
    """
    fname = f"{binance_symbol}-1m-{month}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/monthly/klines/{binance_symbol}/1m/{fname}"


def build_um_daily_liquidation_zip_url(binance_symbol: str, date_str: str) -> str:
    """
    Daily liquidationSnapshot ZIP.
    e.g. https://data.binance.vision/data/futures/um/daily/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2024-01-01.zip
    """
    fname = f"{binance_symbol}-liquidationSnapshot-{date_str}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/daily/liquidationSnapshot/{binance_symbol}/{fname}"


def build_um_monthly_liquidation_zip_url(binance_symbol: str, month: str) -> str:
    """
    Monthly liquidationSnapshot ZIP.
    e.g. https://data.binance.vision/data/futures/um/monthly/liquidationSnapshot/BTCUSDT/BTCUSDT-liquidationSnapshot-2024-01.zip
    """
    fname = f"{binance_symbol}-liquidationSnapshot-{month}.zip"
    return f"{BINANCE_VISION_BASE}/data/futures/um/monthly/liquidationSnapshot/{binance_symbol}/{fname}"


def build_checksum_url(zip_url: str) -> str:
    """Append '.CHECKSUM' to a ZIP URL to get the checksum file URL."""
    return zip_url + ".CHECKSUM"


# ---------------------------------------------------------------------------
# Month → list-of-date-strings
# ---------------------------------------------------------------------------


def _month_dates(month: str) -> list[str]:
    """Return all YYYY-MM-DD strings for a YYYY-MM month."""
    year, mon = int(month[:4]), int(month[5:7])
    if mon == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, mon + 1, 1)
    first = date(year, mon, 1)
    days = (next_month - first).days
    return [(first + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]


# ---------------------------------------------------------------------------
# Download plan builder (pure — no I/O)
# ---------------------------------------------------------------------------


def build_download_plan(
    symbols: list[str],
    months: list[str],
    liquidation_mode: str = "daily",
) -> list[dict]:
    """
    Build a list of download entries (no I/O).

    Each entry is a dict with:
        url           — ZIP URL
        checksum_url  — .CHECKSUM URL
        kind          — 'kline' | 'liquidation'
        symbol        — Binance symbol string
        month         — YYYY-MM
        date          — YYYY-MM-DD (daily liq only) or None

    Args:
        symbols: Binance symbol strings (e.g. ["BTCUSDT"]).
        months:  List of YYYY-MM strings.
        liquidation_mode: 'daily' or 'monthly'.
    """
    plan: list[dict] = []

    for sym in symbols:
        for month in months:
            # 1. Monthly kline entry
            kline_url = build_um_monthly_kline_zip_url(sym, month)
            plan.append(
                {
                    "url": kline_url,
                    "checksum_url": build_checksum_url(kline_url),
                    "kind": "kline",
                    "symbol": sym,
                    "month": month,
                    "date": None,
                }
            )

            # 2. Liquidation entries
            if liquidation_mode == "monthly":
                liq_url = build_um_monthly_liquidation_zip_url(sym, month)
                plan.append(
                    {
                        "url": liq_url,
                        "checksum_url": build_checksum_url(liq_url),
                        "kind": "liquidation",
                        "symbol": sym,
                        "month": month,
                        "date": None,
                    }
                )
            else:
                # Daily mode — one entry per day
                for day_str in _month_dates(month):
                    liq_url = build_um_daily_liquidation_zip_url(sym, day_str)
                    plan.append(
                        {
                            "url": liq_url,
                            "checksum_url": build_checksum_url(liq_url),
                            "kind": "liquidation",
                            "symbol": sym,
                            "month": month,
                            "date": day_str,
                        }
                    )

    return plan


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------


def _download_file(
    url: str,
    dest: Path,
    skip_existing: bool = False,
    sleep_sec: float = 0.5,
) -> bool:
    """Download a single file. Returns True on success."""
    if skip_existing and dest.exists():
        logger.info(f"Skip existing: {dest.name}")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(sleep_sec)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (research-fetch/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        logger.warning(f"Download failed {url}: {e}")
        if dest.exists():
            dest.unlink()
        return False


def _verify_checksum(zip_path: Path, checksum_path: Path) -> bool:
    """
    Verify SHA-256 checksum.
    Returns True if checksum matches, False otherwise.
    """
    try:
        checksum_text = checksum_path.read_text().strip()
        # Format: '<hex>  <filename>' or just '<hex>'
        parts = checksum_text.split()
        expected_hex = parts[0].lower()

        sha256 = hashlib.sha256()
        with open(zip_path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                sha256.update(chunk)
        actual_hex = sha256.hexdigest().lower()
        return actual_hex == expected_hex
    except Exception as e:
        logger.warning(f"Checksum verification error for {zip_path.name}: {e}")
        return False


def _extract_zip(zip_path: Path, extract_dir: Path) -> bool:
    """Extract a ZIP file. Returns True on success."""
    try:
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
        return True
    except Exception as e:
        logger.error(f"Extraction failed {zip_path.name}: {e}")
        return False


# ---------------------------------------------------------------------------
# Core execution
# ---------------------------------------------------------------------------


def execute_download_plan(
    plan: list[dict],
    raw_dir: Path,
    extracted_dir: Path,
    skip_existing: bool = True,
    dry_run: bool = False,
    sleep_sec: float = 0.5,
) -> list[dict]:
    """
    Execute download plan. Returns list of result dicts.

    Result dict fields:
        url, kind, symbol, month, date,
        zip_downloaded, checksum_downloaded, checksum_status,
        extracted
    """
    results: list[dict] = []

    for entry in plan:
        url = entry["url"]
        checksum_url = entry["checksum_url"]
        sym = entry["symbol"]
        month = entry["month"]
        kind = entry["kind"]
        day = entry.get("date")

        # Determine local paths
        zip_fname = url.split("/")[-1]
        cksum_fname = checksum_url.split("/")[-1]

        if kind == "kline":
            sub = raw_dir / "klines" / "monthly" / month / sym
        else:
            if day:
                sub = raw_dir / "liquidationSnapshot" / "daily" / month / sym
            else:
                sub = raw_dir / "liquidationSnapshot" / "monthly" / month / sym

        zip_path = sub / zip_fname
        cksum_path = sub / cksum_fname

        result: dict = {
            "url": url,
            "kind": kind,
            "symbol": sym,
            "month": month,
            "date": day,
            "zip_downloaded": False,
            "checksum_downloaded": False,
            "checksum_status": "not_checked",
            "extracted": False,
        }

        if dry_run:
            logger.info(f"[DRY-RUN] Would download: {zip_fname}")
            result["checksum_status"] = "dry_run"
            results.append(result)
            continue

        # Download ZIP
        zip_ok = _download_file(url, zip_path, skip_existing=skip_existing, sleep_sec=sleep_sec)
        result["zip_downloaded"] = zip_ok

        if not zip_ok:
            result["checksum_status"] = "download_failed"
            results.append(result)
            continue

        # Download CHECKSUM
        cksum_ok = _download_file(
            checksum_url, cksum_path, skip_existing=skip_existing, sleep_sec=sleep_sec
        )
        result["checksum_downloaded"] = cksum_ok

        if cksum_ok:
            verified = _verify_checksum(zip_path, cksum_path)
            result["checksum_status"] = "checksum_verified" if verified else "checksum_failed"
        else:
            result["checksum_status"] = "checksum_unverified"

        # Only extract if checksum is verified or absent (unverified but not failed)
        if result["checksum_status"] in ("checksum_verified", "checksum_unverified"):
            if kind == "kline":
                ext_dir = extracted_dir / "klines" / sym / month
            else:
                if day:
                    ext_dir = extracted_dir / "liquidationSnapshot" / sym / month
                else:
                    ext_dir = extracted_dir / "liquidationSnapshot" / sym / month

            extracted = _extract_zip(zip_path, ext_dir)
            result["extracted"] = extracted
        else:
            logger.warning(f"Quarantined (checksum failed): {zip_fname}")

        results.append(result)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _ccxt_to_binance(sym: str) -> str:
    return sym.replace("/", "")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Binance Vision historical liquidation snapshot + kline data."
    )
    parser.add_argument("--symbols", nargs="+", default=None, help="Binance symbols (e.g. BTCUSDT)")
    parser.add_argument("--months", nargs="+", default=None, help="Months YYYY-MM")
    parser.add_argument("--raw-dir", default=cfg.BINANCE_LIQUIDATION_SNAPSHOT_RAW_DIR)
    parser.add_argument("--extracted-dir", default=cfg.BINANCE_LIQUIDATION_SNAPSHOT_EXTRACTED_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument(
        "--liquidation-mode",
        choices=["daily", "monthly"],
        default="daily",
        help="Download daily or monthly liquidationSnapshot ZIPs (default: daily)",
    )
    args = parser.parse_args()

    symbols = args.symbols or [_ccxt_to_binance(s) for s in cfg.BINANCE_LIQUIDATION_SNAPSHOT_SYMBOLS]
    months = args.months or list(cfg.BINANCE_LIQUIDATION_SNAPSHOT_MONTHS)
    raw_dir = Path(args.raw_dir)
    extracted_dir = Path(args.extracted_dir)

    logger.info(f"Symbols: {symbols}")
    logger.info(f"Months: {months}")
    logger.info(f"Liquidation mode: {args.liquidation_mode}")
    logger.info(f"Dry run: {args.dry_run}")

    plan = build_download_plan(symbols, months, liquidation_mode=args.liquidation_mode)
    logger.info(f"Download plan: {len(plan)} entries")

    results = execute_download_plan(
        plan=plan,
        raw_dir=raw_dir,
        extracted_dir=extracted_dir,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
    )

    # Summary
    total = len(results)
    downloaded = sum(1 for r in results if r["zip_downloaded"])
    verified = sum(1 for r in results if r["checksum_status"] == "checksum_verified")
    unverified = sum(1 for r in results if r["checksum_status"] == "checksum_unverified")
    failed = sum(1 for r in results if r["checksum_status"] in ("checksum_failed", "download_failed"))
    extracted = sum(1 for r in results if r.get("extracted"))

    summary = {
        "symbols": symbols,
        "months": months,
        "liquidation_mode": args.liquidation_mode,
        "total_entries": total,
        "downloaded": downloaded,
        "checksum_verified": verified,
        "checksum_unverified": unverified,
        "checksum_failed_or_download_failed": failed,
        "extracted": extracted,
        "dry_run": args.dry_run,
        "entries": results,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Fetch summary: {downloaded}/{total} downloaded, {verified} verified, {unverified} unverified, {failed} failed")
    logger.info(f"Report written to: {REPORT_PATH}")

    if failed > 0:
        logger.warning(f"{failed} entries failed checksum or download — check report for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
