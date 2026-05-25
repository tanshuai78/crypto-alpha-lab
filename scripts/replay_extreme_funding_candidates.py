from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.research.extreme_funding_replay import (
    detect_extreme_funding_segments,
    load_settled_funding_rows,
)
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


def _segment_to_candidate_row(segment: dict[str, Any]) -> dict[str, Any]:
    intervals = int(segment["row_count"])
    funding_income_bps = float(segment["funding_income_bps"])
    return {
        "timestamp_ms": int(segment["start_ms"]),
        "source_type": "historical_settled",
        "symbol": str(segment["symbol"]),
        "exchange": "binance",
        "direction": "neutral",
        "watch_level": "historical_settled_extreme",
        "annualized_funding_estimate_pct": float(segment["max_annualized_pct"]),
        "funding_rate_per_interval": funding_income_bps / intervals / 10_000.0 if intervals else 0.0,
        "expected_holding_intervals": 1,
        "settlement_persistence": float(segment.get("settlement_persistence", 1.0)),
        "coverage_quality": "funding_only_insufficient_for_basis",
    }


def build_candidate_replay_summary(paths: list[str | Path], *, threshold_pct: float) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    for path in paths:
        rows = load_settled_funding_rows(path)
        segments.extend(detect_extreme_funding_segments(rows, threshold_pct=threshold_pct))

    reject_counts: Counter[str] = Counter()
    candidate_count = 0
    for segment in segments:
        decision = build_extreme_funding_candidate(_segment_to_candidate_row(segment))
        if decision.accepted:
            candidate_count += 1
        else:
            reject_counts[decision.reject_reason or "unknown_reject"] += 1

    has_threshold_segments = len(segments) > 0
    return {
        "threshold_pct": threshold_pct,
        "input_file_count": len(paths),
        "segments_seen": len(segments),
        "has_threshold_segments": has_threshold_segments,
        "status": "ok" if has_threshold_segments else "no_threshold_segments_or_no_input",
        "candidate_count": candidate_count,
        "reject_reason_counts": dict(sorted(reject_counts.items())),
        "coverage_quality": "funding_only_insufficient_for_basis",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay extreme funding Phase 1B funding-only candidates.")
    parser.add_argument("--input-glob", default="data/funding_settled/binance_*_settled.jsonl")
    parser.add_argument("--threshold-pct", type=float, default=100.0)
    parser.add_argument(
        "--output",
        default="reports/extreme_funding/2026-05-25_candidate_replay_summary.json",
    )
    args = parser.parse_args()

    summary = build_candidate_replay_summary(
        sorted(Path().glob(args.input_glob)),
        threshold_pct=args.threshold_pct,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
