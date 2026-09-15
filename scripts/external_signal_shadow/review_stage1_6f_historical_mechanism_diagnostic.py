"""Read-only reviewer script for Stage 1.6F diagnostic bundle."""

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_storage import (
    DiagnosticStorageError,
    load_diagnostic_bundle,
)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.6F Read-Only Diagnostic Bundle Reviewer",
        add_help=False,
    )
    parser.add_argument("--bundle-root", required=True, help="Path to completed F bundle directory")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        sys.exit(2)

    bundle_root = Path(args.bundle_root).resolve()

    try:
        bundle = load_diagnostic_bundle(bundle_root)
    except DiagnosticStorageError as exc:
        sys.stderr.write(f"bundle_review_failed: {exc}\n")
        sys.exit(1)
    except Exception as exc:
        sys.stderr.write(f"bundle_review_error: {exc}\n")
        sys.exit(1)

    manifest = bundle["manifest"]
    summary = bundle["summary"]
    denominator = bundle["denominator"]
    diagnostics = bundle["diagnostics"]

    # Verify all permission flags are strictly False across all loaded records
    for flag_name in ALL_PERMISSION_FLAGS_FALSE:
        if summary.get("authority_flags", {}).get(flag_name) is not False:
            sys.stderr.write(f"permission_or_side_effect_violation: summary flag {flag_name} not False\n")
            sys.exit(1)

    # Compute metrics counts
    status_counts = Counter(m.get("status") for m in diagnostics)
    metric_counts = Counter(m.get("metric_name") for m in diagnostics)

    counts = summary.get("counts", {})
    print("=== STAGE 1.6F HISTORICAL MECHANISM DIAGNOSTIC REVIEW ===")
    print(f"Bundle Root: {bundle_root}")
    print(f"Bundle State: {manifest.get('bundle_state')}")
    print(f"Schema Version: {manifest.get('schema_version')}")
    print(f"Input Export ID: {summary.get('input_export_id')}")
    print(f"Denominator Rows: {len(denominator)} (Eligible: {counts.get('eligible_count')}, Ineligible: {counts.get('ineligible_count')})")
    print(f"Matching: Matched: {counts.get('matched_count')}, Unmatched: {counts.get('unmatched_count')}")
    print(f"Total Metric Diagnostics: {len(diagnostics)}")
    print("Metrics by Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print("Metrics by Name:")
    for mname, count in sorted(metric_counts.items()):
        print(f"  {mname}: {count}")
    print("Authority Flags: ALL_STRICTLY_FALSE")
    print("=== REVIEW PASSED ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
