from scripts.build_extreme_funding_basis_replay_dataset import (
    build_dataset_summary,
    parse_price_payload,
)
from src.research.extreme_funding_basis_replay import build_historical_basis_row


def test_parse_price_payload_turns_klines_into_close_time_price_map() -> None:
    payload = [[0, "1", "2", "0.5", "1.5", "10", 999]]
    prices, row_error_count = parse_price_payload(payload)
    assert prices == {999: 1.5}
    assert row_error_count == 0


def test_parse_price_payload_reports_row_errors() -> None:
    prices, row_error_count = parse_price_payload([[0, "bad"]])
    assert prices == {}
    assert row_error_count == 1


def test_build_dataset_summary_marks_empty_input() -> None:
    summary = build_dataset_summary([], stats={"selected_funding_row_count": 0})
    assert summary["status"] == "no_threshold_rows_or_no_input"
    assert summary["basis_row_count"] == 0
    assert summary["coverage_quality"] == "insufficient_basis_data"
    assert summary["selected_funding_row_count"] == 0
    assert summary["has_basis_rows"] is False


def test_build_dataset_summary_marks_basis_proxy_rows() -> None:
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
    summary = build_dataset_summary(
        rows,
        stats={
            "selected_funding_row_count": 1,
            "request_count": 2,
            "fetch_error_count": 0,
            "spot_empty_count": 0,
            "futures_empty_count": 0,
            "alignment_miss_count": 0,
            "parse_error_count": 0,
            "row_error_count": 0,
            "symbols": ["DOGE/USDT"],
        },
    )
    assert summary["status"] == "ok"
    assert summary["basis_row_count"] == 1
    assert summary["coverage_quality"] == "historical_basis_proxy_not_depth_aware"
    assert summary["depth_aware"] is False
    assert summary["depth_source"] == "static_min_capacity_proxy"
    assert summary["max_price_time_diff_ms"] == 0
