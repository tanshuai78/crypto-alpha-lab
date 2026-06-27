import hashlib
import json
import os
import tempfile
import time

from src.research.external_signal_shadow.stage1_5f_live_depth_observer_models import Watermark


def _get_field(event, field_name, default=None):
    if isinstance(event, dict):
        return event.get(field_name, default)
    return getattr(event, field_name, default)


def get_stable_event_key(event) -> str:
    source_name = str(_get_field(event, "source_name", ""))
    source_article_id = str(_get_field(event, "source_article_id", ""))
    source_detail_url = str(_get_field(event, "source_detail_url", "") or _get_field(event, "url", ""))
    source_detail_url_normalized = source_detail_url.strip().rstrip("/").lower()
    source_published_at_ms = str(_get_field(event, "source_published_at_ms", ""))
    title = str(_get_field(event, "title", ""))
    h = hashlib.sha256()
    h.update(
        f"{source_name}|{source_article_id}|{source_detail_url_normalized}|{source_published_at_ms}|{title}".encode(
            "utf-8"
        )
    )
    return h.hexdigest()


def load_watermark(path: str) -> Watermark:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Watermark file not found at {path}")

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Corrupted watermark file: {e}")

    validate_watermark(data)
    return Watermark.from_dict(data)


def validate_watermark(data: dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("Watermark data must be a dictionary")
    if "watermark_version" not in data:
        raise ValueError("Missing 'watermark_version' in watermark")
    if not isinstance(data["watermark_version"], int):
        raise ValueError("'watermark_version' must be an integer")
    if "max_seen_detected_at_ms" not in data or not isinstance(data["max_seen_detected_at_ms"], int):
        raise ValueError("'max_seen_detected_at_ms' must be an integer")
    if "seen_event_ids" not in data or not isinstance(data["seen_event_ids"], list):
        raise ValueError("'seen_event_ids' must be a list")
    if "seen_source_article_ids" not in data or not isinstance(data["seen_source_article_ids"], list):
        raise ValueError("'seen_source_article_ids' must be a list")
    if "seen_stable_event_keys" not in data or not isinstance(data["seen_stable_event_keys"], list):
        raise ValueError("'seen_stable_event_keys' must be a list")


def write_watermark_atomic(path: str, watermark: Watermark) -> None:
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name, prefix="watermark_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(watermark.to_dict(), f, indent=2)
            f.flush()
            os.fsync(fd)

        os.replace(tmp_path, path)

        try:
            parent_fd = os.open(dir_name, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except Exception:
            pass
    except Exception as e:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise e


def bootstrap_watermark_from_stage1_5d_events(events: list) -> Watermark:
    if not events:
        return Watermark(
            watermark_version=1,
            max_seen_detected_at_ms=0,
            seen_event_ids=[],
            seen_source_article_ids=[],
            seen_stable_event_keys=[],
            updated_at_ms=int(time.time() * 1000),
        )

    max_detected = max((_get_field(e, "detected_at_ms") or 0) for e in events)

    seen_event_ids = []
    seen_source_article_ids = []
    seen_stable_event_keys = []

    for e in events:
        eid = _get_field(e, "event_id")
        aid = _get_field(e, "source_article_id")
        skey = get_stable_event_key(e)

        if eid and eid not in seen_event_ids:
            seen_event_ids.append(eid)
        if aid and aid not in seen_source_article_ids:
            seen_source_article_ids.append(aid)
        if skey not in seen_stable_event_keys:
            seen_stable_event_keys.append(skey)

    return Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=max_detected,
        seen_event_ids=seen_event_ids,
        seen_source_article_ids=seen_source_article_ids,
        seen_stable_event_keys=seen_stable_event_keys,
        updated_at_ms=int(time.time() * 1000),
    )


def event_is_post_watermark(event, watermark: Watermark) -> bool:
    detected_at_ms = _get_field(event, "detected_at_ms")
    if detected_at_ms is None:
        return False

    if detected_at_ms > watermark.max_seen_detected_at_ms:
        return True
    elif detected_at_ms < watermark.max_seen_detected_at_ms:
        return False
    else:
        event_id = _get_field(event, "event_id")
        source_article_id = _get_field(event, "source_article_id")
        stable_key = get_stable_event_key(event)

        if event_id and event_id in watermark.seen_event_ids:
            return False
        if source_article_id and source_article_id in watermark.seen_source_article_ids:
            return False
        if stable_key in watermark.seen_stable_event_keys:
            return False

        return True


def update_watermark_with_event(watermark: Watermark, event) -> Watermark:
    detected_at_ms = _get_field(event, "detected_at_ms")
    event_id = _get_field(event, "event_id")
    source_article_id = _get_field(event, "source_article_id")
    stable_key = get_stable_event_key(event)

    seen_event_ids = list(watermark.seen_event_ids)
    seen_source_article_ids = list(watermark.seen_source_article_ids)
    seen_stable_event_keys = list(watermark.seen_stable_event_keys)

    if detected_at_ms > watermark.max_seen_detected_at_ms:
        new_max = detected_at_ms
        seen_event_ids = [event_id] if event_id else []
        seen_source_article_ids = [source_article_id] if source_article_id else []
        seen_stable_event_keys = [stable_key]
    elif detected_at_ms == watermark.max_seen_detected_at_ms:
        new_max = watermark.max_seen_detected_at_ms
        if event_id and event_id not in seen_event_ids:
            seen_event_ids.append(event_id)
        if source_article_id and source_article_id not in seen_source_article_ids:
            seen_source_article_ids.append(source_article_id)
        if stable_key not in seen_stable_event_keys:
            seen_stable_event_keys.append(stable_key)
    else:
        new_max = watermark.max_seen_detected_at_ms

    return Watermark(
        watermark_version=watermark.watermark_version,
        max_seen_detected_at_ms=new_max,
        seen_event_ids=seen_event_ids,
        seen_source_article_ids=seen_source_article_ids,
        seen_stable_event_keys=seen_stable_event_keys,
        updated_at_ms=int(time.time() * 1000),
    )
