import ast
import json
from pathlib import Path

import configs.base as base_config
from src.research.external_signal_shadow.stage1_6a_futures_delisting_audit import (
    process_capture_bundle,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_models import (
    CANDIDATE_RECALL_PROBE_VERSION,
    AuditCandidateManifest,
    CandidateDiscoveryItem,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_summary import (
    build_stage1_6a_source_audit_summary,
)


def test_stage1_6a_config_constants_exact_values():
    """Verify all 8 Stage 1.6A research-audit constants exist with exact approved values."""
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS == 30
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS == 10
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO == 0.95
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO == 0.95
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO == 0.95
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT == 0
    assert base_config.EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES == 1


def test_stage1_6a_config_ast_single_target_assignments():
    """AST regression ensuring constants are top-level, exactly-once single-target assignments."""
    config_path = Path("configs/base.py")
    tree = ast.parse(config_path.read_text(encoding="utf-8"))

    expected_constants = {
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_HISTORICAL_EVENTS",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_DAYS",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOLS_WITH_EVENTS",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SOURCE_INTEGRITY_RATIO",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_SYMBOL_MAPPING_RATIO",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_EVENT_TYPE_CLASSIFICATION_RATIO",
        "EXTERNAL_SIGNAL_STAGE1_6A_MAX_FORBIDDEN_PAYLOAD_COUNT",
        "EXTERNAL_SIGNAL_STAGE1_6A_MIN_LIVE_OBSERVED_ELIGIBLE_NOTICES",
    }

    found_assignments = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in expected_constants:
                    assert len(node.targets) == 1, f"Multiple targets for {target.id}"
                    found_assignments.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id in expected_constants:
                found_assignments.append(node.target.id)

    assert set(found_assignments) == expected_constants
    assert len(found_assignments) == len(expected_constants), "Duplicate constant assignments detected"


def test_stage1_6a_safety_invariants():
    """Verify live trading and execution permissions remain strictly False."""
    assert getattr(base_config, "RISK_LIVE_TRADING_ENABLED", False) is False


def test_build_summary_from_synthetic_bundle():
    fixture_path = Path("tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl")
    records = [json.loads(line) for line in fixture_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    audit_result = process_capture_bundle(records)
    summary = build_stage1_6a_source_audit_summary(audit_result, run_id="run_test_001", fixture_run=True)

    assert summary["implementation_scope"] == "fixture_historical_contract_only"
    assert summary["source_audit_real_run_allowed"] is False
    assert summary["source_audit_passed"] is False
    assert summary["point_in_time_source_validated"] is False
    assert summary["market_data_coverage_passed"] is False
    assert summary["risk_veto_candidate"] is False
    assert summary["trade_signal_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["replay_allowed"] is False

    # Versions check (including P1-B recall probe version)
    assert summary["versions"]["candidate_recall_probe_version"] == CANDIDATE_RECALL_PROBE_VERSION

    # Metric checks
    m = summary["metrics"]
    assert m["candidate_total_denominator"] == 6
    assert m["trusted_parents_count"] == 5
    assert m["source_integrity_pass_rate"] == round(5 / 6, 4)
    assert m["symbols_with_events"] == 5  # MOB, DREP, UNFI, BTCDOM, PNT
    assert m["historical_events_found"] == 4  # 1001, 1002, 1003, 1004 (1005 was broken, 1007 unavailable)

    # Coverage
    cov = summary["market_data_coverage"]
    assert cov["kline_price_coverage"] == "not_evaluable"
    assert cov["l2_orderbook_coverage"] == "not_evaluable"


def test_source_integrity_rate_uses_frozen_pre_parse_40_notice_denominator():
    items = [
        CandidateDiscoveryItem(
            source_article_id=str(index),
            title=f"Binance Futures Will Delist {index}",
            first_list_capture_id="list",
            notice_lineage_first_detected_at_ms=None,
        )
        for index in range(40)
    ]
    audit_result = {
        "manifest": AuditCandidateManifest("manifest", "rule", items, "manifest-hash"),
        "metrics_raw": {
            "candidate_total_denominator": 40,
            "trusted_parents_count": 30,
            "symbols_mapped_count": 30,
            "classified_parents_count": 30,
            "forbidden_payload_count": 0,
        },
        "contracts": [],
        "notices": [],
    }
    summary = build_stage1_6a_source_audit_summary(audit_result, run_id="rate", fixture_run=True)
    assert summary["metrics"]["source_integrity_pass_rate"] == 0.75
