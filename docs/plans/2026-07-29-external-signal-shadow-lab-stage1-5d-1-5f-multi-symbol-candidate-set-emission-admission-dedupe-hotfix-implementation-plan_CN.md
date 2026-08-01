# Stage 1.5D / 1.5F Multi-Symbol Candidate-Set Emission and Admission Dedupe Hotfix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 2026-07-29 `93b5...` multi-symbol 事故：1.5D 只在完整且安全的 candidate set ready 时写一条 full article row，1.5F 按现有 stable event-symbol key 做全状态去重与 batch-safe admission，1.5G 能拒绝污染 root。

**Architecture:** 1.5D 增加 strict candidate-set readiness、strict anchor source policy、durable emitted terminal scheduler contract、event-stream emission index rebuild。1.5F 以 latest state by `event_symbol_id` 为基础建立 `stable_event_symbol_key -> list[latest_states]`，检测 collision，使用 append-only batch registry 保证 sibling symbols 与 watermark crash consistency。1.5G 增加 duplicate stable identity integrity blocker，防止旧污染 root 被误判为 clean/quarantine evidence。

**Tech Stack:** Python, pytest, JSON/JSONL append-only artifacts, local fixture-driven runner tests, Binance BAPI/exchangeInfo frozen fixtures, Stage 1.5D/1.5F/1.5G offline regression tests.

---

## 0. Non-Negotiable Rules

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

Execution rules:

```text
1. TDD first; every behavior change starts with a failing test.
2. Do not mutate or delete old production roots.
3. Do not turn 93b5 polluted root into clean evidence.
4. Fail closed on identity/collision/schema uncertainty.
5. Preserve append-only audit semantics.
6. Use exact commands with PYTHONPATH=src:. .venv/bin/python.
```

---

## Task 1: Preflight and Fixture Availability

**Files:**
- Read: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Read: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Read: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Read: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Read: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Read: `tests/fixtures/external_signal_shadow/stage1_5d/`

**Step 1: Locate all Stage 1.5D event append paths**

```bash
rg -n "validated_symbols|symbols_override|append_jsonl\(stream_paths\[\"events\"\]|detail_retry_state\.pop|terminal_state|serialize_retry_articles|write_detail_retry_scheduler_state" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py
```

Expected:

```text
All current partial emit and scheduler terminal paths are known.
serialize_retry_articles() is confirmed as persistence boundary.
```

**Step 2: Locate all Stage 1.5F admission and watermark paths**

```bash
rg -n "flatten_event_symbols|make_event_symbol_id|make_stable_event_symbol_key|event_symbol_id in states|terminal_states_by_stable_event_symbol_key|update_watermark_with_event|append_jsonl\(accepted_path|upsert_pending_state_with_event_revision|compact_observer_state_jsonl|load_latest_state_by_event_symbol_id" \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
```

Expected:

```text
Immediate per-sibling watermark update sites are identified.
Existing pending revision helper is confirmed.
```

**Step 3: Check 93b5 fixture availability**

```bash
ls -lh tests/fixtures/external_signal_shadow/stage1_5d/*93b5* 2>/dev/null || true
ls -lh tests/fixtures/external_signal_shadow/stage1_5d/
```

If real 93b5 payload is unavailable, use a synthetic offline fixture with exact symbols/times from production evidence and metadata:

```json
{
  "data_quality": "synthetic_offline_fixture",
  "articleCode": "93b5cd2280874d9cb4303827374b940d",
  "expected_symbols": ["PYPLUSDT", "GSUSDT", "SMHUSDT"],
  "expected_launch_times_ms": {
    "PYPLUSDT": 1785315600000,
    "GSUSDT": 1785315900000,
    "SMHUSDT": 1785316200000
  }
}
```

If real payload is available, metadata must include:

```text
request_id
request_manifest_path
fetched_at_ms
raw_payload_sha256
fixture_sha256
payload_trusted
parser_version_before
source_transport
content_provenance
data_quality = real_frozen_bapi_payload
```

**Step 4: Record any divergence**

If grep output shows different function names or writer paths, update this plan before code changes.

---

## Task 2: Stage 1.5D Candidate Identity and Strict Readiness Contract

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing candidate hash tests**

Add tests:

```text
test_candidate_symbol_set_hash_is_order_insensitive_and_normalized
test_candidate_symbol_set_hash_preserves_ordered_symbols_for_audit
```

Required behavior:

```text
normalize = strip + uppercase + unique + lexicographic sort
serialize = json.dumps(symbols, ensure_ascii=True, separators=(",", ":"))
hash = sha256(serialized bytes)
candidate_symbols_ordered preserves first-seen article order
```

**Step 2: Write failing strict readiness tests**

Add tests:

```text
test_candidate_set_ready_when_all_symbols_pending_trading_with_strict_anchors
test_staggered_symbols_do_not_wait_until_all_trading
test_candidate_set_rejects_article_release_date_anchor
test_candidate_set_rejects_legacy_max_age_anchor
test_candidate_set_rejects_missing_anchor_source
test_candidate_set_requires_validation_partition_complete
test_candidate_set_requires_validated_pending_partition_disjoint
test_candidate_set_rejects_unknown_status_even_if_exchangeinfo_present
```

Readiness must require:

```text
set(validated_symbols) union set(pending_symbols) == set(candidate_symbols)
set(validated_symbols) intersection set(pending_symbols) == empty
rejected_symbols == []
every symbol appears in symbol_exchangeinfo
every metadata has allowed contractType/quoteAsset/marginAsset
every status in EXTERNAL_SIGNAL_STAGE1_5D_VALIDATABLE_SYMBOL_STATUSES
every symbol has effective launch time > 0
every symbol anchor source in {detail_symbol_launch_time, exchangeinfo_onboard_date}
```

Must reject sources:

```text
article_release_date
legacy_max_age
missing
conflict
ambiguous
```

**Step 3: Implement helpers**

Implement:

```python
def build_candidate_symbol_set_identity(candidate_symbols: list[str]) -> dict: ...
def is_multi_symbol_article_state(state: dict, extraction_result: dict | None = None) -> bool: ...
def is_multi_symbol_candidate_set_ready_to_emit(candidate_symbols: list[str], validation_result: dict, effective_launch: dict, allowed_statuses: tuple[str, ...], allowed_anchor_sources: tuple[str, ...]) -> bool: ...
def build_symbol_effective_launch_time_sources(candidate_symbols: list[str], symbol_launch_times_ms: dict, symbol_onboard_times_ms: dict, effective_launch: dict) -> dict[str, str]: ...
```

Important: do **not** use inline `len(state.get("candidate_symbols") or []) > 1` as the multi-symbol/single-symbol switch. Use `is_multi_symbol_article_state(...)`, and only allow single-symbol path when candidate set is trusted and count is exactly 1.

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k "candidate_symbol_set or strict_anchor or validation_partition or staggered_symbols" -q
```

Expected: pass.

---

## Task 3: Stage 1.5D Scheduler Schema and Terminal Emitted Contract

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing scheduler roundtrip tests**

Add tests:

```text
test_emitted_all_symbols_is_terminal_for_retry_selection
test_emitted_terminal_fields_survive_scheduler_roundtrip
test_old_scheduler_schema_loads_with_safe_defaults
test_emitted_article_is_not_reselected_after_restart
```

Required terminal fields:

```text
terminal_state = true
terminal_reason = multi_symbol_candidate_set_emitted
terminal_at_ms
status = emitted_all_symbols
symbol_validation_status = emitted_all_symbols
emission_id
candidate_symbol_set_hash
candidate_symbol_set_hash_version
event_id
event_stream_path
parser_payload_hash
symbol_effective_launch_time_sources
launch_anchor_policy = bapi_multi_contract_strict
```

**Step 2: Update serializer and metadata version**

Modify `serialize_retry_articles()` to preserve new fields explicitly. Bump scheduler metadata version only if needed, and make old metadata load with safe defaults.

**Step 3: Update retry selection terminal checks**

Where scheduler currently skips:

```python
if state.get("terminal_state"):
    continue
```

ensure emitted terminal state sets `terminal_state = True` and never re-enters detail retry or validation selection.

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k "emitted_all_symbols or scheduler_roundtrip or old_scheduler_schema" -q
```

Expected: pass.

---

## Task 4: Stage 1.5D Validated Event-Stream Emission Index Rebuild

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing emission id and rebuild tests**

Add tests:

```text
test_build_multi_symbol_emission_id_is_stable_for_same_article_candidate_set
test_existing_event_stream_rebuilds_emission_index_from_valid_full_row
test_event_stream_rebuild_rejects_partial_row_with_full_candidate_hash
test_event_stream_rebuild_rejects_stored_hash_mismatch
test_event_stream_rebuild_rejects_duplicate_emission_id_different_payload
test_event_stream_rebuild_rejects_malformed_jsonl_fail_safe
```

Accepted event row criteria:

```text
multi_symbol_emission_mode == all_or_none_candidate_set
symbol_validation_status == validated_candidate_set
source_article_id non-empty
event_type == futures_contract_launch
symbols count > 1
recomputed_hash(symbols) == stored candidate hash
recomputed emission_id == stored emission_id
```

Rejected rebuild rows must produce registry integrity diagnostic and block new emission for that article, not silently append another event.

**Step 2: Implement rebuild helpers**

```python
def build_multi_symbol_emission_id(source_article_id: str, event_type: str, candidate_symbol_set_hash: str) -> str: ...
def build_emission_index_key(source_article_id: str, candidate_symbol_set_hash: str) -> str: ...
def validate_emitted_candidate_set_event_row(row: dict) -> tuple[bool, str, dict]: ...
def rebuild_emission_index_from_events(output_root: Path) -> tuple[dict, list[dict]]: ...
```

**Step 3: Fixed crash write ordering**

Normal emission order must be:

```text
1. append event row
2. fsync/close through existing append helper if supported
3. write terminal scheduler state
```

**Step 4: Write crash-window tests**

Add:

```text
test_crash_after_event_append_before_state_write_does_not_duplicate
test_crash_after_state_write_before_event_append_reconciles_missing_event_or_blocks_manual_review
```

If terminal state points to missing event row and preserved full `norm_event` is unavailable, fail-safe behavior is:

```text
manual_review_required = true
block_new_emission_for_article = true
no silent duplicate append
```

Do not auto-rebuild active evidence from incomplete state.

**Step 5: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  -k "emission_index or emission_id or crash_after" -q
```

Expected: pass.

---

## Task 5: Wire Stage 1.5D Candidate-Set Gate Into All Emit Paths

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`

**Step 1: Write failing edge tests**

Add:

```text
test_parser_returns_three_symbols_but_state_initialization_none_does_not_take_single_symbol_path
test_93b5_prelaunch_all_validatable_emits_one_full_row
test_93b5_partial_trading_status_does_not_emit_subset_row
test_93b5_all_trading_later_does_not_emit_duplicate_full_row
test_list_poll_does_not_reset_pending_candidate_state_to_title_symbol_missing
test_hard_rejected_symbol_blocks_entire_multi_symbol_article
```

**Step 2: Replace unsafe inline branch**

Do not implement:

```python
... if len(state.get("candidate_symbols") or []) > 1 else bool(validation_result["validated_symbols"])
```

Use explicit decision:

```python
article_multi = is_multi_symbol_article_state(state, extraction_res)
if article_multi:
    candidate_ready = is_multi_symbol_candidate_set_ready_to_emit(...)
else:
    candidate_ready = is_single_symbol_candidate_ready_to_emit(...)
```

Single-symbol path requires:

```text
trusted candidate_symbols exists
candidate count == 1
symbol validatable/emittable per existing semantics
anchor policy remains safe
```

**Step 3: For multi-symbol not ready**

Persist pending state:

```text
symbol_validation_status = pending_candidate_set_readiness
pending_reason = multi_symbol_candidate_set_not_ready
exchangeinfo_visible_symbols
exchangeinfo_missing_symbols
hard_rejected_symbols
symbol_exchangeinfo_statuses
symbol_effective_launch_time_sources
launch_anchor_policy
next_exchangeinfo_validation_at_ms
```

Do not append event. Do not `pop(code)`. Do not reset candidate symbols.

**Step 4: For multi-symbol ready**

Emit exactly one full row with:

```text
symbols = candidate_symbols_ordered
multi_symbol_emission_mode = all_or_none_candidate_set
multi_symbol_candidate_set_hash
emission_id
symbol_validation_status = validated_candidate_set
symbol_exchangeinfo_statuses
symbol_effective_launch_time_sources
launch_anchor_policy = bapi_multi_contract_strict
```

Then set scheduler terminal emitted state per Task 3.

**Step 5: Static grep guard**

Run:

```bash
rg -n "symbols_override=validation_result\[\"validated_symbols\"\]|if validation_result\[\"validated_symbols\"\]" \
  scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
```

Expected: no unsafe raw multi-symbol path remains. If a single-symbol compatibility path remains, it must call explicit single-symbol helper and be documented in code.

**Step 6: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py \
  -q
```

Expected: pass.

---

## Task 6: Stage 1.5D Summary and Runtime Gate Metrics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py`
- Modify: `src/research/external_signal_shadow/stage1_5d_runtime_gate.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py`

Add defaulted fields:

```text
multi_symbol_candidate_set_emission_enabled
multi_symbol_candidate_set_ready_count
multi_symbol_candidate_set_pending_count
multi_symbol_partial_emit_prevented_count
multi_symbol_full_emit_count
multi_symbol_emission_registry_count
multi_symbol_candidate_set_hash_mismatch_count
multi_symbol_candidate_state_reset_prevented_count
multi_symbol_validation_rejected_count
strict_anchor_policy_rejected_count
emitted_terminal_state_count
```

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  -q
```

Expected: pass with old summary/root compatibility.

---

## Task 7: Stage 1.5F Latest-State Stable-Key Index and Missing Identity Policy

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing latest-state grouping tests**

Add:

```text
test_pending_active_completed_history_same_event_symbol_id_is_not_collision
test_same_stable_key_two_distinct_event_symbol_ids_is_collision
test_compaction_and_collision_detection_produce_same_result
test_startup_detects_two_active_states_with_same_stable_key
test_startup_detects_active_and_completed_same_stable_key
test_identity_collision_does_not_delete_existing_state
```

Grouping order is mandatory:

```text
raw state history
-> latest state by event_symbol_id
-> group latest states by stable_event_symbol_key
-> detect distinct event_symbol_id collision
```

**Step 2: Missing stable key policy tests**

Add:

```text
test_missing_stable_key_is_rebuilt_only_from_complete_identity
test_active_missing_identity_blocks_new_admission
test_missing_identity_does_not_delete_or_merge_state
```

Policy:

```text
if source_article_id + event_type + symbol complete:
  rebuild stable_event_symbol_key deterministically
  record stable_key_rebuilt = true
else:
  identity_missing = true
  block new admission
  preserve existing active observation
  do not create second state
  do not guess identity
```

**Step 3: Implement helpers**

```python
def load_latest_states_by_event_symbol_id(observer_state_jsonl: str) -> dict[str, EventSymbolState]: ...
def rebuild_missing_stable_event_symbol_key_if_safe(state: EventSymbolState) -> tuple[EventSymbolState, dict]: ...
def group_latest_states_by_stable_event_symbol_key(latest: dict[str, EventSymbolState]) -> dict[str, list[EventSymbolState]]: ...
def detect_stable_event_symbol_key_collisions(grouped: dict[str, list[EventSymbolState]]) -> list[dict]: ...
```

Do not scan raw history directly for collision.

**Step 4: Startup blocker**

If collision or unrebuildable active identity missing exists:

```text
block_new_admission_due_to_identity_collision = true
block_new_event_admission = true
append sample-capped diagnostic
continue heartbeat/summary safely
```

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "stable_key or collision or missing_identity" -q
```

Expected: pass.

---

## Task 8: Stage 1.5F Runtime Collision Block and Immutable Pending Revision Lineage

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing admission order tests**

Add:

```text
test_exact_row_replay_does_not_increment_revision_duplicate_counter
test_pending_revision_preserves_event_symbol_id
test_pending_revision_does_not_create_second_state
test_active_revision_does_not_move_observation_window
test_runtime_collision_blocks_subsequent_new_admission
test_terminal_revision_seen_does_not_reopen_clean_evidence
```

**Step 2: Define immutable and mutable fields**

Pending revision immutable:

```text
event_symbol_id
stable_event_symbol_key
initial_source_article_id
symbol
initial_detected_at_ms
observation_started_at_ms if already active
observation_window_start_ms if already active
observation_window_end_ms if already active
```

Pending revision mutable:

```text
latest_source_event_id
latest_source_payload_hash
revision_seen_count
anchor candidates
launch metadata if higher confidence and non-conflicting
```

Anchor update policy:

```text
pending: allow higher-confidence non-conflicting anchor update
pending conflict: status = pending_anchor_conflict
active/completed: do not move observation window; diagnostic only
```

**Step 3: Implement replay/revision classifier**

Return classes:

```text
exact_replay_noop
pending_revision_upsert
active_or_completed_duplicate_revision
terminal_revision_seen
identity_collision_blocked
new_event_symbol
```

Runtime collision must set:

```text
block_new_admission_due_to_identity_collision = true
block_new_event_admission = true
```

and affect subsequent rows in the same poll.

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "revision or exact_row_replay or runtime_collision" -q
```

Expected: pass.

---

## Task 9: Stage 1.5F Durable Event Batch Registry

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Decision:** Use append-only `event_batch_registry.jsonl`. Do not rely only on sibling state fields.

Batch statuses:

```text
batch_started
siblings_partially_durable
siblings_all_durable
watermark_committed
batch_blocked
```

Registry fields:

```text
event_batch_id
source_article_id
source_event_id
candidate_set_hash
expected_stable_keys
durable_stable_keys
pre_row_watermark_max_seen_detected_at_ms
status
created_at_ms
updated_at_ms
block_reason
```

**Step 1: Write failing batch registry tests**

Add:

```text
test_batch_registry_records_started_and_all_durable
test_batch_registry_blocks_on_orphan_accepted_row
test_batch_registry_survives_restart_with_partial_siblings
test_other_event_watermark_advance_does_not_drop_remaining_batch_siblings
```

Accepted row exists but state missing policy:

```text
orphan_accepted_row
batch_blocked
block new admission
no automatic active state reconstruction
```

**Step 2: Implement registry helpers**

```python
def build_event_batch_id(event_row: dict, candidate_set_hash: str) -> str: ...
def append_event_batch_registry_row(output_root: str, row: dict, now_ms: int) -> None: ...
def load_latest_event_batch_registry(output_root: str) -> dict[str, dict]: ...
def update_batch_registry_status(...): ...
```

**Step 3: Add state model default fields**

`EventSymbolState` defaults:

```text
event_batch_id: str = ""
batch_candidate_set_hash: str = ""
batch_symbol_count: int | None = None
batch_registration_status: str = ""
```

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "batch_registry or orphan_accepted or partial_siblings" -q
```

Expected: pass.

---

## Task 10: Stage 1.5F Batch Processing and Watermark Commit

**Files:**
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_watermark.py` only if API support is needed
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Write failing batch processing tests**

Add:

```text
test_multi_symbol_event_row_processes_all_symbols_before_watermark_update
test_three_staggered_symbols_promote_at_their_own_anchor
test_watermark_updates_once_after_all_siblings_durable
test_crash_after_first_sibling_state_write_recovers_batch
test_crash_after_second_sibling_acceptance_recovers_remaining_symbol
test_crash_before_watermark_update_does_not_duplicate_accepted_rows
```

**Step 2: Refactor event row processing into batch function**

Processing order:

```text
1. read original event row
2. compute event_batch_id and candidate_set_hash
3. append batch_started
4. flatten symbols
5. classify every sibling with same pre-row watermark snapshot
6. apply replay/revision/collision checks per sibling
7. persist every sibling state/accepted/pending/terminal result
8. verify all expected stable keys durable
9. append siblings_all_durable
10. update watermark once with original event row
11. append watermark_committed
```

Watermark means:

```text
article row fully registered
```

not:

```text
all siblings accepted
```

**Step 3: Ensure pending siblings survive later global watermark changes**

When an event batch is partially durable and another event advances watermark, remaining siblings must still be recoverable by `event_batch_id` and stable keys, not lost as pre-watermark.

**Step 4: Run tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "multi_symbol_event_row or three_staggered or watermark_updates_once or crash_after" -q
```

Expected: pass.

---

## Task 11: Stage 1.5F Summary and Diagnostics

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
- Modify: `src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py`
- Modify: `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

Add defaulted summary fields:

```text
stable_event_symbol_full_state_dedupe_enabled
exact_event_replay_suppressed_total
duplicate_revision_admission_suppressed_total
canonical_identity_collision_total
duplicate_active_article_symbol_count
batch_watermark_update_enabled
same_event_sibling_watermark_suppressed_count
partial_revision_after_acceptance_count
contaminated_event_symbol_count
block_new_admission_due_to_identity_collision
batch_registry_blocked_count
orphan_accepted_row_count
stable_key_rebuilt_count
missing_identity_blocker_count
```

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "summary or dedupe or collision or batch_registry" -q
```

Expected: pass with old root compatibility.

---

## Task 12: Stage 1.5G Duplicate Identity Integrity Blocker

**Files:**
- Modify: `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py`
- Modify: `scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py` only if CLI output needs fields
- Test: `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py`
- Test: relevant Stage 1.5G review tests

**Step 1: Write failing tests**

Add:

```text
test_1_5g_rejects_duplicate_stable_event_symbol_ids
test_93b5_contaminated_fixture_is_not_clean_or_quarantine_pass
test_clean_distinct_three_symbols_remain_valid_inputs
```

Integrity blocker:

```text
duplicate_stable_event_symbol_identity
partial_multisymbol_event_revision
```

This must not loosen any clean/quarantine threshold. It only blocks polluted inputs.

**Step 2: Implement loader/review blocker**

When loading accepted rows and observer states:

```text
build stable_event_symbol_key per latest event_symbol_id/state
if same stable key maps to multiple event_symbol_id in accepted/active/completed evidence:
  clean_depth_evidence_pass = false
  quarantined_depth_evidence_pass = false
  blocker includes duplicate_stable_event_symbol_identity
```

Distinct symbols from same article remain valid:

```text
article|PYPLUSDT
article|GSUSDT
article|SMHUSDT
```

are three different stable keys.

**Step 3: Run Stage 1.5G tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  -q
```

Expected: pass.

---

## Task 13: 93b5 End-to-End Fixture

**Files:**
- Create or modify: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_93b5_real_frozen_fixture.json`
- Create or modify: `tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_93b5_real_frozen_fixture_metadata.json`
- Test: `tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`

**Step 1: Create fixture with provenance**

If real payload unavailable, use synthetic fixture and declare it. Do not perform network fetch inside tests.

Metadata must include either:

```text
data_quality = real_frozen_bapi_payload
```

or:

```text
data_quality = synthetic_offline_fixture
```

**Step 2: Parser test**

Assert parser returns:

```text
symbols = [PYPLUSDT, GSUSDT, SMHUSDT]
launch times = 1785315600000, 1785315900000, 1785316200000
```

**Step 3: 1.5D staggered test**

Expected:

```text
pre-launch all PENDING_TRADING visible -> one full row
09:00 partial TRADING -> no new row
09:05 partial TRADING -> no new row
09:10 all TRADING -> no duplicate row
```

**Step 4: 1.5F staggered test**

Expected:

```text
before 09:00 -> three durable pending states
09:01 -> PYPLUSDT active, GS/SMH pending
09:06 -> PYPL/GS active, SMH pending
09:11 -> all active
```

Run:

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -k "93b5 or candidate_set or staggered" -q
```

Expected: pass.

---

## Task 14: Regression and Static Safety Verification

**Files:**
- No source changes unless failures expose defects.

**Step 1: Focused Stage 1.5D/1.5F/1.5G tests**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_parser.py \
  tests/research/external_signal_shadow/test_stage1_5d_a827_boundary_regression.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py \
  -q
```

**Step 2: Broader stage suites**

```bash
PYTHONPATH=src:. .venv/bin/python -m pytest tests/research/external_signal_shadow tests/scripts/external_signal_shadow -q
```

If this fails due unrelated legacy failures, record exact failures and still report focused suite result separately.

**Step 3: Safety grep**

Scan only production/config code, not negative tests:

```bash
rg -n "trade_signal_allowed\s*=\s*True|paper_trading_allowed\s*=\s*True|live_trading_allowed\s*=\s*True|execution_engine_allowed\s*=\s*True|alpha_interpretation_allowed\s*=\s*True|execution_feasibility_claim_allowed\s*=\s*True" \
  configs src scripts
```

Expected: no output.

**Step 4: Lint/check**

```bash
git diff --check
make lint
make test
```

If `make test` is too broad and fails legacy tests, record exact failures and do not claim full-suite pass.

---

## Task 15: Dated Deployment Runbook and Rollback

**Files:**
- Create: `docs/reviews/2026-07-29-stage1-5d-1-5f-multisymbol-hotfix-deployment-review_CN.md`

Do not rewrite the historical 2026-06-26 review as the primary deployment runbook. If needed, add only a pointer from the old review to the dated amendment later.

Runbook must include:

```text
1. clean worktree check
2. local commit SHA record
3. scoped file sync or controlled project sync
4. server per-file SHA256 comparison
5. old root active states grouped by source_article_id
6. stop or drain-only decision
7. start new 1.5D with suffix 7d_multisymbol_candidate_set_dedupe_hotfix
8. wait same-root live_safety_gate_summary.json READY
9. bootstrap new 1.5F watermark
10. start new 1.5F normal observer
11. verify cross_root_upstream_summary_dependency=false
12. verify identity/collision/batch metrics
13. rollback Stage 1.5D command
14. rollback Stage 1.5F command
15. explicit ban: old polluted root cannot become formal evidence
```

New root suffix:

```text
7d_multisymbol_candidate_set_dedupe_hotfix
```

**Verification commands in runbook must include:**

```text
multi_symbol_candidate_set_emission_enabled
multi_symbol_partial_emit_prevented_count
emitted_terminal_state_count
stable_event_symbol_full_state_dedupe_enabled
canonical_identity_collision_total
block_new_admission_due_to_identity_collision
batch_registry_blocked_count
orphan_accepted_row_count
cross_root_upstream_summary_dependency
```

---

## Task 16: Final Commit Split

Suggested commits:

```bash
git add scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py \
  src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py \
  src/research/external_signal_shadow/stage1_5d_live_event_source_summary.py \
  src/research/external_signal_shadow/stage1_5d_runtime_gate.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py \
  tests/research/external_signal_shadow/test_stage1_5d_live_event_source_summary.py \
  tests/research/external_signal_shadow/test_stage1_5d_runtime_gate.py \
  tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_93b5_real_frozen_fixture.json \
  tests/fixtures/external_signal_shadow/stage1_5d/bapi_article_detail_93b5_real_frozen_fixture_metadata.json
git commit -m "fix(stage1.5d): emit multi-symbol candidate sets atomically"
```

```bash
git add src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py \
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_summary.py \
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py \
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_models.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
git commit -m "fix(stage1.5f): dedupe stable event-symbol admission batches"
```

```bash
git add src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py \
  scripts/external_signal_shadow/review_stage1_5g_live_depth_evidence.py \
  tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_loader.py
git commit -m "fix(stage1.5g): block duplicate stable identity evidence"
```

```bash
git add docs/reviews/2026-07-29-stage1-5d-1-5f-multisymbol-hotfix-deployment-review_CN.md \
  docs/plans/2026-07-29-external-signal-shadow-lab-stage1-5d-1-5f-multi-symbol-candidate-set-emission-admission-dedupe-hotfix-implementation-plan_CN.md \
  docs/designs/2026-07-29-external-signal-shadow-lab-stage1-5d-1-5f-multi-symbol-all-or-none-emission-admission-dedupe-hotfix-design_CN.md
git commit -m "docs(stage1.5): plan multisymbol candidate-set hotfix deployment"
```

Before committing, run:

```bash
git status --short
git diff --check
```

Do not include unrelated untracked docs unless explicitly approved.

---

## Final Acceptance Criteria

```text
1. 1.5D strict readiness rejects unsafe anchor fallback sources.
2. 1.5D full candidate-set row emits before first launch when all symbols are exchangeInfo-validatable and anchored.
3. 1.5D emits no partial subset rows during staggered TRADING status changes.
4. 1.5D emitted_all_symbols is terminal_state=true and survives scheduler roundtrip/restart.
5. 1.5D event-stream rebuild validates emission_id/hash and rejects malformed/partial rows fail-safe.
6. 1.5F collision detection uses latest state by event_symbol_id, not raw state history.
7. 1.5F missing stable key is rebuilt only from complete identity; otherwise blocks new admission.
8. 1.5F pending revisions preserve event_symbol_id and do not create second state lineage.
9. 1.5F batch registry reaches watermark_committed only after all siblings durable.
10. 1.5F exact replay does not inflate duplicate revision counters every poll.
11. 1.5G rejects duplicate stable event-symbol identity pollution.
12. 93b5 fixture reproduces fixed behavior end-to-end.
13. Runtime gate remains same-root; cross_root_upstream_summary_dependency=false.
14. All safety flags remain false in production/config code.
```
