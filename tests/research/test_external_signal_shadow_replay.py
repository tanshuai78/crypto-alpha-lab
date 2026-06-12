from src.research.external_signal_shadow.models import ExternalSignalEvent, PriceBar

MINUTE = 60_000


def _event(event_id: str, **overrides):
    payload = {
        "event_id": event_id,
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
        "metadata": {
            "spread_bps": 3.0,
            "depth_10bps_usd": 500_000.0,
            "orderbook_coverage": 1.0,
            "price_coverage": 1.0,
        },
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


def _bars():
    return [
        _bar(9, 100.0, 100.1, 99.9, 100.0),
        _bar(10, 100.0, 100.1, 99.9, 100.0),
        _bar(11, 100.0, 102.0, 99.8, 101.0),
        _bar(12, 101.0, 101.2, 100.8, 101.0),
    ]


def test_replay_outputs_no_cusum_and_cusum_branches():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())

    assert "no_cusum_all_accepted_events" in summary["branches"]
    assert "cusum_confirmed_events" in summary["branches"]


def test_replay_rejected_events_do_not_create_shadow_orders():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay(
        [_event("evt-1", metadata={
            "spread_bps": 99.0,
            "depth_10bps_usd": 500_000.0,
            "orderbook_coverage": 1.0,
            "price_coverage": 1.0,
        })],
        _bars(),
    )

    assert summary["events_rejected"] == 1
    assert summary["branches"]["no_cusum_all_accepted_events"]["shadow_order_count"] == 0


def test_replay_observe_only_events_do_not_create_directional_orders():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay(
        [_event("evt-1", direction_hint="unknown")],
        _bars(),
    )

    assert summary["events_accepted"] == 1
    assert summary["branches"]["no_cusum_all_accepted_events"]["shadow_order_count"] == 0


def test_replay_no_cusum_branch_enters_after_event_time():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())
    order = summary["branches"]["no_cusum_all_accepted_events"]["shadow_orders"][0]

    assert order["entry_time_ms"] == 11 * MINUTE


def test_replay_cusum_branch_enters_after_cusum_trigger():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())
    order = summary["branches"]["cusum_confirmed_events"]["shadow_orders"][0]

    assert order["entry_time_ms"] == 12 * MINUTE


def test_replay_records_cusum_no_confirm_count():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    flat_bars = [
        _bar(9, 100.0, 100.1, 99.9, 100.0),
        _bar(10, 100.0, 100.1, 99.9, 100.0),
        _bar(11, 100.0, 100.1, 99.9, 100.01),
    ]
    summary = run_stage0_shadow_replay([_event("evt-1")], flat_bars)

    assert summary["cusum_no_confirm_count"] == 1


def test_replay_records_win_loss_timeout_counts():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())
    branch = summary["branches"]["no_cusum_all_accepted_events"]

    assert branch["take_profit_count"] == 1
    assert branch["stop_loss_count"] == 0
    assert branch["vertical_barrier_count"] == 0


def test_replay_summary_is_deterministic_for_fixture_inputs():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary_1 = run_stage0_shadow_replay([_event("evt-1")], _bars())
    summary_2 = run_stage0_shadow_replay([_event("evt-1")], _bars())

    assert summary_1 == summary_2


def test_summary_labels_no_cusum_branch_as_baseline_control():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())

    assert (
        summary["branch_semantics"]["no_cusum_all_accepted_events"]
        == "baseline_control_not_strategy"
    )


def test_summary_labels_cusum_branch_as_confirmation_filtered_shadow():
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    summary = run_stage0_shadow_replay([_event("evt-1")], _bars())

    assert (
        summary["branch_semantics"]["cusum_confirmed_events"]
        == "confirmation_filtered_shadow_not_strategy"
    )


def test_fixture_contains_same_bar_tp_sl_conservative_case():
    from src.research.external_signal_shadow.models import (
        load_events_jsonl,
        load_price_bars_jsonl,
    )
    from src.research.external_signal_shadow.replay import run_stage0_shadow_replay

    events = load_events_jsonl(
        "tests/fixtures/external_signal_shadow/stage0_events.jsonl"
    )
    bars = load_price_bars_jsonl(
        "tests/fixtures/external_signal_shadow/stage0_price_bars.jsonl"
    )

    summary = run_stage0_shadow_replay(events, bars)
    orders = summary["branches"]["no_cusum_all_accepted_events"]["shadow_orders"]
    same_bar_order = next(order for order in orders if order["event_id"] == "evt-same-bar")

    assert same_bar_order["exit_reason"] == "stop_loss"
