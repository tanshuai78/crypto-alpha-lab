import glob
import hashlib
import json
import os

from configs import base
from src.research.external_signal_shadow.stage1_5f_live_depth_observer_watermark import (
    event_is_post_watermark,
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


def classify_event_symbol_eligibility(row: dict, symbol: str, now_ms: int, watermark, exchangeinfo_state: dict, budget_state: dict):
    event_type = row.get("event_type")
    if event_type != "futures_contract_launch":
        return "rejected", "wrong_event_type"

    if not event_is_post_watermark(row, watermark):
        return "rejected", "pre_watermark"

    detected_at_ms = row.get("detected_at_ms")
    if detected_at_ms is None:
        return "rejected", "detected_at_ms_missing"

    age_ms = now_ms - detected_at_ms
    max_age_ms = base.EXTERNAL_SIGNAL_STAGE1_5F_MAX_EVENT_AGE_TO_START_OBSERVATION_MS
    if age_ms > max_age_ms:
        return "rejected", "age_exceeded"

    if not symbol:
        return "rejected", "symbol_missing"

    if not exchangeinfo_state or not exchangeinfo_state.get("available", False):
        return "pending", "exchangeinfo_unavailable"

    symbols_in_exchange = exchangeinfo_state.get("symbols", set())
    if symbol not in symbols_in_exchange:
        return "rejected", "symbol_not_in_exchangeinfo"

    if budget_state and budget_state.get("budget_exceeded", False):
        return "rejected", "budget_exceeded"

    return "eligible", "ok"


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
