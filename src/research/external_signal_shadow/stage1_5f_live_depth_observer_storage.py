import datetime
import json
import os


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


def append_jsonl(path: str, row: dict) -> None:
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def write_json(path: str, data: dict) -> None:
    dir_name = os.path.dirname(os.path.abspath(path))
    os.makedirs(dir_name, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


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
