from __future__ import annotations

import argparse
import json
from pathlib import Path

from configs.base import (
    EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT,
    EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID,
    EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID,
    EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS,
    EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS,
)
from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from src.research.extreme_funding_parameter_sensitivity import (
    build_parameter_grid,
    run_candidate_sensitivity,
    run_shadow_sensitivity,
)


def load_basis_rows_jsonl(path: str | Path) -> list[HistoricalBasisRow]:
    rows: list[HistoricalBasisRow] = []
    file_path = Path(path)
    if not file_path.exists():
        return rows
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(HistoricalBasisRow(**json.loads(line)))
    return rows


def _decision_gate_snapshot(candidate_summaries: list[dict], shadow_summaries: list[dict]) -> dict:
    any_candidate = any(item.get("candidate_count", 0) > 0 for item in candidate_summaries)
    conservative_candidates = [
        item
        for item in candidate_summaries
        if item.get("param_set", {}).get("assumption_level") == "conservative_1_interval"
    ]
    conservative_has_candidate = any(item.get("candidate_count", 0) > 0 for item in conservative_candidates)
    top_reject_reasons = sorted(
        {
            item.get("top_reject_reason")
            for item in candidate_summaries
            if item.get("top_reject_reason") is not None
        }
    )
    best_median_net_pnl_bps = max(
        (item.get("median_net_pnl_bps", 0.0) for item in shadow_summaries),
        default=0.0,
    )

    return {
        "any_candidate": any_candidate,
        "conservative_has_candidate": conservative_has_candidate,
        "best_median_net_pnl_bps": best_median_net_pnl_bps,
        "top_reject_reasons": top_reject_reasons,
    }


def run_parameter_sensitivity_audit(
    *,
    input_path: str | Path,
    output_dir: str | Path,
    tag: str,
) -> dict[str, Path]:
    rows = load_basis_rows_jsonl(input_path)
    param_sets = build_parameter_grid(
        annualized_grid=EXTREME_FUNDING_SENSITIVITY_ANNUALIZED_GRID_PCT,
        min_income_grid=EXTREME_FUNDING_SENSITIVITY_MIN_INCOME_GRID_BPS,
        max_slippage_grid=EXTREME_FUNDING_SENSITIVITY_MAX_SLIPPAGE_GRID_BPS,
        expected_intervals_grid=EXTREME_FUNDING_SENSITIVITY_EXPECTED_INTERVAL_GRID,
        basis_absorption_grid=EXTREME_FUNDING_SENSITIVITY_BASIS_ABSORPTION_GRID,
    )

    candidate_summaries = run_candidate_sensitivity(rows, param_sets)
    shadow_summaries = run_shadow_sensitivity(rows, candidate_summaries)

    status = "ok" if rows else "insufficient_basis_data"
    coverage_quality = (
        "historical_basis_proxy_not_depth_aware" if rows else "insufficient_basis_data"
    )

    candidate_output_payload = {
        "status": status,
        "coverage_quality": coverage_quality,
        "depth_aware": False,
        "input_row_count": len(rows),
        "param_set_count": len(param_sets),
        "candidate_summaries": candidate_summaries,
        "decision_gate_snapshot": _decision_gate_snapshot(candidate_summaries, shadow_summaries),
    }

    shadow_output_payload = {
        "status": status,
        "coverage_quality": coverage_quality,
        "depth_aware": False,
        "input_row_count": len(rows),
        "param_set_count": len(param_sets),
        "shadow_summaries": shadow_summaries,
        "decision_gate_snapshot": _decision_gate_snapshot(candidate_summaries, shadow_summaries),
    }

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    candidate_output = output_root / f"{tag}_sensitivity_candidate_summary.json"
    shadow_output = output_root / f"{tag}_sensitivity_shadow_summary.json"

    candidate_output.write_text(
        json.dumps(candidate_output_payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    shadow_output.write_text(
        json.dumps(shadow_output_payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    return {
        "candidate_output": candidate_output,
        "shadow_output": shadow_output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit extreme funding parameter sensitivity before orderbook-aware replay.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    outputs = run_parameter_sensitivity_audit(
        input_path=args.input,
        output_dir=args.output_dir,
        tag=args.tag,
    )

    candidate_summary = json.loads(outputs["candidate_output"].read_text(encoding="utf-8"))
    shadow_summary = json.loads(outputs["shadow_output"].read_text(encoding="utf-8"))

    print(
        json.dumps(
            {
                "candidate_output": str(outputs["candidate_output"]),
                "shadow_output": str(outputs["shadow_output"]),
                "status": candidate_summary["status"],
                "param_set_count": candidate_summary["param_set_count"],
                "input_row_count": candidate_summary["input_row_count"],
                "decision_gate_snapshot": candidate_summary["decision_gate_snapshot"],
                "top_shadow_snapshot": shadow_summary["decision_gate_snapshot"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
