import argparse
import json
import os

from configs import base
from src.research.external_signal_shadow.stage1_5a_source_audit_loader import (
    load_or_fetch_payloads,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_models import (
    SourceAuditFinding,
    SourceProfile,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_normalizer import (
    normalize_payload,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_safety import (
    validate_domain_allowlist,
    validate_source_resource_safety,
)
from src.research.external_signal_shadow.stage1_5a_source_audit_summary import (
    build_source_audit_summary,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run Stage 1.5A Historical Event Source Audit"
    )
    parser.add_argument(
        "--source-profile",
        required=True,
        choices=[p.value for p in SourceProfile],
        help="Source profile configuration template",
    )
    parser.add_argument(
        "--source-file",
        help="Local source file path or glob pattern (e.g. data/fixtures/*.jsonl)",
    )
    parser.add_argument(
        "--source-url",
        help="Remote source URL to fetch",
    )
    parser.add_argument(
        "--output-summary",
        required=True,
        help="Output path for the generated audit JSON summary",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum pages or items to process",
    )
    parser.add_argument(
        "--fixture-run",
        action="store_true",
        help="Mark this execution as a local fixture run (research_result_valid = false)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Pre-flight check
    if not args.source_file and not args.source_url:
        raise ValueError("Must specify either --source-file or --source-url")

    # If URL is specified, validate domain allowlist before even loading/fetching
    if args.source_url:
        if not validate_domain_allowlist(
            args.source_url,
            base.EXTERNAL_SIGNAL_STAGE1_5A_SOURCE_AUDIT_ALLOWED_DOMAINS,
        ):
            raise ValueError(f"URL domain is not in allowlist: {args.source_url}")

    # Determine source name from profile/domain
    source_name = f"{args.source_profile}_source"

    # Load payloads
    payloads, fixture_run, loader_metadata = load_or_fetch_payloads(
        source_file=args.source_file,
        source_url=args.source_url,
        source_name=source_name,
        source_profile=args.source_profile,
        write_cache=True if args.source_url else False,
    )

    all_events = []
    all_findings = []

    merged_metrics = {
        "timestamp_source_disagreement_count": 0,
        "source_format_drift_count": 0,
        "schema_quarantine_count": 0,
        **loader_metadata,
    }

    for p in payloads:
        # Run safety validation
        findings = validate_source_resource_safety(p)
        all_findings.extend(findings)

        # Check if there is any veto finding that blocks parsing entirely
        has_veto = any(f.severity == "veto" for f in findings)
        if has_veto:
            # Skip normalization, but record that format/loading failed
            continue

        # Normalize
        events, metrics = normalize_payload(p)
        all_events.extend(events)

        # Merge metrics
        for k, v in metrics.items():
            if k in merged_metrics:
                merged_metrics[k] += v
        if metrics.get("source_format_drift_count", 0) > 0:
            all_findings.append(
                SourceAuditFinding(
                    rule_id="source_format_drift",
                    severity="veto",
                    message="Source profile produced zero normalized events or format drift",
                    finding_details={"source_name": p.source_name},
                )
            )

    # Build summary
    # Override fixture_run if explicitly passed as argument
    final_fixture_run = fixture_run or args.fixture_run
    summary = build_source_audit_summary(
        events=all_events,
        metrics=merged_metrics,
        findings=all_findings,
        fixture_run=final_fixture_run,
    )

    # Write output summary
    os.makedirs(os.path.dirname(os.path.abspath(args.output_summary)), exist_ok=True)
    with open(args.output_summary, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Audit completed. Summary written to: {args.output_summary}")


if __name__ == "__main__":
    main()
