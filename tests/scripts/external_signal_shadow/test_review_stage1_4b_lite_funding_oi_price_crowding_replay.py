import json

from scripts.external_signal_shadow.review_stage1_4b_lite_funding_oi_price_crowding_replay import (
    main,
)


def test_review_generator_writes_markdown_report(tmp_path):
    summary_path = tmp_path / "summary.json"
    review_path = tmp_path / "review.md"

    summary_data = {
        "decision": "crowding_lite_failed",
        "next_action": "stop_crowding_only_branch",
        "liquidation_used": False,
        "full_derivatives_stress_composite_claim_allowed": False,
        "stage1_4b_full_composite_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "signed_replay_only": True,
        "execution_intent_allowed": False,
        "b_lite_failure_interpretation": "crowding_only_failed_not_full_composite_failed",
        "liquidation_missing_leg_remains_unresolved": True,
        "fixture_run": True,
        "research_result_valid": False,
        "total_events": 10,
        "total_days": 2,
        "total_symbols": 1,
        "max_single_symbol_event_share": 1.0,
        "max_single_day_event_share": 0.6,
        "top_5_positive_events_gross_profit_share": 0.5,
        "top_5_abs_pnl_share": 0.4,
        "candidates": {
            "oi_expansion_trend_confirmation": {
                "candidate_name": "oi_expansion_trend_confirmation",
                "event_count": 5,
                "event_days": 2,
                "symbols_count": 1,
                "median_net_return_bps": 15.0,
                "random_baseline_median_bps": 10.0,
                "price_move_baseline_median_bps": 5.0,
                "max_single_symbol_event_share": 1.0,
                "max_single_day_event_share": 0.6,
                "top_5_positive_events_gross_profit_share": 0.5,
                "top_5_abs_pnl_share": 0.4,
                "decision": "crowding_lite_failed",
                "blocker": "total_event_count_below_min"
            },
            "funding_oi_crowding_unwind": {
                "candidate_name": "funding_oi_crowding_unwind",
                "event_count": 5,
                "event_days": 2,
                "symbols_count": 1,
                "median_net_return_bps": -20.0,
                "random_baseline_median_bps": 5.0,
                "price_move_baseline_median_bps": 5.0,
                "max_single_symbol_event_share": 1.0,
                "max_single_day_event_share": 0.6,
                "top_5_positive_events_gross_profit_share": 0.0,
                "top_5_abs_pnl_share": 0.4,
                "decision": "crowding_lite_failed",
                "blocker": "total_event_count_below_min"
            },
            "oi_contraction_after_price_flush": {
                "candidate_name": "oi_contraction_after_price_flush",
                "event_count": 0,
                "event_days": 0,
                "symbols_count": 0,
                "median_net_return_bps": 0.0,
                "random_baseline_median_bps": 0.0,
                "price_move_baseline_median_bps": 0.0,
                "max_single_symbol_event_share": 0.0,
                "max_single_day_event_share": 0.0,
                "top_5_positive_events_gross_profit_share": 0.0,
                "top_5_abs_pnl_share": 0.0,
                "decision": "crowding_lite_failed",
                "blocker": "total_event_count_below_min"
            }
        }
    }

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    rc = main([
        "--summary", str(summary_path),
        "--output-review", str(review_path)
    ])

    assert rc == 0
    assert review_path.exists()

    content = review_path.read_text(encoding="utf-8")
    assert "B-Lite fail != full composite fail" in content or "B-Lite 失败不代表复合条件失败" in content
    assert "liquidation_missing_leg_remains_unresolved" in content
    assert "short" in content or "空头" in content
    assert "crowding_lite_failed" in content
    assert "stop_crowding_only_branch" in content
    assert "oi_expansion_trend_confirmation" in content
    assert "funding_oi_crowding_unwind" in content
    assert "oi_contraction_after_price_flush" in content
    assert "fixture" in content.lower()
    assert "research_result_valid" in content
    assert "smoke run" in content.lower() or "不能证明" in content
