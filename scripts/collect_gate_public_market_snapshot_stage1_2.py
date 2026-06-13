#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from configs import base
from research.external_signal_shadow.gate_public_collector import (
    collect_gate_public_snapshots_from_fetcher,
    default_fetch_json,
    write_failure_summary,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Gate Spot Ticker market snapshots.")
    parser.add_argument("--mock-response", type=str, help="Path to mock ticker responses JSON fixture.")
    parser.add_argument("--live-public-readonly", action="store_true", help="Explicitly enable real public readonly CEX requests.")
    parser.add_argument("--output", type=str, required=True, help="Path to write raw wrapper JSONL.")
    parser.add_argument("--output-summary", type=str, required=True, help="Path to write collector summary JSON.")

    args = parser.parse_args(argv)

    output_summary_path = args.output_summary

    # Safety constraint: Check if credentials env vars are set. We do NOT read them or use them.
    # Actually, the test sets env vars but expects the run to succeed with mock.
    # We must not read them or write them to the outputs.
    # Let's ensure that they are never in the script's variables or output.

    # 1. Flag validation
    if args.mock_response and args.live_public_readonly:
        write_failure_summary(
            output_summary_path=output_summary_path,
            failure_type="conflicting_mock_and_live_public_readonly",
            http_success_count=0,
            http_failure_count=0,
            network_mode="invalid",
        )
        return 2

    if not args.mock_response and not args.live_public_readonly:
        write_failure_summary(
            output_summary_path=output_summary_path,
            failure_type="missing_mock_or_live_public_readonly_flag",
            http_success_count=0,
            http_failure_count=0,
            network_mode="invalid",
        )
        return 2

    # 2. Setup output directories
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(output_summary_path).parent.mkdir(parents=True, exist_ok=True)

    # 3. Setup fetcher and network mode
    if args.mock_response:
        mock_path = Path(args.mock_response)
        if not mock_path.exists():
            write_failure_summary(
                output_summary_path=output_summary_path,
                failure_type="mock_file_missing",
                http_success_count=0,
                http_failure_count=5,
                network_mode="mock",
            )
            return 1

        try:
            with open(mock_path, "r", encoding="utf-8") as f:
                mock_data = json.load(f)
        except Exception:
            write_failure_summary(
                output_summary_path=output_summary_path,
                failure_type="parse_error",
                http_success_count=0,
                http_failure_count=5,
                network_mode="mock",
            )
            return 1

        def mock_fetcher(url: str, timeout_sec: float, user_agent: str) -> tuple[int, object, int]:
            # Url format: https://.../spot/tickers?currency_pair=BTC_USDT
            pair = url.split("currency_pair=")[1]
            if pair in mock_data:
                return 200, mock_data[pair], 10
            return 404, {"error": "pair_not_found"}, 10

        fetcher = mock_fetcher
        network_mode = "mock"
    else:
        fetcher = default_fetch_json
        network_mode = "live_public_readonly"

    # 4. Run collection
    try:
        summary = collect_gate_public_snapshots_from_fetcher(
            gate_pairs=base.EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS,
            output_path=args.output,
            fetcher=fetcher,
            inter_request_delay_sec=base.EXTERNAL_SIGNAL_STAGE1_2_INTER_REQUEST_DELAY_SEC,
            base_url=base.EXTERNAL_SIGNAL_STAGE1_2_GATE_REST_BASE_URL,
            tickers_path=base.EXTERNAL_SIGNAL_STAGE1_2_GATE_TICKERS_PATH,
            timeout_sec=base.EXTERNAL_SIGNAL_STAGE1_2_TIMEOUT_SEC,
            user_agent=base.EXTERNAL_SIGNAL_STAGE1_2_USER_AGENT,
            network_mode=network_mode,
        )

        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        if not summary["collector_minimal_pass"]:
            return 1
        return 0
    except Exception:
        write_failure_summary(
            output_summary_path=output_summary_path,
            failure_type="collector_internal_error",
            http_success_count=0,
            http_failure_count=len(base.EXTERNAL_SIGNAL_STAGE1_2_ALLOWED_GATE_PAIRS),
            network_mode=network_mode,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
