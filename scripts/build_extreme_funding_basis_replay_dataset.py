from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from configs.base import (
    EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS,
    EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC,
    EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR,
    EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC,
    EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS,
    EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
)
from src.research.extreme_funding_basis_replay import (
    HistoricalBasisRow,
    binance_symbol_from_pair,
    build_binance_basis_kline_urls,
    join_funding_rows_with_basis_prices,
    parse_kline_close,
    select_basis_replay_funding_rows,
)

Fetcher = Callable[[str, float], Any]


def fetch_json_url(url: str, timeout_sec: float) -> Any:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(url, timeout=timeout_sec) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep((attempt + 1) * 2.0)
    raise RuntimeError(f"fetch_json_url failed after retries: {last_error}") from last_error


def parse_price_payload(payload: list) -> tuple[dict[int, float], int]:
    prices: dict[int, float] = {}
    row_error_count = 0
    for kline in payload:
        try:
            close_time_ms, close_price = parse_kline_close(kline)
        except (IndexError, TypeError, ValueError):
            row_error_count += 1
            continue
        prices[close_time_ms] = close_price
    return prices, row_error_count


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_dataset_summary(
    rows: list[HistoricalBasisRow],
    *,
    stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats = stats or {}
    selected_count = int(stats.get("selected_funding_row_count", 0))
    if rows:
        status = "ok"
    elif selected_count == 0:
        status = "no_threshold_rows_or_no_input"
    else:
        status = "insufficient_basis_data"
    return {
        "status": status,
        "basis_row_count": len(rows),
        "has_basis_rows": bool(rows),
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "max_price_time_diff_ms": max(row.price_time_diff_ms for row in rows) if rows else None,
        "selected_funding_row_count": selected_count,
        "missing_basis_count": int(stats.get("missing_basis_count", 0)),
        "spot_empty_count": int(stats.get("spot_empty_count", 0)),
        "futures_empty_count": int(stats.get("futures_empty_count", 0)),
        "fetch_error_count": int(stats.get("fetch_error_count", 0)),
        "parse_error_count": int(stats.get("parse_error_count", 0)),
        "row_error_count": int(stats.get("row_error_count", 0)),
        "alignment_miss_count": int(stats.get("alignment_miss_count", 0)),
        "request_count": int(stats.get("request_count", 0)),
        "symbols": list(stats.get("symbols", [])),
    }


def build_basis_rows_for_symbol(
    *,
    symbol: str,
    funding_rows: list[dict[str, Any]],
    fetcher: Fetcher = fetch_json_url,
) -> dict[str, Any]:
    selected_rows = select_basis_replay_funding_rows(
        funding_rows,
        threshold_pct=EXTREME_FUNDING_TRADE_SIGNAL_ANNUALIZED_THRESHOLD_PCT,
        max_following_intervals=EXTREME_FUNDING_SHADOW_MAX_HOLDING_INTERVALS,
    )
    rows: list[HistoricalBasisRow] = []
    stats: dict[str, Any] = {
        "selected_funding_row_count": len(selected_rows),
        "missing_basis_count": 0,
        "spot_empty_count": 0,
        "futures_empty_count": 0,
        "fetch_error_count": 0,
        "parse_error_count": 0,
        "row_error_count": 0,
        "alignment_miss_count": 0,
        "request_count": 0,
        "symbols": [symbol],
    }
    binance_symbol = binance_symbol_from_pair(symbol)
    for funding in selected_rows:
        funding_time_ms = int(funding["funding_time_ms"])
        half_window_ms = EXTREME_FUNDING_BASIS_REPLAY_REQUEST_WINDOW_MS // 2
        urls = build_binance_basis_kline_urls(
            binance_symbol=binance_symbol,
            start_time_ms=funding_time_ms - half_window_ms,
            end_time_ms=funding_time_ms + half_window_ms,
        )
        try:
            spot_payload = fetcher(urls["spot"], EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC)
            stats["request_count"] += 1
            time.sleep(EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC)
            perp_payload = fetcher(
                urls["futures_mark"],
                EXTREME_FUNDING_BASIS_REPLAY_HTTP_TIMEOUT_SEC,
            )
            stats["request_count"] += 1
            time.sleep(EXTREME_FUNDING_BASIS_REPLAY_REQUEST_SLEEP_SEC)
        except Exception:
            stats["fetch_error_count"] += 1
            continue
        if not spot_payload:
            stats["spot_empty_count"] += 1
        if not perp_payload:
            stats["futures_empty_count"] += 1
        try:
            spot_prices, spot_row_errors = parse_price_payload(spot_payload)
            perp_prices, perp_row_errors = parse_price_payload(perp_payload)
        except Exception:
            stats["parse_error_count"] += 1
            continue
        stats["row_error_count"] += spot_row_errors + perp_row_errors
        joined = join_funding_rows_with_basis_prices(
            [funding],
            spot_prices=spot_prices,
            perp_prices=perp_prices,
            tolerance_ms=EXTREME_FUNDING_BASIS_REPLAY_ALIGNMENT_TOLERANCE_MS,
        )
        stats["missing_basis_count"] += int(joined["missing_basis_count"])
        if joined["missing_basis_count"]:
            stats["alignment_miss_count"] += 1
        rows.extend(joined["rows"])
    return {"rows": rows, "stats": stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build historical basis-aware replay rows.")
    parser.add_argument("--symbol", required=True, help="Pair format, for example DOGE/USDT")
    parser.add_argument("--funding-file", required=True)
    parser.add_argument(
        "--output",
        default=f"{EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR}/2026-05-25_basis_rows.jsonl",
    )
    parser.add_argument(
        "--summary-output",
        default=f"{EXTREME_FUNDING_BASIS_REPLAY_OUTPUT_DIR}/2026-05-25_basis_dataset_summary.json",
    )
    args = parser.parse_args()

    funding_rows = load_jsonl(Path(args.funding_file))
    dataset = build_basis_rows_for_symbol(symbol=args.symbol, funding_rows=funding_rows)
    rows = dataset["rows"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(json.dumps(row.__dict__, sort_keys=True) for row in rows),
        encoding="utf-8",
    )

    summary = build_dataset_summary(rows, stats=dataset["stats"])
    summary_output = Path(args.summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
