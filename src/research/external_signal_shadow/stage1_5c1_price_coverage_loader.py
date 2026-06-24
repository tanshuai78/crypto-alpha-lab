import json
from pathlib import Path

from configs import base


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                rows.append(json.loads(line_str))
    return rows


def load_stage1_5b_events(path: str | Path) -> list[dict]:
    all_rows = load_jsonl(path)
    allowed_types = set(base.EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES)
    return [r for r in all_rows if r.get("event_type") in allowed_types]


def build_event_request_window(event: dict, now_ms: int) -> dict:
    event_type = event["event_type"]
    available_at_ms = event["available_at_ms"]
    symbol = event["symbol"]

    pre_days = base.EXTERNAL_SIGNAL_STAGE1_5C1_PRE_EVENT_HISTORY_DAYS
    buffer_days = base.EXTERNAL_SIGNAL_STAGE1_5C1_POST_EVENT_BUFFER_DAYS

    max_entry_hours = max(base.EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS)
    max_forward_hours = max(base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS)

    day_ms = 24 * 60 * 60 * 1000
    hour_ms = 60 * 60 * 1000

    if event_type == "exchange_delisting_notice":
        # Notice time is anchor. Delisting notice requires 30d pre-event history + post-event forward window
        start_ms = available_at_ms - (pre_days + buffer_days) * day_ms
        end_ms = available_at_ms + (max_entry_hours + max_forward_hours) * hour_ms + buffer_days * day_ms
    elif event_type == "futures_contract_launch":
        # Launch notice time is anchor. Pre-event history is not required (starts at available_at_ms)
        start_ms = available_at_ms
        end_ms = available_at_ms + (max_entry_hours + max_forward_hours) * hour_ms + buffer_days * day_ms
    else:
        # Fallback
        start_ms = available_at_ms
        end_ms = available_at_ms + day_ms

    # Truncate end_ms to current completed bar
    interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5C1_KLINE_INTERVAL_MS
    max_allowed_end_ms = now_ms - interval_ms
    if end_ms > max_allowed_end_ms:
        end_ms = max_allowed_end_ms

    if start_ms > end_ms:
        start_ms = end_ms

    return {
        "symbol_event_id": event["symbol_event_id"],
        "event_type": event_type,
        "symbol": symbol,
        "start_ms": start_ms,
        "end_ms": end_ms,
    }


def merge_symbol_windows(windows: list[dict], merge_gap_ms: int) -> list[dict]:
    # Group by (source_type, symbol)
    groups = {}
    for w in windows:
        # Assume futures as default source_type if not present
        source = w.get("source_type", "futures")
        symbol = w["symbol"]
        key = (source, symbol)
        if key not in groups:
            groups[key] = []
        groups[key].append(w)

    merged_results = []

    for (source, symbol), group_list in groups.items():
        # Sort by start_ms
        sorted_windows = sorted(group_list, key=lambda x: x["start_ms"])

        current_merged = None
        for w in sorted_windows:
            if current_merged is None:
                current_merged = {
                    "source_type": source,
                    "symbol": symbol,
                    "start_ms": w["start_ms"],
                    "end_ms": w["end_ms"],
                }
            else:
                # Merge if next start_ms is within current end_ms + merge_gap_ms
                if w["start_ms"] <= current_merged["end_ms"] + merge_gap_ms:
                    current_merged["end_ms"] = max(current_merged["end_ms"], w["end_ms"])
                else:
                    merged_results.append(current_merged)
                    current_merged = {
                        "source_type": source,
                        "symbol": symbol,
                        "start_ms": w["start_ms"],
                        "end_ms": w["end_ms"],
                    }
        if current_merged:
            merged_results.append(current_merged)

    return merged_results
