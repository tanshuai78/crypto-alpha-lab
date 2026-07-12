import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    build_stage1_5h_report_summary,
    generate_stage1_5h_chinese_report,
    load_stage1_5h_inputs,
    validate_stage1_5h_governance,
)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def governance_review_text() -> str:
    return "\n".join([
        "approval_owner = human_research_owner",
        "approval_artifact = docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md",
        "governance_approval_must_be_explicit = true",
        "governance_decision = read_only_report_generator_plan_allowed_with_constraints",
        "allowed_next_action = write_read_only_report_generator_implementation_plan",
        "implementation_plan_allowed = true",
        "implementation_allowed = false",
        "scope = single_event_fixture_bound_report_generator",
        "event_family_conclusion_allowed = false",
        "multi_event_aggregation_allowed = false",
        "execution_feasibility_claim_allowed = false",
    ]) + "\n"


def make_stage1_5h_fixture(tmp_path: Path):
    root = tmp_path / "stage1_5g" / "reviews" / "run1"
    summary = {
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "clean_depth_evidence_pass": False,
        "quarantined_depth_evidence_pass": True,
        "quarantine_candidate": True,
        "formal_announcement_and_launch_count": 1,
        "execution_feasibility_claim_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "event_family_conclusion_allowed": False,
        "cross_event_generalization_allowed": False,
        "blockers": [],
        "warnings": ["summary_level_warning_to_preserve"],
        "clean_pass_missing_reason": [
            "upstream_reason_first",
            "invalid_book_present",
            "observation_initial_empty_book_present",
            "midrun_empty_book_present",
            "launch_time_missing_warmup_anchor_degraded",
        ],
        "quarantine": {
            "blockers": [],
            "warnings": ["launch_time_missing_warmup_anchor_degraded"],
            "clean_depth_evidence_pass": False,
            "quarantined_depth_evidence_pass": True,
            "quarantine_candidate": True,
            "observed_snapshot_count": 718,
            "expected_snapshot_count": 720,
            "invalid_book_row_count": 12,
            "invalid_book_ratio_observed": 0.016713091922005572,
            "valid_snapshot_count_after_quarantine": 706,
            "book_availability_ratio": 0.9805555555555555,
            "book_unavailable_ratio": 0.016666666666666666,
            "invalid_book_by_phase": {"observation_initial": 11, "midrun": 1, "launch_warmup": 0},
            "invalid_book_by_reason": {
                "observation_initial_empty_book": 11,
                "midrun_empty_book": 1,
                "crossed_or_negative_book": 0,
                "schema_invalid": 0,
            },
            "max_consecutive_invalid": 11,
            "max_consecutive_invalid_after_warmup": 1,
            "first_valid_book_latency_ms": 661950,
            "depth_quality_input_row_count": 706,
            "quarantined_invalid_book_row_count": 12,
        },
        "depth_quality": {
            "depth_quality_clean_mode_available": False,
            "depth_quality_quarantined_mode_available": True,
            "depth_quality_input_mode": "quarantined_valid_rows",
            "depth_quality_input_row_count": 706,
            "excluded_invalid_book_row_count": 12,
            "quarantined_depth_quality": {
                "spread_bps_p50": 1.1712687779075193,
                "spread_bps_p95": 2.948591635308917,
                "buy_slippage_bps_500usdt_p50": 0.874380647784001,
                "buy_slippage_bps_500usdt_p95": 2.050259958923384,
                "sell_slippage_bps_500usdt_p50": 0.8679232830582917,
                "sell_slippage_bps_500usdt_p95": 1.8699513715880745,
                "top_bid_depth_usdt_p05": 49704.083725000004,
                "top_ask_depth_usdt_p05": 50671.400125,
                "healthy_window_ratio": 1.0,
                "input_valid_rows": 706,
                "excluded_invalid_rows": 12,
                "blockers": [],
                "warnings": [],
            },
        },
    }
    quarantine = dict(summary["quarantine"])
    summary_path = write_json(root / "stage1_5g_live_depth_evidence_review_summary.json", summary)
    quarantine_path = write_json(root / "stage1_5g_quarantine_summary.json", quarantine)
    valid_rows_path = write_jsonl(root / "depth_quality_input_rows.jsonl", [{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "best_bid": 1.0, "best_ask": 1.01} for _ in range(706)])
    invalid_rows_path = write_jsonl(root / "quarantined_invalid_book_rows.jsonl", [{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "depth_status": "invalid"} for _ in range(12)])
    governance_review_path = tmp_path / "docs" / "reviews" / "2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md"
    governance_review_path.parent.mkdir(parents=True, exist_ok=True)
    governance_review_path.write_text(governance_review_text(), encoding="utf-8")
    return summary_path, quarantine_path, valid_rows_path, invalid_rows_path, governance_review_path


def load_fixture_bundle(tmp_path: Path):
    paths = make_stage1_5h_fixture(tmp_path)
    return load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )


def test_load_stage1_5h_inputs_reads_all_required_artifacts(tmp_path):
    bundle = load_fixture_bundle(tmp_path)

    assert bundle.loader_blockers == []
    assert bundle.stage1_5g_summary["decision"] == "stage1_5g_depth_evidence_quarantined_pass"
    assert bundle.quarantine_summary["invalid_book_row_count"] == 12
    assert len(bundle.depth_quality_input_rows) == 706
    assert len(bundle.quarantined_invalid_book_rows) == 12
    assert bundle.governance_review_path.name.endswith("stage1-5h-read-only-report-generator-governance-review_CN.md")
    assert "approval_owner = human_research_owner" in bundle.governance_review_text


def test_governance_validation_requires_explicit_approval(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_missing" in result["blockers"]
    assert result["governance_plan_admission_confirmed"] is False
    assert result["report_generation_allowed"] is False
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_governance_validation_requires_approval_owner_and_artifact(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text(
        "governance_decision = read_only_report_generator_plan_allowed_with_constraints\n"
        "implementation_plan_allowed = true\n"
        "implementation_allowed = false\n",
        encoding="utf-8",
    )
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_owner_missing" in result["blockers"]
    assert "governance_approval_artifact_missing" in result["blockers"]


def test_governance_validation_rejects_generic_text_file_with_matching_decision_only(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    generic = tmp_path / "approval.txt"
    generic.write_text(governance_review_text(), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=generic,
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_artifact_path_invalid" in result["blockers"]


def test_governance_validation_rejects_same_filename_outside_review_artifact_path(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    spoof = tmp_path / "not_docs" / "not_reviews" / "2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md"
    spoof.parent.mkdir(parents=True, exist_ok=True)
    spoof.write_text(governance_review_text(), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=spoof,
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_artifact_path_invalid" in result["blockers"]


def test_stage1_5h_rejects_invalid_stage1_5g_input(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["decision"] = "stage1_5g_depth_evidence_invalid"
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "invalid_stage1_5g_decision" in result["blockers"]


def test_stage1_5h_rejects_true_execution_or_trading_flags_once(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["paper_trading_allowed"] = True
    summary["live_trading_allowed"] = True
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert result["blockers"].count("unsafe_upstream_flag_true") == 1
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_stage1_5h_rejects_artifact_row_count_mismatch(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[2].write_text('{"event_symbol_id":"es1"}\n', encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]


def test_stage1_5h_rejects_quarantine_summary_value_mismatch(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    quarantine = json.loads(paths[1].read_text(encoding="utf-8"))
    quarantine["book_availability_ratio"] = 1.0
    paths[1].write_text(json.dumps(quarantine), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]


def test_stage1_5h_rejects_depth_quality_input_count_mismatch_between_summary_and_jsonl(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["depth_quality_input_row_count"] = 705
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]


def test_build_stage1_5h_report_summary_preserves_quarantine_and_cost_floor(tmp_path):
    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))

    assert result["decision"] == "stage1_5h_single_event_static_proxy_report_generated"
    assert result["allowed_next_action"] == "review_stage1_5h_read_only_report"
    assert result["scope"] == "single_event_fixture_bound_report_generator"
    assert result["governance_plan_admission_confirmed"] is True
    assert result["report_generation_allowed"] is True
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["clean_depth_evidence_pass"] is False
    assert result["quarantined_depth_evidence_pass"] is True
    assert result["clean_pass_missing_reason"] == [
        "upstream_reason_first",
        "invalid_book_present",
        "observation_initial_empty_book_present",
        "midrun_empty_book_present",
        "launch_time_missing_warmup_anchor_degraded",
    ]
    assert result["quarantine_warnings"] == ["launch_time_missing_warmup_anchor_degraded"]
    assert result["summary_warnings"] == ["summary_level_warning_to_preserve"]
    assert result["book_availability_ratio"] == 0.9805555555555555
    assert result["static_proxy_metrics"]["observed_static_depth_friction_bps_p95"] == 2.050259958923384 + 1.8699513715880745
    assert result["static_proxy_metrics"]["configured_conservative_round_trip_cost_bps"] == 50.0
    assert result["static_proxy_metrics"]["effective_friction_floor_bps"] == 50.0
    assert result["static_proxy_report_status"] == "proxy_metrics_within_configured_bounds"
    assert result["static_proxy_blockers"] == []
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_report_generator_preserves_upstream_clean_pass_missing_reason_without_reordering(tmp_path):
    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    assert result["clean_pass_missing_reason"][0] == "upstream_reason_first"


def test_report_generator_reconstructs_missing_reason_with_warning(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary.pop("clean_pass_missing_reason")
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert "invalid_book_present" in result["clean_pass_missing_reason"]
    assert "clean_pass_missing_reason_reconstructed_by_stage1_5h" in result["warnings"]


def test_report_generator_blocks_when_spread_p95_exceeds_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["quarantined_depth_quality"]["spread_bps_p95"] = 99.0
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "spread_p95_too_high" in result["static_proxy_blockers"]


def test_report_generator_blocks_when_top_depth_p05_below_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["quarantined_depth_quality"]["top_bid_depth_usdt_p05"] = 1.0
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "top_bid_depth_p05_too_low" in result["static_proxy_blockers"]


def test_report_generator_blocks_when_book_availability_below_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    quarantine = json.loads(paths[1].read_text(encoding="utf-8"))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    quarantine["book_availability_ratio"] = 0.97
    summary["quarantine"]["book_availability_ratio"] = 0.97
    paths[1].write_text(json.dumps(quarantine), encoding="utf-8")
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "book_availability_ratio_below_threshold" in result["static_proxy_blockers"]


def test_generate_stage1_5h_chinese_report_includes_safety_and_quarantine_context(tmp_path):
    summary = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    markdown = generate_stage1_5h_chinese_report(summary)

    assert "Stage 1.5H" in markdown
    assert "只读" in markdown
    assert "single_event_fixture_bound_report_generator" in markdown
    assert "clean_depth_evidence_pass = false" in markdown
    assert "quarantined_depth_evidence_pass = true" in markdown
    assert "execution_feasibility_claim_allowed = false" in markdown
    assert "effective_friction_floor_bps" in markdown
    assert "static_proxy_report_status" in markdown
    assert "不能作为 paper/live 或执行可行性证明" in markdown


def test_report_summary_never_contains_order_signal_or_pnl_terms(tmp_path):
    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    encoded = json.dumps(result, ensure_ascii=False)

    forbidden = [
        "SignalCandidate",
        "TradeIntent",
        "virtual_order",
        "hypothetical_trade",
        "entry_exit_path",
        "fill_probability",
        "order_lifecycle_state_machine",
        "pnl_path",
    ]
    for term in forbidden:
        assert term not in encoded
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_report_generator_returns_safe_noop_when_governance_fails(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )
    result = build_stage1_5h_report_summary(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["execution_engine_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False
    assert "governance_approval_missing" in result["blockers"]
