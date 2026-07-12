# Stage 1.5H Read-Only Report Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. For every code task, use TDD: write the failing test, verify it fails, implement the minimal code, then re-run the targeted tests.

**Goal:** Implement a strictly read-only Stage 1.5H single-event static execution proxy report generator that consumes audited Stage 1.5G artifacts and writes JSON/Markdown reports without producing signals, order intents, execution claims, or paper/live readiness.

**Architecture:** Add a new downstream-only Stage 1.5H module and CLI. The module reads Stage 1.5G review/quarantine/depth-quality artifacts, validates governance approval and safety flags, computes only static proxy summary, availability discount, friction floor, and required next evidence, then writes a single-event fixture-bound report. It never recomputes or overrides Stage 1.5G decisions and never reads exchange/private/order endpoints.

**Tech Stack:** Python stdlib, `configs/base.py`, existing Stage 1.5G JSON/JSONL artifacts, pytest, JSON/Markdown outputs.

## Global Constraints

```text
implementation_plan_scope = single_event_fixture_bound_report_generator
implementation_allowed_by_this_plan = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
event_family_conclusion_allowed = false
multi_event_aggregation_allowed = false
cross_event_generalization_allowed = false
```

This plan may only be executed after explicit user approval. Even after execution, the resulting code may only generate offline read-only reports.

Forbidden outputs and concepts:

```text
SignalCandidate
TradeIntent
buy/sell instruction
entry recommendation
position size recommendation
virtual_order
hypothetical_trade
entry_exit_path
fill_probability
order_lifecycle_state_machine
pnl_path
paper/live readiness
alpha confirmed claim
execution feasibility proven claim
```

Allowed calculations only:

```text
static_proxy_metric
availability_discount
friction_floor
required_next_evidence
```

Upstream source of truth:

```text
1.5G decision is source-of-truth.
1.5H must not recompute, override, or promote Stage 1.5G decisions.
```

---

## File Structure

Create:

```text
src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py
scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py
tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py
tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py
```

Modify:

```text
configs/base.py
docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md \
  docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
```

Responsibilities:

```text
configs/base.py:
  Own all Stage 1.5H thresholds. No magic numbers in src/ or scripts/.

stage1_5h_read_only_report_generator.py:
  Load local artifacts, validate governance and Stage 1.5G inputs, compute report summary, render Chinese Markdown.

review_stage1_5h_static_execution_proxy_report.py:
  CLI wrapper. Reads paths, calls module, writes JSON and Markdown, exits non-zero only for missing input or blocker conditions.

test_stage1_5h_read_only_report_generator_config.py:
  Verifies constants exist and remain observation-only/read-only.

test_stage1_5h_read_only_report_generator.py:
  Verifies input validation, safety flags, artifact mismatch handling, and computed report semantics.

test_review_stage1_5h_static_execution_proxy_report.py:
  Verifies CLI writes expected artifacts and refuses invalid inputs.
```

---

## Task 1: Add Stage 1.5H Config Constants

**Files:**
- Modify: `configs/base.py`
- Create: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py`

**Interfaces:**
- Consumes: existing `configs.base`
- Produces: `EXTERNAL_SIGNAL_STAGE1_5H_*` constants used by Task 4 report calculations

- [ ] **Step 1: Write the failing config tests**

Create `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py`:

```python
from configs import base


def test_stage1_5h_config_constants_exist_and_are_safe():
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS == 10.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05 == 5_000.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05 == 5_000.0
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO == 0.98
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS == 50.0
    # Reserved for a future event-family gate. Stage 1.5H v1 must not consume this value.
    assert base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_EVENT_FAMILY_SAMPLE_REQUIRED == 3


def test_stage1_5h_config_does_not_enable_trading():
    assert getattr(base, "RISK_LIVE_TRADING_ENABLED", False) is False
    assert not hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5H_PAPER_TRADING_ENABLED")
    assert not hasattr(base, "EXTERNAL_SIGNAL_STAGE1_5H_LIVE_TRADING_ENABLED")
```

- [ ] **Step 2: Run the failing config tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py \
  -q
```

Expected: FAIL because the `EXTERNAL_SIGNAL_STAGE1_5H_*` constants do not exist.

- [ ] **Step 3: Add constants to `configs/base.py`**

Add near the External Signal Shadow Lab section or create a clearly labeled Stage 1.5H section:

```python
# ─── External Signal Shadow Lab: Stage 1.5H Read-Only Static Proxy ─────────────

EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS = 10.0
# Maximum p95 spread for static proxy reporting. Report blocker only; never enables trading.

EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS = 10.0
# Maximum p95 estimated buy-side 500 USDT slippage for report health classification.

EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS = 10.0
# Maximum p95 estimated sell-side 500 USDT slippage for report health classification.

EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05 = 5_000.0
# Minimum p05 top bid depth. This is a report quality threshold, not a sizing rule.

EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05 = 5_000.0
# Minimum p05 top ask depth. This is a report quality threshold, not a sizing rule.

EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO = 0.98
# Minimum valid-book availability ratio for a quarantined single-event static proxy report.

EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS = 15 * 60 * 1000
# Maximum first-valid-book latency before the report must mark launch warmup as not usable.

EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS = 50.0
# Conservative round-trip cost floor. Do not add this to observed slippage; use max(floor, observed).

EXTERNAL_SIGNAL_STAGE1_5H_MIN_EVENT_FAMILY_SAMPLE_REQUIRED = 3
# Minimum clean/quarantined independent events before any future event-family report design is allowed.
```

- [ ] **Step 4: Re-run the config tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add configs/base.py tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py
git commit -m "config: add stage1 5h read-only report thresholds"
```

---

## Task 2: Build Artifact Loader And Governance Validation

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Create/modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Interfaces:**
- Produces dataclass:

```python
@dataclass(frozen=True)
class Stage1_5HInputBundle:
    stage1_5g_summary: dict[str, Any]
    quarantine_summary: dict[str, Any]
    depth_quality_input_rows: list[dict[str, Any]]
    quarantined_invalid_book_rows: list[dict[str, Any]]
    governance_review_path: Path
    governance_review_text: str
    loader_blockers: list[str]
    loader_warnings: list[str]
```

- Produces functions:

```python
load_stage1_5h_inputs(...) -> Stage1_5HInputBundle
validate_stage1_5h_governance(bundle: Stage1_5HInputBundle) -> dict[str, Any]
```

Runtime semantics are intentionally narrower than the governance review:

```text
governance_plan_admission_confirmed = true
report_generation_allowed = true
implementation_plan_allowed = false
implementation_allowed = false
```

`implementation_plan_allowed = true` must only appear in the governance review artifact, not in the generated Stage 1.5H report summary.

- [ ] **Step 1: Write failing loader and governance tests**

Create `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py` with this shared fixture and tests:

```python
import json
from pathlib import Path

from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    load_stage1_5h_inputs,
    validate_stage1_5h_governance,
)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    return path


def governance_review_text() -> str:
    return "\n".join([
        "approval_owner = human_research_owner",
        "approval_artifact = docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md",
        "governance_approval_must_be_explicit = true",
        "governance_decision = read_only_report_generator_plan_allowed_with_constraints",
        "allowed_next_action = write_read_only_report_generator_implementation_plan",
        "implementation_plan_allowed = true",
        "implementation_allowed = false",
        "scope = single_event_fixture_bound_report_generator",
        "event_family_conclusion_allowed = false",
        "multi_event_aggregation_allowed = false",
        "execution_feasibility_claim_allowed = false",
    ]) + "\n"


def make_stage1_5h_fixture(tmp_path: Path):
    root = tmp_path / "stage1_5g" / "reviews" / "run1"
    summary = {
        "decision": "stage1_5g_depth_evidence_quarantined_pass",
        "allowed_next_action": "write_stage1_5h_design_only",
        "clean_depth_evidence_pass": False,
        "quarantined_depth_evidence_pass": True,
        "quarantine_candidate": True,
        "formal_announcement_and_launch_count": 1,
        "execution_feasibility_claim_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "alpha_interpretation_allowed": False,
        "event_family_conclusion_allowed": False,
        "cross_event_generalization_allowed": False,
        "blockers": [],
        "warnings": ["summary_level_warning_to_preserve"],
        "clean_pass_missing_reason": [
            "upstream_reason_first",
            "invalid_book_present",
            "observation_initial_empty_book_present",
            "midrun_empty_book_present",
            "launch_time_missing_warmup_anchor_degraded",
        ],
        "quarantine": {
            "blockers": [],
            "warnings": ["launch_time_missing_warmup_anchor_degraded"],
            "clean_depth_evidence_pass": False,
            "quarantined_depth_evidence_pass": True,
            "quarantine_candidate": True,
            "observed_snapshot_count": 718,
            "expected_snapshot_count": 720,
            "invalid_book_row_count": 12,
            "invalid_book_ratio_observed": 0.016713091922005572,
            "valid_snapshot_count_after_quarantine": 706,
            "book_availability_ratio": 0.9805555555555555,
            "book_unavailable_ratio": 0.016666666666666666,
            "invalid_book_by_phase": {"observation_initial": 11, "midrun": 1, "launch_warmup": 0},
            "invalid_book_by_reason": {
                "observation_initial_empty_book": 11,
                "midrun_empty_book": 1,
                "crossed_or_negative_book": 0,
                "schema_invalid": 0,
            },
            "max_consecutive_invalid": 11,
            "max_consecutive_invalid_after_warmup": 1,
            "first_valid_book_latency_ms": 661950,
            "depth_quality_input_row_count": 706,
            "quarantined_invalid_book_row_count": 12,
        },
        "depth_quality": {
            "depth_quality_clean_mode_available": False,
            "depth_quality_quarantined_mode_available": True,
            "depth_quality_input_mode": "quarantined_valid_rows",
            "depth_quality_input_row_count": 706,
            "excluded_invalid_book_row_count": 12,
            "quarantined_depth_quality": {
                "spread_bps_p50": 1.1712687779075193,
                "spread_bps_p95": 2.948591635308917,
                "buy_slippage_bps_500usdt_p50": 0.874380647784001,
                "buy_slippage_bps_500usdt_p95": 2.050259958923384,
                "sell_slippage_bps_500usdt_p50": 0.8679232830582917,
                "sell_slippage_bps_500usdt_p95": 1.8699513715880745,
                "top_bid_depth_usdt_p05": 49704.083725000004,
                "top_ask_depth_usdt_p05": 50671.400125,
                "healthy_window_ratio": 1.0,
                "input_valid_rows": 706,
                "excluded_invalid_rows": 12,
                "blockers": [],
                "warnings": [],
            },
        },
    }
    quarantine = dict(summary["quarantine"])
    summary_path = write_json(root / "stage1_5g_live_depth_evidence_review_summary.json", summary)
    quarantine_path = write_json(root / "stage1_5g_quarantine_summary.json", quarantine)
    valid_rows_path = write_jsonl(root / "depth_quality_input_rows.jsonl", [{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "best_bid": 1.0, "best_ask": 1.01} for _ in range(706)])
    invalid_rows_path = write_jsonl(root / "quarantined_invalid_book_rows.jsonl", [{"event_symbol_id": "es1", "symbol": "SKHYUSDT", "depth_status": "invalid"} for _ in range(12)])
    governance_review_path = tmp_path / "docs" / "reviews" / "2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md"
    governance_review_path.parent.mkdir(parents=True, exist_ok=True)
    governance_review_path.write_text(governance_review_text(), encoding="utf-8")
    return summary_path, quarantine_path, valid_rows_path, invalid_rows_path, governance_review_path


def load_fixture_bundle(tmp_path: Path):
    paths = make_stage1_5h_fixture(tmp_path)
    return load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )


def test_load_stage1_5h_inputs_reads_all_required_artifacts(tmp_path):
    bundle = load_fixture_bundle(tmp_path)

    assert bundle.loader_blockers == []
    assert bundle.stage1_5g_summary["decision"] == "stage1_5g_depth_evidence_quarantined_pass"
    assert bundle.quarantine_summary["invalid_book_row_count"] == 12
    assert len(bundle.depth_quality_input_rows) == 706
    assert len(bundle.quarantined_invalid_book_rows) == 12
    assert bundle.governance_review_path.name.endswith("stage1-5h-read-only-report-generator-governance-review_CN.md")
    assert "approval_owner = human_research_owner" in bundle.governance_review_text


def test_governance_validation_requires_explicit_approval(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_missing" in result["blockers"]
    assert result["governance_plan_admission_confirmed"] is False
    assert result["report_generation_allowed"] is False
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_governance_validation_requires_approval_owner_and_artifact(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text(
        "governance_decision = read_only_report_generator_plan_allowed_with_constraints\n"
        "implementation_plan_allowed = true\n"
        "implementation_allowed = false\n",
        encoding="utf-8",
    )
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_owner_missing" in result["blockers"]
    assert "governance_approval_artifact_missing" in result["blockers"]


def test_governance_validation_rejects_generic_text_file_with_matching_decision_only(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    generic = tmp_path / "approval.txt"
    generic.write_text(governance_review_text(), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=generic,
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "governance_approval_artifact_path_invalid" in result["blockers"]
```

- [ ] **Step 2: Run the failing tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_load_stage1_5h_inputs_reads_all_required_artifacts \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_requires_explicit_approval \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_requires_approval_owner_and_artifact \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_rejects_generic_text_file_with_matching_decision_only \
  -q
```

Expected: FAIL because `stage1_5h_read_only_report_generator.py` does not exist.

- [ ] **Step 3: Implement loader and governance validation**

Create `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py` with the loader, safety fields, and governance validation:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Stage1_5HInputBundle:
    stage1_5g_summary: dict[str, Any]
    quarantine_summary: dict[str, Any]
    depth_quality_input_rows: list[dict[str, Any]]
    quarantined_invalid_book_rows: list[dict[str, Any]]
    governance_review_path: Path
    governance_review_text: str
    loader_blockers: list[str]
    loader_warnings: list[str]


def _load_json(path: Path, blocker_name: str, blockers: list[str]) -> dict[str, Any]:
    if not path.exists():
        blockers.append(blocker_name)
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        blockers.append(blocker_name)
        return {}


def _load_jsonl(path: Path, blocker_name: str, blockers: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        blockers.append(blocker_name)
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
    except Exception:
        blockers.append(blocker_name)
        return []
    return rows


def load_stage1_5h_inputs(
    *,
    stage1_5g_summary_path: str | Path,
    quarantine_summary_path: str | Path,
    depth_quality_input_rows_path: str | Path,
    quarantined_invalid_book_rows_path: str | Path,
    governance_review_path: str | Path,
) -> Stage1_5HInputBundle:
    blockers: list[str] = []
    warnings: list[str] = []
    gov_path = Path(governance_review_path)
    governance_text = gov_path.read_text(encoding="utf-8") if gov_path.exists() else ""
    if not governance_text:
        blockers.append("missing_or_unreadable_governance_review")
    return Stage1_5HInputBundle(
        stage1_5g_summary=_load_json(Path(stage1_5g_summary_path), "missing_or_unreadable_stage1_5g_summary", blockers),
        quarantine_summary=_load_json(Path(quarantine_summary_path), "missing_or_unreadable_quarantine_summary", blockers),
        depth_quality_input_rows=_load_jsonl(Path(depth_quality_input_rows_path), "missing_or_unreadable_depth_quality_input_rows", blockers),
        quarantined_invalid_book_rows=_load_jsonl(Path(quarantined_invalid_book_rows_path), "missing_or_unreadable_quarantined_invalid_book_rows", blockers),
        governance_review_path=gov_path,
        governance_review_text=governance_text,
        loader_blockers=blockers,
        loader_warnings=warnings,
    )


def _base_safety_fields() -> dict[str, Any]:
    return {
        "implementation_plan_allowed": False,
        "implementation_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "execution_engine_allowed": False,
        "execution_feasibility_claim_allowed": False,
        "alpha_interpretation_allowed": False,
        "event_family_conclusion_allowed": False,
        "multi_event_aggregation_allowed": False,
        "cross_event_generalization_allowed": False,
    }


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _validate_governance_review(bundle: Stage1_5HInputBundle, blockers: list[str]) -> None:
    text = bundle.governance_review_text
    if bundle.governance_review_path.name != "2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md":
        _append_once(blockers, "governance_approval_artifact_path_invalid")
    required_markers = {
        "governance_approval_missing": "governance_decision = read_only_report_generator_plan_allowed_with_constraints",
        "governance_approval_owner_missing": "approval_owner = human_research_owner",
        "governance_approval_artifact_missing": "approval_artifact = docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md",
        "governance_explicit_approval_missing": "governance_approval_must_be_explicit = true",
        "governance_scope_missing": "scope = single_event_fixture_bound_report_generator",
        "governance_plan_allowed_missing": "implementation_plan_allowed = true",
        "governance_implementation_false_missing": "implementation_allowed = false",
    }
    for blocker, marker in required_markers.items():
        if marker not in text:
            _append_once(blockers, blocker)


def validate_stage1_5h_governance(bundle: Stage1_5HInputBundle) -> dict[str, Any]:
    blockers = list(bundle.loader_blockers)
    warnings = list(bundle.loader_warnings)
    _validate_governance_review(bundle, blockers)
    decision = "stage1_5h_design_only_input_accepted" if not blockers else "stage1_5h_input_rejected"
    return {
        "decision": decision,
        "allowed_next_action": "generate_single_event_read_only_report" if not blockers else "revise_inputs_or_continue_observation",
        "governance_plan_admission_confirmed": bool(not blockers),
        "report_generation_allowed": bool(not blockers),
        "scope": "single_event_fixture_bound_report_generator",
        "blockers": sorted(set(blockers)),
        "warnings": warnings,
        **_base_safety_fields(),
    }
```

- [ ] **Step 4: Re-run targeted tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_load_stage1_5h_inputs_reads_all_required_artifacts \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_requires_explicit_approval \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_requires_approval_owner_and_artifact \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_governance_validation_rejects_generic_text_file_with_matching_decision_only \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
git commit -m "feat: add stage1 5h read-only input governance"
```

---

## Task 3: Enforce Stage 1.5G Source-Of-Truth And Artifact Consistency

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Interfaces:**
- Modify `validate_stage1_5h_governance(bundle)` to validate Stage 1.5G decision, safety flags, clean/quarantined state, row counts, and summary/quarantine value consistency.

- [ ] **Step 1: Add failing validation tests**

Append:

```python

def test_stage1_5h_rejects_invalid_stage1_5g_input(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["decision"] = "stage1_5g_depth_evidence_invalid"
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "invalid_stage1_5g_decision" in result["blockers"]


def test_stage1_5h_rejects_true_execution_or_trading_flags_once(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["paper_trading_allowed"] = True
    summary["live_trading_allowed"] = True
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert result["blockers"].count("unsafe_upstream_flag_true") == 1
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_stage1_5h_rejects_artifact_row_count_mismatch(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[2].write_text('{"event_symbol_id":"es1"}\n', encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]


def test_stage1_5h_rejects_quarantine_summary_value_mismatch(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    quarantine = json.loads(paths[1].read_text(encoding="utf-8"))
    quarantine["book_availability_ratio"] = 1.0
    paths[1].write_text(json.dumps(quarantine), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]


def test_stage1_5h_rejects_depth_quality_input_count_mismatch_between_summary_and_jsonl(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["depth_quality_input_row_count"] = 705
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = validate_stage1_5h_governance(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert "stage1_5h_upstream_artifact_mismatch" in result["blockers"]
```

- [ ] **Step 2: Run failing validation tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_invalid_stage1_5g_input \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_true_execution_or_trading_flags_once \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_artifact_row_count_mismatch \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_quarantine_summary_value_mismatch \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_depth_quality_input_count_mismatch_between_summary_and_jsonl \
  -q
```

Expected: FAIL because detailed validation is not implemented.

- [ ] **Step 3: Implement source-of-truth validation**

Add helpers and call `_validate_stage1_5g_source_of_truth(bundle, blockers)` inside `validate_stage1_5h_governance` before computing `decision`:

```python
UNSAFE_UPSTREAM_FLAGS = (
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "execution_feasibility_claim_allowed",
    "alpha_interpretation_allowed",
)


def _values_equal(left: Any, right: Any) -> bool:
    return left == right


def _validate_quarantine_consistency(summary: dict[str, Any], quarantine: dict[str, Any], blockers: list[str]) -> None:
    embedded = summary.get("quarantine") or {}
    for key in (
        "valid_snapshot_count_after_quarantine",
        "invalid_book_row_count",
        "book_availability_ratio",
        "first_valid_book_latency_ms",
    ):
        if not _values_equal(embedded.get(key), quarantine.get(key)):
            _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")


def _validate_stage1_5g_source_of_truth(bundle: Stage1_5HInputBundle, blockers: list[str]) -> None:
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary
    if summary.get("decision") != "stage1_5g_depth_evidence_quarantined_pass":
        _append_once(blockers, "invalid_stage1_5g_decision")
    if summary.get("clean_depth_evidence_pass") is not False:
        _append_once(blockers, "clean_pass_state_unexpected")
    if summary.get("quarantined_depth_evidence_pass") is not True:
        _append_once(blockers, "quarantined_pass_missing")
    if summary.get("formal_announcement_and_launch_count", 0) < 1:
        _append_once(blockers, "no_formal_announcement_and_launch_evidence")
    for flag in UNSAFE_UPSTREAM_FLAGS:
        if summary.get(flag) is True:
            _append_once(blockers, "unsafe_upstream_flag_true")
    if quarantine.get("blockers") not in ([], None):
        _append_once(blockers, "quarantine_blockers_present")

    _validate_quarantine_consistency(summary, quarantine, blockers)

    expected_valid = int(quarantine.get("valid_snapshot_count_after_quarantine") or -1)
    expected_invalid = int(quarantine.get("quarantined_invalid_book_row_count") or quarantine.get("invalid_book_row_count") or -1)
    summary_depth_count = int((summary.get("depth_quality") or {}).get("depth_quality_input_row_count") or -1)
    if len(bundle.depth_quality_input_rows) != expected_valid:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    if len(bundle.depth_quality_input_rows) != summary_depth_count:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
    if len(bundle.quarantined_invalid_book_rows) != expected_invalid:
        _append_once(blockers, "stage1_5h_upstream_artifact_mismatch")
```

- [ ] **Step 4: Re-run validation tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_invalid_stage1_5g_input \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_true_execution_or_trading_flags_once \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_artifact_row_count_mismatch \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_quarantine_summary_value_mismatch \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_stage1_5h_rejects_depth_quality_input_count_mismatch_between_summary_and_jsonl \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
git commit -m "test: enforce stage1 5h upstream governance gates"
```

---

## Task 4: Compute Static Proxy Summary Without Double-Counting Costs

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Interfaces:**
- Produces:

```python
build_stage1_5h_report_summary(bundle: Stage1_5HInputBundle) -> dict[str, Any]
```

- [ ] **Step 1: Add failing summary tests**

Append:

```python

def test_build_stage1_5h_report_summary_preserves_quarantine_and_cost_floor(tmp_path):
    from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import build_stage1_5h_report_summary

    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))

    assert result["decision"] == "stage1_5h_single_event_static_proxy_report_generated"
    assert result["allowed_next_action"] == "review_stage1_5h_read_only_report"
    assert result["scope"] == "single_event_fixture_bound_report_generator"
    assert result["governance_plan_admission_confirmed"] is True
    assert result["report_generation_allowed"] is True
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["clean_depth_evidence_pass"] is False
    assert result["quarantined_depth_evidence_pass"] is True
    assert result["clean_pass_missing_reason"] == [
        "upstream_reason_first",
        "invalid_book_present",
        "observation_initial_empty_book_present",
        "midrun_empty_book_present",
        "launch_time_missing_warmup_anchor_degraded",
    ]
    assert result["quarantine_warnings"] == ["launch_time_missing_warmup_anchor_degraded"]
    assert result["summary_warnings"] == ["summary_level_warning_to_preserve"]
    assert result["book_availability_ratio"] == 0.9805555555555555
    assert result["static_proxy_metrics"]["observed_static_depth_friction_bps_p95"] == 2.050259958923384 + 1.8699513715880745
    assert result["static_proxy_metrics"]["configured_conservative_round_trip_cost_bps"] == 50.0
    assert result["static_proxy_metrics"]["effective_friction_floor_bps"] == 50.0
    assert result["static_proxy_report_status"] == "proxy_metrics_within_configured_bounds"
    assert result["static_proxy_blockers"] == []
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_report_generator_preserves_upstream_clean_pass_missing_reason_without_reordering(tmp_path):
    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    assert result["clean_pass_missing_reason"][0] == "upstream_reason_first"


def test_report_generator_reconstructs_missing_reason_with_warning(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary.pop("clean_pass_missing_reason")
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert "invalid_book_present" in result["clean_pass_missing_reason"]
    assert "clean_pass_missing_reason_reconstructed_by_stage1_5h" in result["warnings"]


def test_report_generator_blocks_when_spread_p95_exceeds_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["quarantined_depth_quality"]["spread_bps_p95"] = 99.0
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "spread_p95_too_high" in result["static_proxy_blockers"]


def test_report_generator_blocks_when_top_depth_p05_below_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    summary["depth_quality"]["quarantined_depth_quality"]["top_bid_depth_usdt_p05"] = 1.0
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "top_bid_depth_p05_too_low" in result["static_proxy_blockers"]


def test_report_generator_blocks_when_book_availability_below_config(tmp_path):
    paths = list(make_stage1_5h_fixture(tmp_path))
    quarantine = json.loads(paths[1].read_text(encoding="utf-8"))
    summary = json.loads(paths[0].read_text(encoding="utf-8"))
    quarantine["book_availability_ratio"] = 0.97
    summary["quarantine"]["book_availability_ratio"] = 0.97
    paths[1].write_text(json.dumps(quarantine), encoding="utf-8")
    paths[0].write_text(json.dumps(summary), encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )

    result = build_stage1_5h_report_summary(bundle)

    assert result["static_proxy_report_status"] == "proxy_metrics_blocked"
    assert "book_availability_ratio_below_threshold" in result["static_proxy_blockers"]
```

- [ ] **Step 2: Run failing summary tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_build_stage1_5h_report_summary_preserves_quarantine_and_cost_floor \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_preserves_upstream_clean_pass_missing_reason_without_reordering \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_reconstructs_missing_reason_with_warning \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_spread_p95_exceeds_config \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_top_depth_p05_below_config \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_book_availability_below_config \
  -q
```

Expected: FAIL because `build_stage1_5h_report_summary` does not exist.

- [ ] **Step 3: Implement summary builder**

Add imports and functions:

```python
from configs import base


def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    merged: list[str] = []
    for item in list(first or []) + list(second or []):
        if item not in merged:
            merged.append(item)
    return merged


def _fallback_clean_pass_missing_reason(summary: dict[str, Any], quarantine: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if quarantine.get("invalid_book_row_count", 0) > 0:
        reasons.append("invalid_book_present")
    reasons_by_name = quarantine.get("invalid_book_by_reason", {}) or {}
    if reasons_by_name.get("launch_warmup_empty_book", 0) > 0:
        reasons.append("launch_warmup_empty_book_present")
    if reasons_by_name.get("observation_initial_empty_book", 0) > 0:
        reasons.append("observation_initial_empty_book_present")
    if reasons_by_name.get("midrun_empty_book", 0) > 0:
        reasons.append("midrun_empty_book_present")
    # Preserve both quarantine-level and summary-level warnings. They may differ.
    return _merge_unique(reasons, _merge_unique(quarantine.get("warnings", []), summary.get("warnings", [])))


def _clean_pass_missing_reason(summary: dict[str, Any], quarantine: dict[str, Any], warnings: list[str]) -> list[str]:
    upstream = summary.get("clean_pass_missing_reason") or (summary.get("quarantine") or {}).get("clean_pass_missing_reason")
    if upstream:
        return list(upstream)
    _append_once(warnings, "clean_pass_missing_reason_reconstructed_by_stage1_5h")
    return _fallback_clean_pass_missing_reason(summary, quarantine)


def _build_static_proxy_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    quality = ((summary.get("depth_quality") or {}).get("quarantined_depth_quality") or {})
    buy_p95 = float(quality.get("buy_slippage_bps_500usdt_p95") or 0.0)
    sell_p95 = float(quality.get("sell_slippage_bps_500usdt_p95") or 0.0)
    observed = buy_p95 + sell_p95
    configured = float(base.EXTERNAL_SIGNAL_STAGE1_5H_CONSERVATIVE_ROUND_TRIP_COST_BPS)
    return {
        "depth_quality_input_mode": (summary.get("depth_quality") or {}).get("depth_quality_input_mode"),
        "spread_bps_p50": quality.get("spread_bps_p50"),
        "spread_bps_p95": quality.get("spread_bps_p95"),
        "buy_slippage_bps_500usdt_p50": quality.get("buy_slippage_bps_500usdt_p50"),
        "buy_slippage_bps_500usdt_p95": buy_p95,
        "sell_slippage_bps_500usdt_p50": quality.get("sell_slippage_bps_500usdt_p50"),
        "sell_slippage_bps_500usdt_p95": sell_p95,
        "top_bid_depth_usdt_p05": quality.get("top_bid_depth_usdt_p05"),
        "top_ask_depth_usdt_p05": quality.get("top_ask_depth_usdt_p05"),
        "healthy_window_ratio": quality.get("healthy_window_ratio"),
        "observed_static_depth_friction_bps_p95": observed,
        "configured_conservative_round_trip_cost_bps": configured,
        "effective_friction_floor_bps": max(observed, configured),
        "cost_model_note": "effective_friction_floor_bps=max(observed_static_depth_friction_bps_p95, configured_conservative_round_trip_cost_bps); never sum them",
    }


def _static_proxy_blockers(metrics: dict[str, Any], quarantine: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if float(metrics.get("spread_bps_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS:
        blockers.append("spread_p95_too_high")
    if float(metrics.get("buy_slippage_bps_500usdt_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS:
        blockers.append("buy_slippage_p95_too_high")
    if float(metrics.get("sell_slippage_bps_500usdt_p95") or 0.0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS:
        blockers.append("sell_slippage_p95_too_high")
    if float(metrics.get("top_bid_depth_usdt_p05") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05:
        blockers.append("top_bid_depth_p05_too_low")
    if float(metrics.get("top_ask_depth_usdt_p05") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05:
        blockers.append("top_ask_depth_p05_too_low")
    if float(quarantine.get("book_availability_ratio") or 0.0) < base.EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO:
        blockers.append("book_availability_ratio_below_threshold")
    if int(quarantine.get("first_valid_book_latency_ms") or 0) > base.EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS:
        blockers.append("first_valid_book_latency_too_high")
    return blockers


def build_stage1_5h_report_summary(bundle: Stage1_5HInputBundle) -> dict[str, Any]:
    governance = validate_stage1_5h_governance(bundle)
    summary = bundle.stage1_5g_summary
    quarantine = bundle.quarantine_summary
    if governance["blockers"]:
        return {
            **governance,
            "decision": "stage1_5h_input_rejected",
            "allowed_next_action": "revise_inputs_or_continue_observation",
        }
    warnings = _merge_unique(quarantine.get("warnings", []), summary.get("warnings", []))
    metrics = _build_static_proxy_metrics(summary)
    static_blockers = _static_proxy_blockers(metrics, quarantine)
    return {
        "decision": "stage1_5h_single_event_static_proxy_report_generated",
        "allowed_next_action": "review_stage1_5h_read_only_report",
        "scope": "single_event_fixture_bound_report_generator",
        "evidence_scope": "single_event",
        "governance_plan_admission_confirmed": True,
        "report_generation_allowed": True,
        "clean_depth_evidence_pass": False,
        "quarantined_depth_evidence_pass": True,
        "quarantine_candidate": True,
        "clean_pass_missing_reason": _clean_pass_missing_reason(summary, quarantine, warnings),
        "quarantine_warnings": list(quarantine.get("warnings", [])),
        "summary_warnings": list(summary.get("warnings", [])),
        "book_availability_ratio": quarantine.get("book_availability_ratio"),
        "book_unavailable_ratio": quarantine.get("book_unavailable_ratio"),
        "valid_snapshot_count_after_quarantine": quarantine.get("valid_snapshot_count_after_quarantine"),
        "invalid_book_row_count": quarantine.get("invalid_book_row_count"),
        "invalid_book_by_phase": quarantine.get("invalid_book_by_phase"),
        "invalid_book_by_reason": quarantine.get("invalid_book_by_reason"),
        "max_consecutive_invalid": quarantine.get("max_consecutive_invalid"),
        "max_consecutive_invalid_after_warmup": quarantine.get("max_consecutive_invalid_after_warmup"),
        "first_valid_book_latency_ms": quarantine.get("first_valid_book_latency_ms"),
        "static_proxy_metrics": metrics,
        "static_proxy_blockers": static_blockers,
        "static_proxy_warnings": [],
        "static_proxy_report_status": "proxy_metrics_within_configured_bounds" if not static_blockers else "proxy_metrics_blocked",
        "required_next_evidence": [
            "clean_stage1_5g_depth_evidence_or_additional_independent_quarantined_events",
            "higher_frequency_orderbook_for_more_precise_execution_proxy_design",
            "trade_prints_for_future_fill_model_research",
            "separate_governance_before_any_execution_feasibility_claim",
        ],
        "blockers": [],
        "warnings": warnings,
        **_base_safety_fields(),
    }
```

- [ ] **Step 4: Re-run summary tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_build_stage1_5h_report_summary_preserves_quarantine_and_cost_floor \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_preserves_upstream_clean_pass_missing_reason_without_reordering \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_reconstructs_missing_reason_with_warning \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_spread_p95_exceeds_config \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_top_depth_p05_below_config \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_blocks_when_book_availability_below_config \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
git commit -m "feat: compute stage1 5h read-only static proxy summary"
```

---

## Task 5: Generate Chinese Markdown Report

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Interfaces:**
- Produces:

```python
generate_stage1_5h_chinese_report(summary: dict[str, Any]) -> str
```

- [ ] **Step 1: Add failing Markdown test**

Append:

```python

def test_generate_stage1_5h_chinese_report_includes_safety_and_quarantine_context(tmp_path):
    from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
        build_stage1_5h_report_summary,
        generate_stage1_5h_chinese_report,
    )

    summary = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    markdown = generate_stage1_5h_chinese_report(summary)

    assert "Stage 1.5H" in markdown
    assert "只读" in markdown
    assert "single_event_fixture_bound_report_generator" in markdown
    assert "clean_depth_evidence_pass = false" in markdown
    assert "quarantined_depth_evidence_pass = true" in markdown
    assert "execution_feasibility_claim_allowed = false" in markdown
    assert "effective_friction_floor_bps" in markdown
    assert "static_proxy_report_status" in markdown
    assert "不能作为 paper/live 或执行可行性证明" in markdown
```

- [ ] **Step 2: Run failing Markdown test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_generate_stage1_5h_chinese_report_includes_safety_and_quarantine_context \
  -q
```

Expected: FAIL because Markdown generator does not exist.

- [ ] **Step 3: Implement Markdown generator**

Add:

```python
def generate_stage1_5h_chinese_report(summary: dict[str, Any]) -> str:
    metrics = summary.get("static_proxy_metrics", {}) or {}
    reasons = summary.get("clean_pass_missing_reason", []) or []
    return "\n".join([
        "# External Signal Shadow Lab Stage 1.5H Static Execution Proxy Read-Only Report",
        "",
        "## 1. 结论",
        "",
        f"- decision: `{summary.get('decision')}`",
        f"- allowed_next_action: `{summary.get('allowed_next_action')}`",
        f"- scope: `{summary.get('scope')}`",
        f"- static_proxy_report_status: `{summary.get('static_proxy_report_status')}`",
        "- 本报告是只读报告，不是交易信号，不是执行可行性证明。",
        "- 不能作为 paper/live 或执行可行性证明。",
        "",
        "## 2. Safety Flags",
        "",
        f"- execution_feasibility_claim_allowed = {str(summary.get('execution_feasibility_claim_allowed')).lower()}",
        f"- paper_trading_allowed = {str(summary.get('paper_trading_allowed')).lower()}",
        f"- live_trading_allowed = {str(summary.get('live_trading_allowed')).lower()}",
        f"- execution_engine_allowed = {str(summary.get('execution_engine_allowed')).lower()}",
        "",
        "## 3. Quarantine Context",
        "",
        f"- clean_depth_evidence_pass = {str(summary.get('clean_depth_evidence_pass')).lower()}",
        f"- quarantined_depth_evidence_pass = {str(summary.get('quarantined_depth_evidence_pass')).lower()}",
        f"- clean_pass_missing_reason: `{reasons}`",
        f"- book_availability_ratio: `{summary.get('book_availability_ratio')}`",
        f"- invalid_book_row_count: `{summary.get('invalid_book_row_count')}`",
        f"- max_consecutive_invalid: `{summary.get('max_consecutive_invalid')}`",
        f"- max_consecutive_invalid_after_warmup: `{summary.get('max_consecutive_invalid_after_warmup')}`",
        "",
        "## 4. Static Proxy Metrics",
        "",
        f"- spread_bps_p95: `{metrics.get('spread_bps_p95')}`",
        f"- buy_slippage_bps_500usdt_p95: `{metrics.get('buy_slippage_bps_500usdt_p95')}`",
        f"- sell_slippage_bps_500usdt_p95: `{metrics.get('sell_slippage_bps_500usdt_p95')}`",
        f"- observed_static_depth_friction_bps_p95: `{metrics.get('observed_static_depth_friction_bps_p95')}`",
        f"- configured_conservative_round_trip_cost_bps: `{metrics.get('configured_conservative_round_trip_cost_bps')}`",
        f"- effective_friction_floor_bps: `{metrics.get('effective_friction_floor_bps')}`",
        f"- static_proxy_blockers: `{summary.get('static_proxy_blockers')}`",
        "",
        "## 5. Required Next Evidence",
        "",
        *(f"- `{item}`" for item in summary.get("required_next_evidence", [])),
        "",
    ])
```

- [ ] **Step 4: Re-run Markdown test**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_generate_stage1_5h_chinese_report_includes_safety_and_quarantine_context \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
git commit -m "feat: render stage1 5h read-only report"
```

---

## Task 6: Add CLI Wrapper

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py`
- Create: `tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py`

**Interfaces:**
- CLI arguments:

```text
--stage1-5g-summary
--stage1-5g-quarantine-summary
--depth-quality-input-rows
--quarantined-invalid-book-rows
--governance-review
--output-root
--output-summary
--output-review
```

- [ ] **Step 1: Write failing CLI tests**

Create `tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py`:

```python
import json
import sys

from scripts.external_signal_shadow.review_stage1_5h_static_execution_proxy_report import main
from tests.research.external_signal_shadow.test_stage1_5h_read_only_report_generator import make_stage1_5h_fixture


def test_stage1_5h_cli_writes_summary_and_review(tmp_path, monkeypatch):
    paths = make_stage1_5h_fixture(tmp_path)
    output_root = tmp_path / "stage1_5h" / "reports" / "run1"
    summary_out = output_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_out = tmp_path / "docs" / "reviews" / "stage1_5h_report.md"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(paths[0]),
        "--stage1-5g-quarantine-summary", str(paths[1]),
        "--depth-quality-input-rows", str(paths[2]),
        "--quarantined-invalid-book-rows", str(paths[3]),
        "--governance-review", str(paths[4]),
        "--output-root", str(output_root),
        "--output-summary", str(summary_out),
        "--output-review", str(review_out),
    ])

    assert main() == 0
    assert summary_out.exists()
    assert review_out.exists()
    summary = json.loads(summary_out.read_text(encoding="utf-8"))
    assert summary["decision"] == "stage1_5h_single_event_static_proxy_report_generated"
    assert summary["implementation_plan_allowed"] is False
    assert summary["implementation_allowed"] is False
    assert summary["paper_trading_allowed"] is False
    assert "不能作为 paper/live" in review_out.read_text(encoding="utf-8")


def test_stage1_5h_cli_returns_nonzero_for_missing_required_input(tmp_path, monkeypatch):
    output_root = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(tmp_path / "missing.json"),
        "--stage1-5g-quarantine-summary", str(tmp_path / "missing_quarantine.json"),
        "--depth-quality-input-rows", str(tmp_path / "missing_valid.jsonl"),
        "--quarantined-invalid-book-rows", str(tmp_path / "missing_invalid.jsonl"),
        "--governance-review", str(tmp_path / "missing_review.md"),
        "--output-root", str(output_root),
    ])

    assert main() == 1


def test_cli_does_not_write_normal_review_markdown_when_governance_rejected(tmp_path, monkeypatch):
    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    output_root = tmp_path / "stage1_5h" / "reports" / "rejected"
    summary_out = output_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_out = tmp_path / "docs" / "reviews" / "stage1_5h_report.md"

    monkeypatch.setattr(sys, "argv", [
        "review_stage1_5h_static_execution_proxy_report.py",
        "--stage1-5g-summary", str(paths[0]),
        "--stage1-5g-quarantine-summary", str(paths[1]),
        "--depth-quality-input-rows", str(paths[2]),
        "--quarantined-invalid-book-rows", str(paths[3]),
        "--governance-review", str(paths[4]),
        "--output-root", str(output_root),
        "--output-summary", str(summary_out),
        "--output-review", str(review_out),
    ])

    assert main() == 1
    assert summary_out.exists()
    assert not review_out.exists()
```

- [ ] **Step 2: Run failing CLI tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  -q
```

Expected: FAIL because CLI script does not exist.

- [ ] **Step 3: Implement CLI**

Create `scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import (
    build_stage1_5h_report_summary,
    generate_stage1_5h_chinese_report,
    load_stage1_5h_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 1.5H read-only static execution proxy report generator")
    parser.add_argument("--stage1-5g-summary", required=True)
    parser.add_argument("--stage1-5g-quarantine-summary", required=True)
    parser.add_argument("--depth-quality-input-rows", required=True)
    parser.add_argument("--quarantined-invalid-book-rows", required=True)
    parser.add_argument("--governance-review", required=True)
    parser.add_argument("--output-root")
    parser.add_argument("--output-summary")
    parser.add_argument("--output-review")
    args = parser.parse_args()

    utc_now = datetime.now(timezone.utc)
    run_id = utc_now.strftime("%Y%m%dT%H%M%SZ")
    today = utc_now.strftime("%Y-%m-%d")
    out_root = Path(args.output_root) if args.output_root else Path(f"data/external_signal_shadow/stage1_5h/reports/{run_id}")
    summary_path = Path(args.output_summary) if args.output_summary else out_root / "stage1_5h_static_execution_proxy_report_summary.json"
    review_path = Path(args.output_review) if args.output_review else Path(f"docs/reviews/{today}-external-signal-shadow-lab-stage1-5h-static-execution-proxy-report_CN.md")

    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=args.stage1_5g_summary,
        quarantine_summary_path=args.stage1_5g_quarantine_summary,
        depth_quality_input_rows_path=args.depth_quality_input_rows,
        quarantined_invalid_book_rows_path=args.quarantined_invalid_book_rows,
        governance_review_path=args.governance_review,
    )
    if bundle.loader_blockers:
        print(f"Stage 1.5H loader blockers: {bundle.loader_blockers}", file=sys.stderr)
        return 1

    report_summary = build_stage1_5h_report_summary(bundle)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(report_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if report_summary.get("blockers"):
        print(f"Stage 1.5H report blockers: {report_summary['blockers']}", file=sys.stderr)
        return 1

    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(generate_stage1_5h_chinese_report(report_summary) + "\n", encoding="utf-8")

    print(f"Stage 1.5H report summary written to: {summary_path}")
    print(f"Stage 1.5H markdown report written to: {review_path}")
    print(f"Decision: {report_summary['decision']}")
    print(f"Allowed next action: {report_summary['allowed_next_action']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Re-run CLI tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 6**

```bash
git add scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py
git commit -m "feat: add stage1 5h read-only report cli"
```

---

## Task 7: Add Safety Regression Tests And No-Op Invariant

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py`
- Modify: `tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py`

**Interfaces:**
- Ensure report summary never contains forbidden keys or true safety flags.

- [ ] **Step 1: Add safety tests**

Append:

```python

def test_report_summary_never_contains_order_signal_or_pnl_terms(tmp_path):
    from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import build_stage1_5h_report_summary

    result = build_stage1_5h_report_summary(load_fixture_bundle(tmp_path))
    encoded = json.dumps(result, ensure_ascii=False)

    forbidden = [
        "SignalCandidate",
        "TradeIntent",
        "virtual_order",
        "hypothetical_trade",
        "entry_exit_path",
        "fill_probability",
        "order_lifecycle_state_machine",
        "pnl_path",
    ]
    for term in forbidden:
        assert term not in encoded
    assert result["execution_feasibility_claim_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False


def test_report_generator_returns_safe_noop_when_governance_fails(tmp_path):
    from src.research.external_signal_shadow.stage1_5h_read_only_report_generator import build_stage1_5h_report_summary

    paths = list(make_stage1_5h_fixture(tmp_path))
    paths[4].write_text("governance_decision = read_only_report_generator_plan_blocked\n", encoding="utf-8")
    bundle = load_stage1_5h_inputs(
        stage1_5g_summary_path=paths[0],
        quarantine_summary_path=paths[1],
        depth_quality_input_rows_path=paths[2],
        quarantined_invalid_book_rows_path=paths[3],
        governance_review_path=paths[4],
    )
    result = build_stage1_5h_report_summary(bundle)

    assert result["decision"] == "stage1_5h_input_rejected"
    assert result["implementation_plan_allowed"] is False
    assert result["implementation_allowed"] is False
    assert result["execution_engine_allowed"] is False
    assert result["paper_trading_allowed"] is False
    assert result["live_trading_allowed"] is False
    assert "governance_approval_missing" in result["blockers"]
```

- [ ] **Step 2: Run safety tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_summary_never_contains_order_signal_or_pnl_terms \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py::test_report_generator_returns_safe_noop_when_governance_fails \
  -q
```

Expected: PASS if earlier tasks preserved the safety invariant. If failing, fix only the unsafe key/output causing failure.

- [ ] **Step 3: Run production safety grep**

Production code must have no forbidden signal/order/private/live path terms:

```bash
! rg -n "SignalCandidate|TradeIntent|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true|execution_feasibility_claim_allowed.*true|apiKey|secret|private" \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py

! rg -n "\\bplace_order\\b|\\bcreate_order\\b|\\border_endpoint\\b|\\border_intent\\b|\\bOrderIntent\\b|\\bfill_simulation\\b|\\border_lifecycle\\b|\\bvirtual_order\\b|\\bhypothetical_trade\\b|\\bentry_exit_path\\b|\\bpnl_path\\b" \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py
```

Expected: PASS with no production matches.

- [ ] **Step 4: Run test documentation grep**

Tests may contain forbidden terms only inside explicit negative assertions:

```bash
rg -n "SignalCandidate|TradeIntent|virtual_order|hypothetical_trade|entry_exit_path|fill_probability|order_lifecycle_state_machine|pnl_path" \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py
```

Expected: matches only in `test_report_summary_never_contains_order_signal_or_pnl_terms`.

- [ ] **Step 5: Commit Task 7**

```bash
git add src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py
git commit -m "test: lock stage1 5h read-only safety invariants"
```

---

## Task 8: End-To-End Verification And Review Doc Update

**Files:**
- Modify: `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md`
- Optionally create after running CLI: `docs/reviews/YYYY-MM-DD-external-signal-shadow-lab-stage1-5h-static-execution-proxy-report_CN.md`

**Interfaces:**
- Uses CLI from Task 6.

- [ ] **Step 1: Run full targeted test suite**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: Run adjacent Stage 1.5G regression tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_decision.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_metrics.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_quarantine.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5g_live_depth_evidence.py \
  -q
```

Expected: PASS. This proves 1.5H did not regress 1.5G quarantine behavior.

- [ ] **Step 3: Run CLI on the latest real Stage 1.5G run if artifacts exist locally**

```bash
export STAGE1_5G_OUT="$(find data/external_signal_shadow/stage1_5g/reviews -maxdepth 1 -type d | sort | tail -n 1)"
export STAGE1_5H_OUT="data/external_signal_shadow/stage1_5h/reports/$(date -u +%Y%m%dT%H%M%SZ)"

PYTHONPATH=src:. .venv/bin/python scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py \
  --stage1-5g-summary "$STAGE1_5G_OUT/stage1_5g_live_depth_evidence_review_summary.json" \
  --stage1-5g-quarantine-summary "$STAGE1_5G_OUT/stage1_5g_quarantine_summary.json" \
  --depth-quality-input-rows "$STAGE1_5G_OUT/depth_quality_input_rows.jsonl" \
  --quarantined-invalid-book-rows "$STAGE1_5G_OUT/quarantined_invalid_book_rows.jsonl" \
  --governance-review docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md \
  --output-root "$STAGE1_5H_OUT" \
  --output-summary "$STAGE1_5H_OUT/stage1_5h_static_execution_proxy_report_summary.json" \
  --output-review "docs/reviews/$(date -u +%Y-%m-%d)-external-signal-shadow-lab-stage1-5h-static-execution-proxy-report_CN.md"
```

Expected output:

```text
Stage 1.5H report summary written to: .../stage1_5h_static_execution_proxy_report_summary.json
Stage 1.5H markdown report written to: docs/reviews/...stage1_5h-static-execution-proxy-report_CN.md
Decision: stage1_5h_single_event_static_proxy_report_generated
Allowed next action: review_stage1_5h_read_only_report
```

If local real artifacts do not exist, skip this step and state `local_stage1_5g_artifacts_missing`; do not fabricate data.

- [ ] **Step 4: Inspect generated summary safety flags**

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ["STAGE1_5H_OUT"]) / "stage1_5h_static_execution_proxy_report_summary.json"
s = json.loads(p.read_text(encoding="utf-8"))
for k in [
    "decision",
    "allowed_next_action",
    "scope",
    "clean_depth_evidence_pass",
    "quarantined_depth_evidence_pass",
    "governance_plan_admission_confirmed",
    "report_generation_allowed",
    "implementation_plan_allowed",
    "implementation_allowed",
    "execution_feasibility_claim_allowed",
    "paper_trading_allowed",
    "live_trading_allowed",
    "execution_engine_allowed",
    "event_family_conclusion_allowed",
    "multi_event_aggregation_allowed",
    "static_proxy_report_status",
    "static_proxy_blockers",
    "static_proxy_metrics",
    "required_next_evidence",
]:
    print(f"=== {k} ===")
    print(json.dumps(s.get(k), indent=2, ensure_ascii=False))
PY
```

Expected:

```text
governance_plan_admission_confirmed = true
report_generation_allowed = true
implementation_plan_allowed = false
implementation_allowed = false
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
event_family_conclusion_allowed = false
multi_event_aggregation_allowed = false
```

- [ ] **Step 5: Update governance review with implementation-plan execution reference**

Append a short section to `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md`:

```markdown
## 11. Implementation Plan Written

已根据本 governance review 写入 implementation plan：

```text
plan = docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
implementation_plan_allowed = true
implementation_allowed = false
```

该 plan 仍需单独执行和 review，不能直接视为实现批准。
```

- [ ] **Step 6: Final verification**

```bash
git diff --check -- \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
```

Expected: no output.

- [ ] **Step 7: Commit Task 8**

```bash
git add configs/base.py \
  src/research/external_signal_shadow/stage1_5h_read_only_report_generator.py \
  scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator_config.py \
  tests/research/external_signal_shadow/test_stage1_5h_read_only_report_generator.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5h_static_execution_proxy_report.py \
  docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md \
  docs/reviews/*stage1_5h-static-execution-proxy-report_CN.md

git commit -m "feat: add stage1 5h read-only static proxy report generator"
```

---

## Self-Review Checklist

Spec coverage:

```text
1. Explicit governance approval required: Task 2 / Task 3.
2. Single-event fixture-bound only: Task 3 / Task 4.
3. No implementation from governance review alone: Global Constraints / Task 8.
4. Stage 1.5G source-of-truth, no recompute/override/promote: Task 3.
5. Quarantine blockers/warnings and clean-pass missing reason preserved: Task 4 / Task 5.
6. Invalid rows only affect availability/stability/risk discount: Task 4 / Task 7.
7. No SignalCandidate, TradeIntent, order lifecycle, PnL path: Task 7.
8. Config thresholds in configs/base.py only: Task 1.
9. CLI writes local JSON/Markdown only: Task 6.
10. Adjacent 1.5G regression verification: Task 8.
```

Placeholder scan result:

```text
No unresolved placeholder markers are allowed in this plan.
Every task has exact file paths, tests, commands, and expected results.
```

Type consistency:

```text
Stage1_5HInputBundle, load_stage1_5h_inputs, validate_stage1_5h_governance,
build_stage1_5h_report_summary, and generate_stage1_5h_chinese_report are defined before use.
```

---

## Execution Handoff

Plan saved to:

```text
docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
```

Execution options after user approval:

```text
1. Subagent-Driven: one fresh subagent per task, review after each task.
2. Inline Execution: execute tasks in this session with checkpoint review.
```

Recommended: Subagent-Driven for Tasks 1-8 because the plan touches config, src, scripts, tests, and review docs.
