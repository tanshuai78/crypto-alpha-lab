import json

from src.research.extreme_funding_replay import (
    detect_extreme_funding_segments,
    load_settled_funding_rows,
)


def test_load_settled_funding_rows_from_jsonl(tmp_path) -> None:
    path = tmp_path / "funding.jsonl"
    path.write_text(
        json.dumps(
            {
                "symbol": "DOGE/USDT",
                "funding_time_ms": 1000,
                "funding_rate": 0.001,
                "mark_price": 0.2,
                "annualized_pct": 109.5,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows = load_settled_funding_rows(path)
    assert len(rows) == 1
    assert rows[0].symbol == "DOGE/USDT"
    assert rows[0].coverage_quality == "funding_only_insufficient_for_basis"


def test_detect_extreme_funding_segments_groups_consecutive_rows() -> None:
    rows = [
        {"symbol": "DOGE/USDT", "funding_time_ms": 1, "funding_rate": 0.001, "annualized_pct": 109.5},
        {"symbol": "DOGE/USDT", "funding_time_ms": 2, "funding_rate": 0.0011, "annualized_pct": 120.4},
        {"symbol": "DOGE/USDT", "funding_time_ms": 3, "funding_rate": 0.0001, "annualized_pct": 10.9},
        {"symbol": "DOGE/USDT", "funding_time_ms": 4, "funding_rate": 0.0012, "annualized_pct": 131.4},
    ]
    segments = detect_extreme_funding_segments(rows, threshold_pct=100.0)
    assert len(segments) == 2
    assert segments[0]["row_count"] == 2
    assert segments[0]["coverage_quality"] == "funding_only_insufficient_for_basis"
