from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
import sys
from typing import Any

import configs.base as base
from research.external_signal_shadow.stage1_4a_lq30_aggregation import (
    aggregate_forceorder_windows,
    build_density_report,
    build_imbalance_distribution,
    compute_concentration_stats,
)
from research.external_signal_shadow.stage1_4a_lq30_forceorder import (
    load_forceorder_jsonl_files,
    parse_forceorder_rows,
)
from research.external_signal_shadow.stage1_4a_lq30_overlap import compute_overlap_reports
from research.external_signal_shadow.stage1_4a_lq30_summary import (
    build_source_quality_report,
    evaluate_lq30_summary,
)


def load_jsonl_rows(path_or_glob: str | None) -> list[dict[str, Any]]:
    if not path_or_glob:
        return []
    resolved = glob.glob(path_or_glob)
    rows = []
    for p in sorted(resolved):
        if not os.path.exists(p):
            continue
        open_func = gzip.open if p.endswith(".gz") else open
        with open_func(p, "rt", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rows.append(json.loads(stripped))
                except Exception:
                    continue
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LQ30 Local ForceOrder Snapshot Diagnostic Runner")
    parser.add_argument("--local-force-order-archive", required=True, help="Path or glob to forceOrder JSONL files")
    parser.add_argument("--funding-archive", help="Path or glob to funding JSONL files (optional)")
    parser.add_argument("--oi-archive", help="Path or glob to Open Interest JSONL files (optional)")
    parser.add_argument("--price-archive", help="Path or glob to price/kline JSONL files (optional)")
    parser.add_argument("--output-summary", required=True, help="Path to write JSON summary output")

    args = parser.parse_args(argv)

    expected_symbols = set(base.EXTERNAL_SIGNAL_STAGE1_4_SYMBOLS)

    # 1. Load force orders
    loader_stats = load_forceorder_jsonl_files([args.local_force_order_archive])

    # 2. Parse force order rows
    parse_result = parse_forceorder_rows(loader_stats["loaded_rows"], expected_symbols)
    parsed_rows = parse_result["rows"]

    # 3. Aggregate windows
    windows_15m = aggregate_forceorder_windows(
        parsed_rows,
        bucket_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_15M_MS,
        configured_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_CONFIGURED_LAG_MS,
    )
    windows_1h = aggregate_forceorder_windows(
        parsed_rows,
        bucket_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_1H_MS,
        configured_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_CONFIGURED_LAG_MS,
    )

    # 4. Compute concentration
    concentration_report = compute_concentration_stats(windows_15m)

    # 5. Build reports
    density_report = build_density_report(parsed_rows, windows_15m)
    imbalance_report = build_imbalance_distribution(windows_15m, windows_1h)
    source_quality_report = build_source_quality_report(
        loader_stats,
        parsed_rows,
        expected_symbols,
        parse_result,
    )

    # 6. Load optional overlap datasets and compute overlap
    has_alignment = bool(args.funding_archive and args.oi_archive and args.price_archive)
    if has_alignment:
        funding_rows = load_jsonl_rows(args.funding_archive)
        oi_rows = load_jsonl_rows(args.oi_archive)
        price_rows = load_jsonl_rows(args.price_archive)

        overlap_report = compute_overlap_reports(
            liq_windows=windows_15m,
            funding_rows=funding_rows,
            oi_rows=oi_rows,
            price_rows=price_rows,
            funding_publish_lag_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_FUNDING_PUBLISH_LAG_MS,
            max_oi_staleness_ms=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_OI_STALENESS_MS,
            min_abs_funding_rate_preview=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_FUNDING_RATE_PREVIEW,
            min_abs_oi_change_ratio_preview=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_OI_CHANGE_RATIO_PREVIEW,
            min_abs_price_return_1h_preview=base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_PRICE_RETURN_1H_PREVIEW,
        )
    else:
        overlap_report = {
            "alignment_overlap_available": False,
            "data_alignment_overlap_window_count_15m": 0,
            "stress_condition_overlap_window_count_15m": 0,
            "data_alignment_overlap_event_days": 0,
            "stress_condition_overlap_event_days": 0,
            "symbols_with_alignment_overlap": 0,
            "alignment_policy": {
                "funding": "asof_latest_before_bucket_end_minus_lag",
                "oi": "asof_latest_before_bucket_end_with_staleness_limit",
                "price": "bucket_exact_or_covering"
            }
        }

    # 7. Evaluate summary
    summary = evaluate_lq30_summary(
        density_report=density_report,
        overlap_report=overlap_report,
        concentration_report=concentration_report,
        source_quality_report=source_quality_report,
    )

    full_summary = {
        **summary,
        "density_report": density_report,
        "overlap_report": overlap_report,
        "imbalance_distribution": imbalance_report,
        "source_quality_report": source_quality_report,
    }

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.output_summary)), exist_ok=True)
    with open(args.output_summary, "w", encoding="utf-8") as f:
        json.dump(full_summary, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
