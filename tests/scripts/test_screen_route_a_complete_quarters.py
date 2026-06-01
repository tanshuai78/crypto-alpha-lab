"""
Tests for screen_route_a_complete_quarters.py

Focuses on quarter-level gate aggregation and final decision logic.
No network or subprocess I/O in these unit tests.
"""

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent
    / "scripts"
    / "screen_route_a_complete_quarters.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "screen_route_a_complete_quarters", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _month_result(
    *,
    price_coverage_ratio: float = 1.0,
    price_max_gap_minutes: int = 0,
    price_rows: int = 44_640,
    liquidation_files_found: int = 31,
    liquidation_files_expected: int = 31,
    liquidation_file_coverage_ratio: float = 1.0,
    passes_continuity_gate: bool = True,
) -> dict:
    return {
        "price_coverage_ratio": price_coverage_ratio,
        "price_max_gap_minutes": price_max_gap_minutes,
        "price_rows": price_rows,
        "liquidation_files_found": liquidation_files_found,
        "liquidation_files_expected": liquidation_files_expected,
        "liquidation_file_coverage_ratio": liquidation_file_coverage_ratio,
        "passes_continuity_gate": passes_continuity_gate,
    }


def _continuity_results(months: list[str]) -> dict:
    return {
        "BTCUSDT": {m: _month_result() for m in months},
        "ETHUSDT": {m: _month_result() for m in months},
        "SOLUSDT": {m: _month_result() for m in months},
    }


def _density(months: list[str]) -> dict:
    return {
        "total_events": 240,
        "events_per_month": {m: 80 for m in months},
        "events_by_symbol": {
            "BTCUSDT": 100,
            "ETHUSDT": 80,
            "SOLUSDT": 60,
        },
        "events_by_side": {"long": 120, "short": 120},
        "events_by_symbol_month": {
            "BTCUSDT": {months[0]: 34, months[1]: 33, months[2]: 33},
            "ETHUSDT": {months[0]: 27, months[1]: 27, months[2]: 26},
            "SOLUSDT": {months[0]: 19, months[1]: 20, months[2]: 21},
        },
        "events_by_symbol_side": {
            "BTCUSDT": {"long": 50, "short": 50},
            "ETHUSDT": {"long": 40, "short": 40},
            "SOLUSDT": {"long": 30, "short": 30},
        },
    }


def test_module_exports_quarter_helpers():
    mod = _load_module()
    assert hasattr(mod, "quarter_to_months")
    assert hasattr(mod, "evaluate_quarter")
    assert hasattr(mod, "compute_screening_decision")


def test_quarter_to_months_returns_natural_quarter():
    mod = _load_module()
    assert mod.quarter_to_months("2023-Q2") == ["2023-04", "2023-05", "2023-06"]
    assert mod.quarter_to_months("2024-Q1") == ["2024-01", "2024-02", "2024-03"]


def test_evaluate_quarter_passes_when_all_gates_clear():
    mod = _load_module()
    months = ["2023-10", "2023-11", "2023-12"]
    result = mod.evaluate_quarter(
        quarter="2023-Q4",
        required_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        months=months,
        continuity_results=_continuity_results(months),
        density=_density(months),
        min_total_events=120,
        min_events_per_month=25,
        min_events_per_symbol=20,
    )
    assert result["available_symbol_months"] == 9
    assert result["price_continuity_pass_symbol_months"] == 9
    assert result["liq_file_pass_symbol_months"] == 9
    assert result["quarter_universe_integrity_ok"] is True
    assert result["event_density_ok"] is True
    assert result["passes_screening"] is True


def test_evaluate_quarter_fails_when_one_symbol_month_breaks_continuity():
    mod = _load_module()
    months = ["2024-01", "2024-02", "2024-03"]
    continuity = _continuity_results(months)
    continuity["SOLUSDT"]["2024-02"] = _month_result(
        liquidation_files_found=28,
        liquidation_files_expected=29,
        liquidation_file_coverage_ratio=28 / 29,
        passes_continuity_gate=False,
    )

    result = mod.evaluate_quarter(
        quarter="2024-Q1",
        required_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        months=months,
        continuity_results=continuity,
        density=_density(months),
        min_total_events=120,
        min_events_per_month=25,
        min_events_per_symbol=20,
    )
    assert result["liq_file_pass_symbol_months"] == 8
    assert result["quarter_universe_integrity_ok"] is False
    assert result["passes_screening"] is False
    assert "universe_integrity_failed" in result["fail_reasons"]


def test_evaluate_quarter_fails_when_density_too_sparse_for_one_month():
    mod = _load_module()
    months = ["2023-07", "2023-08", "2023-09"]
    density = _density(months)
    density["events_per_month"]["2023-08"] = 12

    result = mod.evaluate_quarter(
        quarter="2023-Q3",
        required_symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        months=months,
        continuity_results=_continuity_results(months),
        density=density,
        min_total_events=120,
        min_events_per_month=25,
        min_events_per_symbol=20,
    )
    assert result["event_density_ok"] is False
    assert result["passes_screening"] is False
    assert "monthly_event_density_failed" in result["fail_reasons"]


def test_compute_screening_decision_returns_found_when_any_quarter_passes():
    mod = _load_module()
    quarter_results = [
        {
            "quarter": "2023-Q1",
            "passes_screening": False,
            "total_events": 180,
            "available_symbol_months": 8,
        },
        {
            "quarter": "2023-Q4",
            "passes_screening": True,
            "total_events": 240,
            "available_symbol_months": 9,
        },
    ]
    result = mod.compute_screening_decision(quarter_results)
    assert result["decision"] == "route_a_quarter_found"
    assert result["selected_quarter"] == "2023-Q4"


def test_compute_screening_decision_prefers_more_complete_then_more_dense_quarter():
    mod = _load_module()
    quarter_results = [
        {
            "quarter": "2023-Q2",
            "passes_screening": True,
            "total_events": 260,
            "available_symbol_months": 8,
        },
        {
            "quarter": "2023-Q3",
            "passes_screening": True,
            "total_events": 220,
            "available_symbol_months": 9,
        },
        {
            "quarter": "2023-Q4",
            "passes_screening": True,
            "total_events": 240,
            "available_symbol_months": 9,
        },
    ]
    result = mod.compute_screening_decision(quarter_results)
    assert result["selected_quarter"] == "2023-Q4"


def test_compute_screening_decision_returns_not_found_when_all_fail():
    mod = _load_module()
    quarter_results = [
        {"quarter": "2023-Q1", "passes_screening": False, "total_events": 180, "available_symbol_months": 8},
        {"quarter": "2023-Q2", "passes_screening": False, "total_events": 90, "available_symbol_months": 9},
    ]
    result = mod.compute_screening_decision(quarter_results)
    assert result["decision"] == "route_a_quarter_not_found"
    assert result["selected_quarter"] is None


def test_build_quarter_density_summary_derives_month_from_shock_bar_start_ms(tmp_path):
    mod = _load_module()
    jan_start = 1_672_531_200_000  # 2023-01-01 00:00:00 UTC
    feb_start = 1_675_209_600_000  # 2023-02-01 00:00:00 UTC
    months = ["2023-01", "2023-02", "2023-03"]

    continuity_summary = {
        "results": {
            "BTCUSDT": {
                "2023-01": {"passes_continuity_gate": True},
                "2023-02": {"passes_continuity_gate": True},
                "2023-03": {"passes_continuity_gate": False},
            }
        }
    }

    (tmp_path / "klines" / "BTCUSDT" / "2023-01").mkdir(parents=True)
    (tmp_path / "klines" / "BTCUSDT" / "2023-02").mkdir(parents=True)
    (tmp_path / "liquidationSnapshot" / "BTCUSDT" / "2023-01").mkdir(parents=True)
    (tmp_path / "liquidationSnapshot" / "BTCUSDT" / "2023-02").mkdir(parents=True)

    mod._load_kline_rows_from_dir = lambda _: []
    mod._load_liq_rows_from_dir = lambda _: []
    mod.dataset_mod.build_dataset = lambda symbol, month_data, passed_months: [
        {"symbol": symbol, "bar_start_ms": jan_start},
        {"symbol": symbol, "bar_start_ms": feb_start},
    ]
    mod.review_mod.detect_shocks_with_gap_resets = lambda rows: [
        SimpleNamespace(
            symbol="BTCUSDT",
            shock_bar_start_ms=jan_start,
            dominant_liquidation_side="long",
            shock_notional_usdt=1_000_000.0,
        ),
        SimpleNamespace(
            symbol="BTCUSDT",
            shock_bar_start_ms=feb_start,
            dominant_liquidation_side="short",
            shock_notional_usdt=2_000_000.0,
        ),
    ]
    mod.deduplicate_events = lambda events: events

    density = mod.build_quarter_density_summary(
        extracted_dir=tmp_path,
        continuity_summary=continuity_summary,
        symbols=["BTCUSDT"],
        months=months,
    )
    assert density["events_per_month"]["2023-01"] == 1
    assert density["events_per_month"]["2023-02"] == 1
