from strategies.extreme_funding.scanner import ExtremeFundingWatchEvent


def test_watch_event_contract_is_observation_only():
    event = ExtremeFundingWatchEvent(
        strategy_type="extreme_funding",
        symbol="DOGE/USDT",
        exchange="binance",
        level="watch_level_1",
        premium_annualized_estimate_pct=35.0,
        micro_persistence=0.55,
        oi_change_1h_pct=None,
        reason="premium_persistent",
        reject_reason=None,
        executable=False,
        metadata={
            "mode": "observation",
            "estimate_type": "naive_premium_annualization",
            "not_settled_funding": True,
        },
    )

    assert event.strategy_type == "extreme_funding"
    assert event.executable is False
    assert event.metadata["mode"] == "observation"
    assert event.metadata["estimate_type"] == "naive_premium_annualization"
    assert event.metadata["not_settled_funding"] is True
