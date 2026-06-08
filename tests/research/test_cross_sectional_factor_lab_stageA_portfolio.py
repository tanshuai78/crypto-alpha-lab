from __future__ import annotations

import pandas as pd

from research.cross_sectional_factor_lab.portfolio import (
    build_equal_weight_targets,
    eligible_monday_rebalance_dates,
)


def test_first_rebalance_after_momentum_and_liquidity_warmup() -> None:
    dates = pd.date_range("2026-01-01", "2026-02-28", freq="D")

    rebalances = eligible_monday_rebalance_dates(dates)

    assert rebalances[0] >= pd.Timestamp("2026-02-02")
    assert all(dt.weekday() == 0 for dt in rebalances)


def test_no_positions_before_warmup_complete() -> None:
    dates = pd.date_range("2026-01-01", "2026-01-20", freq="D")

    assert eligible_monday_rebalance_dates(dates) == []


def test_build_equal_weight_targets_selects_top10_primary() -> None:
    frame = pd.DataFrame(
        {
            "symbol": [f"ALT{i:02d}USDT" for i in range(12)],
            "momentum_30d_skip_1d": list(range(12)),
        }
    )

    targets = build_equal_weight_targets(frame, top_n=10)

    assert len(targets) == 10
    assert targets["target_weight"].sum() == 1.0
    assert "ALT11USDT" in set(targets["symbol"])
    assert "ALT02USDT" in set(targets["symbol"])
    assert "ALT00USDT" not in set(targets["symbol"])


def test_build_equal_weight_targets_marks_insufficient_universe() -> None:
    frame = pd.DataFrame({"symbol": ["AAAUSDT"], "momentum_30d_skip_1d": [0.1]})

    targets = build_equal_weight_targets(frame, top_n=10)

    assert targets.empty
