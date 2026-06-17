from research.external_signal_shadow.stage1_4a_lq30_summary import (
    build_source_quality_report,
    evaluate_lq30_summary,
)


def test_build_source_quality_report():
    loader_stats = {
        "raw_line_count": 100,
        "invalid_json_line_count": 2,
        "invalid_json_line_ratio": 0.02,
        "duplicate_event_count": 10,
        "resolved_path_count": 3,
    }
    parsed_rows = [
        {"symbol": "BTCUSDT", "timestamp_ms": 1710000000000 - 1000},
        {"symbol": "ETHUSDT", "timestamp_ms": 1710000000000 + 12 * 60 * 60 * 1000},
        {"symbol": "BTCUSDT", "timestamp_ms": 1710000000000 + 24 * 60 * 60 * 1000}, # max_ts, recent within 24h
    ]
    expected_symbols = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
    parse_stats = {
        "unknown_schema_count": 4,
        "missing_required_field_count": 3,
        "missing_timestamp_count": 2,
        "parse_error_count": 1,
    }

    report = build_source_quality_report(loader_stats, parsed_rows, expected_symbols, parse_stats)

    assert report["raw_row_count"] == 100
    assert report["raw_history_days"] == 1.0
    assert report["raw_recent_event_count_24h"] == 2 # ts at +12h and +24h are both in [max_ts - 24h, max_ts]
    assert report["duplicate_event_count"] == 10
    assert report["invalid_json_line_count"] == 2
    assert report["invalid_json_line_ratio"] == 0.02
    assert report["expected_symbol_coverage"] == 3
    assert report["actual_symbol_coverage"] == 2
    assert report["unknown_schema_count"] == 4
    assert report["missing_required_field_count"] == 3
    assert report["missing_timestamp_count"] == 2
    assert report["parse_error_count"] == 1
    assert report["collector_gap_verifiable"] is False
    assert report["rotation_fragment_count"] == 2
    assert report["archive_gap_observations"] == "event_sparse_stream_cannot_prove_uptime"


def test_evaluate_lq30_summary_promising():
    density = {
        "liquidation_history_days": 20,
        "symbols_with_events": 4,
        "event_days": 15,
        "max_single_symbol_event_share": 0.4,
        "max_single_day_event_share": 0.2,
        "top_1_day_notional_share": 0.3,
        "top_3_days_notional_share": 0.5,
        "top_1_symbol_notional_share": 0.4,
    }
    overlap = {
        "alignment_overlap_available": True,
        "data_alignment_overlap_event_days": 12,
    }
    source_quality = {
        "invalid_json_line_ratio": 0.0005,
    }

    summary = evaluate_lq30_summary(
        density_report=density,
        overlap_report=overlap,
        concentration_report={"notional_concentration": {}}, # evaluate uses density values for top_1_day_notional_share etc.
        source_quality_report=source_quality,
    )

    assert summary["decision"] == "liquidation_diagnostic_promising"
    assert summary["next_action"] == "continue_accumulating_exact_history"
    assert summary["complete_liquidation_tape_claim_allowed"] is False
    assert summary["paper_trading_allowed"] is False


def test_evaluate_lq30_summary_weak_due_to_low_density():
    density = {
        "liquidation_history_days": 20,
        "symbols_with_events": 2,  # min expected is 3
        "event_days": 15,
        "max_single_symbol_event_share": 0.4,
        "max_single_day_event_share": 0.2,
        "top_1_day_notional_share": 0.3,
        "top_3_days_notional_share": 0.5,
        "top_1_symbol_notional_share": 0.4,
    }
    overlap = {
        "alignment_overlap_available": True,
        "data_alignment_overlap_event_days": 12,
    }
    source_quality = {
        "invalid_json_line_ratio": 0.0005,
    }

    summary = evaluate_lq30_summary(
        density_report=density,
        overlap_report=overlap,
        concentration_report={"notional_concentration": {}},
        source_quality_report=source_quality,
    )

    assert summary["decision"] == "liquidation_diagnostic_weak"
    assert summary["next_action"] == "prioritize_vendor_sample" # alignment is available, but density fails core


def test_evaluate_lq30_summary_unusable():
    density = {
        "liquidation_history_days": 0.0,
        "symbols_with_events": 0,
        "event_days": 0,
        "max_single_symbol_event_share": 0.0,
        "max_single_day_event_share": 0.0,
        "top_1_day_notional_share": 0.0,
        "top_3_days_notional_share": 0.0,
        "top_1_symbol_notional_share": 0.0,
    }
    overlap = {
        "alignment_overlap_available": False,
        "data_alignment_overlap_event_days": 0,
    }
    source_quality = {
        "invalid_json_line_ratio": 0.0,
    }

    summary = evaluate_lq30_summary(
        density_report=density,
        overlap_report=overlap,
        concentration_report={"notional_concentration": {}},
        source_quality_report=source_quality,
    )

    assert summary["decision"] == "liquidation_diagnostic_unusable"
    assert summary["next_action"] == "stop_waiting_for_90d_until_source_quality_or_density_improves"


def test_evaluate_lq30_summary_unusable_when_source_quality_is_bad_even_with_history():
    density = {
        "liquidation_history_days": 20.0,
        "symbols_with_events": 3,
        "event_days": 12,
        "max_single_symbol_event_share": 0.4,
        "max_single_day_event_share": 0.2,
        "top_1_day_notional_share": 0.3,
        "top_3_days_notional_share": 0.5,
        "top_1_symbol_notional_share": 0.4,
    }
    overlap = {
        "alignment_overlap_available": True,
        "data_alignment_overlap_event_days": 12,
    }
    source_quality = {
        "invalid_json_line_ratio": 0.5,
        "actual_symbol_coverage": 0,
        "parse_error_count": 2,
    }

    summary = evaluate_lq30_summary(
        density_report=density,
        overlap_report=overlap,
        concentration_report={"notional_concentration": {}},
        source_quality_report=source_quality,
    )

    assert summary["decision"] == "liquidation_diagnostic_unusable"
    assert summary["next_action"] == "stop_waiting_for_90d_until_source_quality_or_density_improves"
