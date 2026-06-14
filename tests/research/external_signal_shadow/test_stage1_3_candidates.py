from __future__ import annotations

from research.external_signal_shadow.stage1_3_candidates import (
    CandidateEvent,
    detect_price_move_15m_baseline,
    detect_relative_strength_vs_btc,
    detect_volume_confirmed_relative_strength,
    detect_volume_spike_1h,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar

MS_15M = 15 * 60 * 1000


def _bar(symbol: str, i: int, close: float, volume: float) -> HistoricalBar:
    return HistoricalBar(symbol, i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume)


def test_volume_spike_excludes_current_window_from_same_hour_baseline() -> None:
    # 5 historical same-hour volumes at 100, current 1h volume at 400 => 4x spike.
    historical = [100.0] * 5
    event = detect_volume_spike_1h(
        symbol="ETHUSDT",
        current_1h_quote_volume=400.0,
        same_hour_historical_volumes=historical,
        event_time_ms=10_000,
        threshold=3.0,
        min_samples=5,
    )
    assert isinstance(event, CandidateEvent)
    assert event.candidate_name == "volume_spike_1h"


def test_relative_strength_uses_centered_z_score_without_future_data() -> None:
    event = detect_relative_strength_vs_btc(
        symbol="SOLUSDT",
        alt_1h_return=0.05,
        btc_1h_return=0.00,
        historical_spread_returns=[0.0] * 47 + [0.02],
        event_time_ms=10_000,
        z_threshold=1.5,
        min_samples=48,
    )
    assert event is not None
    assert event.candidate_name == "relative_strength_vs_btc"
    assert "historical_spread_center" in event.metadata
    assert "rolling_sigma" in event.metadata


def test_volume_confirmed_requires_both_conditions_same_window() -> None:
    volume = CandidateEvent("volume_spike_1h", "ETHUSDT", 10_000, "primary", {})
    rel = CandidateEvent("relative_strength_vs_btc", "ETHUSDT", 10_000, "primary", {})
    confirmed = detect_volume_confirmed_relative_strength(volume, rel)
    assert confirmed is not None
    assert confirmed.candidate_name == "volume_confirmed_relative_strength"


def test_price_move_15m_is_baseline_only_and_signed() -> None:
    event = detect_price_move_15m_baseline(
        symbol="DOGEUSDT",
        symbol_15m_return=-0.04,
        historical_15m_returns=[0.0] * 47 + [0.02],
        event_time_ms=10_000,
        z_threshold=1.5,
        min_samples=48,
    )
    assert event is not None
    assert event.candidate_role == "baseline"
    assert event.metadata["trigger_sign"] == -1
