from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    classify_event_type,
    normalize_live_event,
    parse_binance_announcement_payload,
)


def run_one_poll_cycle(
    payload: dict,
    detected_at_ms: int,
    source_parent_url: str,
    first_bar_queue: list[dict],
) -> dict:
    parse_res = parse_binance_announcement_payload(payload)

    source_format_drift = parse_res.get("source_format_drift", False)
    schema_parse_error = parse_res.get("schema_parse_error", False)
    poll_success = not (source_format_drift or schema_parse_error)

    heartbeat = {
        "poll_started_at_ms": detected_at_ms,
        "poll_completed_at_ms": detected_at_ms + 100,  # mock completed 100ms later
        "configured_poll_interval_sec": 60,
        "poll_success": poll_success,
        "source_format_drift": source_format_drift,
        "schema_parse_error": schema_parse_error,
        "heartbeat_gap": False,
    }

    events = []
    new_queue = list(first_bar_queue)

    if poll_success:
        raw_articles = parse_res.get("events", [])
        for raw_art in raw_articles:
            title = raw_art.get("title", "")
            event_type = classify_event_type(title)
            if event_type == "futures_contract_launch":
                pub_time = raw_art.get("releaseDate")
                confidence = "medium" if pub_time else "low"
                norm_event = normalize_live_event(
                    raw=raw_art,
                    source_parent_url=source_parent_url,
                    detected_at_ms=detected_at_ms,
                    source_published_at_ms=pub_time,
                    source_published_at_ms_confidence=confidence,
                )
                events.append(norm_event)

                event_id = norm_event["event_id"]
                if not any(eq.get("event_id") == event_id for eq in new_queue):
                    eq_item = dict(norm_event)
                    eq_item["first_futures_bar_status"] = "not_yet_available"
                    eq_item["first_futures_bar_start_ms"] = None
                    new_queue.append(eq_item)

    return {"events": events, "first_bar_queue": new_queue, "heartbeat": heartbeat}
