"""
tests/research/external_signal_shadow/test_stage1_4a_summary.py
"""

from research.external_signal_shadow.stage1_4a_summary import evaluate_feasibility_summary


def _create_perfect_symbol_audit(proxy_accepted=True):
    return {
        "funding": {
            "funding_record_count": 540,
            "funding_history_days": 180.0,
            "funding_field_coverage_ratio": 1.0,
            "funding_settlement_coverage_ratio": 1.0,
            "usable": True,
        },
        "oi": {
            "oi_record_count": 4320,
            "oi_history_days": 180.0,
            "oi_field_coverage_ratio": 1.0,
            "oi_time_coverage_ratio": 1.0,
            "oi_blocks_full_composite": False,
            "usable": True,
        },
        "liquidation": {
            "liquidation_source_quality": "force_order_archive",
            "liquidation_history_days": 180.0,
            "liquidation_field_coverage_ratio": 1.0,
            "liquidation_time_coverage_ratio": 1.0,
            "liquidation_nonzero_window_count": 500,
            "cm_to_um_proxy_used": False,
            "liquidation_proxy_accepted_for_full_replay": proxy_accepted,
            "notional_conversion_required": False,
            "notional_conversion_quality": "verified_by_sample",
        },
        "price": {
            "price_history_days": 180.0,
            "price_bar_count": 17280,
            "price_bar_coverage_ratio": 1.0,
            "time_coverage_ratio": 1.0,
        },
    }


def _create_perfect_preview_counts():
    return {
        "composite_overlap_window_count": 100,
        "composite_overlap_event_days": 30,
    }


def test_summary_feasible_only_when_all_sources_pass_and_proxy_accepted():
    symbol_audits = {
        "BTCUSDT": _create_perfect_symbol_audit(),
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_feasible"
    assert res["primary_blocker"] is None
    assert res["research_result_valid"] is True
    assert res["stage1_4b_candidate_replay_allowed"] is True


def test_fixture_run_is_research_result_invalid():
    symbol_audits = {
        "BTCUSDT": _create_perfect_symbol_audit(),
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    # If fixture run is True, result validity must be False
    global_metadata = {"fixture_run": True, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "fixture_smoke_only"
    assert res["research_result_valid"] is False


def test_summary_degraded_when_funding_coverage_below_min():
    bad_funding = _create_perfect_symbol_audit()
    bad_funding["funding"]["funding_settlement_coverage_ratio"] = 0.90  # below 0.95

    symbol_audits = {
        "BTCUSDT": bad_funding,
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "funding_settlement_coverage_insufficient"
    assert res["stage1_4b_candidate_replay_allowed"] is False


def test_summary_degraded_when_liquidation_coverage_below_min():
    bad_liq = _create_perfect_symbol_audit()
    bad_liq["liquidation"]["liquidation_time_coverage_ratio"] = 0.80  # below 0.90

    symbol_audits = {
        "BTCUSDT": bad_liq,
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "liquidation_time_coverage_insufficient"


def test_summary_degraded_when_price_coverage_below_min():
    bad_price = _create_perfect_symbol_audit()
    bad_price["price"]["price_bar_coverage_ratio"] = 0.90  # below 0.95

    symbol_audits = {
        "BTCUSDT": bad_price,
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "price_coverage_insufficient"


def test_summary_degraded_when_preview_overlap_below_min():
    symbol_audits = {
        "BTCUSDT": _create_perfect_symbol_audit(),
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    bad_preview = {
        "composite_overlap_window_count": 40,  # below 50
        "composite_overlap_event_days": 10,   # below 15
    }
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, bad_preview, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "insufficient_preview_density"


def test_cm_proxy_does_not_allow_full_composite_without_explicit_acceptance():
    bad_liq = _create_perfect_symbol_audit(proxy_accepted=False)
    bad_liq["liquidation"]["cm_to_um_proxy_used"] = True

    symbol_audits = {
        "BTCUSDT": bad_liq,
        "ETHUSDT": _create_perfect_symbol_audit(),
        "SOLUSDT": _create_perfect_symbol_audit(),
    }
    preview_counts = _create_perfect_preview_counts()
    global_metadata = {"fixture_run": False, "live_trading_allowed": False}

    res = evaluate_feasibility_summary(symbol_audits, preview_counts, global_metadata)
    assert res["outcome"] == "stage1_4_data_degraded"
    assert res["primary_blocker"] == "cm_proxy_unaccepted"
