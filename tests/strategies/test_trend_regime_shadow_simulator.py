from src.strategies.trend_regime.shadow_simulator import (
    TrendRegimeShadowPosition,
    simulate_trend_regime_shadow,
)


def _position(**overrides) -> TrendRegimeShadowPosition:
    payload = {
        "symbol": "BTC/USDT",
        "direction": "long",
        "entry_time_ms": 1_710_000_000_000,
        "entry_price": 100_000.0,
        "estimated_cost_bps": 30.0,
        "max_holding_hours": 12.0,
        "stop_loss_pct": 1.5,
        "regime": "vol_breakout_long",
        "symbol_tier": "major",
    }
    payload.update(overrides)
    return TrendRegimeShadowPosition(**payload)


def _row(timestamp_ms: int, close_price: float) -> dict:
    return {
        "timestamp_ms": timestamp_ms,
        "close_price": close_price,
    }


def test_long_path_exits_on_max_holding_time() -> None:
    position = _position()
    result = simulate_trend_regime_shadow(
        position,
        [
            _row(position.entry_time_ms + 6 * 3_600_000, 101_000.0),
            _row(position.entry_time_ms + 12 * 3_600_000, 102_000.0),
            _row(position.entry_time_ms + 13 * 3_600_000, 103_000.0),
        ],
    )

    assert result.exit_reason == "max_holding_time_reached"
    assert result.gross_pnl_pct == 2.0
    assert result.net_pnl_bps == 170.0


def test_long_path_exits_on_stop_loss() -> None:
    position = _position()
    result = simulate_trend_regime_shadow(
        position,
        [_row(position.entry_time_ms + 1 * 3_600_000, 98_000.0)],
    )

    assert result.exit_reason == "stop_loss_hit"
    assert result.gross_pnl_pct == -2.0
    assert result.net_pnl_bps == -230.0


def test_empty_path_returns_cost_loss_and_path_exhausted() -> None:
    position = _position()
    result = simulate_trend_regime_shadow(position, [])

    assert result.exit_reason == "path_exhausted"
    assert result.gross_pnl_pct == 0.0
    assert result.net_pnl_bps == -30.0


def test_short_stop_loss_uses_directional_pnl() -> None:
    position = _position(direction="short", regime="vol_breakout_short")
    result = simulate_trend_regime_shadow(
        position,
        [_row(position.entry_time_ms + 1 * 3_600_000, 102_000.0)],
    )

    assert result.exit_reason == "stop_loss_hit"
    assert result.gross_pnl_pct == -2.0
    assert result.net_pnl_bps == -230.0


def test_short_profit_path_uses_reverse_direction() -> None:
    position = _position(direction="short", regime="vol_breakout_short")
    result = simulate_trend_regime_shadow(
        position,
        [_row(position.entry_time_ms + 2 * 3_600_000, 98_000.0)],
    )

    assert result.exit_reason == "path_exhausted"
    assert result.gross_pnl_pct == 2.0
    assert result.net_pnl_bps == 170.0
