from __future__ import annotations

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_orchestrator import run_stage1_3_candidate_discovery

MS_15M = 15 * 60 * 1000
REQUIRED_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def _bars(symbol: str, count: int) -> list[HistoricalBar]:
    rows: list[HistoricalBar] = []
    for i in range(count):
        close = 100.0 + i * 0.01
        volume = 1_000_000.0
        if symbol == "ETHUSDT" and i % 20 in {4, 5, 6, 7}:
            volume = 10_000_000.0
            close += 5.0
        rows.append(HistoricalBar(symbol, i * MS_15M, (i + 1) * MS_15M, close, close, close, close, volume))
    return rows


def _required_bars(count: int) -> list[HistoricalBar]:
    rows: list[HistoricalBar] = []
    for symbol in REQUIRED_SYMBOLS:
        rows.extend(_bars(symbol, count))
    return rows


def test_stage1_3_orchestrator_returns_safe_summary_shape() -> None:
    bars = _required_bars(240)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    assert summary["decision"] == "stage1_3_candidate_signal_discovery_completed"
    assert summary["alpha_interpretation_allowed"] is False
    assert summary["collector_expansion_allowed"] is False
    assert summary["historical_venue"] == "binance_proxy"
    assert summary["venue_proxy_used"] is True
    assert "candidate_results" in summary


def test_stage1_3_orchestrator_generates_volume_spike_candidate_events() -> None:
    bars = _required_bars(400)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    by_name = {item["candidate_name"]: item for item in summary["candidate_results"]}
    assert by_name["volume_spike_1h"]["candidate_role"] == "primary"
    assert by_name["volume_spike_1h"]["event_count"] > 0
    assert by_name["price_move_15m"]["candidate_role"] == "baseline"
    assert by_name["cross_symbol_rotation"]["candidate_role"] == "diagnostic"


def test_orchestrator_computes_forward_metrics_and_500_random_baseline_trials() -> None:
    bars = _required_bars(500)
    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )
    by_name = {item["candidate_name"]: item for item in summary["candidate_results"]}
    volume = by_name["volume_spike_1h"]
    assert volume["random_baseline_trials"] == 500
    assert "baseline_primary_metric_median" in volume
    assert "candidate_vs_baseline_percentile" in volume
    assert "baseline_excess_net_bps" in volume
    assert "median_net_return_after_50bps" in volume


def test_orchestrator_computes_top5_positive_pnl_share_from_event_pnl() -> None:
    bars = _required_bars(500)
    summary = run_stage1_3_candidate_discovery(bars, historical_venue="binance_proxy", venue_proxy_used=True)
    volume = {item["candidate_name"]: item for item in summary["candidate_results"]}["volume_spike_1h"]
    assert "top_5_positive_events_gross_profit_share" in volume
    assert "top_5_events_abs_pnl_share" in volume
    assert "left_tail_p05_after_50bps_vs_baseline_bps" in volume


def test_bar_coverage_below_min_blocks_replay() -> None:
    interval = 15 * 60 * 1000
    # Provide all required symbols, but BTCUSDT has a gap (coverage = 2/3 = 0.67 < 0.98).
    bars = _bars("ETHUSDT", 3) + _bars("SOLUSDT", 3) + _bars("XRPUSDT", 3) + _bars("DOGEUSDT", 3) + [
        HistoricalBar("BTCUSDT", 0, interval, 100, 100, 100, 100, 1),
        HistoricalBar("BTCUSDT", 2 * interval, 3 * interval, 100, 100, 100, 100, 1),
    ]
    summary = run_stage1_3_candidate_discovery(bars, historical_venue="binance_proxy", venue_proxy_used=True)
    assert summary["decision"] == "stage1_3_candidate_signal_discovery_failed"
    assert summary["primary_blocker"] == "bar_coverage_below_min"
    assert summary["next_action"] == "fix_data_or_stop"


def test_missing_required_symbols_blocks_research_replay() -> None:
    bars = _bars("BTCUSDT", 240) + _bars("ETHUSDT", 240) + _bars("SOLUSDT", 240)

    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )

    assert summary["decision"] == "stage1_3_candidate_signal_discovery_failed"
    assert summary["primary_blocker"] == "missing_required_symbols"
    assert summary["missing_required_symbols"] == ["DOGEUSDT", "XRPUSDT"]


def test_duplicate_bar_start_blocks_research_replay() -> None:
    bars = _required_bars(240)
    bars.append(HistoricalBar("BTCUSDT", 0, MS_15M, 100, 100, 100, 100, 1))

    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )

    assert summary["decision"] == "stage1_3_candidate_signal_discovery_failed"
    assert summary["primary_blocker"] == "duplicate_bar_start_ms"
    assert summary["duplicate_bar_start_ms_by_symbol"] == {"BTCUSDT": [0]}


def test_symbol_bar_count_reports_input_bar_count_not_event_count() -> None:
    bars = _required_bars(240)

    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue="binance_proxy",
        venue_proxy_used=True,
    )

    assert summary["symbol_bar_count"] == {symbol: 240 for symbol in REQUIRED_SYMBOLS}
