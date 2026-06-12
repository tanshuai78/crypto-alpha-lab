"""
Stage 1.1 Manual Payload Dry Run CLI

Usage:
    PYTHONPATH=. uv run python scripts/run_external_signal_shadow_stage1_1_manual_dry_run.py \
        --input data/external_signal_shadow/raw/gate_marketanalysis_manual_export/2026-06-12.jsonl \
        --price-map configs/external_signal_shadow_price_map.json \
        --output-events data/external_signal_shadow/normalized/stage1_1_gate_marketanalysis_manual_events.jsonl \
        --output-summary reports/external_signal_shadow/connectors/stage1_1_gate_marketanalysis_manual_summary.json
"""

import argparse
import json
import sys
from pathlib import Path

from configs import base
from src.research.external_signal_shadow.file_backed_connector import run_file_backed_connector


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1.1 Manual Payload Dry Run – gate_marketanalysis_manual_export"
    )
    parser.add_argument("--input", required=True, help="Path to the JSONL manual payload file")
    parser.add_argument(
        "--price-map",
        required=True,
        help="Path to price mapping JSON file",
    )
    parser.add_argument("--output-events", required=True, help="Path for emitted events JSONL")
    parser.add_argument("--output-summary", required=True, help="Path for JSON summary output")
    parser.add_argument(
        "--external-api",
        action="store_true",
        help="(disabled) Reject external API mode – not supported for safety.",
    )

    args = parser.parse_args()

    # Safety boundary: external API access is not permitted at Stage 1.1.
    if args.external_api:
        print("ERROR: --external-api is not permitted for Stage 1.1 manual dry run.", file=sys.stderr)
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        # Per plan: if raw file is missing, report data_failure; do not fake with fixture.
        summary = {
            "decision": "external_signal_connector_stage1_failed",
            "failure_type": "data_failure",
            "primary_blocker": "missing_raw_input_file",
            "source": base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE,
            "input_file": args.input,
            "message": f"Raw input file not found: {input_path}",
        }
        out_summary = Path(args.output_summary)
        out_summary.parent.mkdir(parents=True, exist_ok=True)
        out_summary.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
        print(f"[data_failure] Raw input file missing: {input_path}")
        print(f"Summary written to: {out_summary}")
        sys.exit(1)

    Path(args.output_events).parent.mkdir(parents=True, exist_ok=True)

    print("[*] Stage 1.1 Dry Run starting")
    print(f"    source    : {base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE}")
    print(f"    input     : {input_path}")
    print(f"    price-map : {args.price_map}")

    summary = run_file_backed_connector(
        input_files=[str(input_path)],
        price_map_path=args.price_map,
        output_path=args.output_events,
        source=base.EXTERNAL_SIGNAL_STAGE1_1_SOURCE,
    )

    out_summary = Path(args.output_summary)
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))

    print()
    print("=" * 60)
    print(f"决策:               {summary.get('decision')}")
    print(f"failure_type:       {summary.get('failure_type')}")
    print(f"minimal_connector_pass: {summary.get('minimal_connector_pass')}")
    print(f"stage0_handoff_ready:   {summary.get('stage0_handoff_ready')}")
    print(f"stage0_handoff_mode:    {summary.get('stage0_handoff_mode')}")
    print("=" * 60)
    print(f"Summary written to: {out_summary}")
    print(f"Events written to:  {args.output_events}")


if __name__ == "__main__":
    main()
