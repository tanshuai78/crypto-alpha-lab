import datetime
import json
import os
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write


def build_daily_path(root: str, stream_name: str, timestamp_ms: int, event_symbol_id: str | None = None) -> str:
    if ".." in stream_name or stream_name.startswith("/") or stream_name.startswith("\\"):
        raise ValueError(f"Invalid stream_name: {stream_name}")

    dt = datetime.datetime.utcfromtimestamp(timestamp_ms / 1000.0)
    date_str = dt.strftime("%Y%m%d")

    root_abs = os.path.abspath(root)

    if stream_name == "depth_snapshots":
        if not event_symbol_id:
            raise ValueError("event_symbol_id is required for depth_snapshots stream")
        if ".." in event_symbol_id or "/" in event_symbol_id or "\\" in event_symbol_id:
            raise ValueError(f"Invalid event_symbol_id: {event_symbol_id}")

        rel_path = os.path.join("depth_snapshots", date_str, f"{event_symbol_id}.jsonl")
    else:
        rel_path = os.path.join(stream_name, f"{date_str}.jsonl")

    target_path = os.path.abspath(os.path.join(root_abs, rel_path))
    if not target_path.startswith(root_abs):
        raise ValueError("Traversal outside root is not allowed")
    return target_path


def append_jsonl(path: str, row: dict, *, storage_guard: Any) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    line_bytes = (json.dumps(row) + "\n").encode("utf-8")
    path_obj = Path(path)

    def _write_action():
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, "ab") as f:
            f.write(line_bytes)
            f.flush()
            os.fsync(f.fileno())

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=len(line_bytes),
        persistent_delta_bytes=len(line_bytes),
        write_func=_write_action,
    )
    require_storage_write(storage_guard, res)
    return {
        "appended": True,
        "storage_blocker": None,
    }



def write_json(path: str, data: dict, *, storage_guard: Any) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    serialized_bytes = json.dumps(data, indent=2).encode("utf-8")
    path_obj = Path(path)
    old_size = path_obj.stat().st_size if path_obj.exists() else 0

    def _write_action():
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        with open(path_obj, "wb") as f:
            f.write(serialized_bytes)
            f.flush()
            os.fsync(f.fileno())

    result = storage_guard.reserve_and_write(
        artifact_class="ordinary_control_plane",
        transient_peak_bytes=len(serialized_bytes),
        persistent_delta_bytes=max(0, len(serialized_bytes) - old_size),
        write_func=_write_action,
    )
    require_storage_write(storage_guard, result)
    return {"written": True, "storage_blocker": None}


def read_jsonl(path: str) -> list:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows
