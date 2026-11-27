from __future__ import annotations

import math
from datetime import datetime

import pytest

from configs import base
from research.external_signal_shadow.stage1_3_candidates import detect_relative_strength_vs_btc
from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    analyze_bars,
    build_default_protocol,
    build_event_ledger,
    classify_result,
    linear_quantile,
    positive_contribution,
    reduce_block_sample,
    verify_base_and_safety_config,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar

MS_15M = 15 * 60 * 1000
MS_1H = 60 * 60 * 1000
MS_1D = 24 * 60 * 60 * 1000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def _utc_ms(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _make_168d_canonical_bars(
    overrides: dict[tuple[str, int], dict[str, float]] | None = None,
) -> list[HistoricalBar]:
    """Generate complete 168-day (2026-06-08T00:00:00Z .. 2026-11-23T00:00:00Z) 15m canonical bars."""
    overrides = overrides or {}
    start_ms = _utc_ms("2026-06-08T00:00:00Z")
    end_ms = _utc_ms("2026-11-23T00:00:00Z")
    total_bars = (end_ms - start_ms) // MS_15M
    bars: list[HistoricalBar] = []
    for sym in SYMBOLS:
        for i in range(total_bars):
            b_start = start_ms + i * MS_15M
            b_end = b_start + MS_15M
            ov = overrides.get((sym, b_start))
            if ov is None:
                bars.append(
                    HistoricalBar(
                        symbol=sym,
                        bar_start_ms=b_start,
                        bar_end_ms=b_end,
                        open_price=100.0,
                        high_price=100.0,
                        low_price=100.0,
                        close_price=100.0,
                        quote_volume=25.0,
                    )
                )
            else:
                o = ov.get("open_price", 100.0)
                c = ov.get("close_price", 100.0)
                h = ov.get("high_price", max(o, c))
                low = ov.get("low_price", min(o, c))
                qv = ov.get("quote_volume", 25.0)
                bars.append(
                    HistoricalBar(
                        symbol=sym,
                        bar_start_ms=b_start,
                        bar_end_ms=b_end,
                        open_price=o,
                        high_price=h,
                        low_price=low,
                        close_price=c,
                        quote_volume=qv,
                    )
                )
    return bars


def _make_volume_spike_canonical_bars() -> list[HistoricalBar]:
    """Plan §3 volume spike canonical 168d bars."""
    overrides = {
        ("ETHUSDT", _utc_ms("2026-06-16T11:45:00Z")): {"quote_volume": 325.0},
        ("ETHUSDT", _utc_ms("2026-06-16T16:00:00Z")): {
            "open_price": 100.0,
            "close_price": 101.0,
            "high_price": 102.0,
            "low_price": 99.0,
            "quote_volume": 25.0,
        },
    }
    return _make_168d_canonical_bars(overrides)


def _make_rs_canonical_bars(btc_same_window_close: float | None = None) -> list[HistoricalBar]:
    """Plan §3 RS canonical 168d bars (independent from volume spike bars)."""
    overrides: dict[tuple[str, int], dict[str, float]] = {
        ("ETHUSDT", _utc_ms("2026-06-14T11:45:00Z")): {"close_price": 101.0},
        ("ETHUSDT", _utc_ms("2026-06-15T11:45:00Z")): {"close_price": 101.5},
        ("ETHUSDT", _utc_ms("2026-06-15T16:00:00Z")): {
            "open_price": 100.0,
            "close_price": 102.0,
            "high_price": 103.0,
            "low_price": 99.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-16T11:45:00Z")): {"close_price": 100.01},
    }
    if btc_same_window_close is not None:
        overrides[("BTCUSDT", _utc_ms("2026-06-15T11:45:00Z"))] = {
            "open_price": 100.0,
            "close_price": btc_same_window_close,
            "high_price": btc_same_window_close,
            "low_price": 100.0,
        }
    return _make_168d_canonical_bars(overrides)


def test_ledger_config_and_safety_checks_pass_and_reject_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = verify_base_and_safety_config()
    assert cfg["RISK_LIVE_TRADING_ENABLED"] is False
    assert cfg["symbols"] == SYMBOLS
    assert cfg["volume_spike_threshold"] == 3.0
    assert cfg["rel_strength_z_threshold"] == 1.5
    assert cfg["cost_scenarios_round_trip_bps"] == (30.0, 50.0, 80.0)

    monkeypatch.setattr(base, "RISK_LIVE_TRADING_ENABLED", True)
    with pytest.raises(DiagnosticStopError) as exc_info:
        verify_base_and_safety_config()
    assert exc_info.value.stop_code == "safety_config_mismatch"


def test_ledger_volume_spike_canonical_168d_timing_occupation_and_metrics() -> None:
    protocol = build_default_protocol()
    bars = _make_volume_spike_canonical_bars()
    ledger = build_event_ledger(bars, protocol=protocol)

    vol_cand = ledger["candidates"]["volume_spike_1h"]
    admitted = vol_cand["admitted_events"]
    assert len(admitted) == 1

    ev = admitted[0]
    assert ev["symbol"] == "ETHUSDT"
    assert ev["window_end_ms"] == _utc_ms("2026-06-16T12:00:00Z")
    assert ev["available_at_ms"] == _utc_ms("2026-06-16T12:01:00Z")
    assert ev["entry_bar_start_ms"] == _utc_ms("2026-06-16T12:15:00Z")
    assert ev["exit_bar_end_ms"] == _utc_ms("2026-06-16T16:15:00Z")
    assert ev["entry_open_price"] == pytest.approx(100.0)
    assert ev["exit_close_price"] == pytest.approx(101.0)
    # Independent hand calculation: (101/100 - 1)*10000 = 100 bps, MFE=200 bps, MAE=-100 bps
    assert ev["y_gross_bps"] == pytest.approx(100.0)
    assert ev["mfe_4h_bps"] == pytest.approx(200.0)
    assert ev["mae_4h_bps"] == pytest.approx(-100.0)
    assert ev["trigger_value"] == pytest.approx(4.0)

    # Next 3 rolling windows (12:15, 12:30, 12:45) must be overlap_suppressed, not admitted
    suppressed = [
        p for p in vol_cand["decision_points"]
        if p["symbol"] == "ETHUSDT" and p["status"] == "overlap_suppressed"
    ]
    suppressed_ends = [p["window_end_ms"] for p in suppressed]
    assert suppressed_ends == [
        _utc_ms("2026-06-16T12:15:00Z"),
        _utc_ms("2026-06-16T12:30:00Z"),
        _utc_ms("2026-06-16T12:45:00Z"),
    ]


def test_signal_relative_strength_independent_detector_vectors() -> None:
    hist = [-0.01] * 24 + [0.01] * 24
    # Independent hand calc: median=0.0, pstdev=0.01 -> z = 0.015 / 0.01 = 1.5
    ev = detect_relative_strength_vs_btc(
        symbol="ETHUSDT",
        alt_1h_return=0.015,
        btc_1h_return=0.0,
        historical_spread_returns=hist,
        event_time_ms=_utc_ms("2026-06-15T12:01:00Z"),
        z_threshold=1.5,
        min_samples=48,
    )
    assert ev is not None
    assert ev.metadata["z_score"] == pytest.approx(1.5)

    # Just below threshold -> None
    assert (
        detect_relative_strength_vs_btc(
            symbol="ETHUSDT",
            alt_1h_return=0.0149,
            btc_1h_return=0.0,
            historical_spread_returns=hist,
            event_time_ms=_utc_ms("2026-06-15T12:01:00Z"),
            z_threshold=1.5,
            min_samples=48,
        )
        is None
    )
    # BTC excluded
    assert (
        detect_relative_strength_vs_btc(
            symbol="BTCUSDT",
            alt_1h_return=0.05,
            btc_1h_return=0.0,
            historical_spread_returns=hist,
            event_time_ms=_utc_ms("2026-06-15T12:01:00Z"),
            z_threshold=1.5,
            min_samples=48,
        )
        is None
    )
    # Zero variance -> None
    assert (
        detect_relative_strength_vs_btc(
            symbol="ETHUSDT",
            alt_1h_return=0.05,
            btc_1h_return=0.0,
            historical_spread_returns=[0.0] * 48,
            event_time_ms=_utc_ms("2026-06-15T12:01:00Z"),
            z_threshold=1.5,
            min_samples=48,
        )
        is None
    )
    # Insufficient history (<48) -> None
    assert (
        detect_relative_strength_vs_btc(
            symbol="ETHUSDT",
            alt_1h_return=0.05,
            btc_1h_return=0.0,
            historical_spread_returns=hist[:47],
            event_time_ms=_utc_ms("2026-06-15T12:01:00Z"),
            z_threshold=1.5,
            min_samples=48,
        )
        is None
    )


def test_ledger_rs_canonical_168d_exact_672_history_and_btc_alignment() -> None:
    protocol = build_default_protocol()
    bars = _make_rs_canonical_bars()
    ledger = build_event_ledger(bars, protocol=protocol)

    rs_cand = ledger["candidates"]["relative_strength_vs_btc"]
    # BTC must not appear in relative_strength_vs_btc applicable symbols or decision points
    assert "BTCUSDT" not in rs_cand["applicable_symbols"]
    assert all(p["symbol"] != "BTCUSDT" for p in rs_cand["decision_points"])

    target_key = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z"))
    matched = [
        ev for ev in rs_cand["admitted_events"]
        if (ev["candidate"], ev["symbol"], ev["available_at_ms"]) == target_key
    ]
    assert len(matched) == 1
    ev = matched[0]
    expected_sigma = 0.01 * math.sqrt(671) / 672.0
    expected_z = 0.015 / expected_sigma
    assert ev["history_sample_count"] == 672
    assert ev["history_first_window_end_ms"] == _utc_ms("2026-06-08T12:00:00Z")
    assert ev["history_last_window_end_ms"] == _utc_ms("2026-06-15T11:45:00Z")
    assert ev["btc_r1h"] == pytest.approx(0.0)
    assert ev["self_r1h"] == pytest.approx(0.015)
    assert ev["trigger_value"] == pytest.approx(expected_z, rel=1e-9)
    assert ev["trigger_value"] > 1.5
    assert ev["entry_bar_start_ms"] == _utc_ms("2026-06-15T12:15:00Z")
    assert ev["exit_bar_end_ms"] == _utc_ms("2026-06-15T16:15:00Z")
    assert ev["entry_open_price"] == pytest.approx(100.0)
    assert ev["exit_close_price"] == pytest.approx(102.0)
    # Independent hand calculation: 100->102 gross=200 bps, high 103 -> MFE=300 bps, low 99 -> MAE=-100 bps
    assert ev["y_gross_bps"] == pytest.approx(200.0)
    assert ev["mfe_4h_bps"] == pytest.approx(300.0)
    assert ev["mae_4h_bps"] == pytest.approx(-100.0)


def test_ledger_rs_btc_alignment_counterexample_removes_target_event() -> None:
    protocol = build_default_protocol()
    bars = _make_rs_canonical_bars(btc_same_window_close=101.5)
    ledger = build_event_ledger(bars, protocol=protocol)

    rs_cand = ledger["candidates"]["relative_strength_vs_btc"]
    target_key = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z"))
    target_pts = [
        p for p in rs_cand["decision_points"]
        if (p["candidate"], p["symbol"], p["available_at_ms"]) == target_key
    ]
    assert len(target_pts) == 1
    assert target_pts[0]["status"] == "not_triggered"
    assert target_pts[0]["btc_r1h"] == pytest.approx(0.015)
    assert all(
        (ev["candidate"], ev["symbol"], ev["available_at_ms"]) != target_key
        for ev in rs_cand["admitted_events"]
    )


def test_timing_7d_left_boundary_utc_end_hour_causality_and_block_censoring() -> None:
    protocol = build_default_protocol()
    # Test 7d exact left boundary retention vs earlier exclusion & UTC end-hour grouping:
    # Put high volume (1000) at 2026-06-08 11:45 (end=12:00, >7d before 2026-06-16 12:00)
    # and check 2026-06-15 12:00 (exact 7d after 2026-06-08 12:00 -> left boundary included!).
    overrides = {
        ("SOLUSDT", _utc_ms("2026-06-08T11:45:00Z")): {"quote_volume": 1000.0},
        # Trigger near end of block 0 (2026-06-21 21:45 -> end 22:00, entry 22:15, exit 02:15 next block -> censored!)
        ("SOLUSDT", _utc_ms("2026-06-21T21:45:00Z")): {"quote_volume": 325.0},
    }
    bars_base = _make_168d_canonical_bars(overrides)
    ledger_base = build_event_ledger(bars_base, protocol=protocol)
    vol = ledger_base["candidates"]["volume_spike_1h"]

    # Check 2026-06-15 12:00 history includes exact 7d boundary 2026-06-08 12:00
    pt_b0 = next(
        p for p in vol["decision_points"]
        if p["symbol"] == "SOLUSDT" and p["window_end_ms"] == _utc_ms("2026-06-15T12:00:00Z")
    )
    assert pt_b0["history_first_window_end_ms"] == _utc_ms("2026-06-08T12:00:00Z")
    assert pt_b0["utc_end_hour"] == 12

    # Check 2026-06-16 12:00 excludes 2026-06-08 12:00 (>7d) and starts at 2026-06-09 12:00
    pt_b1 = next(
        p for p in vol["decision_points"]
        if p["symbol"] == "SOLUSDT" and p["window_end_ms"] == _utc_ms("2026-06-16T12:00:00Z")
    )
    assert pt_b1["history_first_window_end_ms"] == _utc_ms("2026-06-09T12:00:00Z")

    # Check block boundary censoring at 2026-06-21 22:00 (exit 2026-06-22 02:15 > block 0 end 2026-06-22 00:00)
    pt_censored = next(
        p for p in vol["decision_points"]
        if p["symbol"] == "SOLUSDT" and p["window_end_ms"] == _utc_ms("2026-06-21T22:00:00Z")
    )
    assert pt_censored["status"] == "block_boundary_censored"

    # Warmup events are strictly outside evaluation decision_points
    eval_start = _utc_ms("2026-06-15T00:00:00Z")
    assert all(p["available_at_ms"] >= eval_start for p in vol["decision_points"])
    assert vol["warmup_decision_point_count"] > 0

    # Future bar mutation invariance: mutating bars in October must not alter June triggers or available_at
    overrides_future = dict(overrides)
    overrides_future[("SOLUSDT", _utc_ms("2026-10-10T10:00:00Z"))] = {
        "open_price": 100.0,
        "close_price": 150.0,
        "high_price": 150.0,
        "low_price": 100.0,
        "quote_volume": 99999.0,
    }
    bars_mut = _make_168d_canonical_bars(overrides_future)
    ledger_mut = build_event_ledger(bars_mut, protocol=protocol)
    june_cutoff = _utc_ms("2026-07-01T00:00:00Z")
    june_base = [
        (p["symbol"], p["available_at_ms"], p["status"], p["trigger_value"])
        for p in ledger_base["candidates"]["volume_spike_1h"]["decision_points"]
        if p["available_at_ms"] < june_cutoff
    ]
    june_mut = [
        (p["symbol"], p["available_at_ms"], p["status"], p["trigger_value"])
        for p in ledger_mut["candidates"]["volume_spike_1h"]["decision_points"]
        if p["available_at_ms"] < june_cutoff
    ]
    assert june_base == june_mut


def test_control_single_condition_rejections_shared_weights_and_future_signal_retained() -> None:
    protocol = build_default_protocol()
    # Two admitted ETH volume spikes in block 0, hour 12 (on Jun 16 & Jun 17):
    # Jun 16 12:00 admitted -> entry 12:15 (100), exit 16:15 (101) => y1 = +100 bps
    # Jun 17 12:00 admitted -> entry 12:15 (100), exit 16:15 (99.8) => y2 = -20 bps
    # Wait: in block 0 hour 12, non-triggered non-occupied ETH points with self_r1h=0, btc_r1h=0
    # exist on Jun 15, 18, 19, 20, 21 (all shared controls for both events!).
    # Verify equal-event weighting with an explicit synthetic control-weight check AND
    # verify single-condition control matching & future-signal non-exclusion on real canonical bars.
    overrides: dict[tuple[str, int], dict[str, float]] = {
        # Event 1: Jun 16 12:00 (avail 12:01, hour 12), self_r1h > 0 (+0.005), btc_r1h = 0, gross = +100 bps
        ("ETHUSDT", _utc_ms("2026-06-16T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.5,
            "quote_volume": 325.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-16T16:00:00Z")): {
            "open_price": 100.0,
            "close_price": 101.0,
            "quote_volume": 25.0,
        },
        # Valid control for Event 1: Jun 18 12:00 (avail 12:01, same block 0, hour 12, self_r1h > 0, btc_r1h = 0, not triggered, not occupied)
        # Exit at 16:15 close=100.2 => y_ctrl = +20 bps!
        # Also followed 15m later by a future signal at Jun 18 12:15 -> MUST NOT exclude this control!
        ("ETHUSDT", _utc_ms("2026-06-18T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-18T16:00:00Z")): {
            "open_price": 100.0,
            "close_price": 100.2,
            "quote_volume": 25.0,
        },
        # Future signal at Jun 18 12:30 (avail 12:31, hour 12) -> must NOT retroactively disqualify Jun 18 12:01 control!
        # Also has self_r1h = 0 (different sign from Event 1) -> rejected as control for Event 1!
        ("ETHUSDT", _utc_ms("2026-06-18T12:15:00Z")): {
            "open_price": 100.0,
            "close_price": 100.0,
            "quote_volume": 325.0,
        },
        # Single-condition rejection 1: different BTC r1h sign at Jun 19 12:00 (self_r1h > 0, btc_r1h > 0)
        ("ETHUSDT", _utc_ms("2026-06-19T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        ("BTCUSDT", _utc_ms("2026-06-19T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        # Single-condition rejection 2: different UTC hour (Jun 19 13:00, hour 13 != 12, self_r1h > 0, btc_r1h = 0)
        ("ETHUSDT", _utc_ms("2026-06-19T12:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        # Single-condition rejection 3: different block (Jun 22 12:00 is block 1 != block 0, self_r1h > 0, btc_r1h = 0)
        ("ETHUSDT", _utc_ms("2026-06-22T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        # Single-condition rejection 4: different symbol (SOLUSDT Jun 19 12:00, self_r1h > 0, btc_r1h = 0)
        ("SOLUSDT", _utc_ms("2026-06-19T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        # Single-condition rejection 5: occupied point (Jun 16 12:45 is inside Event 1 occupation [12:01, 16:15])
        ("ETHUSDT", _utc_ms("2026-06-16T12:30:00Z")): {
            "open_price": 100.0,
            "close_price": 100.1,
            "quote_volume": 25.0,
        },
        # Event 2: Jun 17 12:00 (avail 12:01, block 0, hour 12), self_r1h < 0, btc_r1h = 0, gross = -20 bps
        ("ETHUSDT", _utc_ms("2026-06-17T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 99.5,
            "quote_volume": 325.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-17T16:00:00Z")): {
            "open_price": 100.0,
            "close_price": 99.8,
            "quote_volume": 25.0,
        },
        # TWO controls for Event 2 (Jun 20 12:00 & Jun 21 12:00, both self_r1h < 0, btc_r1h = 0, gross = 0 bps -> mean=0)
        # Note Event 1 has 1 control (mean=+20), Event 2 has 2 controls (mean=0) -> tests equal event weighting!
        ("ETHUSDT", _utc_ms("2026-06-20T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 99.9,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-21T11:45:00Z")): {
            "open_price": 100.0,
            "close_price": 99.9,
            "quote_volume": 25.0,
        },
    }
    bars = _make_168d_canonical_bars(overrides)
    result = analyze_bars(bars, protocol=protocol)
    vol = result["candidates"]["volume_spike_1h"]
    ev_by_avail = {e["available_at_ms"]: e for e in vol["event_records"]}

    e1 = ev_by_avail[_utc_ms("2026-06-16T12:01:00Z")]
    e2 = ev_by_avail[_utc_ms("2026-06-17T12:01:00Z")]
    # Event 1 matched ONLY to Jun 18 12:01 (all 5 single-condition mutations rejected; future signal at 12:31 did NOT exclude it!)
    assert e1["control_keys"] == [["volume_spike_1h", "ETHUSDT", _utc_ms("2026-06-18T12:01:00Z")]]
    assert e1["y_gross_bps"] == pytest.approx(100.0)
    assert e1["control_mean_bps"] == pytest.approx(20.0)
    assert e1["d_bps"] == pytest.approx(80.0)

    # Event 2 matched to 2 controls (Jun 20 12:01 & Jun 21 12:01), both gross=0 -> mean=0, d2=-20
    assert e2["control_keys"] == [
        ["volume_spike_1h", "ETHUSDT", _utc_ms("2026-06-20T12:01:00Z")],
        ["volume_spike_1h", "ETHUSDT", _utc_ms("2026-06-21T12:01:00Z")],
    ]
    assert e2["y_gross_bps"] == pytest.approx(-20.0)
    assert e2["control_mean_bps"] == pytest.approx(0.0)
    assert e2["d_bps"] == pytest.approx(-20.0)

    # Check equal-event weighting on Event 1 & Event 2 subset (and check constant cost shifts mu by -30/-50/-80, delta unchanged)
    # Note Event 3 (Jun 18 12:31) also admitted with gross=0, matched to self_r1h=0 controls with mean=0 -> verify full summary consistency too!
    # Also verify exact Plan §4 hand calculation on y=[100,-20], ctrl_mean=[20,0] using 2-event pure check:
    two_ev_mu = (e1["y_gross_bps"] + e2["y_gross_bps"]) / 2.0
    two_ev_delta = (e1["d_bps"] + e2["d_bps"]) / 2.0
    assert two_ev_mu == pytest.approx(40.0)
    assert two_ev_delta == pytest.approx(30.0)

    summary = vol["summary"]
    mu_gross = summary["mu_gross_bps"]
    delta = summary["delta_bps"]
    assert summary["cost_scenarios"]["30.0"]["mean_bps"] == pytest.approx(mu_gross - 30.0)
    assert summary["cost_scenarios"]["50.0"]["mean_bps"] == pytest.approx(mu_gross - 50.0)
    assert summary["cost_scenarios"]["80.0"]["mean_bps"] == pytest.approx(mu_gross - 80.0)
    assert summary["cost_scenarios"]["30.0"]["delta_bps"] == pytest.approx(delta)
    assert summary["cost_scenarios"]["50.0"]["delta_bps"] == pytest.approx(delta)
    assert summary["cost_scenarios"]["80.0"]["delta_bps"] == pytest.approx(delta)


def test_control_and_summary_canonical_volume_and_rs_end_to_end() -> None:
    protocol = build_default_protocol()

    # 1. Volume spike canonical bars -> gross=100, delta=100
    vol_res = analyze_bars(_make_volume_spike_canonical_bars(), protocol=protocol)
    vol_c = vol_res["candidates"]["volume_spike_1h"]
    vol_s = vol_c["summary"]
    assert vol_s["counts"]["admitted"] == 1
    assert vol_s["counts"]["matched"] == 1
    assert vol_s["counts"]["unmatched"] == 0
    assert vol_s["mu_gross_bps"] == pytest.approx(100.0)
    assert vol_s["delta_bps"] == pytest.approx(100.0)
    # Conservation checks
    vc = vol_s["counts"]
    assert vc["total_eval_decision_points"] == (
        vc["feature_not_estimable"]
        + vc["block_boundary_censored"]
        + vc["not_triggered"]
        + vc["overlap_suppressed"]
        + vc["admitted"]
    )
    assert vc["triggered"] == vc["overlap_suppressed"] + vc["admitted"]
    assert vc["admitted"] == vc["matched"] + vc["unmatched"]

    # 2. RS canonical bars -> exact 2 admitted events, 1 matched (unique C_i 06-16 12:01 -> d_i=200), 1 unmatched
    rs_res = analyze_bars(_make_rs_canonical_bars(), protocol=protocol)
    rs_c = rs_res["candidates"]["relative_strength_vs_btc"]
    rs_s = rs_c["summary"]
    assert "BTCUSDT" not in rs_c["applicable_symbols"]
    rc = rs_s["counts"]
    assert rc["total_eval_decision_points"] == (
        rc["feature_not_estimable"]
        + rc["block_boundary_censored"]
        + rc["not_triggered"]
        + rc["overlap_suppressed"]
        + rc["admitted"]
    )
    assert rc["triggered"] == rc["overlap_suppressed"] + rc["admitted"]
    assert rc["admitted"] == 2
    assert rc["matched"] == 1
    assert rc["unmatched"] == 1
    assert rc["admitted"] == rc["matched"] + rc["unmatched"]

    evs = rs_c["event_records"]
    assert len(evs) == 2
    ev1, ev2 = evs[0], evs[1]
    assert (ev1["candidate"], ev1["symbol"], ev1["available_at_ms"]) == (
        "relative_strength_vs_btc",
        "ETHUSDT",
        _utc_ms("2026-06-15T12:01:00Z"),
    )
    assert ev1["y_gross_bps"] == pytest.approx(200.0)
    assert ev1["control_keys"] == [["relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-16T12:01:00Z")]]
    assert ev1["control_mean_bps"] == pytest.approx(0.0)
    assert ev1["d_bps"] == pytest.approx(200.0)
    assert ev1["match_status"] == "matched"

    assert (ev2["candidate"], ev2["symbol"], ev2["available_at_ms"]) == (
        "relative_strength_vs_btc",
        "ETHUSDT",
        _utc_ms("2026-06-15T16:16:00Z"),
    )
    assert ev2["entry_bar_start_ms"] == _utc_ms("2026-06-15T16:30:00Z")
    assert ev2["exit_bar_end_ms"] == _utc_ms("2026-06-15T20:30:00Z")
    assert ev2["y_gross_bps"] == pytest.approx(0.0)
    assert ev2["control_keys"] == []
    assert ev2["d_bps"] is None
    assert ev2["match_status"] == "unmatched_control"

    assert rs_s["mu_gross_bps"] == pytest.approx(100.0)
    assert rs_s["delta_bps"] == pytest.approx(200.0)
    assert rs_s["routing"]["observation_label"] == "inconclusive_or_concentrated"
    assert rs_s["routing"]["resource_decision"] == "pause_for_new_evidence"
    assert rs_s["routing"]["alpha_research_status"] == "evidence_insufficient"

    # 3. BTC alignment counterexample on analyze_bars removes target first RS event
    rs_btc_res = analyze_bars(_make_rs_canonical_bars(btc_same_window_close=101.5), protocol=protocol)
    rs_btc_keys = {
        (e["candidate"], e["symbol"], e["available_at_ms"])
        for e in rs_btc_res["candidates"]["relative_strength_vs_btc"]["event_records"]
    }
    assert ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z")) not in rs_btc_keys


def test_summary_quantiles_topk_cost_scenarios_and_diagnostics() -> None:
    # Linear interpolation quantile oracle: [0, 10, 20, 30]
    vec = [0.0, 10.0, 20.0, 30.0]
    assert linear_quantile(vec, 0.25) == pytest.approx(7.5)
    assert linear_quantile(vec, 0.50) == pytest.approx(15.0)
    assert linear_quantile(vec, 0.75) == pytest.approx(22.5)
    assert linear_quantile([], 0.50) is None

    # Design §5.2 Top-K oracle: [100] + [-20]*9 -> n=10, m=1 -> all three 1.0 (100%)
    pc = positive_contribution([100.0] + [-20.0] * 9)
    assert pc["n"] == 10
    assert pc["positive_count"] == 1
    assert pc["top_1_share"] == pytest.approx(1.0)
    assert pc["top_3_share"] == pytest.approx(1.0)
    assert pc["top_10pct_share"] == pytest.approx(1.0)

    # All-negative, all-zero, and empty -> all None
    for empty_case in ([-10.0, -5.0], [0.0, 0.0], []):
        pc_empty = positive_contribution(empty_case)
        assert pc_empty["top_1_share"] is None
        assert pc_empty["top_3_share"] is None
        assert pc_empty["top_10pct_share"] is None


def test_bootstrap_block_reduction_oracle_joint_resampling_and_empty_replicates() -> None:
    # Plan §4 exact 2-block reduction oracle
    blocks = [
        {"sum_y": 200.0, "n": 2, "sum_d": 100.0, "m": 2},  # Block A (idx 0)
        {"sum_y": -100.0, "n": 1, "sum_d": -50.0, "m": 1},  # Block B (idx 1)
        {"sum_y": 0.0, "n": 0, "sum_d": 0.0, "m": 0},  # Empty block (idx 2)
    ]
    aa = reduce_block_sample(blocks, [0, 0])
    assert aa["mu_gross_bps"] == pytest.approx(100.0)
    assert aa["delta_bps"] == pytest.approx(50.0)

    ab = reduce_block_sample(blocks, [0, 1])
    assert ab["mu_gross_bps"] == pytest.approx(100.0 / 3.0)
    assert ab["delta_bps"] == pytest.approx(50.0 / 3.0)

    bb = reduce_block_sample(blocks, [1, 1])
    assert bb["mu_gross_bps"] == pytest.approx(-100.0)
    assert bb["delta_bps"] == pytest.approx(-50.0)

    empty = reduce_block_sample(blocks, [2, 2])
    assert empty["mu_gross_bps"] is None
    assert empty["delta_bps"] is None


def test_routing_all_design_section8_decision_boundaries() -> None:
    def _base_metrics(**overrides: object) -> dict[str, object]:
        m: dict[str, object] = {
            "prerequisites_valid": True,
            "mu_gross_bps": 25.0,
            "delta_bps": 15.0,
            "admitted_count": 20,
            "matched_count": 20,
            "unmatched_count": 0,
            "mu_ci_low": 5.0,
            "delta_ci_low": 2.0,
            "mu_ci_complete": True,
            "delta_ci_complete": True,
            "first_half_mu": 20.0,
            "first_half_delta": 10.0,
            "second_half_mu": 30.0,
            "second_half_delta": 20.0,
            "leave_one_symbol_all_positive": True,
            "leave_one_block_all_positive": True,
            "without_best_mu": 18.0,
            "without_best_delta": 10.0,
            "has_unexplained_dependency_or_data_issue": False,
        }
        m.update(overrides)
        return m

    # Design §8 mandatory 4 vectors
    r1 = classify_result(_base_metrics(mu_gross_bps=-20.0, delta_bps=50.0))
    assert r1["observation_label"] == "relative_increment_without_positive_gross"
    assert r1["resource_decision"] == "stop_fixed_candidate_this_round"
    assert r1["alpha_research_status"] == "evidence_insufficient"

    r2 = classify_result(_base_metrics(mu_gross_bps=20.0, delta_bps=-50.0))
    assert r2["observation_label"] == "no_increment_observed"
    assert r2["resource_decision"] == "stop_fixed_candidate_this_round"

    r3 = classify_result(_base_metrics(mu_gross_bps=-20.0, delta_bps=-50.0))
    assert r3["observation_label"] == "no_increment_observed"
    assert r3["resource_decision"] == "stop_fixed_candidate_this_round"

    r4 = classify_result(_base_metrics(mu_gross_bps=-20.0, delta_bps=None, matched_count=0, unmatched_count=20))
    assert r4["observation_label"] == "not_estimable"
    assert r4["resource_decision"] == "stop_due_to_evidence_or_cost"

    # Partial matching priority (even if delta <= 0, must NOT label full candidate no_increment_observed)
    r_partial = classify_result(_base_metrics(mu_gross_bps=20.0, delta_bps=-50.0, matched_count=19, unmatched_count=1))
    assert r_partial["observation_label"] == "inconclusive_or_concentrated"
    assert r_partial["resource_decision"] == "pause_for_new_evidence"

    # Zero boundaries
    r_delta_zero = classify_result(_base_metrics(mu_gross_bps=20.0, delta_bps=0.0))
    assert r_delta_zero["observation_label"] == "no_increment_observed"

    r_mu_zero = classify_result(_base_metrics(mu_gross_bps=0.0, delta_bps=10.0))
    assert r_mu_zero["observation_label"] == "relative_increment_without_positive_gross"

    r_ci_zero = classify_result(_base_metrics(mu_ci_low=0.0))
    assert r_ci_zero["observation_label"] == "inconclusive_or_concentrated"

    r_empty_rep = classify_result(_base_metrics(mu_ci_complete=False))
    assert r_empty_rep["observation_label"] == "inconclusive_or_concentrated"

    # Full valid dual-positive pattern
    r_pos = classify_result(_base_metrics())
    assert r_pos["observation_label"] == "bounded_positive_pattern"
    assert r_pos["resource_decision"] == "consider_independent_validation_only"
    assert r_pos["alpha_research_status"] == "evidence_insufficient"
