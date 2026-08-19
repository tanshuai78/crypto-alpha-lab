"""
Stage 1.6A USD-M Futures Delisting Metric Population Builder, Gate Evaluator, and Summary Generator.
Design Reference: docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Set

import configs.base as base_config
from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    AUDIT_METRIC_DEFINITION_VERSION,
    CANDIDATE_DISCOVERY_RULE_VERSION,
    CANDIDATE_RECALL_PROBE_VERSION,
    STAGE1_6A_MODELS_VERSION,
    DelistingContract,
)


def build_stage1_6a_source_audit_summary(
    audit_result: Dict[str, Any],
    run_id: str,
    fixture_run: bool = True,
) -> Dict[str, Any]:
    """
    Builds the formal Stage 1.6A summary with frozen denominator metrics, gate predicates,
    and fail-closed authority caps (source_audit_passed=False, etc.).
    """
    manifest = audit_result["manifest"]
    metrics_raw = audit_result["metrics_raw"]
    contracts: List[DelistingContract] = audit_result["contracts"]
    notices: List[Dict[str, Any]] = audit_result["notices"]

    denom = metrics_raw["candidate_total_denominator"]
    trusted_parents = metrics_raw["trusted_parents_count"]
    symbols_mapped = metrics_raw["symbols_mapped_count"]
    classified_parents = metrics_raw["classified_parents_count"]
    forbidden_payloads = metrics_raw["forbidden_payload_count"]
    false_negatives = metrics_raw.get("candidate_discovery_false_negative_count", 0)

    # Rates based on immutable denominator and parent population
    source_integrity_pass_rate = (trusted_parents / denom) if denom > 0 else 0.0
    symbol_mapping_pass_rate = (symbols_mapped / trusted_parents) if trusted_parents > 0 else 0.0
    event_type_classification_pass_rate = (classified_parents / trusted_parents) if trusted_parents > 0 else 0.0

    # Count eligible in-scope contracts and parent notice diversity
    eligible_contracts = [c for c in contracts if c.source_audit_eligible]
    eligible_symbols: Set[str] = {c.canonical_symbol for c in eligible_contracts}

    eligible_notice_ids: Set[str] = {c.parent_article_id for c in eligible_contracts}
    historical_events_found = len(eligible_notice_ids)
    symbols_with_events = len(eligible_symbols)

    # Distinct UTC event dates from published_at_ms of eligible notices
    event_dates: Set[str] = set()
    for n in notices:
        if n.get("source_article_id") in eligible_notice_ids and n.get("published_at_ms"):
            dt_utc = datetime.fromtimestamp(n["published_at_ms"] / 1000.0, tz=timezone.utc)
            event_dates.add(dt_utc.strftime("%Y-%m-%d"))
    event_days = len(event_dates)

    # Candidate predicates
    source_schema_integrity_candidate = (
        source_integrity_pass_rate >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO
        and symbol_mapping_pass_rate >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO
        and event_type_classification_pass_rate >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO
        and forbidden_payloads <= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT
    )

    sample_sufficiency_candidate = (
        historical_events_found >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS
        and event_days >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS
        and symbols_with_events >= base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS
    )

    # In fixture/historical-contract-only implementation, authoritative flags are strictly capped
    summary = {
        "run_id": run_id,
        "implementation_scope": "fixture_historical_contract_only",
        "fixture_run": fixture_run,
        "source_audit_real_run_allowed": False,
        "source_audit_passed": False,  # Hard authority cap for contract-only implementation
        "point_in_time_source_validated": False,
        "market_data_coverage_passed": False,
        "risk_veto_candidate": False,
        "replay_allowed": False,
        "point_in_time_directional_replay_allowed": False,
        "trade_signal_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "allowed_next_action": "write_live_source_observation_design_only",
        "versions": {
            "models_version": STAGE1_6A_MODELS_VERSION,
            "candidate_discovery_rule_version": CANDIDATE_DISCOVERY_RULE_VERSION,
            "candidate_recall_probe_version": CANDIDATE_RECALL_PROBE_VERSION,  # P1-B explicit version
            "audit_metric_definition_version": AUDIT_METRIC_DEFINITION_VERSION,
        },
        "manifest_sha256": manifest.manifest_sha256,
        "metrics": {
            "candidate_total_denominator": denom,
            "trusted_parents_count": trusted_parents,
            "symbols_mapped_count": symbols_mapped,
            "classified_parents_count": classified_parents,
            "forbidden_payload_count": forbidden_payloads,
            "candidate_discovery_false_negative_count": false_negatives,
            "source_integrity_pass_rate": round(source_integrity_pass_rate, 4),
            "symbol_mapping_pass_rate": round(symbol_mapping_pass_rate, 4),
            "event_type_classification_pass_rate": round(event_type_classification_pass_rate, 4),
            "historical_events_found": historical_events_found,
            "symbols_with_events": symbols_with_events,
            "event_days": event_days,
            "mixed_notice_count": metrics_raw.get("mixed_notice_count", 0),
            "out_of_scope_child_count": metrics_raw.get("out_of_scope_child_count", 0),
            "usd_m_crypto_children_excluded_due_to_incomplete_parent_count": metrics_raw.get("usd_m_crypto_children_excluded_due_to_incomplete_parent_count", 0),
        },
        "diagnostic_candidate_predicates": {
            "source_schema_integrity_candidate": source_schema_integrity_candidate,
            "sample_sufficiency_candidate": sample_sufficiency_candidate,
        },
        "market_data_coverage": {
            "kline_price_coverage": "not_evaluable",
            "l2_orderbook_coverage": "not_evaluable",
            "funding_rate_coverage": "not_evaluable",
            "open_interest_coverage": "not_evaluable",
            "fee_schedule_coverage": "not_evaluable",
        },
    }
    return summary
