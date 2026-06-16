"""
tests/scripts/external_signal_shadow/test_review_stage1_4a2_vendor_liquidation_data_feasibility.py
"""
import json

from scripts.external_signal_shadow.review_stage1_4a2_vendor_liquidation_data_feasibility import (
    main,
)


def test_review_renders_vendor_table_and_recommendations(tmp_path) -> None:
    summary = {
        "decision": "vendor_liquidation_source_degraded",
        "primary_blocker": "no_feasible_vendor_sample",
        "recommended_vendor_order": ["tardis_dev", "coinglass"],
        "best_vendor": None,
        "lowest_cost_usable_vendor": None,
        "highest_data_quality_vendor": None,
        "purchase_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_4b_candidate_replay_allowed": False,
        "vendor_decisions": [
            {
                "vendor": "coinglass",
                "priority": "P2",
                "evidence_level": "official_api_docs",
                "sample_access_type": "unknown",
                "sample_file_available": False,
                "history_days_verified_from_sample": 0.0,
                "symbols_verified": [],
                "side_mapping_confidence": "unknown",
                "notional_usd_available": False,
                "timestamp_resolution_ms": None,
                "exchange_scope": "aggregated_unknown",
                "license_status": "unknown",
                "cost_tier": "enterprise_unknown",
                "decision": "vendor_liquidation_source_degraded",
                "primary_blocker": "sample_not_available",
                "next_action": "request_sample_or_trial",
            }
        ],
    }
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    rc = main(["--summary", str(summary_path), "--output-review", str(review_path)])
    assert rc == 0
    text = review_path.read_text(encoding="utf-8")
    assert "Per-Vendor Audit Table" in text
    assert "sample_not_available" in text
    assert "recommended_vendor_order" in text
    assert "不允许推出" in text or "不允许" in text


def test_review_marks_docs_only_as_not_data_feasible(tmp_path) -> None:
    summary = {
        "decision": "vendor_liquidation_source_degraded",
        "primary_blocker": "sample_not_available",
        "recommended_vendor_order": ["coinglass"],
        "best_vendor": None,
        "lowest_cost_usable_vendor": None,
        "highest_data_quality_vendor": None,
        "purchase_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_4b_candidate_replay_allowed": False,
        "vendor_decisions": [
            {
                "vendor": "coinglass",
                "evidence_level": "official_api_docs",
                "decision": "vendor_liquidation_source_degraded",
                "primary_blocker": "sample_not_available",
                "next_action": "request_sample_or_trial",
            }
        ],
    }
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    rc = main(["--summary", str(summary_path), "--output-review", str(review_path)])
    assert rc == 0
    text = review_path.read_text(encoding="utf-8")
    assert "docs-only feasibility smoke" in text or "docs-only" in text
    assert "不能证明 vendor liquidation source 可用" in text or "不能证明" in text
