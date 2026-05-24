"""
risk/limits.py — Position and equity curve hard limits.

All values default to the most conservative setting.
RISK_LIVE_TRADING_ENABLED defaults to False — the system boots in observation mode.
"""
from __future__ import annotations

from dataclasses import dataclass

try:
    from configs.base import (
        RISK_EQUITY_CURVE_DRAWDOWN_HALT_PCT,
        RISK_LIVE_TRADING_ENABLED,
        RISK_MAX_CONCURRENT_POSITIONS,
        RISK_MAX_SINGLE_POSITION_USDT,
    )
except ModuleNotFoundError:
    from configs.base import (  # type: ignore[no-redef]
        RISK_EQUITY_CURVE_DRAWDOWN_HALT_PCT,
        RISK_LIVE_TRADING_ENABLED,
        RISK_MAX_CONCURRENT_POSITIONS,
        RISK_MAX_SINGLE_POSITION_USDT,
    )


@dataclass
class RiskLimits:
    """
    Immutable-ish risk limit snapshot.

    Instantiate once at startup. Never mutate fields directly;
    use a new instance if limits need updating (and log the change).
    """

    max_single_position_usdt: float = RISK_MAX_SINGLE_POSITION_USDT
    max_concurrent_positions: int = RISK_MAX_CONCURRENT_POSITIONS
    equity_curve_drawdown_halt_pct: float = RISK_EQUITY_CURVE_DRAWDOWN_HALT_PCT
    live_trading_enabled: bool = RISK_LIVE_TRADING_ENABLED

    def check_position_size(self, notional_usdt: float) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        if not self.live_trading_enabled:
            return False, "live_trading_enabled is False — system in observation mode"
        if notional_usdt <= 0:
            return False, f"notional must be positive, got {notional_usdt}"
        if notional_usdt > self.max_single_position_usdt:
            return False, (
                f"notional {notional_usdt:.2f} USDT exceeds "
                f"limit {self.max_single_position_usdt:.2f} USDT"
            )
        return True, "ok"

    def check_concurrent_positions(self, current_open: int) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        if not self.live_trading_enabled:
            return False, "live_trading_enabled is False"
        if current_open >= self.max_concurrent_positions:
            return False, (
                f"concurrent positions {current_open} >= "
                f"limit {self.max_concurrent_positions}"
            )
        return True, "ok"
