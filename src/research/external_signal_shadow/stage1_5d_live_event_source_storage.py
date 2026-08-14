import datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write


def build_detail_payload_path(
    root: str | Path,
    source_article_id: str,
    detail_fetch_variant: str,
    raw_payload_sha256: str,
) -> Path:
    if not detail_fetch_variant or not all(c.isalnum() or c in ("-", "_") for c in detail_fetch_variant):
        raise ValueError("detail_fetch_variant_invalid")

    is_safe = bool(source_article_id) and all(c.isalnum() or c in ('-', '_') for c in source_article_id)
    safe_id = source_article_id if is_safe else hashlib.sha256(source_article_id.encode("utf-8")).hexdigest()

    return Path(root) / "raw_payloads" / "announcement_detail" / safe_id / f"{detail_fetch_variant}.{raw_payload_sha256}.bin"


def build_daily_path(root: str | Path, stream_name: str, timestamp_ms: int) -> Path:
    dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0, tz=datetime.timezone.utc)
    date_str = dt.strftime("%Y-%m-%d")
    return Path(root) / stream_name / f"{date_str}.jsonl"


def build_stream_paths(output_root: str | Path, timestamp_ms: int, *, storage_guard: Any = None) -> dict[str, Any]:
    root_path = Path(output_root)
    res = {
        "events": build_daily_path(root_path, "events", timestamp_ms),
        "raw_payloads": build_daily_path(root_path, "raw_payloads", timestamp_ms),
        "heartbeats": build_daily_path(root_path, "heartbeats", timestamp_ms),
        "request_manifest": build_daily_path(root_path, "request_manifest", timestamp_ms),
        "detail_retry_scheduler_diagnostics": build_daily_path(root_path, "detail_retry_scheduler_diagnostics", timestamp_ms),
        "detail_retry_terminal_diagnostics": build_daily_path(root_path, "detail_retry_terminal_diagnostics", timestamp_ms),
        "bapi_parse_results": build_daily_path(root_path, "bapi_parse_results", timestamp_ms),
        "formal_launch_identity_index": root_path / "formal_launch_identity_index.jsonl",
        "revision_payload_versions": root_path / "revision_payload_versions.jsonl",
        "summary": root_path / "binance_futures_launch_smoke_summary.json",
    }
    if storage_guard is not None:
        res["storage_guard"] = storage_guard
    return res



def append_jsonl(path: str | Path, row: dict, *, storage_guard: Any) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    file_path = Path(path).resolve()
    serialized_bytes = (json.dumps(row) + "\n").encode("utf-8")

    def _append_action():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "ab") as f:
            f.write(serialized_bytes)
            f.flush()
            os.fsync(f.fileno())

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=len(serialized_bytes),
        persistent_delta_bytes=len(serialized_bytes),
        write_func=_append_action,
    )

    require_storage_write(storage_guard, res)

    return {"written": True, "storage_blocker": None}


def load_payload_version_first_observed(path: str | Path) -> dict[tuple[str, str], int]:
    registry: dict[tuple[str, str], int] = {}
    file_path = Path(path)
    if not file_path.exists():
        return registry
    for line in file_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            key = (str(row["source_article_id"]), str(row["raw_payload_sha256"]))
            observed_at_ms = int(row["payload_version_first_observed_at_ms"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        if key[0] and key[1] and observed_at_ms > 0:
            registry[key] = min(registry.get(key, observed_at_ms), observed_at_ms)
    return registry


def record_payload_version_first_observed(
    path: str | Path,
    source_article_id: str,
    payload_sha256: str,
    observed_at_ms: int,
    registry: dict[tuple[str, str], int] | None = None,
    *,
    storage_guard: Any,
) -> int:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    key = (str(source_article_id), str(payload_sha256))
    known = registry if registry is not None else load_payload_version_first_observed(path)
    if key in known:
        return known[key]
    append_jsonl(
        path,
        {
            "source_article_id": key[0],
            "raw_payload_sha256": key[1],
            "payload_version_first_observed_at_ms": int(observed_at_ms),
        },
        storage_guard=storage_guard,
    )
    known[key] = int(observed_at_ms)
    return known[key]



def enforce_payload_budget(root: str | Path, max_bytes: int) -> dict:
    raw_dir = Path(root) / "raw_payloads" / "announcement_detail"
    total_bytes = 0
    if raw_dir.exists():
        for dirpath, _, filenames in os.walk(raw_dir):
            for f in filenames:
                try:
                    total_bytes += (Path(dirpath) / f).stat().st_size
                except OSError:
                    pass
    if total_bytes > max_bytes:
        return {
            "storage_budget_passed": False,
            "blocker": "max_raw_payload_bytes_exceeded",
            "total_bytes": total_bytes,
        }
    return {"storage_budget_passed": True, "blocker": None, "total_bytes": total_bytes}


def write_detail_payload_append_only(
    root: str | Path,
    source_article_id: str,
    detail_fetch_variant: str,
    raw_bytes: bytes,
    *,
    storage_guard: Any,
    timestamp_ms: int = 0,
    parsed_payload: object | None = None,
    content_type: str | None = None,
    http_status: int | None = None,
) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")



    if isinstance(raw_bytes, str):
        raw_bytes = raw_bytes.encode("utf-8")
    elif isinstance(raw_bytes, dict):
        if parsed_payload is None:
            parsed_payload = raw_bytes
        raw_bytes = json.dumps(raw_bytes).encode("utf-8")

    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    target_path = build_detail_payload_path(root, source_article_id, detail_fetch_variant, raw_sha256)

    persistent_delta = 0 if target_path.exists() else len(raw_bytes)
    transient_peak = len(raw_bytes)

    def _write_action():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not target_path.exists():
            temp_path = target_path.parent / f".{target_path.name}.atomic.tmp"
            temp_path.write_bytes(raw_bytes)
            temp_path.replace(target_path)

    res = storage_guard.reserve_and_write(
        artifact_class="normal_data",
        transient_peak_bytes=transient_peak,
        persistent_delta_bytes=persistent_delta,
        write_func=_write_action,
    )

    require_storage_write(storage_guard, res)

    canonical_sha256 = None
    if parsed_payload is not None:
        try:
            canonical_bytes = json.dumps(parsed_payload, sort_keys=True).encode("utf-8")
            canonical_sha256 = hashlib.sha256(canonical_bytes).hexdigest()
        except Exception:
            canonical_sha256 = None

    try:
        rel_path = str(target_path.relative_to(Path(root)))
    except ValueError:
        rel_path = str(target_path)

    return {
        "raw_payload_persisted": True,
        "payload_path": rel_path,
        "payload_size_bytes": len(raw_bytes),
        "raw_payload_sha256": raw_sha256,
        "payload_sha256": raw_sha256,
        "canonical_json_sha256": canonical_sha256,
        "storage_blocker": None,
    }



def write_detail_payload(
    root: str | Path,
    timestamp_ms: int,
    source_article_id: str,
    raw_payload: str | bytes | dict,
    detail_fetch_variant: str = "bapi_article_detail_query",
    *,
    storage_guard: Any,
    http_status: int | None = None,
) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")

    parsed = None
    if isinstance(raw_payload, dict):
        parsed = raw_payload
        raw_b = json.dumps(raw_payload).encode("utf-8")
    elif isinstance(raw_payload, str):
        raw_b = raw_payload.encode("utf-8")
    else:
        raw_b = raw_payload

    return write_detail_payload_append_only(
        root=root,
        source_article_id=str(source_article_id),
        detail_fetch_variant=detail_fetch_variant,
        raw_bytes=raw_b,
        timestamp_ms=timestamp_ms,
        parsed_payload=parsed,
        storage_guard=storage_guard,
        http_status=http_status,
    )
