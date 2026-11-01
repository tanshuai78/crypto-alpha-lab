"""Exploratory research module: first-minute taker buy share and 15m residual price response.

Strictly offline, read-only, exploratory / hypothesis_only.
Zero trade signal, paper, live, execution, or network authority.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence

from configs.base import RISK_LIVE_TRADING_ENABLED
from configs.stage1_5j_b_historical_aggtrades_launch_response import (
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
    EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
)
from research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    validate_zip_archive_package,
)

APPROVED_DESIGN_RELATIVE_PATH = (
    "docs/designs/2026-10-31-launch-taker-buy-share-residual-response-exploratory-design_CN.md"
)
APPROVED_DESIGN_SHA256 = "5c05cb304da482bf5c29c0f98938795e11949b4130149474b6f8842175684896"
APPROVED_PLAN_RELATIVE_PATH = (
    "docs/plans/2026-10-31-launch-taker-buy-share-residual-response-exploratory-implementation-plan_CN.md"
)
APPROVED_PLAN_SHA256 = "e644e9dfa25a063884ccf98cf23539e8fece485c6dca7fd2a03278f243bc240d"

J_A_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/"
    "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
)
J_A_RUN_ID = "stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
J_B_ROOT_RELATIVE_PATH = (
    "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/"
    "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
)
J_B_RUN_ID = "stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"
LEDGER_RELATIVE_PATH = "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
LEDGER_SHA256 = "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b"

J_B_CLOSURE_JSON_RELATIVE_PATH = (
    ".git/plan-execution/governance_stage1_5j_b_receipt_profile_v2/"
    "64e14726202b53727a7627139578369cb6af54f08d5a785d4df006009eb25a2d/"
    "evidence/receipt_closure_evidence.json"
)
J_B_CLOSURE_JSON_SHA256 = "8d535303d61b3860eaa69018eff3f76645f91b3e27af1af89e1e956b948f8b6d"
J_B_CLOSURE_SIDECAR_RELATIVE_PATH = f"{J_B_CLOSURE_JSON_RELATIVE_PATH}.sha256"
J_B_CLOSURE_SIDECAR_SHA256 = "c3856c2e9e6d5086a543891902d57246fa64a93acdbba97a1130e541f949c5d9"

FROZEN_UPSTREAM_FILE_HASHES: dict[str, str] = {
    f"{J_A_ROOT_RELATIVE_PATH}/manifest.json": "b6654906108d1a5d3aa5dc9b9e9e6c38a315d55ad6dfe609c9d5f4de4907b0cf",
    f"{J_A_ROOT_RELATIVE_PATH}/summary.json": "722c3be6671ac9ca39d79695fecf351e8d0ccf55e693d7c42ccf86229dff651b",
    f"{J_B_ROOT_RELATIVE_PATH}/manifest.json": "f0a8ac724925084161f6b9aa2dced5139b261707fda0f0f21ebd0eb6de3087fb",
    f"{J_B_ROOT_RELATIVE_PATH}/summary.json": "5ea0f1c87803114c4c6917cd0c3d24292948fa0e7066a80e0a2bce611e32546b",
    f"{J_B_ROOT_RELATIVE_PATH}/review_CN.md": "17e9ffaa973923868621a8ee925dc811c15e12459924ee63897f9c21fcac317e",
    LEDGER_RELATIVE_PATH: LEDGER_SHA256,
    J_B_CLOSURE_JSON_RELATIVE_PATH: J_B_CLOSURE_JSON_SHA256,
    J_B_CLOSURE_SIDECAR_RELATIVE_PATH: J_B_CLOSURE_SIDECAR_SHA256,
}

REQUIRED_CSV_HEADER = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
]
REQUIRED_LEDGER_COLUMNS = [
    "parent_article_id",
    "symbol",
    "asset_class",
    "listing_regime",
    "classification_status",
    "table_index",
    "symbol_column_index",
    "field_header",
    "raw_cell_value",
    "evidence_locator",
    "source_relative_path",
    "source_sha256",
]
REQUIRED_AUTH_KEYS = frozenset(
    {
        "design_relative_path",
        "design_sha256",
        "plan_relative_path",
        "plan_sha256",
        "ja_root_relative_path",
        "jb_root_relative_path",
        "ledger_relative_path",
        "ledger_sha256",
        "output_dir",
        "operation",
        "network_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
        "signal_allowed",
    }
)
ALLOWED_ASSET_CLASSES = frozenset({"crypto", "equity", "etf", "commodity", "index", "unknown"})
ALLOWED_LEDGER_REGIMES = frozenset({"standard", "pre_market", "pre_ipo", "unknown"})
ALLOWED_CLASSIFICATION_STATUS = frozenset({"confirmed", "unknown"})
SHA256_REGEX = re.compile(r"^[0-9a-f]{64}$")
HEX32_REGEX = re.compile(r"^[0-9a-f]{32}$")
NONNEG_INT_STR_REGEX = re.compile(r"^(?:0|[1-9][0-9]*)$")

APPROVED_DESIGN_PROTOCOL_SHA256 = (
    "17cb308b4d69e56a3085c9c72a8f2ab777382640f00844958f3fb6703446331e"
)
LEGAL_LISTING_REGIMES = frozenset({"pre_market", "standard"})
LEGAL_CHILD_STATUSES = frozenset(
    {
        "upstream_gap",
        "anchor_unavailable",
        "feature_unavailable",
        "entry_unavailable",
        "required_package_unavailable",
        "endpoint_unavailable",
        "sequence_gap",
        "complete",
    }
)
_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=timezone.utc)


class TakerBuyShareResearchError(Exception):
    """Fail-closed error for protocol, integrity, ordering, or authority violations."""


@dataclass(frozen=True)
class ExploratoryProtocol:
    feature_window_ms: int
    latency_ms: int
    entry_max_wait_ms: int
    hold_horizon_ms: int
    endpoint_max_age_ms: int


@dataclass(frozen=True)
class AggTradeRecord:
    aggregate_id: int
    price: Decimal | Fraction | str | int
    quantity: Decimal | Fraction | str | int
    timestamp_ms: int
    is_buyer_maker: bool


@dataclass(frozen=True)
class ChildResidualResponseResult:
    parent_article_id: str
    symbol: str
    listing_regime: str
    status: str
    status_reason: str | None
    anchor_time_ms: int | None
    anchor_price: Fraction | None
    feature_trade_count: int
    feature_max_intertrade_gap_ms: int | None
    total_notional: Fraction | None
    taker_buy_share: Fraction | None
    vwap: Fraction | None
    vwap_deviation: Fraction | None
    entry_time_ms: int | None
    entry_trade_id: int | None
    entry_price: Fraction | None
    target_end_time_ms: int | None
    endpoint_time_ms: int | None
    endpoint_trade_id: int | None
    endpoint_price: Fraction | None
    path_trade_count: int
    max_intertrade_gap_ms: int | None
    terminal_return: Fraction | None
    long_mae: Fraction | None
    long_mfe: Fraction | None


def _is_strict_int(val: object) -> bool:
    return isinstance(val, int) and not isinstance(val, bool)


def _to_positive_fraction(val: Decimal | Fraction | str | int, field_name: str) -> Fraction:
    if isinstance(val, bool) or val is None:
        raise TakerBuyShareResearchError(f"STOP=invalid_{field_name}_type")
    if isinstance(val, Fraction):
        frac = val
    elif isinstance(val, int):
        frac = Fraction(val, 1)
    elif isinstance(val, (Decimal, str)):
        try:
            dec = Decimal(val) if isinstance(val, str) else val
        except InvalidOperation as exc:
            raise TakerBuyShareResearchError(f"STOP=invalid_{field_name}_decimal:{val}") from exc
        if not dec.is_finite():
            raise TakerBuyShareResearchError(f"STOP=non_finite_{field_name}:{val}")
        frac = Fraction(dec)
    else:
        raise TakerBuyShareResearchError(f"STOP=unsupported_{field_name}_type:{type(val).__name__}")
    if frac <= 0:
        raise TakerBuyShareResearchError(f"STOP=non_positive_{field_name}:{val}")
    return frac


def validate_exploratory_protocol(protocol: ExploratoryProtocol) -> None:
    if not isinstance(protocol, ExploratoryProtocol):
        raise TakerBuyShareResearchError("STOP=invalid_protocol_type")
    fields = {
        "endpoint_max_age_ms": protocol.endpoint_max_age_ms,
        "entry_max_wait_ms": protocol.entry_max_wait_ms,
        "feature_window_ms": protocol.feature_window_ms,
        "hold_horizon_ms": protocol.hold_horizon_ms,
        "latency_ms": protocol.latency_ms,
    }
    for name, value in fields.items():
        if not _is_strict_int(value) or value <= 0:
            raise TakerBuyShareResearchError(f"STOP=invalid_protocol_field:{name}")
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    if digest != APPROVED_DESIGN_PROTOCOL_SHA256:
        raise TakerBuyShareResearchError(f"STOP=protocol_mismatch_with_approved_design:{digest}")


def utc_date_str_from_ms(timestamp_ms: int) -> str:
    if not _is_strict_int(timestamp_ms) or timestamp_ms < 0:
        raise TakerBuyShareResearchError(f"STOP=invalid_timestamp_ms:{timestamp_ms}")
    dt = _EPOCH_UTC + timedelta(milliseconds=timestamp_ms)
    return dt.strftime("%Y-%m-%d")


def required_utc_dates_for_window(start_ms: int, end_ms: int) -> list[str]:
    if not _is_strict_int(start_ms) or not _is_strict_int(end_ms) or start_ms < 0 or end_ms < start_ms:
        raise TakerBuyShareResearchError(f"STOP=invalid_window_bounds:{start_ms}..{end_ms}")
    cur_date = (_EPOCH_UTC + timedelta(milliseconds=start_ms)).date()
    end_date = (_EPOCH_UTC + timedelta(milliseconds=end_ms)).date()
    dates: list[str] = []
    while cur_date <= end_date:
        dates.append(cur_date.strftime("%Y-%m-%d"))
        cur_date += timedelta(days=1)
    return dates


def _empty_result(
    *,
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    status: str,
    status_reason: str | None,
    anchor_time_ms: int | None = None,
    anchor_price: Fraction | None = None,
    feature_trade_count: int = 0,
    feature_max_intertrade_gap_ms: int | None = None,
    total_notional: Fraction | None = None,
    taker_buy_share: Fraction | None = None,
    vwap: Fraction | None = None,
    vwap_deviation: Fraction | None = None,
    entry_time_ms: int | None = None,
    entry_trade_id: int | None = None,
    entry_price: Fraction | None = None,
    target_end_time_ms: int | None = None,
) -> ChildResidualResponseResult:
    return ChildResidualResponseResult(
        parent_article_id=parent_article_id,
        symbol=symbol,
        listing_regime=listing_regime,
        status=status,
        status_reason=status_reason,
        anchor_time_ms=anchor_time_ms,
        anchor_price=anchor_price,
        feature_trade_count=feature_trade_count,
        feature_max_intertrade_gap_ms=feature_max_intertrade_gap_ms,
        total_notional=total_notional,
        taker_buy_share=taker_buy_share,
        vwap=vwap,
        vwap_deviation=vwap_deviation,
        entry_time_ms=entry_time_ms,
        entry_trade_id=entry_trade_id,
        entry_price=entry_price,
        target_end_time_ms=target_end_time_ms,
        endpoint_time_ms=None,
        endpoint_trade_id=None,
        endpoint_price=None,
        path_trade_count=0,
        max_intertrade_gap_ms=None,
        terminal_return=None,
        long_mae=None,
        long_mfe=None,
    )


def evaluate_child_residual_response(
    *,
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    protocol: ExploratoryProtocol,
    anchor_time_ms: int | None,
    anchor_price: Decimal | Fraction | str | int | None,
    trades: Iterable[AggTradeRecord],
    upstream_gap_reason: str | None = None,
    anchor_unavailable_reason: str | None = None,
    available_utc_dates: set[str] | None = None,
) -> ChildResidualResponseResult:
    """Evaluate single child first-minute taker buy share and 15m post-entry price path in O(1) streaming memory."""
    validate_exploratory_protocol(protocol)
    if not parent_article_id or not isinstance(parent_article_id, str):
        raise TakerBuyShareResearchError("STOP=invalid_parent_article_id")
    if not symbol or not isinstance(symbol, str):
        raise TakerBuyShareResearchError("STOP=invalid_symbol")
    if listing_regime not in LEGAL_LISTING_REGIMES:
        raise TakerBuyShareResearchError(f"STOP=invalid_listing_regime:{listing_regime}")

    if upstream_gap_reason is not None:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="upstream_gap",
            status_reason=upstream_gap_reason,
        )

    if anchor_unavailable_reason is not None or anchor_time_ms is None or anchor_price is None:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="anchor_unavailable",
            status_reason=anchor_unavailable_reason or "anchor_missing",
        )

    if not _is_strict_int(anchor_time_ms) or anchor_time_ms < 0:
        raise TakerBuyShareResearchError(f"STOP=invalid_anchor_time_ms:{anchor_time_ms}")
    validated_anchor_price = _to_positive_fraction(anchor_price, "anchor_price")

    t_obs = anchor_time_ms + protocol.feature_window_ms
    t_decision = t_obs + protocol.latency_ms
    t_entry_deadline = t_decision + protocol.entry_max_wait_ms

    # Single-pass streaming scalar accumulators (zero trade list accumulation)
    prev_ts: int | None = None
    prev_id: int | None = None
    first_post_anchor_ts: int | None = None
    first_post_anchor_price: Fraction | None = None

    feature_trade_count = 0
    feature_prev_ts: int | None = None
    feature_max_gap_ms = 0
    total_notional = Fraction(0, 1)
    buy_notional = Fraction(0, 1)
    total_qty = Fraction(0, 1)
    last_feature_price: Fraction | None = None
    feature_seq_gap = False

    prev_window_id: int | None = None
    gap_before_or_at_entry = False
    active_seq_gap = False

    entry_time_ms: int | None = None
    entry_trade_id: int | None = None
    entry_price: Fraction | None = None
    target_end_time_ms: int | None = None
    t_endpoint_start: int | None = None

    path_trade_count = 0
    path_prev_ts: int | None = None
    path_max_gap_ms = 0
    path_min_price: Fraction | None = None
    path_max_price: Fraction | None = None
    endpoint_time_ms: int | None = None
    endpoint_trade_id: int | None = None
    endpoint_price: Fraction | None = None

    for raw_t in trades:
        if not isinstance(raw_t, AggTradeRecord):
            raise TakerBuyShareResearchError("STOP=invalid_trade_record_type")
        tid = raw_t.aggregate_id
        ts = raw_t.timestamp_ms
        if not _is_strict_int(tid) or tid < 0:
            raise TakerBuyShareResearchError(f"STOP=invalid_aggregate_id:{tid}")
        if not _is_strict_int(ts) or ts < 0:
            raise TakerBuyShareResearchError(f"STOP=invalid_timestamp_ms:{ts}")
        if not isinstance(raw_t.is_buyer_maker, bool):
            raise TakerBuyShareResearchError("STOP=invalid_is_buyer_maker")
        p_frac = _to_positive_fraction(raw_t.price, "price")
        q_frac = _to_positive_fraction(raw_t.quantity, "quantity")

        if prev_ts is not None and prev_id is not None:
            if ts < prev_ts or tid <= prev_id:
                raise TakerBuyShareResearchError(
                    f"STOP=trade_sequence_order_violation:prev=({prev_ts},{prev_id}),curr=({ts},{tid})"
                )
        prev_ts = ts
        prev_id = tid

        if ts < anchor_time_ms:
            continue

        if first_post_anchor_ts is None:
            first_post_anchor_ts = ts
            first_post_anchor_price = p_frac
            if first_post_anchor_ts != anchor_time_ms or first_post_anchor_price != validated_anchor_price:
                raise TakerBuyShareResearchError(
                    f"STOP=anchor_raw_mismatch:expected=({anchor_time_ms},{validated_anchor_price}),"
                    f"observed=({first_post_anchor_ts},{first_post_anchor_price})"
                )

        is_id_gap = prev_window_id is not None and tid != prev_window_id + 1

        if ts < t_obs:
            feature_trade_count += 1
            if feature_prev_ts is not None:
                f_gap = ts - feature_prev_ts
                if f_gap > feature_max_gap_ms:
                    feature_max_gap_ms = f_gap
            feature_prev_ts = ts
            notional = p_frac * q_frac
            total_notional += notional
            total_qty += q_frac
            if raw_t.is_buyer_maker is False:
                buy_notional += notional
            last_feature_price = p_frac
            if is_id_gap:
                feature_seq_gap = True

        if entry_time_ms is None:
            if ts <= t_entry_deadline and is_id_gap:
                gap_before_or_at_entry = True
            if t_decision <= ts <= t_entry_deadline:
                entry_time_ms = ts
                entry_trade_id = tid
                entry_price = p_frac
                target_end_time_ms = ts + protocol.hold_horizon_ms
                t_endpoint_start = target_end_time_ms - protocol.endpoint_max_age_ms
                if gap_before_or_at_entry:
                    active_seq_gap = True

        if (
            entry_time_ms is not None
            and target_end_time_ms is not None
            and t_endpoint_start is not None
            and ts <= target_end_time_ms
        ):
            if is_id_gap:
                active_seq_gap = True
            path_trade_count += 1
            if path_prev_ts is not None:
                p_gap = ts - path_prev_ts
                if p_gap > path_max_gap_ms:
                    path_max_gap_ms = p_gap
            path_prev_ts = ts
            if path_min_price is None or p_frac < path_min_price:
                path_min_price = p_frac
            if path_max_price is None or p_frac > path_max_price:
                path_max_price = p_frac
            if t_endpoint_start <= ts <= target_end_time_ms:
                endpoint_time_ms = ts
                endpoint_trade_id = tid
                endpoint_price = p_frac

        prev_window_id = tid

    # 1. Verify required UTC date packages for the feature window [anchor_time_ms, t_obs - 1]
    if available_utc_dates is not None:
        feat_needed_dates = required_utc_dates_for_window(anchor_time_ms, t_obs - 1)
        feat_missing_dates = [d for d in feat_needed_dates if d not in available_utc_dates]
        if feat_missing_dates:
            return _empty_result(
                parent_article_id=parent_article_id,
                symbol=symbol,
                listing_regime=listing_regime,
                status="required_package_unavailable",
                status_reason=f"missing_utc_dates:{','.join(feat_missing_dates)}",
                anchor_time_ms=anchor_time_ms,
                anchor_price=validated_anchor_price,
            )

    if first_post_anchor_ts is None:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="feature_unavailable",
            status_reason="empty_feature_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
        )

    if feature_trade_count == 0 or last_feature_price is None:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="feature_unavailable",
            status_reason="no_trades_in_feature_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
        )

    if total_notional <= 0 or total_qty <= 0:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="feature_unavailable",
            status_reason="non_positive_feature_totals",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
        )

    taker_buy_share = buy_notional / total_notional
    vwap = total_notional / total_qty
    vwap_deviation = last_feature_price / vwap - 1
    feat_gap_out: int | None = feature_max_gap_ms

    # 2. Check sequence continuity within feature window before proceeding
    if feature_seq_gap:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="sequence_gap",
            status_reason="aggregate_id_gap_in_feature_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
        )

    # 3. Before declaring entry_unavailable, verify all UTC date packages covering the entry window exist
    if (
        entry_time_ms is None
        or entry_trade_id is None
        or entry_price is None
        or target_end_time_ms is None
    ):
        if available_utc_dates is not None:
            entry_needed_dates = required_utc_dates_for_window(anchor_time_ms, t_entry_deadline)
            entry_missing_dates = [d for d in entry_needed_dates if d not in available_utc_dates]
            if entry_missing_dates:
                return _empty_result(
                    parent_article_id=parent_article_id,
                    symbol=symbol,
                    listing_regime=listing_regime,
                    status="required_package_unavailable",
                    status_reason=f"missing_utc_dates:{','.join(entry_missing_dates)}",
                    anchor_time_ms=anchor_time_ms,
                    anchor_price=validated_anchor_price,
                    feature_trade_count=feature_trade_count,
                    feature_max_intertrade_gap_ms=feat_gap_out,
                    total_notional=total_notional,
                    taker_buy_share=taker_buy_share,
                    vwap=vwap,
                    vwap_deviation=vwap_deviation,
                )
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="entry_unavailable",
            status_reason="no_trade_in_entry_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
            feature_trade_count=feature_trade_count,
            feature_max_intertrade_gap_ms=feat_gap_out,
            total_notional=total_notional,
            taker_buy_share=taker_buy_share,
            vwap=vwap,
            vwap_deviation=vwap_deviation,
        )

    # 4. Check if all required UTC date packages for [anchor_time_ms, target_end_time_ms] are available
    if available_utc_dates is not None:
        needed_dates = required_utc_dates_for_window(anchor_time_ms, target_end_time_ms)
        missing_dates = [d for d in needed_dates if d not in available_utc_dates]
        if missing_dates:
            return _empty_result(
                parent_article_id=parent_article_id,
                symbol=symbol,
                listing_regime=listing_regime,
                status="required_package_unavailable",
                status_reason=f"missing_utc_dates:{','.join(missing_dates)}",
                anchor_time_ms=anchor_time_ms,
                anchor_price=validated_anchor_price,
                feature_trade_count=feature_trade_count,
                feature_max_intertrade_gap_ms=feat_gap_out,
                total_notional=total_notional,
                taker_buy_share=taker_buy_share,
                vwap=vwap,
                vwap_deviation=vwap_deviation,
                entry_time_ms=entry_time_ms,
                entry_trade_id=entry_trade_id,
                entry_price=entry_price,
                target_end_time_ms=target_end_time_ms,
            )

    # 5. Check sequence continuity from anchor through the end of the active window
    if active_seq_gap:
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="sequence_gap",
            status_reason="aggregate_id_gap_in_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
            feature_trade_count=feature_trade_count,
            feature_max_intertrade_gap_ms=feat_gap_out,
            total_notional=total_notional,
            taker_buy_share=taker_buy_share,
            vwap=vwap,
            vwap_deviation=vwap_deviation,
            entry_time_ms=entry_time_ms,
            entry_trade_id=entry_trade_id,
            entry_price=entry_price,
            target_end_time_ms=target_end_time_ms,
        )

    # 6. Check endpoint availability in [target_end_time_ms - endpoint_max_age_ms, target_end_time_ms]
    if (
        endpoint_time_ms is None
        or endpoint_trade_id is None
        or endpoint_price is None
        or path_min_price is None
        or path_max_price is None
    ):
        return _empty_result(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            status="endpoint_unavailable",
            status_reason="no_trade_in_endpoint_window",
            anchor_time_ms=anchor_time_ms,
            anchor_price=validated_anchor_price,
            feature_trade_count=feature_trade_count,
            feature_max_intertrade_gap_ms=feat_gap_out,
            total_notional=total_notional,
            taker_buy_share=taker_buy_share,
            vwap=vwap,
            vwap_deviation=vwap_deviation,
            entry_time_ms=entry_time_ms,
            entry_trade_id=entry_trade_id,
            entry_price=entry_price,
            target_end_time_ms=target_end_time_ms,
        )

    terminal_return = endpoint_price / entry_price - 1
    long_mae = path_min_price / entry_price - 1
    long_mfe = path_max_price / entry_price - 1

    return ChildResidualResponseResult(
        parent_article_id=parent_article_id,
        symbol=symbol,
        listing_regime=listing_regime,
        status="complete",
        status_reason=None,
        anchor_time_ms=anchor_time_ms,
        anchor_price=validated_anchor_price,
        feature_trade_count=feature_trade_count,
        feature_max_intertrade_gap_ms=feat_gap_out,
        total_notional=total_notional,
        taker_buy_share=taker_buy_share,
        vwap=vwap,
        vwap_deviation=vwap_deviation,
        entry_time_ms=entry_time_ms,
        entry_trade_id=entry_trade_id,
        entry_price=entry_price,
        target_end_time_ms=target_end_time_ms,
        endpoint_time_ms=endpoint_time_ms,
        endpoint_trade_id=endpoint_trade_id,
        endpoint_price=endpoint_price,
        path_trade_count=path_trade_count,
        max_intertrade_gap_ms=path_max_gap_ms,
        terminal_return=terminal_return,
        long_mae=long_mae,
        long_mfe=long_mfe,
    )


@dataclass(frozen=True)
class DistributionStats:
    n: int
    mean: Fraction | None
    median: Fraction | None
    min_val: Fraction | None
    max_val: Fraction | None
    p25: Fraction | None
    p75: Fraction | None


@dataclass(frozen=True)
class GroupOutcomeSummary:
    group_name: str
    n_items: int
    n_distinct_parents: int
    status: str
    terminal_return: DistributionStats
    long_mae: DistributionStats
    long_mfe: DistributionStats


@dataclass(frozen=True)
class ParentRegimeRecord:
    parent_article_id: str
    listing_regime: str
    status: str
    n_universe_children: int
    n_complete_children: int
    child_symbols: tuple[str, ...]
    taker_buy_share: Fraction | None
    terminal_return: Fraction | None
    long_mae: Fraction | None
    long_mfe: Fraction | None
    group_assignment: str | None


@dataclass(frozen=True)
class LeaveOneParentOutRow:
    excluded_parent_id: str
    n_remaining: int
    n_high: int
    n_low: int
    recalculated_median: Fraction | None
    high_minus_low_terminal_mean: Fraction | None
    status: str


@dataclass(frozen=True)
class LeaveOneParentOutSummary:
    rows: tuple[LeaveOneParentOutRow, ...]
    n_total_iterations: int
    n_non_null_iterations: int
    min_terminal_mean_diff: Fraction | None
    max_terminal_mean_diff: Fraction | None


@dataclass(frozen=True)
class RegimeExploratorySummary:
    listing_regime: str
    n_universe_children: int
    n_universe_parents: int
    n_complete_children: int
    n_complete_parents: int
    status_counts: dict[str, int]
    child_feature_stats: DistributionStats
    child_median_threshold: Fraction | None
    child_high_group: GroupOutcomeSummary
    child_low_group: GroupOutcomeSummary
    child_high_minus_low_terminal_mean: Fraction | None
    child_summary_status: str
    child_group_assignments: dict[tuple[str, str], str]
    parent_records: tuple[ParentRegimeRecord, ...]
    parent_feature_stats: DistributionStats
    parent_median_threshold: Fraction | None
    parent_high_group: GroupOutcomeSummary
    parent_low_group: GroupOutcomeSummary
    parent_high_minus_low_terminal_mean: Fraction | None
    parent_summary_status: str
    parent_leave_one_out: LeaveOneParentOutSummary


def compute_median(values: Sequence[Fraction]) -> Fraction | None:
    n = len(values)
    if n == 0:
        return None
    s = sorted(values)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / Fraction(2, 1)


def compute_nearest_rank_quantile(sorted_values: Sequence[Fraction], q: Fraction) -> Fraction | None:
    n = len(sorted_values)
    if n == 0:
        return None
    rank = math.ceil(q * n)
    idx = max(0, min(n - 1, rank - 1))
    return sorted_values[idx]


def compute_distribution_stats(values: Sequence[Fraction]) -> DistributionStats:
    n = len(values)
    if n == 0:
        return DistributionStats(
            n=0,
            mean=None,
            median=None,
            min_val=None,
            max_val=None,
            p25=None,
            p75=None,
        )
    s = sorted(values)
    mean_val = sum(s, Fraction(0, 1)) / Fraction(n, 1)
    median_val = compute_median(s)
    p25_val = compute_nearest_rank_quantile(s, Fraction(1, 4))
    p75_val = compute_nearest_rank_quantile(s, Fraction(3, 4))
    return DistributionStats(
        n=n,
        mean=mean_val,
        median=median_val,
        min_val=s[0],
        max_val=s[-1],
        p25=p25_val,
        p75=p75_val,
    )


def _summarize_outcome_group(
    *,
    group_name: str,
    parent_ids: Sequence[str],
    terminal_returns: Sequence[Fraction],
    long_maes: Sequence[Fraction],
    long_mfes: Sequence[Fraction],
) -> GroupOutcomeSummary:
    n_items = len(terminal_returns)
    n_parents = len(set(parent_ids))
    status = "exploratory_described" if n_items > 0 else "evidence_insufficient"
    return GroupOutcomeSummary(
        group_name=group_name,
        n_items=n_items,
        n_distinct_parents=n_parents,
        status=status,
        terminal_return=compute_distribution_stats(terminal_returns),
        long_mae=compute_distribution_stats(long_maes),
        long_mfe=compute_distribution_stats(long_mfes),
    )


def _compute_loo_row(
    *,
    excluded_parent_id: str,
    features: Sequence[Fraction],
    terminals: Sequence[Fraction],
) -> LeaveOneParentOutRow:
    n_rem = len(features)
    if n_rem == 0:
        return LeaveOneParentOutRow(
            excluded_parent_id=excluded_parent_id,
            n_remaining=0,
            n_high=0,
            n_low=0,
            recalculated_median=None,
            high_minus_low_terminal_mean=None,
            status="evidence_insufficient",
        )
    med = compute_median(features)
    assert med is not None
    high_idx = [i for i, f in enumerate(features) if f > med]
    low_idx = [i for i, f in enumerate(features) if f <= med]
    n_high = len(high_idx)
    n_low = len(low_idx)
    if n_high == 0 or n_low == 0:
        return LeaveOneParentOutRow(
            excluded_parent_id=excluded_parent_id,
            n_remaining=n_rem,
            n_high=n_high,
            n_low=n_low,
            recalculated_median=med,
            high_minus_low_terminal_mean=None,
            status="evidence_insufficient",
        )
    high_term_mean = sum((terminals[i] for i in high_idx), Fraction(0, 1)) / Fraction(n_high, 1)
    low_term_mean = sum((terminals[i] for i in low_idx), Fraction(0, 1)) / Fraction(n_low, 1)
    return LeaveOneParentOutRow(
        excluded_parent_id=excluded_parent_id,
        n_remaining=n_rem,
        n_high=n_high,
        n_low=n_low,
        recalculated_median=med,
        high_minus_low_terminal_mean=high_term_mean - low_term_mean,
        status="exploratory_described",
    )


def _summarize_loo(rows: Sequence[LeaveOneParentOutRow]) -> LeaveOneParentOutSummary:
    non_null_diffs = [
        r.high_minus_low_terminal_mean
        for r in rows
        if r.high_minus_low_terminal_mean is not None
    ]
    return LeaveOneParentOutSummary(
        rows=tuple(rows),
        n_total_iterations=len(rows),
        n_non_null_iterations=len(non_null_diffs),
        min_terminal_mean_diff=min(non_null_diffs) if non_null_diffs else None,
        max_terminal_mean_diff=max(non_null_diffs) if non_null_diffs else None,
    )


def summarize_regime_residual_response(
    *,
    listing_regime: str,
    child_results: Iterable[ChildResidualResponseResult],
) -> RegimeExploratorySummary:
    if listing_regime not in LEGAL_LISTING_REGIMES:
        raise TakerBuyShareResearchError(f"STOP=invalid_listing_regime:{listing_regime}")

    rows: list[ChildResidualResponseResult] = []
    seen_keys: set[tuple[str, str]] = set()
    for c in child_results:
        if not isinstance(c, ChildResidualResponseResult):
            raise TakerBuyShareResearchError("STOP=invalid_child_result_type")
        if c.listing_regime != listing_regime:
            raise TakerBuyShareResearchError(
                f"STOP=regime_mismatch_in_summarize:{c.listing_regime}!={listing_regime}"
            )
        if c.status not in LEGAL_CHILD_STATUSES:
            raise TakerBuyShareResearchError(f"STOP=invalid_child_status:{c.status}")
        key = (c.parent_article_id, c.symbol)
        if key in seen_keys:
            raise TakerBuyShareResearchError(f"STOP=duplicate_child_key:{key}")
        seen_keys.add(key)
        rows.append(c)

    rows.sort(key=lambda r: (r.parent_article_id, r.symbol))
    status_counts: dict[str, int] = {st: 0 for st in sorted(LEGAL_CHILD_STATUSES)}
    for r in rows:
        status_counts[r.status] += 1

    all_parents = sorted({r.parent_article_id for r in rows})
    complete_children = [r for r in rows if r.status == "complete"]
    for c in complete_children:
        if (
            c.taker_buy_share is None
            or c.terminal_return is None
            or c.long_mae is None
            or c.long_mfe is None
        ):
            raise TakerBuyShareResearchError(
                f"STOP=complete_child_missing_metrics:{c.parent_article_id}:{c.symbol}"
            )

    # Child-level feature distribution across complete children
    complete_child_features = [c.taker_buy_share for c in complete_children if c.taker_buy_share is not None]
    child_feature_stats = compute_distribution_stats(complete_child_features)
    child_median = compute_median(complete_child_features)

    child_high = [
        c for c in complete_children if child_median is not None and c.taker_buy_share is not None and c.taker_buy_share > child_median
    ]
    child_low = [
        c for c in complete_children if child_median is not None and c.taker_buy_share is not None and c.taker_buy_share <= child_median
    ]

    child_group_assignments: dict[tuple[str, str], str] = {}
    for c in child_high:
        child_group_assignments[(c.parent_article_id, c.symbol)] = "high"
    for c in child_low:
        child_group_assignments[(c.parent_article_id, c.symbol)] = "low"

    child_high_summary = _summarize_outcome_group(
        group_name="high",
        parent_ids=[c.parent_article_id for c in child_high],
        terminal_returns=[c.terminal_return for c in child_high if c.terminal_return is not None],
        long_maes=[c.long_mae for c in child_high if c.long_mae is not None],
        long_mfes=[c.long_mfe for c in child_high if c.long_mfe is not None],
    )
    child_low_summary = _summarize_outcome_group(
        group_name="low",
        parent_ids=[c.parent_article_id for c in child_low],
        terminal_returns=[c.terminal_return for c in child_low if c.terminal_return is not None],
        long_maes=[c.long_mae for c in child_low if c.long_mae is not None],
        long_mfes=[c.long_mfe for c in child_low if c.long_mfe is not None],
    )

    if (
        child_high_summary.terminal_return.mean is not None
        and child_low_summary.terminal_return.mean is not None
    ):
        child_diff: Fraction | None = (
            child_high_summary.terminal_return.mean - child_low_summary.terminal_return.mean
        )
        child_status = "exploratory_described"
    else:
        child_diff = None
        child_status = "evidence_insufficient"

    # Parent-level aggregation: only parents where ALL universe children in this regime are complete
    children_by_parent: dict[str, list[ChildResidualResponseResult]] = {pid: [] for pid in all_parents}
    for r in rows:
        children_by_parent[r.parent_article_id].append(r)

    prelim_parents: list[ParentRegimeRecord] = []
    for pid in all_parents:
        p_children = children_by_parent[pid]
        comp_children = [c for c in p_children if c.status == "complete"]
        if len(comp_children) == len(p_children) and len(p_children) > 0:
            p_share = compute_median([c.taker_buy_share for c in comp_children if c.taker_buy_share is not None])
            p_term = compute_median([c.terminal_return for c in comp_children if c.terminal_return is not None])
            p_mae = compute_median([c.long_mae for c in comp_children if c.long_mae is not None])
            p_mfe = compute_median([c.long_mfe for c in comp_children if c.long_mfe is not None])
            prelim_parents.append(
                ParentRegimeRecord(
                    parent_article_id=pid,
                    listing_regime=listing_regime,
                    status="complete",
                    n_universe_children=len(p_children),
                    n_complete_children=len(comp_children),
                    child_symbols=tuple(c.symbol for c in p_children),
                    taker_buy_share=p_share,
                    terminal_return=p_term,
                    long_mae=p_mae,
                    long_mfe=p_mfe,
                    group_assignment=None,
                )
            )
        else:
            prelim_parents.append(
                ParentRegimeRecord(
                    parent_article_id=pid,
                    listing_regime=listing_regime,
                    status="gap",
                    n_universe_children=len(p_children),
                    n_complete_children=len(comp_children),
                    child_symbols=tuple(c.symbol for c in p_children),
                    taker_buy_share=None,
                    terminal_return=None,
                    long_mae=None,
                    long_mfe=None,
                    group_assignment=None,
                )
            )

    complete_parents = [p for p in prelim_parents if p.status == "complete"]
    parent_features = [p.taker_buy_share for p in complete_parents if p.taker_buy_share is not None]
    parent_feature_stats = compute_distribution_stats(parent_features)
    parent_median = compute_median(parent_features)

    final_parents: list[ParentRegimeRecord] = []
    parent_high: list[ParentRegimeRecord] = []
    parent_low: list[ParentRegimeRecord] = []
    for p in prelim_parents:
        if p.status == "complete" and parent_median is not None and p.taker_buy_share is not None:
            grp = "high" if p.taker_buy_share > parent_median else "low"
            assigned = ParentRegimeRecord(
                parent_article_id=p.parent_article_id,
                listing_regime=p.listing_regime,
                status=p.status,
                n_universe_children=p.n_universe_children,
                n_complete_children=p.n_complete_children,
                child_symbols=p.child_symbols,
                taker_buy_share=p.taker_buy_share,
                terminal_return=p.terminal_return,
                long_mae=p.long_mae,
                long_mfe=p.long_mfe,
                group_assignment=grp,
            )
            final_parents.append(assigned)
            if grp == "high":
                parent_high.append(assigned)
            else:
                parent_low.append(assigned)
        else:
            final_parents.append(p)

    parent_high_summary = _summarize_outcome_group(
        group_name="high",
        parent_ids=[p.parent_article_id for p in parent_high],
        terminal_returns=[p.terminal_return for p in parent_high if p.terminal_return is not None],
        long_maes=[p.long_mae for p in parent_high if p.long_mae is not None],
        long_mfes=[p.long_mfe for p in parent_high if p.long_mfe is not None],
    )
    parent_low_summary = _summarize_outcome_group(
        group_name="low",
        parent_ids=[p.parent_article_id for p in parent_low],
        terminal_returns=[p.terminal_return for p in parent_low if p.terminal_return is not None],
        long_maes=[p.long_mae for p in parent_low if p.long_mae is not None],
        long_mfes=[p.long_mfe for p in parent_low if p.long_mfe is not None],
    )

    if (
        parent_high_summary.terminal_return.mean is not None
        and parent_low_summary.terminal_return.mean is not None
    ):
        parent_diff: Fraction | None = (
            parent_high_summary.terminal_return.mean - parent_low_summary.terminal_return.mean
        )
        parent_status = "exploratory_described"
    else:
        parent_diff = None
        parent_status = "evidence_insufficient"

    # Leave-one-parent-out sensitivity (strictly Parent-level terminal_return difference only per Design §3.4)
    parent_loo_rows: list[LeaveOneParentOutRow] = []
    for ex_p in complete_parents:
        rem_p = [p for p in complete_parents if p.parent_article_id != ex_p.parent_article_id]
        parent_loo_rows.append(
            _compute_loo_row(
                excluded_parent_id=ex_p.parent_article_id,
                features=[p.taker_buy_share for p in rem_p if p.taker_buy_share is not None],
                terminals=[p.terminal_return for p in rem_p if p.terminal_return is not None],
            )
        )

    return RegimeExploratorySummary(
        listing_regime=listing_regime,
        n_universe_children=len(rows),
        n_universe_parents=len(all_parents),
        n_complete_children=len(complete_children),
        n_complete_parents=len(complete_parents),
        status_counts=status_counts,
        child_feature_stats=child_feature_stats,
        child_median_threshold=child_median,
        child_high_group=child_high_summary,
        child_low_group=child_low_summary,
        child_high_minus_low_terminal_mean=child_diff,
        child_summary_status=child_status,
        child_group_assignments=child_group_assignments,
        parent_records=tuple(final_parents),
        parent_feature_stats=parent_feature_stats,
        parent_median_threshold=parent_median,
        parent_high_group=parent_high_summary,
        parent_low_group=parent_low_summary,
        parent_high_minus_low_terminal_mean=parent_diff,
        parent_summary_status=parent_status,
        parent_leave_one_out=_summarize_loo(parent_loo_rows),
    )


@dataclass(frozen=True)
class AdmittedJAContext:
    ja_root: Path
    manifest_by_path: dict[str, dict[str, Any]]
    request_by_id: dict[int, dict[str, Any]]
    package_by_key: dict[tuple[str, str, str], dict[str, Any]]
    admitted_object_ids: frozenset[int]


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES):
            h.update(chunk)
    return h.hexdigest()


def _has_symlink_ancestor(path: Path, stop_at: Path | None = None) -> bool:
    cur = path
    stop_resolved = stop_at.resolve() if stop_at is not None and stop_at.exists() else None
    while True:
        if os.path.islink(cur):
            return True
        if stop_resolved is not None and cur.exists():
            try:
                if cur.resolve() == stop_resolved:
                    break
            except OSError:
                return True
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return False


def _resolve_physical_path(path: Path) -> Path:
    cur = path if path.is_absolute() else (Path.cwd() / path)
    tail: list[str] = []
    while not cur.exists() and not os.path.islink(cur):
        parent = cur.parent
        if parent == cur:
            break
        tail.append(cur.name)
        cur = parent
    try:
        base_res = cur.resolve()
    except OSError as exc:
        raise TakerBuyShareResearchError(f"STOP=path_resolve_failed:{path}:{exc}") from exc
    for part in reversed(tail):
        base_res = base_res / part
    return base_res


def verify_safe_new_output_dir(
    *,
    output_dir: Path,
    protected_paths: Sequence[Path] = (),
    project_root: Path | None = None,
) -> Path:
    """Verify output_dir has no symlink ancestors, does not exist, and never collides with protected paths."""
    if _has_symlink_ancestor(output_dir):
        raise TakerBuyShareResearchError(f"STOP=output_dir_symlink_ancestor_rejected:{output_dir}")
    if output_dir.exists() or os.path.islink(output_dir):
        raise TakerBuyShareResearchError(f"STOP=output_dir_already_exists:{output_dir}")

    out_res = _resolve_physical_path(output_dir)

    all_protected: list[Path] = list(protected_paths)
    if project_root is not None:
        all_protected.extend(
            [
                project_root / J_A_ROOT_RELATIVE_PATH,
                project_root / J_B_ROOT_RELATIVE_PATH,
                project_root / "data/external_signal_shadow/stage1_5j_a",
                project_root / "data/external_signal_shadow/stage1_5j_b",
                project_root / "data/external_signal_shadow/stage1_5j_c",
                project_root / LEDGER_RELATIVE_PATH,
                project_root / "src",
                project_root / "scripts",
                project_root / "tests",
                project_root / "configs",
                project_root / "docs",
                project_root / ".git",
                project_root / ".agent",
                project_root / "AGENTS.md",
            ]
        )

    for prot in all_protected:
        prot_res = _resolve_physical_path(prot)
        if out_res == prot_res or out_res.is_relative_to(prot_res) or prot_res.is_relative_to(out_res):
            raise TakerBuyShareResearchError(
                f"STOP=output_dir_collides_with_protected_path:out={out_res}:protected={prot_res}"
            )
    return out_res


def verify_single_run_authorization(
    *,
    auth_file: Path,
    expected_output_dir: Path | None,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Verify single-run user authorization file before calling any strict loader or opening raw data."""
    if RISK_LIVE_TRADING_ENABLED is not False:
        raise TakerBuyShareResearchError("STOP=risk_live_trading_must_be_false")

    proj = project_root if project_root is not None else resolve_project_root()
    if os.path.islink(auth_file) or not auth_file.is_file():
        raise TakerBuyShareResearchError(f"STOP=authorization_file_missing_or_symlink:{auth_file}")

    try:
        raw_text = auth_file.read_text(encoding="utf-8")
        auth_obj = json.loads(raw_text)
    except Exception as exc:
        raise TakerBuyShareResearchError(f"STOP=authorization_json_invalid:{exc}") from exc

    if not isinstance(auth_obj, dict) or set(auth_obj.keys()) != REQUIRED_AUTH_KEYS:
        raise TakerBuyShareResearchError("STOP=authorization_keys_mismatch")

    if (
        auth_obj["design_relative_path"] != APPROVED_DESIGN_RELATIVE_PATH
        or auth_obj["design_sha256"] != APPROVED_DESIGN_SHA256
        or auth_obj["plan_relative_path"] != APPROVED_PLAN_RELATIVE_PATH
        or auth_obj["plan_sha256"] != APPROVED_PLAN_SHA256
        or auth_obj["ja_root_relative_path"] != J_A_ROOT_RELATIVE_PATH
        or auth_obj["jb_root_relative_path"] != J_B_ROOT_RELATIVE_PATH
        or auth_obj["ledger_relative_path"] != LEDGER_RELATIVE_PATH
        or auth_obj["ledger_sha256"] != LEDGER_SHA256
        or auth_obj["operation"] != "offline_research_once"
    ):
        raise TakerBuyShareResearchError("STOP=authorization_identity_or_operation_mismatch")

    for flag in (
        "network_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
        "signal_allowed",
    ):
        if auth_obj[flag] is not False:
            raise TakerBuyShareResearchError(f"STOP=authorization_permission_must_be_false:{flag}")

    out_str = auth_obj["output_dir"]
    if not isinstance(out_str, str) or not out_str.strip():
        raise TakerBuyShareResearchError("STOP=authorization_output_dir_invalid")

    if expected_output_dir is not None:
        if _resolve_physical_path(Path(out_str)) != _resolve_physical_path(expected_output_dir):
            raise TakerBuyShareResearchError("STOP=authorization_output_dir_mismatch")

    design_path = proj / APPROVED_DESIGN_RELATIVE_PATH
    plan_path = proj / APPROVED_PLAN_RELATIVE_PATH
    if not design_path.is_file() or _sha256_file(design_path) != APPROVED_DESIGN_SHA256:
        raise TakerBuyShareResearchError("STOP=design_authority_mismatch")
    if not plan_path.is_file() or _sha256_file(plan_path) != APPROVED_PLAN_SHA256:
        raise TakerBuyShareResearchError("STOP=approved_plan_authority_mismatch")

    return auth_obj


def verify_frozen_upstream_identities(project_root: Path | None = None) -> None:
    """Verify frozen J-A, J-B, V2 ledger, and J-B closure evidence SHA-256 bindings."""
    proj = project_root if project_root is not None else resolve_project_root()
    for rel_path, exp_sha in FROZEN_UPSTREAM_FILE_HASHES.items():
        full = proj / rel_path
        if _has_symlink_ancestor(full, stop_at=proj) or not full.is_file():
            raise TakerBuyShareResearchError(f"STOP=upstream_file_missing_or_symlink:{rel_path}")
        if _sha256_file(full) != exp_sha:
            raise TakerBuyShareResearchError(f"STOP=upstream_file_sha_mismatch:{rel_path}")


def _extract_article_ast_text(node: Any) -> str:
    if isinstance(node, dict):
        if "node" in node and node["node"] == "text":
            return str(node["text"]) if "text" in node else ""
        children = node["child"] if "child" in node and isinstance(node["child"], list) else []
        return "".join(_extract_article_ast_text(c) for c in children)
    if isinstance(node, list):
        return "".join(_extract_article_ast_text(c) for c in node)
    return ""


def _parse_article_ast_tables(body_obj: Any) -> list[list[list[str]]]:
    table_nodes: list[dict[str, Any]] = []

    def _find_tables(node: Any) -> None:
        if isinstance(node, dict):
            if "tag" in node and node["tag"] == "table":
                table_nodes.append(node)
            if "child" in node and isinstance(node["child"], list):
                for c in node["child"]:
                    _find_tables(c)
        elif isinstance(node, list):
            for c in node:
                _find_tables(c)

    _find_tables(body_obj)
    parsed_tables: list[list[list[str]]] = []
    for tbl in table_nodes:
        rows: list[list[str]] = []

        def _find_rows(node: Any) -> None:
            if isinstance(node, dict):
                if "tag" in node and node["tag"] == "tr":
                    cells: list[str] = []
                    children = (
                        node["child"] if "child" in node and isinstance(node["child"], list) else []
                    )
                    for c in children:
                        if isinstance(c, dict) and "tag" in c and c["tag"] in ("td", "th"):
                            cells.append(_extract_article_ast_text(c).strip())
                    if cells:
                        rows.append(cells)
                if "child" in node and isinstance(node["child"], list):
                    for c in node["child"]:
                        _find_rows(c)
            elif isinstance(node, list):
                for c in node:
                    _find_rows(c)

        _find_rows(tbl)
        if rows:
            parsed_tables.append(rows)
    return parsed_tables


def verify_v2_ledger_and_select_universe(
    *,
    ledger_path: Path,
    jb_child_rows: Sequence[dict[str, Any]],
    ja_root: Path,
    project_root: Path | None = None,
    expected_ledger_sha256: str = LEDGER_SHA256,
    expected_universe_count: int = 281,
    expected_selected_count: int = 71,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Verify V2 ledger SHA-256, 12-column schema, 281-key bijection with J-B, and article AST evidence."""
    proj = project_root if project_root is not None else resolve_project_root()
    if os.path.islink(ledger_path) or not ledger_path.is_file():
        raise TakerBuyShareResearchError(f"STOP=ledger_missing_or_symlink:{ledger_path}")
    actual_ledger_sha = _sha256_file(ledger_path)
    if actual_ledger_sha != expected_ledger_sha256:
        raise TakerBuyShareResearchError(
            f"STOP=ledger_sha_mismatch:expected={expected_ledger_sha256}:observed={actual_ledger_sha}"
        )

    manifest_path = ja_root / "manifest.json"
    if os.path.islink(manifest_path) or not manifest_path.is_file():
        raise TakerBuyShareResearchError(f"STOP=ja_manifest_missing:{manifest_path}")
    try:
        ja_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TakerBuyShareResearchError(f"STOP=ja_manifest_invalid_json:{exc}") from exc

    ja_manifest_map: dict[str, dict[str, Any]] = {}
    for item in ja_manifest["artifacts"]:
        ja_manifest_map[str(item["relative_path"])] = item

    with open(ledger_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise TakerBuyShareResearchError("STOP=ledger_empty") from exc
        if header != REQUIRED_LEDGER_COLUMNS:
            raise TakerBuyShareResearchError(f"STOP=ledger_header_mismatch:{header}")
        raw_rows: list[dict[str, str]] = []
        for row_idx, r in enumerate(reader, start=1):
            if len(r) != len(REQUIRED_LEDGER_COLUMNS):
                raise TakerBuyShareResearchError(f"STOP=ledger_column_count_row_{row_idx}")
            raw_rows.append(dict(zip(REQUIRED_LEDGER_COLUMNS, r)))

    seen_keys: set[tuple[str, str]] = set()
    for r in raw_rows:
        key = (r["parent_article_id"], r["symbol"])
        if key in seen_keys:
            raise TakerBuyShareResearchError(f"STOP=ledger_duplicate_key:{key}")
        seen_keys.add(key)

    jb_keys: set[tuple[str, str]] = set()
    for cr in jb_child_rows:
        jb_k = (str(cr["source_article_id"]), str(cr["symbol"]))
        if jb_k in jb_keys:
            raise TakerBuyShareResearchError(f"STOP=jb_duplicate_key:{jb_k}")
        jb_keys.add(jb_k)

    if seen_keys != jb_keys or len(raw_rows) != expected_universe_count:
        raise TakerBuyShareResearchError(
            f"STOP=ledger_bijection_mismatch:ledger={len(raw_rows)}:jb={len(jb_keys)}"
        )

    sorted_rows = sorted(raw_rows, key=lambda x: (x["parent_article_id"], x["symbol"]))
    universe_rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    crypto_headers = {
        "Project Info",
        "Project Information",
        "Smart Contract Address",
        "Total Supply",
        "Max Supply",
    }

    for r in sorted_rows:
        pid = r["parent_article_id"]
        sym = r["symbol"]
        a_cls = r["asset_class"]
        l_reg = r["listing_regime"]
        c_status = r["classification_status"]

        if (
            not HEX32_REGEX.match(pid)
            or not sym
            or not sym.isupper()
            or a_cls not in ALLOWED_ASSET_CLASSES
            or l_reg not in ALLOWED_LEDGER_REGIMES
            or c_status not in ALLOWED_CLASSIFICATION_STATUS
        ):
            raise TakerBuyShareResearchError(f"STOP=ledger_enum_or_key_invalid:{pid}:{sym}")

        in_scope = (
            a_cls == "crypto"
            and l_reg in LEGAL_LISTING_REGIMES
            and c_status == "confirmed"
        )
        if a_cls == "crypto" and c_status != "confirmed":
            raise TakerBuyShareResearchError(f"STOP=ledger_unconfirmed_crypto:{pid}:{sym}")

        u_row: dict[str, Any] = {
            "asset_class": a_cls,
            "classification_status": c_status,
            "in_scope": in_scope,
            "listing_regime": l_reg,
            "parent_article_id": pid,
            "symbol": sym,
        }
        universe_rows.append(u_row)

        if in_scope:
            exp_det_rel_in_ja = f"raw/article_details/{pid}.json"
            if exp_det_rel_in_ja not in ja_manifest_map:
                raise TakerBuyShareResearchError(f"STOP=detail_not_in_ja_manifest:{pid}")
            manifest_entry = ja_manifest_map[exp_det_rel_in_ja]
            src_rel = r["source_relative_path"]
            src_sha = r["source_sha256"]
            src_path = proj / src_rel
            expected_det_path = ja_root / exp_det_rel_in_ja
            if (
                os.path.islink(src_path)
                or not src_path.is_file()
                or src_path.resolve() != expected_det_path.resolve()
            ):
                raise TakerBuyShareResearchError(f"STOP=detail_path_mismatch:{src_rel}")
            actual_det_sha = _sha256_file(src_path)
            if actual_det_sha != src_sha or actual_det_sha != manifest_entry["sha256"]:
                raise TakerBuyShareResearchError(f"STOP=detail_sha_mismatch:{pid}")

            try:
                det_obj = json.loads(src_path.read_text(encoding="utf-8"))
                det_data = det_obj["data"]
                title = str(det_data["title"])
                body_obj = json.loads(str(det_data["body"]))
                t_idx = int(r["table_index"])
                c_idx = int(r["symbol_column_index"])
            except Exception as exc:
                raise TakerBuyShareResearchError(f"STOP=detail_parse_failed:{pid}:{exc}") from exc

            t_lower = title.lower()
            if "pre-market" in t_lower:
                exp_regime = "pre_market"
            elif "pre-ipo" in t_lower:
                exp_regime = "pre_ipo"
            else:
                exp_regime = "standard"
            if exp_regime != l_reg:
                raise TakerBuyShareResearchError(f"STOP=regime_mismatch:{pid}:{sym}")

            tables = _parse_article_ast_tables(body_obj)
            if not (0 <= t_idx < len(tables)):
                raise TakerBuyShareResearchError(f"STOP=table_index_invalid:{pid}:{sym}")
            tbl = tables[t_idx]
            col_cells = [row[c_idx] if len(row) > c_idx else "" for row in tbl]
            if not any(sym.upper() in cell.upper().replace(" ", "") for cell in col_cells):
                raise TakerBuyShareResearchError(f"STOP=symbol_column_mismatch:{pid}:{sym}")

            hdr = r["field_header"]
            raw_cell = r["raw_cell_value"]
            loc = r["evidence_locator"]
            exp_loc = f"table[{t_idx}].col[{c_idx}].row['{hdr}']"
            if hdr not in crypto_headers or not raw_cell or loc != exp_loc:
                raise TakerBuyShareResearchError(f"STOP=locator_or_header_mismatch:{pid}:{sym}")
            row_map = {
                row[0]: (row[c_idx] if len(row) > c_idx else "")
                for row in tbl
                if len(row) > 0
            }
            if hdr not in row_map or row_map[hdr] != raw_cell:
                raise TakerBuyShareResearchError(f"STOP=cell_value_mismatch:{pid}:{sym}")

            selected_rows.append(u_row)

    if len(selected_rows) != expected_selected_count:
        raise TakerBuyShareResearchError(
            f"STOP=selected_count_mismatch:{len(selected_rows)}!={expected_selected_count}"
        )

    return universe_rows, selected_rows


def build_admitted_ja_context(ja_root: Path, ja_summary: dict[str, Any]) -> AdmittedJAContext:
    """Build verified J-A package admission lookup from an already strict-loaded J-A root and summary."""
    if os.path.islink(ja_root) or not ja_root.is_dir():
        raise TakerBuyShareResearchError(f"STOP=ja_root_invalid:{ja_root}")
    manifest_file = ja_root / "manifest.json"
    if os.path.islink(manifest_file) or not manifest_file.is_file():
        raise TakerBuyShareResearchError(f"STOP=ja_manifest_missing:{manifest_file}")
    try:
        manifest_obj = json.loads(manifest_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TakerBuyShareResearchError(f"STOP=ja_manifest_parse_error:{exc}") from exc

    manifest_by_path: dict[str, dict[str, Any]] = {}
    for art in manifest_obj["artifacts"]:
        manifest_by_path[str(art["relative_path"])] = art

    if "request_records" not in ja_summary or not isinstance(ja_summary["request_records"], list):
        raise TakerBuyShareResearchError("STOP=ja_request_records_missing")
    request_by_id: dict[int, dict[str, Any]] = {}
    for req in ja_summary["request_records"]:
        request_by_id[int(req["request_id"])] = req

    if "archive_package_records" not in ja_summary or not isinstance(
        ja_summary["archive_package_records"], list
    ):
        raise TakerBuyShareResearchError("STOP=ja_archive_package_records_missing")
    package_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    obj_ids: set[int] = set()
    for rec in ja_summary["archive_package_records"]:
        if not isinstance(rec, dict):
            raise TakerBuyShareResearchError("STOP=package_record_not_dict")
        k = (str(rec["parent_article_id"]), str(rec["symbol"]), str(rec["utc_date"]))
        if k in package_by_key:
            raise TakerBuyShareResearchError(f"STOP=duplicate_package_record:{k}")
        package_by_key[k] = rec
        obj_ids.add(id(rec))

    return AdmittedJAContext(
        ja_root=ja_root,
        manifest_by_path=manifest_by_path,
        request_by_id=request_by_id,
        package_by_key=package_by_key,
        admitted_object_ids=frozenset(obj_ids),
    )


class _BoundedStreamReader(io.RawIOBase):
    """Local bounded raw stream enforcing EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES."""

    def __init__(self, raw: Any, chunk_limit: int) -> None:
        self._raw = raw
        self._limit = chunk_limit

    def readable(self) -> bool:
        return True

    def readinto(self, b: Any) -> int:
        req_len = len(b)
        if req_len > self._limit:
            raise TakerBuyShareResearchError(
                f"STOP=stream_chunk_bytes_exceeded:{req_len}>{self._limit}"
            )
        readinto_fn = getattr(self._raw, "readinto", None)
        if callable(readinto_fn):
            return int(readinto_fn(b))
        data = self._raw.read(req_len)
        n = len(data)
        b[:n] = data
        return n

    def close(self) -> None:
        if not self.closed:
            super().close()
            self._raw.close()


@contextlib.contextmanager
def open_verified_package_stream(
    admitted_ja_context: AdmittedJAContext,
    pkg_record: dict[str, Any],
    expected_parent_article_id: str,
    expected_symbol: str,
    expected_utc_date: str,
) -> Generator[io.BufferedReader, None, None]:
    """Verify J-A package record provenance, manifest/request linkage, checksum, and ZIP caps, yielding bounded reader."""
    if not isinstance(pkg_record, dict) or id(pkg_record) not in admitted_ja_context.admitted_object_ids:
        raise TakerBuyShareResearchError("STOP=package_record_unadmitted")

    key = (expected_parent_article_id, expected_symbol, expected_utc_date)
    if (
        key not in admitted_ja_context.package_by_key
        or admitted_ja_context.package_by_key[key] is not pkg_record
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_key_mismatch:{key}")

    expected_logical = {
        "market": "futures_um",
        "metric": "aggTrades",
        "parent_article_id": expected_parent_article_id,
        "symbol": expected_symbol,
        "utc_date": expected_utc_date,
    }
    if (
        pkg_record["parent_article_id"] != expected_parent_article_id
        or pkg_record["symbol"] != expected_symbol
        or pkg_record["utc_date"] != expected_utc_date
        or pkg_record["logical_archive_identity"] != expected_logical
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_logical_identity_mismatch:{key}")
    if pkg_record["child_state"] != "archive_verified_with_post_launch_rows":
        raise TakerBuyShareResearchError(
            f"STOP=package_record_child_state_unverified:{pkg_record['child_state']}"
        )

    zip_req_id = pkg_record["zip_request_id"]
    chk_req_id = pkg_record["checksum_request_id"]
    if (
        not _is_strict_int(zip_req_id)
        or not _is_strict_int(chk_req_id)
        or zip_req_id not in admitted_ja_context.request_by_id
        or chk_req_id not in admitted_ja_context.request_by_id
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_request_linkage_missing:{key}")

    zip_rel = f"raw/archive/{expected_symbol}/{expected_symbol}-aggTrades-{expected_utc_date}.zip"
    chk_rel = f"{zip_rel}.CHECKSUM"
    zip_req = admitted_ja_context.request_by_id[zip_req_id]
    chk_req = admitted_ja_context.request_by_id[chk_req_id]

    if (
        zip_req["request_kind"] != "archive"
        or zip_req["request_state"] != "response_persisted"
        or zip_req["response_relative_path"] != zip_rel
        or chk_req["request_kind"] != "checksum"
        or chk_req["request_state"] != "response_persisted"
        or chk_req["response_relative_path"] != chk_rel
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_request_mismatch:{key}")

    if (
        zip_rel not in admitted_ja_context.manifest_by_path
        or chk_rel not in admitted_ja_context.manifest_by_path
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_manifest_missing:{key}")
    zip_man = admitted_ja_context.manifest_by_path[zip_rel]
    chk_man = admitted_ja_context.manifest_by_path[chk_rel]

    if (
        zip_man["sha256"] != zip_req["response_sha256"]
        or zip_man["byte_count"] != zip_req["response_bytes"]
        or chk_man["sha256"] != chk_req["response_sha256"]
        or chk_man["byte_count"] != chk_req["response_bytes"]
    ):
        raise TakerBuyShareResearchError(f"STOP=package_record_manifest_request_sha_mismatch:{key}")

    ja_root = admitted_ja_context.ja_root
    zip_path = ja_root / zip_rel
    chk_path = ja_root / chk_rel
    root_resolved = ja_root.resolve()

    if (
        _has_symlink_ancestor(zip_path, stop_at=ja_root)
        or _has_symlink_ancestor(chk_path, stop_at=ja_root)
        or not zip_path.is_file()
        or not chk_path.is_file()
    ):
        raise TakerBuyShareResearchError(f"STOP=zip_package_missing_or_symlink:{zip_path}")
    zip_res = zip_path.resolve()
    chk_res = chk_path.resolve()
    if not zip_res.is_relative_to(root_resolved) or not chk_res.is_relative_to(root_resolved):
        raise TakerBuyShareResearchError(f"STOP=zip_package_path_escape:{zip_path}")

    chk_bytes = chk_path.read_bytes()
    actual_chk_sha = _sha256_bytes(chk_bytes)
    if actual_chk_sha != chk_man["sha256"] or len(chk_bytes) != chk_man["byte_count"]:
        raise TakerBuyShareResearchError(f"STOP=checksum_invalid:manifest_mismatch:{chk_path}")
    try:
        chk_text = chk_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TakerBuyShareResearchError(f"STOP=checksum_invalid:utf8:{chk_path}") from exc
    parts = chk_text.strip().split()
    if len(parts) != 2 or not SHA256_REGEX.match(parts[0]) or parts[1] != zip_path.name:
        raise TakerBuyShareResearchError(f"STOP=checksum_invalid:format:{chk_path}")
    expected_zip_sha = parts[0]
    actual_zip_sha = _sha256_file(zip_path)
    actual_zip_size = zip_path.stat().st_size
    if (
        actual_zip_sha != expected_zip_sha
        or actual_zip_sha != zip_man["sha256"]
        or actual_zip_size != zip_man["byte_count"]
    ):
        raise TakerBuyShareResearchError(f"STOP=checksum_invalid:zip_sha_mismatch:{zip_path}")

    if not validate_zip_archive_package(
        zip_path,
        max_zip_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_ZIP_BYTES,
        max_uncompressed_bytes=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_CSV_UNCOMPRESSED_BYTES,
        max_ratio=EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ARCHIVE_COMPRESSION_RATIO,
    ):
        raise TakerBuyShareResearchError(f"STOP=zip_package_resource_caps_failed:{zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if len(names) != 1 or not names[0].endswith(".csv"):
                raise TakerBuyShareResearchError(f"STOP=zip_package_members_invalid:{names}")
            with zf.open(names[0], "r") as raw_member:
                bounded = _BoundedStreamReader(
                    raw_member, EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES
                )
                buf = io.BufferedReader(
                    bounded, buffer_size=EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES
                )
                try:
                    yield buf
                finally:
                    buf.close()
    except TakerBuyShareResearchError:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise TakerBuyShareResearchError(f"STOP=zip_package_corrupt:{zip_path}:{exc}") from exc


def _parse_nonneg_int_str(raw: str, field_name: str) -> int:
    if not NONNEG_INT_STR_REGEX.match(raw):
        raise TakerBuyShareResearchError(f"STOP=invalid_csv_int:{field_name}:{raw}")
    return int(raw)


def _utc_date_bounds_ms(utc_date: str) -> tuple[int, int]:
    try:
        dt = datetime.strptime(utc_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise TakerBuyShareResearchError(f"STOP=invalid_utc_date:{utc_date}") from exc
    start_ms = int((dt - _EPOCH_UTC) // timedelta(milliseconds=1))
    end_ms = int((dt + timedelta(days=1) - _EPOCH_UTC) // timedelta(milliseconds=1))
    return start_ms, end_ms


def _iter_bounded_csv_rows_from_package(
    admitted_ja_context: AdmittedJAContext,
    pkg_record: dict[str, Any],
    expected_parent_article_id: str,
    expected_symbol: str,
    expected_utc_date: str,
) -> Generator[AggTradeRecord, None, None]:
    """Stream all CSV rows to EOF with bounded physical line length <= 65,536 bytes and strict field checks."""
    max_line_bytes = EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES
    day_start_ms, day_end_ms = _utc_date_bounds_ms(expected_utc_date)

    with open_verified_package_stream(
        admitted_ja_context,
        pkg_record,
        expected_parent_article_id=expected_parent_article_id,
        expected_symbol=expected_symbol,
        expected_utc_date=expected_utc_date,
    ) as buf:
        header_raw = buf.readline(max_line_bytes + 1)
        if not header_raw:
            raise TakerBuyShareResearchError(
                f"STOP=csv_header_empty:{expected_symbol}:{expected_utc_date}"
            )
        if len(header_raw) > max_line_bytes or not header_raw.endswith(b"\n"):
            raise TakerBuyShareResearchError(
                f"STOP=csv_line_length_exceeded:header:{expected_symbol}:{expected_utc_date}"
            )
        try:
            header_text = header_raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise TakerBuyShareResearchError(f"STOP=csv_encoding_invalid:header:{expected_symbol}") from exc
        header_cols = next(csv.reader([header_text]))
        if header_cols != REQUIRED_CSV_HEADER:
            raise TakerBuyShareResearchError(f"STOP=csv_header_mismatch:{header_cols}")

        phys_row = 0
        prev_tid: int | None = None
        prev_ts: int | None = None
        while True:
            raw_line = buf.readline(max_line_bytes + 1)
            if not raw_line:
                break
            if len(raw_line) > max_line_bytes:
                raise TakerBuyShareResearchError(
                    f"STOP=csv_line_length_exceeded:{expected_symbol}:{expected_utc_date}:{phys_row + 1}"
                )
            try:
                line_text = raw_line.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise TakerBuyShareResearchError(
                    f"STOP=csv_encoding_invalid:{expected_symbol}:{phys_row + 1}"
                ) from exc
            parsed_rows = list(csv.reader([line_text]))
            if len(parsed_rows) != 1 or len(parsed_rows[0]) != 7:
                raise TakerBuyShareResearchError(
                    f"STOP=csv_row_malformed:{expected_symbol}:{phys_row + 1}"
                )
            cols = parsed_rows[0]
            phys_row += 1
            tid = _parse_nonneg_int_str(cols[0], "agg_trade_id")
            fid = _parse_nonneg_int_str(cols[3], "first_trade_id")
            lid = _parse_nonneg_int_str(cols[4], "last_trade_id")
            ts = _parse_nonneg_int_str(cols[5], "transact_time")
            if fid > lid:
                raise TakerBuyShareResearchError(f"STOP=csv_first_gt_last_trade_id:{expected_symbol}")
            if not (day_start_ms <= ts < day_end_ms):
                raise TakerBuyShareResearchError(
                    f"STOP=csv_timestamp_outside_utc_date:{expected_symbol}:{expected_utc_date}:{ts}"
                )
            bm_raw = cols[6]
            if bm_raw in ("true", "True"):
                is_bm = True
            elif bm_raw in ("false", "False"):
                is_bm = False
            else:
                raise TakerBuyShareResearchError(f"STOP=csv_boolean_invalid:{expected_symbol}:{bm_raw}")

            p_frac = _to_positive_fraction(cols[1], "price")
            q_frac = _to_positive_fraction(cols[2], "quantity")

            if prev_tid is not None and tid <= prev_tid:
                raise TakerBuyShareResearchError(f"STOP=csv_agg_trade_id_order_invalid:{expected_symbol}")
            if prev_ts is not None and ts < prev_ts:
                raise TakerBuyShareResearchError(f"STOP=csv_timestamp_order_invalid:{expected_symbol}")
            prev_tid = tid
            prev_ts = ts

            yield AggTradeRecord(
                aggregate_id=tid,
                price=p_frac,
                quantity=q_frac,
                timestamp_ms=ts,
                is_buyer_maker=is_bm,
            )


def stream_and_evaluate_admitted_child(
    *,
    admitted_ja_context: AdmittedJAContext,
    parent_article_id: str,
    symbol: str,
    listing_regime: str,
    jb_child_row: dict[str, Any],
    protocol: ExploratoryProtocol,
) -> ChildResidualResponseResult:
    """Admit required J-A date packages up to entry+15m, stream each to EOF, and evaluate child response."""
    validate_exploratory_protocol(protocol)

    ja_parent_state = str(jb_child_row["j_a_parent_state"])
    ja_child_state = str(jb_child_row["j_a_child_state"])
    anchor_state = str(jb_child_row["anchor_state"])

    if ja_parent_state != "coverage_complete" or ja_child_state != "j_a_child_coverage_complete":
        return evaluate_child_residual_response(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            protocol=protocol,
            anchor_time_ms=None,
            anchor_price=None,
            trades=[],
            upstream_gap_reason=f"{ja_parent_state}:{ja_child_state}",
        )

    if anchor_state != "anchor_found":
        return evaluate_child_residual_response(
            parent_article_id=parent_article_id,
            symbol=symbol,
            listing_regime=listing_regime,
            protocol=protocol,
            anchor_time_ms=None,
            anchor_price=None,
            trades=[],
            anchor_unavailable_reason=anchor_state,
        )

    launch_ms = jb_child_row["symbol_launch_time_ms"]
    anchor_ms = jb_child_row["anchor_time_ms"]
    anchor_price_raw = jb_child_row["anchor_price"]
    if (
        not _is_strict_int(launch_ms)
        or not _is_strict_int(anchor_ms)
        or not isinstance(anchor_price_raw, str)
    ):
        raise TakerBuyShareResearchError(
            f"STOP=jb_anchor_fields_invalid:{parent_article_id}:{symbol}"
        )

    expected_anchor_price = _to_positive_fraction(anchor_price_raw, "anchor_price")
    anchor_date = utc_date_str_from_ms(anchor_ms)
    anchor_key = (parent_article_id, symbol, anchor_date)
    if anchor_key not in admitted_ja_context.package_by_key:
        raise TakerBuyShareResearchError(f"STOP=anchor_package_missing:{anchor_key}")
    anchor_pkg = admitted_ja_context.package_by_key[anchor_key]
    if anchor_pkg["child_state"] != "archive_verified_with_post_launch_rows":
        raise TakerBuyShareResearchError(f"STOP=anchor_package_unverified:{anchor_key}")

    t_decision = anchor_ms + protocol.feature_window_ms + protocol.latency_ms
    t_entry_deadline = t_decision + protocol.entry_max_wait_ms
    max_possible_end_ms = t_entry_deadline + protocol.hold_horizon_ms

    available_dates: set[str] = {anchor_date}

    def _chained_package_trades() -> Generator[AggTradeRecord, None, None]:
        anchor_verified = False
        entry_time_found: int | None = None
        last_tid: int | None = None
        last_ts: int | None = None

        for tr in _iter_bounded_csv_rows_from_package(
            admitted_ja_context,
            anchor_pkg,
            expected_parent_article_id=parent_article_id,
            expected_symbol=symbol,
            expected_utc_date=anchor_date,
        ):
            last_tid = tr.aggregate_id
            last_ts = tr.timestamp_ms
            if not anchor_verified and tr.timestamp_ms >= launch_ms:
                if (
                    tr.timestamp_ms != anchor_ms
                    or tr.price != expected_anchor_price
                    or tr.timestamp_ms - launch_ms > EXTERNAL_SIGNAL_STAGE1_5J_B_MAX_ANCHOR_DELAY_MS
                ):
                    raise TakerBuyShareResearchError(
                        f"STOP=anchor_replay_mismatch:{parent_article_id}:{symbol}"
                    )
                anchor_verified = True

            if anchor_ms <= tr.timestamp_ms <= max_possible_end_ms:
                if entry_time_found is None and t_decision <= tr.timestamp_ms <= t_entry_deadline:
                    entry_time_found = tr.timestamp_ms
                yield tr

        if not anchor_verified:
            raise TakerBuyShareResearchError(
                f"STOP=anchor_not_found_in_raw:{parent_article_id}:{symbol}"
            )

        # Determine required UTC dates dynamically up to entry.timestamp + 15min (or t_entry_deadline if entry crossed midnight)
        target_end_for_dates = (
            entry_time_found + protocol.hold_horizon_ms
            if entry_time_found is not None
            else t_entry_deadline
        )
        needed_dates = required_utc_dates_for_window(anchor_ms, target_end_for_dates)

        for next_date in needed_dates[1:]:
            next_key = (parent_article_id, symbol, next_date)
            if next_key not in admitted_ja_context.package_by_key:
                continue
            next_pkg = admitted_ja_context.package_by_key[next_key]
            if next_pkg["child_state"] != "archive_verified_with_post_launch_rows":
                continue
            available_dates.add(next_date)
            for tr in _iter_bounded_csv_rows_from_package(
                admitted_ja_context,
                next_pkg,
                expected_parent_article_id=parent_article_id,
                expected_symbol=symbol,
                expected_utc_date=next_date,
            ):
                if last_tid is not None and tr.aggregate_id <= last_tid:
                    raise TakerBuyShareResearchError(
                        f"STOP=cross_day_agg_trade_id_order_invalid:{symbol}:{next_date}"
                    )
                if last_ts is not None and tr.timestamp_ms < last_ts:
                    raise TakerBuyShareResearchError(
                        f"STOP=cross_day_timestamp_order_invalid:{symbol}:{next_date}"
                    )
                last_tid = tr.aggregate_id
                last_ts = tr.timestamp_ms
                if anchor_ms <= tr.timestamp_ms <= max_possible_end_ms:
                    if entry_time_found is None and t_decision <= tr.timestamp_ms <= t_entry_deadline:
                        entry_time_found = tr.timestamp_ms
                    yield tr

    return evaluate_child_residual_response(
        parent_article_id=parent_article_id,
        symbol=symbol,
        listing_regime=listing_regime,
        protocol=protocol,
        anchor_time_ms=anchor_ms,
        anchor_price=expected_anchor_price,
        trades=_chained_package_trades(),
        available_utc_dates=available_dates,
    )


def format_exact_fraction(val: Fraction | None) -> str:
    if val is None:
        return ""
    if val == 0:
        return "0/1"
    return f"{val.numerator}/{val.denominator}"


def format_decimal_display(val: Fraction | None) -> str:
    if val is None:
        return "null"
    dec = (Decimal(val.numerator) / Decimal(val.denominator)).quantize(
        Decimal("0.00000001"), rounding=ROUND_HALF_EVEN
    )
    return f"{dec:.8f}"


def _render_stats_md_row(label: str, st: DistributionStats) -> str:
    if st.n == 0:
        return f"| {label} | 0 | null | null | null | null | null | null |"
    return (
        f"| {label} | {st.n} "
        f"| `{format_exact_fraction(st.mean)}` ({format_decimal_display(st.mean)}) "
        f"| `{format_exact_fraction(st.median)}` ({format_decimal_display(st.median)}) "
        f"| `{format_exact_fraction(st.min_val)}` ({format_decimal_display(st.min_val)}) "
        f"| `{format_exact_fraction(st.max_val)}` ({format_decimal_display(st.max_val)}) "
        f"| `{format_exact_fraction(st.p25)}` ({format_decimal_display(st.p25)}) "
        f"| `{format_exact_fraction(st.p75)}` ({format_decimal_display(st.p75)}) |"
    )


def _render_regime_section_md(reg_summary: RegimeExploratorySummary) -> list[str]:
    lines: list[str] = [
        f"## 机制：`{reg_summary.listing_regime}`",
        "",
        f"- Universe Child 数：`{reg_summary.n_universe_children}`；Universe Parent 数：`{reg_summary.n_universe_parents}`",
        f"- Complete Child 数：`{reg_summary.n_complete_children}`；Complete Parent 数：`{reg_summary.n_complete_parents}`",
        f"- Child 汇总状态：`{reg_summary.child_summary_status}`；Parent 汇总状态：`{reg_summary.parent_summary_status}`",
        f"- Child `taker_buy_share` 样本中位数分界：`{format_exact_fraction(reg_summary.child_median_threshold) or 'null'}` ({format_decimal_display(reg_summary.child_median_threshold)})",
        f"- Child `high - low` 终点均值差：`{format_exact_fraction(reg_summary.child_high_minus_low_terminal_mean) or 'null'}` ({format_decimal_display(reg_summary.child_high_minus_low_terminal_mean)})",
        f"- Parent `taker_buy_share` 样本中位数分界：`{format_exact_fraction(reg_summary.parent_median_threshold) or 'null'}` ({format_decimal_display(reg_summary.parent_median_threshold)})",
        f"- Parent `high - low` 终点均值差：`{format_exact_fraction(reg_summary.parent_high_minus_low_terminal_mean) or 'null'}` ({format_decimal_display(reg_summary.parent_high_minus_low_terminal_mean)})",
        "",
        "### 状态计数守恒",
        "",
        "| 状态 | 数量 |",
        "| --- | --- |",
    ]
    for st_name, cnt in sorted(reg_summary.status_counts.items()):
        lines.append(f"| `{st_name}` | {cnt} |")

    lines.extend(
        [
            "",
            "### Child 层分布（`high` vs `low`）",
            "",
            f"- `high` 组：Child 数 = `{reg_summary.child_high_group.n_items}`，涉及 Parent 数 = `{reg_summary.child_high_group.n_distinct_parents}`，状态 = `{reg_summary.child_high_group.status}`",
            f"- `low` 组：Child 数 = `{reg_summary.child_low_group.n_items}`，涉及 Parent 数 = `{reg_summary.child_low_group.n_distinct_parents}`，状态 = `{reg_summary.child_low_group.status}`",
            "",
            "| 组别与指标 | N | Mean | Median | Min | Max | P25 | P75 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            _render_stats_md_row("child_feature (`taker_buy_share`)", reg_summary.child_feature_stats),
            _render_stats_md_row("child_high `terminal_return`", reg_summary.child_high_group.terminal_return),
            _render_stats_md_row("child_high `long_mae`", reg_summary.child_high_group.long_mae),
            _render_stats_md_row("child_high `long_mfe`", reg_summary.child_high_group.long_mfe),
            _render_stats_md_row("child_low `terminal_return`", reg_summary.child_low_group.terminal_return),
            _render_stats_md_row("child_low `long_mae`", reg_summary.child_low_group.long_mae),
            _render_stats_md_row("child_low `long_mfe`", reg_summary.child_low_group.long_mfe),
            "",
            "### Parent 层分布（仅全部 Universe Child 均 Complete 的 Parent）",
            "",
            f"- `high` 组：Parent 数 = `{reg_summary.parent_high_group.n_items}`，状态 = `{reg_summary.parent_high_group.status}`",
            f"- `low` 组：Parent 数 = `{reg_summary.parent_low_group.n_items}`，状态 = `{reg_summary.parent_low_group.status}`",
            "",
            "| 组别与指标 | N | Mean | Median | Min | Max | P25 | P75 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            _render_stats_md_row("parent_feature (`taker_buy_share`)", reg_summary.parent_feature_stats),
            _render_stats_md_row("parent_high `terminal_return`", reg_summary.parent_high_group.terminal_return),
            _render_stats_md_row("parent_high `long_mae`", reg_summary.parent_high_group.long_mae),
            _render_stats_md_row("parent_high `long_mfe`", reg_summary.parent_high_group.long_mfe),
            _render_stats_md_row("parent_low `terminal_return`", reg_summary.parent_low_group.terminal_return),
            _render_stats_md_row("parent_low `long_mae`", reg_summary.parent_low_group.long_mae),
            _render_stats_md_row("parent_low `long_mfe`", reg_summary.parent_low_group.long_mfe),
            "",
            "### Parent 构成明细",
            "",
            "| Parent ID | 状态 | Universe Child 数 | Complete Child 数 | Child 列表 | Parent 特征中位数 | Parent 组别 | Parent `terminal_return` 中位数 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for pr in reg_summary.parent_records:
        lines.append(
            f"| `{pr.parent_article_id}` | `{pr.status}` | {pr.n_universe_children} | {pr.n_complete_children} "
            f"| `{','.join(pr.child_symbols)}` "
            f"| `{format_exact_fraction(pr.taker_buy_share) or 'null'}` "
            f"| `{pr.group_assignment or 'null'}` "
            f"| `{format_exact_fraction(pr.terminal_return) or 'null'}` |"
        )

    loo = reg_summary.parent_leave_one_out
    lines.extend(
        [
            "",
            "### Leave-One-Parent-Out 敏感性（Parent 层）",
            "",
            f"- 总迭代数：`{loo.n_total_iterations}`；非 null 迭代数：`{loo.n_non_null_iterations}`",
            f"- 非 null `high - low` 终点均值差范围：`[{format_exact_fraction(loo.min_terminal_mean_diff) or 'null'}, {format_exact_fraction(loo.max_terminal_mean_diff) or 'null'}]` "
            f"({format_decimal_display(loo.min_terminal_mean_diff)} .. {format_decimal_display(loo.max_terminal_mean_diff)})",
            "",
            "| 剔除 Parent ID | 剩余总数 | High 数 | Low 数 | 重算中位数 | `high - low` Terminal Mean | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for lr in loo.rows:
        lines.append(
            f"| `{lr.excluded_parent_id}` | {lr.n_remaining} | {lr.n_high} | {lr.n_low} "
            f"| `{format_exact_fraction(lr.recalculated_median) or 'null'}` "
            f"| `{format_exact_fraction(lr.high_minus_low_terminal_mean) or 'null'}` "
            f"| `{lr.status}` |"
        )
    lines.append("")
    return lines


def write_exploratory_outputs(
    *,
    output_dir: Path,
    protected_paths: Sequence[Path],
    protocol: ExploratoryProtocol,
    child_results: Sequence[ChildResidualResponseResult],
    design_sha256: str,
    plan_sha256: str,
    ja_run_id: str,
    jb_run_id: str,
    ledger_sha256: str,
    project_root: Path | None = None,
) -> tuple[Path, Path]:
    """Validate output directory, compute summaries, and write child_rows.csv and review_CN.md."""
    validate_exploratory_protocol(protocol)
    out_res = verify_safe_new_output_dir(
        output_dir=output_dir,
        protected_paths=protected_paths,
        project_root=project_root,
    )

    pm_children = [c for c in child_results if c.listing_regime == "pre_market"]
    std_children = [c for c in child_results if c.listing_regime == "standard"]
    if len(pm_children) + len(std_children) != len(child_results):
        raise TakerBuyShareResearchError("STOP=unexpected_listing_regime_in_child_results")

    pm_summary = summarize_regime_residual_response(
        listing_regime="pre_market", child_results=pm_children
    )
    std_summary = summarize_regime_residual_response(
        listing_regime="standard", child_results=std_children
    )

    group_map: dict[tuple[str, str], str] = {}
    group_map.update(pm_summary.child_group_assignments)
    group_map.update(std_summary.child_group_assignments)

    sorted_children = sorted(
        child_results, key=lambda r: (r.listing_regime, r.parent_article_id, r.symbol)
    )

    csv_buf = io.StringIO()
    fieldnames = [
        "parent_article_id",
        "symbol",
        "listing_regime",
        "status",
        "status_reason",
        "anchor_time_ms",
        "anchor_utc_date",
        "anchor_price_exact",
        "feature_trade_count",
        "feature_max_intertrade_gap_ms",
        "total_notional_exact",
        "taker_buy_share_exact",
        "taker_buy_share_decimal",
        "vwap_exact",
        "vwap_deviation_exact",
        "child_group",
        "entry_time_ms",
        "entry_trade_id",
        "entry_price_exact",
        "target_end_time_ms",
        "endpoint_time_ms",
        "endpoint_trade_id",
        "endpoint_price_exact",
        "path_trade_count",
        "max_intertrade_gap_ms",
        "terminal_return_exact",
        "terminal_return_decimal",
        "long_mae_exact",
        "long_mae_decimal",
        "long_mfe_exact",
        "long_mfe_decimal",
    ]
    writer = csv.DictWriter(csv_buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for c in sorted_children:
        key = (c.parent_article_id, c.symbol)
        grp = group_map[key] if key in group_map else ""
        anc_date = utc_date_str_from_ms(c.anchor_time_ms) if c.anchor_time_ms is not None else ""
        writer.writerow(
            {
                "parent_article_id": c.parent_article_id,
                "symbol": c.symbol,
                "listing_regime": c.listing_regime,
                "status": c.status,
                "status_reason": c.status_reason or "",
                "anchor_time_ms": "" if c.anchor_time_ms is None else str(c.anchor_time_ms),
                "anchor_utc_date": anc_date,
                "anchor_price_exact": format_exact_fraction(c.anchor_price),
                "feature_trade_count": str(c.feature_trade_count),
                "feature_max_intertrade_gap_ms": ""
                if c.feature_max_intertrade_gap_ms is None
                else str(c.feature_max_intertrade_gap_ms),
                "total_notional_exact": format_exact_fraction(c.total_notional),
                "taker_buy_share_exact": format_exact_fraction(c.taker_buy_share),
                "taker_buy_share_decimal": ""
                if c.taker_buy_share is None
                else format_decimal_display(c.taker_buy_share),
                "vwap_exact": format_exact_fraction(c.vwap),
                "vwap_deviation_exact": format_exact_fraction(c.vwap_deviation),
                "child_group": grp,
                "entry_time_ms": "" if c.entry_time_ms is None else str(c.entry_time_ms),
                "entry_trade_id": "" if c.entry_trade_id is None else str(c.entry_trade_id),
                "entry_price_exact": format_exact_fraction(c.entry_price),
                "target_end_time_ms": ""
                if c.target_end_time_ms is None
                else str(c.target_end_time_ms),
                "endpoint_time_ms": "" if c.endpoint_time_ms is None else str(c.endpoint_time_ms),
                "endpoint_trade_id": ""
                if c.endpoint_trade_id is None
                else str(c.endpoint_trade_id),
                "endpoint_price_exact": format_exact_fraction(c.endpoint_price),
                "path_trade_count": str(c.path_trade_count),
                "max_intertrade_gap_ms": ""
                if c.max_intertrade_gap_ms is None
                else str(c.max_intertrade_gap_ms),
                "terminal_return_exact": format_exact_fraction(c.terminal_return),
                "terminal_return_decimal": ""
                if c.terminal_return is None
                else format_decimal_display(c.terminal_return),
                "long_mae_exact": format_exact_fraction(c.long_mae),
                "long_mae_decimal": ""
                if c.long_mae is None
                else format_decimal_display(c.long_mae),
                "long_mfe_exact": format_exact_fraction(c.long_mfe),
                "long_mfe_decimal": ""
                if c.long_mfe is None
                else format_decimal_display(c.long_mfe),
            }
        )

    all_distinct_parents = sorted({c.parent_article_id for c in sorted_children})
    date_counts: dict[str, int] = {}
    for c in sorted_children:
        if c.anchor_time_ms is not None:
            d_str = utc_date_str_from_ms(c.anchor_time_ms)
            date_counts[d_str] = (date_counts[d_str] if d_str in date_counts else 0) + 1

    md_lines: list[str] = [
        "# 新合约上线后主动买入占比与剩余价格响应探索报告 (`exploratory`)",
        "",
        "- **研究状态**：`exploratory` / `hypothesis_only`（不声称统计因果、方向预测力、`alpha_candidate` 或 `alpha_validated`；不授予任何下游机器消费、信号、纸面或实盘交易权限）",
        f"- **Design 路径与 SHA-256**：`{APPROVED_DESIGN_RELATIVE_PATH}` (`{design_sha256}`)",
        f"- **Plan 路径与 SHA-256**：`{APPROVED_PLAN_RELATIVE_PATH}` (`{plan_sha256}`)",
        f"- **上游 J-A Run ID**：`{ja_run_id}`",
        f"- **上游 J-B Run ID**：`{jb_run_id}`",
        f"- **分类账本 V2 SHA-256**：`{ledger_sha256}`",
        "",
        "## 1. 时点、特征与分组定义",
        "",
        f"- 特征窗口：`[T0, T0 + {protocol.feature_window_ms}ms)`（含 `T0`，不含 `T0 + {protocol.feature_window_ms}ms`；同时记录成交笔数 `feature_trade_count` 与相邻成交最大时间间隔 `feature_max_intertrade_gap_ms`）",
        f"- 观察与假设延迟：`T_obs = T0 + {protocol.feature_window_ms}ms`，`T_decision = T_obs + {protocol.latency_ms}ms`",
        f"- 入场参考窗口：`[T_decision, T_decision + {protocol.entry_max_wait_ms}ms]` 首笔成交",
        f"- 终点与窗口：`T_end = entry.timestamp + {protocol.hold_horizon_ms}ms`，终点参考窗口 `[T_end - {protocol.endpoint_max_age_ms}ms, T_end]` 最后一笔成交（同时记录路径成交笔数 `path_trade_count` 与路径最大成交间隔 `max_intertrade_gap_ms`）",
        "- 分组规则：按各机制内 `complete` 样本的 `taker_buy_share` 样本中位数划分（`> median` 为 `high`，`<= median` 为 `low`；相同数值不拆分；样本中位数为事后描述边界，不是实时 PIT 交易信号）",
        "",
        "## 2. 总体样本守恒与公告簇统计",
        "",
        f"- 选入总 Child 数：`{len(sorted_children)}`（`pre_market` = `{pm_summary.n_universe_children}`，`standard` = `{std_summary.n_universe_children}`）",
        f"- 跨机制去重总公告簇（Distinct `parent_article_id`）数：`{len(all_distinct_parents)}`",
        f"- 涉及 UTC 日期数：`{len(date_counts)}`",
        "",
    ]
    md_lines.extend(_render_regime_section_md(pm_summary))
    md_lines.extend(_render_regime_section_md(std_summary))
    md_lines.extend(
        [
            "## 3. 未覆盖限制与安全声明",
            "",
            "- `AggTrades` 不含历史 L2 订单簿深度、撤单、排队位置与真实成交执行。",
            "- 所有价格响应（`terminal_return`、`long_mae`、`long_mfe`）均为未扣成本的毛价格变化，不是策略净收益或止损成交保证；负向多头收益不等于已验证的做空收益。",
            "- `RISK_LIVE_TRADING_ENABLED=False`；本报告仅供人工审阅，不授予任何下游消费、交易或部署权限。",
            "",
        ]
    )

    csv_bytes = csv_buf.getvalue().encode("utf-8")
    md_bytes = "\n".join(md_lines).encode("utf-8")

    out_res.parent.mkdir(parents=True, exist_ok=True)
    out_res.mkdir(exist_ok=False)
    csv_file = out_res / "child_rows.csv"
    md_file = out_res / "review_CN.md"
    csv_file.write_bytes(csv_bytes)
    md_file.write_bytes(md_bytes)
    return csv_file, md_file



