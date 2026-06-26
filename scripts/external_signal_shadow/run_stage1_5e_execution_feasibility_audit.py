import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from configs import base
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_client import (
    build_depth_url,
    fetch_public_json,
)
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_depth import (
    compute_depth_metrics,
    load_historical_depth_snapshots,
    normalize_depth_timestamp_fields,
)
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_loader import (
    load_promising_12h_long_attention_candidates,
    validate_stage1_5e_upstream_evidence,
)
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_models import (
    ExecutionFeasibilityCandidate,
)
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_proxy import (
    compute_entry_proxy_metrics,
)
from src.research.external_signal_shadow.stage1_5e_execution_feasibility_summary import (
    build_execution_feasibility_summary,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 1.5E Execution Feasibility Data Audit Runner")
    parser.add_argument("--stage1-5c-summary", help="Path to Stage 1.5C summary JSON")
    parser.add_argument("--stage1-5c1-summary", help="Path to Stage 1.5C.1 summary JSON")
    parser.add_argument("--candidates-jsonl", help="Path to Stage 1.5C candidates JSONL")
    parser.add_argument("--klines-jsonl", help="Path to Stage 1.5C.1 klines JSONL")

    parser.add_argument("--stage1-5d-summary", help="Path to Stage 1.5D summary JSON (optional)")
    parser.add_argument("--stage1-5d-events-jsonl", help="Path to Stage 1.5D live events JSONL (optional)")
    parser.add_argument("--historical-depth-jsonl", help="Path to historical orderbook/depth JSONL (optional)")

    parser.add_argument("--live-public-readonly", action="store_true", help="Enable public readonly depth fetch")
    parser.add_argument("--output-root", help="Root directory for outputs")
    parser.add_argument("--output-summary", required=True, help="Path to write the audit summary JSON")
    parser.add_argument("--fixture-proxy-only", action="store_true", help="Fixture proxy-only mode (skip network/verification)")

    return parser.parse_args()


def map_stage1_5d_dependency_status(decision_value: str) -> str:
    if decision_value == "stage1_5d_smoke_observation_in_progress":
        return "pending"
    if decision_value == "stage1_5d_operational_pass_event_detection_unvalidated":
        return "operational_unvalidated"
    if decision_value == "stage1_5d_event_detection_passed":
        return "event_detection_passed"
    if decision_value in ("stage1_5d_smoke_failed", "stage1_5d_smoke_invalid"):
        return "failed_or_invalid"
    return "unknown"


def extract_live_event_time_ms(event_row: Dict[str, Any]) -> int | None:
    for field in ("announcement_time_ms", "detected_at_ms", "available_at_ms", "source_published_at_ms"):
        value = event_row.get(field)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def main() -> int:
    try:
        args = parse_args()
    except SystemExit as se:
        # If argparse exits due to missing output-summary or similar, return its code
        return se.code

    output_summary_path = Path(args.output_summary)

    # 1. Output folder setup
    output_root = Path(args.output_root) if args.output_root else output_summary_path.parent
    output_root.mkdir(parents=True, exist_ok=True)

    blockers = []

    # Check required options presence
    if not args.stage1_5c_summary or not os.path.exists(args.stage1_5c_summary):
        blockers.append("upstream_evidence_missing_or_invalid")
    if not args.stage1_5c1_summary or not os.path.exists(args.stage1_5c1_summary):
        if "upstream_evidence_missing_or_invalid" not in blockers:
            blockers.append("upstream_evidence_missing_or_invalid")

    if not args.candidates_jsonl or not os.path.exists(args.candidates_jsonl):
        blockers.append("candidates_file_missing")
    if not args.klines_jsonl or not os.path.exists(args.klines_jsonl):
        blockers.append("klines_file_missing")

    # If basic inputs are missing, write invalid summary and return 2
    if blockers:
        logger.error(f"Required inputs validation failed: {blockers}")
        invalid_summary = {
            "decision": "stage1_5e_execution_feasibility_invalid",
            "research_result_valid": False,
            "execution_feasibility_proven": False,
            "historical_orderbook_depth_available": False,
            "historical_proxy_audit_valid": False,
            "live_depth_snapshot_available": False,
            "top_level_unique_symbol_event_count": 0,
            "cell_summaries": {},
            "ready_cells": [],
            "proxy_failed_cells": [],
            "inconclusive_cells": [],
            "candidate_event_days": 0,
            "symbols_with_events": 0,
            "blockers": blockers,
            "allowed_next_action": "none_fix_inputs",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False
        }
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        return 2

    # 2. Validate Upstream Evidence
    upstream_result = validate_stage1_5e_upstream_evidence(args.stage1_5c1_summary, args.stage1_5c_summary)
    if not upstream_result["valid"]:
        logger.error(f"Upstream validation failed: {upstream_result['blockers']}")
        invalid_summary = {
            "decision": "stage1_5e_execution_feasibility_invalid",
            "research_result_valid": False,
            "execution_feasibility_proven": False,
            "historical_orderbook_depth_available": False,
            "historical_proxy_audit_valid": False,
            "live_depth_snapshot_available": False,
            "top_level_unique_symbol_event_count": 0,
            "cell_summaries": {},
            "ready_cells": [],
            "proxy_failed_cells": [],
            "inconclusive_cells": [],
            "candidate_event_days": 0,
            "symbols_with_events": 0,
            "blockers": upstream_result["blockers"],
            "allowed_next_action": "none_fix_upstream",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False
        }
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        return 2

    # 3. Handle live-public-readonly requirements
    if args.live_public_readonly and (not args.stage1_5d_events_jsonl or not os.path.exists(args.stage1_5d_events_jsonl)):
        logger.error("Stage 1.5D events JSONL is required when live_public_readonly is enabled.")
        invalid_summary = {
            "decision": "stage1_5e_execution_feasibility_invalid",
            "research_result_valid": False,
            "execution_feasibility_proven": False,
            "historical_orderbook_depth_available": False,
            "historical_proxy_audit_valid": False,
            "live_depth_snapshot_available": False,
            "top_level_unique_symbol_event_count": 0,
            "cell_summaries": {},
            "ready_cells": [],
            "proxy_failed_cells": [],
            "inconclusive_cells": [],
            "candidate_event_days": 0,
            "symbols_with_events": 0,
            "blockers": ["stage1_5d_events_required_for_live_depth"],
            "allowed_next_action": "none_provide_stage1_5d_events",
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "execution_engine_allowed": False,
            "alpha_interpretation_allowed": False
        }
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(invalid_summary, f, indent=2)
        return 2

    # 4. Load promising candidates
    candidates = load_promising_12h_long_attention_candidates(args.candidates_jsonl)

    # 5. Load and index klines
    # Klines file contains 15m bars for candidate symbols
    klines_by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    klines_path = Path(args.klines_jsonl)
    if klines_path.exists():
        with open(klines_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    bar = json.loads(line)
                    sym = bar.get("symbol")
                    if sym:
                        klines_by_symbol.setdefault(sym, []).append(bar)
                except Exception:
                    continue

    # 6. Compute historical kline proxy metrics
    proxy_rows = []
    for cand in candidates:
        symbol = cand.get("symbol")
        entry_time_ms = cand.get("entry_time_ms")
        bars = klines_by_symbol.get(symbol, [])

        metrics = compute_entry_proxy_metrics(symbol, entry_time_ms, bars)

        # Merge candidate info
        merged = {**cand, **metrics}
        proxy_rows.append(merged)

    # Write historical proxy rows
    proxy_output_path = output_root / "historical_execution_proxy_audit.jsonl"
    with open(proxy_output_path, "w", encoding="utf-8") as f:
        for p in proxy_rows:
            f.write(json.dumps(p) + "\n")

    # 7. Check Stage 1.5D dependency status
    stage1_5d_status = "pending"
    d_summary_path = args.stage1_5d_summary
    if not d_summary_path:
        # Check default path
        default_d_path = Path("data/external_signal_shadow/stage1_5d/live_event_source_smoke/binance_futures_launch_smoke_summary.json")
        if default_d_path.exists():
            d_summary_path = str(default_d_path)

    if d_summary_path and os.path.exists(d_summary_path):
        try:
            with open(d_summary_path, "r", encoding="utf-8") as f:
                d_data = json.load(f)
            stage1_5d_status = map_stage1_5d_dependency_status(d_data.get("decision", ""))
        except Exception:
            stage1_5d_status = "pending"

    # 8. Load historical depth if available
    historical_depth_rows = []
    historical_depth_coverage = {
        "historical_orderbook_depth_available": False,
        "matched_snapshot_count": 0,
        "matched_candidate_event_count": 0,
        "coverage_reject_reason": "historical_orderbook_depth_path_not_provided",
    }
    if args.historical_depth_jsonl and os.path.exists(args.historical_depth_jsonl):
        historical_depth_result = load_historical_depth_snapshots(
            args.historical_depth_jsonl,
            candidates,
            match_window_ms=base.EXTERNAL_SIGNAL_STAGE1_5E_HISTORICAL_DEPTH_MATCH_WINDOW_MS,
            notional_usdt=base.EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_NOTIONAL_USDT,
        )
        historical_depth_rows = historical_depth_result["depth_rows"]
        historical_depth_coverage = historical_depth_result["coverage"]

    historical_depth_output_path = output_root / "historical_orderbook_depth_audit.jsonl"
    with open(historical_depth_output_path, "w", encoding="utf-8") as f:
        for row in historical_depth_rows:
            f.write(json.dumps(row) + "\n")

    # 9. Handle live depth snapshots
    live_depth_rows = []
    request_manifest_rows = []

    if args.live_public_readonly:
        # Load live events from 1.5D
        live_events = []
        with open(args.stage1_5d_events_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    live_events.append(row)
                except Exception:
                    continue

        now_ms = int(time.time() * 1000)
        request_count = 0
        max_requests = base.EXTERNAL_SIGNAL_STAGE1_5E_MAX_PUBLIC_REQUESTS_PER_RUN

        for ev in live_events:
            if request_count >= max_requests:
                logger.warning(f"Reached request budget threshold of {max_requests}")
                break

            symbol = ev.get("symbol")
            ann_time_ms = extract_live_event_time_ms(ev)
            if ann_time_ms is None:
                request_manifest_rows.append({
                    "symbol": symbol,
                    "fetched_at_ms": int(time.time() * 1000),
                    "status": "skipped",
                    "error": "live_event_timestamp_missing",
                })
                continue
            age_ms = now_ms - ann_time_ms

            # Check maximum age
            max_age_ms = base.EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_OBSERVATION_MAX_EVENT_AGE_MS
            if age_ms <= max_age_ms:
                url = build_depth_url(symbol, limit=100)

                # Write to manifest
                manifest_row = {
                    "symbol": symbol,
                    "url": url,
                    "fetched_at_ms": int(time.time() * 1000),
                    "status": "pending"
                }

                # Fetch
                request_count += 1
                logger.info(f"Fetching public depth for {symbol}")
                res = fetch_public_json(url, live_public_readonly=True)

                manifest_row["fetched_at_ms"] = int(time.time() * 1000)

                if res["ok"]:
                    manifest_row["status"] = "success"
                    orderbook = res["data"]

                    depth_metrics = compute_depth_metrics(orderbook, notional_usdt=base.EXTERNAL_SIGNAL_STAGE1_5E_LIVE_DEPTH_NOTIONAL_USDT)
                    ts_metrics = normalize_depth_timestamp_fields(orderbook, fetched_at_ms=manifest_row["fetched_at_ms"])

                    merged_depth = {
                        "symbol": symbol,
                        "event_type": ev.get("event_type"),
                        **depth_metrics,
                        **ts_metrics
                    }
                    live_depth_rows.append(merged_depth)
                else:
                    manifest_row["status"] = "failed"
                    manifest_row["error"] = res.get("error")

                request_manifest_rows.append(manifest_row)
                time.sleep(base.EXTERNAL_SIGNAL_STAGE1_5E_REQUEST_SLEEP_SEC)

        # Write request manifest
        manifest_output_path = output_root / "request_manifest.jsonl"
        with open(manifest_output_path, "w", encoding="utf-8") as f:
            for r in request_manifest_rows:
                f.write(json.dumps(r) + "\n")

        # Write live depth snapshots
        live_depth_output_path = output_root / "live_depth_snapshots.jsonl"
        with open(live_depth_output_path, "w", encoding="utf-8") as f:
            for d in live_depth_rows:
                f.write(json.dumps(d) + "\n")

    # 10. Build summary decision
    summary = build_execution_feasibility_summary(
        upstream_valid=True,
        candidate_rows=candidates,
        proxy_rows=proxy_rows,
        live_depth_rows=live_depth_rows,
        historical_orderbook_depth_available=historical_depth_coverage.get("historical_orderbook_depth_available", False),
        historical_depth_rows=historical_depth_rows,
        historical_depth_coverage=historical_depth_coverage,
        request_manifest_rows=request_manifest_rows,
        stage1_5d_dependency_status=stage1_5d_status
    )

    # Write candidates file
    candidates_output_path = output_root / "execution_feasibility_candidates.jsonl"
    with open(candidates_output_path, "w", encoding="utf-8") as f:
        for cand in candidates:
            # Wrap as model dict
            cand_obj = ExecutionFeasibilityCandidate(
                symbol=cand["symbol"],
                symbol_event_id=cand["symbol_event_id"],
                event_type=cand["event_type"],
                signed_mode=cand["signed_mode"],
                entry_delay_hours=cand["entry_delay_hours"],
                filter_group=cand["filter_group"],
                entry_time_ms=cand["entry_time_ms"]
            )
            f.write(json.dumps(cand_obj.to_dict()) + "\n")

    # Write summary output
    with open(output_summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Stage 1.5E feasibility audit complete. Decision: {summary['decision']}")

    # Return code logic
    if summary["decision"] == "stage1_5e_execution_feasibility_proxy_failed":
        return 1
    elif summary["decision"] == "stage1_5e_execution_feasibility_invalid":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
