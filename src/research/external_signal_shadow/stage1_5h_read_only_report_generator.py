from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configs import base


@dataclass(frozen=True)
class Stage1_5HInputBundle:
    stage1_5g_summary: dict[str, Any]
    quarantine_summary: dict[str, Any]
    depth_quality_input_rows: list[dict[str, Any]]
    quarantined_invalid_book_rows: list[dict[str, Any]]
    governance_review_path: Path
    governance_review_text: str
    loader_blockers: list[str]
    loader_warnings: list[str]


def _load_json(path: Path, blocker_name: str, blockers: list[str]) -> dict[str, Any]:
    if not path.exists():
        blockers.append(blocker_name)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        blockers.append(blocker_name)
        return {}


def _load_jsonl(path: Path, blocker_name: str, blockers: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        blockers.append(blocker_name)
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
    except Exception:
        blockers.append(blocker_name)
        return []
    return rows


def load_stage1_5h_inputs(
    *,
    stage1_5g_summary_path: str | Path,
    quarantine_summary_path: str | Path,
    depth_quality_input_rows_path: str | Path,
    quarantined_invalid_book_rows_path: str | Path,
    governance_review_path: str | Path,
) -> Stage1_5HInputBundle:
    blockers: list[str] = []
    warnings: list[str] = []
    gov_path = Path(governance_review_path)
    governance_text = gov_path.read_text(encoding="utf-8") if gov_path.exists() else ""
    if not governance_text:
        blockers.append("missing_or_unreadable_governance_review")
    return Stage1_5HInputBundle(
        stage1_5g_summary=_load_json(Path(stage1_5g_summary_path), "missing_or_unreadable_stage1_5g_summary", blockers),
        quarantine_summary=_load_json(Path(quarantine_summary_path), "missing_or_unreadable_quarantine_summary", blockers),
        depth_quality_input_rows=_load_jsonl(Path(depth_quality_input_rows_path), "missing_or_unreadable_depth_quality_input_rows", blockers),
        quarantined_invalid_book_rows=_load_jsonl(Path(quarantined_invalid_book_rows_path), "missing_or_unreadable_quarantined_invalid_book_rows", blockers),
        governance_review_path=gov_path,
        governance_review_text=governance_text,
        loader_blockers=blockers,
        loader_warnings=warnings,
    )


def _base_safety_fields() -> dict[str, Any]:
    return {
        "implementation_plan_allowed": False,
        "implementation_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "alpha_interpretation_allowed": False,
        "event_family_conclusion_allowed": False,
        "multi_event_aggregation_allowed": False,
        "cross_event_generalization_allowed": False,
    }


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _validate_governance_review(bundle: Stage1_5HInputBundle, blockers: list[str]) -> None:
    text = bundle.governance_review_text
    expected_artifact = Path(
        "docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md"
    )
    # The approval artifact must be the governance review path, not just an arbitrary same-name file.
    if Path(*bundle.governance_review_path.parts[-3:]) != expected_artifact:
        _append_once(blockers, "governance_approval_artifact_path_invalid")
    required_markers = {
        "governance_approval_missing": "governance_decision = read_only_report_generator_plan_allowed_with_constraints",
        "governance_approval_owner_missing": "approval_owner = human_research_owner",
        "governance_approval_artifact_missing": "approval_artifact = docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md",
        "governance_explicit_approval_missing": "governance_approval_must_be_explicit = true",
        "governance_scope_missing": "scope = single_event_fixture_bound_report_generator",
        "governance_plan_allowed_missing": "implementation_plan_allowed = true",
        "governance_implementation_false_missing": "implementation_allowed = false",
    }
    for blocker, marker in required_markers.items():
        if marker not in text:
            _append_once(blockers, blocker)


UNSAFE_UPSTREAM_FLAGS = (
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "execution_feasibility_claim_allowed",
    "alpha_interpretation_allowed",
)


def _values_equal(left: Any, right: Any) -> bool:
    return left == right


def _validate_quarantine_consistency(summary: dict[str, Any], quarantine: dict[str, Any], blockers: list[str]) -> None:
    embedded = summary.get("quarantine") or {}
    for key in (
        "valid_snapshot_count_after_quarantine",
        "invalid_book_row_count",
        "book_availability_ratio",
        "first_valid_book_latency_ms",
    ):
        if not _values_equal(embedded.get(key), quarantine.get(key)):
            _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")


def _validate_stage1_5g_source_of_truth(bundle: Stage1_5HInputBundle, blockers: list[str]) -> None:
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary
    if summary.get("decision") != "stage1_5g_depth_evidence_quarantined_pass":
        _append_once(blockers, "invalid_stage1_5g_decision")
    if summary.get("clean_depth_evidence_pass") is not False:
        _append_once(blockers, "clean_pass_state_unexpected")
    if summary.get("quarantined_depth_evidence_pass") is not True:
        _append_once(blockers, "quarantined_pass_missing")
    if summary.get("formal_announcement_and_launch_count", 0) < 1:
        _append_once(blockers, "no_formal_announcement_and_launch_evidence")
    for flag in UNSAFE_UPSTREAM_FLAGS:
        if summary.get(flag) is True:
            _append_once(blockers, "unsafe_upstream_flag_true")
    if quarantine.get("blockers") not in ([], None):
        _append_once(blockers, "quarantine_blockers_present")

    _validate_quarantine_consistency(summary, quarantine, blockers)

    expected_valid = int(quarantine.get("valid_snapshot_count_after_quarantine") or -1)
    expected_invalid = int(quarantine.get("quarantined_invalid_book_row_count") or quarantine.get("invalid_book_row_count") or -1)
    summary_depth_count = int((summary.get("depth_quality") or {}).get("depth_quality_input_row_count") or -1)
    if len(bundle.depth_quality_input_rows) != expected_valid:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    if len(bundle.depth_quality_input_rows) != summary_depth_count:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    if len(bundle.quarantined_invalid_book_rows) != expected_invalid:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")


def validate_stage1_5h_governance(bundle: Stage1_5HInputBundle) -> dict[str, Any]:
    blockers = list(bundle.loader_blockers)
    warnings = list(bundle.loader_warnings)
    _validate_governance_review(bundle, blockers)
    _validate_stage1_5g_source_of_truth(bundle, blockers)
    decision = "stage1_5h_design_only_input_accepted" if not blockers else "stage1_5h_input_rejected"
    return {
        "decision": decision,
        "allowed_next_action": "generate_single_event_read_only_report" if not blockers else "revise_inputs_or_continue_observation",
        "governance_plan_admission_confirmed": bool(not blockers),
        "report_generation_allowed": bool(not blockers),
        "scope": "single_event_fixture_bound_report_generator",
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        **_base_safety_fields(),
    }

def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    merged: list[str] = []
    for item in list(first or []) + list(second or []):
        if item not in merged:
            merged.append(item)
    return merged


def _fallback_clean_pass_missing_reason(summary: dict[str, Any], quarantine: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if quarantine.get("invalid_book_row_count", 0) > 0:
        reasons.append("invalid_book_present")
    reasons_by_name = quarantine.get("invalid_book_by_reason", {}) or {}
    if reasons_by_name.get("launch_warmup_empty_book", 0) > 0:
        reasons.append("launch_warmup_empty_book_present")
    if reasons_by_name.get("observation_initial_empty_book", 0) > 0:
        reasons.append("observation_initial_empty_book_present")
    if reasons_by_name.get("midrun_empty_book", 0) > 0:
        reasons.append("midrun_empty_book_present")
    # Preserve both quarantine-level and summary-level warnings. They may differ.
    return _merge_unique(reasons, _merge_unique(quarantine.get("warnings", []), summary.get("warnings", [])))


def _clean_pass_missing_reason(summary: dict[str, Any], quarantine: dict[str, Any], warnings: list[str]) -> list[str]:
    upstream = summary.get("clean_pass_missing_reason") or (summary.get("quarantine") or {}).get("clean_pass_missing_reason")
    if upstream:
        return list(upstream)
    _append_once(warnings, "clean_pass_missing_reason_reconstructed_by_stage1_5h")
    return _fallback_clean_pass_missing_reason(summary, quarantine)


def _build_static_proxy_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    quality = ((summary.get("depth_quality") or {}).get("quarantined_depth_quality") or {})
    buy_p95 = float(quality.get("buy_slippage_bps_500usdt_p95") or 0.0)
    sell_p95 = float(quality.get("sell_slippage_bps_500usdt_p95") or 0.0)
    observed = buy_p95 + sell_p95
    configured = float(base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS)
    return {
        "depth_quality_input_mode": (summary.get("depth_quality") or {}).get("depth_quality_input_mode"),
        "spread_bps_p50": quality.get("spread_bps_p50"),
        "spread_bps_p95": quality.get("spread_bps_p95"),
        "buy_slippage_bps_500usdt_p50": quality.get("buy_slippage_bps_500usdt_p50"),
        "buy_slippage_bps_500usdt_p95": buy_p95,
        "sell_slippage_bps_500usdt_p50": quality.get("sell_slippage_bps_500usdt_p50"),
        "sell_slippage_bps_500usdt_p95": sell_p95,
        "top_bid_depth_usdt_p05": quality.get("top_bid_depth_usdt_p05"),
        "top_ask_depth_usdt_p05": quality.get("top_ask_depth_usdt_p05"),
        "healthy_window_ratio": quality.get("healthy_window_ratio"),
        "observed_static_depth_friction_bps_p95": observed,
        "configured_conservative_round_trip_cost_bps": configured,
        "effective_friction_floor_bps": max(observed, configured),
        "cost_model_note": "effective_friction_floor_bps=max(observed_static_depth_friction_bps_p95, configured_conservative_round_trip_cost_bps); never sum them",
    }


def _static_proxy_blockers(metrics: dict[str, Any], quarantine: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if float(metrics.get("spread_bps_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS:
        blockers.append("spread_p95_too_high")
    if float(metrics.get("buy_slippage_bps_500usdt_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS:
        blockers.append("buy_slippage_p95_too_high")
    if float(metrics.get("sell_slippage_bps_500usdt_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS:
        blockers.append("sell_slippage_p95_too_high")
    if float(metrics.get("top_bid_depth_usdt_p05") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05:
        blockers.append("top_bid_depth_p05_too_low")
    if float(metrics.get("top_ask_depth_usdt_p05") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05:
        blockers.append("top_ask_depth_p05_too_low")
    if float(quarantine.get("book_availability_ratio") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO:
        blockers.append("book_availability_ratio_below_threshold")
    if int(quarantine.get("first_valid_book_latency_ms") or 0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS:
        blockers.append("first_valid_book_latency_too_high")
    return blockers


def build_stage1_5h_report_summary(bundle: Stage1_5HInputBundle) -> dict[str, Any]:
    governance = validate_stage1_5h_governance(bundle)
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary
    if governance["blockers"]:
        return {
            **governance,
            "decision": "stage1_5h_input_rejected",
            "allowed_next_action": "revise_inputs_or_continue_observation",
        }
    warnings = _merge_unique(quarantine.get("warnings", []), summary.get("warnings", []))
    metrics = _build_static_proxy_metrics(summary)
    static_blockers = _static_proxy_blockers(metrics, quarantine)
    return {
        "decision": "stage1_5h_single_event_static_proxy_report_generated",
        "allowed_next_action": "review_stage1_5h_read_only_report",
        "scope": "single_event_fixture_bound_report_generator",
        "evidence_scope": "single_event",
        "governance_plan_admission_confirmed": True,
        "report_generation_allowed": True,
        "clean_depth_evidence_pass": False,
        "quarantined_depth_evidence_pass": True,
        "quarantine_candidate": True,
        "clean_pass_missing_reason": _clean_pass_missing_reason(summary, quarantine, warnings),
        "quarantine_warnings": list(quarantine.get("warnings", [])),
        "summary_warnings": list(summary.get("warnings", [])),
        "book_availability_ratio": quarantine.get("book_availability_ratio"),
        "book_unavailable_ratio": quarantine.get("book_unavailable_ratio"),
        "valid_snapshot_count_after_quarantine": quarantine.get("valid_snapshot_count_after_quarantine"),
        "invalid_book_row_count": quarantine.get("invalid_book_row_count"),
        "invalid_book_by_phase": quarantine.get("invalid_book_by_phase"),
        "invalid_book_by_reason": quarantine.get("invalid_book_by_reason"),
        "max_consecutive_invalid": quarantine.get("max_consecutive_invalid"),
        "max_consecutive_invalid_after_warmup": quarantine.get("max_consecutive_invalid_after_warmup"),
        "first_valid_book_latency_ms": quarantine.get("first_valid_book_latency_ms"),
        "static_proxy_metrics": metrics,
        "static_proxy_blockers": static_blockers,
        "static_proxy_warnings": [],
        "static_proxy_report_status": "proxy_metrics_within_configured_bounds" if not static_blockers else "proxy_metrics_blocked",
        "required_next_evidence": [
            "clean_stage1_5g_depth_evidence_or_additional_independent_quarantined_events",
            "higher_frequency_orderbook_for_more_precise_execution_proxy_design",
            "trade_prints_for_future_fill_model_research",
            "separate_governance_before_any_execution_feasibility_claim",
        ],
        "blockers": [],
        "warnings": warnings,
        **_base_safety_fields(),
    }


def generate_stage1_5h_chinese_report(summary: dict[str, Any]) -> str:
    metrics = summary.get("static_proxy_metrics", {}) or {}
    reasons = summary.get("clean_pass_missing_reason", []) or []
    return "\n".join([
        "# External Signal Shadow Lab Stage 1.5H Static Execution Proxy Read-Only Report",
        "",
        "## 1. 结论",
        "",
        f"- decision: `{summary.get('decision')}`",
        f"- allowed_next_action: `{summary.get('allowed_next_action')}`",
        f"- scope: `{summary.get('scope')}`",
        f"- static_proxy_report_status: `{summary.get('static_proxy_report_status')}`",
        "- 本报告是只读报告，不是交易信号，不是执行可行性证明。",
        "- 不能作为 paper/live 或执行可行性证明。",
        "",
        "## 2. Safety Flags",
        "",
        f"- execution_feasibility_claim_allowed = {str(summary.get('execution_feasibility_claim_allowed')).lower()}",
        f"- paper_trading_allowed = {str(summary.get('paper_trading_allowed')).lower()}",
        f"- live_trading_allowed = {str(summary.get('live_trading_allowed')).lower()}",
        f"- execution_engine_allowed = {str(summary.get('execution_engine_allowed')).lower()}",
        "",
        "## 3. Quarantine Context",
        "",
        f"- clean_depth_evidence_pass = {str(summary.get('clean_depth_evidence_pass')).lower()}",
        f"- quarantined_depth_evidence_pass = {str(summary.get('quarantined_depth_evidence_pass')).lower()}",
        f"- clean_pass_missing_reason: `{reasons}`",
        f"- book_availability_ratio: `{summary.get('book_availability_ratio')}`",
        f"- invalid_book_row_count: `{summary.get('invalid_book_row_count')}`",
        f"- max_consecutive_invalid: `{summary.get('max_consecutive_invalid')}`",
        f"- max_consecutive_invalid_after_warmup: `{summary.get('max_consecutive_invalid_after_warmup')}`",
        "",
        "## 4. Static Proxy Metrics",
        "",
        f"- spread_bps_p95: `{metrics.get('spread_bps_p95')}`",
        f"- buy_slippage_bps_500usdt_p95: `{metrics.get('buy_slippage_bps_500usdt_p95')}`",
        f"- sell_slippage_bps_500usdt_p95: `{metrics.get('sell_slippage_bps_500usdt_p95')}`",
        f"- observed_static_depth_friction_bps_p95: `{metrics.get('observed_static_depth_friction_bps_p95')}`",
        f"- configured_conservative_round_trip_cost_bps: `{metrics.get('configured_conservative_round_trip_cost_bps')}`",
        f"- effective_friction_floor_bps: `{metrics.get('effective_friction_floor_bps')}`",
        f"- static_proxy_blockers: `{summary.get('static_proxy_blockers')}`",
        "",
        "## 5. Required Next Evidence",
        "",
        *(f"- `{item}`" for item in summary.get("required_next_evidence", [])),
        "",
    ])
