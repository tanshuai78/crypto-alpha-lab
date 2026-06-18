from research.external_signal_shadow.stage1_4b_lite_models import CandidateEvent


def _build_price_index(price_bars: list[dict]) -> dict[str, tuple[list[dict], dict[int, int]]]:
    grouped: dict[str, list[dict]] = {}
    for bar in price_bars:
        symbol = bar.get("symbol")
        if symbol:
            grouped.setdefault(str(symbol), []).append(bar)

    index: dict[str, tuple[list[dict], dict[int, int]]] = {}
    for symbol, bars in grouped.items():
        ordered = sorted(bars, key=lambda x: int(x["bar_start_ms"]))
        pos = {int(bar["bar_start_ms"]): idx for idx, bar in enumerate(ordered)}
        index[symbol] = (ordered, pos)
    return index


def _compute_replay_core(
    event: CandidateEvent,
    *,
    price_index: dict[str, tuple[list[dict], dict[int, int]]],
) -> dict | None:
    if price_index is None:
        raise ValueError("price_index must be provided")

    symbol_index = price_index.get(event.symbol)
    if symbol_index is None:
        return None

    sym_bars, entry_positions = symbol_index

    entry_idx = entry_positions.get(int(event.entry_bar_start_ms), -1)
    if entry_idx < 0:
        return None

    if entry_idx + 16 >= len(sym_bars):
        return None

    entry_bar = sym_bars[entry_idx]
    exit_bar_4h = sym_bars[entry_idx + 16]

    entry_close = float(entry_bar["close_price"])
    if entry_close <= 0:
        return None

    raw_return_4h = (float(exit_bar_4h["close_price"]) - entry_close) / entry_close
    signed_return_4h = raw_return_4h * event.signed_direction

    # Secondary 1h window (4 bars)
    if entry_idx + 4 < len(sym_bars):
        exit_bar_1h = sym_bars[entry_idx + 4]
        raw_return_1h = (float(exit_bar_1h["close_price"]) - entry_close) / entry_close
        signed_return_1h = raw_return_1h * event.signed_direction
    else:
        raw_return_1h = None
        signed_return_1h = None

    # Secondary 12h window (48 bars)
    if entry_idx + 48 < len(sym_bars):
        exit_bar_12h = sym_bars[entry_idx + 48]
        raw_return_12h = (float(exit_bar_12h["close_price"]) - entry_close) / entry_close
        signed_return_12h = raw_return_12h * event.signed_direction
    else:
        raw_return_12h = None
        signed_return_12h = None

    # Calculate net returns in bps
    net_4h_30 = signed_return_4h * 10000.0 - 30.0
    net_4h_50 = signed_return_4h * 10000.0 - 50.0
    net_4h_80 = signed_return_4h * 10000.0 - 80.0

    return {
        "raw_return_4h": raw_return_4h,
        "signed_return_4h": signed_return_4h,
        "terminal_return_4h_net_bps_after_30bps": net_4h_30,
        "terminal_return_4h_net_bps_after_50bps": net_4h_50,
        "terminal_return_4h_net_bps_after_80bps": net_4h_80,
        "raw_return_1h": raw_return_1h,
        "signed_return_1h": signed_return_1h,
        "raw_return_12h": raw_return_12h,
        "signed_return_12h": signed_return_12h,
        "signed_short_replay_present": (event.signed_direction == -1),
        "short_execution_intent_allowed": False,
        "borrow_or_margin_feasibility_checked": False,
    }


def replay_event(
    event: CandidateEvent,
    price_bars: list[dict] | None = None,
    *,
    price_index: dict[str, tuple[list[dict], dict[int, int]]] | None = None,
    replay_cache: dict[tuple[str, int, int], dict | None] | None = None,
) -> dict | None:
    if price_index is None:
        if price_bars is None:
            raise ValueError("price_bars or price_index must be provided")
        price_index = _build_price_index(price_bars)

    cache_key = (event.symbol, int(event.entry_bar_start_ms), int(event.signed_direction))
    if replay_cache is not None and cache_key in replay_cache:
        core = replay_cache[cache_key]
    else:
        core = _compute_replay_core(event, price_index=price_index)
        if replay_cache is not None:
            replay_cache[cache_key] = core

    if core is None:
        return None

    return {
        "symbol": event.symbol,
        "candidate_name": event.candidate_name,
        "event_time_ms": event.event_time_ms,
        "event_available_at_ms": event.event_available_at_ms,
        "entry_bar_start_ms": event.entry_bar_start_ms,
        "signed_direction": event.signed_direction,
        **core,
        "metadata": event.metadata,
    }


def replay_candidate_events(events: list[CandidateEvent], price_bars: list[dict]) -> list[dict]:
    price_index = _build_price_index(price_bars)
    replay_cache: dict[tuple[str, int, int], dict | None] = {}
    return replay_candidate_events_with_index(
        events,
        price_index=price_index,
        replay_cache=replay_cache,
    )


def replay_candidate_events_with_index(
    events: list[CandidateEvent],
    *,
    price_index: dict[str, tuple[list[dict], dict[int, int]]],
    replay_cache: dict[tuple[str, int, int], dict | None] | None = None,
) -> list[dict]:
    if replay_cache is None:
        replay_cache = {}
    results = []
    for event in events:
        res = replay_event(event, price_index=price_index, replay_cache=replay_cache)
        if res is not None:
            results.append(res)
    return results
