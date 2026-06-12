from src.research.external_signal_shadow.models import ExternalSignalEvent


def _event(**overrides):
    payload = {
        "event_id": "evt-1",
        "source": "internal",
        "source_skill": "fixture",
        "event_type": "market_tape_anomaly",
        "chain": "cex",
        "symbol": "BTCUSDT",
        "token_address": None,
        "event_time_ms": 1_700_000_000_000,
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


def _token_event(**overrides):
    payload = {
        "event_id": "evt-token",
        "source": "binance_web3",
        "source_skill": "query-token-info",
        "event_type": "smart_money_inflow",
        "chain": "bsc",
        "symbol": None,
        "token_address": "0x0000000000000000000000000000000000000001",
        "event_time_ms": 1_700_000_000_000,
        "direction_hint": "long",
        "raw_score": 1.0,
        "notional_usd": 250_000.0,
        "liquidity_usd": 2_000_000.0,
        "risk_flags": [],
        "data_quality": "ok",
        "shadow_only": True,
        "metadata": {},
    }
    payload.update(overrides)
    return ExternalSignalEvent.from_dict(payload)


def test_risk_guard_rejects_honeypot():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(metadata={"honeypot_risk": True}))

    assert decision.risk_decision == "reject"
    assert "honeypot_risk" in decision.reject_reasons


def test_risk_guard_rejects_low_liquidity():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(liquidity_usd=10_000.0))

    assert decision.risk_decision == "reject"
    assert "low_liquidity" in decision.reject_reasons


def test_risk_guard_rejects_high_sell_tax():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(metadata={"sell_tax_pct": 8.0}))

    assert decision.risk_decision == "reject"
    assert "high_sell_tax" in decision.reject_reasons


def test_risk_guard_rejects_high_holder_concentration():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(metadata={"top10_holder_share": 0.6}))

    assert decision.risk_decision == "reject"
    assert "high_top10_holder_share" in decision.reject_reasons


def test_risk_guard_rejects_high_smart_money_exit_rate():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(metadata={"smart_money_exit_rate": 0.9}))

    assert decision.risk_decision == "reject"
    assert "high_smart_money_exit_rate" in decision.reject_reasons


def test_risk_guard_rejects_degraded_data_quality():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(data_quality="degraded"))

    assert decision.risk_decision == "quarantine"
    assert "data_quality_degraded" in decision.reject_reasons


def test_risk_guard_rejects_cex_wide_spread():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_event(metadata={
        "spread_bps": 25.0,
        "depth_10bps_usd": 500_000.0,
        "orderbook_coverage": 1.0,
        "price_coverage": 1.0,
    }))

    assert decision.risk_decision == "reject"
    assert "wide_spread" in decision.reject_reasons


def test_risk_guard_rejects_cex_low_depth():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_event(metadata={
        "spread_bps": 3.0,
        "depth_10bps_usd": 50_000.0,
        "orderbook_coverage": 1.0,
        "price_coverage": 1.0,
    }))

    assert decision.risk_decision == "reject"
    assert "low_depth_10bps" in decision.reject_reasons


def test_risk_guard_accepts_clean_long_event():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_event())

    assert decision.risk_decision == "accept_for_shadow"
    assert decision.allowed_shadow_direction == "long"
    assert decision.reject_reasons == ()


def test_risk_guard_unknown_direction_becomes_observe_only():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_event(direction_hint="unknown"))

    assert decision.risk_decision == "accept_for_shadow"
    assert decision.allowed_shadow_direction == "observe_only"


def test_risk_guard_cex_event_does_not_require_token_tax_fields():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_event(metadata={
        "spread_bps": 3.0,
        "depth_10bps_usd": 500_000.0,
        "orderbook_coverage": 1.0,
        "price_coverage": 1.0,
    }))

    assert decision.risk_decision == "accept_for_shadow"


def test_risk_guard_token_event_does_not_require_cex_depth_fields():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event())

    assert decision.risk_decision == "accept_for_shadow"


def test_risk_guard_rejects_unknown_chain_or_missing_market_context():
    from src.research.external_signal_shadow.risk_guard import evaluate_event_risk

    decision = evaluate_event_risk(_token_event(chain="unknown"))

    assert decision.risk_decision == "reject"
    assert "unsupported_chain" in decision.reject_reasons
