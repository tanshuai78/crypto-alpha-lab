import random
from datetime import datetime, timezone


def compute_price_move_baseline_events(
    price_index: dict,
    symbol: str,
    signed_direction: int,
    threshold_bps: float,
    excluded_event_times_ms: list[int] = None,
    cooldown_hours: int = 24
) -> list[dict]:
    if symbol not in price_index:
        return []
    bars = price_index[symbol]
    res = []
    cooldown_ms = cooldown_hours * 3600_000
    excluded = excluded_event_times_ms or []

    # Map bar start time to bar for O(1) lookups
    time_map = {b["bar_start_ms"]: b for b in bars}

    for i, bar in enumerate(bars):
        t = bar["bar_start_ms"]
        t_start = t - 3600_000
        t_prev = t - 900_000

        if t_start in time_map and t_prev in time_map:
            b_start = time_map[t_start]
            b_prev = time_map[t_prev]

            # 1h return
            ret_bps = (b_prev["close"] / b_start["open"] - 1.0) * 10000.0
            triggered = False
            if signed_direction == 1 and ret_bps >= threshold_bps:
                triggered = True
            elif signed_direction == -1 and ret_bps <= -threshold_bps:
                triggered = True

            if triggered:
                # Check exclusions
                in_cooldown = False
                for ex_t in excluded:
                    if abs(t - ex_t) < cooldown_ms:
                        in_cooldown = True
                        break
                if not in_cooldown:
                    res.append({
                        "symbol": symbol,
                        "event_type": "price_move_baseline_event",
                        "signed_direction": signed_direction,
                        "event_time_ms": t,
                        "available_at_ms": t,
                    })
    return res


def sample_symbol_hour_event_type_matched_random_baseline(
    candidates: list[dict],
    price_index: dict,
    trials: int = 500,
    random_seed: int = 42
) -> list[list[dict]]:
    # Find list of all events' time to exclude
    excluded_times = {}
    for c in candidates:
        sym = c["symbol"]
        if sym not in excluded_times:
            excluded_times[sym] = []
        excluded_times[sym].append(c["event_time_ms"])

    res_trials = []
    # Seed per trial to ensure reproducibility and variety
    for trial_idx in range(trials):
        rng = random.Random(random_seed + trial_idx)
        trial_events = []
        for c in candidates:
            sym = c["symbol"]
            if sym not in price_index:
                continue
            symbol_bars = price_index[sym]
            if not symbol_bars:
                continue

            dt = datetime.fromtimestamp(c["event_time_ms"] / 1000.0, tz=timezone.utc)
            c_hour = dt.hour
            c_weekday = dt.weekday()

            # Find candidates matching hour and weekday
            matches = []
            weekday_matches = []
            hour_matches = []

            for b in symbol_bars:
                # Check complete window
                # Maximum forward window is 24h
                if b["bar_start_ms"] + 24 * 3600_000 > symbol_bars[-1]["bar_start_ms"]:
                    continue

                # Exclude candidate timestamp +/- 24h
                t_evs = excluded_times.get(sym, [])
                in_exclusion = False
                for t_ev in t_evs:
                    if abs(b["bar_start_ms"] - t_ev) < 24 * 3600_000:
                        in_exclusion = True
                        break
                if in_exclusion:
                    continue

                b_dt = datetime.fromtimestamp(b["bar_start_ms"] / 1000.0, tz=timezone.utc)
                if b_dt.hour == c_hour:
                    hour_matches.append(b)
                    if b_dt.weekday() == c_weekday:
                        weekday_matches.append(b)

            matches = weekday_matches if weekday_matches else hour_matches
            if not matches:
                # fallback to any bar with complete window
                matches = [
                    b for b in symbol_bars
                    if b["bar_start_ms"] + 24 * 3600_000 <= symbol_bars[-1]["bar_start_ms"]
                ]

            if matches:
                selected_bar = rng.choice(matches)
                trial_events.append({
                    "symbol": sym,
                    "event_type": c.get("event_type", "random_baseline_event"),
                    "signed_direction": c["signed_direction"],
                    "entry_delay_hours": c.get("entry_delay_hours", 1),
                    "event_time_ms": selected_bar["bar_start_ms"],
                    "available_at_ms": selected_bar["bar_start_ms"],
                })
        res_trials.append(trial_events)

    return res_trials
