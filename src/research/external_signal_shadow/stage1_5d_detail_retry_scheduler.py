import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from src.research.external_signal_shadow.stage1_5_storage_guard import require_storage_write

logger = logging.getLogger(__name__)

DETAIL_RETRY_SCHEDULER_STATE_FILENAME = "detail_retry_scheduler_state.json"
ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES = {
    "http_202_empty",
    "http_200_empty_untrusted_payload",
}

STAGE1_5D_V3_DURABLE_ARTICLE_KEYS = frozenset({
    "source_article_id",
    "title",
    "source_detail_url_normalized",
    "source_parent_url",
    "source_published_at_ms",
    "detected_at_ms",
    "first_detected_at_ms",
    "event_type",
    "detail_work_type",
    "catalog_id",
    "catalog_title",
    "symbol_extraction_source",
    "symbol_parse_failed_reason",
    "pending_reason",
    "source_published_at_ms_confidence",
    "detail_http_request_count",
    "detail_retry_cycle_count",
    "detail_fetch_attempt_count",
    "transient_detail_error_count",
    "non_transient_detail_error_count",
    "last_retry_at_ms",
    "next_detail_retry_at_ms",
    "first_deferred_at_ms",
    "last_deferred_at_ms",
    "last_deferred_manifest_at_ms",
    "defer_count",
    "terminal_state",
    "terminal_failure_type",
    "candidate_symbols",
    "symbol_derivation_method",
    "symbol_validation_status",
    "symbol_launch_times_ms",
    "symbol_onboard_times_ms",
    "symbol_effective_launch_times_ms",
    "launch_time_source",
    "last_detail_failure_class",
    "detail_retryable",
    "last_bapi_detail_status",
    "last_bapi_payload_hash",
    "last_bapi_parser_version",
    "last_bapi_parser_status",
    "last_bapi_parser_failure_reason",
    "last_bapi_parse_attempt_at_ms",
    "last_support_detail_status",
    "last_support_failure_class",
    "parsed_candidate_symbols",
    "candidate_provenance",
    "launch_time_resolution_status",
    "launch_anchor_policy",
    "required_launch_anchor_source",
    "consumable_event_allowed",
    "symbol_launch_time_candidates_ms",
    "launch_time_conflict_ms",
    "status",
    "terminal_reason",
    "terminal_at_ms",
    "emission_id",
    "candidate_symbol_set_hash",
    "candidate_symbol_set_hash_version",
    "candidate_symbols_ordered",
    "candidate_symbols_normalized",
    "event_id",
    "event_stream_path",
    "parser_payload_hash",
    "symbol_effective_launch_time_sources",
    "exchangeinfo_visible_symbols",
    "exchangeinfo_missing_symbols",
    "hard_rejected_symbols",
    "symbol_exchangeinfo_statuses",
    "inflight_cycle",
    "detail_budget_deferred_count",
    "detail_fetch_attempted",
    "detail_fetch_status",
    "detail_fetch_url_used",
    "detail_fetch_variant",
    "detail_fetched_at_ms",
    "detail_parse_status",
    "detail_payload_hash",
    "detail_payload_trusted",
    "exchangeinfo_validation_attempt_count",
    "exchangeinfo_validation_retryable",
    "last_exchangeinfo_validation_at_ms",
    "next_exchangeinfo_validation_at_ms",
    "quote_derivation_source",
    "retry_count",
    "schedule_revision_producer_status",
})

STAGE1_5D_V3_RUNTIME_ONLY_ARTICLE_ALIASES = frozenset({
    "raw",
    "symbols",
    "payload_sha256",
    "last_bapi_payload_sha256",
    "symbol_launch_times_utc",
    "symbol_effective_launch_times_utc",
})

STAGE1_5D_V3_ALLOWED_TERMINAL_REASONS = {
    "catalog_bootstrap_preexisting": None,
    "historical_prebootstrap_catalog_article": None,
    "source_published_at_invalid": None,
    "detail_never_attempted_budget_starved": "detail_never_attempted_budget_starved",
    "detail_unavailable_timeout": "detail_unavailable_timeout",
    "detail_retry_exhausted": "detail_retry_exhausted",
    "candidate_validation_rejected": "candidate_validation_rejected",
    "detail_source_url_rejected": "detail_source_url_rejected",
    "detail_success_symbols_empty": "detail_success_symbols_empty",
}

STAGE1_5D_V3_ALLOWED_ENDPOINT_RESULTS = frozenset({
    "success",
    "http_202_empty",
    "http_200_empty_untrusted_payload",
    "http_429",
    "http_5xx",
    "http_503",
    "network_error",
    "non_transient_error",
})

_HEX32_RE = re.compile(r"^[0-9a-f]{32}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_non_bool_int(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _is_non_negative_int(val: Any) -> bool:
    return _is_non_bool_int(val) and val >= 0


def _is_positive_int(val: Any) -> bool:
    return _is_non_bool_int(val) and val > 0


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def validate_stage1_5d_v3_scheduler_state(
    raw_state: object,
    *,
    expected_resume_provenance: dict[str, object],
) -> list[str]:
    blockers = []
    if not isinstance(raw_state, dict):
        return ["state_not_dict"]

    top_keys = set(raw_state.keys())
    expected_top_keys = {
        "metadata_version",
        "catalog_bootstrap_cutoff_ms",
        "resume_provenance",
        "articles",
        "endpoint_health",
    }
    if top_keys != expected_top_keys:
        missing = expected_top_keys - top_keys
        extra = top_keys - expected_top_keys
        if missing:
            blockers.append(f"top_level_missing_keys:{sorted(missing)}")
        if extra:
            blockers.append(f"top_level_unknown_keys:{sorted(extra)}")

    # 1. metadata_version
    mv = raw_state.get("metadata_version")
    if not _is_non_bool_int(mv) or mv != 3:
        blockers.append("metadata_version_not_3")

    # 2. catalog_bootstrap_cutoff_ms
    cutoff = raw_state.get("catalog_bootstrap_cutoff_ms")
    if not _is_positive_int(cutoff):
        blockers.append("catalog_bootstrap_cutoff_ms_invalid")

    # 3. resume_provenance
    prov = raw_state.get("resume_provenance")
    if not isinstance(prov, dict):
        blockers.append("resume_provenance_not_dict")
    else:
        expected_prov_keys = {
            "root_id",
            "scheduler_contract_version",
            "producer_startup_head_sha",
            "protected_tree_manifest_sha256",
            "configs_base_sha256",
        }
        if set(prov.keys()) != expected_prov_keys:
            blockers.append("resume_provenance_keys_invalid")
        if not (isinstance(prov.get("root_id"), str) and prov.get("root_id")):
            blockers.append("resume_provenance_root_id_invalid")
        if not (_is_non_bool_int(prov.get("scheduler_contract_version")) and prov.get("scheduler_contract_version") == 3):
            blockers.append("resume_provenance_scheduler_contract_version_invalid")
        head_sha = prov.get("producer_startup_head_sha")
        if not (isinstance(head_sha, str) and _HEX40_RE.match(head_sha)):
            blockers.append("resume_provenance_head_sha_invalid")
        tree_sha = prov.get("protected_tree_manifest_sha256")
        if not (isinstance(tree_sha, str) and _HEX64_RE.match(tree_sha)):
            blockers.append("resume_provenance_protected_tree_manifest_sha_invalid")
        cfg_sha = prov.get("configs_base_sha256")
        if not (isinstance(cfg_sha, str) and _HEX64_RE.match(cfg_sha)):
            blockers.append("resume_provenance_configs_base_sha_invalid")
        if expected_resume_provenance is not None and prov != expected_resume_provenance:
            blockers.append("resume_provenance_mismatch")

    # 4. articles
    articles = raw_state.get("articles")
    if not isinstance(articles, dict):
        blockers.append("articles_not_dict")
    else:
        for code, row in articles.items():
            if not (isinstance(code, str) and _HEX32_RE.match(code)):
                blockers.append(f"article_key_not_32_hex:{code}")
            if not isinstance(row, dict):
                blockers.append(f"article_row_not_dict:{code}")
                continue

            row_keys = set(row.keys())
            if row_keys != STAGE1_5D_V3_DURABLE_ARTICLE_KEYS:
                missing_keys = STAGE1_5D_V3_DURABLE_ARTICLE_KEYS - row_keys
                unknown_keys = row_keys - STAGE1_5D_V3_DURABLE_ARTICLE_KEYS
                if missing_keys:
                    blockers.append(f"article_missing_durable_keys:{code}:{sorted(missing_keys)}")
                if unknown_keys:
                    blockers.append(f"article_unknown_durable_keys:{code}:{sorted(unknown_keys)}")

            if row.get("source_article_id") != code:
                blockers.append(f"article_source_id_mismatch:{code}")
            if row.get("event_type") != "futures_contract_launch":
                blockers.append(f"article_event_type_invalid:{code}")

            pub_ms = row.get("source_published_at_ms")
            if pub_ms is not None and not _is_positive_int(pub_ms):
                blockers.append(f"article_source_published_at_ms_invalid:{code}")

            det_ms = row.get("detected_at_ms")
            first_det_ms = row.get("first_detected_at_ms")
            if not _is_positive_int(det_ms):
                blockers.append(f"article_detected_at_ms_invalid:{code}")
            if not _is_positive_int(first_det_ms):
                blockers.append(f"article_first_detected_at_ms_invalid:{code}")

            non_neg_int_fields = [
                "detail_http_request_count",
                "detail_retry_cycle_count",
                "detail_fetch_attempt_count",
                "transient_detail_error_count",
                "non_transient_detail_error_count",
                "last_retry_at_ms",
                "next_detail_retry_at_ms",
                "last_deferred_manifest_at_ms",
                "defer_count",
                "detail_budget_deferred_count",
                "exchangeinfo_validation_attempt_count",
                "retry_count",
            ]
            for fld in non_neg_int_fields:
                val = row.get(fld)
                if not _is_non_negative_int(val):
                    blockers.append(f"article_field_not_non_neg_int:{code}:{fld}")

            opt_non_neg_int_fields = [
                "first_deferred_at_ms",
                "last_deferred_at_ms",
                "last_bapi_parse_attempt_at_ms",
                "terminal_at_ms",
                "launch_time_conflict_ms",
                "candidate_symbol_set_hash_version",
                "detail_fetched_at_ms",
                "last_exchangeinfo_validation_at_ms",
                "next_exchangeinfo_validation_at_ms",
            ]
            for fld in opt_non_neg_int_fields:
                val = row.get(fld)
                if val is not None and not _is_non_negative_int(val):
                    blockers.append(f"article_field_not_opt_non_neg_int:{code}:{fld}")

            # Terminal relation
            term_state = row.get("terminal_state")
            if not isinstance(term_state, bool):
                blockers.append(f"article_terminal_state_not_bool:{code}")
            else:
                reason = row.get("terminal_reason")
                fail_type = row.get("terminal_failure_type")
                term_at = row.get("terminal_at_ms")
                inflight = row.get("inflight_cycle")
                if term_state:
                    if reason not in STAGE1_5D_V3_ALLOWED_TERMINAL_REASONS:
                        blockers.append(f"article_terminal_reason_invalid:{code}:{reason}")
                    else:
                        expected_fail_type = STAGE1_5D_V3_ALLOWED_TERMINAL_REASONS[reason]
                        if fail_type != expected_fail_type:
                            blockers.append(f"article_terminal_failure_type_mismatch:{code}")
                    if not _is_positive_int(term_at):
                        blockers.append(f"article_terminal_at_ms_invalid:{code}")
                    if inflight is not None:
                        blockers.append(f"article_terminal_inflight_not_null:{code}")
                else:
                    if reason is not None or fail_type is not None or term_at is not None:
                        blockers.append(f"article_non_terminal_has_terminal_fields:{code}")

            # Inflight cycle grammar
            inflight = row.get("inflight_cycle")
            if inflight is not None:
                if not isinstance(inflight, dict):
                    blockers.append(f"article_inflight_not_dict:{code}")
                else:
                    exp_inf_keys = {
                        "operation",
                        "cycle",
                        "request_ordinal",
                        "reserved_at_ms",
                        "symbol",
                        "request_target",
                        "request_identity",
                    }
                    if set(inflight.keys()) != exp_inf_keys:
                        blockers.append(f"article_inflight_keys_invalid:{code}")
                    op = inflight.get("operation")
                    if op not in ("detail_request", "exchangeinfo_request", "formal_emission"):
                        blockers.append(f"article_inflight_operation_invalid:{code}:{op}")
                    if not _is_positive_int(inflight.get("cycle")):
                        blockers.append(f"article_inflight_cycle_invalid:{code}")
                    if not _is_positive_int(inflight.get("request_ordinal")):
                        blockers.append(f"article_inflight_request_ordinal_invalid:{code}")
                    if not _is_positive_int(inflight.get("reserved_at_ms")):
                        blockers.append(f"article_inflight_reserved_at_ms_invalid:{code}")
                    sym = inflight.get("symbol")
                    if sym is not None and not (isinstance(sym, str) and sym == sym.strip().upper() and sym):
                        blockers.append(f"article_inflight_symbol_invalid:{code}")

                    target = inflight.get("request_target")
                    if not isinstance(target, dict):
                        blockers.append(f"article_inflight_target_not_dict:{code}")
                    else:
                        if op == "detail_request":
                            if set(target.keys()) != {"endpoint_kind", "source_article_id", "detail_fetch_variant", "requested_url"}:
                                blockers.append(f"article_inflight_detail_target_keys_invalid:{code}")
                            if target.get("endpoint_kind") not in ("bapi_article_detail_query", "support_article_detail"):
                                blockers.append(f"article_inflight_detail_endpoint_kind_invalid:{code}")
                            if target.get("source_article_id") != code:
                                blockers.append(f"article_inflight_detail_source_id_mismatch:{code}")
                            if target.get("detail_fetch_variant") not in ("bapi_article_detail_query", "primary", "detail_path_fallback"):
                                blockers.append(f"article_inflight_detail_variant_invalid:{code}")
                            if not (isinstance(target.get("requested_url"), str) and target.get("requested_url")):
                                blockers.append(f"article_inflight_detail_url_invalid:{code}")
                        elif op == "exchangeinfo_request":
                            if set(target.keys()) != {"endpoint", "consumer_symbols"}:
                                blockers.append(f"article_inflight_exchangeinfo_target_keys_invalid:{code}")
                            if target.get("endpoint") != "/fapi/v1/exchangeInfo":
                                blockers.append(f"article_inflight_exchangeinfo_endpoint_invalid:{code}")
                            csyms = target.get("consumer_symbols")
                            if not (isinstance(csyms, list) and csyms and csyms == sorted(set(csyms)) and all(isinstance(s, str) and s == s.strip().upper() for s in csyms)):
                                blockers.append(f"article_inflight_exchangeinfo_symbols_invalid:{code}")
                        elif op == "formal_emission":
                            if set(target.keys()) != {"event_id", "symbols"}:
                                blockers.append(f"article_inflight_formal_target_keys_invalid:{code}")
                            if not (isinstance(target.get("event_id"), str) and target.get("event_id")):
                                blockers.append(f"article_inflight_formal_event_id_invalid:{code}")
                            fsyms = target.get("symbols")
                            if not (isinstance(fsyms, list) and fsyms and fsyms == sorted(set(fsyms)) and all(isinstance(s, str) and s == s.strip().upper() for s in fsyms)):
                                blockers.append(f"article_inflight_formal_symbols_invalid:{code}")

                        # verify request_identity
                        ident_payload = {
                            "cycle": inflight.get("cycle"),
                            "operation": op,
                            "request_ordinal": inflight.get("request_ordinal"),
                            "request_target": target,
                            "source_article_id": code,
                            "symbol": sym,
                        }
                        exp_ident = hashlib.sha256(_canonical_json_bytes(ident_payload)).hexdigest()
                        if inflight.get("request_identity") != exp_ident:
                            blockers.append(f"article_inflight_request_identity_mismatch:{code}")

            # Candidate-set invariants (§6.1.2)
            c_ord = row.get("candidate_symbols_ordered")
            c_norm = row.get("candidate_symbols_normalized")
            c_ver = row.get("candidate_symbol_set_hash_version")
            c_hash = row.get("candidate_symbol_set_hash")
            c_all_null = c_ord is None and c_norm is None and c_ver is None and c_hash is None
            c_none_null = c_ord is not None and c_norm is not None and c_ver is not None and c_hash is not None
            if not (c_all_null or c_none_null):
                blockers.append(f"candidate_symbols_partial_null:{code}")
            elif c_none_null:
                if not (isinstance(c_ord, list) and c_ord and all(isinstance(s, str) and s == s.strip().upper() for s in c_ord) and len(c_ord) == len(set(c_ord))):
                    blockers.append(f"candidate_symbols_ordered_invalid:{code}")
                if c_norm != sorted(c_ord if isinstance(c_ord, list) else []):
                    blockers.append("candidate_symbols_normalized_mismatch")
                if c_ver != 1:
                    blockers.append("candidate_symbol_set_hash_version_invalid")
                exp_h = hashlib.sha256(json.dumps(c_norm, ensure_ascii=True, separators=(",", ":")).encode("utf-8")).hexdigest()
                if c_hash != exp_h:
                    blockers.append("candidate_symbol_set_hash_mismatch")

            # HTTP counter alias check
            http_cnt = row.get("detail_http_request_count")
            fetch_cnt = row.get("detail_fetch_attempt_count")
            if http_cnt < fetch_cnt:
                blockers.append("detail_request_counter_alias_mismatch")

    # 5. endpoint_health
    health = raw_state.get("endpoint_health")
    if not isinstance(health, dict):
        blockers.append("endpoint_health_not_dict")
    else:
        exp_health_keys = {
            "recent_detail_attempt_results",
            "detail_endpoint_degraded_until_ms",
            "detail_endpoint_transient_error_rate",
            "by_variant",
            "endpoint_health_by_source",
        }
        if set(health.keys()) != exp_health_keys:
            blockers.append("endpoint_health_keys_invalid")

        top_recent = health.get("recent_detail_attempt_results")
        if not (isinstance(top_recent, list) and len(top_recent) <= 10 and all(r in STAGE1_5D_V3_ALLOWED_ENDPOINT_RESULTS for r in top_recent)):
            blockers.append("endpoint_health_recent_results_invalid")

        top_degraded = health.get("detail_endpoint_degraded_until_ms")
        if not _is_non_negative_int(top_degraded):
            blockers.append("endpoint_health_degraded_until_ms_invalid")

        top_rate = health.get("detail_endpoint_transient_error_rate")
        if not (isinstance(top_rate, (int, float)) and not isinstance(top_rate, bool) and 0.0 <= float(top_rate) <= 1.0):
            blockers.append("endpoint_health_transient_error_rate_invalid")

        by_var = health.get("by_variant")
        if not isinstance(by_var, dict):
            blockers.append("endpoint_health_by_variant_not_dict")
        else:
            allowed_variants = {"bapi_article_detail_query", "support_article_detail", "primary", "detail_path_fallback"}
            for v_key, v_val in by_var.items():
                if v_key not in allowed_variants:
                    blockers.append(f"endpoint_health_by_variant_key_invalid:{v_key}")
                if not isinstance(v_val, dict) or set(v_val.keys()) != {"recent_detail_attempt_results", "detail_endpoint_degraded_until_ms", "detail_endpoint_transient_error_rate"}:
                    blockers.append(f"endpoint_health_by_variant_record_invalid:{v_key}")
                else:
                    rec = v_val.get("recent_detail_attempt_results")
                    if not (isinstance(rec, list) and len(rec) <= 10 and all(r in STAGE1_5D_V3_ALLOWED_ENDPOINT_RESULTS for r in rec)):
                        blockers.append(f"endpoint_health_by_variant_results_invalid:{v_key}")
                    if not _is_non_negative_int(v_val.get("detail_endpoint_degraded_until_ms")):
                        blockers.append(f"endpoint_health_by_variant_degraded_until_invalid:{v_key}")
                    r_val = v_val.get("detail_endpoint_transient_error_rate")
                    if not (isinstance(r_val, (int, float)) and not isinstance(r_val, bool) and 0.0 <= float(r_val) <= 1.0):
                        blockers.append(f"endpoint_health_by_variant_rate_invalid:{v_key}")

        by_src = health.get("endpoint_health_by_source")
        if not isinstance(by_src, dict):
            blockers.append("endpoint_health_by_source_not_dict")
        else:
            allowed_sources = {"bapi_article_detail_query", "support_article_detail"}
            for s_key, s_val in by_src.items():
                if s_key not in allowed_sources:
                    blockers.append(f"endpoint_health_by_source_key_invalid:{s_key}")
                if not isinstance(s_val, dict) or set(s_val.keys()) != {"recent_detail_attempt_results", "detail_endpoint_degraded_until_ms", "detail_endpoint_transient_error_rate"}:
                    blockers.append(f"endpoint_health_by_source_record_invalid:{s_key}")
                else:
                    rec = s_val.get("recent_detail_attempt_results")
                    if not (isinstance(rec, list) and len(rec) <= 10 and all(r in STAGE1_5D_V3_ALLOWED_ENDPOINT_RESULTS for r in rec)):
                        blockers.append(f"endpoint_health_by_source_results_invalid:{s_key}")
                    if not _is_non_negative_int(s_val.get("detail_endpoint_degraded_until_ms")):
                        blockers.append(f"endpoint_health_by_source_degraded_until_invalid:{s_key}")
                    r_val = s_val.get("detail_endpoint_transient_error_rate")
                    if not (isinstance(r_val, (int, float)) and not isinstance(r_val, bool) and 0.0 <= float(r_val) <= 1.0):
                        blockers.append(f"endpoint_health_by_source_rate_invalid:{s_key}")

        # Source mirror check
        if isinstance(by_src, dict) and isinstance(by_var, dict):
            for common_k in ("bapi_article_detail_query", "support_article_detail"):
                if common_k in by_src and common_k in by_var:
                    if by_src[common_k] != by_var[common_k]:
                        blockers.append("endpoint_health_source_mirror_mismatch")

    return blockers


def serialize_stage1_5d_v3_articles(articles: dict[str, dict]) -> dict[str, dict]:
    serialized = {}
    for code, row in articles.items():
        if not isinstance(row, dict):
            raise TypeError(f"article_row_not_dict:{code}")
        row_keys = set(row.keys())
        unknown_keys = row_keys - STAGE1_5D_V3_DURABLE_ARTICLE_KEYS - STAGE1_5D_V3_RUNTIME_ONLY_ARTICLE_ALIASES
        if unknown_keys:
            raise ValueError(f"unknown_runtime_article_key:{code}:{sorted(unknown_keys)}")

        projected = {k: row[k] for k in STAGE1_5D_V3_DURABLE_ARTICLE_KEYS if k in row}
        # ensure exact 86 keys
        if len(projected) != len(STAGE1_5D_V3_DURABLE_ARTICLE_KEYS):
            missing = STAGE1_5D_V3_DURABLE_ARTICLE_KEYS - set(projected.keys())
            raise ValueError(f"missing_durable_article_keys:{code}:{sorted(missing)}")
        serialized[code] = projected
    return serialized


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
