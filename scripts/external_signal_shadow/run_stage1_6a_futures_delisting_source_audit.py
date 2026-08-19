#!/usr/bin/env python3
"""
Stage 1.6A Binance USD-M Futures Delisting Source / Schema / Effective-Time Audit Runner.
Design Reference: docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md

Usage:
    .venv/bin/python scripts/external_signal_shadow/run_stage1_6a_futures_delisting_source_audit.py \
        --capture-bundle tests/fixtures/external_signal_shadow/stage1_6a/synthetic_delisting_capture_bundle.jsonl \
        --output-root data/external_signal_shadow/stage1_6a/run_001 \
        --fixture-run
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.research.external_signal_shadow.stage1_6a_futures_delisting_audit import (
    process_capture_bundle,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_storage import (
    persist_audit_artifacts,
    validate_output_root_path,
)
from src.research.external_signal_shadow.stage1_6a_futures_delisting_summary import (
    build_stage1_6a_source_audit_summary,
)

FIXTURE_CAPTURE_ROOT = Path("tests/fixtures/external_signal_shadow/stage1_6a").resolve()
ALLOWED_RECORD_TYPES = {"list_capture", "detail_observation"}
FORBIDDEN_DERIVED_KEYS = {
    "article_discovery",
    "audit_candidate_manifest",
    "settlement_time_ms",
    "fact_parse_status",
    "normalized_body_utf8_byte_start",
    "normalized_body_utf8_byte_end",
    "excerpt",
    "semantic_extraction_id",
    "source_audit_eligible",
    "risk_veto_candidate",
    "live_observed",
    "market_data_coverage",
    "source_audit_passed",
}


def validate_capture_bundle_path(bundle_path: Path) -> Path:
    """Accepts only regular fixture files after resolving path traversal and symlinks."""
    resolved = bundle_path.resolve()
    if not resolved.is_relative_to(FIXTURE_CAPTURE_ROOT):
        raise ValueError(f"Capture bundle must resolve under fixture root: {FIXTURE_CAPTURE_ROOT}")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"Capture bundle does not exist or is not a file: {bundle_path}")
    return resolved


def load_and_validate_bundle_records(bundle_file: Path) -> List[Dict[str, Any]]:
    """Loads JSONL bundle lines and ensures fail-closed rejection of malformed lines or injected derived fields."""
    records: List[Dict[str, Any]] = []
    with open(bundle_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                rec = json.loads(line_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSONL on line {idx} of {bundle_file.name}: {e}")

            if not isinstance(rec, dict):
                raise ValueError(f"Invalid record type on line {idx}: expected JSON object")

            if rec.get("record_type") not in ALLOWED_RECORD_TYPES:
                raise ValueError(f"Unsupported record_type on line {idx}: {rec.get('record_type')!r}")

            if rec.get("capture_mode") not in (None, "historical_backfill"):
                raise ValueError(f"capture_mode must be historical_backfill on line {idx}")

            # Check for forbidden caller-injected derived fields
            injected = set(rec.keys()) & FORBIDDEN_DERIVED_KEYS
            if injected:
                raise ValueError(
                    f"Forbidden caller-injected derived fields on line {idx}: {sorted(list(injected))}"
                )

            records.append(rec)
    return records


def run_source_audit(
    capture_bundle_path: Path,
    output_root: Path,
    fixture_run: bool,
    run_id: str = None,
) -> Path:
    """Runs the offline Stage 1.6A source audit pipeline and persists verified artifacts."""
    if fixture_run is not True:
        raise ValueError("This implementation requires explicit fixture-run mode")
    valid_bundle_path = validate_capture_bundle_path(capture_bundle_path)
    validate_output_root_path(output_root)

    if not run_id:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    raw_bundle_bytes = valid_bundle_path.read_bytes()
    records = load_and_validate_bundle_records(valid_bundle_path)

    # Process bundle
    audit_result = process_capture_bundle(records)

    # Build summary
    summary = build_stage1_6a_source_audit_summary(audit_result, run_id=run_id, fixture_run=fixture_run)

    # Persist artifacts with two-stage commit
    completion_path = persist_audit_artifacts(
        output_root=output_root,
        audit_result=audit_result,
        summary_dict=summary,
        capture_bundle_bytes=raw_bundle_bytes,
        run_id=run_id,
    )
    return completion_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 1.6A Binance USD-M Futures Delisting Source / Schema / Effective-Time Audit Runner"
    )
    parser.add_argument("--capture-bundle", type=Path, required=True, help="Path to input capture bundle JSONL")
    parser.add_argument("--output-root", type=Path, required=True, help="Path to output directory")
    parser.add_argument("--fixture-run", action="store_true", default=False, help="Flag declaring fixture/synthetic run")

    args = parser.parse_args()

    try:
        completion_manifest_path = run_source_audit(
            capture_bundle_path=args.capture_bundle,
            output_root=args.output_root,
            fixture_run=args.fixture_run,
        )
        print("Stage 1.6A source audit completed successfully.")
        print(f"Completion manifest written: {completion_manifest_path}")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Stage 1.6A source audit failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
