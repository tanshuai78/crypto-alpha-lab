#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import ccxt
from loguru import logger

from research.cross_sectional_factor_lab.stageA2 import run_stageA2_regime_cash_fallback_diagnostic
from research.cross_sectional_factor_lab.universe import filter_stage0_universe, normalize_symbol
from scripts.run_factor_lab_stageA_v1_momentum import (
    get_ccxt_symbol,
    parse_binance_spot_klines_to_daily_bars,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Factor Lab Stage A2 regime/cash fallback diagnostic.")
    parser.add_argument("--offline-sample", help="Path to offline daily bars JSON fixture")
    parser.add_argument("--output", required=True, help="Path to write summary JSON")
    parser.add_argument("--history-days", type=int, default=540, help="Required history days")
    parser.add_argument("--exchange", default="binance", help="Exchange ID; only binance is supported")
    parser.add_argument("--max-symbols", type=int, help="Optional maximum eligible symbols for live fetch")
    parser.add_argument("--fail-on-decision", action="store_true", help="Return non-zero if diagnostic cannot complete")
    return parser.parse_args(argv)


def _unavailable_summary(market: str, blocker: str) -> dict[str, Any]:
    return {
        "run_mode": "stageA2_regime_cash_fallback_diagnostic",
        "scope": "regime_cash_fallback_only",
        "market": market,
        "bias_label": "survivorship_bias_not_controlled",
        "live_usage": "not_allowed",
        "paper_shadow_allowed": False,
        "decision": "stageA2_data_unavailable",
        "primary_blocker": blocker,
        "variants": [],
        "winner_variant": None,
        "can_enter_stageA2_round2": False,
    }


def write_summary(summary: dict[str, Any], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fetch_live_binance_daily_bars(args: argparse.Namespace) -> list[dict[str, Any]]:
    client = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    client.load_markets()

    spot_symbols = [
        m["symbol"]
        for m in client.markets.values()
        if m["active"] and m["spot"] and m.get("quote") == "USDT"
    ]
    audit = filter_stage0_universe(spot_symbols)
    eligible = list(audit.eligible_symbols)
    if args.max_symbols:
        eligible = eligible[: args.max_symbols]

    since_ms = client.milliseconds() - (args.history_days + 35) * 86400 * 1000
    daily_bars: list[dict[str, Any]] = []
    for idx, normalized in enumerate(eligible):
        ccxt_symbol = get_ccxt_symbol(client, normalize_symbol(normalized))
        if not ccxt_symbol:
            logger.warning(f"Could not map symbol {normalized} to CCXT")
            continue
        logger.info(f"[{idx + 1}/{len(eligible)}] Fetching {normalized}")
        try:
            klines = client.publicGetKlines({
                "symbol": normalize_symbol(normalized),
                "interval": "1d",
                "startTime": since_ms,
                "limit": 1000,
            })
            daily_bars.extend(parse_binance_spot_klines_to_daily_bars(normalized, klines))
            time.sleep(0.1)
        except Exception as exc:
            logger.warning(f"Failed to fetch {normalized}: {exc}")
    return daily_bars


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.offline_sample:
        try:
            fixture = json.loads(Path(args.offline_sample).read_text(encoding="utf-8"))
        except Exception as exc:
            summary = _unavailable_summary("binance_spot", f"read_fixture_failed: {exc}")
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0
        daily_bars = fixture.get("daily_bars", [])
        summary = run_stageA2_regime_cash_fallback_diagnostic(daily_bars)
    else:
        if args.exchange.lower() != "binance":
            summary = _unavailable_summary(f"{args.exchange}_spot", f"unsupported_exchange: {args.exchange}")
            write_summary(summary, args.output)
            return 1 if args.fail_on_decision else 0
        try:
            daily_bars = _fetch_live_binance_daily_bars(args)
            summary = run_stageA2_regime_cash_fallback_diagnostic(daily_bars)
        except Exception as exc:
            summary = _unavailable_summary("binance_spot", f"live_fetch_failed: {exc}")

    write_summary(summary, args.output)
    logger.info(f"Summary written to {args.output}")
    logger.info(f"Decision: {summary.get('decision')}")

    if args.fail_on_decision and summary.get("decision") != "stageA2_round1_completed":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
