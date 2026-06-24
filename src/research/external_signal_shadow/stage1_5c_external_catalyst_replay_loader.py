import json
from pathlib import Path

from configs import base


def load_jsonl(path: str | Path) -> list[dict]:
    res = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                res.append(json.loads(line_str))
    return res


def assert_stage1_5b_ready(summary_path: str | Path) -> dict:
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    decision = summary.get("decision")
    if decision != "stage1_5b_event_table_ready":
        raise ValueError(
            f"Stage 1.5B summary decision must be 'stage1_5b_event_table_ready', got: {decision}"
        )
    if summary.get("replay_allowed") is not False:
        raise ValueError("Stage 1.5B replay_allowed must be False")
    if summary.get("stage1_5c_replay_candidate_allowed") is not False:
        raise ValueError("Stage 1.5B stage1_5c_replay_candidate_allowed must be False")
    return summary


def load_stage1_5b_symbol_events(path: str | Path) -> list[dict]:
    raw_events = load_jsonl(path)
    allowed_types = base.EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES
    res = []
    for ev in raw_events:
        event_type = ev.get("event_type")
        if event_type not in allowed_types:
            continue
        if ev.get("replay_allowed") is True or ev.get("paper_trading_allowed") is True or ev.get("live_trading_allowed") is True:
            raise ValueError("Stage 1.5B must not pre-allow replay/paper/live in events")

        ev_copy = dict(ev)
        upstream_allowed = ev_copy.pop("stage1_5c_replay_candidate_allowed", False)
        ev_copy["stage1_5b_replay_candidate_allowed_upstream"] = upstream_allowed
        res.append(ev_copy)
    return res


def load_price_bars(path: str | Path) -> list[dict]:
    raw_bars = load_jsonl(path)
    res = []
    for bar in raw_bars:
        # Find start timestamp
        bar_start_ms = None
        for key in ["bar_start_ms", "open_time", "timestamp", "timestamp_ms"]:
            if key in bar:
                bar_start_ms = int(bar[key])
                break
        if bar_start_ms is None:
            raise ValueError(f"Could not find bar start timestamp in bar: {bar}")

        # Normalize price fields
        open_val = float(bar.get("open") or bar.get("open_price") or 0.0)
        high_val = float(bar.get("high") or bar.get("high_price") or 0.0)
        low_val = float(bar.get("low") or bar.get("low_price") or 0.0)
        close_val = float(bar.get("close") or bar.get("close_price") or 0.0)

        # Normalize volume
        quote_volume = 0.0
        for key in ["quote_volume", "quoteVolume", "volume_quote"]:
            if key in bar:
                quote_volume = float(bar[key])
                break

        res.append({
            "symbol": bar["symbol"],
            "bar_start_ms": bar_start_ms,
            "bar_end_ms": bar_start_ms + base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS,
            "open": open_val,
            "high": high_val,
            "low": low_val,
            "close": close_val,
            "quote_volume": quote_volume,
            "source": bar.get("source", "binance_um_futures_15m"),
        })
    return res
