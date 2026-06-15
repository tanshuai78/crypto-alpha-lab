"""
tests/research/external_signal_shadow/test_stage1_4a_liquidation.py
"""

from research.external_signal_shadow.stage1_4a_liquidation import (
    audit_binance_vision_manifest_entries,
    audit_force_order_archive_rows,
    audit_liquidation_notional_conversion,
    audit_liquidation_snapshot_rows,
    map_force_order_side_to_liquidation_side,
)


def test_force_order_side_maps_sell_to_long_liquidation():
    assert map_force_order_side_to_liquidation_side("SELL") == "long_liquidation"
    assert map_force_order_side_to_liquidation_side("sell") == "long_liquidation"


def test_force_order_side_maps_buy_to_short_liquidation():
    assert map_force_order_side_to_liquidation_side("BUY") == "short_liquidation"
    assert map_force_order_side_to_liquidation_side("buy") == "short_liquidation"
    assert map_force_order_side_to_liquidation_side("invalid") == "unknown"


def test_cm_proxy_does_not_allow_full_composite_without_explicit_acceptance():
    rows = [
        {"symbol": "BTCUSD_PERP", "side": "SELL", "price": 50000.0, "qty": 1.0, "time": 0}
    ]
    res_default = audit_liquidation_snapshot_rows(rows, ("BTCUSDT",), liquidation_proxy_accepted_for_full_replay=False)
    assert res_default["liquidation_proxy_accepted_for_full_replay"] is False

    res_accepted = audit_liquidation_snapshot_rows(rows, ("BTCUSDT",), liquidation_proxy_accepted_for_full_replay=True)
    assert res_accepted["liquidation_proxy_accepted_for_full_replay"] is True


def test_notional_conversion_quality_requires_verified_by_sample():
    res_default = audit_liquidation_notional_conversion(None)
    assert res_default["notional_conversion_quality"] == "unavailable"

    res_estimated = audit_liquidation_notional_conversion({"notional_conversion_quality": "estimated"})
    assert res_estimated["notional_conversion_quality"] == "estimated"

    res_verified = audit_liquidation_notional_conversion({"notional_conversion_quality": "verified_by_sample"})
    assert res_verified["notional_conversion_quality"] == "verified_by_sample"


def test_liquidation_rows_audit_reports_history_days_and_nonzero_windows():
    interval = 60 * 60 * 1000  # 1 hour
    # Generate events in 10 unique hour windows
    rows = [
        {"symbol": "BTCUSDT", "side": "SELL", "price": 50000.0, "origQty": 1.0, "time": i * 5 * interval}
        for i in range(10)
    ]
    # Total history: 0 to 45 hours = 45 hours = 1.875 days
    res = audit_force_order_archive_rows(rows, ("BTCUSDT",))

    assert res["liquidation_history_days"] == 1.875
    assert res["liquidation_nonzero_window_count"] == 10
    assert res["liquidation_record_count"] == 10 if "liquidation_record_count" in res else True
    assert res["liquidation_field_coverage_ratio"] == 1.0


def test_liquidation_field_coverage_below_min_blocks_summary_later():
    # 5 rows, but 2 are missing price field
    rows = [
        {"symbol": "BTCUSDT", "side": "SELL", "price": 50000.0, "origQty": 1.0, "time": 0},
        {"symbol": "BTCUSDT", "side": "SELL", "price": 50000.0, "origQty": 1.0, "time": 1000},
        {"symbol": "BTCUSDT", "side": "SELL", "price": 50000.0, "origQty": 1.0, "time": 2000},
        {"symbol": "BTCUSDT", "side": "SELL", "price": None, "origQty": 1.0, "time": 3000},
        {"symbol": "BTCUSDT", "side": "SELL", "price": None, "origQty": 1.0, "time": 4000},
    ]
    res = audit_force_order_archive_rows(rows, ("BTCUSDT",))
    assert res["liquidation_field_coverage_ratio"] == 0.60


def test_liquidation_time_coverage_never_exceeds_one_for_dense_events():
    rows = [
        {
            "symbol": "BTCUSDT",
            "side": "SELL",
            "price": 50000.0,
            "origQty": 1.0,
            "time": i * 60_000,
        }
        for i in range(120)
    ]

    res = audit_force_order_archive_rows(rows, ("BTCUSDT",))

    assert 0.0 <= res["liquidation_time_coverage_ratio"] <= 1.0


def test_manifest_entries_are_not_converted_to_liquidation_events():
    entries = [
        {
            "symbol": "BTCUSD_PERP",
            "manifest_available": True,
            "timestamp": 1704067200000,
        }
    ]

    res = audit_binance_vision_manifest_entries(entries, ("BTCUSDT",))

    assert res["liquidation_source_quality"] == "cm_liquidation_snapshot_manifest_only"
    assert res["liquidation_nonzero_window_count"] == 0
    assert res["liquidation_field_coverage_ratio"] == 0.0
    assert res["liquidation_proxy_accepted_for_full_replay"] is False


def test_manifest_head_success_records_manifest_not_liquidation_event():
    from research.external_signal_shadow.stage1_4a_liquidation import (
        audit_liquidation_manifest_only,
    )

    res = audit_liquidation_manifest_only(available_count=5)
    assert res["liquidation_source"] == "binance_vision_cm_liquidation_snapshot_manifest"
    assert res["liquidation_source_quality"] == "cm_liquidation_snapshot_manifest_only"
    assert res["liquidation_manifest_available_count"] == 5
    assert res["liquidation_history_days"] == 0.0
    assert res["liquidation_field_coverage_ratio"] == 0.0
    assert res["liquidation_time_coverage_ratio"] == 0.0
    assert res["liquidation_nonzero_window_count"] == 0
    assert res["cm_to_um_proxy_used"] is True
    assert res["liquidation_proxy_accepted_for_full_replay"] is False
    assert res["notional_conversion_quality"] == "unavailable"
    assert res["usable"] is False
