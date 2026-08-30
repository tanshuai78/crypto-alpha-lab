from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from configs import base
from src.research.external_signal_shadow.safety import canonical_json_dumps
from src.research.external_signal_shadow.stage1_5g_live_depth_evidence_review import (
    verify_stage1_5g_review_manifest,
)

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_STAGE1_5H_V2_REPORTS_ROOT = (
    _PROJECT_ROOT / "data/external_signal_shadow/stage1_5h/reports"
)


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
    stage1_5g_summary_path: Path | None = None
    quarantine_summary_path: Path | None = None
    depth_quality_input_rows_path: Path | None = None
    quarantined_invalid_book_rows_path: Path | None = None


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
    rows: list[dict[str, Any]] = []
    if not path.exists():
        blockers.append(blocker_name)
        return rows
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
    sum_path = Path(stage1_5g_summary_path)
    quarantine_path = Path(quarantine_summary_path)
    depth_quality_path = Path(depth_quality_input_rows_path)
    invalid_rows_path = Path(quarantined_invalid_book_rows_path)
    return Stage1_5HInputBundle(
        stage1_5g_summary=_load_json(sum_path, "missing_or_unreadable_stage1_5g_summary", blockers),
        quarantine_summary=_load_json(quarantine_path, "missing_or_unreadable_quarantine_summary", blockers),
        depth_quality_input_rows=_load_jsonl(depth_quality_path, "missing_or_unreadable_depth_quality_input_rows", blockers),
        quarantined_invalid_book_rows=_load_jsonl(invalid_rows_path, "missing_or_unreadable_quarantined_invalid_book_rows", blockers),
        governance_review_path=gov_path,
        governance_review_text=governance_text,
        loader_blockers=blockers,
        loader_warnings=warnings,
        stage1_5g_summary_path=sum_path,
        quarantine_summary_path=quarantine_path,
        depth_quality_input_rows_path=depth_quality_path,
        quarantined_invalid_book_rows_path=invalid_rows_path,
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


def _v2_safety_fields() -> dict[str, Any]:
    return {
        "execution_feasibility_claim_allowed": False,
        "alpha_interpretation_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "private_endpoint_allowed": False,
        "api_key_allowed": False,
        "order_endpoint_allowed": False,
    }


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _validate_governance_review(bundle: Stage1_5HInputBundle, blockers: list[str]) -> None:
    text = bundle.governance_review_text
    expected_artifact = Path(
        "docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md"
    )
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


def _invalid_book_row_count(quarantine: dict[str, Any]) -> Any:
    value = quarantine.get("invalid_book_row_count")
    return value if value is not None else quarantine.get(
        "quarantined_invalid_book_row_count", 0
    )


def _validate_quarantine_consistency(summary: dict[str, Any], quarantine: dict[str, Any], blockers: list[str]) -> None:
    embedded = summary.get("quarantine") or {}
    keys_to_check = [
        ("aggregate_valid_snapshot_count_after_quarantine", "valid_snapshot_count_after_quarantine"),
        ("aggregate_invalid_book_row_count", "invalid_book_row_count"),
        ("aggregate_book_availability_ratio", "book_availability_ratio"),
        ("first_valid_book_latency_ms", "first_valid_book_latency_ms"),
    ]
    for v2_key, v1_key in keys_to_check:
        emb_val = embedded.get(v2_key) if v2_key in embedded else embedded.get(v1_key)
        qua_val = quarantine.get(v2_key) if v2_key in quarantine else quarantine.get(v1_key)
        if not _values_equal(emb_val, qua_val):
            _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")


def _validate_v2_closed_artifact_paths(
    bundle: Stage1_5HInputBundle, blockers: list[str]
) -> tuple[Path, dict[str, Any]] | None:
    required_paths = {
        "summary": bundle.stage1_5g_summary_path,
        "quarantine_summary": bundle.quarantine_summary_path,
        "depth_quality_input_rows": bundle.depth_quality_input_rows_path,
        "quarantined_invalid_book_rows": bundle.quarantined_invalid_book_rows_path,
    }
    if (
        bundle.stage1_5g_summary_path is None
        or any(path is None for path in required_paths.values())
    ):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None

    for p in required_paths.values():
        if p.is_symlink() or not p.is_file():
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None

    root = bundle.stage1_5g_summary_path.resolve().parent
    manifest_path = root / "stage1_5g_review_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None

    manifest_ok, manifest_blockers = verify_stage1_5g_review_manifest(root)
    if not manifest_ok:
        for b in manifest_blockers:
            _append_once(blockers, b)
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None

    artifacts = manifest.get("artifacts") or {}
    for key, supplied_path in required_paths.items():
        meta = artifacts.get(key) or {}
        relative_path = meta.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None
        artifact_path = (root / relative_path).resolve()
        try:
            artifact_path.relative_to(root)
        except ValueError:
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None
        if artifact_path != supplied_path.resolve():
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None

    return root, manifest


def _v2_single_symbol_quarantine_view(
    bundle: Stage1_5HInputBundle,
    blockers: list[str],
) -> dict[str, Any] | None:
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary

    ids = quarantine.get("eligible_event_symbol_ids")
    formal_count = quarantine.get("formal_completed_symbol_count")
    if (
        not isinstance(ids, list)
        or not all(isinstance(item, str) and item for item in ids)
        or ids != sorted(set(ids))
        or not isinstance(formal_count, int)
        or isinstance(formal_count, bool)
        or formal_count <= 0
        or formal_count != len(ids)
    ):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None
    if formal_count > 1:
        _append_once(blockers, "stage1_5h_multi_symbol_input_not_authorized")
        return None

    res = _validate_v2_closed_artifact_paths(bundle, blockers)
    if res is None:
        return None
    root, manifest = res

    if (
        summary.get("quarantine") != quarantine
        or quarantine.get("schema_version") != 2
        or quarantine.get("clean_depth_evidence_pass") is not False
        or quarantine.get("quarantined_depth_evidence_pass") is not True
    ):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None

    formal_hash = hashlib.sha256(
        canonical_json_dumps(ids).encode("utf-8")
    ).hexdigest()
    review_payload = {
        "formal_completed_event_symbol_ids": ids,
        "schema_version": 2,
        "source_evidence_manifest_sha256": summary.get(
            "source_evidence_manifest_sha256", ""
        ),
    }
    review_id = hashlib.sha256(
        canonical_json_dumps(review_payload).encode("utf-8")
    ).hexdigest()
    for key, expected in {
        "stage1_5g_review_id": review_id,
        "formal_completed_event_symbol_ids_sha256": formal_hash,
    }.items():
        if summary.get(key) != expected or quarantine.get(key) != expected:
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None

    if quarantine.get("source_evidence_manifest_sha256") != summary.get(
        "source_evidence_manifest_sha256"
    ):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None

    for key in (
        "stage1_5g_review_id",
        "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256",
    ):
        if manifest.get(key) != summary.get(key):
            _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
            return None

    sole_metrics = (quarantine.get("per_symbol_quarantine_metrics") or {}).get(ids[0])
    if (
        not isinstance(sole_metrics, dict)
        or sole_metrics.get("blockers") not in ([], None)
        or sole_metrics.get("clean_depth_evidence_pass") is not False
        or sole_metrics.get("quarantined_depth_evidence_pass") is not True
    ):
        _append_once(blockers, "stage1_5g_quarantine_v2_artifact_mismatch")
        return None
    return {
        "blockers": sole_metrics.get("blockers", []),
        "warnings": quarantine.get("warnings", []),
        "clean_depth_evidence_pass": sole_metrics.get("clean_depth_evidence_pass"),
        "quarantined_depth_evidence_pass": sole_metrics.get(
            "quarantined_depth_evidence_pass"
        ),
        "valid_snapshot_count_after_quarantine": sole_metrics.get(
            "valid_snapshot_count_after_quarantine"
        ),
        "invalid_book_row_count": sole_metrics.get("invalid_book_row_count"),
        "book_availability_ratio": sole_metrics.get("book_availability_ratio"),
        "book_unavailable_ratio": sole_metrics.get("book_unavailable_ratio"),
        "invalid_book_by_phase": sole_metrics.get("invalid_book_by_phase"),
        "invalid_book_by_reason": sole_metrics.get("invalid_book_by_reason"),
        "max_consecutive_invalid": sole_metrics.get("max_consecutive_invalid"),
        "max_consecutive_invalid_after_warmup": sole_metrics.get(
            "max_consecutive_invalid_after_warmup"
        ),
        "first_valid_book_latency_ms": sole_metrics.get(
            "first_valid_book_latency_ms"
        ),
        "quarantined_depth_quality": sole_metrics.get(
            "quarantined_depth_quality"
        ),
    }


def _validate_stage1_5g_source_of_truth(
    bundle: Stage1_5HInputBundle,
    blockers: list[str],
) -> dict[str, Any]:
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary
    schema_version = summary.get("schema_version")
    if summary.get("decision") != "stage1_5g_depth_evidence_quarantined_pass":
        _append_once(blockers, "invalid_stage1_5g_decision")
    if schema_version == 2 and summary.get("clean_depth_evidence_pass") is True:
        _append_once(blockers, "stage1_5h_stage1_5g_clean_v2_input_not_authorized")
    elif summary.get("clean_depth_evidence_pass") is not False:
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

    if schema_version in (None, 1):
        formal_count = summary.get("formal_announcement_and_launch_count")
        if not isinstance(formal_count, int) or isinstance(formal_count, bool):
            _append_once(blockers, "stage1_5g_schema_version_unsupported")
        elif formal_count > 1:
            _append_once(blockers, "stage1_5g_v1_multi_symbol_denominator_unsafe")
        quarantine_view = quarantine
        _validate_quarantine_consistency(summary, quarantine_view, blockers)
    elif schema_version == 2:
        quarantine_view = _v2_single_symbol_quarantine_view(bundle, blockers) or {}
    else:
        _append_once(blockers, "stage1_5g_schema_version_unsupported")
        quarantine_view = {}

    expected_invalid = _invalid_book_row_count(quarantine_view)
    if len(bundle.quarantined_invalid_book_rows) != expected_invalid:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    summary_quality_count = (summary.get("depth_quality") or {}).get(
        "depth_quality_input_row_count"
    )
    if summary_quality_count is not None and summary_quality_count != len(
        bundle.depth_quality_input_rows
    ):
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    return quarantine_view


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
    if _invalid_book_row_count(quarantine) > 0:
        reasons.append("invalid_book_present")
    reasons_by_name = quarantine.get("invalid_book_by_reason", {}) or {}
    if reasons_by_name.get("launch_warmup_empty_book", 0) > 0:
        reasons.append("launch_warmup_empty_book_present")
    if reasons_by_name.get("observation_initial_empty_book", 0) > 0:
        reasons.append("observation_initial_empty_book_present")
    if reasons_by_name.get("midrun_empty_book", 0) > 0:
        reasons.append("midrun_empty_book_present")
    return _merge_unique(reasons, _merge_unique(quarantine.get("warnings", []), summary.get("warnings", [])))


def _clean_pass_missing_reason(summary: dict[str, Any], quarantine: dict[str, Any], warnings: list[str]) -> list[str]:
    upstream = summary.get("clean_pass_missing_reason") or (summary.get("quarantine") or {}).get("clean_pass_missing_reason")
    if upstream:
        return list(upstream)
    _append_once(warnings, "clean_pass_missing_reason_reconstructed_by_stage1_5h")
    return _fallback_clean_pass_missing_reason(summary, quarantine)


def _build_static_proxy_metrics_from_quality(
    quality: dict[str, Any], *, depth_quality_input_mode: Any
) -> dict[str, Any]:
    buy_p95 = float(quality.get("buy_slippage_bps_500usdt_p95") or 0.0)
    sell_p95 = float(quality.get("sell_slippage_bps_500usdt_p95") or 0.0)
    observed = buy_p95 + sell_p95
    configured = float(base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS)
    return {
        "depth_quality_input_mode": depth_quality_input_mode,
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


def _build_static_proxy_metrics(
    summary: dict[str, Any], quarantine: dict[str, Any]
) -> dict[str, Any]:
    quality = quarantine.get("quarantined_depth_quality") or (
        (summary.get("depth_quality") or {}).get("quarantined_depth_quality") or {}
    )
    return _build_static_proxy_metrics_from_quality(
        quality,
        depth_quality_input_mode=(summary.get("depth_quality") or {}).get("depth_quality_input_mode"),
    )


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
    avail_ratio = float(quarantine.get("book_availability_ratio") or 0.0)
    if avail_ratio < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO:
        blockers.append("book_availability_ratio_below_threshold")
    if int(quarantine.get("first_valid_book_latency_ms") or 0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS:
        blockers.append("first_valid_book_latency_too_high")
    return blockers


def build_stage1_5h_report_summary(bundle: Stage1_5HInputBundle) -> dict[str, Any]:
    governance = validate_stage1_5h_governance(bundle)
    summary = bundle.stage1_5g_summary
    if governance["blockers"]:
        return {
            **governance,
            "decision": "stage1_5h_input_rejected",
            "allowed_next_action": "revise_inputs_or_continue_observation",
        }
    validation_blockers: list[str] = []
    quarantine = _validate_stage1_5g_source_of_truth(bundle, validation_blockers)
    if validation_blockers:
        return {
            **governance,
            "decision": "stage1_5h_input_rejected",
            "allowed_next_action": "revise_inputs_or_continue_observation",
            "blockers": sorted(set(validation_blockers)),
        }
    warnings = _merge_unique(quarantine.get("warnings", []), summary.get("warnings", []))
    metrics = _build_static_proxy_metrics(summary, quarantine)
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
        "invalid_book_row_count": _invalid_book_row_count(quarantine),
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


# ═════════════════════════════════════════════════════════════════════════════
# V2 Event-Bundle Per-Symbol Implementation
# ═════════════════════════════════════════════════════════════════════════════

def _validate_v2_event_bundle_governance(
    bundle: Stage1_5HInputBundle, blockers: list[str]
) -> None:
    expected_path = (
        _PROJECT_ROOT
        / "docs/reviews/2026-08-30-external-signal-shadow-lab-stage1-5h-v2-event-bundle-per-symbol-read-only-report-governance-review_CN.md"
    ).resolve()
    actual_path = bundle.governance_review_path.resolve()
    if actual_path != expected_path or not actual_path.is_file() or actual_path.is_symlink():
        _append_once(blockers, "governance_approval_missing")
        return

    text = bundle.governance_review_text
    expected_sha = "7bf59a14a230da4071bde7acafc0b2022de52c313f47f389eadd293b162dacc4"
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected_sha:
        _append_once(blockers, "governance_approval_missing")
        return

    required_markers = [
        "scope = v2_event_bundle_per_symbol_read_only_report_generator",
        "multi_symbol_per_symbol_reporting_allowed = true",
        "cross_symbol_metric_aggregation_allowed = false",
        "event_family_conclusion_allowed = false",
        "cross_event_generalization_allowed = false",
        "execution_feasibility_claim_allowed = false",
        "alpha_interpretation_allowed = false",
        "trade_signal_allowed = false",
        "paper_trading_allowed = false",
        "live_trading_allowed = false",
        "execution_engine_allowed = false",
        "private_endpoint_allowed = false",
        "api_key_allowed = false",
        "order_endpoint_allowed = false",
        "implementation_plan_allowed = true",
        "deployment_allowed = false",
    ]
    for marker in required_markers:
        if marker not in text:
            _append_once(blockers, "governance_approval_missing")
            return


def _render_stage1_5h_v2_event_bundle_markdown(report: dict[str, Any]) -> str:
    metrics = report.get("static_proxy_metrics", {}) or {}
    lines = [
        f"# Stage 1.5H Static Execution Proxy Read-Only Report: {report.get('symbol')} ({report.get('event_symbol_id')})",
        "",
        "## 1. 结论 (Conclusions)",
        "",
        f"- event_symbol_id: `{report.get('event_symbol_id')}`",
        f"- symbol: `{report.get('symbol')}`",
        f"- source_article_id: `{report.get('source_article_id')}`",
        f"- upstream_stage1_5g_status: `{report.get('upstream_stage1_5g_status')}`",
        f"- stage1_5h_static_proxy_status: `{report.get('stage1_5h_static_proxy_status')}`",
        "- 本报告是只读报告，不是交易信号，不是执行可行性证明。",
        "- 不能作为 paper/live 或执行可行性证明。",
        "",
        "## 2. Safety Flags",
        "",
        f"- execution_feasibility_claim_allowed = {str(report.get('execution_feasibility_claim_allowed')).lower()}",
        f"- alpha_interpretation_allowed = {str(report.get('alpha_interpretation_allowed')).lower()}",
        f"- trade_signal_allowed = {str(report.get('trade_signal_allowed')).lower()}",
        f"- paper_trading_allowed = {str(report.get('paper_trading_allowed')).lower()}",
        f"- live_trading_allowed = {str(report.get('live_trading_allowed')).lower()}",
        f"- execution_engine_allowed = {str(report.get('execution_engine_allowed')).lower()}",
        f"- private_endpoint_allowed = {str(report.get('private_endpoint_allowed')).lower()}",
        f"- api_key_allowed = {str(report.get('api_key_allowed')).lower()}",
        f"- order_endpoint_allowed = {str(report.get('order_endpoint_allowed')).lower()}",
        "",
        "## 3. Quarantine Context",
        "",
        f"- book_availability_ratio: `{report.get('book_availability_ratio')}`",
        f"- book_unavailable_ratio: `{report.get('book_unavailable_ratio')}`",
        f"- invalid_book_row_count: `{report.get('invalid_book_row_count')}`",
        f"- valid_snapshot_count_after_quarantine: `{report.get('valid_snapshot_count_after_quarantine')}`",
        f"- observed_snapshot_count: `{report.get('observed_snapshot_count')}`",
        f"- first_valid_book_latency_ms: `{report.get('first_valid_book_latency_ms')}`",
        f"- max_consecutive_invalid: `{report.get('max_consecutive_invalid')}`",
        f"- max_consecutive_invalid_after_warmup: `{report.get('max_consecutive_invalid_after_warmup')}`",
        f"- invalid_book_by_phase: `{report.get('invalid_book_by_phase')}`",
        f"- invalid_book_by_reason: `{report.get('invalid_book_by_reason')}`",
        "",
        "## 4. Static Proxy Metrics",
        "",
        f"- spread_bps_p50: `{metrics.get('spread_bps_p50')}`",
        f"- spread_bps_p95: `{metrics.get('spread_bps_p95')}`",
        f"- buy_slippage_bps_500usdt_p50: `{metrics.get('buy_slippage_bps_500usdt_p50')}`",
        f"- buy_slippage_bps_500usdt_p95: `{metrics.get('buy_slippage_bps_500usdt_p95')}`",
        f"- sell_slippage_bps_500usdt_p50: `{metrics.get('sell_slippage_bps_500usdt_p50')}`",
        f"- sell_slippage_bps_500usdt_p95: `{metrics.get('sell_slippage_bps_500usdt_p95')}`",
        f"- top_bid_depth_usdt_p05: `{metrics.get('top_bid_depth_usdt_p05')}`",
        f"- top_ask_depth_usdt_p05: `{metrics.get('top_ask_depth_usdt_p05')}`",
        f"- healthy_window_ratio: `{metrics.get('healthy_window_ratio')}`",
        f"- observed_static_depth_friction_bps_p95: `{metrics.get('observed_static_depth_friction_bps_p95')}`",
        f"- configured_conservative_round_trip_cost_bps: `{metrics.get('configured_conservative_round_trip_cost_bps')}`",
        f"- effective_friction_floor_bps: `{metrics.get('effective_friction_floor_bps')}`",
        f"- stage1_5h_static_proxy_blockers: `{report.get('stage1_5h_static_proxy_blockers')}`",
        "",
        "## 5. Required Next Evidence",
        "",
        *(f"- `{item}`" for item in report.get("required_next_evidence", [])),
        "",
    ]
    return "\n".join(lines)


def build_stage1_5h_v2_event_bundle_reports(
    bundle: Stage1_5HInputBundle,
) -> dict[str, Any]:
    blockers: list[str] = []
    _validate_v2_event_bundle_governance(bundle, blockers)

    def reject() -> dict[str, Any]:
        return {
            "decision": "stage1_5h_v2_event_bundle_input_rejected",
            "report_generation_allowed": False,
            "reports": {},
            "blockers": sorted(set(blockers)),
            **_v2_safety_fields(),
        }

    if blockers:
        return reject()

    paths_res = _validate_v2_closed_artifact_paths(bundle, blockers)
    if paths_res is None or blockers:
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    root, manifest = paths_res

    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary

    if summary.get("schema_version") != 2 or quarantine.get("schema_version") != 2:
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if summary.get("clean_depth_evidence_pass") is True:
        _append_once(blockers, "stage1_5h_v2_clean_bundle_not_authorized")
        return reject()
    if summary.get("decision") != "stage1_5g_depth_evidence_quarantined_pass":
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if summary.get("clean_depth_evidence_pass") is not False:
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if summary.get("quarantined_depth_evidence_pass") is not True:
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    embedded_quarantine = summary.get("quarantine")
    if not isinstance(embedded_quarantine, dict) or canonical_json_dumps(embedded_quarantine) != canonical_json_dumps(quarantine):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    raw_ids = embedded_quarantine.get("eligible_event_symbol_ids")
    if not isinstance(raw_ids, list) or not raw_ids or raw_ids != sorted(raw_ids):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if len(raw_ids) != len(set(raw_ids)):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if not all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in raw_ids):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    formal_hash = hashlib.sha256(canonical_json_dumps(raw_ids).encode("utf-8")).hexdigest()
    if formal_hash != summary.get("formal_completed_event_symbol_ids_sha256"):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if formal_hash != quarantine.get("formal_completed_event_symbol_ids_sha256"):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    if quarantine.get("formal_completed_symbol_count") != len(raw_ids):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    # Identity check on manifest
    manifest_sha = hashlib.sha256((root / "stage1_5g_review_manifest.json").read_bytes()).hexdigest()
    if summary.get("stage1_5g_review_id") != quarantine.get("stage1_5g_review_id"):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    if summary.get("source_evidence_manifest_sha256") != quarantine.get("source_evidence_manifest_sha256"):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    event_decisions_list = summary.get("event_level_decisions")
    if not isinstance(event_decisions_list, list):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()
    event_decisions_by_id: dict[str, dict[str, Any]] = {}
    for row in event_decisions_list:
        if not isinstance(row, dict):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        if row.get("formal_completed") is not True:
            continue
        event_symbol_id = row.get("event_symbol_id")
        if (
            not isinstance(event_symbol_id, str)
            or event_symbol_id not in raw_ids
            or event_symbol_id in event_decisions_by_id
            or not isinstance(row.get("symbol"), str)
            or not row["symbol"]
            or not isinstance(row.get("source_article_id"), str)
            or not row["source_article_id"]
        ):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        event_decisions_by_id[event_symbol_id] = row
    if set(event_decisions_by_id) != set(raw_ids):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    per_symbol_metrics = quarantine.get("per_symbol_quarantine_metrics") or {}
    if set(per_symbol_metrics) != set(raw_ids):
        _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
        return reject()

    # Partition JSONL rows
    valid_rows_by_id: dict[str, list[dict[str, Any]]] = {s: [] for s in raw_ids}
    for row in bundle.depth_quality_input_rows:
        if not isinstance(row, dict):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        es_id = row.get("event_symbol_id")
        identity = event_decisions_by_id.get(es_id)
        if identity is None or row.get("symbol") != identity["symbol"]:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        valid_rows_by_id[es_id].append(row)

    invalid_rows_by_id: dict[str, list[dict[str, Any]]] = {s: [] for s in raw_ids}
    for row in bundle.quarantined_invalid_book_rows:
        if not isinstance(row, dict):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        es_id = row.get("event_symbol_id")
        identity = event_decisions_by_id.get(es_id)
        if identity is None or row.get("symbol") != identity["symbol"]:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        invalid_rows_by_id[es_id].append(row)

    # Check each symbol
    prepared_reports: dict[str, Any] = {}
    for s in raw_ids:
        metrics_s = per_symbol_metrics.get(s)
        if not isinstance(metrics_s, dict) or metrics_s.get("blockers") != []:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        sym_meta = event_decisions_by_id.get(s) or {}
        symbol_name = sym_meta.get("symbol")
        if not symbol_name or not isinstance(symbol_name, str):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        if metrics_s.get("symbol") is not None and metrics_s.get("symbol") != symbol_name:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        invalid_count = metrics_s.get("invalid_book_row_count")
        if not isinstance(invalid_count, int) or isinstance(invalid_count, bool) or invalid_count < 0:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        valid_count = metrics_s.get("valid_snapshot_count_after_quarantine")
        if not isinstance(valid_count, int) or isinstance(valid_count, bool) or valid_count < 0:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        if len(valid_rows_by_id[s]) != valid_count:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        if len(invalid_rows_by_id[s]) != invalid_count:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        def count_map(value: Any) -> dict[str, int] | None:
            if not isinstance(value, dict):
                return None
            result: dict[str, int] = {}
            for key, count in value.items():
                if not isinstance(key, str) or not isinstance(count, int) or isinstance(count, bool) or count < 0:
                    return None
                if count:
                    result[key] = count
            return result

        phase_metrics = count_map(metrics_s.get("invalid_book_by_phase"))
        reason_metrics = count_map(metrics_s.get("invalid_book_by_reason"))
        phase_rows: dict[str, int] = {}
        reason_rows: dict[str, int] = {}
        for row in invalid_rows_by_id[s]:
            phase = row.get("quarantine_phase")
            reason = row.get("quarantine_reason")
            if not isinstance(phase, str) or not phase or not isinstance(reason, str) or not reason:
                _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
                return reject()
            phase_rows[phase] = phase_rows.get(phase, 0) + 1
            reason_rows[reason] = reason_rows.get(reason, 0) + 1
        if phase_metrics is None or phase_metrics != phase_rows:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        if reason_metrics is None or reason_metrics != reason_rows:
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()

        upstream_status = "clean" if invalid_count == 0 else "quarantined"
        quality_s = metrics_s.get("quarantined_depth_quality")
        if not isinstance(quality_s, dict):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        quality_fields = (
            "spread_bps_p50", "spread_bps_p95",
            "buy_slippage_bps_500usdt_p50", "buy_slippage_bps_500usdt_p95",
            "sell_slippage_bps_500usdt_p50", "sell_slippage_bps_500usdt_p95",
            "top_bid_depth_usdt_p05", "top_ask_depth_usdt_p05",
            "healthy_window_ratio",
        )
        if any(
            not isinstance(quality_s.get(key), (int, float))
            or isinstance(quality_s.get(key), bool)
            or not math.isfinite(float(quality_s[key]))
            for key in quality_fields
        ):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        availability = metrics_s.get("book_availability_ratio")
        latency = metrics_s.get("first_valid_book_latency_ms")
        if (
            not isinstance(availability, (int, float))
            or isinstance(availability, bool)
            or not math.isfinite(float(availability))
            or not isinstance(latency, int)
            or isinstance(latency, bool)
            or latency < 0
        ):
            _append_once(blockers, "stage1_5h_v2_event_bundle_input_rejected")
            return reject()
        static_metrics_s = _build_static_proxy_metrics_from_quality(
            quality_s,
            depth_quality_input_mode=(summary.get("depth_quality") or {}).get("depth_quality_input_mode"),
        )
        static_blockers_s = _static_proxy_blockers(static_metrics_s, metrics_s)
        proxy_status_s = "within_limits" if not static_blockers_s else "blocked"

        report_dict = {
            "event_symbol_id": s,
            "symbol": symbol_name,
            "source_article_id": sym_meta.get("source_article_id"),
            "event_id": sym_meta.get("event_id"),
            "stage1_5g_review_id": summary.get("stage1_5g_review_id"),
            "source_evidence_manifest_sha256": summary.get("source_evidence_manifest_sha256"),
            "formal_completed_event_symbol_ids_sha256": formal_hash,
            "stage1_5g_review_manifest_sha256": manifest_sha,
            "upstream_stage1_5g_status": upstream_status,
            "stage1_5h_static_proxy_status": proxy_status_s,
            "report_generation_status": "generated",
            "book_availability_ratio": metrics_s.get("book_availability_ratio"),
            "book_unavailable_ratio": metrics_s.get("book_unavailable_ratio"),
            "invalid_book_row_count": invalid_count,
            "valid_snapshot_count_after_quarantine": metrics_s.get("valid_snapshot_count_after_quarantine"),
            "observed_snapshot_count": metrics_s.get("observed_snapshot_count"),
            "first_valid_book_latency_ms": metrics_s.get("first_valid_book_latency_ms"),
            "max_consecutive_invalid": metrics_s.get("max_consecutive_invalid"),
            "max_consecutive_invalid_after_warmup": metrics_s.get("max_consecutive_invalid_after_warmup"),
            "invalid_book_by_phase": metrics_s.get("invalid_book_by_phase"),
            "invalid_book_by_reason": metrics_s.get("invalid_book_by_reason"),
            "static_proxy_metrics": static_metrics_s,
            "stage1_5h_static_proxy_blockers": static_blockers_s,
            "required_next_evidence": [
                "clean_stage1_5g_depth_evidence_or_additional_independent_quarantined_events",
                "higher_frequency_orderbook_for_more_precise_execution_proxy_design",
                "trade_prints_for_future_fill_model_research",
                "separate_governance_before_any_execution_feasibility_claim",
            ],
            **_v2_safety_fields(),
        }
        report_dict["markdown"] = _render_stage1_5h_v2_event_bundle_markdown(report_dict)
        prepared_reports[s] = report_dict

    return {
        "decision": "stage1_5h_v2_event_bundle_reports_ready",
        "report_generation_allowed": True,
        "event_symbol_ids": raw_ids,
        "reports": prepared_reports,
        "blockers": [],
        "stage1_5g_review_manifest_sha256": manifest_sha,
        "stage1_5g_review_id": summary.get("stage1_5g_review_id"),
        "source_evidence_manifest_sha256": summary.get("source_evidence_manifest_sha256"),
        "formal_completed_event_symbol_ids_sha256": formal_hash,
        **_v2_safety_fields(),
    }


def write_stage1_5h_v2_event_bundle_reports(
    *, bundle: Stage1_5HInputBundle, output_root: str | Path
) -> dict[str, Any]:
    supplied_root = Path(output_root).absolute()
    configured_reports_root = _STAGE1_5H_V2_REPORTS_ROOT.absolute()

    if (
        configured_reports_root.is_symlink()
        or supplied_root.is_symlink()
        or supplied_root.parent != configured_reports_root
    ):
        return {
            "decision": "stage1_5h_v2_event_bundle_output_rejected",
            "report_generation_allowed": False,
            "blockers": ["output_root_outside_authorized_reports_root"],
            **_v2_safety_fields(),
        }

    out_root = supplied_root.resolve()
    reports_parent = configured_reports_root.resolve()

    if out_root.exists():
        return {
            "decision": "stage1_5h_v2_event_bundle_output_rejected",
            "report_generation_allowed": False,
            "blockers": ["output_root_already_exists"],
            **_v2_safety_fields(),
        }

    if out_root.parent != reports_parent:
        return {
            "decision": "stage1_5h_v2_event_bundle_output_rejected",
            "report_generation_allowed": False,
            "blockers": ["output_root_outside_authorized_reports_root"],
            **_v2_safety_fields(),
        }

    prepared = build_stage1_5h_v2_event_bundle_reports(bundle)
    if prepared.get("decision") != "stage1_5h_v2_event_bundle_reports_ready":
        return prepared

    # Create root
    out_root.mkdir(parents=True, exist_ok=False)
    reports_dir = out_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=False)

    reports_meta: dict[str, dict[str, Any]] = {}
    for s in prepared["event_symbol_ids"]:
        rep = dict(prepared["reports"][s])
        md_text = rep.pop("markdown")

        json_path = reports_dir / f"{s}.json"
        md_path = reports_dir / f"{s}.md"

        json_bytes = json.dumps(rep, indent=2, ensure_ascii=False).encode("utf-8")
        json_path.write_bytes(json_bytes)

        md_bytes = (md_text + "\n").encode("utf-8")
        md_path.write_bytes(md_bytes)

        reports_meta[s] = {
            "json_relative_path": f"reports/{s}.json",
            "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
            "md_relative_path": f"reports/{s}.md",
            "md_sha256": hashlib.sha256(md_bytes).hexdigest(),
            "upstream_stage1_5g_status": rep["upstream_stage1_5g_status"],
            "stage1_5h_static_proxy_status": rep["stage1_5h_static_proxy_status"],
        }

    directory_payload = {
        "schema_version": 2,
        "upstream": {
            "stage1_5g_review_id": prepared["stage1_5g_review_id"],
            "source_evidence_manifest_sha256": prepared["source_evidence_manifest_sha256"],
            "formal_completed_event_symbol_ids_sha256": prepared["formal_completed_event_symbol_ids_sha256"],
            "stage1_5g_review_manifest_sha256": prepared["stage1_5g_review_manifest_sha256"],
        },
        "event_symbol_ids": prepared["event_symbol_ids"],
        "reports": {
            s: {
                "json_relative_path": reports_meta[s]["json_relative_path"],
                "json_sha256": reports_meta[s]["json_sha256"],
                "md_relative_path": reports_meta[s]["md_relative_path"],
                "md_sha256": reports_meta[s]["md_sha256"],
                "upstream_stage1_5g_status": reports_meta[s]["upstream_stage1_5g_status"],
                "stage1_5h_static_proxy_status": reports_meta[s]["stage1_5h_static_proxy_status"],
            }
            for s in prepared["event_symbol_ids"]
        },
        **_v2_safety_fields(),
    }
    dir_path = out_root / "event_directory.json"
    dir_bytes = json.dumps(directory_payload, indent=2, ensure_ascii=False).encode("utf-8")
    dir_path.write_bytes(dir_bytes)

    manifest_payload = {
        "schema_version": "stage1_5h_v2_event_bundle_manifest_v1",
        "bundle_status": "sealed_read_only_bundle",
        "upstream": dict(directory_payload["upstream"]),
        "event_symbol_ids": prepared["event_symbol_ids"],
        "event_directory": {
            "relative_path": "event_directory.json",
            "sha256": hashlib.sha256(dir_bytes).hexdigest(),
        },
        "reports": reports_meta,
        **_v2_safety_fields(),
    }

    manifest_path = out_root / "stage1_5h_event_bundle_manifest.json"
    temp_fd, temp_manifest_path = tempfile.mkstemp(dir=out_root, prefix="temp_manifest_", suffix=".json")
    with os.fdopen(temp_fd, "w", encoding="utf-8") as fh:
        json.dump(manifest_payload, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())

    os.replace(temp_manifest_path, manifest_path)

    return {
        "decision": "stage1_5h_v2_event_bundle_reports_sealed",
        "output_root": str(out_root),
        "manifest_path": str(manifest_path),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "event_symbol_ids": prepared["event_symbol_ids"],
        "report_count": len(prepared["event_symbol_ids"]),
        **_v2_safety_fields(),
    }


def verify_stage1_5h_v2_event_bundle_manifest(
    output_root: str | Path,
) -> tuple[bool, list[str]]:
    supplied_root = Path(output_root)
    if supplied_root.is_symlink():
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    out_root = supplied_root.resolve()
    manifest_path = out_root / "stage1_5h_event_bundle_manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return False, ["stage1_5h_v2_event_bundle_manifest_missing"]

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return False, ["stage1_5h_v2_event_bundle_manifest_corrupted"]
    if not isinstance(manifest_data, dict):
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    safety_keys = (
        "execution_feasibility_claim_allowed", "alpha_interpretation_allowed",
        "trade_signal_allowed", "paper_trading_allowed", "live_trading_allowed",
        "execution_engine_allowed", "private_endpoint_allowed", "api_key_allowed",
        "order_endpoint_allowed",
    )
    expected_manifest_keys = {
        "schema_version", "bundle_status", "upstream", "event_symbol_ids",
        "event_directory", "reports", *safety_keys,
    }
    expected_upstream_keys = {
        "stage1_5g_review_id", "source_evidence_manifest_sha256",
        "formal_completed_event_symbol_ids_sha256", "stage1_5g_review_manifest_sha256",
    }
    expected_report_meta_keys = {
        "json_relative_path", "json_sha256", "md_relative_path", "md_sha256",
        "upstream_stage1_5g_status", "stage1_5h_static_proxy_status",
    }
    if set(manifest_data) != expected_manifest_keys:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    if manifest_data.get("schema_version") != "stage1_5h_v2_event_bundle_manifest_v1" or manifest_data.get("bundle_status") != "sealed_read_only_bundle":
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    upstream = manifest_data.get("upstream")
    if not isinstance(upstream, dict) or set(upstream) != expected_upstream_keys:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    ids = manifest_data.get("event_symbol_ids")
    if not isinstance(ids, list) or not ids or ids != sorted(ids) or len(ids) != len(set(ids)):
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    dir_meta = manifest_data.get("event_directory")
    if not isinstance(dir_meta, dict) or set(dir_meta) != {"relative_path", "sha256"}:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    if dir_meta.get("relative_path") != "event_directory.json":
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    dir_path = out_root / "event_directory.json"
    if not dir_path.is_file() or dir_path.is_symlink():
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    dir_bytes = dir_path.read_bytes()
    if hashlib.sha256(dir_bytes).hexdigest() != dir_meta.get("sha256"):
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    try:
        directory_data = json.loads(dir_bytes.decode("utf-8"))
    except Exception:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    if not isinstance(directory_data, dict):
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    for p in (manifest_data, directory_data):
        if not all(p.get(k) is False for k in safety_keys):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    expected_dir_keys = {"schema_version", "upstream", "event_symbol_ids", "reports", *safety_keys}
    if set(directory_data) != expected_dir_keys:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
    if directory_data.get("event_symbol_ids") != ids or directory_data.get("upstream") != upstream:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    reports_meta = manifest_data.get("reports")
    directory_reports = directory_data.get("reports")
    if (
        not isinstance(reports_meta, dict)
        or not isinstance(directory_reports, dict)
        or set(reports_meta) != set(ids)
        or set(directory_reports) != set(ids)
    ):
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    reports_dir = out_root / "reports"
    if not reports_dir.is_dir() or reports_dir.is_symlink():
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    expected_tree_files = {
        manifest_path.resolve(),
        dir_path.resolve(),
    }

    for s in ids:
        meta_s = reports_meta.get(s)
        directory_meta_s = directory_reports.get(s)
        if not isinstance(meta_s, dict) or set(meta_s) != expected_report_meta_keys or directory_meta_s != meta_s:
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
        if (
            meta_s.get("json_relative_path") != f"reports/{s}.json"
            or meta_s.get("md_relative_path") != f"reports/{s}.md"
            or meta_s.get("upstream_stage1_5g_status") not in {"clean", "quarantined"}
            or meta_s.get("stage1_5h_static_proxy_status") not in {"within_limits", "blocked"}
        ):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
        json_p = reports_dir / f"{s}.json"
        md_p = reports_dir / f"{s}.md"

        if not json_p.is_file() or json_p.is_symlink() or not md_p.is_file() or md_p.is_symlink():
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

        json_bytes = json_p.read_bytes()
        if hashlib.sha256(json_bytes).hexdigest() != meta_s.get("json_sha256"):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

        md_bytes = md_p.read_bytes()
        if hashlib.sha256(md_bytes).hexdigest() != meta_s.get("md_sha256"):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

        try:
            rep_json = json.loads(json_bytes.decode("utf-8"))
        except Exception:
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

        if not all(rep_json.get(k) is False for k in safety_keys):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
        if (
            rep_json.get("event_symbol_id") != s
            or rep_json.get("upstream_stage1_5g_status") != meta_s["upstream_stage1_5g_status"]
            or rep_json.get("stage1_5h_static_proxy_status") != meta_s["stage1_5h_static_proxy_status"]
            or not isinstance(rep_json.get("stage1_5h_static_proxy_blockers"), list)
            or not all(isinstance(item, str) for item in rep_json["stage1_5h_static_proxy_blockers"])
            or rep_json["stage1_5h_static_proxy_status"] != (
                "within_limits" if not rep_json["stage1_5h_static_proxy_blockers"] else "blocked"
            )
            or md_bytes != (_render_stage1_5h_v2_event_bundle_markdown(rep_json) + "\n").encode("utf-8")
        ):
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

        expected_tree_files.add(json_p)
        expected_tree_files.add(md_p)

    actual_tree_files = set()
    for p in out_root.rglob("*"):
        if p.is_symlink():
            return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]
        if p.is_file():
            actual_tree_files.add(p.resolve())

    if actual_tree_files != expected_tree_files:
        return False, ["stage1_5h_v2_event_bundle_manifest_invalid"]

    return True, []
