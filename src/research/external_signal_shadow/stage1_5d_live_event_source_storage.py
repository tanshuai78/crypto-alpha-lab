import datetime
import json
from pathlib import Path


def build_daily_path(root: str | Path, stream_name: str, timestamp_ms: int) -> Path:
    dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=datetime.timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")
    return Path(root) / stream_name / f"{date_str}.jsonl"


def build_stream_paths(output_root: str | Path, timestamp_ms: int) -> dict[str, Path]:
    root_path = Path(output_root)
    return {
        "events": build_daily_path(root_path, "events", timestamp_ms),
        "raw_payloads": build_daily_path(root_path, "raw_payloads", timestamp_ms),
        "heartbeats": build_daily_path(root_path, "heartbeats", timestamp_ms),
        "request_manifest": build_daily_path(root_path, "request_manifest", timestamp_ms),
        "summary": root_path / "binance_futures_launch_smoke_summary.json",
    }


def append_jsonl(path: str | Path, row: dict) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def enforce_payload_budget(path: str | Path, max_bytes: int) -> dict:
    file_path = Path(path)
    if file_path.exists():
        size = file_path.stat().st_size
        if size > max_bytes:
            return {
                "storage_budget_passed": False,
                "blocker": "max_raw_payload_bytes_per_day_exceeded",
            }
    return {"storage_budget_passed": True, "blocker": None}
