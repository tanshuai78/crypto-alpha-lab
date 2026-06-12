import json

import pytest


def test_external_signal_shadow_stage0_config_constants_exist():
    from configs import base

    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_LIQUIDITY_USD == 500_000.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_SELL_TAX_PCT == 5.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_TOP10_HOLDER_SHARE == 0.35
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_SMART_MONEY_EXIT_RATE == 0.70
    assert base.EXTERNAL_SIGNAL_SHADOW_CEX_MAX_SPREAD_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_SHADOW_CEX_MIN_DEPTH_10BPS_USD == 100_000.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_ORDERBOOK_COVERAGE == 0.95
    assert base.EXTERNAL_SIGNAL_SHADOW_MIN_PRICE_COVERAGE == 0.99
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_FIXED_THRESHOLD_BPS == 30.0
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_VOL_MULTIPLIER == 1.5
    assert base.EXTERNAL_SIGNAL_SHADOW_CUSUM_CONFIRMATION_WINDOW_MIN == 30
    assert base.EXTERNAL_SIGNAL_SHADOW_TAKE_PROFIT_BPS == 150.0
    assert base.EXTERNAL_SIGNAL_SHADOW_STOP_LOSS_BPS == 100.0
    assert base.EXTERNAL_SIGNAL_SHADOW_MAX_HOLDING_MINUTES == 240
    assert base.EXTERNAL_SIGNAL_SHADOW_ENTRY_DELAY_BARS == 1
    assert base.EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS == 50.0


def _event_payload(**overrides):
    payload = {
        "event_id": "evt-1",
        "source": "internal",
        "source_skill": "fixture",
        "event_type": "market_tape_anomaly",
        "chain": "cex",
        "symbol": "BTC/USDT",
        "token_address": None,
        "event_time_ms": 1_700_000_000_000,
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
    return payload


def test_external_signal_event_normalizes_symbol_and_requires_shadow_only():
    from src.research.external_signal_shadow.models import ExternalSignalEvent

    event = ExternalSignalEvent.from_dict(_event_payload())

    assert event.symbol == "BTCUSDT"

    with pytest.raises(ValueError, match="shadow_only"):
        ExternalSignalEvent.from_dict(_event_payload(shadow_only=False))


def test_external_signal_event_rejects_executable_payload_fields():
    from src.research.external_signal_shadow.models import ExternalSignalEvent

    with pytest.raises(ValueError, match="api_key"):
        ExternalSignalEvent.from_dict(_event_payload(api_key="secret"))


def test_external_signal_event_rejects_forbidden_keys_nested_in_metadata():
    from src.research.external_signal_shadow.models import ExternalSignalEvent

    with pytest.raises(ValueError, match="private_key"):
        ExternalSignalEvent.from_dict(
            _event_payload(metadata={"safe": {"private_key": "0xdeadbeef"}})
        )


def test_external_signal_event_rejects_forbidden_keys_inside_list():
    from src.research.external_signal_shadow.models import ExternalSignalEvent

    with pytest.raises(ValueError, match="signed_tx"):
        ExternalSignalEvent.from_dict(
            _event_payload(metadata={"items": [{"signed_tx": "0xabc"}]})
        )


def test_price_bar_rejects_non_positive_prices():
    from src.research.external_signal_shadow.models import PriceBar

    with pytest.raises(ValueError, match="positive"):
        PriceBar(
            symbol="BTCUSDT",
            bar_start_ms=1_000,
            bar_end_ms=61_000,
            open_price=0.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
        )


def test_price_bar_requires_high_gte_low():
    from src.research.external_signal_shadow.models import PriceBar

    with pytest.raises(ValueError, match="high_price"):
        PriceBar(
            symbol="BTCUSDT",
            bar_start_ms=1_000,
            bar_end_ms=61_000,
            open_price=100.0,
            high_price=98.0,
            low_price=99.0,
            close_price=100.0,
        )


def test_price_bar_requires_end_after_start():
    from src.research.external_signal_shadow.models import PriceBar

    with pytest.raises(ValueError, match="bar_end_ms"):
        PriceBar(
            symbol="BTCUSDT",
            bar_start_ms=1_000,
            bar_end_ms=1_000,
            open_price=100.0,
            high_price=101.0,
            low_price=99.0,
            close_price=100.0,
        )


def test_parse_jsonl_events_and_bars_round_trip(tmp_path):
    from src.research.external_signal_shadow.models import (
        load_events_jsonl,
        load_price_bars_jsonl,
    )

    events_path = tmp_path / "events.jsonl"
    bars_path = tmp_path / "bars.jsonl"
    events_path.write_text(json.dumps(_event_payload()) + "\n")
    bars_path.write_text(
        json.dumps(
            {
                "symbol": "BTC/USDT",
                "bar_start_ms": 1_000,
                "bar_end_ms": 61_000,
                "open_price": 100.0,
                "high_price": 101.0,
                "low_price": 99.0,
                "close_price": 100.5,
            }
        )
        + "\n"
    )

    events = load_events_jsonl(str(events_path))
    bars = load_price_bars_jsonl(str(bars_path))

    assert events[0].event_id == "evt-1"
    assert events[0].symbol == "BTCUSDT"
    assert bars[0].symbol == "BTCUSDT"
    assert bars[0].bar_end_ms == 61_000
