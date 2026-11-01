"""Unit tests for launch_taker_buy_share_residual_response pure calculation logic.

All vectors in this file are synthetic, hand-calculated oracle vectors for internal
pure-logic verification per L1 Rule 15. They do not claim real archive coverage or
upstream provenance compatibility.
"""

from __future__ import annotations

import tracemalloc
from decimal import Decimal
from fractions import Fraction
from typing import Generator

import pytest

from research.external_signal_shadow.launch_taker_buy_share_residual_response import (
    AggTradeRecord,
    ChildResidualResponseResult,
    ExploratoryProtocol,
    TakerBuyShareResearchError,
    evaluate_child_residual_response,
    summarize_regime_residual_response,
)

PROTOCOL = ExploratoryProtocol(
    feature_window_ms=60_000,
    latency_ms=3_000,
    entry_max_wait_ms=1_000,
    hold_horizon_ms=900_000,
    endpoint_max_age_ms=1_000,
)


def test_feature_and_path_hand_calculated() -> None:
    """Verify exact rational feature and path calculations against hand-calculated oracle."""
    trades = [
        # Feature window [0, 60000):
        # Trade 1: p=100, q=2, buyer_maker=False (active buy) -> notional=200
        AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("2"), timestamp_ms=0, is_buyer_maker=False),
        # Trade 2: p=110, q=1, buyer_maker=True (active sell) -> notional=110
        AggTradeRecord(aggregate_id=2, price=Decimal("110"), quantity=Decimal("1"), timestamp_ms=30_000, is_buyer_maker=True),
        # Entry at 63000ms: Pe = 100
        AggTradeRecord(aggregate_id=3, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=63_000, is_buyer_maker=False),
        # Path minimum: 90 -> return = -0.1
        AggTradeRecord(aggregate_id=4, price=Decimal("90"), quantity=Decimal("1"), timestamp_ms=200_000, is_buyer_maker=True),
        # Path maximum: 120 -> return = +0.2
        AggTradeRecord(aggregate_id=5, price=Decimal("120"), quantity=Decimal("1"), timestamp_ms=500_000, is_buyer_maker=False),
        # Endpoint at T_end = 63000 + 900000 = 963000ms: P_end = 110 -> return = +0.1
        AggTradeRecord(aggregate_id=6, price=Decimal("110"), quantity=Decimal("1"), timestamp_ms=963_000, is_buyer_maker=False),
    ]

    res = evaluate_child_residual_response(
        parent_article_id="parent_1",
        symbol="TESTUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=trades,
    )

    assert res.status == "complete"
    assert res.feature_trade_count == 2
    assert res.feature_max_intertrade_gap_ms == 30_000
    assert res.total_notional == Fraction(310, 1)
    assert res.taker_buy_share == Fraction(20, 31)
    assert res.vwap == Fraction(310, 3)
    assert res.vwap_deviation == Fraction(2, 31)
    assert res.entry_time_ms == 63_000
    assert res.entry_price == Fraction(100, 1)
    assert res.target_end_time_ms == 963_000
    assert res.endpoint_time_ms == 963_000
    assert res.endpoint_price == Fraction(110, 1)
    assert res.max_intertrade_gap_ms == 463_000
    assert res.terminal_return == Fraction(1, 10)
    assert res.long_mae == Fraction(-1, 10)
    assert res.long_mfe == Fraction(1, 5)


def test_time_order_and_endpoint_boundaries() -> None:
    """Verify [T0, T0+60000), entry [63000, 64000], T_end=entry+900000, endpoint [T_end-1000, T_end], and same-ms ID order."""
    # Case A: trade at 60000ms excluded from feature window; same-ms before entry excluded from path;
    # entry at 64000ms accepted -> T_end = 964000ms; endpoint accepts 963000ms and 964000ms, excludes 964001ms.
    trades = [
        AggTradeRecord(aggregate_id=10, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
        # Exactly at 60000ms: must NOT be included in feature window
        AggTradeRecord(aggregate_id=11, price=Decimal("500"), quantity=Decimal("10"), timestamp_ms=60_000, is_buyer_maker=True),
        # Before entry at 62999ms: must NOT be included in path
        AggTradeRecord(aggregate_id=12, price=Decimal("50"), quantity=Decimal("1"), timestamp_ms=62_999, is_buyer_maker=True),
        # First trade in [63000, 64000] is at 64000ms (id=13); second trade at same ms (id=14) IS in path
        AggTradeRecord(aggregate_id=13, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=64_000, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=14, price=Decimal("105"), quantity=Decimal("1"), timestamp_ms=64_000, is_buyer_maker=False),
        # Endpoint window is [963000, 964000]: 963000 and 964000 included, 964001 excluded
        AggTradeRecord(aggregate_id=15, price=Decimal("102"), quantity=Decimal("1"), timestamp_ms=963_000, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=16, price=Decimal("108"), quantity=Decimal("1"), timestamp_ms=964_000, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=17, price=Decimal("999"), quantity=Decimal("1"), timestamp_ms=964_001, is_buyer_maker=False),
    ]

    res = evaluate_child_residual_response(
        parent_article_id="parent_1",
        symbol="BOUNDUSDT",
        listing_regime="pre_market",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=trades,
    )

    assert res.status == "complete"
    assert res.feature_trade_count == 1
    assert res.taker_buy_share == Fraction(1, 1)
    assert res.entry_trade_id == 13
    assert res.entry_time_ms == 64_000
    assert res.target_end_time_ms == 964_000
    assert res.endpoint_trade_id == 16
    assert res.endpoint_time_ms == 964_000
    assert res.terminal_return == Fraction(8, 100)
    assert res.long_mfe == Fraction(8, 100)
    assert res.long_mae == Fraction(0, 1)

    # Verify entry at 63000ms when multiple trades share 63000ms: first is entry, earlier pre-63000 excluded
    trades_same_ms = [
        AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=2, price=Decimal("80"), quantity=Decimal("1"), timestamp_ms=63_000, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=3, price=Decimal("120"), quantity=Decimal("1"), timestamp_ms=63_000, is_buyer_maker=False),
        AggTradeRecord(aggregate_id=4, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=963_000, is_buyer_maker=False),
    ]
    res_same = evaluate_child_residual_response(
        parent_article_id="parent_1",
        symbol="SAMEMSUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=trades_same_ms,
    )
    assert res_same.status == "complete"
    assert res_same.entry_trade_id == 2
    assert res_same.entry_price == Fraction(80, 1)
    assert res_same.long_mfe == Fraction(1, 2)  # 120 / 80 - 1 = 0.5
    assert res_same.terminal_return == Fraction(1, 4)  # 100 / 80 - 1 = 0.25


def test_unavailable_and_gap_states() -> None:
    """Verify missing feature/entry/endpoint, sequence gap, cross-midnight missing package, and contract errors."""
    # 1. upstream_gap
    res_up = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="UPGAPUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=None,
        anchor_price=None,
        trades=[],
        upstream_gap_reason="j_a_archive_gap",
    )
    assert res_up.status == "upstream_gap"
    assert res_up.taker_buy_share is None
    assert res_up.terminal_return is None

    # 2. anchor_unavailable
    res_anc = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="NOANCUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=None,
        anchor_price=None,
        trades=[],
        anchor_unavailable_reason="anchor_delay_exceeded",
    )
    assert res_anc.status == "anchor_unavailable"
    assert res_anc.taker_buy_share is None

    # 3. feature_unavailable (empty feature window)
    res_feat = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="NOFEATUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[],
    )
    assert res_feat.status == "feature_unavailable"
    assert res_feat.taker_buy_share is None

    # 4. entry_unavailable (only trade at 64001ms, outside [63000, 64000])
    res_no_entry = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="NOENTRYUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=64_001, is_buyer_maker=False),
        ],
    )
    assert res_no_entry.status == "entry_unavailable"
    assert res_no_entry.taker_buy_share == Fraction(1, 1)
    assert res_no_entry.terminal_return is None

    # 5. endpoint_unavailable (last trade at T_end - 1001ms)
    res_no_end = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="NOENDUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=63_000, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=3, price=Decimal("105"), quantity=Decimal("1"), timestamp_ms=961_999, is_buyer_maker=False),
        ],
    )
    assert res_no_end.status == "endpoint_unavailable"
    assert res_no_end.terminal_return is None

    # 6. sequence_gap (aggregate_id jumps from 2 to 4)
    res_seq_gap = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="SEQGAPUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=0,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=63_000, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=4, price=Decimal("110"), quantity=Decimal("1"), timestamp_ms=963_000, is_buyer_maker=False),
        ],
    )
    assert res_seq_gap.status == "sequence_gap"
    assert res_seq_gap.terminal_return is None

    # 7. required_package_unavailable across UTC midnight
    # Case 7a: entry found on day 1, T_end crosses into missing day 2
    t0_midnight = 1_767_311_400_000  # 2026-01-01 23:50:00 UTC
    res_pkg_gap = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="MIDNIGHTUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=t0_midnight,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=t0_midnight, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=t0_midnight + 63_000, is_buyer_maker=False),
        ],
        available_utc_dates={"2026-01-01"},
    )
    assert res_pkg_gap.status == "required_package_unavailable"
    assert res_pkg_gap.taker_buy_share == Fraction(1, 1)
    assert res_pkg_gap.terminal_return is None

    # Case 7b (P1-01): entry window itself crosses UTC midnight (T0 = 23:58:58 UTC -> entry window [00:00:01, 00:00:02] on 2026-01-02).
    # When 2026-01-02 package is missing -> must be required_package_unavailable, NOT entry_unavailable!
    t0_cross_entry = 1_767_311_938_000  # 2026-01-01 23:58:58 UTC
    res_cross_entry_missing_pkg = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="CROSSENTRYMISSINGUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=t0_cross_entry,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("2"), timestamp_ms=t0_cross_entry, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("2"), timestamp_ms=t0_cross_entry + 15_000, is_buyer_maker=True),
        ],
        available_utc_dates={"2026-01-01"},
    )
    assert res_cross_entry_missing_pkg.status == "required_package_unavailable"
    assert res_cross_entry_missing_pkg.taker_buy_share == Fraction(1, 2)
    assert res_cross_entry_missing_pkg.feature_max_intertrade_gap_ms == 15_000
    assert res_cross_entry_missing_pkg.terminal_return is None

    # Case 7c (P1-01 counterpart): when 2026-01-02 package IS available, and has no trade in [00:00:01, 00:00:02] -> entry_unavailable
    res_cross_entry_present_no_trade = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="CROSSENTRYNOTRADEUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=t0_cross_entry,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("2"), timestamp_ms=t0_cross_entry, is_buyer_maker=False),
            AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("2"), timestamp_ms=t0_cross_entry + 15_000, is_buyer_maker=True),
            AggTradeRecord(aggregate_id=3, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=t0_cross_entry + 70_000, is_buyer_maker=False),
        ],
        available_utc_dates={"2026-01-01", "2026-01-02"},
    )
    assert res_cross_entry_present_no_trade.status == "entry_unavailable"
    assert res_cross_entry_present_no_trade.taker_buy_share == Fraction(1, 2)
    assert res_cross_entry_present_no_trade.terminal_return is None

    # Case 7d: feature window itself crosses UTC midnight (T0 = 23:59:30 UTC) and next-day package is missing -> required_package_unavailable with feature=None
    t0_cross_feat = 1_767_311_970_000  # 2026-01-01 23:59:30 UTC
    res_cross_feat_missing_pkg = evaluate_child_residual_response(
        parent_article_id="p1",
        symbol="CROSSFEATMISSINGUSDT",
        listing_regime="standard",
        protocol=PROTOCOL,
        anchor_time_ms=t0_cross_feat,
        anchor_price=Decimal("100"),
        trades=[
            AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=t0_cross_feat, is_buyer_maker=False),
        ],
        available_utc_dates={"2026-01-01"},
    )
    assert res_cross_feat_missing_pkg.status == "required_package_unavailable"
    assert res_cross_feat_missing_pkg.taker_buy_share is None

    # 8. Integrity errors (non-positive price, timestamp regression, protocol mismatch) must raise
    with pytest.raises(TakerBuyShareResearchError):
        evaluate_child_residual_response(
            parent_article_id="p1",
            symbol="BADPRICEUSDT",
            listing_regime="standard",
            protocol=PROTOCOL,
            anchor_time_ms=0,
            anchor_price=Decimal("100"),
            trades=[
                AggTradeRecord(aggregate_id=1, price=Decimal("0"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False),
            ],
        )

    with pytest.raises(TakerBuyShareResearchError):
        evaluate_child_residual_response(
            parent_article_id="p1",
            symbol="BADORDERUSDT",
            listing_regime="standard",
            protocol=PROTOCOL,
            anchor_time_ms=0,
            anchor_price=Decimal("100"),
            trades=[
                AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=10, is_buyer_maker=False),
                AggTradeRecord(aggregate_id=2, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=5, is_buyer_maker=False),
            ],
        )

    with pytest.raises(TakerBuyShareResearchError):
        bad_proto = ExploratoryProtocol(
            feature_window_ms=30_000,
            latency_ms=3_000,
            entry_max_wait_ms=1_000,
            hold_horizon_ms=900_000,
            endpoint_max_age_ms=1_000,
        )
        evaluate_child_residual_response(
            parent_article_id="p1",
            symbol="BADPROTOUSDT",
            listing_regime="standard",
            protocol=bad_proto,
            anchor_time_ms=0,
            anchor_price=Decimal("100"),
            trades=[],
        )


def _make_complete_child(
    *,
    parent_id: str,
    symbol: str,
    regime: str,
    taker_buy_share: Fraction,
    terminal_return: Fraction,
    long_mae: Fraction = Fraction(-1, 20),
    long_mfe: Fraction = Fraction(1, 10),
) -> ChildResidualResponseResult:
    return ChildResidualResponseResult(
        parent_article_id=parent_id,
        symbol=symbol,
        listing_regime=regime,
        status="complete",
        status_reason=None,
        anchor_time_ms=0,
        anchor_price=Fraction(100, 1),
        feature_trade_count=2,
        feature_max_intertrade_gap_ms=10_000,
        total_notional=Fraction(100, 1),
        taker_buy_share=taker_buy_share,
        vwap=Fraction(100, 1),
        vwap_deviation=Fraction(0, 1),
        entry_time_ms=63_000,
        entry_trade_id=2,
        entry_price=Fraction(100, 1),
        target_end_time_ms=963_000,
        endpoint_time_ms=963_000,
        endpoint_trade_id=3,
        endpoint_price=Fraction(100, 1) * (1 + terminal_return),
        path_trade_count=2,
        max_intertrade_gap_ms=900_000,
        terminal_return=terminal_return,
        long_mae=long_mae,
        long_mfe=long_mfe,
    )


def _make_gap_child(
    *,
    parent_id: str,
    symbol: str,
    regime: str,
    status: str = "entry_unavailable",
    taker_buy_share: Fraction | None = Fraction(1, 2),
) -> ChildResidualResponseResult:
    return ChildResidualResponseResult(
        parent_article_id=parent_id,
        symbol=symbol,
        listing_regime=regime,
        status=status,
        status_reason="gap_for_test",
        anchor_time_ms=0,
        anchor_price=Fraction(100, 1),
        feature_trade_count=1 if taker_buy_share is not None else 0,
        feature_max_intertrade_gap_ms=0 if taker_buy_share is not None else None,
        total_notional=Fraction(100, 1) if taker_buy_share is not None else None,
        taker_buy_share=taker_buy_share,
        vwap=Fraction(100, 1) if taker_buy_share is not None else None,
        vwap_deviation=Fraction(0, 1) if taker_buy_share is not None else None,
        entry_time_ms=None,
        entry_trade_id=None,
        entry_price=None,
        target_end_time_ms=None,
        endpoint_time_ms=None,
        endpoint_trade_id=None,
        endpoint_price=None,
        path_trade_count=0,
        max_intertrade_gap_ms=None,
        terminal_return=None,
        long_mae=None,
        long_mfe=None,
    )


def test_group_parent_and_ties() -> None:
    """Verify child/parent median grouping, ties assigned to low, incomplete parent exclusion, and P25/P75 nearest-rank."""
    # P1: 2 complete children -> parent median share = (1/4 + 2/4)/2 = 3/8, return = (1/10 + 3/10)/2 = 2/10
    # P2: 1 complete child + 1 gap child -> parent is incomplete (gap), stays in denominator, excluded from complete parents
    # P3: 1 complete child with share = 2/4 (ties with C2), return = 4/10
    # P4: 1 complete child with share = 3/4, return = 6/10
    children = [
        _make_complete_child(parent_id="P1", symbol="C1USDT", regime="standard", taker_buy_share=Fraction(1, 4), terminal_return=Fraction(1, 10)),
        _make_complete_child(parent_id="P1", symbol="C2USDT", regime="standard", taker_buy_share=Fraction(2, 4), terminal_return=Fraction(3, 10)),
        _make_complete_child(parent_id="P2", symbol="C3USDT", regime="standard", taker_buy_share=Fraction(2, 4), terminal_return=Fraction(5, 10)),
        _make_gap_child(parent_id="P2", symbol="C4USDT", regime="standard", status="entry_unavailable", taker_buy_share=Fraction(9, 10)),
        _make_complete_child(parent_id="P3", symbol="C5USDT", regime="standard", taker_buy_share=Fraction(2, 4), terminal_return=Fraction(4, 10)),
        _make_complete_child(parent_id="P4", symbol="C6USDT", regime="standard", taker_buy_share=Fraction(3, 4), terminal_return=Fraction(6, 10)),
    ]

    summary = summarize_regime_residual_response(listing_regime="standard", child_results=children)

    # Universe conservation
    assert summary.n_universe_children == 6
    assert summary.n_universe_parents == 4
    assert summary.n_complete_children == 5
    assert summary.n_complete_parents == 3  # P1, P3, P4 complete; P2 has 1 gap child

    # Complete child shares: [1/4, 2/4, 2/4, 2/4, 3/4] -> median = 2/4 = 1/2
    # Ties with median (2/4) must all go to low: low has 4 children (C1, C2, C3, C5), high has 1 child (C6)
    assert summary.child_median_threshold == Fraction(1, 2)
    assert summary.child_low_group.n_items == 4
    assert summary.child_high_group.n_items == 1
    # Low returns sorted: [1/10, 3/10, 4/10, 5/10]
    # n=4: mean = 13/40, even median = (3/10 + 4/10)/2 = 7/20, P25 (ceil(0.25*4)=1st) = 1/10, P75 (ceil(0.75*4)=3rd) = 4/10
    assert summary.child_low_group.terminal_return.mean == Fraction(13, 40)
    assert summary.child_low_group.terminal_return.median == Fraction(7, 20)
    assert summary.child_low_group.terminal_return.p25 == Fraction(1, 10)
    assert summary.child_low_group.terminal_return.p75 == Fraction(4, 10)
    assert summary.child_high_group.terminal_return.mean == Fraction(6, 10)

    # Parent level: P1 (share=3/8, ret=2/10), P3 (share=1/2, ret=4/10), P4 (share=3/4, ret=6/10)
    # Parent median threshold = 1/2 -> low: P1, P3 (mean=(2/10+4/10)/2=3/10), high: P4 (mean=6/10)
    assert summary.parent_median_threshold == Fraction(1, 2)
    assert summary.parent_low_group.n_items == 2
    assert summary.parent_high_group.n_items == 1
    assert summary.parent_high_minus_low_terminal_mean == Fraction(3, 10)


def test_leave_one_parent_out_recalculates_and_null() -> None:
    """Verify leave-one-parent-out recalculates median threshold and handles empty high group as null."""
    # Oracle vector from Plan Task 2:
    # Three complete Parents with features 1/4, 1/2, 3/4 and terminal_return 0.1, 0.2, 0.4
    children = [
        _make_complete_child(parent_id="PA", symbol="AUSDT", regime="standard", taker_buy_share=Fraction(1, 4), terminal_return=Fraction(1, 10)),
        _make_complete_child(parent_id="PB", symbol="BUSDT", regime="standard", taker_buy_share=Fraction(1, 2), terminal_return=Fraction(2, 10)),
        _make_complete_child(parent_id="PC", symbol="CUSDT", regime="standard", taker_buy_share=Fraction(3, 4), terminal_return=Fraction(4, 10)),
    ]

    summary = summarize_regime_residual_response(listing_regime="standard", child_results=children)
    # Full sample: median = 1/2; low = {PA, PB} (mean = 0.15 = 3/20); high = {PC} (mean = 0.4 = 8/20); diff = 0.25 = 1/4
    assert summary.parent_median_threshold == Fraction(1, 2)
    assert summary.parent_high_minus_low_terminal_mean == Fraction(1, 4)

    loo = summary.parent_leave_one_out
    assert loo.n_total_iterations == 3
    assert loo.n_non_null_iterations == 3
    by_parent = {r.excluded_parent_id: r for r in loo.rows}

    # Excluding PC (the last parent): remaining PA (1/4, 0.1) and PB (1/2, 0.2)
    # New median = (1/4 + 1/2)/2 = 3/8; low={PA} (0.1), high={PB} (0.2) -> diff = 0.1 = 1/10
    row_pc = by_parent["PC"]
    assert row_pc.n_remaining == 2
    assert row_pc.n_high == 1
    assert row_pc.n_low == 1
    assert row_pc.recalculated_median == Fraction(3, 8)
    assert row_pc.high_minus_low_terminal_mean == Fraction(1, 10)

    # Excluding PA: remaining PB (1/2, 0.2) and PC (3/4, 0.4) -> new median = 5/8 -> diff = 0.2 = 1/5
    row_pa = by_parent["PA"]
    assert row_pa.recalculated_median == Fraction(5, 8)
    assert row_pa.high_minus_low_terminal_mean == Fraction(1, 5)

    # Excluding PB: remaining PA (1/4, 0.1) and PC (3/4, 0.4) -> new median = 1/2 -> diff = 0.3 = 3/10
    row_pb = by_parent["PB"]
    assert row_pb.recalculated_median == Fraction(1, 2)
    assert row_pb.high_minus_low_terminal_mean == Fraction(3, 10)

    assert loo.min_terminal_mean_diff == Fraction(1, 10)
    assert loo.max_terminal_mean_diff == Fraction(3, 10)

    # Now test when removing a parent leaves identical features so high group is empty -> diff is None (null)
    children_tie = [
        _make_complete_child(parent_id="PA", symbol="AUSDT", regime="pre_market", taker_buy_share=Fraction(1, 4), terminal_return=Fraction(1, 10)),
        _make_complete_child(parent_id="PB", symbol="BUSDT", regime="pre_market", taker_buy_share=Fraction(1, 4), terminal_return=Fraction(2, 10)),
        _make_complete_child(parent_id="PC", symbol="CUSDT", regime="pre_market", taker_buy_share=Fraction(3, 4), terminal_return=Fraction(4, 10)),
    ]
    summary_tie = summarize_regime_residual_response(listing_regime="pre_market", child_results=children_tie)
    by_parent_tie = {r.excluded_parent_id: r for r in summary_tie.parent_leave_one_out.rows}
    # Excluding PC leaves PA (1/4) and PB (1/4) -> median = 1/4 -> both <= median -> n_high = 0, n_low = 2 -> diff is None
    assert by_parent_tie["PC"].n_high == 0
    assert by_parent_tie["PC"].n_low == 2
    assert by_parent_tie["PC"].high_minus_low_terminal_mean is None
    assert by_parent_tie["PC"].status == "evidence_insufficient"

    # P1-02 negative assertions: LeaveOneParentOutRow and RegimeExploratorySummary must NOT expose
    # unapproved MAE/MFE leave-one-out differences or child_leave_one_out
    assert not hasattr(row_pc, "high_minus_low_mae_mean")
    assert not hasattr(row_pc, "high_minus_low_mfe_mean")
    assert not hasattr(summary, "child_leave_one_out")


def test_streaming_memory_bounded() -> None:
    """Verify evaluate_child_residual_response streams in O(1) memory without accumulating trade lists (P1-03)."""
    n_trades = 50_000

    def _huge_trade_stream() -> Generator[AggTradeRecord, None, None]:
        # Trade 1 at t=0: price=100, qty=1, buy
        yield AggTradeRecord(aggregate_id=1, price=Decimal("100"), quantity=Decimal("1"), timestamp_ms=0, is_buyer_maker=False)
        # 20,000 trades in feature window [1, 59999]
        for i in range(2, 20_002):
            # Keep timestamp monotonic: step slowly
            ts_mono = min(59_999, (i - 1) * 2)
            yield AggTradeRecord(
                aggregate_id=i,
                price=Decimal("100"),
                quantity=Decimal("1"),
                timestamp_ms=ts_mono,
                is_buyer_maker=(i % 2 == 0),
            )
        # Entry at 63000ms: id=20002, price=100
        yield AggTradeRecord(
            aggregate_id=20_002,
            price=Decimal("100"),
            quantity=Decimal("1"),
            timestamp_ms=63_000,
            is_buyer_maker=False,
        )
        # 29,997 path trades in (63000, 962999]
        for i in range(20_003, n_trades):
            ts_mono = 63_000 + (i - 20_002) * 20
            p = Decimal("90") if i == 25_000 else (Decimal("125") if i == 35_000 else Decimal("105"))
            yield AggTradeRecord(
                aggregate_id=i,
                price=p,
                quantity=Decimal("1"),
                timestamp_ms=ts_mono,
                is_buyer_maker=False,
            )
        # Endpoint at 963000ms: id=50000, price=110
        yield AggTradeRecord(
            aggregate_id=n_trades,
            price=Decimal("110"),
            quantity=Decimal("1"),
            timestamp_ms=963_000,
            is_buyer_maker=False,
        )

    tracemalloc.start()
    try:
        res = evaluate_child_residual_response(
            parent_article_id="p_stream",
            symbol="STREAMUSDT",
            listing_regime="standard",
            protocol=PROTOCOL,
            anchor_time_ms=0,
            anchor_price=Decimal("100"),
            trades=_huge_trade_stream(),
        )
        _current, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert res.status == "complete"
    assert res.feature_trade_count == 20_001
    assert res.path_trade_count == 29_999
    assert res.terminal_return == Fraction(1, 10)
    assert res.long_mae == Fraction(-1, 10)
    assert res.long_mfe == Fraction(1, 4)
    # 50,000 trades materialized in lists would allocate > 15,000,000 bytes; streaming O(1) stays < 256 KiB
    assert peak_bytes < 256_000, f"Peak memory {peak_bytes} bytes exceeded O(1) streaming bound"


