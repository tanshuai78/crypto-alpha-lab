from src.research.external_signal_shadow.stage1_5c1_price_coverage_models import (
    PriceCoverageDecision,
    PriceCoverageEventReport,
    PriceKlineRow,
)


def test_price_kline_row_safety_fields():
    row = PriceKlineRow(
        symbol="ABCUSDT",
        bar_start_ms=1710000000000,
        bar_end_ms=1710000900000,
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.05,
        quote_volume=1000000.0,
        source="binance_um_futures_15m",
        source_quality="exchange_futures_kline_close_price_not_fill_price",
    )
    assert row.api_key_used is False
    assert row.private_endpoint_used is False
    assert row.paper_trading_allowed is False
    assert row.live_trading_allowed is False


def test_event_report_defaults_no_replay_for_spot_proxy():
    report = PriceCoverageEventReport(
        symbol_event_id="e1",
        event_type="futures_contract_launch",
        symbol="ABCUSDT",
        futures_symbol_status="futures_symbol_not_found",
        futures_kline_status="futures_symbol_not_found",
        spot_proxy_status="spot_proxy_available_report_only",
        replay_price_source_allowed="none",
        stage1_5c_rerun_candidate=False,
        coverage_reject_reason="futures_symbol_not_found",
    )
    assert report.spot_proxy_replay_allowed is False
    assert report.alpha_interpretation_allowed is False


def test_decision_enum_values():
    assert PriceCoverageDecision.READY.value == "stage1_5c1_price_coverage_ready_for_1_5c_rerun"
    assert PriceCoverageDecision.SPARSE.value == "stage1_5c1_price_coverage_sparse_inconclusive"
    assert PriceCoverageDecision.FAILED.value == "stage1_5c1_price_coverage_failed"
    assert PriceCoverageDecision.INVALID.value == "stage1_5c1_price_coverage_invalid"
