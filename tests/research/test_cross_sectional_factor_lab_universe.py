from __future__ import annotations

from research.cross_sectional_factor_lab.universe import (
    UniverseAudit,
    filter_stage0_universe,
    is_leveraged_token,
    is_stablecoin_pair,
    is_wrapped_or_synthetic,
    normalize_symbol,
)


def test_normalize_symbol_removes_slash_and_uppercases() -> None:
    assert normalize_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_symbol("ethusdt") == "ETHUSDT"
    assert normalize_symbol("Sol/usdt") == "SOLUSDT"
    assert normalize_symbol("BTC/USDT:USDT") == "BTCUSDT"


def test_static_exclusion_removes_stablecoin_pairs() -> None:
    assert is_stablecoin_pair("USDCUSDT") is True
    assert is_stablecoin_pair("USDC/USDT:USDT") is True
    assert is_stablecoin_pair("FDUSDUSDT") is True
    assert is_stablecoin_pair("TUSDUSDT") is True
    assert is_stablecoin_pair("EURUSDT") is True
    assert is_stablecoin_pair("BTCUSDT") is False
    assert is_stablecoin_pair("ETHUSDT") is False


def test_static_exclusion_removes_leveraged_tokens() -> None:
    assert is_leveraged_token("BTCUPUSDT") is True
    assert is_leveraged_token("BTCUP/USDT:USDT") is True
    assert is_leveraged_token("BTCDOWNUSDT") is True
    assert is_leveraged_token("ETHBULLUSDT") is True
    assert is_leveraged_token("ETHBEARUSDT") is True
    assert is_leveraged_token("LTCUSDT") is False


def test_wrapped_token_exclusion_respects_config_flag(monkeypatch) -> None:
    # Test case when FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS is True
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS", True)
    assert is_wrapped_or_synthetic("WBTCUSDT") is True
    assert is_wrapped_or_synthetic("WETHUSDT") is True
    assert is_wrapped_or_synthetic("BTCUSDT") is False

    # Test case when FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS is False
    monkeypatch.setattr("configs.base.FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS", False)
    assert is_wrapped_or_synthetic("WBTCUSDT") is False
    assert is_wrapped_or_synthetic("WETHUSDT") is False


def test_static_exclusion_keeps_major_usdt_symbols() -> None:
    assert is_stablecoin_pair("BTCUSDT") is False
    assert is_leveraged_token("BTCUSDT") is False
    assert is_wrapped_or_synthetic("BTCUSDT") is False


def test_universe_summary_counts_total_excluded_and_remaining() -> None:
    symbols = [
        "BTC/USDT",
        "ETH/USDT",
        "USDC/USDT",
        "BTCUP/USDT",
        "WBTC/USDT",
    ]
    audit = filter_stage0_universe(symbols)
    assert isinstance(audit, UniverseAudit)
    assert audit.symbols_total == 5
    # USDC/USDT, BTCUP/USDT, WBTC/USDT should be excluded
    assert audit.symbols_after_static_exclusions == 2
    assert "BTCUSDT" in audit.eligible_symbols
    assert "ETHUSDT" in audit.eligible_symbols
    assert "USDCUSDT" in audit.excluded_symbols["stablecoin"]
    assert "BTCUPUSDT" in audit.excluded_symbols["leveraged"]
    assert "WBTCUSDT" in audit.excluded_symbols["wrapped"]


def test_universe_filter_excludes_ccxt_swap_stablecoin_and_leveraged_symbols() -> None:
    symbols = ["BTC/USDT:USDT", "USDC/USDT:USDT", "BTCUP/USDT:USDT"]

    audit = filter_stage0_universe(symbols)

    assert audit.eligible_symbols == ("BTCUSDT",)
    assert "USDCUSDT" in audit.excluded_symbols["stablecoin"]
    assert "BTCUPUSDT" in audit.excluded_symbols["leveraged"]
