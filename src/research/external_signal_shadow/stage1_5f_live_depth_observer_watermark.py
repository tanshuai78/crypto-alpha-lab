import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write
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


def write_watermark_atomic(
    path: str,
    watermark: Watermark,
    *,
    storage_guard: Any,
) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    target_path = Path(path).resolve()
    watermark_dict = watermark.to_dict()
    validate_watermark(watermark_dict)

    serialized_bytes = (json.dumps(watermark_dict, indent=2) + "\n").encode("utf-8")
    old_size = target_path.stat().st_size if target_path.exists() else 0
    persistent_delta = len(serialized_bytes) - old_size
    transient_peak = len(serialized_bytes)

    pid = os.getpid()
    tmp_path = target_path.parent / f".{target_path.name}.atomic.{pid}.tmp"

    def _write_action():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(serialized_bytes)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, target_path)

        try:
            parent_fd = os.open(target_path.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except Exception:
            pass

    res = storage_guard.reserve_and_write(
        artifact_class="ordinary_control_plane",
        transient_peak_bytes=transient_peak,
        persistent_delta_bytes=persistent_delta,
        write_func=_write_action,
    )

    if res["status"] != "ready" or not res.get("written", False):
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        require_storage_write(storage_guard, res)

    return {"written": True, "storage_blocker": None}


def bootstrap_watermark_from_stage1_5d_events(
    events: list,
    source_root: str = "",
    output_root: str = "",
    now_ms: int | None = None,
) -> Watermark:
    created_at = now_ms if now_ms is not None else int(time.time() * 1000)
    if not events:
        max_detected = 0
        seen_event_ids = []
        seen_source_article_ids = []
        seen_stable_event_keys = []
    else:
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

    abs_out_root = os.path.abspath(output_root) if output_root else ""
    raw_root_payload = f"{abs_out_root}|{created_at}|{source_root}|{max_detected}"
    bootstrap_root_id = hashlib.sha256(raw_root_payload.encode("utf-8")).hexdigest()

    return Watermark(
        watermark_version=1,
        max_seen_detected_at_ms=max_detected,
        seen_event_ids=seen_event_ids,
        seen_source_article_ids=seen_source_article_ids,
        seen_stable_event_keys=seen_stable_event_keys,
        updated_at_ms=created_at,
        watermark_schema_version=2,
        bootstrap_max_seen_detected_at_ms=max_detected,
        bootstrap_created_at_ms=created_at,
        bootstrap_source_root=source_root,
        bootstrap_root_id=bootstrap_root_id,
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

    if detected_at_ms is None:
        return watermark

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
        watermark_schema_version=getattr(watermark, "watermark_schema_version", 1),
        bootstrap_max_seen_detected_at_ms=getattr(watermark, "bootstrap_max_seen_detected_at_ms", None),
        bootstrap_created_at_ms=getattr(watermark, "bootstrap_created_at_ms", None),
        bootstrap_source_root=getattr(watermark, "bootstrap_source_root", ""),
        bootstrap_root_id=getattr(watermark, "bootstrap_root_id", ""),
    )
