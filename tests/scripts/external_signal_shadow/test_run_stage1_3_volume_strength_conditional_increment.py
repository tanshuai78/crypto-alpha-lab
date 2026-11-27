from __future__ import annotations

import copy
import hashlib
import json
import socket
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

import scripts.external_signal_shadow.run_stage1_3_volume_strength_conditional_increment as cli_mod
from research.external_signal_shadow.stage1_3_fixed_universe_diagnostic import (
    DiagnosticStopError,
    analyze_bars,
    build_default_protocol,
    build_event_ledger,
)
from research.external_signal_shadow.stage1_3_models import HistoricalBar
from scripts.external_signal_shadow.run_stage1_3_volume_strength_conditional_increment import (
    build_cohort,
    classify_observation,
    main,
    reduce_block_sample,
    summarize_cohort,
)

MS_15M = 15 * 60 * 1000
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def _utc_ms(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1000)


def _make_168d_canonical_bars(
    overrides: dict[tuple[str, int], dict[str, float]] | None = None,
) -> list[HistoricalBar]:
    """Generate complete 168-day [2026-06-08T00:00:00Z, 2026-11-23T00:00:00Z) 15m canonical bars."""
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


def _serialize_and_reload_ledger_rows(bars: list[HistoricalBar], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    """Produce canonical upstream decision_points via build_event_ledger and round-trip JSONL."""
    ledger = build_event_ledger(bars, protocol=protocol)
    lines: list[str] = []
    for cand_name in protocol["candidates"]:
        for pt in ledger["candidates"][cand_name]["decision_points"]:
            lines.append(json.dumps(dict(pt), ensure_ascii=False, allow_nan=False))
    return [json.loads(line) for line in lines]


def _make_plan_section4_dual_rs_with_volume_bars(*, include_volume_spike: bool = True) -> list[HistoricalBar]:
    """Exact Plan §4 canonical dual-RS fixture (with optional 2026-06-15 11:30 volume spike)."""
    overrides: dict[tuple[str, int], dict[str, float]] = {
        ("ETHUSDT", _utc_ms("2026-06-14T11:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.0,
            "low_price": 100.0,
            "close_price": 101.0,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-15T11:45:00Z")): {
            "open_price": 100.0,
            "high_price": 101.5,
            "low_price": 100.0,
            "close_price": 101.5,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-15T16:00:00Z")): {
            "open_price": 100.0,
            "high_price": 103.0,
            "low_price": 99.0,
            "close_price": 102.0,
            "quote_volume": 25.0,
        },
        ("ETHUSDT", _utc_ms("2026-06-16T11:45:00Z")): {
            "open_price": 100.0,
            "high_price": 100.01,
            "low_price": 100.0,
            "close_price": 100.01,
            "quote_volume": 25.0,
        },
    }
    if include_volume_spike:
        overrides[("ETHUSDT", _utc_ms("2026-06-15T11:30:00Z"))] = {
            "open_price": 100.0,
            "high_price": 100.0,
            "low_price": 100.0,
            "close_price": 100.0,
            "quote_volume": 325.0,
        }
    return _make_168d_canonical_bars(overrides)


def test_cohort_canonical_and_a_overlap() -> None:
    """Task 1: canonical dual-RS + volume spike produces exact {k1, k2}, A overlap=True, and negative self_r1h."""
    proto = build_default_protocol()

    # 1. Exact Plan §4 canonical fixture (A overlap_suppressed at k1, A not_triggered at k2)
    rows_vol = _serialize_and_reload_ledger_rows(
        _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True), proto
    )
    cohort = build_cohort(rows_vol, protocol=proto)

    k1 = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z"))
    k2 = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T16:16:00Z"))

    actual_keys = {(m["candidate"], m["symbol"], m["available_at_ms"]) for m in cohort["members"]}
    assert actual_keys == {k1, k2}
    assert cohort["counts"]["q_total"] == 2
    assert cohort["counts"]["joint_all_count"] == 1
    assert cohort["counts"]["b_only_all_count"] == 1
    assert cohort["counts"]["joint_supported_count"] == 1
    assert cohort["counts"]["joint_unmatched_count"] == 0
    assert len(cohort["strata"]) == 4 * 23  # all 92 strata retained including zero-event strata

    by_key = {(m["candidate"], m["symbol"], m["available_at_ms"]): m for m in cohort["members"]}
    m1 = by_key[k1]
    m2 = by_key[k2]

    # k1: 12:00 window_end -> 12:01 available -> 12:15 entry -> 16:15 exit, Y=200 bps, A=overlap_suppressed (4.0)
    assert m1["window_end_ms"] == _utc_ms("2026-06-15T12:00:00Z")
    assert m1["entry_bar_start_ms"] == _utc_ms("2026-06-15T12:15:00Z")
    assert m1["exit_bar_end_ms"] == _utc_ms("2026-06-15T16:15:00Z")
    assert m1["y_gross_bps"] == pytest.approx(200.0)
    assert m1["a_status"] == "overlap_suppressed"
    assert m1["a_trigger_value"] == pytest.approx(4.0)
    assert m1["a_triggered"] is True
    assert m1["group"] == "joint"
    assert m1["in_common_support"] is True
    assert m1["conditional_control_keys"] == [
        ["relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T16:16:00Z")]
    ]

    # k2: 16:15 window_end -> 16:16 available -> 16:30 entry -> 20:30 exit, Y=0 bps, A=not_triggered (None)
    assert m2["window_end_ms"] == _utc_ms("2026-06-15T16:15:00Z")
    assert m2["entry_bar_start_ms"] == _utc_ms("2026-06-15T16:30:00Z")
    assert m2["exit_bar_end_ms"] == _utc_ms("2026-06-15T20:30:00Z")
    assert m2["y_gross_bps"] == pytest.approx(0.0)
    assert m2["a_status"] == "not_triggered"
    assert m2["a_trigger_value"] is None
    assert m2["a_triggered"] is False
    assert m2["group"] == "b_only"
    assert m2["in_common_support"] is True
    assert m2["conditional_control_keys"] == []

    # 2. Compare against no-volume-spike canonical version -> B queue keys {k1, k2} MUST NOT change!
    rows_novol = _serialize_and_reload_ledger_rows(
        _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=False), proto
    )
    cohort_novol = build_cohort(rows_novol, protocol=proto)
    novol_keys = {(m["candidate"], m["symbol"], m["available_at_ms"]) for m in cohort_novol["members"]}
    assert novol_keys == {k1, k2}
    assert cohort_novol["counts"]["joint_all_count"] == 0
    assert cohort_novol["counts"]["b_only_all_count"] == 2

    # 3. Verify A="admitted" + negative self_r1h (ETH falls -1%, BTC falls -3% -> spread +2% triggers RS; vol=325 at 11:45 -> A admitted!)
    # Also include a B overlap_suppressed trigger at 12:15 to prove B overlap_suppressed is NEVER promoted into Q!
    neg_self_overrides: dict[tuple[str, int], dict[str, float]] = {
        ("ETHUSDT", _utc_ms("2026-06-14T11:45:00Z")): {"close_price": 101.0},
        ("ETHUSDT", _utc_ms("2026-06-15T11:45:00Z")): {
            "open_price": 100.0,
            "high_price": 100.0,
            "low_price": 99.0,
            "close_price": 99.0,
            "quote_volume": 325.0,
        },
        ("BTCUSDT", _utc_ms("2026-06-15T11:45:00Z")): {
            "open_price": 100.0,
            "high_price": 100.0,
            "low_price": 97.0,
            "close_price": 97.0,
            "quote_volume": 25.0,
        },
        # At 12:00..12:15 BTC stays low so 12:15 window also triggers RS while occupied by 12:01 admitted RS event
        ("BTCUSDT", _utc_ms("2026-06-15T12:00:00Z")): {
            "open_price": 97.0,
            "high_price": 97.0,
            "low_price": 97.0,
            "close_price": 97.0,
            "quote_volume": 25.0,
        },
    }
    rows_neg = _serialize_and_reload_ledger_rows(_make_168d_canonical_bars(neg_self_overrides), proto)
    # Confirm upstream actually produced a B overlap_suppressed row that must NOT enter Q
    assert any(
        r["candidate"] == "relative_strength_vs_btc" and r["status"] == "overlap_suppressed"
        for r in rows_neg
    )
    cohort_neg = build_cohort(rows_neg, protocol=proto)
    neg_by_key = {(m["candidate"], m["symbol"], m["available_at_ms"]): m for m in cohort_neg["members"]}
    assert k1 in neg_by_key
    assert neg_by_key[k1]["self_r1h"] == pytest.approx(-0.01)
    assert neg_by_key[k1]["a_status"] == "admitted"
    assert neg_by_key[k1]["a_triggered"] is True
    assert ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:16:00Z")) not in neg_by_key


def test_cohort_rejects_missing_duplicate_unknown_and_time() -> None:
    """Task 1 negative checks: exact STOP=cohort_contract_mismatch / STOP=cohort_time_mismatch on single mutations."""
    proto = build_default_protocol()
    base_rows = _serialize_and_reload_ledger_rows(
        _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True), proto
    )
    target_avail = _utc_ms("2026-06-15T12:01:00Z")

    # Sanity check: A non-admitted rows have null prices/returns in base_rows and MUST be accepted as-is
    a_k1 = next(
        r
        for r in base_rows
        if r["candidate"] == "volume_spike_1h"
        and r["symbol"] == "ETHUSDT"
        and r["available_at_ms"] == target_avail
    )
    assert a_k1["status"] == "overlap_suppressed"
    assert a_k1["entry_open_price"] is None and a_k1["y_gross_bps"] is None
    assert build_cohort(copy.deepcopy(base_rows), protocol=proto)["counts"]["q_total"] == 2

    def _mutate_row(
        *,
        cand: str,
        avail_ms: int,
        updates: dict[str, Any],
    ) -> list[dict[str, Any]]:
        cloned = copy.deepcopy(base_rows)
        for r in cloned:
            if r["candidate"] == cand and r["symbol"] == "ETHUSDT" and r["available_at_ms"] == avail_ms:
                r.update(updates)
                break
        return cloned

    # 1. Missing paired A row -> STOP=cohort_contract_mismatch (never defaults to A=0)
    missing_a = [
        r
        for r in copy.deepcopy(base_rows)
        if not (
            r["candidate"] == "volume_spike_1h"
            and r["symbol"] == "ETHUSDT"
            and r["available_at_ms"] == target_avail
        )
    ]
    with pytest.raises(DiagnosticStopError) as exc_miss:
        build_cohort(missing_a, protocol=proto)
    assert exc_miss.value.stop_code == "cohort_contract_mismatch"

    # 2. Duplicate key -> STOP=cohort_contract_mismatch
    dup_rows = copy.deepcopy(base_rows) + [copy.deepcopy(a_k1)]
    with pytest.raises(DiagnosticStopError) as exc_dup:
        build_cohort(dup_rows, protocol=proto)
    assert exc_dup.value.stop_code == "cohort_contract_mismatch"

    # 3. Paired A status in {feature_not_estimable, block_boundary_censored, unknown} -> STOP=cohort_contract_mismatch
    for bad_status in ("feature_not_estimable", "block_boundary_censored", "unknown_state"):
        with pytest.raises(DiagnosticStopError) as exc_st:
            build_cohort(
                _mutate_row(cand="volume_spike_1h", avail_ms=target_avail, updates={"status": bad_status}),
                protocol=proto,
            )
        assert exc_st.value.stop_code == "cohort_contract_mismatch"

    # 4. Status vs trigger_value contradictions -> STOP=cohort_contract_mismatch
    for bad_updates in (
        {"status": "not_triggered", "trigger_value": 3.5},
        {"status": "admitted", "trigger_value": None},
        {"status": "overlap_suppressed", "trigger_value": 2.99},
    ):
        with pytest.raises(DiagnosticStopError) as exc_tv:
            build_cohort(
                _mutate_row(cand="volume_spike_1h", avail_ms=target_avail, updates=bad_updates),
                protocol=proto,
            )
        assert exc_tv.value.stop_code == "cohort_contract_mismatch"

    # 5. Non-finite values (NaN / Infinity) -> STOP=cohort_contract_mismatch
    for nf_val in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(DiagnosticStopError) as exc_nf:
            build_cohort(
                _mutate_row(
                    cand="relative_strength_vs_btc",
                    avail_ms=target_avail,
                    updates={"y_gross_bps": nf_val},
                ),
                protocol=proto,
            )
        assert exc_nf.value.stop_code == "cohort_contract_mismatch"

    # 6. Price-return formula mismatch -> STOP=cohort_contract_mismatch
    with pytest.raises(DiagnosticStopError) as exc_pr:
        build_cohort(
            _mutate_row(
                cand="relative_strength_vs_btc",
                avail_ms=target_avail,
                updates={"y_gross_bps": 205.0},
            ),
            protocol=proto,
        )
    assert exc_pr.value.stop_code == "cohort_contract_mismatch"

    # 7. Hand-calculated causal timing checks (12:00 -> 12:01 -> 12:15 -> 16:15) -> STOP=cohort_time_mismatch
    for time_mutation in (
        {"window_start_ms": _utc_ms("2026-06-15T11:15:00Z")},
        {"window_end_ms": _utc_ms("2026-06-15T12:00:01Z")},
        {"block_id": 1},
        {"entry_bar_start_ms": _utc_ms("2026-06-15T12:00:00Z")},
        {"exit_bar_end_ms": _utc_ms("2026-06-15T16:00:00Z")},
    ):
        with pytest.raises(DiagnosticStopError) as exc_tm:
            build_cohort(
                _mutate_row(
                    cand="relative_strength_vs_btc",
                    avail_ms=target_avail,
                    updates=time_mutation,
                ),
                protocol=proto,
            )
        assert exc_tm.value.stop_code == "cohort_time_mismatch"

    # Also mismatch between paired A and B entry_bar_start_ms -> STOP=cohort_time_mismatch
    with pytest.raises(DiagnosticStopError) as exc_pair_tm:
        build_cohort(
            _mutate_row(
                cand="volume_spike_1h",
                avail_ms=target_avail,
                updates={"entry_bar_start_ms": _utc_ms("2026-06-15T12:30:00Z")},
            ),
            protocol=proto,
        )
    assert exc_pair_tm.value.stop_code == "cohort_time_mismatch"

    # 8. Overlapping B admitted events on same symbol violate non-overlap invariant -> STOP=cohort_time_mismatch
    overlap_avail = _utc_ms("2026-06-15T12:16:00Z")
    with pytest.raises(DiagnosticStopError) as exc_ov:
        build_cohort(
            _mutate_row(
                cand="relative_strength_vs_btc",
                avail_ms=overlap_avail,
                updates={
                    "status": "admitted",
                    "occupied_by_admitted_event": False,
                    "trigger_value": 2.0,
                    "entry_open_price": 100.0,
                    "exit_close_price": 100.0,
                    "y_gross_bps": 0.0,
                    "mfe_4h_bps": 0.0,
                    "mae_4h_bps": 0.0,
                },
            ),
            protocol=proto,
        )
    assert exc_ov.value.stop_code == "cohort_time_mismatch"


def _make_synthetic_cohort_from_specs(
    items: list[tuple[str, int, bool, float]],
    *,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    """Build a minimal synthetic cohort structure from (symbol, block_id, a_triggered, y_bps) for pure-math tests."""
    target_symbols = [s for s in protocol["symbols"] if s != "BTCUSDT"]
    block_count = int(protocol["block_count"])
    eval_start_ms = int(protocol["eval_start_ms"])
    block_ms = int(protocol["block_days"]) * 86_400_000

    strata_joint: dict[tuple[str, int], list[dict[str, Any]]] = {
        (s, b): [] for s in target_symbols for b in range(block_count)
    }
    strata_b_only: dict[tuple[str, int], list[dict[str, Any]]] = {
        (s, b): [] for s in target_symbols for b in range(block_count)
    }
    members: list[dict[str, Any]] = []

    for idx, (sym, block_id, a_trig, y_bps) in enumerate(items):
        win_end = eval_start_ms + block_id * block_ms + (idx + 1) * MS_15M
        avail_ms = win_end + 60_000
        entry_ms = win_end + MS_15M
        exit_ms = entry_ms + 16 * MS_15M
        exit_close = 100.0 * (1.0 + y_bps / 10000.0)
        m: dict[str, Any] = {
            "candidate": "relative_strength_vs_btc",
            "symbol": sym,
            "available_at_ms": avail_ms,
            "block_id": block_id,
            "window_start_ms": win_end - 4 * MS_15M,
            "window_end_ms": win_end,
            "utc_end_hour": (win_end // 3_600_000) % 24,
            "available_at_utc_hour": (avail_ms // 3_600_000) % 24,
            "entry_bar_start_ms": entry_ms,
            "exit_bar_end_ms": exit_ms,
            "entry_open_price": 100.0,
            "exit_close_price": exit_close,
            "self_r1h": 0.02 if a_trig else 0.01,
            "btc_r1h": 0.0,
            "b_trigger_value": 2.5 if a_trig else 1.8,
            "y_gross_bps": float(y_bps),
            "mfe_4h_bps": max(10.0, float(y_bps) + 20.0),
            "mae_4h_bps": min(-10.0, float(y_bps) - 15.0),
            "a_key": ["volume_spike_1h", sym, avail_ms],
            "a_status": "admitted" if a_trig else "not_triggered",
            "a_trigger_value": 3.5 if a_trig else None,
            "a_triggered": a_trig,
            "group": "joint" if a_trig else "b_only",
        }
        members.append(m)
        if a_trig:
            strata_joint[(sym, block_id)].append(m)
        else:
            strata_b_only[(sym, block_id)].append(m)

    strata_records: list[dict[str, Any]] = []
    support_map: dict[tuple[str, int], bool] = {}
    supp_strata = 0
    for s in target_symbols:
        for b in range(block_count):
            n1 = len(strata_joint[(s, b)])
            n0 = len(strata_b_only[(s, b)])
            in_supp = n1 > 0 and n0 > 0
            support_map[(s, b)] = in_supp
            if in_supp:
                supp_strata += 1
            strata_records.append(
                {
                    "symbol": s,
                    "block_id": b,
                    "n_q": n1 + n0,
                    "n_s1_joint": n1,
                    "n_s0_b_only": n0,
                    "in_common_support": in_supp,
                }
            )

    j_all = 0
    b_all = 0
    j_supp = 0
    j_unm = 0
    b_supp = 0
    for m in members:
        sk = (m["symbol"], m["block_id"])
        in_supp = support_map[sk]
        m["in_common_support"] = in_supp
        if m["a_triggered"]:
            j_all += 1
            if in_supp:
                j_supp += 1
                m["support_status"] = "supported"
                m["conditional_control_keys"] = [
                    ["relative_strength_vs_btc", c["symbol"], c["available_at_ms"]]
                    for c in strata_b_only[sk]
                ]
            else:
                j_unm += 1
                m["support_status"] = "unmatched"
                m["conditional_control_keys"] = []
        else:
            b_all += 1
            if in_supp:
                b_supp += 1
                m["support_status"] = "control_in_support"
            else:
                m["support_status"] = "b_only_unpaired_stratum"
            m["conditional_control_keys"] = []

    return {
        "protocol": protocol,
        "target_symbols": target_symbols,
        "status_counts_by_candidate": {},
        "counts": {
            "q_total": len(members),
            "joint_all_count": j_all,
            "b_only_all_count": b_all,
            "joint_supported_count": j_supp,
            "joint_unmatched_count": j_unm,
            "b_only_in_support_count": b_supp,
            "b_only_unpaired_stratum_count": b_all - b_supp,
            "total_strata": len(strata_records),
            "common_support_strata_count": supp_strata,
        },
        "strata": strata_records,
        "members": members,
    }


def test_statistics_hand_oracle_support_weights() -> None:
    """Task 2: pure-math two-stratum support weighting oracle + unmatched +1000 invariance + without-best."""
    proto = build_default_protocol()
    # Stratum 1 (ETH, block 0): joint [100, 0], B-only [20, 40] -> mean_s0=30, d=[70, -30]
    # Stratum 2 (SOL, block 1): joint [-20], B-only [0, 0, 0] -> mean_s0=0, d=[-20]
    base_specs = [
        ("ETHUSDT", 0, True, 100.0),
        ("ETHUSDT", 0, True, 0.0),
        ("ETHUSDT", 0, False, 20.0),
        ("ETHUSDT", 0, False, 40.0),
        ("SOLUSDT", 1, True, -20.0),
        ("SOLUSDT", 1, False, 0.0),
        ("SOLUSDT", 1, False, 0.0),
        ("SOLUSDT", 1, False, 0.0),
    ]
    coh_base = _make_synthetic_cohort_from_specs(base_specs, protocol=proto)
    res_base = summarize_cohort(coh_base, protocol=proto)
    s_base = res_base["summary"]

    assert s_base["mu_joint_all_bps"] == pytest.approx(80.0 / 3.0)
    assert s_base["mu_joint_supported_bps"] == pytest.approx(80.0 / 3.0)
    assert s_base["mu_control_reweighted_bps"] == pytest.approx(20.0)
    assert s_base["delta_bps"] == pytest.approx(20.0 / 3.0)
    # Global unweighted B-only mean is (20+40+0+0+0)/5 = 12.0 != reweighted 20.0
    assert s_base["distributions"]["b_only_all"]["mean_bps"] == pytest.approx(12.0)

    # Without best event (+100 in Stratum 1): remaining joint=[0, -20] -> mu=-10; remaining d=[-30, -20] -> Delta=-25
    wb_base = s_base["diagnostics"]["without_best_joint_event"]
    assert wb_base["mu_joint_all_bps"] == pytest.approx(-10.0)
    assert wb_base["delta_bps"] == pytest.approx(-25.0)

    # Add unmatched resonance event +1000 in (XRPUSDT, block 2) -> mu_joint_all=270, Delta unchanged (20/3)
    plus_unmatched = base_specs + [("XRPUSDT", 2, True, 1000.0)]
    coh_unm = _make_synthetic_cohort_from_specs(plus_unmatched, protocol=proto)
    s_unm = summarize_cohort(coh_unm, protocol=proto)["summary"]

    assert s_unm["counts"]["joint_all_count"] == 4
    assert s_unm["counts"]["joint_supported_count"] == 3
    assert s_unm["counts"]["joint_unmatched_count"] == 1
    assert s_unm["mu_joint_all_bps"] == pytest.approx(270.0)
    assert s_unm["mu_joint_supported_bps"] == pytest.approx(80.0 / 3.0)
    assert s_unm["mu_control_reweighted_bps"] == pytest.approx(20.0)
    assert s_unm["delta_bps"] == pytest.approx(20.0 / 3.0)

    # Without best event now removes unmatched +1000 -> mu reverts to 80/3, Delta stays 20/3!
    wb_unm = s_unm["diagnostics"]["without_best_joint_event"]
    assert wb_unm["mu_joint_all_bps"] == pytest.approx(80.0 / 3.0)
    assert wb_unm["delta_bps"] == pytest.approx(20.0 / 3.0)


def test_statistics_no_common_support_preserves_marginals() -> None:
    """Task 2: zero common support preserves marginal joint_all, cost scenarios, and b_only_all."""
    proto = build_default_protocol()

    # Case 1: ETH/block0 joint +100, SOL/block0 B-only +20 -> 0 common support
    specs_disjoint = [
        ("ETHUSDT", 0, True, 100.0),
        ("SOLUSDT", 0, False, 20.0),
    ]
    coh_dis = _make_synthetic_cohort_from_specs(specs_disjoint, protocol=proto)
    s_dis = summarize_cohort(coh_dis, protocol=proto)["summary"]

    assert s_dis["counts"]["q_total"] == 2
    assert s_dis["counts"]["joint_all_count"] == 1
    assert s_dis["counts"]["joint_supported_count"] == 0
    assert s_dis["counts"]["joint_unmatched_count"] == 1
    assert s_dis["mu_joint_all_bps"] == pytest.approx(100.0)
    assert s_dis["distributions"]["b_only_all"]["mean_bps"] == pytest.approx(20.0)
    assert s_dis["mu_joint_supported_bps"] is None
    assert s_dis["mu_control_reweighted_bps"] is None
    assert s_dis["delta_bps"] is None
    assert s_dis["cost_scenarios_joint_all"]["30.0"]["mean_bps"] == pytest.approx(70.0)
    assert s_dis["cost_scenarios_joint_all"]["50.0"]["mean_bps"] == pytest.approx(50.0)
    assert s_dis["cost_scenarios_joint_all"]["80.0"]["mean_bps"] == pytest.approx(20.0)
    assert s_dis["routing"] == {
        "observation_label": "not_estimable",
        "resource_decision": "stop_due_to_evidence",
        "alpha_research_status": "evidence_insufficient",
    }
    # Block 0 draw gives mu=100, delta=None; empty block 1 draw gives (None, None)
    bstats = s_dis["block_stats"]
    assert reduce_block_sample(bstats, [0]) == {"mu_gross_bps": pytest.approx(100.0), "delta_bps": None}
    assert reduce_block_sample(bstats, [1]) == {"mu_gross_bps": None, "delta_bps": None}
    assert s_dis["bootstrap"]["delta_bps"]["valid_replicates"] == 0
    assert s_dis["bootstrap"]["delta_bps"]["empty_replicates"] == 10000
    assert s_dis["bootstrap"]["delta_bps"]["ci_complete"] is False

    # Case 2: Zero joint events, non-empty B-only [20, 40] -> preserves B-only distribution
    coh_bonly = _make_synthetic_cohort_from_specs(
        [("ETHUSDT", 0, False, 20.0), ("SOLUSDT", 1, False, 40.0)],
        protocol=proto,
    )
    s_bonly = summarize_cohort(coh_bonly, protocol=proto)["summary"]
    assert s_bonly["mu_joint_all_bps"] is None
    assert s_bonly["delta_bps"] is None
    assert s_bonly["distributions"]["b_only_all"]["n"] == 2
    assert s_bonly["distributions"]["b_only_all"]["mean_bps"] == pytest.approx(30.0)
    assert s_bonly["routing"]["observation_label"] == "not_estimable"
    assert s_bonly["routing"]["resource_decision"] == "stop_due_to_evidence"


def test_statistics_block_diagnostics_and_null() -> None:
    """Task 2: 23-block reduction oracle ([0,0], [0,1], [1,1], empty) and fixed half/leave-one-out."""
    proto = build_default_protocol()
    specs = [
        ("ETHUSDT", 0, True, 100.0),
        ("ETHUSDT", 0, True, 0.0),
        ("ETHUSDT", 0, False, 20.0),
        ("ETHUSDT", 0, False, 40.0),
        ("SOLUSDT", 1, True, -20.0),
        ("SOLUSDT", 1, False, 0.0),
        ("SOLUSDT", 1, False, 0.0),
        ("SOLUSDT", 1, False, 0.0),
    ]
    s = summarize_cohort(_make_synthetic_cohort_from_specs(specs, protocol=proto), protocol=proto)["summary"]
    bstats = s["block_stats"]
    assert len(bstats) == 23
    assert (bstats[0]["sum_y"], bstats[0]["n"], bstats[0]["sum_d"], bstats[0]["m"]) == (
        pytest.approx(100.0),
        2,
        pytest.approx(40.0),
        2,
    )
    assert (bstats[1]["sum_y"], bstats[1]["n"], bstats[1]["sum_d"], bstats[1]["m"]) == (
        pytest.approx(-20.0),
        1,
        pytest.approx(-20.0),
        1,
    )
    assert reduce_block_sample(bstats, [0, 0]) == {
        "mu_gross_bps": pytest.approx(50.0),
        "delta_bps": pytest.approx(20.0),
    }
    assert reduce_block_sample(bstats, [0, 1]) == {
        "mu_gross_bps": pytest.approx(80.0 / 3.0),
        "delta_bps": pytest.approx(20.0 / 3.0),
    }
    assert reduce_block_sample(bstats, [1, 1]) == {
        "mu_gross_bps": pytest.approx(-20.0),
        "delta_bps": pytest.approx(-20.0),
    }
    assert reduce_block_sample(bstats, [5, 6]) == {"mu_gross_bps": None, "delta_bps": None}

    diag = s["diagnostics"]
    assert diag["first_half_blocks_0_10"]["mu_joint_all_bps"] == pytest.approx(80.0 / 3.0)
    assert diag["first_half_blocks_0_10"]["delta_bps"] == pytest.approx(20.0 / 3.0)
    assert diag["second_half_blocks_11_22"]["mu_joint_all_bps"] is None
    assert diag["second_half_blocks_11_22"]["delta_bps"] is None
    assert diag["leave_one_block_out"]["0"]["mu_joint_all_bps"] == pytest.approx(-20.0)
    assert diag["leave_one_block_out"]["0"]["delta_bps"] == pytest.approx(-20.0)
    assert diag["leave_one_block_out"]["1"]["mu_joint_all_bps"] == pytest.approx(50.0)
    assert diag["leave_one_block_out"]["1"]["delta_bps"] == pytest.approx(20.0)
    assert diag["leave_one_symbol_out"]["ETHUSDT"]["mu_joint_all_bps"] == pytest.approx(-20.0)
    assert diag["leave_one_symbol_out"]["SOLUSDT"]["delta_bps"] == pytest.approx(20.0)


def test_statistics_distribution_cost_and_routing() -> None:
    """Task 2: distributions, Top-K over N_joint, cost shifts, governance flags, and all 6 §6 routing rows."""
    proto = build_default_protocol()

    # 10 joint events [+100] + [-20]*9 in ETH/block0 + B-only [0] -> N_joint=10, m_pos=1 -> Top-1/3/10% all 1.0!
    specs_topk = [("ETHUSDT", 0, True, 100.0)] + [("ETHUSDT", 0, True, -20.0) for _ in range(9)] + [
        ("ETHUSDT", 0, False, 0.0)
    ]
    s_tk = summarize_cohort(_make_synthetic_cohort_from_specs(specs_topk, protocol=proto), protocol=proto)["summary"]
    pc = s_tk["positive_contribution_joint_all"]
    assert pc["n"] == 10
    assert pc["positive_count"] == 1
    assert pc["top_1_share"] == pytest.approx(1.0)
    assert pc["top_3_share"] == pytest.approx(1.0)
    assert pc["top_10pct_share"] == pytest.approx(1.0)

    # All non-positive joint events -> Top-K shares are None
    s_neg = summarize_cohort(
        _make_synthetic_cohort_from_specs([("ETHUSDT", 0, True, -10.0), ("ETHUSDT", 0, False, -20.0)], protocol=proto),
        protocol=proto,
    )["summary"]
    assert s_neg["positive_contribution_joint_all"]["top_1_share"] is None
    assert s_neg["positive_contribution_joint_all"]["top_3_share"] is None
    assert s_neg["positive_contribution_joint_all"]["top_10pct_share"] is None

    # Single Y=100 vs B-only 40 -> delta=60 unchanged across 30/50/80 cost scenarios (means 70/50/20)
    s_cost = summarize_cohort(
        _make_synthetic_cohort_from_specs([("ETHUSDT", 0, True, 100.0), ("ETHUSDT", 0, False, 40.0)], protocol=proto),
        protocol=proto,
    )["summary"]
    for c_key, exp_mean in (("30.0", 70.0), ("50.0", 50.0), ("80.0", 20.0)):
        assert s_cost["cost_scenarios_joint_all"][c_key]["mean_bps"] == pytest.approx(exp_mean)
        assert s_cost["cost_scenarios_joint_all"][c_key]["delta_bps"] == pytest.approx(60.0)
    assert s_cost["minimum_economically_meaningful_gain"] is None
    gov = s_cost["governance"]
    assert gov["live_trading_enabled"] is False
    assert gov["paper_trading_allowed"] is False
    assert gov["execution_engine_allowed"] is False
    assert gov["independent_out_of_sample_claim_allowed"] is False
    assert gov["distributions_bar_ordering_known"] is False

    # Pure-logic classify_observation across all 6 Plan §5 / Design §6 scenarios
    stable_base = {
        "prerequisites_valid": True,
        "mu_joint_all_bps": 50.0,
        "delta_bps": 10.0,
        "mu_ci_complete": True,
        "mu_ci_low": 5.0,
        "delta_ci_complete": True,
        "delta_ci_low": 2.0,
        "first_half_mu": 40.0,
        "first_half_delta": 8.0,
        "second_half_mu": 60.0,
        "second_half_delta": 12.0,
        "leave_one_symbol_all_positive": True,
        "leave_one_block_all_positive": True,
        "without_best_mu": 45.0,
        "without_best_delta": 9.0,
        "any_cost_scenario_mean_positive": True,
        "has_unexplained_input_issue": False,
    }
    # 1. No support / Delta=None
    assert classify_observation({**stable_base, "delta_bps": None}) == {
        "observation_label": "not_estimable",
        "resource_decision": "stop_due_to_evidence",
        "alpha_research_status": "evidence_insufficient",
    }
    # 2. mu=50, Delta=-1
    assert classify_observation({**stable_base, "mu_joint_all_bps": 50.0, "delta_bps": -1.0}) == {
        "observation_label": "no_increment_observed",
        "resource_decision": "stop_fixed_spec_this_round",
        "alpha_research_status": "evidence_insufficient",
    }
    # 3. mu=-20, Delta=10
    assert classify_observation({**stable_base, "mu_joint_all_bps": -20.0, "delta_bps": 10.0}) == {
        "observation_label": "relative_increment_without_positive_gross",
        "resource_decision": "stop_fixed_spec_this_round",
        "alpha_research_status": "evidence_insufficient",
    }
    # 4. mu=50, Delta=10, unstable (CI crosses 0, incomplete CI, half conflict, or leave-one-out null/non-positive)
    for unstable_patch in (
        {"delta_ci_low": 0.0},
        {"mu_ci_complete": False},
        {"second_half_mu": -1.0},
        {"second_half_delta": None},
        {"leave_one_symbol_all_positive": False},
        {"leave_one_block_all_positive": False},
        {"without_best_delta": 0.0},
    ):
        assert classify_observation({**stable_base, **unstable_patch}) == {
            "observation_label": "inconclusive_or_concentrated",
            "resource_decision": "pause_for_new_evidence",
            "alpha_research_status": "evidence_insufficient",
        }
    # 5. mu=50, Delta=10, stable & 30 bps cost scenario positive
    assert classify_observation(stable_base) == {
        "observation_label": "bounded_positive_pattern",
        "resource_decision": "consider_independent_validation_only",
        "alpha_research_status": "evidence_insufficient",
    }
    # 6. mu=20, Delta=10, stable & all 3 cost scenarios (30/50/80 bps) non-positive
    assert classify_observation(
        {**stable_base, "mu_joint_all_bps": 20.0, "any_cost_scenario_mean_positive": False}
    ) == {
        "observation_label": "bounded_positive_pattern",
        "resource_decision": "stop_strategy_development_this_round",
        "alpha_research_status": "evidence_insufficient",
    }


REPO_ROOT = Path(__file__).resolve().parents[3]
CUR_PLAN_REL = "docs/plans/2026-11-25-stage1-3-volume-strength-conditional-increment-implementation-plan_CN.md"
PRIOR_DESIGN_REL = "docs/designs/2026-11-23-stage1-3-fixed-universe-mean-return-diagnostic-design_CN.md"
PRIOR_PLAN_REL = "docs/plans/2026-11-24-stage1-3-fixed-universe-mean-return-diagnostic-implementation-plan_CN.md"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_synthetic_upstream_bundle(
    base_dir: Path,
    bars: list[HistoricalBar],
) -> tuple[dict[str, tuple[Path, str]], Path, int]:
    """Build a canonical synthetic upstream 4-file bundle from HistoricalBar -> build_event_ledger/analyze_bars."""
    proto = build_default_protocol()
    analysis = analyze_bars(bars, protocol=proto)

    up_run = base_dir / "upstream_run"
    (up_run / "results").mkdir(parents=True, exist_ok=True)
    manifest_path = base_dir / "synthetic_source_manifest.json"

    prior_design_sha = _sha256_file(REPO_ROOT / PRIOR_DESIGN_REL)
    prior_plan_sha = _sha256_file(REPO_ROOT / PRIOR_PLAN_REL)
    authority = {
        "repo_root": str(REPO_ROOT),
        "design_path": PRIOR_DESIGN_REL,
        "design_sha256": prior_design_sha,
        "plan_path": PRIOR_PLAN_REL,
        "plan_sha256": prior_plan_sha,
        "git_head": "9712c5580682062416497191250453b267b97040",
    }
    manifest_payload = {
        "manifest_version": 1,
        "authority": authority,
        "protocol": proto,
        "output": {"run_root": str(up_run)},
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8")
    manifest_sha = _sha256_file(manifest_path)

    # Write ledger.jsonl using the exact upstream writer structure
    ledger_path = up_run / "results" / "ledger.jsonl"
    with ledger_path.open("w", encoding="utf-8") as fh:
        for cand_name in proto["candidates"]:
            cand = analysis["candidates"][cand_name]
            ev_by_key = {(e["symbol"], e["available_at_ms"]): e for e in cand["event_records"]}
            for pt in cand["decision_points"]:
                row = dict(pt)
                key = (pt["symbol"], pt["available_at_ms"])
                if key in ev_by_key:
                    ev = ev_by_key[key]
                    row["control_keys"] = ev["control_keys"]
                    row["control_count"] = ev["control_count"]
                    row["control_mean_bps"] = ev["control_mean_bps"]
                    row["d_bps"] = ev["d_bps"]
                    row["match_status"] = ev["match_status"]
                fh.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")

    summary_path = up_run / "results" / "summary.json"
    summary_payload = {
        "generated_at_utc": "2026-11-25T00:00:00Z",
        "manifest_sha256": manifest_sha,
        "authority": authority,
        "protocol": proto,
        "governance": analysis["governance"],
        "excluded_outside_study_range_bar_counts": analysis["excluded_outside_study_range_bar_counts"],
        "candidates": {
            cand_name: analysis["candidates"][cand_name]["summary"]
            for cand_name in proto["candidates"]
        },
    }
    summary_path.write_text(json.dumps(summary_payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    # Include non-existent raw archive path inside coverage.json to prove our CLI NEVER recursively opens ZIPs!
    coverage_path = up_run / "coverage.json"
    coverage_payload = {
        "coverage_qualified": True,
        "stop_code": None,
        "manifest_sha256": manifest_sha,
        "archive_records": [
            {
                "object_id": "DO_NOT_OPEN_RAW_ZIP",
                "zip_relative_path": "raw/archives/NON_EXISTENT_TRAP.zip",
            }
        ],
    }
    coverage_path.write_text(json.dumps(coverage_payload, indent=2) + "\n", encoding="utf-8")

    specs = {
        "ledger_jsonl": (ledger_path, _sha256_file(ledger_path)),
        "summary_json": (summary_path, _sha256_file(summary_path)),
        "coverage_json": (coverage_path, _sha256_file(coverage_path)),
        "source_manifest_json": (manifest_path, manifest_sha),
    }
    b_admitted_n = int(analysis["candidates"]["relative_strength_vs_btc"]["summary"]["counts"]["admitted"])
    return specs, up_run, b_admitted_n


def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _deny(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("network socket access is strictly forbidden")

    monkeypatch.setattr(socket, "create_connection", _deny)


def test_cli_prepare_and_canonical_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3: canonical HistoricalBar -> build_event_ledger -> JSONL -> prepare -> run -> 200/200/0/200."""
    _forbid_network(monkeypatch)
    bars = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    specs, up_run, b_adm_n = _write_synthetic_upstream_bundle(tmp_path / "canon", bars)
    assert b_adm_n == 2

    out_parent = tmp_path / "evidence_out"
    out_parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", specs)
    monkeypatch.setattr(cli_mod, "EXPECTED_UPSTREAM_RUN_ROOT", up_run)
    monkeypatch.setattr(cli_mod, "ALLOWED_OUTPUT_PARENT", out_parent)
    monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_adm_n)

    plan_sha = _sha256_file(REPO_ROOT / CUR_PLAN_REL)
    binding_path = tmp_path / "source_binding.json"
    out_root = out_parent / "run_canon_01"

    rc_prep = main(
        [
            "prepare",
            "--approved-plan-sha",
            plan_sha,
            "--binding-output",
            str(binding_path),
            "--output-root",
            str(out_root),
        ]
    )
    assert rc_prep == 0
    assert binding_path.is_file()
    assert not out_root.exists()

    binding_sha = _sha256_file(binding_path)
    rc_run = main(["run", "--binding", str(binding_path), "--binding-sha", binding_sha])
    assert rc_run == 0
    assert (out_root / "EXECUTION_FINISHED").is_file()
    assert (out_root / "report_CN.md").is_file()

    members = [
        json.loads(line)
        for line in (out_root / "members.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    k1 = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T12:01:00Z"))
    k2 = ("relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T16:16:00Z"))
    assert {(m["candidate"], m["symbol"], m["available_at_ms"]) for m in members} == {k1, k2}
    for m in members:
        assert "control_keys" not in m
        assert "d_bps" not in m

    m_by_k = {(m["candidate"], m["symbol"], m["available_at_ms"]): m for m in members}
    assert m_by_k[k1]["conditional_control_keys"] == [
        ["relative_strength_vs_btc", "ETHUSDT", _utc_ms("2026-06-15T16:16:00Z")]
    ]
    assert m_by_k[k1]["conditional_control_mean_bps"] == pytest.approx(0.0)
    assert m_by_k[k1]["conditional_d_bps"] == pytest.approx(200.0)

    summ = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert summ["mu_joint_all_bps"] == pytest.approx(200.0)
    assert summ["mu_joint_supported_bps"] == pytest.approx(200.0)
    assert summ["mu_control_reweighted_bps"] == pytest.approx(0.0)
    assert summ["delta_bps"] == pytest.approx(200.0)
    assert summ["routing"] == {
        "observation_label": "inconclusive_or_concentrated",
        "resource_decision": "pause_for_new_evidence",
        "alpha_research_status": "evidence_insufficient",
    }


def test_cli_no_common_support_preserves_marginals_on_disk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 3 (Plan §6): CLI run with disjoint ETH joint +100 and SOL B-only +20 writes mu=100, delta=null, 70/50/20."""
    _forbid_network(monkeypatch)
    overrides: dict[tuple[str, int], dict[str, float]] = {
        # High-variance warmup spread on both ETH & SOL so only +5% triggers RS while +1%/+0.2% exit does not
        ("ETHUSDT", _utc_ms("2026-06-13T11:45:00Z")): {"close_price": 120.0},
        ("SOLUSDT", _utc_ms("2026-06-13T11:45:00Z")): {"close_price": 120.0},
        # ETH triggers BOTH RS and volume spike at 2026-06-15 12:01 -> forward 4h return +100 bps
        ("ETHUSDT", _utc_ms("2026-06-15T11:45:00Z")): {"close_price": 105.0, "quote_volume": 325.0},
        ("ETHUSDT", _utc_ms("2026-06-15T16:00:00Z")): {"close_price": 101.0},
        # SOL triggers RS WITHOUT volume spike at 2026-06-15 12:01 -> forward 4h return +20 bps
        ("SOLUSDT", _utc_ms("2026-06-15T11:45:00Z")): {"close_price": 105.0, "quote_volume": 25.0},
        ("SOLUSDT", _utc_ms("2026-06-15T16:00:00Z")): {"close_price": 100.2},
    }
    bars = _make_168d_canonical_bars(overrides)
    specs, up_run, b_adm_n = _write_synthetic_upstream_bundle(tmp_path / "nosupp", bars)
    assert b_adm_n == 2

    out_parent = tmp_path / "evidence_nosupp"
    out_parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", specs)
    monkeypatch.setattr(cli_mod, "EXPECTED_UPSTREAM_RUN_ROOT", up_run)
    monkeypatch.setattr(cli_mod, "ALLOWED_OUTPUT_PARENT", out_parent)
    monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_adm_n)

    plan_sha = _sha256_file(REPO_ROOT / CUR_PLAN_REL)
    binding_path = tmp_path / "nosupp_binding.json"
    out_root = out_parent / "run_nosupp_01"

    assert (
        main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(binding_path),
                "--output-root",
                str(out_root),
            ]
        )
        == 0
    )
    assert main(["run", "--binding", str(binding_path), "--binding-sha", _sha256_file(binding_path)]) == 0
    assert (out_root / "EXECUTION_FINISHED").is_file()

    summ = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert summ["mu_joint_all_bps"] == pytest.approx(100.0)
    assert summ["delta_bps"] is None
    assert summ["mu_joint_supported_bps"] is None
    assert summ["mu_control_reweighted_bps"] is None
    assert summ["distributions"]["b_only_all"]["mean_bps"] == pytest.approx(20.0)
    assert summ["cost_scenarios_joint_all"]["30.0"]["mean_bps"] == pytest.approx(70.0)
    assert summ["cost_scenarios_joint_all"]["50.0"]["mean_bps"] == pytest.approx(50.0)
    assert summ["cost_scenarios_joint_all"]["80.0"]["mean_bps"] == pytest.approx(20.0)
    assert summ["routing"]["observation_label"] == "not_estimable"
    assert summ["routing"]["resource_decision"] == "stop_due_to_evidence"


def test_cli_input_identity_path_output_and_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Task 3 negative CLI gates: path/digest/symlink/code-change/output-collision/nonfinite/mutation."""
    _forbid_network(monkeypatch)
    bars = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    specs, up_run, b_adm_n = _write_synthetic_upstream_bundle(tmp_path / "neg", bars)

    out_parent = tmp_path / "evidence_neg"
    out_parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", specs)
    monkeypatch.setattr(cli_mod, "EXPECTED_UPSTREAM_RUN_ROOT", up_run)
    monkeypatch.setattr(cli_mod, "ALLOWED_OUTPUT_PARENT", out_parent)
    monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_adm_n)

    plan_sha = _sha256_file(REPO_ROOT / CUR_PLAN_REL)

    # 1. Wrong approved-plan-sha in prepare -> STOP=source_binding_mismatch
    rc = main(
        [
            "prepare",
            "--approved-plan-sha",
            "0" * 64,
            "--binding-output",
            str(tmp_path / "bad_plan.json"),
            "--output-root",
            str(out_parent / "r1"),
        ]
    )
    assert rc != 0 and "STOP=source_binding_mismatch" in capsys.readouterr().err

    # 2. Valid prepare (proving prepare does NOT parse ledger.jsonl); then existing binding_output rejected
    valid_binding = tmp_path / "valid_binding.json"
    valid_out = out_parent / "r_valid"
    orig_build_cohort = cli_mod.build_cohort

    def _forbid_cohort_in_prepare(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("prepare must NOT parse ledger or construct cohort")

    monkeypatch.setattr(cli_mod, "build_cohort", _forbid_cohort_in_prepare)
    try:
        assert (
            main(
                [
                    "prepare",
                    "--approved-plan-sha",
                    plan_sha,
                    "--binding-output",
                    str(valid_binding),
                    "--output-root",
                    str(valid_out),
                ]
            )
            == 0
        )
    finally:
        monkeypatch.setattr(cli_mod, "build_cohort", orig_build_cohort)
    valid_bsha = _sha256_file(valid_binding)

    rc_dup_b = main(
        [
            "prepare",
            "--approved-plan-sha",
            plan_sha,
            "--binding-output",
            str(valid_binding),
            "--output-root",
            str(out_parent / "r2"),
        ]
    )
    assert rc_dup_b != 0 and "STOP=existing_output_path" in capsys.readouterr().err

    # 3. Output root outside ALLOWED_OUTPUT_PARENT or via symlink -> STOP=output_path_invalid
    rc_outside = main(
        [
            "prepare",
            "--approved-plan-sha",
            plan_sha,
            "--binding-output",
            str(tmp_path / "b_outside.json"),
            "--output-root",
            str(tmp_path / "outside_dir"),
        ]
    )
    assert rc_outside != 0 and "STOP=output_path_invalid" in capsys.readouterr().err

    # 4. Wrong --binding-sha in run -> STOP=source_binding_mismatch
    rc_bad_bsha = main(["run", "--binding", str(valid_binding), "--binding-sha", "f" * 64])
    assert rc_bad_bsha != 0 and "STOP=source_binding_mismatch" in capsys.readouterr().err

    # 5. Simulated code SHA change in binding -> STOP=code_identity_mismatch
    tampered_code_b = json.loads(valid_binding.read_text(encoding="utf-8"))
    tampered_code_b["code_bindings"][0]["sha256"] = "a" * 64
    tc_path = tmp_path / "tampered_code_binding.json"
    tc_path.write_text(json.dumps(tampered_code_b), encoding="utf-8")
    rc_code = main(["run", "--binding", str(tc_path), "--binding-sha", _sha256_file(tc_path)])
    assert rc_code != 0 and "STOP=code_identity_mismatch" in capsys.readouterr().err

    # 6. Identical-byte ledger copy at different root in binding -> STOP=input_path_mismatch
    ext_ledger = tmp_path / "identical_ledger_elsewhere.jsonl"
    ext_ledger.write_bytes(specs["ledger_jsonl"][0].read_bytes())
    wrong_root_b = json.loads(valid_binding.read_text(encoding="utf-8"))
    wrong_root_b["fixed_inputs"]["ledger_jsonl"]["path"] = str(ext_ledger)
    wr_path = tmp_path / "wrong_root_binding.json"
    wr_path.write_text(json.dumps(wrong_root_b), encoding="utf-8")
    rc_wr = main(["run", "--binding", str(wr_path), "--binding-sha", _sha256_file(wr_path)])
    assert rc_wr != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err

    # 7. Symlinked input at expected path pointing outside -> STOP=input_path_mismatch
    orig_cov_path = specs["coverage_json"][0]
    cov_backup = tmp_path / "cov_backup.json"
    cov_backup.write_bytes(orig_cov_path.read_bytes())
    orig_cov_path.unlink()
    orig_cov_path.symlink_to(cov_backup)
    try:
        rc_sym = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        assert rc_sym != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err
    finally:
        orig_cov_path.unlink()
        orig_cov_path.write_bytes(cov_backup.read_bytes())

    # 8. Existing output_root before run -> STOP=existing_output_path
    valid_out.mkdir(parents=True, exist_ok=True)
    rc_ex_out = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
    assert rc_ex_out != 0 and "STOP=existing_output_path" in capsys.readouterr().err
    assert not (valid_out / "EXECUTION_FINISHED").exists()
    valid_out.rmdir()

    # 9. Mid-run input mutation detected before publishing EXECUTION_FINISHED -> STOP=input_mutated_during_run
    orig_summarize = cli_mod.summarize_cohort
    cov_bytes_orig = orig_cov_path.read_bytes()

    def _mutating_summarize(cohort: dict[str, Any], *, protocol: dict[str, Any]) -> dict[str, Any]:
        out = orig_summarize(cohort, protocol=protocol)
        orig_cov_path.write_bytes(cov_bytes_orig + b" ")
        return out

    monkeypatch.setattr(cli_mod, "summarize_cohort", _mutating_summarize)
    try:
        rc_mut = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        assert rc_mut != 0 and "STOP=input_mutated_during_run" in capsys.readouterr().err
        assert not (valid_out / "EXECUTION_FINISHED").exists()
    finally:
        orig_cov_path.write_bytes(cov_bytes_orig)
        monkeypatch.setattr(cli_mod, "summarize_cohort", orig_summarize)

    # 10. git_head and environment mismatches in binding -> STOP=source_binding_mismatch / STOP=code_identity_mismatch
    bad_head_b = json.loads(valid_binding.read_text(encoding="utf-8"))
    bad_head_b["authority"]["git_head"] = "0" * 40
    bh_path = tmp_path / "bad_head_binding.json"
    bh_path.write_text(json.dumps(bad_head_b), encoding="utf-8")
    assert main(["run", "--binding", str(bh_path), "--binding-sha", _sha256_file(bh_path)]) != 0
    assert "STOP=source_binding_mismatch" in capsys.readouterr().err

    bad_env_b = json.loads(valid_binding.read_text(encoding="utf-8"))
    bad_env_b["environment"]["python_executable"] = "/nonexistent/python3"
    be_path = tmp_path / "bad_env_binding.json"
    be_path.write_text(json.dumps(bad_env_b), encoding="utf-8")
    assert main(["run", "--binding", str(be_path), "--binding-sha", _sha256_file(be_path)]) != 0
    assert "STOP=code_identity_mismatch" in capsys.readouterr().err

    # 11. Symlinked parent directory (up_run/results -> outside dir) -> STOP=input_path_mismatch
    results_dir = up_run / "results"
    moved_results = tmp_path / "moved_results_real"
    results_dir.rename(moved_results)
    results_dir.symlink_to(moved_results)
    try:
        rc_pdir_sym = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        assert rc_pdir_sym != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err
    finally:
        results_dir.unlink()
        moved_results.rename(results_dir)

    # 12. Helper to run with a single mutated upstream file (re-preparing binding so digest matches mutated bytes)
    def _run_with_mutated_upstream(
        tag: str,
        file_key: str,
        new_bytes: bytes,
        *,
        b_count_override: int | None = None,
    ) -> tuple[int, str, Path]:
        target_p, orig_sha = specs[file_key]
        orig_b = target_p.read_bytes()
        target_p.write_bytes(new_bytes)
        new_specs = dict(specs)
        new_specs[file_key] = (target_p, _sha256_file(target_p))
        monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", new_specs)
        if b_count_override is not None:
            monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_count_override)
        b_file = tmp_path / f"mut_{tag}_binding.json"
        o_dir = out_parent / f"mut_{tag}_out"
        try:
            assert (
                main(
                    [
                        "prepare",
                        "--approved-plan-sha",
                        plan_sha,
                        "--binding-output",
                        str(b_file),
                        "--output-root",
                        str(o_dir),
                    ]
                )
                == 0
            )
            capsys.readouterr()
            rc_m = main(["run", "--binding", str(b_file), "--binding-sha", _sha256_file(b_file)])
            err_m = capsys.readouterr().err
            return rc_m, err_m, o_dir
        finally:
            target_p.write_bytes(orig_b)
            monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", specs)
            monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_adm_n)
            assert _sha256_file(target_p) == orig_sha

    # 12a. Upstream summary.json manifest_sha256 mismatch -> STOP=upstream_provenance_mismatch
    sum_obj = json.loads(specs["summary_json"][0].read_text(encoding="utf-8"))
    sum_bad_msha = copy.deepcopy(sum_obj)
    sum_bad_msha["manifest_sha256"] = "1" * 64
    rc_um, err_um, out_um = _run_with_mutated_upstream(
        "bad_msha", "summary_json", json.dumps(sum_bad_msha).encode("utf-8")
    )
    assert rc_um != 0 and "STOP=upstream_provenance_mismatch" in err_um and not out_um.exists()

    # 12b. Upstream summary.json protocol mismatch -> STOP=upstream_provenance_mismatch
    sum_bad_proto = copy.deepcopy(sum_obj)
    sum_bad_proto["protocol"]["volume_spike_threshold"] = 2.5
    rc_up, err_up, out_up = _run_with_mutated_upstream(
        "bad_proto", "summary_json", json.dumps(sum_bad_proto).encode("utf-8")
    )
    assert rc_up != 0 and "STOP=upstream_provenance_mismatch" in err_up and not out_up.exists()

    # 12c. B admitted count mismatch vs EXPECTED_B_ADMITTED_COUNT -> STOP=cohort_contract_mismatch
    rc_bc, err_bc, out_bc = _run_with_mutated_upstream(
        "bad_bcount", "ledger_jsonl", specs["ledger_jsonl"][0].read_bytes(), b_count_override=964
    )
    assert rc_bc != 0 and "STOP=cohort_contract_mismatch" in err_bc and not out_bc.exists()

    # 12d. Literal NaN in ledger.jsonl -> STOP=cohort_contract_mismatch
    orig_ledger_lines = specs["ledger_jsonl"][0].read_text(encoding="utf-8").splitlines()
    nan_lines = list(orig_ledger_lines)
    first_obj = json.loads(nan_lines[0])
    first_obj["self_r1h"] = float("nan")
    nan_lines[0] = json.dumps(first_obj, allow_nan=True)
    rc_nan, err_nan, out_nan = _run_with_mutated_upstream(
        "ledger_nan", "ledger_jsonl", ("\n".join(nan_lines) + "\n").encode("utf-8")
    )
    assert rc_nan != 0 and "STOP=cohort_contract_mismatch" in err_nan and not out_nan.exists()

    # 12e. Duplicate row in ledger.jsonl -> STOP=cohort_contract_mismatch
    dup_lines = list(orig_ledger_lines) + [orig_ledger_lines[0]]
    rc_dl, err_dl, out_dl = _run_with_mutated_upstream(
        "ledger_dup", "ledger_jsonl", ("\n".join(dup_lines) + "\n").encode("utf-8")
    )
    assert rc_dl != 0 and "STOP=cohort_contract_mismatch" in err_dl and not out_dl.exists()

    # 12f. Corrupted available_at_ms timestamp in ledger.jsonl -> STOP=cohort_time_mismatch
    bad_t_lines = list(orig_ledger_lines)
    t_obj = json.loads(bad_t_lines[0])
    t_obj["available_at_ms"] = int(t_obj["window_end_ms"]) + 15_000
    bad_t_lines[0] = json.dumps(t_obj)
    rc_bt, err_bt, out_bt = _run_with_mutated_upstream(
        "ledger_time", "ledger_jsonl", ("\n".join(bad_t_lines) + "\n").encode("utf-8")
    )
    assert rc_bt != 0 and "STOP=cohort_time_mismatch" in err_bt and not out_bt.exists()


def test_cli_rejects_ancestor_symlinks_and_post_read_root_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """R1 P1-01 regression: reject ancestor symlinks (manifest grandparent / upstream ancestor) and mid-run root relocation."""
    _forbid_network(monkeypatch)
    bundle_container = tmp_path / "container" / "sub"
    bars = _make_plan_section4_dual_rs_with_volume_bars(include_volume_spike=True)
    specs, up_run, b_adm_n = _write_synthetic_upstream_bundle(bundle_container, bars)

    # Place source_manifest.json under a deeper directory hierarchy: gp_dir/remediation_r4/source_manifest.json
    gp_dir = tmp_path / "manifest_gp"
    manifest_dir = gp_dir / "remediation_r4"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    deep_manifest = manifest_dir / "source_manifest.json"
    deep_manifest.write_bytes(specs["source_manifest_json"][0].read_bytes())
    specs = dict(specs)
    specs["source_manifest_json"] = (deep_manifest, _sha256_file(deep_manifest))

    out_parent = tmp_path / "evidence_r1"
    out_parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(cli_mod, "FIXED_INPUT_SPECS", specs)
    monkeypatch.setattr(cli_mod, "EXPECTED_UPSTREAM_RUN_ROOT", up_run)
    monkeypatch.setattr(cli_mod, "ALLOWED_OUTPUT_PARENT", out_parent)
    monkeypatch.setattr(cli_mod, "EXPECTED_B_ADMITTED_COUNT", b_adm_n)

    plan_sha = _sha256_file(REPO_ROOT / CUR_PLAN_REL)
    valid_binding = tmp_path / "r1_valid_binding.json"
    valid_out = out_parent / "run_r1_01"

    assert (
        main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(valid_binding),
                "--output-root",
                str(valid_out),
            ]
        )
        == 0
    )
    capsys.readouterr()
    valid_bsha = _sha256_file(valid_binding)

    # 1. Grandparent directory of source_manifest.json is a symlink (leaf & immediate parent are real) -> STOP=input_path_mismatch
    moved_gp = tmp_path / "manifest_gp_relocated_real"
    gp_dir.rename(moved_gp)
    gp_dir.symlink_to(moved_gp)
    try:
        assert deep_manifest.is_file() and not deep_manifest.is_symlink()
        assert not deep_manifest.parent.is_symlink()
        assert gp_dir.is_symlink()
        prep_sym_gp = tmp_path / "sym_gp_binding.json"
        rc_pgp = main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(prep_sym_gp),
                "--output-root",
                str(out_parent / "run_pgp"),
            ]
        )
        assert rc_pgp != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err
        assert not prep_sym_gp.exists()

        rc_rgp = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        assert rc_rgp != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err
        assert not valid_out.exists() and not (valid_out / "EXECUTION_FINISHED").exists()
    finally:
        gp_dir.unlink()
        moved_gp.rename(gp_dir)

    # 2. Ancestor directory above upstream_run_root is a symlink (up_run itself is a real dir inside it) -> STOP=input_path_mismatch
    top_container = tmp_path / "container"
    moved_container = tmp_path / "container_relocated_real"
    top_container.rename(moved_container)
    top_container.symlink_to(moved_container)
    try:
        assert up_run.is_dir() and not up_run.is_symlink()
        rc_panc = main(
            [
                "prepare",
                "--approved-plan-sha",
                plan_sha,
                "--binding-output",
                str(tmp_path / "sym_anc_binding.json"),
                "--output-root",
                str(out_parent / "run_panc"),
            ]
        )
        assert rc_panc != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err

        rc_ranc = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        assert rc_ranc != 0 and "STOP=input_path_mismatch" in capsys.readouterr().err
        assert not valid_out.exists() and not (valid_out / "EXECUTION_FINISHED").exists()
    finally:
        top_container.unlink()
        moved_container.rename(top_container)

    # 3. Post-read / pre-publish upstream_run_root relocated and symlinked back (all 4 SHA-256s unchanged!) -> STOP=input_mutated_during_run
    orig_summarize = cli_mod.summarize_cohort
    relocated_up_run = tmp_path / "unapproved_relocated_source"

    def _relocate_up_run_after_read(cohort: dict[str, Any], *, protocol: dict[str, Any]) -> dict[str, Any]:
        out = orig_summarize(cohort, protocol=protocol)
        up_run.rename(relocated_up_run)
        up_run.symlink_to(relocated_up_run)
        return out

    monkeypatch.setattr(cli_mod, "summarize_cohort", _relocate_up_run_after_read)
    try:
        rc_reloc = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        err_reloc = capsys.readouterr().err
        assert up_run.is_symlink()
        for _k, (p, expected_s) in specs.items():
            assert _sha256_file(p) == expected_s
        assert rc_reloc != 0 and "STOP=input_mutated_during_run" in err_reloc
        assert not valid_out.exists() and not (valid_out / "EXECUTION_FINISHED").exists()
    finally:
        if up_run.is_symlink():
            up_run.unlink()
        if relocated_up_run.exists():
            relocated_up_run.rename(up_run)
        monkeypatch.setattr(cli_mod, "summarize_cohort", orig_summarize)

    # 4. Post-read / pre-publish source_manifest grandparent relocated and symlinked back -> STOP=input_mutated_during_run
    relocated_gp_mid = tmp_path / "unapproved_relocated_manifest_gp"

    def _relocate_manifest_gp_after_read(cohort: dict[str, Any], *, protocol: dict[str, Any]) -> dict[str, Any]:
        out = orig_summarize(cohort, protocol=protocol)
        gp_dir.rename(relocated_gp_mid)
        gp_dir.symlink_to(relocated_gp_mid)
        return out

    monkeypatch.setattr(cli_mod, "summarize_cohort", _relocate_manifest_gp_after_read)
    try:
        rc_mgp = main(["run", "--binding", str(valid_binding), "--binding-sha", valid_bsha])
        err_mgp = capsys.readouterr().err
        assert gp_dir.is_symlink()
        assert rc_mgp != 0 and "STOP=input_mutated_during_run" in err_mgp
        assert not valid_out.exists() and not (valid_out / "EXECUTION_FINISHED").exists()
    finally:
        if gp_dir.is_symlink():
            gp_dir.unlink()
        if relocated_gp_mid.exists():
            relocated_gp_mid.rename(gp_dir)
        monkeypatch.setattr(cli_mod, "summarize_cohort", orig_summarize)




