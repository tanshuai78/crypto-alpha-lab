import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5b_minimal_historical_event_table import (
    generate_review_content,
    main,
)


def test_review_writes_markdown_and_states_no_replay(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "source_audit_passed": True,
        "article_level_row_count": 94,
        "normalized_symbol_event_count": 194,
        "unique_event_days": 81,
        "symbols_with_events": 191,
        "event_type_counts_article_level": {
            "futures_contract_launch": 71,
            "exchange_delisting_notice": 23,
        },
        "event_type_counts_symbol_level": {
            "futures_contract_launch": 120,
            "exchange_delisting_notice": 74,
        },
        "blockers": [],
        "next_action": "write_stage1_5c_external_catalyst_replay_implementation_plan",
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": True,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "context_label_join_allowed": False,
    }))

    args = [
        "review_stage1_5b_minimal_historical_event_table.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()

    content = review.read_text()
    assert "Stage 1.5B" in content
    assert "stage1_5b_event_table_ready" in content
    assert "replay_allowed" in content
    assert "stage1_5c_replay_candidate_allowed" in content
    assert "market pair" in content or "tradability" in content
    assert "directional_hypothesis" in content
    assert "context_label_join_allowed" in content
    assert "write_stage1_5c_external_catalyst_replay_implementation_plan" in content


def test_review_failed_summary_does_not_claim_coverage_passed():
    content = generate_review_content({
        "decision": "stage1_5b_event_table_failed",
        "source_audit_passed": False,
        "article_level_row_count": 0,
        "normalized_symbol_event_count": 0,
        "unique_event_days": 0,
        "symbols_with_events": 0,
        "event_type_counts_article_level": {},
        "event_type_counts_symbol_level": {},
        "blockers": ["source_audit_not_passed"],
        "next_action": "fix_event_table_inputs_before_replay",
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": True,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "context_label_join_allowed": False,
    })

    assert "未达到 Stage 1.5B 事件表 ready 门槛" in content
    assert "达到了首期目标" not in content
    assert "具有合理的时间分布密度" not in content


def test_review_sparse_summary_states_inconclusive_not_passed():
    content = generate_review_content({
        "decision": "stage1_5b_event_table_sparse_inconclusive",
        "source_audit_passed": True,
        "article_level_row_count": 12,
        "normalized_symbol_event_count": 12,
        "unique_event_days": 8,
        "symbols_with_events": 4,
        "event_type_counts_article_level": {"futures_contract_launch": 12},
        "event_type_counts_symbol_level": {"futures_contract_launch": 12},
        "blockers": ["article_level_row_count_below_30", "unique_event_days_below_20"],
        "next_action": "collect_more_high_confidence_events_or_add_okx_source_audit",
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "stage1_5c_candidate_allowance_not_determined_by_stage1_5b": True,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "context_label_join_allowed": False,
    })

    assert "样本仍为 sparse/inconclusive" in content
    assert "达到了首期目标" not in content
    assert "具有合理的时间分布密度" not in content
