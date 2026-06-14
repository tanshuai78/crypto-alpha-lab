from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median, pstdev
from typing import Any


@dataclass(frozen=True)
class CandidateEvent:
    candidate_name: str
    symbol: str
    event_time_ms: int
    candidate_role: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _safe_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    return pstdev(values)


def detect_volume_spike_1h(
    *,
    symbol: str,
    current_1h_quote_volume: float,
    same_hour_historical_volumes: list[float],
    event_time_ms: int,
    threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if len(same_hour_historical_volumes) < min_samples:
        return None
    baseline = median(same_hour_historical_volumes)
    if baseline <= 0:
        return None
    ratio = current_1h_quote_volume / baseline
    if ratio < threshold:
        return None
    return CandidateEvent(
        "volume_spike_1h",
        symbol,
        event_time_ms,
        "primary",
        {"volume_ratio": ratio, "baseline_volume": baseline},
    )


def detect_relative_strength_vs_btc(
    *,
    symbol: str,
    alt_1h_return: float,
    btc_1h_return: float,
    historical_spread_returns: list[float],
    event_time_ms: int,
    z_threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if symbol.upper() == "BTCUSDT" or len(historical_spread_returns) < min_samples:
        return None
    spread = alt_1h_return - btc_1h_return
    historical_spread_center = median(historical_spread_returns)
    sigma = _safe_std(historical_spread_returns)
    if sigma <= 0:
        return None
    z_score = (spread - historical_spread_center) / sigma
    if z_score < z_threshold:
        return None
    return CandidateEvent(
        "relative_strength_vs_btc",
        symbol,
        event_time_ms,
        "primary",
        {
            "spread_return": spread,
            "historical_spread_center": historical_spread_center,
            "rolling_sigma": sigma,
            "z_score": z_score,
            "evaluation_modes": ("outright_long_alt", "relative_spread_observation"),
        },
    )


def detect_volume_confirmed_relative_strength(
    volume_event: CandidateEvent | None,
    relative_strength_event: CandidateEvent | None,
) -> CandidateEvent | None:
    if volume_event is None or relative_strength_event is None:
        return None
    if volume_event.symbol != relative_strength_event.symbol:
        return None
    if volume_event.event_time_ms != relative_strength_event.event_time_ms:
        return None
    return CandidateEvent(
        "volume_confirmed_relative_strength",
        volume_event.symbol,
        volume_event.event_time_ms,
        "primary",
        {
            "volume_metadata": volume_event.metadata,
            "relative_strength_metadata": relative_strength_event.metadata,
        },
    )


def detect_price_move_15m_baseline(
    *,
    symbol: str,
    symbol_15m_return: float,
    historical_15m_returns: list[float],
    event_time_ms: int,
    z_threshold: float,
    min_samples: int,
) -> CandidateEvent | None:
    if len(historical_15m_returns) < min_samples:
        return None
    sigma = _safe_std(historical_15m_returns)
    if sigma <= 0 or abs(symbol_15m_return) < z_threshold * sigma:
        return None
    return CandidateEvent(
        "price_move_15m",
        symbol,
        event_time_ms,
        "baseline",
        {"trigger_sign": 1 if symbol_15m_return > 0 else -1},
    )
