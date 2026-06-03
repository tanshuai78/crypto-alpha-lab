# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from scripts.audit_route_c1_data_overlap import (
    normalize_symbol,
    compute_time_span,
    compute_overlap_hours_by_symbol,
    compute_coverage_ratio,
    compute_overlap_decision,
)


def test_normalize_symbol_matches_slash_and_non_slash_formats():
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_symbol("BTCUSDT") == "BTCUSDT"
    assert normalize_symbol("BTC/USDT:USDT") == "BTCUSDT"
    assert normalize_symbol("eth/usdt") == "ETHUSDT"


def test_compute_time_span_reports_earliest_latest_and_hours():
    rows = [
        {"timestamp_ms": 1700000000000},  # Min
        {"timestamp_ms": 1700003600000},  # Max (1 hour later)
        {"timestamp_ms": 1700001800000},
    ]
    earliest, latest, hours = compute_time_span(rows, "timestamp_ms")
    assert earliest == 1700000000000
    assert latest == 1700003600000
    assert hours == 1.0

    # Test empty input
    assert compute_time_span([], "timestamp_ms") == (None, None, 0.0)


def test_compute_symbol_overlap_hours_intersects_liquidation_price_and_orderbook():
    # Intersection of:
    # liq: [100, 200]
    # price: [120, 250]
    # ob: [90, 180]
    # Intersects to [120, 180] -> length 60 -> 60 ms? Usually spans are (start, end)
    # Let's say inputs are spans: tuple[int, int]
    liq_spans = {"BTCUSDT": (1000, 2000)}
    price_spans = {"BTCUSDT": (1200, 2500)}
    ob_spans = {"BTCUSDT": (900, 1800)}

    overlap = compute_overlap_hours_by_symbol(liq_spans, price_spans, ob_spans)
    # [1200, 1800] is length 600 ms -> 600 / 3_600_000 hours
    assert overlap["BTCUSDT"] == pytest.approx(600 / 3600000.0)


def test_compute_coverage_ratio():
    # 3 expected minutes, 2 present
    rows = [{"timestamp_ms": 1000}, {"timestamp_ms": 2000}]
    ratio = compute_coverage_ratio(rows, expected_minutes=3)
    assert ratio == pytest.approx(2.0 / 3.0)

    # Empty rows
    assert compute_coverage_ratio([], expected_minutes=10) == 0.0


def test_overlap_audit_marks_price_only_ready_without_orderbook():
    summary = {
        "mode": "live_overlap",
        "liquidation_input_exists": True,
        "price_input_exists": True,
        "orderbook_dir_exists": False,
        "primary_blocker": None,
        "liquidation_1m_zero_fill_coverage_24h": 0.98,
        "price_1m_coverage_24h": 0.99,
        "orderbook_snapshot_coverage_24h": 0.0,
        "overlap_hours_by_symbol": {"BTCUSDT": 168.0, "ETHUSDT": 168.0},
        "ready_for_price_only": False,  # decision function will set this
        "ready_for_orderbook_aware": False,
        "decision": None,
    }
    updated = compute_overlap_decision(summary)
    assert updated["ready_for_price_only"] is True
    assert updated["ready_for_orderbook_aware"] is False
    assert updated["decision"] == "route_c1_overlap_ready_for_price_only"


def test_overlap_audit_marks_orderbook_aware_true_when_orderbook_coverage_passes():
    summary = {
        "mode": "live_overlap",
        "liquidation_input_exists": True,
        "price_input_exists": True,
        "orderbook_dir_exists": True,
        "primary_blocker": None,
        "liquidation_1m_zero_fill_coverage_24h": 0.98,
        "price_1m_coverage_24h": 0.99,
        "orderbook_snapshot_coverage_24h": 0.85,
        "overlap_hours_by_symbol": {"BTCUSDT": 168.0, "ETHUSDT": 168.0, "SOLUSDT": 10.0},
        "ready_for_price_only": False,
        "ready_for_orderbook_aware": False,
        "decision": None,
    }
    updated = compute_overlap_decision(summary)
    assert updated["ready_for_price_only"] is True
    assert updated["ready_for_orderbook_aware"] is True
    assert updated["decision"] == "route_c1_overlap_ready_for_orderbook_aware"


def test_overlap_decision_requires_coverage_thresholds():
    summary = {
        "mode": "live_overlap",
        "liquidation_input_exists": True,
        "price_input_exists": True,
        "orderbook_dir_exists": True,
        "primary_blocker": None,
        "liquidation_1m_zero_fill_coverage_24h": 0.90,  # too low? Wait, liquidation coverage isn't price coverage
        "price_1m_coverage_24h": 0.90,  # Price coverage < 0.95 -> not ready for price only
        "orderbook_snapshot_coverage_24h": 0.85,
        "overlap_hours_by_symbol": {"BTCUSDT": 168.0, "ETHUSDT": 168.0},
        "ready_for_price_only": False,
        "ready_for_orderbook_aware": False,
        "decision": None,
    }
    updated = compute_overlap_decision(summary)
    assert updated["ready_for_price_only"] is False
    assert updated["decision"] == "route_c1_overlap_not_ready"


def test_overlap_audit_reports_missing_liquidation_input_blocker():
    summary = {
        "mode": "live_overlap",
        "liquidation_input_exists": False,
        "price_input_exists": True,
        "orderbook_dir_exists": True,
        "primary_blocker": None,
        "liquidation_1m_zero_fill_coverage_24h": 0.0,
        "price_1m_coverage_24h": 0.99,
        "orderbook_snapshot_coverage_24h": 0.85,
        "overlap_hours_by_symbol": {},
        "ready_for_price_only": False,
        "ready_for_orderbook_aware": False,
        "decision": None,
    }
    updated = compute_overlap_decision(summary)
    assert updated["primary_blocker"] == "missing_liquidation_1m_input"
    assert updated["decision"] == "route_c1_overlap_not_ready"
