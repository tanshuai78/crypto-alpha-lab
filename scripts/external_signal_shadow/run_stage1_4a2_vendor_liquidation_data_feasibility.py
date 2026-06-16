#!/usr/bin/env python3
"""
scripts/external_signal_shadow/run_stage1_4a2_vendor_liquidation_data_feasibility.py
"""
import argparse
import json
import sys
from pathlib import Path

from research.external_signal_shadow.stage1_4a2_vendor import (
    audit_vendor_sample_file,
    build_vendor_feasibility_summary,
    get_highest_data_quality_vendor,
    load_vendor_audits_json,
)


def main(argv: list[str] = None) -> int:
    parser = argparse.ArgumentParser(description="Stage 1.4A.2 Vendor Feasibility Auditor")
    parser.add_argument("--vendor-audits", required=True, help="Path to vendor audits JSON")
    parser.add_argument("--output-summary", required=True, help="Path to output summary JSON")
    parser.add_argument(
        "--sample-dir",
        default="data/external_signal_shadow/vendor_liquidation_samples",
        help="Root directory for vendor liquidation sample files",
    )

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    output_path = Path(args.output_summary)
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load audits
    try:
        audits = load_vendor_audits_json(args.vendor_audits)
    except Exception:
        # Write failure summary and return non-zero
        failure_summary = {
            "decision": "vendor_liquidation_source_unavailable",
            "primary_blocker": "vendor_audit_input_missing_or_invalid",
            "purchase_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "alpha_interpretation_allowed": False,
            "stage1_4b_candidate_replay_allowed": False,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(failure_summary, f, indent=2, sort_keys=True)
        return 1

    # Build base summary
    summary = build_vendor_feasibility_summary(audits)
    audit_map = {a.vendor: a for a in audits}

    # Perform runtime sample validation
    for dec_dict in summary["vendor_decisions"]:
        vendor = dec_dict["vendor"]
        audit = audit_map[vendor]
        if audit.sample_file_available:
            file_blocker = None
            if not audit.sample_file_path:
                file_blocker = "sample_file_not_verified"
            else:
                file_path = Path(audit.sample_file_path)
                if not file_path.exists():
                    file_blocker = "sample_file_not_verified"
                else:
                    resolved_sample_dir = Path(args.sample_dir).resolve()
                    resolved_file_path = file_path.resolve()
                    try:
                        resolved_file_path.relative_to(resolved_sample_dir)
                        is_under = True
                    except ValueError:
                        is_under = False

                    if not is_under:
                        file_blocker = "sample_file_not_under_runtime_vendor_dir"
                    else:
                        try:
                            sample_audit = audit_vendor_sample_file(resolved_file_path)
                            has_conflict = False
                            if audit.side_available and not sample_audit["side_available"]:
                                has_conflict = True
                            if audit.notional_usd_available and not sample_audit["notional_usd_available"]:
                                has_conflict = True
                            if audit.symbol_field_available and not sample_audit["symbol_field_available"]:
                                has_conflict = True
                            if audit.timestamp_field_available and not sample_audit["timestamp_field_available"]:
                                has_conflict = True
                            if sample_audit["history_days"] < audit.history_days_verified_from_sample - 0.01:
                                has_conflict = True

                            if has_conflict:
                                file_blocker = "sample_audit_conflict"
                        except Exception:
                            file_blocker = "sample_file_not_verified"

            if file_blocker:
                dec_dict["decision"] = "vendor_liquidation_source_degraded"
                dec_dict["primary_blocker"] = file_blocker
                dec_dict["feasible_for_stage1_4a3_parser"] = False
                if file_blocker == "sample_file_not_verified":
                    dec_dict["next_action"] = "request_sample_or_trial"
                elif file_blocker == "sample_file_not_under_runtime_vendor_dir":
                    dec_dict["next_action"] = "move_sample_file_to_gitignored_dir"
                elif file_blocker == "sample_audit_conflict":
                    dec_dict["next_action"] = "verify_sample_fields_and_update_audit_json"

    # Re-calculate summary level decisions
    feasible_decisions = [d for d in summary["vendor_decisions"] if d["feasible_for_stage1_4a3_parser"]]
    summary["feasible_vendor_count"] = len(feasible_decisions)

    if len(feasible_decisions) > 0:
        summary["decision"] = "vendor_liquidation_source_feasible"
        summary["primary_blocker"] = None
        summary["next_action"] = "write_stage1_4a3_vendor_sample_parser_plan"
        summary["best_vendor"] = feasible_decisions[0]["vendor"]

        summary["lowest_cost_usable_vendor"] = None
        for d in feasible_decisions:
            a = audit_map[d["vendor"]]
            if a.cost_tier in {"free", "low"}:
                summary["lowest_cost_usable_vendor"] = d["vendor"]
                break

        feasible_audit_objs = [audit_map[d["vendor"]] for d in feasible_decisions]
        summary["highest_data_quality_vendor"] = get_highest_data_quality_vendor(feasible_audit_objs)
    else:
        summary["decision"] = "vendor_liquidation_source_degraded"
        summary["best_vendor"] = None
        summary["lowest_cost_usable_vendor"] = None
        summary["highest_data_quality_vendor"] = None

        first_dec = summary["vendor_decisions"][0] if summary["vendor_decisions"] else None
        if first_dec:
            summary["primary_blocker"] = first_dec["primary_blocker"]
            if first_dec["primary_blocker"] == "user_cost_decision_required":
                summary["next_action"] = "user_cost_decision_required"
            else:
                summary["next_action"] = first_dec["next_action"]
        else:
            summary["primary_blocker"] = "no_feasible_vendor_sample"
            summary["next_action"] = "request_sample_or_trial_from_top_ranked_vendor_or_continue_live_collection"

    # Output summary JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
