from __future__ import annotations

from dataclasses import dataclass

import configs.base

STABLECOINS = {"USDC", "FDUSD", "TUSD", "BUSD", "DAI", "EUR", "GBP", "USDP", "USD"}
REAL_W_TOKENS = {"WOO", "WIF", "WAVES", "WAXP", "WLD", "WTC", "WAN"}


def get_base(symbol: str) -> str:
    """Helper to extract uppercase base asset from symbol string."""
    clean = normalize_symbol(symbol)
    if clean.endswith("USDT"):
        return clean[:-4]
    return clean


def normalize_symbol(symbol: str) -> str:
    """Normalize spot/perp symbols to uppercase base+quote form.

    CCXT represents USDT-margined swaps as ``BTC/USDT:USDT``. The settlement
    suffix is not part of the exchange symbol and must not leak into static
    exclusion checks.
    """
    return symbol.split(":", 1)[0].replace("/", "").upper()


def is_stablecoin_pair(symbol: str) -> bool:
    """Check if the base asset is a stablecoin or fiat currency."""
    base = get_base(symbol)
    return base in STABLECOINS


def is_leveraged_token(symbol: str) -> bool:
    """Check if the base asset is a leveraged token (ends with UP/DOWN/BULL/BEAR)."""
    base = get_base(symbol)
    return (
        base.endswith("UP")
        or base.endswith("DOWN")
        or base.endswith("BULL")
        or base.endswith("BEAR")
    )


def is_wrapped_or_synthetic(symbol: str) -> bool:
    """Check if the base asset is a wrapped or synthetic asset, respecting configuration."""
    exclude_flag = getattr(configs.base, "FACTOR_LAB_STAGE0_EXCLUDE_WRAPPED_TOKENS", True)
    if not exclude_flag:
        return False
    base = get_base(symbol)
    # Exclude known real tokens that start with W
    if base in REAL_W_TOKENS:
        return False
    return (base.startswith("W") or base.startswith("S")) and len(base) > 2


@dataclass
class UniverseAudit:
    symbols_total: int
    symbols_after_static_exclusions: int
    excluded_symbols: dict[str, list[str]]
    eligible_symbols: tuple[str, ...]


def filter_stage0_universe(symbols: list[str]) -> UniverseAudit:
    """Filter symbols list by static exclusion rules and return audit summary."""
    excluded = {
        "stablecoin": [],
        "leveraged": [],
        "wrapped": [],
    }
    eligible = []

    for sym in symbols:
        normalized = normalize_symbol(sym)
        if is_stablecoin_pair(normalized):
            excluded["stablecoin"].append(normalized)
        elif is_leveraged_token(normalized):
            excluded["leveraged"].append(normalized)
        elif is_wrapped_or_synthetic(normalized):
            excluded["wrapped"].append(normalized)
        else:
            eligible.append(normalized)

    # De-duplicate lists to keep audit summary clean
    eligible_tuple = tuple(sorted(list(set(eligible))))

    return UniverseAudit(
        symbols_total=len(symbols),
        symbols_after_static_exclusions=len(eligible_tuple),
        excluded_symbols=excluded,
        eligible_symbols=eligible_tuple,
    )
