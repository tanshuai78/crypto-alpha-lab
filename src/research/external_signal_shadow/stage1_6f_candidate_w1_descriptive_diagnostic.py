"""Candidate W1 descriptive diagnostic reducer.

Invariants: INV-CA04, INV-CA05, INV-CA06, INV-CA08, INV-CA11, INV-CA12.
Zero-permission boundary: RISK_LIVE_TRADING_ENABLED = False.
Descriptive transformations only; no signal, alpha, PnL, or execution logic.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from src.research.external_signal_shadow.stage1_6f_candidate_evidence_source import (
    CandidateIdentity,
    PublicationAuthority,
    VerifiedCandidateEvidence,
    ceil_step,
    evaluate_coverage,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    VerifiedCInput,
)

DENOMINATOR_SCHEMA_VERSION = "stage1_6f_candidate_w1_denominator_v1"
METRIC_SCHEMA_VERSION = "stage1_6f_candidate_w1_metric_v1"

EXPECTED_19_METRIC_HORIZON_TUPLES: List[Tuple[str, str]] = [
    ("hourly_bar_observation", "H1"),
    ("price_path", "H4"),
    ("price_path", "H12"),
    ("perp_index_basis", "H4"),
    ("perp_index_basis", "H12"),
    ("mark_index_basis", "H4"),
    ("mark_index_basis", "H12"),
    ("funding_observations", "H1"),
    ("funding_observations", "H4"),
    ("funding_observations", "H12"),
    ("open_interest", "H1"),
    ("open_interest", "H4"),
    ("open_interest", "H12"),
    ("visible_depth_proxy", "H1"),
    ("visible_depth_proxy", "H4"),
    ("visible_depth_proxy", "H12"),
    ("agg_trade_observations", "H1"),
    ("agg_trade_observations", "H4"),
    ("agg_trade_observations", "H12"),
]

HORIZON_MS: Dict[str, int] = {
    "H1": 3_600_000,
    "H4": 14_400_000,
    "H12": 43_200_000,
}

METRIC_REQUIRED_FAMILIES: Dict[str, List[str]] = {
    "hourly_bar_observation": ["klines_1h"],
    "price_path": ["klines_1h"],
    "perp_index_basis": ["index_price_1h", "klines_1h"],
    "mark_index_basis": ["index_price_1h", "mark_price_1h"],
    "funding_observations": ["funding_rate"],
    "open_interest": ["metrics_5m"],
    "visible_depth_proxy": ["book_depth"],
    "agg_trade_observations": ["agg_trades"],
}

FAMILY_TIMESTAMP_FIELDS: Dict[str, str] = {
    "klines_1h": "open_time",
    "index_price_1h": "open_time",
    "mark_price_1h": "open_time",
    "premium_index_1h": "open_time",
    "metrics_5m": "create_time",
    "funding_rate": "calc_time",
    "book_depth": "timestamp",
    "agg_trades": "transact_time",
}

BOOK_DEPTH_REQUIRED_PERCENTAGES: Set[int] = {-5, -4, -3, -2, -1, 1, 2, 3, 4, 5}


@dataclass(frozen=True)
class DenominatorRow:
    schema_version: str
    parent_article_id: str
    contract_id: str
    canonical_symbol: str
    eligibility_passed: bool
    ineligibility_reasons: List[str]
    publication_time_authority: str
    t_pub_ms: int
    point_in_time_source_validated: bool
    capture_time_status: str
    system_available_at_ms: Optional[int]
    fact_available_at_ms: Optional[int]
    candidate_root_relative_path: str
    candidate_manifest_sha256: str
    authority_flags: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "parent_article_id": self.parent_article_id,
            "contract_id": self.contract_id,
            "canonical_symbol": self.canonical_symbol,
            "eligibility_passed": self.eligibility_passed,
            "ineligibility_reasons": self.ineligibility_reasons,
            "publication_time_authority": self.publication_time_authority,
            "t_pub_ms": self.t_pub_ms,
            "point_in_time_source_validated": self.point_in_time_source_validated,
            "capture_time_status": self.capture_time_status,
            "system_available_at_ms": self.system_available_at_ms,
            "fact_available_at_ms": self.fact_available_at_ms,
            "candidate_root_relative_path": self.candidate_root_relative_path,
            "candidate_manifest_sha256": self.candidate_manifest_sha256,
            "authority_flags": self.authority_flags,
        }


@dataclass(frozen=True)
class MetricRecord:
    schema_version: str
    parent_article_id: str
    contract_id: str
    canonical_symbol: str
    metric_name: str
    horizon: str
    requested_interval: Dict[str, int]
    publication_time_authority: str
    t_pub_ms: int
    point_in_time_source_validated: bool
    capture_time_status: str
    system_available_at_ms: Optional[int]
    fact_available_at_ms: Optional[int]
    source_family_audits: List[Dict[str, Any]]
    source_logical_archive_record_ids: List[str]
    gate_failures: List[str]
    status: str
    descriptors: Dict[str, Any]
    authority_flags: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "parent_article_id": self.parent_article_id,
            "contract_id": self.contract_id,
            "canonical_symbol": self.canonical_symbol,
            "metric_name": self.metric_name,
            "horizon": self.horizon,
            "requested_interval": self.requested_interval,
            "publication_time_authority": self.publication_time_authority,
            "t_pub_ms": self.t_pub_ms,
            "point_in_time_source_validated": self.point_in_time_source_validated,
            "capture_time_status": self.capture_time_status,
            "system_available_at_ms": self.system_available_at_ms,
            "fact_available_at_ms": self.fact_available_at_ms,
            "source_family_audits": self.source_family_audits,
            "source_logical_archive_record_ids": self.source_logical_archive_record_ids,
            "gate_failures": self.gate_failures,
            "status": self.status,
            "descriptors": self.descriptors,
            "authority_flags": self.authority_flags,
        }


@dataclass(frozen=True)
class CandidateW1DiagnosticResult:
    denominator_rows: List[DenominatorRow]
    metric_records: List[MetricRecord]


def reduce_hourly_bar_observation(
    bars: List[Dict[str, Any]],
    coverage_admissible: bool,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce H1 hourly bar observation."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")
    if len(bars) < 1:
        failures.append("horizon_grid_incomplete")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    first_bar = bars[0]
    last_bar = bars[-1]
    descriptors = {
        "first_open_time_ms": first_bar["open_time"],
        "first_close_time_ms": first_bar["close_time"],
        "first_open": first_bar["open"],
        "first_high": first_bar["high"],
        "first_low": first_bar["low"],
        "first_close": first_bar["close"],
        "last_open_time_ms": last_bar["open_time"],
        "last_close_time_ms": last_bar["close_time"],
        "last_open": last_bar["open"],
        "last_high": last_bar["high"],
        "last_low": last_bar["low"],
        "last_close": last_bar["close"],
        "row_count": len(bars),
        "note": "hourly_bar_open_time_in_window_observation_only",
    }
    return "descriptive_only", descriptors, []


def reduce_price_path_metric(
    bars: List[Dict[str, Any]],
    coverage_admissible: bool,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce H4/H12 price path proxy."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")

    if len(bars) < 2:
        failures.append("insufficient_complete_post_publication_bars")
    else:
        first_close = bars[0]["close"]
        if first_close == 0.0 or abs(first_close) < 1e-12:
            failures.append("zero_price_path_denominator")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    first_bar = bars[0]
    last_bar = bars[-1]
    first_close = first_bar["close"]
    last_close = last_bar["close"]
    change_bps = 10000.0 * (last_close / first_close - 1.0)

    descriptors = {
        "first_close_time_ms": first_bar["close_time"],
        "last_close_time_ms": last_bar["close_time"],
        "first_complete_bar_close": first_close,
        "last_complete_bar_close": last_close,
        "bar_close_change_bps": change_bps,
        "bar_count": len(bars),
        "note": "coarse_complete_post_publication_bar_close_proxy",
    }
    return "descriptive_only", descriptors, []


def reduce_basis_metric(
    perp_or_mark_bars: List[Dict[str, Any]],
    index_bars: List[Dict[str, Any]],
    coverage_admissible: bool,
    is_mark: bool = False,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce perp/index or mark/index basis."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")

    p_map = {b["open_time"]: b for b in perp_or_mark_bars}
    i_map = {b["open_time"]: b for b in index_bars}
    aligned_times = sorted(set(p_map.keys()) & set(i_map.keys()))

    if len(aligned_times) < 1:
        failures.append("missing_aligned_complete_bars")
    else:
        if any(i_map[t]["close"] <= 0 for t in aligned_times):
            failures.append("missing_positive_index_close")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    bps_series = [
        10000.0 * (p_map[t]["close"] / i_map[t]["close"] - 1.0)
        for t in aligned_times
    ]
    if is_mark:
        descriptors = {
            "first_mark_basis_bps": bps_series[0],
            "last_mark_basis_bps": bps_series[-1],
            "median_mark_basis_bps": statistics.median(bps_series),
            "bar_count": len(bps_series),
            "note": "non_tradable_reference_only",
        }
    else:
        descriptors = {
            "first_basis_bps": bps_series[0],
            "last_basis_bps": bps_series[-1],
            "median_basis_bps": statistics.median(bps_series),
            "bar_count": len(bps_series),
            "note": "perp_index_reference_basis_only",
        }
    return "descriptive_only", descriptors, []


def reduce_funding_observations(
    rows: List[Dict[str, Any]],
    coverage_admissible: bool,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce discrete funding observations."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")
    if len(rows) < 1:
        failures.append("no_horizon_funding_observation")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    sorted_rows = sorted(rows, key=lambda x: x["calc_time"])
    obs = [
        {
            "calc_time": r["calc_time"],
            "funding_interval_hours": r["funding_interval_hours"],
            "last_funding_rate": r["last_funding_rate"],
        }
        for r in sorted_rows
    ]
    descriptors = {
        "observations": obs,
        "count": len(obs),
        "note": "discrete_observations_only_no_carry_pnl",
    }
    return "descriptive_only", descriptors, []


def reduce_open_interest(
    rows: List[Dict[str, Any]],
    coverage_admissible: bool,
    expected_start_ms: int,
    expected_end_ms: int,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce open interest observations."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")

    expected_grid = list(range(expected_start_ms, expected_end_ms, 300_000))
    obs_creates = [r["create_time"] for r in rows]
    obs_counts: Dict[int, int] = {}
    for c in obs_creates:
        obs_counts[c] = obs_counts.get(c, 0) + 1

    if any(cnt > 1 for cnt in obs_counts.values()):
        failures.append("horizon_duplicate_or_conflict")
    if len(set(expected_grid) - set(obs_counts.keys())) > 0 or len(rows) < 1:
        failures.append("horizon_grid_incomplete")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    sorted_rows = sorted(rows, key=lambda x: x["create_time"])
    first_oi = sorted_rows[0]["sum_open_interest_value"]
    last_oi = sorted_rows[-1]["sum_open_interest_value"]
    delta_oi = last_oi - first_oi
    latest_ratio = sorted_rows[-1]["sum_toptrader_long_short_ratio"]

    descriptors = {
        "first_oi_value": first_oi,
        "last_oi_value": last_oi,
        "delta_oi_value": delta_oi,
        "latest_toptrader_long_short_ratio": latest_ratio,
        "bar_count": len(sorted_rows),
        "note": "raw_open_interest_observation_only",
    }
    return "descriptive_only", descriptors, []


def reduce_visible_depth_proxy(
    rows: List[Dict[str, Any]],
    coverage_admissible: bool,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce visible depth proxy."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")

    snapshots: Dict[int, Dict[int, float]] = {}
    for r in rows:
        snapshots.setdefault(r["timestamp"], {})[r["percentage"]] = r["notional"]

    complete_ts = [
        ts for ts, ladder in snapshots.items()
        if set(ladder.keys()) == BOOK_DEPTH_REQUIRED_PERCENTAGES
    ]

    if len(complete_ts) < 1:
        failures.append("no_complete_horizon_depth_ladder")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    sorted_ts = sorted(complete_ts)
    pct_keys = [
        (-5, "pct_neg_5"),
        (-4, "pct_neg_4"),
        (-3, "pct_neg_3"),
        (-2, "pct_neg_2"),
        (-1, "pct_neg_1"),
        (1, "pct_pos_1"),
        (2, "pct_pos_2"),
        (3, "pct_pos_3"),
        (4, "pct_pos_4"),
        (5, "pct_pos_5"),
    ]
    descriptors: Dict[str, Any] = {}
    for pct_val, key_name in pct_keys:
        series = [snapshots[ts][pct_val] for ts in sorted_ts]
        descriptors[key_name] = {
            "count": len(series),
            "first_notional": series[0],
            "last_notional": series[-1],
            "median_notional": statistics.median(series),
        }
    descriptors["note"] = "visible_discrete_depth_proxy_only_no_slippage"
    return "descriptive_only", descriptors, []


def reduce_agg_trade_observations(
    rows: List[Dict[str, Any]],
    coverage_admissible: bool,
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Reduce aggregate trade observations."""
    failures: List[str] = []
    if not coverage_admissible:
        failures.append("candidate_coverage_not_admissible")
    if len(rows) < 1:
        failures.append("no_horizon_agg_trade_observation")

    if failures:
        return "diagnostic_incomplete", {}, sorted(set(failures))

    true_rows = [r for r in rows if r.get("is_buyer_maker") is True]
    false_rows = [r for r in rows if r.get("is_buyer_maker") is False]

    total_notional = sum(r["price"] * r["quantity"] for r in rows)
    true_notional = sum(r["price"] * r["quantity"] for r in true_rows)
    false_notional = sum(r["price"] * r["quantity"] for r in false_rows)

    descriptors = {
        "total_trades": len(rows),
        "total_notional": total_notional,
        "buyer_maker_true_count": len(true_rows),
        "buyer_maker_true_notional": true_notional,
        "buyer_maker_false_count": len(false_rows),
        "buyer_maker_false_notional": false_notional,
        "note": "exchange_label_only_not_aggressor_inference",
    }
    return "descriptive_only", descriptors, []


def compute_candidate_w1_descriptive_diagnostic(
    *,
    verified_candidate: VerifiedCandidateEvidence,
    verified_c: VerifiedCInput,
    c_authority: Any,
    publication_authority: Mapping[CandidateIdentity, PublicationAuthority],
) -> CandidateW1DiagnosticResult:
    """Compute 41 denominator rows and 779 metric records across exactly 19 tuples."""
    # 1. Reconstruct denominator from verified C
    denom_source_rows = reconstruct_denominator(verified_c)
    denom_eligible_symbols = {r.symbol for r in denom_source_rows if r.eligibility_passed}

    # Intersect with candidate cohort
    cohort_symbols = set(verified_candidate.cohort)
    eligible_cohort = sorted(denom_eligible_symbols & cohort_symbols)
    if len(eligible_cohort) != 41:
        raise ValueError(f"Expected 41 cohort symbols, got {len(eligible_cohort)}")

    # Map candidate coverages and logical records by (parent_id, contract_id, symbol, window, metric)
    cov_map: Dict[Tuple[str, str, str, str, str], Dict[str, Any]] = {}
    for cov in verified_candidate.metric_window_coverages:
        k = (
            cov["parent_article_id"],
            cov["contract_id"],
            cov["canonical_symbol"],
            cov["window"],
            cov["metric"],
        )
        cov_map[k] = cov

    logical_map: Dict[Tuple[str, str, str, str, str], List[str]] = {}
    for l_rec in verified_candidate.logical_archive_records:
        k = (
            l_rec["parent_article_id"],
            l_rec["contract_id"],
            l_rec["canonical_symbol"],
            l_rec["window"],
            l_rec["metric"],
        )
        logical_map.setdefault(k, []).append(l_rec["logical_archive_record_id"])

    # 2. Build sorted DenominatorRow list
    denominator_rows: List[DenominatorRow] = []
    for ident, pub_auth in sorted(publication_authority.items(), key=lambda x: (x[0].parent_article_id, x[0].contract_id, x[0].canonical_symbol)):
        row = DenominatorRow(
            schema_version=DENOMINATOR_SCHEMA_VERSION,
            parent_article_id=ident.parent_article_id,
            contract_id=ident.contract_id,
            canonical_symbol=ident.canonical_symbol,
            eligibility_passed=True,
            ineligibility_reasons=[],
            publication_time_authority=pub_auth.publication_time_authority,
            t_pub_ms=pub_auth.t_pub_ms,
            point_in_time_source_validated=False,
            capture_time_status="historical_unknown",
            system_available_at_ms=None,
            fact_available_at_ms=None,
            candidate_root_relative_path=verified_candidate.candidate_root_relative_path,
            candidate_manifest_sha256=verified_candidate.manifest_sha256,
            authority_flags=dict(verified_candidate.authority_flags),
        )
        denominator_rows.append(row)

    # 3. Compute 19 tuples per denominator event -> exactly 779 metric records
    metric_records: List[MetricRecord] = []

    for denom in denominator_rows:
        pid = denom.parent_article_id
        cid = denom.contract_id
        sym = denom.canonical_symbol
        tpub = denom.t_pub_ms

        for metric_name, horizon in EXPECTED_19_METRIC_HORIZON_TUPLES:
            h_duration = HORIZON_MS[horizon]
            start_ms = tpub
            end_ms = tpub + h_duration
            req_interval = {"start_ms": start_ms, "end_ms": end_ms}

            required_fams = sorted(METRIC_REQUIRED_FAMILIES[metric_name])
            audits: List[Dict[str, Any]] = []

            for fam in required_fams:
                fam_key = (pid, cid, sym, "w1_shock_12h", fam)
                cov_entry = cov_map.get(fam_key, {})
                log_ids = sorted(set(logical_map.get(fam_key, [])))

                cov_status = cov_entry.get("coverage_status", "not_proven")
                cov_reason = cov_entry.get("reason", "unknown")
                ts_field = FAMILY_TIMESTAMP_FIELDS[fam]

                series_key = (pid, cid, sym, fam)
                all_rows = verified_candidate.parsed_series.get(series_key, [])
                h_rows = [r for r in all_rows if start_ms <= r[ts_field] < end_ms]
                h_rows.sort(key=lambda x: x[ts_field])
                row_cnt = len(h_rows)

                first_ts = h_rows[0][ts_field] if row_cnt > 0 else None
                last_ts = h_rows[-1][ts_field] if row_cnt > 0 else None

                # Compute duplicate, conflict, gap count for horizon
                if row_cnt > 0:
                    eval_res = evaluate_coverage(
                        metric=fam,
                        window="horizon",
                        window_start_ms=start_ms,
                        window_end_ms=end_ms,
                        rows=h_rows,
                        canonical_symbol=sym,
                        fetch_status="fetched_verified" if cov_status in {"window_observed", "rows_observed_continuity_not_proven"} else cov_status,
                        failure_reason=cov_reason,
                    )
                    dup_cnt = eval_res["duplicate_count"]
                    conf_cnt = eval_res["conflict_count"]
                    gap_cnt = eval_res["gap_count"]
                else:
                    dup_cnt = 0
                    conf_cnt = 0
                    gap_cnt = 1 if fam in {"klines_1h", "index_price_1h", "mark_price_1h", "metrics_5m"} else 0

                audit_item = {
                    "family_name": fam,
                    "coverage_status": cov_status,
                    "coverage_reason": cov_reason,
                    "logical_record_ids": log_ids,
                    "timestamp_field": ts_field,
                    "first_observed_ms": first_ts,
                    "last_observed_ms": last_ts,
                    "row_count": row_cnt,
                    "duplicate_count": dup_cnt,
                    "conflict_count": conf_cnt,
                    "gap_count": gap_cnt,
                }
                audits.append(audit_item)

            audits.sort(key=lambda a: a["family_name"])
            audit_log_union = sorted({lid for a in audits for lid in a["logical_record_ids"]})

            # Execute metric-specific reduction
            status = "diagnostic_incomplete"
            descriptors: Dict[str, Any] = {}
            gate_failures: List[str] = []

            if metric_name == "hourly_bar_observation":
                fam_cov = audits[0]["coverage_status"] == "window_observed"
                k_rows = [r for r in verified_candidate.parsed_series.get((pid, cid, sym, "klines_1h"), []) if start_ms <= r["open_time"] < end_ms]
                status, descriptors, gate_failures = reduce_hourly_bar_observation(
                    bars=k_rows,
                    coverage_admissible=fam_cov,
                )

            elif metric_name == "price_path":
                fam_cov = audits[0]["coverage_status"] == "window_observed"
                first_open = ceil_step(tpub, 3_600_000)
                complete_bars = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "klines_1h"), [])
                    if r["open_time"] >= first_open
                    and r["close_time"] == r["open_time"] + 3_600_000 - 1
                    and r["open_time"] + 3_600_000 <= end_ms
                ]
                complete_bars.sort(key=lambda x: x["open_time"])
                status, descriptors, gate_failures = reduce_price_path_metric(
                    bars=complete_bars,
                    coverage_admissible=fam_cov,
                )

            elif metric_name == "perp_index_basis":
                both_cov = all(a["coverage_status"] == "window_observed" for a in audits)
                first_open = ceil_step(tpub, 3_600_000)
                p_bars = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "klines_1h"), [])
                    if r["open_time"] >= first_open
                    and r["open_time"] + 3_600_000 <= end_ms
                ]
                i_bars = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "index_price_1h"), [])
                    if r["open_time"] >= first_open
                    and r["open_time"] + 3_600_000 <= end_ms
                ]
                status, descriptors, gate_failures = reduce_basis_metric(
                    perp_or_mark_bars=p_bars,
                    index_bars=i_bars,
                    coverage_admissible=both_cov,
                    is_mark=False,
                )

            elif metric_name == "mark_index_basis":
                both_cov = all(a["coverage_status"] == "window_observed" for a in audits)
                first_open = ceil_step(tpub, 3_600_000)
                m_bars = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "mark_price_1h"), [])
                    if r["open_time"] >= first_open
                    and r["open_time"] + 3_600_000 <= end_ms
                ]
                i_bars = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "index_price_1h"), [])
                    if r["open_time"] >= first_open
                    and r["open_time"] + 3_600_000 <= end_ms
                ]
                status, descriptors, gate_failures = reduce_basis_metric(
                    perp_or_mark_bars=m_bars,
                    index_bars=i_bars,
                    coverage_admissible=both_cov,
                    is_mark=True,
                )

            elif metric_name == "funding_observations":
                fam_cov = audits[0]["coverage_status"] in {"rows_observed_continuity_not_proven", "window_observed"}
                f_rows = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "funding_rate"), [])
                    if start_ms <= r["calc_time"] < end_ms
                ]
                status, descriptors, gate_failures = reduce_funding_observations(
                    rows=f_rows,
                    coverage_admissible=fam_cov,
                )

            elif metric_name == "open_interest":
                fam_cov = audits[0]["coverage_status"] == "window_observed"
                first_create = ceil_step(tpub, 300_000)
                m_rows = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "metrics_5m"), [])
                    if first_create <= r["create_time"] < end_ms
                ]
                status, descriptors, gate_failures = reduce_open_interest(
                    rows=m_rows,
                    coverage_admissible=fam_cov,
                    expected_start_ms=first_create,
                    expected_end_ms=end_ms,
                )

            elif metric_name == "visible_depth_proxy":
                fam_cov = audits[0]["coverage_status"] in {"rows_observed_continuity_not_proven", "window_observed"}
                d_rows = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "book_depth"), [])
                    if start_ms <= r["timestamp"] < end_ms
                ]
                status, descriptors, gate_failures = reduce_visible_depth_proxy(
                    rows=d_rows,
                    coverage_admissible=fam_cov,
                )

            elif metric_name == "agg_trade_observations":
                fam_cov = audits[0]["coverage_status"] in {"rows_observed_continuity_not_proven", "window_observed"}
                t_rows = [
                    r for r in verified_candidate.parsed_series.get((pid, cid, sym, "agg_trades"), [])
                    if start_ms <= r["transact_time"] < end_ms
                ]
                status, descriptors, gate_failures = reduce_agg_trade_observations(
                    rows=t_rows,
                    coverage_admissible=fam_cov,
                )

            rec = MetricRecord(
                schema_version=METRIC_SCHEMA_VERSION,
                parent_article_id=pid,
                contract_id=cid,
                canonical_symbol=sym,
                metric_name=metric_name,
                horizon=horizon,
                requested_interval=req_interval,
                publication_time_authority=denom.publication_time_authority,
                t_pub_ms=tpub,
                point_in_time_source_validated=False,
                capture_time_status="historical_unknown",
                system_available_at_ms=None,
                fact_available_at_ms=None,
                source_family_audits=audits,
                source_logical_archive_record_ids=audit_log_union,
                gate_failures=sorted(set(gate_failures)),
                status=status,
                descriptors=descriptors,
                authority_flags=dict(denom.authority_flags),
            )
            metric_records.append(rec)

    return CandidateW1DiagnosticResult(
        denominator_rows=denominator_rows,
        metric_records=metric_records,
    )
