#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import ccxt
from loguru import logger

from research.cross_sectional_factor_lab.backtest import run_stageA_v1_backtest
from research.cross_sectional_factor_lab.universe import filter_stage0_universe, normalize_symbol


def get_ccxt_symbol(client: ccxt.Exchange, normalized: str) -> str | None:
    for sym, m in client.markets.items():
        if m["id"] == normalized or normalize_symbol(sym) == normalized:
            return sym
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Cross-Sectional Factor Lab Stage A v1 backtest.")
    parser.add_argument("--offline-sample", help="Path to offline daily bars JSON fixture")
    parser.add_argument("--output", required=True, help="Path to write the summary JSON output")
    parser.add_argument("--history-days", type=int, default=540, help="Required history days (default: 540)")
    parser.add_argument("--exchange", default="binance", help="Exchange ID (default: binance)")
    parser.add_argument("--max-symbols", type=int, help="Optional maximum number of symbols to audit/backtest")
    parser.add_argument("--fail-on-decision", action="store_true", help="Return non-zero exit code if backtest fails")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.offline_sample:
        logger.info(f"Running in offline mode using fixture: {args.offline_sample}")
        try:
            with open(args.offline_sample, encoding="utf-8") as f:
                fixture = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read offline fixture: {e}")
            summary = {
                "run_mode": "stageA_v1_momentum_backtest",
                "market": "binance_spot",
                "bias_label": "survivorship_bias_not_controlled",
                "primary_portfolio": "top10_equal_weight",
                "live_usage": "not_allowed",
                "decision": "stageA_v1_data_unavailable",
                "primary_blocker": f"read_fixture_failed: {str(e)}",
            }
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0

        daily_bars = fixture.get("daily_bars", [])
        summary = run_stageA_v1_backtest(daily_bars)

    else:
        logger.info("Running in live network mode fetching Binance spot daily bars...")
        if args.exchange.lower() != "binance":
            logger.error(f"Exchange {args.exchange} not supported for Stage A v1 live run.")
            summary = {
                "run_mode": "stageA_v1_momentum_backtest",
                "market": f"{args.exchange}_spot",
                "bias_label": "survivorship_bias_not_controlled",
                "primary_portfolio": "top10_equal_weight",
                "live_usage": "not_allowed",
                "decision": "stageA_v1_data_unavailable",
                "primary_blocker": f"unsupported_exchange: {args.exchange}",
            }
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0

        client = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
        try:
            client.load_markets()
        except Exception as e:
            logger.error(f"Failed to load markets: {e}")
            summary = {
                "run_mode": "stageA_v1_momentum_backtest",
                "market": "binance_spot",
                "bias_label": "survivorship_bias_not_controlled",
                "primary_portfolio": "top10_equal_weight",
                "live_usage": "not_allowed",
                "decision": "stageA_v1_data_unavailable",
                "primary_blocker": f"load_markets_failed: {str(e)}",
            }
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0

        # Get active USDT spot pairs
        spot_symbols = [
            m["symbol"]
            for m in client.markets.values()
            if m["active"] and m["spot"] and m.get("quote") == "USDT"
        ]

        # Apply static exclusions
        audit = filter_stage0_universe(spot_symbols)
        eligible_normalized = list(audit.eligible_symbols)

        if args.max_symbols:
            logger.info(f"Limiting to first {args.max_symbols} eligible symbols.")
            eligible_normalized = eligible_normalized[:args.max_symbols]

        # Fetch daily bars
        daily_bars = []
        # Fetch lookback + warmup buffer: history_days + 35 days
        since_ms = client.milliseconds() - (args.history_days + 35) * 86400 * 1000

        logger.info(f"Fetching {args.history_days + 35} days of history for {len(eligible_normalized)} symbols...")
        for idx, normalized in enumerate(eligible_normalized):
            ccxt_sym = get_ccxt_symbol(client, normalized)
            if not ccxt_sym:
                logger.warning(f"Could not map symbol {normalized} to CCXT")
                continue

            logger.info(f"[{idx+1}/{len(eligible_normalized)}] Fetching {normalized} ({ccxt_sym})...")
            try:
                # Binance returns up to 1000 bars
                ohlcv = client.fetch_ohlcv(ccxt_sym, timeframe="1d", since=since_ms, limit=1000)
                for bar in ohlcv:
                    ts, o, h, l, c, v = bar
                    date_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    daily_bars.append({
                        "symbol": normalized,
                        "date_utc": date_str,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c,
                        "base_volume": v,
                        "quote_volume": v * c  # Estimate quote volume as base_volume * close
                    })
                time.sleep(0.1)  # Sleep between calls to respect rate limits
            except Exception as e:
                logger.warning(f"Failed to fetch {normalized}: {e}")

        summary = run_stageA_v1_backtest(daily_bars)

    write_summary(summary, args.output)
    
    logger.info(f"Summary written to {args.output}")
    logger.info(f"Decision: {summary['decision']}")

    if args.fail_on_decision:
        if summary.get("decision") == "stageA_v1_passed":
            return 0
        else:
            logger.error(f"Backtest failed decision gate: {summary.get('decision')}")
            return 1
    
    return 0


def write_summary(summary: dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    sys.exit(main())
