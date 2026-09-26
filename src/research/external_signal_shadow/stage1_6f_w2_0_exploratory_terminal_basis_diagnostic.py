"""Stage 1.6F-W2-0 exploratory terminal basis diagnostic source module.

Provides:
- Exact authority admission and verification (admit_w2_0_inputs)
- Verified row materialization via production validator (materialize_verified_w2_rows)
- Full denominator and parent ledger reducer (compute_w2_0_exploratory_terminal_basis)
- Nearest-rank quantiles and research classification reducer
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from src.research.external_signal_shadow.stage1_6f_w2_evidence_source import (
    VerifiedW2Evidence,
    compute_w2_grid_points,
    validate_w2_zip_and_csv,
)

# Exact 20-key deny vector required by Design §11 and INV-W20-08
FROZEN_20_FALSE_FLAGS: Dict[str, bool] = {
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
    "alpha_candidate_allowed": False,
    "alpha_validated_allowed": False,
    "network_collection_allowed": False,
    "deployment_allowed": False,
    "ssh_allowed": False,
    "commit_allowed": False,
    "push_allowed": False,
}

HISTORICAL_RECEIPT_EXACT_KEYS = {
    "schema_version",
    "receipt_id",
    "candidate_run_id",
    "candidate_root_path",
    "final_manifest_sha256",
    "completion_audit_review_artifact_path",
    "completion_audit_review_artifact_sha256",
    "target_w2_0_analysis_design_sha",
    "outcome_inspection_status",
    "issued_at_utc",
    "governance_invariants",
}


class W20AdmissionError(Exception):
    """Raised when authority admission or historical binding verification fails."""
    pass


class W20MaterializationError(Exception):
    """Raised when physical object validation or row materialization fails."""
    pass


class W20DiagnosticError(Exception):
    """Raised when exploratory diagnostic calculation fails."""
    pass


@dataclass(frozen=True)
class W20Admission:
    candidate_run_id: str
    outcome_inspection_status: str
    audit_verdict: str
    candidate_manifest_sha256: str
    external_audit_sha256: str
    historical_receipt_sha256: str
    w2_0_design_path: Path
    w2_0_design_sha: str
    w2_0_plan_path: Path
    w2_0_plan_sha: str
    w2_design_path: Path
    w2_design_sha: str
    w2_plan_path: Path
    w2_plan_sha: str
    w2_network_auth_path: Path
    w2_network_auth_sha: str
    external_audit_path: Path
    historical_receipt_path: Path


@dataclass(frozen=True)
class W20VerifiedRows:
    rows_by_physical_id: Dict[str, Tuple[Dict[str, Any], ...]]

    def get_rows(self, physical_id: str) -> Tuple[Dict[str, Any], ...]:
        return self.rows_by_physical_id[physical_id]


@dataclass(frozen=True)
class W20ContractRecord:
    parent_article_id: str
    contract_id: str
    canonical_symbol: str
    status: str
    t_first_ms: Optional[int] = None
    t_last_ms: Optional[int] = None
    perp_basis_first_bps: Optional[float] = None
    perp_basis_last_bps: Optional[float] = None
    delta_abs_perp_basis_bps: Optional[float] = None
    mark_basis_first_bps: Optional[float] = None
    mark_basis_last_bps: Optional[float] = None
    delta_abs_mark_basis_bps: Optional[float] = None
    non_independence_notice: str = "correlated_diagnostic_row"


@dataclass(frozen=True)
class W20ParentRecord:
    parent_article_id: str
    status: str
    n_child_contracts: int
    n_qualified_child_contracts: int
    median_delta_abs_perp_basis_bps: Optional[float] = None
    median_delta_abs_mark_basis_bps: Optional[float] = None
    perp_metric_evidence_status: str = "evidence_insufficient"
    mark_metric_evidence_status: str = "evidence_insufficient"


@dataclass(frozen=True)
class W20MetricDistributionSummary:
    metric_evidence_status: str
    n_parent_denominator: int
    n_parent_window_defined: int
    n_parent_exploratory_described: int
    minimum: Optional[float] = None
    p25: Optional[float] = None
    median: Optional[float] = None
    p75: Optional[float] = None
    maximum: Optional[float] = None
    n_negative_delta_parents: Optional[int] = None


@dataclass(frozen=True)
class W20Summary:
    outcome_inspection_status: str
    research_classification: str
    n_denominator_contracts: int
    n_contract_exploratory_described: int
    n_contract_temporal_unproven: int
    n_contract_no_complete_bars: int
    n_contract_endpoint_gaps: int
    n_parent_denominator: int
    n_parent_window_defined: int
    n_parent_exploratory_described: int
    n_parent_temporal_unproven: int
    n_parent_no_complete_bars: int
    perp_index_summary: W20MetricDistributionSummary
    mark_index_summary: W20MetricDistributionSummary
    non_independence_notice: str = "parent_article_id_is_independent_unit"


@dataclass(frozen=True)
class W20DiagnosticResult:
    admission: W20Admission
    contract_records: Tuple[W20ContractRecord, ...]
    parent_records: Tuple[W20ParentRecord, ...]
    summary: W20Summary
    authority_flags: Dict[str, bool]


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise W20AdmissionError(f"STOP=w2_0_admission_invalid:file_missing:{path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def calculate_basis_bps(*, price: float, index_price: float) -> float:
    """Calculate basis in basis points: 10_000 * (price - index_price) / index_price."""
    if index_price <= 0 or not math.isfinite(price) or not math.isfinite(index_price):
        raise ValueError(f"invalid_basis_inputs:price={price}:index={index_price}")
    return 10_000.0 * (price - index_price) / index_price


def calculate_delta_abs_basis(*, basis_first: float, basis_last: float) -> float:
    """Calculate delta absolute basis: abs(basis_last) - abs(basis_first)."""
    if not math.isfinite(basis_first) or not math.isfinite(basis_last):
        raise ValueError(f"invalid_delta_inputs:first={basis_first}:last={basis_last}")
    return abs(basis_last) - abs(basis_first)


def compute_nearest_rank_quantile(values: List[float], p: float) -> Optional[float]:
    """Compute nearest-rank quantile: rank = ceil(p * n), index = max(1, rank) - 1."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    rank = math.ceil(p * n)
    idx = max(1, rank) - 1
    return s[idx]


def compute_median(values: List[float]) -> Optional[float]:
    """Compute median: single central value or arithmetic mean of two central values."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def reduce_research_classification(*, n_perp_descriptors: int, n_mark_descriptors: int) -> str:
    """Design §1 unique reducer: exploratory_only if either metric has >= 1 descriptor, else evidence_insufficient."""
    if n_perp_descriptors > 0 or n_mark_descriptors > 0:
        return "exploratory_only"
    return "evidence_insufficient"


def admit_w2_0_inputs(
    *,
    project_root: Path,
    candidate_root: Path,
    w2_0_design_path: Path,
    w2_0_design_sha: str,
    w2_0_plan_path: Path,
    w2_0_plan_sha: str,
    w2_design_path: Path,
    w2_design_sha: str,
    w2_plan_path: Path,
    w2_plan_sha: str,
    w2_network_auth_path: Path,
    w2_network_auth_sha: str,
    candidate_manifest_sha: str,
    external_audit_path: Path,
    external_audit_sha: str,
    historical_receipt_path: Path,
    historical_receipt_sha: str,
) -> W20Admission:
    """Verify all 7 authority hashes, external audit verdict, and receipt bindings."""
    # 1. Authority hash checks
    if _sha256_file(w2_0_design_path) != w2_0_design_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:w2_0_design_sha_mismatch")
    if _sha256_file(w2_0_plan_path) != w2_0_plan_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:w2_0_plan_sha_mismatch")
    if _sha256_file(w2_design_path) != w2_design_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:w2_design_sha_mismatch")
    if _sha256_file(w2_plan_path) != w2_plan_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:w2_plan_sha_mismatch")
    if _sha256_file(w2_network_auth_path) != w2_network_auth_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:w2_network_auth_sha_mismatch")

    candidate_manifest_file = candidate_root / "candidate_manifest.json"
    if _sha256_file(candidate_manifest_file) != candidate_manifest_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:candidate_manifest_sha_mismatch")
    if _sha256_file(external_audit_path) != external_audit_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:external_audit_sha_mismatch")
    if _sha256_file(historical_receipt_path) != historical_receipt_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:historical_receipt_sha_mismatch")

    # 2. Read candidate manifest to get run_id
    manifest_data = json.loads(candidate_manifest_file.read_text(encoding="utf-8"))
    candidate_run_id = manifest_data.get("run_id")
    if not candidate_run_id:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:manifest_missing_run_id")

    # 3. Verify external audit content
    audit_text = external_audit_path.read_text(encoding="utf-8")
    if "Verdict: `complete`" not in audit_text and "Final Verdict: `complete`" not in audit_text:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:audit_verdict_not_complete")

    # 4. Verify historical receipt JSON
    try:
        receipt_data = json.loads(historical_receipt_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise W20AdmissionError(f"STOP=w2_0_admission_invalid:receipt_json_invalid:{exc}")

    if set(receipt_data.keys()) != HISTORICAL_RECEIPT_EXACT_KEYS:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_keys_mismatch")

    if receipt_data.get("schema_version") != "stage1_6f_w2_preanalysis_blind_receipt_v1":
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_schema_version_mismatch")

    if receipt_data.get("candidate_run_id") != candidate_run_id:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_run_id_mismatch")

    if receipt_data.get("final_manifest_sha256") != candidate_manifest_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_manifest_mismatch")

    if receipt_data.get("completion_audit_review_artifact_sha256") != external_audit_sha:
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_audit_mismatch")

    if receipt_data.get("outcome_inspection_status") != "not_seen":
        raise W20AdmissionError("STOP=w2_0_admission_invalid:receipt_issued_status_not_not_seen")

    return W20Admission(
        candidate_run_id=candidate_run_id,
        outcome_inspection_status="outcome_seen",  # forced fail-closed
        audit_verdict="complete",
        candidate_manifest_sha256=candidate_manifest_sha,
        external_audit_sha256=external_audit_sha,
        historical_receipt_sha256=historical_receipt_sha,
        w2_0_design_path=w2_0_design_path,
        w2_0_design_sha=w2_0_design_sha,
        w2_0_plan_path=w2_0_plan_path,
        w2_0_plan_sha=w2_0_plan_sha,
        w2_design_path=w2_design_path,
        w2_design_sha=w2_design_sha,
        w2_plan_path=w2_plan_path,
        w2_plan_sha=w2_plan_sha,
        w2_network_auth_path=w2_network_auth_path,
        w2_network_auth_sha=w2_network_auth_sha,
        external_audit_path=external_audit_path,
        historical_receipt_path=historical_receipt_path,
    )


def materialize_verified_w2_rows(*, verified_w2: VerifiedW2Evidence) -> W20VerifiedRows:
    """Materialize parsed rows by calling production validate_w2_zip_and_csv for every physical object."""
    root = verified_w2.completed_root
    rows_by_pid: Dict[str, Tuple[Dict[str, Any], ...]] = {}

    for phys in verified_w2.physical_source_objects:
        pid = phys["physical_source_object_id"]
        status = phys["fetch_status"]
        if status != "fetched_verified":
            continue

        zip_path = root / phys["zip_relative_path"]
        csv_path = root / phys["csv_relative_path"]
        url = phys["exact_source_url"]

        try:
            val_res = validate_w2_zip_and_csv(zip_path, csv_path, url)
            if not isinstance(val_res, dict) or "parsed_rows" not in val_res:
                raise W20MaterializationError(
                    f"STOP=w2_0_candidate_row_materialization_invalid:production_validator_rejected:{pid}:invalid_result_structure"
                )
        except W20MaterializationError:
            raise
        except Exception as exc:
            raise W20MaterializationError(
                f"STOP=w2_0_candidate_row_materialization_invalid:production_validator_rejected:{pid}:{exc}"
            ) from exc

        parsed_rows = val_res["parsed_rows"]
        row_count = val_res["csv_row_count"]
        if row_count != phys["csv_row_count"]:
            raise W20MaterializationError(
                f"STOP=w2_0_candidate_row_materialization_invalid:row_count_mismatch:{pid}:{row_count}!={phys['csv_row_count']}"
            )
        if val_res["csv_sha256"] != phys["csv_sha256"]:
            raise W20MaterializationError(
                f"STOP=w2_0_candidate_row_materialization_invalid:csv_sha_mismatch:{pid}:{val_res['csv_sha256']}!={phys['csv_sha256']}"
            )
        if val_res["zip_sha256"] != phys["zip_sha256"]:
            raise W20MaterializationError(
                f"STOP=w2_0_candidate_row_materialization_invalid:zip_sha_mismatch:{pid}:{val_res['zip_sha256']}!={phys['zip_sha256']}"
            )

        rows_by_pid[pid] = tuple(parsed_rows)

    # Verify every logical archive record maps to an existing materialized physical object
    for log_rec in verified_w2.logical_archive_records:
        pid = log_rec["physical_source_object_id"]
        if pid not in rows_by_pid:
            raise W20MaterializationError(
                f"STOP=w2_0_candidate_row_materialization_invalid:missing_physical_id:{pid}"
            )

    return W20VerifiedRows(rows_by_physical_id=rows_by_pid)


def compute_w2_0_exploratory_terminal_basis(
    *,
    verified_w2: VerifiedW2Evidence,
    verified_rows: W20VerifiedRows,
    admission: W20Admission,
) -> W20DiagnosticResult:
    """Compute endpoint basis absolute differences across 41 contracts and 27 parents."""
    # 1. Build lookup from (canonical_symbol, metric_family) to rows by open_time
    rows_by_sym_metric: Dict[Tuple[str, str], Dict[int, Dict[str, Any]]] = {}
    symbols_with_duplicate_timestamps: Set[str] = set()
    for log_rec in verified_w2.logical_archive_records:
        proj = log_rec["matrix_record_projection_v1"]
        sym = proj["canonical_symbol"]
        family = proj["metric"]
        pid = log_rec["physical_source_object_id"]
        key = (sym, family)
        if key not in rows_by_sym_metric:
            rows_by_sym_metric[key] = {}
        target_map = rows_by_sym_metric[key]
        for r in verified_rows.get_rows(pid):
            ot = r["open_time"]
            if ot in target_map:
                symbols_with_duplicate_timestamps.add(sym)
            else:
                target_map[ot] = r

    # 2. Process all 41 denominator contracts in deterministic order
    contract_records: List[W20ContractRecord] = []
    children_by_parent: Dict[str, List[W20ContractRecord]] = {}

    for denom in verified_w2.denominator_records:
        p_id = denom["parent_article_id"]
        c_id = denom["contract_id"]
        sym = denom["canonical_symbol"]
        temporal_st = denom["temporal_status"]

        if temporal_st == "settlement_time_unproven":
            rec = W20ContractRecord(
                parent_article_id=p_id,
                contract_id=c_id,
                canonical_symbol=sym,
                status="diagnostic_incomplete:temporal_unproven",
            )
        else:
            w_start = denom["window_start_ms"]
            w_end = denom["window_end_ms"]
            _, comp_grid = compute_w2_grid_points(w_start, w_end)

            if len(comp_grid) == 0:
                rec = W20ContractRecord(
                    parent_article_id=p_id,
                    contract_id=c_id,
                    canonical_symbol=sym,
                    status="diagnostic_incomplete:no_complete_bars",
                )
            else:
                t_first = comp_grid[0]
                t_last = comp_grid[-1]

                if t_first >= t_last:
                    rec = W20ContractRecord(
                        parent_article_id=p_id,
                        contract_id=c_id,
                        canonical_symbol=sym,
                        status="diagnostic_incomplete:endpoint_coverage_gap",
                    )
                elif sym in symbols_with_duplicate_timestamps:
                    rec = W20ContractRecord(
                        parent_article_id=p_id,
                        contract_id=c_id,
                        canonical_symbol=sym,
                        status="diagnostic_incomplete:duplicate_timestamp",
                        t_first_ms=t_first,
                        t_last_ms=t_last,
                    )
                else:
                    k_map = rows_by_sym_metric.get((sym, "klines_1h"), {})
                    i_map = rows_by_sym_metric.get((sym, "index_price_1h"), {})
                    m_map = rows_by_sym_metric.get((sym, "mark_price_1h"), {})

                    if (
                        t_first not in k_map or t_last not in k_map
                        or t_first not in i_map or t_last not in i_map
                        or t_first not in m_map or t_last not in m_map
                    ):
                        rec = W20ContractRecord(
                            parent_article_id=p_id,
                            contract_id=c_id,
                            canonical_symbol=sym,
                            status="diagnostic_incomplete:endpoint_coverage_gap",
                            t_first_ms=t_first,
                            t_last_ms=t_last,
                        )
                    else:
                        p_first = k_map[t_first]["close"]
                        p_last = k_map[t_last]["close"]
                        idx_first = i_map[t_first]["close"]
                        idx_last = i_map[t_last]["close"]
                        m_first = m_map[t_first]["close"]
                        m_last = m_map[t_last]["close"]

                        if (
                            idx_first <= 0 or idx_last <= 0
                            or not math.isfinite(p_first) or not math.isfinite(p_last)
                            or not math.isfinite(idx_first) or not math.isfinite(idx_last)
                            or not math.isfinite(m_first) or not math.isfinite(m_last)
                        ):
                            rec = W20ContractRecord(
                                parent_article_id=p_id,
                                contract_id=c_id,
                                canonical_symbol=sym,
                                status="diagnostic_incomplete:non_finite_or_non_positive_price",
                                t_first_ms=t_first,
                                t_last_ms=t_last,
                            )
                        else:
                            perp_b_first = calculate_basis_bps(price=p_first, index_price=idx_first)
                            perp_b_last = calculate_basis_bps(price=p_last, index_price=idx_last)
                            delta_perp = calculate_delta_abs_basis(basis_first=perp_b_first, basis_last=perp_b_last)

                            mark_b_first = calculate_basis_bps(price=m_first, index_price=idx_first)
                            mark_b_last = calculate_basis_bps(price=m_last, index_price=idx_last)
                            delta_mark = calculate_delta_abs_basis(basis_first=mark_b_first, basis_last=mark_b_last)

                            rec = W20ContractRecord(
                                parent_article_id=p_id,
                                contract_id=c_id,
                                canonical_symbol=sym,
                                status="exploratory_described",
                                t_first_ms=t_first,
                                t_last_ms=t_last,
                                perp_basis_first_bps=perp_b_first,
                                perp_basis_last_bps=perp_b_last,
                                delta_abs_perp_basis_bps=delta_perp,
                                mark_basis_first_bps=mark_b_first,
                                mark_basis_last_bps=mark_b_last,
                                delta_abs_mark_basis_bps=delta_mark,
                            )

        contract_records.append(rec)
        if p_id not in children_by_parent:
            children_by_parent[p_id] = []
        children_by_parent[p_id].append(rec)

    # 3. Aggregate across 27 distinct parents (sorted by parent_article_id)
    parent_records: List[W20ParentRecord] = []
    parent_perp_deltas: List[float] = []
    parent_mark_deltas: List[float] = []

    # Get distinct parent IDs in sorted order
    all_parent_ids = sorted(list({d["parent_article_id"] for d in verified_w2.denominator_records}))
    assert len(all_parent_ids) == 27

    for p_id in all_parent_ids:
        children = children_by_parent.get(p_id, [])
        n_child = len(children)
        qualified = [c for c in children if c.status == "exploratory_described"]
        n_qual = len(qualified)

        if n_qual > 0:
            med_perp = compute_median([c.delta_abs_perp_basis_bps for c in qualified])
            med_mark = compute_median([c.delta_abs_mark_basis_bps for c in qualified])
            prec = W20ParentRecord(
                parent_article_id=p_id,
                status="exploratory_described",
                n_child_contracts=n_child,
                n_qualified_child_contracts=n_qual,
                median_delta_abs_perp_basis_bps=med_perp,
                median_delta_abs_mark_basis_bps=med_mark,
                perp_metric_evidence_status="exploratory_described",
                mark_metric_evidence_status="exploratory_described",
            )
            parent_perp_deltas.append(med_perp)
            parent_mark_deltas.append(med_mark)
        else:
            # All children incomplete
            if all(c.status == "diagnostic_incomplete:temporal_unproven" for c in children):
                p_status = "diagnostic_incomplete:temporal_unproven"
            elif all(c.status == "diagnostic_incomplete:no_complete_bars" for c in children):
                p_status = "diagnostic_incomplete:no_complete_bars"
            else:
                p_status = children[0].status

            prec = W20ParentRecord(
                parent_article_id=p_id,
                status=p_status,
                n_child_contracts=n_child,
                n_qualified_child_contracts=0,
                perp_metric_evidence_status="evidence_insufficient",
                mark_metric_evidence_status="evidence_insufficient",
            )

        parent_records.append(prec)

    # 4. Compute distributions and summary (independently decoupled)
    if parent_perp_deltas:
        perp_summary = W20MetricDistributionSummary(
            metric_evidence_status="exploratory_described",
            n_parent_denominator=27,
            n_parent_window_defined=21,
            n_parent_exploratory_described=len(parent_perp_deltas),
            minimum=min(parent_perp_deltas),
            p25=compute_nearest_rank_quantile(parent_perp_deltas, 0.25),
            median=compute_median(parent_perp_deltas),
            p75=compute_nearest_rank_quantile(parent_perp_deltas, 0.75),
            maximum=max(parent_perp_deltas),
            n_negative_delta_parents=sum(1 for v in parent_perp_deltas if v < 0),
        )
    else:
        perp_summary = W20MetricDistributionSummary(
            metric_evidence_status="evidence_insufficient",
            n_parent_denominator=27,
            n_parent_window_defined=21,
            n_parent_exploratory_described=0,
        )

    if parent_mark_deltas:
        mark_summary = W20MetricDistributionSummary(
            metric_evidence_status="exploratory_described",
            n_parent_denominator=27,
            n_parent_window_defined=21,
            n_parent_exploratory_described=len(parent_mark_deltas),
            minimum=min(parent_mark_deltas),
            p25=compute_nearest_rank_quantile(parent_mark_deltas, 0.25),
            median=compute_median(parent_mark_deltas),
            p75=compute_nearest_rank_quantile(parent_mark_deltas, 0.75),
            maximum=max(parent_mark_deltas),
            n_negative_delta_parents=sum(1 for v in parent_mark_deltas if v < 0),
        )
    else:
        mark_summary = W20MetricDistributionSummary(
            metric_evidence_status="evidence_insufficient",
            n_parent_denominator=27,
            n_parent_window_defined=21,
            n_parent_exploratory_described=0,
        )

    res_class = reduce_research_classification(
        n_perp_descriptors=len(parent_perp_deltas),
        n_mark_descriptors=len(parent_mark_deltas),
    )

    contract_status_list = [c.status for c in contract_records]
    parent_status_list = [p.status for p in parent_records]

    summary = W20Summary(
        outcome_inspection_status="outcome_seen",
        research_classification=res_class,
        n_denominator_contracts=41,
        n_contract_exploratory_described=contract_status_list.count("exploratory_described"),
        n_contract_temporal_unproven=contract_status_list.count("diagnostic_incomplete:temporal_unproven"),
        n_contract_no_complete_bars=contract_status_list.count("diagnostic_incomplete:no_complete_bars"),
        n_contract_endpoint_gaps=contract_status_list.count("diagnostic_incomplete:endpoint_coverage_gap"),
        n_parent_denominator=27,
        n_parent_window_defined=21,
        n_parent_exploratory_described=parent_status_list.count("exploratory_described"),
        n_parent_temporal_unproven=parent_status_list.count("diagnostic_incomplete:temporal_unproven"),
        n_parent_no_complete_bars=parent_status_list.count("diagnostic_incomplete:no_complete_bars"),
        perp_index_summary=perp_summary,
        mark_index_summary=mark_summary,
    )

    return W20DiagnosticResult(
        admission=admission,
        contract_records=tuple(contract_records),
        parent_records=tuple(parent_records),
        summary=summary,
        authority_flags=dict(FROZEN_20_FALSE_FLAGS),
    )
