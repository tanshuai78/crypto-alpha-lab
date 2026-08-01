import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path


from configs import base
from src.research.external_signal_shadow.stage1_5_launch_event_contract import (
    build_formal_launch_event,
    coerce_legacy_launch_event_to_formal,
    validate_formal_launch_event,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_client import (
    build_announcement_list_url,
    fetch_public_json,
    fetch_public_payload,
    validate_announcement_detail_url,
    build_announcement_detail_fallback_urls,
    build_bapi_article_detail_url,
    fetch_public_bapi_article_detail,
    validate_bapi_article_detail_payload,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_collector import (
    run_one_poll_cycle,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_evidence import (
    validate_upstream_evidence,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_first_bar import (
    check_first_bar_for_event,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
    PARSER_VERSION,
    SYMBOL_EXTRACTION_VERSION,
    LAUNCH_SCHEDULE_PARSER_VERSION,
    extract_symbol_candidates_from_detail_payload,
    extract_symbol_candidates_from_bapi_article_payload,
    normalize_live_event,
    extract_symbol_candidates_from_title,
)

from src.research.external_signal_shadow.stage1_5d_live_event_source_storage import (
    append_jsonl,
    build_stream_paths,
    enforce_payload_budget,
    write_detail_payload,
    write_detail_payload_append_only,
)
from src.research.external_signal_shadow.stage1_5d_live_event_source_summary import (
    build_smoke_summary,
)
from src.research.external_signal_shadow.stage1_5d_detail_retry_scheduler import (
    ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES,
    select_detail_retry_attempts,
    compute_detail_transient_backoff_ms,
    serialize_retry_articles,
    load_detail_retry_scheduler_state,
    write_detail_retry_scheduler_state,
    classify_never_attempted_defer_state,
    update_detail_endpoint_health,
    update_detail_endpoint_health_by_variant,
    update_detail_endpoint_health_by_source,
    is_detail_source_degraded,
    summarize_detail_source_health,
    classify_detail_source_failure,
    summarize_detail_retry_overdue_state,
)
from src.research.external_signal_shadow.stage1_5d_runtime_gate import (
    build_stage1_5d_runtime_gate,
    write_stage1_5d_runtime_gate,
    get_stage1_5d_runtime_gate_filename,
)


def append_stage1_5d_diagnostic(stream_paths: dict, row: dict) -> None:
    diagnostics_path = stream_paths.get("detail_retry_terminal_diagnostics")
    if diagnostics_path is None:
        diagnostics_path = stream_paths.get("diagnostics")
    if diagnostics_path is None:
        return
    append_jsonl(diagnostics_path, row)


def append_formal_futures_launch_event(stream_paths: dict, row: dict) -> dict | None:
    row = coerce_legacy_launch_event_to_formal(row)
    validation = validate_formal_launch_event(row)
    if not validation["valid"]:
        append_stage1_5d_diagnostic(
            stream_paths,
            {
                "diagnostic_stream": "formal_contract_validation_failed",
                "diagnostic_type": "formal_event_contract_invalid",
                "formal_contract_blockers": validation.get("blockers", []),
                "source_article_id": row.get("source_article_id"),
                "event_id": row.get("event_id"),
                "symbols": row.get("symbols"),
                "parser_version": row.get("parser_version"),
                "symbol_extraction_version": row.get("symbol_extraction_version"),
                "raw_event": row,
            },
        )
        return None
    append_jsonl(stream_paths["events"], row)
    return row


def record_formal_futures_launch_event(
    *,
    stream_paths: dict,
    row: dict,
    seen_event_ids: set,
    events_detected: list,
) -> dict | None:
    event_id = row.get("event_id")
    if event_id in seen_event_ids:
        return None
    written = append_formal_futures_launch_event(stream_paths, row)
    if written is None:
        return None
    seen_event_ids.add(written["event_id"])
    events_detected.append(written)
    return written





def validate_candidate_symbols_against_exchangeinfo(
    candidates: list[str],
    exchangeinfo_by_symbol: dict[str, dict],
    allowed_margin_assets: tuple[str, ...],
    allowed_quote_assets: tuple[str, ...],
    allowed_contract_types: tuple[str, ...],
    validatable_statuses: tuple[str, ...],
    emittable_statuses: tuple[str, ...],
    now_ms: int,
) -> dict:
    validated_symbols = []
    pending_symbols = []
    rejected_symbols = []
    pending_reasons = {}
    rejection_reasons = {}
    symbol_exchangeinfo = {}
    symbol_onboard_times_ms = {}

    for c in candidates:
        target_symbol = c
        if target_symbol not in exchangeinfo_by_symbol:
            pending_symbols.append(c)
            pending_reasons[c] = "exchange_info_symbol_missing"
            continue
        
        meta = exchangeinfo_by_symbol[target_symbol]
        required_keys = ("status", "contractType", "quoteAsset", "marginAsset")
        if not all(k in meta for k in required_keys):
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_incomplete_metadata"
            continue
        
        if meta.get("contractType") not in allowed_contract_types:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_contract_type"
            continue
            
        if meta.get("marginAsset") not in allowed_margin_assets:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_margin_asset"
            continue
            
        if meta.get("quoteAsset") not in allowed_quote_assets:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_disallowed_quote_asset"
            continue

        status = meta.get("status")
        if status in emittable_statuses:
            validated_symbols.append(target_symbol)
            symbol_exchangeinfo[target_symbol] = meta
            if "onboardDate" in meta:
                try:
                    symbol_onboard_times_ms[target_symbol] = int(meta["onboardDate"])
                except (ValueError, TypeError):
                    pass
        elif status in validatable_statuses:
            pending_symbols.append(c)
            pending_reasons[c] = "exchange_info_symbol_status_not_trading_prelaunch"
            symbol_exchangeinfo[target_symbol] = meta
            if "onboardDate" in meta:
                try:
                    symbol_onboard_times_ms[target_symbol] = int(meta["onboardDate"])
                except (ValueError, TypeError):
                    pass
        else:
            rejected_symbols.append(c)
            rejection_reasons[c] = "exchange_info_unrecognized_status"


    return {
        "validated_symbols": validated_symbols,
        "pending_symbols": pending_symbols,
        "rejected_symbols": rejected_symbols,
        "pending_reasons": pending_reasons,
        "rejection_reasons": rejection_reasons,
        "symbol_exchangeinfo": symbol_exchangeinfo,
        "symbol_onboard_times_ms": symbol_onboard_times_ms,
    }


def build_effective_launch_times_ms(
    candidate_symbols: list[str],
    symbol_onboard_times_ms: dict,
    symbol_launch_times_ms: dict,
    source_published_at_ms: int,
    first_detected_at_ms: int,
    allow_release_date_fallback: bool = True,
    allow_legacy_max_age_fallback: bool = True,
) -> dict:
    effective = {}
    per_symbol_sources = {}
    sources = set()
    for s in candidate_symbols:
        if s in symbol_onboard_times_ms and symbol_onboard_times_ms[s] > 0:
            effective[s] = symbol_onboard_times_ms[s]
            per_symbol_sources[s] = "exchangeinfo_onboard_date"
            sources.add("exchange_info")
        elif s in symbol_launch_times_ms and symbol_launch_times_ms[s] > 0:
            effective[s] = symbol_launch_times_ms[s]
            per_symbol_sources[s] = "detail_symbol_launch_time"
            sources.add("detail")
        elif allow_release_date_fallback and source_published_at_ms > 0:
            effective[s] = source_published_at_ms
            per_symbol_sources[s] = "article_release_date"
            sources.add("article_release_date")
        elif allow_legacy_max_age_fallback:
            legacy_max_age_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 3600) * 1000
            effective[s] = first_detected_at_ms + legacy_max_age_ms
            per_symbol_sources[s] = "legacy_max_age"
            sources.add("legacy_max_age")
        else:
            effective[s] = 0
            per_symbol_sources[s] = "none"
            sources.add("none")

    if "exchange_info" in sources:
        source_str = "exchange_info"
    elif "detail" in sources:
        source_str = "detail"
    elif "article_release_date" in sources:
        source_str = "article_release_date"
    elif "legacy_max_age" in sources:
        source_str = "legacy_max_age"
    else:
        source_str = "none"

    return {
        "symbol_effective_launch_times_ms": effective,
        "launch_time_source": source_str,
        "symbol_effective_launch_time_sources": per_symbol_sources,
    }


def build_candidate_symbol_set_identity(candidate_symbols: list[str]) -> dict:
    ordered = []
    seen = set()
    for sym in candidate_symbols or []:
        norm = str(sym or "").strip().upper()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        ordered.append(norm)
    normalized = sorted(ordered)
    payload = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"))
    return {
        "candidate_symbols_ordered": ordered,
        "candidate_symbols_normalized": normalized,
        "candidate_symbol_set_hash_version": 1,
        "candidate_symbol_set_hash": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def is_multi_symbol_article_state(state: dict, extraction_result: dict | None = None) -> bool:
    if extraction_result and extraction_result.get("symbols"):
        ext_symbols = list(extraction_result.get("symbols") or [])
        if len(ext_symbols) > 1:
            return True
    if state.get("candidate_symbols") is not None:
        return len(state.get("candidate_symbols") or []) > 1
    if state.get("parsed_candidate_symbols") is not None:
        return len(state.get("parsed_candidate_symbols") or []) > 1
    if state.get("candidate_symbols_ordered") is not None:
        return len(state.get("candidate_symbols_ordered") or []) > 1
    symbols = state.get("symbols")
    if symbols and isinstance(symbols, (list, tuple)):
        return len(symbols) > 1
    return False


def build_symbol_effective_launch_time_sources(
    candidate_symbols: list[str],
    symbol_launch_times_ms: dict,
    symbol_onboard_times_ms: dict,
    effective_launch: dict,
) -> dict[str, str]:
    res = {}
    eff_times = (effective_launch or {}).get("symbol_effective_launch_times_ms") or {}
    eff_sources = (effective_launch or {}).get("symbol_effective_launch_time_sources") or {}
    for sym in candidate_symbols or []:
        norm = str(sym or "").strip().upper()
        if not norm:
            continue
        if norm in eff_sources:
            res[norm] = eff_sources[norm]
        elif int((symbol_launch_times_ms or {}).get(norm) or 0) > 0:
            res[norm] = "detail_symbol_launch_time"
        elif int((symbol_onboard_times_ms or {}).get(norm) or 0) > 0:
            res[norm] = "exchangeinfo_onboard_date"
        elif int(eff_times.get(norm) or 0) > 0:
            res[norm] = "effective_launch_time"
        else:
            res[norm] = "none"
    return res


def is_multi_symbol_candidate_set_ready_to_emit(
    candidate_symbols: list[str],
    validation_result: dict,
    effective_launch_times: dict,
    allowed_anchor_sources: tuple[str, ...] = (
        "detail_symbol_launch_time",
        "exchangeinfo_onboard_date",
    ),
) -> bool:
    candidates = [str(s or "").strip().upper() for s in (candidate_symbols or []) if str(s or "").strip()]
    if len(candidates) <= 1:
        return False
    candidate_set = set(candidates)
    if len(candidate_set) != len(candidates):
        return False

    validated = set(validation_result.get("validated_symbols") or [])
    pending = set(validation_result.get("pending_symbols") or [])
    rejected = list(validation_result.get("rejected_symbols") or [])

    if rejected:
        return False

    if validated & pending != set():
        return False
    if (validated | pending) != candidate_set:
        return False

    symbol_exchangeinfo = validation_result.get("symbol_exchangeinfo") or {}
    launch_times = (effective_launch_times or {}).get("symbol_effective_launch_times_ms") or {}
    anchor_sources = (effective_launch_times or {}).get("symbol_effective_launch_time_sources")
    if not anchor_sources:
        top_source = (effective_launch_times or {}).get("launch_time_source")
        if top_source in ("detail", "exchange_info"):
            anchor_sources = {sym: top_source for sym in candidates}
        else:
            anchor_sources = build_symbol_effective_launch_time_sources(candidates, {}, {}, effective_launch_times)

    allowed_statuses = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES", ("PENDING_TRADING", "PRE_TRADING", "TRADING"))
    pending_reasons = validation_result.get("pending_reasons") or {}
    for sym in candidates:
        if str(pending_reasons.get(sym) or "").startswith("exchange_info_symbol_missing") or pending_reasons.get(sym) == "exchange_info_missing":
            return False

        meta = symbol_exchangeinfo.get(sym)
        if meta:
            status = meta.get("status")
        elif sym in validated:
            status = "TRADING"
        elif sym in pending:
            status = "PENDING_TRADING"
        else:
            return False

        if status not in allowed_statuses:
            return False

        t = int(launch_times.get(sym) or 0)
        if t <= 0:
            return False

        src = str(anchor_sources.get(sym) or "").strip()
        if src not in allowed_anchor_sources:
            return False

    return True


def is_multi_symbol_article_ready_to_emit(
    candidate_symbols: list[str],
    validation_result: dict,
    effective_launch: dict,
    state: dict | None = None,
) -> bool:
    return is_multi_symbol_candidate_set_ready_to_emit(candidate_symbols, validation_result, effective_launch)


def build_multi_symbol_emission_id(source_article_id: str, event_type: str, candidate_symbol_set_hash: str) -> str:
    schema_version = 1
    namespace = "binance_futures_announcement"
    raw_key = f"{schema_version}|{namespace}|{event_type}|{source_article_id}|{candidate_symbol_set_hash}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def apply_multi_symbol_candidate_set_contract(
    norm_event: dict,
    state: dict,
    validation_result: dict,
    symbols_override: list[str],
    identity: dict,
    emission_id: str,
    effective_launch: dict,
    now_ms: int,
) -> None:
    norm_event["multi_symbol_emission_mode"] = "all_or_none_candidate_set"
    norm_event["multi_symbol_candidate_set_hash"] = identity["candidate_symbol_set_hash"]
    norm_event["candidate_symbol_set_hash_version"] = identity["candidate_symbol_set_hash_version"]
    norm_event["candidate_symbols_ordered"] = identity["candidate_symbols_ordered"]
    norm_event["candidate_symbols_normalized"] = identity["candidate_symbols_normalized"]
    norm_event["emission_id"] = emission_id
    norm_event["symbol_validation_status"] = "validated_candidate_set"
    norm_event["symbol_exchangeinfo_statuses"] = {
        s: validation_result.get("symbol_exchangeinfo", {}).get(s, {}).get("status")
        for s in symbols_override
    }
    norm_event["symbol_effective_launch_time_sources"] = (
        effective_launch.get("symbol_effective_launch_time_sources") or {}
    )
    norm_event["launch_anchor_policy"] = "bapi_multi_contract_strict"

    state["terminal_state"] = True
    state["terminal_reason"] = "multi_symbol_candidate_set_emitted"
    state["terminal_at_ms"] = now_ms
    state["status"] = "emitted_all_symbols"
    state["symbol_validation_status"] = "emitted_all_symbols"
    state["emission_id"] = emission_id
    state["candidate_symbol_set_hash"] = identity["candidate_symbol_set_hash"]
    state["candidate_symbol_set_hash_version"] = identity["candidate_symbol_set_hash_version"]
    state["candidate_symbols_ordered"] = identity["candidate_symbols_ordered"]
    state["candidate_symbols_normalized"] = identity["candidate_symbols_normalized"]
    state["symbol_effective_launch_time_sources"] = norm_event["symbol_effective_launch_time_sources"]
    state["symbol_exchangeinfo_statuses"] = norm_event["symbol_exchangeinfo_statuses"]
    state["launch_anchor_policy"] = norm_event["launch_anchor_policy"]


def build_emission_index_key(source_article_id: str, candidate_symbol_set_hash: str) -> str:
    return f"{source_article_id}|{candidate_symbol_set_hash}"


def validate_emitted_candidate_set_event_row(row: dict) -> tuple[bool, str, dict]:
    source_article_id = str(row.get("source_article_id") or "").strip()
    if not source_article_id:
        return False, "missing_source_article_id", {}

    symbols = list(row.get("symbols") or [])
    if len(symbols) <= 1 and row.get("multi_symbol_emission_mode") != "all_or_none_candidate_set":
        return False, "not_candidate_set_event_row", {}
    if len(symbols) <= 1:
        return False, "missing_symbols", {}

    mode = row.get("multi_symbol_emission_mode")
    if mode != "all_or_none_candidate_set":
        return False, "invalid_multi_symbol_emission_mode", {}
    if row.get("symbol_validation_status") != "validated_candidate_set":
        return False, "invalid_candidate_set_validation_status", {}
    if row.get("event_type") != "futures_contract_launch":
        return False, "invalid_event_type", {}

    identity = build_candidate_symbol_set_identity(symbols)
    computed_hash = identity["candidate_symbol_set_hash"]
    stored_hash = row.get("multi_symbol_candidate_set_hash")
    if not stored_hash:
        return False, "missing_candidate_set_hash", {}
    if stored_hash != computed_hash:
        return False, "candidate_set_hash_mismatch", {}

    event_type = str(row.get("event_type") or "futures_contract_launch")
    computed_emission_id = build_multi_symbol_emission_id(source_article_id, event_type, computed_hash)
    stored_emission_id = row.get("emission_id")
    if not stored_emission_id:
        return False, "missing_emission_id", {}
    if stored_emission_id != computed_emission_id:
        return False, "emission_id_mismatch", {}

    key = build_emission_index_key(source_article_id, computed_hash)
    info = {
        "key": key,
        "source_article_id": source_article_id,
        "candidate_symbol_set_hash": computed_hash,
        "emission_id": computed_emission_id,
        "event_id": row.get("event_id"),
        "symbols": symbols,
        "parser_payload_hash": row.get("parser_payload_hash"),
    }
    return True, "valid", info


def rebuild_emission_index_from_events(output_root: Path) -> tuple[dict, list[dict]]:
    index = {}
    diagnostics = []
    events_dir = Path(output_root) / "events"
    if not events_dir.exists():
        return index, diagnostics

    seen_emission_ids = {}

    for event_file in sorted(events_dir.glob("*.jsonl")):
        try:
            lines = event_file.read_text(encoding="utf-8").splitlines()
        except Exception as e:
            diagnostics.append({"file": str(event_file), "reason": f"read_error: {e}"})
            continue

        for line_no, line in enumerate(lines, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                row = json.loads(line_str)
            except Exception:
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": "malformed_jsonl",
                })
                continue

            valid, reason, info = validate_emitted_candidate_set_event_row(row)
            if not valid:
                if reason == "not_candidate_set_event_row":
                    continue
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": reason,
                    "source_article_id": row.get("source_article_id"),
                })
                continue

            em_id = info["emission_id"]
            if em_id in seen_emission_ids and seen_emission_ids[em_id] != info["parser_payload_hash"]:
                diagnostics.append({
                    "file": str(event_file),
                    "line": line_no,
                    "reason": "duplicate_emission_id_different_payload",
                    "emission_id": em_id,
                })
                continue
            seen_emission_ids[em_id] = info["parser_payload_hash"]

            try:
                rel_path = str(event_file.relative_to(output_root))
            except ValueError:
                rel_path = str(event_file)
            info["event_stream_path"] = rel_path
            index[info["key"]] = info

    return index, diagnostics


def check_article_emission_eligibility(
    state: dict,
    validation_result: dict,
    effective_launch: dict,
    extraction_res: dict | None = None,
) -> tuple[bool, bool, list[str]]:
    is_multi = is_multi_symbol_article_state(state, extraction_res)
    if is_multi:
        candidates = state.get("candidate_symbols") or (extraction_res.get("symbols") if extraction_res else None) or []
        ready = is_multi_symbol_candidate_set_ready_to_emit(candidates, validation_result, effective_launch)
        return ready, True, list(candidates)
    else:
        valid_symbols = list(validation_result.get("validated_symbols") or [])
        effective_times = (effective_launch or {}).get("symbol_effective_launch_times_ms") or {}
        effective_sources = (effective_launch or {}).get("symbol_effective_launch_time_sources") or {}
        ready_symbols = []
        for sym in valid_symbols:
            norm = str(sym or "").strip().upper()
            if int(effective_times.get(norm) or 0) <= 0:
                continue
            if str(effective_sources.get(norm) or "") not in ("detail_symbol_launch_time", "exchangeinfo_onboard_date"):
                continue
            ready_symbols.append(norm)
        return bool(ready_symbols), False, ready_symbols


def title_candidate_needs_detail_launch_anchor(state: dict) -> bool:
    if state.get("detail_fetch_attempted"):
        return False
    if state.get("detail_fetch_status") not in (None, "", "not_needed"):
        return False
    if state.get("symbol_extraction_source") not in ("title", "title_contract_symbol", "title_base_asset_derived"):
        return False
    candidates = state.get("candidate_symbols") or []
    if not candidates:
        return False
    launch_times = state.get("symbol_launch_times_ms") or {}
    effective_sources = state.get("symbol_effective_launch_time_sources") or {}
    for sym in candidates:
        norm = str(sym or "").strip().upper()
        if int(launch_times.get(norm) or 0) > 0:
            return False
        if str(effective_sources.get(norm) or "") in ("detail_symbol_launch_time", "exchangeinfo_onboard_date"):
            return False
    return True


def apply_formal_launch_event_contract(
    norm_event: dict,
    state: dict,
    validation_result: dict,
    symbols_override: list[str],
    effective_launch: dict,
) -> None:
    symbols = [str(s or "").strip().upper() for s in symbols_override if str(s or "").strip()]
    launch_times = dict(state.get("symbol_launch_times_ms") or {})
    onboard_times = dict(state.get("symbol_onboard_times_ms") or validation_result.get("symbol_onboard_times_ms") or {})
    effective_times = dict((effective_launch or {}).get("symbol_effective_launch_times_ms") or {})
    sources = dict((effective_launch or {}).get("symbol_effective_launch_time_sources") or {})

    norm_event["symbol_launch_times_ms"] = launch_times
    norm_event["symbol_onboard_times_ms"] = onboard_times
    norm_event["symbol_effective_launch_times_ms"] = effective_times
    norm_event["symbol_launch_time_candidates_ms"] = {
        sym: launch_times.get(sym) or onboard_times.get(sym) or effective_times.get(sym)
        for sym in symbols
        if int((launch_times.get(sym) or onboard_times.get(sym) or effective_times.get(sym) or 0)) > 0
    }
    norm_event["symbol_effective_launch_time_sources"] = sources
    norm_event["launch_time_source"] = (effective_launch or {}).get("launch_time_source")
    norm_event["formal_event_contract_version"] = 1
    norm_event["formal_event_consumable_by_stage1_5f"] = True
    norm_event["source_contract_status"] = "formal_v1_valid"
    norm_event["symbol_identity_validation_status"] = "validated_by_exchangeinfo"
    norm_event["launch_anchor_validation_status"] = "valid"

    detail_status = str(norm_event.get("detail_fetch_status") or state.get("detail_fetch_status") or "")
    detail_attempted = bool(norm_event.get("detail_fetch_attempted", state.get("detail_fetch_attempted", False)))
    has_detail = all(int(launch_times.get(sym) or 0) > 0 for sym in symbols)
    has_onboard = all(int(onboard_times.get(sym) or 0) > 0 for sym in symbols)

    norm_event["detail_fetch_attempted"] = detail_attempted
    norm_event["detail_fetch_status"] = detail_status

    if has_detail and has_onboard:
        disagreement_ms = max(abs(int(launch_times[sym]) - int(onboard_times[sym])) for sym in symbols)
        tolerance_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS", 60000)
        if disagreement_ms <= tolerance_ms:
            norm_event["launch_anchor_evidence_level"] = "detail_exchangeinfo_consensus"
            norm_event["launch_anchor_comparison_status"] = "consensus"
            norm_event["launch_anchor_disagreement_ms"] = disagreement_ms
            norm_event["detail_confirmation_missing"] = False
        else:
            norm_event["launch_anchor_evidence_level"] = "detail_confirmed"
            norm_event["launch_anchor_comparison_status"] = "single_source_detail"
            norm_event["launch_anchor_disagreement_ms"] = disagreement_ms
            norm_event["detail_confirmation_missing"] = False
    elif has_detail:
        norm_event["launch_anchor_evidence_level"] = "detail_confirmed"
        norm_event["launch_anchor_comparison_status"] = "single_source_detail"
        norm_event["launch_anchor_disagreement_ms"] = None
        norm_event["detail_confirmation_missing"] = False
    elif has_onboard and detail_attempted:
        norm_event["launch_anchor_evidence_level"] = "exchangeinfo_fallback"
        norm_event["launch_anchor_comparison_status"] = "single_source_exchangeinfo"
        norm_event["launch_anchor_disagreement_ms"] = None
        norm_event["detail_confirmation_missing"] = True

    state["symbol_launch_time_candidates_ms"] = norm_event["symbol_launch_time_candidates_ms"]
    state["symbol_effective_launch_time_sources"] = sources


def apply_pending_candidate_validation_state(state: dict, validation_result: dict) -> str:
    pending_reasons = validation_result.get("pending_reasons") or {}
    is_prelaunch = any(
        reason == "exchange_info_symbol_status_not_trading_prelaunch"
        for reason in pending_reasons.values()
    )
    if is_prelaunch:
        status = "pending_pre_trading"
        pending_reason = "exchange_info_symbol_status_not_trading_prelaunch"
    else:
        status = "pending_exchangeinfo_missing"
        pending_reason = "exchangeinfo_symbol_not_yet_visible"

    state["symbol_validation_status"] = status
    state["pending_reason"] = pending_reason
    state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
    state["exchangeinfo_missing_symbols"] = [
        s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})
    ]
    state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
    state["symbol_exchangeinfo_statuses"] = {
        s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()
    }
    return status


def should_expire_candidate_validation(state: dict, now_ms: int) -> bool:
    first_detected_at_ms = state["first_detected_at_ms"]
    absolute_max_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_MAX_TOTAL_SEC * 1000

    effective_launch_times = state.get("symbol_effective_launch_times_ms") or {}
    positive_effective_launch_times = [
        int(v) for v in effective_launch_times.values()
        if isinstance(v, (int, float)) and int(v) > 0
    ]
    if positive_effective_launch_times:
        latest_effective_launch_ms = max(positive_effective_launch_times)
        launch_grace_ms = latest_effective_launch_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_PENDING_VALIDATION_GRACE_AFTER_LAUNCH_SEC * 1000
        return now_ms > min(absolute_max_ms, launch_grace_ms)

    if effective_launch_times:
        return now_ms > absolute_max_ms

    legacy_max_age_ms = first_detected_at_ms + base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC * 1000
    return now_ms > min(absolute_max_ms, legacy_max_age_ms)


def build_candidate_terminal_event(
    state: dict,
    source_parent_url: str,
    now_ms: int,
    reason: str,
    detail_fetch_status: str = "success",
    symbol_validation_status: str = "rejected",
) -> dict:
    norm_event = normalize_live_event(
        raw=state["raw"],
        source_parent_url=source_parent_url,
        detected_at_ms=state["first_detected_at_ms"],
        source_published_at_ms=state["raw"].get("releaseDate"),
        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
        symbols_override=() if symbol_validation_status == "rejected" else tuple(state.get("candidate_symbols") or ()),
        extraction_metadata={
            "symbol_extraction_source": state.get("symbol_extraction_source", "none"),
            "symbol_derivation_method": state.get("symbol_derivation_method"),
            "quote_derivation_source": state.get("quote_derivation_source"),
            "symbol_validation_status": symbol_validation_status,
            "detail_fetch_attempted": state.get("detail_fetch_attempted", True),
            "detail_fetch_status": detail_fetch_status,
            "symbol_parse_failed_reason": reason,
            "symbol_parse_status": "terminal_failed",
        },
    )
    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
    norm_event["symbol_resolved_at_ms"] = now_ms
    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
    norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
    norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
    norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
    norm_event["launch_time_source"] = state.get("launch_time_source")
    return norm_event


TRANSIENT_DETAIL_HTTP_STATUSES = {202, 408, 425, 429, 500, 502, 503, 504}

def is_transient_detail_fetch_error(fetch_res: dict) -> bool:
    error = fetch_res.get("error") or ""
    status = fetch_res.get("http_status")
    if error in {"empty_detail_payload", "fixture_missing"}:
        return True
    if status in TRANSIENT_DETAIL_HTTP_STATUSES:
        return True
    if error.startswith("detail_payload_http_status_5"):
        return True
    return False


def is_overdue_retryable_failure_class(state: dict) -> bool:
    return (
        state.get("detail_retryable") is not False
        and state.get("last_detail_failure_class") in ALLOWED_OVERDUE_DETAIL_RETRY_FAILURE_CLASSES
    )


def build_detail_retry_scheduler_diagnostic_row(
    *,
    detail_retry_state: dict[str, dict],
    attempt_codes: list[str],
    now_ms: int,
    endpoint_degraded_until_ms: int,
    detail_budget_per_poll: int,
    min_never_attempted_slots_per_poll: int,
    overdue_attempted_min_interval_ms: int,
    max_article_ids: int = 20,
) -> dict:
    selected = set(attempt_codes)
    selected_overdue = []
    deferred_reason_counts: dict[str, int] = {}
    deferred_count = 0
    never_attempted_exists = any(
        int((state.get("detail_http_request_count") if state.get("detail_http_request_count") is not None else state.get("detail_fetch_attempt_count", 0)) or 0) <= 0
        and not state.get("terminal_state")
        for state in detail_retry_state.values()
    )

    def add_defer(reason: str) -> None:
        nonlocal deferred_count
        deferred_count += 1
        deferred_reason_counts[reason] = deferred_reason_counts.get(reason, 0) + 1

    for code, state in detail_retry_state.items():
        if state.get("terminal_state"):
            continue
        http_count = int(state.get("detail_http_request_count") or 0)
        fetch_count = int(state.get("detail_fetch_attempt_count") or 0)
        next_retry = int(state.get("next_detail_retry_at_ms") or 0)
        if http_count <= 0:
            continue
        if next_retry <= 0:
            add_defer("missing_next_retry_at")
            continue
        if now_ms < next_retry:
            continue

        if code in selected:
            selected_overdue.append(code)
            continue

        if now_ms < endpoint_degraded_until_ms:
            add_defer("endpoint_degraded_active")
        elif not is_overdue_retryable_failure_class(state):
            add_defer("state_not_retryable")
        elif now_ms < int(state.get("last_retry_at_ms") or 0) + overdue_attempted_min_interval_ms:
            add_defer("minimum_interval_not_elapsed")
        elif detail_budget_per_poll <= 0:
            add_defer("http_request_budget_exhausted")
        elif never_attempted_exists and detail_budget_per_poll <= min_never_attempted_slots_per_poll:
            add_defer("never_attempted_slot_protection")
        else:
            add_defer("logical_retry_budget_exhausted")

        if http_count == 0 and fetch_count > 0:
            deferred_reason_counts["attempt_manifest_mismatch"] = (
                deferred_reason_counts.get("attempt_manifest_mismatch", 0) + 1
            )

    return {
        "timestamp_ms": now_ms,
        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
        "detail_retry_overdue_selected_count": len(selected_overdue),
        "detail_retry_overdue_deferred_count": deferred_count,
        "detail_retry_overdue_deferred_reason_counts": deferred_reason_counts,
        "detail_retry_overdue_selected_article_ids": selected_overdue[:max_article_ids],
        "detail_retry_overdue_selected_article_ids_truncated": len(selected_overdue) > max_article_ids,
    }


def classify_detail_attempt_result(fetch_res: dict) -> str:
    if fetch_res.get("error") == "empty_detail_payload":
        return "http_200_empty_untrusted_payload"
    if fetch_res.get("ok"):
        status = fetch_res.get("http_status")
        if status == 202:
            return "http_202_empty"
        return "success"
    else:
        status = fetch_res.get("http_status")
        error = fetch_res.get("error") or ""
        if status == 202 or error == "detail_payload_http_status_202":
            return "http_202_empty"
        if status == 429:
            return "http_429"
        if status and status >= 500:
            return "http_5xx"
        if is_transient_detail_fetch_error(fetch_res):
            return "network_error"
        return "non_transient_error"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-public-readonly", action="store_true")
    parser.add_argument("--fixture-json", type=str)
    parser.add_argument("--poll-interval-sec", type=int, default=60)
    parser.add_argument("--max-polls", type=int)
    parser.add_argument("--max-seconds", type=int)
    parser.add_argument(
        "--stage1-5c1-summary",
        type=str,
        default="data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json",
    )
    parser.add_argument(
        "--stage1-5c-summary",
        type=str,
        default="data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="data/external_signal_shadow/stage1_5d/live_event_source_smoke/",
    )
    parser.add_argument("--output-summary", type=str)

    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_summary_path = (
        Path(args.output_summary)
        if args.output_summary
        else output_root / "binance_futures_launch_smoke_summary.json"
    )

    # 1. Safety Check: must have live-public-readonly or fixture-json BEFORE checking evidence files
    if not args.live_public_readonly and not args.fixture_json:
        invalid_summary = {
            "decision": "stage1_5d_smoke_invalid",
            "blockers": ["missing_live_flag_or_fixture"],
            "fixture_run": False,
            "debug_short_run": False,
            "observation_hours": 0.0,
            "research_result_valid": False,
            "event_detection_validated": False,
            "poll_count": 0,
            "new_futures_launch_event_count": 0,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        print("Error: missing --live-public-readonly or --fixture-json")
        return 2

    # 2. Validate Upstream Evidence
    evidence_res = validate_upstream_evidence(args.stage1_5c1_summary, args.stage1_5c_summary)
    prior_stage_safety_prerequisite_met = bool(evidence_res.get("upstream_evidence_valid", True))
    if not evidence_res["upstream_evidence_valid"]:

        invalid_summary = {
            "decision": "stage1_5d_smoke_invalid",
            "blockers": ["upstream_evidence_missing_or_invalid"] + evidence_res["blockers"],
            "fixture_run": bool(args.fixture_json),
            "debug_short_run": True,
            "observation_hours": 0.0,
            "research_result_valid": False,
            "event_detection_validated": False,
            "poll_count": 0,
            "new_futures_launch_event_count": 0,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False,
        }
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        print("Error: upstream evidence invalid")
        return 0

    # 3. Main Polling Loop
    start_time = time.time()
    poll_count = 0
    poll_success_count = 0
    poll_failed_count = 0
    consecutive_failed_polls = 0
    source_format_drift_count = 0
    schema_parse_error_count = 0
    storage_budget_passed = True
    detail_budget_starved_count = 0
    heartbeats = []
    events_detected = []
    seen_event_ids = set()
    first_bar_queue = []
    request_manifest = []
    raw_futures_launch_article_count = 0
    symbol_parsed_event_count = 0
    symbol_parse_failed_count = 0
    last_poll_started_at_ms = None
    first_poll_started_at_ms = None



    detail_retry_state = {}
    scheduler_state = load_detail_retry_scheduler_state(output_root)
    persisted_articles = scheduler_state.get("articles", {})
    endpoint_health = scheduler_state.get("endpoint_health", {})
    if not isinstance(endpoint_health, dict):
        endpoint_health = {}
    if "recent_detail_attempt_results" not in endpoint_health:
        endpoint_health["recent_detail_attempt_results"] = []
    if "detail_endpoint_degraded_until_ms" not in endpoint_health:
        endpoint_health["detail_endpoint_degraded_until_ms"] = 0

    startup_now_ms = int(time.time() * 1000)
    for code, article in persisted_articles.items():
        if article.get("terminal_state"):
            continue
        raw_art = {
            "code": article["source_article_id"],
            "title": article["title"],
            "releaseDate": article.get("source_published_at_ms"),
        }
        detail_retry_state[code] = {
            "raw": raw_art,
            "source_article_id": code,
            "title": article["title"],
            "source_detail_url_normalized": article["source_detail_url_normalized"],
            "source_parent_url": article["source_parent_url"],
            "source_published_at_ms": article["source_published_at_ms"],
            "detected_at_ms": article.get("detected_at_ms", startup_now_ms),
            "event_type": article.get("event_type") or "futures_contract_launch",
            "first_detected_at_ms": article.get("first_detected_at_ms", startup_now_ms),
            "detail_http_request_count": article.get("detail_http_request_count", article.get("detail_fetch_attempt_count", 0)),
            "detail_retry_cycle_count": article.get("detail_retry_cycle_count", article.get("detail_fetch_attempt_count", 0)),
            "detail_fetch_attempt_count": article.get("detail_fetch_attempt_count", 0),
            "transient_detail_error_count": article.get("transient_detail_error_count", 0),
            "non_transient_detail_error_count": article.get("non_transient_detail_error_count", 0),
            "retry_count": article.get("non_transient_detail_error_count", 0),
            "last_retry_at_ms": article.get("last_retry_at_ms", 0),
            "next_detail_retry_at_ms": article.get("next_detail_retry_at_ms", 0),
            "first_deferred_at_ms": article.get("first_deferred_at_ms"),
            "last_deferred_at_ms": article.get("last_deferred_at_ms"),
            "last_deferred_manifest_at_ms": article.get("last_deferred_manifest_at_ms", 0),
            "defer_count": article.get("defer_count", 0),
            "source_published_at_ms_confidence": article.get("source_published_at_ms_confidence", "medium"),
            "symbol_extraction_source": article.get("symbol_extraction_source", "none"),
            "pending_reason": article.get("pending_reason", "title_symbol_missing"),
            "candidate_symbols": article.get("candidate_symbols"),
            "symbol_derivation_method": article.get("symbol_derivation_method"),
            "symbol_validation_status": article.get("symbol_validation_status"),
            "symbol_launch_times_ms": article.get("symbol_launch_times_ms", {}),
            "symbol_onboard_times_ms": article.get("symbol_onboard_times_ms", {}),
            "symbol_effective_launch_times_ms": article.get("symbol_effective_launch_times_ms", {}),
            "last_detail_failure_class": article.get("last_detail_failure_class"),
            "detail_retryable": article.get("detail_retryable"),
            "last_bapi_detail_status": article.get("last_bapi_detail_status"),
            "last_bapi_payload_hash": article.get("last_bapi_payload_hash"),
            "last_bapi_parser_version": article.get("last_bapi_parser_version"),
            "last_bapi_parser_status": article.get("last_bapi_parser_status"),
            "last_bapi_parser_failure_reason": article.get("last_bapi_parser_failure_reason"),
            "last_bapi_parse_attempt_at_ms": article.get("last_bapi_parse_attempt_at_ms"),
            "last_support_detail_status": article.get("last_support_detail_status"),
            "last_support_failure_class": article.get("last_support_failure_class"),
            "parsed_candidate_symbols": article.get("parsed_candidate_symbols"),
            "candidate_provenance": article.get("candidate_provenance"),
            "launch_time_resolution_status": article.get("launch_time_resolution_status"),
            "launch_anchor_policy": article.get("launch_anchor_policy"),
            "required_launch_anchor_source": article.get("required_launch_anchor_source"),
            "consumable_event_allowed": article.get("consumable_event_allowed"),
            "symbol_launch_time_candidates_ms": article.get("symbol_launch_time_candidates_ms"),
            "launch_time_conflict_ms": article.get("launch_time_conflict_ms"),
        }


    detail_fetch_attempted_count = 0
    detail_fetch_fallback_attempt_count = 0
    detail_fetch_fallback_success_count = 0
    detail_fetch_success_count = 0
    detail_fetch_failed_count = 0
    detail_fetch_budget_deferred_count = 0
    detail_fetch_url_rejected_count = 0
    detail_symbol_extracted_count = 0
    detail_symbol_parse_failed_count = 0
    detail_empty_payload_count = 0
    detail_http_not_ready_count = 0
    detail_terminal_failed_count = 0
    detail_transient_timeout_count = 0
    title_symbol_extracted_count = 0
    symbol_empty_event_count = 0

    # New scheduler counters
    detail_budget_deferred_count = 0
    detail_budget_starved_count = 0
    detail_never_attempted_expired_count = 0
    detail_first_attempt_sla_breach_count = 0
    detail_scheduler_pending_count = 0
    detail_scheduler_backoff_count = 0
    detail_endpoint_degraded_count = 0
    detail_endpoint_degraded_active = 0
    detail_degraded_recent_retry_count = 0
    detail_success_symbols_empty_count = 0
    detail_retry_overdue_selected_total = 0
    detail_retry_overdue_deferred_total = 0
    detail_retry_overdue_retry_cycle_total = 0

    bapi_detail_request_count = 0
    bapi_detail_success_count = 0
    bapi_detail_trusted_payload_count = 0
    bapi_detail_schema_drift_count = 0
    bapi_detail_identity_mismatch_count = 0
    bapi_detail_rate_limited_count = 0
    bapi_to_support_fallback_count = 0
    bapi_symbol_parse_success_count = 0
    bapi_symbol_validation_pending_count = 0
    bapi_symbol_validation_success_count = 0
    bapi_payload_revision_count = 0
    bapi_payload_hash_change_count = 0

    candidate_validation_pending_count = 0

    candidate_validation_success_count = 0
    candidate_validation_failed_count = 0
    candidate_validation_expired_count = 0
    u_settlement_symbol_extracted_count = 0
    pre_launch_validation_deferred_count = 0
    max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)



    query_params = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_ANNOUNCEMENT_QUERY_PARAMS",
        {"type": "1", "pageNo": "1", "pageSize": "50"},
    )
    base_url = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_BASE_URL",
        "https://www.binance.com",
    )
    list_path = getattr(
        base,
        "EXTERNAL_SIGNAL_STAGE1_5D_BINANCE_ANNOUNCEMENT_LIST_PATH",
        "/bapi/composite/v1/public/cms/article/list/query",
    )

    fatal_blockers = []
    source_parent_url = "https://www.binance.com/en/support/announcement"
    output_root.mkdir(parents=True, exist_ok=True)

    # Write startup runtime gate (INITIALIZING)
    init_gate_context = {
        "output_root": output_root,
        "run_id": output_root.name,
        "events_stream_relative_path": "events/*.jsonl",
        "live_public_readonly": args.live_public_readonly,
        "generated_at_ms": int(time.time() * 1000),
        "first_poll_started_at_ms": 0,
        "last_poll_finished_at_ms": 0,
        "last_successful_poll_at_ms": 0,
        "poll_attempt_count": 0,
        "successful_poll_count": 0,
        "failed_poll_count": 0,
        "consecutive_failed_polls": 0,
        "fatal_blockers": fatal_blockers,
        "prior_stage_safety_prerequisite_met": prior_stage_safety_prerequisite_met,

        "fixture_run": bool(args.fixture_json),
        "source_format_drift_active": False,
        "schema_parse_error_active": False,
        "storage_budget_passed": True,
        "detail_endpoint_degraded_active": False,
        "bapi_trusted_payload_rate": 1.0,
        "symbol_parse_success_rate": 1.0,
        "symbol_validation_success_rate": 1.0,
        "scheduler_starved_expired_count": 0,
    }
    write_stage1_5d_runtime_gate(output_root, build_stage1_5d_runtime_gate(init_gate_context))

    while True:
        if args.max_polls is not None and poll_count >= args.max_polls:
            break
        if args.max_seconds is not None and (time.time() - start_time) >= args.max_seconds:
            break


        poll_count += 1
        now_ms = int(time.time() * 1000)
        if first_poll_started_at_ms is None:
            first_poll_started_at_ms = now_ms
        actual_poll_interval_sec = None

        poll_schedule_drift_ms = None
        if last_poll_started_at_ms is not None:
            actual_interval_ms = now_ms - last_poll_started_at_ms
            actual_poll_interval_sec = actual_interval_ms / 1000.0
            poll_schedule_drift_ms = actual_interval_ms - (args.poll_interval_sec * 1000)
        last_poll_started_at_ms = now_ms

        stream_paths = build_stream_paths(output_root, now_ms)

        exchangeinfo_by_symbol_cache = None
        ex_ok_cache = None

        def get_exchangeinfo_by_symbol():
            nonlocal exchangeinfo_by_symbol_cache, ex_ok_cache
            if exchangeinfo_by_symbol_cache is not None:
                return exchangeinfo_by_symbol_cache, ex_ok_cache

            if args.fixture_json:
                ex_by_sym = {}
                ex_ok = False
                try:
                    with open(args.fixture_json, "r", encoding="utf-8") as f:
                        fixture_data = json.load(f)
                    if "exchangeInfoPayload" in fixture_data:
                        syms = fixture_data["exchangeInfoPayload"].get("symbols", [])
                        for s_info in syms:
                            symbol_name = s_info.get("symbol")
                            if symbol_name:
                                ex_by_sym[symbol_name] = s_info
                        ex_ok = True
                except Exception as e:
                    print(f"Error parsing fixture exchangeInfoPayload: {e}")
                
                ex_manifest = {
                    "request_id": f"exchangeInfo_fixture_{int(time.time()*1000)}",
                    "request_type": "exchange_info",
                    "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                    "source_type": "fixture_exchangeinfo",
                    "symbol": "ALL",
                    "url": f"file://{args.fixture_json}#exchangeInfoPayload",
                    "final_url": f"file://{args.fixture_json}#exchangeInfoPayload",
                    "http_status": 200 if ex_ok else None,
                    "row_count": len(ex_by_sym),
                    "error": None if ex_ok else "fixture_exchangeinfo_missing",
                    "fetched_at_ms": int(time.time() * 1000),
                }
                append_jsonl(stream_paths["request_manifest"], ex_manifest)
                request_manifest.append(ex_manifest)

                exchangeinfo_by_symbol_cache = ex_by_sym
                ex_ok_cache = ex_ok
                return exchangeinfo_by_symbol_cache, ex_ok_cache

            ex_path = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_EXCHANGEINFO_PATH", "/fapi/v1/exchangeInfo")
            ex_url = ex_path if ex_path.startswith("http") else "https://fapi.binance.com" + ex_path

            ex_ok = False
            ex_by_sym = {}
            ex_manifest = {
                "request_id": f"exchangeInfo_{int(time.time()*1000)}",
                "request_type": "exchange_info",
                "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                "source_type": "exchangeInfo",
                "symbol": "ALL",
                "url": ex_url,
                "final_url": ex_url,
                "http_status": None,
                "row_count": 0,
                "error": None,
                "fetched_at_ms": int(time.time() * 1000),
            }
            try:
                ex_res = fetch_public_json(ex_url, live_public_readonly=args.live_public_readonly, timeout_sec=10.0)
                ex_manifest["final_url"] = ex_res.get("final_url", ex_url)
                ex_manifest["http_status"] = ex_res.get("http_status")
                if ex_res["ok"]:
                    ex_ok = True
                    syms = ex_res["payload"].get("symbols", [])
                    ex_manifest["row_count"] = len(syms)
                    for s_info in syms:
                        symbol_name = s_info.get("symbol")
                        if symbol_name:
                            ex_by_sym[symbol_name] = s_info
                else:
                    ex_manifest["error"] = ex_res.get("error")
            except Exception as e:
                ex_manifest["error"] = str(e)
            append_jsonl(stream_paths["request_manifest"], ex_manifest)
            request_manifest.append(ex_manifest)

            exchangeinfo_by_symbol_cache = ex_by_sym
            ex_ok_cache = ex_ok
            return exchangeinfo_by_symbol_cache, ex_ok_cache



        budget_res = enforce_payload_budget(
            stream_paths["raw_payloads"],
            getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_MAX_RAW_PAYLOAD_BYTES_PER_DAY", 50_000_000),
        )
        if not budget_res["storage_budget_passed"]:
            print(f"Error: storage budget exceeded: {budget_res['blocker']}")
            break

        payload = None
        fetch_err = None
        req_url = ""
        final_url = ""
        http_status = None

        if args.fixture_json:
            try:
                with open(args.fixture_json, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                req_url = f"file://{args.fixture_json}"
                final_url = req_url
                http_status = 200
            except Exception as e:
                fetch_err = str(e)
        else:
            req_url = build_announcement_list_url(base_url, list_path, query_params)
            try:
                fetch_res = fetch_public_json(
                    req_url,
                    live_public_readonly=args.live_public_readonly,
                    timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_REQUEST_TIMEOUT_SEC", 10.0),
                    retry_budget=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_RETRY_BUDGET", 2),
                )
                if fetch_res["ok"]:
                    payload = fetch_res["payload"]
                    final_url = fetch_res["final_url"]
                    http_status = fetch_res["http_status"]
                else:
                    fetch_err = fetch_res["error"]
                    http_status = fetch_res["http_status"]
            except Exception as e:
                fetch_err = str(e)

        manifest_row = {
            "request_id": f"req_{now_ms}_{poll_count}",
            "request_type": "announcement_list",
            "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
            "source_type": "announcements" if not args.fixture_json else "fixture",
            "symbol": "ALL",
            "url": req_url,
            "final_url": final_url or req_url,
            "http_status": http_status,
            "row_count": len(payload.get("data", {}).get("catalogs", [{}])[0].get("articles", []))
            if payload
            else 0,
            "error": fetch_err,
            "fetched_at_ms": now_ms,
        }
        append_jsonl(stream_paths["request_manifest"], manifest_row)
        request_manifest.append(manifest_row)

        if payload:
            poll_success_count += 1
            consecutive_failed_polls = 0
            cycle_res = run_one_poll_cycle(

                payload=payload,
                detected_at_ms=now_ms,
                source_parent_url="https://www.binance.com/en/support/announcement",
                first_bar_queue=first_bar_queue,
            )
            for ev in cycle_res["events"]:
                raw_futures_launch_article_count += 1
                if ev.get("symbols"):
                    title_symbol_extracted_count += 1
                    symbol_parsed_event_count += 1

                code = ev["source_article_id"]
                catalogs = payload.get("data", {}).get("catalogs", [])
                raw_articles = catalogs[0].get("articles", []) if catalogs else []
                raw_art = next((art for art in raw_articles if art.get("code") == code), {})

                if code not in seen_event_ids and code not in detail_retry_state:
                    persisted = persisted_articles.get(code, {})
                    title_candidate_res = extract_symbol_candidates_from_title(raw_art.get("title") or "", max_symbols)
                    if title_candidate_res["symbol_validation_status"] == "requires_exchange_info_validation":
                        detail_retry_state[code] = {
                            "raw": raw_art,
                            "source_article_id": code,
                            "title": raw_art.get("title") or persisted.get("title") or "",
                            "source_detail_url_normalized": persisted.get("source_detail_url_normalized") or f"{source_parent_url.rstrip('/')}/{code}",
                            "source_parent_url": source_parent_url,
                            "source_published_at_ms": raw_art.get("releaseDate") or persisted.get("source_published_at_ms"),
                            "detected_at_ms": persisted.get("detected_at_ms", now_ms),
                            "event_type": "futures_contract_launch",
                            "first_detected_at_ms": persisted.get("first_detected_at_ms", now_ms),
                            "detail_http_request_count": persisted.get("detail_http_request_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "detail_retry_cycle_count": persisted.get("detail_retry_cycle_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "detail_fetch_attempt_count": persisted.get("detail_fetch_attempt_count", 0),
                            "transient_detail_error_count": persisted.get("transient_detail_error_count", 0),
                            "non_transient_detail_error_count": persisted.get("non_transient_detail_error_count", 0),
                            "retry_count": persisted.get("retry_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "last_retry_at_ms": persisted.get("last_retry_at_ms", 0),
                            "next_detail_retry_at_ms": persisted.get("next_detail_retry_at_ms", 0),
                            "first_deferred_at_ms": persisted.get("first_deferred_at_ms"),
                            "last_deferred_at_ms": persisted.get("last_deferred_at_ms"),
                            "last_deferred_manifest_at_ms": persisted.get("last_deferred_manifest_at_ms", 0),
                            "defer_count": persisted.get("defer_count", 0),
                            "source_published_at_ms_confidence": ev["source_published_at_ms_confidence"],
                            "candidate_symbols": title_candidate_res["symbols"],
                            "symbol_extraction_source": title_candidate_res["symbol_extraction_source"],
                            "symbol_derivation_method": title_candidate_res["symbol_derivation_method"],
                            "quote_derivation_source": "exchange_info",
                            "symbol_validation_status": "pending_exchangeinfo_missing",
                            "symbol_launch_times_ms": title_candidate_res.get("symbol_launch_times_ms", {}),
                            "symbol_onboard_times_ms": {},
                            "detail_fetch_attempted": False,
                            "detail_fetch_status": "not_needed",
                        }
                    else:
                        detail_retry_state[code] = {
                            "raw": raw_art,
                            "source_article_id": code,
                            "title": raw_art.get("title") or persisted.get("title") or "",
                            "source_detail_url_normalized": persisted.get("source_detail_url_normalized") or f"{source_parent_url.rstrip('/')}/{code}",
                            "source_parent_url": source_parent_url,
                            "source_published_at_ms": raw_art.get("releaseDate") or persisted.get("source_published_at_ms"),
                            "detected_at_ms": persisted.get("detected_at_ms", now_ms),
                            "event_type": "futures_contract_launch",
                            "first_detected_at_ms": persisted.get("first_detected_at_ms", now_ms),
                            "detail_http_request_count": persisted.get("detail_http_request_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "detail_retry_cycle_count": persisted.get("detail_retry_cycle_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "detail_fetch_attempt_count": persisted.get("detail_fetch_attempt_count", 0),
                            "transient_detail_error_count": persisted.get("transient_detail_error_count", 0),
                            "non_transient_detail_error_count": persisted.get("non_transient_detail_error_count", 0),
                            "retry_count": persisted.get("retry_count", persisted.get("detail_fetch_attempt_count", 0)),
                            "last_retry_at_ms": persisted.get("last_retry_at_ms", 0),
                            "next_detail_retry_at_ms": persisted.get("next_detail_retry_at_ms", 0),
                            "first_deferred_at_ms": persisted.get("first_deferred_at_ms"),
                            "last_deferred_at_ms": persisted.get("last_deferred_at_ms"),
                            "last_deferred_manifest_at_ms": persisted.get("last_deferred_manifest_at_ms", 0),
                            "defer_count": persisted.get("defer_count", 0),
                            "source_published_at_ms_confidence": ev["source_published_at_ms_confidence"],
                            "symbol_extraction_source": persisted.get("symbol_extraction_source", "none"),
                            "pending_reason": persisted.get("pending_reason", "title_symbol_missing"),
                            "last_detail_failure_class": persisted.get("last_detail_failure_class"),
                            "detail_retryable": persisted.get("detail_retryable"),
                        }


            # Clean up first_bar_queue to remove empty symbol events
            first_bar_queue = [
                q for q in cycle_res["first_bar_queue"]
                if q.get("symbols") or q.get("source_article_id") not in detail_retry_state
            ]

            # Detail fallback processing
            detail_budget_remaining = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL", 3)
            detail_http_requests_remaining = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_HTTP_REQUEST_BUDGET_PER_POLL", 4)
            source_parent_url = "https://www.binance.com/en/support/announcement"
            bapi_article_code_pattern = getattr(
                base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_ARTICLE_CODE_PATTERN", r"^[0-9a-fA-F]{32}$"
            )
            bapi_eligible_pending_exists = any(
                bool(code and re.match(bapi_article_code_pattern, str(code)))
                for code in detail_retry_state
            )

            bapi_degraded_active = is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", now_ms)
            support_degraded_active = is_detail_source_degraded(endpoint_health, "support_article_detail", now_ms)
            endpoint_degraded_until_ms = (
                endpoint_health.get("detail_endpoint_degraded_until_ms", 0)
                if (
                    (bapi_eligible_pending_exists and bapi_degraded_active and support_degraded_active)
                    or (not bapi_eligible_pending_exists and support_degraded_active)
                )
                else 0
            )

            if now_ms < endpoint_degraded_until_ms:
                detail_endpoint_degraded_active = 1
                detail_endpoint_degraded_count += 1
            else:
                detail_endpoint_degraded_active = 0


            attempt_codes = select_detail_retry_attempts(
                detail_retry_state=detail_retry_state,
                now_ms=now_ms,
                detail_budget_per_poll=detail_budget_remaining,
                endpoint_degraded_until_ms=endpoint_degraded_until_ms,
                degraded_recent_article_window_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_ARTICLE_WINDOW_SEC * 1000,
                degraded_recent_retry_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_INTERVAL_SEC * 1000,
                degraded_recent_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_BUDGET_PER_POLL,
                degraded_recent_retry_max_cycles=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEGRADED_RECENT_RETRY_MAX_CYCLES,
                max_first_attempt_delay_polls=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS,
                max_first_attempt_delay_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS,
                overdue_attempted_retry_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_RETRY_BUDGET_PER_POLL,
                overdue_attempted_min_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC * 1000,
                min_never_attempted_slots_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL,
            )
            if now_ms < endpoint_degraded_until_ms:
                detail_degraded_recent_retry_count += sum(
                    1
                    for code in attempt_codes
                    if int(detail_retry_state.get(code, {}).get("detail_http_request_count") or 0) > 0
                    and int(detail_retry_state.get(code, {}).get("transient_detail_error_count") or 0) > 0
                )
            scheduler_diag = build_detail_retry_scheduler_diagnostic_row(
                detail_retry_state=detail_retry_state,
                attempt_codes=attempt_codes,
                now_ms=now_ms,
                endpoint_degraded_until_ms=endpoint_degraded_until_ms,
                detail_budget_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_BUDGET_PER_POLL,
                min_never_attempted_slots_per_poll=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MIN_NEVER_ATTEMPTED_SLOTS_PER_POLL,
                overdue_attempted_min_interval_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_ATTEMPTED_MIN_INTERVAL_SEC * 1000,
            )
            if (
                scheduler_diag["detail_retry_overdue_selected_count"] > 0
                or scheduler_diag["detail_retry_overdue_deferred_count"] > 0
            ):
                append_jsonl(stream_paths["detail_retry_scheduler_diagnostics"], scheduler_diag)
                detail_retry_overdue_selected_total += scheduler_diag["detail_retry_overdue_selected_count"]
                detail_retry_overdue_deferred_total += scheduler_diag["detail_retry_overdue_deferred_count"]
                detail_retry_overdue_retry_cycle_total += scheduler_diag["detail_retry_overdue_selected_count"]

            # Pass 1: Expiry, validation, and scheduling checks
            to_fetch_codes = []
            for code in list(detail_retry_state.keys()):
                if code not in detail_retry_state:
                    continue
                state = detail_retry_state[code]
                if state.get("terminal_state"):
                    continue

                # 1. Check max-age expiry
                max_age_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC", 3600)
                age_sec = (now_ms - state["first_detected_at_ms"]) / 1000.0
                has_candidate_symbols = bool(state.get("candidate_symbols"))
                has_transient_detail_errors = state.get("transient_detail_error_count", 0) > 0
                if has_candidate_symbols:
                    expire = should_expire_candidate_validation(state, now_ms)
                elif has_transient_detail_errors:
                    transient_max_age = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC", 86400)
                    expire = age_sec >= transient_max_age
                else:
                    expire = age_sec >= max_age_limit

                if expire:
                    if state.get("detail_fetch_attempt_count", 0) == 0:
                        detail_budget_starved_count += 1
                        detail_never_attempted_expired_count += 1
                        detail_terminal_failed_count += 1
                        fetch_status = "budget_starved"
                        failed_reason = "detail_never_attempted_budget_starved"
                        terminal_fail_type = "detail_never_attempted_budget_starved"
                    else:
                        if has_transient_detail_errors and not has_candidate_symbols:
                            detail_terminal_failed_count += 1
                            detail_transient_timeout_count += 1
                            fetch_status = "transient_detail_max_age_exceeded"
                            failed_reason = "transient_detail_max_age_exceeded"
                            terminal_fail_type = "detail_unavailable_timeout"
                        else:
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            detail_terminal_failed_count += 1
                            fetch_status = "max_age_exceeded"
                            failed_reason = "detail_retry_max_age_exceeded"
                            terminal_fail_type = None

                    if has_candidate_symbols:
                        candidate_validation_expired_count += len(state["candidate_symbols"])

                    is_derived = state.get("candidate_symbols") is not None
                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=tuple(state.get("candidate_symbols") or ()),
                        extraction_metadata={
                            "symbol_extraction_source": state.get("symbol_extraction_source", "none"),
                            "symbol_derivation_method": state.get("symbol_derivation_method", None),
                            "symbol_validation_status": "rejected" if is_derived else None,
                            "detail_fetch_attempted": state["retry_count"] > 0 or state.get("detail_fetch_attempt_count", 0) > 0,
                            "detail_fetch_status": fetch_status,
                            "symbol_parse_failed_reason": failed_reason,
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    if terminal_fail_type:
                        norm_event["terminal_failure_type"] = terminal_fail_type
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
                    norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                    norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                    norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
                    norm_event["launch_time_source"] = state.get("launch_time_source")

                    event_id = norm_event["event_id"]
                    if terminal_fail_type == "detail_unavailable_timeout":
                        terminal_diag = dict(norm_event)
                        terminal_diag["consumable_by_stage1_5f"] = False
                        terminal_diag["diagnostic_stream"] = "detail_retry_terminal_diagnostics"
                        append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], terminal_diag)
                    elif event_id not in seen_event_ids:
                        record_formal_futures_launch_event(
                            stream_paths=stream_paths,
                            row=norm_event,
                            seen_event_ids=seen_event_ids,
                            events_detected=events_detected,
                        )

                    detail_retry_state.pop(code, None)
                    continue

                # 2. Check max retries exhausted or non-retryable hard failure
                max_retries_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3)
                is_non_retryable = (
                    state.get("detail_retryable") is False
                    and int(state.get("detail_fetch_attempt_count") or 0) > 0
                    and int(state.get("retry_count") or 0) > 0
                )
                if (
                    (state["retry_count"] >= max_retries_limit or is_non_retryable)
                    and "candidate_symbols" not in state
                    and state.get("transient_detail_error_count", 0) == 0
                ):
                    symbol_empty_event_count += 1
                    symbol_parse_failed_count += 1
                    detail_symbol_parse_failed_count += 1
                    detail_terminal_failed_count += 1

                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=(),
                        extraction_metadata={
                            "symbol_extraction_source": "none",
                            "detail_fetch_attempted": True,
                            "detail_fetch_status": "retry_exhausted",
                            "symbol_parse_failed_reason": "detail_retry_exhausted",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        record_formal_futures_launch_event(
                            stream_paths=stream_paths,
                            row=norm_event,
                            seen_event_ids=seen_event_ids,
                            events_detected=events_detected,
                        )

                    detail_retry_state.pop(code, None)
                    continue

                # 2.5 Check if we already have candidates pending validation
                if state.get("candidate_symbols") is not None and not title_candidate_needs_detail_launch_anchor(state):
                    exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                    if not ex_ok:
                        continue

                    validation_result = validate_candidate_symbols_against_exchangeinfo(
                        candidates=state["candidate_symbols"],
                        exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                        allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                        allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                        allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                        validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                        emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                        now_ms=now_ms,
                    )

                    # Update timings
                    state["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
                    effective_launch = build_effective_launch_times_ms(
                        candidate_symbols=state["candidate_symbols"],
                        symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                        symbol_launch_times_ms=state.get("symbol_launch_times_ms", {}),
                        source_published_at_ms=state.get("source_published_at_ms") or state["raw"].get("releaseDate") or 0,
                        first_detected_at_ms=state["first_detected_at_ms"],
                        allow_release_date_fallback=False,
                        allow_legacy_max_age_fallback=False,
                    )
                    state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                    state["launch_time_source"] = effective_launch["launch_time_source"]

                    should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                        state, validation_result, effective_launch
                    )
                    if should_emit:
                        if state.get("detail_fetch_attempted", True):
                            detail_fetch_success_count += 1
                        detail_symbol_extracted_count += 1
                        candidate_validation_success_count += len(symbols_override)

                        for sym in symbols_override:
                            meta = validation_result["symbol_exchangeinfo"].get(sym, {})
                            if meta.get("quoteAsset") == "U" or meta.get("marginAsset") == "U":
                                u_settlement_symbol_extracted_count += 1

                        identity = build_candidate_symbol_set_identity(symbols_override)
                        c_hash = identity["candidate_symbol_set_hash"]
                        em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)

                        norm_event = normalize_live_event(
                            raw=state["raw"],
                            source_parent_url=source_parent_url,
                            detected_at_ms=state["first_detected_at_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate"),
                            source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                            symbols_override=symbols_override,
                            extraction_metadata={
                                "symbol_extraction_source": state["symbol_extraction_source"],
                                "symbol_derivation_method": state["symbol_derivation_method"],
                                "quote_derivation_source": "exchange_info",
                                "symbol_validation_status": "validated_candidate_set" if is_multi else "validated",
                                "detail_fetch_attempted": state.get("detail_fetch_attempted", True),
                                "detail_fetch_status": state.get("detail_fetch_status", "success"),
                                "symbol_parse_failed_reason": None,
                                "symbol_parse_status": "parsed",
                                "detail_fetch_variant": state.get("detail_fetch_variant"),
                                "detail_fetch_url_used": state.get("detail_fetch_url_used"),
                                "detail_payload_hash": state.get("detail_payload_hash"),
                                "detail_payload_trusted": state.get("detail_payload_trusted"),
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = state.get("detail_fetched_at_ms")
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]
                        norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                        norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                        norm_event["symbol_effective_launch_times_ms"] = state.get("symbol_effective_launch_times_ms", {})
                        norm_event["launch_time_source"] = state.get("launch_time_source")

                        apply_formal_launch_event_contract(
                            norm_event,
                            state,
                            validation_result,
                            symbols_override,
                            effective_launch,
                        )

                        if is_multi:
                            apply_multi_symbol_candidate_set_contract(
                                norm_event,
                                state,
                                validation_result,
                                symbols_override,
                                identity,
                                em_id,
                                effective_launch,
                                now_ms,
                            )

                        val_res = validate_formal_launch_event(norm_event)
                        event_id = norm_event["event_id"]

                        if val_res["valid"]:
                            if event_id not in seen_event_ids:
                                written_event = record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )

                                # Add to first_bar_queue
                                if written_event is not None:
                                    eq_item = dict(written_event)
                                    eq_item["first_futures_bar_status"] = "not_yet_available"
                                    eq_item["first_futures_bar_start_ms"] = None
                                    first_bar_queue.append(eq_item)
                        else:
                            diag = dict(norm_event)
                            diag["formal_contract_blockers"] = val_res.get("blockers", [])
                            diag["diagnostic_stream"] = "formal_contract_validation_failed"
                            append_jsonl(stream_paths["detail_retry_terminal_diagnostics"], diag)

                        if is_multi:
                            state["event_id"] = event_id
                        else:
                            detail_retry_state.pop(code, None)
                    else:
                        if is_multi and (validation_result.get("pending_symbols") or len(state.get("candidate_symbols", [])) == 0):
                            state["symbol_validation_status"] = "pending_candidate_set_readiness"
                            state["pending_reason"] = "multi_symbol_candidate_set_not_ready" if validation_result.get("pending_symbols") else "multi_symbol_candidate_symbols_empty"
                            state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
                            state["exchangeinfo_missing_symbols"] = [s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})]
                            state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
                            state["symbol_exchangeinfo_statuses"] = {s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()}
                        elif validation_result["pending_symbols"]:
                            is_prelaunch = any(
                                reason == "exchange_info_symbol_status_not_trading_prelaunch"
                                  for reason in validation_result["pending_reasons"].values()
                            )
                            if is_prelaunch:
                                state["symbol_validation_status"] = "pending_pre_trading"
                                pre_launch_validation_deferred_count += len(validation_result["pending_symbols"])
                            else:
                                state["symbol_validation_status"] = "pending_exchangeinfo_missing"
                                candidate_validation_pending_count += len(validation_result["pending_symbols"])
                        elif not state.get("candidate_symbols") and (not state.get("detail_fetch_attempted", False) or state.get("status") == "pending_detail_retry"):
                            state["status"] = "pending_detail_retry"
                            state["symbol_validation_status"] = "pending_detail_retry"
                            state["pending_reason"] = state.get("pending_reason") or "title_symbol_missing"
                            detail_retry_state[code] = state
                        else:
                            state["symbol_validation_status"] = "rejected"
                            reason = next(
                                iter(validation_result.get("rejection_reasons", {}).values()),
                                "exchange_info_candidate_rejected",
                            )
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            if state.get("detail_fetch_attempted", True):
                                detail_fetch_success_count += 1

                            norm_event = build_candidate_terminal_event(
                                state=state,
                                source_parent_url=source_parent_url,
                                now_ms=now_ms,
                                reason=reason,
                                detail_fetch_status=state.get("detail_fetch_status", "success"),
                                symbol_validation_status="rejected",
                            )
                            norm_event["terminal_failure_type"] = "candidate_validation_rejected"
                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )
                            state["terminal_state"] = True
                            state["terminal_reason"] = "candidate_validation_rejected"
                            state["terminal_at_ms"] = now_ms
                            state["symbol_validation_status"] = "rejected"
                    continue

                # 3. Check if this code is allowed to fetch in this poll (scheduling check)
                if code not in attempt_codes:
                    if state.get("detail_fetch_attempt_count", 0) == 0:
                        defer_classification = classify_never_attempted_defer_state(
                            detail_fetch_attempt_count=0,
                            first_detected_at_ms=state["first_detected_at_ms"],
                            now_ms=now_ms,
                            never_attempted_max_defer_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_NEVER_ATTEMPTED_MAX_DEFER_SEC,
                            detail_fetch_max_age_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_AGE_SEC,
                            defer_count=state.get("defer_count", 0),
                            max_first_attempt_delay_polls=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_POLLS,
                            max_first_attempt_delay_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_MAX_FIRST_ATTEMPT_DELAY_MS,
                        )
                        if defer_classification["classification"] == "detail_first_attempt_sla_breach":
                            detail_first_attempt_sla_breach_count += 1
                            if not state.get("first_deferred_at_ms"):
                                state["first_deferred_at_ms"] = now_ms
                            state["last_deferred_at_ms"] = now_ms
                            state["defer_count"] = state.get("defer_count", 0) + 1

                            deferred_manifest_min_interval_sec = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_DEFERRED_MANIFEST_MIN_INTERVAL_SEC", 15 * 60)
                            last_deferred_manifest_at_ms = state.get("last_deferred_manifest_at_ms", 0)
                            if (now_ms - last_deferred_manifest_at_ms) >= deferred_manifest_min_interval_sec * 1000:
                                state["last_deferred_manifest_at_ms"] = now_ms
                                deferred_manifest = {
                                    "request_id": f"detail_deferred_{now_ms}_{code}",
                                    "request_type": "announcement_detail_deferred",
                                    "audit_metadata_version": base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION,
                                    "source_type": "announcement_detail_deferred",
                                    "symbol": "ALL",
                                    "url": state["source_detail_url_normalized"],
                                    "final_url": state["source_detail_url_normalized"],
                                    "http_status": None,
                                    "row_count": 0,
                                    "error": "detail_budget_exhausted",
                                    "fetched_at_ms": now_ms,
                                    "payload_sha256": None,
                                    "payload_size_bytes": 0,
                                    "payload_path": None,
                                    "parser_version": PARSER_VERSION,
                                    "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                                }
                                append_jsonl(stream_paths["request_manifest"], deferred_manifest)
                                request_manifest.append(deferred_manifest)
                        else:
                            if not state.get("first_deferred_at_ms"):
                                state["first_deferred_at_ms"] = now_ms
                            state["last_deferred_at_ms"] = now_ms
                            state["defer_count"] = state.get("defer_count", 0) + 1

                        detail_fetch_budget_deferred_count += 1
                        detail_scheduler_pending_count += 1
                    else:
                        detail_scheduler_backoff_count += 1

                    continue

                to_fetch_codes.append(code)

            # Sort to_fetch_codes to match prioritized order in attempt_codes
            to_fetch_codes.sort(key=lambda c: attempt_codes.index(c))

            # Pass 2: Perform fetches in the priority order of attempt_codes!
            for code in to_fetch_codes:
                if code not in detail_retry_state:
                    continue
                state = detail_retry_state[code]

                # 4. Attempt fetch
                detail_budget_remaining -= 1
                state["detail_retry_cycle_count"] = state.get("detail_retry_cycle_count", 0) + 1
                state["last_retry_at_ms"] = now_ms
                detail_fetch_attempted_count += 1

                detail_url = f"{source_parent_url.rstrip('/')}/{code}"

                # URL validation (Requested URL)
                try:
                    if not code:
                        raise ValueError("detail_url_missing")
                    validate_announcement_detail_url(detail_url)
                except ValueError as e:
                    detail_fetch_url_rejected_count += 1
                    symbol_empty_event_count += 1
                    symbol_parse_failed_count += 1
                    detail_symbol_parse_failed_count += 1

                    norm_event = normalize_live_event(
                        raw=state["raw"],
                        source_parent_url=source_parent_url,
                        detected_at_ms=state["first_detected_at_ms"],
                        source_published_at_ms=state["raw"].get("releaseDate"),
                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                        symbols_override=(),
                        extraction_metadata={
                            "symbol_extraction_source": "none",
                            "detail_fetch_attempted": False,
                            "detail_fetch_status": "url_missing" if str(e) == "detail_url_missing" else "url_not_allowlisted",
                            "symbol_parse_failed_reason": "detail_url_rejected",
                            "symbol_parse_status": "terminal_failed",
                        }
                    )
                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                    norm_event["detail_fetched_at_ms"] = None
                    norm_event["symbol_resolved_at_ms"] = now_ms
                    norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                    event_id = norm_event["event_id"]
                    if event_id not in seen_event_ids:
                        record_formal_futures_launch_event(
                            stream_paths=stream_paths,
                            row=norm_event,
                            seen_event_ids=seen_event_ids,
                            events_detected=events_detected,
                        )
                    detail_retry_state.pop(code, None)
                    continue

                # Perform fetch
                bapi_degraded = is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", now_ms)
                bapi_recheck_interval_ms = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC", 3600) * 1000
                is_bapi_no_symbol_deduped = (
                    state.get("last_bapi_payload_hash") is not None
                    and state.get("last_bapi_parser_version") == PARSER_VERSION
                    and state.get("last_bapi_parser_status") == "no_symbols"
                    and (now_ms - int(state.get("last_bapi_parse_attempt_at_ms") or 0) < bapi_recheck_interval_ms)
                )
                bapi_handled = False
                pattern = bapi_article_code_pattern

                if not bapi_degraded and not is_bapi_no_symbol_deduped and detail_http_requests_remaining > 0 and code and re.match(pattern, code):
                    bapi_url = build_bapi_article_detail_url(code)

                    bapi_res = None
                    if args.fixture_json:
                        bapi_payload = state["raw"].get("bapiPayload")
                        if bapi_payload is not None:
                            payload_obj = bapi_payload if isinstance(bapi_payload, dict) else json.loads(bapi_payload)
                            raw_b_data = json.dumps(bapi_payload).encode("utf-8") if isinstance(bapi_payload, dict) else bapi_payload.encode("utf-8")
                            bapi_res = {
                                "ok": True,
                                "payload": payload_obj,
                                "raw_bytes": raw_b_data,
                                "final_url": bapi_url,
                                "http_status": 200,
                                "error": None,
                            }
                        else:
                            bapi_res = {
                                "ok": False,
                                "payload": None,
                                "raw_bytes": b"",
                                "final_url": bapi_url,
                                "http_status": None,
                                "error": "fixture_missing",
                            }
                    else:
                        try:
                            bapi_res = fetch_public_bapi_article_detail(
                                code,
                                live_public_readonly=args.live_public_readonly,
                                timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC", 10.0),
                                retry_budget=0,
                            )
                        except Exception as e:
                            bapi_res = {
                                "ok": False,
                                "payload": None,
                                "raw_bytes": b"",
                                "final_url": bapi_url,
                                "http_status": None,
                                "error": str(e),
                            }

                    detail_http_requests_remaining -= 1
                    bapi_detail_request_count += 1
                    state["detail_http_request_count"] = state.get("detail_http_request_count", 0) + 1
                    state["detail_fetch_attempt_count"] = state["detail_http_request_count"]

                    bapi_trusted_info = None
                    if bapi_res["ok"] and bapi_res.get("payload"):
                        bapi_trusted_info = validate_bapi_article_detail_payload(
                            bapi_res["payload"],
                            requested_article_code=code,
                            catalog_title=state["raw"].get("title"),
                        )

                    bapi_is_trusted = bool(bapi_trusted_info and bapi_trusted_info.get("payload_trusted"))

                    bapi_raw_bytes = bapi_res.get("raw_bytes") or (
                        json.dumps(bapi_res["payload"]).encode("utf-8") if bapi_res.get("payload") else b""
                    )
                    bapi_write_res = write_detail_payload_append_only(
                        root=output_root,
                        timestamp_ms=now_ms,
                        source_article_id=code,
                        detail_fetch_variant="bapi_article_detail_query",
                        raw_bytes=bapi_raw_bytes,
                        parsed_payload=bapi_res.get("payload"),
                        http_status=bapi_res.get("http_status"),
                    )

                    bapi_manifest = {
                        "request_id": f"detail_bapi_{now_ms}_{code}",
                        "request_type": "announcement_detail",
                        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 2),
                        "source_article_id": code,
                        "source_detail_url_normalized": state["source_detail_url_normalized"],
                        "source_type": "announcement_detail",
                        "symbol": "ALL",
                        "url": bapi_url,
                        "final_url": bapi_res.get("final_url") or bapi_url,
                        "http_status": bapi_res.get("http_status"),
                        "row_count": 0,
                        "error": bapi_res.get("error") if not bapi_is_trusted else None,

                        "fetched_at_ms": now_ms,
                        "payload_sha256": bapi_write_res.get("raw_payload_sha256"),
                        "payload_size_bytes": bapi_write_res.get("payload_size_bytes") or 0,
                        "payload_path": bapi_write_res.get("payload_path"),
                        "payload_trusted": bapi_is_trusted,
                        "response_payload_size_bytes": bapi_res.get("payload_size_bytes") or 0,
                        "detail_fetch_variant": "bapi_article_detail_query",
                        "source_transport": "binance_first_party_public_web_bapi_undocumented",
                        "content_provenance": "binance_official_announcement",
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], bapi_manifest)
                    request_manifest.append(bapi_manifest)

                    bapi_attempt_result = classify_detail_attempt_result(bapi_res) if not bapi_is_trusted else "success"
                    endpoint_health = update_detail_endpoint_health_by_source(
                        endpoint_health,
                        now_ms=now_ms,
                        source="bapi_article_detail_query",
                        result_code=bapi_attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    state["last_bapi_detail_status"] = "success" if bapi_is_trusted else "failure"
                    state["last_bapi_payload_hash"] = bapi_write_res.get("raw_payload_sha256")
                    state["last_bapi_parser_version"] = PARSER_VERSION
                    state["last_bapi_parse_attempt_at_ms"] = now_ms

                    if bapi_is_trusted:
                        bapi_detail_success_count += 1
                        bapi_detail_trusted_payload_count += 1
                        max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)
                        bapi_extraction = extract_symbol_candidates_from_bapi_article_payload(
                            bapi_res["payload"], max_symbols=max_symbols, title=state["raw"].get("title")
                        )

                        bapi_parsed_symbols = bapi_extraction.get("symbols") or []
                        state["last_bapi_parser_status"] = bapi_extraction.get("parser_status", "no_symbols" if not bapi_parsed_symbols else "parsed")
                        state["last_bapi_parser_failure_reason"] = bapi_extraction.get("symbol_parse_failed_reason")
                        state["parsed_candidate_symbols"] = bapi_parsed_symbols
                        state["candidate_provenance"] = bapi_extraction.get("candidate_provenance")
                        state["launch_time_resolution_status"] = bapi_extraction.get("launch_time_resolution_status")
                        state["consumable_event_allowed"] = bapi_extraction.get("consumable_event_allowed")

                        bapi_parse_audit_row = {
                            "request_id": bapi_manifest["request_id"],
                            "source_article_id": code,
                            "payload_sha256": bapi_write_res.get("raw_payload_sha256"),
                            "parser_version": PARSER_VERSION,
                            "launch_schedule_parser_version": bapi_extraction.get("launch_schedule_parser_version", LAUNCH_SCHEDULE_PARSER_VERSION),
                            "parser_status": bapi_extraction.get("parser_status", "no_symbols" if not bapi_parsed_symbols else "parsed"),
                            "parser_failure_reason": bapi_extraction.get("symbol_parse_failed_reason"),
                            "symbol_count": len(bapi_parsed_symbols),
                            "launch_time_count": len(bapi_extraction.get("symbol_launch_times_ms") or {}),
                            "fallback_reason": "bapi_trusted_parser_no_match" if not bapi_parsed_symbols else None,
                            "candidate_provenance": bapi_extraction.get("candidate_provenance") or [],
                            "parsed_at_ms": now_ms,
                        }
                        append_jsonl(stream_paths["bapi_parse_results"], bapi_parse_audit_row)

                        if bapi_parsed_symbols:
                            bapi_symbol_parse_success_count += 1
                            state["candidate_symbols"] = bapi_parsed_symbols
                            exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                            validation_res = {}
                            if ex_ok:
                                validation_res = validate_candidate_symbols_against_exchangeinfo(
                                    candidates=bapi_parsed_symbols,
                                    exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                                    allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                                    allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                                    allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                                    validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                                    emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                                    now_ms=now_ms,
                                )
                            state["symbol_onboard_times_ms"] = validation_res.get("symbol_onboard_times_ms", {})
                            state["symbol_launch_times_ms"] = bapi_extraction.get("symbol_launch_times_ms", {})
                            effective_launch = build_effective_launch_times_ms(
                                candidate_symbols=bapi_parsed_symbols,
                                symbol_onboard_times_ms=state.get("symbol_onboard_times_ms", {}),
                                symbol_launch_times_ms=state.get("symbol_launch_times_ms", {}),
                                source_published_at_ms=state["raw"].get("releaseDate") or 0,
                                first_detected_at_ms=state["first_detected_at_ms"],
                                allow_release_date_fallback=False,
                                allow_legacy_max_age_fallback=False,
                            )
                            state["symbol_effective_launch_times_ms"] = effective_launch.get("symbol_effective_launch_times_ms", {})
                            state["launch_time_source"] = effective_launch.get("launch_time_source")
                            should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                                state,
                                validation_res,
                                effective_launch,
                                bapi_extraction,
                            )

                            if should_emit:
                                bapi_symbol_validation_success_count += 1
                                bapi_handled = True
                                symbol_validation_status = "validated_candidate_set" if is_multi else "validated_by_exchangeinfo"
                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=tuple(symbols_override),
                                    extraction_metadata={
                                        "evidence_source": "official_article_body_confirmed",
                                        "detail_transport": "bapi_article_detail_query",
                                        "symbol_extraction_source": "bapi_article_body",
                                        "content_provenance": "binance_official_announcement",
                                        "source_transport": "binance_first_party_public_web_bapi_undocumented",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "detail_fetch_variant": "bapi_article_detail_query",
                                        "detail_payload_trusted": True,
                                        "symbol_validation_status": symbol_validation_status,
                                    },
                                )
                                norm_event["symbol_launch_times_ms"] = state.get("symbol_launch_times_ms", {})
                                norm_event["symbol_onboard_times_ms"] = state.get("symbol_onboard_times_ms", {})
                                norm_event["symbol_effective_launch_times_ms"] = effective_launch.get("symbol_effective_launch_times_ms", {})
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                apply_formal_launch_event_contract(
                                    norm_event,
                                    state,
                                    validation_res,
                                    symbols_override,
                                    effective_launch,
                                )

                                if is_multi:
                                    identity = build_candidate_symbol_set_identity(symbols_override)
                                    c_hash = identity["candidate_symbol_set_hash"]
                                    em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)
                                    apply_multi_symbol_candidate_set_contract(
                                        norm_event,
                                        state,
                                        validation_res,
                                        symbols_override,
                                        identity,
                                        em_id,
                                        effective_launch,
                                        now_ms,
                                    )

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                if is_multi:
                                    state["event_id"] = event_id
                                else:
                                    detail_retry_state.pop(code, None)
                                continue
                            else:
                                bapi_symbol_validation_pending_count += 1
                                bapi_handled = True
                                state["candidate_symbols"] = bapi_parsed_symbols
                                state["detail_parse_status"] = "parsed"
                                state["parsed_candidate_symbols"] = bapi_parsed_symbols
                                pending_status = apply_pending_candidate_validation_state(state, validation_res)
                                if pending_status == "pending_pre_trading":
                                    pre_launch_validation_deferred_count += len(validation_res.get("pending_symbols") or [])
                                else:
                                    candidate_validation_pending_count += len(validation_res.get("pending_symbols") or [])
                                state["detail_fetch_status"] = "success"
                                state["detail_retryable"] = False
                                state["exchangeinfo_validation_retryable"] = True
                                state["next_exchangeinfo_validation_at_ms"] = now_ms + getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_EXCHANGEINFO_VALIDATION_RETRY_INTERVAL_SEC", 60) * 1000
                                state["last_exchangeinfo_validation_at_ms"] = now_ms
                                state["exchangeinfo_validation_attempt_count"] = state.get("exchangeinfo_validation_attempt_count", 0) + 1
                                state["symbol_launch_times_ms"] = bapi_extraction.get("symbol_launch_times_ms", {})
                                state["symbol_extraction_source"] = "bapi_article_body"
                                state["symbol_derivation_method"] = "none"
                                state["detail_fetch_variant"] = "bapi_article_detail_query"
                                state["detail_payload_trusted"] = True
                                continue
                    else:
                        bapi_to_support_fallback_count += 1

                if bapi_handled:
                    continue

                fallback_urls = build_announcement_detail_fallback_urls(detail_url)

                max_urls_cap = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FALLBACK_MAX_URLS_PER_ARTICLE", 2)
                fallback_urls = fallback_urls[:max_urls_cap]

                final_fetch_res = None
                chosen_url_idx = -1
                chosen_url = None
                chosen_extraction_res = None
                chosen_payload_sha256 = None
                chosen_payload_size_bytes = 0
                chosen_payload_path = None
                is_trusted = False
                immediate_terminal_failed = False

                for url_idx, active_url in enumerate(fallback_urls):
                    if detail_http_requests_remaining <= 0:
                        detail_fetch_budget_deferred_count += 1
                        state["detail_budget_deferred_count"] = state.get("detail_budget_deferred_count", 0) + 1
                        break

                    detail_http_requests_remaining -= 1

                    if url_idx > 0:
                        detail_fetch_fallback_attempt_count += 1


                    state["detail_http_request_count"] = state.get("detail_http_request_count", 0) + 1
                    state["detail_fetch_attempt_count"] = state["detail_http_request_count"]

                    variant_name = "primary" if url_idx == 0 else "detail_path_fallback"

                    current_res = None
                    if args.fixture_json:
                        detail_payload = state["raw"].get("detailPayload")
                        if detail_payload is not None:
                            current_res = {
                                "ok": True,
                                "payload": detail_payload,
                                "final_url": active_url,
                                "http_status": 200,
                                "error": None,
                            }
                        else:
                            current_res = {
                                "ok": False,
                                "payload": None,
                                "final_url": active_url,
                                "http_status": None,
                                "error": "fixture_missing",
                            }
                    else:
                        try:
                            current_res = fetch_public_payload(
                                active_url,
                                live_public_readonly=args.live_public_readonly,
                                timeout_sec=getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_REQUEST_TIMEOUT_SEC", 10.0),
                                retry_budget=0
                            )
                        except Exception as e:
                            current_res = {
                                "ok": False,
                                "payload": None,
                                "final_url": active_url,
                                "http_status": None,
                                "error": str(e),
                            }

                    # Validate final URL host
                    is_url_valid = True
                    if current_res["ok"]:
                        try:
                            validate_announcement_detail_url(current_res["final_url"])
                        except ValueError:
                            # Immediate terminal failure for URL validation rejection
                            detail_fetch_url_rejected_count += 1
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1

                            norm_event = normalize_live_event(
                                raw=state["raw"],
                                source_parent_url=source_parent_url,
                                detected_at_ms=state["first_detected_at_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate"),
                                source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                symbols_override=(),
                                extraction_metadata={
                                    "symbol_extraction_source": "none",
                                    "detail_fetch_attempted": True,
                                    "detail_fetch_status": "final_url_not_allowlisted",
                                    "symbol_parse_failed_reason": "final_url_rejected",
                                    "symbol_parse_status": "terminal_failed",
                                    "detail_fetch_variant": variant_name,
                                }
                            )
                            norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                            norm_event["detail_fetched_at_ms"] = now_ms
                            norm_event["symbol_resolved_at_ms"] = now_ms
                            norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )

                            # Append manifest row
                            detail_manifest = {
                                "request_id": f"detail_{now_ms}_{code}_{url_idx}",
                                "request_type": "announcement_detail",
                                "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                                "source_article_id": code,
                                "source_detail_url_normalized": state["source_detail_url_normalized"],
                                "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                                "symbol": "ALL",
                                "url": active_url,
                                "final_url": current_res["final_url"],
                                "http_status": current_res.get("http_status"),
                                "row_count": 0,
                                "error": "final_url_rejected",
                                "fetched_at_ms": now_ms,
                                "payload_sha256": None,
                                "payload_size_bytes": 0,
                                "payload_path": None,
                                "payload_trusted": False,
                                "response_payload_size_bytes": current_res.get("payload_size_bytes") or 0,
                                "detail_fetch_variant": variant_name,
                                "parser_version": PARSER_VERSION,
                                "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                            }
                            append_jsonl(stream_paths["request_manifest"], detail_manifest)
                            request_manifest.append(detail_manifest)

                            detail_retry_state.pop(code, None)
                            is_url_valid = False
                            immediate_terminal_failed = True
                            break

                    is_trusted = False
                    current_extraction_res = None
                    payload_sha256 = None
                    payload_size_bytes = 0
                    payload_path = None

                    if current_res["ok"] and is_url_valid:
                        write_res = write_detail_payload(output_root, now_ms, code, current_res["payload"])
                        payload_sha256 = write_res["payload_sha256"]
                        payload_size_bytes = write_res["payload_size_bytes"]
                        payload_path = write_res["payload_path"]

                        max_symbols = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SYMBOL_EXTRACTION_MAX_SYMBOLS", 30)
                        title_context = state["raw"].get("title")
                        current_extraction_res = extract_symbol_candidates_from_detail_payload(
                            current_res["payload"], max_symbols, title=title_context
                        )

                        is_trusted = bool(current_extraction_res and current_extraction_res.get("symbols"))
                        if not is_trusted:
                            current_res = dict(current_res)
                            current_res["error"] = "empty_detail_payload"

                    detail_manifest = {
                        "request_id": f"detail_{now_ms}_{code}_{url_idx}",
                        "request_type": "announcement_detail",
                        "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                        "source_article_id": code,
                        "source_detail_url_normalized": state["source_detail_url_normalized"],
                        "source_type": "announcement_detail" if not args.fixture_json else "fixture_detail",
                        "symbol": "ALL",
                        "url": active_url,
                        "final_url": current_res.get("final_url") or active_url,
                        "http_status": current_res.get("http_status"),
                        "row_count": 0,
                        "error": current_res.get("error"),
                        "fetched_at_ms": now_ms,
                        "payload_sha256": payload_sha256,
                        "payload_size_bytes": payload_size_bytes,
                        "payload_path": payload_path,
                        "payload_trusted": is_trusted,
                        "response_payload_size_bytes": current_res.get("payload_size_bytes") or 0,
                        "detail_fetch_variant": variant_name,
                        "parser_version": PARSER_VERSION,
                        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
                    }
                    append_jsonl(stream_paths["request_manifest"], detail_manifest)
                    request_manifest.append(detail_manifest)

                    # Update health based on this request
                    attempt_result = classify_detail_attempt_result(current_res)
                    endpoint_health = update_detail_endpoint_health(
                        endpoint_health,
                        now_ms=now_ms,
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    # Update variant health
                    endpoint_health = update_detail_endpoint_health_by_variant(
                        endpoint_health,
                        now_ms=now_ms,
                        variant=variant_name,
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )
                    endpoint_health = update_detail_endpoint_health_by_source(
                        endpoint_health,
                        now_ms=now_ms,
                        source="support_article_detail",
                        result_code=attempt_result,
                        degraded_rate_threshold=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_202_RATE_THRESHOLD,
                        degraded_min_sample=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_MIN_SAMPLE,
                        degraded_backoff_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_ENDPOINT_DEGRADED_BACKOFF_SEC,
                    )

                    if current_res["ok"] and is_url_valid and is_trusted:
                        final_fetch_res = current_res
                        chosen_url_idx = url_idx
                        chosen_url = active_url
                        chosen_extraction_res = current_extraction_res
                        chosen_payload_sha256 = payload_sha256
                        chosen_payload_size_bytes = payload_size_bytes
                        chosen_payload_path = payload_path
                        if url_idx > 0:
                            detail_fetch_fallback_success_count += 1
                        break

                    if url_idx == 0:
                        is_allowed = False
                        if attempt_result == "http_202_empty" or current_res.get("error") == "empty_detail_payload":
                            is_allowed = True
                        if not is_allowed:
                            final_fetch_res = current_res
                            break

                    final_fetch_res = current_res

                if immediate_terminal_failed:
                    continue

                # Post-fetch handling
                if final_fetch_res and final_fetch_res.get("ok") and (chosen_url_idx == 0 or (chosen_extraction_res and chosen_extraction_res.get("symbols"))):
                    detail_fetch_success_count += 1
                    detail_symbol_extracted_count += 1
                    extraction_res = chosen_extraction_res
                    state["detail_fetched_at_ms"] = now_ms
                    variant_name = "primary" if chosen_url_idx == 0 else "detail_path_fallback"

                    if extraction_res["symbols"]:
                        state["candidate_symbols"] = extraction_res["symbols"]
                        state["symbol_extraction_source"] = "detail_path_fallback" if chosen_url_idx > 0 else extraction_res["symbol_extraction_source"]
                        state["symbol_derivation_method"] = extraction_res["symbol_derivation_method"]
                        state["quote_derivation_source"] = "exchange_info"
                        state["symbol_validation_status"] = "pending_exchangeinfo_missing"
                        state["symbol_launch_times_ms"] = extraction_res.get("symbol_launch_times_ms", {})
                        state["symbol_onboard_times_ms"] = {}
                        state["detail_fetch_variant"] = variant_name
                        state["detail_fetch_url_used"] = chosen_url
                        state["detail_payload_hash"] = chosen_payload_sha256
                        state["detail_payload_trusted"] = True

                        effective_launch = build_effective_launch_times_ms(
                            candidate_symbols=state["candidate_symbols"],
                            symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                            symbol_launch_times_ms=state["symbol_launch_times_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate") or 0,
                            first_detected_at_ms=state["first_detected_at_ms"],
                            allow_release_date_fallback=False,
                            allow_legacy_max_age_fallback=False,
                        )
                        state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                        state["launch_time_source"] = effective_launch["launch_time_source"]

                        exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()
                        if ex_ok:
                            validation_result = validate_candidate_symbols_against_exchangeinfo(
                                candidates=state["candidate_symbols"],
                                exchangeinfo_by_symbol=exchangeinfo_by_symbol,
                                allowed_margin_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_MARGIN_ASSETS,
                                allowed_quote_assets=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_FUTURES_QUOTE_ASSETS,
                                allowed_contract_types=base.EXTERNAL_SIGNAL_STAGE1_5D_ALLOWED_CONTRACT_TYPES,
                                validatable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES,
                                emittable_statuses=base.EXTERNAL_SIGNAL_STAGE1_5D_EMITTABLE_SYMBOL_STATUSES,
                                now_ms=now_ms,
                            )

                            state["symbol_onboard_times_ms"] = validation_result.get("symbol_onboard_times_ms", {})
                            effective_launch = build_effective_launch_times_ms(
                                candidate_symbols=state["candidate_symbols"],
                                symbol_onboard_times_ms=state["symbol_onboard_times_ms"],
                                symbol_launch_times_ms=state["symbol_launch_times_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate") or 0,
                                first_detected_at_ms=state["first_detected_at_ms"],
                                allow_release_date_fallback=False,
                                allow_legacy_max_age_fallback=False,
                            )
                            state["symbol_effective_launch_times_ms"] = effective_launch["symbol_effective_launch_times_ms"]
                            state["launch_time_source"] = effective_launch["launch_time_source"]

                            should_emit, is_multi, symbols_override = check_article_emission_eligibility(
                                state, validation_result, effective_launch
                            )
                            if should_emit:
                                candidate_validation_success_count += len(symbols_override)

                                for sym in symbols_override:
                                    meta = validation_result["symbol_exchangeinfo"].get(sym, {})
                                    if meta.get("quoteAsset") == "U" or meta.get("marginAsset") == "U":
                                        u_settlement_symbol_extracted_count += 1

                                identity = build_candidate_symbol_set_identity(symbols_override)
                                c_hash = identity["candidate_symbol_set_hash"]
                                em_id = build_multi_symbol_emission_id(code, state.get("event_type", "futures_contract_launch"), c_hash)

                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=symbols_override,
                                    extraction_metadata={
                                        "symbol_extraction_source": state["symbol_extraction_source"],
                                        "symbol_derivation_method": state["symbol_derivation_method"],
                                        "quote_derivation_source": "exchange_info",
                                        "symbol_validation_status": "validated_candidate_set" if is_multi else "validated",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "symbol_parse_failed_reason": None,
                                        "symbol_parse_status": "parsed",
                                        "detail_fetch_variant": state.get("detail_fetch_variant", variant_name),
                                        "detail_fetch_url_used": state.get("detail_fetch_url_used", chosen_url),
                                        "detail_payload_hash": state.get("detail_payload_hash", chosen_payload_sha256),
                                        "detail_payload_trusted": state.get("detail_payload_trusted", True),
                                    }
                                )
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                apply_formal_launch_event_contract(
                                    norm_event,
                                    state,
                                    validation_result,
                                    symbols_override,
                                    effective_launch,
                                )

                                if is_multi:
                                    apply_multi_symbol_candidate_set_contract(
                                        norm_event,
                                        state,
                                        validation_result,
                                        symbols_override,
                                        identity,
                                        em_id,
                                        effective_launch,
                                        now_ms,
                                    )

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                if is_multi:
                                    state["event_id"] = event_id
                                else:
                                    detail_retry_state.pop(code, None)
                            else:
                                if is_multi and (validation_result.get("pending_symbols") or len(state.get("candidate_symbols", [])) == 0):
                                    state["symbol_validation_status"] = "pending_candidate_set_readiness"
                                    state["pending_reason"] = "multi_symbol_candidate_set_not_ready" if validation_result.get("pending_symbols") else "multi_symbol_candidate_symbols_empty"
                                    state["exchangeinfo_visible_symbols"] = list(validation_result.get("symbol_exchangeinfo", {}).keys())
                                    state["exchangeinfo_missing_symbols"] = [s for s in state.get("candidate_symbols", []) if s not in validation_result.get("symbol_exchangeinfo", {})]
                                    state["hard_rejected_symbols"] = list(validation_result.get("rejected_symbols", []))
                                    state["symbol_exchangeinfo_statuses"] = {s: meta.get("status") for s, meta in validation_result.get("symbol_exchangeinfo", {}).items()}
                                elif validation_result["rejected_symbols"]:
                                    candidate_validation_failed_count += len(validation_result["rejected_symbols"])

                                    reason = next(
                                        iter(validation_result.get("rejection_reasons", {}).values()),
                                        "exchange_info_candidate_rejected",
                                    )
                                    symbol_empty_event_count += 1
                                    symbol_parse_failed_count += 1
                                    detail_symbol_parse_failed_count += 1

                                    norm_event = normalize_live_event(
                                        raw=state["raw"],
                                        source_parent_url=source_parent_url,
                                        detected_at_ms=state["first_detected_at_ms"],
                                        source_published_at_ms=state["raw"].get("releaseDate"),
                                        source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                        symbols_override=(),
                                        extraction_metadata={
                                            "symbol_extraction_source": state["symbol_extraction_source"],
                                            "symbol_derivation_method": state["symbol_derivation_method"],
                                            "quote_derivation_source": "exchange_info",
                                            "symbol_validation_status": "rejected",
                                            "detail_fetch_attempted": True,
                                            "detail_fetch_status": "success",
                                            "symbol_parse_failed_reason": reason,
                                            "symbol_parse_status": "terminal_failed",
                                            "detail_fetch_variant": state.get("detail_fetch_variant", variant_name),
                                            "detail_fetch_url_used": state.get("detail_fetch_url_used", chosen_url),
                                            "detail_payload_hash": state.get("detail_payload_hash", chosen_payload_sha256),
                                            "detail_payload_trusted": state.get("detail_payload_trusted", True),
                                        }
                                    )
                                    norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                    norm_event["detail_fetched_at_ms"] = now_ms
                                    norm_event["symbol_resolved_at_ms"] = now_ms
                                    event_id = norm_event["event_id"]
                                    if event_id not in seen_event_ids:
                                        record_formal_futures_launch_event(
                                            stream_paths=stream_paths,
                                            row=norm_event,
                                            seen_event_ids=seen_event_ids,
                                            events_detected=events_detected,
                                        )

                                    state["terminal_state"] = True
                                    state["terminal_reason"] = "candidate_validation_rejected"
                                    state["terminal_at_ms"] = now_ms
                                    state["symbol_validation_status"] = "rejected"
                                elif validation_result["pending_symbols"]:
                                    pending_status = apply_pending_candidate_validation_state(state, validation_result)
                                    if pending_status == "pending_pre_trading":
                                        pre_launch_validation_deferred_count += len(validation_result["pending_symbols"])
                                    else:
                                        candidate_validation_pending_count += len(validation_result["pending_symbols"])
                        else:
                            if extraction_res and extraction_res.get("symbol_validation_status") == "validated_by_exact_text":
                                norm_event = normalize_live_event(
                                    raw=state["raw"],
                                    source_parent_url=source_parent_url,
                                    detected_at_ms=state["first_detected_at_ms"],
                                    source_published_at_ms=state["raw"].get("releaseDate"),
                                    source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                    symbols_override=extraction_res["symbols"],
                                    extraction_metadata={
                                        "symbol_extraction_source": "detail_path_fallback" if chosen_url_idx > 0 else extraction_res["symbol_extraction_source"],
                                        "symbol_derivation_method": extraction_res["symbol_derivation_method"],
                                        "quote_derivation_source": None,
                                        "symbol_validation_status": "validated_by_exact_text",
                                        "detail_fetch_attempted": True,
                                        "detail_fetch_status": "success",
                                        "symbol_parse_failed_reason": None,
                                        "symbol_parse_status": "parsed",
                                        "detail_fetch_variant": variant_name,
                                        "detail_fetch_url_used": chosen_url,
                                        "detail_payload_hash": chosen_payload_sha256,
                                        "detail_payload_trusted": True,
                                    }
                                )
                                norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                                norm_event["detail_fetched_at_ms"] = now_ms
                                norm_event["symbol_resolved_at_ms"] = now_ms
                                norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                                event_id = norm_event["event_id"]
                                if event_id not in seen_event_ids:
                                    written_event = record_formal_futures_launch_event(
                                        stream_paths=stream_paths,
                                        row=norm_event,
                                        seen_event_ids=seen_event_ids,
                                        events_detected=events_detected,
                                    )

                                    if written_event is not None:
                                        eq_item = dict(written_event)
                                        eq_item["first_futures_bar_status"] = "not_yet_available"
                                        eq_item["first_futures_bar_start_ms"] = None
                                        first_bar_queue.append(eq_item)

                                detail_retry_state.pop(code, None)
                    else:
                        symbol_empty_event_count += 1
                        symbol_parse_failed_count += 1
                        detail_symbol_parse_failed_count += 1

                        norm_event = normalize_live_event(
                            raw=state["raw"],
                            source_parent_url=source_parent_url,
                            detected_at_ms=state["first_detected_at_ms"],
                            source_published_at_ms=state["raw"].get("releaseDate"),
                            source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                            symbols_override=tuple(state.get("candidate_symbols") or ()),
                            extraction_metadata={
                                "symbol_extraction_source": extraction_res["symbol_extraction_source"],
                                "symbol_derivation_method": extraction_res["symbol_derivation_method"],
                                "quote_derivation_source": None,
                                "symbol_validation_status": "rejected",
                                "detail_fetch_attempted": True,
                                "detail_fetch_status": "success",
                                "symbol_parse_failed_reason": "detail_symbols_empty",
                                "symbol_parse_status": "terminal_failed",
                                "detail_fetch_variant": variant_name,
                                "detail_fetch_url_used": chosen_url,
                                "detail_payload_hash": chosen_payload_sha256,
                                "detail_payload_trusted": True,
                            }
                        )
                        norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                        norm_event["detail_fetched_at_ms"] = now_ms
                        norm_event["symbol_resolved_at_ms"] = now_ms
                        norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                        event_id = norm_event["event_id"]
                        if event_id not in seen_event_ids:
                            record_formal_futures_launch_event(
                                stream_paths=stream_paths,
                                row=norm_event,
                                seen_event_ids=seen_event_ids,
                                events_detected=events_detected,
                            )

                        detail_retry_state.pop(code, None)
                else:
                    detail_fetch_failed_count += 1

                    if final_fetch_res is None:
                        continue

                    attempt_result = classify_detail_attempt_result(final_fetch_res)
                    err_reason = final_fetch_res.get("error") or "fetch_failed"

                    if final_fetch_res.get("ok") and not is_trusted:
                        err_reason = "empty_detail_payload"

                    if err_reason == "empty_detail_payload" or final_fetch_res.get("payload_size_bytes") == 0:
                        detail_empty_payload_count += 1

                    status = final_fetch_res.get("http_status")
                    if status in TRANSIENT_DETAIL_HTTP_STATUSES:
                        detail_http_not_ready_count += 1

                    chk_res = dict(final_fetch_res)
                    if err_reason == "empty_detail_payload":
                        chk_res["error"] = "empty_detail_payload"

                    status = chk_res.get("http_status")
                    if status == 202:
                        attempt_res_class = "http_202_empty"
                    elif status == 200 and chk_res.get("payload_size_bytes") == 0:
                        attempt_res_class = "http_200_empty_untrusted_payload"
                    elif status:
                        attempt_res_class = f"http_{status}"
                    else:
                        attempt_res_class = "network_or_fixture_error"
                    if is_transient_detail_fetch_error(chk_res):
                        state["transient_detail_error_count"] = state.get("transient_detail_error_count", 0) + 1
                        state["retry_count"] = int(state.get("retry_count") or 0) + 1
                        state["detail_fetch_attempt_count"] = int(state.get("detail_fetch_attempt_count") or 0) + 1
                        state["detail_fetch_attempted"] = True
                        state["status"] = "pending_detail_retry"
                        state["pending_reason"] = err_reason
                        state["last_retry_at_ms"] = now_ms
                        state["last_detail_failure_class"] = attempt_res_class
                        state["detail_retryable"] = True
                        state["next_detail_retry_at_ms"] = now_ms + compute_detail_transient_backoff_ms(
                            state["transient_detail_error_count"],
                            base_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_BASE_SEC,
                            max_sec=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_TRANSIENT_BACKOFF_MAX_SEC,
                        )
                        continue
                    else:
                        state["non_transient_detail_error_count"] = state.get("non_transient_detail_error_count", 0) + 1
                        state["retry_count"] = state["non_transient_detail_error_count"]
                        state["last_detail_failure_class"] = f"http_{chk_res.get('http_status')}" if chk_res.get("http_status") else "non_transient_error"
                        state["detail_retryable"] = False


                        max_retries_limit = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES", 3)
                        if state["retry_count"] >= max_retries_limit:
                            symbol_empty_event_count += 1
                            symbol_parse_failed_count += 1
                            detail_symbol_parse_failed_count += 1
                            detail_terminal_failed_count += 1

                            norm_event = normalize_live_event(
                                raw=state["raw"],
                                source_parent_url=source_parent_url,
                                detected_at_ms=state["first_detected_at_ms"],
                                source_published_at_ms=state["raw"].get("releaseDate"),
                                source_published_at_ms_confidence=state.get("source_published_at_ms_confidence", "medium"),
                                symbols_override=(),
                                extraction_metadata={
                                    "symbol_extraction_source": "none",
                                    "detail_fetch_attempted": True,
                                    "detail_fetch_status": err_reason,
                                    "symbol_parse_failed_reason": err_reason,
                                    "symbol_parse_status": "terminal_failed",
                                }
                            )
                            norm_event["first_detected_at_ms"] = state["first_detected_at_ms"]
                            norm_event["detail_fetched_at_ms"] = now_ms
                            norm_event["symbol_resolved_at_ms"] = now_ms
                            norm_event["symbol_resolution_latency_ms"] = now_ms - state["first_detected_at_ms"]

                            event_id = norm_event["event_id"]
                            if event_id not in seen_event_ids:
                                record_formal_futures_launch_event(
                                    stream_paths=stream_paths,
                                    row=norm_event,
                                    seen_event_ids=seen_event_ids,
                                    events_detected=events_detected,
                                )

                            detail_retry_state.pop(code, None)
                        continue

            # Persist scheduler state
            scheduler_state["articles"] = serialize_retry_articles(detail_retry_state)
            scheduler_state["endpoint_health"] = endpoint_health
            write_detail_retry_scheduler_state(
                output_root,
                scheduler_state,
                metadata_version=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION,
            )

            append_jsonl(stream_paths["raw_payloads"], {"timestamp_ms": now_ms, "payload": payload})

            hb = cycle_res["heartbeat"]

        else:
            poll_failed_count += 1
            consecutive_failed_polls += 1
            hb = {

                "poll_started_at_ms": now_ms,
                "poll_completed_at_ms": int(time.time() * 1000),
                "configured_poll_interval_sec": args.poll_interval_sec,
                "poll_success": False,
                "source_format_drift": False,
                "schema_parse_error": False,
                "heartbeat_gap": False,
                "error": fetch_err,
            }

        hb["configured_poll_interval_sec"] = args.poll_interval_sec
        hb["actual_poll_interval_sec"] = actual_poll_interval_sec
        hb["poll_schedule_drift_ms"] = poll_schedule_drift_ms
        append_jsonl(stream_paths["heartbeats"], hb)
        heartbeats.append(hb)

        # 4. Check First Futures Bar for events in queue (only if live/readonly)
        if first_bar_queue and args.live_public_readonly and not args.fixture_json:
            budget = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_FIRST_BAR_CHECK_BUDGET_PER_POLL", 3)

            exchangeinfo_by_symbol, ex_ok = get_exchangeinfo_by_symbol()

            to_process = first_bar_queue[:budget]
            remaining = first_bar_queue[budget:]
            processed = []

            for eq_item in to_process:
                symbols = eq_item.get("symbols", [])
                if not symbols:
                    eq_item["first_futures_bar_status"] = "current_exchangeinfo_not_found"
                    processed.append(eq_item)
                    continue

                symbol = symbols[0]
                if not ex_ok:
                    eq_item["first_futures_bar_status"] = "network_error"
                    processed.append(eq_item)
                    continue

                if symbol not in exchangeinfo_by_symbol:
                    eq_item["first_futures_bar_status"] = "current_exchangeinfo_not_found"
                    processed.append(eq_item)
                    continue


                klines_url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=15m&limit=5"
                kline_res = None
                kline_err = None
                try:
                    k_res = fetch_public_json(klines_url, live_public_readonly=True, timeout_sec=10.0)
                    if k_res["ok"]:
                        kline_res = k_res["payload"]
                    else:
                        kline_err = k_res["error"]
                except Exception as e:
                    kline_err = str(e)

                k_manifest = {
                    "request_id": f"kline_{int(time.time()*1000)}_{symbol}",
                    "request_type": "first_futures_bar_klines",
                    "audit_metadata_version": getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION", 1),
                    "source_type": "klines",
                    "symbol": symbol,
                    "url": klines_url,
                    "final_url": klines_url,
                    "http_status": 200 if kline_res else 400,
                    "row_count": len(kline_res) if kline_res else 0,
                    "error": kline_err,
                    "fetched_at_ms": int(time.time() * 1000),
                }
                append_jsonl(stream_paths["request_manifest"], k_manifest)
                request_manifest.append(k_manifest)

                if kline_res is not None:
                    bars_by_symbol = {symbol: [{"bar_start_ms": bar[0]} for bar in kline_res]}
                    checked = check_first_bar_for_event(
                        eq_item, bars_by_symbol, int(time.time() * 1000)
                    )
                    processed.append(checked)
                else:
                    eq_item["first_futures_bar_status"] = "network_error"
                    processed.append(eq_item)

            first_bar_queue = processed + remaining

        loop_gate_context = {
            "output_root": output_root,
            "run_id": output_root.name,
            "events_stream_relative_path": "events/*.jsonl",
            "live_public_readonly": args.live_public_readonly,
            "generated_at_ms": int(time.time() * 1000),
            "first_poll_started_at_ms": first_poll_started_at_ms or int(time.time() * 1000),
            "last_poll_finished_at_ms": int(time.time() * 1000),
            "last_successful_poll_at_ms": int(time.time() * 1000) if hb.get("poll_success") else 0,
            "poll_attempt_count": poll_count,
            "successful_poll_count": poll_success_count,
            "failed_poll_count": poll_failed_count,
            "consecutive_failed_polls": consecutive_failed_polls,
            "fatal_blockers": fatal_blockers,
            "prior_stage_safety_prerequisite_met": prior_stage_safety_prerequisite_met,
            "fixture_run": bool(args.fixture_json),
            "source_format_drift_active": source_format_drift_count > 0,
            "schema_parse_error_active": schema_parse_error_count > 0,
            "storage_budget_passed": storage_budget_passed,
            "detail_endpoint_degraded_active": is_detail_source_degraded(endpoint_health, "bapi_article_detail_query", int(time.time() * 1000)),
            "bapi_trusted_payload_rate": 1.0 if bapi_detail_request_count == 0 else (bapi_detail_trusted_payload_count / float(bapi_detail_request_count)),
            "symbol_parse_success_rate": 1.0 if bapi_detail_trusted_payload_count == 0 else (bapi_symbol_parse_success_count / float(bapi_detail_trusted_payload_count)),
            "symbol_validation_success_rate": 1.0 if bapi_symbol_parse_success_count == 0 else (bapi_symbol_validation_success_count / float(bapi_symbol_parse_success_count)),
            "scheduler_starved_expired_count": detail_budget_starved_count,
        }
        write_stage1_5d_runtime_gate(output_root, build_stage1_5d_runtime_gate(loop_gate_context))

        if args.max_polls is not None and poll_count >= args.max_polls:
            break

        time.sleep(args.poll_interval_sec)


    end_time = time.time()
    observation_hours = (end_time - start_time) / 3600.0
    debug_short_run = (
        args.max_polls is not None or args.max_seconds is not None or observation_hours < 24.0
    )

    final_events = []
    for ev in events_detected:
        updated = None
        for q_item in first_bar_queue:
            if q_item.get("event_id") == ev.get("event_id"):
                updated = q_item
                break
        if updated:
            final_events.append(updated)
        else:
            final_events.append(ev)

    detail_pending_retry_count = sum(
        1
        for state in detail_retry_state.values()
        if state.get("detail_fetch_attempt_count", 0) > 0
        or state.get("transient_detail_error_count", 0) > 0
    )
    detail_manifest_counts_by_article = {}
    request_manifest_root = output_root / "request_manifest"
    for manifest_path in sorted(request_manifest_root.glob("*.jsonl")) if request_manifest_root.exists() else []:
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("request_type") != "announcement_detail":
                continue
            source_article_id = row.get("source_article_id")
            if not source_article_id:
                continue
            detail_manifest_counts_by_article[source_article_id] = (
                detail_manifest_counts_by_article.get(source_article_id, 0) + 1
            )
    detail_fetch_attempt_manifest_mismatch_count = sum(
        1
        for code, state in detail_retry_state.items()
        if int(state.get("detail_http_request_count") or 0) != detail_manifest_counts_by_article.get(code, 0)
    )

    summary_now_ms = int(time.time() * 1000)
    overdue_diag = summarize_detail_retry_overdue_state(
        detail_retry_state,
        now_ms=summary_now_ms,
        warn_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_WARN_SEC * 1000,
        hard_warn_ms=base.EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_OVERDUE_PENDING_HARD_WARN_SEC * 1000,
    )
    source_health_diag = summarize_detail_source_health(endpoint_health, summary_now_ms)

    summary = build_smoke_summary(
        upstream_evidence=evidence_res,
        heartbeats=heartbeats,
        events=final_events,
        request_manifest=request_manifest,
        fixture_run=bool(args.fixture_json),
        debug_short_run=debug_short_run,
        observation_hours=observation_hours,
        counters={
            "raw_futures_launch_article_count": raw_futures_launch_article_count,
            "symbol_parsed_event_count": symbol_parsed_event_count,
            "symbol_parse_failed_count": symbol_parse_failed_count,
            "deduped_new_event_count": len(events_detected),
            "detail_retry_overdue_pending_count": overdue_diag["detail_retry_overdue_pending_count"],
            "detail_retry_overdue_attempted_count": overdue_diag["detail_retry_overdue_attempted_count"],
            "detail_retry_overdue_never_attempted_count": overdue_diag["detail_retry_overdue_never_attempted_count"],
            "detail_retry_due_timestamp_missing_count": overdue_diag["detail_retry_due_timestamp_missing_count"],
            "detail_attempt_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "detail_retry_oldest_overdue_ms": overdue_diag["detail_retry_oldest_overdue_ms"],
            "detail_retry_overdue_warn_active": overdue_diag["detail_retry_overdue_warn_active"],
            "detail_retry_overdue_hard_warn_active": overdue_diag["detail_retry_overdue_hard_warn_active"],
            "detail_retry_overdue_selected_total": detail_retry_overdue_selected_total,
            "detail_retry_overdue_deferred_total": detail_retry_overdue_deferred_total,
            "detail_retry_overdue_retry_cycle_total": detail_retry_overdue_retry_cycle_total,
            "detail_fetch_attempted_count": detail_fetch_attempted_count,
            "detail_fetch_success_count": detail_fetch_success_count,
            "detail_fetch_failed_count": detail_fetch_failed_count,
            "detail_fetch_budget_deferred_count": detail_fetch_budget_deferred_count,
            "detail_fetch_url_rejected_count": detail_fetch_url_rejected_count,
            "detail_symbol_extracted_count": detail_symbol_extracted_count,
            "detail_symbol_parse_failed_count": detail_symbol_parse_failed_count,
            "title_symbol_extracted_count": title_symbol_extracted_count,
            "symbol_empty_event_count": symbol_empty_event_count,
            "candidate_validation_pending_count": candidate_validation_pending_count,
            "candidate_validation_success_count": candidate_validation_success_count,
            "candidate_validation_expired_count": candidate_validation_expired_count,
            "u_settlement_symbol_extracted_count": u_settlement_symbol_extracted_count,
            "pre_launch_validation_deferred_count": pre_launch_validation_deferred_count,
            "detail_pending_retry_count": detail_pending_retry_count,
            "detail_empty_payload_count": detail_empty_payload_count,
            "detail_http_not_ready_count": detail_http_not_ready_count,
            "detail_terminal_failed_count": detail_terminal_failed_count,
            "detail_transient_timeout_count": detail_transient_timeout_count,
            "detail_budget_starved_count": detail_budget_starved_count,
            "detail_never_attempted_expired_count": detail_never_attempted_expired_count,
            "detail_first_attempt_sla_breach_count": detail_first_attempt_sla_breach_count,
            "detail_scheduler_pending_count": detail_scheduler_pending_count,
            "detail_scheduler_backoff_count": detail_scheduler_backoff_count,
            "detail_endpoint_degraded_count": detail_endpoint_degraded_count,
            "detail_endpoint_degraded_active": detail_endpoint_degraded_active,
            "detail_success_symbols_empty_count": detail_success_symbols_empty_count,
            "detail_degraded_recent_retry_count": detail_degraded_recent_retry_count,
            "detail_fetch_fallback_attempt_count": detail_fetch_fallback_attempt_count,
            "detail_fetch_fallback_success_count": detail_fetch_fallback_success_count,
            "detail_fetch_attempt_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "bapi_detail_request_count": bapi_detail_request_count,
            "bapi_detail_success_count": bapi_detail_success_count,
            "bapi_detail_trusted_payload_count": bapi_detail_trusted_payload_count,
            "bapi_detail_schema_drift_count": bapi_detail_schema_drift_count,
            "bapi_detail_identity_mismatch_count": bapi_detail_identity_mismatch_count,
            "bapi_detail_rate_limited_count": bapi_detail_rate_limited_count,
            "bapi_to_support_fallback_count": bapi_to_support_fallback_count,
            "bapi_symbol_parse_success_count": bapi_symbol_parse_success_count,
            "bapi_symbol_validation_pending_count": bapi_symbol_validation_pending_count,
            "bapi_symbol_validation_success_count": bapi_symbol_validation_success_count,
            "support_fallback_success_count": detail_fetch_fallback_success_count,
            "detail_http_manifest_mismatch_count": detail_fetch_attempt_manifest_mismatch_count,
            "bapi_payload_revision_count": bapi_payload_revision_count,
            "bapi_payload_hash_change_count": bapi_payload_hash_change_count,
            "bapi_detail_source_degraded": source_health_diag["bapi_detail_source_degraded"],
            "support_detail_source_degraded": source_health_diag["support_detail_source_degraded"],
            "all_detail_sources_degraded": source_health_diag["all_detail_sources_degraded"],
        },
    )



    output_summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Summary written to {output_summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
