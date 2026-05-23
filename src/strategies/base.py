"""
strategies/base.py — BaseStrategy abstract contract.

Every strategy implementation must subclass this and implement all three methods.
Entry logic without exit logic and risk boundaries is rejected by design.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SignalCandidate:
    """Unified signal output from any scanner.

    Strategies return SignalCandidate instances — never raw dicts.
    The execution layer consumes SignalCandidate to build TradeIntent.
    """
    strategy_type: str          # e.g. "extreme_funding", "trend_regime"
    symbol: str                 # e.g. "BTCUSDT"
    direction: str              # "long" | "short" | "neutral"
    confidence: float           # 0.0 – 1.0
    expected_edge_bps: float    # Expected net edge after fees and slippage
    entry_exchange: str         # Primary leg exchange
    hedge_exchange: str         # Hedge leg exchange (same as entry for single-leg)
    trigger_reason: str         # Human-readable explanation
    invalidation_reason: str    # Condition that would invalidate this signal
    max_holding_hours: float    # Hard time limit for this position
    stop_loss_pct: float        # Per-trade stop loss percent
    suggested_notional_usdt: float  # Suggested position size
    metadata: dict[str, Any]    # Strategy-specific diagnostic data


class BaseStrategy(ABC):
    """Abstract base for all alpha lab strategies.

    Subclasses MUST implement all three methods. This enforces the
    Freqtrade-inspired rule: entry + exit + risk boundaries are atomic.
    A strategy that only defines entry logic is not a strategy.
    """

    strategy_type: str  # Class-level identifier, must be set by subclass

    @abstractmethod
    async def scan(self, market_data: dict[str, Any]) -> list[SignalCandidate]:
        """Scan market data and return signal candidates.

        Returns an empty list if no opportunity is found.
        Must NOT raise exceptions — catch internally and return [].
        """
        ...

    @abstractmethod
    def should_exit(
        self,
        signal: SignalCandidate,
        current_market: dict[str, Any],
        position_age_hours: float,
        unrealized_pnl_pct: float,
    ) -> tuple[bool, str]:
        """Evaluate whether an open position should be closed.

        Returns (should_exit, reason).
        Must be called after every funding settlement and on market data updates.
        """
        ...

    @abstractmethod
    def risk_check(self, signal: SignalCandidate) -> tuple[bool, str]:
        """Final risk gate before any execution attempt.

        Returns (allowed, reason). If False, signal is discarded without execution.
        Checks: position size, concurrent position count, live_trading_enabled, etc.
        """
        ...
