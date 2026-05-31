"""
Tests for probe_binance_liquidation_snapshot_manifest.py

All tests use unit-test doubles (no real HTTP). The probe's network layer
is expected to be injected via a `url_head_fn` parameter or patched with
monkeypatching.
"""

import sys
import os
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Import the module under test
import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).parent.parent.parent / "scripts" / "probe_binance_liquidation_snapshot_manifest.py"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("probe_binance_liquidation_snapshot_manifest", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Basic imports / module structure
# ---------------------------------------------------------------------------


def test_probe_module_imports():
    mod = _load_probe_module()
    assert hasattr(mod, "build_kline_monthly_url"), "Must export build_kline_monthly_url"
    assert hasattr(mod, "build_liquidation_monthly_url"), "Must export build_liquidation_monthly_url"
    assert hasattr(mod, "build_liquidation_daily_url"), "Must export build_liquidation_daily_url"
    assert hasattr(mod, "probe_manifest"), "Must export probe_manifest"


# ---------------------------------------------------------------------------
# URL construction tests
# ---------------------------------------------------------------------------


def test_kline_monthly_url_format():
    mod = _load_probe_module()
    url = mod.build_kline_monthly_url("BTCUSDT", "2024-01")
    assert "data.binance.vision" in url
    assert "futures/um/monthly/klines" in url
    assert "BTCUSDT" in url
    assert "1m" in url
    assert "2024-01" in url
    assert url.endswith(".zip")


def test_liquidation_monthly_url_format():
    mod = _load_probe_module()
    url = mod.build_liquidation_monthly_url("BTCUSDT", "2024-01")
    assert "data.binance.vision" in url
    assert "futures/um/monthly/liquidationSnapshot" in url
    assert "BTCUSDT" in url
    assert "2024-01" in url
    assert url.endswith(".zip")


def test_liquidation_daily_url_format():
    mod = _load_probe_module()
    url = mod.build_liquidation_daily_url("BTCUSDT", "2024-01-15")
    assert "data.binance.vision" in url
    assert "futures/um/daily/liquidationSnapshot" in url
    assert "BTCUSDT" in url
    assert "2024-01-15" in url
    assert url.endswith(".zip")


# ---------------------------------------------------------------------------
# probe_manifest output structure tests
# ---------------------------------------------------------------------------


def _always_available(url: str) -> bool:
    return True


def _never_available(url: str) -> bool:
    return False


def _monthly_liq_unavailable(url: str) -> bool:
    """Simulates monthly liquidation missing, daily available."""
    if "monthly/liquidationSnapshot" in url:
        return False
    return True


def test_probe_manifest_returns_required_keys():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    required_keys = {
        "source",
        "market",
        "symbols",
        "months",
        "kline_monthly_available",
        "liquidation_monthly_available",
        "liquidation_daily_available",
        "selected_liquidation_download_mode",
        "missing_symbol_months",
        "decision",
    }
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"


def test_probe_manifest_source_is_binance_vision():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    assert result["source"] == "binance_vision"


def test_probe_manifest_market_is_futures_um():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    assert result["market"] == "futures_um"


def test_probe_manifest_prefers_monthly_kline():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    # When monthly klines are available, they should be selected
    assert result["kline_monthly_available"]["BTCUSDT"]["2024-01"] is True


def test_probe_manifest_selects_daily_liquidation_when_monthly_missing():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_monthly_liq_unavailable,
    )
    assert result["selected_liquidation_download_mode"] == "daily"


def test_probe_manifest_selects_monthly_liquidation_when_available():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    # When both monthly and daily are available, should prefer monthly
    assert result["selected_liquidation_download_mode"] in ("monthly", "daily")


def test_probe_manifest_decision_proceed_when_data_available():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_always_available,
    )
    assert result["decision"] in (
        "proceed_with_daily_liquidation",
        "proceed_with_monthly_liquidation",
    )


def test_probe_manifest_decision_unavailable_when_all_missing():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_never_available,
    )
    assert result["decision"] == "data_unavailable"


def test_probe_manifest_daily_mode_decision():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_monthly_liq_unavailable,
    )
    assert result["decision"] == "proceed_with_daily_liquidation"


def test_probe_manifest_missing_symbol_months_populated():
    mod = _load_probe_module()
    result = mod.probe_manifest(
        symbols=["BTCUSDT"],
        months=["2024-01"],
        url_head_fn=_never_available,
    )
    assert isinstance(result["missing_symbol_months"], list)


def test_probe_manifest_allowed_decisions():
    mod = _load_probe_module()
    allowed = {
        "proceed_with_daily_liquidation",
        "proceed_with_monthly_liquidation",
        "data_unavailable",
    }
    for head_fn in [_always_available, _never_available, _monthly_liq_unavailable]:
        result = mod.probe_manifest(
            symbols=["BTCUSDT"],
            months=["2024-01"],
            url_head_fn=head_fn,
        )
        assert result["decision"] in allowed, f"Unexpected decision: {result['decision']}"
