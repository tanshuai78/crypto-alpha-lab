# Stage 1.5D Detail Retry Cycle Durability 与 Active-Root Recovery Hotfix Design

**日期:** 2026-08-17  
**状态:** design_revised_for_review  
**适用范围:** External Signal Shadow Lab / Stage 1.5D、1.5F recovery boundary  
**事故候选:** Binance article `0872245db74c4daaabd4f11984ba52c1`  
**安全模式:** public-read-only；交易、paper、execution、alpha interpretation 均保持禁用。

## 1. 结论

当前 Design 不授权“补回 clean event”。若 symbol 与 launch anchor 只能在可信 detail 于 `T1` 出现后才知道，那么不能把该知识回填为首次公告检测时间 `T0` 已知。即使补丁赶在 8 月 18 日 launch 前成功，最多只能收集并标记为 `recovery_validation_only` 的深度证据，不能计入 1.5G 的 `formal_announcement_and_launch_count`。

本次要修复的是一个真实但必须在执行前再次固化的 selector liveness bug：物理 HTTP 请求数被用作逻辑 retry 上限，导致 retryable transient article 永久滞留。修补同时闭合其 crash、shared-lock、Git attestation、time provenance、exactly-once emission 与 active-root mixed-lineage 边界。

```text
detail_http_request_count
  = non-authoritative transport telemetry / manifest reconciliation input.

detail_retry_cycle_count
  = durable logical retry reservation; it is persisted before the first HTTP side effect.

T0 = announcement/list first detected
T1 = trusted detail, symbols and anchor become knowable / formal row becomes available
T2 = 1.5F first processes that formal row

T1/T2 never become T0.

active-root recovery is transported explicitly as:
  detail_recovery_provenance = active_root_retry_cycle_recovery_v1
```

## 2. Confirmed Facts and Evidence Boundary

### 2.1 Confirmed from current workspace source

1. `select_detail_retry_attempts()` currently reads `detail_http_request_count` (fallback `detail_fetch_attempt_count`) and executes `if cnt >= EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES: continue` before forming attempted candidates.
2. The same scheduler already uses `detail_retry_cycle_count` for the degraded-recent retry cap.
3. The D runner increments `detail_retry_cycle_count` after budget allocation but persists `detail_retry_scheduler_state.json` only at poll end; an HTTP side effect can therefore occur before the cycle reservation is durable.
4. D runner increments `detail_http_request_count` per BAPI/primary/fallback request. Request manifest reconciliation is an existing diagnostic, not a transactional protocol.
5. The existing transient max-age reducer is 24 hours and emits only a non-consumable `detail_unavailable_timeout` result.
6. F verifies its worktree `HEAD` and protected runtime manifest on every poll. Checking out a different commit in its current worktree makes the compromise sticky and blocks admission.
7. `StorageGuard` currently resolves the shared lock from the process working directory, not from `output_root`; separate worktrees would therefore use different locks without a narrow guard change.
8. F currently derives `announcement_and_launch_time` from `detected_at_ms`/watermark. Its `evidence_start_class` is an F-owned admission/state field, not a D-to-F transport field. Without an explicit D recovery marker, F cannot distinguish ordinary BAPI detail resolution from active-root recovery and would mislabel the latter as clean.
9. D rebuilds emission identity from durable `events/*.jsonl` on startup and has existing restart coverage, but the specific crash window “event append succeeded before scheduler-row cleanup” is not yet mechanically proven.

### 2.2 Runtime evidence supplied by the operator; independently re-capture before implementation

The following observation is consistent with the source defect but is not independently retrievable by this local Design session:

```text
article = 0872245db74c4daaabd4f11984ba52c1
status = pending_detail_retry
detail_retryable = true
last_detail_failure_class = http_202_empty
detail_http_request_count = 4
detail_retry_cycle_count = 2
next_detail_retry_at_ms = overdue
terminal_state = false
```

The article's BAPI response was reported as HTTP 200 but rejected by the existing trusted-payload validator as `bapi_waf_or_login_shell`; primary/support detail responses were HTTP 202 empty. These are external-source observations, not parser success.

**Implementation Plan Task 0 is mandatory:** it must freeze the current workspace and server evidence listed in Section 14. If the exact HTTP-count predicate or the supplied state shape is absent, stale, terminal, or already emitted, stop. No selector change may be made based on this incident hypothesis alone.

## 3. Scope and Non-Goals

### 3.1 In scope

1. Separate physical request telemetry from logical retry eligibility.
2. Make a selected retry-cycle reservation durable before any external HTTP side effect.
3. Preserve retry liveness under bounded budgets, endpoint degradation and transient max age.
4. Add one explicit durable D-to-F active-root recovery provenance marker. F must classify recovery only from that marker, never from `T1 - T0` or wall-clock inference.
5. Define one-off recovery for the **currently active paired D/F roots only**, using isolated patched worktree processes and a shared host lock.
6. Prove restart duplicate suppression for the post-append/pre-cleanup crash window.

### 3.2 Explicit non-goals

- Guarantee a trusted Binance detail payload before the 8 月 18 日 launch window.
- Claim, manufacture, or relabel this incident as clean/formal announcement-and-launch evidence.
- Change title parsing, anchor precedence, formal contract versions, schedule revision producer policy, data retention limits, retry thresholds, or trading permissions.
- Restart or mutate archived/inactive roots; establish a general old-root resurrection policy; hand-edit scheduler state, watermark, events, manifests, raw payloads, or snapshots.
- Add queues, databases, external services, interfaces, factories, generic migration framework, or a transaction log for request manifests.

## 4. Decisions and Rationale

### D-01: Keep the smallest counter separation

`detail_http_request_count` remains physical transport telemetry and request-manifest reconciliation input only. `detail_retry_cycle_count` remains the existing logical-cycle field. No new counter, schema version, config literal, dependency, or retry framework is introduced.

`EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES=3` remains the existing non-transient `retry_count` terminal boundary. The Plan may amend only its misleading comment; the literal must not change. Transient liveness remains bounded by existing backoff, degraded-cycle controls and `TRANSIENT_DETAIL_FETCH_MAX_AGE_SEC`.

### D-02: Persist cycle reservation before HTTP

For every selected detail retry:

```text
select under existing budget/fairness rules
-> increment detail_retry_cycle_count, set last_retry_at_ms and durable inflight_cycle reservation
-> atomically persist scheduler state through StorageGuard
-> only if persistence succeeds, issue first BAPI/primary/fallback HTTP request
```

Crash after reservation but before HTTP consumes one cycle. This is intentionally conservative. Crash after an HTTP request cannot reuse that cycle number after restart. Storage checkpoint failure produces no HTTP request and fails closed/defer according to the existing D storage-failure policy.

`inflight_cycle` is a minimal optional durable record containing the reserved cycle number and reservation timestamp, not a new counter or request journal. It is cleared only after the normal cycle recording checkpoint succeeds. On restart, a remaining record produces `request_manifest_persistence_unknown` diagnostic evidence before a later new cycle may be selected. The system does not infer how many HTTP calls occurred and does not repair count/manifest history.

### D-03: Do not promise impossible manifest equality

In the normal completed recording path, each HTTP request increments transport telemetry and attempts one manifest row. Across process crash or StorageGuard write failure, a bounded telemetry/manifest gap is permitted and must surface as existing/new explicit persistence-unknown diagnostic state. It is never used for scheduling, admission, retry caps or manual history repair.

No request-intent/completion transaction log is introduced: that is a materially larger system outside this hotfix.

### D-04: Use an isolated patched worktree and restart the D/F pair on the same active roots

Leaving F running in worktree `B` while checking out patched commit `C` in that same worktree violates F's sticky runtime attestation. Running only D from a second worktree while leaving old F code also cannot enforce the corrected `T0/T1/T2` evidence label.

The approved recovery shape is therefore:

```text
worktree B: frozen pre-patch source evidence; no checkout/mutation
worktree C: verified patched commit; source for restarted D and F processes
output roots: the exact active B-host D/F data roots, passed as absolute paths
watermark: existing F watermark, read and preserved; never bootstrap
```

Before this can run, StorageGuard must derive its shared flock path from the absolute common `data/external_signal_shadow` ancestor of `output_root`, rather than CWD. Thus both restarted C processes lock the original host data plane; the lock remains identical to the old B-worktree lock path. This is a narrow TCB correction, not a new lock configuration.

F is restarted only after preflight proves `active_observation_count=0`; it resumes the same F root and durable watermark/state without `--bootstrap-watermark`. The restart creates a new F process identity and root-contract facts for commit C, which is expected and captured in the external recovery ledger.

### D-05: Freeze T0/T1/T2 and explicit recovery provenance

```text
T0 = original detected_at_ms / first_detected_at_ms
T1 = detail_fetched_at_ms and symbol_resolved_at_ms, set only when trusted detail succeeds
T2 = F first_seen_at_ms, set only when F processes the formal event
```

Normal BAPI detail resolution can legitimately have `T1 > T0`; F must therefore never infer recovery from detail latency, timestamps, or current wall clock.

During one approved active-root recovery, the D runner receives a narrow exact source-article input. Only when the emitted formal row's `source_article_id` equals that input does D add this durable additive transport field before the guarded event append:

```text
detail_recovery_provenance = active_root_retry_cycle_recovery_v1
```

F consumes this marker mechanically: it sets its own `evidence_start_class` to `recovery_start`, emits `live_depth_evidence_basis = recovery_validation_only`, and sets announcement-time capture eligibility to false. A row without the marker retains existing normal title-known and normal BAPI-detail semantics. Stage 1.5G consumes only the final recovery label and never counts it as formal announcement-and-launch evidence.

### D-06: Active-root-only recovery and external boundary ledger

This is not an old-root migration policy. It applies only when all are true:

- D and F are an actively running pair bound to the same source D root;
- their watermark/state/root contract are readable and healthy;
- no D/F active observation exists at the cutover;
- the target article is nonterminal and has not emitted a formal event;
- the Section 14 preflight passes.

The operator records a local, append-only recovery ledger outside the VPS output roots before and after cutover. It contains hashes/identities, stop/start timestamps and B/C commit/process facts. It does not modify historic JSONL or claim the full root was produced by one commit.

## 5. Allowed Change Scope

### Allowed implementation paths

- `src/research/external_signal_shadow/stage1_5d_detail_retry_scheduler.py`
- `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py`
- `src/research/external_signal_shadow/stage1_5_storage_guard.py`
- `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
- `configs/base.py` (comment-only clarification for `EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_FETCH_MAX_RETRIES`; no AST value/assignment change)

### Allowed verification paths

- `tests/research/external_signal_shadow/test_stage1_5d_detail_retry_scheduler.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5d_live_event_source_smoke_collector.py`
- `tests/research/external_signal_shadow/test_stage1_5_storage_guard.py`
- `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
- `tests/research/external_signal_shadow/test_stage1_5f_runtime_gate_validator.py` (read-only compatibility)
- `tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py` (read-only compatibility)

### Allowed documentation paths

- This Design.
- The existing deployment runbook only if the final Plan requires documented active-root recovery commands and ledger format.

### Forbidden

- Any other 1.5D/F/G source edit, formal schema/version change, config value change, producer enablement, trading permission change, or storage threshold change.
- Hand mutation, deletion, compaction, replay or synthetic insertion in live D/F roots.
- F bootstrap, a new F root, concurrent D/F writers, VPS 1.5G review, `ruff check --fix .`, global formatter, `git clean`, `git reset --hard`, `rsync --delete`, or arbitrary worktree checkout under a running process.

## 6. Acceptance Invariants

**INV-01 -- Evidence preflight.** The Plan freezes exact current source predicate, commits, runtime state and artifacts before modifying code. Predicate/state mismatch stops work.

**INV-02 -- No HTTP retry cap.** `detail_http_request_count` never culls a retryable row or defines a logical retry-cycle limit.

**INV-03 -- Durable cycle reservation.** The selected cycle number and `last_retry_at_ms` are durable before first HTTP. Checkpoint failure means no HTTP side effect.

**INV-04 -- Existing bounds survive.** Never-attempted reservation, per-poll budget, endpoint-degraded recent window/cycle cap, overdue slot, minimum interval, non-transient retry cap and 24-hour transient max-age all remain enforced.

**INV-05 -- No infinite sink.** A nonterminal due row is selected, locally backoff-deferred, bounded by explicit endpoint-degraded-until, or terminalized by existing reducers. It cannot remain overdue only because HTTP telemetry crossed three.

**INV-06 -- Request provenance is fail-closed.** HTTP 200 WAF/login shell, HTTP 202 empty and untrusted payloads never emit a formal event. Crash/storage gaps are explicitly diagnostic, never silently repaired.

**INV-07 -- T0/T1/T2 integrity.** T0 stays original; T1/T2 record actual later availability/consumption. `T1 > T0` alone never changes evidence class.

**INV-08 -- Explicit recovery transport.** F classifies active-root recovery only from durable `detail_recovery_provenance=active_root_retry_cycle_recovery_v1`, never from `T1 - T0`. D writes it only for the exact preflighted source article, before event append; it can only downgrade evidence.

**INV-09 -- Exactly-once event emission.** Durable event stream/index reconstruction suppresses a second formal event after append-before-scheduler-cleanup crash; repeated trusted payload cannot duplicate emission.

**INV-10 -- Shared host lock.** D/F processes from a patched worktree contend on the same absolute host lock as the output roots, independent of CWD/worktree.

**INV-11 -- Attested pair recovery.** Both restarted processes attest against commit C; F preserves existing watermark/root identity and valid source-D-root binding. No sticky compromise, source binding mismatch or blocked admission is allowed post-cutover.

**INV-12 -- Mixed lineage is explicit.** A local recovery ledger proves B-to-C boundary without modifying historic evidence rows. The recovery applies to the active pair only.

**INV-13 -- Authority unchanged.** All live/paper/execution/alpha flags remain false and schedule-revision producer remains disabled.

## 7. State, Failure and Time Contract

### 7.1 Retry reducer

```text
retryable row due
-> grant bounded logical cycle
-> durable reservation checkpoint
-> HTTP request(s)
-> trusted detail + formal validation: emit once, scheduler row removed
-> transient/untrusted: persist existing backoff state
-> non-transient exhausted: existing terminal path
-> transient age >= 24h: detail_unavailable_timeout, non-consumable
```

Rows with missing/invalid counters retain defensive legacy parsing but are not eligible for active-root recovery unless Task 0 proves the target has explicit `detail_retry_cycle_count`.

### 7.2 Time/evidence reducer

| Condition | Evidence label |
|---|---|
| symbol/anchor was already formally known at T0; normal post-watermark conditions hold | existing `announcement_and_launch_time` or `launch_time_only` semantics |
| ordinary BAPI detail first resolves symbols at T1, with no recovery marker | existing normal reducer semantics |
| exact active-root recovery formal row carries `detail_recovery_provenance=active_root_retry_cycle_recovery_v1` | `recovery_validation_only` |
| source remains untrusted/202 or validation fails | no consumable event |

The recovery label may retain depth snapshots for operational research but never upgrades 1.5G formal clean counts or alpha claims.

## 8. Persistence, Crash and Idempotency

1. The pre-HTTP checkpoint is written with the existing guarded scheduler writer. It serializes the complete retry state; no separate persistence subsystem is created.
2. The checkpoint includes an optional `inflight_cycle` reservation. Crash after durable reservation but before HTTP: restart observes the consumed cycle. One conservative lost opportunity is acceptable.
3. Crash after BAPI but before fallback, manifest, or end-of-poll checkpoint: durable `inflight_cycle` produces `request_manifest_persistence_unknown`; a later cycle has a new durable number and never treats missing manifest as proof of success.
4. Crash after event append before scheduler row removal: startup rebuilds durable event identity, sees the event, and emits no second row. The Plan must prove this with deterministic fixtures.
5. StorageGuard denial during reservation/write stops or safely defers before HTTP as specified by the existing fail-closed runner behavior. It does not bypass storage reservation to rescue an event.

## 9. Fixture Provenance and Verification

All new fixtures are synthetic unless explicitly described as a frozen public payload. No live root file is committed.

Required RED coverage:

1. Current incident shape: HTTP count 4, cycle count 2, due `http_202_empty`, nonterminal => selected under an available bounded slot.
2. Same shape remains excluded when terminal/non-retryable/not due/minimum interval/cycle cap applies.
3. Reservation persistence fails => zero network calls. Persisted reservation then simulated restart => subsequent request receives a new cycle, not the reserved cycle.
4. Crash after first HTTP with durable `inflight_cycle` => restart emits `request_manifest_persistence_unknown`, does not reconstruct physical count/manifest history, and does not reuse the reserved cycle.
5. Physical request/manifest normal-path accounting remains one attempt per completed recording path; crash/storage failure is surfaced as persistence-unknown rather than equality assertion failure.
6. Append-before-cleanup restart and repeated trusted payload produce exactly one formal event.
7. Separate worktree/CWD guards pointing to the same absolute D/F data plane use one flock path and serialize writes.
8. F resume without bootstrap preserves watermark/state/root ID but receives new C process/attestation facts without compromise.
9. Ordinary BAPI detail resolution with `T1 > T0` and no recovery marker retains existing normal evidence semantics.
10. The same T0/T1 shape with the durable recovery marker becomes `recovery_validation_only`; 1.5G does not increment formal announcement-and-launch count.
11. Restart/replay of the recovered durable formal row preserves the marker and remains `recovery_validation_only`.
12. Existing ordinary title-known-at-T0 clean and launch-time-only regressions remain unchanged.
13. AST/value check proves every `configs/base.py` assignment is identical pre/post; only the approved comment text changes.

## 10. Active-Root Recovery Contract

### 10.1 Preconditions

Before any process stop, future runbook/Plan captures the following in a local recovery ledger:

```text
deployed/current B commit and target C commit
exact selector source excerpt + predicate line/hash
D absolute root/id, gate/StorageGuard health, process PID/start identity
target scheduler JSON SHA256 + canonical target-row hash
target counters, retry state, next retry, terminal status
exact recovery source_article_id and intended recovery marker value
event-stream count/tail hash, manifest count/tail hash, formal identity-index hash
proof that no formal event exists for article
F absolute root/id, process identity, startup commit, watermark SHA/value,
root-contract SHA, fresh healthy summary, source-D-root IDs, no active observations
host free space and shared lock path
```

Any mismatch is a stop condition. This ledger is stored locally outside VPS D/F output roots and records both B (pre-cutover) and C (post-cutover) facts.

### 10.2 Cutover

```text
create/verify clean, non-shallow patched worktree C
-> stop active D and F processes; prove both exited
-> do not checkout or alter worktree B
-> start patched D from C using existing absolute D output root
-> verify D READY, shared lock path and target-state continuity
-> start patched F from C using existing absolute F output root, without bootstrap
-> verify original watermark/root id preserved; F attestation/source binding healthy
```

The Plan must require an `active_observation_count=0` precondition; otherwise recovery stops rather than creating a collection gap.

### 10.3 Success and stop conditions

Success is limited to: D reselects the stranded row under normal bounds, preserves T0 and prior counters, and later emits at most one formal event only if trusted detail becomes available. That exact recovered formal row carries the durable recovery marker; F may collect only recovery-labelled evidence.

Stop without manual repair if any preflight fails, target is terminal/already emitted, StorageGuard/gate is non-ready, F watermark/root binding is not preserved, attestation is compromised, a concurrent writer exists, target exceeds transient max age, or trusted detail never appears.

## 11. Open Questions

None that alter the implementation path.

Whether Binance makes a trusted detail payload available before launch is an external runtime outcome. It does not permit a weaker trust boundary and does not block writing the Implementation Plan.
