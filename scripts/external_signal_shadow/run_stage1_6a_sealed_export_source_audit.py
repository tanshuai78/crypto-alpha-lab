#!/usr/bin/env python3
"""CLI runner for Stage 1.6A sealed-export source audit."""

import argparse
import sys
import time
from pathlib import Path

from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter import (
    G2_GRAMMAR_PAIR,
    AdapterInputError,
    load_verified_source_snapshot,
    reduce_verified_snapshot,
)
from src.research.external_signal_shadow.stage1_6a_sealed_export_adapter_storage import (
    persist_adapter_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 1.6A sealed-export source audit.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Path to project root.")
    parser.add_argument("--source-export", type=Path, required=True, help="Path to completed Stage 1.6B sealed export.")
    parser.add_argument("--audit-run-id", type=str, required=True, help="Audit run identifier.")
    parser.add_argument("--output-root", type=Path, required=True, help="Output directory path.")

    args = parser.parse_args()

    try:
        project_root = args.project_root.resolve(strict=True)
        output_root = args.output_root if args.output_root.is_absolute() else project_root / args.output_root
        if output_root.name != args.audit_run_id:
            raise AdapterInputError(f"output_root_basename_mismatch: {output_root.name} != {args.audit_run_id}")

        if output_root.exists():
            raise AdapterInputError(f"output_root_already_exists: {output_root}")

        snapshot = load_verified_source_snapshot(project_root, args.source_export)
        extracted_at_ms = int(time.time() * 1000)
        reduction = reduce_verified_snapshot(
            snapshot,
            semantic_extracted_at_ms=extracted_at_ms,
            grammar_pair=G2_GRAMMAR_PAIR,
        )
        completion_path = persist_adapter_audit(
            output_root,
            audit_run_id=args.audit_run_id,
            snapshot=snapshot,
            reduction=reduction,
            semantic_extracted_at_ms=extracted_at_ms,
        )
        print(f"Source audit complete: {completion_path}")
        sys.exit(0)
    except AdapterInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
