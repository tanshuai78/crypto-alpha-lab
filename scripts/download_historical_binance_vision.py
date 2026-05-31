#!/usr/bin/env python3
"""
Download historical liquidation snapshots (Coin-Margined proxy) and price Klines (USD-Margined) from Binance Vision.

Usage:
    python scripts/download_historical_binance_vision.py \
        --cm-symbol BTCUSD_PERP \
        --um-symbol BTCUSDT \
        --start-date 2024-01-01 \
        --end-date 2024-01-31 \
        --output-dir data/historical_vision
"""

import argparse
import datetime
import os
import time
import urllib.request
import zipfile
from pathlib import Path

from loguru import logger


def parse_date(date_str: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD.")


def download_file(url: str, output_path: Path) -> bool:
    """Download file with basic retry and rate limit compliance."""
    if output_path.exists():
        logger.info(f"File already exists, skipping: {output_path.name}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    retries = 3
    for attempt in range(retries):
        try:
            time.sleep(1.0)  # Sleep 1 second between requests to respect rate limits
            logger.info(f"Downloading {url} ...")
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with (
                urllib.request.urlopen(req, timeout=15) as response,
                open(output_path, "wb") as out_file,
            ):
                out_file.write(response.read())
            logger.info(f"Successfully downloaded: {output_path.name}")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{retries} failed for {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            if attempt < retries - 1:
                time.sleep(2.0 * (attempt + 1))
    return False


def unzip_and_clean(zip_path: Path, extract_to: Path) -> bool:
    """Extract zip file and delete the archive to save space."""
    if not zip_path.exists():
        return False
    try:
        logger.info(f"Extracting {zip_path.name} to {extract_to} ...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        zip_path.unlink()  # Clean up zip file
        return True
    except Exception as e:
        logger.error(f"Failed to unzip {zip_path.name}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download historical Coin-Margined liquidations and USD-Margined Klines from Binance Vision."
    )
    parser.add_argument(
        "--cm-symbol",
        default="BTCUSD_PERP",
        help="Coin-Margined symbol to use as liquidation proxy (default: BTCUSD_PERP)",
    )
    parser.add_argument(
        "--um-symbol",
        default="BTCUSDT",
        help="USD-Margined symbol to fetch price Klines for (default: BTCUSDT)",
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default="2024-01-01",
        help="Start date in YYYY-MM-DD format (default: 2024-01-01)",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default="2024-01-31",
        help="End date in YYYY-MM-DD format (default: 2024-01-31)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/historical_vision",
        help="Directory to save downloaded and extracted data (default: data/historical_vision)",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cm_symbol = args.cm_symbol.upper()
    um_symbol = args.um_symbol.upper()
    current_date = args.start_date
    end_date = args.end_date

    logger.info(
        f"Starting download of Vision data from {current_date} to {end_date} for "
        f"liquidations ({cm_symbol}) and klines ({um_symbol})."
    )

    downloaded_liq = 0
    downloaded_klines = 0
    total_days = (end_date - current_date).days + 1

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        logger.info(f"=== Processing Date: {date_str} ===")

        # 1. Download Coin-Margined Daily Liquidation Snapshot
        cm_zip_name = f"{cm_symbol}-liquidationSnapshot-{date_str}.zip"
        cm_url = (
            f"https://data.binance.vision/data/futures/cm/daily/liquidationSnapshot/"
            f"{cm_symbol}/{cm_zip_name}"
        )
        cm_zip_path = output_dir / "zips" / cm_zip_name
        extracted_liq_dir = output_dir / "liquidations" / cm_symbol

        if download_file(cm_url, cm_zip_path):
            if unzip_and_clean(cm_zip_path, extracted_liq_dir):
                downloaded_liq += 1

        # 2. Download USD-Margined Daily 1m Klines
        um_zip_name = f"{um_symbol}-1m-{date_str}.zip"
        um_url = (
            f"https://data.binance.vision/data/futures/um/daily/klines/{um_symbol}/1m/{um_zip_name}"
        )
        um_zip_path = output_dir / "zips" / um_zip_name
        extracted_kline_dir = output_dir / "klines" / um_symbol

        if download_file(um_url, um_zip_path):
            if unzip_and_clean(um_zip_path, extracted_kline_dir):
                downloaded_klines += 1

        current_date += datetime.timedelta(days=1)

    # Clean up empty zips folder if it exists
    zips_dir = output_dir / "zips"
    if zips_dir.exists() and not os.listdir(zips_dir):
        zips_dir.rmdir()

    logger.info("=== Download and Extraction Summary ===")
    logger.info(f"Date range: {args.start_date} to {end_date} ({total_days} days)")
    logger.info(
        f"Coin-Margined liquidations ({cm_symbol}): {downloaded_liq}/{total_days} days downloaded and unzipped"
    )
    logger.info(
        f"USD-Margined 1m klines ({um_symbol}): {downloaded_klines}/{total_days} days downloaded and unzipped"
    )
    logger.info(f"Output files are located in: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
