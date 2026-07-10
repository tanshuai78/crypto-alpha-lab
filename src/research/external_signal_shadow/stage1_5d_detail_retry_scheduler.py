import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DETAIL_RETRY_SCHEDULER_STATE_FILENAME = "detail_retry_scheduler_state.json"


def compute_detail_transient_backoff_ms(
    transient_detail_error_count: int,
    *,
    base_sec: int,
    max_sec: int,
) -> int:
    exponent = max(0, min(transient_detail_error_count - 1, 5))
    return min(max_sec, base_sec * (2 ** exponent)) * 1000


def select_detail_retry_attempts(
    *,
    detail_retry_state: dict[str, dict],
    now_ms: int,
    detail_budget_per_poll: int,
    endpoint_degraded_until_ms: int,
    max_first_attempt_delay_polls: int | None = None,
    max_first_attempt_delay_ms: int | None = None,
) -> list[str]:
    if detail_budget_per_poll <= 0:
        return []

    never_attempted = []
    attempted = []
    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        if now_ms < int(state.get("next_detail_retry_at_ms") or 0):
            continue
        if int(state.get("detail_fetch_attempt_count") or 0) <= 0:
            never_attempted.append((code, state))
        else:
            attempted.append((code, state))

    never_attempted.sort(
        key=lambda item: (
            0 if _first_attempt_sla_breached(
                item[1],
                now_ms=now_ms,
                max_first_attempt_delay_polls=max_first_attempt_delay_polls,
                max_first_attempt_delay_ms=max_first_attempt_delay_ms,
            ) else 1,
            -int(item[1].get("defer_count") or 0),
            int(item[1].get("first_detected_at_ms") or 0),
            item[0],
        )
    )

    if now_ms < endpoint_degraded_until_ms:
        attempted = []
    else:
        attempted.sort(
            key=lambda item: (
                int(item[1].get("last_retry_at_ms") or 0),
                int(item[1].get("transient_detail_error_count") or 0),
                int(item[1].get("first_detected_at_ms") or 0),
                item[0],
            )
        )

    ordered = never_attempted + attempted
    return [code for code, _ in ordered[:detail_budget_per_poll]]


def _first_attempt_sla_breached(
    state: dict,
    *,
    now_ms: int,
    max_first_attempt_delay_polls: int | None,
    max_first_attempt_delay_ms: int | None,
) -> bool:
    if int(state.get("detail_fetch_attempt_count") or 0) > 0:
        return False
    if max_first_attempt_delay_polls is not None:
        if int(state.get("defer_count") or 0) >= max_first_attempt_delay_polls:
            return True
    if max_first_attempt_delay_ms is not None:
        first_detected_at_ms = int(state.get("first_detected_at_ms") or 0)
        if first_detected_at_ms and max(0, now_ms - first_detected_at_ms) >= max_first_attempt_delay_ms:
            return True
    return False


def classify_never_attempted_defer_state(
    *,
    detail_fetch_attempt_count: int,
    first_detected_at_ms: int,
    now_ms: int,
    never_attempted_max_defer_sec: int,
    detail_fetch_max_age_sec: int,
    defer_count: int = 0,
    max_first_attempt_delay_polls: int | None = None,
    max_first_attempt_delay_ms: int | None = None,
) -> dict:
    if detail_fetch_attempt_count > 0:
        return {"classification": "attempted", "terminal_failure_type": None}
    age_ms = max(0, now_ms - first_detected_at_ms)
    if age_ms >= detail_fetch_max_age_sec * 1000:
        return {
            "classification": "detail_never_attempted_budget_starved",
            "terminal_failure_type": "detail_never_attempted_budget_starved",
            "detail_fetch_status": "budget_starved",
        }
    if max_first_attempt_delay_polls is not None and defer_count >= max_first_attempt_delay_polls:
        return {
            "classification": "detail_first_attempt_sla_breach",
            "terminal_failure_type": None,
            "detail_fetch_status": "budget_deferred",
        }
    if max_first_attempt_delay_ms is not None and age_ms >= max_first_attempt_delay_ms:
        return {
            "classification": "detail_first_attempt_sla_breach",
            "terminal_failure_type": None,
            "detail_fetch_status": "budget_deferred",
        }
    if age_ms >= never_attempted_max_defer_sec * 1000:
        return {
            "classification": "detail_first_attempt_sla_breach",
            "terminal_failure_type": None,
            "detail_fetch_status": "budget_deferred",
        }
    return {"classification": "pending", "terminal_failure_type": None}


def serialize_retry_articles(detail_retry_state: dict[str, dict]) -> dict[str, dict]:
    serialized = {}
    for code, state in detail_retry_state.items():
        # Ensure all required keys exist in the serialized representation
        serialized[code] = {
            "source_article_id": code,
            "title": state.get("title") or "",
            "source_detail_url_normalized": state.get("source_detail_url_normalized") or "",
            "source_parent_url": state.get("source_parent_url") or "",
            "source_published_at_ms": state.get("source_published_at_ms"),
            "detected_at_ms": state.get("detected_at_ms", 0),
            "first_detected_at_ms": state.get("first_detected_at_ms", 0),
            "event_type": state.get("event_type") or "futures_contract_launch",
            "catalog_id": state.get("catalog_id"),
            "catalog_title": state.get("catalog_title"),
            "symbol_extraction_source": state.get("symbol_extraction_source") or "none",
            "symbol_parse_failed_reason": state.get("symbol_parse_failed_reason"),
            "pending_reason": state.get("pending_reason") or "title_symbol_missing",
            "source_published_at_ms_confidence": state.get("source_published_at_ms_confidence") or "medium",
            "detail_fetch_attempt_count": int(state.get("detail_fetch_attempt_count") or 0),
            "transient_detail_error_count": int(state.get("transient_detail_error_count") or 0),
            "non_transient_detail_error_count": int(state.get("non_transient_detail_error_count") or 0),
            "last_retry_at_ms": int(state.get("last_retry_at_ms") or 0),
            "next_detail_retry_at_ms": int(state.get("next_detail_retry_at_ms") or 0),
            "first_deferred_at_ms": state.get("first_deferred_at_ms"),
            "last_deferred_at_ms": state.get("last_deferred_at_ms"),
            "last_deferred_manifest_at_ms": int(state.get("last_deferred_manifest_at_ms") or 0),
            "defer_count": int(state.get("defer_count") or 0),
            "terminal_state": bool(state.get("terminal_state", False)),
            "terminal_failure_type": state.get("terminal_failure_type"),
            "candidate_symbols": state.get("candidate_symbols"),
            "symbol_derivation_method": state.get("symbol_derivation_method"),
            "symbol_validation_status": state.get("symbol_validation_status"),
            "symbol_launch_times_ms": state.get("symbol_launch_times_ms"),
            "symbol_onboard_times_ms": state.get("symbol_onboard_times_ms"),
            "symbol_effective_launch_times_ms": state.get("symbol_effective_launch_times_ms"),
            "launch_time_source": state.get("launch_time_source"),
        }
    return serialized


def load_detail_retry_scheduler_state(output_root: Path) -> dict:
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    if not path.exists():
        return {"metadata_version": 1, "articles": {}, "endpoint_health": {}}
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded.get("articles"), dict):
        loaded["articles"] = {}
    if not isinstance(loaded.get("endpoint_health"), dict):
        loaded["endpoint_health"] = {}
    return loaded


def write_detail_retry_scheduler_state(output_root: Path, state: dict, *, metadata_version: int) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    tmp_path = path.with_suffix(".json.tmp")
    serializable = dict(state)
    serializable["metadata_version"] = metadata_version
    tmp_path.write_text(json.dumps(serializable, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def update_detail_endpoint_health(
    endpoint_health: dict,
    *,
    now_ms: int,
    result_code: str,
    degraded_rate_threshold: float,
    degraded_min_sample: int,
    degraded_backoff_sec: int,
) -> dict:
    health = dict(endpoint_health)
    if "recent_detail_attempt_results" not in health:
        health["recent_detail_attempt_results"] = []

    # Record current result
    health["recent_detail_attempt_results"].append(result_code)
    # Keep only the last N samples
    max_samples = max(10, degraded_min_sample * 2)
    health["recent_detail_attempt_results"] = health["recent_detail_attempt_results"][-max_samples:]

    recent = health["recent_detail_attempt_results"]
    if len(recent) >= degraded_min_sample:
        transient_failures = sum(1 for r in recent if r in {"http_202_empty", "http_429", "http_5xx", "network_error"})
        error_rate = transient_failures / len(recent)
        health["detail_endpoint_transient_error_rate"] = error_rate
        if error_rate >= degraded_rate_threshold:
            health["detail_endpoint_degraded_until_ms"] = now_ms + degraded_backoff_sec * 1000
    else:
        health["detail_endpoint_transient_error_rate"] = 0.0

    return health

