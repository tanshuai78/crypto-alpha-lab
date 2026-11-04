"""Tests for launch_open_interest_basis_exploratory.py.

Conforms to L1 engineering process, Rule 15 fixture provenance integrity,
and independent expected value calculations.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
    OBSERVATION_OFFSET_MS,
    AggTradeRecord,
    ChildEvaluation,
    KlineBar,
    LaunchOiResearchError,
    OiMetricRecord,
    ParentEvaluation,
    aggregate_and_group,
    calculate_baseline,
    calculate_basis,
    calculate_oi_change,
    calculate_path_response,
    compute_required_utc_dates,
    evaluate_oi_scenarios,
    execute_exploratory_pipeline,
    load_child_aggtrades_from_ja_root,
    load_child_oi_metrics_from_sources,
    perform_parent_jackknife,
)


def test_scenario_assumptions_abc_independent_vector():
    """Task 1 (Plan L49): T0 = 16:03:00, D = 16:28:00 (T0 + 25m).

    Given 5m grid labels 16:00, 16:05, 16:10, 16:15, 16:20, 16:25:
    - Scenario A (+5m = 300,000ms): selects (L0, L1) = (16:15, 16:20)
    - Scenario B (+10m = 600,000ms, Main): selects (L0, L1) = (16:10, 16:15)
    - Scenario C (+15m = 900,000ms): selects (L0, L1) = (16:05, 16:10)
    Also verifies opening grid control floor_5m(T0) = (16:00, 16:05) and explicit scenario assumption fields.
    """
    # 16:00:00 UTC in ms from midnight = 16 * 3600 * 1000 = 57,600,000
    t_1600 = 57_600_000
    t_1603 = t_1600 + 180_000  # 57,780,000 (16:03:00)
    t_1605 = t_1600 + 300_000  # 57,900,000 (16:05:00)
    t_1610 = t_1600 + 600_000  # 58,200,000 (16:10:00)
    t_1615 = t_1600 + 900_000  # 58,500,000 (16:15:00)
    t_1620 = t_1600 + 1_200_000  # 58,800,000 (16:20:00)
    t_1625 = t_1600 + 1_500_000  # 59,100,000 (16:25:00)
    d_1628 = t_1603 + 1_500_000  # 59,280,000 (16:28:00 = T0 + 25m)

    records = [
        OiMetricRecord(create_time_ms=t_1600, symbol="TESTUSDT", sum_open_interest=80.0, unit="TEST"),
        OiMetricRecord(create_time_ms=t_1605, symbol="TESTUSDT", sum_open_interest=100.0, unit="TEST"),
        OiMetricRecord(create_time_ms=t_1610, symbol="TESTUSDT", sum_open_interest=120.0, unit="TEST"),
        OiMetricRecord(create_time_ms=t_1615, symbol="TESTUSDT", sum_open_interest=150.0, unit="TEST"),
        OiMetricRecord(create_time_ms=t_1620, symbol="TESTUSDT", sum_open_interest=210.0, unit="TEST"),
        OiMetricRecord(create_time_ms=t_1625, symbol="TESTUSDT", sum_open_interest=300.0, unit="TEST"),
    ]

    scen = evaluate_oi_scenarios(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t_1603,
        d_ms=d_1628,
        scheduled_launch_ms=t_1600,
    )
    assert set(scen.keys()) == {"A", "B", "C"}

    # Scenario A: info_offset=0, pub_margin=300k -> total=300k -> L1 <= 16:23 -> (16:15, 16:20), OI: 150 -> 210 (+0.40)
    res_a = scen["A"]
    assert res_a.status == "ok"
    assert res_a.l0_ms == t_1615
    assert res_a.l1_ms == t_1620
    assert res_a.oi_l0 == 150.0
    assert res_a.oi_l1 == 210.0
    assert abs(res_a.oi_change - 0.40) < 1e-9
    assert res_a.assumed_info_time_l1_ms == t_1620
    assert res_a.assumed_avail_time_l1_ms == t_1620 + 300_000
    assert res_a.label_age_ms == d_1628 - t_1620  # 480,000 ms (8m)
    assert res_a.assumed_avail_age_ms == d_1628 - (t_1620 + 300_000)  # 180,000 ms (3m)
    assert res_a.real_pit_verified is False
    assert res_a.information_time_ms is None
    assert res_a.available_time_ms is None

    # Scenario B (Main): info_offset=300k, pub_margin=300k -> total=600k -> L1 <= 16:18 -> (16:10, 16:15), OI: 120 -> 150 (+0.25)
    res_b = scen["B"]
    assert res_b.status == "ok"
    assert res_b.l0_ms == t_1610
    assert res_b.l1_ms == t_1615
    assert res_b.oi_l0 == 120.0
    assert res_b.oi_l1 == 150.0
    assert abs(res_b.oi_change - 0.25) < 1e-9
    assert res_b.assumed_info_time_l1_ms == t_1615 + 300_000
    assert res_b.assumed_avail_time_l1_ms == t_1615 + 600_000
    assert res_b.label_age_ms == d_1628 - t_1615  # 780,000 ms (13m)
    assert res_b.assumed_avail_age_ms == d_1628 - (t_1615 + 600_000)  # 180,000 ms (3m)
    assert res_b.real_pit_verified is False
    assert res_b.information_time_ms is None
    assert res_b.available_time_ms is None

    # Scenario C: info_offset=600k, pub_margin=300k -> total=900k -> L1 <= 16:13 -> (16:05, 16:10), OI: 100 -> 120 (+0.20)
    res_c = scen["C"]
    assert res_c.status == "ok"
    assert res_c.l0_ms == t_1605
    assert res_c.l1_ms == t_1610
    assert res_c.oi_l0 == 100.0
    assert res_c.oi_l1 == 120.0
    assert abs(res_c.oi_change - 0.20) < 1e-9
    assert res_c.assumed_info_time_l1_ms == t_1610 + 600_000
    assert res_c.assumed_avail_time_l1_ms == t_1610 + 900_000
    assert res_c.label_age_ms == d_1628 - t_1610  # 1,080,000 ms (18m)
    assert res_c.assumed_avail_age_ms == d_1628 - (t_1610 + 900_000)  # 180,000 ms (3m)

    # Opening grid control: floor_5m(16:03) = 16:00, L1 = 16:05 (OI: 80 -> 100, +0.25)
    for k in ("A", "B", "C"):
        assert scen[k].grid_status == "ok"
        assert scen[k].grid_l0_ms == t_1600
        assert scen[k].grid_l1_ms == t_1605
        assert abs(scen[k].grid_oi_change - 0.25) < 1e-9
        assert scen[k].grid_t0_minus_l0_ms == 180_000
        assert scen[k].grid_scheduled_minus_l0_ms == 0
        assert scen[k].grid_coincides_with_main is False


def test_scenario_boundary_exact_d_and_plus_1ms_and_verified_fact_conflict():
    """Task 1 (Plan L49-50):
    - Exact equality assumed_available_time == D is accepted; D + 1ms is excluded.
    - Cross-day dates cover up to T0 + 40m05s (2,405,000 ms).
    - Injecting a verified time fact that conflicts with a scenario stops that scenario with 'verified_fact_conflict'.
    """
    t0 = 0
    d = 1_500_000  # T0 + 25m
    # Under Scenario B (total_margin = 600,000 ms), cutoff is D - 600,000 = 900,000 ms (15m).
    # At L1 = 900,000 ms, assumed_available_time = 1,500,000 == D (accepted).
    records_exact = [
        OiMetricRecord(create_time_ms=600_000, symbol="S1", sum_open_interest=100.0, unit="S1"),
        OiMetricRecord(create_time_ms=900_000, symbol="S1", sum_open_interest=130.0, unit="S1"),
    ]
    res_exact = evaluate_oi_scenarios(records_exact, "S1", t0_ms=t0, d_ms=d)["B"]
    assert res_exact.status == "ok"
    assert res_exact.l0_ms == 600_000
    assert res_exact.l1_ms == 900_000
    assert res_exact.assumed_avail_time_l1_ms == d
    assert res_exact.assumed_avail_age_ms == 0

    # If D is 1ms earlier (d - 1 = 1,499,999), L1 = 900,000 has assumed_avail = 1,500,000 > D - 1 (rejected).
    # Only 600,000 remains <= cutoff, whose predecessor 300,000 is missing -> missing_predecessor.
    res_plus_1ms = evaluate_oi_scenarios(records_exact, "S1", t0_ms=t0, d_ms=d - 1)["B"]
    assert res_plus_1ms.status == "missing_predecessor"

    # Cross-day date coverage up to T0 + 40m05s (2,405,000 ms):
    # Suppose T0 is at 23:19:56 UTC on 2026-10-01 (1790896796000 ms).
    # T0 + 30m05s would still be on 2026-10-01 (23:50:01 UTC),
    # whereas T0 + 40m05s is 2026-10-02 00:00:01 UTC!
    t0_cross = 1_790_896_796_000  # 2026-10-01 23:19:56 UTC
    dates = compute_required_utc_dates(t0_cross)
    assert dates == ["2026-10-01", "2026-10-02"]

    # Verified fact conflict: suppose record at 600,000 carries verified_information_time_ms = 600,000 + 400,000 = 1,000,000.
    # This conflicts with Scenario A (assumed_info = T + 0 = 600,000) and Scenario B (assumed_info = T + 300,000 = 900,000),
    # but does NOT conflict with Scenario C (assumed_info = T + 600,000 = 1,200,000 <= D).
    records_conflict = [
        OiMetricRecord(create_time_ms=0, symbol="S1", sum_open_interest=80.0, unit="S1"),
        OiMetricRecord(create_time_ms=300_000, symbol="S1", sum_open_interest=100.0, unit="S1"),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="S1",
            sum_open_interest=120.0,
            unit="S1",
            verified_information_time_ms=1_000_000,
        ),
        OiMetricRecord(create_time_ms=900_000, symbol="S1", sum_open_interest=150.0, unit="S1"),
    ]
    scen_conf = evaluate_oi_scenarios(records_conflict, "S1", t0_ms=t0, d_ms=d)
    assert scen_conf["A"].status == "verified_fact_conflict"
    assert scen_conf["A"].oi_change is None
    assert scen_conf["B"].status == "verified_fact_conflict"
    assert scen_conf["B"].oi_change is None
    assert scen_conf["C"].status == "ok"
    assert scen_conf["C"].l0_ms == 300_000
    assert scen_conf["C"].l1_ms == 600_000


def test_basis_natural_minute_and_1628_negative_vectors():
    """Task 1 (Plan L53):
    Fix D = 16:28:00 (59,280,000 ms).
    1. Given valid Mark/Index 1m bar pairs ending at 16:27:00 and 16:28:00, selects 16:27:00 and rejects 16:28:00 (> D - 1m).
    2. Given Mark and Index bars whose end times both satisfy <= D - 1m but belong to different natural minutes, rejects pairing.
    """
    d_1628 = 59_280_000  # 16:28:00
    open_1625 = 59_100_000  # 16:25:00
    open_1626 = 59_160_000  # 16:26:00
    end_1626 = 59_160_000  # 16:26:00
    open_1627 = 59_220_000  # 16:27:00
    end_1627 = 59_220_000  # 16:27:00 (== D - 1m)
    end_1628 = 59_280_000  # 16:28:00 (> D - 1m)

    mark_bars = [
        KlineBar(open_time_ms=open_1626, close_time_ms=end_1627, close_price=105.0, symbol="TESTUSDT", unit="USDT"),
        KlineBar(open_time_ms=open_1627, close_time_ms=end_1628, close_price=120.0, symbol="TESTUSDT", unit="USDT"),
    ]
    index_bars = [
        KlineBar(open_time_ms=open_1626, close_time_ms=end_1627, close_price=100.0, symbol="TESTUSDT_INDEX", unit="USDT"),
        KlineBar(open_time_ms=open_1627, close_time_ms=end_1628, close_price=100.0, symbol="TESTUSDT_INDEX", unit="USDT"),
    ]
    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TESTUSDT",
        mapped_index_symbol="TESTUSDT_INDEX",
        d_ms=d_1628,
        cutoff_margin_ms=60_000,
    )
    assert res.status == "ok"
    assert res.bar_open_time_ms == open_1626
    assert res.bar_close_time_ms == end_1627
    assert abs(res.basis - 0.05) < 1e-9

    # Different natural minutes (Mark is 16:25-16:26, Index is 16:26-16:27; or Mark open_time is non-natural minute)
    mark_diff_min = [
        KlineBar(open_time_ms=open_1625, close_time_ms=end_1626, close_price=105.0, symbol="TESTUSDT", unit="USDT"),
        # Also test non-natural minute bar with same close_time_ms
        KlineBar(open_time_ms=open_1626 + 15_000, close_time_ms=end_1627, close_price=105.0, symbol="TESTUSDT", unit="USDT"),
    ]
    index_diff_min = [
        KlineBar(open_time_ms=open_1626, close_time_ms=end_1627, close_price=100.0, symbol="TESTUSDT_INDEX", unit="USDT"),
        KlineBar(open_time_ms=open_1626 + 15_000, close_time_ms=end_1627, close_price=100.0, symbol="TESTUSDT_INDEX", unit="USDT"),
    ]
    res_diff = calculate_basis(
        mark_bars=mark_diff_min,
        index_bars=index_diff_min,
        target_symbol="TESTUSDT",
        mapped_index_symbol="TESTUSDT_INDEX",
        d_ms=d_1628,
        cutoff_margin_ms=60_000,
    )
    assert res_diff.status == "no_eligible_bar_pair"
    assert res_diff.basis is None


def test_scenario_abc_aggregation_overlap_and_multi_child_parent_exclusion(tmp_path: Path):
    """Task 2 (Plan L65-69):
    1. Independent per-regime (pre_market, standard) and per-scenario (A, B, C) Child/Parent aggregation.
    2. Multi-Child Parent negative vector: same Parent has Child A complete and Child B endpoint_unavailable ->
       Parent is excluded from complete Parent grouping and Jackknife LOO, while preserving Parent denominator and gap reason.
    3. Cross-scenario overlap (A∩B, B∩C, A∩B∩C) and difference (A\\B, B\\C) counts.
    4. Ties / empty high group returns diff_mean = None.
    5. Report outputs historical_scenario_only, unverified_scenario_assumption, and Scenarios A/B/C.
    """
    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        write_exploratory_outputs,
    )

    children = [
        # Parent p1 (standard): single child, complete in A, B, and C
        ChildEvaluation(
            parent_article_id="p1",
            symbol="S1USDT",
            listing_regime="standard",
            is_complete=True,
            path_status="ok",
            oi_status="ok",
            oi_change=0.20,
            oi_a_status="ok",
            oi_a_change=0.25,
            oi_b_status="ok",
            oi_b_change=0.20,
            oi_c_status="ok",
            oi_c_change=0.10,
            terminal_return=0.05,
            long_mae=-0.02,
            long_mfe=0.08,
            utc_date="2026-10-01",
        ),
        # Parent p2 (standard): single child, complete in A and B, but missing in C (l0_before_t0)
        ChildEvaluation(
            parent_article_id="p2",
            symbol="S2USDT",
            listing_regime="standard",
            is_complete=True,
            path_status="ok",
            oi_status="ok",
            oi_change=0.60,
            oi_a_status="ok",
            oi_a_change=0.70,
            oi_b_status="ok",
            oi_b_change=0.60,
            oi_c_status="l0_before_t0",
            oi_c_change=None,
            terminal_return=0.15,
            long_mae=-0.01,
            long_mfe=0.20,
            utc_date="2026-10-02",
        ),
        # Parent p_multi (standard): Child A complete, Child B endpoint_unavailable
        ChildEvaluation(
            parent_article_id="p_multi",
            symbol="M1USDT",
            listing_regime="standard",
            is_complete=True,
            path_status="ok",
            oi_status="ok",
            oi_change=0.40,
            oi_a_status="ok",
            oi_a_change=0.45,
            oi_b_status="ok",
            oi_b_change=0.40,
            oi_c_status="ok",
            oi_c_change=0.30,
            terminal_return=0.10,
            long_mae=-0.03,
            long_mfe=0.12,
            utc_date="2026-10-03",
        ),
        ChildEvaluation(
            parent_article_id="p_multi",
            symbol="M2USDT",
            listing_regime="standard",
            is_complete=False,
            missing_reason="endpoint_unavailable",
            path_status="endpoint_unavailable",
            oi_status="ok",
            oi_change=0.50,
            oi_a_status="ok",
            oi_a_change=0.55,
            oi_b_status="ok",
            oi_b_change=0.50,
            oi_c_status="ok",
            oi_c_change=0.35,
            terminal_return=None,
            utc_date="2026-10-03",
        ),
        # Parent p_tie (pre_market): two parents with identical OI change (ties stay in low -> high is empty -> diff is None)
        ChildEvaluation(
            parent_article_id="pm1",
            symbol="PM1USDT",
            listing_regime="pre_market",
            is_complete=True,
            path_status="ok",
            oi_status="ok",
            oi_change=0.10,
            oi_a_status="ok",
            oi_a_change=0.10,
            oi_b_status="ok",
            oi_b_change=0.10,
            oi_c_status="ok",
            oi_c_change=0.10,
            terminal_return=0.02,
            long_mae=-0.01,
            long_mfe=0.04,
            utc_date="2026-10-04",
        ),
        ChildEvaluation(
            parent_article_id="pm2",
            symbol="PM2USDT",
            listing_regime="pre_market",
            is_complete=True,
            path_status="ok",
            oi_status="ok",
            oi_change=0.10,
            oi_a_status="ok",
            oi_a_change=0.10,
            oi_b_status="ok",
            oi_b_change=0.10,
            oi_c_status="ok",
            oi_c_change=0.10,
            terminal_return=0.08,
            long_mae=-0.02,
            long_mfe=0.10,
            utc_date="2026-10-05",
        ),
    ]

    res = aggregate_and_group(children)
    assert res.interpretation_status == "historical_scenario_only"
    assert res.pit_verification_status == "unverified_scenario_assumption"

    # Check standard regime main (Scenario B) summary:
    st_sum = res.regime_summaries["standard"]
    # 4 children in standard universe: S1, S2, M1 are complete (3), M2 is incomplete (1)
    assert st_sum.child_universe_count == 4
    assert st_sum.child_complete_count == 3
    assert st_sum.child_missing_count == 1
    assert st_sum.child_missing_reasons == {"endpoint_unavailable": 1}

    # 3 parents in standard universe (p1, p2, p_multi):
    # p_multi has M2 incomplete (endpoint_unavailable), so p_multi MUST be excluded from complete_parents and Jackknife!
    assert st_sum.parent_universe_count == 3
    assert st_sum.parent_complete_count == 2
    assert st_sum.parent_missing_count == 1
    assert st_sum.parent_missing_reasons == {"endpoint_unavailable": 1}
    assert [p.parent_article_id for p in st_sum.complete_parents] == ["p1", "p2"]
    assert st_sum.parent_jackknife is not None
    assert [it.omitted_parent_id for it in st_sum.parent_jackknife.jackknife_items] == ["p1", "p2"]

    # Check Scenario A / B / C summaries for standard:
    st_scen = res.scenario_summaries["standard"]
    assert set(st_scen.keys()) == {"A", "B", "C"}
    assert st_scen["A"].child_complete_count == 3
    assert st_scen["A"].parent_complete_count == 2
    assert st_scen["B"].child_complete_count == 3
    assert st_scen["B"].parent_complete_count == 2
    # In Scenario C, p2 has l0_before_t0, so only S1 and M1 are complete children (2), and only p1 is a complete parent (1)!
    assert st_scen["C"].child_complete_count == 2
    assert st_scen["C"].parent_complete_count == 1
    assert st_scen["C"].parent_terminal_diff_mean is None  # Single parent -> high group empty -> diff is None

    # Check Scenario Overlap for standard:
    st_ov = res.scenario_overlaps["standard"]
    assert st_ov.child_complete_counts == {"A": 3, "B": 3, "C": 2}
    assert st_ov.child_overlap_ab == 3
    assert st_ov.child_overlap_bc == 2
    assert st_ov.child_overlap_abc == 2
    assert st_ov.child_diff_a_minus_b == 0
    assert st_ov.child_diff_b_minus_c == 1
    assert st_ov.parent_complete_counts == {"A": 2, "B": 2, "C": 1}
    assert st_ov.parent_overlap_ab == 2
    assert st_ov.parent_overlap_bc == 1
    assert st_ov.parent_overlap_abc == 1
    assert st_ov.parent_diff_b_minus_c == 1

    # Check ties in pre_market: both pm1 and pm2 have oi_change == 0.10 -> both in low, high is 0 -> diff is None
    pm_sum = res.regime_summaries["pre_market"]
    assert pm_sum.parent_high_group is not None and pm_sum.parent_high_group.count == 0
    assert pm_sum.parent_low_group is not None and pm_sum.parent_low_group.count == 2
    assert pm_sum.parent_terminal_diff_mean is None

    # Check report generation includes historical_scenario_only and unverified_scenario_assumption
    out_dir = tmp_path / "report_abc_out"
    csv_path, md_path = write_exploratory_outputs(out_dir, children, res, project_root=tmp_path)
    md_text = md_path.read_text(encoding="utf-8")
    assert "historical_scenario_only" in md_text
    assert "unverified_scenario_assumption" in md_text
    assert "evidence_insufficient" in md_text
    assert "Scenario A" in md_text and "Scenario B" in md_text and "Scenario C" in md_text
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "oi_a_status" in csv_text and "oi_b_status" in csv_text and "oi_c_status" in csv_text
    assert "unverified_scenario_assumption" in csv_text


def test_independent_vector_oi_and_grid():
    """Plan line 56 vector: T0=1000ms, D=901000ms, labels 300k/600k, OI 100/150 -> oi_change=0.5.

    Label 0 is excluded from main (since 0 < T0=1000), but available for grid control.
    """
    t0 = 1000
    d = t0 + 900_000  # 901_000 ms
    records = [
        OiMetricRecord(
            create_time_ms=0,
            symbol="TESTUSDT",
            sum_open_interest=80.0,
            information_time_ms=0,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=300_000,
            symbol="TESTUSDT",
            sum_open_interest=100.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="TESTUSDT",
            sum_open_interest=150.0,
            information_time_ms=600_000,
            unit="TEST",
        ),
    ]

    # Main scenario with 5m margin: cutoff = D - 300,000 = 601,000
    res_main = calculate_oi_change(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t0,
        d_ms=d,
        margin_ms=300_000,
    )
    assert res_main.status == "ok"
    assert res_main.l0_ms == 300_000
    assert res_main.l1_ms == 600_000
    assert res_main.oi_l0 == 100.0
    assert res_main.oi_l1 == 150.0
    # Expected: (150 - 100) / 100 = 0.5
    assert abs(res_main.oi_change - 0.5) < 1e-9

    # Opening grid control: floor_5m(T0) = 0, L0=0, L1=300_000
    # OI at 0 is 80.0, at 300k is 100.0 -> (100 - 80) / 80 = 0.25
    assert res_main.grid_status == "ok"
    assert res_main.grid_l0_ms == 0
    assert res_main.grid_l1_ms == 300_000
    assert res_main.grid_oi_l0 == 80.0
    assert res_main.grid_oi_l1 == 100.0
    assert abs(res_main.grid_oi_change - 0.25) < 1e-9


def test_time_oi_latest_missing_predecessor_no_fallback():
    """Plan line 52 requirement:

    If latest L1 does not have a valid predecessor L0=L1-5m satisfying lower bound,
    must NOT fallback to an earlier pair.
    """
    t0 = 1000
    d = t0 + 900_000  # 901_000 ms
    # Suppose we have valid pair at 300k and 600k, but there is an L1 at 900k without 600k (e.g. missing 600k).
    # Cutoff = 901000 - 60000 (1m margin) = 841000 ms.
    # If we have 300k, 600k, and 900k:
    # At cutoff = 601000 ms (5m margin), max label is 600k, L0 is 300k.
    # Now let margin = 60_000 (1m margin). Cutoff = 841_000 ms.
    # If records are 300k, 600k (valid pair), but we also have 800k (invalid cadence) or 700k without 400k.
    # Suppose records are: 300k, 600k (a pair 5m apart), and 800k (or 900k if cutoff allows).
    # Let's say cutoff = 700k, and we have records at 300k, 500k, 700k.
    # Latest label <= cutoff is 700k. But 700k - 300k = 400k (not 500k). Predecessor 400k is MISSING!
    # Even though earlier 300k might exist, it must NOT fallback to any arbitrary pair.
    records = [
        OiMetricRecord(
            create_time_ms=300_000,
            symbol="TESTUSDT",
            sum_open_interest=100.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="TESTUSDT",
            sum_open_interest=150.0,
            information_time_ms=600_000,
            unit="TEST",
        ),
        # A newer record at 700_000 ms (predecessor 400_000 is missing):
        OiMetricRecord(
            create_time_ms=700_000,
            symbol="TESTUSDT",
            sum_open_interest=180.0,
            information_time_ms=700_000,
            unit="TEST",
        ),
    ]
    # With margin = 180_000 (3m margin), cutoff = 901_000 - 180_000 = 721_000 ms.
    # The latest label <= 721_000 is 700_000 ms.
    # Predecessor L0 = 700_000 - 300_000 = 400_000 ms.
    # 400_000 ms is missing in records!
    # Expected: status must be missing (e.g. 'predecessor_missing'), NOT fallback to (300k, 600k)!
    res = calculate_oi_change(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t0,
        d_ms=d,
        margin_ms=180_000,
    )
    assert res.status == "missing_predecessor"
    assert res.l1_ms == 700_000
    assert res.oi_change is None


def test_oi_information_time_upper_bound_violation():
    """Plan line 50: If a verified time fact conflicts with the scenario assumption or > D, stops scenario."""
    t0 = 1000
    d = 901_000
    records = [
        OiMetricRecord(
            create_time_ms=300_000,
            symbol="TESTUSDT",
            sum_open_interest=100.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="TESTUSDT",
            sum_open_interest=150.0,
            information_time_ms=1_000_000,  # verified information cutoff > D (901_000)
            unit="TEST",
        ),
    ]
    res = calculate_oi_change(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t0,
        d_ms=d,
        margin_ms=300_000,
    )
    assert res.status == "verified_fact_conflict"
    assert res.oi_change is None


def test_basis_bar_end_cutoff_selects_older_pair():
    """Plan line 52 requirement:

    Basis requires same natural minute bar, bar_end <= D - 1m, and selects the latest
    eligible pair. If a newer pair has bar_end > D - 1m, it must select the older eligible pair.
    """
    d = 901_000  # D = 901_000 ms
    d - 60_000  # 841_000 ms

    # Older pair: 780_000 - 839_999 (bar_end = 839_999 <= 841_000)
    # Newer pair: 840_000 - 899_999 (bar_end = 899_999 > 841_000, exceeds cutoff!)
    mark_bars = [
        KlineBar(
            open_time_ms=780_000,
            close_time_ms=839_999,
            close_price=105.0,
            symbol="TESTUSDT",
            unit="USDT",
        ),
        KlineBar(
            open_time_ms=840_000,
            close_time_ms=899_999,
            close_price=110.0,
            symbol="TESTUSDT",
            unit="USDT",
        ),
    ]
    index_bars = [
        KlineBar(
            open_time_ms=780_000,
            close_time_ms=839_999,
            close_price=100.0,
            symbol="TESTUSDT_INDEX",
            unit="USDT",
        ),
        KlineBar(
            open_time_ms=840_000,
            close_time_ms=899_999,
            close_price=100.0,
            symbol="TESTUSDT_INDEX",
            unit="USDT",
        ),
    ]

    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TESTUSDT",
        mapped_index_symbol="TESTUSDT_INDEX",
        d_ms=d,
        cutoff_margin_ms=60_000,
    )
    assert res.status == "ok"
    assert res.bar_open_time_ms == 780_000
    assert res.bar_close_time_ms == 839_999
    assert res.mark_price == 105.0
    assert res.index_price == 100.0
    # Basis = 105 / 100 - 1 = 0.05
    assert abs(res.basis - 0.05) < 1e-9


def test_basis_mismatched_index_or_missing_index():
    """Plan line 50: Missing or mismatched index leaves basis missing without dropping sample."""
    res = calculate_basis(
        mark_bars=[
            KlineBar(
                open_time_ms=780_000,
                close_time_ms=839_999,
                close_price=105.0,
                symbol="MONUSDT",
                unit="USDT",
            )
        ],
        index_bars=[],  # e.g. Pre-Market 404
        target_symbol="MONUSDT",
        mapped_index_symbol=None,
        d_ms=901_000,
        cutoff_margin_ms=60_000,
    )
    assert res.status == "index_unavailable"
    assert res.basis is None


def test_independent_vector_path_response():
    """Plan line 56 vector: entry 100, PE 110, path min 90, max 120 -> terminal=0.1, mae=-0.1, mfe=0.2.

    Entry in [D, D+5s], Endpoint in [E-1s, E], E = entry_time + 15m.
    """
    d = 901_000  # ms
    entry_time = d + 2000  # within [D, D+5000]
    e = entry_time + 900_000  # 1_803_000 ms

    trades = [
        # trade before D
        AggTradeRecord(
            transact_time_ms=d - 100, trade_id=1, price=99.0, quantity=1.0, is_buyer_maker=False
        ),
        # entry trade at D + 2000ms
        AggTradeRecord(
            transact_time_ms=entry_time, trade_id=2, price=100.0, quantity=1.0, is_buyer_maker=False
        ),
        # path trades
        AggTradeRecord(
            transact_time_ms=entry_time + 10_000,
            trade_id=3,
            price=90.0,
            quantity=1.0,
            is_buyer_maker=True,
        ),
        AggTradeRecord(
            transact_time_ms=entry_time + 50_000,
            trade_id=4,
            price=120.0,
            quantity=1.0,
            is_buyer_maker=False,
        ),
        AggTradeRecord(
            transact_time_ms=entry_time + 100_000,
            trade_id=5,
            price=105.0,
            quantity=1.0,
            is_buyer_maker=True,
        ),
        # endpoint trade in [E - 1000, E]
        AggTradeRecord(
            transact_time_ms=e - 200, trade_id=6, price=110.0, quantity=1.0, is_buyer_maker=False
        ),
        # trade after E
        AggTradeRecord(
            transact_time_ms=e + 50, trade_id=7, price=112.0, quantity=1.0, is_buyer_maker=False
        ),
    ]

    res = calculate_path_response(trades=trades, d_ms=d, entry_window_ms=5000, horizon_ms=900_000)
    assert res.status == "ok"
    assert res.entry_price == 100.0
    assert res.entry_trade_id == 2
    assert res.entry_delay_ms == 2000
    assert res.endpoint_price == 110.0
    assert res.endpoint_trade_id == 6
    # terminal_return = (110 - 100) / 100 = 0.1
    assert abs(res.terminal_return - 0.1) < 1e-9
    # long_mae = min(90 - 100) / 100 = -0.1
    assert abs(res.long_mae - (-0.1)) < 1e-9
    # long_mfe = max(120 - 100) / 100 = 0.2
    assert abs(res.long_mfe - 0.2) < 1e-9


def test_path_response_entry_window_boundary():
    """Test boundary checks for D, D+5s, D+5s+1ms, and same-millisecond trade_id tie-break."""
    d = 901_000
    # Case 1: two trades at exact same millisecond D with unsorted trade_id -> selects smaller trade_id
    t_exact_d = [
        AggTradeRecord(
            transact_time_ms=d, trade_id=20, price=105.0, quantity=1.0, is_buyer_maker=False
        ),
        AggTradeRecord(
            transact_time_ms=d, trade_id=10, price=100.0, quantity=1.0, is_buyer_maker=False
        ),
    ]
    # Case 2: trade exactly at D + 5000 -> accepted
    t_exact_edge = [
        AggTradeRecord(
            transact_time_ms=d + 5000, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False
        )
    ]
    # Case 3: trade at D + 5001 -> rejected (no entry trade)
    t_outside = [
        AggTradeRecord(
            transact_time_ms=d + 5001, trade_id=1, price=100.0, quantity=1.0, is_buyer_maker=False
        )
    ]

    r1 = calculate_path_response(trades=t_exact_d, d_ms=d, entry_window_ms=5000, horizon_ms=900_000)
    # will be missing endpoint, but entry was found and tie-broken by smaller trade_id=10
    assert r1.entry_price == 100.0
    assert r1.entry_trade_id == 10

    r2 = calculate_path_response(
        trades=t_exact_edge, d_ms=d, entry_window_ms=5000, horizon_ms=900_000
    )
    assert r2.entry_price == 100.0

    r3 = calculate_path_response(trades=t_outside, d_ms=d, entry_window_ms=5000, horizon_ms=900_000)
    assert r3.status == "missing_entry_trade"
    assert r3.entry_price is None


def test_baseline_metrics_calculation():
    """Verify [T0, D) baseline metrics calculation."""
    t0 = 1000
    d = 901_000
    trades = [
        AggTradeRecord(
            transact_time_ms=1000, trade_id=1, price=10.0, quantity=2.0, is_buyer_maker=False
        ),  # taker buy: 20 notional
        AggTradeRecord(
            transact_time_ms=500_000, trade_id=2, price=15.0, quantity=2.0, is_buyer_maker=True
        ),  # taker sell: 30 notional
        AggTradeRecord(
            transact_time_ms=900_999, trade_id=3, price=20.0, quantity=2.0, is_buyer_maker=False
        ),  # taker buy: 40 notional
        AggTradeRecord(
            transact_time_ms=901_000, trade_id=4, price=25.0, quantity=2.0, is_buyer_maker=False
        ),  # AT D, must NOT be included!
    ]
    b = calculate_baseline(trades=trades, t0_ms=t0, d_ms=d)
    assert b.status == "ok"
    assert b.trade_count == 3
    # First price 10.0, last price 20.0 -> price change (20 - 10) / 10 = 1.0
    assert abs(b.price_change - 1.0) < 1e-9
    # Total notional = 20 + 30 + 40 = 90.0
    assert abs(b.total_notional - 90.0) < 1e-9
    # Taker buy notional = 20 + 40 = 60.0 -> taker buy share = 60 / 90 = 2/3 ≈ 0.66666666667
    assert abs(b.taker_buy_share - (2.0 / 3.0)) < 1e-9


def test_independent_vector_parent_jackknife():
    """Plan line 70 vector:

    三个 Parent OI 为 1/4, 1/2, 3/4，terminal 为 0.1, 0.2, 0.4，原差 0.25；删除第三个后差 0.1.
    """
    parents = [
        ParentEvaluation(
            parent_article_id="p1",
            listing_regime="standard",
            is_complete=True,
            child_count=1,
            oi_change=0.25,
            terminal_return=0.1,
            long_mae=-0.05,
            long_mfe=0.15,
        ),
        ParentEvaluation(
            parent_article_id="p2",
            listing_regime="standard",
            is_complete=True,
            child_count=1,
            oi_change=0.50,
            terminal_return=0.2,
            long_mae=-0.08,
            long_mfe=0.25,
        ),
        ParentEvaluation(
            parent_article_id="p3",
            listing_regime="standard",
            is_complete=True,
            child_count=1,
            oi_change=0.75,
            terminal_return=0.4,
            long_mae=-0.02,
            long_mfe=0.45,
        ),
    ]

    # Baseline grouping on all 3 parents:
    # Median OI is 0.50.
    # High (> 0.50): p3 (return = 0.4, mean = 0.4)
    # Low (<= 0.50): p1, p2 (returns = 0.1, 0.2, mean = (0.1 + 0.2)/2 = 0.15)
    # Diff = 0.4 - 0.15 = 0.25
    jk_res = perform_parent_jackknife(parents)
    assert jk_res.base_median_oi == 0.50
    assert jk_res.base_high_count == 1
    assert jk_res.base_low_count == 2
    assert abs(jk_res.base_diff - 0.25) < 1e-9

    # Jackknife step omitting p3:
    # Remaining: p1 (oi=0.25, ret=0.1), p2 (oi=0.50, ret=0.2)
    # New median OI = (0.25 + 0.50) / 2 = 0.375
    # High (> 0.375): p2 (ret = 0.2, mean = 0.2)
    # Low (<= 0.375): p1 (ret = 0.1, mean = 0.1)
    # Diff = 0.2 - 0.1 = 0.1
    p3_omission = [item for item in jk_res.jackknife_items if item.omitted_parent_id == "p3"][0]
    assert p3_omission.remaining_count == 2
    assert p3_omission.high_count == 1
    assert p3_omission.low_count == 1
    assert abs(p3_omission.diff_mean_terminal_return - 0.1) < 1e-9


def test_parent_aggregation_multi_child_incomplete_exclusion():
    """Plan line 68: Parent is complete ONLY IF ALL selected children under that (parent_article_id, regime) are complete."""
    children = [
        # Parent 1: 2 children, both complete
        ChildEvaluation(
            parent_article_id="p1",
            symbol="C1",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.10,
            terminal_return=0.05,
            long_mae=-0.02,
            long_mfe=0.08,
            utc_date="2026-10-01",
        ),
        ChildEvaluation(
            parent_article_id="p1",
            symbol="C2",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.30,
            terminal_return=0.15,
            long_mae=-0.04,
            long_mfe=0.20,
            utc_date="2026-10-01",
        ),
        # Parent 2: 2 children, 1 complete, 1 missing
        ChildEvaluation(
            parent_article_id="p2",
            symbol="C3",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.20,
            terminal_return=0.10,
            long_mae=-0.03,
            long_mfe=0.12,
            utc_date="2026-10-02",
        ),
        ChildEvaluation(
            parent_article_id="p2",
            symbol="C4",
            listing_regime="standard",
            is_complete=False,
            missing_reason="missing_entry_trade",
            utc_date="2026-10-02",
        ),
    ]

    res = aggregate_and_group(children=children)
    # Child universe = 4, complete = 3, incomplete = 1
    assert res.child_universe_count == 4
    assert res.child_complete_count == 3
    assert res.child_missing_count == 1

    # Parent universe = 2, complete = 1 (p1), incomplete = 1 (p2)
    assert res.parent_universe_count == 2
    assert res.parent_complete_count == 1
    assert res.parent_missing_count == 1

    # p1 child values: oi_change=[0.10, 0.30] -> median=0.20
    # terminal_return=[0.05, 0.15] -> median=0.10
    p1 = [p for p in res.complete_parents if p.parent_article_id == "p1"][0]
    assert abs(p1.oi_change - 0.20) < 1e-9
    assert abs(p1.terminal_return - 0.10) < 1e-9


def test_cross_regime_parent_deduplication():
    """Plan line 68: Same parent_article_id across different regimes still counts as ONE distinct announcement."""
    children = [
        ChildEvaluation(
            parent_article_id="shared_p",
            symbol="SYM1",
            listing_regime="pre_market",
            is_complete=True,
            oi_change=0.1,
            terminal_return=0.02,
            long_mae=-0.01,
            long_mfe=0.03,
            utc_date="2026-10-10",
        ),
        ChildEvaluation(
            parent_article_id="shared_p",
            symbol="SYM2",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.2,
            terminal_return=0.05,
            long_mae=-0.02,
            long_mfe=0.06,
            utc_date="2026-10-10",
        ),
    ]
    res = aggregate_and_group(children=children)
    assert res.distinct_parent_article_count == 1


def test_oi_selection_not_affected_by_irrelevant_future_records():
    """P1-02 remediation: Irrelevant future records (> cutoff) with unknown info time do not invalidate earlier window."""
    t0 = 1000
    d = t0 + 900_000  # 901_000 ms
    records = [
        OiMetricRecord(
            create_time_ms=300_000,
            symbol="TESTUSDT",
            sum_open_interest=100.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="TESTUSDT",
            sum_open_interest=150.0,
            information_time_ms=600_000,
            unit="TEST",
        ),
        # Irrelevant future record at 20:00 UTC with unknown information time:
        OiMetricRecord(
            create_time_ms=72_000_000,
            symbol="TESTUSDT",
            sum_open_interest=500.0,
            information_time_ms=None,
            information_time_upper_bound_ms=None,
            unit="TEST",
        ),
    ]

    res = calculate_oi_change(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t0,
        d_ms=d,
        margin_ms=300_000,
    )
    assert res.status == "ok"
    assert res.oi_l0 == 100.0
    assert res.oi_l1 == 150.0
    assert abs(res.oi_change - 0.5) < 1e-9


def test_oi_duplicate_timestamp_rejected():
    """P1-02 remediation: Duplicate create_time_ms for the same symbol must be rejected, not silently overwritten."""
    t0 = 1000
    d = t0 + 900_000
    records = [
        OiMetricRecord(
            create_time_ms=300_000,
            symbol="TESTUSDT",
            sum_open_interest=100.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=300_000,  # Duplicate timestamp!
            symbol="TESTUSDT",
            sum_open_interest=110.0,
            information_time_ms=300_000,
            unit="TEST",
        ),
        OiMetricRecord(
            create_time_ms=600_000,
            symbol="TESTUSDT",
            sum_open_interest=150.0,
            information_time_ms=600_000,
            unit="TEST",
        ),
    ]

    res = calculate_oi_change(
        records=records,
        symbol="TESTUSDT",
        t0_ms=t0,
        d_ms=d,
        margin_ms=300_000,
    )
    assert res.status == "duplicate_timestamp"
    assert res.oi_change is None


def test_basis_unverified_product_mapping_rejected():
    """P1-03 remediation: Product identity mismatch in KlineBar is flagged as unverified_product_mapping."""
    d = 1000 + 900_000
    mark_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=10.0,
            symbol="TARGET_USDT",
            unit="USDT",
        )
    ]
    index_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=9.5,
            symbol="WRONG_INDEX",  # Mismatch against expected mapped index symbol
            unit="USDT",
        )
    ]

    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TARGET_USDT",
        mapped_index_symbol="CORRECT_INDEX",
        d_ms=d,
    )
    assert res.status == "unverified_product_mapping"
    assert res.basis is None


def test_basis_unit_mismatch_rejected():
    """P1-03 remediation: Unit mismatch between mark and index bars is flagged as unit_mismatch."""
    d = 1000 + 900_000
    mark_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=10.0,
            symbol="TARGET_USDT",
            unit="USDT",
        )
    ]
    index_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=9.5,
            symbol="MAPPED_INDEX",
            unit="USD",  # Mismatch: USDT vs USD
        )
    ]

    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TARGET_USDT",
        mapped_index_symbol="MAPPED_INDEX",
        d_ms=d,
    )
    assert res.status == "unit_mismatch"
    assert res.basis is None


def test_basis_failure_preserves_sample_conservation():
    """P1-03 remediation: Basis failure does not drop complete OI sample from universe."""
    child = ChildEvaluation(
        parent_article_id="p1",
        symbol="S1",
        listing_regime="standard",
        is_complete=True,
        oi_change=0.5,
        terminal_return=0.1,
        long_mae=-0.02,
        long_mfe=0.15,
        basis=None,  # Missing basis
    )
    res = aggregate_and_group(children=[child])
    assert res.child_universe_count == 1
    assert res.child_complete_count == 1
    assert res.parent_complete_count == 1


def test_basis_missing_symbol_on_bars_rejected():
    """P1-03 remediation: Bars with symbol=None are rejected as unverified_product_mapping."""
    d = 1000 + 900_000
    mark_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=10.0,
            symbol=None,  # Missing symbol!
            unit="USDT",
        )
    ]
    index_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=9.5,
            symbol="INDEX_USDT",
            unit="USDT",
        )
    ]
    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TARGET_USDT",
        mapped_index_symbol="INDEX_USDT",
        d_ms=d,
    )
    assert res.status == "unverified_product_mapping"
    assert res.basis is None


def test_basis_unverified_index_mapping_string_rejected():
    """P1-03 remediation: Mapped index symbol set to 'UNVERIFIED' or empty is rejected."""
    d = 1000 + 900_000
    mark_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=10.0,
            symbol="TARGET_USDT",
            unit="USDT",
        )
    ]
    index_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=9.5,
            symbol="UNVERIFIED",
            unit="USDT",
        )
    ]
    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TARGET_USDT",
        mapped_index_symbol="UNVERIFIED",
        d_ms=d,
    )
    assert res.status == "unverified_product_mapping"
    assert res.basis is None


def test_basis_missing_unit_rejected():
    """P1-03 remediation: Bars with unit=None are rejected as unverified_product_mapping."""
    d = 1000 + 900_000
    mark_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=10.0,
            symbol="TARGET_USDT",
            unit=None,  # Missing unit!
        )
    ]
    index_bars = [
        KlineBar(
            open_time_ms=600_000,
            close_time_ms=660_000,
            close_price=9.5,
            symbol="INDEX_USDT",
            unit="USDT",
        )
    ]
    res = calculate_basis(
        mark_bars=mark_bars,
        index_bars=index_bars,
        target_symbol="TARGET_USDT",
        mapped_index_symbol="INDEX_USDT",
        d_ms=d,
    )
    assert res.status == "unverified_product_mapping"
    assert res.basis is None


def test_load_child_aggtrades_missing_date_rejected(tmp_path: Path):
    """P1-01 remediation: If required date is missing from J-A package inventory, returns missing_aggtrades_archive."""
    ja_summary = {
        "archive_package_records": [
            {
                "parent_article_id": "p1",
                "symbol": "S1",
                "utc_date": "2026-10-01",
                "child_state": "archive_verified_with_post_launch_rows",
            }
        ]
    }
    # t0_ms on 2026-10-01 at 23:55:00 UTC crosses into 2026-10-02
    t0_ms = 1790898900000  # 2026-10-01 23:55:00 UTC
    st, trades = load_child_aggtrades_from_ja_root(
        ja_root=tmp_path,
        ja_summary=ja_summary,
        parent_article_id="p1",
        symbol="S1",
        t0_ms=t0_ms,
    )
    assert st.startswith("missing_aggtrades_archive:missing_date_2026-10-02")
    assert trades == []


def test_load_child_aggtrades_unverified_package_rejected(tmp_path: Path):
    """P1-01 remediation: If J-A package is not archive_verified_with_post_launch_rows, returns unverified reason."""
    ja_summary = {
        "archive_package_records": [
            {
                "parent_article_id": "p1",
                "symbol": "S1",
                "utc_date": "2026-10-01",
                "child_state": "archive_request_nonpersisted",  # Not verified!
            }
        ]
    }
    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    st, trades = load_child_aggtrades_from_ja_root(
        ja_root=tmp_path,
        ja_summary=ja_summary,
        parent_article_id="p1",
        symbol="S1",
        t0_ms=t0_ms,
    )
    assert st.startswith("missing_aggtrades_archive:unverified_j_a_package_2026-10-01")
    assert trades == []


def _build_synthetic_ja_package(
    ja_root: Path,
    parent_id: str,
    symbol: str,
    utc_date: str,
    csv_rows: list[str],
    raw_zip_bytes_override: bytes | None = None,
) -> dict:
    """Helper to write a complete synthetic J-A package (.zip, .CHECKSUM, manifest.json) and return ja_summary."""
    import hashlib
    import json
    import zipfile

    zip_name = f"{symbol}-aggTrades-{utc_date}.zip"
    chk_name = f"{zip_name}.CHECKSUM"
    zip_rel = f"raw/archive/{symbol}/{zip_name}"
    chk_rel = f"raw/archive/{symbol}/{chk_name}"

    zip_path = ja_root / zip_rel
    chk_path = ja_root / chk_rel
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    if raw_zip_bytes_override is not None:
        zip_path.write_bytes(raw_zip_bytes_override)
    else:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{symbol}-aggTrades-{utc_date}.csv", "\n".join(csv_rows).encode("utf-8"))

    zip_bytes = zip_path.read_bytes()
    zip_sha = hashlib.sha256(zip_bytes).hexdigest()
    chk_content = f"{zip_sha}  {zip_name}\n".encode("utf-8")
    chk_path.write_bytes(chk_content)
    chk_sha = hashlib.sha256(chk_content).hexdigest()

    identity = {
        "market": "futures_um",
        "metric": "aggTrades",
        "parent_article_id": parent_id,
        "symbol": symbol,
        "utc_date": utc_date,
    }
    zip_req_id = 1
    chk_req_id = 2

    manifest_obj = {
        "artifacts": [
            {"relative_path": zip_rel, "sha256": zip_sha, "byte_count": len(zip_bytes)},
            {"relative_path": chk_rel, "sha256": chk_sha, "byte_count": len(chk_content)},
        ]
    }
    (ja_root / "manifest.json").write_text(json.dumps(manifest_obj), encoding="utf-8")

    return {
        "request_records": [
            {
                "request_id": zip_req_id,
                "request_kind": "archive",
                "request_state": "response_persisted",
                "response_relative_path": zip_rel,
                "response_sha256": zip_sha,
                "response_bytes": len(zip_bytes),
                "logical_archive_identity": identity,
            },
            {
                "request_id": chk_req_id,
                "request_kind": "checksum",
                "request_state": "response_persisted",
                "response_relative_path": chk_rel,
                "response_sha256": chk_sha,
                "response_bytes": len(chk_content),
                "logical_archive_identity": identity,
            },
        ],
        "archive_package_records": [
            {
                "parent_article_id": parent_id,
                "symbol": symbol,
                "utc_date": utc_date,
                "child_state": "archive_verified_with_post_launch_rows",
                "logical_archive_identity": identity,
                "zip_relative_path": zip_rel,
                "checksum_relative_path": chk_rel,
                "zip_request_id": zip_req_id,
                "checksum_request_id": chk_req_id,
                "zip_sha256": zip_sha,
                "zip_size_bytes": len(zip_bytes),
            }
        ],
    }


def test_load_child_aggtrades_corrupted_archive_halts(tmp_path: Path):
    """P1-01 remediation: Corrupted zip or corrupted CSV rows halt with LaunchOiResearchError."""
    import pytest

    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    ja_summary = _build_synthetic_ja_package(
        ja_root=tmp_path,
        parent_id="p1",
        symbol="S1",
        utc_date="2026-10-01",
        csv_rows=[],
        raw_zip_bytes_override=b"NOT_A_VALID_ZIP_BYTES_CORRUPTED",
    )

    with pytest.raises(LaunchOiResearchError, match="corrupted_archive_data"):
        load_child_aggtrades_from_ja_root(
            ja_root=tmp_path,
            ja_summary=ja_summary,
            parent_article_id="p1",
            symbol="S1",
            t0_ms=t0_ms,
        )


def test_load_child_aggtrades_claimed_file_missing_halts(tmp_path: Path):
    """P1-01 remediation: If a package is claimed archive_verified_with_post_launch_rows but missing on disk, halts fail-closed."""
    import pytest

    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    csv_rows = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"1,10.0,1.0,1,1,{t0_ms + 1000},false",
    ]
    ja_summary = _build_synthetic_ja_package(
        ja_root=tmp_path,
        parent_id="p1",
        symbol="S1",
        utc_date="2026-10-01",
        csv_rows=csv_rows,
    )
    # Remove the claimed verified zip file from disk
    (tmp_path / "raw/archive/S1/S1-aggTrades-2026-10-01.zip").unlink()

    with pytest.raises(
        LaunchOiResearchError, match="corrupted_archive_data:.*zip_package_missing"
    ):
        load_child_aggtrades_from_ja_root(
            ja_root=tmp_path,
            ja_summary=ja_summary,
            parent_article_id="p1",
            symbol="S1",
            t0_ms=t0_ms,
        )


def test_load_child_aggtrades_streams_to_eof_and_validates_late_rows(tmp_path: Path):
    """P1-01 remediation: Reader streams past end_ms to EOF and rejects malformed/non-boolean/out-of-order late rows."""
    import pytest

    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    d_entry_max = t0_ms + 905_000
    endpoint_max = d_entry_max + 900_000

    # Row 4 is AFTER endpoint_max and has an invalid boolean 'maybe'
    csv_rows = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"1,10.0,1.0,1,1,{t0_ms + 1000},false",
        f"2,10.5,1.0,2,2,{d_entry_max},true",
        f"3,11.0,1.0,3,3,{endpoint_max},false",
        f"4,12.0,1.0,4,4,{endpoint_max + 50_000},maybe",
    ]
    ja_summary = _build_synthetic_ja_package(
        ja_root=tmp_path,
        parent_id="p1",
        symbol="S1",
        utc_date="2026-10-01",
        csv_rows=csv_rows,
    )

    with pytest.raises(LaunchOiResearchError, match="corrupted_archive_data:invalid_boolean"):
        load_child_aggtrades_from_ja_root(
            ja_root=tmp_path,
            ja_summary=ja_summary,
            parent_article_id="p1",
            symbol="S1",
            t0_ms=t0_ms,
        )


def test_load_child_aggtrades_reads_up_to_span_ms(tmp_path: Path):
    """Task 1 & 3: AggTrades reader collects trades up to T0 + 2_405_000ms (covering D=T0+25m + 5s entry + 15m endpoint)."""
    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    d_entry_max = t0_ms + 1_505_000  # D+5s (25m05s)
    endpoint_max = d_entry_max + 900_000  # 2_405_000ms after T0 (40m05s)

    csv_rows = [
        "agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker",
        f"1,10.0,1.0,1,1,{t0_ms + 1000},false",
        f"2,10.5,1.0,2,2,{d_entry_max},true",
        f"3,11.0,1.0,3,3,{endpoint_max},false",
        f"4,12.0,1.0,4,4,{endpoint_max + 1000},false",  # Beyond endpoint window
    ]
    ja_summary = _build_synthetic_ja_package(
        ja_root=tmp_path,
        parent_id="p1",
        symbol="S1",
        utc_date="2026-10-01",
        csv_rows=csv_rows,
    )

    st, trades = load_child_aggtrades_from_ja_root(
        ja_root=tmp_path,
        ja_summary=ja_summary,
        parent_article_id="p1",
        symbol="S1",
        t0_ms=t0_ms,
    )
    assert st == "ok"
    assert len(trades) == 3
    assert trades[-1].trade_id == 3
    assert trades[-1].transact_time_ms == endpoint_max


def test_load_child_oi_metrics_corrupted_file_halts(tmp_path: Path):
    """P1-01 remediation: Corrupted metrics file halts fail-closed with LaunchOiResearchError."""
    import pytest

    corrupted_csv = tmp_path / "TEST-metrics-2026-10-01.csv"
    corrupted_csv.write_text("corrupted_header_without_create_time\n1,2,3\n", encoding="utf-8")

    with pytest.raises(LaunchOiResearchError, match="corrupted_metrics_data"):
        load_child_oi_metrics_from_sources(
            symbol="TEST",
            sources_dirs=[tmp_path],
        )


def test_pipeline_no_speculative_basis_mapping(tmp_path: Path):
    """P1-03 remediation: Without an authoritative verified mapping, pipeline sets basis=None and does not drop sample."""
    import csv

    ja_summary = {"archive_package_records": []}
    jb_summary = {
        "child_rows": [
            {
                "source_article_id": "p1",
                "symbol": "S1",
                "anchor_time_ms": 1_000_000,
            }
        ]
    }
    selected = [
        {
            "parent_article_id": "p1",
            "symbol": "S1",
            "listing_regime": "standard",
            "utc_date": "2026-10-01",
        }
    ]
    mock_metrics = {
        "S1": [
            OiMetricRecord(
                create_time_ms=1_000_000,
                symbol="S1",
                sum_open_interest=100.0,
                information_time_ms=1_000_000,
            ),
            OiMetricRecord(
                create_time_ms=1_300_000,
                symbol="S1",
                sum_open_interest=150.0,
                information_time_ms=1_300_000,
            ),
            OiMetricRecord(
                create_time_ms=1_600_000,
                symbol="S1",
                sum_open_interest=200.0,
                information_time_ms=1_600_000,
            ),
        ]
    }
    mock_trades = {
        "S1": [
            AggTradeRecord(
                transact_time_ms=2_500_000,
                trade_id=1,
                price=10.0,
                quantity=1.0,
                is_buyer_maker=False,
            ),
            AggTradeRecord(
                transact_time_ms=3_400_000,
                trade_id=2,
                price=11.0,
                quantity=1.0,
                is_buyer_maker=False,
            ),
        ]
    }
    out_dir = tmp_path / "out"
    res = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: ja_summary,
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
    )
    assert res.child_complete_count == 1
    # Read generated child_rows.csv and verify basis is empty without dropping sample
    child_csv = out_dir / "child_rows.csv"
    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["is_complete"].lower() == "true"
    assert rows[0]["basis"] == ""  # Basis is None / missing, not fabricated
    assert rows[0]["basis_status"] == "unverified_product_mapping"


def test_pipeline_missing_aggtrades_package_branch_preserves_child(tmp_path: Path):
    """P1-01 remediation: When aggTrades archive is legitimately missing in J-A, PathResult(status=agg_st) is constructed without TypeError."""
    import csv

    ja_summary = {"archive_package_records": []}
    jb_summary = {
        "child_rows": [
            {
                "source_article_id": "p1",
                "symbol": "S1",
                "anchor_time_ms": 1790812800000,
            }
        ]
    }
    selected = [
        {
            "parent_article_id": "p1",
            "symbol": "S1",
            "listing_regime": "standard",
            "utc_date": "2026-10-01",
        }
    ]
    mock_metrics = {
        "S1": [
            OiMetricRecord(
                create_time_ms=1790812800000,
                symbol="S1",
                sum_open_interest=100.0,
                information_time_ms=1790812800000,
            ),
            OiMetricRecord(
                create_time_ms=1790813100000,
                symbol="S1",
                sum_open_interest=150.0,
                information_time_ms=1790813100000,
            ),
            OiMetricRecord(
                create_time_ms=1790813400000,
                symbol="S1",
                sum_open_interest=200.0,
                information_time_ms=1790813400000,
            ),
        ]
    }
    out_dir = tmp_path / "out_missing_agg"
    res = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: ja_summary,
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
    )
    assert res.child_universe_count == 1
    assert res.child_complete_count == 0
    assert res.child_missing_count == 1
    assert sorted([p.name for p in out_dir.iterdir()]) == ["child_rows.csv", "review_CN.md"]
    assert not (out_dir / "consumed_inputs.json").exists()

    with open(out_dir / "child_rows.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["is_complete"] == "false"
    assert rows[0]["missing_reason"].startswith("missing_aggtrades_archive:missing_date_")


def test_oi_provenance_manifest_verified_and_unverified_gate(tmp_path: Path):
    """Item 3 remediation:
    - Unlisted metrics file on disk is rejected fail-closed.
    - Self-certified JSON boolean/offset on a create_time-only CSV does NOT pass information_time gate.
    - Only traceable time_semantics_evidence + per-record information_time_upper_bound_ms column passes.
    """
    import hashlib
    import json

    import pytest

    t0_ms = 1790812800000  # 2026-10-01 00:00:00 UTC
    d_ms = t0_ms + 900_000
    csv_path = tmp_path / "S1-metrics-2026-10-01.csv"
    csv_content_create_only = (
        "create_time,symbol,sum_open_interest\n"
        "2026-10-01 00:00:00,S1,100.0\n"
        "2026-10-01 00:05:00,S1,125.0\n"
        "2026-10-01 00:10:00,S1,150.0\n"
    )
    csv_path.write_text(csv_content_create_only, encoding="utf-8")
    csv_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    # 1. Unlisted file on disk without oi_provenance_manifest.json -> fail-closed
    with pytest.raises(
        LaunchOiResearchError, match="corrupted_metrics_data:unlisted_metrics_file_without_manifest"
    ):
        load_child_oi_metrics_from_sources("S1", [tmp_path])

    # 2. Listed in manifest with create_time-only CSV ->
    # Evaluates under scenario assumption while keeping true information_time_ms=None and real_pit_verified=False
    prov_self_declared = {
        "symbols": {
            "S1": {
                "source_name": "binance_vision_futures_um_metrics",
                "source_version": "v1",
                "applicable_scope": "stage1_5j_launch_oi_exploratory",
                "unit": "base_coin",
                "files": {"S1-metrics-2026-10-01.csv": {"sha256": csv_sha}},
            }
        }
    }
    (tmp_path / "oi_provenance_manifest.json").write_text(
        json.dumps(prov_self_declared), encoding="utf-8"
    )
    st_unv, recs_unv = load_child_oi_metrics_from_sources("S1", [tmp_path])
    assert st_unv == "ok"
    assert recs_unv[0].information_time_ms is None
    res_unv = calculate_oi_change(recs_unv, "S1", t0_ms=t0_ms, d_ms=d_ms, margin_ms=300_000)
    assert res_unv.status == "ok"
    assert res_unv.real_pit_verified is False
    assert res_unv.information_time_ms is None

    # 3. Unlisted extra file alongside manifest -> rejected fail-closed
    extra_csv = tmp_path / "S1-metrics-2026-10-02.csv"
    extra_csv.write_text(csv_content_create_only, encoding="utf-8")
    with pytest.raises(LaunchOiResearchError, match="corrupted_metrics_data:unlisted_metrics_file"):
        load_child_oi_metrics_from_sources("S1", [tmp_path])
    extra_csv.unlink()

    # 4. Traceable time_semantics_evidence + per-record information_time_upper_bound_ms column (+30s):
    # Conflicts with Scenario A (info_offset=0) -> verified_fact_conflict; compatible with Scenario B (info_offset=5m) -> ok
    csv_with_ub = (
        "create_time,symbol,sum_open_interest,information_time_upper_bound_ms\n"
        f"2026-10-01 00:00:00,S1,100.0,{t0_ms + 30_000}\n"
        f"2026-10-01 00:05:00,S1,125.0,{t0_ms + 330_000}\n"
        f"2026-10-01 00:10:00,S1,150.0,{t0_ms + 630_000}\n"
    )
    csv_path.write_text(csv_with_ub, encoding="utf-8")
    csv_ub_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    prov_verified = {
        "symbols": {
            "S1": {
                "source_name": "binance_vision_futures_um_metrics",
                "source_version": "v1",
                "applicable_scope": "stage1_5j_launch_oi_exploratory",
                "unit": "base_coin",
                "time_semantics_evidence": {
                    "source": "exchange_receipt_audit_log_v1",
                    "applicable_scope": "S1:2026-10-01",
                    "verifiable_basis": "per_row_receipt_timestamp_upper_bound",
                },
                "files": {"S1-metrics-2026-10-01.csv": {"sha256": csv_ub_sha}},
            }
        }
    }
    (tmp_path / "oi_provenance_manifest.json").write_text(
        json.dumps(prov_verified), encoding="utf-8"
    )
    st_ver, recs_ver = load_child_oi_metrics_from_sources("S1", [tmp_path])
    assert st_ver == "ok"
    assert recs_ver[0].time_evidence_source == "exchange_receipt_audit_log_v1"
    res_ver_a = calculate_oi_change(
        recs_ver, "S1", t0_ms=t0_ms, d_ms=t0_ms + 1_500_000, scenario_name="A", margin_ms=300_000
    )
    assert res_ver_a.status == "verified_fact_conflict"
    res_ver_b = calculate_oi_change(
        recs_ver, "S1", t0_ms=t0_ms, d_ms=t0_ms + 1_500_000, scenario_name="B", margin_ms=600_000
    )
    assert res_ver_b.status == "ok"
    assert abs(res_ver_b.oi_change - 0.2) < 1e-9  # 150.0 / 125.0 - 1.0 = 0.2


def test_kline_mapping_manifest_verified_basis_and_unit_mismatch(tmp_path: Path):
    """Item 4 remediation: Verified kline_mapping_manifest.json + exchange_info.json computes basis;
    unverified pair or unit mismatch sets basis=None while keeping OI sample.
    """
    import csv
    import hashlib
    import json

    t0_ms = 1790812800000
    d_ms = t0_ms + OBSERVATION_OFFSET_MS
    bar_open = d_ms - 120_000
    bar_close = d_ms - 60_000  # Last closed 1m bar at or before D - 60_000ms cutoff

    mark_csv = tmp_path / "S1-markPriceKlines-1m-2026-10-01.csv"
    index_csv = tmp_path / "S1_INDEX-indexPriceKlines-1m-2026-10-01.csv"
    mark_csv.write_text(
        f"open_time,open,high,low,close,volume,close_time\n{bar_open},10.0,10.5,9.9,10.2,0,{bar_close}\n",
        encoding="utf-8",
    )
    index_csv.write_text(
        f"open_time,open,high,low,close,volume,close_time\n{bar_open},10.0,10.1,9.9,10.0,0,{bar_close}\n",
        encoding="utf-8",
    )
    mark_sha = hashlib.sha256(mark_csv.read_bytes()).hexdigest()
    index_sha = hashlib.sha256(index_csv.read_bytes()).hexdigest()

    exchange_info_path = tmp_path / "exchange_info.json"
    exchange_info_obj = {
        "symbols": [
            {
                "symbol": "S1",
                "pair": "S1_INDEX",
                "contractType": "PERPETUAL",
                "quoteAsset": "USDT",
            }
        ]
    }
    exchange_info_path.write_text(json.dumps(exchange_info_obj), encoding="utf-8")
    ex_info_sha = hashlib.sha256(exchange_info_path.read_bytes()).hexdigest()

    # 1. Valid verified mapping with hash-verified exchange_info.json -> basis = 10.2 / 10.0 - 1.0 = 0.02
    kman = {
        "symbols": {
            "S1": {
                "source_name": "binance_futures_exchange_info",
                "source_version": "v1",
                "evidence_reference": "exchangeInfo_pair_contract_mapping",
                "target_symbol": "S1",
                "mapped_index_symbol": "S1_INDEX",
                "mark_unit": "USDT",
                "index_unit": "USDT",
                "exchange_info_file": "exchange_info.json",
                "exchange_info_sha256": ex_info_sha,
                "mark_files": {"S1-markPriceKlines-1m-2026-10-01.csv": {"sha256": mark_sha}},
                "index_files": {
                    "S1_INDEX-indexPriceKlines-1m-2026-10-01.csv": {"sha256": index_sha}
                },
            }
        }
    }
    (tmp_path / "kline_mapping_manifest.json").write_text(json.dumps(kman), encoding="utf-8")

    selected = [
        {
            "parent_article_id": "p1",
            "symbol": "S1",
            "listing_regime": "standard",
            "utc_date": "2026-10-01",
        }
    ]
    jb_summary = {"child_rows": [{"source_article_id": "p1", "symbol": "S1", "anchor_time_ms": t0_ms}]}
    mock_metrics = {
        "S1": [
            OiMetricRecord(t0_ms, "S1", 100.0, information_time_ms=t0_ms),
            OiMetricRecord(t0_ms + 300_000, "S1", 120.0, information_time_ms=t0_ms + 300_000),
            OiMetricRecord(t0_ms + 600_000, "S1", 150.0, information_time_ms=t0_ms + 600_000),
        ]
    }
    mock_trades = {
        "S1": [
            AggTradeRecord(d_ms, 1, 10.0, 1.0, False),
            AggTradeRecord(d_ms + 900_000, 2, 11.0, 1.0, False),
        ]
    }

    out1 = tmp_path / "out_valid_basis"
    res1 = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out1,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
        extra_sources_dirs=[tmp_path],
    )
    assert res1.child_complete_count == 1
    with open(out1 / "child_rows.csv", "r", encoding="utf-8") as f:
        r1 = list(csv.DictReader(f))[0]
    assert abs(float(r1["basis"]) - 0.02) < 1e-8
    assert r1["basis_status"] == "ok"

    # 2. Mismatched units (USDT vs USD) -> basis is empty, basis_status is unit_mismatch, child remains complete!
    kman["symbols"]["S1"]["index_unit"] = "USD"
    (tmp_path / "kline_mapping_manifest.json").write_text(json.dumps(kman), encoding="utf-8")
    out2 = tmp_path / "out_unit_mismatch"
    res2 = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out2,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
        extra_sources_dirs=[tmp_path],
    )
    assert res2.child_complete_count == 1
    with open(out2 / "child_rows.csv", "r", encoding="utf-8") as f:
        r2 = list(csv.DictReader(f))[0]
    assert r2["is_complete"] == "true"
    assert r2["basis"] == ""
    assert r2["basis_status"] == "unit_mismatch"


def test_regime_separated_grouping_does_not_mix_pre_market_and_standard():
    """Item 1 remediation: pre_market and standard must compute independent Child/Parent medians,
    High/Low groups, and Jackknife LOO without cross-regime mixing.
    """
    children = [
        # pre_market samples have smaller OI change (0.05, 0.15)
        ChildEvaluation(
            parent_article_id="pm_1",
            symbol="PM1USDT",
            listing_regime="pre_market",
            is_complete=True,
            oi_change=0.05,
            terminal_return=0.01,
            long_mae=-0.02,
            long_mfe=0.03,
            utc_date="2026-10-01",
        ),
        ChildEvaluation(
            parent_article_id="pm_2",
            symbol="PM2USDT",
            listing_regime="pre_market",
            is_complete=True,
            oi_change=0.15,
            terminal_return=0.09,
            long_mae=-0.01,
            long_mfe=0.12,
            utc_date="2026-10-02",
        ),
        # standard samples have larger OI change (0.50, 0.90)
        ChildEvaluation(
            parent_article_id="st_1",
            symbol="ST1USDT",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.50,
            terminal_return=-0.04,
            long_mae=-0.08,
            long_mfe=0.02,
            utc_date="2026-10-03",
        ),
        ChildEvaluation(
            parent_article_id="st_2",
            symbol="ST2USDT",
            listing_regime="standard",
            is_complete=True,
            oi_change=0.90,
            terminal_return=0.06,
            long_mae=-0.03,
            long_mfe=0.10,
            utc_date="2026-10-04",
        ),
    ]

    res = aggregate_and_group(children)
    assert "pre_market" in res.regime_summaries
    assert "standard" in res.regime_summaries

    pm_sum = res.regime_summaries["pre_market"]
    st_sum = res.regime_summaries["standard"]

    # Within pre_market: median OI is (0.05 + 0.15)/2 = 0.10 -> 1 High (PM2: 0.09), 1 Low (PM1: 0.01)
    assert pm_sum.child_high_group is not None and pm_sum.child_high_group.count == 1
    assert pm_sum.child_low_group is not None and pm_sum.child_low_group.count == 1
    assert abs(pm_sum.child_high_group.terminal_stats.mean - 0.09) < 1e-9
    assert abs(pm_sum.child_low_group.terminal_stats.mean - 0.01) < 1e-9
    assert pm_sum.parent_jackknife is not None
    assert abs(pm_sum.parent_jackknife.base_diff - 0.08) < 1e-9

    # Within standard: median OI is (0.50 + 0.90)/2 = 0.70 -> 1 High (ST2: 0.06), 1 Low (ST1: -0.04)
    assert st_sum.child_high_group is not None and st_sum.child_high_group.count == 1
    assert st_sum.child_low_group is not None and st_sum.child_low_group.count == 1
    assert abs(st_sum.child_high_group.terminal_stats.mean - 0.06) < 1e-9
    assert abs(st_sum.child_low_group.terminal_stats.mean - (-0.04)) < 1e-9
    assert st_sum.parent_jackknife is not None
    assert abs(st_sum.parent_jackknife.base_diff - 0.10) < 1e-9


def test_pipeline_scenarios_a_b_c_and_opening_grid_control_in_outputs(tmp_path: Path):
    """Scenario A/B/C evaluation & opening grid control:
    - Pipeline evaluates fixed Scenarios A (+5m), B (+10m, Main), and C (+15m) and floor_5m(T0) opening grid control.
    - Writes strictly approved columns to child_rows.csv and dedicated sections to review_CN.md.
    - Output directory strictly contains only the two approved files: child_rows.csv and review_CN.md.
    - Rejects existing output directory in write_exploratory_outputs.
    """
    import csv

    import pytest

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        write_exploratory_outputs,
    )

    # T0 = 1_000 ms (so floor_5m(T0) = 0, strictly < T0)
    t0_ms = 1_000
    d_ms = t0_ms + OBSERVATION_OFFSET_MS  # 1_501_000 ms
    # Cutoffs:
    # 5m margin: 1_201_000 -> latest label 600_000 (L0=300_000, L1=600_000)
    # 3m margin: 1_321_000 -> latest label 600_000
    # 1m margin: 1_441_000 -> latest label 600_000
    selected = [
        {
            "parent_article_id": "p1",
            "symbol": "S1",
            "listing_regime": "standard",
            "utc_date": "1970-01-01",
        },
        {
            "parent_article_id": "p2",
            "symbol": "S2",
            "listing_regime": "standard",
            "utc_date": "1970-01-01",
        },
    ]
    jb_summary = {
        "child_rows": [
            {"source_article_id": "p1", "symbol": "S1", "anchor_time_ms": t0_ms},
            {"source_article_id": "p2", "symbol": "S2", "anchor_time_ms": t0_ms},
        ]
    }
    mock_metrics = {
        "S1": [
            OiMetricRecord(0, "S1", 80.0, information_time_ms=0),
            OiMetricRecord(300_000, "S1", 100.0, information_time_ms=300_000),
            OiMetricRecord(600_000, "S1", 120.0, information_time_ms=600_000),
        ],
        "S2": [
            OiMetricRecord(0, "S2", 50.0, information_time_ms=0),
            OiMetricRecord(300_000, "S2", 100.0, information_time_ms=300_000),
            OiMetricRecord(600_000, "S2", 180.0, information_time_ms=600_000),
        ],
    }
    mock_trades = {
        "S1": [
            AggTradeRecord(d_ms, 1, 10.0, 1.0, False),
            AggTradeRecord(d_ms + 900_000, 2, 10.5, 1.0, False),  # +0.05
        ],
        "S2": [
            AggTradeRecord(d_ms, 1, 10.0, 1.0, False),
            AggTradeRecord(d_ms + 900_000, 2, 12.0, 1.0, False),  # +0.20
        ],
    }

    out_dir = tmp_path / "sens_and_grid_out"
    res = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
    )

    # Check scenario summaries for standard regime (A, B, C)
    st_scen = res.scenario_summaries["standard"]
    for k in ("A", "B", "C"):
        assert st_scen[k].child_complete_count == 2
        assert st_scen[k].parent_complete_count == 2
        assert abs(st_scen[k].child_terminal_diff_mean - 0.15) < 1e-9

    # Check grid summary for standard regime (L0=0, L1=300_000, does NOT coincide with main L0=300_000, L1=600_000)
    st_grid = res.grid_summaries["standard"]
    assert st_grid.child_grid_valid_count == 2
    assert st_grid.coincides_with_main_count == 0

    assert sorted([p.name for p in out_dir.iterdir()]) == ["child_rows.csv", "review_CN.md"]
    assert not (out_dir / "consumed_inputs.json").exists()

    with open(out_dir / "child_rows.csv", "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]["oi_a_status"] == "ok"
    assert rows[0]["oi_b_status"] == "ok"
    assert rows[0]["oi_c_status"] == "ok"
    assert "oi_3m_status" not in rows[0]
    assert "oi_1m_status" not in rows[0]
    assert rows[0]["grid_status"] == "ok"
    assert rows[0]["grid_t0_minus_l0_ms"] == "1000"
    assert rows[0]["grid_coincides_with_main"] == "false"

    md_text = (out_dir / "review_CN.md").read_text(encoding="utf-8")
    assert "三组 OI 时间假设情景对照（Scenario A / B / C）与跨情景样本重合" in md_text
    assert "开盘网格对照（`floor_5m(T0)` 单独列出，不混入主样本）" in md_text

    # Item 6: Calling write_exploratory_outputs on an existing output_dir must fail-closed
    with pytest.raises(LaunchOiResearchError, match="output_dir_already_exists"):
        write_exploratory_outputs(out_dir, [], res, project_root=tmp_path)


def test_pipeline_missing_oi_source_preserves_sample(tmp_path: Path):
    """P1-01 remediation: missing OI source must not crash with TypeError (scenario_id vs scenario_name) and must preserve universe gap."""
    jb_summary = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [
            {
                "source_article_id": "art_1",
                "symbol": "BTCUSDT",
                "anchor_time_ms": 1_000_000,
                "scheduled_anchor_time_ms": 1_000_000,
            }
        ],
    }
    selected_children = [
        {
            "parent_article_id": "art_1",
            "symbol": "BTCUSDT",
            "listing_regime": "standard",
            "utc_date": "2026-05-01",
        }
    ]
    out_dir = tmp_path / "out_missing_oi"

    # Execute pipeline with empty sources_dirs and no in-memory metrics
    res = execute_exploratory_pipeline(
        selected_children=selected_children,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=None,
        aggtrades_by_symbol={"BTCUSDT": []},
        sources_dirs=[],
    )

    assert res.child_universe_count == 1
    assert res.child_complete_count == 0
    assert res.child_missing_count == 1

    child_csv = out_dir / "child_rows.csv"
    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    c0 = rows[0]
    assert c0["symbol"] == "BTCUSDT"
    assert c0["is_complete"] == "false"
    assert c0["oi_a_status"] == "metrics_source_not_found"
    assert c0["oi_b_status"] == "metrics_source_not_found"
    assert c0["oi_c_status"] == "metrics_source_not_found"
    assert c0["grid_a_status"] == "metrics_source_not_found"
    assert c0["grid_b_status"] == "metrics_source_not_found"
    assert c0["grid_c_status"] == "metrics_source_not_found"


def test_opening_grid_per_scenario_differential_and_time_points(tmp_path: Path):
    """P1-02 and P1-04 remediation: per-scenario opening grid evaluation, differential fact conflict, and exposure of time points."""
    # T0 = 1_000_000 -> floor_5m(T0) = 900_000, grid_l1 = 1_200_000. D = 1_000_000 + 1_500_000 = 2_500_000.
    t0_ms = 1_000_000
    # Provide records for grid L0 (900_000), grid L1 (1_200_000), and main L0/L1 (1_500_000, 1_800_000)
    # Inject verified_available_time_ms = 900_000 + 400_000 = 1_300_000 on grid L0 (900_000).
    # Since 900_000 < T0, it is not in [T0, D], so it does not conflict with main scenario calculation.
    # For Scenario A opening grid: pub_margin is 300_000, cutoff is 900_000 + 300_000 = 1_200_000. 1_300_000 > 1_200_000 -> conflict!
    # For Scenario B opening grid: pub_margin is 600_000, cutoff is 900_000 + 600_000 = 1_500_000. 1_300_000 <= 1_500_000 -> ok!
    # For Scenario C opening grid: pub_margin is 900_000, cutoff is 900_000 + 900_000 = 1_800_000. 1_300_000 <= 1_800_000 -> ok!
    metrics = [
        OiMetricRecord(
            symbol="ABCUSDT",
            create_time_ms=900_000,
            sum_open_interest=100.0,
            unit="USDT",
            verified_available_time_ms=1_300_000,
        ),
        OiMetricRecord(symbol="ABCUSDT", create_time_ms=1_200_000, sum_open_interest=110.0, unit="USDT"),
        OiMetricRecord(symbol="ABCUSDT", create_time_ms=1_500_000, sum_open_interest=120.0, unit="USDT"),
        OiMetricRecord(symbol="ABCUSDT", create_time_ms=1_800_000, sum_open_interest=130.0, unit="USDT"),
    ]
    # Trade path covering [D, D+5s] entry and [E-1s, E] endpoint
    trades = [
        AggTradeRecord(
            transact_time_ms=2_500_000,
            trade_id=1,
            price=10.0,
            quantity=1.0,
            is_buyer_maker=False,
        ),
        AggTradeRecord(
            transact_time_ms=3_400_000,
            trade_id=2,
            price=12.0,
            quantity=1.0,
            is_buyer_maker=False,
        ),
    ]

    jb_summary = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [
            {
                "source_article_id": "art_2",
                "symbol": "ABCUSDT",
                "anchor_time_ms": t0_ms,
                "symbol_launch_time_ms": t0_ms + 100_000,
            }
        ],
    }
    selected = [
        {
            "parent_article_id": "art_2",
            "symbol": "ABCUSDT",
            "listing_regime": "standard",
            "utc_date": "2026-05-01",
        }
    ]
    out_dir = tmp_path / "out_grid_diff"

    res = execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol={"ABCUSDT": metrics},
        aggtrades_by_symbol={"ABCUSDT": trades},
    )
    assert res.child_complete_count == 1

    child_csv = out_dir / "child_rows.csv"
    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    r0 = rows[0]

    # Grid per-scenario assertions
    assert r0["grid_a_status"] == "verified_fact_conflict"
    assert r0["grid_b_status"] == "ok"
    assert r0["grid_c_status"] == "ok"
    assert r0["grid_t0_minus_l0_ms"] == "100000"
    assert r0["grid_scheduled_minus_l0_ms"] == "200000"

    # Detailed time points exposure assertions
    assert r0["oi_a_assumed_info_l0_ms"] != ""
    assert r0["oi_a_assumed_avail_l0_ms"] != ""
    assert r0["oi_b_assumed_info_l0_ms"] != ""
    assert r0["oi_b_assumed_avail_l0_ms"] != ""
    assert r0["oi_c_assumed_info_l0_ms"] != ""
    assert r0["oi_c_assumed_avail_l0_ms"] != ""

    md_text = (out_dir / "review_CN.md").read_text(encoding="utf-8")
    assert "开盘网格对照（`floor_5m(T0)` 单独列出，不混入主样本）" in md_text
    assert "Grid A Status" in md_text or "Scenario A" in md_text


def test_grid_scheduled_launch_distinct_from_t0_and_missing_handling(tmp_path: Path):
    """P1-02 remediation: J-B child field symbol_launch_time_ms must be used without T0 fallback; missing launch time remains None."""
    # Child 1: planned launch at 1_000_000, physical first trade T0 at 1_005_000.
    # floor_5m(T0) = 900_000.
    # T0 - L0 = 1_005_000 - 900_000 = 105_000 ms.
    # scheduled - L0 = 1_000_000 - 900_000 = 100_000 ms. Distinct!
    # Child 2: symbol_launch_time_ms is missing (None).
    # T0 - L0 = 105_000 ms.
    # scheduled - L0 must be None (do NOT fall back to T0)!
    jb_summary = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [
            {
                "source_article_id": "art_1",
                "symbol": "SYM1USDT",
                "anchor_time_ms": 1_005_000,
                "symbol_launch_time_ms": 1_000_000,
            },
            {
                "source_article_id": "art_2",
                "symbol": "SYM2USDT",
                "anchor_time_ms": 1_005_000,
                "symbol_launch_time_ms": None,
            },
        ],
    }
    selected = [
        {"parent_article_id": "art_1", "symbol": "SYM1USDT", "listing_regime": "standard", "utc_date": "2026-05-01"},
        {"parent_article_id": "art_2", "symbol": "SYM2USDT", "listing_regime": "standard", "utc_date": "2026-05-01"},
    ]
    out_dir = tmp_path / "out_sched_test"

    execute_exploratory_pipeline(
        selected_children=selected,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=None,
        aggtrades_by_symbol={"SYM1USDT": [], "SYM2USDT": []},
        sources_dirs=[],
    )

    child_csv = out_dir / "child_rows.csv"
    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    r_sym1 = next(r for r in rows if r["symbol"] == "SYM1USDT")
    r_sym2 = next(r for r in rows if r["symbol"] == "SYM2USDT")

    # Sym 1 has distinct T0 - L0 and Scheduled - L0
    assert r_sym1["grid_t0_minus_l0_ms"] == "105000"
    assert r_sym1["grid_scheduled_minus_l0_ms"] == "100000"

    # Sym 2 has missing scheduled_launch_time_ms -> must be empty, NOT 105000!
    assert r_sym2["grid_t0_minus_l0_ms"] == "105000"
    assert r_sym2["grid_scheduled_minus_l0_ms"] == ""


def test_consumed_inputs_provenance_report_logging_and_output_scope(tmp_path: Path):
    """P1-03 remediation & output scope:
    - Pipeline records actual consumed input file identities in review_CN.md Section 7.
    - Output directory strictly contains only the approved two files: child_rows.csv and review_CN.md.
    - No unexpected extra files (such as consumed_inputs.json) are created.
    """
    import hashlib
    import json

    # 1. Synthetic / in-memory run: 0 consumed files on disk
    out_synth = tmp_path / "out_synth"
    jb_synth = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [{"source_article_id": "art_1", "symbol": "TEST", "anchor_time_ms": 1_000_000}],
    }
    sel_synth = [{"parent_article_id": "art_1", "symbol": "TEST", "listing_regime": "standard", "utc_date": "2026-05-01"}]
    res_synth = execute_exploratory_pipeline(
        selected_children=sel_synth,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_synth,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_synth,
        metrics_by_symbol={"TEST": []},
        aggtrades_by_symbol={"TEST": []},
        sources_dirs=[],
    )
    assert res_synth.consumed_inputs == []
    assert not (out_synth / "consumed_inputs.json").exists()
    assert sorted([p.name for p in out_synth.iterdir()]) == ["child_rows.csv", "review_CN.md"]
    md_synth = (out_synth / "review_CN.md").read_text(encoding="utf-8")
    assert "## 7. 实际消费输入文件清单与身份（Input Provenance Manifest）" in md_synth
    assert "无实际磁盘输入文件消费记录" in md_synth

    # 2. Disk sources run: consumes manifest and data CSV
    oi_dir = tmp_path / "oi_sources"
    oi_dir.mkdir(parents=True, exist_ok=True)
    csv_file = oi_dir / "TEST-metrics-2026-05-01.csv"
    csv_file.write_text("create_time,sum_open_interest\n2026-05-01 00:00:00,100.0\n", encoding="utf-8")
    csv_sha = hashlib.sha256(csv_file.read_bytes()).hexdigest()

    manifest_file = oi_dir / "oi_provenance_manifest.json"
    manifest_data = {
        "symbols": {
            "TEST": {
                "source_name": "binance",
                "source_version": "v1",
                "applicable_scope": "all",
                "unit": "USDT",
                "files": {
                    csv_file.name: {"sha256": csv_sha}
                },
            }
        }
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    manifest_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()

    out_disk = tmp_path / "out_disk"
    res_disk = execute_exploratory_pipeline(
        selected_children=sel_synth,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_disk,
        project_root=tmp_path,
        ja_loader=lambda r: {"archive_package_records": []},
        jb_loader=lambda r: jb_synth,
        metrics_by_symbol=None,
        aggtrades_by_symbol={"TEST": []},
        sources_dirs=[oi_dir],
    )
    assert res_disk.consumed_inputs is not None
    assert len(res_disk.consumed_inputs) >= 2
    assert not (out_disk / "consumed_inputs.json").exists()
    assert sorted([p.name for p in out_disk.iterdir()]) == ["child_rows.csv", "review_CN.md"]

    c_paths = [item["file_path"] for item in res_disk.consumed_inputs]
    c_shas = [item["sha256"] for item in res_disk.consumed_inputs]
    assert any("TEST-metrics-2026-05-01.csv" in p for p in c_paths)
    assert any("oi_provenance_manifest.json" in p for p in c_paths)
    assert csv_sha in c_shas
    assert manifest_sha in c_shas

    md_disk = (out_disk / "review_CN.md").read_text(encoding="utf-8")
    assert "## 7. 实际消费输入文件清单与身份（Input Provenance Manifest）" in md_disk
    assert csv_sha in md_disk
    assert manifest_sha in md_disk


def test_pipeline_derives_utc_date_from_jb_anchor_and_reports_both_universe_and_complete_date_counts(tmp_path: Path):
    """P1 defect remediation:
    - selected_children without 'utc_date' (strictly conforming to EXPECTED_LEDGER_COLUMNS 12 fields)
      must automatically derive 'utc_date' from verified J-B anchor_time_ms.
    - child_rows.csv must record the derived 'utc_date' (not empty or unknown).
    - review_CN.md must report both 'Parent Universe UTC 日期分布' and '完整 Parent 样本 UTC 日期分布',
      accurately matching their respective statistical denominators.
    """
    import csv
    import json
    from datetime import datetime, timezone

    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        EXPECTED_LEDGER_COLUMNS,
        OBSERVATION_OFFSET_MS,
        AggTradeRecord,
        OiMetricRecord,
        execute_exploratory_pipeline,
    )

    t0_ms = int(datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    d_ms = t0_ms + OBSERVATION_OFFSET_MS
    expected_utc_date = "2026-05-01"

    row_parent1 = {
        "parent_article_id": "p_valid",
        "symbol": "BTCUSDT",
        "asset_class": "crypto",
        "listing_regime": "standard",
        "classification_status": "confirmed",
        "table_index": "0",
        "symbol_column_index": "0",
        "field_header": "Symbol",
        "raw_cell_value": "BTC",
        "evidence_locator": "loc_1",
        "source_relative_path": "path_1",
        "source_sha256": "sha_1",
    }
    assert set(row_parent1.keys()) == set(EXPECTED_LEDGER_COLUMNS)
    assert "utc_date" not in row_parent1

    row_parent2 = {
        "parent_article_id": "p_incomplete",
        "symbol": "ETHUSDT",
        "asset_class": "crypto",
        "listing_regime": "standard",
        "classification_status": "confirmed",
        "table_index": "0",
        "symbol_column_index": "0",
        "field_header": "Symbol",
        "raw_cell_value": "ETH",
        "evidence_locator": "loc_2",
        "source_relative_path": "path_2",
        "source_sha256": "sha_2",
    }
    assert set(row_parent2.keys()) == set(EXPECTED_LEDGER_COLUMNS)

    selected_children = [row_parent1, row_parent2]

    jb_summary = {
        "schema_version": "stage1_5j_b_historical_aggtrades_launch_response.v1",
        "child_rows": [
            {
                "source_article_id": "p_valid",
                "symbol": "BTCUSDT",
                "anchor_time_ms": t0_ms,
                "symbol_launch_time_ms": t0_ms,
            },
            {
                "source_article_id": "p_incomplete",
                "symbol": "ETHUSDT",
                "anchor_time_ms": t0_ms,
                "symbol_launch_time_ms": t0_ms,
            },
        ],
    }

    mock_metrics = {
        "BTCUSDT": [
            OiMetricRecord(t0_ms + 600_000, "BTCUSDT", 100.0, information_time_ms=t0_ms + 600_000),
            OiMetricRecord(t0_ms + 900_000, "BTCUSDT", 150.0, information_time_ms=t0_ms + 900_000),
        ],
        "ETHUSDT": [],
    }

    mock_trades = {
        "BTCUSDT": [
            AggTradeRecord(transact_time_ms=d_ms, trade_id=1, price=10.0, quantity=1.0, is_buyer_maker=False),
            AggTradeRecord(transact_time_ms=d_ms + 900_000, trade_id=2, price=11.0, quantity=1.0, is_buyer_maker=False),
        ],
        "ETHUSDT": [],
    }

    out_dir = tmp_path / "out_utc_date_test"
    res = execute_exploratory_pipeline(
        selected_children=selected_children,
        ja_root=tmp_path,
        jb_root=tmp_path,
        output_dir=out_dir,
        project_root=tmp_path,
        ja_loader=lambda r: {"artifacts": []},
        jb_loader=lambda r: jb_summary,
        metrics_by_symbol=mock_metrics,
        aggtrades_by_symbol=mock_trades,
        sources_dirs=[],
    )

    # 1. Pipeline result checks
    std_reg = res.regime_summaries["standard"]
    assert std_reg.parent_universe_count == 2
    assert std_reg.parent_complete_count == 1
    assert getattr(std_reg, "universe_parent_utc_date_counts", None) == {expected_utc_date: 2}
    assert getattr(std_reg, "complete_parent_utc_date_counts", None) == {expected_utc_date: 1}

    # 2. child_rows.csv checks: derived utc_date must be populated
    child_csv = out_dir / "child_rows.csv"
    with open(child_csv, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    btc_row = next(r for r in rows if r["symbol"] == "BTCUSDT")
    eth_row = next(r for r in rows if r["symbol"] == "ETHUSDT")
    assert btc_row["utc_date"] == expected_utc_date
    assert eth_row["utc_date"] == expected_utc_date

    # 3. review_CN.md checks: both distributions must be present and distinct
    review_md = out_dir / "review_CN.md"
    md_text = review_md.read_text(encoding="utf-8")
    assert f"- **Parent Universe UTC 日期分布**: `{json.dumps({expected_utc_date: 2})}`" in md_text
    assert f"- **完整 Parent 样本 UTC 日期分布**: `{json.dumps({expected_utc_date: 1})}`" in md_text


def test_parent_utc_date_resolved_from_all_children_when_first_child_missing_date():
    """P2 defect remediation:
    When a Parent has multiple children where the first child has missing utc_date
    but subsequent child has a known date, the Parent's date must be resolved to the known date,
    NOT silently recorded as 'unknown'.
    """
    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        ChildEvaluation,
        _compute_regime_summary,
    )

    c1 = ChildEvaluation(
        parent_article_id="p1",
        symbol="SYM1",
        listing_regime="standard",
        is_complete=False,
        missing_reason="missing_jb_anchor_time",
        utc_date=None,
    )
    c2 = ChildEvaluation(
        parent_article_id="p1",
        symbol="SYM2",
        listing_regime="standard",
        is_complete=False,
        missing_reason="missing_oi",
        utc_date="2026-05-01",
    )

    summary = _compute_regime_summary("standard", [c1, c2])
    assert summary.universe_parent_utc_date_counts == {"2026-05-01": 1}
    assert "unknown" not in (summary.universe_parent_utc_date_counts or {})


def test_parent_utc_date_conflict_when_children_have_different_dates():
    """P2 defect remediation:
    When a Parent has multiple children with differing known UTC dates (e.g. cross-date launch),
    the Parent must be explicitly marked as a multi-date conflict, NOT silently defaulting to the first child's date.
    """
    from src.research.external_signal_shadow.launch_open_interest_basis_exploratory import (
        ChildEvaluation,
        _compute_regime_summary,
    )

    c1 = ChildEvaluation(
        parent_article_id="p1",
        symbol="SYM1",
        listing_regime="standard",
        is_complete=True,
        oi_change=0.10,
        terminal_return=0.05,
        utc_date="2026-05-01",
    )
    c2 = ChildEvaluation(
        parent_article_id="p1",
        symbol="SYM2",
        listing_regime="standard",
        is_complete=True,
        oi_change=0.20,
        terminal_return=0.08,
        utc_date="2026-05-02",
    )

    summary = _compute_regime_summary("standard", [c1, c2])
    assert summary.parent_complete_count == 1
    comp_p = summary.complete_parents[0]
    assert comp_p.utc_date == "multi_date_conflict:2026-05-01,2026-05-02"
    assert summary.complete_parent_utc_date_counts == {"multi_date_conflict:2026-05-01,2026-05-02": 1}
    assert summary.universe_parent_utc_date_counts == {"multi_date_conflict:2026-05-01,2026-05-02": 1}








