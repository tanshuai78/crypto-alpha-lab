import json
import os
import tempfile
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5a_historical_event_source_audit import (
    main,
)


def test_review_generator_writes_markdown_report():
    # GIVEN a mock summary JSON
    summary_data = {
        "stage": "external_signal_shadow_lab_stage1_5a",
        "scope": "historical_event_source_audit_only",
        "execution_engine_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "historical_replay_allowed": False,
        "live_smoke_allowed": False,
        "source_resource_safety_required": True,
        "overall_decision": "source_audit_passed",
        "research_result_valid": True,
        "metrics": {
            "historical_events_found": 30,
            "unique_event_days": 20,
            "symbols_with_events": 3,
            "source_integrity_pass_rate": 1.0,
            "trade_pair_mapping_pass_rate": 1.0,
            "timestamp_quality_high_or_medium_ratio": 1.0,
            "forbidden_payload_count": 0,
            "payload_too_large_count": 0,
            "json_depth_exceeded_count": 0,
            "disallowed_domain_count": 0,
            "schema_parse_error_count": 0,
            "timestamp_source_disagreement_count": 0,
            "source_format_drift_count": 0,
            "schema_quarantine_count": 0,
            "timestamp_quality_distribution": {"high": 30},
            "raw_cache_written": True,
            "raw_cache_path": "data/external_signal_shadow/stage1_5a/raw/20260622/binance",
            "network_result_not_deterministic": True,
            "collector_received_at_ms": 1710921605000,
        },
        "source_decisions": {
            "binance_announcements": {
                "decision": "source_audit_passed",
                "recommended_event_types_for_stage1_5b": ["exchange_delisting_notice"],
            }
        },
        "event_type_decisions": {
            "exchange_delisting_notice": "source_audit_passed",
            "major_unlock_event": "observation_only",
        },
    }

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", encoding="utf-8", delete=False) as f:
        json.dump(summary_data, f)
        f_name = f.name

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as out_f:
        out_name = out_f.name

    try:
        args = [
            "review_stage1_5a_historical_event_source_audit.py",
            "--summary",
            f_name,
            "--output-review",
            out_name,
        ]

        with patch("sys.argv", args):
            main()

        assert os.path.exists(out_name)
        with open(out_name, "r", encoding="utf-8") as r:
            content = r.read()

        assert "结论" in content
        assert "Source Integrity" in content
        assert "Source Resource Safety" in content
        assert "Raw Cache / Network Evidence" in content
        assert "network_result_not_deterministic" in content
        assert "data/external_signal_shadow/stage1_5a/raw/20260622/binance" in content
        assert "Timestamp / Available-at Quality" in content
        assert "Binance" in content or "binance" in content
        assert "exchange_delisting_notice" in content
        assert "dydx" in content or "unlock" in content or "observation_only" in content
        assert "write_stage1_5b_minimal_historical_event_table_implementation_plan" in content

    finally:
        os.unlink(f_name)
        os.unlink(out_name)
