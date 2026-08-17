import json
import logging
import os
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write

logger = logging.getLogger(__name__)

DETAIL_RETRY_SCHEDULER_STATE_FILENAME = "detail_retry_scheduler_state.json"
ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES = {
    "http_202_empty",
    "http_200_empty_untrusted_payload",
}


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
    degraded_recent_article_window_ms: int | None = None,
    degraded_recent_retry_interval_ms: int | None = None,
    degraded_recent_retry_budget_per_poll: int = 0,
    degraded_recent_retry_max_cycles: int | None = None,
    max_first_attempt_delay_polls: int | None = None,
    max_first_attempt_delay_ms: int | None = None,
    overdue_attempted_retry_budget_per_poll: int = 0,
    overdue_attempted_min_interval_ms: int | None = None,
    min_never_attempted_slots_per_poll: int = 1,
) -> list[str]:
    if detail_budget_per_poll <= 0:
        return []

    never_attempted = []
    attempted = []
    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        if state.get("detail_fetch_status") == "not_needed" and not _not_needed_state_missing_launch_anchor(state):
            continue
        cycle_count = state.get("detail_retry_cycle_count")
        if cycle_count is None:
            cycle_count = state.get("detail_fetch_attempt_count")
        cnt = int(cycle_count or 0)
        if cnt <= 0:
            never_attempted.append((code, state))
        else:
            attempted.append((code, state))

    never_attempted.sort(
        key=lambda item: (
            0 if len(item[1].get("candidate_symbols") or item[1].get("symbols") or []) == 1 else
            (1 if len(item[1].get("candidate_symbols") or item[1].get("symbols") or []) > 1 else 2),
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
        selected_never = never_attempted[:detail_budget_per_poll]
        remaining_budget = detail_budget_per_poll - len(selected_never)
        if remaining_budget <= 0 or degraded_recent_retry_budget_per_poll <= 0:
            selected_attempted = []
        else:
            eligible_recent = []
            for code, state in attempted:
                if now_ms < int(state.get("next_detail_retry_at_ms") or 0):
                    continue
                first_detected_at_ms = int(state.get("first_detected_at_ms") or 0)
                if degraded_recent_article_window_ms is not None:
                    if now_ms - first_detected_at_ms > degraded_recent_article_window_ms:
                        continue
                cycle_count = int(state.get("detail_retry_cycle_count", state.get("detail_fetch_attempt_count", 0)) or 0)
                if degraded_recent_retry_max_cycles is not None:
                    if cycle_count >= degraded_recent_retry_max_cycles:
                        continue
                last_retry_at_ms = int(state.get("last_retry_at_ms") or 0)
                if degraded_recent_retry_interval_ms is not None:
                    if now_ms - last_retry_at_ms < degraded_recent_retry_interval_ms:
                        continue
                eligible_recent.append((code, state))

            eligible_recent.sort(
                key=lambda item: (
                    int(item[1].get("last_retry_at_ms") or 0),
                    int(item[1].get("transient_detail_error_count") or 0),
                    int(item[1].get("first_detected_at_ms") or 0),
                    item[0],
                )
            )
            selected_attempted = eligible_recent[:min(remaining_budget, degraded_recent_retry_budget_per_poll)]
        ordered = selected_never + selected_attempted
    else:
        # Endpoint degraded is not active
        selected_overdue = []
        if overdue_attempted_retry_budget_per_poll > 0:
            overdue_slots = min(
                overdue_attempted_retry_budget_per_poll,
                max(0, detail_budget_per_poll - (min_never_attempted_slots_per_poll if never_attempted else 0)),
            )
            if overdue_slots > 0:
                eligible_overdue = []
                for code, state in attempted:
                    next_retry = int(state.get("next_detail_retry_at_ms") or 0)
                    if next_retry <= 0:
                        continue
                    last_retry = int(state.get("last_retry_at_ms") or 0)
                    min_interval = overdue_attempted_min_interval_ms or 0
                    effective_due = max(next_retry, last_retry + min_interval)
                    if now_ms < effective_due:
                        continue

                    if not _is_overdue_detail_retryable(state):
                        continue

                    eligible_overdue.append((code, state))

                eligible_overdue.sort(
                    key=lambda item: (
                        int(item[1].get("next_detail_retry_at_ms") or 0),
                        int(item[1].get("last_retry_at_ms") or 0),
                        -int(item[1].get("transient_detail_error_count") or 0),
                        int(item[1].get("first_detected_at_ms") or 0),
                        item[0],
                    )
                )
                selected_overdue = eligible_overdue[:overdue_slots]

        selected_never = never_attempted[: detail_budget_per_poll - len(selected_overdue)]
        overdue_codes = {code for code, _ in selected_overdue}

        remaining_budget = detail_budget_per_poll - len(selected_never) - len(selected_overdue)
        remaining_attempted = []
        if remaining_budget > 0:
            eligible_attempted = []
            for code, state in attempted:
                if code in overdue_codes:
                    continue
                next_retry = int(state.get("next_detail_retry_at_ms") or 0)
                if next_retry <= 0 or now_ms < next_retry:
                    continue

                is_retryable = state.get("detail_retryable")
                if is_retryable is False:
                    continue
                if is_retryable is None and not _is_overdue_detail_retryable(state):
                    continue

                eligible_attempted.append((code, state))

            eligible_attempted.sort(
                key=lambda item: (
                    int(item[1].get("last_retry_at_ms") or 0),
                    int(item[1].get("transient_detail_error_count") or 0),
                    int(item[1].get("first_detected_at_ms") or 0),
                    item[0],
                )
            )
            remaining_attempted = eligible_attempted[:remaining_budget]


        ordered = selected_never + selected_overdue + remaining_attempted

    seen = set()
    result = []
    for code, _ in ordered:
        if code not in seen:
            seen.add(code)
            result.append(code)
    return result[:detail_budget_per_poll]


def _is_overdue_detail_retryable(state: dict) -> bool:
    if state.get("terminal_state"):
        return False
    if state.get("detail_retryable") is False:
        return False
    return state.get("last_detail_failure_class") in ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES


def _not_needed_state_missing_launch_anchor(state: dict) -> bool:
    candidates = state.get("candidate_symbols") or []
    if not candidates:
        return False
    launch_times = state.get("symbol_launch_times_ms") or {}
    effective_sources = state.get("symbol_effective_launch_time_sources") or {}
    for symbol in candidates:
        sym = str(symbol or "").strip().upper()
        if int(launch_times.get(sym) or 0) > 0:
            return False
        if str(effective_sources.get(sym) or "") in ("detail_symbol_launch_time", "exchangeinfo_onboard_date"):
            return False
    return True




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
            "detail_work_type": state.get("detail_work_type"),
            "catalog_id": state.get("catalog_id"),
            "catalog_title": state.get("catalog_title"),
            "symbol_extraction_source": state.get("symbol_extraction_source") or "none",
            "symbol_parse_failed_reason": state.get("symbol_parse_failed_reason"),
            "pending_reason": state.get("pending_reason") or "title_symbol_missing",
            "source_published_at_ms_confidence": state.get("source_published_at_ms_confidence") or "medium",
            "detail_http_request_count": int(state.get("detail_http_request_count") or 0),
            "detail_retry_cycle_count": int(state.get("detail_retry_cycle_count") or 0),
            "detail_fetch_attempt_count": int(state.get("detail_http_request_count") or state.get("detail_fetch_attempt_count") or 0),
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
            "last_detail_failure_class": state.get("last_detail_failure_class"),
            "detail_retryable": state.get("detail_retryable"),
            # Schema V2 new BAPI parser and anchor fields
            "last_bapi_detail_status": state.get("last_bapi_detail_status"),
            "last_bapi_payload_hash": state.get("last_bapi_payload_hash"),
            "last_bapi_parser_version": state.get("last_bapi_parser_version"),
            "last_bapi_parser_status": state.get("last_bapi_parser_status"),
            "last_bapi_parser_failure_reason": state.get("last_bapi_parser_failure_reason"),
            "last_bapi_parse_attempt_at_ms": state.get("last_bapi_parse_attempt_at_ms"),
            "last_support_detail_status": state.get("last_support_detail_status"),
            "last_support_failure_class": state.get("last_support_failure_class"),
            "parsed_candidate_symbols": state.get("parsed_candidate_symbols"),
            "candidate_provenance": state.get("candidate_provenance"),
            "launch_time_resolution_status": state.get("launch_time_resolution_status"),
            "launch_anchor_policy": state.get("launch_anchor_policy"),
            "required_launch_anchor_source": state.get("required_launch_anchor_source"),
            "consumable_event_allowed": state.get("consumable_event_allowed"),
            "symbol_launch_time_candidates_ms": state.get("symbol_launch_time_candidates_ms"),
            "launch_time_conflict_ms": state.get("launch_time_conflict_ms"),
            # Terminal emitted and candidate-set contract fields
            "status": state.get("status"),
            "terminal_reason": state.get("terminal_reason"),
            "terminal_at_ms": state.get("terminal_at_ms"),
            "emission_id": state.get("emission_id"),
            "candidate_symbol_set_hash": state.get("candidate_symbol_set_hash"),
            "candidate_symbol_set_hash_version": state.get("candidate_symbol_set_hash_version"),
            "candidate_symbols_ordered": state.get("candidate_symbols_ordered"),
            "candidate_symbols_normalized": state.get("candidate_symbols_normalized"),
            "event_id": state.get("event_id"),
            "event_stream_path": state.get("event_stream_path"),
            "parser_payload_hash": state.get("parser_payload_hash"),
            "symbol_effective_launch_time_sources": state.get("symbol_effective_launch_time_sources"),
            "exchangeinfo_visible_symbols": state.get("exchangeinfo_visible_symbols"),
            "exchangeinfo_missing_symbols": state.get("exchangeinfo_missing_symbols"),
            "hard_rejected_symbols": state.get("hard_rejected_symbols"),
            "symbol_exchangeinfo_statuses": state.get("symbol_exchangeinfo_statuses"),
            "inflight_cycle": state.get("inflight_cycle"),
        }
    return serialized


def load_detail_retry_scheduler_state(output_root: Path) -> dict:
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    if not path.exists():
        return {"metadata_version": 2, "articles": {}, "endpoint_health": {}}
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    if not isinstance(loaded.get("articles"), dict):
        loaded["articles"] = {}
    if not isinstance(loaded.get("endpoint_health"), dict):
        loaded["endpoint_health"] = {}

    for art in loaded["articles"].values():
        art.setdefault("last_bapi_detail_status", None)
        art.setdefault("last_bapi_payload_hash", None)
        art.setdefault("last_bapi_parser_version", None)
        art.setdefault("last_bapi_parser_status", None)
        art.setdefault("last_bapi_parser_failure_reason", None)
        art.setdefault("last_bapi_parse_attempt_at_ms", None)
        art.setdefault("last_support_detail_status", None)
        art.setdefault("last_support_failure_class", None)
        art.setdefault("parsed_candidate_symbols", None)
        art.setdefault("candidate_provenance", None)
        art.setdefault("launch_time_resolution_status", None)
        art.setdefault("launch_anchor_policy", None)
        art.setdefault("required_launch_anchor_source", None)
        art.setdefault("consumable_event_allowed", None)
        art.setdefault("symbol_launch_time_candidates_ms", None)
        art.setdefault("launch_time_conflict_ms", None)
        art.setdefault("detail_work_type", None)

    return loaded



def write_detail_retry_scheduler_state(
    output_root: Path,
    state: dict,
    *,
    storage_guard: Any,
    metadata_version: int = 2,
) -> dict:
    if storage_guard is None:
        raise TypeError("storage_guard_required")



    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / DETAIL_RETRY_SCHEDULER_STATE_FILENAME
    serializable = dict(state)
    serializable["metadata_version"] = metadata_version

    serialized_bytes = (json.dumps(serializable, sort_keys=True, indent=2) + "\n").encode("utf-8")
    old_size = path.stat().st_size if path.exists() else 0
    persistent_delta = len(serialized_bytes) - old_size
    transient_peak = len(serialized_bytes)

    pid = os.getpid()
    tmp_path = output_root / f".{DETAIL_RETRY_SCHEDULER_STATE_FILENAME}.atomic.{pid}.tmp"

    def _write_action():
        with open(tmp_path, "wb") as f:
            f.write(serialized_bytes)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)

        try:
            parent_fd = os.open(output_root, os.O_RDONLY)
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
        transient_failures = sum(
            1
            for r in recent
            if r in {"http_202_empty", "http_200_empty_untrusted_payload", "http_429", "http_5xx", "network_error"}
        )
        error_rate = transient_failures / len(recent)
        health["detail_endpoint_transient_error_rate"] = error_rate
        if error_rate >= degraded_rate_threshold:
            health["detail_endpoint_degraded_until_ms"] = now_ms + degraded_backoff_sec * 1000
    else:
        health["detail_endpoint_transient_error_rate"] = 0.0

    return health


def update_detail_endpoint_health_by_variant(
    endpoint_health: dict,
    *,
    now_ms: int,
    variant: str,
    result_code: str,
    degraded_rate_threshold: float,
    degraded_min_sample: int,
    degraded_backoff_sec: int,
) -> dict:
    health = dict(endpoint_health)
    if "by_variant" not in health:
        health["by_variant"] = {}

    if variant not in health["by_variant"]:
        health["by_variant"][variant] = {
            "recent_detail_attempt_results": [],
            "detail_endpoint_degraded_until_ms": 0,
            "detail_endpoint_transient_error_rate": 0.0,
        }

    var_health = dict(health["by_variant"][variant])
    if "recent_detail_attempt_results" not in var_health:
        var_health["recent_detail_attempt_results"] = []

    var_health["recent_detail_attempt_results"].append(result_code)
    max_samples = max(10, degraded_min_sample * 2)
    var_health["recent_detail_attempt_results"] = var_health["recent_detail_attempt_results"][-max_samples:]

    recent = var_health["recent_detail_attempt_results"]
    if len(recent) >= degraded_min_sample:
        transient_failures = sum(
            1
            for r in recent
            if r in {"http_202_empty", "http_200_empty_untrusted_payload", "http_429", "http_5xx", "network_error"}
        )
        error_rate = transient_failures / len(recent)
        var_health["detail_endpoint_transient_error_rate"] = error_rate
        if error_rate >= degraded_rate_threshold:
            var_health["detail_endpoint_degraded_until_ms"] = now_ms + degraded_backoff_sec * 1000
    else:
        var_health["detail_endpoint_transient_error_rate"] = 0.0

    health["by_variant"][variant] = var_health
    return health


def summarize_detail_retry_overdue_state(
    detail_retry_state: dict[str, dict],
    *,
    now_ms: int,
    warn_ms: int,
    hard_warn_ms: int,
    max_articles: int = 10,
) -> dict:
    overdue = []
    due_timestamp_missing_count = 0
    attempt_manifest_mismatch_count = 0
    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        next_retry = int(state.get("next_detail_retry_at_ms") or 0)
        http_count = int(state.get("detail_http_request_count") or 0)
        fetch_count = int(state.get("detail_fetch_attempt_count") or 0)
        if next_retry <= 0:
            if http_count > 0:
                due_timestamp_missing_count += 1
            if http_count == 0 and fetch_count > 0:
                attempt_manifest_mismatch_count += 1
            continue
        if now_ms < next_retry:
            continue
        overdue_ms = now_ms - next_retry
        attempt_manifest_mismatch = http_count == 0 and fetch_count > 0
        row = {
            "source_article_id": code,
            "title": state.get("title"),
            "overdue_ms": overdue_ms,
            "attempted": http_count > 0,
            "detail_http_request_count": http_count,
            "detail_fetch_attempt_count": fetch_count,
            "detail_attempt_manifest_mismatch": attempt_manifest_mismatch,
            "transient_detail_error_count": int(state.get("transient_detail_error_count") or 0),
            "next_detail_retry_at_ms": next_retry,
            "pending_reason": state.get("pending_reason"),
            "candidate_symbols": state.get("candidate_symbols"),
        }
        overdue.append(row)

    overdue.sort(key=lambda r: (-r["overdue_ms"], r["source_article_id"]))
    oldest = overdue[0]["overdue_ms"] if overdue else 0
    return {
        "detail_retry_overdue_pending_count": len(overdue),
        "detail_retry_overdue_attempted_count": sum(1 for r in overdue if r["attempted"]),
        "detail_retry_overdue_never_attempted_count": sum(1 for r in overdue if not r["attempted"]),
        "detail_retry_due_timestamp_missing_count": due_timestamp_missing_count,
        "detail_attempt_manifest_mismatch_count": attempt_manifest_mismatch_count + sum(1 for r in overdue if r["detail_attempt_manifest_mismatch"]),
        "legacy_attempt_count_fallback_used": False,
        "detail_retry_oldest_overdue_ms": oldest,
        "detail_retry_overdue_warn_active": oldest >= warn_ms if oldest else False,
        "detail_retry_overdue_hard_warn_active": oldest >= hard_warn_ms if oldest else False,
        "detail_retry_overdue_articles": overdue[:max_articles],
    }


def update_detail_endpoint_health_by_source(
    endpoint_health: dict,
    *,
    now_ms: int,
    source: str,
    result_code: str,
    degraded_rate_threshold: float = 0.8,
    degraded_min_sample: int = 1,
    degraded_backoff_sec: int = 900,
) -> dict:
    health = dict(endpoint_health)
    if "endpoint_health_by_source" not in health:
        health["endpoint_health_by_source"] = {}

    if source not in health["endpoint_health_by_source"]:
        health["endpoint_health_by_source"][source] = {
            "recent_detail_attempt_results": [],
            "detail_endpoint_degraded_until_ms": 0,
            "detail_endpoint_transient_error_rate": 0.0,
        }

    src_health = dict(health["endpoint_health_by_source"][source])
    if "recent_detail_attempt_results" not in src_health:
        src_health["recent_detail_attempt_results"] = []

    src_health["recent_detail_attempt_results"].append(result_code)
    max_samples = max(10, degraded_min_sample * 2)
    src_health["recent_detail_attempt_results"] = src_health["recent_detail_attempt_results"][-max_samples:]

    recent = src_health["recent_detail_attempt_results"]
    if len(recent) >= degraded_min_sample:
        transient_failures = sum(
            1
            for r in recent
            if r in {"http_202_empty", "http_200_empty_untrusted_payload", "http_429", "http_5xx", "http_503", "network_error"}
        )
        error_rate = transient_failures / len(recent)
        src_health["detail_endpoint_transient_error_rate"] = error_rate
        if error_rate >= degraded_rate_threshold:
            src_health["detail_endpoint_degraded_until_ms"] = now_ms + degraded_backoff_sec * 1000
    else:
        src_health["detail_endpoint_transient_error_rate"] = 0.0

    health["endpoint_health_by_source"][source] = src_health

    # Mirror in by_variant for backward compatibility
    if "by_variant" not in health:
        health["by_variant"] = {}
    health["by_variant"][source] = src_health

    return health


def is_detail_source_degraded(endpoint_health: dict, source: str, now_ms: int) -> bool:
    if not isinstance(endpoint_health, dict):
        return False
    by_source = endpoint_health.get("endpoint_health_by_source") or endpoint_health.get("by_variant") or {}
    source_aliases = {
        "support_article_detail": ("support_article_detail", "support_announcement_detail"),
        "support_announcement_detail": ("support_article_detail", "support_announcement_detail"),
    }
    for candidate_source in source_aliases.get(source, (source,)):
        if by_source and candidate_source in by_source:
            src_data = by_source[candidate_source]
            degraded_until = src_data.get("degraded_until_ms") or src_data.get("detail_endpoint_degraded_until_ms") or 0
            return bool(degraded_until > now_ms)
    if source == "bapi_article_detail_query":
        return False
    if source in ("support_article_detail", "support_announcement_detail"):
        top_degraded = endpoint_health.get("detail_endpoint_degraded_until_ms") or 0
        return bool(top_degraded > now_ms)
    if by_source and source in by_source:
        src_data = by_source[source]
        degraded_until = src_data.get("degraded_until_ms") or src_data.get("detail_endpoint_degraded_until_ms") or 0
        return bool(degraded_until > now_ms)
    return False




def summarize_detail_source_health(endpoint_health: dict, now_ms: int) -> dict:
    bapi_degraded = is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", now_ms)
    support_degraded = is_detail_source_degraded(endpoint_health, "support_article_detail", now_ms)
    return {
        "bapi_detail_source_degraded": bapi_degraded,
        "support_detail_source_degraded": support_degraded,
        "all_detail_sources_degraded": bapi_degraded and support_degraded,
    }


def classify_detail_source_failure(
    source: str,
    http_status: int | None = None,
    error: str | None = None,
) -> dict:
    err_str = str(error or "")

    if http_status in (400, 404) or err_str in ("bapi_api_code_non_000000", "bapi_article_illegal_parameter"):
        return {
            "retryable": False,
            "terminal_reason": err_str or f"{source}_http_{http_status}",
            "support_fallback_allowed": True,
            "integrity_alert": False,
            "breaker_source": None,
        }

    if err_str == "bapi_article_identity_mismatch":
        return {
            "retryable": False,
            "terminal_reason": err_str,
            "support_fallback_allowed": True,
            "integrity_alert": True,
            "breaker_source": None,
        }

    if (
        http_status in (429, 500, 502, 503, 504)
        or "timeout" in err_str.lower()
        or err_str in ("bapi_http_non_200", "bapi_http_non_429", "http_503")
    ):
        return {
            "retryable": True,
            "terminal_reason": None,
            "support_fallback_allowed": True,
            "integrity_alert": False,
            "breaker_source": source,
        }

    return {
        "retryable": False,
        "terminal_reason": err_str or "unknown_source_failure",
        "support_fallback_allowed": True,
        "integrity_alert": False,
        "breaker_source": None,
    }
