#!/usr/bin/env python3
"""CLI Entrypoint for Stage 1.5J-B Historical aggTrades Launch-Anchor Price-Response Exploratory Research.

Usage:
  python3 scripts/external_signal_shadow/run_stage1_5j_b_historical_aggtrades_launch_response.py \
    --run-id stage1_5j_b_historical_aggtrades_launch_response_20261011T120000Z
"""

from __future__ import annotations

import argparse
import sys

from src.research.external_signal_shadow.stage1_5j_b_historical_aggtrades_launch_response import (
    RUN_ID_REGEX,
    run_stage1_5j_b_historical_aggtrades_launch_response,
)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and invoke public runner."""
    parser = argparse.ArgumentParser(
        description="Stage 1.5J-B Historical aggTrades Launch-Anchor Price-Response Exploratory Research"
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Target RUN_ID matching ^stage1_5j_b_historical_aggtrades_launch_response_[0-9]{8}T[0-9]{6}Z$",
    )

    args = parser.parse_args(argv)

    if not RUN_ID_REGEX.match(args.run_id):
        sys.stderr.write(f"Invalid --run-id format: {args.run_id}\n")
        sys.exit(2)

    return run_stage1_5j_b_historical_aggtrades_launch_response(args.run_id)


if __name__ == "__main__":
    sys.exit(main())
