import json

from scripts.replay_extreme_funding_basis_aware_candidates import (
    build_basis_aware_candidate_summary,
    load_basis_rows_jsonl,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_basis_aware_candidate_summary_accepts_low_absorption_row() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=100.10,
            selected_price_time_ms=1000,
        )
    ]

    summary = build_basis_aware_candidate_summary(rows)

    assert summary["input_row_count"] == 1
    assert summary["candidate_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert summary["depth_aware"] is False
    assert summary["depth_source"] == "static_min_capacity_proxy"
    assert summary["reject_reason_counts"] == {}


def test_basis_aware_candidate_summary_rejects_absorbed_basis() -> None:
    rows = [
        build_historical_basis_row(
            symbol="DOGE/USDT",
            funding_time_ms=1000,
            funding_rate=0.008,
            annualized_pct=650.0,
            spot_mid_price=100.0,
            perp_mid_price=105.0,
            selected_price_time_ms=1000,
        )
    ]

    summary = build_basis_aware_candidate_summary(rows)

    assert summary["candidate_count"] == 0
    assert summary["reject_reason_counts"]["basis_absorbed"] == 1


def test_load_basis_rows_jsonl_round_trips_row(tmp_path) -> None:
    row = build_historical_basis_row(
        symbol="DOGE/USDT",
        funding_time_ms=1000,
        funding_rate=0.008,
        annualized_pct=650.0,
        spot_mid_price=100.0,
        perp_mid_price=100.10,
        selected_price_time_ms=1000,
    )
    path = tmp_path / "basis_rows.jsonl"
    path.write_text(json.dumps(row.__dict__, sort_keys=True) + "\n", encoding="utf-8")

    loaded = load_basis_rows_jsonl(path)

    assert loaded[0].basis_bps == row.basis_bps
