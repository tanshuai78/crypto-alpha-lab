import glob
import hashlib
import json
import os

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
    event_is_post_watermark,
    get_stable_event_key,
)


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
    sym = symbol.strip().upper()
    if source_article_id:
        return f"{event_type}|{source_article_id}|{sym}"
    return f"{event_type}|{get_stable_event_key(row)}|{sym}"


def upsert_pending_state_with_event_revision(pending_state, event_row: dict, symbol: str):
    if not getattr(pending_state, "status", "").startswith("pending_"):
        return pending_state

    event_id = event_row.get("event_id") or pending_state.event_id
    latest_payload_hash = (
        event_row.get("detail_payload_hash")
        or event_row.get("payload_hash")
        or getattr(pending_state, "latest_event_payload_hash", "")
    )

    d = pending_state.to_dict()
    d["event_id"] = event_id
    d["latest_event_payload_hash"] = latest_payload_hash
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

    anchor_diag = resolve_depth_observation_anchor_ms(target_row, pending_state.symbol, exchangeinfo_state, now_ms)
    anchor_ms = anchor_diag.get("observation_anchor_ms")
    conflict_active = anchor_diag.get("observation_anchor_conflict_active", False)

    d = pending_state.to_dict()
    if target_row:
        if target_row.get("event_id"):
            d["event_id"] = target_row["event_id"]
        if target_row.get("detail_payload_hash") or target_row.get("payload_hash"):
            d["latest_event_payload_hash"] = target_row.get("detail_payload_hash") or target_row.get("payload_hash")

    d["anchor_resolution_attempt_count"] = pending_state.anchor_resolution_attempt_count + 1
    d["last_anchor_resolution_at_ms"] = now_ms

    d["observation_anchor_candidates"] = anchor_diag.get("observation_anchor_candidates", {})
    d["observation_anchor_disagreement_max_ms"] = anchor_diag.get("observation_anchor_disagreement_max_ms", 0)
    d["observation_anchor_conflict_active"] = conflict_active

    retry_interval_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC * 1000
    d["next_anchor_resolution_at_ms"] = now_ms + retry_interval_ms

    if conflict_active:
        d["status"] = "pending_anchor_conflict"
        d["observation_anchor_ms"] = None
    elif anchor_ms is None:
        d["status"] = "pending_launch_anchor_missing"
        d["observation_anchor_ms"] = None
    else:
        d["observation_anchor_ms"] = anchor_ms
        d["observation_anchor_basis"] = anchor_diag.get("observation_anchor_basis", "")
        d["observation_anchor_confidence"] = anchor_diag.get("observation_anchor_confidence", "")
        if now_ms < anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS:
            d["status"] = "pending_launch_time_in_future"
            d["next_admission_check_at_ms"] = anchor_ms
        else:
            d["status"] = "pending_ready_for_admission"
            d["next_admission_check_at_ms"] = now_ms

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

    launch_time_ms = _get_symbol_time(row, "symbol_effective_launch_times_ms", symbol)
    if launch_time_ms is None:
        launch_time_ms = _get_symbol_time(row, "symbol_onboard_times_ms", symbol)
    return launch_time_ms is not None and launch_time_ms > watermark.max_seen_detected_at_ms


def resolve_observation_age_base_ms(row: dict, symbol: str) -> tuple[int | None, str]:
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


def classify_event_symbol_eligibility_with_diagnostics(
    row: dict,
    symbol: str,
    now_ms: int,
    watermark,
    exchangeinfo_state: dict,
    budget_state: dict,
) -> tuple[str, str, dict]:
    event_type = row.get("event_type")
    if event_type != "futures_contract_launch":
        return "rejected", "wrong_event_type", {}

    if not symbol:
        return "rejected", "symbol_missing", {}

    if not event_is_post_watermark(row, watermark) and not delayed_launch_event_symbol_is_post_watermark(
        row, symbol, watermark
    ):
        return "rejected", "pre_watermark", {}

    if not exchangeinfo_state or not exchangeinfo_state.get("available", False):
        return "pending", "exchangeinfo_unavailable", {}

    symbols_in_exchange = exchangeinfo_state.get("symbols", set())
    if symbol not in symbols_in_exchange:
        return "rejected", "symbol_not_in_exchangeinfo", {}

    if budget_state and budget_state.get("budget_exceeded", False):
        return "rejected", "budget_exceeded", {}

    anchor_diag = resolve_depth_observation_anchor_ms(row, symbol, exchangeinfo_state, now_ms)
    anchor_ms = anchor_diag.get("observation_anchor_ms")
    conflict_active = anchor_diag.get("observation_anchor_conflict_active", False)

    diag = dict(anchor_diag)
    diag["announcement_capture_time_ms"], diag["announcement_capture_time_source"] = resolve_announcement_capture_time_ms(row)
    diag["observation_age_base_ms"] = anchor_ms
    diag["event_age_ms"] = (now_ms - anchor_ms) if anchor_ms is not None else None
    diag["max_event_age_ms"] = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS
    diag["watermark_max_seen_detected_at_ms"] = getattr(watermark, "max_seen_detected_at_ms", 0)
    diag["watermark_version"] = getattr(watermark, "watermark_version", 1)
    diag.update(build_first_seen_watermark_diagnostics(row, symbol, diag, watermark))



    if conflict_active:
        return "pending", "pending_anchor_conflict", diag


    if anchor_ms is None:
        diag["live_depth_evidence_basis"] = "recovery_validation_only"
        return "pending", "pending_launch_anchor_missing", diag

    if now_ms < anchor_ms + base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS:
        diag["next_admission_check_at_ms"] = anchor_ms
        return "pending", "pending_launch_time_in_future", diag

    delay_ms = now_ms - anchor_ms
    clean_delay_max = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS
    recovery_delay_max = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS

    if delay_ms <= clean_delay_max:
        diag["evidence_start_class"] = "clean_start"
        diag["live_depth_evidence_basis"] = "announcement_and_launch_time"
        return "eligible", "eligible_clean_start", diag
    elif delay_ms <= recovery_delay_max:
        diag["evidence_start_class"] = "recovery_start"
        diag["live_depth_evidence_basis"] = "recovery_validation_only"
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
