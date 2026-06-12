import json


def _summary(path):
    path.write_text(
        json.dumps(
            {
                "mode": "fixture_only_stage0",
                "decision": "external_signal_shadow_stage0_passed",
                "failure_type": "stage0_completed",
                "live_trading_enabled": False,
                "external_api_enabled": False,
                "wallet_required": False,
                "events_total": 9,
                "events_accepted": 6,
                "events_rejected": 2,
                "events_quarantined": 0,
                "branches": {
                    "no_cusum_all_accepted_events": {"shadow_order_count": 4},
                    "cusum_confirmed_events": {"shadow_order_count": 2},
                },
                "branch_semantics": {
                    "no_cusum_all_accepted_events": "baseline_control_not_strategy",
                    "cusum_confirmed_events": "confirmation_filtered_shadow_not_strategy",
                },
                "parameter_policy": "fixed_stage0_sanity_check_not_optimized",
                "alpha_interpretation_allowed": False,
            },
            indent=2,
        )
    )


def test_review_external_signal_shadow_stage0_writes_markdown(tmp_path):
    from scripts.review_external_signal_shadow_stage0 import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    _summary(summary)

    assert main(["--summary", str(summary), "--output", str(output)]) == 0
    assert output.exists()
    assert "External Signal Shadow Lab Stage 0 Review" in output.read_text()


def test_review_mentions_no_live_trading_and_no_external_api(tmp_path):
    from scripts.review_external_signal_shadow_stage0 import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    _summary(summary)
    main(["--summary", str(summary), "--output", str(output)])
    text = output.read_text()

    assert "不允许下单" in text
    assert "不允许接钱包" in text
    assert "external_api_enabled = false" in text


def test_review_explains_cusum_is_confirmation_not_alpha(tmp_path):
    from scripts.review_external_signal_shadow_stage0 import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    _summary(summary)
    main(["--summary", str(summary), "--output", str(output)])

    assert "CUSUM" in output.read_text()
    assert "不是 alpha" in output.read_text()


def test_review_explains_triple_barrier_is_shadow_evaluation(tmp_path):
    from scripts.review_external_signal_shadow_stage0 import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    _summary(summary)
    main(["--summary", str(summary), "--output", str(output)])

    assert "三重屏障" in output.read_text()
    assert "shadow" in output.read_text()


def test_review_includes_failure_taxonomy(tmp_path):
    from scripts.review_external_signal_shadow_stage0 import main

    summary = tmp_path / "summary.json"
    output = tmp_path / "review.md"
    _summary(summary)
    main(["--summary", str(summary), "--output", str(output)])

    assert "data_failure" in output.read_text()
    assert "shadow_order_structure_failure" in output.read_text()
