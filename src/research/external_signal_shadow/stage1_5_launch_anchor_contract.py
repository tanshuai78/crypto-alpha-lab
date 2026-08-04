"""
src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py
Single Source of Truth (SSOT) for Stage 1.5 Official Schedule Priority Anchor Contract V2.
"""

import hashlib
import json
from typing import Any

FORMAL_EVENT_CONTRACT_VERSION_V2 = 2
FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION = 1
ANCHOR_CONTRACT_HASH_SCHEMA_VERSION = 1
ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE = "official_schedule_priority_v1"

REVISION_SELECTOR_STATUSES = {
    "selected",
    "cancelled",
    "postponed_without_anchor",
    "official_schedule_conflict",
    "missing",
    "malformed",
}
ANCHOR_SOURCES = {"official_schedule_anchor", "exchangeinfo_onboard_date", "none"}
ANCHOR_EVIDENCE_LEVELS = {"official_schedule", "exchangeinfo_fallback", "missing", "official_conflict", "malformed"}
MAX_EVIDENCE_CLASSES = {"clean_or_recovery", "recovery_validation_only", "diagnostic_only", "none"}
MAPPING_CONFIDENCE_VALUES = {"exact_single_symbol", "exact_per_symbol_row", "exact_all_symbols_statement", "ambiguous"}
REQUIRED_OFFICIAL_PROVENANCE_FIELDS = {
    "raw_time_text",
    "timezone_text",
    "node_path",
    "logical_block_id",
    "schedule_text_context",
    "payload_sha256",
    "parser_version",
    "mapping_method",
}


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 bytes for canonical JSON serialization."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def select_latest_applicable_official_schedule(symbol: str, revisions: list[dict[str, Any]], as_of_ms: int) -> dict[str, Any]:
    """
    Return point-in-time selection for revisions with available_at_ms <= as_of_ms.
    Rules:
    - Ignore available_at_ms > as_of_ms.
    - Ignore non-matching symbol.
    - Equal available_at_ms conflicts fail-closed.
    - Revision ID lexical ordering MUST NOT resolve semantic conflicts.
    """
    applicable = [
        r for r in revisions
        if r.get("symbol") == symbol and isinstance(r.get("available_at_ms"), (int, float)) and r["available_at_ms"] <= as_of_ms
    ]
    if not applicable:
        return {
            "status": "missing",
            "effective_official_anchor_ms": None,
            "revision_id": None,
            "available_at_ms": None,
            "consumable": False,
            "pending_reason": "official_schedule_missing",
        }

    # Find max available_at_ms
    max_avail = max(r["available_at_ms"] for r in applicable)
    latest_candidates = [r for r in applicable if r["available_at_ms"] == max_avail]

    if len(latest_candidates) > 1:
        # Check if they disagree semantically
        signatures = set()
        for c in latest_candidates:
            sig = (c.get("status"), c.get("anchor_ms"), c.get("supersedes_revision_id"))
            signatures.add(sig)
        if len(signatures) > 1:
            return {
                "status": "official_schedule_conflict",
                "effective_official_anchor_ms": None,
                "revision_id": None,
                "available_at_ms": max_avail,
                "consumable": False,
                "pending_reason": "equal_timestamp_schedule_conflict",
            }

    latest = latest_candidates[0]
    st = latest.get("status", "scheduled")
    anchor_ms = latest.get("anchor_ms")
    rev_id = latest.get("revision_id")

    if st == "cancelled":
        return {
            "status": "cancelled",
            "effective_official_anchor_ms": None,
            "revision_id": rev_id,
            "available_at_ms": max_avail,
            "consumable": False,
            "pending_reason": "official_schedule_cancelled",
        }
    elif st in ("postponed", "rescheduled") and anchor_ms is None:
        return {
            "status": "postponed_without_anchor",
            "effective_official_anchor_ms": None,
            "revision_id": rev_id,
            "available_at_ms": max_avail,
            "consumable": False,
            "pending_reason": "pending_schedule_revision",
        }
    elif anchor_ms is not None:
        return {
            "status": "selected",
            "effective_official_anchor_ms": anchor_ms,
            "revision_id": rev_id,
            "available_at_ms": max_avail,
            "consumable": True,
            "pending_reason": None,
        }
    else:
        return {
            "status": "malformed",
            "effective_official_anchor_ms": None,
            "revision_id": rev_id,
            "available_at_ms": max_avail,
            "consumable": False,
            "pending_reason": "malformed_schedule_revision",
        }


def build_symbol_anchor_contract(
    *,
    symbol: str,
    official_schedule_anchor_ms: int | None,
    exchangeinfo_onboard_date_ms: int | None,
    anchor_contract_decision_at_ms: int,
    official_schedule_revision_id: str | None,
    official_schedule_available_at_ms: int | None,
    mapping_confidence: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Build one per-symbol anchor contract dictionary."""
    is_official_valid = (
        official_schedule_anchor_ms is not None
        and mapping_confidence in MAPPING_CONFIDENCE_VALUES
        and mapping_confidence != "ambiguous"
    )

    if is_official_valid:
        effective_anchor_ms = official_schedule_anchor_ms
        effective_source = "official_schedule_anchor"
        evidence_level = "official_schedule"
        max_evidence_class = "clean_or_recovery"
        validation_status = "valid_official"
    elif exchangeinfo_onboard_date_ms is not None and exchangeinfo_onboard_date_ms > 0:
        effective_anchor_ms = exchangeinfo_onboard_date_ms
        effective_source = "exchangeinfo_onboard_date"
        evidence_level = "exchangeinfo_fallback"
        max_evidence_class = "recovery_validation_only"
        validation_status = "valid_fallback"
    else:
        effective_anchor_ms = None
        effective_source = "none"
        evidence_level = "missing"
        max_evidence_class = "none"
        validation_status = "missing"

    disagreement_ms = None
    disagreement_direction = "none"
    comparison_status = "missing"

    if official_schedule_anchor_ms is not None and exchangeinfo_onboard_date_ms is not None:
        disagreement_ms = abs(official_schedule_anchor_ms - exchangeinfo_onboard_date_ms)
        if exchangeinfo_onboard_date_ms < official_schedule_anchor_ms:
            disagreement_direction = "exchangeinfo_earlier"
        elif exchangeinfo_onboard_date_ms > official_schedule_anchor_ms:
            disagreement_direction = "exchangeinfo_later"
        else:
            disagreement_direction = "none"

        if disagreement_ms == 0:
            comparison_status = "article_exchangeinfo_match"
        else:
            comparison_status = "exchangeinfo_disagrees_with_official_schedule"
    elif official_schedule_anchor_ms is not None:
        comparison_status = "single_source_official_schedule"
    elif exchangeinfo_onboard_date_ms is not None:
        comparison_status = "single_source_exchangeinfo"

    contract = {
        "symbol": symbol,
        "official_schedule_anchor_ms": official_schedule_anchor_ms,
        "exchangeinfo_onboard_date_ms": exchangeinfo_onboard_date_ms,
        "effective_observation_anchor_ms": effective_anchor_ms,
        "effective_observation_anchor_source": effective_source,
        "anchor_evidence_level": evidence_level,
        "max_evidence_class": max_evidence_class,
        "validation_status": validation_status,
        "comparison_status": comparison_status,
        "disagreement_ms": disagreement_ms,
        "disagreement_direction": disagreement_direction,
        "mapping_confidence": mapping_confidence,
        "anchor_contract_decision_at_ms": anchor_contract_decision_at_ms,
        "official_schedule_revision_id": official_schedule_revision_id,
        "official_schedule_available_at_ms": official_schedule_available_at_ms,
        "provenance": provenance,
    }

    # Compute source anchor contract hash for symbol
    contract["source_anchor_contract_hash"] = compute_source_anchor_contract_hash(contract, symbol)
    return contract


def build_formal_event_anchor_contract_row(
    *,
    base_event: dict[str, Any],
    symbol_contracts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Return complete formal V2 event row wrapping per-symbol contracts."""
    row = dict(base_event)
    symbols = row.get("symbols", list(symbol_contracts.keys()))

    row["formal_event_contract_version"] = FORMAL_EVENT_CONTRACT_VERSION_V2
    row["anchor_precedence_policy"] = ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE

    decision_at_ms = max(
        (c.get("anchor_contract_decision_at_ms", 0) for c in symbol_contracts.values()),
        default=row.get("detected_at_ms", 0),
    )
    row["anchor_contract_decision_at_ms"] = decision_at_ms
    row["official_schedule_selection_as_of_ms"] = decision_at_ms
    row["latest_known_revision_id_at_decision"] = row.get("latest_known_revision_id_at_decision")

    row["symbol_official_schedule_anchor_ms"] = {s: symbol_contracts[s].get("official_schedule_anchor_ms") for s in symbols if s in symbol_contracts}
    row["symbol_exchangeinfo_onboard_date_ms"] = {s: symbol_contracts[s].get("exchangeinfo_onboard_date_ms") for s in symbols if s in symbol_contracts}
    row["symbol_effective_observation_anchor_ms"] = {s: symbol_contracts[s].get("effective_observation_anchor_ms") for s in symbols if s in symbol_contracts}
    row["symbol_effective_observation_anchor_sources"] = {s: symbol_contracts[s].get("effective_observation_anchor_source") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_evidence_levels"] = {s: symbol_contracts[s].get("anchor_evidence_level") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_comparison_statuses"] = {s: symbol_contracts[s].get("comparison_status") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_disagreement_ms"] = {s: symbol_contracts[s].get("disagreement_ms") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_disagreement_directions"] = {s: symbol_contracts[s].get("disagreement_direction") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_validation_statuses"] = {s: symbol_contracts[s].get("validation_status") for s in symbols if s in symbol_contracts}
    row["symbol_max_evidence_classes"] = {s: symbol_contracts[s].get("max_evidence_class") for s in symbols if s in symbol_contracts}
    row["symbol_anchor_provenance"] = {s: symbol_contracts[s].get("provenance", {}) for s in symbols if s in symbol_contracts}
    row["symbol_official_schedule_statuses"] = {s: symbol_contracts[s].get("official_schedule_status", "selected") for s in symbols if s in symbol_contracts}
    row["symbol_official_schedule_revision_ids"] = {s: symbol_contracts[s].get("official_schedule_revision_id") for s in symbols if s in symbol_contracts}
    row["symbol_official_schedule_revision_available_at_ms"] = {s: symbol_contracts[s].get("official_schedule_available_at_ms") for s in symbols if s in symbol_contracts}
    row["symbol_source_anchor_contract_hashes"] = {s: symbol_contracts[s].get("source_anchor_contract_hash") for s in symbols if s in symbol_contracts}

    # Aggregate status calculations
    has_fallback = any(c.get("effective_observation_anchor_source") == "exchangeinfo_onboard_date" for c in symbol_contracts.values())
    has_official = any(c.get("effective_observation_anchor_source") == "official_schedule_anchor" for c in symbol_contracts.values())
    has_missing = any(c.get("effective_observation_anchor_source") == "none" for c in symbol_contracts.values())
    has_conflict = any(c.get("comparison_status") == "official_schedule_conflict" for c in symbol_contracts.values())
    has_malformed = any(c.get("validation_status") == "malformed" for c in symbol_contracts.values())

    if has_malformed:
        agg_status = "malformed"
    elif has_conflict:
        agg_status = "has_official_conflict"
    elif has_missing:
        agg_status = "has_missing"
    elif has_official and has_fallback:
        agg_status = "mixed_official_and_fallback"
    elif has_official:
        agg_status = "all_official_valid"
    else:
        agg_status = "fallback_only"

    disagreements = [c["disagreement_ms"] for c in symbol_contracts.values() if c.get("disagreement_ms") is not None]
    max_disagreement = max(disagreements) if disagreements else None

    all_consumable = (
        len(symbol_contracts) == len(symbols)
        and not has_missing
        and not has_conflict
        and not has_malformed
    )
    all_clean_eligible = (
        all_consumable
        and all(c.get("max_evidence_class") == "clean_or_recovery" for c in symbol_contracts.values())
    )

    row["event_anchor_aggregate_status"] = agg_status
    row["event_has_fallback_anchor"] = has_fallback
    row["event_has_official_conflict"] = has_conflict
    row["event_has_anchor_missing"] = has_missing
    row["event_max_anchor_disagreement_ms"] = max_disagreement
    row["event_all_symbols_consumable_by_stage1_5f"] = all_consumable
    row["event_all_symbols_clean_eligible"] = all_clean_eligible

    return row


def build_formal_schedule_revision_row(
    *,
    source_article_id: str,
    supersedes_source_article_id: str,
    symbol: str,
    revised_anchor_ms: int | None,
    superseded_anchor_ms: int | None,
    revision_id: str,
    revision_payload_hash: str,
    revision_available_at_ms: int,
    revision_reason: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Build a formal schedule revision transport row for Stage 1.5D -> 1.5F."""
    sym = str(symbol or "").strip().upper()
    stable_identity = f"binance|futures_contract_launch|{supersedes_source_article_id}|{sym}" if supersedes_source_article_id and sym else ""
    status = "rescheduled" if revised_anchor_ms is not None else "postponed_without_anchor"
    return {
        "event_type": "futures_contract_launch_schedule_revision",
        "formal_schedule_revision_contract_version": FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION,
        "source_article_id": source_article_id,
        "supersedes_source_article_id": supersedes_source_article_id,
        "stable_schedule_identity": stable_identity,
        "symbols": [sym] if sym else [],
        "symbol_official_schedule_statuses": {sym: status} if sym else {},
        "symbol_revised_anchor_ms": {sym: revised_anchor_ms} if sym else {},
        "symbol_official_schedule_revision_ids": {sym: revision_id} if sym else {},
        "symbol_official_schedule_revision_available_at_ms": {sym: revision_available_at_ms} if sym else {},
        "symbol_superseded_anchor_ms": {sym: superseded_anchor_ms} if sym else {},
        "revision_id": revision_id,
        "revision_payload_hash": revision_payload_hash,
        "revision_reason": revision_reason,
        "revision_link_status": "linked" if stable_identity else "ambiguous",
        "anchor_precedence_policy": ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE,
        "revision_provenance": provenance or {},
    }


def validate_schedule_revision_contract(row: dict[str, Any]) -> dict[str, Any]:
    """Validate the formal schedule revision transport row."""
    blockers = []
    if row.get("event_type") != "futures_contract_launch_schedule_revision":
        blockers.append("event_type_not_schedule_revision")
    if row.get("formal_schedule_revision_contract_version") != FORMAL_SCHEDULE_REVISION_CONTRACT_VERSION:
        blockers.append("formal_schedule_revision_contract_version_invalid")
    symbols = [str(s).strip().upper() for s in (row.get("symbols") or []) if str(s).strip()]
    if len(symbols) != 1:
        blockers.append("revision_symbol_count_not_one")
    symbol = symbols[0] if len(symbols) == 1 else ""
    if not row.get("source_article_id"):
        blockers.append("source_article_id_missing")
    if not row.get("supersedes_source_article_id"):
        blockers.append("supersedes_source_article_id_missing")
    if not row.get("stable_schedule_identity"):
        blockers.append("stable_schedule_identity_missing")
    if not row.get("revision_id"):
        blockers.append("revision_id_missing")
    if not row.get("revision_payload_hash"):
        blockers.append("revision_payload_hash_missing")
    if row.get("anchor_precedence_policy") != ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE:
        blockers.append("anchor_precedence_policy_invalid")
    if symbol:
        if symbol not in (row.get("symbol_official_schedule_statuses") or {}):
            blockers.append("symbol_official_schedule_status_missing")
        if symbol not in (row.get("symbol_revised_anchor_ms") or {}):
            blockers.append("symbol_revised_anchor_ms_missing")
        if symbol not in (row.get("symbol_official_schedule_revision_ids") or {}):
            blockers.append("symbol_official_schedule_revision_id_missing")
        if symbol not in (row.get("symbol_official_schedule_revision_available_at_ms") or {}):
            blockers.append("symbol_official_schedule_revision_available_at_ms_missing")
    provenance = row.get("revision_provenance") or {}
    if not {"payload_sha256", "parser_version"}.issubset(provenance.keys()):
        blockers.append("revision_provenance_missing")

    return {
        "valid": len(blockers) == 0,
        "blockers": blockers,
        "stable_schedule_identity": row.get("stable_schedule_identity", ""),
        "symbol": symbol,
    }


def validate_launch_anchor_contract(row: dict[str, Any], symbol: str, *, compatibility_mode: bool = False) -> dict[str, Any]:
    """Validate a launch anchor contract row for a target symbol."""
    blockers = []

    contract_ver = row.get("formal_event_contract_version")
    if contract_ver != FORMAL_EVENT_CONTRACT_VERSION_V2:
        if not compatibility_mode:
            blockers.append("formal_event_contract_version_not_v2")

    if not compatibility_mode:
        if row.get("anchor_precedence_policy") != ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE:
            blockers.append("anchor_precedence_policy_invalid")

    # Check per-symbol fields
    eff_anchor_map = row.get("symbol_effective_observation_anchor_ms", {})
    eff_source_map = row.get("symbol_effective_observation_anchor_sources", {})
    max_class_map = row.get("symbol_max_evidence_classes", {})
    comp_map = row.get("symbol_anchor_comparison_statuses", {})
    prov_map = row.get("symbol_anchor_provenance", {})

    eff_anchor = eff_anchor_map.get(symbol) if isinstance(eff_anchor_map, dict) else None
    eff_source = eff_source_map.get(symbol) if isinstance(eff_source_map, dict) else None
    max_class = max_class_map.get(symbol) if isinstance(max_class_map, dict) else None
    comp_status = comp_map.get(symbol) if isinstance(comp_map, dict) else None

    # Scalar fallback check if maps missing in legacy rows
    if eff_anchor is None and "symbol_effective_launch_times_ms" in row:
        eff_anchor = row["symbol_effective_launch_times_ms"].get(symbol)

    if eff_source is None:
        eff_source = row.get("symbol_effective_observation_anchor_source", "none")

    if eff_source not in ANCHOR_SOURCES:
        blockers.append("effective_anchor_source_invalid")

    if eff_source == "official_schedule_anchor":
        official_anchor = row.get("symbol_official_schedule_anchor_ms", {}).get(symbol)
        if official_anchor is None:
            official_anchor = eff_anchor
        if eff_anchor != official_anchor:
            blockers.append("effective_anchor_does_not_match_official_anchor")
        prov = prov_map.get(symbol, {}) if isinstance(prov_map, dict) else {}
        if not REQUIRED_OFFICIAL_PROVENANCE_FIELDS.issubset(prov.keys()):
            blockers.append("official_schedule_provenance_missing")

    if eff_source == "exchangeinfo_onboard_date":
        if max_class == "clean_or_recovery":
            blockers.append("exchangeinfo_fallback_clean_forbidden")

    is_valid = len(blockers) == 0
    return {
        "valid": is_valid,
        "blockers": blockers,
        "effective_observation_anchor_ms": eff_anchor,
        "effective_observation_anchor_source": eff_source,
        "max_evidence_class": max_class or ("clean_or_recovery" if is_valid else "none"),
        "symbol_anchor_comparison_statuses": comp_map,
        "observation_anchor_conflict_active": (comp_status == "official_schedule_conflict"),
    }


def compute_source_anchor_contract_hash(row_or_symbol_contract: dict[str, Any], symbol: str) -> str:
    """Compute deterministic SHA256 hash for source anchor contract."""
    data = row_or_symbol_contract
    # Extract symbol contract fields
    if "symbol_effective_observation_anchor_ms" in data:
        eff_anchor = data.get("symbol_effective_observation_anchor_ms", {}).get(symbol)
        eff_source = data.get("symbol_effective_observation_anchor_sources", {}).get(symbol)
        ev_level = data.get("symbol_anchor_evidence_levels", {}).get(symbol)
        max_class = data.get("symbol_max_evidence_classes", {}).get(symbol)
        val_status = data.get("symbol_anchor_validation_statuses", {}).get(symbol)
        comp_status = data.get("symbol_anchor_comparison_statuses", {}).get(symbol)
        off_anchor = data.get("symbol_official_schedule_anchor_ms", {}).get(symbol)
        onboard_date = data.get("symbol_exchangeinfo_onboard_date_ms", {}).get(symbol)
        rev_id = data.get("symbol_official_schedule_revision_ids", {}).get(symbol)
        avail_ms = data.get("symbol_official_schedule_revision_available_at_ms", {}).get(symbol)
        prov = data.get("symbol_anchor_provenance", {}).get(symbol, {})
        contract_ver = data.get("formal_event_contract_version", FORMAL_EVENT_CONTRACT_VERSION_V2)
        policy = data.get("anchor_precedence_policy", ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE)
        decision_ms = data.get("anchor_contract_decision_at_ms")
        as_of_ms = data.get("official_schedule_selection_as_of_ms")
        article_id = data.get("source_article_id")
    else:
        eff_anchor = data.get("effective_observation_anchor_ms")
        eff_source = data.get("effective_observation_anchor_source")
        ev_level = data.get("anchor_evidence_level")
        max_class = data.get("max_evidence_class")
        val_status = data.get("validation_status")
        comp_status = data.get("comparison_status")
        off_anchor = data.get("official_schedule_anchor_ms")
        onboard_date = data.get("exchangeinfo_onboard_date_ms")
        rev_id = data.get("official_schedule_revision_id")
        avail_ms = data.get("official_schedule_available_at_ms")
        prov = data.get("provenance", {})
        contract_ver = FORMAL_EVENT_CONTRACT_VERSION_V2
        policy = ANCHOR_PRECEDENCE_POLICY_OFFICIAL_SCHEDULE
        decision_ms = data.get("anchor_contract_decision_at_ms")
        as_of_ms = decision_ms
        article_id = data.get("article_id")

    payload = {
        "hash_schema_version": ANCHOR_CONTRACT_HASH_SCHEMA_VERSION,
        "symbol": symbol,
        "source_article_id": article_id,
        "formal_event_contract_version": contract_ver,
        "anchor_precedence_policy": policy,
        "anchor_contract_decision_at_ms": decision_ms,
        "official_schedule_selection_as_of_ms": as_of_ms,
        "selected_official_schedule_revision_id": rev_id,
        "selected_official_schedule_available_at_ms": avail_ms,
        "official_schedule_anchor_ms": off_anchor,
        "exchangeinfo_onboard_date_ms": onboard_date,
        "effective_observation_anchor_ms": eff_anchor,
        "effective_observation_anchor_source": eff_source,
        "anchor_evidence_level": ev_level,
        "max_evidence_class": max_class,
        "validation_status": val_status,
        "comparison_status": comp_status,
        "mapping_confidence": data.get("mapping_confidence", prov.get("mapping_confidence")),
        "payload_sha256": prov.get("payload_sha256"),
        "parser_version": prov.get("parser_version"),
        "logical_block_id": prov.get("logical_block_id"),
        "node_path": prov.get("node_path"),
        "raw_time_text": prov.get("raw_time_text"),
        "timezone_text": prov.get("timezone_text"),
    }

    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_admission_anchor_contract_hash(*, source_anchor_contract_hash: str, admission_snapshot: dict[str, Any]) -> str:
    """Compute deterministic SHA256 hash for admission anchor contract."""
    payload = {
        "hash_schema_version": ANCHOR_CONTRACT_HASH_SCHEMA_VERSION,
        "source_anchor_contract_hash": source_anchor_contract_hash,
        "admission_at_ms": admission_snapshot.get("admission_at_ms"),
        "observation_anchor_ms": admission_snapshot.get("observation_anchor_ms"),
        "evidence_start_class": admission_snapshot.get("evidence_start_class"),
        "admission_max_evidence_class": admission_snapshot.get("admission_max_evidence_class"),
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def compute_latest_anchor_contract_hash(
    *,
    previous_latest_anchor_contract_hash: str,
    revision_application_id: str,
    latest_contract: dict[str, Any],
) -> str:
    """
    Compute deterministic SHA256 hash for latest anchor contract.
    CRITICAL: CHAINED HASH including previous_latest_anchor_contract_hash!
    """
    payload = {
        "hash_schema_version": ANCHOR_CONTRACT_HASH_SCHEMA_VERSION,
        "previous_latest_anchor_contract_hash": previous_latest_anchor_contract_hash,
        "revision_application_id": revision_application_id,
        "latest_contract": latest_contract,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
