def check_first_bar_for_event(
    event: dict, bars_by_symbol: dict, now_ms: int, timeout_ms: int = 24 * 3600 * 1000
) -> dict:
    updated = dict(event)
    symbols = event.get("symbols", [])
    detected_at_ms = event.get("detected_at_ms", 0)

    found_start_ms = None
    for symbol in symbols:
        bars = bars_by_symbol.get(symbol, [])
        for bar in bars:
            bar_start = bar.get("bar_start_ms")
            try:
                bar_start_val = int(bar_start)
            except (TypeError, ValueError):
                continue
            if bar_start_val >= detected_at_ms:
                if found_start_ms is None or bar_start_val < found_start_ms:
                    found_start_ms = bar_start_val


    if found_start_ms is not None:
        updated["first_futures_bar_status"] = "found"
        updated["first_futures_bar_start_ms"] = found_start_ms
    else:
        if now_ms - detected_at_ms >= timeout_ms:
            updated["first_futures_bar_status"] = "timeout"
        else:
            updated["first_futures_bar_status"] = "not_yet_available"
            updated["first_futures_bar_start_ms"] = None
    return updated


def fetch_first_bar_status_for_event(event: dict, fetch_result: dict, now_ms: int) -> dict:
    updated = dict(event)
    manifest_rows = []
    if "request_manifest_row" in fetch_result:
        manifest_rows.append(fetch_result["request_manifest_row"])

    if not fetch_result.get("ok", True):
        updated["first_futures_bar_status"] = "network_error"
        updated["request_manifest_rows"] = manifest_rows
        return updated

    payload = fetch_result.get("payload", [])
    bars = []
    for item in payload:
        if isinstance(item, list) and len(item) > 0:
            bars.append({"bar_start_ms": item[0]})
        elif isinstance(item, dict):
            bars.append(item)

    symbols = event.get("symbols", [])
    bars_by_symbol = {}
    if symbols:
        bars_by_symbol[symbols[0]] = bars

    checked = check_first_bar_for_event(event, bars_by_symbol, now_ms)
    updated.update(checked)
    updated["request_manifest_rows"] = manifest_rows
    return updated


def process_first_bar_queue(
    queue: list[dict], bars_by_symbol: dict, now_ms: int, budget: int
) -> tuple[list[dict], list[dict]]:
    processed = []
    remaining = list(queue)

    to_process_count = min(budget, len(remaining))
    for _ in range(to_process_count):
        event = remaining.pop(0)
        updated = check_first_bar_for_event(event, bars_by_symbol, now_ms)
        processed.append(updated)

    return processed, remaining
