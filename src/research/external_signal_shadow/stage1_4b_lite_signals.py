from __future__ import annotations

from bisect import bisect_right
from typing import Any

from configs import base
from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent

BAR_INTERVAL_MS = 15 * 60 * 1000
FOUR_HOURS_MS = 4 * 60 * 60 * 1000


def build_candidate_definitions() -> dict[str, dict[str, Any]]:
    return {
        "oi_expansion_trend_confirmation": {
            "signed_replay_only": False,
            "deleveraging_proxy_only": False,
            "long": {
                "price_4h_return_gte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT,
                "oi_4h_change_gte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT,
                "funding_abs_percentile_lt": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE,
                "signed_direction": 1,
            },
            "short": {
                "price_4h_return_lte": -base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT,
                "oi_4h_change_gte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT,
                "funding_abs_percentile_lt": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE,
                "signed_direction": -1,
            },
        },
        "funding_oi_crowding_unwind": {
            "signed_replay_only": True,
            "deleveraging_proxy_only": False,
            "long_crowded_unwind": {
                "funding_percentile_gte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE,
                "oi_4h_change_lte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT,
                "price_4h_return_lte": -0.01,
                "signed_direction": -1,
                "crowded_side": "long",
            },
            "short_crowded_unwind": {
                "funding_percentile_lte": 100 - base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE,
                "oi_4h_change_lte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT,
                "price_4h_return_gte": 0.01,
                "signed_direction": 1,
                "crowded_side": "short",
            },
        },
        "oi_contraction_after_price_flush": {
            "signed_replay_only": False,
            "deleveraging_proxy_only": True,
            "down_flush": {
                "price_4h_return_lte": -base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT,
                "oi_4h_change_lte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT,
                "signed_direction": 1,
                "liquidation_observed": False,
            },
            "up_squeeze": {
                "price_4h_return_gte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT,
                "oi_4h_change_lte": base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT,
                "signed_direction": -1,
                "liquidation_observed": False,
            },
        },
    }


def funding_state_at_event(
    rows: list[dict], event_available_at_ms: int, funding_publish_lag_ms: int
) -> dict | None:
    eligible = [
        r for r in rows
        if r.get("fundingTime") is not None
        and int(r["fundingTime"]) + funding_publish_lag_ms <= event_available_at_ms
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda x: int(x["fundingTime"]))


def funding_percentile_at_event(
    rows: list[dict], event_available_at_ms: int, funding_publish_lag_ms: int
) -> float | None:
    latest_eligible = funding_state_at_event(rows, event_available_at_ms, funding_publish_lag_ms)
    if not latest_eligible:
        return None

    latest_time = int(latest_eligible["fundingTime"])
    lookback_ms = base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PERCENTILE_LOOKBACK_DAYS * 24 * 60 * 60 * 1000
    window_start = latest_time - lookback_ms

    window_rows = [
        r for r in rows
        if r.get("fundingTime") is not None
        and window_start <= int(r["fundingTime"]) <= latest_time
    ]
    if len(window_rows) < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_FUNDING_HISTORY_POINTS:
        return None

    rates = [float(r["fundingRate"]) for r in window_rows]
    target_rate = float(latest_eligible["fundingRate"])
    less_or_equal = sum(1 for rate in rates if rate <= target_rate)
    return (less_or_equal / len(rates)) * 100.0


def oi_state_at_or_before(
    rows: list[dict], target_ms: int, max_staleness_ms: int
) -> dict | None:
    eligible = [
        r for r in rows
        if r.get("timestamp_ms") is not None
        and int(r["timestamp_ms"]) <= target_ms
    ]
    if not eligible:
        return None
    best = max(eligible, key=lambda x: int(x["timestamp_ms"]))
    if target_ms - int(best["timestamp_ms"]) > max_staleness_ms:
        return None
    return best


def price_bar_at_or_after_event(
    bars: list[dict], event_available_at_ms: int, entry_delay_bars: int
) -> dict | None:
    if entry_delay_bars < 1:
        raise ValueError("entry_delay_bars must be >= 1")
    eligible = sorted(
        [b for b in bars if b.get("bar_start_ms") is not None and int(b["bar_start_ms"]) >= event_available_at_ms],
        key=lambda x: int(x["bar_start_ms"]),
    )
    if len(eligible) < entry_delay_bars:
        return None
    return eligible[entry_delay_bars - 1]


def compute_event_available_at_ms(bar_start_ms: int) -> int:
    return bar_start_ms + BAR_INTERVAL_MS


def compute_price_4h_return_pct(price_bars: list[dict], *, end_index: int) -> float | None:
    start_index = end_index - 15
    if start_index < 0:
        return None
    start_open = float(price_bars[start_index]["open_price"])
    end_close = float(price_bars[end_index]["close_price"])
    if start_open <= 0:
        return None
    return (end_close - start_open) / start_open


def compute_oi_4h_change_pct(
    oi_rows: list[dict],
    *,
    event_available_at_ms: int,
    max_staleness_ms: int,
) -> float | None:
    current_oi_row = oi_state_at_or_before(oi_rows, event_available_at_ms, max_staleness_ms)
    past_oi_row = oi_state_at_or_before(oi_rows, event_available_at_ms - FOUR_HOURS_MS, max_staleness_ms)
    if current_oi_row is None or past_oi_row is None:
        return None
    past_oi = float(past_oi_row["sumOpenInterest"])
    if past_oi <= 0:
        return None
    return (float(current_oi_row["sumOpenInterest"]) - past_oi) / past_oi


def _compute_oi_4h_change_pct_from_index(
    oi_times: list[int],
    oi_rows: list[dict],
    *,
    event_available_at_ms: int,
    max_staleness_ms: int,
) -> float | None:
    current_oi_row = _oi_row_at_or_before(
        oi_times,
        oi_rows,
        target_ms=event_available_at_ms,
        max_staleness_ms=max_staleness_ms,
    )
    past_oi_row = _oi_row_at_or_before(
        oi_times,
        oi_rows,
        target_ms=event_available_at_ms - FOUR_HOURS_MS,
        max_staleness_ms=max_staleness_ms,
    )
    if current_oi_row is None or past_oi_row is None:
        return None
    past_oi = float(past_oi_row["sumOpenInterest"])
    if past_oi <= 0:
        return None
    return (float(current_oi_row["sumOpenInterest"]) - past_oi) / past_oi


def _build_symbol_context(rows: list[dict], ts_key: str) -> tuple[list[int], list[dict]]:
    ordered = sorted(
        [row for row in rows if row.get(ts_key) is not None],
        key=lambda x: int(x[ts_key]),
    )
    times = [int(row[ts_key]) for row in ordered]
    return times, ordered


def _eligible_funding_index(funding_times: list[int], event_available_at_ms: int, lag_ms: int) -> int:
    target = event_available_at_ms - lag_ms
    return bisect_right(funding_times, target) - 1


def _funding_percentile_from_index(
    funding_times: list[int],
    funding_rows: list[dict],
    *,
    eligible_index: int,
) -> float | None:
    if eligible_index < 0:
        return None
    latest_time = funding_times[eligible_index]
    lookback_ms = base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PERCENTILE_LOOKBACK_DAYS * 24 * 60 * 60 * 1000
    window_start = latest_time - lookback_ms
    start_index = bisect_right(funding_times, window_start - 1)
    window_rows = funding_rows[start_index : eligible_index + 1]
    if len(window_rows) < base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MIN_FUNDING_HISTORY_POINTS:
        return None
    rates = [float(row["fundingRate"]) for row in window_rows]
    target_rate = float(funding_rows[eligible_index]["fundingRate"])
    less_or_equal = sum(1 for rate in rates if rate <= target_rate)
    return (less_or_equal / len(rates)) * 100.0


def _oi_row_at_or_before(
    oi_times: list[int],
    oi_rows: list[dict],
    *,
    target_ms: int,
    max_staleness_ms: int,
) -> dict | None:
    idx = bisect_right(oi_times, target_ms) - 1
    if idx < 0:
        return None
    row = oi_rows[idx]
    if target_ms - int(row["timestamp_ms"]) > max_staleness_ms:
        return None
    return row


def detect_candidate_events(
    *,
    symbol: str,
    funding_rows: list[dict],
    oi_rows: list[dict],
    price_bars: list[dict],
) -> list[CandidateEvent]:
    sym_price_bars = sorted(
        [b for b in price_bars if b.get("symbol") == symbol],
        key=lambda x: int(x["bar_start_ms"]),
    )
    sym_funding = [f for f in funding_rows if f.get("symbol") == symbol]
    sym_oi = [o for o in oi_rows if o.get("symbol") == symbol]

    if len(sym_price_bars) < 16:
        return []

    funding_times, ordered_funding = _build_symbol_context(sym_funding, "fundingTime")
    oi_times, ordered_oi = _build_symbol_context(sym_oi, "timestamp_ms")

    potential_events: list[CandidateEvent] = []
    for idx in range(15, len(sym_price_bars)):
        bar = sym_price_bars[idx]
        bar_start_ms = int(bar["bar_start_ms"])
        event_available_at_ms = compute_event_available_at_ms(bar_start_ms)

        entry_index = idx + base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_ENTRY_DELAY_BARS
        if entry_index >= len(sym_price_bars):
            continue
        entry_bar = sym_price_bars[entry_index]

        price_4h_return = compute_price_4h_return_pct(sym_price_bars, end_index=idx)
        if price_4h_return is None:
            continue

        oi_4h_change = _compute_oi_4h_change_pct_from_index(
            oi_times,
            ordered_oi,
            event_available_at_ms=event_available_at_ms,
            max_staleness_ms=base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_MAX_OI_STALENESS_MS,
        )
        if oi_4h_change is None:
            continue

        funding_idx = _eligible_funding_index(
            funding_times,
            event_available_at_ms,
            base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_PUBLISH_LAG_MS,
        )
        funding_pct = _funding_percentile_from_index(
            funding_times,
            ordered_funding,
            eligible_index=funding_idx,
        )

        entry_bar_start_ms = int(entry_bar["bar_start_ms"])

        if funding_pct is not None and 10 < funding_pct < 90:
            if (
                price_4h_return >= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT
                and oi_4h_change >= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT
            ):
                potential_events.append(
                    CandidateEvent(
                        candidate_name="oi_expansion_trend_confirmation",
                        symbol=symbol,
                        event_time_ms=bar_start_ms,
                        event_available_at_ms=event_available_at_ms,
                        entry_bar_start_ms=entry_bar_start_ms,
                        signed_direction=1,
                        metadata={"trigger_type": "long", "funding_percentile": funding_pct},
                    )
                )
            elif (
                price_4h_return <= -base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_RETURN_4H_PCT
                and oi_4h_change >= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_EXPANSION_4H_PCT
            ):
                potential_events.append(
                    CandidateEvent(
                        candidate_name="oi_expansion_trend_confirmation",
                        symbol=symbol,
                        event_time_ms=bar_start_ms,
                        event_available_at_ms=event_available_at_ms,
                        entry_bar_start_ms=entry_bar_start_ms,
                        signed_direction=-1,
                        metadata={"trigger_type": "short", "funding_percentile": funding_pct},
                    )
                )

        if funding_pct is not None:
            if (
                funding_pct >= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE
                and oi_4h_change <= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT
                and price_4h_return <= -0.01
            ):
                potential_events.append(
                    CandidateEvent(
                        candidate_name="funding_oi_crowding_unwind",
                        symbol=symbol,
                        event_time_ms=bar_start_ms,
                        event_available_at_ms=event_available_at_ms,
                        entry_bar_start_ms=entry_bar_start_ms,
                        signed_direction=-1,
                        metadata={
                            "trigger_type": "long_crowded_unwind",
                            "crowded_side": "long",
                            "funding_percentile": funding_pct,
                            "signed_replay_only": True,
                        },
                    )
                )
            elif (
                funding_pct <= 100 - base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_FUNDING_EXTREME_PERCENTILE
                and oi_4h_change <= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT
                and price_4h_return >= 0.01
            ):
                potential_events.append(
                    CandidateEvent(
                        candidate_name="funding_oi_crowding_unwind",
                        symbol=symbol,
                        event_time_ms=bar_start_ms,
                        event_available_at_ms=event_available_at_ms,
                        entry_bar_start_ms=entry_bar_start_ms,
                        signed_direction=1,
                        metadata={
                            "trigger_type": "short_crowded_unwind",
                            "crowded_side": "short",
                            "funding_percentile": funding_pct,
                            "signed_replay_only": True,
                        },
                    )
                )

        if (
            price_4h_return <= -base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT
            and oi_4h_change <= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT
        ):
            potential_events.append(
                CandidateEvent(
                    candidate_name="oi_contraction_after_price_flush",
                    symbol=symbol,
                    event_time_ms=bar_start_ms,
                    event_available_at_ms=event_available_at_ms,
                    entry_bar_start_ms=entry_bar_start_ms,
                    signed_direction=1,
                    metadata={
                        "trigger_type": "down_flush",
                        "deleveraging_proxy_only": True,
                        "liquidation_observed": False,
                    },
                )
            )
        elif (
            price_4h_return >= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_PRICE_FLUSH_4H_PCT
            and oi_4h_change <= base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_OI_CONTRACTION_4H_PCT
        ):
            potential_events.append(
                CandidateEvent(
                    candidate_name="oi_contraction_after_price_flush",
                    symbol=symbol,
                    event_time_ms=bar_start_ms,
                    event_available_at_ms=event_available_at_ms,
                    entry_bar_start_ms=entry_bar_start_ms,
                    signed_direction=-1,
                    metadata={
                        "trigger_type": "up_squeeze",
                        "deleveraging_proxy_only": True,
                        "liquidation_observed": False,
                    },
                )
            )

    cooldown_ms = base.EXTERNAL_SIGNAL_STAGE1_4B_LITE_EVENT_COOLDOWN_HOURS * FOUR_HOURS_MS // 4
    last_triggered: dict[tuple[str, str, int], int] = {}
    filtered_events: list[CandidateEvent] = []

    potential_events.sort(key=lambda x: x.event_time_ms)
    for event in potential_events:
        key = (event.symbol, event.candidate_name, event.signed_direction)
        last_t = last_triggered.get(key)
        if last_t is None or event.event_time_ms - last_t >= cooldown_ms:
            filtered_events.append(event)
            last_triggered[key] = event.event_time_ms

    return filtered_events
