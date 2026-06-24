from configs import base
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
)


def event_direction_modes(event_type: str) -> list[tuple[str, int]]:
    if event_type == "exchange_delisting_notice":
        return [("delisting_avoid_long_or_signed_short_diagnostic", -1)]
    elif event_type == "futures_contract_launch":
        return [
            ("futures_launch_long_attention_diagnostic", 1),
            ("futures_launch_short_access_diagnostic", -1),
        ]
    return []


def allowed_filter_groups() -> list[str]:
    return list(base.EXTERNAL_SIGNAL_STAGE1_5C_FILTER_GROUPS)


def apply_event_cooldown(events: list[dict], cooldown_hours: int = 24) -> list[dict]:
    # Sort events by event_time_ms
    sorted_events = sorted(events, key=lambda x: x["event_time_ms"])
    kept = []
    cooldown_ms = cooldown_hours * 3600_000

    for ev in sorted_events:
        # Check if there is an event already kept with same symbol, event_type, signed_mode within cooldown
        is_cooldown = False
        symbol = ev.get("symbol")
        etype = ev.get("event_type")
        mode = ev.get("signed_mode")
        t_ms = ev.get("event_time_ms")

        for k_ev in kept:
            if (
                k_ev.get("symbol") == symbol
                and k_ev.get("event_type") == etype
                and k_ev.get("signed_mode") == mode
                and abs(t_ms - k_ev.get("event_time_ms")) < cooldown_ms
            ):
                is_cooldown = True
                break

        if not is_cooldown:
            kept.append(ev)

    return kept


def build_replay_candidates(
    events: list[dict],
    coverage_reports: dict,
    entry_delay_hours: int
) -> list[ExternalCatalystReplayCandidate]:
    res = []
    for ev in events:
        key = (ev["symbol_event_id"], entry_delay_hours)
        report = coverage_reports.get(key)
        if not report:
            continue
        if not report.get("price_coverage_gate_passed", False):
            continue
        if not report.get("candidate_allowed_for_close_price_replay", False):
            continue
        modes = event_direction_modes(ev["event_type"])
        for mode_name, direction in modes:
            res.append(ExternalCatalystReplayCandidate(
                symbol_event_id=ev["symbol_event_id"],
                event_type=ev["event_type"],
                signed_mode=mode_name,
                signed_direction=direction,
                symbol=ev["symbol"],
                event_time_ms=ev["event_time_ms"],
                available_at_ms=ev["available_at_ms"],
                entry_delay_hours=entry_delay_hours,
                entry_candidate_time_ms=report.get("entry_candidate_time_ms", 0),
                entry_bar_start_ms=report.get("entry_bar_start_ms", 0),
                entry_price=report.get("entry_price", 0.0),
                price_history_coverage_verified=report.get("price_history_coverage_verified", False),
                market_pair_existence_verified=report.get("market_pair_existence_verified", False),
                liquidity_proxy_verified=report.get("liquidity_proxy_pass", False),
                replay_allowed=report.get("price_coverage_gate_passed", False),
                paper_trading_allowed=False,
                live_trading_allowed=False,
                short_execution_intent_allowed=False,
                execution_engine_allowed=False,
            ))
    return res
