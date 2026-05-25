from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from src.research.extreme_funding_basis_replay import HistoricalBasisRow
from src.strategies.extreme_funding.candidate_builder import build_extreme_funding_candidate


def load_basis_rows_jsonl(path: str | Path) -> list[HistoricalBasisRow]:
    rows: list[HistoricalBasisRow] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(HistoricalBasisRow(**json.loads(line)))
    return rows


def build_basis_aware_candidate_summary(rows: list[HistoricalBasisRow]) -> dict:
    reject_counts: Counter[str] = Counter()
    candidate_count = 0
    for row in rows:
        decision = build_extreme_funding_candidate(row.to_candidate_row())
        if decision.accepted:
            candidate_count += 1
        else:
            reject_counts[decision.reject_reason or "unknown_reject"] += 1
    return {
        "input_row_count": len(rows),
        "candidate_count": candidate_count,
        "reject_reason_counts": dict(sorted(reject_counts.items())),
        "coverage_quality": (
            "historical_basis_proxy_not_depth_aware"
            if rows
            else "insufficient_basis_data"
        ),
        "depth_aware": False,
        "depth_source": "static_min_capacity_proxy" if rows else None,
        "status": "ok" if rows else "insufficient_basis_data",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay basis-aware extreme funding candidates.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = load_basis_rows_jsonl(args.input)
    summary = build_basis_aware_candidate_summary(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
