from __future__ import annotations

from bisect import bisect_right
from collections import Counter, deque
from statistics import median

from configs import base
from research.external_signal_shadow.stage1_3_baseline import run_random_baseline_trials
from research.external_signal_shadow.stage1_3_candidates import (
    CandidateEvent,
    detect_price_move_15m_baseline,
    detect_relative_strength_vs_btc,
    detect_volume_confirmed_relative_strength,
    detect_volume_spike_1h,
)
from research.external_signal_shadow.stage1_3_metrics import (
    compute_forward_metrics_from_entry_index,
)
from research.external_signal_shadow.stage1_3_models import (
    HistoricalBar,
    compute_bar_coverage,
    find_duplicate_bar_starts,
    group_bars_by_symbol,
)
from research.external_signal_shadow.stage1_3_replay import (
    historical_available_at_ms,
)
from research.external_signal_shadow.stage1_3_summary import decide_stage1_3_summary

MS_15M = 15 * 60 * 1000
MS_ROLLING_WINDOW = base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_DAYS * 24 * 3_600_000



def _utc_hour(ts_ms: int) -> int:
    return (ts_ms // 3_600_000) % 24


def _safe_median(values: list[float]) -> float:
    return median(values) if values else 0.0


def _safe_p05(values: list[float]) -> float:
    if not values:
        return 0.0
    return sorted(values)[max(int(len(values) * 0.05) - 1, 0)]


def _build_forward_metric_cache(
    grouped: dict[str, list[HistoricalBar]],
) -> tuple[dict[str, list[int]], dict[str, dict[int, dict[int, dict]]]]:
    eligible_event_times_by_symbol: dict[str, list[int]] = {}
    metrics_by_symbol_direction: dict[str, dict[int, dict[int, dict]]] = {}
    entry_delay = base.EXTERNAL_SIGNAL_STAGE1_3_ENTRY_DELAY_BARS
    for symbol, s_bars in grouped.items():
        starts = [bar.bar_start_ms for bar in s_bars]
        eligible_event_times_by_symbol[symbol] = []
        metrics_by_symbol_direction[symbol] = {1: {}, -1: {}}
        for idx in range(3, len(s_bars)):
            event_time_ms = historical_available_at_ms(
                s_bars[idx],
                configured_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS,
            )
            entry_index = bisect_right(starts, event_time_ms) + entry_delay - 1
            long_metrics = compute_forward_metrics_from_entry_index(
                s_bars,
                entry_index=entry_index,
                cost_round_trip_bps=50.0,
                signed_direction=1,
            )
            short_metrics = compute_forward_metrics_from_entry_index(
                s_bars,
                entry_index=entry_index,
                cost_round_trip_bps=50.0,
                signed_direction=-1,
            )
            metrics_by_symbol_direction[symbol][1][event_time_ms] = long_metrics
            metrics_by_symbol_direction[symbol][-1][event_time_ms] = short_metrics
            if long_metrics.get("status") == "success":
                eligible_event_times_by_symbol[symbol].append(event_time_ms)
    return eligible_event_times_by_symbol, metrics_by_symbol_direction


def run_stage1_3_candidate_discovery(
    bars: list[HistoricalBar],
    *,
    historical_venue: str,
    venue_proxy_used: bool,
    fixture_run: bool = False,
) -> dict:
    interval_ms = base.EXTERNAL_SIGNAL_STAGE1_3_SNAPSHOT_INTERVAL_MINUTES * 60 * 1000
    coverage = compute_bar_coverage(bars, interval_ms=interval_ms)
    grouped = group_bars_by_symbol(bars)
    bar_count_by_symbol = Counter({symbol: len(items) for symbol, items in grouped.items()})

    # 8.8 Data coverage gate
    required_symbols = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"}
    missing_required_symbols = sorted(required_symbols - set(grouped))
    if missing_required_symbols:
        return {
            "decision": "stage1_3_candidate_signal_discovery_failed",
            "primary_blocker": "missing_required_symbols",
            "next_action": "fix_data_or_stop",
            "missing_required_symbols": missing_required_symbols,
            "fixture_run": fixture_run,
            "research_result_valid": False,
            "bar_coverage_ratio_by_symbol": coverage,
            "symbol_bar_count": dict(bar_count_by_symbol),
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }

    duplicate_bar_starts = find_duplicate_bar_starts(bars)
    if duplicate_bar_starts:
        return {
            "decision": "stage1_3_candidate_signal_discovery_failed",
            "primary_blocker": "duplicate_bar_start_ms",
            "next_action": "fix_data_or_stop",
            "duplicate_bar_start_ms_by_symbol": duplicate_bar_starts,
            "fixture_run": fixture_run,
            "research_result_valid": False,
            "bar_coverage_ratio_by_symbol": coverage,
            "symbol_bar_count": dict(bar_count_by_symbol),
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }

    coverage_failures = {
        symbol: coverage.get(symbol, 0.0)
        for symbol in required_symbols
        if coverage.get(symbol, 0.0) < base.EXTERNAL_SIGNAL_STAGE1_3_MIN_BAR_COVERAGE_RATIO
    }
    if coverage_failures:
        return {
            "decision": "stage1_3_candidate_signal_discovery_failed",
            "primary_blocker": "bar_coverage_below_min",
            "next_action": "fix_data_or_stop",
            "fixture_run": fixture_run,
            "research_result_valid": False,
            "bar_coverage_ratio_by_symbol": coverage,
            "symbol_bar_count": dict(bar_count_by_symbol),
            "alpha_interpretation_allowed": False,
            "collector_expansion_allowed": False,
            "live_shadow_required_now": False,
        }

    # Calculate history days
    all_starts = [b.bar_start_ms for b in bars]
    all_ends = [b.bar_end_ms for b in bars]
    if all_starts and all_ends:
        history_days = (max(all_ends) - min(all_starts)) / 86_400_000.0
    else:
        history_days = 0.0

    # 1h returns and volumes precomputation for all symbols to speed up
    btc_returns: dict[int, float] = {}
    if "BTCUSDT" in grouped:
        btc_bars = grouped["BTCUSDT"]
        for idx in range(3, len(btc_bars)):
            w = btc_bars[idx - 3 : idx + 1]
            if w[0].open_price > 0:
                btc_returns[w[-1].bar_end_ms] = w[-1].close_price / w[0].open_price - 1.0

    # We will collect events here
    detected_events: dict[str, list[CandidateEvent]] = {
        "volume_spike_1h": [],
        "relative_strength_vs_btc": [],
        "volume_confirmed_relative_strength": [],
        "price_move_15m": [],
        "cross_symbol_rotation": [],  # stub only
    }

    rolling_baseline_insufficient_count = 0

    # Generate candidates per symbol
    for symbol, s_bars in grouped.items():
        # Precompute window details for this symbol
        # windows_info maps index to its 1h volume, return, hour, end_ms
        windows_info = []
        for idx in range(3, len(s_bars)):
            w = s_bars[idx - 3 : idx + 1]
            w_end_ms = w[-1].bar_end_ms
            w_vol = sum(b.quote_volume for b in w)
            w_ret = w[-1].close_price / w[0].open_price - 1.0 if w[0].open_price > 0 else 0.0
            windows_info.append({
                "index": idx,
                "end_ms": w_end_ms,
                "volume": w_vol,
                "return": w_ret,
                "hour": _utc_hour(w_end_ms)
            })

        # Precompute 15m returns
        s_15m_returns = []
        for idx in range(len(s_bars)):
            b = s_bars[idx]
            s_15m_returns.append(b.close_price / b.open_price - 1.0 if b.open_price > 0 else 0.0)

        volume_history_by_hour: dict[int, deque[tuple[int, float]]] = {}
        spread_history: deque[tuple[int, float]] = deque()

        # Replay loop for 1h window based candidates
        for info_idx, info in enumerate(windows_info):
            idx = info["index"]
            event_time_ms = historical_available_at_ms(s_bars[idx], configured_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS)

            # Same-hour historical volumes in last 7 days
            hour_history = volume_history_by_hour.setdefault(info["hour"], deque())
            while hour_history and info["end_ms"] - hour_history[0][0] > MS_ROLLING_WINDOW:
                hour_history.popleft()
            historical_volumes = [item[1] for item in hour_history]

            # 1. detect volume_spike_1h
            vol_event = None
            if len(historical_volumes) >= base.EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES:
                vol_event = detect_volume_spike_1h(
                    symbol=symbol,
                    current_1h_quote_volume=info["volume"],
                    same_hour_historical_volumes=historical_volumes,
                    event_time_ms=event_time_ms,
                    threshold=base.EXTERNAL_SIGNAL_STAGE1_3_VOLUME_SPIKE_THRESHOLD,
                    min_samples=base.EXTERNAL_SIGNAL_STAGE1_3_SAME_HOUR_MIN_SAMPLES,
                )
                if vol_event:
                    detected_events["volume_spike_1h"].append(vol_event)
            else:
                rolling_baseline_insufficient_count += 1

            # 2. detect relative_strength_vs_btc
            rel_event = None
            if symbol != "BTCUSDT":
                # Historical spread returns in last 7 days
                while spread_history and info["end_ms"] - spread_history[0][0] > MS_ROLLING_WINDOW:
                    spread_history.popleft()
                historical_spreads = [item[1] for item in spread_history]

                btc_ret = btc_returns.get(info["end_ms"])
                if btc_ret is not None and len(historical_spreads) >= base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES:
                    rel_event = detect_relative_strength_vs_btc(
                        symbol=symbol,
                        alt_1h_return=info["return"],
                        btc_1h_return=btc_ret,
                        historical_spread_returns=historical_spreads,
                        event_time_ms=event_time_ms,
                        z_threshold=base.EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD,
                        min_samples=base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES,
                    )
                    if rel_event:
                        detected_events["relative_strength_vs_btc"].append(rel_event)
                else:
                    rolling_baseline_insufficient_count += 1

            # 3. detect volume_confirmed_relative_strength
            if vol_event and rel_event:
                confirmed_event = detect_volume_confirmed_relative_strength(vol_event, rel_event)
                if confirmed_event:
                    detected_events["volume_confirmed_relative_strength"].append(confirmed_event)

            hour_history.append((info["end_ms"], info["volume"]))
            current_btc_ret = btc_returns.get(info["end_ms"])
            if symbol != "BTCUSDT" and current_btc_ret is not None:
                spread_history.append((info["end_ms"], info["return"] - current_btc_ret))

        # Replay loop for 15m price move
        return_history: deque[tuple[int, float]] = deque()
        for idx in range(len(s_bars)):
            b = s_bars[idx]
            event_time_ms = historical_available_at_ms(b, configured_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_3_CONFIGURED_DATA_LAG_MS)

            # Historical 15m returns in last 7 days
            while return_history and b.bar_start_ms - return_history[0][0] > MS_ROLLING_WINDOW:
                return_history.popleft()
            historical_15m = [item[1] for item in return_history]

            if len(historical_15m) >= base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES:
                p_event = detect_price_move_15m_baseline(
                    symbol=symbol,
                    symbol_15m_return=s_15m_returns[idx],
                    historical_15m_returns=historical_15m,
                    event_time_ms=event_time_ms,
                    z_threshold=base.EXTERNAL_SIGNAL_STAGE1_3_REL_STRENGTH_Z_THRESHOLD,
                    min_samples=base.EXTERNAL_SIGNAL_STAGE1_3_ROLLING_STD_MIN_SAMPLES,
                )
                if p_event:
                    detected_events["price_move_15m"].append(p_event)
            else:
                rolling_baseline_insufficient_count += 1

            return_history.append((b.bar_start_ms, s_15m_returns[idx]))

    eligible_event_times_by_symbol, metrics_by_symbol_direction = _build_forward_metric_cache(grouped)

    # Summarize candidates with metrics
    forward_window_incomplete_count = 0
    candidate_results = []

    for name, events in detected_events.items():
        role = "baseline" if name == "price_move_15m" else ("diagnostic" if name == "cross_symbol_rotation" else "primary")

        # 1. Filter events with complete forward metrics and calculate PnL
        valid_event_pnls = []
        valid_events = []
        for event in events:
            signed_direction = int(event.metadata.get("trigger_sign", 1)) if name == "price_move_15m" else 1
            metrics = metrics_by_symbol_direction.get(event.symbol, {}).get(signed_direction, {}).get(
                event.event_time_ms,
                {"status": "forward_window_incomplete"},
            )
            if metrics["status"] == "success":
                valid_events.append(event)
                valid_event_pnls.append(metrics["terminal_return_4h_net_bps"])
            else:
                forward_window_incomplete_count += 1

        total = len(valid_events)
        symbols = {event.symbol for event in valid_events}
        event_days = {event.event_time_ms // 86_400_000 for event in valid_events}
        event_symbol_counts = Counter(event.symbol for event in valid_events)
        day_counts = Counter(event.event_time_ms // 86_400_000 for event in valid_events)

        # Concentration metrics
        positive_pnls = [max(val, 0.0) for val in valid_event_pnls]
        positive_total = sum(positive_pnls)
        top5_pos_share = sum(sorted(positive_pnls, reverse=True)[:5]) / positive_total if positive_total > 0 else 0.0

        abs_pnls = [abs(val) for val in valid_event_pnls]
        abs_total = sum(abs_pnls)
        top5_abs_share = sum(sorted(abs_pnls, reverse=True)[:5]) / abs_total if abs_total > 0 else 0.0

        # Trial results initialization
        actual_median = _safe_median(valid_event_pnls)
        actual_p05 = _safe_p05(valid_event_pnls)

        trial_medians = []
        trial_p05s = []

        baseline_excess_net_bps = 0.0
        left_tail_p05_vs_baseline = 0.0
        baseline_primary_metric_median = 0.0
        candidate_vs_baseline_percentile = 0.0

        # Baseline trials computation
        # Run 500 baseline trials for primary and baseline events
        if name != "cross_symbol_rotation" and total > 0:
            trials_res = run_random_baseline_trials(
                valid_events,
                eligible_event_times_by_symbol=eligible_event_times_by_symbol,
                trials=base.EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS,
                random_seed=base.EXTERNAL_SIGNAL_STAGE1_3_RANDOM_SEED,
            )
            for trial in trials_res["trials"]:
                trial_pnls = []
                for be in trial:
                    signed_direction = int(be.metadata.get("trigger_sign", 1)) if name == "price_move_15m" else 1
                    metrics = metrics_by_symbol_direction.get(be.symbol, {}).get(signed_direction, {}).get(
                        be.event_time_ms,
                        {"status": "forward_window_incomplete"},
                    )
                    if metrics["status"] == "success":
                        trial_pnls.append(metrics["terminal_return_4h_net_bps"])

                trial_medians.append(_safe_median(trial_pnls))
                trial_p05s.append(_safe_p05(trial_pnls))

            baseline_primary_metric_median = _safe_median(trial_medians)
            baseline_excess_net_bps = actual_median - baseline_primary_metric_median
            left_tail_p05_vs_baseline = actual_p05 - _safe_median(trial_p05s)
            candidate_vs_baseline_percentile = sum(1 for tm in trial_medians if tm < actual_median) / len(trial_medians) if trial_medians else 0.0

        res_dict = {
            "candidate_name": name,
            "candidate_role": role,
            "event_count": total,
            "symbols_with_events": len(symbols),
            "event_days": len(event_days),
            "max_single_symbol_event_share": max(event_symbol_counts.values(), default=0) / total if total else 0.0,
            "max_single_day_event_share": max(day_counts.values(), default=0) / total if total else 0.0,
            "top_5_positive_events_gross_profit_share": top5_pos_share,
            "top_5_events_abs_pnl_share": top5_abs_share,
            "baseline_excess_net_bps": baseline_excess_net_bps,
            "median_net_return_after_50bps": actual_median,
            "left_tail_p05_after_50bps_vs_baseline_bps": left_tail_p05_vs_baseline,
        }

        if name != "cross_symbol_rotation":
            res_dict.update({
                "random_baseline_trials": base.EXTERNAL_SIGNAL_STAGE1_3_RANDOM_BASELINE_TRIALS,
                "baseline_primary_metric_median": baseline_primary_metric_median,
                "candidate_vs_baseline_percentile": candidate_vs_baseline_percentile,
            })

        if name == "relative_strength_vs_btc":
            res_dict.update({
                "evaluation_mode": "outright_long_alt",
                "relative_spread_observation_reported": True,
            })

        candidate_results.append(res_dict)

    summary = {
        "historical_venue": historical_venue,
        "venue_proxy_used": venue_proxy_used,
        "venue_proxy_risk": "gate_live_binance_history_mismatch" if venue_proxy_used else "none",
        "bar_coverage_ratio_by_symbol": coverage,
        "symbol_bar_count": dict(bar_count_by_symbol),
        "excluded_event_reason_counts": {},
        "rolling_baseline_insufficient_count": rolling_baseline_insufficient_count,
        "forward_window_incomplete_count": forward_window_incomplete_count,
        "candidate_results": candidate_results,
        "baseline_results": {},
        "fixture_run": fixture_run,
        "research_result_valid": not fixture_run and history_days >= base.EXTERNAL_SIGNAL_STAGE1_3_HISTORY_DAYS_MIN,
        "history_days": history_days,
        "alpha_interpretation_allowed": False,
        "collector_expansion_allowed": False,
        "live_shadow_required_now": False,
    }
    return decide_stage1_3_summary(summary)
