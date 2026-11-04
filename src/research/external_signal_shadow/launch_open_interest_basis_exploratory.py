"""Launch Open Interest and Basis Exploratory Research Core Module.

Implements calculations for:
1. OI change and opening grid control with strict time semantics and no-fallback rule.
2. Basis from mark and index klines with natural minute and cutoff matching.
3. Pre-decision baseline metrics over [T0, D).
4. Subsequent price response over [D, E] with [D, D+5s] entry and [E-1s, E] endpoint.

Governed by:
- docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md
- docs/plans/2026-11-01-launch-open-interest-basis-exploratory-implementation-plan_CN.md
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO, Dict, Generator, List, Optional, Sequence, Set, Tuple

from configs.stage1_5j_b_historical_aggtrades_launch_response import (
    EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
)
from src.research.external_signal_shadow.launch_taker_buy_share_residual_response import (
    AdmittedJAContext,
    TakerBuyShareResearchError,
    build_admitted_ja_context,
    open_verified_package_stream,
)
from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    validate_zip_archive_package,
)

OBSERVATION_OFFSET_MS = 1_500_000  # D = T0 + 25m
ENTRY_WINDOW_MS = 5_000  # [D, D + 5s]
PATH_HORIZON_MS = 900_000  # E = entry_time + 15m
EXTERNAL_SIGNAL_LAUNCH_OI_MAX_AGGTRADES_SEARCH_SPAN_MS = (
    OBSERVATION_OFFSET_MS + ENTRY_WINDOW_MS + PATH_HORIZON_MS
)  # 2,405,000 ms (40m05s)

# Scenario -> (info_offset_ms, pub_margin_ms)
OI_SCENARIO_CONFIGS: Dict[str, Tuple[int, int]] = {
    "A": (0, 300_000),        # info_offset=0m, pub_margin=5m -> total_margin=5m (300,000 ms)
    "B": (300_000, 300_000),  # info_offset=5m, pub_margin=5m -> total_margin=10m (600,000 ms), MAIN
    "C": (600_000, 300_000),  # info_offset=10m, pub_margin=5m -> total_margin=15m (900,000 ms)
}

APPROVED_DESIGN_PATH = "docs/designs/2026-11-01-launch-open-interest-basis-exploratory-design_CN.md"
APPROVED_DESIGN_SHA256 = "82dd58310d7f2377c23eac7606a2cf74ec038c9b96b84436dd6a5af2826aa00f"
APPROVED_DESIGN_DELTA_PATH = (
    "docs/designs/2026-11-02-launch-open-interest-scenario-assumptions-design-delta_CN.md"
)
APPROVED_DESIGN_DELTA_SHA256 = "7941e641437ad20f4aee96be4b3ff65e7f97503d5d3f8693fdce81c29db55b54"
APPROVED_PLAN_PATH = (
    "docs/plans/2026-11-02-launch-open-interest-scenario-assumptions-implementation-plan_CN.md"
)
APPROVED_PLAN_SHA256 = "256541023e83bbf063b78b0bd84259de73e3dd05268d0b1e924d38eabf2d53d1"

LEDGER_RELATIVE_PATH = "data/exports/stage1_5j_token_launch_classification_ledger_v2.csv"
LEDGER_SHA256 = "36e56f45728f1cd8e0f7d0ae4a45f982fdf85b9c3a08c407607029c8e21aa26b"
J_A_ROOT_RELATIVE_PATH = "data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261010T163500Z"
J_B_ROOT_RELATIVE_PATH = "data/external_signal_shadow/stage1_5j_b/historical_aggtrades_launch_response/stage1_5j_b_historical_aggtrades_launch_response_20261014T044500Z"

EXPECTED_LEDGER_COLUMNS = [
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


class LaunchOiResearchError(Exception):
    """Exception raised on admission, authorization, or contract failures."""

    pass


@dataclass(frozen=True)
class OiMetricRecord:
    create_time_ms: int
    symbol: str
    sum_open_interest: float
    information_time_ms: Optional[int] = None
    information_time_upper_bound_ms: Optional[int] = None
    unit: str = "base_coin"
    time_evidence_source: Optional[str] = None
    time_evidence_scope: Optional[str] = None
    time_evidence_basis: Optional[str] = None
    verified_information_time_ms: Optional[int] = None
    verified_available_time_ms: Optional[int] = None


@dataclass(frozen=True)
class KlineBar:
    open_time_ms: int
    close_time_ms: int
    close_price: float
    symbol: Optional[str] = None
    unit: Optional[str] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None


@dataclass(frozen=True)
class AggTradeRecord:
    transact_time_ms: int
    trade_id: int
    price: float
    quantity: float
    is_buyer_maker: bool


@dataclass(frozen=True)
class OiResult:
    status: str
    symbol: str
    d_ms: int
    margin_ms: int
    scenario_name: str = "B"
    info_offset_ms: int = 300_000
    pub_margin_ms: int = 300_000
    l0_ms: Optional[int] = None
    l1_ms: Optional[int] = None
    oi_l0: Optional[float] = None
    oi_l1: Optional[float] = None
    oi_change: Optional[float] = None
    age_ms: Optional[int] = None
    label_age_ms: Optional[int] = None
    assumed_info_time_l0_ms: Optional[int] = None
    assumed_info_time_l1_ms: Optional[int] = None
    assumed_avail_time_l0_ms: Optional[int] = None
    assumed_avail_time_l1_ms: Optional[int] = None
    assumed_avail_age_ms: Optional[int] = None
    information_time_ms: Optional[int] = None
    available_time_ms: Optional[int] = None
    real_pit_verified: bool = False
    pit_verification_status: str = "unverified_scenario_assumption"
    # Opening grid control fields
    grid_status: Optional[str] = None
    grid_l0_ms: Optional[int] = None
    grid_l1_ms: Optional[int] = None
    grid_oi_l0: Optional[float] = None
    grid_oi_l1: Optional[float] = None
    grid_oi_change: Optional[float] = None
    grid_t0_minus_l0_ms: Optional[int] = None
    grid_scheduled_minus_l0_ms: Optional[int] = None
    grid_coincides_with_main: Optional[bool] = None


@dataclass(frozen=True)
class BasisResult:
    status: str
    target_symbol: str
    mapped_index_symbol: Optional[str]
    bar_open_time_ms: Optional[int] = None
    bar_close_time_ms: Optional[int] = None
    mark_price: Optional[float] = None
    index_price: Optional[float] = None
    basis: Optional[float] = None
    age_ms: Optional[int] = None


@dataclass(frozen=True)
class BaselineMetrics:
    status: str
    trade_count: int
    price_change: Optional[float] = None
    total_notional: Optional[float] = None
    taker_buy_share: Optional[float] = None


@dataclass(frozen=True)
class PathResult:
    status: str
    entry_time_ms: Optional[int] = None
    entry_trade_id: Optional[int] = None
    entry_price: Optional[float] = None
    entry_delay_ms: Optional[int] = None
    endpoint_time_ms: Optional[int] = None
    endpoint_trade_id: Optional[int] = None
    endpoint_price: Optional[float] = None
    path_trade_count: int = 0
    terminal_return: Optional[float] = None
    long_mae: Optional[float] = None
    long_mfe: Optional[float] = None


def _has_verified_fact_conflict(
    r: OiMetricRecord,
    d_ms: int,
    info_offset_ms: int,
    total_margin_ms: int,
) -> bool:
    v_info = (
        r.verified_information_time_ms
        if r.verified_information_time_ms is not None
        else (
            r.information_time_upper_bound_ms
            if r.information_time_upper_bound_ms is not None
            else r.information_time_ms
        )
    )
    if v_info is not None and (v_info > r.create_time_ms + info_offset_ms or v_info > d_ms):
        return True
    v_avail = r.verified_available_time_ms
    if v_avail is not None and (v_avail > r.create_time_ms + total_margin_ms or v_avail > d_ms):
        return True
    return False


def calculate_oi_change(
    records: List[OiMetricRecord],
    symbol: str,
    t0_ms: int,
    d_ms: Optional[int] = None,
    margin_ms: int = 600_000,
    *,
    scenario_name: str = "B",
    info_offset_ms: Optional[int] = None,
    pub_margin_ms: Optional[int] = None,
    scheduled_launch_ms: Optional[int] = None,
) -> OiResult:
    """Calculates OI change under an explicit scenario assumption (A/B/C) with strict predecessor check and opening grid control.

    Invariants:
    - Fixed observation point D = T0 + 25m (1,500,000 ms) by default.
    - Under scenario S (info_offset_ms, pub_margin_ms, total_margin_ms = info_offset_ms + pub_margin_ms):
      assumed_information_time(T) = T + info_offset_ms
      assumed_available_time(T) = T + total_margin_ms
    - Selects latest L1 satisfying T0 <= L1 and assumed_available_time(L1) <= D.
    - Checks L0 = L1 - 300_000 ms. L0 must be >= T0, exist, and satisfy assumed_available_time(L0) <= D.
    - If L0 missing or L0 < T0: NO FALLBACK to earlier pair, marks missing.
    - If any verified time fact conflicts with the scenario assumption in [T0, D], halts scenario with 'verified_fact_conflict'.
    """
    actual_d_ms = (t0_ms + OBSERVATION_OFFSET_MS) if d_ms is None else d_ms
    if info_offset_ms is not None and pub_margin_ms is not None:
        eff_info_offset = info_offset_ms
        eff_pub_margin = pub_margin_ms
        eff_total_margin = eff_info_offset + eff_pub_margin
    elif scenario_name in OI_SCENARIO_CONFIGS and margin_ms == 600_000:
        eff_info_offset, eff_pub_margin = OI_SCENARIO_CONFIGS[scenario_name]
        eff_total_margin = eff_info_offset + eff_pub_margin
    else:
        eff_total_margin = margin_ms
        eff_pub_margin = min(300_000, eff_total_margin)
        eff_info_offset = max(0, eff_total_margin - eff_pub_margin)

    sym_records = [r for r in records if r.symbol == symbol]
    if not sym_records:
        return OiResult(
            status="no_records_for_symbol",
            symbol=symbol,
            d_ms=actual_d_ms,
            margin_ms=eff_total_margin,
            scenario_name=scenario_name,
            info_offset_ms=eff_info_offset,
            pub_margin_ms=eff_pub_margin,
            grid_status="no_records_for_symbol",
        )

    # 1. Check for duplicate timestamps in symbol records
    seen_times: Set[int] = set()
    for r in sym_records:
        if r.create_time_ms in seen_times:
            return OiResult(
                status="duplicate_timestamp",
                symbol=symbol,
                d_ms=actual_d_ms,
                margin_ms=eff_total_margin,
                scenario_name=scenario_name,
                info_offset_ms=eff_info_offset,
                pub_margin_ms=eff_pub_margin,
                grid_status="duplicate_timestamp",
            )
        seen_times.add(r.create_time_ms)

    # 2. Check verified fact conflict on records in [T0, D]
    for r in sym_records:
        if t0_ms <= r.create_time_ms <= actual_d_ms:
            if _has_verified_fact_conflict(r, actual_d_ms, eff_info_offset, eff_total_margin):
                return OiResult(
                    status="verified_fact_conflict",
                    symbol=symbol,
                    d_ms=actual_d_ms,
                    margin_ms=eff_total_margin,
                    scenario_name=scenario_name,
                    info_offset_ms=eff_info_offset,
                    pub_margin_ms=eff_pub_margin,
                    grid_status="verified_fact_conflict",
                )

    cutoff_ms = actual_d_ms - eff_total_margin
    by_time = {
        r.create_time_ms: r
        for r in sym_records
        if math.isfinite(r.sum_open_interest) and r.sum_open_interest > 0
    }

    candidate_l1 = [ts for ts in by_time if t0_ms <= ts <= cutoff_ms]

    main_status = "ok"
    l0_ms: Optional[int] = None
    l1_ms: Optional[int] = None
    oi_l0: Optional[float] = None
    oi_l1: Optional[float] = None
    oi_change: Optional[float] = None
    label_age_ms: Optional[int] = None
    assumed_info_l0: Optional[int] = None
    assumed_info_l1: Optional[int] = None
    assumed_avail_l0: Optional[int] = None
    assumed_avail_l1: Optional[int] = None
    assumed_avail_age: Optional[int] = None
    verified_info_l1: Optional[int] = None
    verified_avail_l1: Optional[int] = None

    if not candidate_l1:
        main_status = "no_records_in_window"
    else:
        l1_ms = max(candidate_l1)
        r1 = by_time[l1_ms]
        l0_ms = l1_ms - 300_000

        if l0_ms < t0_ms:
            main_status = "l0_before_t0"
        elif l0_ms not in by_time:
            main_status = "missing_predecessor"
        else:
            r0 = by_time[l0_ms]
            if not r0.unit or not r1.unit or r0.unit != r1.unit:
                main_status = "unit_mismatch"
            else:
                oi_l0 = r0.sum_open_interest
                oi_l1 = r1.sum_open_interest
                oi_change = oi_l1 / oi_l0 - 1.0
                label_age_ms = actual_d_ms - l1_ms
                assumed_info_l0 = l0_ms + eff_info_offset
                assumed_info_l1 = l1_ms + eff_info_offset
                assumed_avail_l0 = l0_ms + eff_total_margin
                assumed_avail_l1 = l1_ms + eff_total_margin
                assumed_avail_age = actual_d_ms - assumed_avail_l1
                verified_info_l1 = r1.verified_information_time_ms
                verified_avail_l1 = r1.verified_available_time_ms

    # Opening grid control calculation: L0 = floor_5m(T0), L1 = L0 + 300_000
    grid_status = "ok"
    grid_l0_ms: Optional[int] = None
    grid_l1_ms: Optional[int] = None
    grid_oi_l0: Optional[float] = None
    grid_oi_l1: Optional[float] = None
    grid_oi_change: Optional[float] = None

    target_grid_l0 = (t0_ms // 300_000) * 300_000
    target_grid_l1 = target_grid_l0 + 300_000
    grid_t0_minus_l0_ms = t0_ms - target_grid_l0
    grid_scheduled_minus_l0_ms = (
        (scheduled_launch_ms - target_grid_l0) if scheduled_launch_ms is not None else None
    )

    if target_grid_l1 > cutoff_ms:
        grid_status = "grid_l1_exceeds_cutoff"
    elif target_grid_l0 not in by_time or target_grid_l1 not in by_time:
        grid_status = "grid_records_missing"
    else:
        gr0 = by_time[target_grid_l0]
        gr1 = by_time[target_grid_l1]
        if _has_verified_fact_conflict(
            gr0, actual_d_ms, eff_info_offset, eff_total_margin
        ) or _has_verified_fact_conflict(
            gr1, actual_d_ms, eff_info_offset, eff_total_margin
        ):
            grid_status = "verified_fact_conflict"
        elif not gr0.unit or not gr1.unit or gr0.unit != gr1.unit:
            grid_status = "grid_unit_mismatch"
        else:
            grid_l0_ms = target_grid_l0
            grid_l1_ms = target_grid_l1
            grid_oi_l0 = gr0.sum_open_interest
            grid_oi_l1 = gr1.sum_open_interest
            grid_oi_change = grid_oi_l1 / grid_oi_l0 - 1.0

    grid_coincides = (
        main_status == "ok"
        and grid_status == "ok"
        and l0_ms == grid_l0_ms
        and l1_ms == grid_l1_ms
    )

    return OiResult(
        status=main_status,
        symbol=symbol,
        d_ms=actual_d_ms,
        margin_ms=eff_total_margin,
        scenario_name=scenario_name,
        info_offset_ms=eff_info_offset,
        pub_margin_ms=eff_pub_margin,
        l0_ms=l0_ms,
        l1_ms=l1_ms,
        oi_l0=oi_l0,
        oi_l1=oi_l1,
        oi_change=oi_change,
        age_ms=label_age_ms,
        label_age_ms=label_age_ms,
        assumed_info_time_l0_ms=assumed_info_l0,
        assumed_info_time_l1_ms=assumed_info_l1,
        assumed_avail_time_l0_ms=assumed_avail_l0,
        assumed_avail_time_l1_ms=assumed_avail_l1,
        assumed_avail_age_ms=assumed_avail_age,
        information_time_ms=verified_info_l1,
        available_time_ms=verified_avail_l1,
        real_pit_verified=False,
        pit_verification_status="unverified_scenario_assumption",
        grid_status=grid_status,
        grid_l0_ms=grid_l0_ms,
        grid_l1_ms=grid_l1_ms,
        grid_oi_l0=grid_oi_l0,
        grid_oi_l1=grid_oi_l1,
        grid_oi_change=grid_oi_change,
        grid_t0_minus_l0_ms=grid_t0_minus_l0_ms,
        grid_scheduled_minus_l0_ms=grid_scheduled_minus_l0_ms,
        grid_coincides_with_main=grid_coincides,
    )


def evaluate_oi_scenarios(
    records: List[OiMetricRecord],
    symbol: str,
    t0_ms: int,
    d_ms: Optional[int] = None,
    scheduled_launch_ms: Optional[int] = None,
) -> Dict[str, OiResult]:
    """Evaluates fixed Scenarios A (+5m), B (+10m, Main), and C (+15m) at D = T0 + 25m."""
    actual_d_ms = (t0_ms + OBSERVATION_OFFSET_MS) if d_ms is None else d_ms
    out: Dict[str, OiResult] = {}
    for scen_name, (info_off, pub_marg) in OI_SCENARIO_CONFIGS.items():
        out[scen_name] = calculate_oi_change(
            records=records,
            symbol=symbol,
            t0_ms=t0_ms,
            d_ms=actual_d_ms,
            margin_ms=info_off + pub_marg,
            scenario_name=scen_name,
            info_offset_ms=info_off,
            pub_margin_ms=pub_marg,
            scheduled_launch_ms=scheduled_launch_ms,
        )
    return out


def calculate_basis(
    mark_bars: List[KlineBar],
    index_bars: List[KlineBar],
    target_symbol: str,
    mapped_index_symbol: Optional[str],
    d_ms: int,
    cutoff_margin_ms: int = 60_000,
) -> BasisResult:
    """Calculates basis from mark and index klines for the latest eligible natural-minute 1m bar pair."""
    if not mark_bars:
        return BasisResult(
            status="mark_unavailable",
            target_symbol=target_symbol or "",
            mapped_index_symbol=mapped_index_symbol,
        )

    if not index_bars:
        return BasisResult(
            status="index_unavailable",
            target_symbol=target_symbol or "",
            mapped_index_symbol=mapped_index_symbol,
        )

    # 1. Product mapping validity check
    unverified_tags = {"", "UNVERIFIED", "UNKNOWN", "unverified", "unknown"}
    if (
        not target_symbol
        or target_symbol.strip() in unverified_tags
        or not mapped_index_symbol
        or mapped_index_symbol.strip() in unverified_tags
    ):
        return BasisResult(
            status="unverified_product_mapping",
            target_symbol=target_symbol or "",
            mapped_index_symbol=mapped_index_symbol,
        )

    # 2. Bar identity and unit presence verification
    for b in mark_bars:
        if not b.symbol or b.symbol != target_symbol or not b.unit:
            return BasisResult(
                status="unverified_product_mapping",
                target_symbol=target_symbol,
                mapped_index_symbol=mapped_index_symbol,
            )
    for b in index_bars:
        if not b.symbol or b.symbol != mapped_index_symbol or not b.unit:
            return BasisResult(
                status="unverified_product_mapping",
                target_symbol=target_symbol,
                mapped_index_symbol=mapped_index_symbol,
            )

    cutoff_ms = d_ms - cutoff_margin_ms
    mark_by_open = {
        b.open_time_ms: b
        for b in mark_bars
        if b.close_price > 0
        and b.open_time_ms % 60_000 == 0
        and b.open_time_ms < b.close_time_ms <= b.open_time_ms + 60_000
    }
    index_by_open = {
        b.open_time_ms: b
        for b in index_bars
        if b.close_price > 0
        and b.open_time_ms % 60_000 == 0
        and b.open_time_ms < b.close_time_ms <= b.open_time_ms + 60_000
    }

    # Find common natural-minute open times where close_time_ms <= cutoff_ms (D - 1m)
    eligible_open_times = []
    for open_t, m_bar in mark_by_open.items():
        if open_t in index_by_open:
            i_bar = index_by_open[open_t]
            if m_bar.close_time_ms == i_bar.close_time_ms and m_bar.close_time_ms <= cutoff_ms:
                eligible_open_times.append(open_t)

    if not eligible_open_times:
        return BasisResult(
            status="no_eligible_bar_pair",
            target_symbol=target_symbol,
            mapped_index_symbol=mapped_index_symbol,
        )

    # Select latest eligible bar pair
    best_open_t = max(eligible_open_times)
    m_best = mark_by_open[best_open_t]
    i_best = index_by_open[best_open_t]

    # Unit verification
    if not m_best.unit or not i_best.unit or m_best.unit != i_best.unit:
        return BasisResult(
            status="unit_mismatch",
            target_symbol=target_symbol,
            mapped_index_symbol=mapped_index_symbol,
            bar_open_time_ms=m_best.open_time_ms,
            bar_close_time_ms=m_best.close_time_ms,
            mark_price=m_best.close_price,
            index_price=i_best.close_price,
            basis=None,
        )

    basis_val = m_best.close_price / i_best.close_price - 1.0
    age_ms = d_ms - m_best.close_time_ms

    return BasisResult(
        status="ok",
        target_symbol=target_symbol,
        mapped_index_symbol=mapped_index_symbol,
        bar_open_time_ms=m_best.open_time_ms,
        bar_close_time_ms=m_best.close_time_ms,
        mark_price=m_best.close_price,
        index_price=i_best.close_price,
        basis=basis_val,
        age_ms=age_ms,
    )


def calculate_baseline(
    trades: List[AggTradeRecord],
    t0_ms: int,
    d_ms: int,
) -> BaselineMetrics:
    """Calculates price change, total notional, and taker buy share over [T0, D)."""
    # Strict filter: T0 <= transact_time_ms < D
    baseline_trades = [
        t for t in trades if t0_ms <= t.transact_time_ms < d_ms and t.price > 0 and t.quantity > 0
    ]
    if not baseline_trades:
        return BaselineMetrics(status="no_trades_in_baseline", trade_count=0)

    # Sort deterministically
    baseline_trades.sort(key=lambda t: (t.transact_time_ms, t.trade_id))

    trade_count = len(baseline_trades)
    first_price = baseline_trades[0].price
    last_price = baseline_trades[-1].price
    price_change = last_price / first_price - 1.0

    total_notional = sum(t.price * t.quantity for t in baseline_trades)
    taker_buy_notional = sum(t.price * t.quantity for t in baseline_trades if not t.is_buyer_maker)
    taker_buy_share = taker_buy_notional / total_notional if total_notional > 0 else 0.0

    return BaselineMetrics(
        status="ok",
        trade_count=trade_count,
        price_change=price_change,
        total_notional=total_notional,
        taker_buy_share=taker_buy_share,
    )


def calculate_path_response(
    trades: List[AggTradeRecord],
    d_ms: int,
    entry_window_ms: int = 5000,
    horizon_ms: int = 900_000,
) -> PathResult:
    """Calculates subsequent price path response over [D, E] with [D, D+5s] entry and [E-1s, E] endpoint."""
    valid_trades = [t for t in trades if t.price > 0 and t.quantity > 0]
    if not valid_trades:
        return PathResult(status="no_valid_trades")

    valid_trades.sort(key=lambda t: (t.transact_time_ms, t.trade_id))

    # 1. Entry trade in [D, D + entry_window_ms]
    entry_candidates = [
        t for t in valid_trades if d_ms <= t.transact_time_ms <= d_ms + entry_window_ms
    ]
    if not entry_candidates:
        return PathResult(status="missing_entry_trade")

    entry_trade = entry_candidates[0]
    entry_price = entry_trade.price
    entry_time = entry_trade.transact_time_ms
    entry_delay = entry_time - d_ms

    # 2. Endpoint trade in [E - 1000, E] where E = entry_time + horizon_ms
    e_ms = entry_time + horizon_ms
    endpoint_candidates = [t for t in valid_trades if (e_ms - 1000) <= t.transact_time_ms <= e_ms]
    if not endpoint_candidates:
        return PathResult(
            status="missing_endpoint_trade",
            entry_time_ms=entry_time,
            entry_trade_id=entry_trade.trade_id,
            entry_price=entry_price,
            entry_delay_ms=entry_delay,
        )

    endpoint_trade = endpoint_candidates[-1]
    endpoint_price = endpoint_trade.price

    # 3. Path trades from entry_trade to endpoint_trade (inclusive)
    path_trades = [
        t
        for t in valid_trades
        if (
            t.transact_time_ms > entry_time
            or (t.transact_time_ms == entry_time and t.trade_id >= entry_trade.trade_id)
        )
        and (
            t.transact_time_ms < endpoint_trade.transact_time_ms
            or (
                t.transact_time_ms == endpoint_trade.transact_time_ms
                and t.trade_id <= endpoint_trade.trade_id
            )
        )
    ]

    if not path_trades:
        return PathResult(
            status="empty_path",
            entry_time_ms=entry_time,
            entry_trade_id=entry_trade.trade_id,
            entry_price=entry_price,
            entry_delay_ms=entry_delay,
            endpoint_time_ms=endpoint_trade.transact_time_ms,
            endpoint_trade_id=endpoint_trade.trade_id,
            endpoint_price=endpoint_price,
        )

    min_p = min(t.price for t in path_trades)
    max_p = max(t.price for t in path_trades)

    terminal_return = endpoint_price / entry_price - 1.0
    long_mae = min(0.0, min_p / entry_price - 1.0)
    long_mfe = max(0.0, max_p / entry_price - 1.0)

    return PathResult(
        status="ok",
        entry_time_ms=entry_time,
        entry_trade_id=entry_trade.trade_id,
        entry_price=entry_price,
        entry_delay_ms=entry_delay,
        endpoint_time_ms=endpoint_trade.transact_time_ms,
        endpoint_trade_id=endpoint_trade.trade_id,
        endpoint_price=endpoint_price,
        path_trade_count=len(path_trades),
        terminal_return=terminal_return,
        long_mae=long_mae,
        long_mfe=long_mfe,
    )


@dataclass(frozen=True)
class DistributionStats:
    count: int
    mean: Optional[float] = None
    median: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    p25: Optional[float] = None
    p75: Optional[float] = None


def compute_distribution_stats(values: List[float]) -> DistributionStats:
    """Computes mean, median, min, max, and nearest-rank P25/P75."""
    valid_vals = [v for v in values if v is not None and not math.isnan(v)]
    if not valid_vals:
        return DistributionStats(count=0)

    sorted_vals = sorted(valid_vals)
    n = len(sorted_vals)
    mean_val = sum(sorted_vals) / n

    # Median (average of two middle if even)
    if n % 2 == 1:
        med_val = sorted_vals[n // 2]
    else:
        med_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    # Nearest-rank method: rank = ceil(p / 100 * n), index = rank - 1
    rank_25 = math.ceil(0.25 * n)
    p25_idx = max(0, min(n - 1, rank_25 - 1))
    p25_val = sorted_vals[p25_idx]

    rank_75 = math.ceil(0.75 * n)
    p75_idx = max(0, min(n - 1, rank_75 - 1))
    p75_val = sorted_vals[p75_idx]

    return DistributionStats(
        count=n,
        mean=mean_val,
        median=med_val,
        min_val=min_val,
        max_val=max_val,
        p25=p25_val,
        p75=p75_val,
    )


@dataclass(frozen=True)
class ChildEvaluation:
    parent_article_id: str
    symbol: str
    listing_regime: str
    is_complete: bool
    missing_reason: Optional[str] = None
    oi_change: Optional[float] = None
    terminal_return: Optional[float] = None
    long_mae: Optional[float] = None
    long_mfe: Optional[float] = None
    utc_date: Optional[str] = None
    basis: Optional[float] = None
    entry_price: Optional[float] = None
    entry_delay_ms: Optional[int] = None
    endpoint_price: Optional[float] = None
    path_status: Optional[str] = None
    oi_status: Optional[str] = None
    oi_l0_time_ms: Optional[int] = None
    oi_l1_time_ms: Optional[int] = None
    oi_l0: Optional[float] = None
    oi_l1: Optional[float] = None
    oi_age_ms: Optional[int] = None
    oi_assumed_info_l0_ms: Optional[int] = None
    oi_assumed_info_l1_ms: Optional[int] = None
    oi_assumed_avail_l0_ms: Optional[int] = None
    oi_assumed_avail_l1_ms: Optional[int] = None
    oi_assumed_avail_age_ms: Optional[int] = None
    # Scenario A (+5m = 300,000 ms)
    oi_a_status: Optional[str] = None
    oi_a_change: Optional[float] = None
    oi_a_l0_time_ms: Optional[int] = None
    oi_a_l1_time_ms: Optional[int] = None
    oi_a_l0: Optional[float] = None
    oi_a_l1: Optional[float] = None
    oi_a_age_ms: Optional[int] = None
    oi_a_assumed_info_l0_ms: Optional[int] = None
    oi_a_assumed_info_l1_ms: Optional[int] = None
    oi_a_assumed_avail_l0_ms: Optional[int] = None
    oi_a_assumed_avail_l1_ms: Optional[int] = None
    oi_a_assumed_avail_age_ms: Optional[int] = None
    # Scenario B (+10m = 600,000 ms, Main)
    oi_b_status: Optional[str] = None
    oi_b_change: Optional[float] = None
    oi_b_l0_time_ms: Optional[int] = None
    oi_b_l1_time_ms: Optional[int] = None
    oi_b_l0: Optional[float] = None
    oi_b_l1: Optional[float] = None
    oi_b_age_ms: Optional[int] = None
    oi_b_assumed_info_l0_ms: Optional[int] = None
    oi_b_assumed_info_l1_ms: Optional[int] = None
    oi_b_assumed_avail_l0_ms: Optional[int] = None
    oi_b_assumed_avail_l1_ms: Optional[int] = None
    oi_b_assumed_avail_age_ms: Optional[int] = None
    # Scenario C (+15m = 900,000 ms)
    oi_c_status: Optional[str] = None
    oi_c_change: Optional[float] = None
    oi_c_l0_time_ms: Optional[int] = None
    oi_c_l1_time_ms: Optional[int] = None
    oi_c_l0: Optional[float] = None
    oi_c_l1: Optional[float] = None
    oi_c_age_ms: Optional[int] = None
    oi_c_assumed_info_l0_ms: Optional[int] = None
    oi_c_assumed_info_l1_ms: Optional[int] = None
    oi_c_assumed_avail_l0_ms: Optional[int] = None
    oi_c_assumed_avail_l1_ms: Optional[int] = None
    oi_c_assumed_avail_age_ms: Optional[int] = None
    grid_status: Optional[str] = None
    grid_l0_time_ms: Optional[int] = None
    grid_l1_time_ms: Optional[int] = None
    grid_t0_minus_l0_ms: Optional[int] = None
    grid_scheduled_minus_l0_ms: Optional[int] = None
    grid_oi_l0: Optional[float] = None
    grid_oi_l1: Optional[float] = None
    grid_oi_change: Optional[float] = None
    grid_coincides_with_main: Optional[bool] = None
    grid_a_status: Optional[str] = None
    grid_a_oi_change: Optional[float] = None
    grid_a_l0_time_ms: Optional[int] = None
    grid_a_l1_time_ms: Optional[int] = None
    grid_a_oi_l0: Optional[float] = None
    grid_a_oi_l1: Optional[float] = None
    grid_a_coincides: Optional[bool] = None
    grid_b_status: Optional[str] = None
    grid_b_oi_change: Optional[float] = None
    grid_b_l0_time_ms: Optional[int] = None
    grid_b_l1_time_ms: Optional[int] = None
    grid_b_oi_l0: Optional[float] = None
    grid_b_oi_l1: Optional[float] = None
    grid_b_coincides: Optional[bool] = None
    grid_c_status: Optional[str] = None
    grid_c_oi_change: Optional[float] = None
    grid_c_l0_time_ms: Optional[int] = None
    grid_c_l1_time_ms: Optional[int] = None
    grid_c_oi_l0: Optional[float] = None
    grid_c_oi_l1: Optional[float] = None
    grid_c_coincides: Optional[bool] = None
    basis_status: Optional[str] = None
    basis_age_ms: Optional[int] = None
    baseline_price_change: Optional[float] = None
    baseline_total_notional: Optional[float] = None
    baseline_taker_buy_share: Optional[float] = None
    oi_time_evidence_source: Optional[str] = None
    oi_time_evidence_scope: Optional[str] = None
    oi_time_evidence_basis: Optional[str] = None
    pit_verification_status: str = "unverified_scenario_assumption"
    interpretation_status: str = "historical_scenario_only"


@dataclass(frozen=True)
class ParentEvaluation:
    parent_article_id: str
    listing_regime: str
    is_complete: bool
    missing_reason: Optional[str] = None
    child_count: int = 1
    oi_change: Optional[float] = None
    terminal_return: Optional[float] = None
    long_mae: Optional[float] = None
    long_mfe: Optional[float] = None
    utc_date: Optional[str] = None


@dataclass(frozen=True)
class GroupSummary:
    group_name: str
    count: int
    oi_stats: DistributionStats
    terminal_stats: DistributionStats
    mae_stats: DistributionStats
    mfe_stats: DistributionStats


@dataclass(frozen=True)
class JackknifeItem:
    omitted_parent_id: str
    remaining_count: int
    high_count: int
    low_count: int
    diff_mean_terminal_return: Optional[float]


@dataclass(frozen=True)
class JackknifeResult:
    base_median_oi: Optional[float]
    base_high_count: int
    base_low_count: int
    base_diff: Optional[float]
    jackknife_items: List[JackknifeItem]
    diff_min: Optional[float]
    diff_max: Optional[float]


@dataclass(frozen=True)
class ScenarioRegimeSummary:
    scenario_name: str
    margin_ms: int
    regime: str
    child_universe_count: int
    child_oi_pair_count: int
    child_complete_count: int
    child_missing_count: int
    child_missing_reasons: Dict[str, int]
    child_median_oi: Optional[float]
    child_high_group: Optional[GroupSummary]
    child_low_group: Optional[GroupSummary]
    child_terminal_diff_mean: Optional[float]
    parent_universe_count: int
    parent_complete_count: int
    parent_missing_count: int
    parent_missing_reasons: Dict[str, int]
    parent_median_oi: Optional[float]
    parent_high_group: Optional[GroupSummary]
    parent_low_group: Optional[GroupSummary]
    parent_terminal_diff_mean: Optional[float]


@dataclass(frozen=True)
class GridControlRegimeSummary:
    regime: str
    child_universe_count: int
    child_grid_valid_count: int
    child_grid_missing_count: int
    child_grid_missing_reasons: Dict[str, int]
    coincides_with_main_count: int
    parent_universe_count: int
    parent_grid_valid_count: int
    parent_grid_missing_count: int
    grid_oi_change_stats: DistributionStats


@dataclass(frozen=True)
class RegimeGroupingSummary:
    regime: str
    child_universe_count: int
    child_complete_count: int
    child_missing_count: int
    child_missing_reasons: Dict[str, int]
    parent_universe_count: int
    parent_complete_count: int
    parent_missing_count: int
    parent_missing_reasons: Dict[str, int]
    complete_parents: List[ParentEvaluation]
    child_median_oi: Optional[float] = None
    child_high_group: Optional[GroupSummary] = None
    child_low_group: Optional[GroupSummary] = None
    child_terminal_diff_mean: Optional[float] = None
    parent_median_oi: Optional[float] = None
    parent_high_group: Optional[GroupSummary] = None
    parent_low_group: Optional[GroupSummary] = None
    parent_terminal_diff_mean: Optional[float] = None
    parent_jackknife: Optional[JackknifeResult] = None
    utc_date_parent_counts: Optional[Dict[str, int]] = None
    universe_parent_utc_date_counts: Optional[Dict[str, int]] = None
    complete_parent_utc_date_counts: Optional[Dict[str, int]] = None
    basis_complete_count: int = 0
    basis_missing_count: int = 0
    basis_stats: Optional[DistributionStats] = None
    basis_missing_reasons: Optional[Dict[str, int]] = None
    baseline_complete_count: int = 0
    baseline_price_change_stats: Optional[DistributionStats] = None
    baseline_notional_stats: Optional[DistributionStats] = None
    baseline_tbs_stats: Optional[DistributionStats] = None
    oi_age_stats: Optional[DistributionStats] = None
    basis_age_stats: Optional[DistributionStats] = None


@dataclass(frozen=True)
class ScenarioOverlapSummary:
    regime: str
    child_complete_counts: Dict[str, int]
    child_overlap_ab: int
    child_overlap_bc: int
    child_overlap_abc: int
    child_diff_a_minus_b: int
    child_diff_b_minus_c: int
    parent_complete_counts: Dict[str, int]
    parent_overlap_ab: int
    parent_overlap_bc: int
    parent_overlap_abc: int
    parent_diff_a_minus_b: int
    parent_diff_b_minus_c: int


@dataclass(frozen=True)
class AggregateGroupingResult:
    child_universe_count: int
    child_complete_count: int
    child_missing_count: int
    parent_universe_count: int
    parent_complete_count: int
    parent_missing_count: int
    distinct_parent_article_count: int
    complete_parents: List[ParentEvaluation]
    child_high_group: Optional[GroupSummary] = None
    child_low_group: Optional[GroupSummary] = None
    parent_high_group: Optional[GroupSummary] = None
    parent_low_group: Optional[GroupSummary] = None
    parent_jackknife: Optional[JackknifeResult] = None
    regime_summaries: Optional[Dict[str, RegimeGroupingSummary]] = None
    scenario_summaries: Optional[Dict[str, Dict[str, ScenarioRegimeSummary]]] = None
    scenario_overlaps: Optional[Dict[str, ScenarioOverlapSummary]] = None
    grid_summaries: Optional[Dict[str, GridControlRegimeSummary]] = None
    grid_scenario_summaries: Optional[Dict[str, Dict[str, GridControlRegimeSummary]]] = None
    consumed_inputs: Optional[List[Dict[str, Any]]] = None
    interpretation_status: str = "historical_scenario_only"
    pit_verification_status: str = "unverified_scenario_assumption"
    conclusion_status: str = "evidence_insufficient"


def _median_of_floats(values: Sequence[float]) -> float:
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 == 1 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _build_group_summary(
    group_name: str, items: List[Tuple[float, float, float, float]]
) -> GroupSummary:
    """Builds GroupSummary from items of (oi_change, terminal_return, long_mae, long_mfe)."""
    return GroupSummary(
        group_name=group_name,
        count=len(items),
        oi_stats=compute_distribution_stats([it[0] for it in items]),
        terminal_stats=compute_distribution_stats([it[1] for it in items]),
        mae_stats=compute_distribution_stats([it[2] for it in items]),
        mfe_stats=compute_distribution_stats([it[3] for it in items]),
    )


def _split_high_low_groups(
    items: List[Tuple[float, float, float, float]]
) -> Tuple[Optional[float], Optional[GroupSummary], Optional[GroupSummary], Optional[float]]:
    if not items:
        return None, None, None, None
    med_oi = _median_of_floats([it[0] for it in items])
    high_items = [it for it in items if it[0] > med_oi]
    low_items = [it for it in items if it[0] <= med_oi]
    high_g = _build_group_summary("high", high_items)
    low_g = _build_group_summary("low", low_items)
    diff_mean: Optional[float] = None
    if high_g.count > 0 and low_g.count > 0:
        if high_g.terminal_stats.mean is not None and low_g.terminal_stats.mean is not None:
            diff_mean = high_g.terminal_stats.mean - low_g.terminal_stats.mean
    return med_oi, high_g, low_g, diff_mean


def perform_parent_jackknife(parents: List[ParentEvaluation]) -> JackknifeResult:
    """Performs leave-one-parent-out jackknife sensitivity test on complete parents within a regime."""
    complete_parents = [
        p
        for p in parents
        if p.is_complete and p.oi_change is not None and p.terminal_return is not None
    ]
    if not complete_parents:
        return JackknifeResult(
            base_median_oi=None,
            base_high_count=0,
            base_low_count=0,
            base_diff=None,
            jackknife_items=[],
            diff_min=None,
            diff_max=None,
        )

    base_med_oi = _median_of_floats([p.oi_change for p in complete_parents if p.oi_change is not None])
    base_high = [p for p in complete_parents if p.oi_change is not None and p.oi_change > base_med_oi]
    base_low = [p for p in complete_parents if p.oi_change is not None and p.oi_change <= base_med_oi]

    base_diff: Optional[float] = None
    if base_high and base_low:
        high_mean = sum(p.terminal_return for p in base_high if p.terminal_return is not None) / len(base_high)
        low_mean = sum(p.terminal_return for p in base_low if p.terminal_return is not None) / len(base_low)
        base_diff = high_mean - low_mean

    items: List[JackknifeItem] = []
    diff_vals: List[float] = []

    for idx, omitted in enumerate(complete_parents):
        subset = [p for i, p in enumerate(complete_parents) if i != idx]
        if not subset:
            items.append(
                JackknifeItem(
                    omitted_parent_id=omitted.parent_article_id,
                    remaining_count=0,
                    high_count=0,
                    low_count=0,
                    diff_mean_terminal_return=None,
                )
            )
            continue

        sub_med_oi = _median_of_floats([p.oi_change for p in subset if p.oi_change is not None])
        sub_high = [p for p in subset if p.oi_change is not None and p.oi_change > sub_med_oi]
        sub_low = [p for p in subset if p.oi_change is not None and p.oi_change <= sub_med_oi]

        sub_diff: Optional[float] = None
        if sub_high and sub_low:
            sub_h_mean = sum(p.terminal_return for p in sub_high if p.terminal_return is not None) / len(sub_high)
            sub_l_mean = sum(p.terminal_return for p in sub_low if p.terminal_return is not None) / len(sub_low)
            sub_diff = sub_h_mean - sub_l_mean
            diff_vals.append(sub_diff)

        items.append(
            JackknifeItem(
                omitted_parent_id=omitted.parent_article_id,
                remaining_count=len(subset),
                high_count=len(sub_high),
                low_count=len(sub_low),
                diff_mean_terminal_return=sub_diff,
            )
        )

    return JackknifeResult(
        base_median_oi=base_med_oi,
        base_high_count=len(base_high),
        base_low_count=len(base_low),
        base_diff=base_diff,
        jackknife_items=items,
        diff_min=min(diff_vals) if diff_vals else None,
        diff_max=max(diff_vals) if diff_vals else None,
    )


def _resolve_parent_utc_date(children: Sequence[ChildEvaluation]) -> str:
    """Resolves the UTC date for a parent across all its children:
    - If all known child dates are identical, returns that unique date (e.g. '2026-05-01').
    - If no known child dates exist, returns 'unknown'.
    - If multiple distinct dates exist across children, returns 'multi_date_conflict:<date1>,<date2>...'.
    """
    distinct = sorted({c.utc_date.strip() for c in children if c.utc_date and c.utc_date.strip()})
    if not distinct:
        return "unknown"
    if len(distinct) == 1:
        return distinct[0]
    return f"multi_date_conflict:{','.join(distinct)}"


def _compute_regime_summary(regime: str, reg_children: List[ChildEvaluation]) -> RegimeGroupingSummary:
    c_univ = len(reg_children)
    comp_c = [
        c
        for c in reg_children
        if c.is_complete and c.oi_change is not None and c.terminal_return is not None
    ]
    c_comp = len(comp_c)
    c_miss = c_univ - c_comp

    c_miss_reasons: Dict[str, int] = {}
    for c in reg_children:
        if not (c.is_complete and c.oi_change is not None and c.terminal_return is not None):
            r = c.missing_reason or "incomplete"
            c_miss_reasons[r] = (c_miss_reasons[r] if r in c_miss_reasons else 0) + 1

    c_items = [
        (
            c.oi_change,
            c.terminal_return,
            c.long_mae if c.long_mae is not None else 0.0,
            c.long_mfe if c.long_mfe is not None else 0.0,
        )
        for c in comp_c
        if c.oi_change is not None and c.terminal_return is not None
    ]
    c_med, c_high, c_low, c_diff = _split_high_low_groups(c_items)

    p_map: Dict[str, List[ChildEvaluation]] = {}
    for c in reg_children:
        if c.parent_article_id not in p_map:
            p_map[c.parent_article_id] = []
        p_map[c.parent_article_id].append(c)

    p_univ = len(p_map)
    comp_p: List[ParentEvaluation] = []
    p_miss = 0
    p_miss_reasons: Dict[str, int] = {}
    universe_utc_counts: Dict[str, int] = {}
    complete_utc_counts: Dict[str, int] = {}

    for p_id in sorted(p_map.keys()):
        p_children = p_map[p_id]
        u_date = _resolve_parent_utc_date(p_children)
        universe_utc_counts[u_date] = (universe_utc_counts[u_date] if u_date in universe_utc_counts else 0) + 1
        if all(
            c.is_complete and c.oi_change is not None and c.terminal_return is not None
            for c in p_children
        ):
            c_ois = [c.oi_change for c in p_children if c.oi_change is not None]
            c_rets = [c.terminal_return for c in p_children if c.terminal_return is not None]
            c_maes = [c.long_mae if c.long_mae is not None else 0.0 for c in p_children]
            c_mfes = [c.long_mfe if c.long_mfe is not None else 0.0 for c in p_children]
            comp_p.append(
                ParentEvaluation(
                    parent_article_id=p_id,
                    listing_regime=regime,
                    is_complete=True,
                    child_count=len(p_children),
                    oi_change=_median_of_floats(c_ois),
                    terminal_return=_median_of_floats(c_rets),
                    long_mae=_median_of_floats(c_maes),
                    long_mfe=_median_of_floats(c_mfes),
                    utc_date=u_date,
                )
            )
            complete_utc_counts[u_date] = (complete_utc_counts[u_date] if u_date in complete_utc_counts else 0) + 1
        else:
            p_miss += 1
            first_bad = next(
                (
                    c.missing_reason or "incomplete"
                    for c in p_children
                    if not (c.is_complete and c.oi_change is not None and c.terminal_return is not None)
                ),
                "incomplete",
            )
            p_miss_reasons[first_bad] = (
                p_miss_reasons[first_bad] if first_bad in p_miss_reasons else 0
            ) + 1

    p_items = [
        (
            p.oi_change,
            p.terminal_return,
            p.long_mae if p.long_mae is not None else 0.0,
            p.long_mfe if p.long_mfe is not None else 0.0,
        )
        for p in comp_p
        if p.oi_change is not None and p.terminal_return is not None
    ]
    p_med, p_high, p_low, p_diff = _split_high_low_groups(p_items)
    jk = perform_parent_jackknife(comp_p) if comp_p else None

    basis_vals = [c.basis for c in reg_children if c.basis is not None]
    basis_miss_reasons: Dict[str, int] = {}
    for c in reg_children:
        if c.basis is None:
            br = c.basis_status or "missing_basis"
            basis_miss_reasons[br] = (basis_miss_reasons[br] if br in basis_miss_reasons else 0) + 1

    base_pc = [c.baseline_price_change for c in reg_children if c.baseline_price_change is not None]
    base_not = [c.baseline_total_notional for c in reg_children if c.baseline_total_notional is not None]
    base_tbs = [c.baseline_taker_buy_share for c in reg_children if c.baseline_taker_buy_share is not None]
    oi_ages = [float(c.oi_age_ms) for c in reg_children if c.oi_age_ms is not None]
    basis_ages = [float(c.basis_age_ms) for c in reg_children if c.basis_age_ms is not None]

    return RegimeGroupingSummary(
        regime=regime,
        child_universe_count=c_univ,
        child_complete_count=c_comp,
        child_missing_count=c_miss,
        child_missing_reasons=c_miss_reasons,
        parent_universe_count=p_univ,
        parent_complete_count=len(comp_p),
        parent_missing_count=p_miss,
        parent_missing_reasons=p_miss_reasons,
        complete_parents=comp_p,
        child_median_oi=c_med,
        child_high_group=c_high,
        child_low_group=c_low,
        child_terminal_diff_mean=c_diff,
        parent_median_oi=p_med,
        parent_high_group=p_high,
        parent_low_group=p_low,
        parent_terminal_diff_mean=p_diff,
        parent_jackknife=jk,
        utc_date_parent_counts=complete_utc_counts,
        universe_parent_utc_date_counts=universe_utc_counts,
        complete_parent_utc_date_counts=complete_utc_counts,
        basis_complete_count=len(basis_vals),
        basis_missing_count=c_univ - len(basis_vals),
        basis_stats=compute_distribution_stats(basis_vals),
        basis_missing_reasons=basis_miss_reasons,
        baseline_complete_count=len(base_pc),
        baseline_price_change_stats=compute_distribution_stats(base_pc),
        baseline_notional_stats=compute_distribution_stats(base_not),
        baseline_tbs_stats=compute_distribution_stats(base_tbs),
        oi_age_stats=compute_distribution_stats(oi_ages),
        basis_age_stats=compute_distribution_stats(basis_ages),
    )


def _extract_child_scenario_oi(
    c: ChildEvaluation, scenario_name: str
) -> Tuple[str, Optional[float]]:
    if scenario_name in ("A", "5m"):
        if c.oi_a_status is not None:
            return c.oi_a_status, c.oi_a_change
    elif scenario_name == "C":
        if c.oi_c_status is not None:
            return c.oi_c_status, c.oi_c_change
    else:
        # Scenario B (Main default)
        if c.oi_b_status is not None:
            return c.oi_b_status, c.oi_b_change
    st = c.oi_status or (
        "ok" if (c.is_complete and c.oi_change is not None) else (c.missing_reason or "missing")
    )
    return st, c.oi_change


def _is_child_path_ok(c: ChildEvaluation) -> bool:
    if c.path_status is not None:
        return c.path_status == "ok" and c.terminal_return is not None
    return c.is_complete and c.terminal_return is not None


def _compute_scenario_regime_summary(
    scenario_name: str,
    margin_ms: int,
    regime: str,
    reg_children: List[ChildEvaluation],
) -> ScenarioRegimeSummary:
    c_univ = len(reg_children)
    oi_pair_count = 0
    comp_items: List[Tuple[ChildEvaluation, float]] = []
    c_miss_reasons: Dict[str, int] = {}

    for c in reg_children:
        oi_st, oi_val = _extract_child_scenario_oi(c, scenario_name)
        path_ok = _is_child_path_ok(c)
        if oi_st == "ok" and oi_val is not None:
            oi_pair_count += 1
            if path_ok and c.terminal_return is not None:
                comp_items.append((c, oi_val))
            else:
                pr = c.path_status or c.missing_reason or "missing_path"
                c_miss_reasons[pr] = (c_miss_reasons[pr] if pr in c_miss_reasons else 0) + 1
        else:
            c_miss_reasons[oi_st] = (c_miss_reasons[oi_st] if oi_st in c_miss_reasons else 0) + 1

    c_tuples = [
        (
            oi_v,
            c.terminal_return if c.terminal_return is not None else 0.0,
            c.long_mae if c.long_mae is not None else 0.0,
            c.long_mfe if c.long_mfe is not None else 0.0,
        )
        for c, oi_v in comp_items
    ]
    c_med, c_high, c_low, c_diff = _split_high_low_groups(c_tuples)

    p_map: Dict[str, List[ChildEvaluation]] = {}
    for c in reg_children:
        if c.parent_article_id not in p_map:
            p_map[c.parent_article_id] = []
        p_map[c.parent_article_id].append(c)

    comp_oi_by_child = {(c.parent_article_id, c.symbol): oi_v for c, oi_v in comp_items}
    p_tuples: List[Tuple[float, float, float, float]] = []
    p_miss = 0
    p_miss_reasons: Dict[str, int] = {}

    for p_id in sorted(p_map.keys()):
        p_children = p_map[p_id]
        if all((c.parent_article_id, c.symbol) in comp_oi_by_child for c in p_children):
            p_ois = [comp_oi_by_child[(c.parent_article_id, c.symbol)] for c in p_children]
            p_rets = [c.terminal_return for c in p_children if c.terminal_return is not None]
            p_maes = [c.long_mae if c.long_mae is not None else 0.0 for c in p_children]
            p_mfes = [c.long_mfe if c.long_mfe is not None else 0.0 for c in p_children]
            p_tuples.append(
                (
                    _median_of_floats(p_ois),
                    _median_of_floats(p_rets),
                    _median_of_floats(p_maes),
                    _median_of_floats(p_mfes),
                )
            )
        else:
            p_miss += 1
            bad_reason = "incomplete_child"
            for c in p_children:
                if (c.parent_article_id, c.symbol) not in comp_oi_by_child:
                    oi_st, _ = _extract_child_scenario_oi(c, scenario_name)
                    bad_reason = (
                        oi_st
                        if oi_st != "ok"
                        else (c.path_status or c.missing_reason or "missing_path")
                    )
                    break
            p_miss_reasons[bad_reason] = (
                p_miss_reasons[bad_reason] if bad_reason in p_miss_reasons else 0
            ) + 1

    p_med, p_high, p_low, p_diff = _split_high_low_groups(p_tuples)

    return ScenarioRegimeSummary(
        scenario_name=scenario_name,
        margin_ms=margin_ms,
        regime=regime,
        child_universe_count=c_univ,
        child_oi_pair_count=oi_pair_count,
        child_complete_count=len(comp_items),
        child_missing_count=c_univ - len(comp_items),
        child_missing_reasons=c_miss_reasons,
        child_median_oi=c_med,
        child_high_group=c_high,
        child_low_group=c_low,
        child_terminal_diff_mean=c_diff,
        parent_universe_count=len(p_map),
        parent_complete_count=len(p_tuples),
        parent_missing_count=p_miss,
        parent_missing_reasons=p_miss_reasons,
        parent_median_oi=p_med,
        parent_high_group=p_high,
        parent_low_group=p_low,
        parent_terminal_diff_mean=p_diff,
    )


def _compute_scenario_overlap_summary(
    regime: str, reg_children: List[ChildEvaluation]
) -> ScenarioOverlapSummary:
    p_map: Dict[str, List[ChildEvaluation]] = {}
    for c in reg_children:
        if c.parent_article_id not in p_map:
            p_map[c.parent_article_id] = []
        p_map[c.parent_article_id].append(c)

    child_sets: Dict[str, Set[Tuple[str, str]]] = {"A": set(), "B": set(), "C": set()}
    parent_sets: Dict[str, Set[str]] = {"A": set(), "B": set(), "C": set()}

    for scen_name in ("A", "B", "C"):
        for c in reg_children:
            oi_st, oi_val = _extract_child_scenario_oi(c, scen_name)
            if oi_st == "ok" and oi_val is not None and _is_child_path_ok(c):
                child_sets[scen_name].add((c.parent_article_id, c.symbol))
        for p_id, p_children in p_map.items():
            if all((c.parent_article_id, c.symbol) in child_sets[scen_name] for c in p_children):
                parent_sets[scen_name].add(p_id)

    ca, cb, cc = child_sets["A"], child_sets["B"], child_sets["C"]
    pa, pb, pc = parent_sets["A"], parent_sets["B"], parent_sets["C"]

    return ScenarioOverlapSummary(
        regime=regime,
        child_complete_counts={"A": len(ca), "B": len(cb), "C": len(cc)},
        child_overlap_ab=len(ca & cb),
        child_overlap_bc=len(cb & cc),
        child_overlap_abc=len(ca & cb & cc),
        child_diff_a_minus_b=len(ca - cb),
        child_diff_b_minus_c=len(cb - cc),
        parent_complete_counts={"A": len(pa), "B": len(pb), "C": len(pc)},
        parent_overlap_ab=len(pa & pb),
        parent_overlap_bc=len(pb & pc),
        parent_overlap_abc=len(pa & pb & pc),
        parent_diff_a_minus_b=len(pa - pb),
        parent_diff_b_minus_c=len(pb - pc),
    )


def _compute_grid_regime_summary(
    regime: str, reg_children: List[ChildEvaluation], scenario_name: str = "B"
) -> GridControlRegimeSummary:
    c_univ = len(reg_children)
    valid_vals: List[float] = []
    miss_reasons: Dict[str, int] = {}
    coincide_cnt = 0

    def _get_grid_item(c: ChildEvaluation) -> Tuple[Optional[str], Optional[float], Optional[bool]]:
        if scenario_name == "A":
            st = c.grid_a_status if c.grid_a_status is not None else c.grid_status
            chg = c.grid_a_oi_change if c.grid_a_status is not None else c.grid_oi_change
            coincides = c.grid_a_coincides if c.grid_a_status is not None else c.grid_coincides_with_main
        elif scenario_name == "C":
            st = c.grid_c_status if c.grid_c_status is not None else c.grid_status
            chg = c.grid_c_oi_change if c.grid_c_status is not None else c.grid_oi_change
            coincides = c.grid_c_coincides if c.grid_c_status is not None else c.grid_coincides_with_main
        else:
            st = c.grid_b_status if c.grid_b_status is not None else c.grid_status
            chg = c.grid_b_oi_change if c.grid_b_status is not None else c.grid_oi_change
            coincides = c.grid_b_coincides if c.grid_b_status is not None else c.grid_coincides_with_main
        return st, chg, coincides

    for c in reg_children:
        st, chg, coincides = _get_grid_item(c)
        if st == "ok" and chg is not None:
            valid_vals.append(chg)
            if coincides is True:
                coincide_cnt += 1
        else:
            gr = st or "grid_not_available"
            miss_reasons[gr] = (miss_reasons[gr] if gr in miss_reasons else 0) + 1

    p_map: Dict[str, List[ChildEvaluation]] = {}
    for c in reg_children:
        if c.parent_article_id not in p_map:
            p_map[c.parent_article_id] = []
        p_map[c.parent_article_id].append(c)

    p_valid = sum(
        1
        for p_children in p_map.values()
        if all(_get_grid_item(c)[0] == "ok" and _get_grid_item(c)[1] is not None for c in p_children)
    )

    return GridControlRegimeSummary(
        regime=regime,
        child_universe_count=c_univ,
        child_grid_valid_count=len(valid_vals),
        child_grid_missing_count=c_univ - len(valid_vals),
        child_grid_missing_reasons=miss_reasons,
        coincides_with_main_count=coincide_cnt,
        parent_universe_count=len(p_map),
        parent_grid_valid_count=p_valid,
        parent_grid_missing_count=len(p_map) - p_valid,
        grid_oi_change_stats=compute_distribution_stats(valid_vals),
    )


def aggregate_and_group(
    children: List[ChildEvaluation],
    consumed_inputs: Optional[List[Dict[str, Any]]] = None,
) -> AggregateGroupingResult:
    """Aggregates children into parents and computes independent per-regime (pre_market, standard) median groupings across Scenarios A, B (Main), and C, scenario overlap summaries, and opening grid control summaries."""
    regimes_ordered = ["pre_market", "standard"]
    for c in children:
        if c.listing_regime not in regimes_ordered:
            regimes_ordered.append(c.listing_regime)

    regime_summaries: Dict[str, RegimeGroupingSummary] = {}
    all_complete_parents: List[ParentEvaluation] = []
    for reg in regimes_ordered:
        reg_c = [c for c in children if c.listing_regime == reg]
        r_sum = _compute_regime_summary(reg, reg_c)
        regime_summaries[reg] = r_sum
        all_complete_parents.extend(r_sum.complete_parents)

    scenario_summaries: Dict[str, Dict[str, ScenarioRegimeSummary]] = {}
    scenario_overlaps: Dict[str, ScenarioOverlapSummary] = {}
    for reg in regimes_ordered:
        scenario_summaries[reg] = {}
        reg_c = [c for c in children if c.listing_regime == reg]
        for scen_name, (info_off, pub_marg) in OI_SCENARIO_CONFIGS.items():
            s_sum = _compute_scenario_regime_summary(
                scen_name, info_off + pub_marg, reg, reg_c
            )
            scenario_summaries[reg][scen_name] = s_sum
        scenario_overlaps[reg] = _compute_scenario_overlap_summary(reg, reg_c)

    grid_summaries: Dict[str, GridControlRegimeSummary] = {}
    grid_scenario_summaries: Dict[str, Dict[str, GridControlRegimeSummary]] = {}
    for reg in regimes_ordered:
        reg_c = [c for c in children if c.listing_regime == reg]
        grid_summaries[reg] = _compute_grid_regime_summary(reg, reg_c, scenario_name="B")
        grid_scenario_summaries[reg] = {
            "A": _compute_grid_regime_summary(reg, reg_c, scenario_name="A"),
            "B": _compute_grid_regime_summary(reg, reg_c, scenario_name="B"),
            "C": _compute_grid_regime_summary(reg, reg_c, scenario_name="C"),
        }

    child_universe_count = len(children)
    child_complete_count = sum(r.child_complete_count for r in regime_summaries.values())
    child_missing_count = child_universe_count - child_complete_count
    parent_universe_count = sum(r.parent_universe_count for r in regime_summaries.values())
    parent_complete_count = len(all_complete_parents)
    parent_missing_count = parent_universe_count - parent_complete_count
    distinct_parent_article_count = len({c.parent_article_id for c in children})

    active_regimes = [r for r in regime_summaries.values() if r.child_complete_count > 0]
    single_reg = active_regimes[0] if len(active_regimes) == 1 else None

    return AggregateGroupingResult(
        child_universe_count=child_universe_count,
        child_complete_count=child_complete_count,
        child_missing_count=child_missing_count,
        parent_universe_count=parent_universe_count,
        parent_complete_count=parent_complete_count,
        parent_missing_count=parent_missing_count,
        distinct_parent_article_count=distinct_parent_article_count,
        complete_parents=all_complete_parents,
        child_high_group=single_reg.child_high_group if single_reg else None,
        child_low_group=single_reg.child_low_group if single_reg else None,
        parent_high_group=single_reg.parent_high_group if single_reg else None,
        parent_low_group=single_reg.parent_low_group if single_reg else None,
        parent_jackknife=single_reg.parent_jackknife if single_reg else None,
        regime_summaries=regime_summaries,
        scenario_summaries=scenario_summaries,
        scenario_overlaps=scenario_overlaps,
        grid_summaries=grid_summaries,
        grid_scenario_summaries=grid_scenario_summaries,
        consumed_inputs=consumed_inputs,
        interpretation_status="historical_scenario_only",
        pit_verification_status="unverified_scenario_assumption",
        conclusion_status="evidence_insufficient",
    )


def _compute_file_sha256_chunked(
    path: Path,
    chunk_size: int = EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
) -> str:
    """Computes SHA-256 hex digest in bounded chunks without reading whole file into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def stream_aggtrades_csv_lines(
    stream: BinaryIO,
    chunk_size: int = EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
    max_line_bytes: int = EXTERNAL_SIGNAL_STAGE1_5J_B_STREAM_CHUNK_BYTES,
) -> Generator[str, None, None]:
    """Yields decoded CSV lines from a binary stream with bounded chunking and physical line length protection."""
    buffer = bytearray()
    while True:
        while b"\n" in buffer:
            idx = buffer.index(b"\n")
            line_len_with_nl = idx + 1
            if line_len_with_nl > max_line_bytes:
                raise LaunchOiResearchError(
                    f"physical_line_length_exceeded: line of {line_len_with_nl} bytes > {max_line_bytes}"
                )
            line_bytes = buffer[:idx]
            del buffer[: idx + 1]
            yield line_bytes.decode("utf-8", errors="strict").rstrip("\r")

        if len(buffer) > max_line_bytes:
            raise LaunchOiResearchError(
                f"physical_line_length_exceeded: line without newline reached {len(buffer)} bytes > {max_line_bytes}"
            )

        remaining_budget = (max_line_bytes + 1) - len(buffer)
        read_size = min(chunk_size, remaining_budget)
        if read_size <= 0:
            raise LaunchOiResearchError(
                f"physical_line_length_exceeded: line without newline reached {len(buffer)} bytes > {max_line_bytes}"
            )

        chunk = stream.read(read_size)
        if not chunk:
            break
        buffer.extend(chunk)

    while b"\n" in buffer:
        idx = buffer.index(b"\n")
        line_len_with_nl = idx + 1
        if line_len_with_nl > max_line_bytes:
            raise LaunchOiResearchError(
                f"physical_line_length_exceeded: line of {line_len_with_nl} bytes > {max_line_bytes}"
            )
        line_bytes = buffer[:idx]
        del buffer[: idx + 1]
        yield line_bytes.decode("utf-8", errors="strict").rstrip("\r")

    if buffer:
        if len(buffer) > max_line_bytes:
            raise LaunchOiResearchError(
                f"physical_line_length_exceeded: trailing line of {len(buffer)} bytes > {max_line_bytes}"
            )
        yield buffer.decode("utf-8", errors="strict").rstrip("\r")


def verify_safe_new_output_dir(
    output_dir: Path,
    protected_paths: Optional[Sequence[Path]] = None,
    project_root: Optional[Path] = None,
) -> None:
    """Verifies that output_dir does not exist and does not collide with or reside inside protected roots."""
    if output_dir.exists() or output_dir.is_symlink():
        raise LaunchOiResearchError(f"output_dir_already_exists: {output_dir}")

    all_protected: List[Path] = []
    if project_root is not None:
        all_protected.append(project_root)
        all_protected.append(project_root / J_A_ROOT_RELATIVE_PATH)
        all_protected.append(project_root / J_B_ROOT_RELATIVE_PATH)
    if protected_paths:
        all_protected.extend(protected_paths)

    curr = output_dir
    while not curr.exists() and curr != curr.parent:
        curr = curr.parent

    resolved_ancestor = curr.resolve()

    for prot in all_protected:
        if not prot.exists():
            continue
        prot_res = prot.resolve()
        if resolved_ancestor == prot_res or prot_res in resolved_ancestor.parents:
            raise LaunchOiResearchError(
                f"output_dir_inside_protected_root: {output_dir} resolves into {prot_res}"
            )
        if resolved_ancestor in prot_res.parents:
            raise LaunchOiResearchError(
                f"protected_root_inside_output_ancestor: {prot_res} inside {resolved_ancestor}"
            )


def verify_single_run_authorization(
    auth_file: Path,
    expected_output_dir: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Validates single-run explicit authorization JSON structure and bound identities."""
    if not auth_file.is_file():
        raise LaunchOiResearchError(f"auth_file_not_found: {auth_file}")

    try:
        data = json.loads(auth_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LaunchOiResearchError(f"auth_file_invalid_json: {exc}")

    # Check required identity bounds
    if data.get("design_relative_path") != APPROVED_DESIGN_PATH:
        raise LaunchOiResearchError(
            f"auth_design_path_mismatch: {data.get('design_relative_path')}"
        )
    if data.get("design_sha256") != APPROVED_DESIGN_SHA256:
        raise LaunchOiResearchError(f"auth_design_sha_mismatch: {data.get('design_sha256')}")

    if data.get("design_delta_relative_path") != APPROVED_DESIGN_DELTA_PATH:
        raise LaunchOiResearchError(
            f"auth_design_delta_path_mismatch: {data.get('design_delta_relative_path')}"
        )
    if data.get("design_delta_sha256") != APPROVED_DESIGN_DELTA_SHA256:
        raise LaunchOiResearchError(
            f"auth_design_delta_sha_mismatch: {data.get('design_delta_sha256')}"
        )

    if data.get("plan_relative_path") != APPROVED_PLAN_PATH:
        raise LaunchOiResearchError(f"auth_plan_path_mismatch: {data.get('plan_relative_path')}")
    if data.get("plan_sha256") != APPROVED_PLAN_SHA256:
        raise LaunchOiResearchError(f"auth_plan_sha_mismatch: {data.get('plan_sha256')}")

    if data.get("ja_root_relative_path") != J_A_ROOT_RELATIVE_PATH:
        raise LaunchOiResearchError(f"auth_ja_root_mismatch: {data.get('ja_root_relative_path')}")
    if data.get("jb_root_relative_path") != J_B_ROOT_RELATIVE_PATH:
        raise LaunchOiResearchError(f"auth_jb_root_mismatch: {data.get('jb_root_relative_path')}")

    if data.get("ledger_relative_path") != LEDGER_RELATIVE_PATH:
        raise LaunchOiResearchError(
            f"auth_ledger_path_mismatch: {data.get('ledger_relative_path')}"
        )
    if data.get("ledger_sha256") != LEDGER_SHA256:
        raise LaunchOiResearchError(f"auth_ledger_sha_mismatch: {data.get('ledger_sha256')}")

    if data.get("operation") != "offline_research_once":
        raise LaunchOiResearchError(f"auth_operation_unauthorized: {data.get('operation')}")

    # Check output_dir
    claimed_out = data.get("output_dir")
    if not claimed_out or not isinstance(claimed_out, str):
        raise LaunchOiResearchError(f"auth_output_dir_invalid: {claimed_out}")
    if expected_output_dir is not None and Path(claimed_out) != expected_output_dir:
        raise LaunchOiResearchError(
            f"auth_output_dir_mismatch: {claimed_out} vs {expected_output_dir}"
        )

    # Check false flags
    required_false = [
        "network_allowed",
        "paper_trading_allowed",
        "live_trading_allowed",
        "execution_allowed",
        "signal_allowed",
    ]
    for flag in required_false:
        if data.get(flag) is not False:
            raise LaunchOiResearchError(f"auth_flag_must_be_false: {flag}={data.get(flag)}")

    # Check authorized sources paths and identity binding (no project_root escape, no symlinks, bound manifest or file SHAs)
    if "oi_source_relative_path" in data and data["oi_source_relative_path"] is not None:
        rel = data["oi_source_relative_path"]
        if not isinstance(rel, str) or not rel.strip():
            raise LaunchOiResearchError(f"auth_source_path_invalid: oi_source_relative_path={rel}")
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise LaunchOiResearchError(
                f"auth_source_path_escapes_project_root: oi_source_relative_path={rel}"
            )
        if project_root is not None:
            full_path = (project_root / rel).resolve()
            proj_root_resolved = project_root.resolve()
            if not full_path.is_relative_to(proj_root_resolved):
                raise LaunchOiResearchError(
                    f"auth_source_path_escapes_project_root: oi_source_relative_path={rel}"
                )
            check_path = project_root / rel
            if check_path.is_symlink():
                raise LaunchOiResearchError(
                    f"auth_source_path_symlink_forbidden: {check_path}"
                )
            for parent in check_path.parents:
                if parent == project_root or parent == proj_root_resolved:
                    break
                if parent.is_symlink():
                    raise LaunchOiResearchError(
                        f"auth_source_path_symlink_forbidden: {parent}"
                    )

        auth_oi_manifest_sha = data.get("oi_source_manifest_sha256") or data.get("oi_manifest_sha256")
        auth_input_files = data.get("authorized_input_files") or data.get("authorized_files")
        if not auth_oi_manifest_sha and not auth_input_files:
            raise LaunchOiResearchError(
                "auth_missing_oi_source_identity_binding: either oi_source_manifest_sha256 or authorized_input_files must be provided when oi_source_relative_path is set"
            )
        if auth_oi_manifest_sha and project_root is not None:
            manifest_file = project_root / rel / "oi_provenance_manifest.json"
            if not manifest_file.is_file():
                raise LaunchOiResearchError(f"auth_oi_manifest_file_missing: {manifest_file}")
            actual_manifest_sha = _compute_file_sha256_chunked(manifest_file)
            if actual_manifest_sha != auth_oi_manifest_sha:
                raise LaunchOiResearchError(
                    f"auth_oi_manifest_sha_mismatch: expected {auth_oi_manifest_sha}, got {actual_manifest_sha}"
                )

    if "kline_source_relative_path" in data and data["kline_source_relative_path"] is not None:
        rel = data["kline_source_relative_path"]
        if not isinstance(rel, str) or not rel.strip():
            raise LaunchOiResearchError(f"auth_source_path_invalid: kline_source_relative_path={rel}")
        rel_path = Path(rel)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            raise LaunchOiResearchError(
                f"auth_source_path_escapes_project_root: kline_source_relative_path={rel}"
            )
        if project_root is not None:
            full_path = (project_root / rel).resolve()
            proj_root_resolved = project_root.resolve()
            if not full_path.is_relative_to(proj_root_resolved):
                raise LaunchOiResearchError(
                    f"auth_source_path_escapes_project_root: kline_source_relative_path={rel}"
                )
            check_path = project_root / rel
            if check_path.is_symlink():
                raise LaunchOiResearchError(
                    f"auth_source_path_symlink_forbidden: {check_path}"
                )
            for parent in check_path.parents:
                if parent == project_root or parent == proj_root_resolved:
                    break
                if parent.is_symlink():
                    raise LaunchOiResearchError(
                        f"auth_source_path_symlink_forbidden: {parent}"
                    )

        auth_k_manifest_sha = data.get("kline_source_manifest_sha256") or data.get("kline_manifest_sha256")
        auth_input_files = data.get("authorized_input_files") or data.get("authorized_files")
        if not auth_k_manifest_sha and not auth_input_files:
            raise LaunchOiResearchError(
                "auth_missing_kline_source_identity_binding: either kline_source_manifest_sha256 or authorized_input_files must be provided when kline_source_relative_path is set"
            )
        if auth_k_manifest_sha and project_root is not None:
            manifest_file = project_root / rel / "kline_mapping_manifest.json"
            if not manifest_file.is_file():
                raise LaunchOiResearchError(f"auth_kline_manifest_file_missing: {manifest_file}")
            actual_manifest_sha = _compute_file_sha256_chunked(manifest_file)
            if actual_manifest_sha != auth_k_manifest_sha:
                raise LaunchOiResearchError(
                    f"auth_kline_manifest_sha_mismatch: expected {auth_k_manifest_sha}, got {actual_manifest_sha}"
                )

    return data


def verify_v2_ledger_and_select_universe(ledger_path: Path) -> List[Dict[str, str]]:
    """Verifies SHA-256 of v2 ledger, checks 12 columns, and selects crypto confirmed standard/pre_market universe."""
    if not ledger_path.is_file():
        raise LaunchOiResearchError(f"ledger_file_not_found: {ledger_path}")

    actual_sha = _compute_file_sha256_chunked(ledger_path)
    if actual_sha != LEDGER_SHA256:
        raise LaunchOiResearchError(
            f"ledger_sha256_mismatch: expected {LEDGER_SHA256}, got {actual_sha}"
        )

    with open(ledger_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise LaunchOiResearchError("ledger_is_empty")

        if header != EXPECTED_LEDGER_COLUMNS:
            raise LaunchOiResearchError(
                f"ledger_columns_mismatch: expected {EXPECTED_LEDGER_COLUMNS}, got {header}"
            )

        rows: List[Dict[str, str]] = []
        for line in reader:
            if not line:
                continue
            row_dict = dict(zip(header, line))
            rows.append(row_dict)

    # Filter universe: asset_class == 'crypto', classification_status == 'confirmed', listing_regime in ('pre_market', 'standard')
    selected: List[Dict[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    for r in rows:
        if r.get("asset_class") == "crypto" and r.get("classification_status") == "confirmed":
            regime = r.get("listing_regime")
            if regime in ("pre_market", "standard"):
                key = (r["parent_article_id"], r["symbol"])
                if key not in seen:
                    seen.add(key)
                    selected.append(r)

    selected.sort(key=lambda x: (x["parent_article_id"], x["symbol"]))
    return selected


def write_exploratory_outputs(
    output_dir: Path,
    child_evaluations: List[ChildEvaluation],
    aggregate_result: AggregateGroupingResult,
    design_sha256: str = APPROVED_DESIGN_SHA256,
    design_delta_sha256: str = APPROVED_DESIGN_DELTA_SHA256,
    plan_sha256: str = APPROVED_PLAN_SHA256,
    ledger_sha256: str = LEDGER_SHA256,
    project_root: Optional[Path] = None,
    consumed_inputs: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Path, Path]:
    """Exclusively creates output_dir and writes child_rows.csv and review_CN.md."""
    import shutil

    prot_roots = (
        [project_root / J_A_ROOT_RELATIVE_PATH, project_root / J_B_ROOT_RELATIVE_PATH]
        if project_root is not None
        else None
    )
    verify_safe_new_output_dir(output_dir, protected_paths=prot_roots)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_dir.mkdir(parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise LaunchOiResearchError(f"output_dir_already_exists: {output_dir}") from exc

    child_csv_path = output_dir / "child_rows.csv"
    review_md_path = output_dir / "review_CN.md"

    try:
        # 1. Write child_rows.csv
        csv_header = [
            "parent_article_id",
            "symbol",
            "listing_regime",
            "utc_date",
            "is_complete",
            "missing_reason",
            "path_status",
            "oi_status",
            "oi_change",
            "terminal_return",
            "long_mae",
            "long_mfe",
            "basis",
            "entry_price",
            "entry_delay_ms",
            "endpoint_price",
            "oi_l0_time_ms",
            "oi_l1_time_ms",
            "oi_l0",
            "oi_l1",
            "oi_age_ms",
            "oi_assumed_info_l0_ms",
            "oi_assumed_info_l1_ms",
            "oi_assumed_avail_l0_ms",
            "oi_assumed_avail_l1_ms",
            "oi_assumed_avail_age_ms",
            "oi_a_status",
            "oi_a_change",
            "oi_a_l0_time_ms",
            "oi_a_l1_time_ms",
            "oi_a_l0",
            "oi_a_l1",
            "oi_a_age_ms",
            "oi_a_assumed_info_l0_ms",
            "oi_a_assumed_info_l1_ms",
            "oi_a_assumed_avail_l0_ms",
            "oi_a_assumed_avail_l1_ms",
            "oi_a_assumed_avail_age_ms",
            "oi_b_status",
            "oi_b_change",
            "oi_b_l0_time_ms",
            "oi_b_l1_time_ms",
            "oi_b_l0",
            "oi_b_l1",
            "oi_b_age_ms",
            "oi_b_assumed_info_l0_ms",
            "oi_b_assumed_info_l1_ms",
            "oi_b_assumed_avail_l0_ms",
            "oi_b_assumed_avail_l1_ms",
            "oi_b_assumed_avail_age_ms",
            "oi_c_status",
            "oi_c_change",
            "oi_c_l0_time_ms",
            "oi_c_l1_time_ms",
            "oi_c_l0",
            "oi_c_l1",
            "oi_c_age_ms",
            "oi_c_assumed_info_l0_ms",
            "oi_c_assumed_info_l1_ms",
            "oi_c_assumed_avail_l0_ms",
            "oi_c_assumed_avail_l1_ms",
            "oi_c_assumed_avail_age_ms",
            "grid_status",
            "grid_oi_change",
            "grid_l0_time_ms",
            "grid_l1_time_ms",
            "grid_l0",
            "grid_l1",
            "grid_t0_minus_l0_ms",
            "grid_scheduled_minus_l0_ms",
            "grid_coincides_with_main",
            "grid_a_status",
            "grid_a_oi_change",
            "grid_a_l0_time_ms",
            "grid_a_l1_time_ms",
            "grid_a_oi_l0",
            "grid_a_oi_l1",
            "grid_a_coincides",
            "grid_b_status",
            "grid_b_oi_change",
            "grid_b_l0_time_ms",
            "grid_b_l1_time_ms",
            "grid_b_oi_l0",
            "grid_b_oi_l1",
            "grid_b_coincides",
            "grid_c_status",
            "grid_c_oi_change",
            "grid_c_l0_time_ms",
            "grid_c_l1_time_ms",
            "grid_c_oi_l0",
            "grid_c_oi_l1",
            "grid_c_coincides",
            "basis_status",
            "basis_age_ms",
            "baseline_price_change",
            "baseline_total_notional",
            "baseline_taker_buy_share",
            "pit_verification_status",
            "interpretation_status",
        ]
        with open(child_csv_path, "x", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            for c in sorted(child_evaluations, key=lambda x: (x.parent_article_id, x.symbol)):
                b_status = c.oi_b_status if c.oi_b_status is not None else c.oi_status
                b_chg = c.oi_b_change if c.oi_b_change is not None else c.oi_change
                b_l0_t = c.oi_b_l0_time_ms if c.oi_b_l0_time_ms is not None else c.oi_l0_time_ms
                b_l1_t = c.oi_b_l1_time_ms if c.oi_b_l1_time_ms is not None else c.oi_l1_time_ms
                b_l0 = c.oi_b_l0 if c.oi_b_l0 is not None else c.oi_l0
                b_l1 = c.oi_b_l1 if c.oi_b_l1 is not None else c.oi_l1
                b_age = c.oi_b_age_ms if c.oi_b_age_ms is not None else c.oi_age_ms
                writer.writerow(
                    [
                        c.parent_article_id,
                        c.symbol,
                        c.listing_regime,
                        c.utc_date or "",
                        "true" if c.is_complete else "false",
                        c.missing_reason or "",
                        c.path_status or "",
                        b_status or "",
                        f"{b_chg:.8f}" if b_chg is not None else "",
                        f"{c.terminal_return:.8f}" if c.terminal_return is not None else "",
                        f"{c.long_mae:.8f}" if c.long_mae is not None else "",
                        f"{c.long_mfe:.8f}" if c.long_mfe is not None else "",
                        f"{c.basis:.8f}" if c.basis is not None else "",
                        f"{c.entry_price:.8f}" if c.entry_price is not None else "",
                        str(c.entry_delay_ms) if c.entry_delay_ms is not None else "",
                        f"{c.endpoint_price:.8f}" if c.endpoint_price is not None else "",
                        str(b_l0_t) if b_l0_t is not None else "",
                        str(b_l1_t) if b_l1_t is not None else "",
                        f"{b_l0:.8f}" if b_l0 is not None else "",
                        f"{b_l1:.8f}" if b_l1 is not None else "",
                        str(b_age) if b_age is not None else "",
                        str(c.oi_assumed_info_l0_ms) if c.oi_assumed_info_l0_ms is not None else "",
                        str(c.oi_assumed_info_l1_ms) if c.oi_assumed_info_l1_ms is not None else "",
                        str(c.oi_assumed_avail_l0_ms) if c.oi_assumed_avail_l0_ms is not None else "",
                        str(c.oi_assumed_avail_l1_ms) if c.oi_assumed_avail_l1_ms is not None else "",
                        str(c.oi_assumed_avail_age_ms) if c.oi_assumed_avail_age_ms is not None else "",
                        c.oi_a_status or "",
                        f"{c.oi_a_change:.8f}" if c.oi_a_change is not None else "",
                        str(c.oi_a_l0_time_ms) if c.oi_a_l0_time_ms is not None else "",
                        str(c.oi_a_l1_time_ms) if c.oi_a_l1_time_ms is not None else "",
                        f"{c.oi_a_l0:.8f}" if c.oi_a_l0 is not None else "",
                        f"{c.oi_a_l1:.8f}" if c.oi_a_l1 is not None else "",
                        str(c.oi_a_age_ms) if c.oi_a_age_ms is not None else "",
                        str(c.oi_a_assumed_info_l0_ms) if c.oi_a_assumed_info_l0_ms is not None else "",
                        str(c.oi_a_assumed_info_l1_ms) if c.oi_a_assumed_info_l1_ms is not None else "",
                        str(c.oi_a_assumed_avail_l0_ms) if c.oi_a_assumed_avail_l0_ms is not None else "",
                        str(c.oi_a_assumed_avail_l1_ms) if c.oi_a_assumed_avail_l1_ms is not None else "",
                        str(c.oi_a_assumed_avail_age_ms) if c.oi_a_assumed_avail_age_ms is not None else "",
                        b_status or "",
                        f"{b_chg:.8f}" if b_chg is not None else "",
                        str(b_l0_t) if b_l0_t is not None else "",
                        str(b_l1_t) if b_l1_t is not None else "",
                        f"{b_l0:.8f}" if b_l0 is not None else "",
                        f"{b_l1:.8f}" if b_l1 is not None else "",
                        str(b_age) if b_age is not None else "",
                        str(c.oi_b_assumed_info_l0_ms) if c.oi_b_assumed_info_l0_ms is not None else "",
                        str(c.oi_b_assumed_info_l1_ms) if c.oi_b_assumed_info_l1_ms is not None else "",
                        str(c.oi_b_assumed_avail_l0_ms) if c.oi_b_assumed_avail_l0_ms is not None else "",
                        str(c.oi_b_assumed_avail_l1_ms) if c.oi_b_assumed_avail_l1_ms is not None else "",
                        str(c.oi_b_assumed_avail_age_ms) if c.oi_b_assumed_avail_age_ms is not None else "",
                        c.oi_c_status or "",
                        f"{c.oi_c_change:.8f}" if c.oi_c_change is not None else "",
                        str(c.oi_c_l0_time_ms) if c.oi_c_l0_time_ms is not None else "",
                        str(c.oi_c_l1_time_ms) if c.oi_c_l1_time_ms is not None else "",
                        f"{c.oi_c_l0:.8f}" if c.oi_c_l0 is not None else "",
                        f"{c.oi_c_l1:.8f}" if c.oi_c_l1 is not None else "",
                        str(c.oi_c_age_ms) if c.oi_c_age_ms is not None else "",
                        str(c.oi_c_assumed_info_l0_ms) if c.oi_c_assumed_info_l0_ms is not None else "",
                        str(c.oi_c_assumed_info_l1_ms) if c.oi_c_assumed_info_l1_ms is not None else "",
                        str(c.oi_c_assumed_avail_l0_ms) if c.oi_c_assumed_avail_l0_ms is not None else "",
                        str(c.oi_c_assumed_avail_l1_ms) if c.oi_c_assumed_avail_l1_ms is not None else "",
                        str(c.oi_c_assumed_avail_age_ms) if c.oi_c_assumed_avail_age_ms is not None else "",
                        c.grid_status or "",
                        f"{c.grid_oi_change:.8f}" if c.grid_oi_change is not None else "",
                        str(c.grid_l0_time_ms) if c.grid_l0_time_ms is not None else "",
                        str(c.grid_l1_time_ms) if c.grid_l1_time_ms is not None else "",
                        f"{c.grid_oi_l0:.8f}" if c.grid_oi_l0 is not None else "",
                        f"{c.grid_oi_l1:.8f}" if c.grid_oi_l1 is not None else "",
                        str(c.grid_t0_minus_l0_ms) if c.grid_t0_minus_l0_ms is not None else "",
                        str(c.grid_scheduled_minus_l0_ms) if c.grid_scheduled_minus_l0_ms is not None else "",
                        (
                            "true"
                            if c.grid_coincides_with_main is True
                            else ("false" if c.grid_coincides_with_main is False else "")
                        ),
                        c.grid_a_status or "",
                        f"{c.grid_a_oi_change:.8f}" if c.grid_a_oi_change is not None else "",
                        str(c.grid_a_l0_time_ms) if c.grid_a_l0_time_ms is not None else "",
                        str(c.grid_a_l1_time_ms) if c.grid_a_l1_time_ms is not None else "",
                        f"{c.grid_a_oi_l0:.8f}" if c.grid_a_oi_l0 is not None else "",
                        f"{c.grid_a_oi_l1:.8f}" if c.grid_a_oi_l1 is not None else "",
                        (
                            "true"
                            if c.grid_a_coincides is True
                            else ("false" if c.grid_a_coincides is False else "")
                        ),
                        c.grid_b_status or "",
                        f"{c.grid_b_oi_change:.8f}" if c.grid_b_oi_change is not None else "",
                        str(c.grid_b_l0_time_ms) if c.grid_b_l0_time_ms is not None else "",
                        str(c.grid_b_l1_time_ms) if c.grid_b_l1_time_ms is not None else "",
                        f"{c.grid_b_oi_l0:.8f}" if c.grid_b_oi_l0 is not None else "",
                        f"{c.grid_b_oi_l1:.8f}" if c.grid_b_oi_l1 is not None else "",
                        (
                            "true"
                            if c.grid_b_coincides is True
                            else ("false" if c.grid_b_coincides is False else "")
                        ),
                        c.grid_c_status or "",
                        f"{c.grid_c_oi_change:.8f}" if c.grid_c_oi_change is not None else "",
                        str(c.grid_c_l0_time_ms) if c.grid_c_l0_time_ms is not None else "",
                        str(c.grid_c_l1_time_ms) if c.grid_c_l1_time_ms is not None else "",
                        f"{c.grid_c_oi_l0:.8f}" if c.grid_c_oi_l0 is not None else "",
                        f"{c.grid_c_oi_l1:.8f}" if c.grid_c_oi_l1 is not None else "",
                        (
                            "true"
                            if c.grid_c_coincides is True
                            else ("false" if c.grid_c_coincides is False else "")
                        ),
                        c.basis_status or "",
                        str(c.basis_age_ms) if c.basis_age_ms is not None else "",
                        f"{c.baseline_price_change:.8f}"
                        if c.baseline_price_change is not None
                        else "",
                        f"{c.baseline_total_notional:.8f}"
                        if c.baseline_total_notional is not None
                        else "",
                        f"{c.baseline_taker_buy_share:.8f}"
                        if c.baseline_taker_buy_share is not None
                        else "",
                        c.pit_verification_status,
                        c.interpretation_status,
                    ]
                )

        # 2. Collect consumed inputs for review_CN.md Section 7
        if consumed_inputs is None and aggregate_result.consumed_inputs is not None:
            consumed_inputs = aggregate_result.consumed_inputs
        c_inputs = list(consumed_inputs) if consumed_inputs else []

        # 3. Write review_CN.md
        res = aggregate_result
        lines = [
            "# 新币上线持仓量（OI）与基差探索性研究报告（时间假设情景协议）",
            "",
            "## 1. 权威身份、假设声明与方法论边界",
            "",
            f"- **Parent Design SHA-256**: `{design_sha256}`",
            f"- **Design Delta SHA-256**: `{design_delta_sha256}`",
            f"- **Plan SHA-256**: `{plan_sha256}`",
            f"- **Ledger SHA-256**: `{ledger_sha256}`",
            "- **解释级别（Interpretation Status）**: `historical_scenario_only`",
            "- **PIT 验证状态（PIT Verification Status）**: `unverified_scenario_assumption` (`real_pit_verified=false`)",
            "- **固定观察时点**: `D = T0 + 25m` (`1,500,000 ms`)",
            "- **情景假设定义**:",
            "  - `Scenario A`（5m 标签余量）：假定 `assumed_info_time = L`, `assumed_avail_time = L + 5m`，要求 `L1 <= D - 5m`",
            "  - `Scenario B`（10m 主情景）：假定 `assumed_info_time = L + 5m`, `assumed_avail_time = L + 10m`，要求 `L1 <= D - 10m`",
            "  - `Scenario C`（15m 保守情景）：假定 `assumed_info_time = L + 10m`, `assumed_avail_time = L + 15m`，要求 `L1 <= D - 15m`",
            "- **研究性质**: 离线探索性情景对照（exploratory），假设余量并非已证实的交易所发布延迟或真实 PIT 时间证据，无任何交易或信号权限。",
            "- **结论状态**: `evidence_insufficient` / `no_alpha_claim` / `historical_scenario_only`",
            "",
            "## 2. 样本守恒与分母覆盖（Scenario B 主情景总览）",
            "",
            f"- **Child Universe 候选总数**: {res.child_universe_count}",
            f"- **Child 完整样本数（Scenario B）**: {res.child_complete_count}",
            f"- **Child 缺失样本数（Scenario B）**: {res.child_missing_count}",
            f"- **Parent Universe 候选总数（按机制合计）**: {res.parent_universe_count}",
            f"- **Parent 完整样本数（Scenario B 按机制合计）**: {res.parent_complete_count}",
            f"- **Parent 缺失样本数（Scenario B 按机制合计）**: {res.parent_missing_count}",
            f"- **跨机制去重后独立公告 Parent 篇数**: {res.distinct_parent_article_count}",
            "",
        ]

        def _format_stats(name: str, s: Optional[DistributionStats]) -> str:
            if s is None or s.count == 0:
                return f"{name}: count=0"
            m_val = f"{s.mean:.6f}" if s.mean is not None else "null"
            med_val = f"{s.median:.6f}" if s.median is not None else "null"
            min_s = f"{s.min_val:.6f}" if s.min_val is not None else "null"
            max_s = f"{s.max_val:.6f}" if s.max_val is not None else "null"
            p25_s = f"{s.p25:.6f}" if s.p25 is not None else "null"
            p75_s = f"{s.p75:.6f}" if s.p75 is not None else "null"
            return (
                f"{name}: count={s.count}, mean={m_val}, median={med_val}, "
                f"min={min_s}, max={max_s}, P25={p25_s}, P75={p75_s}"
            )

        lines.append("## 3. 按上市机制独立分组与逐 Parent 剔除（Scenario B 主情景：`pre_market` vs `standard`）")
        lines.append("")

        reg_map = res.regime_summaries or {}
        for reg in ("pre_market", "standard"):
            reg_sum = reg_map.get(reg)
            lines.append(f"### 3.{1 if reg == 'pre_market' else 2} 机制：`{reg}`")
            lines.append("")
            if reg_sum is None:
                lines.append("- 无该机制样本记录")
                lines.append("")
                continue

            lines.extend(
                [
                    f"- **Child Universe / Complete / Missing**: {reg_sum.child_universe_count} / {reg_sum.child_complete_count} / {reg_sum.child_missing_count}",
                    f"- **Parent Universe / Complete / Missing**: {reg_sum.parent_universe_count} / {reg_sum.parent_complete_count} / {reg_sum.parent_missing_count}",
                    f"- **Child 缺失原因统计**: `{json.dumps(reg_sum.child_missing_reasons, sort_keys=True)}`",
                    f"- **Parent 缺失原因统计**: `{json.dumps(reg_sum.parent_missing_reasons, sort_keys=True)}`",
                    f"- **Parent Universe UTC 日期分布**: `{json.dumps(reg_sum.universe_parent_utc_date_counts or {}, sort_keys=True)}`",
                    f"- **完整 Parent 样本 UTC 日期分布**: `{json.dumps(reg_sum.complete_parent_utc_date_counts or reg_sum.utc_date_parent_counts or {}, sort_keys=True)}`",
                    f"- **Baseline [T0, D) 统计**: {_format_stats('Price Change', reg_sum.baseline_price_change_stats)} | {_format_stats('Total Notional', reg_sum.baseline_notional_stats)} | {_format_stats('Taker Buy Share', reg_sum.baseline_tbs_stats)}",
                    f"- **Basis 覆盖与分布**: complete={reg_sum.basis_complete_count}, missing={reg_sum.basis_missing_count}, {_format_stats('Basis', reg_sum.basis_stats)}, missing_reasons=`{json.dumps(reg_sum.basis_missing_reasons or {}, sort_keys=True)}`",
                    "",
                ]
            )

            if reg_sum.child_high_group and reg_sum.child_low_group:
                lines.extend(
                    [
                        f"#### `{reg}` — Child 视角分组（独立中位数分组）",
                        f"- High 组样本数: {reg_sum.child_high_group.count}",
                        f"  - {_format_stats('OI Change', reg_sum.child_high_group.oi_stats)}",
                        f"  - {_format_stats('Terminal Return', reg_sum.child_high_group.terminal_stats)}",
                        f"  - {_format_stats('Long MAE', reg_sum.child_high_group.mae_stats)}",
                        f"  - {_format_stats('Long MFE', reg_sum.child_high_group.mfe_stats)}",
                        f"- Low 组样本数: {reg_sum.child_low_group.count}",
                        f"  - {_format_stats('OI Change', reg_sum.child_low_group.oi_stats)}",
                        f"  - {_format_stats('Terminal Return', reg_sum.child_low_group.terminal_stats)}",
                        f"  - {_format_stats('Long MAE', reg_sum.child_low_group.mae_stats)}",
                        f"  - {_format_stats('Long MFE', reg_sum.child_low_group.mfe_stats)}",
                        "",
                    ]
                )

            if reg_sum.parent_high_group and reg_sum.parent_low_group:
                lines.extend(
                    [
                        f"#### `{reg}` — Parent 视角分组（独立中位数分组）",
                        f"- High 组样本数: {reg_sum.parent_high_group.count}",
                        f"  - {_format_stats('OI Change', reg_sum.parent_high_group.oi_stats)}",
                        f"  - {_format_stats('Terminal Return', reg_sum.parent_high_group.terminal_stats)}",
                        f"  - {_format_stats('Long MAE', reg_sum.parent_high_group.mae_stats)}",
                        f"  - {_format_stats('Long MFE', reg_sum.parent_high_group.mfe_stats)}",
                        f"- Low 组样本数: {reg_sum.parent_low_group.count}",
                        f"  - {_format_stats('OI Change', reg_sum.parent_low_group.oi_stats)}",
                        f"  - {_format_stats('Terminal Return', reg_sum.parent_low_group.terminal_stats)}",
                        f"  - {_format_stats('Long MAE', reg_sum.parent_low_group.mae_stats)}",
                        f"  - {_format_stats('Long MFE', reg_sum.parent_low_group.mfe_stats)}",
                        "",
                    ]
                )

            if reg_sum.parent_jackknife:
                jk = reg_sum.parent_jackknife
                b_diff_str = f"{jk.base_diff:.6f}" if jk.base_diff is not None else "null"
                d_min_str = f"{jk.diff_min:.6f}" if jk.diff_min is not None else "null"
                d_max_str = f"{jk.diff_max:.6f}" if jk.diff_max is not None else "null"
                b_med_str = f"{jk.base_median_oi:.6f}" if jk.base_median_oi is not None else "null"
                lines.extend(
                    [
                        f"#### `{reg}` — Parent 逐一剔除（Jackknife Sensitivity）",
                        f"- Base Median OI Change: {b_med_str}",
                        f"- Base High Count: {jk.base_high_count}, Base Low Count: {jk.base_low_count}",
                        f"- Base Diff (High - Low Terminal Return Mean): {b_diff_str}",
                        f"- Diff 范围: [{d_min_str}, {d_max_str}]",
                        "",
                        "| Omitted Parent ID | Remaining Count | High Count | Low Count | Diff Mean Terminal Return |",
                        "| --- | --- | --- | --- | --- |",
                    ]
                )
                for item in jk.jackknife_items:
                    diff_str = (
                        f"{item.diff_mean_terminal_return:.6f}"
                        if item.diff_mean_terminal_return is not None
                        else "null"
                    )
                    lines.append(
                        f"| {item.omitted_parent_id} | {item.remaining_count} | {item.high_count} | {item.low_count} | {diff_str} |"
                    )
                lines.append("")

        lines.extend(
            [
                "## 4. 三组 OI 时间假设情景对照（Scenario A / B / C）与跨情景样本重合",
                "",
                "### 4.1 按机制与情景汇总表（Scenario A: 5m, Scenario B: 10m 主情景, Scenario C: 15m）",
                "",
                "| 上市机制 | 假设情景 | Child 候选 | OI 有效对数 | Child 完整数 | Parent 候选 | Parent 完整数 | Child High/Low | Child Mean Diff (High-Low) | Parent High/Low | Parent Mean Diff (High-Low) | Child 缺失原因 | Parent 缺失原因 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        scen_all = res.scenario_summaries or {}
        for reg in ("pre_market", "standard"):
            scen_map = scen_all.get(reg, {})
            for scen_key in ("A", "B", "C"):
                sc = scen_map.get(scen_key)
                if sc is None:
                    continue
                c_diff_s = (
                    f"{sc.child_terminal_diff_mean:.6f}"
                    if sc.child_terminal_diff_mean is not None
                    else "null"
                )
                p_diff_s = (
                    f"{sc.parent_terminal_diff_mean:.6f}"
                    if sc.parent_terminal_diff_mean is not None
                    else "null"
                )
                c_hi = sc.child_high_group.count if sc.child_high_group else 0
                c_lo = sc.child_low_group.count if sc.child_low_group else 0
                p_hi = sc.parent_high_group.count if sc.parent_high_group else 0
                p_lo = sc.parent_low_group.count if sc.parent_low_group else 0
                c_miss_s = json.dumps(sc.child_missing_reasons, sort_keys=True)
                p_miss_s = json.dumps(sc.parent_missing_reasons or {}, sort_keys=True)
                lines.append(
                    f"| `{reg}` | `Scenario {scen_key}` ({sc.margin_ms}ms) | {sc.child_universe_count} | {sc.child_oi_pair_count} | {sc.child_complete_count} | {sc.parent_universe_count} | {sc.parent_complete_count} | {c_hi}/{c_lo} | {c_diff_s} | {p_hi}/{p_lo} | {p_diff_s} | `{c_miss_s}` | `{p_miss_s}` |"
                )
        lines.append("")

        lines.extend(
            [
                "### 4.2 跨情景样本重合与差异（`A∩B`、`B∩C`、`A∩B∩C`、`A\\B`、`B\\C`）",
                "",
                "- 注：不同情景间的样本差异仅反映不同标签可用余量假设下的窗口截断，不得解释为已证实的发布延迟测量。",
                "",
                "| 上市机制 | Child A∩B | Child B∩C | Child A∩B∩C | Child A\\B | Child B\\C | Parent A∩B | Parent B∩C | Parent A∩B∩C | Parent A\\B | Parent B\\C |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        ov_all = res.scenario_overlaps or {}
        for reg in ("pre_market", "standard"):
            ov = ov_all.get(reg)
            if ov is None:
                continue
            lines.append(
                f"| `{reg}` | {ov.child_overlap_ab} | {ov.child_overlap_bc} | {ov.child_overlap_abc} | {ov.child_diff_a_minus_b} | {ov.child_diff_b_minus_c} | {ov.parent_overlap_ab} | {ov.parent_overlap_bc} | {ov.parent_overlap_abc} | {ov.parent_diff_a_minus_b} | {ov.parent_diff_b_minus_c} |"
            )
        lines.append("")

        lines.extend(
            [
                "## 5. 开盘网格对照（`floor_5m(T0)` 单独列出，不混入主样本）",
                "",
            ]
        )
        grid_all = res.grid_summaries or {}
        grid_scen_all = res.grid_scenario_summaries or {}
        for reg in ("pre_market", "standard"):
            gs = grid_all.get(reg)
            lines.append(f"### 5.{1 if reg == 'pre_market' else 2} 机制：`{reg}` 开盘网格对照")
            scen_grids = grid_scen_all.get(reg, {})
            if not scen_grids and gs is not None:
                scen_grids = {"B": gs}
            if not scen_grids:
                lines.append("- 无记录")
                lines.append("")
                continue

            lines.extend(
                [
                    "| 假设情景 | Child 候选 | 网格有效数 | 网格缺失数 | 与该情景主结果重合数 | 开盘网格 OI Change (均值/中位数) | 缺失原因 |",
                    "| --- | --- | --- | --- | --- | --- | --- |",
                ]
            )
            for sk in ("A", "B", "C"):
                gs_k = scen_grids.get(sk)
                if gs_k is not None:
                    mean_s = f"{gs_k.grid_oi_change_stats.mean:.6f}" if gs_k.grid_oi_change_stats and gs_k.grid_oi_change_stats.mean is not None else "null"
                    med_s = f"{gs_k.grid_oi_change_stats.median:.6f}" if gs_k.grid_oi_change_stats and gs_k.grid_oi_change_stats.median is not None else "null"
                    lines.append(
                        f"| `Scenario {sk}` | {gs_k.child_universe_count} | {gs_k.child_grid_valid_count} | {gs_k.child_grid_missing_count} | {gs_k.coincides_with_main_count} | {mean_s} / {med_s} | `{json.dumps(gs_k.child_grid_missing_reasons, sort_keys=True)}` |"
                    )
            lines.append("")

            reg_children = [
                c
                for c in sorted(child_evaluations, key=lambda x: (x.parent_article_id, x.symbol))
                if c.listing_regime == reg
            ]
            if reg_children:
                lines.extend(
                    [
                        "| Parent ID | Symbol | Grid A Status | Grid B Status | Grid C Status | Grid L0 | Grid L1 | T0 - Grid L0 (ms) | Sched - Grid L0 (ms) | Grid B OI Change | Coincides With Scenario B | Terminal Return |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                    ]
                )
                for item in reg_children:
                    g_chg = (
                        f"{item.grid_b_oi_change:.6f}" if item.grid_b_oi_change is not None else (
                            f"{item.grid_oi_change:.6f}" if item.grid_oi_change is not None else "null"
                        )
                    )
                    t_ret = (
                        f"{item.terminal_return:.6f}"
                        if item.terminal_return is not None
                        else "null"
                    )
                    g_a_st = item.grid_a_status or item.grid_status or ""
                    g_b_st = item.grid_b_status or item.grid_status or ""
                    g_c_st = item.grid_c_status or item.grid_status or ""
                    g_b_coin = item.grid_b_coincides if item.grid_b_coincides is not None else item.grid_coincides_with_main
                    lines.append(
                        f"| {item.parent_article_id} | {item.symbol} | {g_a_st} | {g_b_st} | {g_c_st} | {item.grid_l0_time_ms} | {item.grid_l1_time_ms} | {item.grid_t0_minus_l0_ms} | {item.grid_scheduled_minus_l0_ms} | {g_chg} | {g_b_coin} | {t_ret} |"
                    )
                lines.append("")

        lines.extend(
            [
                "## 6. 方法论边界与不具有交易许可声明",
                "",
                "- 本报告仅供离线探索性分析（`historical_scenario_only`），OI 时间口径为显式情景假设（`unverified_scenario_assumption`），所报告的事后中位数分组绝不构成可部署交易规则或预测信号。",
                "- 依据 L0 / L1 / L2 规则，未经过独立样本验证、真实前瞻 PIT 检验与实盘影子验证，严禁任何实盘或模拟盘交易。",
                "",
                "## 7. 实际消费输入文件清单与身份（Input Provenance Manifest）",
                "",
                f"- **实际消费输入文件总数**: {len(c_inputs)}",
                "",
            ]
        )
        if not c_inputs:
            lines.extend(
                [
                    "- 本次运行使用内存注入数据（synthetic/in-memory），无实际磁盘输入文件消费记录。",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "| 相对路径 / 文件名 | SHA-256 | 文件类型 | 标的 | 数据源 |",
                    "| --- | --- | --- | --- | --- |",
                ]
            )
            for item in sorted(
                c_inputs,
                key=lambda x: (
                    str(x["file_type"]),
                    str(x.get("symbol") or ""),
                    str(x["file_path"]),
                ),
            ):
                f_p = item["file_path"]
                f_sha = item["sha256"]
                f_type = item["file_type"]
                f_sym = item.get("symbol") or "-"
                f_src = item.get("source_name") or "-"
                lines.append(f"| `{f_p}` | `{f_sha}` | {f_type} | {f_sym} | {f_src} |")
            lines.append("")

        with open(review_md_path, "x", encoding="utf-8") as rf:
            rf.write("\n".join(lines))
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise

    return child_csv_path, review_md_path


def compute_required_utc_dates(
    start_ms: int,
    span_ms: int = EXTERNAL_SIGNAL_LAUNCH_OI_MAX_AGGTRADES_SEARCH_SPAN_MS,
) -> List[str]:
    """Compute sorted list of YYYY-MM-DD UTC dates intersecting [start_ms, start_ms + span_ms]."""
    start_sec = start_ms // 1000
    end_sec = (start_ms + span_ms) // 1000
    start_dt = datetime.fromtimestamp(start_sec, tz=timezone.utc).date()
    end_dt = datetime.fromtimestamp(end_sec, tz=timezone.utc).date()
    cur = start_dt
    dates = []
    while cur <= end_dt:
        dates.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return sorted(dates)


AGGTRADES_HEADER = [
    "agg_trade_id",
    "price",
    "quantity",
    "first_trade_id",
    "last_trade_id",
    "transact_time",
    "is_buyer_maker",
]


def _is_strict_nonneg_int_str(val: str) -> bool:
    return bool(val) and val.isascii() and val.isdigit()


def load_child_aggtrades_from_ja_root(
    ja_root: Path,
    ja_summary: Dict[str, Any],
    parent_article_id: str,
    symbol: str,
    t0_ms: int,
    horizon_span_ms: int = EXTERNAL_SIGNAL_LAUNCH_OI_MAX_AGGTRADES_SEARCH_SPAN_MS,
    ja_ctx: Optional[AdmittedJAContext] = None,
) -> Tuple[str, List[AggTradeRecord]]:
    """Loads and streams aggTrades for a child from J-A verified zip archives over [T0, T0 + horizon_span_ms].

    Enforces:
    - Required UTC dates intersecting [T0, T0 + 2_405_000ms] (entry window [D, D+5s] + 15m horizon).
    - J-A archive record presence and child_state == 'archive_verified_with_post_launch_rows' for all required dates.
    - Package admission via upstream open_verified_package_stream: logical_archive_identity, request_records, manifest.json, .CHECKSUM, SHA-256, and ZIP validation.
    - Full CSV stream to EOF (verifying ZIP CRC-32), 7-column schema, UTC day bounds, strict boolean, and monotonic ordering.
    """
    pkg_records = ja_summary.get("archive_package_records")
    if not isinstance(pkg_records, list):
        raise LaunchOiResearchError("corrupted_archive_data:ja_summary_missing_package_records")

    pkg_by_date = {
        str(r["utc_date"]): r
        for r in pkg_records
        if isinstance(r, dict)
        and str(r.get("parent_article_id")) == parent_article_id
        and str(r.get("symbol")) == symbol
    }

    required_dates = compute_required_utc_dates(t0_ms, horizon_span_ms)
    end_ms = t0_ms + horizon_span_ms

    # Check date coverage and child_state in J-A package records first
    for req_d in required_dates:
        if req_d not in pkg_by_date:
            return f"missing_aggtrades_archive:missing_date_{req_d}", []
        pkg = pkg_by_date[req_d]
        if pkg.get("child_state") != "archive_verified_with_post_launch_rows":
            return f"missing_aggtrades_archive:unverified_j_a_package_{req_d}", []

    if ja_ctx is None:
        try:
            ja_ctx = build_admitted_ja_context(ja_root, ja_summary)
        except TakerBuyShareResearchError as exc:
            raise LaunchOiResearchError(f"corrupted_archive_data:{exc}") from exc

    all_trades: List[AggTradeRecord] = []
    prev_tid: Optional[int] = None
    prev_ts: Optional[int] = None

    for req_d in required_dates:
        pkg = pkg_by_date[req_d]
        day_dt = datetime.strptime(req_d, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        day_start_ms = int(day_dt.timestamp() * 1000)
        day_end_ms = day_start_ms + 86_400_000

        try:
            with open_verified_package_stream(
                admitted_ja_context=ja_ctx,
                pkg_record=pkg,
                expected_parent_article_id=parent_article_id,
                expected_symbol=symbol,
                expected_utc_date=req_d,
            ) as raw_f:
                lines = stream_aggtrades_csv_lines(raw_f)
                header_line = next(lines, None)
                if header_line is None:
                    raise LaunchOiResearchError(f"corrupted_archive_data:empty_csv:{req_d}")

                header_cols = next(csv.reader([header_line]))
                if header_cols != AGGTRADES_HEADER:
                    raise LaunchOiResearchError(
                        f"corrupted_archive_data:invalid_header_columns:{req_d}:{header_cols}"
                    )

                row_count = 0
                for line_str in lines:
                    if not line_str.strip():
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:blank_csv_row:{req_d}"
                        )
                    cols = next(csv.reader([line_str]))
                    if len(cols) != 7:
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:invalid_column_count:{req_d}:{line_str}"
                        )

                    if not (
                        _is_strict_nonneg_int_str(cols[0])
                        and _is_strict_nonneg_int_str(cols[3])
                        and _is_strict_nonneg_int_str(cols[4])
                        and _is_strict_nonneg_int_str(cols[5])
                    ):
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:invalid_integer_field:{req_d}:{line_str}"
                        )

                    trade_id = int(cols[0])
                    first_tid = int(cols[3])
                    last_tid = int(cols[4])
                    trade_time = int(cols[5])

                    if first_tid > last_tid:
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:first_tid_gt_last_tid:{req_d}:{line_str}"
                        )
                    if not (day_start_ms <= trade_time < day_end_ms):
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:timestamp_out_of_utc_day:{req_d}:{trade_time}"
                        )

                    if cols[6] not in ("true", "True", "false", "False"):
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:invalid_boolean:{req_d}:{cols[6]}"
                        )
                    is_buyer_maker = cols[6] in ("true", "True")

                    try:
                        price = float(cols[1])
                        qty = float(cols[2])
                    except ValueError as exc:
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:malformed_numeric_field:{req_d}:{exc}:{line_str}"
                        )
                    if not (
                        math.isfinite(price)
                        and price > 0.0
                        and math.isfinite(qty)
                        and qty > 0.0
                    ):
                        raise LaunchOiResearchError(
                            f"corrupted_archive_data:non_positive_or_non_finite_price_qty:{req_d}:{line_str}"
                        )

                    if prev_tid is not None:
                        if trade_id <= prev_tid or trade_time < prev_ts:  # type: ignore[operator]
                            raise LaunchOiResearchError(
                                f"corrupted_archive_data:non_monotonic_row_order:{req_d}:{trade_id}:{trade_time}"
                            )
                    prev_tid = trade_id
                    prev_ts = trade_time
                    row_count += 1

                    if t0_ms <= trade_time <= end_ms:
                        all_trades.append(
                            AggTradeRecord(
                                transact_time_ms=trade_time,
                                trade_id=trade_id,
                                price=price,
                                quantity=qty,
                                is_buyer_maker=is_buyer_maker,
                            )
                        )

                if row_count == 0:
                    raise LaunchOiResearchError(
                        f"corrupted_archive_data:zero_data_rows:{req_d}"
                    )
        except TakerBuyShareResearchError as exc:
            raise LaunchOiResearchError(f"corrupted_archive_data:{exc}") from exc

    return "ok", all_trades


def _parse_oi_metrics_rows_from_reader(
    reader: Any,
    locator: str,
    symbol: str,
    effective_unit: str,
    time_evidence_tuple: Optional[Tuple[str, str, str]],
    information_time_known: bool,
    information_time_offset_ms: int,
) -> List[OiMetricRecord]:
    """Parses OI metric rows from a CSV reader with strict schema and time-evidence checks."""
    out: List[OiMetricRecord] = []
    header = next(reader, None)
    if (
        not header
        or "create_time" not in header
        or "sum_open_interest" not in header
    ):
        raise LaunchOiResearchError(
            f"corrupted_metrics_data:invalid_header:{locator}:{header}"
        )
    t_idx = header.index("create_time")
    oi_idx = header.index("sum_open_interest")
    sym_idx = header.index("symbol") if "symbol" in header else None
    info_ub_idx = (
        header.index("information_time_upper_bound_ms")
        if "information_time_upper_bound_ms" in header
        else None
    )

    for row in reader:
        if not row:
            continue
        max_idx = max(
            t_idx,
            oi_idx,
            sym_idx if sym_idx is not None else 0,
            info_ub_idx if info_ub_idx is not None else 0,
        )
        if len(row) <= max_idx:
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:short_row:{locator}:{row}"
            )
        if sym_idx is not None and row[sym_idx].strip() != symbol:
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:symbol_mismatch:{locator}:{row[sym_idx]}!={symbol}"
            )
        t_str = row[t_idx].strip()
        try:
            dt = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            ts_ms = int(dt.timestamp() * 1000)
            oi_val = float(row[oi_idx])
        except Exception as exc:
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:malformed_row:{locator}:{exc}:{row}"
            )
        if not math.isfinite(oi_val):
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:non_finite_oi:{locator}:{row}"
            )

        info_time: Optional[int] = None
        ev_source: Optional[str] = None
        ev_scope: Optional[str] = None
        ev_basis: Optional[str] = None

        if time_evidence_tuple is not None and info_ub_idx is not None:
            ub_raw = row[info_ub_idx].strip()
            if ub_raw:
                if not _is_strict_nonneg_int_str(ub_raw):
                    raise LaunchOiResearchError(
                        f"corrupted_metrics_data:invalid_information_time_upper_bound_ms:{locator}:{ub_raw}"
                    )
                ub_ms = int(ub_raw)
                if ub_ms < ts_ms:
                    raise LaunchOiResearchError(
                        f"corrupted_metrics_data:information_time_before_create_time:{locator}:{ub_ms}<{ts_ms}"
                    )
                info_time = ub_ms
                ev_source, ev_scope, ev_basis = time_evidence_tuple
        elif information_time_known:
            info_time = ts_ms + information_time_offset_ms

        out.append(
            OiMetricRecord(
                create_time_ms=ts_ms,
                symbol=symbol,
                sum_open_interest=oi_val,
                information_time_ms=info_time,
                information_time_upper_bound_ms=info_time,
                unit=effective_unit,
                time_evidence_source=ev_source,
                time_evidence_scope=ev_scope,
                time_evidence_basis=ev_basis,
            )
        )
    return out


def load_child_oi_metrics_from_sources(
    symbol: str,
    sources_dirs: Sequence[Path],
    information_time_known: bool = False,
    information_time_offset_ms: int = 0,
    authorized_input_files: Optional[Dict[str, str]] = None,
    project_root: Optional[Path] = None,
    consumed_files_collector: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[OiMetricRecord]]:
    """Loads OI metric records for symbol strictly from manifest-listed files in sources_dirs.

    Enforces:
    - Every {symbol}-metrics-*.zip or .csv on disk in s_dir MUST be listed in oi_provenance_manifest.json with a matching SHA-256.
      Unlisted metrics files on disk raise LaunchOiResearchError.
    - Never fabricates information_time from a self-certified JSON boolean/offset when the CSV only contains create_time labels.
      Only populates information_time_upper_bound_ms when BOTH:
      (a) oi_provenance_manifest.json provides non-empty time_semantics_evidence.{source, applicable_scope, verifiable_basis}, AND
      (b) the data row itself carries an explicit verified information_time_upper_bound_ms column (>= create_time_ms).
      Otherwise information_time_upper_bound_ms remains None so calculate_oi_change returns 'evidence_insufficient_information_time'.
    """
    records: List[OiMetricRecord] = []
    found_file = False
    import io
    import zipfile

    for s_dir in sources_dirs:
        if not s_dir.is_dir():
            continue

        disk_files = sorted(
            list(s_dir.glob(f"{symbol}-metrics-*.zip"))
            + list(s_dir.glob(f"{symbol}-metrics-*.csv"))
        )
        prov_path = s_dir / "oi_provenance_manifest.json"

        if not prov_path.is_file():
            if disk_files:
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:unlisted_metrics_file_without_manifest:{disk_files[0]}"
                )
            continue

        try:
            prov_obj = json.loads(prov_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:invalid_oi_provenance_manifest_json:{prov_path}:{exc}"
            )
        if not isinstance(prov_obj, dict) or not isinstance(prov_obj.get("symbols"), dict):
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:invalid_oi_provenance_manifest_schema:{prov_path}"
            )

        sym_prov = prov_obj["symbols"].get(symbol)
        if sym_prov is None:
            if disk_files:
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:unlisted_metrics_file_for_symbol:{disk_files[0]}"
                )
            continue

        if not isinstance(sym_prov, dict):
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:invalid_symbol_provenance:{prov_path}:{symbol}"
            )
        for req_field in ("source_name", "source_version", "applicable_scope", "unit"):
            fval = sym_prov.get(req_field)
            if not isinstance(fval, str) or not fval.strip():
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:missing_provenance_field:{req_field}:{symbol}"
                )
        effective_unit = sym_prov["unit"].strip()
        files_map = sym_prov.get("files")
        if not isinstance(files_map, dict) or not files_map:
            raise LaunchOiResearchError(
                f"corrupted_metrics_data:missing_provenance_files:{symbol}"
            )

        if consumed_files_collector is not None:
            rel_p = (
                str(prov_path.relative_to(project_root))
                if (project_root and prov_path.is_relative_to(project_root))
                else str(prov_path)
            )
            consumed_files_collector.append(
                {
                    "file_path": rel_p,
                    "sha256": _compute_file_sha256_chunked(prov_path),
                    "file_type": "oi_provenance_manifest",
                    "symbol": symbol,
                    "source_name": sym_prov["source_name"].strip(),
                }
            )

        # Reject any unlisted {symbol}-metrics-* file on disk
        for df in disk_files:
            if df.name not in files_map:
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:unlisted_metrics_file:{df}"
                )

        time_evidence_tuple: Optional[Tuple[str, str, str]] = None
        if "time_semantics_evidence" in sym_prov and sym_prov["time_semantics_evidence"] is not None:
            tse = sym_prov["time_semantics_evidence"]
            if not isinstance(tse, dict):
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:invalid_time_semantics_evidence:{symbol}"
                )
            ev_src = tse.get("source")
            ev_scp = tse.get("applicable_scope")
            ev_bas = tse.get("verifiable_basis")
            if (
                not isinstance(ev_src, str)
                or not ev_src.strip()
                or not isinstance(ev_scp, str)
                or not ev_scp.strip()
                or not isinstance(ev_bas, str)
                or not ev_bas.strip()
            ):
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:incomplete_time_semantics_evidence:{symbol}"
                )
            time_evidence_tuple = (ev_src.strip(), ev_scp.strip(), ev_bas.strip())

        for fname, fmeta in sorted(files_map.items()):
            if not isinstance(fmeta, dict) or not isinstance(fmeta.get("sha256"), str):
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:invalid_file_hash_entry:{fname}"
                )
            fpath = s_dir / fname
            if not fpath.is_file():
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:claimed_metrics_file_missing:{fpath}"
                )
            actual_fsha = _compute_file_sha256_chunked(fpath)
            if actual_fsha != fmeta["sha256"]:
                raise LaunchOiResearchError(
                    f"corrupted_metrics_data:metrics_file_sha256_mismatch:{fpath}"
                )

            if authorized_input_files is not None:
                matched_key = None
                candidates = [fpath.name, str(fpath)]
                if project_root is not None:
                    try:
                        candidates.append(str(fpath.relative_to(project_root)))
                    except ValueError:
                        pass
                for c in candidates:
                    if c in authorized_input_files:
                        matched_key = c
                        break
                if matched_key is None:
                    raise LaunchOiResearchError(
                        f"unauthorized_source_file_rejected: {fpath}"
                    )
                if actual_fsha != authorized_input_files[matched_key]:
                    raise LaunchOiResearchError(
                        f"auth_source_file_sha_mismatch: {fpath}"
                    )

            found_file = True
            if consumed_files_collector is not None:
                rel_p = (
                    str(fpath.relative_to(project_root))
                    if (project_root and fpath.is_relative_to(project_root))
                    else str(fpath)
                )
                consumed_files_collector.append(
                    {
                        "file_path": rel_p,
                        "sha256": actual_fsha,
                        "file_type": "oi_metrics",
                        "symbol": symbol,
                        "source_name": sym_prov["source_name"].strip(),
                    }
                )
            if fpath.suffix == ".zip":
                if not validate_zip_archive_package(fpath):
                    raise LaunchOiResearchError(
                        f"corrupted_metrics_data:zip_package_invalid_or_resource_caps_exceeded:{fpath}"
                    )
                try:
                    with zipfile.ZipFile(fpath, "r") as zf:
                        csv_members = [m for m in zf.namelist() if m.endswith(".csv")]
                        if not csv_members:
                            raise LaunchOiResearchError(
                                f"corrupted_metrics_data:no_csv_member_in_zip:{fpath}"
                            )
                        for m in sorted(csv_members):
                            with zf.open(m, "r") as mf:
                                reader = csv.reader(io.TextIOWrapper(mf, encoding="utf-8"))
                                records.extend(
                                    _parse_oi_metrics_rows_from_reader(
                                        reader=reader,
                                        locator=f"{fpath}:{m}",
                                        symbol=symbol,
                                        effective_unit=effective_unit,
                                        time_evidence_tuple=time_evidence_tuple,
                                        information_time_known=information_time_known,
                                        information_time_offset_ms=information_time_offset_ms,
                                    )
                                )
                except zipfile.BadZipFile as exc:
                    raise LaunchOiResearchError(f"corrupted_metrics_data:bad_zip:{fpath}:{exc}")
                except Exception as exc:
                    if isinstance(exc, LaunchOiResearchError):
                        raise
                    raise LaunchOiResearchError(
                        f"corrupted_metrics_data:zip_read_error:{fpath}:{exc}"
                    )
            else:
                try:
                    with open(fpath, "r", encoding="utf-8") as mf:
                        reader = csv.reader(mf)
                        records.extend(
                            _parse_oi_metrics_rows_from_reader(
                                reader=reader,
                                locator=str(fpath),
                                symbol=symbol,
                                effective_unit=effective_unit,
                                time_evidence_tuple=time_evidence_tuple,
                                information_time_known=information_time_known,
                                information_time_offset_ms=information_time_offset_ms,
                            )
                        )
                except Exception as exc:
                    if isinstance(exc, LaunchOiResearchError):
                        raise
                    raise LaunchOiResearchError(
                        f"corrupted_metrics_data:csv_read_error:{fpath}:{exc}"
                    )

    if not found_file:
        return "metrics_source_not_found", []

    return "ok", records


def _parse_kline_file(path: Path, expected_symbol: str, unit: str) -> List[KlineBar]:
    """Parses a single verified CSV or ZIP kline file into KlineBar items, failing closed on corruption."""
    import io
    import zipfile

    bars: List[KlineBar] = []

    def _read_rows(reader: Any, locator: str) -> None:
        for row_idx, row in enumerate(reader):
            if not row:
                continue
            if row_idx == 0 and not row[0].strip().isdigit():
                # Header row in kline CSV
                continue
            if len(row) < 7:
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:short_row:{locator}:{row}"
                )
            try:
                ot = int(row[0])
                op = float(row[1])
                hp = float(row[2])
                lp = float(row[3])
                cp = float(row[4])
                ct = int(row[6])
            except ValueError as exc:
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:malformed_row:{locator}:{exc}:{row}"
                )
            if not (
                math.isfinite(op)
                and math.isfinite(hp)
                and math.isfinite(lp)
                and math.isfinite(cp)
                and cp > 0.0
            ):
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:non_positive_or_non_finite_price:{locator}:{row}"
                )
            bars.append(
                KlineBar(
                    open_time_ms=ot,
                    close_time_ms=ct,
                    close_price=cp,
                    symbol=expected_symbol,
                    unit=unit,
                    open_price=op,
                    high_price=hp,
                    low_price=lp,
                )
            )

    if path.suffix == ".zip":
        if not validate_zip_archive_package(path):
            raise LaunchOiResearchError(
                f"corrupted_klines_data:zip_package_invalid_or_resource_caps_exceeded:{path}"
            )
        try:
            with zipfile.ZipFile(path, "r") as zf:
                csv_members = [m for m in zf.namelist() if m.endswith(".csv")]
                if not csv_members:
                    raise LaunchOiResearchError(
                        f"corrupted_klines_data:no_csv_member_in_zip:{path}"
                    )
                for m in csv_members:
                    with zf.open(m, "r") as mf:
                        reader = csv.reader(io.TextIOWrapper(mf, encoding="utf-8"))
                        _read_rows(reader, f"{path}:{m}")
        except zipfile.BadZipFile as exc:
            raise LaunchOiResearchError(f"corrupted_klines_data:bad_zip:{path}:{exc}")
    else:
        with open(path, "r", encoding="utf-8") as mf:
            reader = csv.reader(mf)
            _read_rows(reader, str(path))

    return bars


def load_verified_child_klines_from_sources(
    symbol: str,
    sources_dirs: Sequence[Path],
    authorized_input_files: Optional[Dict[str, str]] = None,
    project_root: Optional[Path] = None,
    consumed_files_collector: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[KlineBar], List[KlineBar], Optional[str]]:
    """Loads mark and index 1m klines for symbol ONLY when verified exchange product metadata and unit provenance exist.

    Requires kline_mapping_manifest.json with:
    - source_name, source_version, evidence_reference
    - exchange_info_file and exchange_info_sha256 referencing a hash-verified exchange metadata file on disk
      whose PERPETUAL contract entry for `symbol` proves `pair == mapped_index_symbol` and `quoteAsset == mark_unit`
    - mark_files and index_files with verified SHA-256 on disk.
    If no verified mapping manifest or exchange metadata exists for symbol, returns ('unverified_product_mapping', [], [], None).
    """
    unverified_tags = {"UNVERIFIED", "UNKNOWN", "NONE", "NULL"}

    def _verify_file_auth(fpath: Path, actual_sha: str) -> None:
        if authorized_input_files is None:
            return
        matched_key = None
        candidates = [fpath.name, str(fpath)]
        if project_root is not None:
            try:
                candidates.append(str(fpath.relative_to(project_root)))
            except ValueError:
                pass
        for c in candidates:
            if c in authorized_input_files:
                matched_key = c
                break
        if matched_key is None:
            raise LaunchOiResearchError(f"unauthorized_source_file_rejected: {fpath}")
        if actual_sha != authorized_input_files[matched_key]:
            raise LaunchOiResearchError(f"auth_source_file_sha_mismatch: {fpath}")

    for s_dir in sources_dirs:
        if not s_dir.is_dir():
            continue
        man_path = s_dir / "kline_mapping_manifest.json"
        if not man_path.is_file():
            continue

        try:
            man_obj = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LaunchOiResearchError(
                f"corrupted_klines_data:invalid_kline_mapping_manifest_json:{man_path}:{exc}"
            )
        if not isinstance(man_obj, dict) or not isinstance(man_obj.get("symbols"), dict):
            raise LaunchOiResearchError(
                f"corrupted_klines_data:invalid_kline_mapping_manifest_schema:{man_path}"
            )

        sym_map = man_obj["symbols"].get(symbol)
        if sym_map is None:
            continue
        if not isinstance(sym_map, dict):
            raise LaunchOiResearchError(
                f"corrupted_klines_data:invalid_symbol_mapping_entry:{man_path}:{symbol}"
            )

        for req_f in (
            "source_name",
            "source_version",
            "evidence_reference",
            "target_symbol",
            "mapped_index_symbol",
            "mark_unit",
            "index_unit",
            "exchange_info_file",
            "exchange_info_sha256",
        ):
            val = sym_map.get(req_f)
            if not isinstance(val, str) or not val.strip():
                return "unverified_product_mapping", [], [], None

        if sym_map["target_symbol"].strip() != symbol:
            return "unverified_product_mapping", [], [], None

        if consumed_files_collector is not None:
            rel_p = (
                str(man_path.relative_to(project_root))
                if (project_root and man_path.is_relative_to(project_root))
                else str(man_path)
            )
            consumed_files_collector.append(
                {
                    "file_path": rel_p,
                    "sha256": _compute_file_sha256_chunked(man_path),
                    "file_type": "kline_mapping_manifest",
                    "symbol": symbol,
                    "source_name": sym_map["source_name"].strip(),
                }
            )

        mapped_idx = sym_map["mapped_index_symbol"].strip()
        if mapped_idx.upper() in unverified_tags:
            return "unverified_product_mapping", [], [], None

        mark_unit = sym_map["mark_unit"].strip()
        index_unit = sym_map["index_unit"].strip()
        if mark_unit.upper() in unverified_tags or index_unit.upper() in unverified_tags:
            return "unverified_product_mapping", [], [], None

        # Verify exchange_info_file hash and contract-to-index / unit metadata
        ex_info_path = s_dir / sym_map["exchange_info_file"].strip()
        if not ex_info_path.is_file():
            raise LaunchOiResearchError(
                f"corrupted_klines_data:claimed_exchange_info_missing:{ex_info_path}"
            )
        ex_info_actual_sha = _compute_file_sha256_chunked(ex_info_path)
        if ex_info_actual_sha != sym_map["exchange_info_sha256"].strip():
            raise LaunchOiResearchError(
                f"corrupted_klines_data:exchange_info_sha256_mismatch:{ex_info_path}"
            )
        _verify_file_auth(ex_info_path, ex_info_actual_sha)
        if consumed_files_collector is not None:
            rel_p = (
                str(ex_info_path.relative_to(project_root))
                if (project_root and ex_info_path.is_relative_to(project_root))
                else str(ex_info_path)
            )
            consumed_files_collector.append(
                {
                    "file_path": rel_p,
                    "sha256": ex_info_actual_sha,
                    "file_type": "kline_exchange_info",
                    "symbol": symbol,
                    "source_name": sym_map["source_name"].strip(),
                }
            )
        try:
            ex_info_obj = json.loads(ex_info_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise LaunchOiResearchError(
                f"corrupted_klines_data:invalid_exchange_info_json:{ex_info_path}:{exc}"
            )
        if not isinstance(ex_info_obj, dict) or not isinstance(ex_info_obj.get("symbols"), list):
            raise LaunchOiResearchError(
                f"corrupted_klines_data:invalid_exchange_info_schema:{ex_info_path}"
            )

        matched_contract: Optional[Dict[str, Any]] = None
        for entry in ex_info_obj["symbols"]:
            if isinstance(entry, dict) and entry.get("symbol") == symbol:
                matched_contract = entry
                break
        if matched_contract is None:
            return "unverified_product_mapping", [], [], None

        ex_pair = str(matched_contract.get("pair") or "").strip()
        ex_quote = str(matched_contract.get("quoteAsset") or "").strip()
        ex_ctype = str(matched_contract.get("contractType") or "").strip()
        if (
            ex_ctype != "PERPETUAL"
            or not ex_pair
            or ex_pair.upper() in unverified_tags
            or ex_pair != mapped_idx
            or not ex_quote
            or ex_quote != mark_unit
        ):
            return "unverified_product_mapping", [], [], None

        mark_files = sym_map.get("mark_files")
        index_files = sym_map.get("index_files")
        if (
            not isinstance(mark_files, dict)
            or not mark_files
            or not isinstance(index_files, dict)
            or not index_files
        ):
            raise LaunchOiResearchError(
                f"corrupted_klines_data:missing_mark_or_index_files_in_manifest:{symbol}"
            )

        mark_bars: List[KlineBar] = []
        for fname, fmeta in sorted(mark_files.items()):
            if not isinstance(fmeta, dict) or not isinstance(fmeta.get("sha256"), str):
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:invalid_mark_file_meta:{fname}"
                )
            fpath = s_dir / fname
            if not fpath.is_file():
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:claimed_mark_file_missing:{fpath}"
                )
            mark_actual_sha = _compute_file_sha256_chunked(fpath)
            if mark_actual_sha != fmeta["sha256"]:
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:mark_file_sha256_mismatch:{fpath}"
                )
            _verify_file_auth(fpath, mark_actual_sha)
            if consumed_files_collector is not None:
                rel_p = (
                    str(fpath.relative_to(project_root))
                    if (project_root and fpath.is_relative_to(project_root))
                    else str(fpath)
                )
                consumed_files_collector.append(
                    {
                        "file_path": rel_p,
                        "sha256": mark_actual_sha,
                        "file_type": "mark_kline",
                        "symbol": symbol,
                        "source_name": sym_map["source_name"].strip(),
                    }
                )
            mark_bars.extend(_parse_kline_file(fpath, expected_symbol=symbol, unit=mark_unit))

        index_bars: List[KlineBar] = []
        for fname, fmeta in sorted(index_files.items()):
            if not isinstance(fmeta, dict) or not isinstance(fmeta.get("sha256"), str):
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:invalid_index_file_meta:{fname}"
                )
            fpath = s_dir / fname
            if not fpath.is_file():
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:claimed_index_file_missing:{fpath}"
                )
            idx_actual_sha = _compute_file_sha256_chunked(fpath)
            if idx_actual_sha != fmeta["sha256"]:
                raise LaunchOiResearchError(
                    f"corrupted_klines_data:index_file_sha256_mismatch:{fpath}"
                )
            _verify_file_auth(fpath, idx_actual_sha)
            if consumed_files_collector is not None:
                rel_p = (
                    str(fpath.relative_to(project_root))
                    if (project_root and fpath.is_relative_to(project_root))
                    else str(fpath)
                )
                consumed_files_collector.append(
                    {
                        "file_path": rel_p,
                        "sha256": idx_actual_sha,
                        "file_type": "index_kline",
                        "symbol": mapped_idx,
                        "source_name": sym_map["source_name"].strip(),
                    }
                )
            index_bars.extend(
                _parse_kline_file(fpath, expected_symbol=mapped_idx, unit=index_unit)
            )

        return "ok", mark_bars, index_bars, mapped_idx

    return "unverified_product_mapping", [], [], None


def execute_exploratory_pipeline(
    selected_children: List[Dict[str, str]],
    ja_root: Path,
    jb_root: Path,
    output_dir: Path,
    project_root: Path,
    ja_loader: Optional[Any] = None,
    jb_loader: Optional[Any] = None,
    metrics_by_symbol: Optional[Dict[str, List[OiMetricRecord]]] = None,
    aggtrades_by_symbol: Optional[Dict[str, List[AggTradeRecord]]] = None,
    klines_by_symbol: Optional[
        Dict[str, Tuple[List[KlineBar], List[KlineBar], Optional[str]]]
    ] = None,
    sources_dirs: Optional[Sequence[Path]] = None,
    extra_sources_dirs: Optional[Sequence[Path]] = None,
    authorized_input_files: Optional[Dict[str, str]] = None,
) -> AggregateGroupingResult:
    """Executes exploratory reduction pipeline across selected children."""
    if ja_loader is None:
        from src.research.external_signal_shadow.stage1_5j_a_historical_archive_coverage_inventory import (
            load_verified_stage1_5j_a_historical_archive_coverage_root,
        )

        actual_ja_loader = load_verified_stage1_5j_a_historical_archive_coverage_root
    else:
        actual_ja_loader = ja_loader

    if jb_loader is None:
        from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
            load_verified_stage1_5j_b_historical_aggtrades_launch_response_root,
        )

        actual_jb_loader = load_verified_stage1_5j_b_historical_aggtrades_launch_response_root
    else:
        actual_jb_loader = jb_loader

    ja_summary = actual_ja_loader(ja_root)
    jb_summary = actual_jb_loader(jb_root)

    jb_by_key: Dict[Tuple[str, str], Dict[str, Any]] = {}
    jb_rows = jb_summary.get("child_rows")
    if isinstance(jb_rows, list):
        for r in jb_rows:
            jb_by_key[(str(r.get("source_article_id")), str(r.get("symbol")))] = r

    # Determine external data search sources: strictly use authorized sources (default empty, NO hardcoded default paths)
    actual_sources_dirs: List[Path] = []
    seen_source_paths: Set[Path] = set()
    candidate_sources = sources_dirs if sources_dirs is not None else (extra_sources_dirs or [])
    for s_dir in candidate_sources:
        s_res = s_dir.resolve()
        if s_res not in seen_source_paths:
            seen_source_paths.add(s_res)
            actual_sources_dirs.append(s_dir)

    admitted_ja_ctx: Optional[AdmittedJAContext] = None
    raw_consumed_inputs: List[Dict[str, Any]] = []
    child_evals: List[ChildEvaluation] = []
    for s_row in selected_children:
        pid = str(s_row["parent_article_id"])
        sym = str(s_row["symbol"])
        reg = str(s_row["listing_regime"])
        utc_date = s_row.get("utc_date")

        jb_entry = jb_by_key.get((pid, sym))
        if jb_entry is None:
            child_evals.append(
                ChildEvaluation(
                    parent_article_id=pid,
                    symbol=sym,
                    listing_regime=reg,
                    is_complete=False,
                    missing_reason="missing_in_jb_universe",
                    utc_date=utc_date,
                    path_status="missing_in_jb_universe",
                    oi_status="missing_in_jb_universe",
                    oi_a_status="missing_in_jb_universe",
                    oi_b_status="missing_in_jb_universe",
                    oi_c_status="missing_in_jb_universe",
                    grid_status="missing_in_jb_universe",
                    grid_a_status="missing_in_jb_universe",
                    grid_b_status="missing_in_jb_universe",
                    grid_c_status="missing_in_jb_universe",
                )
            )
            continue

        t0_ms = jb_entry.get("anchor_time_ms")
        if t0_ms is None:
            child_evals.append(
                ChildEvaluation(
                    parent_article_id=pid,
                    symbol=sym,
                    listing_regime=reg,
                    is_complete=False,
                    missing_reason="missing_jb_anchor_time",
                    utc_date=utc_date,
                    path_status="missing_jb_anchor_time",
                    oi_status="missing_jb_anchor_time",
                    oi_a_status="missing_jb_anchor_time",
                    oi_b_status="missing_jb_anchor_time",
                    oi_c_status="missing_jb_anchor_time",
                    grid_status="missing_jb_anchor_time",
                    grid_a_status="missing_jb_anchor_time",
                    grid_b_status="missing_jb_anchor_time",
                    grid_c_status="missing_jb_anchor_time",
                )
            )
            continue

        # Derive utc_date from J-B verified anchor_time_ms (ground truth)
        if isinstance(t0_ms, (int, float)):
            try:
                utc_date = datetime.fromtimestamp(t0_ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                pass

        d_ms = t0_ms + OBSERVATION_OFFSET_MS
        raw_launch_ms = jb_entry.get("symbol_launch_time_ms")
        scheduled_launch_ms = (
            int(raw_launch_ms) if raw_launch_ms is not None else None
        )

        # 1. Resolve OI metric records and evaluate Scenarios A, B (main), C + opening grid control
        if metrics_by_symbol is not None and sym in metrics_by_symbol:
            oi_records = metrics_by_symbol[sym]
            oi_st = "ok"
        else:
            oi_st, oi_records = load_child_oi_metrics_from_sources(
                sym,
                actual_sources_dirs,
                authorized_input_files=authorized_input_files,
                project_root=project_root,
                consumed_files_collector=raw_consumed_inputs,
            )

        if oi_st != "ok":
            target_grid_l0 = (t0_ms // 300_000) * 300_000
            grid_t0_minus_l0_val = t0_ms - target_grid_l0
            grid_sched_minus_l0_val = (
                (scheduled_launch_ms - target_grid_l0)
                if scheduled_launch_ms is not None
                else None
            )
            oi_a_res = OiResult(
                status=oi_st,
                symbol=sym,
                d_ms=d_ms,
                margin_ms=300_000,
                scenario_name="A",
                grid_status=oi_st,
                grid_t0_minus_l0_ms=grid_t0_minus_l0_val,
                grid_scheduled_minus_l0_ms=grid_sched_minus_l0_val,
            )
            oi_b_res = OiResult(
                status=oi_st,
                symbol=sym,
                d_ms=d_ms,
                margin_ms=600_000,
                scenario_name="B",
                grid_status=oi_st,
                grid_t0_minus_l0_ms=grid_t0_minus_l0_val,
                grid_scheduled_minus_l0_ms=grid_sched_minus_l0_val,
            )
            oi_c_res = OiResult(
                status=oi_st,
                symbol=sym,
                d_ms=d_ms,
                margin_ms=900_000,
                scenario_name="C",
                grid_status=oi_st,
                grid_t0_minus_l0_ms=grid_t0_minus_l0_val,
                grid_scheduled_minus_l0_ms=grid_sched_minus_l0_val,
            )
        else:
            scen_map = evaluate_oi_scenarios(
                records=oi_records,
                symbol=sym,
                t0_ms=t0_ms,
                d_ms=d_ms,
                scheduled_launch_ms=scheduled_launch_ms,
            )
            oi_a_res = scen_map["A"]
            oi_b_res = scen_map["B"]
            oi_c_res = scen_map["C"]
        oi_res = oi_b_res

        # 2. Resolve aggTrades
        if aggtrades_by_symbol is not None and sym in aggtrades_by_symbol:
            trades = aggtrades_by_symbol[sym]
            agg_st = "ok"
        else:
            if admitted_ja_ctx is None and (ja_root / "manifest.json").is_file():
                admitted_ja_ctx = build_admitted_ja_context(ja_root, ja_summary)
            agg_st, trades = load_child_aggtrades_from_ja_root(
                ja_root=ja_root,
                ja_summary=ja_summary,
                parent_article_id=pid,
                symbol=sym,
                t0_ms=t0_ms,
                ja_ctx=admitted_ja_ctx,
            )

        if agg_st != "ok":
            path_res = PathResult(status=agg_st)
            base_res = BaselineMetrics(status=agg_st, trade_count=0)
        else:
            path_res = calculate_path_response(trades=trades, d_ms=d_ms)
            base_res = calculate_baseline(trades=trades, t0_ms=t0_ms, d_ms=d_ms)

        # 3. Resolve basis klines
        basis_val: Optional[float] = None
        basis_status: Optional[str] = None
        basis_age_ms: Optional[int] = None
        if klines_by_symbol is not None and sym in klines_by_symbol:
            mark_b, index_b, mapped_idx = klines_by_symbol[sym]
            basis_res = calculate_basis(
                mark_bars=mark_b,
                index_bars=index_b,
                target_symbol=sym,
                mapped_index_symbol=mapped_idx,
                d_ms=d_ms,
            )
            basis_status = basis_res.status
            basis_age_ms = basis_res.age_ms
            if basis_res.status == "ok":
                basis_val = basis_res.basis
        else:
            kline_st, mark_b, index_b, mapped_idx = load_verified_child_klines_from_sources(
                sym,
                actual_sources_dirs,
                authorized_input_files=authorized_input_files,
                project_root=project_root,
                consumed_files_collector=raw_consumed_inputs,
            )
            if kline_st == "ok":
                basis_res = calculate_basis(
                    mark_bars=mark_b,
                    index_bars=index_b,
                    target_symbol=sym,
                    mapped_index_symbol=mapped_idx,
                    d_ms=d_ms,
                )
                basis_status = basis_res.status
                basis_age_ms = basis_res.age_ms
                if basis_res.status == "ok":
                    basis_val = basis_res.basis
            else:
                basis_val = None
                basis_status = kline_st
                basis_age_ms = None

        is_complete = (oi_res.status == "ok") and (path_res.status == "ok")
        missing_reason: Optional[str] = None
        if not is_complete:
            missing_reason = oi_res.status if oi_res.status != "ok" else path_res.status

        child_evals.append(
            ChildEvaluation(
                parent_article_id=pid,
                symbol=sym,
                listing_regime=reg,
                is_complete=is_complete,
                missing_reason=missing_reason,
                oi_change=oi_res.oi_change,
                terminal_return=path_res.terminal_return,
                long_mae=path_res.long_mae,
                long_mfe=path_res.long_mfe,
                utc_date=utc_date,
                basis=basis_val,
                entry_price=path_res.entry_price,
                entry_delay_ms=path_res.entry_delay_ms,
                endpoint_price=path_res.endpoint_price,
                oi_l0_time_ms=oi_res.l0_ms,
                oi_l1_time_ms=oi_res.l1_ms,
                oi_l0=oi_res.oi_l0,
                oi_l1=oi_res.oi_l1,
                oi_age_ms=oi_res.age_ms,
                oi_assumed_info_l0_ms=oi_res.assumed_info_time_l0_ms,
                oi_assumed_info_l1_ms=oi_res.assumed_info_time_l1_ms,
                oi_assumed_avail_l0_ms=oi_res.assumed_avail_time_l0_ms,
                oi_assumed_avail_l1_ms=oi_res.assumed_avail_time_l1_ms,
                oi_assumed_avail_age_ms=oi_res.assumed_avail_age_ms,
                basis_status=basis_status,
                basis_age_ms=basis_age_ms,
                baseline_price_change=base_res.price_change,
                baseline_total_notional=base_res.total_notional,
                baseline_taker_buy_share=base_res.taker_buy_share,
                path_status=path_res.status,
                oi_status=oi_res.status,
                oi_a_status=oi_a_res.status,
                oi_a_change=oi_a_res.oi_change,
                oi_a_l0_time_ms=oi_a_res.l0_ms,
                oi_a_l1_time_ms=oi_a_res.l1_ms,
                oi_a_l0=oi_a_res.oi_l0,
                oi_a_l1=oi_a_res.oi_l1,
                oi_a_age_ms=oi_a_res.age_ms,
                oi_a_assumed_info_l0_ms=oi_a_res.assumed_info_time_l0_ms,
                oi_a_assumed_info_l1_ms=oi_a_res.assumed_info_time_l1_ms,
                oi_a_assumed_avail_l0_ms=oi_a_res.assumed_avail_time_l0_ms,
                oi_a_assumed_avail_l1_ms=oi_a_res.assumed_avail_time_l1_ms,
                oi_a_assumed_avail_age_ms=oi_a_res.assumed_avail_age_ms,
                oi_b_status=oi_b_res.status,
                oi_b_change=oi_b_res.oi_change,
                oi_b_l0_time_ms=oi_b_res.l0_ms,
                oi_b_l1_time_ms=oi_b_res.l1_ms,
                oi_b_l0=oi_b_res.oi_l0,
                oi_b_l1=oi_b_res.oi_l1,
                oi_b_age_ms=oi_b_res.age_ms,
                oi_b_assumed_info_l0_ms=oi_b_res.assumed_info_time_l0_ms,
                oi_b_assumed_info_l1_ms=oi_b_res.assumed_info_time_l1_ms,
                oi_b_assumed_avail_l0_ms=oi_b_res.assumed_avail_time_l0_ms,
                oi_b_assumed_avail_l1_ms=oi_b_res.assumed_avail_time_l1_ms,
                oi_b_assumed_avail_age_ms=oi_b_res.assumed_avail_age_ms,
                oi_c_status=oi_c_res.status,
                oi_c_change=oi_c_res.oi_change,
                oi_c_l0_time_ms=oi_c_res.l0_ms,
                oi_c_l1_time_ms=oi_c_res.l1_ms,
                oi_c_l0=oi_c_res.oi_l0,
                oi_c_l1=oi_c_res.oi_l1,
                oi_c_age_ms=oi_c_res.age_ms,
                oi_c_assumed_info_l0_ms=oi_c_res.assumed_info_time_l0_ms,
                oi_c_assumed_info_l1_ms=oi_c_res.assumed_info_time_l1_ms,
                oi_c_assumed_avail_l0_ms=oi_c_res.assumed_avail_time_l0_ms,
                oi_c_assumed_avail_l1_ms=oi_c_res.assumed_avail_time_l1_ms,
                oi_c_assumed_avail_age_ms=oi_c_res.assumed_avail_age_ms,
                grid_status=oi_res.grid_status,
                grid_oi_change=oi_res.grid_oi_change,
                grid_l0_time_ms=oi_res.grid_l0_ms,
                grid_l1_time_ms=oi_res.grid_l1_ms,
                grid_oi_l0=oi_res.grid_oi_l0,
                grid_oi_l1=oi_res.grid_oi_l1,
                grid_t0_minus_l0_ms=oi_res.grid_t0_minus_l0_ms,
                grid_scheduled_minus_l0_ms=oi_res.grid_scheduled_minus_l0_ms,
                grid_coincides_with_main=oi_res.grid_coincides_with_main,
                grid_a_status=oi_a_res.grid_status,
                grid_a_oi_change=oi_a_res.grid_oi_change,
                grid_a_l0_time_ms=oi_a_res.grid_l0_ms,
                grid_a_l1_time_ms=oi_a_res.grid_l1_ms,
                grid_a_oi_l0=oi_a_res.grid_oi_l0,
                grid_a_oi_l1=oi_a_res.grid_oi_l1,
                grid_a_coincides=oi_a_res.grid_coincides_with_main,
                grid_b_status=oi_b_res.grid_status,
                grid_b_oi_change=oi_b_res.grid_oi_change,
                grid_b_l0_time_ms=oi_b_res.grid_l0_ms,
                grid_b_l1_time_ms=oi_b_res.grid_l1_ms,
                grid_b_oi_l0=oi_b_res.grid_oi_l0,
                grid_b_oi_l1=oi_b_res.grid_oi_l1,
                grid_b_coincides=oi_b_res.grid_coincides_with_main,
                grid_c_status=oi_c_res.grid_status,
                grid_c_oi_change=oi_c_res.grid_oi_change,
                grid_c_l0_time_ms=oi_c_res.grid_l0_ms,
                grid_c_l1_time_ms=oi_c_res.grid_l1_ms,
                grid_c_oi_l0=oi_c_res.grid_oi_l0,
                grid_c_oi_l1=oi_c_res.grid_oi_l1,
                grid_c_coincides=oi_c_res.grid_coincides_with_main,
            )
        )

    seen_c: Set[Tuple[str, str]] = set()
    dedup_consumed: List[Dict[str, Any]] = []
    for item in raw_consumed_inputs:
        k = (str(item.get("file_path")), str(item.get("sha256")))
        if k not in seen_c:
            seen_c.add(k)
            dedup_consumed.append(item)

    res = aggregate_and_group(child_evals, consumed_inputs=dedup_consumed)
    write_exploratory_outputs(
        output_dir, child_evals, res, project_root=project_root, consumed_inputs=dedup_consumed
    )
    return res
