# Stage 1.6E-B Live Semantic Trigger And Event-Level Market-Data Observer Design

**日期:** 2026-09-03  
**状态:** `design_draft`  
**Design authority:** 本文尚未批准；`implementation_plan_allowed=false`，`implementation_allowed=false`，`deployment_allowed=false`，`runtime_action_allowed=false`。  
**Revision authority:** Closure Audit, `review_mode=closure_audit`; pre-revision candidate SHA-256 `19350bfce6743aef6c1c920e5b800fcd69847b97c60a82391c0dd0a41e805848`; `scope_expanded=false`。  
**Second revision authority:** Closure Audit follow-up; pre-second-revision candidate SHA-256 `ad9d3d6bcf1b85b32fd96c9c01a8cc32e0a4cca7199133a393ffed53ffc3dbc6`; `scope_expanded=false`。
**Third revision authority:** Closure Confirmation follow-up; pre-third-revision candidate SHA-256 `ec4e3b07b9aa6ae0c6db5d7972fa38839ada1aed5a8021d1db13b0b09a2a980c`; `scope_expanded=false`。
**上游 authority:**

1. `docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`
2. `docs/designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`
3. `docs/designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md`
4. `docs/designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md`
5. `docs/designs/2026-08-30-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-design_CN.md` (SHA-256 `8703e4804fe924b5b43ad1b431d1ffc2239b045510bea2fae94ab1305c1cead3`)
6. `docs/reviews/2026-08-31-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-completion-audit_CN.md` (E-A complete Manifest ID `e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3`)
7. `docs/project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md`

## 0.1 Closure Revision Record

**Mutable set:** 本文的 E-B source/environment/admission/slot/restart/terminal/config/verification contracts。  
**No-touch set:** 1.6D source writer/root/session/polling cadence, 1.6C G2 grammar bytes, E-A approved Design SHA/ProfileCore bytes/endpoints, 12-hour MVP, three-symbol cap, public-read-only permissions, and all existing `configs/base.py` assignments.

| Audit item | Resolution | Reason / closure edge |
|---|---|---|
| P0-1 | adopted | Section 6.2.1 reuses the exact E-A attestation schema and isolates E-B/E-A binding in a separate immutable receipt. |
| P0-2..P0-5 | adopted | Sections 7.2-7.3 freeze one deployment-authorized source root/run, the three-artifact binding, complete stream snapshots, null bootstrap state, and two-sided heartbeat freshness. |
| P0-6 | adopted | Section 8 makes provenance/grammar contradictions source structural failures, distinct from durable semantic `not_eligible` outcomes. |
| P0-7 | adopted | Section 9.1 makes the first eligible projection create one final notice-level admission; later revisions cannot create another event. |
| P0-8..P0-9 | adopted | Section 13 adds a single-flight durable request intent plus a closed observation/checkpoint reconciliation matrix. |
| P0-10 and supervisor continuity | adopted | Sections 7.1 and 9.1 scan both root families, require explicit supervisor resume, and define complete/failed active-event release versus terminal-write blockers. |
| P1-1 multi-observation source linkage | not adopted | The proposed historical 1.6A rule conflicts with current 1.6D V3 live topology: one article enters `trusted_detail_observed` terminal state after its one trusted observation. E-B consumes that live topology, not a sealed historical export. |
| P1-4 separate `semantic_trigger_receipt.json` | adopted in smaller form | The same immutable authority fields are added to existing `event_contract.json`, which is already first-request durable and manifested. A second receipt file adds no authority. |
| P1-2, P1-3, P1-5, P1-6, P2-1, P2-2 | adopted | Canonical identities, future config SSOT, exact reducer grammar, honest sequential timing, and wording/grammar corrections. |
| Follow-up P0-1 | adopted | `request_outcome_unknown_after_restart` records no dispatch timestamp because a durable reservation cannot prove the HTTP call began. |
| Follow-up P0-2 | adopted | Projection identity excludes volatile time; the immutable persisted projection timestamp now fixes the event window through admission/restart. |
| Follow-up P1-1..P1-3 and P2 | adopted | The later-admission branch, manifest schema, nested authoritative structures, supervisor terminal vocabulary, and raw boolean wording are frozen. |
| Withdrawn previous P1-1 | `previous_P1_1=RETRACTED_REVIEWER_ERROR` | The reviewer confirmed the current one-live-revision/one-trusted-observation rule is correct for 1.6D V3 and needs no Design change. |
| Third-review P0 | adopted | An existing projection retains immutable first-validating checkpoint provenance while a newer valid 1.6D boundary proves the same revision/raw lineage remains committed. |
| Third-review P1-1/P1-2/P2 | adopted | The later-revision branch, outcome matrix, and D-04 wording now have one exact interpretation. |

Review findings remain investigation inputs. The approved E-A contract and current 1.6D source topology override any incompatible reviewer premise.

**Author-side mini Closure Confirmation (not approval):** `previous_followup_p0_closed=2/2`; `revision_introduced_p0_closed=1/1`; `required_p1_closed=5/5`; `withdrawn_reviewer_error=1`; `partial_closure_count=0`; `revision_introduced_p0_count=0`; `no_touch_violation_count=0`; `scope_expanded=false`. Independent Closure Confirmation remains required before any approval or Implementation Plan.

## 1. Final Claim

Stage 1.6E-B may run one bounded public-read-only supervisor in the approved E-A execution environment. It consumes only a validated committed boundary of the active Stage 1.6D live root, turns a trusted BAPI detail revision into its own durable semantic projection with the approved 1.6C G2 body grammar, and only then starts at most one 12-hour event-level USD-M market-data observer for at most three eligible symbols.

The observer records exact public REST request/profile/raw-response provenance for four E-A-proven endpoint families. It seals both complete and explicitly incomplete coverage bundles, but it never grants point-in-time replay, alpha, execution, cost/profit, paper-trading, live-trading, or order authority.

## 1.1 Core Issue

The project has a live official delisting-source capture (1.6D), an approved body grammar (1.6C G2), and a verified public market-data capability bundle (E-A), but no durable authority boundary connecting them. Directly reacting to a 1.6D raw body would bypass semantic validation and would make an HTTP request depend on mutable source state. Reusing E-A's `BTCUSDT` ProfileCore with an unrecorded symbol override would likewise make event-symbol requests unverifiable. E-B resolves only those boundaries: source checkpoint to semantic projection, then semantic projection to an independently attested event bundle.

## 2. Confirmed Facts

1. Stage 1.6D is the active official Binance English Delisting catalog/detail observer. Its live checkpoint is one atomically replaced `observer_checkpoint.json`, not a `checkpoints/checkpoint_*.json` history.
2. A valid live checkpoint is `stage1_6b_observer_checkpoint_v3`. It binds `checkpoint_id`, `stream_offsets`, `stream_last_hashes`, `candidate_states`, `heartbeat_at_ms`, `last_index_poll_status`, `last_index_poll_coverage`, and `pending_terminal_failure_reason`.
3. `detail_revisions.jsonl` identifies a trusted detail revision; linked `detail_observations/<UTC-date>.jsonl` identifies the actual request and content-addressed `raw_payloads/detail/<article-id>/<sha256>.bin` contains the raw body.
4. The 1.6C full sealed-export adapter is explicitly historical-only. Its G2 BAPI body grammar (`stage1_6a_bapi_body_tree_v2`, `stage1_6a_extractor_v2`) is reusable; its `historical_backfill`/sealed-export loader contract is not.
5. E-A proved four fixed Binance USD-M public REST endpoint families in the VPS environment. Its ProfileCore bytes bind `BTCUSDT`, so E-B must not issue an event-symbol request by applying an unrecorded runtime override to an E-A profile.
6. The current Stage 1.6 route map forbids E-B from being directly triggered by 1.6D raw source evidence and forbids restarting, reusing, modifying, or resealing 1.6D or E-A roots to start E-B.
7. `RISK_LIVE_TRADING_ENABLED=False` is the project L0 invariant.

## 3. Assumptions

1. The authorized VPS retains the E-A complete root named in Section 1, allowing E-B runtime preflight to verify its closed tree and recover the E-A per-profile attestation hashes. This is a runtime precondition, not an assumption that may be bypassed.
2. Stage 1.6D continues to use its frozen 300-second live polling cadence. E-B does not alter that cadence.
3. A product-operations estimate says a three-symbol cap covers most historical USD-M delisting announcements. This is not project-verified evidence and must never appear as an E-B coverage conclusion.

## 4. Scope And Non-Goals

### 4.1 In Scope

1. A read-only Stage 1.6D committed-checkpoint consumer.
2. A durable E-B semantic projection, based on one validated trusted detail revision and the G2 grammar.
3. A single active 12-hour event observer for qualified USD-M crypto perpetual symbols.
4. Exact raw-response, request, profile, checkpoint, terminal, and manifest provenance for the four E-A-proven public profiles.
5. Controlled restart without reissuing a durably completed slot.

### 4.2 Explicit Non-Goals

1. Modifying Stage 1.6D code, root, checkpoint, stream, lock, tmux session, polling schedule, or source-profile attestation.
2. Direct raw-to-network triggering. Raw source bytes may be read only to create a durable, verified E-B semantic projection; no market-data request is admitted before that projection is durable and read back.
3. Any second terminal/delisting-time observation window, dormant state, wake-up queue, timer, or delayed scheduler.
4. Historical replay, backfill, market coverage claim, mechanism conclusion, alpha interpretation, trade signal, paper trading, live trading, execution engine, private/authenticated API, account API, or order API.
5. Reusing an E-A root, E-A ProfileCore bytes, a terminal event root, or a sealed event root as a writable root.

### 4.3 Deferred Upgrade

`two_stage_delisting_terminal_window_v1` is a possible future Design delta: it may define a separate pre-terminal observation window near a verified effective delisting time. This Design creates no corresponding state, field, timer, queue, task, or implementation hook. It is not implementation authority.

## 5. Decisions

| ID | Decision | Reason |
|---|---|---|
| D-01 | E-B reads 1.6D committed state read-only and produces its own semantic projection before any market request. | Preserves the route-map raw-input boundary without altering 1.6D. |
| D-02 | The supervisor reads the source checkpoint every 60 seconds; stale after 900 seconds. | More frequent read than the 1.6D source poll bounds reaction latency; three source periods tolerate ordinary delay but fail closed for new admission. |
| D-03 | A valid G2 semantic trigger requires a future parseable settlement time. | E-B records an authoritative, unambiguous `effective_delist_time_ms`; it does not infer an unstated time. |
| D-04 | Each event has a fixed 12-hour window from immutable persisted `semantic_projection.semantic_projected_at_ms`. | Bounded MVP with deterministic storage and request count. |
| D-05 | Sampling is profile-specific: depth/premium 60 seconds; OI 5 minutes; funding at start/end only. | Matches endpoint semantics without useless funding-history polling. |
| D-06 | One notice is all-or-blocked at three eligible symbols; globally only one active event exists. | There is no intentional subset selection. Sequential collection can still produce asymmetric missed slots under failure; the terminal exposes that asymmetry. |
| D-07 | A delayed slot expires at 60 seconds without an HTTP request. | No catch-up request may masquerade as an on-time observation. |
| D-08 | Network/schema failures persist one failed slot and later slots continue; storage/integrity failure stops the event. | Preserves available later evidence without making an incomplete event look complete. |
| D-09 | An E-B event ProfileCore is canonical and event-symbol-specific, derived only through the exact transform in Section 9. | E-A's `BTCUSDT` bytes cannot authorize a different symbol by implicit parameter override. |
| D-10 | Semantic eligibility and runtime event admission are separate immutable records. | A durable semantic fact cannot be rewritten merely because the single active-event capacity is occupied. |

## 6. Authority And Trust Boundary

### 6.1 Permitted Read Graph

```text
validated E-A sealed complete root
  -> E-B environment/profile authority

validated 1.6D observer_checkpoint + committed streams + linked raw bytes
  -> E-B semantic projection
  -> E-B event contract
  -> E-B public market-data requests
  -> E-B event evidence bundle
```

The first arrow verifies market-source capability and execution-environment identity. The second arrow is source provenance. The semantic projection is a mandatory durable boundary between them and all public REST requests.

### 6.2 E-A Runtime Attestation Gate

Before E-B creates a root, reads a source raw payload, or makes a network request, it must:

1. verify the E-A root as a complete closed bundle using the E-A verifier;
2. require Manifest ID exactly `e918b344b6781bbdb0cd005b3744acf3bb0d370e98ddd5c2973312dc974874b3`;
3. load and validate the E-A `stage1_6e_a_execution_environment_attestation_v1`;
4. recompute the E-A Step-A projection grammar on the current host; and
5. require current `deployment_host_identity`, `project_root_realpath`, `network_namespace_inode`, and `proxy_environment` to exactly equal the E-A attestation; require current `capability_root_parent_filesystem_st_dev == E-A.root_filesystem_st_dev`; and require current `shared_lock_filesystem_st_dev == E-A.shared_lock_filesystem_st_dev`.

The E-B deployment commit is separately authorized by its future deployment authorization. It must be a clean approved E-B deployment, but it is intentionally not required to equal the E-A implementation commit. After fresh-root creation and writer-lock acquisition, E-B requires `root_filesystem_st_dev` to equal current `capability_root_parent_filesystem_st_dev`, E-A attested `root_filesystem_st_dev`, E-A attested `shared_lock_filesystem_st_dev`, and the Section 7.1 global-lock filesystem device; only then it writes its E-B environment attestation and authority receipt and may read source raw bytes.

Any missing/malformed E-A artifact, closed-tree failure, manifest mismatch, stable-field mismatch, non-clean approved E-B deployment identity, root-filesystem mismatch, or unavailable shared filesystem is `environment_attestation_failed`: no source read or network request is allowed.

### 6.2.1 E-B Same-Schema Attestation And Authority Receipt

Each E-B supervisor/event root writes `execution_environment_attestation.json` before it consumes source bytes or makes a market request. It reuses the E-A schema without extension:

```text
schema_version = stage1_6e_a_execution_environment_attestation_v1
execution_environment_id
deployment_host_identity
hostname
project_root_realpath
root_filesystem_st_dev
shared_lock_filesystem_st_dev
network_namespace_inode
proxy_environment
runtime_user_uid
deployment_git_commit
deployment_runtime_worktree_clean = true
permissions
```

`execution_environment_id` uses the frozen E-A canonical identity projection. E-B's `deployment_git_commit` is the separately authorized clean E-B commit. Only `deployment_host_identity`, `project_root_realpath`, `root_filesystem_st_dev`, `shared_lock_filesystem_st_dev`, `network_namespace_inode`, and `proxy_environment` must equal E-A's attested values; `hostname`, `runtime_user_uid`, and deployment commit are recorded but are not E-A equality predicates.

Each root also writes the separate immutable control artifact `environment_authority_receipt.json` with exactly:

```text
schema_version = stage1_6e_b_environment_authority_receipt_v1
root_kind = supervisor | event
e_a_manifest_id
e_a_manifest_sha256
e_a_environment_attestation_sha256
e_b_execution_environment_attestation_sha256
permissions
receipt_id
```

`receipt_id = SHA256(canonical_json(the object with only receipt_id omitted))`. The three SHA-256 fields hash exact read-back files. Unknown, missing, noncanonical, or mismatched fields in either artifact reject the E-B root before source/network work.

### 6.3 Permissions Object

Every E-B first-party semantic/control artifact contains exactly this object:

```json
{
  "RISK_LIVE_TRADING_ENABLED": false,
  "execution_feasibility_claim_allowed": false,
  "net_cost_or_profit_claim_allowed": false,
  "replay_allowed": false,
  "alpha_interpretation_allowed": false,
  "trade_signal_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "private_api_allowed": false,
  "authenticated_api_allowed": false,
  "order_api_allowed": false
}
```

Raw bytes and canonical ProfileCore bytes do not inject this object.

### 6.4 Acceptance Invariants

1. `INV-01 Source boundary`: no E-B market request occurs without a fresh, internally validated 1.6D V3 checkpoint and committed source linkage.
2. `INV-02 Semantic boundary`: no E-B market request occurs before the corresponding immutable eligible projection and admitted event record are durable/read-back valid.
3. `INV-03 Profile authority`: every E-B request has exactly one event ProfileCore derived by the Section 9.2 transform and bound to the verified E-A manifest/profile attestation.
4. `INV-04 Bounded observation`: one event has 1-3 symbols, one 12-hour window, 1,586 slots per symbol, at most one HTTP attempt per network-admitted slot, and at most one active event globally. A crash after durable prepared intent leaves the actual count conservatively unknown (zero or one) and never permits reissue.
5. `INV-05 Timing honesty`: a slot at or after its 60-second deadline produces no HTTP request and is recorded as missed.
6. `INV-06 Immutable lifecycle`: E-B never changes 1.6D/E-A artifacts; it never rewrites a semantic projection/admission, reuses a terminal root, or reissues a durable completed slot.
7. `INV-07 Evidence honesty`: only a complete terminal with a valid closed-tree manifest is sealed; `coverage_status=incomplete` is explicitly non-authoritative for coverage/mechanism/replay claims.
8. `INV-08 Safety`: every authority flag remains false, including `RISK_LIVE_TRADING_ENABLED`; public unauthenticated read-only HTTP is the only remote operation.
9. `INV-09 Canonical identity`: every SHA-256 is lowercase `^[0-9a-f]{64}$` over UTF-8 `canonical_json` bytes: recursively lexicographic object-key ordering, compact JSON separators, no whitespace, no NaN/infinity, and no pipe-delimited identity grammar.

### 6.5 E-B Operational Configuration Authority

All operational, resource, and network thresholds below are future `configs/base.py` E-B assignments. They are the only runtime authority for these values; this Design neither changes existing E-A nor schedule-revision configuration assignments.

```text
EXTERNAL_SIGNAL_STAGE1_6E_B_SOURCE_CHECK_INTERVAL_SEC = 60
EXTERNAL_SIGNAL_STAGE1_6E_B_SOURCE_STALE_MS = 900000
EXTERNAL_SIGNAL_STAGE1_6E_B_SOURCE_HEARTBEAT_FUTURE_SKEW_MS = 30000
EXTERNAL_SIGNAL_STAGE1_6E_B_HTTP_TIMEOUT_SEC = 10.0
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS = 43200000
EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS = 60000
EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_INTERVAL_MS = 60000
EXTERNAL_SIGNAL_STAGE1_6E_B_PREMIUM_INTERVAL_MS = 60000
EXTERNAL_SIGNAL_STAGE1_6E_B_OPEN_INTEREST_INTERVAL_MS = 300000
EXTERNAL_SIGNAL_STAGE1_6E_B_MAX_SYMBOLS_PER_NOTICE = 3
EXTERNAL_SIGNAL_STAGE1_6E_B_MAX_ACTIVE_EVENTS = 1
EXTERNAL_SIGNAL_STAGE1_6E_B_SUPERVISOR_ROOT_MAX_BYTES = 134217728
EXTERNAL_SIGNAL_STAGE1_6E_B_SUPERVISOR_ORDINARY_RESERVE_BYTES = 4194304
EXTERNAL_SIGNAL_STAGE1_6E_B_SUPERVISOR_EMERGENCY_RESERVE_BYTES = 1048576
EXTERNAL_SIGNAL_STAGE1_6E_B_SUPERVISOR_TERMINAL_WRITE_SET_MAX_PEAK_BYTES = 262144
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES = 805306368
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ORDINARY_RESERVE_BYTES = 16777216
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_EMERGENCY_RESERVE_BYTES = 4194304
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_TERMINAL_WRITE_SET_MAX_PEAK_BYTES = 2097152
EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_MANIFEST_MAX_BYTES = 1048576
EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_MAX_RAW_RESPONSE_BYTES = 262144
EXTERNAL_SIGNAL_STAGE1_6E_B_SINGLE_ROW_MAX_RAW_RESPONSE_BYTES = 32768
```

## 7. Supervisor And Source-Consumer Contract

### 7.1 Fresh Supervisor Root

Before creating a supervisor root, E-B obtains an exclusive non-blocking lifetime `flock` on exactly:

```text
data/external_signal_shadow/stage1_6e_b/.stage1_6e_b_supervisor.lock
```

The lock file is a zero-byte regular file and its bytes never change. Lock contention is `stage1_6e_b_supervisor_lock_held`: the competing process exits with zero source/network work and does not wait. While holding this lock, E-B scans the direct deterministic directories below both `semantic_trigger/` and `event_observations/`. A fresh start is admissible only when both contain zero non-terminal roots. If exactly one valid non-terminal supervisor root exists, startup is legal only with `--resume-supervisor-root <absolute-exact-path>` equal to that root; E-B never chooses a root by latest time, glob, mtime, or scan order. More than one non-terminal supervisor root, any malformed/unvalidated supervisor root, any non-terminal event root not owned by that resumed supervisor, or a fresh start while either family is non-terminal is `global_active_supervisor_state_invalid`; no source/network work is allowed.

The supervisor root is exactly:

```text
data/external_signal_shadow/stage1_6e_b/semantic_trigger/<supervisor_run_id>/
```

`supervisor_run_id` follows `stage1_6e_b_semantic_<UTC-YYYYMMDDThhmmssZ>_<uuid4-hex>`. The directory must be created with `mkdir(exist_ok=False)`. A pre-existing root is `fresh_root_exists`; it is not a resume target unless it is the exact explicitly named interrupted root accepted by Section 13.

The supervisor has one lifetime writer lock in addition to the global lock and uses the Section 6.5 supervisor limits. A capacity failure stops new source consumption and is terminal for the supervisor. Its terminal artifact, when required, is exactly:

```text
schema_version = stage1_6e_b_supervisor_terminal_status_v1
supervisor_run_id
status = failed
terminal_reason
terminal_at_ms
accounted_root_bytes
permissions
```

`terminal_reason` is exactly `storage_write_blocked | local_integrity_failed`. Source structural failures remain `source_degraded` and never manufacture a supervisor terminal. The supervisor has no manifest and grants no evidence authority.

### 7.2 Source Checkpoint Validation

The future deployment authorization supplies exactly one absolute `authorized_source_root_realpath` and one `authorized_source_run_id`. They must name an existing 1.6D live root and are persisted unchanged in the E-B consumer checkpoint. E-B rejects `latest`, globs, mtime selection, scan-and-pick selection, fallback roots, relative source paths, and a later source-root substitution.

For every source read, E-B snapshots and validates exact bytes of `capture_run_contract.json`, `source_profile_probe_attestation.json`, and `observer_checkpoint.json` from that authorized root before loader/defaulting, mutation, diagnostic append, source raw copy, semantic parsing, or network. It requires:

```text
capture_run_contract.run_id == observer_checkpoint.run_id == authorized_source_run_id
capture_run_contract.capture_mode == observer_checkpoint.capture_mode == live_observed
capture_run_contract.source_profile_id == observer_checkpoint.source_profile_id
  == binance_public_web_bapi_en_delisting_catalog_v2
SHA256(exact source_profile_probe_attestation bytes)
  == capture_run_contract.source_profile_attestation_sha256
  == observer_checkpoint.source_profile_attestation_sha256
```

The E-B consumer then accepts only a complete exact-key `observer_checkpoint.json` where all conditions hold:

```text
schema_version == stage1_6b_observer_checkpoint_v3
last_index_poll_status == trusted
last_index_poll_coverage == successful
pending_terminal_failure_reason == null
checkpoint_id == recompute_live_v3_checkpoint_id(exact checkpoint projection)
heartbeat_at_ms is integer > 0
-30000 <= now_ms - heartbeat_at_ms <= 900000
```

Its required key set, with no unknown or missing key, is exactly:

```text
schema_version
run_id
capture_mode
source_profile_id
source_profile_attestation_sha256
checkpoint_id
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

The consumer reads only bytes below the complete `stream_offsets` map and uses the complete `stream_last_hashes` map to verify every declared committed stream boundary. `detail_revisions.jsonl` may be absent only when its committed offset is zero, no physical file exists, and no last-hash exists. Once a nonzero detail-revision boundary exists, the stream and last hash are mandatory. A JSONL line crossing an offset, any other missing stream, a malformed line, an offset/hash mismatch, a revision/observation mismatch, source raw hash mismatch, run-contract mismatch, profile-attestation mismatch, checkpoint exact-key failure, or heartbeat failure is `source_checkpoint_invalid` and admits no new event.

For an existing supervisor checkpoint, the authorized root/run ID and captured contract/profile hashes must be identical. For each previously captured stream map entry, the new map must include that stream with `old_offset <= new_offset`, and exact bytes through `old_offset` must still have the stored `old_last_hash` as the final committed line hash. For `detail_revisions.jsonl`, a prior nonzero offset also requires the SHA-256 of its exact previously committed last line to equal `detail_revisions_last_line_sha256`; a zero offset requires that hash and record sequence to be null. A source truncation, replacement, missing old stream, or prefix rewrite is `source_checkpoint_rollback_or_rewrite` and admits no new event.

`source_degraded` is not a terminal event state. It blocks new semantic/event admission while the supervisor retains its current state. A later valid checkpoint with an advancing `checkpoint_id` and fresh heartbeat restores `source_ready`. Existing event roots are independent and continue.

### 7.3 Consumer Checkpoint And Idempotency

`source_consumer_checkpoint.json` has exactly:

```text
schema_version = stage1_6e_b_source_consumer_checkpoint_v1
supervisor_run_id
authorized_source_root_realpath
authorized_source_run_id
capture_run_contract_sha256
source_profile_probe_attestation_sha256
source_checkpoint_id
source_checkpoint_sha256
source_stream_offsets
source_stream_last_hashes
detail_revisions_committed_offset
detail_revisions_last_line_sha256 | null
last_consumed_detail_revision_record_seq | null
active_notice_event_key | null
active_event_id | null
updated_at_ms
permissions
source_consumer_checkpoint_id
```

`source_consumer_checkpoint_id = SHA256(canonical_json(the object with only source_consumer_checkpoint_id omitted))`. `source_stream_offsets` and `source_stream_last_hashes` are the complete accepted checkpoint maps, not a reduced projection. `detail_revisions_committed_offset` and `detail_revisions_last_line_sha256` refer to their `detail_revisions.jsonl` entries. When that offset is zero, the last hash and `last_consumed_detail_revision_record_seq` are null; when it is nonzero, the last hash is a SHA-256 and the record sequence is a positive integer. The consumer processes new trusted revisions in ascending `record_seq`, then `source_article_id`, then `detail_revision_id` order.

For a fresh supervisor with no consumer checkpoint, E-B validates the current 1.6D committed boundary and atomically writes the consumer checkpoint with that exact full stream-map boundary and its last committed `record_seq` or null when the detail-revision offset is zero. This is `live_bootstrap`: it copies no raw payload, writes no semantic projection/admission, and sends no market request. Revisions at or before that boundary are permanently pre-bootstrap for this supervisor and are never replayed. Only revisions appended after the bootstrap boundary are eligible for the flows below.

For a not-eligible revision, the durable write order is exact:

```text
validate source linkage and source raw bytes
-> atomically copy/read-back source raw into E-B supervisor root
-> atomically persist/read-back semantic projection row
-> atomically persist/read-back source_consumer_checkpoint.json
```

For an eligible revision, E-B first resolves its `notice_event_key`. If no final admission exists, exactly one immutable event-admission row (Section 9.1) is inserted after projection read-back and before the consumer checkpoint advances. If the admission is `admitted`, fresh event-root creation/attestation/checkpoint persistence occurs before the consumer checkpoint records its `active_event_id`. If the admission is capacity-blocked, no event root or market request is permitted. If a final notice admission already exists, E-B validates that existing row, writes no admission/event, and may then advance the consumer checkpoint. This defensive later-revision branch does not alter the active/terminal event.

If the process crashes before the final checkpoint write, restart first validates a newly read current committed source boundary under Section 7.2. It then re-derives the stable projection ID. When exactly one existing projection row has that ID, E-B reuses its exact canonical bytes and `semantic_projected_at_ms`; it must not rebuild it with the current checkpoint identity. The existing row's `source_checkpoint_id` and `source_checkpoint_sha256` remain immutable **first-validating-source-checkpoint provenance**. The current boundary need not equal them, but it must still prove the same authorized root/run/profile, the same revision/raw/path linkage, and the previously accepted consumer-checkpoint prefix. E-B reruns G2 and exact-compares every deterministic semantic field other than `semantic_projection_id`, `source_checkpoint_id`, `source_checkpoint_sha256`, and `semantic_projected_at_ms`; any difference is `semantic_projection_identity_conflict`.

For an eligible reused row, E-B either validates the one existing deterministic final notice admission or creates it only when none exists before it advances the consumer checkpoint. A consumer checkpoint must never advance before its projection and required final admission state are durable. Duplicate projection/admission IDs are rejected unless their canonical bytes are exactly equal.

## 8. Semantic Projection Contract

### 8.1 Source Linkage

The consumer accepts a source revision only if exactly one committed trusted `DetailObservationRecord` in the current 1.6D V3 live topology has the same:

```text
source_article_id
raw_payload_sha256 == detail_raw_sha256
raw_payload_relative_path
request_variant == bapi_article_detail_query_v1
capture_mode == live_observed
```

The referenced source raw file must be a regular file and its SHA-256 must equal `detail_raw_sha256`. Zero or multiple matching trusted observations are `source_structural_failure/orphan_or_ambiguous_live_revision`; they write no semantic projection and do not advance the consumer checkpoint. This deliberately follows the active 1.6D V3 live lifecycle, in which an article becomes `trusted_detail_observed` after one trusted detail observation; it does not import the distinct historical sealed-export multiplicity rule.

E-B copies an accepted raw file to:

```text
source_detail_raw/<detail_raw_sha256>.bin
```

The copy is atomic, read back, and hash checked. A copy is content-addressed and deduplicated; it does not modify the 1.6D file.

### 8.2 Grammar And Eligibility

E-B calls only the approved G2 `parse_and_normalize_bapi_body` grammar with:

```text
grammar_pair = (
  stage1_6a_bapi_body_tree_v2,
  stage1_6a_extractor_v2
)
article_id = source_article_id
```

The E-B live semantic reducer may reuse G2 parsing, schedule-fact extraction, symbol declaration, and USD-M crypto-perpetual classification rules. It must not call the 1.6C historical sealed-export loader or claim `historical_backfill`, `historical_unknown`, or replay authority.

The following are **source structural failures**, not semantic outcomes: `bapi_data_code_mismatch`, `unsupported_g2_grammar`, `orphan_or_ambiguous_live_revision`, `source_raw_path_hash_or_profile_mismatch`, `source_checkpoint_invalid`, and `source_checkpoint_rollback_or_rewrite`. They respectively cover present string `data.code` mismatch; unsupported grammar/version; revision/observation mismatch; raw/path/hash/profile contradiction; and every Section 7.2 authority failure. A structural failure writes no semantic projection, does not advance the consumer checkpoint, changes the supervisor to `source_degraded`, and permits zero market request.

The following are **semantic not-eligible blockers** and each produces one durable `not_eligible` projection followed by normal consumer-checkpoint advancement:

```text
malformed_bapi_envelope
body_parse_unresolved
declaration_incomplete
semantic_revision_conflict
out_of_scope_product
zero_eligible_symbols
symbol_count_exceeds_three
settlement_time_missing_or_unparseable
settlement_time_not_future
post_admission_semantic_conflict
```

An `eligible` projection requires all of:

1. G2 parsing succeeds without a source structural failure.
2. The selected trusted revision has no G2 semantic conflict against any other committed trusted revision for the same source article.
3. The batch is fully resolved by the G2 declaration grammar.
4. At least one, and at most three, canonical symbols classify as `USD_M`, `PERPETUAL`, and `crypto_asset` under the frozen 1.6C classifier.
5. `settlement_time.fact_parse_status == present`, `settlement_time.timestamp_ms` is an integer, and `settlement_time.timestamp_ms > semantic_projected_at_ms`.

The exact selected `settlement_time.timestamp_ms` is `effective_delist_time_ms`. `last_trading_time`, `order_restriction`, and `delisting_complete_time` are recorded when the G2 reducer can parse them, but never substituted for `effective_delist_time_ms` in this version.

Any semantic failed condition writes one `not_eligible` projection with exactly one blocker from the closed vocabulary above. More than three otherwise eligible symbols is `not_eligible` with `blocker=symbol_count_exceeds_three`. Both outcomes admit zero market-data request.

### 8.3 Projection Row

`delisting_semantic_projections.jsonl` contains canonical UTF-8 JSON rows. Each row has exactly:

```text
schema_version = stage1_6e_b_delisting_semantic_projection_v1
semantic_projection_id
supervisor_run_id
authorized_source_root_realpath
source_profile_id
source_checkpoint_id
source_checkpoint_sha256
source_article_id
source_request_observation_id
source_detail_revision_id
source_detail_raw_sha256
source_detail_raw_relative_path
copied_source_raw_relative_path
g2_body_normalization_version
g2_semantic_extractor_version
normalized_body_sha256 | null
semantic_projected_at_ms
source_first_detected_at_ms
source_detail_trusted_at_ms
eligible_symbols_ordered
eligible_symbols_normalized
eligible_symbol_set_sha256 | null
effective_delist_time_ms | null
eligibility_status = eligible | not_eligible
blocker | null
permissions
```

`semantic_projection_id = SHA256(canonical_json({supervisor_run_id, authorized_source_root_realpath, source_profile_id, source_article_id, source_detail_revision_id, source_detail_raw_sha256, g2_body_normalization_version, g2_semantic_extractor_version}))`. It excludes `semantic_projected_at_ms`, `source_checkpoint_id`, `source_checkpoint_sha256`, and every other derived semantic field. For a new projection, `source_checkpoint_id/source_checkpoint_sha256` are copied once from the currently accepted checkpoint as first-validating-source-checkpoint provenance, and `semantic_projected_at_ms` is captured exactly once immediately before the durable append. Once the row is durable, all three are immutable and restart must reuse that exact row/time rather than reconstructing it with a later checkpoint. A same-ID row with different canonical bytes is `semantic_projection_identity_conflict`: no consumer-checkpoint advance, event admission, or market request is permitted.

`eligible_symbols_ordered` is an array of unique uppercase symbols in G2 declaration order. `eligible_symbols_normalized` is its lexicographic sort. When at least one symbol is present, `eligible_symbol_set_sha256 = SHA256(canonical_json(eligible_symbols_normalized))`; otherwise all three symbol identity fields are `[]`, `[]`, and `null` respectively. `eligible` requires `blocker=null`, 1-3 symbols, and non-null `effective_delist_time_ms`; `not_eligible` requires one exact blocker from Section 8.2 and `effective_delist_time_ms=null`. Unknown/missing fields, invalid hashes, noncanonical ordering, bool-as-int, or any other inconsistent status/blocker combination are rejected.

`source_request_observation_id` is the exact `request_observation_id` from the one linked committed trusted 1.6D detail-observation row. `source_first_detected_at_ms` is taken only from the accepted source checkpoint's matching `candidate_states[source_article_id].first_discovered_at_ms`; a missing or non-integer value rejects the source revision.

## 9. Event Contract And Derived Profiles

### 9.1 Event Admission

Only an `eligible` projection can create an event. `notice_event_key = SHA256(canonical_json({authorized_source_root_realpath, source_profile_id, source_article_id, event_contract_version=stage1_6e_b_event_contract_v1}))`. `event_admissions.jsonl` contains exactly one immutable canonical row for the first eligible projection of each `notice_event_key`:

```text
schema_version = stage1_6e_b_event_admission_v1
admission_id
notice_event_key
semantic_projection_id
event_id
decision = admitted | event_observation_capacity_blocked
blocker = null | active_event_exists
active_event_id_at_decision | null
decided_at_ms
permissions
```

`event_id = SHA256(canonical_json({semantic_projection_id, event_contract_version=stage1_6e_b_event_contract_v1}))` and `admission_id = SHA256(canonical_json(all fields above except admission_id and permissions))`. Before an admission row is written, E-B checks the one globally discovered non-terminal event root and requires it to agree with `source_consumer_checkpoint.active_event_id` when that field is non-null. If a non-terminal event exists, it writes `decision=event_observation_capacity_blocked`, `blocker=active_event_exists`, records that active ID, persists the consumer checkpoint, and performs zero event-root or market-data work. This is final for the notice: E-B has no waiting queue or later re-admission path.

After a final admission exists for `notice_event_key`, later revisions may still create auditable semantic projections but create no second admission or event. If their resolved semantic facts conflict with the admitted projection, they are `not_eligible` with `blocker=post_admission_semantic_conflict`; they cannot modify the existing event or admission.

For an eligible projection with no active event, E-B writes and reads back `decision=admitted` before root creation:

```text
event root = data/external_signal_shadow/stage1_6e_b/event_observations/<event_id>/
```

The event root is fresh with `mkdir(exist_ok=False)`. A pre-existing non-terminal root may only be resumed under Section 13 after exact contract and checkpoint validation. A terminal root is never restarted.

The event-admission write order is exact:

```text
semantic projection durable/read-back
-> event admission(admitted) durable/read-back
-> fresh event root + writer lock
-> environment attestation, event contract, derived ProfileCores, empty event checkpoint: durable/read-back
-> source_consumer_checkpoint.active_notice_event_key/event_id: durable/read-back
-> first due slot admission
```

If a crash occurs after the admission row and before the supervisor checkpoint records `active_event_id`, restart reads the same admitted row and either creates the deterministic missing event root or validates the deterministic pre-existing non-terminal event root, then records that same `notice_event_key` and `event_id`; it must not create another root. A stopped writer means that the supervisor can acquire the event writer `flock` non-blocking after terminal validation. After an event reaches a validated complete terminal with its manifest, or a validated failed terminal with no manifest and a stopped writer, the supervisor clears both `active_notice_event_key` and `active_event_id` in a durable/read-back consumer checkpoint. A partial/malformed terminal or terminal-write failure never clears either field and remains a global blocker.

`event_contract.json` is atomically persisted/read back before the first market request. It contains exactly:

```text
schema_version = stage1_6e_b_event_contract_v1
event_id
supervisor_run_id
semantic_projection_id
semantic_projection_row_sha256
notice_event_key
admission_id
admission_row_sha256
source_article_id
source_detail_revision_id
source_detail_raw_sha256
source_checkpoint_id
source_checkpoint_sha256
authorized_source_root_realpath
effective_delist_time_ms
event_window_started_at_ms
event_window_ends_at_ms
window_duration_ms = 43200000
canonical_symbols_ordered
canonical_symbols_normalized
symbol_set_sha256
expected_slot_count
e_a_manifest_id
e_a_manifest_sha256
e_a_profile_attestation_sha256_by_id
execution_environment_attestation_sha256
environment_authority_receipt_sha256
storage_contract
permissions
```

`source_checkpoint_id/source_checkpoint_sha256` exactly equal the admitted semantic projection's immutable first-validating-source-checkpoint provenance; they are never replaced by a later checkpoint at event-root creation or restart. `event_window_started_at_ms` exactly equals the persisted admitted semantic projection's `semantic_projected_at_ms`; it is never recomputed from a later read-back or restart time. `event_window_ends_at_ms = event_window_started_at_ms + EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_WINDOW_MS`. `expected_slot_count = len(canonical_symbols_ordered) * 1586`. Therefore a crash after projection or admission cannot shift the 12-hour window.

`e_a_profile_attestation_sha256_by_id` is exactly the lexically keyed four-entry object below, with each value the verified lowercase SHA-256 of the corresponding E-A profile-attestation file:

```text
binance_usdm_rest_depth_v1
binance_usdm_rest_funding_rate_v1
binance_usdm_rest_open_interest_hist_5m_v1
binance_usdm_rest_premium_index_v1
```

`storage_contract` is exactly:

```text
event_root_max_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES
ordinary_reserve_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ORDINARY_RESERVE_BYTES
emergency_reserve_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_EMERGENCY_RESERVE_BYTES
terminal_write_set_max_peak_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
manifest_max_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_MANIFEST_MAX_BYTES
depth_max_raw_response_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_MAX_RAW_RESPONSE_BYTES
single_row_max_raw_response_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_SINGLE_ROW_MAX_RAW_RESPONSE_BYTES
```

No nested key is optional, literal-defaulted, or extensible. The event contract rejects unknown/missing keys, non-integer byte values, bool-as-int, or any value unequal to Section 6.5.

### 9.2 Exact Derived ProfileCore

For every `(canonical_symbol, base_profile_id)` pair, E-B writes one canonical file at:

```text
profile_attestations/<canonical_symbol>.<base_profile_id>.json
```

Its exact object is:

```text
schema_version = stage1_6e_b_event_profile_core_v1
event_id
source_article_id
source_detail_revision_id
canonical_symbol
base_e_a_manifest_id
base_e_a_profile_id
base_e_a_profile_attestation_sha256
base_e_a_profile_core_sha256
event_max_raw_response_bytes
http_profile_core
profile_attestation_sha256
```

`profile_attestation_sha256 = SHA256(canonical_json(the object with profile_attestation_sha256 omitted))`. `http_profile_core` is copied from the E-A verified profile and transformed only as follows:

| Base profile | Required exact transform |
|---|---|
| `binance_usdm_rest_depth_v1` | `limit=100&symbol=BTCUSDT` becomes `limit=100&symbol=<canonical_symbol>`; `max_raw_response_bytes=EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_MAX_RAW_RESPONSE_BYTES`. |
| `binance_usdm_rest_premium_index_v1` | `symbol=BTCUSDT` becomes `symbol=<canonical_symbol>`; required schema token `literal_BTCUSDT` becomes `literal_<canonical_symbol>`; `max_raw_response_bytes=EXTERNAL_SIGNAL_STAGE1_6E_B_SINGLE_ROW_MAX_RAW_RESPONSE_BYTES`. |
| `binance_usdm_rest_funding_rate_v1` | `limit=1&symbol=BTCUSDT` becomes `limit=1&symbol=<canonical_symbol>`; required schema token becomes `literal_<canonical_symbol>`; `max_raw_response_bytes=EXTERNAL_SIGNAL_STAGE1_6E_B_SINGLE_ROW_MAX_RAW_RESPONSE_BYTES`. |
| `binance_usdm_rest_open_interest_hist_5m_v1` | `limit=1&period=5m&symbol=BTCUSDT` becomes `limit=1&period=5m&symbol=<canonical_symbol>`; required schema token becomes `literal_<canonical_symbol>`; `max_raw_response_bytes=EXTERNAL_SIGNAL_STAGE1_6E_B_SINGLE_ROW_MAX_RAW_RESPONSE_BYTES`. |

No other E-A ProfileCore key, value, token, URL component, header policy, parser version, response schema rule, time semantic, or rate-limit provenance may change. A response symbol mismatch is schema-invalid. E-B adds a lower raw-body bound; it does not weaken E-A's two-MiB safety bound.

## 10. Slot Schedule And Network Contract

All requests are sequential, public, unauthenticated `GET`, no body, no cookies, no authorization, `Accept-Encoding: identity`, and no redirects. Each attempt uses `EXTERNAL_SIGNAL_STAGE1_6E_B_HTTP_TIMEOUT_SEC`. E-B uses exactly the E-A request host, method, paths, header policy, response validators, and no-transparent-decompression policy.

For each symbol, the deterministic slot table is:

| Slot family | Slot indices | Due time | Count |
|---|---:|---|---:|
| `depth_60s` | `0..719` | `start + index * EXTERNAL_SIGNAL_STAGE1_6E_B_DEPTH_INTERVAL_MS` | 720 |
| `premium_60s` | `0..719` | `start + index * EXTERNAL_SIGNAL_STAGE1_6E_B_PREMIUM_INTERVAL_MS` | 720 |
| `oi_5m` | `0..143` | `start + index * EXTERNAL_SIGNAL_STAGE1_6E_B_OPEN_INTEREST_INTERVAL_MS` | 144 |
| `funding_start` | `0` | `start` | 1 |
| `funding_end` | `0` | `end` | 1 |

Total is `1586` slots per symbol and at most `4758` slots per event. At equal due time, dispatch order is exactly base-profile order `depth`, `premium`, `funding`, `open_interest`, then lexicographic `canonical_symbol`. Each slot has one `slot_id = SHA256(canonical_json({event_id, base_e_a_profile_id, canonical_symbol, slot_family, slot_index, due_at_ms}))`.

A network admission is allowed only if `due_at_ms <= dispatch_started_at_ms < due_at_ms + EXTERNAL_SIGNAL_STAGE1_6E_B_SLOT_DEADLINE_MS`. If the deadline is reached before dispatch, E-B persists `outcome_kind=slot_missed_deadline`, performs zero HTTP request, and never catches up. A single admitted request has no retry. Complete coverage is opportunistic under the sequential 10-second timeout envelope; no result may claim per-symbol symmetry.

## 11. Event Observations, Storage, And Terminal Rules

### 11.1 Observation Row

`observations.jsonl` contains one canonical row for every planned slot. Each row includes exactly:

```text
schema_version = stage1_6e_b_market_observation_v1
event_id
slot_id
slot_family
slot_index
due_at_ms
dispatch_started_at_ms | null
completed_at_ms
canonical_symbol
base_e_a_profile_id
profile_attestation_sha256
request_identity
request_sequence | null
outcome_kind
http_status | null
response_headers_subset
raw_payload_persisted
raw_sha256 | null
raw_relative_path | null
raw_byte_count | null
schema_validation_status = verified | not_applicable | failed
time_validation_status = verified | not_applicable | failed
failure_reason | null
permissions
```

`request_identity = SHA256(canonical_json({method, scheme, host, path, canonical_query}))` from the exact event ProfileCore. `slot_missed_deadline` has `dispatch_started_at_ms=null`, `request_sequence=null`, and no raw fields. Every admitted success persists exact raw bytes at `raw/<sha256>.body`, reads them back, validates hash/byte count, then appends the observation. Raw bodies are content-addressed and deduplicated only by exact SHA-256.

Every JSONL line is exact `canonical_json(row) + "\\n"`; `observation_row_sha256 = SHA256(canonical_json(row))`. `request_sequence` is a positive, strictly increasing event-local integer and is null only for `slot_missed_deadline`. `response_headers_subset` is a lexicographically keyed object containing only lowercase `content-type`, `content-encoding`, and `date` keys that were present in the received response; values are strings, its canonical bytes are at most 8192, and no default/coercion is allowed.

The closed observation outcome grammar is:

| Outcome kind | dispatch / sequence | HTTP / headers / raw | validators / failure reason |
|---|---|---|---|
| `slot_missed_deadline` | both null | HTTP null; `{}`; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `slot_missed_deadline` |
| `response_verified` | integer / positive integer | ProfileCore-accepted HTTP status; received normalized subset; `raw_payload_persisted=true` and all raw fields valid | both `verified`; null |
| `request_timeout` | integer / positive integer | HTTP null; `{}`; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `request_timeout` |
| `transport_error` | integer / positive integer | HTTP null; `{}`; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `transport_error` |
| `redirect_rejected` | integer / positive integer | HTTP 300-399; received normalized subset; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `redirect_rejected` |
| `http_response_invalid` | integer / positive integer | HTTP integer not accepted by the ProfileCore; received normalized subset; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `http_response_invalid` |
| `content_encoding_invalid` | integer / positive integer | ProfileCore-accepted HTTP status; received normalized subset; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `content_encoding_invalid` |
| `raw_size_exceeded` | integer / positive integer | ProfileCore-accepted HTTP status; received normalized subset; `raw_payload_persisted=false` and all raw fields null | both `not_applicable`; `raw_size_exceeded` |
| `schema_validation_failed` | integer / positive integer | ProfileCore-accepted HTTP status; received normalized subset; `raw_payload_persisted=true` and all raw fields valid | schema `failed`, time `not_applicable`; `schema_validation_failed` |
| `time_validation_failed` | integer / positive integer | ProfileCore-accepted HTTP status; received normalized subset; `raw_payload_persisted=true` and all raw fields valid | schema `verified`, time `failed`; `time_validation_failed` |
| `request_outcome_unknown_after_restart` | dispatch null; positive sequence from durable intent | HTTP null; `{}`; either `raw_payload_persisted=false` with all raw fields null, or true with all raw fields valid | both `not_applicable`; `request_outcome_unknown_after_restart` |

For every row, `raw_payload_persisted=false` requires all raw fields null; `true` requires a regular in-root `raw/<sha256>.body`, matching SHA-256 and byte count. All named timestamps are integers when non-null; booleans are not integers; unknown keys, unknown enums, missing keys, defaulting, and coercion reject the row.

### 11.2 Storage Bound

Per event root, Section 6.5 is the sole numeric authority:

```text
event_root_max_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ROOT_MAX_BYTES
ordinary_reserve_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_ORDINARY_RESERVE_BYTES
emergency_reserve_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_EMERGENCY_RESERVE_BYTES
terminal_write_set_max_peak_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_TERMINAL_WRITE_SET_MAX_PEAK_BYTES
manifest_max_bytes = EXTERNAL_SIGNAL_STAGE1_6E_B_EVENT_MANIFEST_MAX_BYTES
```

The worst allowed raw-body total for three symbols is below `622 MiB`:

```text
3 * (720 * 256 KiB + 720 * 32 KiB + 144 * 32 KiB + 2 * 32 KiB)
```

The shared storage guard must reserve the existing 1.5D, 1.5F, 1.6D, E-A, E-B supervisor, and one E-B event terminal write sets before normal E-B admission. It must never delete, weaken, or borrow another root's reserve.

### 11.3 Reducer

For every scheduled slot, evaluate in order:

1. missing/invalid event checkpoint or terminal root -> stop; no request;
2. missed slot deadline -> durable `slot_missed_deadline`; continue later slots;
3. storage admission rejection before request -> construct `terminal_failed/storage_write_blocked`; no later requests;
4. request timeout, transport/redirect/HTTP/content-encoding/schema/time/raw-size failure -> persist the exact failed observation; continue later slots;
5. valid response -> persist raw then verified observation; continue later slots.

If observation persistence/read-back fails after a request, it supersedes the response result: `terminal_failed/local_integrity_failed`; no later requests. If terminal persistence/read-back fails, no valid terminal and no manifest exists.

At the end of the window, only when every expected slot has one durable row:

```text
all rows successful -> terminal.status=complete, coverage_status=complete
any failed/missed row -> terminal.status=complete, coverage_status=incomplete
```

`terminal_status.json` has exactly:

```text
schema_version = stage1_6e_b_terminal_status_v1
event_id
status = complete | failed
coverage_status = complete | incomplete | null
terminal_reason | null
event_window_started_at_ms
event_window_ends_at_ms
terminal_at_ms
expected_slot_count
durable_slot_count
successful_slot_count
failed_slot_count
missed_slot_count
per_symbol_slot_counts
accounted_root_bytes
permissions
```

`per_symbol_slot_counts` is a lexicographically ordered list of `{canonical_symbol, expected_slot_count, successful_slot_count, failed_slot_count, missed_slot_count}` whose sums equal the event totals. For `status=complete`, `terminal_reason=null` and `coverage_status` is non-null. For `failed`, `coverage_status=null`, `terminal_reason` is exactly `storage_write_blocked | local_integrity_failed`, and no manifest is allowed. `coverage_status=incomplete` is sealed evidence of an incomplete collection; it is never coverage authority.

### 11.4 Manifest

`manifest.json` is written last after a valid `status=complete` terminal. It has exactly:

```text
schema_version = stage1_6e_b_event_manifest_v1
event_id
coverage_status = complete | incomplete
terminal_status_sha256
event_contract_sha256
authoritative_artifacts
permissions
manifest_id
```

`authoritative_artifacts` is the lexicographically sorted array of exactly every durable regular event-root file except `manifest.json`, each exact `{relative_path, sha256, byte_count}` object. `terminal_status_sha256` and `event_contract_sha256` must equal the matching entries. `manifest_id = SHA256(canonical_json(the object with only manifest_id omitted))`. Unknown/missing keys, duplicate/out-of-order artifacts, non-SHA hash values, non-integer byte counts, or a coverage value different from the valid terminal reject the manifest.

Unknown path, symlink, temp/orphan file, missing expected artifact, duplicate/out-of-order path, hash mismatch, byte-count mismatch, or terminal/coverage mismatch invalidates the bundle. A consumer must reject an invalid manifest and must reject `coverage_status=incomplete` for any complete-coverage or mechanism claim.

### 11.5 Root File Grammars

Outside roots, the only E-B shared control artifact is `.stage1_6e_b_supervisor.lock` at the Section 7.1 path. It is never part of an event manifest.

The live supervisor is not a sealed evidence bundle. Its only allowed regular paths are:

```text
execution_environment_attestation.json
environment_authority_receipt.json
source_consumer_checkpoint.json
delisting_semantic_projections.jsonl
event_admissions.jsonl
source_detail_raw/<sha256>.bin
terminal_status.json                 # only if supervisor terminal
```

Its only allowed non-manifest control artifact is `.stage1_6e_b_supervisor_writer.lock`, a zero-byte regular file whose SHA-256 stays unchanged from acquisition to release. An event root's only allowed paths are:

```text
.stage1_6e_b_event_writer.lock
execution_environment_attestation.json
environment_authority_receipt.json
event_contract.json
event_checkpoint.json
profile_attestations/<symbol>.<base-profile-id>.json
observations.jsonl
raw/<sha256>.body
terminal_status.json
manifest.json                        # last, only for status=complete
```

The event lock is likewise a zero-byte immutable control file. Before terminal persistence, `terminal_status.json` and `manifest.json` are absent. Before manifest persistence, only `manifest.json` is absent. Any path outside the applicable grammar, symlink, temporary file, or modified lock makes resume/sealing fail closed; no cleanup or deletion is allowed.

## 12. State Machines

```text
supervisor:
new -> source_ready <-> source_degraded -> terminal_failed

semantic projection:
validated -> eligible | not_eligible

event admission:
eligible -> admitted | event_observation_capacity_blocked

event:
new -> semantic_projected -> observing
    -> terminal_complete_coverage
    |  terminal_incomplete_coverage
    |  terminal_failed
```

`terminal_complete_coverage` maps to `terminal.status=complete, coverage_status=complete`. `terminal_incomplete_coverage` maps to `terminal.status=complete, coverage_status=incomplete`. A completed or failed event root cannot return to `observing`.

## 13. Restart, Crash, And Idempotency

The supervisor and a non-terminal event root support only controlled resume. Before any source or market request, resume must validate: root family/path, global and writer locks, checkpoint schema/hash, exact event contract (including `supervisor_run_id` equal to the resumed supervisor), event ProfileCore hashes, observed raw hashes, JSONL sequence uniqueness, no terminal, and no manifest.

Event checkpoint fields are exactly:

```text
schema_version = stage1_6e_b_event_checkpoint_v1
event_id
event_contract_sha256
profile_attestation_sha256_by_symbol_and_profile
completed_slot_ids_ordered
last_observation_sha256
inflight_slot_intent | null
accounted_root_bytes
updated_at_ms
permissions
```

`profile_attestation_sha256_by_symbol_and_profile` is exactly a lexically keyed nested object: its outer keys equal `canonical_symbols_normalized`; each outer value has exactly the four base profile IDs listed in Section 9.2; each inner value is the lowercase SHA-256 of the matching event-root `profile_attestations/<symbol>.<base-profile-id>.json` file. Unknown/missing keys, bool-as-int, noncanonical key ordering, or a hash mismatch reject resume.

`completed_slot_ids_ordered` is the lexicographically sorted exact `slot_id` set reconstructed from validated `observations.jsonl`, and `last_observation_sha256` is the SHA-256 of the final exact canonical JSON observation row (null only when no rows exist). `inflight_slot_intent`, when present, has exactly:

```text
slot_id
request_identity
request_sequence
base_e_a_profile_id
canonical_symbol
due_at_ms
reserved_at_ms
stage = prepared | raw_persisted
raw_sha256 | null
raw_relative_path | null
raw_byte_count | null
```

The reducer writes and reads back `stage=prepared` before one HTTP attempt. After a raw response is durably written/read-back it updates the same intent to `stage=raw_persisted`; only then it appends the observation and checkpoint-clears the intent while adding the slot ID. `prepared` requires all raw fields null. `raw_persisted` requires all raw fields valid under Section 11.1.

Resume uses this closed matrix before a request:

| Validated state | Required action | HTTP |
|---|---|---|
| no intent and no observation | normal deadline evaluation | allowed once |
| intent and matching durable observation | checkpoint-only clear/reconcile | zero |
| `prepared` intent and no observation | append `request_outcome_unknown_after_restart`, then checkpoint-clear | zero |
| `raw_persisted` intent and no observation with valid raw | append `request_outcome_unknown_after_restart`, then checkpoint-clear | zero |
| `raw_persisted` intent and no observation with missing/invalid raw | construct `terminal_failed/local_integrity_failed`; if that terminal cannot be made valid, preserve the root as blocker | zero |
| durable observation one slot ahead of checkpoint | reconstruct/checkpoint-only roll-forward | zero |
| checkpoint ahead of observations, raw without matching `raw_persisted` intent, intent/observation slot mismatch, or more than one observation ahead | reject root; preserve unchanged | zero |

The sequential reducer permits at most one observation ahead of the checkpoint. Resume creates no new request for a completed or uncertain slot. A due slot not completed at resume time is evaluated under the normal deadline only when no intent was ever durable; an already expired one becomes `slot_missed_deadline`, not a late HTTP request.

If a root cannot satisfy resume validation, it is preserved unchanged and admission stops. The implementation must not delete it, overwrite it, create a second root for the same `event_id`, or invent a terminal/manifest.

## 14. Compatibility And Migration

1. Stage 1.6D V3 remains the only accepted live source checkpoint. V2, historical roots, sealed exports, source raw files outside the active committed root, and loader-defaulted state are rejected.
2. Stage 1.6C historical adapter artifacts remain immutable historical evidence. E-B imports only the named G2 grammar/classification contract through a live-specific adapter boundary.
3. E-A source profile files stay immutable. E-B writes new event-specific ProfileCore files and never changes an E-A file.
4. Existing 1.5D/F and 1.6D writers continue independently. E-B never stops/restarts them as an operational workaround.

## 15. Producer / Writer / Loader / Consumer / Reviewer Matrix

| Artifact / authority | Producer/writer | Loader | Consumer | Reviewer | Mutability |
|---|---|---|---|---|---|
| E-A complete bundle | E-A | E-A closed-tree verifier | E-B environment gate | E-B verifier + future audit | read-only |
| 1.6D checkpoint/streams/raw | active 1.6D | E-B strict committed-boundary validator | E-B semantic reducer | source validator + future audit | read-only |
| G2 parser/classifier | 1.6C authority | E-B live adapter | E-B semantic reducer | fixture/version verifier | imported immutable contract |
| semantic projection | E-B supervisor | E-B strict JSONL validator | admission reducer | E-B/future audit | append-only |
| event admission | E-B supervisor | E-B strict JSONL validator | event-root creator | E-B/future audit | append-only, final |
| event contract/profile/slots/raw | E-B event observer | E-B resume verifier | E-B event observer | manifest verifier | event-root only |
| event terminal/manifest | E-B event observer | closed-tree verifier | downstream evidence consumer | future audit | terminal/write-last |

## 16. Verification Strategy

The future Plan must require at least:

1. E-A exact same-schema attestation, equality-set comparison, distinct E-B deployment commit, authority-receipt hash binding, and E-A manifest/environment mismatch;
2. authorized-source-root/run-ID rejection for relative/latest/glob/mtime/fallback paths; run-contract/profile-attestation/checkpoint cross-binding; every V3 required/unknown key; two-sided heartbeat bounds; complete stream map/old-boundary proof; zero-offset null sequence; source rollback/rewrite; and recovery;
3. fresh live bootstrap consumes zero historical revisions/raw/network; a current 1.6D single trusted-detail linkage is accepted, while zero/multiple live links, raw/path/hash mismatch, BAPI data-code mismatch, and unsupported grammar fail structurally without projection/checkpoint advancement;
4. G2 H2 accepted fixture, malformed envelope, body parse unresolved, unresolved batch, revision conflict, out-of-scope product, zero symbol, four-symbol block, and missing/unparseable/past settlement produce their exact semantic outcomes;
5. C1 contains revision R -> projection P durable under C1 -> crash before consumer checkpoint -> source extends normally to C2 still containing R/raw -> exact P/time/provenance reuse with no duplicate projection/admission/event and unchanged event window; C2 prefix rewrite, truncation, or R/raw-linkage loss -> structural reject; same-ID/different deterministic semantic row rejection; one notice-level final admission across later revisions; post-admission semantic conflict; capacity block without event root; no queue/re-admission; event-contract self-contained projection/admission/checkpoint receipt hashes; and canonical identity test vectors;
6. exact event ProfileCore byte/hash derivation for every profile/symbol, forbidden template mutation, response-symbol mismatch, all permissions false, and `RISK_LIVE_TRADING_ENABLED=False`;
7. 60-second/5-minute/start/end slot enumeration, same-due deterministic ordering, 60-second expiry without HTTP, at-most-one/no-retry behavior including prepared-intent uncertainty, and visible per-symbol missed-slot asymmetry;
8. every observation outcome grammar combination including unknown-after-restart with null dispatch time, header subset bounds, bool-as-int rejection, raw/hash/path relations, per-symbol terminal totals, complete/incomplete sealing, failed-terminal no-manifest release, terminal-write failure blocker, exact manifest schema/artifact list, nested profile/storage-contract grammar, and manifest closed-tree corruption;
9. global-lock contention; fresh-supervisor rejection when a non-terminal supervisor/event root exists; explicit exact-root supervisor resume; supervisor crash before later source consumption; and no duplicate supervisor/event root;
10. crash before intent, after prepared intent/before HTTP, after HTTP/before raw, after raw/before observation, after observation/before checkpoint, checkpoint-only reconciliation, no duplicate HTTP after uncertain work, and invalid intent/raw/checkpoint states; and
11. aggregate storage admission with 1.5D/F, 1.6D, E-A, supervisor, and one event reserve equation.

Real fixture provenance must distinguish frozen 1.6C H2 BAPI bodies, E-A capability evidence, and synthetic fault fixtures. No test may use an external network call.

## 17. Rollout And Rollback

Implementation/deployment is prohibited until this Design receives independent review, explicit user approval, an approved Implementation Plan, a completion audit, and a separate VPS deployment authorization.

The future runtime start contract must use a fresh supervisor root, a fresh session, the exact approved deployment commit, E-A root verification, same-environment attestation, read-only 1.6D health check, and shared-storage preflight. Rollback is no-start for preflight failure. A running root is preserved on failure; it is never deleted, mutated, or replaced to manufacture a healthy state.

## 18. Open Questions

None that alter this implementation path. The terminal-window second phase is explicitly deferred by Section 4.3 and requires a new Design delta.
