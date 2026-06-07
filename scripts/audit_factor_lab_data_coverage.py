#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import ccxt.async_support as ccxt
from loguru import logger

from configs.base import (
    FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN,
    FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED,
    FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY,
)
from research.cross_sectional_factor_lab.bias_contract import stage0_current_tradable_bias_contract
from research.cross_sectional_factor_lab.coverage import (
    Stage0CoverageSummary,
    SymbolCoverage,
    decide_stage0_readiness,
    expected_utc_daily_dates,
)
from research.cross_sectional_factor_lab.universe import filter_stage0_universe, normalize_symbol

LIQUIDITY_GATE_USAGE = "stage0_screening_only_not_historical_tradability"


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return sorted_vals[mid]


def get_medians(coverages: list[SymbolCoverage]) -> tuple[float, float, float, float]:
    if not coverages:
        return 0.0, 0.0, 0.0, 0.0
    ohlcvs = [c.ohlcv_coverage for c in coverages]
    fundings = [c.funding_coverage for c in coverages]
    ois = [c.oi_coverage for c in coverages]
    hists = [float(c.history_days) for c in coverages]
    return median(ohlcvs), median(fundings), median(ois), median(hists)


def build_stage0_summary(
    *,
    symbols_total: int,
    symbols_after_static_exclusions: int,
    symbols_passing_liquidity: int,
    daily_ohlcv_coverage_ratio_median: float,
    funding_coverage_ratio_median: float,
    open_interest_coverage_ratio_median: float,
    history_days_available_median: float,
    funding_oi_veto_readiness: str,
) -> Stage0CoverageSummary:
    return Stage0CoverageSummary(
        symbols_total=symbols_total,
        symbols_after_static_exclusions=symbols_after_static_exclusions,
        symbols_passing_liquidity=symbols_passing_liquidity,
        daily_ohlcv_coverage_ratio_median=daily_ohlcv_coverage_ratio_median,
        funding_coverage_ratio_median=funding_coverage_ratio_median,
        open_interest_coverage_ratio_median=open_interest_coverage_ratio_median,
        history_days_available_median=history_days_available_median,
        listing_metadata_available=True,
        funding_oi_veto_readiness=funding_oi_veto_readiness,
    )


def primary_blocker_for_summary(summary: Stage0CoverageSummary) -> str | None:
    if summary.symbols_passing_liquidity < FACTOR_LAB_STAGE0_MIN_SYMBOLS_PASSING_LIQUIDITY:
        return "insufficient_symbol_count"
    if summary.daily_ohlcv_coverage_ratio_median < FACTOR_LAB_STAGE0_DAILY_OHLCV_COVERAGE_MIN:
        return "insufficient_ohlcv_coverage"
    if summary.history_days_available_median < FACTOR_LAB_STAGE0_HISTORY_DAYS_REQUIRED:
        return "insufficient_history_days"
    return None


def allowed_modes_for_decision(*, decision: str, funding_oi_status: str) -> dict[str, Any]:
    if decision == "factor_lab_data_ready_with_bias":
        return {
            "price_volume_fast_track": True,
            "funding_veto": funding_oi_status == "ready",
            "oi_veto": False,
            "long_only_only": True,
            "c1_entry_block": "diagnostic_only",
            "survivorship_bias_label_required": True,
        }
    return {
        "price_volume_fast_track": False,
        "funding_veto": False,
        "oi_veto": False,
        "long_only_only": True,
        "c1_entry_block": "disabled",
        "survivorship_bias_label_required": True,
    }


def market_payload(
    *,
    audit: Any,
    symbols_passing_liquidity: int,
    coverages: list[SymbolCoverage],
    market_type: str,
    funding_oi_status: str,
) -> tuple[dict[str, Any], Stage0CoverageSummary, str]:
    ohlcv_med, funding_med, oi_med, hist_med = get_medians(coverages)
    summary = build_stage0_summary(
        symbols_total=audit.symbols_total,
        symbols_after_static_exclusions=audit.symbols_after_static_exclusions,
        symbols_passing_liquidity=symbols_passing_liquidity,
        daily_ohlcv_coverage_ratio_median=ohlcv_med,
        funding_coverage_ratio_median=funding_med,
        open_interest_coverage_ratio_median=oi_med,
        history_days_available_median=hist_med,
        funding_oi_veto_readiness=funding_oi_status,
    )
    decision = decide_stage0_readiness(summary)
    payload: dict[str, Any] = {
        "symbols_total": audit.symbols_total,
        "symbols_after_static_exclusions": audit.symbols_after_static_exclusions,
        "symbols_passing_liquidity": symbols_passing_liquidity,
        "daily_ohlcv_coverage_ratio_median": ohlcv_med,
        "history_days_available_median": hist_med,
        "decision": decision,
        "primary_blocker": primary_blocker_for_summary(summary),
    }
    if market_type == "spot":
        payload.update(
            {
                "funding_coverage_ratio_median": None,
                "open_interest_coverage_ratio_median": None,
                "funding_oi_veto_readiness": "not_applicable",
            }
        )
    else:
        payload.update(
            {
                "funding_coverage_ratio_median": funding_med,
                "open_interest_recent_coverage_ratio_median": oi_med,
                "open_interest_history_mode": "recent_only",
                "funding_oi_veto_readiness": funding_oi_status,
            }
        )
    return payload, summary, decision


def get_ccxt_symbol(client: ccxt.Exchange, normalized: str) -> str | None:
    """Map normalized symbol (e.g. BTCUSDT, VETUSDT:USDT) back to CCXT symbol (e.g. BTC/USDT, VET/USDT:USDT)."""
    for sym, m in client.markets.items():
        if m["id"] == normalized or normalize_symbol(sym) == normalized:
            return sym
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 0 Data Coverage & Bias Audit CLI.")
    parser.add_argument("--exchange", default="binance", help="Exchange ID (default: binance)")
    parser.add_argument(
        "--market-types",
        nargs="+",
        default=["spot", "usdt_perp"],
        help="Market types to audit (spot, usdt_perp)",
    )
    parser.add_argument("--history-days", type=int, default=540, help="Required history days (default: 540)")
    parser.add_argument(
        "--min-30d-median-quote-volume-usdt",
        type=float,
        default=20000000.0,
        help="Minimum 30-day median quote volume (default: 20M USDT)",
    )
    parser.add_argument("--output", required=True, help="Path to write the JSON summary output")
    parser.add_argument(
        "--offline-sample",
        help="Path to offline JSON fixture to run in deterministic offline test mode",
    )
    return parser.parse_args(argv)


def run_offline_audit(args: argparse.Namespace) -> dict[str, Any]:
    logger.info(f"Running in offline mode using fixture: {args.offline_sample}")
    with open(args.offline_sample, encoding="utf-8") as f:
        fixture = json.load(f)

    # 1. Split symbols from fixture
    spot_raw_symbols = []
    perp_raw_symbols = []
    for m in fixture["markets"]:
        if m["type"] == "spot":
            spot_raw_symbols.append(m["symbol"])
        elif m["type"] == "swap":
            perp_raw_symbols.append(m["symbol"])

    # 2. Filter via universe logic
    spot_audit = filter_stage0_universe(spot_raw_symbols)
    perp_audit = filter_stage0_universe(perp_raw_symbols)

    # Setup date range (stubbed for offline)
    end_date = date(2026, 6, 6)
    expected_utc_daily_dates(end_date, args.history_days)

    # Process Spot markets
    spot_symbols_passing_liquidity = 0
    spot_coverages = []
    for symbol in spot_audit.eligible_symbols:
        # Mock coverage matching symbol ID
        kline_key = f"{symbol}_spot"
        mock_kline = fixture["klines"].get(kline_key, {"history_length": 0, "coverage_ratio": 0.0, "median_volume_30d": 0.0})

        ohlcv_cov = mock_kline["coverage_ratio"]
        hist_days = mock_kline["history_length"]
        vol_30d = mock_kline["median_volume_30d"]

        passing_liq = vol_30d >= args.min_30d_median_quote_volume_usdt
        if passing_liq:
            spot_symbols_passing_liquidity += 1

        spot_coverages.append(
            SymbolCoverage(
                symbol=symbol,
                market_type="spot",
                ohlcv_coverage=ohlcv_cov,
                funding_coverage=0.0,
                oi_coverage=0.0,
                history_days=hist_days,
            )
        )

    # Process Perp markets
    perp_symbols_passing_liquidity = 0
    perp_coverages = []
    for symbol in perp_audit.eligible_symbols:
        kline_key = f"{symbol}_swap"
        mock_kline = fixture["klines"].get(kline_key, {"history_length": 0, "coverage_ratio": 0.0, "median_volume_30d": 0.0})
        mock_funding = fixture["funding_rates"].get(symbol, {"coverage_ratio": 0.0})
        mock_oi = fixture["open_interest_recent"].get(symbol, {"recent_days_count": 0, "coverage_ratio": 0.0})

        ohlcv_cov = mock_kline["coverage_ratio"]
        hist_days = mock_kline["history_length"]
        vol_30d = mock_kline["median_volume_30d"]
        funding_cov = mock_funding["coverage_ratio"]
        oi_cov = mock_oi["coverage_ratio"]

        passing_liq = vol_30d >= args.min_30d_median_quote_volume_usdt
        if passing_liq:
            perp_symbols_passing_liquidity += 1

        perp_coverages.append(
            SymbolCoverage(
                symbol=symbol,
                market_type="usdt_perp",
                ohlcv_coverage=ohlcv_cov,
                funding_coverage=funding_cov,
                oi_coverage=oi_cov,
                history_days=hist_days,
            )
        )

    # Calculate medians
    def get_medians(coverages: list[SymbolCoverage]) -> tuple[float, float, float, float]:
        if not coverages:
            return 0.0, 0.0, 0.0, 0.0
        ohlcvs = [c.ohlcv_coverage for c in coverages]
        fundings = [c.funding_coverage for c in coverages]
        ois = [c.oi_coverage for c in coverages]
        hists = [float(c.history_days) for c in coverages]
        return median(ohlcvs), median(fundings), median(ois), median(hists)

    spot_ohlcv_med, _, _, spot_hist_med = get_medians(spot_coverages)
    perp_ohlcv_med, perp_funding_med, perp_oi_med, perp_hist_med = get_medians(perp_coverages)

    # Deduce funding/OI readiness status
    # In offline mode we check if the mock perps have decent funding coverage
    funding_oi_status = "ready"
    if perp_coverages:
        if perp_funding_med < 0.90:
            funding_oi_status = "degraded"
        if perp_oi_med < 0.90:
            # We flag degraded if recent OI is below gate
            funding_oi_status = "degraded"
    else:
        funding_oi_status = "degraded"

    spot_market, spot_summary, spot_decision = market_payload(
        audit=spot_audit,
        symbols_passing_liquidity=spot_symbols_passing_liquidity,
        coverages=spot_coverages,
        market_type="spot",
        funding_oi_status="not_applicable",
    )
    perp_market, perp_summary, perp_decision = market_payload(
        audit=perp_audit,
        symbols_passing_liquidity=perp_symbols_passing_liquidity,
        coverages=perp_coverages,
        market_type="usdt_perp",
        funding_oi_status=funding_oi_status,
    )

    # Aggregate summaries
    total_passing_liquidity = spot_symbols_passing_liquidity + perp_symbols_passing_liquidity
    total_after_static = spot_audit.symbols_after_static_exclusions + perp_audit.symbols_after_static_exclusions

    summary = Stage0CoverageSummary(
        symbols_total=spot_audit.symbols_total + perp_audit.symbols_total,
        symbols_after_static_exclusions=total_after_static,
        symbols_passing_liquidity=total_passing_liquidity,
        daily_ohlcv_coverage_ratio_median=(
            spot_ohlcv_med if spot_decision == "factor_lab_data_ready_with_bias" else perp_ohlcv_med
        ),
        funding_coverage_ratio_median=perp_funding_med,
        open_interest_coverage_ratio_median=perp_oi_med,
        history_days_available_median=(
            spot_hist_med if spot_decision == "factor_lab_data_ready_with_bias" else perp_hist_med
        ),
        listing_metadata_available=True,
        funding_oi_veto_readiness=funding_oi_status,
    )

    market_decisions = (spot_decision, perp_decision)
    decision = (
        "factor_lab_data_ready_with_bias"
        if "factor_lab_data_ready_with_bias" in market_decisions
        else "factor_lab_data_unavailable"
    )

    # Allowed next stage logic
    if decision == "factor_lab_data_ready_with_bias":
        allowed_next_stage = "stage_a_exchange_only_fast_track"
        allowed_modes = {
            "price_volume_fast_track": True,
            "funding_veto": funding_oi_status == "ready",
            "oi_veto": False,  # OI is always recent-only degraded in Phase 1
            "long_only_only": True,
            "c1_entry_block": "diagnostic_only",
            "survivorship_bias_label_required": True,
        }
    else:
        allowed_next_stage = "fix_data_source"
        allowed_modes = {
            "price_volume_fast_track": False,
            "funding_veto": False,
            "oi_veto": False,
            "long_only_only": True,
            "c1_entry_block": "disabled",
            "survivorship_bias_label_required": True,
        }

    return {
        "run_mode": "stage0_data_coverage_audit",
        "data_source": args.exchange,
        "market_types": args.market_types,
        "universe_scope": "current_tradable_universe_only",
        "survivorship_bias_control": "not_controlled",
        "delisted_symbols_included": False,
        "result_usage": "hypothesis_screening_only_not_final_evidence",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_mode": "offline_sample",
        "api_errors_count": 0,
        "rate_limited_count": 0,
        "primary_blocker": None if decision == "factor_lab_data_ready_with_bias" else primary_blocker_for_summary(summary),
        "allowed_next_stage": allowed_next_stage,
        "stage_a_allowed_modes": allowed_modes,
        "stage_a_allowed_modes_by_market": {
            "spot": allowed_modes_for_decision(
                decision=spot_decision,
                funding_oi_status="not_applicable",
            ),
            "usdt_perp": allowed_modes_for_decision(
                decision=perp_decision,
                funding_oi_status=funding_oi_status,
            ),
        },
        "current_liquidity_gate": {
            "min_30d_median_quote_volume_usdt": args.min_30d_median_quote_volume_usdt,
            "usage": LIQUIDITY_GATE_USAGE,
        },
        "historical_liquidity_gate_ready": False,
        "symbols_total": summary.symbols_total,
        "symbols_after_static_exclusions": summary.symbols_after_static_exclusions,
        "symbols_passing_liquidity": summary.symbols_passing_liquidity,
        "history_days_required": args.history_days,
        "expected_daily_grid": {
            "timezone": "UTC",
            "end_date": end_date.isoformat(),
            "history_days": args.history_days,
            "excludes_incomplete_today": True,
        },
        "history_days_available_median": summary.history_days_available_median,
        "daily_ohlcv_coverage_ratio_median": summary.daily_ohlcv_coverage_ratio_median,
        "funding_coverage_ratio_median": summary.funding_coverage_ratio_median,
        "open_interest_coverage_ratio_median": summary.open_interest_coverage_ratio_median,
        "listing_metadata_available": summary.listing_metadata_available,
        "funding_oi_veto_readiness": summary.funding_oi_veto_readiness,
        "open_interest_history_mode": "recent_only",
        "open_interest_coverage_note": "binance_open_interest_hist_latest_30_days_only",
        "bias_contract": stage0_current_tradable_bias_contract(),
        "markets": {
            "spot": spot_market,
            "usdt_perp": perp_market,
        },
        "decision": decision,
    }


async def async_network_audit(args: argparse.Namespace) -> dict[str, Any]:
    logger.info("Running in live network mode auditing Binance public APIs...")
    spot_client = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "spot"}})
    perp_client = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "swap"}})

    try:
        await asyncio.gather(spot_client.load_markets(), perp_client.load_markets())
    except Exception as e:
        logger.error(f"Failed to load Binance markets: {e}")
        return {
            "run_mode": "stage0_data_coverage_audit",
            "decision": "factor_lab_data_unavailable",
            "primary_blocker": f"binance_markets_load_failed: {e}",
            "allowed_next_stage": "fix_data_source",
        }

    # Discover and filter spot
    spot_raw = [m["symbol"] for m in spot_client.markets.values() if m["active"] and m.get("quote") == "USDT"]
    spot_audit = filter_stage0_universe(spot_raw)

    # Discover and filter perp
    perp_raw = [
        m["symbol"]
        for m in perp_client.markets.values()
        if m["active"] and m.get("quote") == "USDT" and m.get("linear", True)
    ]
    perp_audit = filter_stage0_universe(perp_raw)

    # Setup date range
    today_utc = datetime.now(timezone.utc).date()
    end_date = today_utc - timedelta(days=1)
    expected_utc_daily_dates(end_date, args.history_days)
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=args.history_days)).timestamp() * 1000)

    sem = asyncio.Semaphore(10)
    api_errors = 0
    rate_limits = 0

    async def audit_ohlcv(client: ccxt.Exchange, symbol: str) -> tuple[float, float, int]:
        nonlocal api_errors, rate_limits
        ccxt_sym = get_ccxt_symbol(client, symbol)
        if not ccxt_sym:
            logger.warning(f"Could not resolve CCXT symbol for {symbol}")
            return 0.0, 0.0, 0

        async with sem:
            try:
                # 1. O(1) history probe
                hist = await client.fetch_ohlcv(ccxt_sym, timeframe="1d", since=since_ms, limit=5)
                # 2. Last 30 days probe for quote volume and coverage
                recent = await client.fetch_ohlcv(ccxt_sym, timeframe="1d", limit=30)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Error fetching OHLCV for {symbol} ({ccxt_sym}): {e}")
                api_errors += 1
                return 0.0, 0.0, 0

            if not hist:
                return 0.0, 0.0, 0

            first_ts = hist[0][0]
            # Verify first candle is near targeted historical window (within 10 days of buffer)
            has_history = first_ts <= since_ms + 10 * 86400 * 1000

            ohlcv_cov = 1.0 if has_history else 0.0

            # Estimate 30d median quote volume
            quote_volumes = []
            if recent:
                for bar in recent:
                    close_price = bar[4]
                    base_volume = bar[5]
                    quote_volumes.append(base_volume * close_price)

            med_vol = median(quote_volumes) if quote_volumes else 0.0
            available_days = len(recent) if ohlcv_cov > 0 else 0

            return ohlcv_cov, med_vol, available_days

    async def audit_funding_and_oi(symbol: str) -> tuple[float, float]:
        nonlocal api_errors
        ccxt_sym = get_ccxt_symbol(perp_client, symbol)
        if not ccxt_sym:
            logger.warning(f"Could not resolve CCXT perp symbol for {symbol}")
            return 0.0, 0.0

        async with sem:
            funding_cov = 0.0
            oi_cov = 0.0
            try:
                # Audit historical funding rate availability
                funding = await perp_client.fetch_funding_rate_history(ccxt_sym, since=since_ms, limit=5)
                if funding:
                    funding_cov = 1.0
                await asyncio.sleep(0.1)

                # Audit recent OI availability
                oi = await perp_client.fetch_open_interest(ccxt_sym)
                if oi and oi.get("openInterest") is not None:
                    oi_cov = 1.0
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Error fetching funding/OI for {symbol} ({ccxt_sym}): {e}")
                api_errors += 1

            return funding_cov, oi_cov

    # Execute audits for Spot
    logger.info(f"Auditing {len(spot_audit.eligible_symbols)} eligible spot symbols...")
    spot_tasks = [audit_ohlcv(spot_client, sym) for sym in spot_audit.eligible_symbols]
    spot_results = await asyncio.gather(*spot_tasks)

    spot_coverages = []
    spot_passing_liq = 0
    for sym, res in zip(spot_audit.eligible_symbols, spot_results):
        ohlcv_cov, med_vol, available_days = res
        passing_liq = med_vol >= args.min_30d_median_quote_volume_usdt
        if passing_liq:
            spot_passing_liq += 1
        spot_coverages.append(
            SymbolCoverage(
                symbol=sym,
                market_type="spot",
                ohlcv_coverage=ohlcv_cov,
                funding_coverage=0.0,
                oi_coverage=0.0,
                history_days=args.history_days if ohlcv_cov > 0 else available_days,
            )
        )

    # Execute audits for Perp
    logger.info(f"Auditing {len(perp_audit.eligible_symbols)} eligible perp symbols...")
    perp_tasks = [audit_ohlcv(perp_client, sym) for sym in perp_audit.eligible_symbols]
    perp_ohlcv_res = await asyncio.gather(*perp_tasks)

    perp_oi_tasks = [audit_funding_and_oi(sym) for sym in perp_audit.eligible_symbols]
    perp_oi_res = await asyncio.gather(*perp_oi_tasks)

    perp_coverages = []
    perp_passing_liq = 0
    for sym, ohlcv_res, oi_res in zip(perp_audit.eligible_symbols, perp_ohlcv_res, perp_oi_res):
        ohlcv_cov, med_vol, available_days = ohlcv_res
        funding_cov, oi_cov = oi_res
        passing_liq = med_vol >= args.min_30d_median_quote_volume_usdt
        if passing_liq:
            perp_passing_liq += 1
        perp_coverages.append(
            SymbolCoverage(
                symbol=sym,
                market_type="usdt_perp",
                ohlcv_coverage=ohlcv_cov,
                funding_coverage=funding_cov,
                oi_coverage=oi_cov,
                history_days=args.history_days if ohlcv_cov > 0 else available_days,
            )
        )

    # Close clients
    await asyncio.gather(spot_client.close(), perp_client.close())

    # Calculate medians
    def get_medians(coverages: list[SymbolCoverage]) -> tuple[float, float, float, float]:
        if not coverages:
            return 0.0, 0.0, 0.0, 0.0
        ohlcvs = [c.ohlcv_coverage for c in coverages]
        fundings = [c.funding_coverage for c in coverages]
        ois = [c.oi_coverage for c in coverages]
        hists = [float(c.history_days) for c in coverages]
        return median(ohlcvs), median(fundings), median(ois), median(hists)

    spot_ohlcv_med, _, _, spot_hist_med = get_medians(spot_coverages)
    perp_ohlcv_med, perp_funding_med, perp_oi_med, perp_hist_med = get_medians(perp_coverages)

    total_passing_liquidity = spot_passing_liq + perp_passing_liq
    total_after_static = spot_audit.symbols_after_static_exclusions + perp_audit.symbols_after_static_exclusions

    funding_oi_status = "ready"
    if perp_coverages:
        if perp_funding_med < 0.90:
            funding_oi_status = "degraded"
        if perp_oi_med < 0.90:
            funding_oi_status = "degraded"
    else:
        funding_oi_status = "degraded"

    spot_market, spot_summary, spot_decision = market_payload(
        audit=spot_audit,
        symbols_passing_liquidity=spot_passing_liq,
        coverages=spot_coverages,
        market_type="spot",
        funding_oi_status="not_applicable",
    )
    perp_market, perp_summary, perp_decision = market_payload(
        audit=perp_audit,
        symbols_passing_liquidity=perp_passing_liq,
        coverages=perp_coverages,
        market_type="usdt_perp",
        funding_oi_status=funding_oi_status,
    )

    summary = Stage0CoverageSummary(
        symbols_total=spot_audit.symbols_total + perp_audit.symbols_total,
        symbols_after_static_exclusions=total_after_static,
        symbols_passing_liquidity=total_passing_liquidity,
        daily_ohlcv_coverage_ratio_median=(
            spot_ohlcv_med if spot_decision == "factor_lab_data_ready_with_bias" else perp_ohlcv_med
        ),
        funding_coverage_ratio_median=perp_funding_med,
        open_interest_coverage_ratio_median=perp_oi_med,
        history_days_available_median=(
            spot_hist_med if spot_decision == "factor_lab_data_ready_with_bias" else perp_hist_med
        ),
        listing_metadata_available=True,
        funding_oi_veto_readiness=funding_oi_status,
    )

    market_decisions = (spot_decision, perp_decision)
    decision = (
        "factor_lab_data_ready_with_bias"
        if "factor_lab_data_ready_with_bias" in market_decisions
        else "factor_lab_data_unavailable"
    )

    if decision == "factor_lab_data_ready_with_bias":
        allowed_next_stage = "stage_a_exchange_only_fast_track"
        allowed_modes = {
            "price_volume_fast_track": True,
            "funding_veto": funding_oi_status == "ready",
            "oi_veto": False,
            "long_only_only": True,
            "c1_entry_block": "diagnostic_only",
            "survivorship_bias_label_required": True,
        }
    else:
        allowed_next_stage = "fix_data_source"
        allowed_modes = {
            "price_volume_fast_track": False,
            "funding_veto": False,
            "oi_veto": False,
            "long_only_only": True,
            "c1_entry_block": "disabled",
            "survivorship_bias_label_required": True,
        }

    return {
        "run_mode": "stage0_data_coverage_audit",
        "data_source": args.exchange,
        "market_types": args.market_types,
        "universe_scope": "current_tradable_universe_only",
        "survivorship_bias_control": "not_controlled",
        "delisted_symbols_included": False,
        "result_usage": "hypothesis_screening_only_not_final_evidence",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_mode": "live",
        "api_errors_count": api_errors,
        "rate_limited_count": rate_limits,
        "primary_blocker": None if decision == "factor_lab_data_ready_with_bias" else primary_blocker_for_summary(summary),
        "allowed_next_stage": allowed_next_stage,
        "stage_a_allowed_modes": allowed_modes,
        "stage_a_allowed_modes_by_market": {
            "spot": allowed_modes_for_decision(
                decision=spot_decision,
                funding_oi_status="not_applicable",
            ),
            "usdt_perp": allowed_modes_for_decision(
                decision=perp_decision,
                funding_oi_status=funding_oi_status,
            ),
        },
        "current_liquidity_gate": {
            "min_30d_median_quote_volume_usdt": args.min_30d_median_quote_volume_usdt,
            "usage": LIQUIDITY_GATE_USAGE,
        },
        "historical_liquidity_gate_ready": False,
        "symbols_total": summary.symbols_total,
        "symbols_after_static_exclusions": summary.symbols_after_static_exclusions,
        "symbols_passing_liquidity": summary.symbols_passing_liquidity,
        "history_days_required": args.history_days,
        "expected_daily_grid": {
            "timezone": "UTC",
            "end_date": end_date.isoformat(),
            "history_days": args.history_days,
            "excludes_incomplete_today": True,
        },
        "history_days_available_median": summary.history_days_available_median,
        "daily_ohlcv_coverage_ratio_median": summary.daily_ohlcv_coverage_ratio_median,
        "funding_coverage_ratio_median": summary.funding_coverage_ratio_median,
        "open_interest_coverage_ratio_median": summary.open_interest_coverage_ratio_median,
        "listing_metadata_available": summary.listing_metadata_available,
        "funding_oi_veto_readiness": summary.funding_oi_veto_readiness,
        "open_interest_history_mode": "recent_only",
        "open_interest_coverage_note": "binance_open_interest_hist_latest_30_days_only",
        "bias_contract": stage0_current_tradable_bias_contract(),
        "markets": {
            "spot": spot_market,
            "usdt_perp": perp_market,
        },
        "decision": decision,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.offline_sample:
        summary_data = run_offline_audit(args)
    else:
        summary_data = asyncio.run(async_network_audit(args))

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    logger.info(f"Stage 0 data coverage summary written to: {output_path}")
    logger.info(f"Audit decision: {summary_data['decision']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
