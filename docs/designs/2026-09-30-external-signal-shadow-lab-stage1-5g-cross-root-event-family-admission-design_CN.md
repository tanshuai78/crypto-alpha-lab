# Stage 1.5G Cross-Root Event-Family Admission Design

- 日期：2026-09-30
- 状态：Design candidate；未授权 implementation、network、replay、paper trading、live trading、execution、commit、push、deployment 或 SSH。
- 目标：当两个 Section 2 frozen candidate root 在 implementation preflight 中确实存在且重新准入通过时，对其做一次性、只读的 cross-root admission，机械证明其满足 Gate 3 的**运营证据数量**门槛。该产物不证明 Gate 3 的持续运行前置条件，且不是 Alpha、策略、回测、执行可行性或事件族市场结论。

## 1. Confirmed Facts

1. 当前配置的门槛为 `EXTERNAL_SIGNAL_STAGE1_5G_MIN_EVENT_FAMILY_SAMPLE_REQUIRED = 3` 与 `EXTERNAL_SIGNAL_STAGE1_5G_MIN_SOURCE_ARTICLES_REQUIRED = 2`。
2. 已验证的 Moonshot stored review summary bytes 声明 clean pass、一个 `MOONSHOTUSDT` formal child、一个 `source_article_id` 与一个 parent `event_id`；该 summary bytes 不是 source-root 仍存在或有效的证明。
3. 已验证的 batch7 stored review summary bytes 声明 clean pass、7 个 formal children、共享一个 `source_article_id` 与一个 parent `event_id`；该 summary bytes 不是 source-root 仍存在或有效的证明。
4. 若且仅若 Section 2.2 的 preflight 重现这些 frozen identities，本次 receipt 将有 8 个 formal symbols、2 个 source articles、2 个 parent events。batch7 的 7 个 child 不得作为 7 个独立机会。
5. `load_stage1_5g_inputs()` 与 `build_stage1_5g_review_summary()` 是本次重新准入的 production owner；其 exact reviewed bytes 由 Section 2.1 冻结。
6. Graphify 在当前环境不可用（`.venv` 没有 `graphify` module）；本 Design 的拓扑结论以实际 source、CLI 与测试检索为准，不更新 `graphify-out/`。

## 2. Frozen Authority Packet

### 2.1 Reviewed Upstream Contract Packet

Implementation Task 0 must require each path below to be a regular file and require its exact SHA-256 before it imports or invokes the production admission path. This is a whole-file contract binding; a drift in an otherwise unrelated line is intentionally fail-closed.

| path | SHA-256 | bound responsibility |
| --- | --- | --- |
| `src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py` | `596d2c0771ffdde722055c7d7151ea4d9bcaa365d550bc0ab58c453158e6277d` | `load_stage1_5g_inputs`, `build_stage1_5g_review_summary`, source manifest and runtime-attestation validation |
| `configs/base.py` | `414b3e66268ce6b40f6879005464316d525db88d66dded47be5c57b4628a0cb4` | the `3` formal-symbol and `2` source-article thresholds |
| `src/research/external_signal_shadow/safety.py` | `1a788a16a5638ba29bb074a577263450f9d77929b0fef3d2ee3f9f6b363fcf8d` | canonical serialization used by the frozen upstream admission contract |

Any missing path or changed byte is `STOP=stage1_5g_cross_root_upstream_contract_drift`. The implementation must not reinterpret current source, update a hash, or use a local fallback.

The exact current upstream false-key set required in each recomputed Stage 1.5G summary is:

```text
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
alpha_interpretation_allowed
execution_feasibility_claim_allowed
```

Every key must be present with boolean value `false`; missing is not false.

### 2.2 Frozen Conditional Input Packet

本 Design 只接受下列两个 ordered input records；不得发现、选择或追加任何第三 root，也不得以 `SPCXUSD1`、会话记忆或缺少本地 bytes 的历史记录替代其中任一条。它们是 implementation preflight 的 expected paths/bytes，不是本 Design 对当前 root presence 或 content validity 的 Confirmed Fact。

| input_key | stored Stage 1.5G review summary | SHA-256 | Stage 1.5F source root | source `SHA256SUMS` SHA-256 |
| --- | --- | --- | --- | --- |
| `moonshot` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` | `849622a43cb52ec7ab03232d873be326dc779e42e7c4c2bf0e8cfe9e9a548082` | `data/external_signal_shadow/local_evidence/20260923T025100Z_stage1_5f_moonshot` | `611074cf5daa25691d2e14f3998b82b50d19295f1cc0ac38e792cc18256a84db` |
| `batch7` | `data/external_signal_shadow/stage1_5g/reviews/20260930T021507Z_batch7_review/stage1_5g_live_depth_evidence_review_summary.json` | `28b4b7eeac9afc7750a3d998f235dbf063473127ccf86e1f9b6531c8d449ba37` | `data/external_signal_shadow/local_evidence/20260930T021507Z_stage1_5f_batch7` | `0e57f517bb8bce741c40e0bda60d6f11b7b3201604c514b342bd580683569280` |

The admitted frozen parent ledger is:

| parent_article_id | parent_event_id | formal child symbols |
| --- | --- | --- |
| `7379b99aa0f349a49c3b3feca1b4bbd6` | `e4c80f44f8cb5386977ab87d61636ce0ca1e55918a85fd3802ebadd0dd7b39d5` | `MOONSHOTUSDT` |
| `0c6ea14ba89b451db6ec9ec364045d22` | `d4d4f70a87eeae1963e749a374c0df1b42cac1747e9719f4871e03e6c92dc9e0` | `ACNUSDT`, `BWETUSDT`, `CRMLUSDT`, `MPUSDT`, `NKEUSDT`, `SECZUSDT`, `UNHUSDT` |

The stored summaries are historical identity receipts, not the producer authority. The implementation must first verify their exact bytes, then independently re-admit each Stage 1.5F root through the production loader and production reducer.

## 3. Core Issue and Decision

The two stored summaries individually declare `event_family_conclusion_allowed = false`, because neither summary has both configured cross-root symbol/article counts. The current 1.5G production reducer has no cross-root owner. Treating either stored summary as a family receipt, or treating batch7 children as independent parents, would violate the existing authority and L2 cluster rule.

Decision: add one narrowly scoped, local-only `Stage1_5GCrossRootAdmission` producer. It accepts exactly the authority packet in Section 2, reuses the frozen production 1.5G loader/reducer per root, derives a parent-aware cross-root ledger, and writes one sealed receipt only when every invariant passes. It does not alter the 1.5G reducer, any collector, any config threshold, any existing consumer, or any existing root.

The only positive outcome is:

```text
decision = stage1_5g_cross_root_event_family_admission_pass
cross_root_evidence_count_status = sufficient
stage1_5g_gate3_complete = false
formal_symbol_count = 8
distinct_source_article_count = 2
independent_parent_event_count = 2
```

`cross_root_evidence_count_status = sufficient` means only that the frozen data set has passed Gate 3's count/integrity admission for a later separately approved Design. `stage1_5g_gate3_complete` remains exactly `false`: this local receipt cannot attest that Stage 1.5D and 1.5F remain continuously stable. It does not mean an event-family phenomenon is supported, and it must not set or infer `event_family_conclusion_allowed = true` for an economic, Alpha, or execution claim.

## 4. Scope and Non-Goals

### In scope

- Local read-only admission of the two Section 2.2 conditional Stage 1.5F roots and their stored review summaries, only when their exact bytes are present and valid at preflight.
- A new sealed cross-root receipt rooted at `data/external_signal_shadow/stage1_5g/event_family_admissions/<RUN_ID>/`.
- Parent-aware counts, source lineage, receipt integrity, failure handling, and tests.

### Explicit non-goals

- No network request, VPS operation, collector change, data repair, data download, raw-orderbook aggregation, or new event discovery.
- No change to `configs/base.py`, 1.5D, 1.5F, the production 1.5G reducer, existing consumers, existing data roots, or historical review outputs.
- No price/outcome/PnL/expectancy/replay/backtest analysis; no threshold, entry, exit, sizing, Alpha, phenomenon, risk-veto, simulation, paper, live, or execution claim.
- No generic arbitrary-root union framework, registry, plugin, callback, or future-consumer extension point.

## 5. Data and State Contract

### 5.1 Input admission sequence

For each ordered Section 2.2 record, the producer must perform this sequence before using any child field or creating a staging directory:

1. Verify every Section 2.1 upstream contract byte and stop on any drift before importing the production admission module.
2. Require the exact stored summary path to be a regular file, not a symlink; verify its byte SHA-256.
3. Require the exact source root to be a directory, not a symlink; run `load_stage1_5g_inputs(source_root)` and reject any loader blocker.
4. Invoke `build_stage1_5g_review_summary()` with the returned production bundle fields. Do not construct a substitute dictionary and do not read raw JSONL from another call path.
5. Require the root's recomputed summary to have `schema_version = 2`, `decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true`, no blockers, the six exact upstream false keys in Section 2.1, and the exact expected `source_evidence_manifest_sha256` in Section 2.2.
6. Require the stored summary and recomputed summary to agree exactly on schema version, decision, clean flag, source manifest SHA, `formal_completed_event_symbol_ids_sha256`, and the ordered `event_level_decisions` projection (`event_symbol_id`, `event_id`, `symbol`, `source_article_id`, `evidence_label`, `state_status`, `formal_completed`).
7. Accept only `announcement_and_launch_time` / `state_status = completed` children. Require the recomputed formal child set to equal the corresponding Section 2.2 parent-ledger row exactly.

Any mismatch is `STOP=stage1_5g_cross_root_input_authority_mismatch`; no receipt may be published.

### 5.2 Cross-root reducer

After both roots pass Section 5.1, the reducer must:

1. Preserve every admitted child in the parent ledger; no liquidity-based filtering, symbol selection, sorting-dependent deletion, or metric averaging is allowed.
2. Require exactly two distinct `source_article_id` and exactly two distinct `event_id`; a duplicated article or event is `STOP=stage1_5g_cross_root_parent_independence_mismatch`.
3. Require the exact eight-symbol set in Section 2.2 and require no duplicate `event_symbol_id` or `symbol` across roots; any collision is `STOP=stage1_5g_cross_root_child_identity_collision`.
4. Require current config values to remain exactly `3` and `2`, then require `formal_symbol_count >= 3` and `distinct_source_article_count >= 2`; otherwise `STOP=stage1_5g_cross_root_threshold_not_met`.
5. Emit the counts above plus the two-parent ledger. It must emit `independent_parent_event_count = 2`, never 8.

The reducer may state only `cross_root_evidence_count_status = sufficient` and `stage1_5g_gate3_complete = false`. It must emit all of the following exact-false authority flags: `event_family_conclusion_allowed`, `trade_signal_allowed`, `paper_trading_allowed`, `live_trading_allowed`, `execution_engine_allowed`, `alpha_interpretation_allowed`, `execution_feasibility_claim_allowed`, `network_collection_allowed`, `replay_allowed`, `deployment_allowed`, `ssh_allowed`, `commit_allowed`, and `push_allowed`.

### 5.3 Output lifecycle

`RUN_ID` must match `^stage1_5g_cross_root_admission_[0-9]{8}T[0-9]{6}Z$`. The final output root must be exactly:

```text
data/external_signal_shadow/stage1_5g/event_family_admissions/<RUN_ID>/
```

All Section 5.1 and 5.2 admission/reducer checks must pass in memory before the writer creates a staging directory. Therefore an input or reducer failure leaves both final root and matching staging root absent. The final root must not exist before start. Only after those checks, the writer creates a sibling `.<RUN_ID>.staging.<pid>/` and writes only:

1. `stage1_5g_cross_root_admission_summary.json`
2. `stage1_5g_cross_root_admission_review_CN.md`
3. `stage1_5g_cross_root_admission_manifest.json` last.

The summary is UTF-8 without BOM and its bytes must equal `canonical_json_dumps(summary_payload).encode("utf-8")` from the frozen Section 2.1 `safety.py`. Its exact top-level key set is:

```text
authority_flags
cross_root_evidence_count_status
decision
distinct_source_article_count
formal_symbol_count
independent_parent_event_count
input_records
parent_ledger
run_id
schema_version
stage1_5g_gate3_complete
```

The exact values/types are `schema_version: 1` (integer); `run_id` matching the Section 5.3 grammar; `decision: "stage1_5g_cross_root_event_family_admission_pass"`; `cross_root_evidence_count_status: "sufficient"`; `stage1_5g_gate3_complete: false`; `formal_symbol_count: 8`; `distinct_source_article_count: 2`; and `independent_parent_event_count: 2`. No missing or extra top-level key is accepted.

`input_records` is an array of exactly two records in this order: `moonshot`, then `batch7`. Each record has exactly these keys and types:

```text
input_key: string, exact Section 2.2 key
stored_summary_path: string, exact Section 2.2 path
stored_summary_sha256: lowercase 64-hex string, exact Section 2.2 value
source_root_path: string, exact Section 2.2 path
source_manifest_sha256: lowercase 64-hex string, exact Section 2.2 value
recomputed_formal_projection: object
```

`recomputed_formal_projection` has exactly `schema_version` (integer `2`), `decision` (exact clean-pass string), `clean_depth_evidence_pass` (boolean `true`), `source_evidence_manifest_sha256` (the same exact input-record value), `formal_completed_event_symbol_ids_sha256` (lowercase 64-hex string), and `formal_children` (ordered non-empty array). Every `formal_children` record has exactly `event_symbol_id`, `event_id`, `symbol`, `source_article_id`, `evidence_label`, `state_status`, and `formal_completed`; the first four are non-empty strings, `evidence_label` is exactly `announcement_and_launch_time`, `state_status` is exactly `completed`, and `formal_completed` is boolean `true`. Its ordered values must equal the stored/recomputed 1.5G projection from Section 5.1.

`parent_ledger` is an array of exactly two records in the same parent order as `input_records`. Each has exactly `parent_article_id`, `parent_event_id`, `child_event_symbol_ids`, and `child_symbols`; the first two are non-empty strings, the latter two are ordered non-empty string arrays, and both arrays must be derived exactly from the corresponding `formal_children`. `authority_flags` has exactly the 13 Section 5.2 keys and every value is boolean `false`. The summary contains no raw snapshots, price, spread, slippage, depth, coverage, outcome, PnL, or derived market metric.

The Markdown is UTF-8 with LF line endings and one final LF. It is an authoritative artifact only as this byte-for-byte deterministic projection of the parsed summary. The literal template is below; placeholders are substituted without escaping, input/parent rows preserve their summary-array order, authority rows sort lexically by flag name, and child arrays join with a single comma and no space.

```text
# Stage 1.5G Cross-Root Admission Receipt

- `run_id`: `<run_id>`
- `decision`: `stage1_5g_cross_root_event_family_admission_pass`
- `cross_root_evidence_count_status`: `sufficient`
- `stage1_5g_gate3_complete`: `false`
- `formal_symbol_count`: `8`
- `distinct_source_article_count`: `2`
- `independent_parent_event_count`: `2`

## Parent Ledger

| parent_article_id | parent_event_id | child_event_symbol_ids | child_symbols |
| --- | --- | --- | --- |
| <parent_article_id> | <parent_event_id> | <comma_joined_child_event_symbol_ids> | <comma_joined_child_symbols> |

## Frozen Inputs

| input_key | stored_summary_path | stored_summary_sha256 | source_root_path | source_manifest_sha256 |
| --- | --- | --- | --- | --- |
| <input_key> | <stored_summary_path> | <stored_summary_sha256> | <source_root_path> | <source_manifest_sha256> |

## Authority Flags

| flag | value |
| --- | --- |
| <lexically_sorted_flag> | false |
```

The writer must render every parent/input/flag row and no other row. It must not import, receive, or render a production 1.5G Chinese review, a full recomputed summary, raw rows, or any market/depth/economic/Alpha assertion. The strict loader must parse the summary, recreate this exact template, and require byte equality with the stored Markdown before accepting the manifest. Any injected or differently rendered Markdown is `STOP=stage1_5g_cross_root_review_projection_mismatch`.

The manifest is UTF-8 without BOM and its bytes must equal `canonical_json_dumps(manifest_payload).encode("utf-8")`. Its exact top-level key set is `artifacts`, `frozen_input_records`, `run_id`, and `schema_version`; `schema_version` is integer `1`, `run_id` exactly equals the summary, and `frozen_input_records` is canonical-JSON equal to summary `input_records`. `artifacts` has exactly `review` and `summary`, in either JSON-object insertion order but canonicalized by the frozen serializer. Each artifact entry has exactly `relative_path`, `sha256`, and `byte_count`: paths are respectively `stage1_5g_cross_root_admission_review_CN.md` and `stage1_5g_cross_root_admission_summary.json`; `sha256` is lowercase 64-hex; and `byte_count` is a positive integer equal to the actual bytes. Missing or extra key at any manifest level is reject.

The writer must write each artifact through a same-directory temporary regular file, `fsync` it before its final staged name, write and verify the manifest last, then `fsync` the staging directory. It must atomically rename the complete staging directory to the final root and `fsync` the final parent directory. No state file, PID record, prior return code, or in-memory completion flag is authoritative.

The strict loader and restart logic use this exact byte-authoritative state matrix:

| Filesystem state | Canonical state | Consumable | Restart meaning |
| --- | --- | --- | --- |
| final root absent; matching staging root absent | `unpublished` | no | a fresh `RUN_ID` may start |
| final root absent; one or more matching staging roots exist | `staging_only` | no | leave staging untouched; start only with a fresh `RUN_ID` |
| final root exists and exact three-file root, schema, manifest paths, SHA-256, byte counts, summary schema, deterministic Markdown projection, frozen identities and 13 false flags all verify | `receipt_published` | local inspection only | published regardless of whether the producing process returned normally |
| final root exists but any strict check fails | `corrupt_or_unknown` | no | never overwrite, resume, or consume; STOP |

Thus a process crash immediately after successful rename, before normal return, or after rename but before the caller observes success is `receipt_published` if and only if the final bytes strictly validate. A crash before rename is `staging_only`; no resume/reuse is allowed. Any pre-existing final root that is not `receipt_published`, missing manifest, unlisted file, hash/length mismatch, symlink, malformed JSON, incomplete authority vector, or Markdown projection mismatch is rejected fail-closed.

### 5.4 Transition x Failure Matrix

| Transition / failure point | Final-root interpretation | Required producer result | Strict-loader result |
| --- | --- | --- | --- |
| Input admission or reducer fails before staging creation | no final or staging root | `PRE_RENAME_STOP`, non-zero; no artifact is written | `unpublished` only |
| Temporary artifact write / file `fsync` fails | final root absent; staging may exist | non-zero STOP; do not write manifest | `staging_only` is non-consumable |
| Manifest write, manifest verification, or staging-directory `fsync` fails | final root absent; staging may exist | non-zero STOP; do not rename | `staging_only` is non-consumable |
| Atomic rename fails | final root absent; staging may exist | non-zero STOP; do not retry same `RUN_ID` | `staging_only` is non-consumable |
| Rename succeeds, then process crashes before normal return | final root exists | producer outcome is irrelevant after restart | `receipt_published` iff final bytes strictly validate; otherwise `corrupt_or_unknown` |
| Rename succeeds, then final-parent `fsync` fails or process crashes before it returns | final root may exist | `POST_RENAME_DURABILITY_FAILURE`, non-zero; never delete/overwrite final root | determine only from final bytes: `receipt_published` or `corrupt_or_unknown` |
| Restart sees a final root | final root exists | never resume or overwrite | accept only `receipt_published`; otherwise STOP |

### 5.5 Authority Matrix

| Object / actor | What it proves | What it cannot prove or authorize |
| --- | --- | --- |
| Section 2 stored review summary | Historical review identity only | Current source-root validity or producer execution |
| Production 1.5G loader/reducer run | Local re-admission of one frozen root during this invocation | Cross-stage producer authenticity after its output is copied |
| Cross-root summary + deterministic Markdown + manifest | Locally inspectable, self-consistent receipt bytes | That a particular producer invocation executed; any future consumer admission |
| New strict loader | Local receipt integrity and state classification | Producer authenticity, Alpha, phenomenon, replay, execution, or runtime authority |
| Completion Audit | Independent verification for this implementation only | A binding usable by future consumers unless a later Design freezes its identity/hash and verifier grammar |

## 6. Acceptance Invariants

- `INV-15U-01`: Exactly the two Section 2.2 input records are admitted; no discovery, substitution, or third root is allowed.
- `INV-15U-02`: The Section 2.1 upstream contract bytes must verify before source admission; stored summary bytes, source `SHA256SUMS`, and frozen production re-admission must then all bind to the frozen input identity.
- `INV-15U-03`: A root that does not recompute as clean pass is never counted, even if its stored summary says clean pass.
- `INV-15U-04`: The parent ledger is exactly 2 parent articles / 2 parent events / 8 formal children; batch7 children remain one parent cluster.
- `INV-15U-05`: The summary has the exact identity/count/false-vector schema in Section 5.3, and the Markdown is its byte-for-byte deterministic projection. No raw snapshot, orderbook row, price, spread, slippage, aggregate depth metric, outcome, PnL, economic, Alpha, phenomenon, or execution assertion may enter the output receipt.
- `INV-15U-06`: `sufficient` is an operational input-admission state only. `stage1_5g_gate3_complete` remains false until a separately approved current-runtime gate verifies the Stage 1.5D/1.5F prerequisite; neither state can promote `phenomenon_supported`, `alpha_candidate`, `alpha_validated`, executable edge, or runtime authority.
- `INV-15U-07`: The exact 13-field authority vector is present and all values are boolean `false`; absent is not false.
- `INV-15U-08`: Only the Section 5.3 `receipt_published` byte state is locally inspectable. `staging_only`, `unpublished`, `corrupt_or_unknown`, collision, partial, and all failed strict-validation states are non-consumable; process exit status cannot override final bytes.
- `INV-15U-09`: This Design adds no wiring to any existing consumer. This receipt has no current or future consumer authority: any later clean-report, simulator, event-study, replay, or execution route must either independently re-admit the two frozen roots or define a new Design-owned audit identity/hash and receipt-to-audit binding.
- `INV-15U-10`: The admission result must not be used as a third independent parent event, an independent holdout, an L2 research promotion input, or a cross-stage admission prerequisite under this Design.

## 7. Producer / Consumer Matrix

| Role | Owner / artifact | Allowed responsibility | Forbidden responsibility |
| --- | --- | --- | --- |
| Producer | Section 2.1-frozen `load_stage1_5g_inputs` + `build_stage1_5g_review_summary` | Re-admit each Stage 1.5F root under its frozen production rules | Trusting stored review prose as source authority or drifting to changed upstream bytes |
| New writer | `Stage1_5GCrossRootAdmission` | Build the exact-schema summary and its deterministic Markdown projection from admitted projections | Recompute depth metrics, read raw rows independently, choose children, or import the old 1.5G review renderer |
| Loader | New strict receipt loader | Verify manifest, paths, hashes, lengths, exact schema, deterministic Markdown projection, frozen identities and false vector | Tolerant defaults, partial-root consumption, or producer-authenticity inference |
| Existing consumers | None wired by this Design | N/A | Consuming this receipt |
| Future consumer | None under this Design | N/A | Consuming this receipt as an admission prerequisite or producer-execution proof |
| Reviewer | Independent completion audit | Re-run strict source and receipt loading, inspect scope and actual permissions | Rely only on produced summary/review prose |

## 8. L2 Research Boundary

This Design is evidence governance, not an Alpha research stage. The required L2 items are deliberately `N/A`:

| L2 item | Status and reason |
| --- | --- |
| Alpha / economic mechanism hypothesis | N/A; no market claim is computed. |
| Claim level | Data-quality / operational-admission only; not `phenomenon_supported`. |
| Independent sampling unit | Fixed at `parent_article_id` / parent `event_id` only to prevent correlated-child misuse; count is 2. |
| PIT / anti-hindsight | Input roots are frozen historical captures; no forward outcome or post-selection rule is read. |
| Observation rule, outcomes, costs, liquidity/capacity, MAE, outliers, conditional Alpha | N/A; receipt carries no outcome or metric values. |
| Promotion / kill | N/A for Alpha. A valid receipt may be described in a later Design but is not that Design's admission authority; invalid or insufficient input is `EVIDENCE_GAP`, not a negative Alpha claim. |

## 9. Failure Semantics

| Condition | Result |
| --- | --- |
| Missing/changed Section 2.1 upstream contract byte | `STOP=stage1_5g_cross_root_upstream_contract_drift` |
| Missing/changed stored summary or source manifest | `STOP=stage1_5g_cross_root_input_authority_mismatch` |
| Production loader/reducer blocker or non-clean recomputation | `STOP=stage1_5g_cross_root_root_not_clean` |
| Parent/article/event/child collision or unexpected set | `STOP=stage1_5g_cross_root_parent_independence_mismatch` or `STOP=stage1_5g_cross_root_child_identity_collision` |
| Threshold/config drift | `STOP=stage1_5g_cross_root_threshold_not_met` |
| Output collision, path escape, `staging_only`, `corrupt_or_unknown`, projection mismatch, or integrity failure | `STOP=stage1_5g_cross_root_publication_integrity_failure` |
| Request to consume by an existing consumer, future Design, simulator, replay, or execution path without independent root re-admission / a new audit-binding Design | `STOP=stage1_5g_cross_root_future_consumer_not_authorized` |

`PRE_RENAME_STOP` paths return non-zero, create no final receipt, and leave all authority flags false. `POST_RENAME_DURABILITY_FAILURE` also returns non-zero and leaves all authority flags false, but it must never delete or overwrite the final root: only the strict final-byte classifier decides `receipt_published` versus `corrupt_or_unknown`.

## 10. Implementation Scope and Verification Strategy

The later Implementation Plan may whitelist only a new local source module, a local CLI, focused tests, and the generated runtime receipt root. It must not modify `configs/base.py`, existing 1.5G producer code, collectors, deployment files, or existing evidence.

Required proof includes:

1. Canonical positive fixture: call the actual 1.5G production loader/reducer on the exact Section 2 roots; do not handcraft source dictionaries.
2. Single-mutation negative cases: one Section 2.1 upstream-file SHA mismatch; stored summary SHA mismatch; source manifest mismatch; one recomputed root non-clean; duplicate parent article; duplicate child symbol; threshold drift; one missing/extra/wrong-type summary or manifest key; missing one authority key; unlisted/changed output artifact; forbidden market/economic/Alpha text injected into Markdown; existing final root.
3. Crash test: crash after each staged artifact, before/after manifest write, immediately after final rename, and after final rename before normal return / parent-directory `fsync`. The strict loader must reject all non-final states and must classify a strictly valid final root as `receipt_published` independently of producer exit status.
4. Restart test: stale staging root remains non-consumable; `corrupt_or_unknown` final root is never overwritten; a fresh distinct `RUN_ID` can succeed without reusing either state.
5. Production wiring: CLI must reach the production loader/reducer; an `open` spy or AST gate must reject a second direct source-row reader.
6. Safety and scope: actual anti-shortcut scanner return code, `RISK_LIVE_TRADING_ENABLED=False`, no network call, exact Git diff/index/worktree proof, independent code review, then fresh Completion Audit.

## 11. Open Questions

None blocking this Design. Whether a cross-root receipt should later feed any report, simulator, or exploratory event study is deliberately deferred. Each would require its own Design because it changes the consumer claim and validation surface.

## 12. Design Handoff

This candidate authorizes nothing. Required route:

```text
independent Design review
-> user approval of exact Design bytes
-> Implementation Plan
-> independent Plan review
-> user approval of exact Plan bytes
-> local implementation and Completion Audit
```

At every stage, `RISK_LIVE_TRADING_ENABLED` remains `False` and all receipt authority flags remain false.
