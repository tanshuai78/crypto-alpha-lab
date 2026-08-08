import glob
import hashlib
import json
import os
from pathlib import Path

from configs import base
from research.external_signal_shadow.stage1_5_launch_anchor_contract import (
    ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE,
    FORMAL_EVENT_CONTRACT_VERSION_V2,
    compute_admission_anchor_contract_hash,
    validate_launch_anchor_contract,
)
from src.research.external_signal_shadow.stage1_5_launch_event_contract import (
    validate_formal_launch_event,
)
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
    event_is_post_watermark,
    get_stable_event_key,
)
from src.risk.limits import RiskLimits

RUNTIME_GATE_SAFETY_FALSE_FIELDS = (
    "execution_feasibility_claim_allowed",
    "trade_signal_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "alpha_interpretation_allowed",
)


def derive_stage1_5d_root_from_events_glob(events_glob: str) -> Path | None:
    if not events_glob:
        return None
    normalized = events_glob.replace("\\", "/")
    marker = "/events/"
    if marker in normalized:
        return Path(normalized.split(marker, 1)[0]).resolve()
    path = Path(events_glob)
    if path.name == "*.jsonl" and path.parent.name == "events":
        return path.parent.parent.resolve()
    if path.parent.name == "events":
        return path.parent.parent.resolve()
    return path.parent.resolve()


def validate_stage1_5d_runtime_gate(
    stage1_5d_root_or_gate_path: str | Path,
    expected_events_glob: str = "",
    now_ms: int | None = None,
) -> dict:
    path = Path(stage1_5d_root_or_gate_path)
    if path.is_dir():
        gate_file = path / "live_safety_gate_summary.json"
    else:
        gate_file = path

    if not gate_file.exists() or not gate_file.is_file():
        return {
            "valid": False,
            "status": "MISSING",
            "reason": "runtime_gate_file_missing_or_corrupt",
            "gate_summary": None,
        }

    try:
        gate_data = json.loads(gate_file.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "valid": False,
            "status": "CORRUPT",
            "reason": "runtime_gate_file_missing_or_corrupt",
            "error": str(e),
            "gate_summary": None,
        }

    if gate_data.get("runtime_gate_schema_version") != 1:
        return {
            "valid": False,
            "decision": gate_data.get("decision", "UNKNOWN"),
            "status": gate_data.get("status", "UNKNOWN"),
            "reason": "runtime_gate_unsupported_version",
            "gate_summary": gate_data,
        }

    if gate_data.get("fatal_blockers"):
        return {
            "valid": False,
            "decision": gate_data.get("decision"),
            "status": "FAILED",
            "reason": "runtime_gate_fatal_blockers_present",
            "gate_summary": gate_data,
        }

    if gate_data.get("decision") != "stage1_5d_runtime_gate_ready":
        return {
            "valid": False,
            "decision": gate_data.get("decision"),
            "status": gate_data.get("status", "NOT_READY"),
            "reason": "runtime_gate_not_ready",
            "gate_summary": gate_data,
        }

    if not gate_data.get("consumable_by_stage1_5f"):
        return {
            "valid": False,
            "decision": gate_data.get("decision"),
            "status": gate_data.get("status"),
            "reason": "runtime_gate_not_consumable",
            "gate_summary": gate_data,
        }

    missing_or_true = [
        field for field in RUNTIME_GATE_SAFETY_FALSE_FIELDS
        if gate_data.get(field) is not False
    ]
    if missing_or_true:
        return {
            "valid": False,
            "decision": gate_data.get("decision"),
            "status": "FAILED",
            "reason": "runtime_gate_safety_field_missing_or_true",
            "unsafe_fields": missing_or_true,
            "gate_summary": gate_data,
        }

    if gate_data.get("live_trading_enabled") or RiskLimits.live_trading_enabled:
        return {
            "valid": False,
            "decision": gate_data.get("decision"),
            "status": "FAILED",
            "reason": "live_trading_enabled_invariant_violation",
            "gate_summary": gate_data,
        }

    if expected_events_glob:
        expected_root = derive_stage1_5d_root_from_events_glob(expected_events_glob)
        gate_root = Path(gate_data.get("source_root") or "").resolve()
        if expected_root is None or gate_root != expected_root:
            return {
                "valid": False,
                "decision": gate_data.get("decision"),
                "status": gate_data.get("status"),
                "reason": "runtime_gate_root_mismatch",
                "expected_root": str(expected_root) if expected_root else "",
                "source_root": str(gate_root),
                "gate_summary": gate_data,
            }

    if now_ms is not None:
        generated_at_ms = int(gate_data.get("generated_at_ms") or 0)
        max_staleness_ms = int(getattr(base, "EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC", 180) * 1000)
        if generated_at_ms <= 0 or now_ms - generated_at_ms > max_staleness_ms:
            return {
                "valid": False,
                "decision": gate_data.get("decision"),
                "status": gate_data.get("status"),
                "reason": "runtime_gate_stale",
                "stale": True,
                "gate_age_ms": now_ms - generated_at_ms if generated_at_ms else None,
                "gate_summary": gate_data,
            }

    return {
        "valid": True,
        "decision": gate_data.get("decision"),
        "status": "READY",
        "reason": None,
        "stale": False,
        "gate_summary": gate_data,
    }


def validate_historical_stage1_5d_safety_gate(
    summary_path: str | Path,
    bootstrap_watermark_ms: int | None,
) -> dict:
    path = Path(summary_path)
    if not path.exists() or not path.is_file():
        return {
            "valid": False,
            "reason": "historical_summary_missing",
        }

    if bootstrap_watermark_ms is None:
        return {
            "valid": False,
            "reason": "historical_classification_bootstrap_watermark_missing",
        }

    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "valid": False,
            "reason": f"historical_summary_corrupt:{e}",
        }

    if summary.get("decision") != "stage1_5d_smoke_ready":
        return {
            "valid": False,
            "reason": "historical_summary_decision_not_ready",
        }

    if summary.get("fatal_blockers"):
        return {
            "valid": False,
            "reason": "historical_summary_fatal_blockers_present",
        }

    if summary.get("live_trading_enabled") or RiskLimits.live_trading_enabled:
        return {
            "valid": False,
            "reason": "live_trading_enabled_invariant_violation",
        }

    return {
        "valid": True,
        "reason": None,
        "summary": summary,
    }


def historical_anchor_classification_allowed(watermark) -> bool:
    return (
        getattr(watermark, "watermark_schema_version", 1) >= 2
        and getattr(watermark, "bootstrap_max_seen_detected_at_ms", None) is not None
    )


def get_immutable_bootstrap_watermark_ms(watermark) -> int | None:
    if not historical_anchor_classification_allowed(watermark):
        return None
    return int(watermark.bootstrap_max_seen_detected_at_ms)



def iter_stage1_5d_event_rows(events_glob: str):
    for filepath in sorted(glob.glob(events_glob)):
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    pass


def flatten_event_symbols(event_row: dict):
    symbols = event_row.get("symbols")
    if not symbols:
        single_sym = event_row.get("symbol")
        if single_sym:
            yield {
                **event_row,
                "symbol": single_sym
            }
        else:
            yield {
                **event_row,
                "symbol": ""
            }
        return
    for symbol in symbols:
        yield {
            **event_row,
            "symbol": symbol
        }


def make_event_symbol_id(event_row: dict, symbol: str) -> str:
    sym = symbol.strip().upper()
    event_id = event_row.get("event_id")
    if not event_id:
        source_name = str(event_row.get("source_name") or "")
        source_article_id = str(event_row.get("source_article_id") or "")
        url = event_row.get("source_detail_url") or event_row.get("url") or ""
        # Advisory A fallback URL normalization rule
        source_detail_url_normalized = url.strip().rstrip("/").lower() if url else ""
        source_published_at_ms = str(event_row.get("source_published_at_ms") or "")

        raw_str = f"{source_name}|{source_article_id}|{source_detail_url_normalized}|{source_published_at_ms}|{sym}"
        event_id = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    raw_symbol_id_str = f"{event_id}|{sym}"
    return hashlib.sha256(raw_symbol_id_str.encode("utf-8")).hexdigest()


def make_stable_event_symbol_key(row: dict, symbol: str) -> str:
    source_article_id = str(row.get("source_article_id") or "")
    event_type = str(row.get("event_type") or "")
    sym = symbol.strip().upper() if symbol else ""
    if source_article_id:
        return f"{event_type}|{source_article_id}|{sym}"
    return f"{event_type}|{get_stable_event_key(row)}|{sym}"


def normalize_event_symbol_identity(flat_event: dict, symbol: str) -> dict:
    errors = []
    sym = (symbol or flat_event.get("symbol") or "").strip().upper()
    if not sym:
        errors.append("symbol_missing")

    detected_at_ms = _valid_ms(flat_event.get("detected_at_ms"))
    if detected_at_ms is None:
        errors.append("detected_at_ms_invalid_or_missing")

    source_article_id = str(flat_event.get("source_article_id") or "").strip()
    event_id = str(flat_event.get("event_id") or "").strip()
    if not source_article_id and not event_id:
        errors.append("source_article_id_and_event_id_both_missing")

    event_type = flat_event.get("event_type")
    if not event_type:
        errors.append("event_type_missing")

    identity_valid = len(errors) == 0
    event_symbol_id = flat_event.get("event_symbol_id") or (make_event_symbol_id(flat_event, sym) if sym else "")
    stable_key = flat_event.get("stable_event_symbol_key") or (make_stable_event_symbol_key(flat_event, sym) if sym else "")

    return {
        "identity_valid": identity_valid,
        "event_symbol_id": event_symbol_id,
        "stable_event_symbol_key": stable_key,
        "source_article_id": source_article_id,
        "event_id": event_id,
        "detected_at_ms": detected_at_ms,
        "identity_errors": errors,
    }


def classify_event_symbol_revision_admission(
    flat_event: dict,
    latest_states_by_id: dict,
    grouped_states_by_key: dict,
) -> tuple[str, object | None, dict]:
    sym = (flat_event.get("symbol") or "").strip().upper()
    event_symbol_id = flat_event.get("event_symbol_id") or make_event_symbol_id(flat_event, sym)
    stable_key = flat_event.get("stable_event_symbol_key") or make_stable_event_symbol_key(flat_event, sym)
    payload_hash = str(
        flat_event.get("detail_payload_hash")
        or flat_event.get("payload_hash")
        or flat_event.get("raw_payload_hash")
        or ""
    )

    existing = latest_states_by_id.get(event_symbol_id)
    if existing is not None:
        latest_event_id = getattr(existing, "latest_source_event_id", None) or existing.event_id
        if (
            latest_event_id == flat_event.get("event_id")
            and getattr(existing, "latest_event_payload_hash", "") == payload_hash
            and payload_hash != ""
        ):
            return "exact_replay_noop", existing, {"reason": "exact_payload_hash_replay"}

        status = getattr(existing, "status", "") or ""
        rej_reason = getattr(existing, "rejection_reason", "") or getattr(existing, "rejected_reason", "") or getattr(existing, "terminal_reason", "")
        existing_contract_status = getattr(existing, "source_contract_status", None)

        is_legacy_rejected = (
            status == "rejected"
            and (rej_reason == "symbol_not_in_exchangeinfo" or existing_contract_status == "legacy_unvalidated_recoverable")
        )
        new_contract_status = classify_stage1_5d_source_contract(flat_event, sym)["source_contract_status"]
        new_is_formal = new_contract_status in {"formal_v1_valid", "formal_v2_valid"}

        if status.startswith("pending_") or (is_legacy_rejected and new_is_formal):
            upgraded_reason = "legacy_rejected_upgraded_by_formal_v2" if new_contract_status == "formal_v2_valid" else "legacy_rejected_upgraded_by_formal_v1"
            return "pending_revision_upsert", existing, {"reason": "pending_state_revision" if status.startswith("pending_") else upgraded_reason}
        elif status in ("active", "completed", "active_anchor_revision_contaminated", "completed_anchor_revision_contaminated"):
            return "active_or_completed_duplicate_revision", existing, {"reason": f"existing_{status}_state"}
        else:
            return "terminal_revision_seen", existing, {"reason": f"terminal_{status}_state"}

    matching_key_states = grouped_states_by_key.get(stable_key, [])
    distinct_colliding = [s for s in matching_key_states if getattr(s, "event_symbol_id", None) != event_symbol_id]
    if distinct_colliding:
        return "identity_collision_blocked", distinct_colliding[0], {
            "reason": "stable_key_collision_with_distinct_event_symbol_id",
            "stable_event_symbol_key": stable_key,
            "colliding_event_symbol_id": getattr(distinct_colliding[0], "event_symbol_id", None),
            "new_event_symbol_id": event_symbol_id,
        }

    return "new_event_symbol", None, {"reason": "new_unseen_event_symbol"}


def upsert_pending_state_with_event_revision(pending_state, event_row: dict, symbol: str):
    if not getattr(pending_state, "status", "").startswith("pending_"):
        return pending_state

    event_id = event_row.get("event_id") or pending_state.event_id
    latest_payload_hash = str(
        event_row.get("detail_payload_hash")
        or event_row.get("payload_hash")
        or event_row.get("raw_payload_hash")
        or getattr(pending_state, "latest_event_payload_hash", "")
    )
    rev_count = int(getattr(pending_state, "revision_seen_count", 1) or 1) + 1

    d = pending_state.to_dict()
    d["latest_source_event_id"] = event_id
    d["latest_event_payload_hash"] = latest_payload_hash
    d["revision_seen_count"] = rev_count
    return pending_state.__class__.from_dict(d)



def _valid_ms(value) -> int | None:
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    return ms if ms > 0 else None


def _get_symbol_time(row: dict, field: str, symbol: str) -> int | None:
    data = row.get(field)
    if not isinstance(data, dict):
        return None
    sym = symbol.strip().upper()
    return _valid_ms(data.get(sym) or data.get(symbol))


def resolve_depth_observation_anchor_ms(row: dict, symbol: str, exchangeinfo_state: dict, now_ms: int) -> dict:
    sym = symbol.strip().upper()
    candidates = {}

    if row.get("formal_event_contract_version") == FORMAL_EVENT_CONTRACT_VERSION_V2:
        val = validate_launch_anchor_contract(row, sym, compatibility_mode=False)
        if val.get("valid"):
            official_anchor = _get_symbol_time(row, "symbol_official_schedule_anchor_ms", sym)
            exchangeinfo_onboard = _get_symbol_time(row, "symbol_exchangeinfo_onboard_date_ms", sym)
            effective_anchor = _valid_ms(val.get("effective_observation_anchor_ms"))
            effective_source = str(val.get("effective_observation_anchor_source") or "")
            if official_anchor:
                candidates["official_schedule_anchor"] = official_anchor
            if exchangeinfo_onboard:
                candidates["exchangeinfo_onboard_date"] = exchangeinfo_onboard

            ex_rows = exchangeinfo_state.get("symbol_rows", {}) if isinstance(exchangeinfo_state, dict) else {}
            ex_row = ex_rows.get(sym) or ex_rows.get(symbol) or {}
            ex_onboard = _valid_ms(ex_row.get("onboardDate"))
            if ex_onboard:
                candidates["exchangeinfo_current_onboard_time"] = ex_onboard

            disagreement_map = row.get("symbol_anchor_disagreement_ms", {})
            disagreement_ms = 0
            if isinstance(disagreement_map, dict):
                disagreement_ms = int(disagreement_map.get(sym) or disagreement_map.get(symbol) or 0)

            source_hashes = row.get("symbol_source_anchor_contract_hashes", {})
            evidence_levels = row.get("symbol_anchor_evidence_levels", {})
            max_classes = row.get("symbol_max_evidence_classes", {})
            return {
                "observation_anchor_ms": effective_anchor,
                "observation_anchor_basis": effective_source,
                "observation_anchor_confidence": "high" if effective_source == "official_schedule_anchor" else "medium",
                "observation_anchor_candidates": candidates,
                "observation_anchor_disagreement_max_ms": disagreement_ms,
                "observation_anchor_conflict_active": bool(val.get("observation_anchor_conflict_active", False)),
                "exchangeinfo_anchor_clean_eligible": False,
                "exchangeinfo_anchor_evidence": {
                    "payload_sha256": str(exchangeinfo_state.get("payload_sha256") or "") if isinstance(exchangeinfo_state, dict) else "",
                    "raw_payload_path": str(exchangeinfo_state.get("raw_payload_path") or "") if isinstance(exchangeinfo_state, dict) else "",
                    "fetched_at_ms": exchangeinfo_state.get("fetched_at_ms", 0) if isinstance(exchangeinfo_state, dict) else 0,
                },
                "source_anchor_contract_hash": source_hashes.get(sym) if isinstance(source_hashes, dict) else "",
                "anchor_contract_version": FORMAL_EVENT_CONTRACT_VERSION_V2,
                "anchor_precedence_policy": row.get("anchor_precedence_policy", ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE),
                "anchor_contract_decision_at_ms": row.get("anchor_contract_decision_at_ms"),
                "admission_anchor_evidence_level": evidence_levels.get(sym, "") if isinstance(evidence_levels, dict) else "",
                "latest_anchor_evidence_level": evidence_levels.get(sym, "") if isinstance(evidence_levels, dict) else "",
                "admission_max_evidence_class": max_classes.get(sym, "") if isinstance(max_classes, dict) else "",
                "latest_max_evidence_class": max_classes.get(sym, "") if isinstance(max_classes, dict) else "",
            }

    eff_launch = _get_symbol_time(row, "symbol_effective_launch_times_ms", sym)
    if eff_launch:
        candidates["symbol_effective_launch_time"] = eff_launch

    onboard_t = _get_symbol_time(row, "symbol_onboard_times_ms", sym)
    if onboard_t:
        candidates["symbol_onboard_time"] = onboard_t

    ex_rows = exchangeinfo_state.get("symbol_rows", {}) if isinstance(exchangeinfo_state, dict) else {}
    ex_row = ex_rows.get(sym) or ex_rows.get(symbol) or {}
    ex_status = str(ex_row.get("status") or "")
    ex_contract_type = str(ex_row.get("contractType") or "")
    ex_quote_asset = str(ex_row.get("quoteAsset") or "")
    ex_margin_asset = str(ex_row.get("marginAsset") or "")
    ex_onboard = _valid_ms(ex_row.get("onboardDate"))
    quote_margin_match = (
        ex_quote_asset in {"USDT", "USDC", "USD1", "BUSD"}
        and ex_margin_asset == ex_quote_asset
        and sym.endswith(ex_quote_asset)
    )
    perpetual_contract = ex_contract_type == "PERPETUAL" or ex_contract_type.endswith("_PERPETUAL")
    if ex_status in ("PENDING_TRADING", "TRADING") and perpetual_contract and quote_margin_match and ex_onboard:
        candidates["exchangeinfo_current_onboard_time"] = ex_onboard

    non_empty_values = [v for v in candidates.values() if v is not None]
    disagreement_max_ms = 0
    conflict_active = False
    if len(non_empty_values) > 1:
        disagreement_max_ms = max(non_empty_values) - min(non_empty_values)
        if disagreement_max_ms > base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS:
            conflict_active = True

    observation_anchor_ms = None
    observation_anchor_basis = ""
    observation_anchor_confidence = ""
    exchangeinfo_clean_eligible = False

    ex_payload_sha = str(exchangeinfo_state.get("payload_sha256") or "") if isinstance(exchangeinfo_state, dict) else ""

    if "symbol_effective_launch_time" in candidates:
        observation_anchor_ms = candidates["symbol_effective_launch_time"]
        observation_anchor_basis = "symbol_effective_launch_time"
        observation_anchor_confidence = "high"
    elif "symbol_onboard_time" in candidates:
        observation_anchor_ms = candidates["symbol_onboard_time"]
        observation_anchor_basis = "symbol_onboard_time"
        observation_anchor_confidence = "high"
    elif "exchangeinfo_current_onboard_time" in candidates:
        observation_anchor_ms = candidates["exchangeinfo_current_onboard_time"]
        observation_anchor_basis = "exchangeinfo_current_onboard_time"
        observation_anchor_confidence = "medium"
        if ex_payload_sha:
            exchangeinfo_clean_eligible = True

    ex_evidence = {
        "payload_sha256": ex_payload_sha,
        "raw_payload_path": str(exchangeinfo_state.get("raw_payload_path") or "") if isinstance(exchangeinfo_state, dict) else "",
        "fetched_at_ms": exchangeinfo_state.get("fetched_at_ms", 0) if isinstance(exchangeinfo_state, dict) else 0,
    }

    return {
        "observation_anchor_ms": observation_anchor_ms,
        "observation_anchor_basis": observation_anchor_basis,
        "observation_anchor_confidence": observation_anchor_confidence,
        "observation_anchor_candidates": candidates,
        "observation_anchor_disagreement_max_ms": disagreement_max_ms,
        "observation_anchor_conflict_active": conflict_active,
        "exchangeinfo_anchor_clean_eligible": exchangeinfo_clean_eligible,
        "exchangeinfo_anchor_evidence": ex_evidence,
    }


def build_first_seen_watermark_diagnostics(
    event_row: dict,
    symbol: str,
    diagnostics: dict,
    watermark,
    bootstrap_watermark_max_seen_detected_at_ms: int | None = None
) -> dict:
    res = resolve_announcement_capture_time_ms(event_row)
    ann_time = res[0] if isinstance(res, tuple) else res
    boot_wm = bootstrap_watermark_max_seen_detected_at_ms
    if boot_wm is None:
        boot_wm = watermark.max_seen_detected_at_ms if hasattr(watermark, "max_seen_detected_at_ms") else 0

    curr_wm = watermark.max_seen_detected_at_ms if hasattr(watermark, "max_seen_detected_at_ms") else 0

    ann_post_boot = bool(ann_time > boot_wm) if ann_time else True
    anchor_ms = diagnostics.get("observation_anchor_ms")
    anchor_post_boot = bool(anchor_ms > boot_wm) if anchor_ms else True

    return {
        "bootstrap_watermark_max_seen_detected_at_ms": boot_wm,
        "admission_watermark_at_first_seen_ms": curr_wm,
        "announcement_capture_post_bootstrap_watermark": ann_post_boot,
        "launch_anchor_post_bootstrap_watermark": anchor_post_boot,
    }



def re_resolve_pending_anchor(pending_state, event_revisions: list[dict], exchangeinfo_state: dict, now_ms: int):
    if not getattr(pending_state, "status", "").startswith("pending_"):
        return pending_state

    source_status = getattr(pending_state, "source_contract_status", None)
    is_legacy = source_status == "legacy_unvalidated_recoverable" or pending_state.status == "pending_source_event_unvalidated"

    if is_legacy:
        deadline = getattr(pending_state, "legacy_source_revision_wait_deadline_ms", None) or pending_state.anchor_resolution_deadline_ms
    else:
        deadline = pending_state.anchor_resolution_deadline_ms

    if deadline is not None and now_ms >= deadline:
        status = "rejected_launch_anchor_unavailable_timeout"
        if pending_state.status == "pending_anchor_conflict":
            status = "rejected_anchor_conflict_unresolved_timeout"
        d = pending_state.to_dict()
        d["status"] = status
        d["pending_terminal_reason"] = status
        return pending_state.__class__.from_dict(d)

    target_row = {}
    for rev in event_revisions:
        rev_stable_key = make_stable_event_symbol_key(rev, pending_state.symbol)
        stable_key_matches = (
            pending_state.stable_event_symbol_key
            and rev_stable_key == pending_state.stable_event_symbol_key
        )
        legacy_symbol_match = (
            not pending_state.stable_event_symbol_key
            and pending_state.symbol in rev.get("symbols", [])
        )
        if stable_key_matches or legacy_symbol_match:
            target_row = rev

    d = pending_state.to_dict()

    if target_row:
        if target_row.get("event_id"):
            d["event_id"] = target_row["event_id"]
            d["latest_source_event_id"] = target_row["event_id"]
        payload_hash = str(target_row.get("detail_payload_hash") or target_row.get("payload_hash") or target_row.get("raw_payload_hash") or "")
        if payload_hash:
            d["latest_event_payload_hash"] = payload_hash

        # Re-triage contract if revision provided
        c_res = classify_stage1_5d_source_contract(target_row, pending_state.symbol)
        d.update(c_res)
        source_status = c_res["source_contract_status"]

    anchor_diag = resolve_depth_observation_anchor_ms(target_row or pending_state.to_dict(), pending_state.symbol, exchangeinfo_state, now_ms)
    anchor_ms = anchor_diag.get("observation_anchor_ms")
    conflict_active = anchor_diag.get("observation_anchor_conflict_active", False)

    d["anchor_resolution_attempt_count"] = pending_state.anchor_resolution_attempt_count + 1
    d["last_anchor_resolution_at_ms"] = now_ms

    d["observation_anchor_candidates"] = anchor_diag.get("observation_anchor_candidates", {})
    d["observation_anchor_disagreement_max_ms"] = anchor_diag.get("observation_anchor_disagreement_max_ms", 0)
    d["observation_anchor_conflict_active"] = conflict_active
    for key in (
        "source_anchor_contract_hash",
        "anchor_contract_version",
        "anchor_precedence_policy",
        "anchor_contract_decision_at_ms",
        "admission_anchor_evidence_level",
        "latest_anchor_evidence_level",
        "admission_max_evidence_class",
        "latest_max_evidence_class",
        "source_detail_url_normalized",
        "source_published_at_ms",
        "formal_event_contract_version",
        "formal_event_consumable_by_stage1_5f",
        "symbol_identity_validation_status",
        "launch_anchor_evidence_level",
        "effective_observation_anchor_source",
        "launch_anchor_validation_status",
    ):
        val = anchor_diag.get(key) if anchor_diag.get(key) not in (None, "") else (target_row.get(key) if target_row and target_row.get(key) not in (None, "") else None)
        if val not in (None, ""):
            d[key] = val

    retry_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC * 1000
    d["next_anchor_resolution_at_ms"] = now_ms + retry_interval_ms

    if conflict_active:
        d["status"] = "pending_anchor_conflict"
        d["observation_anchor_ms"] = None
    elif anchor_ms is None:
        if source_status == "legacy_unvalidated_recoverable":
            d["status"] = "pending_source_event_unvalidated"
        else:
            d["status"] = "pending_launch_anchor_missing"
        d["observation_anchor_ms"] = None
    else:
        d["observation_anchor_ms"] = anchor_ms
        d["observation_anchor_basis"] = anchor_diag.get("observation_anchor_basis", "")
        d["observation_anchor_confidence"] = anchor_diag.get("observation_anchor_confidence", "")

        if source_status not in {"formal_v1_valid", "formal_v2_valid"}:
            d["status"] = "pending_source_event_unvalidated"
        elif now_ms < anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS:
            d["status"] = "pending_launch_time_in_future"
            d["next_admission_check_at_ms"] = anchor_ms
        else:
            d["status"] = "pending_ready_for_admission"
            d["next_admission_check_at_ms"] = now_ms
            _attach_admission_anchor_lineage(d, now_ms)

    return pending_state.__class__.from_dict(d)


def merge_first_seen_watermark_fields(existing_state, new_diagnostics: dict) -> dict:

    frozen_keys = (
        "bootstrap_watermark_max_seen_detected_at_ms",
        "admission_watermark_at_first_seen_ms",
        "announcement_capture_post_bootstrap_watermark",
        "launch_anchor_post_bootstrap_watermark",
    )
    result = dict(new_diagnostics)
    for k in frozen_keys:
        val = getattr(existing_state, k, None)
        if val is None and isinstance(existing_state, dict):
            val = existing_state.get(k)
        if val is not None:
            result[k] = val
    return result




def _event_identity_seen_by_watermark(row: dict, watermark) -> bool:
    event_id = row.get("event_id")
    source_article_id = row.get("source_article_id")
    stable_key = get_stable_event_key(row)

    if event_id and event_id in watermark.seen_event_ids:
        return True
    if source_article_id and source_article_id in watermark.seen_source_article_ids:
        return True
    return stable_key in watermark.seen_stable_event_keys


def delayed_launch_event_symbol_is_post_watermark(row: dict, symbol: str, watermark) -> bool:
    if _event_identity_seen_by_watermark(row, watermark):
        return False

    if row.get("symbol_extraction_source") not in {"title_contract_symbol", "detail_contract_symbol"}:
        return False
    if row.get("symbol_validation_status") != "validated":
        return False

    launch_time_ms = _get_symbol_time(row, "symbol_effective_observation_anchor_ms", symbol)
    if launch_time_ms is None:
        launch_time_ms = _get_symbol_time(row, "symbol_effective_launch_times_ms", symbol)
    if launch_time_ms is None:
        launch_time_ms = _get_symbol_time(row, "symbol_onboard_times_ms", symbol)
    return launch_time_ms is not None and launch_time_ms > watermark.max_seen_detected_at_ms


def delayed_launch_event_symbol_is_post_bootstrap_watermark(row: dict, symbol: str, bootstrap_watermark_ms: int) -> bool:
    if row.get("symbol_extraction_source") not in {"title_contract_symbol", "detail_contract_symbol"}:
        return False
    if row.get("symbol_validation_status") != "validated":
        return False

    launch_time_ms = _get_symbol_time(row, "symbol_effective_observation_anchor_ms", symbol)
    if launch_time_ms is None:
        launch_time_ms = _get_symbol_time(row, "symbol_effective_launch_times_ms", symbol)
    if launch_time_ms is None:
        launch_time_ms = _get_symbol_time(row, "symbol_onboard_times_ms", symbol)
    return launch_time_ms is not None and launch_time_ms > bootstrap_watermark_ms


def normalize_anchor_candidates(anchor_candidates: dict) -> dict:
    out = {}
    for key, value in (anchor_candidates or {}).items():
        try:
            v = int(value)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        if v < base.EXTERNAL_SIGNAL_STAGE1_5F_MIN_VALID_ANCHOR_EPOCH_MS or v > base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_VALID_ANCHOR_EPOCH_MS:
            continue
        out[key] = v
    return out


def classify_historical_anchor_pre_bootstrap(row: dict, symbol: str, anchor_diag: dict, watermark) -> tuple[str, str, dict]:
    boot = get_immutable_bootstrap_watermark_ms(watermark)
    normalized = normalize_anchor_candidates(anchor_diag.get("observation_anchor_candidates", {}))
    if not normalized:
        return "normal", "", {"normalized_anchor_candidates": normalized}

    max_seen = getattr(watermark, "max_seen_detected_at_ms", 0)
    cutoff = boot if boot is not None else max_seen

    detected_at_ms = row.get("detected_at_ms")
    if detected_at_ms and int(detected_at_ms) > cutoff:
        return "normal", "", {"normalized_anchor_candidates": normalized, "announcement_post_bootstrap_watermark": True}

    if delayed_launch_event_symbol_is_post_bootstrap_watermark(row, symbol, cutoff):
        return "normal", "", {"normalized_anchor_candidates": normalized, "delayed_launch_exception_active": True}

    if all(v <= cutoff for v in normalized.values()):
        if boot is None:
            return (
                "diagnostic_only",
                "historical_classification_bootstrap_watermark_missing",
                {
                    "historical_anchor_classification_allowed": False,
                    "bootstrap_watermark_missing": True,
                    "normalized_anchor_candidates": normalized,
                },
            )
        return (
            "ignored",
            "ignored_historical_anchor_pre_bootstrap",
            {
                "terminal_status": "ignored_historical_anchor_pre_bootstrap",
                "terminal_reason": "historical_anchor_pre_bootstrap",
                "normalized_anchor_candidates": normalized,
                "bootstrap_watermark_max_seen_detected_at_ms": boot,
                "normalized_anchor_class": "all_pre_bootstrap",
            },
        )

    return "normal", "", {"normalized_anchor_candidates": normalized}


def resolve_observation_age_base_ms(row: dict, symbol: str) -> tuple[int | None, str]:
    ms = _get_symbol_time(row, "symbol_effective_observation_anchor_ms", symbol)
    if ms is not None:
        source = row.get("symbol_effective_observation_anchor_sources", {})
        basis = source.get(symbol.strip().upper(), "effective_observation_anchor") if isinstance(source, dict) else "effective_observation_anchor"
        return ms, basis

    for field, basis in (
        ("symbol_effective_launch_times_ms", "symbol_effective_launch_time"),
        ("symbol_onboard_times_ms", "symbol_onboard_time"),
    ):
        ms = _get_symbol_time(row, field, symbol)
        if ms is not None:
            return ms, basis

    delayed_launch_allowed = bool(row.get("delayed_launch_observation_allowed"))
    delayed_contract_source = row.get("symbol_extraction_source") in {
        "title_contract_symbol",
        "detail_contract_symbol",
    }
    validated = row.get("symbol_validation_status") == "validated"
    sym = symbol.strip().upper()
    has_per_symbol_launch_metadata = any(
        isinstance(row.get(field), dict) and sym in row.get(field, {})
        for field in ("symbol_effective_launch_times_ms", "symbol_onboard_times_ms")
    )
    if delayed_launch_allowed or (delayed_contract_source and validated and has_per_symbol_launch_metadata):
        ms = _valid_ms(row.get("symbol_resolved_at_ms"))
        if ms is not None:
            return ms, "symbol_resolved_time"

    ms = _valid_ms(row.get("detected_at_ms"))
    if ms is not None:
        return ms, "detected_time"

    return None, "missing"


def resolve_announcement_capture_time_ms(row: dict) -> tuple[int | None, str]:
    for field in ("detected_at_ms", "available_at_ms", "collected_at_ms", "source_published_at_ms"):
        ms = _valid_ms(row.get(field))
        if ms is not None:
            return ms, field
    return None, "missing"


def _build_eligibility_diagnostics(
    row: dict,
    now_ms: int,
    watermark,
    observation_age_base_ms: int | None,
    observation_age_basis: str,
) -> dict:
    announcement_capture_time_ms, announcement_capture_time_source = resolve_announcement_capture_time_ms(row)
    max_age_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
    event_age_ms = None if observation_age_base_ms is None else now_ms - observation_age_base_ms

    return {
        "observation_age_base_ms": observation_age_base_ms,
        "observation_age_basis": observation_age_basis,
        "event_age_ms": event_age_ms,
        "max_event_age_ms": max_age_ms,
        "announcement_capture_time_ms": announcement_capture_time_ms,
        "announcement_capture_time_source": announcement_capture_time_source,
        "detected_at_ms": row.get("detected_at_ms"),
        "symbol_resolved_at_ms": row.get("symbol_resolved_at_ms"),
        "watermark_max_seen_detected_at_ms": watermark.max_seen_detected_at_ms,
        "watermark_version": watermark.watermark_version,
    }


def _attach_admission_anchor_lineage(diag: dict, now_ms: int) -> dict:
    source_hash = str(diag.get("source_anchor_contract_hash") or "")
    if not source_hash:
        return diag
    admission_hash = compute_admission_anchor_contract_hash(
        source_anchor_contract_hash=source_hash,
        admission_snapshot={
            "admission_at_ms": now_ms,
            "observation_anchor_ms": diag.get("observation_anchor_ms"),
            "evidence_start_class": diag.get("evidence_start_class"),
            "admission_max_evidence_class": diag.get("admission_max_evidence_class")
            or diag.get("latest_max_evidence_class")
            or "clean_or_recovery",
        },
    )
    diag["admission_anchor_contract_hash"] = admission_hash
    diag["latest_anchor_contract_hash"] = admission_hash
    return diag


def classify_stage1_5d_source_contract(row: dict, symbol: str) -> dict:
    if not isinstance(row, dict):
        return {
            "source_contract_status": "malformed",
            "pending_source_event_unvalidated": True,
            "required_source_revision": "formal_v2_valid",
            "source_contract_blocker": "row_not_dict",
        }

    if row.get("formal_event_contract_version") == FORMAL_EVENT_CONTRACT_VERSION_V2:
        if row.get("consumable_event_allowed") is False or row.get("formal_event_consumable_by_stage1_5f") is False or row.get("event_all_symbols_consumable_by_stage1_5f") is False:
            return {
                "source_contract_status": "explicit_non_consumable",
                "pending_source_event_unvalidated": False,
                "required_source_revision": "formal_v2_valid",
                "source_contract_blocker": "explicitly_marked_non_consumable",
            }
        val_v2 = validate_launch_anchor_contract(row, symbol, compatibility_mode=False)
        if val_v2["valid"]:
            return {
                "source_contract_status": "formal_v2_valid",
                "pending_source_event_unvalidated": False,
                "required_source_revision": None,
                "source_contract_blocker": None,
            }
        return {
            "source_contract_status": "malformed",
            "pending_source_event_unvalidated": True,
            "required_source_revision": "formal_v2_valid",
            "source_contract_blocker": f"contract_invalid:{','.join(val_v2.get('blockers', []))}",
        }

    val = validate_formal_launch_event(row, symbol)
    if val["valid"]:
        return {
            "source_contract_status": "formal_v1_valid",
            "pending_source_event_unvalidated": False,
            "required_source_revision": None,
            "source_contract_blocker": None,
        }

    if row.get("consumable_event_allowed") is False or row.get("formal_event_consumable_by_stage1_5f") is False:
        return {
            "source_contract_status": "explicit_non_consumable",
            "pending_source_event_unvalidated": False,
            "required_source_revision": "formal_v1_valid",
            "source_contract_blocker": "explicitly_marked_non_consumable",
        }

    code = row.get("source_article_id") or row.get("code") or row.get("event_id") or ""
    sym = (symbol or row.get("symbol") or (row.get("symbols") or [""])[0]).strip().upper()
    has_identity = bool(code and sym)

    if has_identity and "formal_event_contract_version" not in row:
        return {
            "source_contract_status": "legacy_unvalidated_recoverable",
            "pending_source_event_unvalidated": True,
            "required_source_revision": "formal_v1_valid",
            "source_contract_blocker": "legacy_unversioned_contract",
        }

    return {
        "source_contract_status": "malformed",
        "pending_source_event_unvalidated": True,
        "required_source_revision": "formal_v1_valid",
        "source_contract_blocker": f"contract_invalid:{','.join(val.get('blockers', []))}",
    }


def classify_event_symbol_eligibility_with_diagnostics(
    row: dict,
    symbol: str,
    now_ms: int,
    watermark,
    exchangeinfo_state: dict,
    budget_state: dict,
) -> tuple[str, str, dict]:
    norm_id = normalize_event_symbol_identity(row, symbol)
    if not norm_id["identity_valid"]:
        return "diagnostic_only", "malformed_source_identity", {"identity_diagnostics": norm_id}

    event_type = row.get("event_type")
    if event_type != "futures_contract_launch":
        return "rejected", "wrong_event_type", {}

    anchor_diag = resolve_depth_observation_anchor_ms(row, symbol, exchangeinfo_state or {}, now_ms)
    hist_status, hist_reason, hist_diag = classify_historical_anchor_pre_bootstrap(row, symbol, anchor_diag, watermark)

    anchor_ms = anchor_diag.get("observation_anchor_ms")
    diag = dict(anchor_diag)
    diag["announcement_capture_time_ms"], diag["announcement_capture_time_source"] = resolve_announcement_capture_time_ms(row)
    diag["observation_age_base_ms"] = anchor_ms
    diag["event_age_ms"] = (now_ms - anchor_ms) if anchor_ms is not None else None
    diag["max_event_age_ms"] = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
    diag["watermark_max_seen_detected_at_ms"] = getattr(watermark, "max_seen_detected_at_ms", 0)
    diag["watermark_version"] = getattr(watermark, "watermark_version", 1)
    diag.update(build_first_seen_watermark_diagnostics(row, symbol, diag, watermark))
    diag.update(hist_diag)

    if hist_status == "diagnostic_only":
        return "diagnostic_only", hist_reason, diag
    elif hist_status == "ignored":
        return "ignored", hist_reason, diag

    contract_res = classify_stage1_5d_source_contract(row, symbol)
    diag.update(contract_res)
    source_status = contract_res["source_contract_status"]

    if source_status == "explicit_non_consumable":
        return "diagnostic_only", "explicit_non_consumable", diag
    elif source_status == "malformed":
        return "diagnostic_only", "malformed_source_contract", diag

    if not event_is_post_watermark(row, watermark) and not delayed_launch_event_symbol_is_post_watermark(
        row, symbol, watermark
    ):
        return "rejected", "pre_watermark", {}

    conflict_active = anchor_diag.get("observation_anchor_conflict_active", False)
    if conflict_active:
        return "pending", "pending_anchor_conflict", diag

    if anchor_ms is None:
        diag["live_depth_evidence_basis"] = "recovery_validation_only"
        return "pending", "pending_launch_anchor_missing", diag

    if now_ms < anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS:
        diag["next_admission_check_at_ms"] = anchor_ms
        return "pending", "pending_launch_time_in_future", diag

    if source_status not in {"formal_v1_valid", "formal_v2_valid"}:
        return "pending", "pending_source_event_unvalidated", diag

    if not exchangeinfo_state or not exchangeinfo_state.get("available", False):
        return "pending", "pending_exchangeinfo_unavailable", diag

    symbols_in_exchange = exchangeinfo_state.get("symbols", set())
    if symbol not in symbols_in_exchange:
        delay_ms = now_ms - anchor_ms
        if delay_ms <= base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS:
            return "pending", "pending_exchangeinfo_symbol_not_visible_after_anchor", diag
        else:
            return "rejected", "rejected_launch_symbol_not_visible_timeout", diag

    if budget_state and budget_state.get("budget_exceeded", False):
        return "pending", "pending_observation_capacity", diag

    delay_ms = now_ms - anchor_ms
    clean_delay_max = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS
    recovery_delay_max = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS

    max_evidence_class = diag.get("admission_max_evidence_class") or diag.get("latest_max_evidence_class") or "clean_or_recovery"
    if max_evidence_class != "clean_or_recovery":
        diag["evidence_start_class"] = "recovery_start"
        diag["live_depth_evidence_basis"] = "recovery_validation_only"
        diag["clean_start_forbidden_reason"] = "anchor_contract_not_clean_eligible"
        _attach_admission_anchor_lineage(diag, now_ms)
        return "eligible", "eligible_recovery_only", diag

    if delay_ms <= clean_delay_max:
        diag["evidence_start_class"] = "clean_start"
        diag["live_depth_evidence_basis"] = "announcement_and_launch_time"
        _attach_admission_anchor_lineage(diag, now_ms)
        return "eligible", "eligible_clean_start", diag
    elif delay_ms <= recovery_delay_max:
        diag["evidence_start_class"] = "recovery_start"
        diag["live_depth_evidence_basis"] = "recovery_validation_only"
        _attach_admission_anchor_lineage(diag, now_ms)
        return "eligible", "eligible_recovery_only", diag
    else:
        diag["evidence_start_class"] = "expired"
        return "rejected", "rejected_launch_anchor_age_exceeded", diag


def classify_event_symbol_eligibility(
    row: dict,
    symbol: str,
    now_ms: int,
    watermark,
    exchangeinfo_state: dict,
    budget_state: dict,
) -> tuple[str, str]:
    status, reason, _diag = classify_event_symbol_eligibility_with_diagnostics(
        row, symbol, now_ms, watermark, exchangeinfo_state, budget_state
    )
    return status, reason


def classify_live_depth_evidence_basis(row: dict, watermark) -> dict:
    if "announcement_capture_post_bootstrap_watermark" in row and row["announcement_capture_post_bootstrap_watermark"] is not None:
        ann_post = bool(row["announcement_capture_post_bootstrap_watermark"])
        launch_post = bool(row.get("launch_anchor_post_bootstrap_watermark", False))
        evidence_start_class = row.get("evidence_start_class", "")
        if evidence_start_class == "recovery_start":
            basis = "recovery_validation_only"
        elif ann_post and launch_post:
            basis = "announcement_and_launch_time"
        elif launch_post:
            basis = "launch_time_only"
        else:
            basis = "recovery_validation_only"

        return {
            "announcement_capture_time_ms": row.get("announcement_capture_time_ms"),
            "announcement_capture_time_source": row.get("announcement_capture_time_source", ""),
            "announcement_time_capture_evidence_allowed": ann_post,
            "launch_time_depth_evidence_allowed": launch_post,
            "live_depth_evidence_basis": basis,
        }

    announcement_capture_time_ms, announcement_capture_time_source = resolve_announcement_capture_time_ms(row)
    observation_age_base_ms, observation_age_basis = resolve_observation_age_base_ms(
        row, row.get("symbol") or (row.get("symbols") or [""])[0]
    )

    announcement_after_watermark = (
        announcement_capture_time_ms is not None
        and announcement_capture_time_ms > watermark.max_seen_detected_at_ms
    )
    observation_after_watermark = (
        observation_age_base_ms is not None
        and observation_age_base_ms > watermark.max_seen_detected_at_ms
    )

    return {
        "announcement_capture_time_ms": announcement_capture_time_ms,
        "announcement_capture_time_source": announcement_capture_time_source,
        "announcement_time_capture_evidence_allowed": bool(announcement_after_watermark),
        "launch_time_depth_evidence_allowed": bool(observation_after_watermark),
        "live_depth_evidence_basis": (
            "announcement_and_launch_time"
            if announcement_after_watermark and observation_after_watermark
            else "launch_time_only"
            if observation_after_watermark
            else "recovery_validation_only"
        ),
    }



def validate_stage1_5d_summary(summary_path: str) -> None:
    if not os.path.exists(summary_path):
        raise FileNotFoundError(f"Stage 1.5D summary file not found at {summary_path}")

    try:
        with open(summary_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Corrupted Stage 1.5D summary JSON: {e}")

    decision = data.get("decision")
    if decision in ("stage1_5d_smoke_invalid", "stage1_5d_smoke_failed"):
        raise ValueError(f"Stage 1.5D decision is invalid or failed: {decision}")

    risk_fields = [
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_engine_allowed",
        "alpha_interpretation_allowed",
    ]
    for field in risk_fields:
        if data.get(field) is not False:
            raise ValueError(f"Safety violation: Stage 1.5D summary has {field} = {data.get(field)}")

    if "trade_signal_allowed" in data and data.get("trade_signal_allowed") is not False:
        raise ValueError(f"Safety violation: Stage 1.5D summary has trade_signal_allowed = {data.get('trade_signal_allowed')}")
