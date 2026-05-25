from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlencode

from configs.base import (
    EXTREME_FUNDING_BASIS_REPLAY_INTERVAL,
    EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER,
    EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
    RISK_MAX_SINGLE_POSITION_USDT,
)


@dataclass(frozen=True)
class HistoricalBasisRow:
    symbol: str
    funding_time_ms: int
    funding_rate: float
    annualized_pct: float
    spot_mid_price: float
    perp_mid_price: float
    spot_price_time_ms: int
    perp_price_time_ms: int
    selected_price_time_ms: int
    price_time_diff_ms: int
    basis_bps: float
    basis_source: str
    depth_capacity_usdt: float
    depth_source: str
    coverage_quality: str

    def to_candidate_row(self) -> dict:
        row = asdict(self)
        row.update(
            {
                "timestamp_ms": self.funding_time_ms,
                "source_type": "historical_settled",
                "exchange": "binance",
                "direction": "neutral",
                "watch_level": "historical_settled_extreme",
                "annualized_funding_estimate_pct": self.annualized_pct,
                "funding_rate_per_interval": self.funding_rate,
                "expected_holding_intervals": EXTREME_FUNDING_EXPECTED_HOLDING_INTERVALS,
                "settlement_persistence": 1.0,
                "planned_notional_usdt": RISK_MAX_SINGLE_POSITION_USDT,
            }
        )
        return row


def basis_bps_from_prices(*, spot_mid_price: float, perp_mid_price: float) -> float:
    if spot_mid_price <= 0.0:
        raise ValueError("spot_mid_price must be positive")
    return round((perp_mid_price / spot_mid_price - 1.0) * 10_000.0, 10)


def build_historical_basis_row(
    *,
    symbol: str,
    funding_time_ms: int,
    funding_rate: float,
    annualized_pct: float,
    spot_mid_price: float,
    perp_mid_price: float,
    selected_price_time_ms: int | None = None,
    spot_price_time_ms: int | None = None,
    perp_price_time_ms: int | None = None,
) -> HistoricalBasisRow:
    spot_time = funding_time_ms if spot_price_time_ms is None else spot_price_time_ms
    perp_time = funding_time_ms if perp_price_time_ms is None else perp_price_time_ms
    selected_time = (
        max(spot_time, perp_time) if selected_price_time_ms is None else selected_price_time_ms
    )
    return HistoricalBasisRow(
        symbol=symbol,
        funding_time_ms=funding_time_ms,
        funding_rate=funding_rate,
        annualized_pct=annualized_pct,
        spot_mid_price=spot_mid_price,
        perp_mid_price=perp_mid_price,
        spot_price_time_ms=spot_time,
        perp_price_time_ms=perp_time,
        selected_price_time_ms=selected_time,
        price_time_diff_ms=abs(spot_time - perp_time),
        basis_bps=basis_bps_from_prices(
            spot_mid_price=spot_mid_price,
            perp_mid_price=perp_mid_price,
        ),
        basis_source="spot_close_vs_futures_mark_close",
        depth_capacity_usdt=(
            RISK_MAX_SINGLE_POSITION_USDT
            * EXTREME_FUNDING_BASIS_REPLAY_STATIC_DEPTH_MULTIPLIER
        ),
        depth_source="static_min_capacity_proxy",
        coverage_quality="historical_basis_proxy_not_depth_aware",
    )


def binance_symbol_from_pair(pair: str) -> str:
    return pair.replace("/", "")


def build_binance_basis_kline_urls(
    *,
    binance_symbol: str,
    start_time_ms: int,
    end_time_ms: int,
) -> dict[str, str]:
    params = {
        "symbol": binance_symbol,
        "interval": EXTREME_FUNDING_BASIS_REPLAY_INTERVAL,
        "startTime": str(start_time_ms),
        "endTime": str(end_time_ms),
        "limit": "1000",
    }
    query = urlencode(params)
    return {
        "spot": f"https://api.binance.com/api/v3/klines?{query}",
        "futures_mark": f"https://fapi.binance.com/fapi/v1/markPriceKlines?{query}",
    }


def parse_kline_close(kline: list) -> tuple[int, float]:
    return int(kline[6]), float(kline[4])


def select_basis_replay_funding_rows(
    funding_rows: list[dict[str, Any]],
    *,
    threshold_pct: float,
    max_following_intervals: int,
) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in funding_rows:
        by_symbol[str(row["symbol"])].append(row)

    selected: list[dict[str, Any]] = []
    for symbol_rows in by_symbol.values():
        selected_indexes: set[int] = set()
        sorted_rows = sorted(symbol_rows, key=lambda row: int(row["funding_time_ms"]))
        for index, row in enumerate(sorted_rows):
            if float(row.get("annualized_pct", 0.0)) < threshold_pct:
                continue
            for offset in range(max_following_intervals + 1):
                path_index = index + offset
                if path_index < len(sorted_rows):
                    selected_indexes.add(path_index)
        selected.extend(sorted_rows[index] for index in sorted(selected_indexes))
    return sorted(selected, key=lambda row: (str(row["symbol"]), int(row["funding_time_ms"])))


def _latest_price_at_or_before(
    prices: dict[int, float],
    *,
    target_time_ms: int,
    tolerance_ms: int,
) -> tuple[int, float] | None:
    if not prices:
        return None
    candidates = [timestamp for timestamp in prices if timestamp <= target_time_ms]
    if not candidates:
        return None
    selected_time = max(candidates)
    if target_time_ms - selected_time > tolerance_ms:
        return None
    return selected_time, prices[selected_time]


def join_funding_rows_with_basis_prices(
    funding_rows: list[dict[str, Any]],
    *,
    spot_prices: dict[int, float],
    perp_prices: dict[int, float],
    tolerance_ms: int,
) -> dict[str, Any]:
    rows: list[HistoricalBasisRow] = []
    missing_basis_count = 0
    for funding in funding_rows:
        funding_time_ms = int(funding["funding_time_ms"])
        spot = _latest_price_at_or_before(
            spot_prices,
            target_time_ms=funding_time_ms,
            tolerance_ms=tolerance_ms,
        )
        perp = _latest_price_at_or_before(
            perp_prices,
            target_time_ms=funding_time_ms,
            tolerance_ms=tolerance_ms,
        )
        if spot is None or perp is None:
            missing_basis_count += 1
            continue
        rows.append(
            build_historical_basis_row(
                symbol=str(funding["symbol"]),
                funding_time_ms=funding_time_ms,
                funding_rate=float(funding["funding_rate"]),
                annualized_pct=float(funding["annualized_pct"]),
                spot_mid_price=spot[1],
                perp_mid_price=perp[1],
                spot_price_time_ms=spot[0],
                perp_price_time_ms=perp[0],
            )
        )
    return {
        "status": "ok" if rows else "insufficient_basis_data",
        "rows": rows,
        "missing_basis_count": missing_basis_count,
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
    }
