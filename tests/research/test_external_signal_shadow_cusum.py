
import pytest

from src.research.external_signal_shadow.models import ExternalSignalEvent, PriceBar

MINUTE = 60_000


def _event(**overrides):
    payload = {
        "event_id": "evt-cusum",
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


def _bar(index: int, close: float, *, open_price: float | None = None) -> PriceBar:
    return PriceBar(
        symbol="BTCUSDT",
        bar_start_ms=index * MINUTE,
        bar_end_ms=(index + 1) * MINUTE,
        open_price=open_price or close,
        high_price=max(open_price or close, close) + 0.1,
        low_price=min(open_price or close, close) - 0.1,
        close_price=close,
    )


def _bars(closes: list[float]) -> list[PriceBar]:
    return [_bar(index, close) for index, close in enumerate(closes)]


def test_cusum_confirms_positive_move_after_event():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.8, 101.0])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "confirmed"
    assert result.direction == "long"
    assert result.trigger_time_ms == 11 * MINUTE


def test_cusum_confirms_negative_move_after_event():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [99.2, 99.0])
    result = confirm_event_with_cusum(
        _event(direction_hint="short"),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "confirmed"
    assert result.direction == "short"
    assert result.trigger_time_ms == 11 * MINUTE


def test_cusum_returns_no_confirm_when_threshold_not_crossed():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.01, 100.02])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "no_confirm"


def test_cusum_respects_confirmation_window():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.01, 100.02, 101.0])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=1,
    )

    assert result.status == "no_confirm"


def test_cusum_long_hint_rejects_negative_confirmation_as_adverse():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [99.2])
    result = confirm_event_with_cusum(
        _event(direction_hint="long"),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "adverse_confirm"
    assert result.direction == "short"


def test_cusum_short_hint_rejects_positive_confirmation_as_adverse():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.8])
    result = confirm_event_with_cusum(
        _event(direction_hint="short"),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "adverse_confirm"
    assert result.direction == "long"


def test_cusum_unknown_direction_returns_observe_only_no_order():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.8])
    result = confirm_event_with_cusum(
        _event(direction_hint="unknown"),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "observe_only"


def test_cusum_uses_max_of_fixed_threshold_and_vol_threshold():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    closes = [100.0 + ((-1) ** i) * 0.5 for i in range(11)] + [100.2]
    result = confirm_event_with_cusum(
        _event(),
        _bars(closes),
        fixed_threshold_bps=1.0,
        vol_multiplier=3.0,
        confirmation_window_min=30,
    )

    assert result.threshold_source == "vol"
    assert result.status == "no_confirm"


def test_cusum_uses_pre_event_close_only_as_return_baseline():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.5])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "confirmed"
    assert result.trigger_time_ms == 11 * MINUTE


def test_cusum_does_not_trigger_on_pre_event_move():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 9 + [105.0, 105.0, 105.01])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "no_confirm"


def test_cusum_first_post_event_return_is_computed_correctly():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    bars = _bars([100.0] * 11 + [100.31])
    result = confirm_event_with_cusum(
        _event(),
        bars,
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.status == "confirmed"
    assert result.threshold_bps == pytest.approx(30.0)


def test_cusum_threshold_units_are_log_return_not_bps():
    from src.research.external_signal_shadow.cusum import _fixed_threshold_log_return

    assert _fixed_threshold_log_return(30.0) == pytest.approx(0.003)


def test_cusum_reports_threshold_source_fixed_or_vol():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    result = confirm_event_with_cusum(
        _event(),
        _bars([100.0] * 11 + [100.5]),
        fixed_threshold_bps=30.0,
        vol_multiplier=1.5,
        confirmation_window_min=30,
    )

    assert result.threshold_source in {"fixed", "vol"}
    assert result.threshold_bps is not None
    assert result.rolling_vol_bps is not None


def test_cusum_falls_back_to_fixed_threshold_when_pre_event_bars_insufficient():
    from src.research.external_signal_shadow.cusum import confirm_event_with_cusum

    result = confirm_event_with_cusum(
        _event(event_time_ms=MINUTE + 30_000),
        _bars([100.0, 100.1, 100.5]),
        fixed_threshold_bps=30.0,
        vol_multiplier=100.0,
        confirmation_window_min=30,
    )

    assert result.threshold_source == "fixed"
    assert result.threshold_bps == pytest.approx(30.0)
