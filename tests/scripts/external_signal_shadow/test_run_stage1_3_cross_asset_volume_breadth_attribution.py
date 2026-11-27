from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import scripts.external_signal_shadow.run_stage1_3_cross_asset_volume_breadth_attribution as attr_mod
from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    build_default_protocol,
    build_event_ledger,
)
from scripts.external_signal_shadow.run_stage1_3_cross_asset_volume_breadth_attribution import (
    AttributionStopError,
    annotate_breadth,
    describe_attribution,
)
from scripts.external_signal_shadow.run_stage1_3_volume_strength_conditional_increment import (
    build_cohort,
    summarize_cohort,
)
from tests.scripts.external_signal_shadow.test_run_stage1_3_volume_strength_conditional_increment import (
    _make_168d_canonical_bars,
    _make_plan_section4_dual_rs_with_volume_bars,
    _serialize_and_reload_ledger_rows,
)

CAND_A = "volume_spike_1h"
CAND_B = "relative_strength_vs_btc"
MS_15M = 15 * 60 * 1000
MS_1H = 60 * 60 * 1000


def _utc_ms(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _make_a_row(
    symbol: str,
    avail_ms: int,
    *,
    status: str = "not_triggered",
    trigger_value: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    win_end = avail_ms - 60_000
    win_start = None if status == "feature_not_estimable" else (win_end - MS_1H)
    row: dict[str, Any] = {
        "candidate": CAND_A,
        "symbol": symbol,
        "window_start_ms": win_start,
        "window_end_ms": win_end,
        "available_at_ms": avail_ms,
        "status": status,
        "trigger_value": trigger_value,
    }
    if extra:
        row.update(extra)
    return row


def test_breadth_three_valued_oracle() -> None:
    """Task 1: exact (t-L, t] 4-slot grid, repeated trigger=1 coin, trigger+unknown=1, null propagation, and invalid inputs."""
    proto = build_default_protocol()
    t = _utc_ms("2026-06-15T12:01:00Z")
    u1 = _utc_ms("2026-06-15T11:16:00Z")
    u2 = _utc_ms("2026-06-15T11:31:00Z")
    u3 = _utc_ms("2026-06-15T11:46:00Z")
    u4 = _utc_ms("2026-06-15T12:01:00Z")
    target = [(CAND_B, "ETHUSDT", t)]

    # 1. SOL triggered twice (admitted=4.0 at 11:31, overlap_suppressed=4.0 at 11:46), XRP 4x not_triggered,
    #    DOGE missing 11:16 but admitted=3.0 at 12:01 -> H=(SOL:1, XRP:0, DOGE:1), G=2!
    rows_case1 = [
        _make_a_row("SOLUSDT", u1, status="not_triggered", trigger_value=None),
        _make_a_row("SOLUSDT", u2, status="admitted", trigger_value=4.0),
        _make_a_row("SOLUSDT", u3, status="overlap_suppressed", trigger_value=4.0),
        _make_a_row("SOLUSDT", u4, status="not_triggered", trigger_value=None),
        _make_a_row("XRPUSDT", u1),
        _make_a_row("XRPUSDT", u2),
        _make_a_row("XRPUSDT", u3),
        _make_a_row("XRPUSDT", u4),
        # DOGE u1 intentionally omitted (missing_row), u2/u3 not_triggered, u4 admitted=3.0
        _make_a_row("DOGEUSDT", u2),
        _make_a_row("DOGEUSDT", u3),
        _make_a_row("DOGEUSDT", u4, status="admitted", trigger_value=3.0),
    ]
    res1 = annotate_breadth(target, rows_case1, protocol=proto)
    assert res1["target_count"] == 1
    assert res1["known_g_count"] == 1
    assert res1["unknown_g_count"] == 0
    ann1 = res1["annotations"][0]
    assert ann1["expected_u_ms"] == [u1, u2, u3, u4]
    assert ann1["h_by_symbol"] == {"SOLUSDT": 1, "XRPUSDT": 0, "DOGEUSDT": 1}
    assert ann1["breadth_g"] == 2

    # 2. Change DOGE 12:01 to not_triggered/None while u1 remains missing -> DOGE=None, G=None, target preserved!
    rows_case2 = [
        r if not (r["symbol"] == "DOGEUSDT" and r["available_at_ms"] == u4) else _make_a_row("DOGEUSDT", u4)
        for r in copy.deepcopy(rows_case1)
    ]
    res2 = annotate_breadth(target, rows_case2, protocol=proto)
    assert res2["target_count"] == 1
    assert res2["known_g_count"] == 0
    assert res2["unknown_g_count"] == 1
    ann2 = res2["annotations"][0]
    assert ann2["target_key"] == [CAND_B, "ETHUSDT", t]
    assert ann2["h_by_symbol"] == {"SOLUSDT": 1, "XRPUSDT": 0, "DOGEUSDT": None}
    assert ann2["breadth_g"] is None

    # 3. All 3 other coins have all 4 points not_triggered -> G=0; all 3 have 1 valid trigger -> G=3
    all_zero_rows = [
        _make_a_row(sym, u)
        for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT")
        for u in (u1, u2, u3, u4)
    ]
    res_zero = annotate_breadth(target, all_zero_rows, protocol=proto)
    assert res_zero["annotations"][0]["breadth_g"] == 0
    assert res_zero["annotations"][0]["h_by_symbol"] == {"SOLUSDT": 0, "XRPUSDT": 0, "DOGEUSDT": 0}

    all_three_rows = [
        _make_a_row(sym, u, status="overlap_suppressed" if u == u4 else "not_triggered", trigger_value=3.2 if u == u4 else None)
        for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT")
        for u in (u1, u2, u3, u4)
    ]
    res_three = annotate_breadth(target, all_three_rows, protocol=proto)
    assert res_three["annotations"][0]["breadth_g"] == 3

    # 4. Left boundary u_left=11:01, future u_future=12:16, self ETHUSDT, and BTCUSDT triggers MUST NOT increase G!
    u_left = _utc_ms("2026-06-15T11:01:00Z")
    u_future = _utc_ms("2026-06-15T12:16:00Z")
    boundary_rows = copy.deepcopy(all_zero_rows) + [
        _make_a_row("SOLUSDT", u_left, status="admitted", trigger_value=5.0),
        _make_a_row("XRPUSDT", u_future, status="admitted", trigger_value=6.0),
        _make_a_row("ETHUSDT", u4, status="admitted", trigger_value=8.0),
        _make_a_row("BTCUSDT", u4, status="admitted", trigger_value=9.0),
    ]
    res_bound = annotate_breadth(target, boundary_rows, protocol=proto)
    assert res_bound["annotations"][0]["breadth_g"] == 0

    # 5. Even when SOL already has a trigger at u2, contradictions on another point MUST raise STOP=input_invalid (never masked!)
    # 5a. not_triggered carrying numeric trigger_value -> cohort_mismatch
    bad_nt = copy.deepcopy(rows_case1)
    bad_nt[0]["trigger_value"] = 3.5
    with pytest.raises(AttributionStopError) as exc_nt:
        annotate_breadth(target, bad_nt, protocol=proto)
    assert exc_nt.value.stop_code == "input_invalid" and exc_nt.value.cause == "cohort_mismatch"

    # 5b. Invalid status enum -> cohort_mismatch
    bad_st = copy.deepcopy(rows_case1)
    bad_st[0]["status"] = "bogus_status"
    with pytest.raises(AttributionStopError) as exc_st:
        annotate_breadth(target, bad_st, protocol=proto)
    assert exc_st.value.stop_code == "input_invalid" and exc_st.value.cause == "cohort_mismatch"

    # 5c. NaN trigger_value -> nonfinite_value
    bad_nan = copy.deepcopy(rows_case1)
    bad_nan[1]["trigger_value"] = float("nan")
    with pytest.raises(AttributionStopError) as exc_nan:
        annotate_breadth(target, bad_nan, protocol=proto)
    assert exc_nan.value.stop_code == "input_invalid" and exc_nan.value.cause == "nonfinite_value"

    # 5d. Duplicate key -> duplicate_key
    bad_dup = copy.deepcopy(rows_case1) + [copy.deepcopy(rows_case1[1])]
    with pytest.raises(AttributionStopError) as exc_dup:
        annotate_breadth(target, bad_dup, protocol=proto)
    assert exc_dup.value.stop_code == "input_invalid" and exc_dup.value.cause == "duplicate_key"

    # 5e. Time mismatch (window_end_ms + 60000 != available_at_ms) -> time_or_price_mismatch
    bad_tm = copy.deepcopy(rows_case1)
    bad_tm[0]["window_end_ms"] = u1 - 30_000
    with pytest.raises(AttributionStopError) as exc_tm:
        annotate_breadth(target, bad_tm, protocol=proto)
    assert exc_tm.value.stop_code == "input_invalid" and exc_tm.value.cause == "time_or_price_mismatch"


def test_breadth_causality_and_unknowns() -> None:
    """Task 1: missing/feature_not_estimable/block_boundary_censored yield unknown (not 0); future/outcome/block mutations cannot alter G."""
    proto = build_default_protocol()
    t = _utc_ms("2026-06-15T12:01:00Z")
    us = [
        _utc_ms("2026-06-15T11:16:00Z"),
        _utc_ms("2026-06-15T11:31:00Z"),
        _utc_ms("2026-06-15T11:46:00Z"),
        _utc_ms("2026-06-15T12:01:00Z"),
    ]
    target = [(CAND_B, "ETHUSDT", t)]

    # Check each of feature_not_estimable and block_boundary_censored produces unknown H=None, G=None (not 0)
    for gap_status in ("feature_not_estimable", "block_boundary_censored"):
        rows_gap = []
        for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT"):
            for idx, u in enumerate(us):
                st = gap_status if (sym == "SOLUSDT" and idx == 0) else "not_triggered"
                rows_gap.append(_make_a_row(sym, u, status=st, trigger_value=None))
        out_gap = annotate_breadth(target, rows_gap, protocol=proto)
        ann = out_gap["annotations"][0]
        assert ann["h_by_symbol"] == {"SOLUSDT": None, "XRPUSDT": 0, "DOGEUSDT": 0}
        assert ann["breadth_g"] is None
        assert out_gap["slot_gap_counts_by_reason"][gap_status] == 1

    # Strict causality & projection invariance: mutating post-t spikes, outcome columns, or block_id NEVER alters G(t)
    base_rows = [
        _make_a_row(
            sym,
            u,
            status="admitted" if (sym == "SOLUSDT" and u == us[-1]) else "not_triggered",
            trigger_value=4.5 if (sym == "SOLUSDT" and u == us[-1]) else None,
            extra={"y_gross_bps": 50.0, "d_bps": 10.0, "block_id": 0},
        )
        for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT")
        for u in us
    ]
    g_base = annotate_breadth(target, base_rows, protocol=proto)["annotations"][0]
    assert g_base["breadth_g"] == 1

    perturbed_rows = copy.deepcopy(base_rows)
    for r in perturbed_rows:
        r["y_gross_bps"] = -9999.0
        r["d_bps"] = -5000.0
        r["block_id"] = 22
    # Add post-t huge volume spikes at t+15m, t+30m across all coins
    for future_u in (_utc_ms("2026-06-15T12:16:00Z"), _utc_ms("2026-06-15T12:31:00Z")):
        for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT"):
            perturbed_rows.append(_make_a_row(sym, future_u, status="admitted", trigger_value=15.0))
    g_pert = annotate_breadth(target, perturbed_rows, protocol=proto)["annotations"][0]
    assert g_pert["breadth_g"] == 1
    assert g_pert["h_by_symbol"] == g_base["h_by_symbol"]
    # Verify projected slot records do NOT carry outcome columns
    for slot in g_pert["slots_by_symbol"]["SOLUSDT"]:
        assert "y_gross_bps" not in slot and "d_bps" not in slot


def test_breadth_canonical_positive() -> None:
    """Task 1 (Rule 15): canonical HistoricalBar -> build_event_ledger -> JSONL -> build_cohort/summarize_cohort -> annotate_breadth."""
    proto = build_default_protocol()
    bars_g0 = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    ledger_rows_g0 = _serialize_and_reload_ledger_rows(bars_g0, proto)
    cohort_g0 = build_cohort(ledger_rows_g0, protocol=proto)
    members_g0 = summarize_cohort(cohort_g0, protocol=proto)["members"]

    k1 = (CAND_B, "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z"))
    k2 = (CAND_B, "ETHUSDT", _utc_ms("2026-06-15T16:16:00Z"))
    assert {(m["candidate"], m["symbol"], m["available_at_ms"]) for m in members_g0} == {k1, k2}
    j_keys_g0 = [
        (m["candidate"], m["symbol"], int(m["available_at_ms"]))
        for m in members_g0
        if m["group"] == "joint"
    ]
    assert j_keys_g0 == [k1]
    assert members_g0[0]["y_gross_bps"] == pytest.approx(200.0)

    a_rows_g0 = [r for r in ledger_rows_g0 if r["candidate"] == CAND_A]
    breadth_g0 = annotate_breadth(j_keys_g0, a_rows_g0, protocol=proto)
    assert breadth_g0["annotations"][0]["breadth_g"] == 0
    assert breadth_g0["annotations"][0]["h_by_symbol"] == {"SOLUSDT": 0, "XRPUSDT": 0, "DOGEUSDT": 0}

    # Replace SOLUSDT 2026-06-15 11:30 quote_volume 25 -> 325 (1h vol=400 vs median 100 -> 4.0x)
    sol_spike_start = _utc_ms("2026-06-15T11:30:00Z")
    bars_g1 = [
        dataclasses.replace(b, quote_volume=325.0)
        if (b.symbol == "SOLUSDT" and b.bar_start_ms == sol_spike_start)
        else b
        for b in bars_g0
    ]
    ledger_rows_g1 = _serialize_and_reload_ledger_rows(bars_g1, proto)
    cohort_g1 = build_cohort(ledger_rows_g1, protocol=proto)
    members_g1 = summarize_cohort(cohort_g1, protocol=proto)["members"]
    j_keys_g1 = [
        (m["candidate"], m["symbol"], int(m["available_at_ms"]))
        for m in members_g1
        if m["group"] == "joint"
    ]
    assert j_keys_g1 == [k1]

    a_rows_g1 = [r for r in ledger_rows_g1 if r["candidate"] == CAND_A]
    breadth_g1 = annotate_breadth(j_keys_g1, a_rows_g1, protocol=proto)
    ann_g1 = breadth_g1["annotations"][0]
    assert ann_g1["breadth_g"] == 1
    assert ann_g1["h_by_symbol"] == {"SOLUSDT": 1, "XRPUSDT": 0, "DOGEUSDT": 0}
    sol_statuses = [s["actual_status"] for s in ann_g1["slots_by_symbol"]["SOLUSDT"]]
    assert "admitted" in sol_statuses and "overlap_suppressed" in sol_statuses


def test_breadth_canonical_block_censoring() -> None:
    """Task 1 (Rule 15): canonical Monday 00:01 resonance encounters real upstream block_boundary_censored lookback -> G=None."""
    proto = build_default_protocol()
    overrides = {
        ("ETHUSDT", _utc_ms("2026-06-20T23:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.0,
            "low_price": 100.0,
            "close_price": 101.0,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-21T23:30:00Z")): {
            "open_price": 100.0,
            "high_price": 100.0,
            "low_price": 100.0,
            "close_price": 100.0,
            "quote_volume": 325.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-21T23:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.5,
            "low_price": 100.0,
            "close_price": 101.5,
            "quote_volume": 25.0,
        },
    }
    bars = _make_168d_canonical_bars(overrides)
    ledger_rows = _serialize_and_reload_ledger_rows(bars, proto)
    cohort = build_cohort(ledger_rows, protocol=proto)
    members = summarize_cohort(cohort, protocol=proto)["members"]

    expected_j_key = (CAND_B, "ETHUSDT", _utc_ms("2026-06-22T00:01:00Z"))
    j_keys = [
        (m["candidate"], m["symbol"], int(m["available_at_ms"]))
        for m in members
        if m["group"] == "joint"
    ]
    assert j_keys == [expected_j_key]

    a_rows = [r for r in ledger_rows if r["candidate"] == CAND_A]
    breadth = annotate_breadth(j_keys, a_rows, protocol=proto)
    assert breadth["all_g_estimable"] is False
    assert breadth["known_g_count"] == 0
    assert breadth["unknown_g_count"] == 1
    ann = breadth["annotations"][0]
    assert ann["target_key"] == list(expected_j_key)
    assert ann["breadth_g"] is None
    assert ann["h_by_symbol"] == {"SOLUSDT": None, "XRPUSDT": None, "DOGEUSDT": None}
    for sym in ("SOLUSDT", "XRPUSDT", "DOGEUSDT"):
        statuses = [s["actual_status"] for s in ann["slots_by_symbol"][sym]]
        assert statuses == [
            "block_boundary_censored",
            "block_boundary_censored",
            "block_boundary_censored",
            "not_triggered",
        ]


def _make_synthetic_member_and_breadth_pair(
    specs: list[dict[str, Any]],
    *,
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Construct synthetic members + locked breadth payload for pure-logic Task 2 tests."""
    eval_start_ms = int(protocol["eval_start_ms"])
    block_ms = int(protocol["block_days"]) * 86_400_000
    members: list[dict[str, Any]] = []
    annotations: list[dict[str, Any]] = []
    breadth_counts = {"0": 0, "1": 0, "2": 0, "3": 0, "unknown": 0}
    unknown_gaps: list[dict[str, Any]] = []
    known_n = 0
    unknown_n = 0

    for idx, sp in enumerate(specs):
        sym = sp["symbol"]
        block_id = int(sp["block_id"])
        avail_ms = sp.get("available_at_ms")
        if avail_ms is None:
            win_end = eval_start_ms + block_id * block_ms + (idx + 1) * MS_15M
            avail_ms = win_end + 60_000
        else:
            win_end = int(avail_ms) - 60_000
        entry_ms = win_end + MS_15M
        exit_ms = entry_ms + 16 * MS_15M
        y_bps = float(sp["y_gross_bps"])
        exit_close = 100.0 * (1.0 + y_bps / 10000.0)
        mae_bps = float(sp.get("mae_4h_bps", min(-10.0, y_bps - 10.0)))
        mfe_bps = float(sp.get("mfe_4h_bps", max(10.0, y_bps + 10.0)))
        grp = sp.get("group", "joint")
        a_trig = grp == "joint"

        member = {
            "candidate": CAND_B,
            "symbol": sym,
            "available_at_ms": int(avail_ms),
            "block_id": block_id,
            "window_start_ms": win_end - MS_1H,
            "window_end_ms": win_end,
            "utc_end_hour": (win_end // MS_1H) % 24,
            "available_at_utc_hour": (int(avail_ms) // MS_1H) % 24,
            "entry_bar_start_ms": entry_ms,
            "exit_bar_end_ms": exit_ms,
            "entry_open_price": 100.0,
            "exit_close_price": exit_close,
            "self_r1h": float(sp.get("self_r1h", 0.015)),
            "btc_r1h": 0.0,
            "b_trigger_value": float(sp.get("b_trigger_value", 2.2)),
            "y_gross_bps": y_bps,
            "mfe_4h_bps": mfe_bps,
            "mae_4h_bps": mae_bps,
            "a_key": [CAND_A, sym, int(avail_ms)],
            "a_status": "admitted" if a_trig else "not_triggered",
            "a_trigger_value": float(sp.get("a_trigger_value", 4.0)) if a_trig else None,
            "a_triggered": a_trig,
            "group": grp,
            "in_common_support": bool(sp.get("in_common_support", True)),
            "support_status": sp.get("support_status", "supported" if a_trig else "control_in_support"),
            "conditional_control_keys": sp.get("conditional_control_keys", []),
            "conditional_control_mean_bps": sp.get("conditional_control_mean_bps", 0.0 if a_trig else None),
            "conditional_d_bps": sp.get("conditional_d_bps", y_bps if a_trig else None),
        }
        members.append(member)

        if a_trig:
            g_val = sp["breadth_g"]
            other_syms = [s for s in ("ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT") if s != sym]
            if g_val is None:
                h_map: dict[str, int | None] = {other_syms[0]: None, other_syms[1]: 0, other_syms[2]: 0}
                unknown_n += 1
                breadth_counts["unknown"] += 1
                gap_slot = {
                    "expected_key": [CAND_A, other_syms[0], int(avail_ms)],
                    "symbol": other_syms[0],
                    "available_at_ms": int(avail_ms),
                    "present": True,
                    "window_start_ms": win_end - MS_1H,
                    "window_end_ms": win_end,
                    "actual_status": "block_boundary_censored",
                    "trigger_value": None,
                    "fact": "unknown",
                    "gap_reason": "block_boundary_censored",
                }
                unknown_gaps.append(
                    {
                        "target_key": [CAND_B, sym, int(avail_ms)],
                        "h_by_symbol": h_map,
                        "blocking_unknown_slots": [gap_slot],
                    }
                )
                unk_slots = [gap_slot]
            else:
                h_map = {
                    other_syms[k]: (1 if k < int(g_val) else 0)
                    for k in range(3)
                }
                known_n += 1
                breadth_counts[str(g_val)] += 1
                unk_slots = []

            annotations.append(
                {
                    "target_key": [CAND_B, sym, int(avail_ms)],
                    "candidate": CAND_B,
                    "symbol": sym,
                    "available_at_ms": int(avail_ms),
                    "lookback_ms": MS_1H,
                    "expected_u_ms": [int(avail_ms) - 3 * MS_15M, int(avail_ms) - 2 * MS_15M, int(avail_ms) - MS_15M, int(avail_ms)],
                    "other_symbols": other_syms,
                    "h_by_symbol": h_map,
                    "breadth_g": g_val,
                    "g_estimable": g_val is not None,
                    "slots_by_symbol": {s: [] for s in other_syms},
                    "triggered_evidence": [],
                    "unknown_slots": unk_slots,
                }
            )

    breadth = {
        "lookback_ms": MS_1H,
        "target_count": len(annotations),
        "known_g_count": known_n,
        "unknown_g_count": unknown_n,
        "all_g_estimable": unknown_n == 0,
        "breadth_counts": breadth_counts,
        "slot_gap_counts_by_reason": {
            "missing_row": 0,
            "feature_not_estimable": 0,
            "block_boundary_censored": unknown_n,
        },
        "unknown_gaps": unknown_gaps,
        "annotations": annotations,
    }
    return members, breadth


def test_attribution_hand_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2: hand-calculated 4-level G0=[100,0], G1=[-20], G2=[], G3=[300], MAE/MFE, cost shifts, without_block_9, 4x4 & 23x4 conservation."""
    proto = build_default_protocol()
    specs = [
        {"symbol": "ETHUSDT", "block_id": 0, "breadth_g": 0, "y_gross_bps": 100.0, "mae_4h_bps": -50.0, "mfe_4h_bps": 200.0},
        {"symbol": "SOLUSDT", "block_id": 0, "breadth_g": 0, "y_gross_bps": 0.0, "mae_4h_bps": -100.0, "mfe_4h_bps": 100.0},
        {"symbol": "XRPUSDT", "block_id": 1, "breadth_g": 1, "y_gross_bps": -20.0, "mae_4h_bps": -40.0, "mfe_4h_bps": 10.0},
        {"symbol": "DOGEUSDT", "block_id": 9, "breadth_g": 3, "y_gross_bps": 300.0, "mae_4h_bps": -15.0, "mfe_4h_bps": 350.0},
    ]
    members, breadth = _make_synthetic_cohort_pair_alias(specs, protocol=proto)

    # Spy on CORE.linear_quantile to verify actual reuse
    quantile_calls: list[tuple[list[float], float]] = []
    orig_lq = attr_mod.linear_quantile

    def _spy_lq(vals: list[float], p: float) -> float | None:
        quantile_calls.append((list(vals), p))
        return orig_lq(vals, p)

    monkeypatch.setattr(attr_mod, "linear_quantile", _spy_lq)
    out = describe_attribution(members, breadth, protocol=proto)
    assert len(quantile_calls) > 0

    fs = out["full_sample"]
    assert [fs[g]["n"] for g in ("0", "1", "2", "3")] == [2, 1, 0, 1]

    g0 = fs["0"]
    assert g0["symbol_count"] == 2
    assert g0["non_empty_block_count"] == 1
    assert g0["sum_y_bps"] == pytest.approx(100.0)
    assert g0["mean_bps"] == pytest.approx(50.0)
    assert g0["median_bps"] == pytest.approx(50.0)
    assert g0["win_rate"] == pytest.approx(0.5)
    assert g0["avg_win_bps"] == pytest.approx(100.0)
    assert g0["avg_loss_bps"] is None
    assert g0["payoff_ratio"] is None
    assert g0["worst_event_bps"] == pytest.approx(0.0)
    assert g0["quantiles_bps"] == {
        "p05": pytest.approx(5.0),
        "p10": pytest.approx(10.0),
        "p25": pytest.approx(25.0),
        "p50": pytest.approx(50.0),
        "p75": pytest.approx(75.0),
        "p90": pytest.approx(90.0),
    }
    assert g0["mae_4h_gross_bps"] == {
        "mean": pytest.approx(-75.0),
        "p10": pytest.approx(-95.0),
        "p50": pytest.approx(-75.0),
        "min": pytest.approx(-100.0),
    }
    assert g0["mfe_4h_gross_bps"] == {
        "mean": pytest.approx(150.0),
        "p50": pytest.approx(150.0),
        "p90": pytest.approx(190.0),
        "max": pytest.approx(200.0),
    }
    assert g0["cost_scenarios"] == {
        "30.0": {"cost_round_trip_bps": 30.0, "mean_bps": pytest.approx(20.0), "p10_bps": pytest.approx(-20.0), "worst_event_bps": pytest.approx(-30.0)},
        "50.0": {"cost_round_trip_bps": 50.0, "mean_bps": pytest.approx(0.0), "p10_bps": pytest.approx(-40.0), "worst_event_bps": pytest.approx(-50.0)},
        "80.0": {"cost_round_trip_bps": 80.0, "mean_bps": pytest.approx(-30.0), "p10_bps": pytest.approx(-70.0), "worst_event_bps": pytest.approx(-80.0)},
    }

    g1 = fs["1"]
    assert g1["n"] == 1 and g1["win_rate"] == pytest.approx(0.0)
    assert g1["avg_win_bps"] is None and g1["avg_loss_bps"] == pytest.approx(-20.0) and g1["payoff_ratio"] is None

    g2 = fs["2"]
    assert g2["n"] == 0 and g2["symbol_count"] == 0 and g2["non_empty_block_count"] == 0
    for k in ("mean_bps", "median_bps", "win_rate", "avg_win_bps", "avg_loss_bps", "payoff_ratio", "worst_event_bps"):
        assert g2[k] is None
    assert all(v is None for v in g2["quantiles_bps"].values())
    assert all(v is None for v in g2["mae_4h_gross_bps"].values())
    assert all(v is None for v in g2["mfe_4h_gross_bps"].values())
    for c_key in ("30.0", "50.0", "80.0"):
        assert g2["cost_scenarios"][c_key]["mean_bps"] is None
        assert g2["cost_scenarios"][c_key]["p10_bps"] is None
        assert g2["cost_scenarios"][c_key]["worst_event_bps"] is None

    # Removing block 9 ONLY empties G3; remaining members' G levels stay unchanged (2/1/0/0)
    wb9 = out["without_block_9"]
    assert [wb9[g]["n"] for g in ("0", "1", "2", "3")] == [2, 1, 0, 0]
    assert wb9["0"]["mean_bps"] == pytest.approx(50.0)
    assert wb9["1"]["mean_bps"] == pytest.approx(-20.0)
    assert wb9["3"]["n"] == 0 and wb9["3"]["mean_bps"] is None

    # 4 coins x 4 G levels & 23 blocks x 4 G levels retain zero cells and sum back to 4
    ps = out["per_symbol"]
    assert set(ps.keys()) == {"ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"}
    assert sum(ps[sym]["by_g"][g]["n"] for sym in ps for g in ("0", "1", "2", "3")) == 4
    assert ps["ETHUSDT"]["by_g"]["2"]["n"] == 0 and ps["ETHUSDT"]["by_g"]["2"]["mean_bps"] is None

    pb = out["per_block"]
    assert len(pb) == 23
    assert sum(b["by_g"][g]["n"] for b in pb for g in ("0", "1", "2", "3")) == 4
    assert pb[2]["by_g"]["0"]["n"] == 0 and pb[2]["by_g"]["0"]["mean_bps"] is None

    assert out["minimum_economically_meaningful_gain"] is None
    assert out["cost_mode"] == "cost_context_only"
    assert out["routing"] == {
        "conclusion": "descriptive_attribution_only",
        "observation_label": "descriptive_attribution_only",
        "resource_decision": "pause_for_new_evidence",
        "alpha_research_status": "evidence_insufficient",
    }
    gov = out["governance"]
    assert gov["live_trading_enabled"] is False
    assert gov["paper_trading_allowed"] is False
    assert gov["execution_engine_allowed"] is False
    assert gov["independent_out_of_sample_claim_allowed"] is False


def _make_synthetic_cohort_pair_alias(
    specs: list[dict[str, Any]],
    *,
    protocol: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return _make_synthetic_member_and_breadth_pair(specs, protocol=protocol)


def test_attribution_unknown_blocks_all_group_statistics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 2: any unknown G blocks all 4-level return tables (all None), preserves J rows/gaps/focus_week, and outputs breadth_not_estimable."""
    proto = build_default_protocol()
    specs = [
        {"symbol": "ETHUSDT", "block_id": 0, "breadth_g": 0, "y_gross_bps": 100.0},
        {"symbol": "DOGEUSDT", "block_id": 9, "breadth_g": None, "y_gross_bps": 250.0},
        {"symbol": "DOGEUSDT", "block_id": 9, "group": "b_only", "breadth_g": None, "y_gross_bps": -120.0},
    ]
    members, breadth = _make_synthetic_member_and_breadth_pair(specs, protocol=proto)

    # Spy on linear_quantile to prove 4-level return distribution summarizer is NEVER called when G has unknown!
    def _forbid_quantile_on_unknown(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("4-level return distribution must NOT be computed when any G is unknown")

    monkeypatch.setattr(attr_mod, "linear_quantile", _forbid_quantile_on_unknown)
    out = describe_attribution(members, breadth, protocol=proto)

    assert len(out["breadth_members"]) == 2
    assert out["coverage"]["all_g_estimable"] is False
    assert out["coverage"]["known_g_count"] == 1
    assert out["coverage"]["unknown_g_count"] == 1
    assert len(out["coverage"]["unknown_targets"]) == 1
    assert len(out["focus_week"]["timeline"]) == 2

    assert out["full_sample"] is None
    assert out["without_block_9"] is None
    assert out["per_symbol"] is None
    assert out["per_block"] is None
    assert out["routing"] == {
        "conclusion": "breadth_not_estimable",
        "observation_label": "breadth_not_estimable",
        "resource_decision": "stop_due_to_evidence",
        "alpha_research_status": "evidence_insufficient",
    }

    # Mismatched breadth target keys vs J keys -> STOP=input_invalid, cause=cohort_mismatch
    bad_breadth = copy.deepcopy(breadth)
    bad_breadth["annotations"].pop()
    with pytest.raises(AttributionStopError) as exc_m:
        describe_attribution(members, bad_breadth, protocol=proto)
    assert exc_m.value.stop_code == "input_invalid" and exc_m.value.cause == "cohort_mismatch"


def test_attribution_focus_week_passthrough() -> None:
    """Task 2: Block-9 timeline sorted by (available_at_ms, symbol), verbatim passthrough of controls/d_bps, UTC day/coin summary & DOGE controls."""
    proto = build_default_protocol()
    t_aug18_doge = _utc_ms("2026-08-18T10:01:00Z")
    t_aug18_eth = _utc_ms("2026-08-18T10:01:00Z")
    t_aug23_doge_c1 = _utc_ms("2026-08-23T04:01:00Z")
    t_aug23_doge_c2 = _utc_ms("2026-08-23T14:01:00Z")
    t_block0_sol = _utc_ms("2026-06-15T12:01:00Z")

    ctrl_keys = [
        [CAND_B, "DOGEUSDT", t_aug23_doge_c1],
        [CAND_B, "DOGEUSDT", t_aug23_doge_c2],
    ]
    # Deliberately pass unsorted order to verify deterministic (available_at_ms, symbol) sorting
    specs = [
        {
            "symbol": "DOGEUSDT",
            "block_id": 9,
            "available_at_ms": t_aug23_doge_c2,
            "group": "b_only",
            "breadth_g": None,
            "y_gross_bps": -86.23,
        },
        {
            "symbol": "DOGEUSDT",
            "block_id": 9,
            "available_at_ms": t_aug18_doge,
            "group": "joint",
            "breadth_g": 2,
            "y_gross_bps": 150.0,
            "conditional_control_keys": ctrl_keys,
            "conditional_control_mean_bps": -279.97,
            "conditional_d_bps": 429.97,
        },
        {
            "symbol": "ETHUSDT",
            "block_id": 9,
            "available_at_ms": t_aug18_eth,
            "group": "joint",
            "breadth_g": 1,
            "y_gross_bps": 50.0,
            "conditional_control_keys": [],
            "conditional_control_mean_bps": -10.0,
            "conditional_d_bps": 60.0,
        },
        {
            "symbol": "DOGEUSDT",
            "block_id": 9,
            "available_at_ms": t_aug23_doge_c1,
            "group": "b_only",
            "breadth_g": None,
            "y_gross_bps": -473.71,
        },
        {
            "symbol": "SOLUSDT",
            "block_id": 0,
            "available_at_ms": t_block0_sol,
            "group": "joint",
            "breadth_g": 0,
            "y_gross_bps": 25.0,
        },
    ]
    members, breadth = _make_synthetic_member_and_breadth_pair(specs, protocol=proto)
    out = describe_attribution(members, breadth, protocol=proto)

    fw = out["focus_week"]
    tl = fw["timeline"]
    assert len(tl) == 4  # excludes block 0 SOLUSDT
    assert [(r["available_at_ms"], r["symbol"]) for r in tl] == [
        (t_aug18_doge, "DOGEUSDT"),
        (t_aug18_eth, "ETHUSDT"),
        (t_aug23_doge_c1, "DOGEUSDT"),
        (t_aug23_doge_c2, "DOGEUSDT"),
    ]
    assert tl[0]["conditional_control_keys"] == ctrl_keys
    assert tl[0]["conditional_d_bps"] == pytest.approx(429.97)

    # UTC date summary on 2026-08-18: 2 joint events (150 + 50 = 200, mean 100); on 2026-08-23: 0 joint, 2 b_only
    by_day = {d["utc_date"]: d for d in fw["by_utc_date"]}
    assert by_day["2026-08-18"]["joint_count"] == 2
    assert by_day["2026-08-18"]["joint_sum_y_bps"] == pytest.approx(200.0)
    assert by_day["2026-08-18"]["joint_mean_y_bps"] == pytest.approx(100.0)
    assert by_day["2026-08-23"]["joint_count"] == 0
    assert by_day["2026-08-23"]["joint_mean_y_bps"] is None
    assert by_day["2026-08-23"]["b_only_count"] == 2

    # Dedicated DOGE controls list
    doge_ctrls = fw["doge_controls"]
    assert len(doge_ctrls) == 2
    assert [c["utc_date"] for c in doge_ctrls] == ["2026-08-23", "2026-08-23"]
    assert [c["y_gross_bps"] for c in doge_ctrls] == [pytest.approx(-473.71), pytest.approx(-86.23)]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _block_all_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _deny_net(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("network_forbidden_in_stage1_3_breadth_cli")

    monkeypatch.setattr(socket.socket, "connect", _deny_net)
    monkeypatch.setattr(socket.socket, "connect_ex", _deny_net)
    monkeypatch.setattr(socket, "create_connection", _deny_net)


def _build_canonical_five_input_fixture(
    base_dir: Path,
    bars: list[Any],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    base_dir = base_dir.resolve()
    u_root = base_dir / "u_run"
    r_root = base_dir / "r_run"
    old_bind_dir = base_dir / "old_bind"
    out_parent = base_dir / "new_evidence_parent"
    (u_root / "results").mkdir(parents=True, exist_ok=True)
    r_root.mkdir(parents=True, exist_ok=True)
    old_bind_dir.mkdir(parents=True, exist_ok=True)
    out_parent.mkdir(parents=True, exist_ok=True)

    ledger = build_event_ledger(bars, protocol=protocol)
    u_ledger_path = u_root / "results" / "ledger.jsonl"
    raw_dp_rows: list[dict[str, Any]] = []
    for cand in protocol["candidates"]:
        raw_dp_rows.extend(ledger["candidates"][cand]["decision_points"])
    u_ledger_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False, allow_nan=False) for r in raw_dp_rows) + "\n",
        encoding="utf-8",
    )
    u_ledger_sha = _sha256_file(u_ledger_path)

    # Deliberately point coverage_json and source_manifest_json to non-existent paths to prove zero recursive read
    unopened_cov_path = u_root / "DO_NOT_OPEN_coverage.json"
    unopened_manifest_path = base_dir / "DO_NOT_OPEN_source_manifest.json"
    fake_cov_sha = "1" * 64
    fake_manifest_sha = "2" * 64

    u_summary_path = u_root / "results" / "summary.json"
    u_summary_obj = {
        "manifest_sha256": fake_manifest_sha,
        "authority": {
            "design_path": attr_mod.PRIOR_1124_DESIGN_REL_PATH,
            "design_sha256": attr_mod.PRIOR_1124_DESIGN_SHA256,
            "plan_path": attr_mod.PRIOR_1124_PLAN_REL_PATH,
            "plan_sha256": attr_mod.PRIOR_1124_PLAN_SHA256,
        },
        "protocol": protocol,
        "candidates": {
            CAND_A: {"counts": ledger["candidates"][CAND_A]["counts"]},
            CAND_B: {"counts": ledger["candidates"][CAND_B]["counts"]},
        },
    }
    u_summary_path.write_text(json.dumps(u_summary_obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    u_summary_sha = _sha256_file(u_summary_path)

    reloaded_rows = [
        json.loads(line)
        for line in u_ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cohort = build_cohort(reloaded_rows, protocol=protocol)
    res_r = summarize_cohort(cohort, protocol=protocol)

    old_fixed_inputs = {
        "ledger_jsonl": {"path": str(u_ledger_path), "sha256": u_ledger_sha},
        "summary_json": {"path": str(u_summary_path), "sha256": u_summary_sha},
        "coverage_json": {"path": str(unopened_cov_path), "sha256": fake_cov_sha},
        "source_manifest_json": {"path": str(unopened_manifest_path), "sha256": fake_manifest_sha},
    }
    old_binding_path = old_bind_dir / "source_binding.json"
    old_binding_obj = {
        "binding_version": 1,
        "note": "provenance_record_only_not_execution_authorization",
        "authority": {
            "design_path": attr_mod.PRIOR_1125_DESIGN_REL_PATH,
            "design_sha256": attr_mod.PRIOR_1125_DESIGN_SHA256,
            "plan_path": attr_mod.PRIOR_1125_PLAN_REL_PATH,
            "plan_sha256": attr_mod.PRIOR_1125_PLAN_SHA256,
        },
        "protocol": protocol,
        "fixed_inputs": old_fixed_inputs,
        "output": {"output_root": str(r_root)},
    }
    old_binding_path.write_text(json.dumps(old_binding_obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    old_binding_sha = _sha256_file(old_binding_path)

    r_members_path = r_root / "members.jsonl"
    r_members_path.write_text(
        (
            "\n".join(json.dumps(m, ensure_ascii=False, allow_nan=False) for m in res_r["members"]) + "\n"
            if res_r["members"]
            else ""
        ),
        encoding="utf-8",
    )
    r_members_sha = _sha256_file(r_members_path)

    r_summary_path = r_root / "summary.json"
    r_summary_obj = dict(res_r["summary"])
    r_summary_obj["source_binding_sha256"] = old_binding_sha
    r_summary_obj["fixed_inputs"] = old_fixed_inputs
    r_summary_path.write_text(json.dumps(r_summary_obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    r_summary_sha = _sha256_file(r_summary_path)

    members = res_r["members"]
    b9_members = [m for m in members if int(m["block_id"]) == 9]
    expected_counts = {
        "q_total": len(members),
        "j_joint_total": sum(1 for m in members if m["group"] == "joint"),
        "b_only_total": sum(1 for m in members if m["group"] == "b_only"),
        "focus_week_q_total": len(b9_members),
        "focus_week_joint_count": sum(1 for m in b9_members if m["group"] == "joint"),
        "focus_week_b_only_count": sum(1 for m in b9_members if m["group"] == "b_only"),
    }
    specs = {
        "r_members_jsonl": (r_members_path, r_members_sha),
        "r_summary_json": (r_summary_path, r_summary_sha),
        "u_ledger_jsonl": (u_ledger_path, u_ledger_sha),
        "u_summary_json": (u_summary_path, u_summary_sha),
        "old_source_binding_json": (old_binding_path, old_binding_sha),
    }
    return {
        "u_root": u_root,
        "r_root": r_root,
        "old_bind_dir": old_bind_dir,
        "out_parent": out_parent,
        "specs": specs,
        "expected_counts": expected_counts,
    }


def _apply_fixture_monkeypatch(monkeypatch: pytest.MonkeyPatch, fx: dict[str, Any]) -> None:
    monkeypatch.setattr(attr_mod, "EXPECTED_U_ROOT", fx["u_root"])
    monkeypatch.setattr(attr_mod, "EXPECTED_R_ROOT", fx["r_root"])
    monkeypatch.setattr(attr_mod, "FIXED_INPUT_SPECS", copy.deepcopy(fx["specs"]))
    monkeypatch.setattr(attr_mod, "ALLOWED_OUTPUT_PARENT", fx["out_parent"])
    monkeypatch.setattr(attr_mod, "EXPECTED_COUNTS", copy.deepcopy(fx["expected_counts"]))


def test_cli_canonical_prepare_and_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3 (Rule 15): full canonical G=1 pipeline prepare -> run -> 3 files, zero JSON parse of 5 inputs during prepare."""
    _block_all_network(monkeypatch)
    proto = build_default_protocol()
    bars_g0 = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    sol_spike_start = _utc_ms("2026-06-15T11:30:00Z")
    bars_g1 = [
        dataclasses.replace(b, quote_volume=325.0)
        if (b.symbol == "SOLUSDT" and b.bar_start_ms == sol_spike_start)
        else b
        for b in bars_g0
    ]
    fx = _build_canonical_five_input_fixture(tmp_path / "canon_g1", bars_g1, protocol=proto)
    assert fx["expected_counts"] == {
        "q_total": 2,
        "j_joint_total": 1,
        "b_only_total": 1,
        "focus_week_q_total": 0,
        "focus_week_joint_count": 0,
        "focus_week_b_only_count": 0,
    }
    _apply_fixture_monkeypatch(monkeypatch, fx)

    plan_sha = _sha256_file(attr_mod.REPO_ROOT / attr_mod.PLAN_REL_PATH)
    binding_out = (tmp_path / "work" / "source_binding.json").resolve()
    out_root = (fx["out_parent"] / "run_g1").resolve()

    # Spy on json.loads during prepare to prove the 5 input files' contents are NEVER parsed in prepare
    five_input_texts = {p.read_text(encoding="utf-8") for p, _ in fx["specs"].values()}
    orig_loads = json.loads

    def _guard_prepare_loads(s: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(s, str) and s in five_input_texts:
            raise AssertionError("prepare MUST NOT JSON-parse any of the 5 fixed inputs!")
        return orig_loads(s, *args, **kwargs)

    with monkeypatch.context() as mp_prep:
        mp_prep.setattr(json, "loads", _guard_prepare_loads)
        rc_prep = attr_mod.main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(binding_out),
                "--output-root",
                str(out_root),
            ]
        )
    assert rc_prep == 0
    assert binding_out.is_file()
    assert not out_root.exists()

    b_obj = json.loads(binding_out.read_text(encoding="utf-8"))
    assert b_obj["note"] == "provenance_record_only_not_execution_authorization"
    assert len(b_obj["code_bindings"]) == 6
    assert set(b_obj["fixed_inputs"].keys()) == set(fx["specs"].keys())
    binding_sha = _sha256_file(binding_out)

    rc_run = attr_mod.main(["run", "--binding", str(binding_out), "--binding-sha", binding_sha])
    assert rc_run == 0
    assert {p.name for p in out_root.iterdir()} == {"breadth_members.jsonl", "summary.json", "report_CN.md"}

    bm_lines = (out_root / "breadth_members.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(bm_lines) == 1
    bm = json.loads(bm_lines[0])
    assert bm["target_key"] == [CAND_B, "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z")]
    assert bm["breadth_g"] == 1
    assert bm["h_by_symbol"] == {"SOLUSDT": 1, "XRPUSDT": 0, "DOGEUSDT": 0}
    assert sum(len(v) for v in bm["slots_by_symbol"].values()) == 12
    sol_trig = [e for e in bm["triggered_evidence"] if e["symbol"] == "SOLUSDT"]
    assert len(sol_trig) == 2
    assert {e["actual_status"] for e in sol_trig} == {"admitted", "overlap_suppressed"}
    assert all(e["trigger_value"] == pytest.approx(4.0) for e in sol_trig)
    assert bm["y_gross_bps"] == pytest.approx(200.0)

    summary = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["execution_status"] == "execution_completed_pending_independent_audit"
    fs = summary["full_sample"]
    assert fs["1"]["n"] == 1
    assert fs["1"]["mean_bps"] == pytest.approx(200.0)
    assert fs["1"]["cost_scenarios"]["30.0"]["mean_bps"] == pytest.approx(170.0)
    assert fs["1"]["cost_scenarios"]["50.0"]["mean_bps"] == pytest.approx(150.0)
    assert fs["1"]["cost_scenarios"]["80.0"]["mean_bps"] == pytest.approx(120.0)
    for empty_g in ("0", "2", "3"):
        assert fs[empty_g]["n"] == 0
        assert fs[empty_g]["mean_bps"] is None
    assert sum(summary["per_symbol"][s]["by_g"][g]["n"] for s in summary["per_symbol"] for g in ("0", "1", "2", "3")) == 1
    assert sum(b["by_g"][g]["n"] for b in summary["per_block"] for g in ("0", "1", "2", "3")) == 1
    assert summary["routing"] == {
        "conclusion": "descriptive_attribution_only",
        "observation_label": "descriptive_attribution_only",
        "resource_decision": "pause_for_new_evidence",
        "alpha_research_status": "evidence_insufficient",
    }

    report_md = (out_root / "report_CN.md").read_text(encoding="utf-8")
    assert "descriptive_attribution_only" in report_md
    assert "evidence_insufficient" in report_md


def test_cli_canonical_gap_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 3 (Rule 15): canonical Monday 00:01 censoring vector delivers RC=0, preserves J row with G=None, all 4 return tables null."""
    _block_all_network(monkeypatch)
    proto = build_default_protocol()
    overrides = {
        ("ETHUSDT", _utc_ms("2026-06-20T23:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.0,
            "low_price": 100.0,
            "close_price": 101.0,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-21T23:30:00Z")): {
            "open_price": 100.0,
            "high_price": 100.0,
            "low_price": 100.0,
            "close_price": 100.0,
            "quote_volume": 325.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-21T23:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.5,
            "low_price": 100.0,
            "close_price": 101.5,
            "quote_volume": 25.0,
        },
    }
    bars = _make_168d_canonical_bars(overrides)
    fx = _build_canonical_five_input_fixture(tmp_path / "canon_gap", bars, protocol=proto)
    _apply_fixture_monkeypatch(monkeypatch, fx)

    plan_sha = _sha256_file(attr_mod.REPO_ROOT / attr_mod.PLAN_REL_PATH)
    binding_out = (tmp_path / "work_gap" / "source_binding.json").resolve()
    out_root = (fx["out_parent"] / "run_gap").resolve()

    assert (
        attr_mod.main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(binding_out),
                "--output-root",
                str(out_root),
            ]
        )
        == 0
    )
    binding_sha = _sha256_file(binding_out)
    assert attr_mod.main(["run", "--binding", str(binding_out), "--binding-sha", binding_sha]) == 0
    assert {p.name for p in out_root.iterdir()} == {"breadth_members.jsonl", "summary.json", "report_CN.md"}

    bm_lines = (out_root / "breadth_members.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(bm_lines) == 1
    bm = json.loads(bm_lines[0])
    assert bm["target_key"] == [CAND_B, "ETHUSDT", _utc_ms("2026-06-22T00:01:00Z")]
    assert bm["breadth_g"] is None
    assert bm["g_estimable"] is False
    assert bm["outcome_joined"] is False
    assert bm["y_gross_bps"] is None

    summary = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert summary["execution_status"] == "execution_completed_pending_independent_audit"
    assert summary["coverage"]["all_g_estimable"] is False
    assert summary["coverage"]["unknown_g_count"] == 1
    assert summary["full_sample"] is None
    assert summary["without_block_9"] is None
    assert summary["per_symbol"] is None
    assert summary["per_block"] is None
    assert summary["routing"] == {
        "conclusion": "breadth_not_estimable",
        "observation_label": "breadth_not_estimable",
        "resource_decision": "stop_due_to_evidence",
        "alpha_research_status": "evidence_insufficient",
    }

    report_md = (out_root / "report_CN.md").read_text(encoding="utf-8")
    assert "breadth_not_estimable" in report_md
    assert "stop_due_to_evidence" in report_md


def test_cli_identity_scope_and_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Task 3: inject faults on synthetic copies covering all 11 exact causes + zero network + identical-byte directory relocation."""
    _block_all_network(monkeypatch)
    # Verify network blocker is live
    with pytest.raises(RuntimeError, match="network_forbidden"):
        socket.create_connection(("127.0.0.1", 80), timeout=0.1)

    proto = build_default_protocol()
    bars = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    master_fx = _build_canonical_five_input_fixture(tmp_path / "master_fx", bars, protocol=proto)
    plan_sha = _sha256_file(attr_mod.REPO_ROOT / attr_mod.PLAN_REL_PATH)

    def _clone_case(name: str) -> dict[str, Any]:
        case_dir = (tmp_path / name).resolve()
        shutil.copytree(tmp_path.resolve() / "master_fx", case_dir)
        u_root = case_dir / "u_run"
        r_root = case_dir / "r_run"
        old_bind_dir = case_dir / "old_bind"
        out_parent = case_dir / "new_evidence_parent"

        # Rewrite paths inside old_binding and r_summary for this isolated case_dir
        u_ledger = u_root / "results" / "ledger.jsonl"
        u_sum = u_root / "results" / "summary.json"
        r_mem = r_root / "members.jsonl"
        r_sum = r_root / "summary.json"
        old_b = old_bind_dir / "source_binding.json"

        ob_obj = json.loads(old_b.read_text(encoding="utf-8"))
        ob_obj["fixed_inputs"]["ledger_jsonl"] = {"path": str(u_ledger), "sha256": _sha256_file(u_ledger)}
        ob_obj["fixed_inputs"]["summary_json"] = {"path": str(u_sum), "sha256": _sha256_file(u_sum)}
        ob_obj["output"]["output_root"] = str(r_root)
        old_b.write_text(json.dumps(ob_obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ob_sha = _sha256_file(old_b)

        rs_obj = json.loads(r_sum.read_text(encoding="utf-8"))
        rs_obj["source_binding_sha256"] = ob_sha
        rs_obj["fixed_inputs"] = ob_obj["fixed_inputs"]
        r_sum.write_text(json.dumps(rs_obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")

        specs = {
            "r_members_jsonl": (r_mem, _sha256_file(r_mem)),
            "r_summary_json": (r_sum, _sha256_file(r_sum)),
            "u_ledger_jsonl": (u_ledger, _sha256_file(u_ledger)),
            "u_summary_json": (u_sum, _sha256_file(u_sum)),
            "old_source_binding_json": (old_b, ob_sha),
        }
        return {
            "case_dir": case_dir,
            "u_root": u_root,
            "r_root": r_root,
            "old_bind_dir": old_bind_dir,
            "out_parent": out_parent,
            "specs": specs,
            "expected_counts": copy.deepcopy(master_fx["expected_counts"]),
        }

    def _refresh_specs_and_prepare(mp: pytest.MonkeyPatch, fx: dict[str, Any], tag: str) -> tuple[Path, str, Path]:
        for k in list(fx["specs"].keys()):
            p, _ = fx["specs"][k]
            fx["specs"][k] = (p, _sha256_file(p))
        _apply_fixture_monkeypatch(mp, fx)
        b_out = fx["case_dir"] / f"bind_{tag}.json"
        out_root = fx["out_parent"] / f"out_{tag}"
        assert (
            attr_mod.main(
                [
                    "prepare",
                    "--approved-plan-sha",
                    plan_sha,
                    "--binding-output",
                    str(b_out),
                    "--output-root",
                    str(out_root),
                ]
            )
            == 0
        )
        capsys.readouterr()
        return b_out, _sha256_file(b_out), out_root

    def _assert_stop_cause(rc: int, expected_cause: str, out_root: Path | None = None) -> None:
        captured = capsys.readouterr()
        assert rc == 2
        assert "STOP=input_invalid" in captured.err
        assert f"cause={expected_cause}" in captured.err
        if out_root is not None:
            assert not out_root.exists()

    # 1. code_or_authority_mismatch (wrong --approved-plan-sha in prepare; tampered code_bindings in run)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_auth")
        _apply_fixture_monkeypatch(mp, fx)
        out_r = fx["out_parent"] / "out_auth"
        rc = attr_mod.main(
            [
                "prepare",
                "--approved-plan-sha",
                "f" * 64,
                "--binding-output",
                str(fx["case_dir"] / "bad_bind.json"),
                "--output-root",
                str(out_r),
            ]
        )
        _assert_stop_cause(rc, "code_or_authority_mismatch", out_r)

        b_out, _, out_r2 = _refresh_specs_and_prepare(mp, fx, "tamper_code")
        b_json = json.loads(b_out.read_text(encoding="utf-8"))
        b_json["code_bindings"][0]["sha256"] = "0" * 64
        b_out.write_text(json.dumps(b_json, indent=2) + "\n", encoding="utf-8")
        rc2 = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", _sha256_file(b_out)])
        _assert_stop_cause(rc2, "code_or_authority_mismatch", out_r2)

    # 2. output_not_new (existing binding_output or existing output_root)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_out_exists")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "exists")
        # Existing binding_output on prepare
        rc_b = attr_mod.main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(b_out),
                "--output-root",
                str(fx["out_parent"] / "fresh_out"),
            ]
        )
        _assert_stop_cause(rc_b, "output_not_new")
        # Existing output_root on run
        out_r.mkdir(parents=True)
        rc_o = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_o, "output_not_new")
        assert list(out_r.iterdir()) == []

    # 3. hash_mismatch (corrupted input bytes after prepare; or wrong --binding-sha)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_hash")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "hash")
        rc_bs = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", "a" * 64])
        _assert_stop_cause(rc_bs, "hash_mismatch", out_r)

        u_ledger_p = fx["specs"]["u_ledger_jsonl"][0]
        u_ledger_p.write_text(u_ledger_p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        rc_in = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_in, "hash_mismatch", out_r)

    # 4. path_mismatch (cross-root identical bytes AND ancestor symlink on old_source_binding_json)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_path")
        b_out, _, out_r = _refresh_specs_and_prepare(mp, fx, "path")
        # Cross-root identical bytes in binding
        outside_copy = fx["case_dir"] / "outside_members.jsonl"
        shutil.copyfile(fx["specs"]["r_members_jsonl"][0], outside_copy)
        b_json = json.loads(b_out.read_text(encoding="utf-8"))
        b_json["fixed_inputs"]["r_members_jsonl"]["path"] = str(outside_copy)
        b_out.write_text(json.dumps(b_json, indent=2) + "\n", encoding="utf-8")
        rc_xr = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", _sha256_file(b_out)])
        _assert_stop_cause(rc_xr, "path_mismatch", out_r)

    with monkeypatch.context() as mp:
        fx_sym = _clone_case("c_anc_symlink")
        real_ob_dir = fx_sym["case_dir"] / "real_ob_dir"
        fx_sym["old_bind_dir"].rename(real_ob_dir)
        fx_sym["old_bind_dir"].symlink_to(real_ob_dir)
        _apply_fixture_monkeypatch(mp, fx_sym)
        out_r_sym = fx_sym["out_parent"] / "out_sym"
        rc_sym = attr_mod.main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(fx_sym["case_dir"] / "b_sym.json"),
                "--output-root",
                str(out_r_sym),
            ]
        )
        _assert_stop_cause(rc_sym, "path_mismatch", out_r_sym)

    # 5. reference_mismatch (r_summary source_binding_sha256 != old_source_binding_json SHA)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_ref")
        r_sum_p = fx["specs"]["r_summary_json"][0]
        rs_obj = json.loads(r_sum_p.read_text(encoding="utf-8"))
        rs_obj["source_binding_sha256"] = "9" * 64
        r_sum_p.write_text(json.dumps(rs_obj, indent=2) + "\n", encoding="utf-8")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "ref")
        rc_ref = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_ref, "reference_mismatch", out_r)

    # 6. protocol_mismatch (u_summary protocol altered)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_proto")
        u_sum_p = fx["specs"]["u_summary_json"][0]
        us_obj = json.loads(u_sum_p.read_text(encoding="utf-8"))
        us_obj["protocol"]["volume_spike_threshold"] = 4.0
        u_sum_p.write_text(json.dumps(us_obj, indent=2) + "\n", encoding="utf-8")
        # Sync u_summary sha into old_binding & r_summary so reference check passes and protocol check triggers!
        ob_p = fx["specs"]["old_source_binding_json"][0]
        ob_obj = json.loads(ob_p.read_text(encoding="utf-8"))
        ob_obj["fixed_inputs"]["summary_json"]["sha256"] = _sha256_file(u_sum_p)
        ob_p.write_text(json.dumps(ob_obj, indent=2) + "\n", encoding="utf-8")
        rs_p = fx["specs"]["r_summary_json"][0]
        rs_obj = json.loads(rs_p.read_text(encoding="utf-8"))
        rs_obj["source_binding_sha256"] = _sha256_file(ob_p)
        rs_obj["fixed_inputs"] = ob_obj["fixed_inputs"]
        rs_p.write_text(json.dumps(rs_obj, indent=2) + "\n", encoding="utf-8")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "proto")
        rc_pr = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_pr, "protocol_mismatch", out_r)

    # 7. cohort_mismatch (missing member in r_members.jsonl vs B admitted in u_ledger.jsonl)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_cohort")
        r_mem_p = fx["specs"]["r_members_jsonl"][0]
        lines = r_mem_p.read_text(encoding="utf-8").splitlines()
        r_mem_p.write_text(lines[0] + "\n", encoding="utf-8")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "cohort")
        rc_ch = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_ch, "cohort_mismatch", out_r)

    # 8. duplicate_key (duplicated member line in r_members.jsonl)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_dup")
        r_mem_p = fx["specs"]["r_members_jsonl"][0]
        lines = r_mem_p.read_text(encoding="utf-8").splitlines()
        r_mem_p.write_text("\n".join(lines + [lines[0]]) + "\n", encoding="utf-8")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "dup")
        rc_dp = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_dp, "duplicate_key", out_r)

    # 9. time_or_price_mismatch (member entry_open_price disagrees with ledger / formula)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_price")
        r_mem_p = fx["specs"]["r_members_jsonl"][0]
        m_rows = [json.loads(ln) for ln in r_mem_p.read_text(encoding="utf-8").splitlines()]
        m_rows[0]["entry_open_price"] = float(m_rows[0]["entry_open_price"]) + 5.0
        r_mem_p.write_text(
            "\n".join(json.dumps(m, ensure_ascii=False, allow_nan=False) for m in m_rows) + "\n",
            encoding="utf-8",
        )
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "price")
        rc_tp = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_tp, "time_or_price_mismatch", out_r)

    # 10. nonfinite_value (literal NaN injected into r_members.jsonl)
    with monkeypatch.context() as mp:
        fx = _clone_case("c_nan")
        r_mem_p = fx["specs"]["r_members_jsonl"][0]
        m_rows = [json.loads(ln) for ln in r_mem_p.read_text(encoding="utf-8").splitlines()]
        m_rows[0]["y_gross_bps"] = float("nan")
        r_mem_p.write_text(
            "\n".join(json.dumps(m, ensure_ascii=False, allow_nan=True) for m in m_rows) + "\n",
            encoding="utf-8",
        )
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "nan")
        rc_nan = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_nan, "nonfinite_value", out_r)

    # 11a. input_changed_during_run — content mutation after read, before publish
    with monkeypatch.context() as mp:
        fx = _clone_case("c_mut_content")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "mut_content")
        orig_desc = attr_mod.describe_attribution

        def _mutate_content_mid_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
            res = orig_desc(*args, **kwargs)
            p = fx["specs"]["r_members_jsonl"][0]
            p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            return res

        mp.setattr(attr_mod, "describe_attribution", _mutate_content_mid_run)
        rc_mc = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_mc, "input_changed_during_run", out_r)

    # 11b. input_changed_during_run — identical-byte directory relocation + symlink back before publish!
    with monkeypatch.context() as mp:
        fx = _clone_case("c_mut_reloc")
        b_out, b_sha, out_r = _refresh_specs_and_prepare(mp, fx, "mut_reloc")
        orig_desc = attr_mod.describe_attribution

        def _relocate_root_with_symlink_mid_run(*args: Any, **kwargs: Any) -> dict[str, Any]:
            res = orig_desc(*args, **kwargs)
            moved_r = fx["case_dir"] / "relocated_r_run_identical_bytes"
            fx["r_root"].rename(moved_r)
            fx["r_root"].symlink_to(moved_r)
            return res

        mp.setattr(attr_mod, "describe_attribution", _relocate_root_with_symlink_mid_run)
        rc_mr = attr_mod.main(["run", "--binding", str(b_out), "--binding-sha", b_sha])
        _assert_stop_cause(rc_mr, "input_changed_during_run", out_r)
