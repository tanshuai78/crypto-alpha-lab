import time

from configs import base
from src.research.external_signal_shadow.stage1_5c1_price_coverage_models import (
    PriceCoverageDecision,
)


def dedupe_kline_rows(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for r in rows:
        key = (r["symbol"], r["bar_start_ms"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def infer_market_scope(event: dict) -> dict:
    event_type = event["event_type"]
    title = event.get("title", "")

    if event_type == "futures_contract_launch":
        return {
            "market_scope_inferred": "um_futures",
            "market_scope_source": "event_type_contract_launch",
            "futures_price_required": True,
            "futures_coverage_failure_does_not_invalidate_event_source": False
        }

    # Delisting notice type
    title_lower = title.lower()
    if "futures" in title_lower or "perpetual" in title_lower:
        return {
            "market_scope_inferred": "um_futures",
            "market_scope_source": "title_pattern",
            "futures_price_required": True,
            "futures_coverage_failure_does_not_invalidate_event_source": False
        }
    elif "delist" in title_lower:
        # Standard delisting announcement on Binance usually implies spot delisting,
        # but futures might follow. Since we only check futures price, if it's spot-only delisting,
        # the futures price coverage failure shouldn't invalidate the source event itself.
        return {
            "market_scope_inferred": "spot",
            "market_scope_source": "title_pattern",
            "futures_price_required": False,
            "futures_coverage_failure_does_not_invalidate_event_source": True
        }

    return {
        "market_scope_inferred": "unknown",
        "market_scope_source": "unknown",
        "futures_price_required": False,
        "futures_coverage_failure_does_not_invalidate_event_source": True
    }


def compute_event_coverage_status(
    event: dict,
    futures_bars: list[dict],
    futures_symbol_verified: bool,
    current_time_ms: int | None = None
) -> dict:
    now_ms = current_time_ms or int(time.time() * 1000)
    symbol = event["symbol"]
    event_type = event["event_type"]
    available_at_ms = event["available_at_ms"]

    # Filter bars for this symbol
    bars = sorted([b for b in futures_bars if b["symbol"] == symbol], key=lambda x: x["bar_start_ms"])

    # Basic setup for safety outputs
    out = {
        "futures_symbol_status": "futures_symbol_currently_verified" if futures_symbol_verified else "futures_symbol_current_exchangeinfo_not_found",
        "historical_futures_existence": "verified" if (futures_symbol_verified or len(bars) > 0) else "unknown",
        "futures_kline_status": "futures_kline_not_found",
        "stage1_5c_rerun_candidate": False,
        "first_futures_bar_start_ms": 0,
        "first_futures_bar_after_available_at_ms": 0,
        "launch_price_anchor_status": "no_futures_bar_after_available_at",
        "suggested_replay_anchor_ms": 0,
        "rerun_after_ms": None,
        "required_last_bar_end_ms": 0,
        "coverage_reject_reason": None
    }

    if not futures_symbol_verified and len(bars) == 0:
        out["futures_kline_status"] = "futures_symbol_not_found"
        out["coverage_reject_reason"] = "futures_symbol_current_exchangeinfo_not_found"
        return out

    # Determine desired windows
    pre_days = base.EXTERNAL_SIGNAL_STAGE1_5C1_PRE_EVENT_HISTORY_DAYS
    buffer_days = base.EXTERNAL_SIGNAL_STAGE1_5C1_POST_EVENT_BUFFER_DAYS
    max_entry_hours = max(base.EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS)
    max_forward_hours = max(base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS)

    day_ms = 24 * 60 * 60 * 1000
    hour_ms = 60 * 60 * 1000
    interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL_MS

    required_end_ms = available_at_ms + (max_entry_hours + max_forward_hours) * hour_ms + buffer_days * day_ms
    out["required_last_bar_end_ms"] = required_end_ms

    if not bars:
        # Check maturity: if we expect bars but now is too early
        if now_ms < required_end_ms:
            out["futures_kline_status"] = "post_launch_futures_coverage_not_matured"
            out["rerun_after_ms"] = required_end_ms + interval_ms
            out["coverage_reject_reason"] = "forward_window_not_matured"
        else:
            out["futures_kline_status"] = "futures_kline_not_found"
            out["coverage_reject_reason"] = "no_klines_found"
        return out

    first_bar_start = bars[0]["bar_start_ms"]
    last_bar_end = bars[-1]["bar_end_ms"]

    # Extract bars starting after available_at_ms for anchor analysis
    post_launch_bars = [b for b in bars if b["bar_start_ms"] >= available_at_ms]
    if post_launch_bars:
        first_post_launch_bar_start = post_launch_bars[0]["bar_start_ms"]
        out["first_futures_bar_start_ms"] = first_bar_start
        out["first_futures_bar_after_available_at_ms"] = first_post_launch_bar_start
        out["launch_price_anchor_status"] = "first_futures_bar_after_available_at"
        out["suggested_replay_anchor_ms"] = max(available_at_ms, first_post_launch_bar_start)

    # Perform event-specific check
    if event_type == "futures_contract_launch":
        # Launch only requires post-launch coverage
        # Ensure we have post-launch bars
        if not post_launch_bars:
            if now_ms < required_end_ms:
                out["futures_kline_status"] = "post_launch_futures_coverage_not_matured"
                out["rerun_after_ms"] = required_end_ms + interval_ms
                out["coverage_reject_reason"] = "forward_window_not_matured"
            else:
                out["futures_kline_status"] = "futures_kline_not_found"
                out["coverage_reject_reason"] = "no_post_launch_klines_found"
            return out

        # Verify last bar end covers required_end_ms
        last_post_launch_end = post_launch_bars[-1]["bar_end_ms"]
        if last_post_launch_end >= required_end_ms - interval_ms * 2:
            out["futures_kline_status"] = "post_launch_futures_coverage_pass"
            out["stage1_5c_rerun_candidate"] = True
        else:
            # Check maturity
            if now_ms < required_end_ms:
                out["futures_kline_status"] = "post_launch_futures_coverage_not_matured"
                out["rerun_after_ms"] = required_end_ms + interval_ms
                out["coverage_reject_reason"] = "forward_window_not_matured"
            else:
                out["futures_kline_status"] = "futures_kline_partial"
                out["coverage_reject_reason"] = "post_launch_coverage_incomplete"

    elif event_type == "exchange_delisting_notice":
        # Delisting requires 30d pre-event history + post-event forward window
        # Check pre-event history start time
        required_pre_start_ms = available_at_ms - pre_days * day_ms
        # We need a bar starting at or before required_pre_start_ms + 1 hour buffer
        has_pre_history = first_bar_start <= required_pre_start_ms + hour_ms

        if not has_pre_history:
            out["futures_kline_status"] = "futures_kline_partial"
            out["coverage_reject_reason"] = "pre_event_30d_history_missing"
            return out

        # Check post-event forward window coverage
        if last_bar_end >= required_end_ms - interval_ms * 2:
            out["futures_kline_status"] = "futures_pre_event_coverage_pass"
            out["stage1_5c_rerun_candidate"] = True
        else:
            if now_ms < required_end_ms:
                out["futures_kline_status"] = "future_bar_request_truncated"
                out["rerun_after_ms"] = required_end_ms + interval_ms
                out["coverage_reject_reason"] = "forward_window_not_matured"
            else:
                out["futures_kline_status"] = "futures_kline_partial"
                out["coverage_reject_reason"] = "post_event_coverage_incomplete"

    return out


def build_event_coverage_report(
    event: dict,
    futures_bars: list[dict],
    spot_bars: list[dict],
    futures_symbol_verified: bool,
    spot_symbol_verified: bool,
    current_time_ms: int | None = None
) -> dict:
    scope_info = infer_market_scope(event)
    status_info = compute_event_coverage_status(event, futures_bars, futures_symbol_verified, current_time_ms)

    # Spot proxy status
    symbol = event["symbol"]
    spot_symbol_bars = [b for b in spot_bars if b["symbol"] == symbol]
    if spot_symbol_verified:
        if spot_symbol_bars:
            spot_proxy_status = "spot_proxy_available_report_only"
        else:
            spot_proxy_status = "spot_symbol_not_found"
    else:
        spot_proxy_status = "spot_symbol_not_found" if spot_bars else "not_requested"

    report = {
        "symbol_event_id": event["symbol_event_id"],
        "event_type": event["event_type"],
        "symbol": symbol,
        "futures_symbol_status": status_info["futures_symbol_status"],
        "historical_futures_existence": status_info["historical_futures_existence"],
        "futures_kline_status": status_info["futures_kline_status"],
        "spot_proxy_status": spot_proxy_status,
        "replay_price_source_allowed": "futures_only" if status_info["stage1_5c_rerun_candidate"] else "none",
        "spot_proxy_replay_allowed": False,
        "stage1_5c_rerun_candidate": status_info["stage1_5c_rerun_candidate"],
        "coverage_reject_reason": status_info["coverage_reject_reason"],
        "event_day": time.strftime("%Y-%m-%d", time.gmtime(event["available_at_ms"] / 1000)),

        # Inferred scope fields
        "market_scope_inferred": scope_info["market_scope_inferred"],
        "market_scope_source": scope_info["market_scope_source"],
        "futures_price_required": scope_info["futures_price_required"],
        "futures_coverage_failure_does_not_invalidate_event_source": scope_info["futures_coverage_failure_does_not_invalidate_event_source"],

        # Launch anchors
        "first_futures_bar_start_ms": status_info["first_futures_bar_start_ms"],
        "first_futures_bar_after_available_at_ms": status_info["first_futures_bar_after_available_at_ms"],
        "launch_price_anchor_status": status_info["launch_price_anchor_status"],
        "suggested_replay_anchor_ms": status_info["suggested_replay_anchor_ms"],
        "rerun_after_ms": status_info["rerun_after_ms"]
    }

    # Override for spot-only delisting:
    # If the delisting is spot-only and futures price isn't required,
    # the failure of futures coverage shouldn't count as a blocker for rerun candidate
    # BUT since we only support futures_only replay, it still cannot be rerun candidate without futures price.
    # The plan says: "stage1_5c_rerun_candidate = false unless a later plan designs spot replay".
    # So we keep stage1_5c_rerun_candidate = False, but we distinguish it in the blockers list.
    if report["market_scope_inferred"] in {"spot", "unknown"}:
        report["stage1_5c_rerun_candidate"] = False
        report["replay_price_source_allowed"] = "none"

    return report


def summarize_coverage_reports(reports: list[dict]) -> dict:
    total_events = len(reports)
    pass_events = [r for r in reports if r["stage1_5c_rerun_candidate"]]
    pass_count = len(pass_events)

    unique_symbols = len(set(r["symbol"] for r in reports))
    pass_symbols = len(set(r["symbol"] for r in pass_events))

    spot_proxy_count = len([r for r in reports if r["spot_proxy_status"] == "spot_proxy_available_report_only"])
    not_matured_count = len([r for r in reports if "not_matured" in str(r["futures_kline_status"])])

    # Count distinct days in UTC
    pass_days = len(set(r["event_day"] for r in pass_events))

    # Evaluate decision
    min_count = base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_COUNT
    min_days = base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_EVENT_DAYS
    min_symbols = base.EXTERNAL_SIGNAL_STAGE1_5C1_MIN_RERUN_SYMBOLS

    decision = PriceCoverageDecision.FAILED.value
    blockers = []

    if total_events == 0:
        decision = PriceCoverageDecision.INVALID.value
        blockers.append("no_events_found_in_input")
    else:
        if pass_count >= min_count and pass_days >= min_days and pass_symbols >= min_symbols:
            decision = PriceCoverageDecision.READY.value
        elif pass_count > 0:
            decision = PriceCoverageDecision.SPARSE.value
            if pass_count < min_count:
                blockers.append("futures_coverage_event_count_insufficient")
            if pass_days < min_days:
                blockers.append("futures_coverage_days_insufficient")
            if pass_symbols < min_symbols:
                blockers.append("futures_coverage_symbols_insufficient")
        else:
            decision = PriceCoverageDecision.FAILED.value
            blockers.append("zero_futures_price_coverage_pass")

    return {
        "decision": decision,
        "stage1_5b_symbol_events": total_events,
        "futures_coverage_pass_event_count": pass_count,
        "futures_coverage_pass_event_days": pass_days,
        "futures_coverage_pass_symbols": pass_symbols,
        "spot_proxy_available_event_count": spot_proxy_count,
        "not_matured_event_count": not_matured_count,
        "unique_symbol_count": unique_symbols,
        "blockers": blockers,
        "api_key_used": False,
        "private_endpoint_used": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False
    }


def filter_futures_coverage_pass_events(events: list[dict], reports: list[dict]) -> list[dict]:
    report_by_id = {
        r["symbol_event_id"]: r
        for r in reports
        if r["stage1_5c_rerun_candidate"] and r["replay_price_source_allowed"] == "futures_only"
    }
    rows = []
    coverage_keys = (
        "stage1_5c_rerun_candidate",
        "replay_price_source_allowed",
        "futures_kline_status",
        "first_futures_bar_start_ms",
        "first_futures_bar_after_available_at_ms",
        "launch_price_anchor_status",
        "suggested_replay_anchor_ms",
        "market_scope_inferred",
    )
    for event in events:
        report = report_by_id.get(event["symbol_event_id"])
        if not report:
            continue
        row = dict(event)
        for key in coverage_keys:
            row[key] = report.get(key)
        rows.append(row)
    return rows
