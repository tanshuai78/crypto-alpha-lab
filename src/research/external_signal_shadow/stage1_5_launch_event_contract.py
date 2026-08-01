import hashlib
import json
from configs import base

FORMAL_CONTRACT_VERSION = 1
PARSER_VERSION = "stage1_5d_symbol_extraction_v3"
SYMBOL_EXTRACTION_VERSION = 3

ALLOWED_EFFECTIVE_LAUNCH_TIME_SOURCES = {
    "detail_symbol_launch_time",
    "bapi_detail_body",
    "bapi_article_body",
    "exchangeinfo_onboard_date",
    "exchangeinfo_onboard_time",
    "exchange_info",
}


def classify_anchor_evidence(row: dict, symbol: str) -> dict:
    sym = symbol.strip().upper() if symbol else ""
    eff_map = row.get("symbol_effective_launch_times_ms") or {}
    onboard_map = row.get("symbol_onboard_times_ms") or {}
    cand_map = row.get("symbol_launch_time_candidates_ms") or {}
    src_map = row.get("symbol_effective_launch_time_sources") or {}

    eff_ms = eff_map.get(sym)
    onboard_ms = onboard_map.get(sym)
    cand_ms = cand_map.get(sym)
    src_name = src_map.get(sym, "")

    detail_attempted = bool(row.get("detail_fetch_attempted", False))
    detail_status = str(row.get("detail_fetch_status") or "")
    detail_missing = bool(row.get("detail_confirmation_missing", True))

    disagreement_ms = row.get("launch_anchor_disagreement_ms")
    comparison_status = str(row.get("launch_anchor_comparison_status") or "")

    # Determine evidence level
    evidence_level = "missing"
    if eff_ms is not None:
        if detail_attempted and not detail_missing and detail_status == "success":
            if onboard_ms is not None:
                diff = abs(eff_ms - onboard_ms)
                tolerance = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS", 60000)
                if diff <= tolerance:
                    evidence_level = "detail_exchangeinfo_consensus"
                else:
                    evidence_level = "conflict"
            else:
                evidence_level = "detail_confirmed"
        elif detail_attempted and detail_missing and onboard_ms is not None:
            evidence_level = "exchangeinfo_fallback"
        elif onboard_ms is not None:
            evidence_level = "exchangeinfo_fallback"
        elif detail_attempted and not detail_missing:
            evidence_level = "detail_confirmed"

    return {
        "symbol": sym,
        "effective_launch_time_ms": eff_ms,
        "onboard_time_ms": onboard_ms,
        "launch_time_candidate_ms": cand_ms,
        "launch_time_source": src_name,
        "launch_anchor_disagreement_ms": disagreement_ms,
        "launch_anchor_comparison_status": comparison_status,
        "launch_anchor_evidence_level": evidence_level,
    }


def validate_formal_launch_event(row: dict, symbol: str | None = None) -> dict:
    blockers = []
    if not isinstance(row, dict):
        return {"valid": False, "status": "INVALID", "blockers": ["row_not_dict"], "diagnostics": {}}

    if row.get("formal_event_contract_version") != FORMAL_CONTRACT_VERSION:
        blockers.append("formal_event_contract_version_missing_or_unsupported")

    if row.get("formal_event_consumable_by_stage1_5f") is not True:
        blockers.append("formal_event_not_consumable_by_stage1_5f")

    if row.get("source_contract_status") != "formal_v1_valid":
        blockers.append("source_contract_status_not_formal_v1_valid")

    if row.get("symbol_identity_validation_status") != "validated_by_exchangeinfo":
        blockers.append("symbol_identity_not_validated_by_exchangeinfo")

    for field in ("event_id", "source_article_id", "stable_event_key", "parser_version", "symbol_extraction_version"):
        if row.get(field) in (None, "", []):
            blockers.append(f"{field}_missing")

    syms = row.get("symbols") or []
    if symbol:
        sym_list = [symbol.strip().upper()]
    else:
        sym_list = [str(s).strip().upper() for s in syms] if isinstance(syms, (list, tuple)) else []

    if not sym_list and row.get("symbol"):
        sym_list = [str(row["symbol"]).strip().upper()]

    if not sym_list:
        blockers.append("symbols_missing")

    evidence_level = str(row.get("launch_anchor_evidence_level") or "")
    detail_attempted = bool(row.get("detail_fetch_attempted", False))
    detail_status = str(row.get("detail_fetch_status") or "")
    detail_missing = bool(row.get("detail_confirmation_missing", True))

    allowed_evidence_levels = {
        "detail_confirmed",
        "detail_exchangeinfo_consensus",
        "exchangeinfo_fallback",
    }
    if evidence_level not in allowed_evidence_levels:
        blockers.append(f"invalid_launch_anchor_evidence_level_{evidence_level or 'missing'}")

    disagreement_ms = row.get("launch_anchor_disagreement_ms")
    comparison_status = str(row.get("launch_anchor_comparison_status") or "")
    tolerance = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS", 60000)

    if disagreement_ms is not None and isinstance(disagreement_ms, (int, float)):
        if disagreement_ms > tolerance and comparison_status == "consensus":
            blockers.append("launch_anchor_disagreement_conflict")

    if comparison_status not in ("single_source_detail", "single_source_exchangeinfo", "consensus"):
        blockers.append("launch_anchor_comparison_status_invalid")

    eff_map = row.get("symbol_effective_launch_times_ms") or {}
    onboard_map = row.get("symbol_onboard_times_ms") or {}
    cand_map = row.get("symbol_launch_time_candidates_ms") or {}
    source_map = row.get("symbol_effective_launch_time_sources") or {}

    if not isinstance(eff_map, dict):
        blockers.append("symbol_effective_launch_times_ms_not_dict")
        eff_map = {}
    if not isinstance(onboard_map, dict):
        blockers.append("symbol_onboard_times_ms_not_dict")
        onboard_map = {}
    if not isinstance(cand_map, dict):
        blockers.append("symbol_launch_time_candidates_ms_not_dict")
        cand_map = {}
    if not isinstance(source_map, dict):
        blockers.append("symbol_effective_launch_time_sources_not_dict")
        source_map = {}

    for sym in sym_list:
        eff_ms = eff_map.get(sym)
        if not isinstance(eff_ms, int) or eff_ms <= 0:
            blockers.append(f"symbol_effective_launch_time_missing_{sym}")

        cand_value = cand_map.get(sym)
        cand_valid = isinstance(cand_value, int) and cand_value > 0
        if isinstance(cand_value, dict):
            cand_valid = any(isinstance(v, int) and v > 0 for v in cand_value.values())
        if not cand_valid:
            blockers.append(f"symbol_launch_time_candidate_missing_{sym}")

        if not source_map.get(sym):
            blockers.append(f"symbol_effective_launch_time_source_missing_{sym}")
        elif str(source_map.get(sym)) not in ALLOWED_EFFECTIVE_LAUNCH_TIME_SOURCES:
            blockers.append(f"symbol_effective_launch_time_source_invalid_{sym}")

        onboard_ms = onboard_map.get(sym)
        if evidence_level in ("exchangeinfo_fallback", "detail_exchangeinfo_consensus"):
            if not isinstance(onboard_ms, int) or onboard_ms <= 0:
                blockers.append(f"symbol_onboard_time_missing_{sym}")

    if evidence_level == "detail_confirmed":
        if not detail_attempted:
            blockers.append("detail_confirmed_requires_detail_fetch_attempted")
        if detail_status != "success":
            blockers.append("detail_confirmed_requires_success_status")
        if detail_missing:
            blockers.append("detail_confirmed_requires_detail_confirmation")
        if comparison_status not in ("single_source_detail", "consensus"):
            blockers.append("detail_confirmed_comparison_status_invalid")

    if evidence_level == "detail_exchangeinfo_consensus":
        if not detail_attempted:
            blockers.append("consensus_requires_detail_fetch_attempted")
        if detail_status != "success":
            blockers.append("consensus_requires_success_status")
        if detail_missing:
            blockers.append("consensus_requires_detail_confirmation")
        if comparison_status != "consensus":
            blockers.append("consensus_requires_consensus_comparison_status")

    if evidence_level == "exchangeinfo_fallback":
        if not detail_attempted:
            blockers.append("exchangeinfo_fallback_requires_detail_fetch_attempted")
        if not detail_missing:
            blockers.append("exchangeinfo_fallback_requires_missing_detail_confirmation")
        if not row.get("detail_fetch_variant"):
            blockers.append("exchangeinfo_fallback_requires_detail_fetch_variant")
        if comparison_status != "single_source_exchangeinfo":
            blockers.append("exchangeinfo_fallback_requires_single_source_exchangeinfo")

    valid = len(blockers) == 0
    return {
        "valid": valid,
        "status": "VALID" if valid else "INVALID",
        "blockers": blockers,
        "diagnostics": {
            "evidence_level": evidence_level,
            "symbols_checked": sym_list,
        },
    }


def build_formal_launch_event(*, raw_event: dict, symbol_rows: list[dict], diagnostics: dict) -> dict:
    code = raw_event.get("source_article_id") or raw_event.get("code") or ""
    title = raw_event.get("title") or ""
    detected_at_ms = raw_event.get("detected_at_ms") or 0
    source_published_at_ms = raw_event.get("source_published_at_ms") or detected_at_ms

    symbols = [s["symbol"] for s in symbol_rows if "symbol" in s]
    symbols = list(dict.fromkeys(symbols))

    eff_times = {}
    onboard_times = {}
    cand_times = {}
    sources = {}

    detail_attempted = True
    detail_status = "success"
    detail_missing = False

    for s in symbol_rows:
        sym = s["symbol"]
        if "effective_launch_time_ms" in s and s["effective_launch_time_ms"] is not None:
            eff_times[sym] = s["effective_launch_time_ms"]
        if "onboard_time_ms" in s and s["onboard_time_ms"] is not None:
            onboard_times[sym] = s["onboard_time_ms"]
        if "launch_time_candidate_ms" in s and s["launch_time_candidate_ms"] is not None:
            cand_times[sym] = s["launch_time_candidate_ms"]
        elif sym in eff_times:
            cand_times[sym] = eff_times[sym]

        if "launch_time_source" in s:
            sources[sym] = s["launch_time_source"]
        if "detail_fetch_attempted" in s:
            detail_attempted = s["detail_fetch_attempted"]
        if "detail_fetch_status" in s:
            detail_status = s["detail_fetch_status"]
        if "detail_confirmation_missing" in s:
            detail_missing = bool(s["detail_confirmation_missing"])

    if len(symbols) == 1:
        stable_key = f"binance_{code}_{symbols[0]}"
        event_id = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
    else:
        stable_key = f"binance_{code}_MULTI"
        event_id = hashlib.sha256(f"{stable_key}|{','.join(sorted(symbols))}".encode("utf-8")).hexdigest()

    disagreement_ms = diagnostics.get("launch_anchor_disagreement_ms")
    comparison_status = diagnostics.get("launch_anchor_comparison_status", "single_source_detail")
    evidence_level = diagnostics.get("launch_anchor_evidence_level", "detail_confirmed")

    event_row = {
        "formal_event_contract_version": FORMAL_CONTRACT_VERSION,
        "formal_event_consumable_by_stage1_5f": True,
        "source_contract_status": "formal_v1_valid",
        "symbol_identity_validation_status": "validated_by_exchangeinfo",
        "event_id": event_id,
        "event_type": "futures_contract_launch",
        "source_name": "binance_official_announcements",
        "source_profile": "binance_official_announcements_like_rows",
        "title": title,
        "symbols": symbols,
        "base_assets": [s.replace("USDT", "").replace("USDC", "") for s in symbols],
        "detected_at_ms": detected_at_ms,
        "available_at_ms": detected_at_ms,
        "source_article_id": code,
        "source_detail_url_normalized": f"https://www.binance.com/en/support/announcement/{code}",
        "source_published_at_ms": source_published_at_ms,
        "source_published_at_ms_confidence": "medium",
        "historical_delay_comparison_allowed": True,
        "stable_event_key": stable_key,
        "symbol_effective_launch_times_ms": eff_times,
        "symbol_onboard_times_ms": onboard_times,
        "symbol_launch_time_candidates_ms": cand_times,
        "symbol_effective_launch_time_sources": sources,
        "launch_anchor_validation_status": "valid",
        "launch_anchor_disagreement_ms": disagreement_ms,
        "launch_anchor_comparison_status": comparison_status,
        "launch_anchor_evidence_level": evidence_level,
        "detail_fetch_attempted": detail_attempted,
        "detail_fetch_status": detail_status,
        "detail_fetch_variant": diagnostics.get("detail_fetch_variant", "bapi_detail_query"),
        "detail_confirmation_missing": detail_missing,
        "parser_version": PARSER_VERSION,
        "symbol_extraction_version": SYMBOL_EXTRACTION_VERSION,
        "stage1_5c_research_context_label": "futures_launch_long_attention_12h_close_price_replay_only",
        "trade_signal_allowed": False,
        "replay_context_label_only": True,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }

    val = validate_formal_launch_event(event_row)
    if not val["valid"]:
        raise ValueError(f"build_formal_launch_event generated invalid event: {val['blockers']}")

    return event_row


def coerce_legacy_launch_event_to_formal(row: dict) -> dict:
    """Upgrade an already validated legacy Stage 1.5D row to formal v1, or return it unchanged."""
    if not isinstance(row, dict):
        return row
    if row.get("formal_event_contract_version") == FORMAL_CONTRACT_VERSION:
        return row
    if row.get("event_type") != "futures_contract_launch":
        return row

    symbols = [str(s).strip().upper() for s in (row.get("symbols") or []) if str(s or "").strip()]
    if not symbols:
        return row

    effective = row.get("symbol_effective_launch_times_ms") or row.get("symbol_launch_times_ms") or {}
    if not isinstance(effective, dict):
        return row
    if any(not isinstance(effective.get(sym), int) or effective.get(sym) <= 0 for sym in symbols):
        return row

    sources = row.get("symbol_effective_launch_time_sources") or {}
    if not isinstance(sources, dict):
        source = row.get("launch_time_source") or ""
        if source == "detail":
            sources = {sym: "detail_symbol_launch_time" for sym in symbols}
        elif source == "exchange_info":
            sources = {sym: "exchangeinfo_onboard_date" for sym in symbols}
        else:
            sources = {sym: source for sym in symbols}
    elif not sources:
        source = row.get("launch_time_source") or ""
        if source == "detail":
            sources = {sym: "detail_symbol_launch_time" for sym in symbols}
        elif source == "exchange_info":
            sources = {sym: "exchangeinfo_onboard_date" for sym in symbols}
        else:
            sources = {sym: source for sym in symbols}

    if any(str(sources.get(sym) or "") not in ALLOWED_EFFECTIVE_LAUNCH_TIME_SOURCES for sym in symbols):
        return row

    detail_status = str(row.get("detail_fetch_status") or "")
    detail_attempted = bool(row.get("detail_fetch_attempted", detail_status not in ("", "not_needed")))
    detail_missing = bool(row.get("detail_confirmation_missing", detail_status != "success"))
    if detail_status == "not_needed" and not detail_attempted:
        return row

    coerced = dict(row)
    coerced["formal_event_contract_version"] = FORMAL_CONTRACT_VERSION
    coerced["formal_event_consumable_by_stage1_5f"] = True
    coerced["source_contract_status"] = "formal_v1_valid"
    coerced["symbol_identity_validation_status"] = "validated_by_exchangeinfo"
    coerced["symbol_effective_launch_times_ms"] = effective
    coerced.setdefault("symbol_launch_time_candidates_ms", {sym: effective[sym] for sym in symbols})
    coerced["symbol_effective_launch_time_sources"] = sources
    coerced.setdefault("symbol_onboard_times_ms", {})
    coerced.setdefault("parser_version", PARSER_VERSION)
    coerced.setdefault("symbol_extraction_version", SYMBOL_EXTRACTION_VERSION)
    coerced.setdefault("source_contract_status", "formal_v1_valid")
    coerced.setdefault("source_article_id", row.get("source_article_id") or "")
    coerced.setdefault("stable_event_key", row.get("stable_event_key") or "")
    coerced.setdefault("event_id", row.get("event_id") or "")
    coerced["detail_fetch_attempted"] = detail_attempted
    coerced["detail_fetch_status"] = detail_status or ("success" if not detail_missing else "transient_unavailable")
    coerced.setdefault("detail_fetch_variant", row.get("detail_fetch_variant") or "legacy_validated_detail")
    coerced["detail_confirmation_missing"] = detail_missing

    onboard = coerced.get("symbol_onboard_times_ms") or {}
    has_onboard = all(isinstance(onboard.get(sym), int) and onboard.get(sym) > 0 for sym in symbols)
    if detail_status == "success" and not detail_missing:
        if has_onboard:
            max_diff = max(abs(effective[sym] - onboard[sym]) for sym in symbols)
            tolerance = getattr(base, "EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS", 60000)
            if max_diff <= tolerance:
                coerced["launch_anchor_evidence_level"] = "detail_exchangeinfo_consensus"
                coerced["launch_anchor_comparison_status"] = "consensus"
                coerced["launch_anchor_disagreement_ms"] = max_diff
            else:
                return row
        else:
            coerced["launch_anchor_evidence_level"] = "detail_confirmed"
            coerced["launch_anchor_comparison_status"] = "single_source_detail"
            coerced["launch_anchor_disagreement_ms"] = None
    elif has_onboard and detail_attempted and detail_missing:
        coerced["launch_anchor_evidence_level"] = "exchangeinfo_fallback"
        coerced["launch_anchor_comparison_status"] = "single_source_exchangeinfo"
        coerced["launch_anchor_disagreement_ms"] = None
    else:
        return row

    coerced["launch_anchor_validation_status"] = "valid"
    return coerced
