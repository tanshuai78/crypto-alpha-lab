"""Tests for Stage 1.6F denominator reconstruction, deterministic matching, windows, and descriptive reducers."""

from pathlib import Path

import pytest

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    DenominatorRow,
    compute_descriptive_metrics,
    compute_window_intervals,
    match_control_candidates,
    project_denominator_row,
    reconstruct_denominator,
    resolve_settlement_rule,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_c_input,
    verify_market_evidence,
)
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    build_valid_completed_c_root,
    copy_market_evidence_package,
)


def test_reconstruct_denominator_preserves_all_rows(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified_c = verify_c_input(project_root, completed_root, source_export)

    denominator = reconstruct_denominator(verified_c)
    assert len(denominator) > 0

    # Ensure all rows have required provenance and linkage
    for row in denominator:
        assert isinstance(row, DenominatorRow)
        assert row.parent_article_id
        assert row.contract_id
        assert row.symbol
        assert row.input_export_id == verified_c.input_export_id
        assert row.input_manifest_sha256 == verified_c.input_manifest_sha256
        assert row.source_export_receipt_sha256 == verified_c.source_export_receipt_sha256
        assert isinstance(row.eligibility_passed, bool)
        assert isinstance(row.ineligibility_reasons, tuple)


def test_reconstruct_denominator_absent_c_fields_no_fallback(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified_c = verify_c_input(project_root, completed_root, source_export)

    # Mutate retained bytes of delisting_contracts.jsonl to strip C semantic fields
    import json
    lines = [json.loads(line) for line in verified_c.retained_bytes["delisting_contracts.jsonl"].decode("utf-8").splitlines()]
    first_contract = lines[0]
    # Delete semantic fields
    first_contract.pop("quote_asset", None)
    first_contract.pop("settlement_asset", None)
    first_contract.pop("margin_family", None)
    first_contract.pop("contract_type", None)
    first_contract.pop("underlying_family", None)

    mutated_bytes = "\n".join(json.dumps(r) for r in lines).encode("utf-8")
    new_retained_bytes = dict(verified_c.retained_bytes)
    new_retained_bytes["delisting_contracts.jsonl"] = mutated_bytes

    from dataclasses import replace
    mutated_c = replace(verified_c, retained_bytes=new_retained_bytes)

    denominator = reconstruct_denominator(mutated_c)
    mutated_row = denominator[0]

    # Must NOT fall back to USDT, USDM, PERPETUAL!
    assert mutated_row.quote_asset == "", f"Expected empty string, got {mutated_row.quote_asset}"
    assert mutated_row.settlement_asset == "", f"Expected empty string, got {mutated_row.settlement_asset}"
    assert mutated_row.margin_family == "", f"Expected empty string, got {mutated_row.margin_family}"
    assert mutated_row.contract_type == "", f"Expected empty string, got {mutated_row.contract_type}"
    assert mutated_row.underlying_family == "", f"Expected empty string, got {mutated_row.underlying_family}"
    assert mutated_row.eligibility_passed is False
    assert any("quote_asset" in r for r in mutated_row.ineligibility_reasons)
    assert any("settlement_asset" in r for r in mutated_row.ineligibility_reasons)
    assert any("margin_family" in r for r in mutated_row.ineligibility_reasons)
    assert any("contract_type" in r for r in mutated_row.ineligibility_reasons)


def test_parent_inv_f02_projection_matrix(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified_c = verify_c_input(project_root, completed_root, source_export)
    denominator = reconstruct_denominator(verified_c)
    row = denominator[0]

    # Projection must preserve exact None availability and historical_unknown status
    proj = project_denominator_row(row)
    assert proj["system_available_at_ms"] is None
    assert proj["fact_available_at_ms"] is None
    assert proj["capture_time_status"] == "historical_unknown"

    # All 13 permission flags must be exact boolean False
    for flag_name, flag_val in ALL_PERMISSION_FLAGS_FALSE.items():
        assert proj[flag_name] is False

    # Attempting to substitute t_pub_ms or a download timestamp for available_at must be rejected
    with pytest.raises(ValueError, match="availability_substitution_forbidden"):
        project_denominator_row(row, substitute_available_at_ms=1736928000000)


def test_pure_matcher_reef_auxiliary_conservation(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified_market = verify_market_evidence(pkg_dir)

    # 1. Conservation checks on verified auxiliary artifacts
    universe_snap = verified_market.auxiliary_artifacts["historical_universe_snapshot_20250115.json"]
    all_syms = universe_snap["census_878_all_usdt_perpetual_symbols"]
    active_syms = universe_snap["census_380_active_usdt_perpetuals"]
    inactive_syms = universe_snap["census_498_inactive_or_unlisted_perpetuals"]
    assert len(all_syms) == 878
    assert len(active_syms) == 380
    assert len(inactive_syms) == 498
    assert len(active_syms) + len(inactive_syms) == 878

    prov = verified_market.auxiliary_artifacts["historical_control_candidates_baseline_provenance_reef_20250115.json"]
    candidates = prov["candidates"]
    assert len(candidates) == 365
    assert 380 - 15 == 365

    qualified_candidates = [c for c in candidates if c["decision"] == "qualified"]
    rejected_candidates = [c for c in candidates if c["decision"] != "qualified"]
    assert len(qualified_candidates) == 120
    assert len(rejected_candidates) == 245
    assert len(qualified_candidates) + len(rejected_candidates) == 365

    # 2. Match evaluation on REEF auxiliary data
    ctrl_eval = verified_market.auxiliary_artifacts["historical_control_universe_reef_20250115.json"]
    top_3 = ctrl_eval["top_qualified_controls"]
    assert [c["symbol"] for c in top_3] == ["AXLUSDT", "AKTUSDT", "REZUSDT"]
    assert top_3[0]["matching_distance"] == pytest.approx(0.0096, abs=1e-4)
    assert top_3[1]["matching_distance"] == pytest.approx(0.0377, abs=1e-4)
    assert top_3[2]["matching_distance"] == pytest.approx(0.0709, abs=1e-4)


def test_pure_matcher_boundary_matrix():
    event_vol = 0.05
    event_volm = 100000.0

    # 1. Zero candidates -> unmatched
    res_zero = match_control_candidates(event_vol, event_volm, [])
    assert res_zero["match_status"] == "unmatched"
    assert len(res_zero["selected_controls"]) == 0

    # 2. One candidate passing -> weight 1.0
    cand1 = {"symbol": "SYM1USDT", "volatility": 0.05, "median_quote_volume": 100000.0, "is_valid": True}
    res_one = match_control_candidates(event_vol, event_volm, [cand1])
    assert res_one["match_status"] == "matched"
    assert len(res_one["selected_controls"]) == 1
    assert res_one["selected_controls"][0]["weight"] == 1.0

    # 3. Three candidates -> three equal weights 1/3
    cand2 = {"symbol": "SYM2USDT", "volatility": 0.06, "median_quote_volume": 120000.0, "is_valid": True}
    cand3 = {"symbol": "SYM3USDT", "volatility": 0.04, "median_quote_volume": 80000.0, "is_valid": True}
    res_three = match_control_candidates(event_vol, event_volm, [cand1, cand2, cand3])
    assert len(res_three["selected_controls"]) == 3
    for c in res_three["selected_controls"]:
        assert c["weight"] == pytest.approx(1.0 / 3.0)

    # 4. Four candidates -> only top 3 selected
    cand4 = {"symbol": "SYM4USDT", "volatility": 0.08, "median_quote_volume": 180000.0, "is_valid": True}
    res_four = match_control_candidates(event_vol, event_volm, [cand1, cand2, cand3, cand4])
    assert len(res_four["selected_controls"]) == 3

    # 5. Ratios exactly 0.5 and 2.0 accepted; just outside rejected
    cand_min = {"symbol": "MINUSDT", "volatility": 0.025, "median_quote_volume": 50000.0, "is_valid": True}
    res_min = match_control_candidates(event_vol, event_volm, [cand_min])
    assert len(res_min["selected_controls"]) == 1

    cand_max = {"symbol": "MAXUSDT", "volatility": 0.10, "median_quote_volume": 200000.0, "is_valid": True}
    res_max = match_control_candidates(event_vol, event_volm, [cand_max])
    assert len(res_max["selected_controls"]) == 1

    cand_below = {"symbol": "BELOWUSDT", "volatility": 0.0249, "median_quote_volume": 50000.0, "is_valid": True}
    res_below = match_control_candidates(event_vol, event_volm, [cand_below])
    assert len(res_below["selected_controls"]) == 0

    cand_above = {"symbol": "ABOVEUSDT", "volatility": 0.1001, "median_quote_volume": 200000.0, "is_valid": True}
    res_above = match_control_candidates(event_vol, event_volm, [cand_above])
    assert len(res_above["selected_controls"]) == 0

    # 6. Tie-breaking by canonical symbol alphabetically
    cand_tie_b = {"symbol": "B_USDT", "volatility": 0.05, "median_quote_volume": 100000.0, "is_valid": True}
    cand_tie_a = {"symbol": "A_USDT", "volatility": 0.05, "median_quote_volume": 100000.0, "is_valid": True}
    res_tie = match_control_candidates(event_vol, event_volm, [cand_tie_b, cand_tie_a])
    assert [c["symbol"] for c in res_tie["selected_controls"]] == ["A_USDT", "B_USDT"]

    # 7. Permutation invariance
    res_perm1 = match_control_candidates(event_vol, event_volm, [cand1, cand2, cand3])
    res_perm2 = match_control_candidates(event_vol, event_volm, [cand3, cand1, cand2])
    assert [c["symbol"] for c in res_perm1["selected_controls"]] == [c["symbol"] for c in res_perm2["selected_controls"]]

    # 8. Invalid candidate (missing bar, zero volatility, zero volume) rejected
    cand_bad1 = {"symbol": "BAD1", "volatility": 0.0, "median_quote_volume": 100000.0, "is_valid": True}
    assert len(match_control_candidates(event_vol, event_volm, [cand_bad1])["selected_controls"]) == 0

    cand_bad2 = {"symbol": "BAD2", "volatility": 0.05, "median_quote_volume": 0.0, "is_valid": True}
    assert len(match_control_candidates(event_vol, event_volm, [cand_bad2])["selected_controls"]) == 0

    cand_bad3 = {"symbol": "BAD3", "volatility": 0.05, "median_quote_volume": 100000.0, "is_valid": False}
    assert len(match_control_candidates(event_vol, event_volm, [cand_bad3])["selected_controls"]) == 0


def test_settlement_rule_mapping(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified_market = verify_market_evidence(pkg_dir)
    rule_mapping = verified_market.auxiliary_artifacts["settlement_rule_mapping_37contracts.json"]

    # Event before 2024-11-11 boundary (1731312000000 ms) selects V1
    rule_v1 = resolve_settlement_rule(
        symbol="BTCUSDT",
        event_time_ms=1720000000000,
        rule_mapping_data=rule_mapping,
    )
    assert rule_v1["rule_version"] == "V1"
    assert rule_v1["sample_interval_seconds"] == 1
    assert rule_v1["sample_window_minutes"] == 30
    assert rule_v1["expected_sample_count"] == 1800

    # Event after boundary (e.g. REEF on 2025-01-15) selects V2
    rule_v2 = resolve_settlement_rule(
        symbol="REEFUSDT",
        event_time_ms=1736928006723,
        rule_mapping_data=rule_mapping,
    )
    assert rule_v2["rule_version"] == "V2"
    assert rule_v2["sample_interval_seconds"] == 1
    assert rule_v2["sample_window_minutes"] == 60
    assert rule_v2["expected_sample_count"] == 3600


def test_window_intervals_and_truncation():
    # 1. Normal non-truncated window
    # Tpub = 1736928000000 (2025-01-15 08:00:00), Tsettle = 1737536400000 (2025-01-22 09:00:00)
    w_norm = compute_window_intervals(t_pub_ms=1736928000000, t_settle_ms=1737536400000)
    assert w_norm["w1_start_ms"] == 1736928000000
    assert w_norm["w1_end_ms"] == 1736928000000 + 12 * 3600000
    assert w_norm["is_truncated_by_tpub"] is False
    assert w_norm["nominal_w2_start_ms"] == 1737536400000 - 24 * 3600000
    assert w_norm["paired_w2_start_ms"] == w_norm["nominal_w2_start_ms"]

    # 2. Truncated W2 by Tpub (like AIA / PORT3 where Tpub was only ~30 min before settlement)
    # Tpub = 1737534600000 (30 min before Tsettle)
    w_trunc = compute_window_intervals(t_pub_ms=1737534600000, t_settle_ms=1737536400000)
    assert w_trunc["is_truncated_by_tpub"] is True
    assert w_trunc["truncation_reason"] == "t_pub_after_nominal_w2_start"
    assert w_trunc["paired_w2_start_ms"] == 1737534600000
    assert w_trunc["paired_w2_end_ms"] == 1737536400000

    # 3. Abnormal: Tsettlement <= Tpub
    w_abnorm = compute_window_intervals(t_pub_ms=1737536400000, t_settle_ms=1737536400000)
    assert w_abnorm["is_truncated_by_tpub"] is True
    assert w_abnorm["truncation_reason"] == "settlement_before_or_at_publication"
    assert w_abnorm["paired_w2_start_ms"] is None


def test_parent_inv_f09_announcement_and_contract_grouping(tmp_path: Path):
    project_root, completed_root, source_export = build_valid_completed_c_root(tmp_path)
    verified_c = verify_c_input(project_root, completed_root, source_export)
    denominator = reconstruct_denominator(verified_c)

    parent_ids = {row.parent_article_id for row in denominator}
    contract_ids = {row.contract_id for row in denominator}

    # Verify announcement count and contract row count are reported separately
    assert len(parent_ids) > 0
    assert len(contract_ids) >= len(parent_ids)


def test_descriptive_reducers_on_real_reef_evidence(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified_market = verify_market_evidence(pkg_dir)

    t_pub_ms = 1736928006723
    t_settle_ms = 1737536400000
    selected_controls = ["AXLUSDT", "AKTUSDT", "REZUSDT"]

    results = compute_descriptive_metrics(
        symbol="REEFUSDT",
        t_pub_ms=t_pub_ms,
        t_settle_ms=t_settle_ms,
        selected_controls=selected_controls,
        verified_market=verified_market,
    )

    assert isinstance(results, list)
    metric_map = {r.metric_name: r for r in results}

    # 1. Price path
    assert "price_path" in metric_map
    r_price = metric_map["price_path"]
    assert r_price.status in ("descriptive_only", "price_path_unavailable")

    # 2. Basis
    assert "basis" in metric_map
    r_basis = metric_map["basis"]
    assert r_basis.status in ("descriptive_only", "basis_unavailable")

    # 3. Mark basis
    assert "mark_basis" in metric_map
    r_mark = metric_map["mark_basis"]
    assert r_mark.status in ("descriptive_only", "mark_basis_unavailable")

    # 4. Funding
    assert "funding" in metric_map
    r_fund = metric_map["funding"]
    assert r_fund.status in ("descriptive_only", "funding_unavailable")

    # 5. OI
    assert "open_interest" in metric_map
    r_oi = metric_map["open_interest"]
    assert r_oi.status in ("descriptive_only", "oi_unavailable")

    # 6. Visible depth
    assert "visible_depth" in metric_map
    r_depth = metric_map["visible_depth"]
    assert r_depth.status in ("descriptive_only", "visible_depth_unavailable")

    # 7. Agg trades
    assert "agg_trades" in metric_map
    r_trades = metric_map["agg_trades"]
    assert r_trades.status in ("descriptive_only", "agg_trade_unavailable")

    # 8. Settlement mechanism
    assert "settlement_mechanism" in metric_map
    r_settle = metric_map["settlement_mechanism"]
    assert r_settle.status == "settlement_value_unavailable_insufficient_1s_index"


def test_semantic_boundary_prohibitions(tmp_path: Path):
    pkg_dir = copy_market_evidence_package(tmp_path)
    verified_market = verify_market_evidence(pkg_dir)

    results = compute_descriptive_metrics(
        symbol="REEFUSDT",
        t_pub_ms=1736928006723,
        t_settle_ms=1737536400000,
        selected_controls=["AXLUSDT", "AKTUSDT", "REZUSDT"],
        verified_market=verified_market,
    )

    for r in results:
        # No alpha or PnL or slippage or execution claims
        assert "pnl" not in r.descriptors
        assert "carry_pnl" not in r.descriptors
        assert "spread" not in r.descriptors
        assert "slippage" not in r.descriptors
        assert "tradable_price" not in r.descriptors or r.metric_name == "price_path"
        # All permission flags must be False
        for flag, val in ALL_PERMISSION_FLAGS_FALSE.items():
            assert r.authority_flags[flag] is False
