import datetime
import hashlib
import json
from pathlib import Path


def build_detail_payload_path(root: str | Path, timestamp_ms: int, source_article_id: str, suffix: str = "json") -> Path:
    dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=datetime.timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")

    if suffix not in ("json", "html", "txt"):
        raise ValueError(f"Unsupported storage suffix: {suffix}")

    is_safe = bool(source_article_id) and all(c.isalnum() or c in ('-', '_') for c in source_article_id)
    if is_safe:
        safe_id = source_article_id
    else:
        safe_id = hashlib.sha256(source_article_id.encode("utf-8")).hexdigest()

    return Path(root) / "raw_payloads" / "announcement_detail" / date_str / f"{safe_id}.{suffix}"



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


def write_detail_payload(root: str | Path, timestamp_ms: int, source_article_id: str, payload: object) -> dict:
    if isinstance(payload, bytes):
        text_content = payload.decode("utf-8", errors="replace")
        suffix = "txt"
    elif isinstance(payload, str):
        text_content = payload
        stripped = payload.strip()
        if stripped.startswith("<") or "<html>" in payload.lower() or "<!doctype" in payload.lower():
            suffix = "html"
        else:
            suffix = "txt"
    else:
        text_content = json.dumps(payload, sort_keys=True)
        suffix = "json"

    path = build_detail_payload_path(root, timestamp_ms, source_article_id, suffix)
    path.parent.mkdir(parents=True, exist_ok=True)

    encoded_bytes = text_content.encode("utf-8")
    with open(path, "wb") as f:
        f.write(encoded_bytes)

    sha256_hash = hashlib.sha256(encoded_bytes).hexdigest()
    rel_path = path.relative_to(Path(root))

    return {
        "payload_path": str(rel_path),
        "payload_size_bytes": len(encoded_bytes),
        "payload_sha256": sha256_hash,
    }

