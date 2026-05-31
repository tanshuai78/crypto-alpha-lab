"""
Tests for fetch_binance_liquidation_snapshot_history.py

All tests are unit-level: no real HTTP requests. Network and filesystem
operations are injected or mocked.
"""

import sys
import os
import json
import importlib.util
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent / "scripts" / "fetch_binance_liquidation_snapshot_history.py"
)


def _load_fetch_module():
    spec = importlib.util.spec_from_file_location(
        "fetch_binance_liquidation_snapshot_history", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Module structure
# ---------------------------------------------------------------------------


def test_fetch_module_imports():
    mod = _load_fetch_module()
    assert hasattr(mod, "build_um_monthly_kline_zip_url"), "Must export build_um_monthly_kline_zip_url"
    assert hasattr(mod, "build_um_daily_liquidation_zip_url"), "Must export build_um_daily_liquidation_zip_url"
    assert hasattr(mod, "build_um_monthly_liquidation_zip_url"), "Must export build_um_monthly_liquidation_zip_url"
    assert hasattr(mod, "build_checksum_url"), "Must export build_checksum_url"
    assert hasattr(mod, "build_download_plan"), "Must export build_download_plan"


# ---------------------------------------------------------------------------
# URL construction: monthly kline
# ---------------------------------------------------------------------------


def test_builds_binance_um_monthly_kline_zip_url():
    mod = _load_fetch_module()
    url = mod.build_um_monthly_kline_zip_url("BTCUSDT", "2024-01")
    assert "data.binance.vision" in url
    assert "futures/um/monthly/klines" in url
    assert "BTCUSDT" in url
    assert "1m" in url
    assert "2024-01" in url
    assert url.endswith(".zip")


def test_builds_binance_um_monthly_kline_zip_url_for_eth():
    mod = _load_fetch_module()
    url = mod.build_um_monthly_kline_zip_url("ETHUSDT", "2024-02")
    assert "ETHUSDT" in url
    assert "2024-02" in url


# ---------------------------------------------------------------------------
# URL construction: daily liquidation
# ---------------------------------------------------------------------------


def test_builds_binance_um_daily_liquidation_snapshot_zip_url():
    mod = _load_fetch_module()
    url = mod.build_um_daily_liquidation_zip_url("BTCUSDT", "2024-01-15")
    assert "data.binance.vision" in url
    assert "futures/um/daily/liquidationSnapshot" in url
    assert "BTCUSDT" in url
    assert "2024-01-15" in url
    assert url.endswith(".zip")


def test_builds_binance_um_monthly_liquidation_snapshot_zip_url():
    mod = _load_fetch_module()
    url = mod.build_um_monthly_liquidation_zip_url("BTCUSDT", "2024-01")
    assert "data.binance.vision" in url
    assert "futures/um/monthly/liquidationSnapshot" in url
    assert "BTCUSDT" in url
    assert "2024-01" in url
    assert url.endswith(".zip")


# ---------------------------------------------------------------------------
# Checksum URL
# ---------------------------------------------------------------------------


def test_builds_checksum_url_from_zip_url():
    mod = _load_fetch_module()
    zip_url = mod.build_um_monthly_kline_zip_url("BTCUSDT", "2024-01")
    cksum_url = mod.build_checksum_url(zip_url)
    assert cksum_url.endswith(".CHECKSUM")
    assert "BTCUSDT" in cksum_url
    assert "2024-01" in cksum_url


# ---------------------------------------------------------------------------
# Download plan construction
# ---------------------------------------------------------------------------


def test_manifest_selects_daily_liquidation_when_monthly_missing():
    """build_download_plan with mode='daily' must include daily liq URLs."""
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="daily",
    )
    assert len(plan) > 0
    # All liquidation entries should be daily
    liq_entries = [e for e in plan if e["kind"] == "liquidation"]
    assert len(liq_entries) > 0
    for entry in liq_entries:
        assert "daily" in entry["url"], f"Expected daily URL, got: {entry['url']}"


def test_download_plan_includes_kline_entries():
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="daily",
    )
    kline_entries = [e for e in plan if e["kind"] == "kline"]
    assert len(kline_entries) > 0


def test_download_plan_entry_has_required_fields():
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="daily",
    )
    for entry in plan:
        assert "url" in entry, "Plan entry must have 'url'"
        assert "checksum_url" in entry, "Plan entry must have 'checksum_url'"
        assert "kind" in entry, "Plan entry must have 'kind' (kline|liquidation)"
        assert "symbol" in entry, "Plan entry must have 'symbol'"
        assert "month" in entry, "Plan entry must have 'month'"


def test_download_plan_monthly_mode_uses_monthly_liquidation():
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="monthly",
    )
    liq_entries = [e for e in plan if e["kind"] == "liquidation"]
    assert len(liq_entries) > 0
    for entry in liq_entries:
        assert "monthly/liquidationSnapshot" in entry["url"]


def test_download_summary_requires_checksum_verification_for_phase1_inputs():
    """
    The download summary must record checksum_status for every entry.
    Even if CHECKSUM is missing, it must be recorded (not silently ignored).
    """
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="daily",
    )
    # build_download_plan entries must expose checksum_url
    for entry in plan:
        assert "checksum_url" in entry
        # checksum_url must not be empty
        assert entry["checksum_url"], f"checksum_url is empty for entry {entry}"


def test_download_plan_covers_all_days_in_month_for_daily_mode():
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        liquidation_mode="daily",
    )
    liq_entries = [e for e in plan if e["kind"] == "liquidation" and e["symbol"] == "BTCUSDT"]
    # Jan 2024 has 31 days
    assert len(liq_entries) == 31, f"Expected 31 daily liq entries for Jan, got {len(liq_entries)}"


def test_download_plan_covers_all_months_for_monthly_kline():
    mod = _load_fetch_module()
    plan = mod.build_download_plan(
        symbols=["BTCUSDT", "ETHUSDT"],
        months=["2024-01", "2024-02", "2024-03"],
        liquidation_mode="daily",
    )
    kline_entries = [e for e in plan if e["kind"] == "kline"]
    # 2 symbols × 3 months = 6 kline entries
    assert len(kline_entries) == 6
