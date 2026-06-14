from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from research.external_signal_shadow.stage1_3_models import HistoricalBar
from research.external_signal_shadow.stage1_3_orchestrator import run_stage1_3_candidate_discovery


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run External Signal Shadow Lab Stage 1.3 Candidate Discovery")
    parser.add_argument("--bars", type=str, required=True, help="Path to input JSONL bars file")
    parser.add_argument("--output", type=str, required=True, help="Path to output JSON summary file")
    parser.add_argument("--historical-venue", type=str, required=True, help="Name of historical venue")
    parser.add_argument("--venue-proxy-used", action="store_true", help="Whether venue proxy was used")
    parser.add_argument("--fixture-run", action="store_true", help="Whether this is a fixture smoke run")

    args = parser.parse_args(argv)

    bars_path = Path(args.bars)
    if not bars_path.exists():
        print(f"Error: bars file {args.bars} does not exist", file=sys.stderr)
        return 1

    bars = []
    with open(bars_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                bar = HistoricalBar(
                    symbol=data["symbol"],
                    bar_start_ms=int(data["bar_start_ms"]),
                    bar_end_ms=int(data["bar_end_ms"]),
                    open_price=float(data["open_price"]),
                    high_price=float(data["high_price"]),
                    low_price=float(data["low_price"]),
                    close_price=float(data["close_price"]),
                    quote_volume=float(data["quote_volume"]),
                )
                bars.append(bar)
            except Exception as e:
                print(f"Error parsing line {line_num}: {e}", file=sys.stderr)
                return 1

    summary = run_stage1_3_candidate_discovery(
        bars,
        historical_venue=args.historical_venue,
        venue_proxy_used=args.venue_proxy_used,
        fixture_run=args.fixture_run,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
