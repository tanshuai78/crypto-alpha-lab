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

    if not event_is_post_watermark(row, watermark) and not delayed_launch_event_symbol_is_post_watermark(
        row, symbol, watermark
    ):
        return "rejected", "pre_watermark", {}

    observation_age_base_ms, observation_age_basis = resolve_observation_age_base_ms(row, symbol)
    diag = _build_eligibility_diagnostics(
        row=row,
        now_ms=now_ms,
        watermark=watermark,
        observation_age_base_ms=observation_age_base_ms,
        observation_age_basis=observation_age_basis,
    )
    if observation_age_base_ms is None:
        return "rejected", "detected_at_ms_missing", diag

    clock_skew_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_TIME_CLOCK_SKEW_TOLERANCE_MS
    if observation_age_base_ms > now_ms + clock_skew_ms:
        return "pending", "launch_time_in_future", diag

    if diag["event_age_ms"] > diag["max_event_age_ms"]:
        return "rejected", "age_exceeded", diag

    if not symbol:
        return "rejected", "symbol_missing", diag

    if not exchangeinfo_state or not exchangeinfo_state.get("available", False):
        return "pending", "exchangeinfo_unavailable", diag

    symbols_in_exchange = exchangeinfo_state.get("symbols", set())
    if symbol not in symbols_in_exchange:
        return "rejected", "symbol_not_in_exchangeinfo", diag

    if budget_state and budget_state.get("budget_exceeded", False):
        return "rejected", "budget_exceeded", diag

    return "eligible", "ok", diag


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
