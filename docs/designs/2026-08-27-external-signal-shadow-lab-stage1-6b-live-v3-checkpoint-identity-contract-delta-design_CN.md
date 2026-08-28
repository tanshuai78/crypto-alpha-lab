# Stage 1.6B Live V3 Checkpoint Identity Contract Delta Design

- **日期:** 2026-08-27
- **状态:** `design_approved`
- **Review Mode:** `closure_confirmation`
- **类型:** narrow checkpoint identity authority delta
- **研究路线:** Stage 1.6 = Binance USD-M Futures Delisting；Stage 1.6D = VPS live source observation and PIT provenance
- **直接上游 Design:** `2026-08-26-external-signal-shadow-lab-stage1-6b-live-detail-burst-queue-controlled-failure-terminal-delta-design_CN.md` (`SHA-256: 9f514d19e5238db38e66d9ae150fb25930b18b4058102adba2a89d6df09bd1c1`)
- **继承 authority:** 2026-08-19 parent 1.6B Design、2026-08-21 catalog schema authority Delta、2026-08-21 Storage scope amendment、2026-08-23 TerminalStatus field-contract correction、2026-08-25 1.6D deployment Design
- **代码基线:** `d9de951`（本 Delta 起草时的生产代码基线）
- **门禁状态:** `implementation_plan_allowed=true`；`implementation_allowed=false`；`deployment_allowed=false`

---

## 1. Confirmed Facts

1. 当前 normal `ObserverCheckpoint` producer 的 v2 ID 为：

```text
SHA256(UTF-8(
  run_id | poll_seq | monotonic_request_seq | record_seq | accounted_root_bytes
))
```

它不绑定 `candidate_states`。

2. 当前 `reconcile_and_write_checkpoint()` 的 v2 ID 为：

```text
SHA256(canonical_json({
  prior_checkpoint_id,
  accounted_root_bytes,
  stream_offsets,
  stream_last_hashes,
}))
```

它同样不绑定 `candidate_states`。

3. 已批准的 2026-08-26 live-detail Delta 对 fresh `live_observed` root 增加 checkpoint v3 的 immutable candidate `first_attempt_ahead_count_at_admission`、`first_attempt_deadline_poll_seq` 与 checkpoint `pending_terminal_failure_reason`。

4. 该 live-detail Delta Section 10 同时冻结：record identity formulas 保持不变，除非该 Delta 明确覆盖。它没有定义 v3 `checkpoint_id` formula。

5. `TerminalStatus.final_checkpoint_id` 和 sealed export manifest 均引用 persisted `checkpoint_id`；checkpoint 是 bounded restart authority。因此 v3 scheduler/failure state 若不被 ID 绑定，ID 不能唯一代表其所指向的 v3 state。

6. 当前已部署的 VPS incident root `stage1_6d_live_20260826T031333Z` 是 pre-Delta live v2 interrupted evidence。它不得 resume、写新 checkpoint、manual terminal、seal、delete 或 cleanup。

7. 本路线仍是 anonymous public HTTPS source observation。`RISK_LIVE_TRADING_ENABLED=False`，且 PIT、replay、alpha、paper trading、live trading 与 execution authority 均为 false。

## 2. Assumptions

1. `canonical_json()` 保持既有确定性定义：UTF-8 JSON、lexical key sort、compact separators；本 Delta 不改变该 helper 的通用语义。
2. `accounted_root_bytes` 的 checkpoint 前值、stream offsets、stream last hashes、poll/request/record sequence 与 heartbeat/status/coverage 都是 checkpoint authoritative state，必须属于 v3 identity projection。
3. v3 writer、reconciliation reader/writer 和 sealed loader 均可在现有 `models`、`observer`、`storage` 文件内复用一个纯 stdlib helper；不需要 registry、factory、数据库、队列或新 dependency。

## 3. Root Cause / Core Issue

live-detail Delta 使 v3 checkpoint 增加 scheduler 与 controlled-failure authority，但既有 v2 ID formulas 不覆盖这些新增字段。若继续套用 v2 seed，则只改变 ahead count、deadline 或 failure intent 的两个 v3 checkpoints 可以得到同一 ID。

Implementation Plan 不能自行替换 frozen record identity formula。要同时满足 v3 durable-state binding 与上游 authority，必须由本 Delta 仅对 fresh live v3 定义一条 explicit version-scoped formula，并明确 v2 formulas 不变。

## 4. Decisions

### 4.1 Exact supersession and unchanged authority

For `capture_mode=live_observed` and only when:

```text
schema_version = stage1_6b_observer_checkpoint_v3
```

this Delta supersedes the 2026-08-26 Delta Section 10 statement that record identity formulas remain unchanged. The supersession is limited to `ObserverCheckpoint.checkpoint_id` computation and verification for fresh v3 roots.

Unchanged:

- all v2 normal checkpoint ID and v2 reconciliation checkpoint ID formulas;
- all historical checkpoint/consumer behavior;
- every non-checkpoint record identity, raw SHA path, terminal status schema/key set, sealed export ID formula, guard formula/reserve, source profile and request contract;
- queue budget, FIFO ordering, deadline formula, candidate/checkpoint v3 key sets, terminal-reason mapping, resume matrix and incident-root policy from the 2026-08-26 Delta.

No compatibility alias, v2-to-v3 migration, identity guessing or rewrite is permitted.

### 4.2 Exact v3 checkpoint identity projection

Define the exact ordered-key-independent projection `V3_CHECKPOINT_ID_PROJECTION` as these exact keys from one validated v3 checkpoint record:

```text
schema_version
run_id
capture_mode
source_profile_id
source_profile_attestation_sha256
prior_checkpoint_id
poll_seq
monotonic_request_seq
record_seq
accounted_root_bytes
stream_offsets
stream_last_hashes
candidate_states
heartbeat_at_ms
last_index_poll_status
last_index_poll_coverage
pending_terminal_failure_reason
```

`checkpoint_id` is deliberately excluded only to avoid self-reference. No other field may be omitted, added, normalized, defaulted, sorted outside `canonical_json()`, or read from wall clock/current queue rank during identity calculation.

The exact v3 formula is:

```text
v3_checkpoint_id =
  SHA256(UTF-8(canonical_json(V3_CHECKPOINT_ID_PROJECTION)))
```

The projection is valid only if its `schema_version` is `stage1_6b_observer_checkpoint_v3` and `capture_mode` is `live_observed`; any other input is an input-validation error. `candidate_states` is the exact v3 serialized map, including each candidate's immutable ahead count and deadline. `pending_terminal_failure_reason` is `null` for normal/reconciliation checkpoints and the exact controlled-failure reason for a failure-intent checkpoint.

For every serialized v3 checkpoint, the exact top-level key-set requirement is:

```text
set(serialized_v3_checkpoint.keys())
  == set(V3_CHECKPOINT_ID_PROJECTION.keys()) | {"checkpoint_id"}
```

Missing or extra top-level keys reject before identity calculation. This equality and the Section 4.2 projection jointly mean that only self-referential `checkpoint_id` is excluded.

### 4.2.1 Independent canonical-byte golden vector

The following is a frozen, synthetic projection `P`. Its `candidate_states` value contains one admitted Lane A candidate so the vector covers the v3 immutable scheduler fields. `B` is the exact UTF-8 byte sequence of the one-line JSON below: no trailing newline, lexical key sort, compact separators and `ensure_ascii=False`.

```json
{"accounted_root_bytes":17,"candidate_states":{"0123456789abcdef0123456789abcdef":{"detail_attempt_count":0,"first_attempt_ahead_count_at_admission":0,"first_attempt_at_ms":null,"first_attempt_deadline_poll_seq":7,"first_discovered_at_ms":1700000000000,"first_discovered_poll_seq":7,"lane":"lane_a","last_attempt_at_ms":null,"next_retry_at_ms":null,"retry_cycle_count":0,"source_article_id":"0123456789abcdef0123456789abcdef","terminal_reason":null,"trusted_detail_revision_id":null}},"capture_mode":"live_observed","heartbeat_at_ms":1700000000123,"last_index_poll_coverage":"successful","last_index_poll_status":"trusted","monotonic_request_seq":11,"pending_terminal_failure_reason":null,"poll_seq":7,"prior_checkpoint_id":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","record_seq":13,"run_id":"stage1_6b_identity_golden","schema_version":"stage1_6b_observer_checkpoint_v3","source_profile_attestation_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","source_profile_id":"binance_public_web_bapi_en_delisting_catalog_v2","stream_last_hashes":{"article_discoveries.jsonl":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","detail_observations.jsonl":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"},"stream_offsets":{"article_discoveries.jsonl":101,"detail_observations.jsonl":202}}
```

```text
len(B) = 1365
SHA256(B) = 2610ca21cd7a91f14c38581b184765bb9946b5e64776bb93789e66947eaaa71f
```

Future tests must construct `P` independently, assert its canonical bytes equal `B`, and assert `compute_live_v3_checkpoint_id(P)` equals the frozen digest. The expected bytes and digest must never be generated by the production identity helper.

### 4.3 One v3 writer mechanism and reader verification

All three v3 checkpoint writers must call the same pure `compute_live_v3_checkpoint_id()` mechanism:

```text
normal completed-poll checkpoint
failure-intent checkpoint
reconciliation checkpoint
```

No writer may recreate the formula inline or use a v2 seed. The caller constructs validated v3 state, computes the ID from Section 4.2, inserts that ID into the persisted checkpoint record, and writes atomically through the existing ordinary-control-plane guard path.

Before any v3 tail reconciliation write or network/client construction, the existing bounded reader must recompute the ID from the persisted v3 record and require equality. `load_sealed_export()` must independently apply the same equality check before accepting a sealed post-Delta v3 live export. A mismatch rejects fail-closed without migration, rewrite, seal or new network request.

### 4.4 Terminal and export binding

`TerminalStatus.final_checkpoint_id` remains unchanged structurally. A successful failure-intent checkpoint provides a v3 ID computed by Section 4.2; the existing failure terminal references that ID. If intent persistence fails, the terminal retains the existing rule: reference the last committed normal checkpoint ID or `null`.

The sealed export ID formula remains unchanged. Its existing checkpoint-ID input therefore binds the full exact v3 checkpoint state only through this Delta's v3 identity formula. This Delta does not make failure roots sealable and does not change terminal authority.

## 5. Scope / Non-Goals

### In Scope

- Explicit v3-only `ObserverCheckpoint.checkpoint_id` formula and read-time equality verification.
- One shared v3 identity mechanism across normal, failure-intent and reconciliation writers.
- Tests proving v3 identity sensitivity, same-state determinism, v2 identity preservation and v3 reader rejection on mismatch.

### Non-Goals

- Changing any v2 formula, v2 serialized bytes, historical backfill, existing sealed export or incident root.
- Changing candidate queue/budget/deadline semantics, source profile, endpoint, header, locale, parser, storage quota, terminal schema/reason set, sealed export formula or `final_checkpoint_id` field.
- Adding a new checkpoint key, artifact profile, registry/factory, dependency, migration, root scan, network request, VPS action, PIT/replay/alpha conclusion or trading permission.

## 6. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-ID-01 | Only fresh `live_observed` v3 checkpoints use Section 4.2; no v2/historical checkpoint formula or serialization changes. |
| INV-ID-02 | Every v3 identity binds every exact Section 4.2 projection field except self-referential `checkpoint_id`. |
| INV-ID-03 | Changing only v3 ahead count, deadline or pending failure reason changes `checkpoint_id`; identical complete v3 projection yields the identical ID. |
| INV-ID-04 | Normal, failure-intent and reconciliation v3 writers use the same mechanism; no inline or v2 fallback formula exists in v3 paths. |
| INV-ID-05 | v3 reconciliation and sealed-loader acceptance recompute and require ID equality before a write, client/network construction or consumer acceptance. |
| INV-ID-06 | ID mismatch, unknown/mixed v3 schema, missing v3 field or invalid intent reason is fail-closed; no migration, alias, repair or rewrite occurs. |
| INV-ID-07 | Terminal success/failure, guard reserve hierarchy, failure-intent sequence and all non-trading authority boundaries remain exactly as approved. |

## 7. Producer / Writer / Loader / Consumer / Reviewer Impact Matrix

| Role | Effect | Required behavior |
|---|---|---|
| `Stage16BObserver` | Changed fresh-v3 normal/intent producer | construct v3 state then call the one v3 ID mechanism |
| checkpoint reconciler | Changed fresh-v3 reader/writer | verify persisted v3 ID before bounded tail; use same mechanism for reconciliation checkpoint |
| `load_sealed_export()` | Changed v3 live consumer validation | recompute v3 ID before accepting sealed post-Delta live export |
| terminal writer | Structurally unchanged | retains existing `final_checkpoint_id` reference semantics |
| sealed export producer | Structurally unchanged | keeps current export-ID formula; consumes the verified checkpoint ID |
| historical backfill and v2 roots | Unchanged | retain exact existing ID formulas and read-only behavior |
| Stage 1.6A/1.6C | Unchanged downstream boundary | no new audit/PIT/replay/alpha authority; historical-only path confinement remains required |
| reviewer | New proof edge | verify formula exactness, three-writer reuse, reader validation and v2 golden preservation |

## 8. Data / State / Temporal Contract

```text
validated fresh live v3 state
  -> project exact Section 4.2 fields excluding checkpoint_id
  -> canonical_json
  -> SHA-256
  -> insert checkpoint_id
  -> existing guarded atomic checkpoint write

persisted v3 checkpoint
  -> validate schema/capture mode/v3 fields
  -> recompute same projection
  -> equality required
  -> bounded reconciliation or sealed-loader acceptance
```

Normal checkpoint:

```text
pending_terminal_failure_reason = null
poll completed under the existing status/coverage semantics
```

Failure-intent checkpoint:

```text
pending_terminal_failure_reason = exact known controlled-failure reason
may represent an incomplete poll
never resume or seal
```

Reconciliation checkpoint:

```text
pending_terminal_failure_reason = null
only after exactly one valid bounded incomplete tail reconstructs
before the next network admission
```

The formula uses persisted timestamps/fields only. It does not claim official publication time or alter first-observed semantics.

## 9. Failure Semantics / Persistence / Restart / Idempotency

| Condition | Required result |
|---|---|
| v3 state violates formula/schema/intent validator before write | reject; no checkpoint write or network admission |
| normal/intent/reconciliation writer cannot compute valid v3 ID | existing write path fails; no substitute ID or v2 fallback |
| persisted v3 ID mismatch during resume | reject before reconciliation write and before client construction |
| persisted v3 ID mismatch during sealed loading | reject consumer input without rewriting export/root |
| same exact v3 projection is computed again | same SHA-256 ID; atomic write/idempotency rules remain existing |
| any v2/historical checkpoint | existing v2 branch and IDs remain exact; this Delta's v3 helper is not called |

An ID mismatch is evidence invalidity, not a terminal reason. It must not be translated into `source_profile_schema_drift`, `storage_exhausted` or any other terminal reason. Existing controlled-failure terminal behavior remains authoritative.

## 10. Compatibility / Migration / Existing Roots

| Artifact/root | Required behavior |
|---|---|
| historical v2 | unchanged producer/consumer and v2 ID formulas |
| sealed pre-Delta live v2 | read-only acceptance only under existing live-v2 branch |
| pre-Delta unsealed live v2, including incident root | preserved interrupted evidence; no resume/seal/write/delete |
| fresh post-Delta live v3 | Section 4.2 identity required for writer, resume and sealed-loader acceptance |
| v3 checkpoint with mismatched ID | reject; no migration, compatibility alias or repair |

No artifact-profile bump is required because v3 schema version already separates this contract and the new formula is explicitly scoped to that version.

## 11. Evidence and Fixture Provenance

| Evidence | Role | Limitation |
|---|---|---|
| current v2 observer/reconciliation source | establishes exact old formulas and their omission of v3 fields | code baseline evidence, not a new live observation |
| `stage1_6d_live_20260826T031333Z` operator transcript | established the scheduler incident that produced v3 requirements | preserved v2 incident; never mutated or resumed |
| synthetic v3 checkpoints/tails | prove projection sensitivity, mismatch rejection and three-writer equivalence | not official source/PIT/alpha evidence |
| historical v2 fixtures | prove byte/identity compatibility | no authorization to regenerate historical evidence |

## 12. Safety / Authority Boundary

This Delta authorizes no source collection, historical backfill, VPS deployment, process restart, resume, seal, replay, market-data read, alpha claim, paper trading, live trading or execution. It changes only an internal fresh-v3 durable identity contract after a future reviewed implementation plan and explicit implementation authorization.

```text
RISK_LIVE_TRADING_ENABLED = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
```

## 13. Verification Strategy

Future Implementation Plan must use RED then GREEN and prove:

1. v2 normal and reconciliation checkpoint golden IDs/serialized bytes are unchanged.
2. same exact v3 projection produces the same ID.
3. changing only candidate ahead count changes v3 ID.
4. changing only candidate deadline changes v3 ID.
5. changing only `pending_terminal_failure_reason` changes v3 ID.
6. normal, failure-intent and reconciliation writers each call the same v3 mechanism and persist its exact result.
7. v3 resume rejects a mismatched ID before reconciliation write/client construction; valid v3 tail still writes exactly one reconciliation checkpoint.
8. sealed v3 loader rejects mismatched ID and accepts a valid normal complete v3 export; historical/v2 matrices remain unchanged.
9. the Section 4.2.1 literal vector's independently constructed projection produces the exact 1365 UTF-8 bytes and frozen SHA-256; expected bytes/digest do not call the production helper.
10. `set(serialized_v3_checkpoint.keys()) == set(V3_CHECKPOINT_ID_PROJECTION.keys()) | {"checkpoint_id"}`; missing or extra top-level v3 key rejects fail-closed.
11. invalid identity projection value or unknown/non-string intent reason rejects fail-closed.
12. terminal reserve/failure-reason preservation, StorageGuard admission and all safety flags regress unchanged.

## 14. Rollout / Rollback

No rollout or deployment is authorized by this Design. After implementation approval, the first runtime use must still be a separately authorized fresh v3 root and fresh target-local attestation.

Rollback is no-start or stopping a new process while preserving its root. It never changes v2 code paths or mutates the incident root. A v3 ID validation failure is retained as invalid evidence and requires a new Design decision; it is not repaired in place.

## 15. Open Questions

**N/A.** The v3 projection, hash grammar, scope override, reader validation and v2 preservation are exact. Future checkpoint schema changes require another identity Design delta; they must not silently enter this projection.

## 16. Approval Boundary

This Design authorizes neither code nor deployment. It may proceed to a revised implementation-plan review only when review confirms:

1. the Section 4.1 override is limited to fresh v3 `checkpoint_id` identity;
2. the Section 4.2 projection is exact and excludes only self-referential `checkpoint_id`;
3. all three v3 writers and both v3 readers are mechanically covered;
4. v2 identity/serialization and incident-root immutability remain unchanged; and
5. no PIT, alpha, replay or trading authority is widened.

```text
design_p0 = 0
design_p1 = 0
implementation_plan_allowed = true
implementation_allowed = false
deployment_allowed = false
```
