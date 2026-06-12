from src.research.external_signal_shadow.models import ExternalSignalEvent, PriceBar

MINUTE = 60_000


def _event(**overrides):
    payload = {
        "event_id": "evt-tb",
        "source": "internal",
        "source_skill": "fixture",
        "event_type": "market_tape_anomaly",
        "chain": "cex",
        "symbol": "BTCUSDT",
        "token_address": None,
        "event_time_ms": 10 * MINUTE + 30_000,
        "direction_hint": "long",
        "raw_score": 1.0,
        "notional_usd": 1_000_000.0,
        "liquidity_usd": 5_000_000.0,
        "risk_flags": [],
        "data_quality": "ok",
        "shadow_only": True,
        "metadata": {},
    }
    payload.update(overrides)
    return ExternalSignalEvent.from_dict(payload)


def _bar(index: int, open_price: float, high: float, low: float, close: float):
    return PriceBar(
        symbol="BTCUSDT",
        bar_start_ms=index * MINUTE,
        bar_end_ms=(index + 1) * MINUTE,
        open_price=open_price,
        high_price=high,
        low_price=low,
        close_price=close,
    )


def _order(direction: str, bars: list[PriceBar], *, trigger_time_ms: int | None = None):
    from src.research.external_signal_shadow.triple_barrier import (
        build_shadow_order_with_triple_barrier,
    )

    return build_shadow_order_with_triple_barrier(
        _event(direction_hint=direction),
        trigger_time_ms if trigger_time_ms is not None else 10 * MINUTE + 30_000,
        bars,
        direction=direction,
        take_profit_bps=150.0,
        stop_loss_bps=100.0,
        max_holding_minutes=5,
        entry_delay_bars=1,
        cost_round_trip_bps=50.0,
    )


def test_triple_barrier_long_take_profit_first():
    order = _order("long", [_bar(11, 100.0, 102.0, 99.5, 101.0)])

    assert order.exit_reason == "take_profit"
    assert order.gross_return_bps == 150.0
    assert order.net_return_bps == 100.0


def test_triple_barrier_long_stop_loss_first():
    order = _order("long", [_bar(11, 100.0, 100.5, 98.0, 99.0)])

    assert order.exit_reason == "stop_loss"
    assert order.gross_return_bps == -100.0
    assert order.net_return_bps == -150.0


def test_triple_barrier_short_take_profit_first():
    order = _order("short", [_bar(11, 100.0, 100.5, 98.0, 99.0)])

    assert order.exit_reason == "take_profit"
    assert order.gross_return_bps == 150.0
    assert order.net_return_bps == 100.0


def test_triple_barrier_short_stop_loss_first():
    order = _order("short", [_bar(11, 100.0, 102.0, 99.0, 101.0)])

    assert order.exit_reason == "stop_loss"
    assert order.gross_return_bps == -100.0
    assert order.net_return_bps == -150.0


def test_triple_barrier_vertical_timeout():
    order = _order(
        "long",
        [
            _bar(11, 100.0, 100.5, 99.5, 100.2),
            _bar(12, 100.2, 100.4, 99.9, 100.3),
        ],
    )

    assert order.exit_reason == "vertical_barrier"
    assert order.status == "closed"
    assert order.exit_price == 100.3


def test_triple_barrier_entry_uses_next_complete_bar_after_trigger():
    order = _order(
        "long",
        [
            _bar(10, 100.0, 200.0, 50.0, 120.0),
            _bar(11, 101.0, 102.6, 100.8, 102.0),
        ],
    )

    assert order.entry_time_ms == 11 * MINUTE
    assert order.entry_price == 101.0
    assert order.exit_reason == "take_profit"


def test_triple_barrier_applies_round_trip_cost_to_net_return():
    order = _order("long", [_bar(11, 100.0, 102.0, 99.5, 101.0)])

    assert order.net_return_bps == order.gross_return_bps - 50.0


def test_triple_barrier_reports_mae_and_mfe():
    order = _order("long", [_bar(11, 100.0, 101.0, 99.0, 100.5)])

    assert order.max_adverse_excursion_bps == 100.0
    assert order.max_favorable_excursion_bps == 100.0


def test_triple_barrier_returns_data_unavailable_without_entry_bar():
    order = _order("long", [])

    assert order.status == "data_unavailable"
    assert order.exit_reason == "data_unavailable"


def test_triple_barrier_does_not_use_pre_entry_high_low():
    order = _order(
        "long",
        [
            _bar(10, 100.0, 300.0, 1.0, 120.0),
            _bar(11, 100.0, 100.5, 99.5, 100.2),
        ],
    )

    assert order.exit_reason == "vertical_barrier"


def test_entry_does_not_use_bar_that_contains_trigger_time():
    order = _order(
        "long",
        [
            _bar(10, 100.0, 300.0, 1.0, 120.0),
            _bar(11, 101.0, 102.6, 100.8, 102.0),
        ],
        trigger_time_ms=10 * MINUTE + 30_000,
    )

    assert order.entry_time_ms == 11 * MINUTE


def test_triple_barrier_does_not_use_trigger_bar_high_low():
    order = _order(
        "long",
        [
            _bar(10, 100.0, 300.0, 1.0, 120.0),
            _bar(11, 100.0, 100.5, 99.5, 100.1),
        ],
        trigger_time_ms=10 * MINUTE + 30_000,
    )

    assert order.exit_reason == "vertical_barrier"


def test_triple_barrier_same_bar_tp_and_sl_uses_conservative_stop_loss():
    order = _order("long", [_bar(11, 100.0, 102.0, 98.0, 101.0)])

    assert order.exit_reason == "stop_loss"
    assert order.gross_return_bps == -100.0
