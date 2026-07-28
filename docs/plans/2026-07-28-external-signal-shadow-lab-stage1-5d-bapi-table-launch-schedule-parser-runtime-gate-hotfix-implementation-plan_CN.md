# Stage 1.5D BAPI Table Launch Schedule Parser and Runtime Gate Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix missed Binance BAPI table/list launch schedule announcements such as A827, enforce safe multi-symbol launch-time semantics, and replace cross-root Stage 1.5D summary dependency with a dedicated same-root runtime gate consumed by Stage 1.5F.

**Architecture:** Split the work into two independently revertible commits. Task A upgrades Stage 1.5D parser/runner behavior with a real frozen A827 fixture, v3 provenance, all-or-none multi-symbol validation, safe launch anchor rules, and BAPI parser diagnostics. Task B adds a dedicated Stage 1.5D runtime gate artifact, strict Stage 1.5F allowlist validator, same-root/freshness binding, and periodic gate revalidation that blocks only new admissions.

**Tech Stack:** Python stdlib, JSON/JSONL artifacts, `configs/base.py`, pytest, existing `src/research/external_signal_shadow/stage1_5d_*` modules, existing `src/research/external_signal_shadow/stage1_5f_*` modules, existing `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` and `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` runners.

---

## 0. Non-Negotiable Boundaries

Keep all execution permissions disabled everywhere:

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

Forbidden:

```text
private Binance endpoint
login cookie
Authorization header
X-MBX-APIKEY
account/session state
order placement
paper/live/execution wiring
old event backfill into 1.5F clean evidence
1.5G threshold relaxation
```

Terminology:

```text
content_provenance = binance_official_announcement
source_transport = binance_first_party_public_web_bapi_undocumented
```

Do not call BAPI an official supported API, documented API, or stable public API.

Implementation commits:

```text
Commit A: parser/scheduler/runner hotfix only
Commit B: runtime gate writer + 1.5F validator only
```



## 0.1 Review Amendments That Override Later Task Text

The following amendments are blocking requirements. If any later task appears weaker or ambiguous, follow this section.

### A. Scheduler Schema V2 And Explicit Persistence

`serialize_retry_articles()` is an explicit whitelist. Any new scheduler field not added there will be silently dropped before `detail_retry_scheduler_state.json` is written.

Required changes:

```text
configs/base.py:
  EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_SCHEDULER_METADATA_VERSION = 2

src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py:
  serialize_retry_articles() includes all new parser/anchor fields
  load_detail_retry_scheduler_state() migrates metadata_version=1 with safe defaults
  write_detail_retry_scheduler_state() writes metadata_version=2

scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py:
  startup recovery copies all new fields from persisted articles into detail_retry_state
```

New fields that must survive restart:

```text
last_bapi_detail_status
last_bapi_payload_hash
last_bapi_parser_version
last_bapi_parser_status
last_bapi_parser_failure_reason
last_bapi_parse_attempt_at_ms
last_support_detail_status
last_support_failure_class
parsed_candidate_symbols
candidate_provenance
launch_time_resolution_status
launch_anchor_policy
required_launch_anchor_source
consumable_event_allowed
symbol_launch_time_candidates_ms
launch_time_conflict_ms
```

Required tests:

```text
test_bapi_parser_diagnostics_round_trip
test_no_symbol_dedup_survives_restart
test_v1_scheduler_state_loads_with_safe_defaults
test_parser_version_change_survives_restart_and_reparses
test_strict_multi_contract_anchor_policy_survives_restart
```

### B. Strict Launch Anchor Policy Must Be Durable

BAPI multi-contract strict anchor behavior cannot be only a function-call parameter. It must be persisted in scheduler state:

```text
launch_anchor_policy = bapi_multi_contract_strict
required_launch_anchor_source = detail_per_symbol_time_or_exchangeinfo_onboard
```

Every emission path must read this persisted policy:

```text
initial BAPI path
pending exchangeInfo revalidation path
restart recovery path
all-symbols-later-validated path
```

Required tests:

```text
test_pending_revalidation_never_reenables_release_date_fallback
test_pending_revalidation_never_reenables_legacy_max_age_fallback
```

### C. A827 Fixture Must Bind To One Manifest Row

Do not choose “latest or earliest trusted payload” loosely. Select one unique request_manifest row and record:

```text
request_id
fetched_at_ms
payload_path
payload_sha256
payload_trusted
source_article_id
detail_fetch_variant
http_status
```

Required invariant:

```text
server_file_sha256 == request_manifest.payload_sha256 == local_fixture_sha256
```

If fixture is minimized/redacted, do not label it `real_frozen_bapi_payload`; label it `manually_minimized_from_real_bapi_payload` and include `source_raw_payload_sha256`.

### D. Table Pairing Must Fail Safe

A consumable symbol/time mapping must include provenance:

```text
logical_block_id
symbol_node_path
time_node_path
common_ancestor_path
raw_time_text
timezone_text
pairing_method
pairing_confidence
```

Minimum consumable conditions:

```text
same logical launch block
explicit UTC
unique symbols
unique times
monotonic time order
no duplicate-layout ambiguity
symbol_count == time_count
```

Use exact timestamp agreement for first version:

```text
EXTERNAL_SIGNAL_STAGE1_5D_MAX_LAUNCH_TIME_DISAGREEMENT_MS = 0
```

Required tests:

```text
test_equal_counts_but_swapped_order_is_ambiguous
test_duplicate_mobile_desktop_table_is_ambiguous
test_duplicate_time_is_not_consumable
test_candidate_limit_exceeded_is_not_consumable
test_old_parser_symbols_plus_ambiguous_schedule_fails_closed
```

### E. Parser Result Audit Stream

Do not mutate already-written HTTP request_manifest rows. Add a separate audit stream:

```text
$STAGE1_5D_EVENTS_OUT/bapi_parse_results/YYYY-MM-DD.jsonl
```

Each row must link to the HTTP manifest request:

```text
request_id
source_article_id
payload_sha256
parser_version
launch_schedule_parser_version
parser_status
parser_failure_reason
symbol_count
launch_time_count
fallback_reason
candidate_provenance
```

Parser counters must be included in `build_smoke_summary()`.

Required tests:

```text
test_parser_result_row_links_to_http_manifest_request_id
test_parser_no_match_survives_support_202_and_restart
test_smoke_summary_contains_parser_method_counters
```

### F. Runtime Gate Strictness

Runtime gate READY requires all of the following:

```text
runtime_gate_schema_version == expected
prior_stage_safety_prerequisite_met == true
successful_poll_count >= 1
successful_poll_count <= poll_count
consecutive_poll_failure_count < EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES
last_heartbeat_at_ms > 0
last_successful_poll_at_ms > 0
now - last_heartbeat_at_ms <= max_staleness
now - last_successful_poll_at_ms <= max_staleness
fatal_blockers == []
fixture_run == false
live_public_readonly == true
source_format_drift_active == false
schema_parse_error_active == false
all six safety fields present and false
```

Use `>=` for degraded threshold:

```text
consecutive_poll_failure_count >= configured_max -> DEGRADED
```

Use this field name consistently:

```text
prior_stage_safety_prerequisite_met
```

Meaning:

```text
For independent 1.5D continuous live-public-readonly run, pass True after local safety prerequisites and input summaries are accepted.
For future non-independent runs, caller owns this prerequisite.
```

### G. Runtime Gate Lifecycle Must Cover Early Exits

1.5D runner must use explicit lifecycle handling:

```text
startup -> INITIALIZING
first valid poll -> READY
consecutive failures >= max -> DEGRADED
normal max-polls/max-seconds exit -> STOPPED
controlled KeyboardInterrupt -> STOPPED
uncaught/fatal error -> FAILED
```

Early exits to cover:

```text
missing safety flag
invalid prior evidence
fixture loading failure
fatal parser/schema error
normal max duration
KeyboardInterrupt / controlled shutdown
```

Atomic write tests must verify:

```text
old valid gate survives failed replace
temp file is not consumed by validator
written gate is complete JSON
```

### H. Strict Historical Summary Override Validator

Emergency historical summary override must not reuse the current fail-open `validate_stage1_5d_summary()`.

Add:

```text
validate_historical_stage1_5d_safety_gate(summary_path, override_reason)
```

Requirements:

```text
decision in explicit final-summary allowlist
all six safety fields present and false
fixture_run is false or absent with safe legacy compatibility
reason non-empty
cross_root_upstream_summary_dependency recorded true
```

### I. 1.5F Bootstrap Must Validate Runtime Gate

New 1.5F root startup sequence:

```text
1. Start new 1.5D.
2. Wait for runtime gate READY.
3. Run 1.5F --bootstrap-watermark with current events root and current runtime gate.
4. Verify watermark schema v2, bootstrap_root_id, bootstrap max seen.
5. Start normal 1.5F observer with the same runtime gate.
```

Bootstrap path must reject:

```text
missing runtime gate
stale runtime gate
root mismatch
fixture mode gate
invalid safety fields
```

Required tests:

```text
test_bootstrap_rejects_missing_runtime_gate
test_bootstrap_rejects_stale_runtime_gate
test_bootstrap_rejects_root_mismatch
test_bootstrap_does_not_write_watermark_on_gate_failure
test_bootstrap_ready_gate_writes_v2_watermark
```

### J. Gate Invalid Blocks Pending Promotion Too

When runtime gate is stale/degraded/invalid, block:

```text
pending -> active promotion
new event -> active
new event -> accepted row
watermark advancement caused by blocked event
```

Allow:

```text
existing active observation depth requests
existing active observation finalization
pending anchor metadata refresh
terminal hygiene reconciliation
```

Required tests:

```text
test_stale_gate_blocks_pending_to_active_promotion
test_stale_gate_does_not_write_accepted_row
test_stale_gate_does_not_advance_watermark
test_active_observation_continues_when_gate_stale
test_ready_stale_ready_recovery_promotes_pending_once
```

### K. Summary Context Plumbing

Do not rely on dataclass defaults for runtime gate fields. Add a runtime gate context object passed into every `build_live_depth_observer_summary()` call:

```text
RuntimeGateContext(
  mode,
  path,
  decision,
  last_validated_at_ms,
  stale,
  invalid_count,
  block_new_event_admission,
  diagnostic_count,
  cross_root_dependency,
  override_reason,
)
```

Update summary branches:

```text
bootstrap summary
startup invalid summary
missing watermark summary
normal per-poll summary
final summary
historical override summary
```

### L. Tests Must Use Injected/Frozen Time

Staleness tests must not depend on wall clock. Use monkeypatch or explicit `now_ms` injection:

```text
monkeypatch.setattr(time, "time_ns", lambda: fixed_ns)
```

or call validators with explicit `now_ms`.

### M. Scoped Deployment Only

Do not default to whole-worktree rsync.

Before deployment:

```text
git status --short is empty except approved deployment artifacts
Commit A / Commit B SHA recorded
git diff <base>..<commitB> --name-only within allowlist
```

Deploy only explicit changed files, then verify SHA256 on server.

Do not stop an old 1.5F root with active observations:

```text
active_observation_count > 0 -> drain-only / keep running until observation_window_end_ms
active_observation_count == 0 -> safe to stop
```

Full verification before deploy must include:

```text
git diff --check
make lint
make test
all Stage 1.5D tests
all Stage 1.5F tests
Stage 1.5G compatibility tests
```

Safety grep must cover all six fields, including `execution_feasibility_claim_allowed`.

---

## 1. Preflight Inspection And Fixture Capture

**Files:**
- Read: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Read: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Create: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json`
- Create: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Confirm current code paths**

Run:

```bash
rg -n "SYMBOL_EXTRACTION_VERSION|PARSER_VERSION|extract_symbol_candidates_from_bapi_article_payload|extract_symbol_launch_times_ms" \
  src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py

rg -n "build_effective_launch_times_ms|candidate_symbols|validated_symbols|detail_retry_state.pop|bapi_article_detail_query" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py

rg -n "add_argument|stage1-5d-events-glob|stage1-5d-summary|fixture-events-jsonl|validate_stage1_5d_summary" \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py
```

Expected:

```text
Current parser version is v2.
1.5D pending exchangeInfo path emits when validated_symbols is non-empty.
1.5F has --stage1-5d-summary but no --stage1-5d-runtime-gate.
```

**Step 2: Copy real A827 BAPI raw payload into fixture**

Use the server raw payload already saved under the active 1.5D root. Select the latest or the earliest trusted BAPI payload whose `payload_trusted=true` row exists in request_manifest.

Example server command:

```bash
export ARTICLE_ID=a827177a387e4ebea830110ba222ca48
export A827_PAYLOAD="$(find "$STAGE1_5D_EVENTS_OUT/raw_payloads/announcement_detail/$ARTICLE_ID" -type f -name '*.bapi_article_detail_query.*.json' | sort | tail -n 1)"
sha256sum "$A827_PAYLOAD"
```

Copy it locally into:

```text
tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json
```

**Step 3: Write metadata file**

Create `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json`:

```json
{
  "articleCode": "a827177a387e4ebea830110ba222ca48",
  "title": "Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts (2026-07-27)",
  "data_quality": "real_frozen_bapi_payload",
  "raw_payload_sha256": "<fill-from-sha256sum>",
  "fixture_sha256": "<fill-after-local-write>",
  "parser_version_before": "stage1_5d_symbol_extraction_v2",
  "symbol_extraction_version_before": 2,
  "current_parser_output_symbols": [],
  "current_parser_output_symbol_launch_times_ms": {},
  "expected_symbols": ["TMFUSDT", "TBTUSDT", "BITOUSDT"],
  "expected_symbol_launch_times_ms": {
    "TMFUSDT": 1785159000000,
    "TBTUSDT": 1785159300000,
    "BITOUSDT": 1785159600000
  }
}
```

**Step 4: Write failing fixture/hash tests**

Append to `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`:

```python
def test_a827_real_frozen_fixture_hash_matches_expected():
    import hashlib, json
    from pathlib import Path

    fixture = Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json")
    meta = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json").read_text())
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == meta["fixture_sha256"]
    payload = json.loads(fixture.read_text())
    assert payload.get("data", {}).get("code") == meta["articleCode"]


def test_a827_bapi_fixture_extracts_symbols_and_launch_times():
    import json
    from pathlib import Path
    from src.research.external_signal_shadow.stage1_5d_live_event_source_parser import (
        extract_symbol_candidates_from_bapi_article_payload,
    )

    payload = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json").read_text())
    meta = json.loads(Path("tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json").read_text())
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title=meta["title"])
    assert result["symbols"] == meta["expected_symbols"]
    assert result["symbol_launch_times_ms"] == meta["expected_symbol_launch_times_ms"]
```

**Step 5: Run tests and verify expected failure**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'a827_real_frozen_fixture_hash_matches_expected or a827_bapi_fixture_extracts_symbols_and_launch_times' -q
```

Expected:

```text
hash test passes
extract test fails with symbols == [] or launch times == {}
```

Do not proceed until the real fixture reproduces the bug.

---

## 2. Add Parser Config And Version Constants

**Files:**
- Modify: `configs/base.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing config/version tests**

Add tests asserting:

```python
def test_bapi_launch_schedule_parser_config_defaults():
    from configs import base
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_SCHEDULE_LINE_LOOKAHEAD == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_MAX_LAUNCH_TIME_DISAGREEMENT_MS == 0
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC >= 3600


def test_stage1_5d_parser_versions_are_v3():
    from src.research.external_signal_shadow import stage1_5d_live_event_source_parser as p
    assert p.PARSER_VERSION == "stage1_5d_symbol_extraction_v3"
    assert p.SYMBOL_EXTRACTION_VERSION == 3
    assert p.LAUNCH_SCHEDULE_PARSER_VERSION == "stage1_5d_bapi_launch_schedule_v1"
```

**Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'bapi_launch_schedule_parser_config_defaults or parser_versions_are_v3' -q
```

Expected:

```text
FAIL: constants missing or parser version still v2
```

**Step 3: Implement constants**

Add to `configs/base.py` near existing Stage 1.5D detail/parser config:

```python
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_SCHEDULE_LINE_LOOKAHEAD = 4
EXTERNAL_SIGNAL_STAGE1_5D_MAX_LAUNCH_TIME_DISAGREEMENT_MS = 0
EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC = 3600
```

Tradeoff:

```text
The 1h no-symbol dedup window prioritizes preventing high-frequency BAPI/parser starvation. It accepts that an article updated within that hour may be parsed late unless payload hash revision detection or operator replay triggers earlier reparse.
```

**Step 4: Update parser versions**

In `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`:

```python
SYMBOL_EXTRACTION_VERSION = 3
PARSER_VERSION = "stage1_5d_symbol_extraction_v3"
LAUNCH_SCHEDULE_PARSER_VERSION = "stage1_5d_bapi_launch_schedule_v1"
```

**Step 5: Run tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'bapi_launch_schedule_parser_config_defaults or parser_versions_are_v3' -q
```

Expected: PASS.

---

## 3. Implement BAPI Logical Line And Schedule Candidate Parser

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`

**Step 1: Write failing parser tests**

Add tests:

```python
def test_bapi_separated_launch_schedule_extracts_a827_symbols_and_launch_times():
    # Use real frozen A827 fixture.
    # Assert symbols, per-symbol times, parser method provenance.


def test_bapi_table_launch_schedule_symbol_time_count_mismatch_is_diagnostic():
    payload = make_minimal_bapi_payload_with_table(symbols=["AAAUSDT", "BBBUSDT"], times=["2026-07-27 13:30 (UTC)"])
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title="Binance Futures Will Launch Multiple USDⓈ-Margined TradFi Perpetual Contracts")
    assert result["symbols"] == []
    assert result["symbol_launch_times_ms"] == {}
    assert result["parser_status"] == "launch_schedule_ambiguous"
    assert result["consumable_event_allowed"] is False


def test_bapi_table_parser_does_not_capture_disclaimer_symbols():
    payload = make_minimal_bapi_payload_with_launch_and_disclaimer(
        launch_symbol="TMFUSDT",
        disclaimer_symbol="BTCUSDT",
    )
    result = extract_symbol_candidates_from_bapi_article_payload(payload, title="Binance Futures Will Launch TMFUSDT")
    assert result["symbols"] == ["TMFUSDT"]
    assert "BTCUSDT" not in result["symbols"]
```

If helper constructors do not exist, define private test helpers inside the test module.

**Step 2: Run and verify failures**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'bapi_separated_launch_schedule or bapi_table_launch_schedule or disclaimer_symbols or a827_bapi_fixture' -q
```

Expected: FAIL.

**Step 3: Implement logical text extraction helpers**

In `stage1_5d_live_event_source_parser.py`, add small helpers:

```python
def _normalize_article_text(value: str) -> str:
    ...


def _build_bapi_logical_lines(text_nodes: list[dict]) -> list[dict]:
    ...
```

Each logical line should include:

```python
{
    "text": normalized_line,
    "node_path": node_path,
    "node_order": order_index,
    "line_index": line_index,
}
```

Use HTML unescape, Unicode normalization, whitespace collapse, and skip empty lines.

**Step 4: Implement separated schedule extraction**

Add helper:

```python
def _extract_separated_launch_schedule_candidates(logical_lines: list[dict], max_symbols: int) -> dict:
    ...
```

Rules:

```text
match explicit UTC time line
look ahead 4 logical lines for symbol
require local Perpetual Contract context
return symbol/time/provenance candidates
candidate limit exceeded returns consumable_event_allowed=false
```

**Step 5: Implement table-like extraction**

Add helper:

```python
def _extract_table_launch_schedule_candidates(logical_lines: list[dict], max_symbols: int) -> dict:
    ...
```

Rules:

```text
find USDⓈ-M Perpetual Contract block
collect symbols until Launch Time
collect explicit UTC times after Launch Time
require count equality and uniqueness
fail closed on mismatch or ambiguity
```

**Step 6: Implement reconciliation**

Add helper:

```python
def _reconcile_bapi_launch_schedule_candidates(candidate_sets: list[dict], max_disagreement_ms: int) -> dict:
    ...
```

Return fields:

```text
symbols
symbol_launch_times_ms
symbol_launch_time_candidates_ms
launch_time_resolution_status
launch_time_conflict_ms
candidate_provenance
parser_status
consumable_event_allowed
launch_schedule_parser_version
```

**Step 7: Wire into `extract_symbol_candidates_from_bapi_article_payload()`**

Preserve old segment parser, then add separated/table candidates, then reconcile. Do not use full-text regex as a consumable source.

**Step 8: Run parser tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'bapi or a827 or launch_schedule or f434 or d0833 or 6cbb' -q
```

Expected: PASS.

---

## 4. Preserve BAPI Parser Diagnostics And No-Match Dedup

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Modify if needed: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`

**Step 1: Write failing diagnostics tests**

Add tests:

```python
def test_bapi_parser_no_symbol_preserves_bapi_diagnostic_even_if_support_fallback_202(tmp_path, monkeypatch):
    # BAPI returns 200 trusted payload, parser returns no_symbols, support fallback returns 202.
    # Assert scheduler state keeps last_bapi_detail_status=success and last_bapi_parser_status=no_symbols.


def test_bapi_same_hash_same_parser_no_symbols_dedupes_high_frequency_retry(tmp_path, monkeypatch):
    # Persist state with same last_bapi_payload_hash, parser v3, no_symbols, recent parse time.
    # Run another poll.
    # Assert BAPI request count does not increment before recheck interval.


def test_bapi_parser_version_change_allows_reparse_of_same_payload_hash(tmp_path, monkeypatch):
    # Persist no_symbols from v2 and run v3.
    # Assert BAPI parse/request is attempted.
```

**Step 2: Run and verify failures**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  -k 'bapi_parser_no_symbol or no_symbols_dedupes or parser_version_change' -q
```

Expected: FAIL.

**Step 3: Persist BAPI parser state fields**

When BAPI is attempted, update scheduler state with:

```python
state["last_bapi_detail_status"] = "success" or "failure"
state["last_bapi_payload_hash"] = payload_hash
state["last_bapi_parser_version"] = PARSER_VERSION
state["last_bapi_parser_status"] = parser_status
state["last_bapi_parser_failure_reason"] = failure_reason
state["last_bapi_parse_attempt_at_ms"] = now_ms
state["last_support_detail_status"] = ...
state["last_support_failure_class"] = ...
```

On trusted no-symbol fallback, increment:

```python
bapi_parser_no_symbol_count
bapi_trusted_parser_no_match_to_support_fallback_count
```

**Step 4: Add no-match dedup guard**

Before BAPI fetch/parse, if state has:

```text
same last_bapi_payload_hash
same last_bapi_parser_version
last_bapi_parser_status = no_symbols
now_ms - last_bapi_parse_attempt_at_ms < EXTERNAL_SIGNAL_STAGE1_5D_BAPI_NO_SYMBOL_RECHECK_INTERVAL_SEC * 1000
```

Skip high-frequency BAPI re-fetch/re-parse for that article. Support fallback can still proceed only if existing HTTP budget and fallback limits allow it, and `fallback_reason = bapi_trusted_parser_no_match` is manifest/audit visible.

**Step 5: Run focused tests**

Run the same pytest command. Expected: PASS.

---

## 5. Enforce Multi-Symbol All-Or-None And Safe Launch Anchors

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing all-or-none tests**

Add tests:

```python
def test_multi_symbol_one_of_three_validated_does_not_emit_partial_event(tmp_path, monkeypatch):
    # Parsed candidates: TMFUSDT, TBTUSDT, BITOUSDT.
    # exchangeInfo validates only TMFUSDT.
    # Assert no events/*.jsonl row and scheduler state retains all three candidates.


def test_multi_symbol_pending_state_preserves_all_candidates(tmp_path, monkeypatch):
    # Run pending exchangeInfo path.
    # Assert candidate_symbols and parsed_candidate_symbols remain full set.


def test_multi_symbol_all_three_later_validate_emits_once(tmp_path, monkeypatch):
    # First poll partial validation -> no emit.
    # Second poll all validated -> exactly one multi-symbol event.


def test_multi_symbol_restart_does_not_duplicate_or_drop_symbols(tmp_path, monkeypatch):
    # Persist pending state, restart runner, all symbols validate.
    # Assert one event with all symbols.
```

**Step 2: Write failing unsafe-anchor tests**

Add tests:

```python
def test_bapi_multi_contract_missing_launch_time_does_not_use_article_release_date_anchor(tmp_path, monkeypatch):
    # Parsed symbols but no reliable launch times and no exchangeInfo onboardDate.
    # Assert no consumable event and no symbol_effective_launch_times_ms from releaseDate.


def test_bapi_multi_contract_missing_launch_time_does_not_use_legacy_max_age_anchor(tmp_path, monkeypatch):
    # Parsed symbols, no releaseDate, no onboardDate.
    # Assert no consumable event and no first_detected+max_age anchor.
```

**Step 3: Run and verify failures**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'multi_symbol or missing_launch_time' -q
```

Expected: FAIL due current partial emit/fallback behavior.

**Step 3.5: Run current parser suite before changing fallback parameters**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py -q
```

Expected: PASS before implementing strict fallback parameters. If this fails, fix existing parser regression first. The strict `allow_release_date_fallback=False` and `allow_legacy_max_age_fallback=False` calls apply only to BAPI multi-contract schedule paths; single-symbol BAPI and support detail paths keep legacy defaults.

**Step 4: Refactor validation emission guard**

Create a small helper in the runner or an existing Stage 1.5D module:

```python
def is_multi_symbol_article_ready_to_emit(candidate_symbols: list[str], validation_result: dict, effective_launch: dict) -> bool:
    candidates = list(candidate_symbols or [])
    validated = set(validation_result.get("validated_symbols") or [])
    pending = validation_result.get("pending_symbols") or []
    rejected = validation_result.get("rejected_symbols") or []
    launch_times = effective_launch.get("symbol_effective_launch_times_ms") or {}
    return (
        len(candidates) > 0
        and len(validated) == len(candidates)
        and set(candidates) == validated
        and not pending
        and not rejected
        and all(int(launch_times.get(sym) or 0) > 0 for sym in candidates)
    )
```

Use it in:

```text
first BAPI parse path
pending exchangeInfo revalidation path
restart recovered pending path
```

**Step 5: Make launch anchor builder strict for BAPI multi-contract**

Do not globally remove legacy behavior if older tests depend on it. Add a strict mode parameter:

```python
def build_effective_launch_times_ms(..., allow_release_date_fallback: bool = True, allow_legacy_max_age_fallback: bool = True) -> dict:
    ...
```

For BAPI multi-contract schedule events call:

```python
allow_release_date_fallback=False
allow_legacy_max_age_fallback=False
```

If safe anchors are missing, return empty/missing diagnostics and keep scheduler state pending or terminal diagnostic, but do not emit event.

**Step 6: Run focused tests**

Run same pytest command. Expected: PASS.

**Step 7: Commit Task A**

Run parser and 1.5D runner focused test suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -q
```

Expected: PASS.

Commit:

```bash
git add configs/base.py \
  src/research/external_signal_shadow/stage1_5d_live_event_source_parser.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture.json \
  tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_a827_real_frozen_fixture_metadata.json

git commit -m "fix(stage1_5d): parse bapi table launch schedules safely"
```

---

## 6. Add Stage 1.5D Runtime Gate Config And Writer

**Files:**
- Modify: `configs/base.py`
- Create or modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing runtime gate config tests**

Create `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py` with:

```python
def test_runtime_gate_config_defaults():
    from configs import base
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC >= 120
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_REVALIDATION_INTERVAL_SEC >= 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES >= 1
```

**Step 2: Implement config constants**

Add to `configs/base.py`:

```python
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_STALENESS_SEC = 180
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_REVALIDATION_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_5D_RUNTIME_GATE_MAX_CONSECUTIVE_FAILURES = 3
```

**Step 3: Write failing writer tests**

In `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`:

```python
def test_build_runtime_gate_initializing_has_no_fake_success_rate(tmp_path):
    from src.research.external_signal_shadow.stage1_5d_runtime_gate import build_stage1_5d_runtime_gate
    gate = build_stage1_5d_runtime_gate(
        output_root=str(tmp_path),
        runner_started_at_ms=1000,
        now_ms=1000,
        poll_count=0,
        successful_poll_count=0,
        consecutive_poll_failure_count=0,
        prior_stage_safety_prerequisite_met=False,
        live_public_readonly=True,
        fatal_blockers=[],
    )
    assert gate["decision"] == "stage1_5d_runtime_gate_initializing"
    assert gate.get("request_success_rate") is None
    assert gate["trade_signal_allowed"] is False
    assert gate["execution_feasibility_claim_allowed"] is False


def test_write_runtime_gate_is_atomic_and_readable(tmp_path):
    from src.research.external_signal_shadow.stage1_5d_runtime_gate import write_stage1_5d_runtime_gate_atomic
    gate = {"runtime_gate_schema_version": 1, "decision": "stage1_5d_runtime_gate_initializing", "source_root": str(tmp_path)}
    path = write_stage1_5d_runtime_gate_atomic(tmp_path, gate)
    assert path.name == "live_safety_gate_summary.json"
    assert path.exists()
```

**Step 4: Implement `stage1_5d_runtime_gate.py`**

Implement:

```python
RUNTIME_GATE_SCHEMA_VERSION = 1


def build_stage1_5d_runtime_gate(...):
    ...


def write_stage1_5d_runtime_gate_atomic(output_root: str | Path, gate: dict) -> Path:
    ...
```

Decision rules:

```text
fatal_blockers non-empty -> failed
not prior_stage_safety_prerequisite_met or successful_poll_count < 1 -> initializing
consecutive failures > max -> degraded
otherwise -> ready
```

Safety fields must be present and false.

**Step 5: Wire 1.5D runner**

In `run_stage1_5d_live_event_source_smoke_collector.py`:

```text
write INITIALIZING gate immediately after output dirs are ready and safety args pass
refresh gate after each poll/heartbeat with current counters
write STOPPED gate on normal exit if feasible
write FAILED gate on fatal blocker if feasible
```

Do not overwrite `binance_futures_launch_smoke_summary.json` during the run.

**Step 6: Run tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k 'runtime_gate' -q
```

Expected: PASS.

---

## 7. Add Stage 1.5F Runtime Gate Validator And CLI

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py`

**Step 1: Write failing validator tests**

In `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`:

```python
def test_validate_stage1_5d_runtime_gate_accepts_ready_same_root(tmp_path):
    from src.research.external_signal_shadow.stage1_5f_live_depth_observer_loader import validate_stage1_5d_runtime_gate
    root = tmp_path / "stage1_5d_root"
    root.mkdir()
    gate = build_ready_gate(root, generated_at_ms=10_000)
    gate_path = root / "live_safety_gate_summary.json"
    gate_path.write_text(json.dumps(gate))
    validate_stage1_5d_runtime_gate(str(gate_path), str(root / "events" / "*.jsonl"), now_ms=11_000)


def test_validate_stage1_5d_runtime_gate_rejects_unknown_decision(tmp_path):
    ...


def test_validate_stage1_5d_runtime_gate_rejects_root_mismatch(tmp_path):
    ...


def test_validate_stage1_5d_runtime_gate_rejects_stale_gate(tmp_path):
    ...


def test_validate_stage1_5d_runtime_gate_rejects_missing_or_true_safety_fields(tmp_path):
    ...
```

**Step 2: Run and verify failures**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  -k 'runtime_gate' -q
```

Expected: FAIL because validator does not exist.

**Step 3: Implement dedicated validator**

Add to `stage1_5f_live_depth_observer_loader.py`:

```python
def derive_stage1_5d_root_from_events_glob(events_glob: str) -> str:
    ...


def validate_stage1_5d_runtime_gate(gate_path: str, expected_events_glob: str, now_ms: int) -> dict:
    ...
```

Use allowlist only:

```text
accepted decision = stage1_5d_runtime_gate_ready
all other decisions fail closed
```

Require same-root canonical path equality between gate `source_root` and derived events root.

**Step 4: Add 1.5F CLI args**

In `run_stage1_5f_live_depth_observer.py` add:

```python
parser.add_argument("--stage1-5d-runtime-gate", type=str, default="")
parser.add_argument("--allow-historical-stage1-5d-safety-gate", action="store_true")
parser.add_argument("--historical-stage1-5d-gate-reason", type=str, default="")
```

Startup rules:

```text
if --stage1-5d-runtime-gate is provided:
  validate dedicated runtime gate with explicit now_ms from runner clock
elif --allow-historical-stage1-5d-safety-gate and --stage1-5d-summary and reason:
  validate legacy summary and record override
else:
  fail closed with blocker = stage1_5d_runtime_gate_missing
```

Do not silently use old `--stage1-5d-summary` as current runtime gate.

**Step 5: Add summary fields with defaults**

In `LiveDepthObserverSummary`, add defaulted fields:

```python
stage1_5d_gate_mode: str = "unknown"
stage1_5d_runtime_gate_path: str = ""
stage1_5d_runtime_gate_decision: str = ""
stage1_5d_runtime_gate_last_validated_at_ms: int | None = None
stage1_5d_runtime_gate_stale: bool = False
stage1_5d_runtime_gate_invalid_count: int = 0
cross_root_upstream_summary_dependency: bool = False
historical_stage1_5d_gate_reason: str = ""
block_new_event_admission: bool = False
runtime_gate_diagnostic_count: int = 0
```

Maintain backwards compatibility for old summary loading.

**Step 6: Run focused tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  -k 'runtime_gate or historical_stage1_5d_gate or cross_root' -q
```

Expected: PASS.

---

## 8. Implement Periodic Gate Revalidation And Admission Blocking

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing periodic revalidation tests**

Add tests:

```python
def test_stage1_5f_periodic_gate_revalidation_blocks_new_admission_but_continues_active_observation(tmp_path, monkeypatch):
    # Poll 1 gate ready, one event accepted/active.
    # Poll 2 gate stale/degraded, new event appears.
    # Assert active depth request continues; new event is not admitted; pending state is not deleted.


def test_stage1_5f_runtime_gate_invalid_emits_diagnostic(tmp_path, monkeypatch):
    # Gate becomes corrupt/truncated after startup.
    # Assert diagnostic counter increments and new admission is blocked.
```

**Step 2: Run and verify failures**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'periodic_gate_revalidation or runtime_gate_invalid' -q
```

Expected: FAIL.

**Step 3: Wire revalidation cadence**

In 1.5F loop:

```text
if now_ms >= next_runtime_gate_validation_at_ms:
  validate runtime gate
  update block_new_event_admission
  update diagnostics and summary fields
```

Admission rule:

```text
if block_new_event_admission:
  skip new flat_event admission
  continue existing active observation snapshot requests
  preserve pending state
```

Do not stop active 12h observation only because 1.5D gate is stale.

**Step 4: Run focused tests**

Run same pytest command. Expected: PASS.

---

## 9. Add A827 Late Evidence Boundary Tests

**Files:**
- Modify: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- Modify if needed: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`

**Step 1: Write precise A827 late tests**

Add tests:

```python
def test_a827_pre_bootstrap_late_fixture_is_ignored_historical_anchor_pre_bootstrap(tmp_path, monkeypatch):
    # Bootstrap watermark after A827 launch anchors.
    # Feed A827 event.
    # Assert terminal ignored state, no accepted event, no depth.


def test_a827_post_bootstrap_late_resolved_fixture_is_rejected_launch_anchor_age_exceeded(tmp_path, monkeypatch):
    # Bootstrap before event detected, but now_ms beyond recovery start window after launch anchor.
    # Assert rejected_launch_anchor_age_exceeded, no clean/recovery start.


def test_a827_late_fixture_never_marks_clean_or_recovery_start(tmp_path, monkeypatch):
    # Assert evidence_start_class is not clean_start or recovery_validation_only.
```

**Step 2: Run tests**

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'a827_pre_bootstrap or a827_post_bootstrap or a827_late_fixture' -q
```

Expected: These are regression verification tests for Task 3/5 + 1.5F loader integration, not new threshold-driving tests. If they fail, fix the strict launch-time parser / effective-anchor / 1.5F loader connection; do not relax 1.5F thresholds.

---

## 10. Commit Task B

Run focused Stage 1.5D runtime gate and Stage 1.5F gate tests:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k 'runtime_gate or historical_stage1_5d_gate or cross_root or a827' -q
```

Expected: PASS.

Commit:

```bash
git add configs/base.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py

git commit -m "fix(stage1_5f): require same-root stage1_5d runtime gate"
```

---

## 11. Full Verification

Run the focused suite:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_config.py \
  tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

Run safety grep:

```bash
rg -n \
'paper_trading_allowed\s*[:=]\s*True|live_trading_allowed\s*[:=]\s*True|execution_engine_allowed\s*[:=]\s*True|trade_signal_allowed\s*[:=]\s*True|alpha_interpretation_allowed\s*[:=]\s*True|execution_feasibility_claim_allowed\s*[:=]\s*True' \
configs src scripts
```

Expected:

```text
pytest focused suite passes
safety grep has no production code matches
```

Run style checks if available:

```bash
make lint
```

If `make lint` is not configured or fails on unrelated legacy files, capture exact output and do not claim full lint pass.

---

## 12. Deployment Plan

Deploy only after both commits pass local verification.

Scoped server sync only:

```bash
git status --short
git diff --check
git diff --name-only <base_commit>..<commitB>
```

The deploy file list must be exactly the changed implementation/test/config/doc files approved for Commit A and Commit B. Do not rsync the whole workspace by default. For each deployed file, compare local and server SHA256 after sync.

Before stopping an old 1.5F root, inspect its summary. If `active_observation_count > 0`, keep the old root running in drain-only mode until its `observation_window_end_ms` completes; do not truncate active evidence.

Start new roots with new suffix:

```text
1.5D root suffix = 7d_bapi_table_schedule_runtime_gate_hotfix
1.5F root suffix = 7d_bapi_table_schedule_runtime_gate_hotfix
```

Deployment order:

```text
1. Stop old 1.5D and 1.5F tmux sessions.
2. Start new 1.5D root.
3. Confirm live_safety_gate_summary.json exists and decision becomes stage1_5d_runtime_gate_ready after first successful poll.
4. Start new 1.5F root using --stage1-5d-runtime-gate pointing to current 1.5D root.
5. Confirm 1.5F summary reports same-root runtime gate and no cross-root dependency.
```

1.5F startup must use:

```bash
--stage1-5d-events-glob "$STAGE1_5D_EVENTS_OUT/events/*.jsonl" \
--stage1-5d-runtime-gate "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" \
--stage1-5e-summary data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json
```

Do not use `--stage1-5d-summary` for runtime gate unless explicitly using emergency historical override.

---

## 13. Production Acceptance Checks

Check runtime gate:

```bash
cat "$STAGE1_5D_EVENTS_OUT/live_safety_gate_summary.json" | python3 -m json.tool | grep -E \
'"decision"|"source_root"|"poll_count"|"successful_poll_count"|"last_heartbeat_at_ms"|"last_successful_poll_at_ms"|"trade_signal_allowed"|"paper_trading_allowed"|"live_trading_allowed"|"execution_engine_allowed"|"alpha_interpretation_allowed"|"execution_feasibility_claim_allowed"'
```

Expected:

```text
decision = stage1_5d_runtime_gate_ready
poll_count >= 1
successful_poll_count >= 1
all safety flags false
```

Check same-root binding from 1.5F:

```bash
python3 - <<'PY'
import json, os, pathlib
stage1_5d = pathlib.Path(os.environ['STAGE1_5D_EVENTS_OUT']).resolve()
stage1_5f = pathlib.Path(os.environ['STAGE1_5F_OUT']).resolve()
gate = json.loads((stage1_5d / 'live_safety_gate_summary.json').read_text())
summary = json.loads((stage1_5f / 'live_depth_observer_summary.json').read_text())
print({
    'gate_decision': gate.get('decision'),
    'gate_source_root': gate.get('source_root'),
    'stage1_5d_root': str(stage1_5d),
    'same_root_gate': pathlib.Path(gate.get('source_root', '')).resolve() == stage1_5d,
    'stage1_5d_gate_mode': summary.get('stage1_5d_gate_mode'),
    'cross_root_upstream_summary_dependency': summary.get('cross_root_upstream_summary_dependency'),
    'block_new_event_admission': summary.get('block_new_event_admission'),
})
PY
```

Expected:

```text
same_root_gate = True
stage1_5d_gate_mode = runtime_gate
cross_root_upstream_summary_dependency = False
block_new_event_admission = False when gate is fresh/ready
```

Check A827 fixture regression locally:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  -k 'a827' -q
```

Expected: PASS.

Check live future event behavior:

```text
Next fresh Binance table/list launch article should reach 1.5D consumable event after all exchangeInfo validations pass.
If launch anchor is future, 1.5F should hold pending until anchor.
If launch anchor is stale beyond recovery window, 1.5F should reject/ignore according to launch gate rules.
No pre-launch depth request is allowed.
```

---

## 14. Rollback

Rollback Task A only:

```text
Revert parser/scheduler commit.
BAPI transport and support fallback remain.
Risk: future table/list launch schedule articles may again be missed.
```

Rollback Task B only:

```text
Revert runtime gate commit.
Emergency operation can use historical summary only with explicit override and documented reason.
Risk: cross-root safety gate dependency returns, but no trading or execution permissions are opened.
```

Never rewrite old roots to make A827, POPMARTUSDT, or any stale event appear clean.
