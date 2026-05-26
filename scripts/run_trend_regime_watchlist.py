from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

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


async def run_trend_regime_poll_once(
    *,
    rows: list[dict[str, Any]],
    strategy: TrendRegimeObservationStrategy,
) -> dict[str, Any]:
    signals = []
    reject_reasons = []
    snapshots = []

    for raw in rows:
        snapshot = build_snapshot(raw)
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


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    strategy = TrendRegimeObservationStrategy()
    rows = load_rows_from_jsonl(args.input_jsonl)
    event_log_path = Path(args.data_root) / TREND_REGIME_EVENT_LOG_JSONL

    iteration = 0
    while args.forever or iteration < args.max_iterations:
        started_at = time.time()
        result = await run_trend_regime_poll_once(rows=rows, strategy=strategy)

        payload = {
            "ts_ms": int(time.time() * 1000),
            "signal_count": len(result["signals"]),
            "reject_counts": summarize_reject_counts(result["reject_reasons"]),
            "snapshot_count": len(result["snapshots"]),
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
