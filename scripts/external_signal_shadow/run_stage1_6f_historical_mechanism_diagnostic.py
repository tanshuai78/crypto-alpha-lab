"""Offline runner script for Stage 1.6F historical mechanism diagnostic."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.research.external_signal_shadow.stage1_6f_historical_diagnostic import (
    ALL_PERMISSION_FLAGS_FALSE,
    DenominatorRow,
    DiagnosticMetricResult,
    compute_descriptive_metrics,
    reconstruct_denominator,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_source import (
    verify_c_input,
    verify_market_evidence,
)
from src.research.external_signal_shadow.stage1_6f_historical_diagnostic_storage import (
    BUNDLE_MANIFEST_FILENAME,
    write_diagnostic_bundle,
)


def _resolve_safe_path(raw_path: str, arg_name: str) -> Path:
    p = Path(raw_path).resolve()
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stage 1.6F Offline Historical Mechanism Diagnostic Runner",
        add_help=False,
    )
    parser.add_argument("--project-root", required=True, help="Path to project root")
    parser.add_argument("--source-export", required=True, help="Path to source export receipt")
    parser.add_argument("--completed-root", required=True, help="Path to completed C audit root")
    parser.add_argument("--market-evidence-root", required=True, help="Path to GAP-02 market evidence package")
    parser.add_argument("--output-root", required=True, help="Path to destination F bundle directory")

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        sys.exit(2)

    project_root = _resolve_safe_path(args.project_root, "--project-root")
    source_export = _resolve_safe_path(args.source_export, "--source-export")
    completed_root = _resolve_safe_path(args.completed_root, "--completed-root")
    market_evidence_root = _resolve_safe_path(args.market_evidence_root, "--market-evidence-root")
    output_root = _resolve_safe_path(args.output_root, "--output-root")

    # Reject if output_root already contains a completed bundle
    if (output_root / BUNDLE_MANIFEST_FILENAME).is_file():
        sys.stderr.write(f"output_root_already_completed: {output_root}\n")
        sys.exit(1)

    # 1. Verify upstream C input (fails closed on any invalidity)
    verified_c = verify_c_input(
        project_root=project_root,
        completed_root=completed_root,
        source_export=source_export,
    )

    # 2. Verify market evidence package (fails closed on any invalidity)
    verified_market = verify_market_evidence(
        market_evidence_root=market_evidence_root,
    )

    # 3. Reconstruct denominator
    raw_denominator = reconstruct_denominator(verified_c)

    # 4. Deterministic matching and descriptive metric computation
    # Check for historical control universe artifacts in auxiliary artifacts
    reef_control_artifact = verified_market.auxiliary_artifacts.get("historical_control_universe_reef_20250115.json", {})
    reef_top_controls = reef_control_artifact.get("top_qualified_controls", [])

    updated_denominator: List[DenominatorRow] = []
    all_metrics: List[DiagnosticMetricResult] = []

    for row in raw_denominator:
        matched_controls: List[Dict[str, Any]] = []
        match_status = "unmatched"

        if row.symbol == "REEFUSDT" and reef_top_controls:
            matched_controls = reef_top_controls
            match_status = "matched"

        updated_row = replace(
            row,
            match_status=match_status,
            selected_controls=tuple(matched_controls),
        )
        updated_denominator.append(updated_row)

        ctrl_symbols = [
            (c.get("symbol") or c.get("canonical_symbol")) if isinstance(c, dict) else str(c)
            for c in matched_controls
        ]

        if updated_row.t_pub_ms is not None:
            row_metrics = compute_descriptive_metrics(
                symbol=updated_row.symbol,
                t_pub_ms=updated_row.t_pub_ms,
                t_settle_ms=updated_row.t_settle_ms,
                selected_controls=ctrl_symbols,
                verified_market=verified_market,
                parent_article_id=updated_row.parent_article_id,
                contract_id=updated_row.contract_id,
                ineligibility_reasons=updated_row.ineligibility_reasons,
            )
            all_metrics.extend(row_metrics)
        else:
            # For rows lacking t_pub_ms, emit all standard metric placeholders as unavailable
            for metric_name, unavail_status in (
                ("price_path", "price_path_unavailable"),
                ("basis", "basis_unavailable"),
                ("mark_basis", "mark_basis_unavailable"),
                ("funding", "funding_unavailable"),
                ("open_interest", "oi_unavailable"),
                ("visible_depth", "visible_depth_unavailable"),
                ("agg_trades", "agg_trade_unavailable"),
                ("settlement_mechanism", "settlement_value_unavailable_insufficient_1s_index"),
            ):
                all_metrics.append(
                    DiagnosticMetricResult(
                        metric_name=metric_name,
                        window="W1" if metric_name != "settlement_mechanism" else "W2",
                        status=unavail_status,
                        observed_interval={"observation_count": 0},
                        descriptors={"note": "t_pub_ms_missing_or_ineligible"},
                        authority_flags=ALL_PERMISSION_FLAGS_FALSE,
                        parent_article_id=updated_row.parent_article_id,
                        contract_id=updated_row.contract_id,
                        symbol=updated_row.symbol,
                        original_interval={
                            "requested_window": "W1" if metric_name != "settlement_mechanism" else "W2",
                            "start_ms": None,
                            "end_ms": None,
                        },
                        controls_or_exclusion_reasons=updated_row.ineligibility_reasons or ("missing_t_pub_ms",),
                    )
                )

    # Determine bundle_state
    # If any metric is unavailable or any row is unmatched/ineligible -> diagnostic_incomplete
    has_unavailable = any(m.status != "descriptive_only" for m in all_metrics)
    has_unmatched = any(r.match_status != "matched" for r in updated_denominator)
    bundle_state = (
        "protocol_executed_complete"
        if (not has_unavailable and not has_unmatched and len(all_metrics) > 0)
        else "diagnostic_incomplete"
    )

    # 5. Atomically write diagnostic bundle
    write_diagnostic_bundle(
        output_root=output_root,
        verified_c=verified_c,
        verified_market=verified_market,
        denominator_rows=updated_denominator,
        diagnostic_metrics=all_metrics,
        bundle_state=bundle_state,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
