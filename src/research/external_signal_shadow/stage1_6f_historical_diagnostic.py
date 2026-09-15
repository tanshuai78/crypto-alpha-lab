"""Stage 1.6F Denominator reconstruction, deterministic matching, windows, and descriptive reducers."""

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
    VerifiedMarketEvidence,
    parse_delisting_contracts,
    parse_delisting_notices,
    parse_parent_audit_outcomes,
)

ALL_PERMISSION_FLAGS_FALSE: Dict[str, bool] = {
    "RISK_LIVE_TRADING_ENABLED": False,
    "trade_signal_allowed": False,
    "paper_trading_allowed": False,
    "live_trading_allowed": False,
    "execution_engine_allowed": False,
    "private_api_allowed": False,
    "authenticated_api_allowed": False,
    "order_api_allowed": False,
    "alpha_interpretation_allowed": False,
    "execution_feasibility_claim_allowed": False,
    "net_cost_or_profit_claim_allowed": False,
    "replay_allowed": False,
    "point_in_time_directional_replay_allowed": False,
}

DESCRIPTIVE_METRIC_STATUS_NAMES: Tuple[str, ...] = (
    "diagnostic_incomplete",
    "descriptive_only",
    "protocol_executed_complete",
    "price_path_unavailable",
    "basis_unavailable",
    "mark_basis_unavailable",
    "funding_unavailable",
    "oi_unavailable",
    "visible_depth_unavailable",
    "agg_trade_unavailable",
    "settlement_value_unavailable_insufficient_1s_index",
)


@dataclass(frozen=True)
class DenominatorRow:
    """Complete C denominator row preserving eligibility and linkage."""
    parent_article_id: str
    contract_id: str
    symbol: str
    input_export_id: str
    input_manifest_sha256: str
    source_export_receipt_sha256: str
    quote_asset: str
    settlement_asset: str
    margin_family: str
    contract_type: str
    underlying_family: str
    eligibility_passed: bool
    ineligibility_reasons: Tuple[str, ...]
    t_pub_ms: Optional[int]
    t_settle_ms: Optional[int]
    system_available_at_ms: Optional[int] = None
    fact_available_at_ms: Optional[int] = None
    capture_time_status: str = "historical_unknown"
    match_status: str = "unmatched"
    selected_controls: Tuple[Dict[str, Any], ...] = ()


@dataclass(frozen=True)
class DiagnosticMetricResult:
    """Individual diagnostic metric result strictly restricted to descriptive summaries."""
    metric_name: str
    window: str
    status: str
    observed_interval: Dict[str, Any]
    descriptors: Dict[str, Any]
    authority_flags: Dict[str, bool]
    parent_article_id: str = ""
    contract_id: str = ""
    symbol: str = ""
    original_interval: Dict[str, Any] = None  # type: ignore
    controls_or_exclusion_reasons: Tuple[Any, ...] = ()


def reconstruct_denominator(verified_c: VerifiedCInput) -> List[DenominatorRow]:
    """
    Reconstructs complete C denominator from verified retained C bytes.
    Preserves parent failures, ineligible child rows, missing times, out of range rows.
    No input row disappears.
    """
    outcomes = parse_parent_audit_outcomes(verified_c)
    contracts = parse_delisting_contracts(verified_c)
    notices = parse_delisting_notices(verified_c)

    outcomes_by_parent: Dict[str, Dict[str, Any]] = {
        (o.get("source_article_id") or o.get("parent_article_id")): o
        for o in outcomes
        if (o.get("source_article_id") or o.get("parent_article_id"))
    }
    notices_by_parent: Dict[str, Dict[str, Any]] = {
        (n.get("source_article_id") or n.get("parent_article_id")): n
        for n in notices
        if (n.get("source_article_id") or n.get("parent_article_id"))
    }

    rows: List[DenominatorRow] = []

    for c in contracts:
        parent_id = c["parent_article_id"]
        contract_id = c["contract_id"]
        symbol = c.get("canonical_symbol") or c["symbol"]

        outcome = outcomes_by_parent.get(parent_id)
        notice = notices_by_parent.get(parent_id)

        reasons: List[str] = []
        if outcome is None:
            reasons.append("parent_outcome_missing")
        else:
            if outcome.get("source_integrity_parent_pass") is not True:
                reasons.append("parent_source_integrity_failed")
            if outcome.get("detail_authority_status") != "trusted":
                reasons.append("parent_detail_not_trusted")
            if outcome.get("parent_declaration_status") != "complete":
                reasons.append("parent_declaration_incomplete")
            if outcome.get("mapping_status") != "pass":
                reasons.append("parent_mapping_failed")
            if outcome.get("classification_status") != "in_scope":
                reasons.append("parent_classification_out_of_scope")

        quote_asset = c.get("quote_asset")
        if not isinstance(quote_asset, str) or not quote_asset:
            reasons.append("quote_asset_missing")
            quote_asset_str = ""
        else:
            quote_asset_str = quote_asset
            if quote_asset != "USDT":
                reasons.append(f"ineligible_quote_asset_{quote_asset}")

        settlement_asset = c.get("settlement_asset")
        if not isinstance(settlement_asset, str) or not settlement_asset:
            reasons.append("settlement_asset_missing")
            settlement_asset_str = ""
        else:
            settlement_asset_str = settlement_asset
            if settlement_asset != "USDT":
                reasons.append(f"ineligible_settlement_asset_{settlement_asset}")

        margin_family = c.get("margin_family")
        if not isinstance(margin_family, str) or not margin_family:
            reasons.append("margin_family_missing")
            margin_family_str = ""
        else:
            margin_family_str = margin_family
            if margin_family not in ("USD_M", "USDM"):
                reasons.append(f"ineligible_margin_family_{margin_family}")

        contract_type = c.get("contract_type")
        if not isinstance(contract_type, str) or not contract_type:
            reasons.append("contract_type_missing")
            contract_type_str = ""
        else:
            contract_type_str = contract_type
            if contract_type != "PERPETUAL":
                reasons.append(f"ineligible_contract_type_{contract_type}")

        underlying_family = c.get("underlying_family")
        if not isinstance(underlying_family, str) or not underlying_family:
            reasons.append("underlying_family_missing")
            underlying_family_str = ""
        else:
            underlying_family_str = underlying_family

        if c.get("source_audit_eligible") is not True:
            reasons.append("contract_not_eligible")

        eligibility_passed = len(reasons) == 0

        # Extract publication timestamp
        t_pub_ms: Optional[int] = None
        for entity in (outcome, notice):
            if entity:
                for date_key in ("source_published_at_ms", "publish_date"):
                    if date_key in entity and isinstance(entity[date_key], int):
                        t_pub_ms = entity[date_key]
                        break
            if t_pub_ms is not None:
                break

        # Extract settlement timestamp from schedule facts
        t_settle_ms: Optional[int] = None
        settle_fact = c.get("settlement_time")
        if isinstance(settle_fact, dict) and settle_fact.get("fact_parse_status") == "present":
            t_settle_ms = settle_fact.get("timestamp_ms")

        rows.append(
            DenominatorRow(
                parent_article_id=parent_id,
                contract_id=contract_id,
                symbol=symbol,
                input_export_id=verified_c.input_export_id,
                input_manifest_sha256=verified_c.input_manifest_sha256,
                source_export_receipt_sha256=verified_c.source_export_receipt_sha256,
                quote_asset=quote_asset_str,
                settlement_asset=settlement_asset_str,
                margin_family=margin_family_str,
                contract_type=contract_type_str,
                underlying_family=underlying_family_str,
                eligibility_passed=eligibility_passed,
                ineligibility_reasons=tuple(reasons),
                t_pub_ms=t_pub_ms,
                t_settle_ms=t_settle_ms,
                system_available_at_ms=None,
                fact_available_at_ms=None,
                capture_time_status="historical_unknown",
                match_status="unmatched",
                selected_controls=(),
            )
        )

    return rows


def project_denominator_row(
    row: DenominatorRow,
    *,
    substitute_available_at_ms: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Implements Parent INV-F02 projection matrix.
    Null availability timestamps and capture_time_status=historical_unknown must be preserved unchanged.
    Any attempt to substitute Tpub or download timestamps must raise ValueError.
    """
    if substitute_available_at_ms is not None:
        raise ValueError("availability_substitution_forbidden: cannot substitute Tpub or download timestamp")

    if row.system_available_at_ms is not None or row.fact_available_at_ms is not None:
        raise ValueError("availability_timestamp_must_be_null_in_historical_c")
    if row.capture_time_status != "historical_unknown":
        raise ValueError("capture_time_status_must_be_historical_unknown")

    record: Dict[str, Any] = {
        "schema_version": "stage1_6f_historical_mechanism_diagnostic_v1",
        "parent_article_id": row.parent_article_id,
        "contract_id": row.contract_id,
        "symbol": row.symbol,
        "input_export_id": row.input_export_id,
        "input_manifest_sha256": row.input_manifest_sha256,
        "source_export_receipt_sha256": row.source_export_receipt_sha256,
        "quote_asset": row.quote_asset,
        "settlement_asset": row.settlement_asset,
        "margin_family": row.margin_family,
        "contract_type": row.contract_type,
        "underlying_family": row.underlying_family,
        "eligibility_passed": row.eligibility_passed,
        "ineligibility_reasons": list(row.ineligibility_reasons),
        "t_pub_ms": row.t_pub_ms,
        "t_settle_ms": row.t_settle_ms,
        "system_available_at_ms": None,
        "fact_available_at_ms": None,
        "capture_time_status": "historical_unknown",
        "match_status": row.match_status,
        "selected_controls": list(row.selected_controls),
    }
    # Bind all 13 safety flags
    record.update(ALL_PERMISSION_FLAGS_FALSE)
    return record


def match_control_candidates(
    event_volatility: float,
    event_median_quote_volume: float,
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Pure matcher implementing Parent Section 6 and Delta INV-FD04.
    - Volatility ratio R_vol = cand_vol / event_vol in [0.5, 2.0]
    - Volume ratio R_volm = cand_volm / event_volm in [0.5, 2.0]
    - Distance D = abs(ln(R_vol)) + abs(ln(R_volm))
    - Sorted by D ascending, canonical symbol tie-break.
    - Select top 1-3 controls with equal weights (1.0 / K).
    """
    if event_volatility <= 0 or event_median_quote_volume <= 0:
        return {"match_status": "unmatched", "selected_controls": []}

    passed_candidates: List[Dict[str, Any]] = []

    for c in candidates:
        if c.get("is_valid") is False:
            continue
        c_vol = float(c.get("volatility") or 0.0)
        c_volm = float(c.get("median_quote_volume") or 0.0)
        sym = str(c.get("symbol") or "")
        if c_vol <= 0 or c_volm <= 0 or not sym:
            continue

        r_vol = c_vol / event_volatility
        r_volm = c_volm / event_median_quote_volume

        # Exact ratio bounds [0.5, 2.0]
        if not (0.5 <= r_vol <= 2.0 and 0.5 <= r_volm <= 2.0):
            continue

        distance = abs(math.log(r_vol)) + abs(math.log(r_volm))
        passed_candidates.append({
            "symbol": sym,
            "volatility": c_vol,
            "median_quote_volume": c_volm,
            "volatility_ratio": r_vol,
            "volume_ratio": r_volm,
            "distance": distance,
        })

    if not passed_candidates:
        return {"match_status": "unmatched", "selected_controls": []}

    # Deterministic sort: distance ascending, symbol alphabetically
    passed_candidates.sort(key=lambda x: (x["distance"], x["symbol"]))

    top_k = passed_candidates[:3]
    k = len(top_k)
    weight = 1.0 / k

    selected: List[Dict[str, Any]] = []
    for cand in top_k:
        selected.append({
            "symbol": cand["symbol"],
            "distance": cand["distance"],
            "weight": weight,
            "volatility_ratio": cand["volatility_ratio"],
            "volume_ratio": cand["volume_ratio"],
        })

    return {
        "match_status": "matched",
        "selected_controls": selected,
    }


def resolve_settlement_rule(
    symbol: str,
    event_time_ms: int,
    rule_mapping_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Resolves settlement rule version and parameter specifications from official settlement rule mapping."""
    boundary_ms = 1731312000000  # 2024-11-11T08:00:00Z
    if event_time_ms < boundary_ms:
        return {
            "rule_version": "V1",
            "effective_boundary_ms": boundary_ms,
            "sample_interval_seconds": 1,
            "sample_window_minutes": 30,
            "expected_sample_count": 1800,
            "official_scope": "last_30_min_1s_twap",
        }
    return {
        "rule_version": "V2",
        "effective_boundary_ms": boundary_ms,
        "sample_interval_seconds": 1,
        "sample_window_minutes": 60,
        "expected_sample_count": 3600,
        "official_scope": "last_60_min_1s_twap",
    }


def compute_window_intervals(
    t_pub_ms: int,
    t_settle_ms: Optional[int],
) -> Dict[str, Any]:
    """Computes W1 and W2 intervals and records truncation by Tpub according to Parent 4.3."""
    w1_start_ms = t_pub_ms
    w1_end_ms = t_pub_ms + 12 * 3600000

    if t_settle_ms is None:
        return {
            "w1_start_ms": w1_start_ms,
            "w1_end_ms": w1_end_ms,
            "nominal_w2_start_ms": None,
            "nominal_w2_end_ms": None,
            "paired_w2_start_ms": None,
            "paired_w2_end_ms": None,
            "is_truncated_by_tpub": True,
            "truncation_reason": "settlement_time_missing",
        }

    nominal_w2_start_ms = t_settle_ms - 24 * 3600000
    nominal_w2_end_ms = t_settle_ms

    if t_settle_ms <= t_pub_ms:
        return {
            "w1_start_ms": w1_start_ms,
            "w1_end_ms": w1_end_ms,
            "nominal_w2_start_ms": nominal_w2_start_ms,
            "nominal_w2_end_ms": nominal_w2_end_ms,
            "paired_w2_start_ms": None,
            "paired_w2_end_ms": None,
            "is_truncated_by_tpub": True,
            "truncation_reason": "settlement_before_or_at_publication",
        }

    if t_pub_ms > nominal_w2_start_ms:
        return {
            "w1_start_ms": w1_start_ms,
            "w1_end_ms": w1_end_ms,
            "nominal_w2_start_ms": nominal_w2_start_ms,
            "nominal_w2_end_ms": nominal_w2_end_ms,
            "paired_w2_start_ms": t_pub_ms,
            "paired_w2_end_ms": t_settle_ms,
            "is_truncated_by_tpub": True,
            "truncation_reason": "t_pub_after_nominal_w2_start",
        }

    return {
        "w1_start_ms": w1_start_ms,
        "w1_end_ms": w1_end_ms,
        "nominal_w2_start_ms": nominal_w2_start_ms,
        "nominal_w2_end_ms": nominal_w2_end_ms,
        "paired_w2_start_ms": nominal_w2_start_ms,
        "paired_w2_end_ms": nominal_w2_end_ms,
        "is_truncated_by_tpub": False,
        "truncation_reason": None,
    }


def compute_descriptive_metrics(
    symbol: str,
    t_pub_ms: int,
    t_settle_ms: Optional[int],
    selected_controls: List[str],
    verified_market: VerifiedMarketEvidence,
    parent_article_id: str = "",
    contract_id: str = "",
    ineligibility_reasons: Tuple[str, ...] = ()
) -> List[DiagnosticMetricResult]:
    """
    Computes pure descriptive metric results according to Delta Section 5.2.
    Emits raw descriptors only, exact unavailable statuses, and zero financial claims.
    """
    windows = compute_window_intervals(t_pub_ms, t_settle_ms)
    results: List[DiagnosticMetricResult] = []

    # 1. Price path in W1
    w1_start = windows["w1_start_ms"]
    w1_end = windows["w1_end_ms"]
    raw_event_1h = verified_market.get_series("klines_1h", symbol) or ()
    w1_event_bars = [b for b in raw_event_1h if w1_start <= b["open_time"] < w1_end]

    if not w1_event_bars:
        results.append(
            DiagnosticMetricResult(
                metric_name="price_path",
                window="W1",
                status="price_path_unavailable",
                observed_interval={"w1_start_ms": w1_start, "w1_end_ms": w1_end, "bar_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        first_c = w1_event_bars[0]["close"]
        last_c = w1_event_bars[-1]["close"]
        event_chg_bps = 10000.0 * (last_c / first_c - 1.0)
        event_timestamps = {b["open_time"] for b in w1_event_bars}

        # Check paired controls
        controls_share_timestamps = True
        control_bps_list: List[float] = []
        for ctrl_sym in selected_controls:
            c_bars = [b for b in (verified_market.get_series("klines_1h", ctrl_sym) or ()) if w1_start <= b["open_time"] < w1_end]
            if {b["open_time"] for b in c_bars} != event_timestamps or not c_bars:
                controls_share_timestamps = False
                break
            control_bps_list.append(10000.0 * (c_bars[-1]["close"] / c_bars[0]["close"] - 1.0))

        paired_diff_bps: Optional[float] = None
        if controls_share_timestamps and control_bps_list:
            avg_ctrl_bps = sum(control_bps_list) / len(control_bps_list)
            paired_diff_bps = event_chg_bps - avg_ctrl_bps

        results.append(
            DiagnosticMetricResult(
                metric_name="price_path",
                window="W1",
                status="descriptive_only",
                observed_interval={
                    "w1_start_ms": w1_start,
                    "w1_end_ms": w1_end,
                    "first_observed_at_ms": w1_event_bars[0]["open_time"],
                    "last_observed_at_ms": w1_event_bars[-1]["open_time"],
                    "bar_count": len(w1_event_bars),
                },
                descriptors={
                    "first_close": first_c,
                    "last_close": last_c,
                    "price_change_bps": event_chg_bps,
                    "event_minus_control_bps": paired_diff_bps,
                    "paired_diff_censored": not controls_share_timestamps,
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 2. Perp / index basis in W1
    raw_index_1h = verified_market.get_series("index_price_1h", symbol) or ()
    w1_index_bars = {b["open_time"]: b for b in raw_index_1h if w1_start <= b["open_time"] < w1_end}
    aligned_basis_points: List[float] = []
    for b in w1_event_bars:
        t = b["open_time"]
        if t in w1_index_bars and w1_index_bars[t]["close"] > 0:
            aligned_basis_points.append(10000.0 * (b["close"] / w1_index_bars[t]["close"] - 1.0))

    if not aligned_basis_points:
        results.append(
            DiagnosticMetricResult(
                metric_name="basis",
                window="W1",
                status="basis_unavailable",
                observed_interval={"bar_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        results.append(
            DiagnosticMetricResult(
                metric_name="basis",
                window="W1",
                status="descriptive_only",
                observed_interval={"bar_count": len(aligned_basis_points)},
                descriptors={
                    "first_basis_bps": aligned_basis_points[0],
                    "last_basis_bps": aligned_basis_points[-1],
                    "median_basis_bps": sorted(aligned_basis_points)[len(aligned_basis_points) // 2],
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 3. Mark / index basis in W1
    raw_mark_1h = verified_market.get_series("mark_price_1h", symbol) or ()
    w1_mark_bars = {b["open_time"]: b for b in raw_mark_1h if w1_start <= b["open_time"] < w1_end}
    aligned_mark_basis: List[float] = []
    for t, m_bar in w1_mark_bars.items():
        if t in w1_index_bars and w1_index_bars[t]["close"] > 0:
            aligned_mark_basis.append(10000.0 * (m_bar["close"] / w1_index_bars[t]["close"] - 1.0))

    if not aligned_mark_basis:
        results.append(
            DiagnosticMetricResult(
                metric_name="mark_basis",
                window="W1",
                status="mark_basis_unavailable",
                observed_interval={"bar_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        results.append(
            DiagnosticMetricResult(
                metric_name="mark_basis",
                window="W1",
                status="descriptive_only",
                observed_interval={"bar_count": len(aligned_mark_basis)},
                descriptors={
                    "first_mark_basis_bps": aligned_mark_basis[0],
                    "last_mark_basis_bps": aligned_mark_basis[-1],
                    "median_mark_basis_bps": sorted(aligned_mark_basis)[len(aligned_mark_basis) // 2],
                    "note": "non_tradable_risk_price_basis_only",
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 4. Funding in W1
    raw_funding = verified_market.get_series("funding_rate", symbol) or ()
    w1_funding = [f for f in raw_funding if w1_start <= f["calc_time"] < w1_end]
    if not w1_funding:
        results.append(
            DiagnosticMetricResult(
                metric_name="funding",
                window="W1",
                status="funding_unavailable",
                observed_interval={"observation_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        obs_tuples = [(f["calc_time"], f["funding_interval_hours"], f["last_funding_rate"]) for f in w1_funding]
        results.append(
            DiagnosticMetricResult(
                metric_name="funding",
                window="W1",
                status="descriptive_only",
                observed_interval={"observation_count": len(w1_funding)},
                descriptors={
                    "funding_observations": obs_tuples,
                    "count": len(obs_tuples),
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 5. Open Interest in W1
    raw_metrics = verified_market.get_series("metrics_5m", symbol) or ()
    w1_metrics = [m for m in raw_metrics if w1_start <= m["create_time"] < w1_end]
    if not w1_metrics:
        results.append(
            DiagnosticMetricResult(
                metric_name="open_interest",
                window="W1",
                status="oi_unavailable",
                observed_interval={"bar_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        results.append(
            DiagnosticMetricResult(
                metric_name="open_interest",
                window="W1",
                status="descriptive_only",
                observed_interval={"bar_count": len(w1_metrics)},
                descriptors={
                    "first_oi_value": w1_metrics[0]["sum_open_interest_value"],
                    "last_oi_value": w1_metrics[-1]["sum_open_interest_value"],
                    "delta_oi_value": w1_metrics[-1]["sum_open_interest_value"] - w1_metrics[0]["sum_open_interest_value"],
                    "latest_toptrader_long_short_ratio": w1_metrics[-1]["sum_toptrader_long_short_ratio"],
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 6. Visible depth in W1
    raw_depth = verified_market.get_series("book_depth", symbol) or ()
    w1_depth = [d for d in raw_depth if w1_start <= d["timestamp"] < w1_end]
    if not w1_depth:
        results.append(
            DiagnosticMetricResult(
                metric_name="visible_depth",
                window="W1",
                status="visible_depth_unavailable",
                observed_interval={"snapshot_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        depth_by_pct: Dict[float, List[float]] = defaultdict(list)
        for d in w1_depth:
            depth_by_pct[d["percentage"]].append(d["notional"])
        descriptors_by_pct: Dict[str, Any] = {}
        for pct, notionals in depth_by_pct.items():
            descriptors_by_pct[f"pct_{int(pct)}"] = {
                "count": len(notionals),
                "first_notional": notionals[0],
                "last_notional": notionals[-1],
                "median_notional": sorted(notionals)[len(notionals) // 2],
            }
        results.append(
            DiagnosticMetricResult(
                metric_name="visible_depth",
                window="W1",
                status="descriptive_only",
                observed_interval={"snapshot_count": len(w1_depth)},
                descriptors={
                    "percentage_levels": descriptors_by_pct,
                    "note": "visible_discrete_depth_ladder_proxy_only_no_slippage",
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 7. Agg trades in W1
    raw_trades = verified_market.get_series("agg_trades", symbol) or ()
    w1_trades = [t for t in raw_trades if w1_start <= t["transact_time"] < w1_end]
    if not w1_trades:
        results.append(
            DiagnosticMetricResult(
                metric_name="agg_trades",
                window="W1",
                status="agg_trade_unavailable",
                observed_interval={"trade_count": 0},
                descriptors={},
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )
    else:
        total_vol = sum(t["price"] * t["quantity"] for t in w1_trades)
        bm_true = [t for t in w1_trades if t["is_buyer_maker"]]
        bm_false = [t for t in w1_trades if not t["is_buyer_maker"]]
        results.append(
            DiagnosticMetricResult(
                metric_name="agg_trades",
                window="W1",
                status="descriptive_only",
                observed_interval={"trade_count": len(w1_trades)},
                descriptors={
                    "total_trades": len(w1_trades),
                    "total_notional": total_vol,
                    "buyer_maker_true_count": len(bm_true),
                    "buyer_maker_true_notional": sum(t["price"] * t["quantity"] for t in bm_true),
                    "buyer_maker_false_count": len(bm_false),
                    "buyer_maker_false_notional": sum(t["price"] * t["quantity"] for t in bm_false),
                },
                authority_flags=ALL_PERMISSION_FLAGS_FALSE,
            )
        )

    # 8. Settlement mechanism
    settle_rule = resolve_settlement_rule(
        symbol=symbol,
        event_time_ms=t_pub_ms,
        rule_mapping_data=verified_market.auxiliary_artifacts.get("settlement_rule_mapping_37contracts.json", {}),
    )
    results.append(
        DiagnosticMetricResult(
            metric_name="settlement_mechanism",
            window="W2",
            status="settlement_value_unavailable_insufficient_1s_index",
            observed_interval={"sample_count": 0},
            descriptors={
                "rule_version": settle_rule["rule_version"],
                "expected_sample_count": settle_rule["expected_sample_count"],
                "sample_interval_seconds": settle_rule["sample_interval_seconds"],
                "sample_window_minutes": settle_rule["sample_window_minutes"],
                "note": "1h_index_is_insufficient_to_reconstruct_historical_1s_settlement_twap",
            },
            authority_flags=ALL_PERMISSION_FLAGS_FALSE,
        )
    )

    w1_original = {
        "requested_window": "W1",
        "start_ms": windows["w1_start_ms"],
        "end_ms": windows["w1_end_ms"],
    }
    w2_original = {
        "requested_window": "W2",
        "nominal_start_ms": windows["nominal_w2_start_ms"],
        "nominal_end_ms": windows["nominal_w2_end_ms"],
        "paired_start_ms": windows["paired_w2_start_ms"],
        "paired_end_ms": windows["paired_w2_end_ms"],
        "is_truncated_by_tpub": windows["is_truncated_by_tpub"],
        "truncation_reason": windows["truncation_reason"],
    }
    controls_or_reasons = (
        tuple(selected_controls)
        if selected_controls
        else (tuple(ineligibility_reasons) if ineligibility_reasons else ("unmatched",))
    )

    final_results: List[DiagnosticMetricResult] = []
    for r in results:
        orig = w1_original if r.window == "W1" else w2_original
        final_results.append(
            DiagnosticMetricResult(
                metric_name=r.metric_name,
                window=r.window,
                status=r.status,
                observed_interval=r.observed_interval,
                descriptors=r.descriptors,
                authority_flags=r.authority_flags,
                parent_article_id=parent_article_id,
                contract_id=contract_id,
                symbol=symbol,
                original_interval=orig,
                controls_or_exclusion_reasons=controls_or_reasons,
            )
        )

    return final_results
