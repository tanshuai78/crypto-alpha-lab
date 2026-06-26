from src.research.external_signal_shadow.stage1_5e_execution_feasibility_summary import (
    build_execution_feasibility_summary,
)


def test_summary_inconclusive_when_proxy_passes_but_depth_missing():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="missing",
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    assert summary["execution_feasibility_proven"] is False
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert cell in summary["cell_summaries"]
    assert cell in summary["inconclusive_cells"]


def test_summary_proxy_failed_when_entry_range_too_wide():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 400.0,  # exceeds EXTERNAL_SIGNAL_STAGE1_5E_MAX_ENTRY_15M_RANGE_BPS = 300
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed"
    assert "entry_15m_range_too_wide" in summary["blockers"]
    assert cell in summary["proxy_failed_cells"]


def test_summary_proxy_failed_when_quote_volume_pass_rate_below_threshold():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    candidate_rows = [{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)]
    proxy_rows = []
    for i in range(30):
        # quote volume is 100M for first 15 (passed), and 10M for remaining 15 (failed, since min quote vol is 50M)
        # pass rate = 15/30 = 0.50 (below 0.70 threshold)
        vol = 100_000_000.0 if i < 15 else 10_000_000.0
        proxy_rows.append({
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": vol,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        })

    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=candidate_rows,
        proxy_rows=proxy_rows,
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["cell_summaries"][cell]["quote_volume_pass_rate"] < 0.70
    assert summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed"
    assert "quote_volume_pass_rate_below_threshold" in summary["blockers"]


def test_summary_ready_for_live_depth_observer_when_proxy_ok_and_source_ready():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="operational_unvalidated",
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_audit_ready_for_live_depth_observer"
    assert summary["allowed_next_action"] == "write_stage1_5f_live_execution_feasibility_observer_design"
    assert cell in summary["ready_cells"]


def test_summary_does_not_treat_unmatched_historical_depth_path_as_ready():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=True,
        historical_depth_coverage={
            "historical_orderbook_depth_available": False,
            "matched_snapshot_count": 0,
            "matched_candidate_event_count": 0,
        },
        request_manifest_rows=[],
        stage1_5d_dependency_status="missing",
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_inconclusive_depth_missing"
    assert "historical_orderbook_depth_no_matched_snapshots" in summary["blockers"]
    assert summary["historical_orderbook_depth_available"] is False


def test_stage1_5d_pending_does_not_block_historical_proxy_audit():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(30)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="pending",
    )

    assert summary["historical_proxy_audit_valid"] is True
    assert summary["source_smoke_dependency_status"] == "pending"
    assert summary["decision"] == "stage1_5e_execution_feasibility_inconclusive_pending_stage1_5d"


def test_top_level_event_count_does_not_double_count_g1_g2_same_symbol_event():
    g1 = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    g2 = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G2_price_coverage_only"
    candidates = []
    proxies = []
    for i in range(30):
        for cell, group in ((g1, "G1_source_event_after_first_hour_delay"), (g2, "G2_price_coverage_only")):
            row = {"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": group, "cell_key": cell}
            candidates.append(row)
            proxies.append({
                **row,
                "historical_proxy_status": "proxy_computed",
                "entry_bar_found": True,
                "entry_bar_range_bps": 100.0,
                "entry_bar_close_to_open_bps": 50.0,
                "entry_1h_range_bps": 150.0,
                "entry_4h_range_bps": 200.0,
                "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
                "post_entry_1h_quote_volume_usdt": 5_000_000.0,
                "post_entry_4h_quote_volume_usdt": 15_000_000.0,
                "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
                "volume_collapse_ratio_1h": 1.25,
            })

    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=candidates,
        proxy_rows=proxies,
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
        stage1_5d_dependency_status="pending",
    )

    assert summary["top_level_unique_symbol_event_count"] == 30
    assert summary["cell_summaries"][g1]["cell_event_count"] == 30
    assert summary["cell_summaries"][g2]["cell_event_count"] == 30


def test_summary_invalid_when_candidate_count_below_minimum():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": "2026-06-01", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(10)],
        proxy_rows=[{
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": 100.0,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": "2026-06-01",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        } for i in range(10)],
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_invalid"
    assert "insufficient_candidate_event_count" in summary["blockers"]


def test_summary_proxy_failed_when_p95_range_multiplier_block_triggered():
    cell = "futures_contract_launch|futures_launch_long_attention_diagnostic|12h|G1_source_event_after_first_hour_delay"
    # p95 will be calculated. If we have 30 rows:
    # 29 rows have range 100 bps
    # 1 row has range 650 bps
    # The 95th percentile will be 650 bps, which exceeds MAX_ENTRY_15M_RANGE_BPS (300.0) * P95_RANGE_MULTIPLIER_BLOCK (2.0) = 600.0
    proxy_rows = []
    for i in range(30):
        val = 650.0 if i >= 27 else 100.0
        proxy_rows.append({
            "historical_proxy_status": "proxy_computed",
            "entry_bar_found": True,
            "entry_bar_range_bps": val,
            "entry_bar_close_to_open_bps": 50.0,
            "entry_1h_range_bps": 150.0,
            "entry_4h_range_bps": 200.0,
            "pre_entry_24h_quote_volume_usdt": 100_000_000.0,
            "post_entry_1h_quote_volume_usdt": 5_000_000.0,
            "post_entry_4h_quote_volume_usdt": 15_000_000.0,
            "median_same_symbol_pre_entry_24h_hourly_volume": 4_000_000.0,
            "volume_collapse_ratio_1h": 1.25,
            "symbol": f"S{i}USDT",
            "symbol_event_id": f"evt-{i}",
            "event_day": f"2026-06-{(i % 10) + 1:02d}",
            "filter_group": "G1_source_event_after_first_hour_delay",
            "cell_key": cell
        })

    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=[{"symbol": f"S{i}USDT", "symbol_event_id": f"evt-{i}", "event_day": f"2026-06-{(i % 10) + 1:02d}", "filter_group": "G1_source_event_after_first_hour_delay", "cell_key": cell} for i in range(30)],
        proxy_rows=proxy_rows,
        live_depth_rows=[],
        historical_orderbook_depth_available=False,
        request_manifest_rows=[],
    )

    assert summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed"
    assert "p95_entry_15m_range_exceeds_multiplier_threshold" in summary["blockers"]
