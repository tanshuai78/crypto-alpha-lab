import json
import sys

from scripts.external_signal_shadow.review_stage1_5e_execution_feasibility_audit import main


def test_review_renders_decision_and_safety_boundaries(tmp_path, monkeypatch):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "decision": "stage1_5e_execution_feasibility_inconclusive_depth_missing",
        "execution_feasibility_proven": False,
        "historical_orderbook_depth_available": False,
        "historical_depth_coverage": {
            "historical_depth_file_count": 1358,
            "candidate_symbol_overlap_count": 0,
            "matched_snapshot_count": 0,
            "matched_candidate_event_count": 0,
            "coverage_reject_reason": "historical_orderbook_no_candidate_symbol_overlap",
        },
        "mark_index_proxy_available": False,
        "mark_index_divergence_status": "not_audited",
        "top_level_unique_symbol_event_count": 62,
        "cell_summaries": {
            "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay": {
                "cell_event_count": 62,
                "median_entry_bar_range_bps": 180.0,
                "p95_entry_bar_range_bps": 520.0,
                "cell_status": "inconclusive_depth_missing",
                "median_entry_1h_range_bps": 310.0,
                "median_entry_4h_range_bps": 550.0,
                "median_pre_entry_24h_quote_volume_usdt": 120_000_000.0,
                "quote_volume_pass_rate": 0.85,
                "median_spread_bps_if_live_depth_available": None,
                "median_slippage_bps_for_500usdt_buy_if_live_depth_available": None,
            }
        },
        "median_entry_bar_range_bps": 180.0,
        "p95_entry_bar_range_bps": 520.0,
        "blockers": ["historical_orderbook_depth_missing"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
    }))

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5e_execution_feasibility_audit.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ])

    assert main() == 0
    text = review.read_text()
    assert "stage1_5e_execution_feasibility_inconclusive_depth_missing" in text
    assert "historical_orderbook_depth_available" in text
    assert "historical_orderbook_no_candidate_symbol_overlap" in text
    assert "mark_index_divergence_status" in text
    assert "not_audited" in text
    assert "paper_trading_allowed" in text
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in text
