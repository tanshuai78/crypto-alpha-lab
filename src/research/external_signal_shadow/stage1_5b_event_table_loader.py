import json
from pathlib import Path
from typing import Any, Dict, List, Set

from configs import base


def load_high_confidence_candidate_rows(path: str | Path) -> List[Dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_idx}: {exc}")

            # Required fields check
            if "manual_review_status" not in row:
                raise ValueError(f"Line {line_idx}: missing manual_review_status")
            if row["manual_review_status"] != "reviewed_high_confidence":
                raise ValueError(
                    f"Line {line_idx}: manual_review_status must be 'reviewed_high_confidence', got {row['manual_review_status']!r}"
                )

            if "manual_review_required" not in row:
                raise ValueError(f"Line {line_idx}: missing manual_review_required")
            if not row["manual_review_required"]:
                raise ValueError(f"Line {line_idx}: manual_review_required must be true")

            if "source_name" not in row:
                raise ValueError(f"Line {line_idx}: missing source_name")
            if row["source_name"] != "binance_official_announcements":
                raise ValueError(
                    f"Line {line_idx}: source_name must be 'binance_official_announcements', got {row['source_name']!r}"
                )

            for field in ("time", "url", "source_url", "title", "symbol"):
                if field not in row:
                    raise ValueError(f"Line {line_idx}: missing required field {field!r}")

            # Forbidden input safety check
            forbidden_keys = {
                "replay_allowed",
                "paper_trading_allowed",
                "live_trading_allowed",
                "execution_engine_allowed",
            }
            found_forbidden = forbidden_keys.intersection(row.keys())
            if found_forbidden:
                raise ValueError(
                    f"Line {line_idx}: payload contains forbidden keys: {found_forbidden}"
                )

            rows.append(row)

    return rows


def assert_stage1_5a_audit_passed(summary_path: str | Path) -> Set[str]:
    summary_path = Path(summary_path)
    if not summary_path.exists():
        raise FileNotFoundError(f"Stage 1.5A summary not found: {summary_path}")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    if summary.get("overall_decision") != "source_audit_passed":
        raise ValueError(
            f"Stage 1.5A overall_decision is not 'source_audit_passed': {summary.get('overall_decision')!r}"
        )

    if not summary.get("research_result_valid", False):
        raise ValueError("Stage 1.5A research_result_valid is not True")

    config_allowed = set(base.EXTERNAL_SIGNAL_STAGE1_5B_ALLOWED_EVENT_TYPES)

    source_recommended = set()
    for src_key, src_data in summary.get("source_decisions", {}).items():
        if src_data.get("decision") == "source_audit_passed":
            source_recommended.update(src_data.get("recommended_event_types_for_stage1_5b", []))

    event_types_passed = set()
    for et, decision in summary.get("event_type_decisions", {}).items():
        if decision == "source_audit_passed":
            event_types_passed.add(et)

    allowed = config_allowed.intersection(source_recommended).intersection(event_types_passed)
    return allowed
