# Stage 1.6E-B Live Semantic Trigger And Event-Level Market-Data Observer Implementation Plan

Do not modify configuration, source, scripts or tests until this Plan has an Approve review verdict and explicit user implementation authorization. Plan approval is not implementation, deployment or runtime authorization.

Goal: build one bounded public-read-only supervisor. It consumes one explicit Stage 1.6D V3 live root, admits at most one active notice-level event with one to three USD-M symbols at a time, uses one fixed twelve-hour event window, and seals only a complete internally consistent event bundle.

Architecture:

~~~text
validated E-A environment
to validated 1.6D V3 committed snapshot
to verified revision, observation and raw linkage
to durable semantic projection
to durable notice admission
to durable event contract and derived E-A ProfileCore
to sequential public requests
to observations, terminal, manifest last
~~~

New E-B models, storage, source consumer, client, observer and runner read-only reuse E-A complete-bundle verification, 1.6D V3 checkpoint ID calculation and G2 parsing. No E-A ProfileCore/endpoint, 1.6D writer/checkpoint or G2 grammar changes.

## Plan Status

- Design SHA256 = 752aecff8735f22513483e6bf65ae991386f46ff2ae953da44cd1fe9c5898583
- Design status = externally approved
- Plan status = draft_for_review
- implementation_allowed = false
- deployment_allowed = false
- runtime_action_allowed = false
- Planning baseline = e943878f74e65067ac9fbb39f4717017f49f3cce

Plan approval != implementation authorization != deployment authorization.

Approved Design remains read-only. Do not alter its status text. Approved Plan SHA256 is an external-review result and is never self-referenced in this Plan.

## Allowed Change Scope

Allowed implementation paths:
- configs/base.py
- src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_models.py
- src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_storage.py
- src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_source.py
- src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_client.py
- src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer.py
- scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py

Allowed verification paths:
- tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py
- tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py
- tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py
- tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py
- tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
- tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py

Allowed documentation paths:
- docs/plans/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-implementation-plan_CN.md
- docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md only after completion audit

Allowed generated/runtime artifacts:
- pytest tmp_path only, never committed
- data/external_signal_shadow/stage1_6e_b/semantic_trigger/<supervisor-run-id>/** only after separate deployment authorization
- data/external_signal_shadow/stage1_6e_b/event_observations/<event-id>/** only after separate deployment authorization

Affected but unchanged:
- E-A models/storage/client: E-A suite and E-B gate/ProfileCore byte vectors.
- 1.6D models/storage/observer/client/runner: source fixtures, upstream suite, static no-write proof.
- G2 adapter: parser fixture/current adapter suite, no historical loader.
- Stage 1.5 storage guard and Stage 1.5D/F: reserve/diff proof.

Forbidden: mutation outside scope; existing E-A or schedule-revision config changes; migration, replay/import, V2, root heuristic/default, retry, concurrency, queue, second window, more active events; private/auth/account/order API; trading/alpha/signal/PnL/cost/replay authority; real test network; broad autofix/cleanup.

## STOP Vocabulary

STOP return to Design: new artifact/state branch, changed identity/admission/window/cap, second window, changed E-A ProfileCore/1.6D writer/checkpoint, migration, retry/concurrency, private/account/order API, replay/alpha/trading authority, or Design-byte change.

STOP implementation defect: test/schema/hash/reducer/crash/storage/scope proof failure. Never modify frozen authority to conceal a defect.

## Task 0: Approved Contract, Baseline, And Scope Preflight

Authority and matrix: all invariants, P-01, P-28, P-32. Files: none.

Before editing record exact root, BASE_SHA, worktree and protected bytes outside repository. Require external APPROVED_PLAN_SHA256 but do not write it into this Plan. SHA-record approved Design, config, E-A, 1.6D, G2 and all dirty paths. Existing untracked Design is provenance only. Abort on unexpected dirty configuration/source/script/test paths and preserve them. Record E-A verifier/ProfileCore/attestation, 1.6D V3 keys/checkpoint ID/current trusted detail topology, exact G2 pair, and absence of E-B configs. Run targeted Graphify queries for verify_complete_bundle, compute_live_v3_checkpoint_id and parse_and_normalize_bapi_body, then inspect all candidate edges in source.

Proof: exact SHA/root/baseline/scope recorded; no root/request. STOP: mismatch, protected drift, needed E-A/1.6D/G2/Design change or authority expansion. Out: implementation/deployment/runtime.

## Task 1: Config SSOT, Canonical Identity, Strict Models

Authority and matrix: Design 6.3-6.5, 7.3, 8.3, 9-11; P-02, P-15, P-16, P-19. Files: config, E-B models/test.

RED then GREEN exact-key validators for permissions, environment attestation, authority receipt, consumer checkpoint, projection, admission, event contract, event checkpoint, derived ProfileCore, slot intent, observation, terminal and manifest. Reject unknown/missing/wrong type, bool-as-int, upper/malformed SHA, noncanonical/pipe identity, duplicate unequal bytes, coercion/default/auto-upgrade. Reuse E-A canonical JSON/SHA only after byte-vector equality.

Add only these Design 6.5 config assignments under one E-B heading:
~~~text
SOURCE_CHECK_INTERVAL_SEC=60, SOURCE_STALE_MS=900000,
SOURCE_HEARTBEAT_FUTURE_SKEW_MS=30000, HTTP_TIMEOUT_SEC=10.0,
EVENT_WINDOW_MS=43200000, SLOT_DEADLINE_MS=60000,
DEPTH_INTERVAL_MS=60000, PREMIUM_INTERVAL_MS=60000,
OPEN_INTEREST_INTERVAL_MS=300000, MAX_SYMBOLS_PER_NOTICE=3,
MAX_ACTIVE_EVENTS=1, SUPERVISOR_ROOT_MAX_BYTES=134217728,
SUPERVISOR_ORDINARY_RESERVE_BYTES=4194304,
SUPERVISOR_EMERGENCY_RESERVE_BYTES=1048576,
SUPERVISOR_TERMINAL_WRITE_SET_MAX_PEAK_BYTES=262144,
EVENT_ROOT_MAX_BYTES=805306368, EVENT_ORDINARY_RESERVE_BYTES=16777216,
EVENT_EMERGENCY_RESERVE_BYTES=4194304,
EVENT_TERMINAL_WRITE_SET_MAX_PEAK_BYTES=2097152,
EVENT_MANIFEST_MAX_BYTES=1048576, DEPTH_MAX_RAW_RESPONSE_BYTES=262144,
SINGLE_ROW_MAX_RAW_RESPONSE_BYTES=32768.
~~~
All names use the EXTERNAL_SIGNAL_STAGE1_6E_B prefix. Fixed vectors cover environment, receipt, consumer checkpoint, projection, notice, admission, event, profile attestation, slot and manifest IDs, plus exact twelve false permissions. Event-checkpoint fixtures reject a missing/unknown key, bad event-contract SHA, bad nested profile map, unordered completed slots, bad last-observation hash, invalid intent stage/raw relation, and bool-as-int. Task 10 AST proof permits only these 22 assignments and one heading against Task-0 config base; it cannot use/widen schedule-revision helper.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py
~~~
STOP: hidden threshold, alias/default, coercion/schema upgrade, or config diff outside additions. Out: E-A/schedule-revision changes.

## Task 2: E-A Runtime Gate, Roots, Storage

Authority and matrix: Design 6.1-6.2.1, 7.1, 11.2, 11.5; P-03, P-04, P-24, P-25, P-27. Files: E-B storage/test, models/test.

RED E-A gate: locate and call the frozen E-A Step-A environment-projection helper/grammar, recompute its exact projection on the current host, then compare the Design equality set against the read-back E-A same-schema attestation. Require read-only complete verifier, exact manifest and authorized clean E-B deployment. No independently reconstructed subset is acceptable; all pass before source/client. Implement only E-B atomic write/read-back, bounded JSONL, regular-file guard, closed-tree validation, accounting and zero-byte flock with standard library. Fresh roots use mkdir nonexistence and nonblocking global/lifetime locks. Reject inferred/relative/latest/glob roots, collision, foreign/multiple nonterminal root, symlink/FIFO/socket/device, temp/orphan and lock mutation.

Write/read-back E-B same-schema attestation then authority receipt. Supervisor grammar: lock, attestation, receipt, source checkpoint, projections, admissions, source raw, terminal. Event grammar: lock, attestation, receipt, event contract/checkpoint, profile attestations, observations, raw, terminal, manifest last. Test wrong/missing/malformed/hash E-A artifact, closed-tree extra, each environment mismatch, dirty deployment, root path/special file/collision/lock. Every failure has zero source/client work. Test aggregate reserve of 1.5D + 1.5F + 1.6D + E-A + E-B supervisor + one E-B event.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_storage.py tests/research/external_signal_shadow/test_stage1_5_storage_guard.py
~~~
STOP: E-A incompatibility, root/device/reserve failure, new artifact. Out: E-A/shared-guard change, migration/resume heuristic.

## Task 3: Exact 1.6D Source Consumer

Authority and matrix: Design 7.2-7.3, 8.1; P-05 through P-09, P-26. Files: E-B source/test.

RED source API accepts only absolute source root/run ID, never latest/glob/mtime/scan/fallback/relative/later substitution. Before loader/default/mutation/raw/G2/client snapshot capture contract, profile attestation, checkpoint. Verify run/mode/profile, attestation SHA, V3 exact keys, trusted/successful/null terminal, ID and heartbeat range. Reuse only 1.6D V3 checkpoint ID computation.

Verify committed stream offsets/hashes, JSONL boundary, zero-offset detail case, raw/revision/observation linkage. Resume requires old prefix, old offset less/equal new, old final and detail last-line hash intact. Persist/read-back consumer checkpoint. Fresh bootstrap copies no raw/projection/admission/network. Process post-bootstrap record/article/revision order. Degraded source blocks new admission; advancing valid source restores ready. A pre-existing active event remains independent: it continues dispatching due eligible slots and completes its terminal lifecycle while source is degraded, but no new projection/admission is produced.

Fixtures: source selection rejects; run/mode/profile/attestation mismatch; V2/missing/unknown/bad ID/future/stale heartbeat; missing/cross-offset/hash/raw/revision-observation; C1-C2 append pass; truncate/rewrite/replacement/missing stream fail. Also prove active event plus stale/invalid source gives source_degraded, zero new projection/admission, continued due-slot dispatch; subsequent source recovery leaves active event unchanged and any later admission remains capacity-limited. Structural failure zero projection/checkpoint advance/request.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py
~~~
STOP: source migration/default or 1.6D semantic change. Out: 1.6D mutation, V2, historical multiplicity.

## Task 4: G2 Semantic Projection

Authority and matrix: Design 8.1-8.3; P-09, P-10, P-11, P-20. Files: E-B observer and tests.

RED reducer accepts exactly one trusted live observation matching article, raw SHA/path, BAPI detail V1 and live mode; raw regular hash matches. Atomically copy/read-back source raw under source_detail_raw/<sha>.bin. Call only G2 parse_and_normalize_bapi_body with frozen pair, never historical loader. Durable projection/read-back precedes admission/client.

Structural data-code/grammar/observation/raw/profile/checkpoint failure creates zero projection, zero consumer-checkpoint advancement, and zero market-data request. Semantic blocker persists a noneligible projection only after read-back. Fixtures: valid H2, malformed envelope, unresolved body, incomplete declaration, conflict, out-of-scope, zero/more-than-three symbols, settlement missing/unparseable/past, no raw direct-to-network.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py
~~~
STOP: grammar/classifier/fallback change or structural projection. Out: G2/source change.

## Task 5: Projection, Admission, Event Contract, Profiles

Authority and matrix: Design 7.3, 8.3, 9.1-9.2; P-11 through P-15, P-25. Files: E-B observer/models/storage tests.

Stable projection ID accepts duplicate only with exact bytes. Mandatory dedicated crash proof: C1 commits R, P durable with C1 provenance, crash before consumer checkpoint, C2 commits same R/raw, restart reuses exact P bytes and time, C1 remains in event provenance. Rerun G2 and exact-compare deterministic fields except Design-permitted ID/provenance/time fields.

First eligible projection writes one immutable notice admission before consumer advance. Active event creates final capacity-blocked, no root/queue/readmission. Later revisions only semantic audit. Add a post-admission semantic-conflict fixture: first revision is admitted, a later revision of the same notice conflicts with admitted semantic facts, then a durable not_eligible projection has blocker post_admission_semantic_conflict; admission bytes/event contract remain unchanged and no second event exists. Event contract binds projection/admission SHA, revision/raw, C1 checkpoint ID/SHA, twelve-hour window from projection time, E-A manifest/four profile attestation SHA, E-B attestation/receipt SHA, storage contract, false permissions. Never substitute C2.

Create independent canonical ProfileCore per symbol times four E-A profiles only by Design transform. Exact vectors prove all other endpoint/header/parser/time fields unchanged. Test first/equal duplicate/conflict/capacity/later revision/one-three symbols/root scan/C1-C2 same event/window/admission.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
~~~
STOP: changed identity/admission/window/cap/ProfileCore or branch. Out: terminal wakeup, dormancy, queue, multiple event.

## Task 6: Slot Scheduler And Public Client

Authority and matrix: Design 10 and 12; P-16 through P-18, P-30. Files: E-B client/observer tests.

RED schedule: depth 720, premium 720, OI 144, funding start/end, total 1586 per symbol and <=4758/event. Same due order depth/premium/funding/open interest/lexical symbol. Due and due plus deadline minus one allowed; deadline and later missed, zero request. No catch-up/retry.

One sequential standard-library URL client: public GET, no proxy/redirect/cookie/auth, identity encoding, exact E-A host/path/header/profile validation, configured timeout. Tests inject opener. Before request persist/read-back slot intent with exact slot/request identity/sequence/base profile/symbol/due/reserved/stage. At most one actual attempt; prepared no-observation becomes unknown after restart, never reissued. Inject timeout/transport/redirect/status/encoding/oversize/schema/time and prove no retry/async/thread/executor/extra endpoint.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
~~~
STOP: retry/concurrency/alternate endpoint or E-A transport incompatibility. Out: websocket/private API/profile expansion.

## Task 7: Observation, Terminal, Manifest

Authority and matrix: Design 11.1-11.5; P-19 through P-24. Files: E-B storage/observer/models tests.

Exact outcomes: missed deadline, verified, timeout, transport, redirect, HTTP, encoding, raw size, schema, time, unknown after restart. Assert dispatch, sequence, status, headers, raw flag/SHA/path/size, schema/time, reason. Content-addressed raw must read-back/hash/size before provenance and respect caps.

All durable success gives complete/complete; durable fail/miss gives complete/incomplete; storage/integrity gives failed exact reason/no manifest. Verify event/per-symbol expected/durable/success/failed/missed algebra. Manifest last after valid complete terminal only. Verify exact schema, all/only regular files excluding manifest, lexical order, hashes/bytes, event/terminal hashes, coverage and manifest ID. Reject unknown/missing/temp/symlink/hash/size/duplicate/order errors.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
~~~
STOP: outcome/total/manifest/provenance error or new artifact. Out: report/replay/alpha and failed/supervisor manifest.

## Task 8: Crash, Restart, WAL

Authority and matrix: Design 7.3, 12-13; P-12, P-18, P-21, P-23, P-25, P-26. Files: E-B source/storage/observer tests.

Fault injection only: C0 intent; C1 prepared before request; C2 request before raw; C3 raw before observation; C4 observation before checkpoint; C5 admission before root; C6 root before supervisor checkpoint; C7 projection before source checkpoint; C8 terminal failure; C9 manifest failure.

Matrix: no intent/observation evaluates once; matching intent/observation checkpoint only; prepared/no observation or valid raw/no observation creates unknown and no request; corrupt raw fails integrity/no request; one observation ahead rolls forward; checkpoint ahead/orphan raw/slot mismatch/more than one ahead rejects unchanged. Resume only explicit absolute supervisor root after root/global validation. Fresh invalid/multiple/nonowned nonterminal root rejects without wait. Repeat C1-P-crash-C2 proof end-to-end with no duplicate admission/event/request.

The following admission-root-terminal transition matrix is mandatory and is separate from the slot-WAL matrix above:

| Crash point and validated durable state | Required restart action | Active-event checkpoint | HTTP / forbidden action |
|---|---|---|---|
| C5: exact admitted row; deterministic event root absent; consumer active fields null | validate exact admission, create only its deterministic event_id root, write/read-back exact attestation, receipt, contract, profiles and initial event checkpoint | atomically set the same active_notice_event_key and event_id only after the root is valid | zero HTTP before checkpoint; no duplicate admission/root |
| C6: exact admitted row; exactly one valid nonterminal deterministic root owned by resumed supervisor; consumer active fields null | validate root contract/profile/checkpoint and root ownership; do not recreate it | checkpoint-only set same active_notice_event_key and event_id, then continue the slot reducer | zero duplicate admission/root; normal later slots only after checkpoint |
| C5/C6 negative: wrong event-id root, multiple matching roots, malformed root, foreign supervisor ownership, admission/root contract mismatch | preserve all bytes unchanged | do not set or clear active fields | global_active_supervisor_state_invalid; zero HTTP |
| C8: terminal write/read-back failed or terminal malformed | preserve root as nonterminal blocker; do not invent/rewrite terminal | retain active fields | zero HTTP, zero new event/admission/root |
| C9: valid complete terminal but manifest absent or manifest write/read-back/closed-tree validation failed | preserve terminal-without-manifest root as blocker; do not restart observing or rewrite a manifest | retain active fields | zero HTTP, zero new event/admission/root |
| valid complete terminal and valid manifest | validate closed tree and manifest | clear active fields only after validation | zero HTTP; later unrelated notice may be considered |
| valid failed terminal, manifest absent, writer stopped | validate failed terminal and no manifest | clear active fields only after validation | zero HTTP; later unrelated notice may be considered |

The C5/C6 test fixture must assert exact admission bytes, event ID, root path, active_notice_event_key, active_event_id and zero duplicate root creation. The C8/C9 fixture must assert that a complete terminal alone does not release global capacity: active_event_id stays set, the root remains preserved, no seal exists, no new notice admission occurs, and no event re-observation/reissue is permitted. Event checkpoint validation runs before every reconciliation and validates its exact key set, nested profile-attestation map, contract SHA, ordered completed slots, last-observation SHA and inflight intent cross-fields.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py
~~~
STOP: reissue, inferred resume, new durable artifact/state change. Out: terminal reuse/uncertain request retry.

## Task 9: Integration, Regression, Static Safety

Authority and matrix: Design 6.3, 14-17; P-27 through P-31. Files: allowed tests and runner test.

Runner RED/GREEN requires explicit E-A root, 1.6D root/run, E-B deployment identity and optional exact resume. Task 2 executes before source/client. Missing/relative/ambiguous input rejects; one sequential loop; no runtime authority default.

Run focused E-B and unchanged 1.6D models/storage/observer/client/runner, G2 adapter, E-A models/storage/client/runner, shared guard. Static scan rejects historical loader, 1.6D writer, E-A mutation, async/thread/executor, retry/backoff/websocket, proxy/cookie/auth/account/order/execution/paper/live trading/replay/alpha/signal. Assert all permissions and RISK_LIVE_TRADING_ENABLED false. Scope proof requires changed paths equal allowlist/mapped task, no generated data and no E-A/1.6D/G2/1.5D/F diff.

Proof command:
~~~bash
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_models.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_storage.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_source.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_client.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer.py tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
PYTHONPATH=src:. .venv/bin/pytest -q tests/research/external_signal_shadow/test_stage1_6b_canonical_source_models.py tests/research/external_signal_shadow/test_stage1_6b_canonical_source_storage.py tests/research/external_signal_shadow/test_stage1_6b_canonical_source_observer.py tests/research/external_signal_shadow/test_stage1_6b_canonical_source_client.py tests/scripts/external_signal_shadow/test_run_stage1_6b_live_source_observer.py tests/research/external_signal_shadow/test_stage1_6a_sealed_export_adapter.py tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_models.py tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_storage.py tests/research/external_signal_shadow/test_stage1_6e_a_market_data_capability_client.py tests/scripts/external_signal_shadow/test_run_stage1_6e_a_market_data_capability_audit.py tests/research/external_signal_shadow/test_stage1_5_storage_guard.py
ruff check configs/base.py src/research/external_signal_shadow/stage1_6e_b_live_semantic_observer_*.py scripts/external_signal_shadow/run_stage1_6e_b_live_semantic_trigger_observer.py tests/research/external_signal_shadow/test_stage1_6e_b_live_semantic_observer_*.py tests/scripts/external_signal_shadow/test_run_stage1_6e_b_live_semantic_trigger_observer.py
~~~

STOP: upstream regression, authority scan hit, reserve/scope failure or upstream API need. Out: upstream change, broad cleanup, deployment.

## Task 10: Completion Audit And Deployment Handoff

Authority and matrix: Design 16-17; P-01, P-28 to P-32. Files: allowed completion-audit document only after implementation/audit.

Rerun Task 0 Design/Plan SHA gate. Record BASE_SHA, FINAL_SHA, changed inventory, config AST proof, focused/upstream/co-tenant results, static scan, root/writer inventory and false permissions. Invoke .agent/skills/audit-plan-completion. Only a complete verdict may be written to allowed completion audit; otherwise STOP implementation defect.

Handoff states implementation completion is not deployment authority, deployment_allowed=false, and Plan made no runtime root/session/request. Separate reviewed/user-approved VPS deployment authorization must bind implementation commit, E-A root/manifest, exact 1.6D root/run, storage preflight and runbook before runtime.

STOP: noncomplete audit, SHA/scope drift, missing evidence or deployment inference. Out: commit/push/VPS sync/session/deployment/live request.

## Completion Acceptance Matrix

Mandatory, not guidance. Every row needs Task-10 executable evidence; absence is STOP.

| ID | Proof edge | Mechanical evidence | Task |
|---|---|---|---:|
| P-01 | Approved Design binding | exact SHA before edits | 0,10 |
| P-02 | Config SSOT | AST/config assignments | 1,10 |
| P-03 | E-A environment identity | closed-tree, exact E-A Step-A projection vector, equality fixtures | 2 |
| P-04 | Exact E-B roots | path/symlink/special file | 2 |
| P-05 | Authorized 1.6D root | exact root/run, no latest/glob | 3 |
| P-06 | V3 checkpoint authority | exact keys/hash/heartbeat | 3 |
| P-07 | Prefix monotonicity | C1-C2 pass, rewrite/truncate fail | 3 |
| P-08 | Bootstrap no replay | zero projection/raw/network | 3 |
| P-09 | Trusted live linkage | exactly one trusted observation | 3,4 |
| P-10 | Structural/semantic split | no projection vs noneligible | 4 |
| P-11 | Projection determinism | stable ID/exact reuse | 4,5 |
| P-12 | Moving checkpoint crash | C1-P-crash-C2-reuse P | 5,8 |
| P-13 | Notice once | final/no readmission plus post-admission semantic-conflict fixture | 5,8 |
| P-14 | Event provenance | projection/admission/checkpoint hashes | 5 |
| P-15 | Derived ProfileCore | exact four times symbol vectors | 1,5 |
| P-16 | Slots | 1586 per symbol/order | 6 |
| P-17 | Deadline | equality/+1, zero late request | 6 |
| P-18 | At-most-one request | WAL/crash/no reissue | 6,8 |
| P-19 | Observation grammar | every exact outcome | 7 |
| P-20 | Raw provenance | path/hash/size | 4,7 |
| P-21 | Reconciliation | event-checkpoint schema plus zero/one-ahead/invalid state matrix | 1,8 |
| P-22 | Complete terminal | totals/coverage | 7 |
| P-23 | Failed terminal | storage/integrity/no manifest and terminal-write blocker | 7,8 |
| P-24 | Closed-tree manifest | inventory/hash/bytes/order | 2,7 |
| P-25 | Single active event | lock/root/capacity plus C5/C6/C8/C9 active-state fixtures | 2,5,8 |
| P-26 | Resume | explicit exact root plus C5/C6 exact-root reconciliation | 3,8 |
| P-27 | Storage reserves | co-tenant algebra | 2,9 |
| P-28 | No upstream mutation | 1.6D/1.6C/E-A diff/static | 0,9,10 |
| P-29 | Safety authority | all flags false | 1,9 |
| P-30 | No hidden network | no auth/private/order/retry/parallel | 6,9 |
| P-31 | Full regression | focused/upstream/co-tenant | 9 |
| P-32 | Completion audit | mandatory before deployment | 10 |

## Plan Review Checklist

- [ ] Every Design edge maps to Task, proof and STOP.
- [ ] Behavioral tasks are RED then GREEN with paths, interface, command and non-goal.
- [ ] No factory, registry, worker, or queue; existing pure primitives and standard library only.
- [ ] E-B config AST proof cannot weaken schedule-revision policy.
- [ ] Passing tests or Plan approval never implies deployment/runtime authority.
- [ ] Review must be Approve and user must explicitly authorize implementation before code.
