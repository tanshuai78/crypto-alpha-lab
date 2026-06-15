#!/usr/bin/env python3
"""
scripts/external_signal_shadow/review_stage1_4a_derivatives_stress_data_feasibility.py
"""

import argparse
import json
import sys
from pathlib import Path

from configs.base import (
    EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN,
    EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO,
    EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO,
)


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Stage 1.4A Derivatives Stress Data Feasibility Review Generator"
    )
    parser.add_argument(
        "--summary",
        type=str,
        required=True,
        help="Path to the feasibility summary JSON file.",
    )
    parser.add_argument(
        "--output-review",
        type=str,
        required=True,
        help="Output path for the Markdown review document.",
    )
    return parser.parse_args(args)


def generate_markdown_review(summary: dict) -> str:
    outcome = summary.get("outcome", "stage1_4_data_unavailable")
    primary_blocker = summary.get("primary_blocker")
    res_valid = summary.get("research_result_valid", False)
    fixture_run = summary.get("fixture_run", False)

    # Convert res_valid and fixture_run to strings for rendering
    res_valid_str = "VALID" if res_valid else "INVALID (Fixture or Network Error)"
    fixture_str = "YES (Smoke Test Only)" if fixture_run else "NO (Real Data Run)"

    symbol_audits = summary.get("symbol_audits", {})
    symbols = list(symbol_audits.keys())
    symbol_count = len(symbols)

    # Aggregate per-source metrics across all audited symbols
    sources = {
        "funding": {
            "name": "Binance Funding Rate (/fapi/v1/fundingRate)",
            "history_days": [],
            "time_cov": [],
            "field_cov": [],
            "proxy": False,
            "quality": "public_settled_funding_history",
            "blocker": "no_audit_data",
            "usable": False,
        },
        "oi": {
            "name": "Binance Open Interest (/futures/data/openInterestHist)",
            "history_days": [],
            "time_cov": [],
            "field_cov": [],
            "proxy": False,
            "quality": "public_history",
            "blocker": "no_audit_data",
            "usable": False,
        },
        "liquidation": {
            "name": "Binance Liquidations (Vision Snapshots / Force Orders)",
            "history_days": [],
            "time_cov": [],
            "field_cov": [],
            "proxy": False,
            "quality": "force_order_archive",
            "blocker": "no_audit_data",
            "usable": False,
        },
        "price": {
            "name": "Binance Futures Prices (/fapi/v1/klines)",
            "history_days": [],
            "time_cov": [],
            "field_cov": [],
            "proxy": False,
            "quality": "futures_klines",
            "blocker": "no_audit_data",
            "usable": False,
        },
    }

    for sym, audits in symbol_audits.items():
        # Funding rate
        f = audits.get("funding", {})
        if f:
            sources["funding"]["usable"] = True
            sources["funding"]["blocker"] = None
            sources["funding"]["history_days"].append(f.get("funding_history_days", 0.0))
            sources["funding"]["time_cov"].append(f.get("funding_settlement_coverage_ratio", 0.0))
            sources["funding"]["field_cov"].append(f.get("funding_field_coverage_ratio", 0.0))
            if not f.get("usable", False):
                sources["funding"]["usable"] = False
                sources["funding"]["blocker"] = "coverage_or_history_insufficient"

        # Open Interest
        o = audits.get("oi", {})
        if o:
            sources["oi"]["usable"] = True
            sources["oi"]["blocker"] = None
            sources["oi"]["history_days"].append(o.get("oi_history_days", 0.0))
            sources["oi"]["time_cov"].append(o.get("oi_time_coverage_ratio", 0.0))
            sources["oi"]["field_cov"].append(o.get("oi_field_coverage_ratio", 0.0))
            if o.get("source_quality"):
                sources["oi"]["quality"] = o.get("source_quality")
            if not o.get("usable", False):
                sources["oi"]["usable"] = False
                sources["oi"]["blocker"] = "oi_blocks_full_composite"

        # Liquidations
        liq = audits.get("liquidation", {})
        if liq:
            sources["liquidation"]["usable"] = True
            sources["liquidation"]["blocker"] = None
            sources["liquidation"]["history_days"].append(liq.get("liquidation_history_days", 0.0))
            sources["liquidation"]["time_cov"].append(liq.get("liquidation_time_coverage_ratio", 0.0))
            sources["liquidation"]["field_cov"].append(liq.get("liquidation_field_coverage_ratio", 0.0))
            sources["liquidation"]["proxy"] = liq.get("cm_to_um_proxy_used", False)
            sources["liquidation"]["notional_conversion_quality"] = liq.get("notional_conversion_quality", "unavailable")
            if liq.get("liquidation_source_quality"):
                sources["liquidation"]["quality"] = liq.get("liquidation_source_quality")
            if not liq.get("liquidation_proxy_accepted_for_full_replay", False) or liq.get("notional_conversion_quality") != "verified_by_sample":
                sources["liquidation"]["usable"] = False
                sources["liquidation"]["blocker"] = "cm_proxy_unaccepted_or_notional_unverified"

        # Prices
        p = audits.get("price", {})
        if p:
            sources["price"]["usable"] = True
            sources["price"]["blocker"] = None
            sources["price"]["history_days"].append(p.get("price_history_days", 0.0))
            sources["price"]["time_cov"].append(p.get("time_coverage_ratio", 0.0))
            sources["price"]["field_cov"].append(p.get("price_bar_coverage_ratio", 0.0))
            sources["price"]["proxy"] = p.get("price_venue_proxy_used", False)
            if p.get("price_source"):
                sources["price"]["quality"] = p.get("price_source")

    # Helper to calculate min or default
    def get_min(lst, default=0.0):
        return min(lst) if lst else default

    def bounded_ratio(value: float) -> float:
        return max(0.0, min(1.0, value))

    liquidation_history_days = get_min(sources["liquidation"]["history_days"])
    liquidation_time_coverage = get_min(sources["liquidation"]["time_cov"])
    liquidation_field_coverage = get_min(sources["liquidation"]["field_cov"])
    if liquidation_history_days < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
        sources["liquidation"]["usable"] = False
        sources["liquidation"]["blocker"] = "liquidation_history_insufficient"
    elif liquidation_time_coverage < EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_TIME_COVERAGE_MIN_RATIO:
        sources["liquidation"]["usable"] = False
        sources["liquidation"]["blocker"] = "liquidation_time_coverage_insufficient"
    elif liquidation_field_coverage < EXTERNAL_SIGNAL_STAGE1_4_LIQUIDATION_FIELD_COVERAGE_MIN_RATIO:
        sources["liquidation"]["usable"] = False
        sources["liquidation"]["blocker"] = "liquidation_field_coverage_insufficient"

    # Build Markdown
    md = []
    md.append("# Stage 1.4A Derivatives Stress Data Feasibility Audit Review")
    md.append("")
    md.append("## 1. Decision Summary")
    md.append(f"- **Final Outcome:** `{outcome}`")
    md.append(f"- **Primary Blocker:** `{primary_blocker}`")
    md.append(f"- **Research Result Valid:** `{res_valid_str}`")
    md.append(f"- **Fixture Smoke Run:** `{fixture_str}`")
    md.append("")

    if fixture_run:
        md.append("> [!IMPORTANT]")
        md.append("> **本 artifact 是 fixture smoke，不证明真实 derivatives stress data availability。**")
        md.append("")

    md.append("## 2. Safety and Scope Boundaries")
    md.append("- **Live Trading Master Switch:** `RISK_LIVE_TRADING_ENABLED` is confirmed `False`.")
    md.append("- **Credentials check:** No private API keys or environment variables were loaded during this execution.")
    md.append("- **Execution scope:** No paper trading, live order placement, or alpha estimation was performed.")
    md.append("")

    md.append("## 3. Per-Source Audit Table")
    md.append("| Source | History (Days) | Time Coverage | Field Coverage | Symbol Count | Quality | Proxy Used | Blocker | Usable for 1.4B |")
    md.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    for key, data in sources.items():
        hist = f"{get_min(data['history_days']):.2f}d"
        t_cov = f"{bounded_ratio(get_min(data['time_cov'])) * 100:.1f}%"
        f_cov = f"{bounded_ratio(get_min(data['field_cov'])) * 100:.1f}%"
        sym_cnt = str(symbol_count)
        proxy = "Yes" if data["proxy"] else "No"
        blocker_str = data["blocker"] if data["blocker"] else "None"
        usable_str = "Yes" if data["usable"] else "No"

        row = (
            f"| {data['name']} | {hist} | {t_cov} | {f_cov} | {sym_cnt} | "
            f"{data['quality']} | {proxy} | {blocker_str} | {usable_str} |"
        )
        md.append(row)

    md.append("")
    md.append("## 4. Per-Symbol Blocker Table")
    md.append("| Symbol | Funding Days | OI Days | Price Days | Liquidation Days | Blockers | Usable |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")

    for sym in sorted(symbol_audits.keys()):
        audits = symbol_audits[sym]
        funding = audits.get("funding", {})
        oi = audits.get("oi", {})
        liq = audits.get("liquidation", {})
        price = audits.get("price", {})

        funding_days = funding.get("funding_history_days", 0.0)
        oi_days = oi.get("oi_history_days", 0.0)
        price_days = price.get("price_history_days", 0.0)
        liq_days = liq.get("liquidation_history_days", 0.0)

        symbol_blockers = []
        if not funding or funding_days < 90.0 or not funding.get("usable", False):
            symbol_blockers.append("funding_insufficient")
        if not oi or oi_days < 90.0 or not oi.get("usable", False) or oi.get("oi_blocks_full_composite", False):
            symbol_blockers.append("oi_insufficient")
        if not price or price_days < 90.0:
            symbol_blockers.append("price_insufficient")
        if not liq or liq_days < 90.0 or not liq.get("liquidation_proxy_accepted_for_full_replay", False) or liq.get("notional_conversion_quality") != "verified_by_sample":
            symbol_blockers.append("liquidation_insufficient")

        if symbol_blockers:
            blockers_str = ", ".join(symbol_blockers)
            usable_str = "No"
        else:
            blockers_str = "None"
            usable_str = "Yes"

        md.append(
            f"| {sym} | {funding_days:.2f}d | {oi_days:.2f}d | {price_days:.2f}d | {liq_days:.2f}d | {blockers_str} | {usable_str} |"
        )

    md.append("")
    md.append("## 5. Source Semantics Notes")

    # 1. Funding Rates
    md.append("### 5.1 Funding Rates")
    min_funding_days = get_min(sources["funding"]["history_days"])
    if min_funding_days >= 90.0:
        md.append(f"- **Status:** Pass. Min history of {min_funding_days:.1f} days satisfies the 90d requirement.")
    else:
        md.append(f"- **Status:** Block. Min history of {min_funding_days:.1f} days is below the 90d requirement.")
    md.append("- **Notes:** Checked for 8h settlement cadence and publishing lags.")
    md.append("")

    # 2. Open Interest
    md.append("### 5.2 Open Interest")
    min_oi_days = get_min(sources["oi"]["history_days"])
    min_oi_time_cov = get_min(sources["oi"]["time_cov"])
    if min_oi_days < 90.0 or min_oi_time_cov < 0.90:
        md.append("- **Status:** Block. Open Interest blocks full composite replay due to insufficient history or time continuity gaps.")
    else:
        md.append("- **Status:** Pass. Open interest satisfies 90d history and 90% time continuity.")
    md.append("- **Notes:** Continuity checks verify time-series buckets are not missing.")
    md.append("")

    # 3. Liquidations
    md.append("### 5.3 Liquidations")
    min_liquidation_days = get_min(sources["liquidation"]["history_days"])
    if not sources["liquidation"]["history_days"]:
        md.append("- **Status:** Block. No liquidation audit data was supplied in this run.")
    elif min_liquidation_days < EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN:
        md.append(
            f"- **Status:** Block. Min liquidation history is {min_liquidation_days:.1f} days, "
            f"below the {EXTERNAL_SIGNAL_STAGE1_4_HISTORY_DAYS_MIN}d requirement."
        )
    elif sources["liquidation"]["proxy"]:
        md.append("- **Status:** Block (unless accepted). Binance Vision CM liquidation snapshots are used as a proxy, which does not constitute a complete USD-M tape.")
    else:
        md.append("- **Status:** Pass (Exact). Using exact force order archives.")
    if sources["liquidation"]["proxy"]:
        md.append("- **Proxy Note:** Binance Vision CM liquidation snapshot proxy does not constitute a complete USD-M tape.")
    md.append("- **Notes:** Notional conversion must be verified by sample to unlock full feasibility.")
    md.append(f"- **Notional Conversion Quality:** `{sources['liquidation'].get('notional_conversion_quality', 'unavailable')}`")
    md.append("")

    # 4. Futures Prices
    md.append("### 5.4 Futures Prices")
    min_price_days = get_min(sources["price"]["history_days"])
    if min_price_days >= 90.0:
        md.append(f"- **Status:** Pass. Min price history is {min_price_days:.1f} days.")
    else:
        md.append("- **Status:** Block. Price history is below 90d.")
    md.append("")

    md.append("## 6. Preview Density Explanation")
    preview_metrics = summary.get("preview_metrics", {})
    windows = preview_metrics.get("composite_overlap_window_count", 0)
    days = preview_metrics.get("composite_overlap_event_days", 0)
    md.append(f"- **Composite Overlap Windows:** {windows}")
    md.append(f"- **Distinct Event Days:** {days}")
    md.append("- **Notes:** Preview density represents raw event overlap and is **NOT** a backtest or alpha score.")
    md.append("")

    md.append("## 7. Next Action Recommendation")
    if outcome == "stage1_4_data_feasible":
        md.append("- Proceed to **Stage 1.4B Candidate Replay** design.")
    elif outcome == "stage1_4_data_degraded":
        md.append("- Continue in **degraded mode** using proxies/archives, or gather longer history before proceeding.")
    else:
        md.append("- Halt research on derivatives stress alpha due to critical data unavailability.")

    return "\n".join(md) + "\n"


def main(args=None):
    parsed = parse_args(args)

    summary_path = Path(parsed.summary)
    if not summary_path.is_file():
        print(f"ERROR: summary file not found: {summary_path}", file=sys.stderr)
        return 1

    try:
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
    except Exception as e:
        print(f"ERROR: failed to parse summary JSON: {e}", file=sys.stderr)
        return 1

    markdown_report = generate_markdown_review(summary)

    output_path = Path(parsed.output_review)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        print(f"Feasibility review Markdown written to {output_path}")
        return 0
    except Exception as e:
        print(f"ERROR: failed to write Markdown review: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
