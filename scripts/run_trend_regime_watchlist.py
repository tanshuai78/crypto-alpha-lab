from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from loguru import logger

from configs.base import TREND_REGIME_EVENT_LOG_JSONL
from src.strategies.trend_regime.scanner import (
    TrendRegimeObservationStrategy,
    classify_trend_regime_snapshot,
)

PUBLIC_SNAPSHOT_FIELDS = {
    "timestamp_ms",
    "exchange",
    "symbol",
    "close_price",
    "return_1h_pct",
    "vol_1h_pct",
    "vol_baseline_30d_pct",
    "open_interest",
    "oi_change_1h_pct",
    "liquidation_notional_1h_usdt",
    "volume_24h_usdt",
    "estimated_spread_bps",
    "estimated_slippage_bps",
    "funding_state",
    "data_age_sec",
}


def build_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    return {key: raw.get(key) for key in PUBLIC_SNAPSHOT_FIELDS}


def _symbol_key(symbol: str) -> str:
    return symbol.replace("/", "").upper()


def apply_liquidation_notional_from_cache(
    row: dict[str, Any],
    liquidation_notional_by_symbol: dict[str, float] | None,
) -> dict[str, Any]:
    if not liquidation_notional_by_symbol:
        return row

    current = row.get("liquidation_notional_1h_usdt")
    try:
        current_number = float(current) if current is not None else None
    except (TypeError, ValueError):
        current_number = None
    if current_number is not None and current_number > 0.0:
        return row

    symbol = str(row.get("symbol") or "")
    if not symbol:
        return row
    cache_value = liquidation_notional_by_symbol.get(_symbol_key(symbol))
    if cache_value is None:
        return row

    patched = dict(row)
    patched["liquidation_notional_1h_usdt"] = float(cache_value)
    return patched


def estimate_liquidation_notional_usdt(force_orders_payload: list[dict[str, Any]]) -> float:
    total = 0.0
    for order in force_orders_payload:
        try:
            quantity = float(
                order.get("executedQty")
                or order.get("origQty")
                or order.get("cumQty")
                or 0.0
            )
        except (TypeError, ValueError):
            quantity = 0.0

        try:
            price = float(
                order.get("averagePrice")
                or order.get("avragePrice")
                or order.get("avgPrice")
                or order.get("price")
                or 0.0
            )
        except (TypeError, ValueError):
            price = 0.0

        if quantity > 0.0 and price > 0.0:
            total += quantity * price
    return round(total, 10)


def build_binance_fapi_url(*, base_url: str, path: str, params: dict[str, str] | None = None) -> str:
    normalized_base = base_url.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    if not params:
        return f"{normalized_base}{normalized_path}"
    return f"{normalized_base}{normalized_path}?{urlencode(params)}"


def fetch_json_url(url: str, *, timeout_sec: float) -> Any:
    request = Request(url, headers={"User-Agent": "crypto-alpha-lab/trend-regime-phase1a"})
    with urlopen(request, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_liquidation_notional_1h_from_binance(
    *,
    symbols: tuple[str, ...],
    base_url: str,
    timeout_sec: float = 10.0,
    now_ms: int | None = None,
) -> tuple[dict[str, float], dict[str, str]]:
    now = int(time.time() * 1000) if now_ms is None else now_ms
    start = now - 3_600_000
    liquidation_notional_by_symbol: dict[str, float] = {}
    status_by_symbol: dict[str, str] = {}

    for symbol in symbols:
        symbol_key = _symbol_key(symbol)
        url = build_binance_fapi_url(
            base_url=base_url,
            path="/fapi/v1/allForceOrders",
            params={
                "symbol": symbol_key,
                "startTime": str(start),
                "endTime": str(now),
                "limit": "100",
            },
        )
        try:
            payload = fetch_json_url(url, timeout_sec=timeout_sec)
            if isinstance(payload, list):
                liquidation_notional_by_symbol[symbol_key] = estimate_liquidation_notional_usdt(payload)
                status_by_symbol[symbol_key] = "ok"
            else:
                status_by_symbol[symbol_key] = "unexpected_payload"
        except HTTPError as exc:
            message = ""
            try:
                body = exc.read().decode("utf-8")
                message = body
            except Exception:
                message = str(exc)
            # Binance currently reports maintenance for /fapi/v1/allForceOrders.
            if "out of maintenance" in message:
                status_by_symbol[symbol_key] = "endpoint_out_of_maintenance"
            else:
                status_by_symbol[symbol_key] = f"http_error_{exc.code}"
        except Exception:
            status_by_symbol[symbol_key] = "fetch_error"

    return liquidation_notional_by_symbol, status_by_symbol


async def run_trend_regime_poll_once(
    *,
    rows: list[dict[str, Any]],
    strategy: TrendRegimeObservationStrategy,
    liquidation_notional_by_symbol: dict[str, float] | None = None,
) -> dict[str, Any]:
    signals = []
    reject_reasons = []
    snapshots = []

    for raw in rows:
        enriched = apply_liquidation_notional_from_cache(raw, liquidation_notional_by_symbol)
        snapshot = build_snapshot(enriched)
        snapshots.append(snapshot)
        classification = classify_trend_regime_snapshot(snapshot)
        if classification.reject_reason is not None:
            reject_reasons.append(classification.reject_reason)
            continue
        scanned = await strategy.scan(snapshot)
        signals.extend(scanned)

    return {
        "signals": signals,
        "reject_reasons": reject_reasons,
        "snapshots": snapshots,
    }


def summarize_reject_counts(reasons: list[str]) -> dict[str, int]:
    return dict(Counter(reasons))


def append_jsonl(filepath: Path, data: dict[str, Any]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run trend-regime Phase 1A watchlist daemon")
    parser.add_argument("--input-jsonl", default="")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--poll-interval-sec", type=float, default=10.0)
    parser.add_argument("--forever", action="store_true")
    parser.add_argument(
        "--liquidation-cache-json",
        default="data/trend_regime_liquidation_cache.json",
        help="Optional JSON file: {\"BTCUSDT\": 12345.0, ...} for liquidation_notional_1h_usdt injection.",
    )
    parser.add_argument(
        "--collect-liquidation-from-binance",
        action="store_true",
        help="Try collecting liquidation notional via /fapi/v1/allForceOrders for watch symbols.",
    )
    parser.add_argument("--binance-fapi-base-url", default="https://fapi.binance.com")
    return parser.parse_args(argv)


def load_rows_from_jsonl(path: str) -> list[dict[str, Any]]:
    if not path:
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_liquidation_cache(path: str) -> dict[str, float]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in payload.items():
        try:
            result[_symbol_key(str(key))] = float(value)
        except (TypeError, ValueError):
            continue
    return result


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    strategy = TrendRegimeObservationStrategy()
    rows = load_rows_from_jsonl(args.input_jsonl)
    event_log_path = Path(args.data_root) / TREND_REGIME_EVENT_LOG_JSONL

    iteration = 0
    while args.forever or iteration < args.max_iterations:
        started_at = time.time()
        liquidation_notional_by_symbol = load_liquidation_cache(args.liquidation_cache_json)
        liquidation_status_by_symbol: dict[str, str] = {}
        if args.collect_liquidation_from_binance:
            collected, status = fetch_liquidation_notional_1h_from_binance(
                symbols=tuple({str(row.get("symbol") or "") for row in rows if row.get("symbol")}),
                base_url=args.binance_fapi_base_url,
            )
            liquidation_notional_by_symbol.update(collected)
            liquidation_status_by_symbol = status

        result = await run_trend_regime_poll_once(
            rows=rows,
            strategy=strategy,
            liquidation_notional_by_symbol=liquidation_notional_by_symbol,
        )

        payload = {
            "ts_ms": int(time.time() * 1000),
            "signal_count": len(result["signals"]),
            "reject_counts": summarize_reject_counts(result["reject_reasons"]),
            "snapshot_count": len(result["snapshots"]),
            "liquidation_status": liquidation_status_by_symbol,
        }
        append_jsonl(event_log_path, payload)
        logger.info(
            "trend_regime_heartbeat signals={} rejects={}",
            payload["signal_count"],
            payload["reject_counts"],
        )

        iteration += 1
        if not args.forever and iteration >= args.max_iterations:
            break

        elapsed = time.time() - started_at
        sleep_sec = max(args.poll_interval_sec - elapsed, 0.0)
        if sleep_sec > 0.0:
            await asyncio.sleep(sleep_sec)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
