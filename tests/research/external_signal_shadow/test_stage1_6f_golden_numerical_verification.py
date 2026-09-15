"""
Stage 1.6F Current Numerical Snapshot Regression Test.

Permanently detects a change from the current REEFUSDT W1 descriptive reducer snapshot,
using the frozen local evidence package and one deterministic pytest.
"""

import hashlib
import math
from pathlib import Path

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    compute_descriptive_metrics,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_market_evidence,
)
from tests.research.external_signal_shadow.stage1_6f_historical_diagnostic_test_support import (
    copy_market_evidence_package,
)

FROZEN_MANIFEST_SHA256 = (
    "9e44b24d935c3b3165911ef651b8ade174edefc2e6d9b696e1e23f3d6c260c5f"
)

EXPECTED_DEPTH = {
    "pct_-5": (1440, 283079.160823, 333617.024617, 385648.745531),
    "pct_-4": (1440, 217558.967351, 291654.601869, 335300.052711),
    "pct_-3": (1440, 160876.386087, 243766.42073, 282177.560653),
    "pct_-2": (1440, 131484.899513, 170901.85691, 221390.282449),
    "pct_-1": (1440, 44193.649303, 90257.400987, 106993.138865),
    "pct_1": (1440, 37278.942028, 89126.22403, 93751.537525),
    "pct_2": (1440, 147053.596677, 154025.329339, 184400.194495),
    "pct_3": (1440, 199796.067384, 186170.381003, 220761.744244),
    "pct_4": (1440, 234731.576448, 192858.088739, 243415.06369),
    "pct_5": (1440, 245215.602344, 222972.328403, 262599.015962),
}


def _assert_close(actual: float, expected: float, field_name: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
        raise AssertionError(
            f"Snapshot regression for {field_name}: expected {expected}, got {actual}"
        )


def test_reef_w1_descriptive_metrics_match_current_snapshot_values(tmp_path: Path) -> None:
    # 1. Copy fixture to tmp_path and verify manifest hash
    pkg_dir = copy_market_evidence_package(tmp_path)
    manifest_path = pkg_dir / "gap02_evidence_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    assert manifest_sha256 == FROZEN_MANIFEST_SHA256

    verified_market = verify_market_evidence(pkg_dir)
    assert verified_market.manifest_sha256 == FROZEN_MANIFEST_SHA256

    # 2. Call reducer with exact Section 3.1 inputs
    results = compute_descriptive_metrics(
        symbol="REEFUSDT",
        t_pub_ms=1736928006723,
        t_settle_ms=1737536400000,
        selected_controls=["AXLUSDT", "AKTUSDT", "REZUSDT"],
        verified_market=verified_market,
    )

    # 3. Assert eight exact metric names and uniqueness
    expected_metric_names = {
        "price_path",
        "basis",
        "mark_basis",
        "funding",
        "open_interest",
        "visible_depth",
        "agg_trades",
        "settlement_mechanism",
    }
    assert len(results) == 8
    actual_names = [r.metric_name for r in results]
    assert set(actual_names) == expected_metric_names
    assert len(set(actual_names)) == len(actual_names)

    metric_map = {r.metric_name: r for r in results}

    # 4. Assert authority flags and absence of forbidden fields
    for r in results:
        assert r.authority_flags == ALL_PERMISSION_FLAGS_FALSE
        for _flag_name, flag_val in r.authority_flags.items():
            assert flag_val is False
        for forbidden_key in ("alpha", "pnl", "carry_pnl", "slippage"):
            assert forbidden_key not in r.descriptors
        if r.metric_name != "price_path":
            assert "tradable_price" not in r.descriptors

    # 5. Metric 1: price_path
    r_price = metric_map["price_path"]
    assert r_price.status == "descriptive_only"
    assert r_price.observed_interval == {
        "w1_start_ms": 1736928006723,
        "w1_end_ms": 1736971206723,
        "first_observed_at_ms": 1736931600000,
        "last_observed_at_ms": 1736971200000,
        "bar_count": 12,
    }
    _assert_close(r_price.descriptors["first_close"], 0.000828, "price_path.first_close")
    _assert_close(r_price.descriptors["last_close"], 0.001018, "price_path.last_close")
    _assert_close(
        r_price.descriptors["price_change_bps"],
        2294.6859903381655,
        "price_path.price_change_bps",
    )
    _assert_close(
        r_price.descriptors["event_minus_control_bps"],
        1441.6271512850253,
        "price_path.event_minus_control_bps",
    )
    assert r_price.descriptors["paired_diff_censored"] is False

    # 6. Metric 2: basis
    r_basis = metric_map["basis"]
    assert r_basis.status == "descriptive_only"
    assert r_basis.observed_interval == {"bar_count": 12}
    _assert_close(r_basis.descriptors["first_basis_bps"], -119.331742243437, "basis.first_basis_bps")
    _assert_close(r_basis.descriptors["last_basis_bps"], 0.0, "basis.last_basis_bps")
    _assert_close(r_basis.descriptors["median_basis_bps"], 0.0, "basis.median_basis_bps")

    # 7. Metric 3: mark_basis
    r_mark = metric_map["mark_basis"]
    assert r_mark.status == "descriptive_only"
    assert r_mark.observed_interval == {"bar_count": 12}
    _assert_close(r_mark.descriptors["first_mark_basis_bps"], -37.82816229117025, "mark_basis.first_mark_basis_bps")
    _assert_close(r_mark.descriptors["last_mark_basis_bps"], 9.823182711197198, "mark_basis.last_mark_basis_bps")
    _assert_close(r_mark.descriptors["median_mark_basis_bps"], 0.0, "mark_basis.median_mark_basis_bps")
    assert r_mark.descriptors["note"] == "non_tradable_risk_price_basis_only"

    # 8. Metric 4: funding
    r_fund = metric_map["funding"]
    assert r_fund.status == "descriptive_only"
    assert r_fund.observed_interval == {"observation_count": 3}
    assert r_fund.descriptors["count"] == 3
    assert r_fund.descriptors["funding_observations"] == [
        (1736942400000, 4, -0.00464199),
        (1736956800000, 4, -0.0006037),
        (1736971200000, 4, 0.00005),
    ]

    # 9. Metric 5: open_interest
    r_oi = metric_map["open_interest"]
    assert r_oi.status == "descriptive_only"
    assert r_oi.observed_interval == {"bar_count": 144}
    _assert_close(r_oi.descriptors["first_oi_value"], 5880098.4449056, "open_interest.first_oi_value")
    _assert_close(r_oi.descriptors["last_oi_value"], 5687841.42686945, "open_interest.last_oi_value")
    _assert_close(r_oi.descriptors["delta_oi_value"], -192257.01803614944, "open_interest.delta_oi_value")
    _assert_close(
        r_oi.descriptors["latest_toptrader_long_short_ratio"],
        0.918348,
        "open_interest.latest_toptrader_long_short_ratio",
    )

    # 10. Metric 6: visible_depth
    r_depth = metric_map["visible_depth"]
    assert r_depth.status == "descriptive_only"
    assert r_depth.observed_interval == {"snapshot_count": 14400}
    assert r_depth.descriptors["note"] == "visible_discrete_depth_ladder_proxy_only_no_slippage"
    levels = r_depth.descriptors["percentage_levels"]
    assert set(levels.keys()) == set(EXPECTED_DEPTH.keys())
    for pct_key, (exp_count, exp_first, exp_last, exp_med) in EXPECTED_DEPTH.items():
        entry = levels[pct_key]
        assert entry["count"] == exp_count
        _assert_close(entry["first_notional"], exp_first, f"visible_depth.{pct_key}.first_notional")
        _assert_close(entry["last_notional"], exp_last, f"visible_depth.{pct_key}.last_notional")
        _assert_close(entry["median_notional"], exp_med, f"visible_depth.{pct_key}.median_notional")

    # 11. Metric 7: agg_trades
    r_trades = metric_map["agg_trades"]
    assert r_trades.status == "descriptive_only"
    assert r_trades.observed_interval == {"trade_count": 121749}
    assert r_trades.descriptors["total_trades"] == 121749
    _assert_close(r_trades.descriptors["total_notional"], 78177015.7525911, "agg_trades.total_notional")
    assert r_trades.descriptors["buyer_maker_true_count"] == 66022
    _assert_close(
        r_trades.descriptors["buyer_maker_true_notional"],
        39228553.41463927,
        "agg_trades.buyer_maker_true_notional",
    )
    assert r_trades.descriptors["buyer_maker_false_count"] == 55727
    _assert_close(
        r_trades.descriptors["buyer_maker_false_notional"],
        38948462.33794786,
        "agg_trades.buyer_maker_false_notional",
    )

    # 12. Metric 8: settlement_mechanism
    r_settle = metric_map["settlement_mechanism"]
    assert r_settle.status == "settlement_value_unavailable_insufficient_1s_index"
    assert r_settle.observed_interval == {"sample_count": 0}
    assert r_settle.descriptors == {
        "rule_version": "V2",
        "expected_sample_count": 3600,
        "sample_interval_seconds": 1,
        "sample_window_minutes": 60,
        "note": "1h_index_is_insufficient_to_reconstruct_historical_1s_settlement_twap",
    }
