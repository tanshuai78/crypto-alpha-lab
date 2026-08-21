# Stage 1.5F Formal-V2 Anchor Source Lineage Projection Hotfix Design

**状态：** Draft for review
**日期：** 2026-08-20
**设计基线：** `9e39705`
**关联事故：** `UNITREEUSDT` / Binance article `3e662272597c44b7939f5db5c8c86d4f`
**关联证据：** `data/external_signal_shadow/stage1_5g/reviews/20260820T023941Z_unitree_local/`

> **Design Delta 1 (2026-08-20, Draft for review):** This delta resolves the
> previously blocking semantic-fingerprint authority and restart crash window.
> It supersedes only the fingerprint-related Task 0 STOP boundary below. The
> existing implementation plan is not approved authority and must be rewritten
> after this delta is independently reviewed.

## 1. 已确认事实

1. `UNITREEUSDT` 的 1.5F 观察已完成 12 小时采集：`715 / 720` 个 depth snapshot；这不是盘口采集或 HTTP book 有效性故障。
2. 该本地 1.5G review 的唯一 blocker 是 `formal_v2_lineage_incomplete_or_mismatch`，因此 `formal_announcement_and_launch_count = 0`，结论为 `stage1_5g_depth_evidence_invalid`。
3. UNITREE accepted row 与其最新 observer state 都具有：
   - `formal_event_contract_version = 2`
   - `source_contract_status = "formal_v2_valid"`
   - `launch_anchor_evidence_level = "official_schedule"`
   - `anchor_precedence_policy = "official_schedule_priority_v1"`
   - 一致且非空的 source/admission/latest anchor-contract hashes
   - `observation_anchor_basis = "official_schedule_anchor"`
4. 同一对 artifact 的 `effective_observation_anchor_source` 均为 `null`。1.5G 的 formal-v2 predicate 要求 accepted row 的该值精确为 `"official_schedule_anchor"`，因此拒绝是预期的 fail-closed 行为。
5. 1.5D 已在正式 v2 event 的 per-symbol map `symbol_effective_observation_anchor_sources[symbol]` 中持久化该来源。1.5D 不缺此事实。
6. 1.5F 的 `resolve_depth_observation_anchor_ms()` 从已验证的 1.5D contract 正确读出 `effective_source`，并赋给 `observation_anchor_basis`，但其返回 diagnostics 未包含 `effective_observation_anchor_source`。
7. `create_pending_observation_state()` 当前从 diagnostics **或** event row 顶层读取 `effective_observation_anchor_source`。真实 formal-v2 source 是 per-symbol map，不是 event row 顶层字段，故 UNITREE state 记录为 `null`；同时这个顶层 fallback 会把测试或非 canonical input 伪造为 clean source。
8. 现有 fixture/test 常直接构造顶层 `effective_observation_anchor_source` 或已带此字段的 state，未覆盖真实的 per-symbol map -> resolver -> state -> accepted row -> 1.5G 链路。
9. Schedule revision 是与 initial launch event 不同的正式 transport contract。其 `selected` 结果目前只携带 schedule status、anchor、revision identity 和 availability，不携带显式 source provenance；当前 reducer 因此直接写 literal `"official_schedule_anchor"`。
10. Frozen `source_semantic_fingerprint_v1` contains the per-symbol anchor time but not `symbol_effective_observation_anchor_sources[symbol]`. `symbol_anchor_evidence_levels[symbol]` is not a proved invariant-equivalent substitute for the source map. Therefore a source-only correction can be suppressed by v1 replay classification.
11. The prior storage-lifecycle Design freezes v1's canonical projection, raw SHA-256 storage format and observer-state schema v3. Reinterpreting an existing raw v1 value as a v2 value, or changing v1's hash input in place, would silently alter historical replay identity.
12. The F runner loads the complete D event/revision stream on each poll. A schedule-revision registry `revision_applied` record is not consulted by `re_resolve_pending_anchor()` when it constructs the current-poll revision inputs. This existing full-stream path can recover a pending state after a crash, but it lacks an explicit contract and regression proof.

## 2. 显式假设

1. 对 initial formal-v2 launch event，`symbol_effective_observation_anchor_sources[symbol]` 是唯一 source authority；其值已由 `validate_launch_anchor_contract()` 验证后才可进入 1.5F。event row 顶层同名字段不是 formal-v2 authority。
2. 对 pending schedule transition，唯一 authority 是通过 `validate_schedule_revision_contract()`、stable identity/supersedes match 和 point-in-time `select_latest_applicable_official_schedule()` 的正式 revision contract；它不是 initial-event map 的 fallback，也不是 raw branch literal。
3. 本 hotfix 不改变官方排期优先级、anchor 时间选择、revision business semantics、watermark、12 小时观察窗口、盘口请求频率或任一配置阈值。
4. UNITREE 的历史 JSONL、depth snapshot、state、accepted row 和 1.5G review 都是 immutable historical evidence，绝不回写或删除。
5. 1.5G 对 formal-v2 的拒绝必须维持 fail-closed；不得以 `observation_anchor_basis`、hash 存在性或任何推断替代缺失的 durable source field。

## 3. 根因与核心问题

### 3.1 根因

1.5F 共享 anchor resolver 已完成正确的 contract validation 和 source selection：

```text
1.5D symbol_effective_observation_anchor_sources[symbol]
-> validate_launch_anchor_contract(...)
-> effective_source = "official_schedule_anchor"
-> observation_anchor_basis = effective_source
```

但 resolver diagnostics 缺失同一事实的 formal-audit projection：

```text
effective_observation_anchor_source = effective_source
```

这造成运行行为和审计行为分裂：F 以官方排期开始观察，但 state/accepted row 没有可由 G 审计的持久化证明。

### 3.2 为什么不能在 1.5G 中推断修复

`observation_anchor_basis` 是 F 的运行诊断字段；`effective_observation_anchor_source` 是 formal-v2 lineage 中声明“实际所用 anchor 来源”的 durable contract field。若 G 用前者补全后者，会让新版 reviewer 利用事后逻辑将旧证据升级为 clean，破坏 point-in-time 与 append-only evidence semantics。

因此缺字段必须继续 invalid，而不是在 reviewer 中容错。

## 4. 范围与显式非目标

### 4.1 范围内

1. 修正 1.5F shared resolver 的 formal-v2 source diagnostics projection。
2. 在 schedule revision re-resolution 覆盖 observation anchor 时，同步覆盖 `observation_anchor_basis` 与 `effective_observation_anchor_source`。
3. 强化 1.5G formal-v2 predicate：accepted row 与 latest state 必须都声明同一 `"official_schedule_anchor"`，不得只验证 accepted row。
4. 补足真实 D per-symbol source map 的端到端 RED/regression tests。
5. 为未来 rollout 冻结 root separation 规则：包含 UNITREE 这种 immutable invalid formal-v2 artifact 的 F root 不得再用于新的 clean evidence 结论。
6. Add a prospective-only `source_semantic_fingerprint_v2` state-value contract so that a validated source-only correction is observable for newly created states without modifying frozen v1 identity.
7. Freeze the pending revision crash-recovery contract for the case where the registry is durable but the adapter-derived state transition is not.

### 4.2 显式非目标

1. 不修改 1.5D collector、formal event schema、`stage1_5_launch_anchor_contract.py` 或 schedule revision producer。
2. 不增加 state 字段、不提高 `observer_state_schema_version`、不迁移旧 state，也不改变任何已持久化的 v1 fingerprint value。
3. 不改变 1.5G depth quality thresholds、指标、evidence labels 或任何放宽条件。
4. 不修改 `configs/base.py`，不新增 config、CLI flag、storage writer、network request 或依赖。
5. 不回写 UNITREE artifact，也不将 UNITREE 重新分类为 clean evidence。
6. 不部署、不重启当前 VPS 1.5D/1.5F 进程；部署与新 root 创建属于后续独立批准的 rollout 操作。
7. `RISK_LIVE_TRADING_ENABLED` 保持 `False`；不授权 trade signal、paper trading、live trading、execution engine、alpha interpretation 或 execution-feasibility claim。

## 5. 已作决策及理由

### 5.1 Initial formal-v2 禁止顶层 fallback，并在共享 resolver 一次性投影

`resolve_depth_observation_anchor_ms()` is the source-selection outlet for an
**initial launch event** only. It must return both fields in its formal-v2
validated branch:

```text
observation_anchor_basis = effective_source
effective_observation_anchor_source = effective_source
```

Pending formal schedule revisions do not enter this initial-event resolver;
they use the distinct validated adapter in §5.2. `create_pending_observation_state()`
must branch by contract version:

```text
formal-v2:
  source = diagnostics.effective_observation_anchor_source only
  event_row.effective_observation_anchor_source fallback = forbidden

formal-v1:
  retain existing legacy compatibility behavior
```

因此 formal-v2 的 canonical per-symbol map 缺失或 validation 失败时，即使 event row 顶层伪造 `official_schedule_anchor`，state 也不得成为 clean source。此处需要修改 state builder；只补 resolver 不足以消除第二套 authority。

### 5.2 Pending revision 只能使用已验证的 revision-contract authority

schedule revision 不能被伪装为 initial launch event 并复用其 resolver input，因为两者 schema 不同。它必须走一个 loader-local 的 validated schedule-selection adapter：

```text
validate_schedule_revision_contract(revision row)
AND stable identity / supersedes source article match
AND select_latest_applicable_official_schedule(..., now_ms) == selected
AND selected revision has an effective official anchor
-> validated_revision_source = "official_schedule_anchor"
```

只有该 adapter 的输出可使 `re_resolve_pending_anchor()` 同时写入：

```text
observation_anchor_ms = validated selected anchor
observation_anchor_basis = validated_revision_source
effective_observation_anchor_source = validated_revision_source
```

raw revision row、official-looking anchor timestamp、`schedule["status"] == "selected"` 分支本身或任何顶层 fallback 均不得单独制造 source。若 revision contract/source provenance 无法验证，保留既有 pending/invalid handling，不得进入 clean lineage。

### 5.3 Pending 可更新，active/completed 的 admission source 冻结

在 observation 尚未 active 前，pending state 可仅通过 §5.2 的 validated revision transition 从 fallback/missing source 改为 official source。该 transition 必须原子更新 anchor、basis、source 和既有 revision lineage fields。

一旦 source 已用于 active admission：

```text
active -> accepted row -> completed
```

admission source、admission anchor 和 accepted source 必须保持一致。之后 incompatible revision 继续走既有 contamination semantics；completed state 不得 reopen、upgrade 或重写。这保留既有 `pending fallback -> official`、`active -> contamination` 与 `completed -> immutable` 的业务生命周期。

### 5.4 1.5G 保持严格，并验证 source、basis 与 accepted/state 一致性

对于 declared formal-v2 event，1.5G pass 的必要条件增加为：

```text
accepted.effective_observation_anchor_source
    == "official_schedule_anchor"
AND
latest_state.effective_observation_anchor_source
    == "official_schedule_anchor"
AND
accepted.effective_observation_anchor_source
    == latest_state.effective_observation_anchor_source
AND
accepted.observation_anchor_basis
    == accepted.effective_observation_anchor_source
AND
latest_state.observation_anchor_basis
    == latest_state.effective_observation_anchor_source
AND
accepted.observation_anchor_basis
    == latest_state.observation_anchor_basis
```

缺失、空值、fallback source 或 accepted/state 不一致均返回既有 blocker `formal_v2_lineage_incomplete_or_mismatch`。这不改变 legacy v1 fallback 行为。

### 5.5 UNITREE 只作为负向回归证据

UNITREE 证明此前真实运行会漏投影该字段。它必须以最小化、去敏后的 regression shape 保留，断言旧形态继续被 1.5G 拒绝；不可改写真实 root 使其通过。历史证据的 invalid 结论优先于获得额外 clean sample 的便利。

### 5.6 未来 clean evidence 采用新 F root

1.5G 对一个 root 内所有 accepted events 进行完整性审查。含 UNITREE invalid artifact 的旧 F root 即使后来采集了正确事件，仍会产生 lineage blocker。因此，经后续 Plan、审计和用户部署批准后：

```text
preserve old F root unchanged
-> start one new F root with --bootstrap-watermark
-> bind it to the already-running eligible D root
-> admit only post-watermark future events
```

不得删除 UNITREE accepted/state 行来“清理”旧 root，也不得同时运行两个 F writer。

### 5.7 Versioned semantic fingerprint: preserve v1, admit v2 only prospectively

`source_semantic_fingerprint_v1` is frozen historical identity. It remains
the exact prior canonical projection and its stored value remains a bare
64-character SHA-256 hex digest. It must not gain the source map, be
recomputed into a different value, or be reinterpreted as v2.

This hotfix instead defines `source_semantic_fingerprint_v2` for states first
created by the hotfixed code in a **new F root**. Its canonical projection is
the exact frozen v1 projection plus exactly one additional field:

```text
symbol_effective_observation_anchor_sources[symbol]
```

All v1 canonical JSON rules remain unchanged: uppercase symbol map lookup,
sorted keys, compact UTF-8 JSON and SHA-256. The durable value in the existing
`EventSymbolState.latest_source_semantic_fingerprint` field is exactly:

```text
source_semantic_fingerprint_v2:<lowercase-64-character-sha256>
```

No state field or schema version is added. A bare digest and `""` are legacy
v1/unknown values. Replay dispatch is version-aware and deterministic:

```text
existing prefixed v2 value -> compare only v2 candidates
existing bare v1 value    -> compare only frozen v1 candidates
existing empty value      -> legacy compatibility handling; never infer v2
newly created state       -> seed and persist a prefixed v2 value before it
                            can be classified as an exact replay
```

The v2 grammar is exact and fail-closed:

```text
source_semantic_fingerprint_v2:<exactly 64 lowercase hexadecimal characters>
```

An explicit but malformed or unknown version is never legacy input:

```text
source_semantic_fingerprint_v2:
source_semantic_fingerprint_v2:xyz
source_semantic_fingerprint_v3:<hash>
any other non-v1 prefix
-> integrity/replay blocker; no legacy fallback, state transition, acceptance,
   watermark mutation or clean-evidence conclusion
```

Thus a source-only change with the same anchor creates at most one pending
state update for v2, while the same correction on a legacy v1/empty state is
not silently upgraded. A v2 source-only change against an active or completed
state must retain the existing no-reopen/no-accepted-row-rewrite lifecycle.
The fingerprint is a replay/state-dedupe mechanism only; it does not change
formal event identity, stable keys, anchor-contract hashes, schedule revision
identity, watermark schema or 1.5G's evidence predicate.

### 5.8 Registry record is not pending-state selection completion

For a pending formal-v2 revision, the schedule-revision registry may durably
record `revision_applied` before the loader-local validated adapter has
durably written its selection transition. In this narrow meaning,
`revision_applied` records revision dispatch/idempotency only; it is **not**
proof that anchor, basis, source and the existing applied-revision lineage
reached the pending state.

The full revision stream plus the pending state remains the authority for
adapter recovery. On every restart or replay, the loader must re-evaluate the
raw revision through the validated adapter regardless of an existing registry
record. The adapter may write the final pending transition exactly once; it
must not append a second registry row, a second accepted row, or regress the
watermark. This reuses the existing full-stream re-resolution path rather than
adding runner-level recovery state.

## 6. 验收不变量

| ID | 不变量 |
|---|---|
| INV-01 | Initial formal-v2 source 只能来自 validated `symbol_effective_observation_anchor_sources[symbol]` 的 resolver diagnostics；event row 顶层 fallback 被禁止。 |
| INV-02 | 已验证 initial formal-v2 per-symbol source 为 `official_schedule_anchor` 时，shared resolver 必须同时返回同值的 `observation_anchor_basis` 与 `effective_observation_anchor_source`。 |
| INV-03 | pending source transition 只能来自已验证、identity-matched、point-in-time selected 的 formal schedule revision；不得由 raw branch 或 official-looking timestamp 制造。 |
| INV-04 | 一旦 source 用于 active admission，它必须在 active -> accepted row -> completed 之间保持一致；之后 revision 维持既有 contamination/immutability 语义。 |
| INV-05 | formal-v2 accepted row/latest state 的 source 或 basis 为空、不相等或不是 `official_schedule_anchor` 时，1.5G 必须 fail closed。 |
| INV-06 | 1.5G 不得从 `observation_anchor_basis`、hash、clock 或任何事后逻辑推断、填补或覆盖 `effective_observation_anchor_source`。 |
| INV-07 | formal-v1 compatibility、exchangeinfo fallback rejection、anchor conflict、missing anchor、revision contamination 与 completed-hash 检查保持原语义。 |
| INV-08 | UNITREE historical artifact 仍被判为 `formal_v2_lineage_incomplete_or_mismatch`，不得因修补后代码而被升级。 |
| INV-09 | 本 hotfix 不改变任何时间锚点、观察窗口、请求频率、storage limit、watermark、状态 schema version 或 config assignment。 |
| INV-10 | 同一 event/state 的 repeated loader/re-resolution/restart 不得产生不同 source 值或额外 accepted row。 |
| INV-11 | 含历史 formal-v2 lineage blocker 的 F root 不能作为未来 clean evidence root；root separation 不得通过删除或重写旧 artifact 实现。 |
| INV-12 | 所有交易、paper、execution、alpha interpretation 和部署权限保持 false/not allowed。 |
| INV-13 | Frozen v1 fingerprint canonical input and every already persisted bare/empty value remain legacy; only a new state in a new F root may persist a prefixed v2 value. |
| INV-14 | For v2, the effective source map is part of replay identity. Same anchor plus changed source causes at most one pending durable state transition; active/completed states never reopen or rewrite accepted source. |
| INV-15 | Registry durable plus adapter-state-absent crash recovery replays the full revision stream through validation and writes one complete selected-revision lineage tuple exactly once, without duplicate registry/accepted/watermark effects. |
| INV-16 | An explicit malformed or unknown fingerprint version is an integrity/replay blocker and must never silently downgrade to legacy v1 handling. |
| INV-17 | Under hotfixed deployment, every legacy root is read-only historical evidence. The hotfixed runtime must not resume it for new collection; v1/empty dispatch exists only to load or deterministically replay legacy state inputs. |

## 7. 数据、状态与时间契约

### 7.1 Formal-v2 source projection contract

| Artifact | Field | Writer | Required value for clean formal-v2 official anchor |
|---|---|---|---|
| Initial 1.5D event | `symbol_effective_observation_anchor_sources[symbol]` | validated formal-v2 launch contract | `official_schedule_anchor` |
| Pending schedule revision | validated revision contract + selected schedule result | validated schedule-selection adapter | `official_schedule_anchor` only after all §5.2 predicates |
| F resolver diagnostics | `effective_observation_anchor_source` | shared resolver | Exact validated per-symbol source |
| F state | `effective_observation_anchor_source` | initial/re-resolution reducer | Exact resolver source |
| F accepted row | `effective_observation_anchor_source` | accepted-row builder | Exact state source, no fallback |
| G review | accepted + latest state source | strict consumer | Both exact and equal |

The source field states which accepted anchor drove the observation. It is not a replacement for `source_anchor_contract_hash`, `admission_anchor_contract_hash`, `latest_anchor_contract_hash`, `observation_anchor_ms`, or `observation_anchor_basis`; all remain required and semantically distinct.

### 7.2 Reducer sequence

```text
initial formal-v2 row
-> validate launch contract for symbol
-> extract canonical per-symbol effective_source
-> resolver diagnostics contain basis + source
-> formal-v2 state builder consumes diagnostics only

pending revision
-> validate revision contract, identity, availability and selected result
-> validated schedule-selection adapter returns anchor + source
-> atomically update pending anchor/basis/source/revision lineage

active admission
-> freeze admission source through accepted row and completed state
-> 1.5G compares accepted/latest source and basis
```

No current clock, D detection time, event title, exchangeinfo value, raw schedule branch or G-side inference may supply the source field.

### 7.3 Replay identity contract

| Existing durable value | Candidate algorithm | Permitted action |
|---|---|---|
| `source_semantic_fingerprint_v2:<digest>` | v2 only | Apply an included-field pending transition at most once; identical v2 is replay. |
| bare v1 digest | frozen v1 only | Retain existing v1 classification and bare-value storage; never upgrade representation in place. |
| `""` / missing legacy value | legacy compatibility only | Do not infer a v2 revision from a source-only correction. |
| malformed/unknown explicit prefix | none | Fail closed as an integrity/replay blocker; never reinterpret as v1. |
| newly constructed state | v2 | Seed the prefixed v2 value before normal replay classification. |

The v2 encoding is deliberately self-describing inside the existing additive
field. `observer_state_schema_version` remains `3`; no consumer may use a
bare digest as evidence that a source map was included.

## 8. 异常处理、持久化与幂等性

### 8.1 Fail-closed semantics

| Condition | Required result |
|---|---|
| Initial formal-v2 contract invalid, canonical source absent, or only top-level source exists | Existing pending/diagnostic handling; no fabricated source value and no event-row fallback. |
| Revision has an official-looking anchor but fails formal revision validation, identity match, availability or selected-source predicate | Existing pending/invalid handling; it cannot transition source or become clean. |
| State source missing after a purported official-source selection | State remains evidence-incomplete; resulting 1.5G review rejects formal-v2 lineage. |
| Accepted/state source or basis mismatch | 1.5G returns `formal_v2_lineage_incomplete_or_mismatch`. |
| Source is `exchangeinfo_onboard_date` or any non-official source | Existing fallback/rejection semantics remain; it cannot become formal clean evidence. |
| Historical UNITREE artifact | Preserve bytes and invalid review result; no migration or replay upgrade. |

### 8.2 Persistence and restart

`EventSymbolState` already owns `effective_observation_anchor_source`; no schema change is required. Existing guarded state append, checkpoint, compaction and restart machinery remain the only persistence mechanism.

The new projection is deterministic from the immutable formal-v2 row and selected schedule revision. A restart or repeated re-resolution of the same valid input must preserve the same value. No repair task may scan old roots and mutate their rows.

### 8.3 Registry-before-adapter crash window

The required crash/restart sequence is:

```text
pending old state
-> valid v2 revision is received
-> registry revision_applied is durable
-> process crashes before adapter-derived state append
-> restart reloads the full D event/revision stream
-> validated adapter writes one final pending state transition
-> repeated replay writes no further transition
```

The test fixture must prove one coherent tuple from one validated selection:
the selected `revision_id`, its `revision_application_id`, the state
`applied_schedule_revision_ids`, revision count, latest anchor-contract hash,
source, basis and anchor must all correspond to that same selection. This
does not add a `revision_application_id` field to `EventSymbolState`; it
compares the raw revision/application identity with the existing durable state
lineage. Recovery must neither add a registry row nor an accepted row nor
change/regress the watermark. If the revision cannot be validated again,
recovery remains pending or fails closed under existing handling; it must not
manufacture a source.

## 9. Producer / Consumer 契约影响矩阵

| Component | Role | Change | Contract consequence |
|---|---|---|---|
| `run_stage1_5d_live_event_source_smoke_collector.py` | producer | unchanged | Existing per-symbol source map remains authority. |
| `stage1_5_launch_anchor_contract.py` | formal contract validator | unchanged | No formal event version or hash identity change. |
| `stage1_5f_live_depth_observer_loader.py` | resolver/reducer/replay dispatch | modify | Project initial source; validate/adapt pending revision source before transition; preserve v1 and dispatch prefixed v2 correctly. |
| `stage1_5f_live_depth_observer_models.py` | state schema | unchanged | Existing field is reused. |
| `stage1_5f_live_depth_observer_state.py` | state builder | modify | Formal-v2 diagnostics-only source assignment; seed v2 for new states; retain formal-v1 compatibility branch. |
| `run_stage1_5f_live_depth_observer.py` | accepted-row writer | unchanged | Existing exact state serialization consumes projection. |
| `stage1_5g_live_depth_evidence_review.py` | consumer/reviewer | modify | Require accepted/latest-state source equality for formal-v2. |
| storage guard / D-F attestation | safety infrastructure | unchanged | No write surface or deployment trust change. |

## 10. 兼容性、迁移和旧 root 规则

1. `observer_state_schema_version` remains unchanged because the field already exists.
2. Formal event contract version, revision contract version, event identity, stable keys, anchor contract hash and schedule revision identity remain unchanged.
3. Formal-v1 behavior remains governed by the existing legacy compatibility path.
4. Old formal-v2 rows lacking the field remain invalid on a fresh G review. This is a deliberate compatibility result, not a regression.
5. No online migration, backfill, JSONL rewrite or accepted-row reconciliation is permitted for existing roots.
6. A later approved rollout must preserve the old root and use a separate F root for prospective clean evidence. The new root must bootstrap a new watermark and have a single F writer.
7. New-root states use the prefixed v2 fingerprint contract. Under the hotfixed deployment, a legacy root is read-only historical evidence and the hotfixed runtime must not resume it for new collection. v1/empty dispatch exists only for deterministic compatibility/replay of legacy state inputs, not to authorize continued collection into that root.
8. Existing state rows with an empty fingerprint remain compatible through the legacy path. Their missing value does not authorize a source-only replay update or v2 interpretation.

## 11. 证据与 Fixture Provenance

1. Incident review output is `data/external_signal_shadow/stage1_5g/reviews/20260820T023941Z_unitree_local/`; its copied source F evidence bundle is `data/external_signal_shadow/local_evidence/20260820T023941Z_unitree_stage1_5f/`. Task 0 must record their artifact hashes and copied-from relationship before using a derived regression shape.
2. The existing `ko_rddt_formal_v2_lineage` fixture is insufficient by itself because it supplies a top-level source field and does not reproduce the real per-symbol formal-v2 input shape.
3. New tests must use a minimal synthetic dict explicitly labelled as a structural regression fixture. It must include the D-owned per-symbol maps and no network payload or live root path.
4. The negative regression must express the UNITREE defect shape: valid hashes/policy/basis but `effective_observation_anchor_source = null`; expected result is G rejection.

## 12. 验证策略

### 12.1 RED tests before implementation

1. Formal-v2 per-symbol map with official source -> resolver returns both exact source fields.
2. Formal-v2 row with top-level `official_schedule_anchor` but missing/invalid canonical per-symbol source and diagnostics -> state source remains unavailable; G rejects.
3. The same valid resolver output -> pending -> active/completed state -> accepted row, with identical non-empty source and basis values at every boundary.
4. Pending fallback/missing source -> validated matching revision -> atomically transitions anchor/basis/source to official; invalid revision with official-looking anchor does not.
5. Active and completed revision lifecycle retains existing contamination/immutability behavior; it does not rewrite accepted source.
6. G accepts only an official formal-v2 row whose accepted/latest source and basis are exact, equal and official.
7. G rejects each of: accepted null, latest state null, accepted/state source mismatch, accepted basis/source mismatch, latest basis/source mismatch, accepted/latest basis mismatch, fallback source, and source inferred only through `observation_anchor_basis`.
8. UNITREE negative shape remains rejected.
9. A same-anchor source-only change produces a new v2 pending transition exactly once; the same v1 input retains frozen v1 replay behavior and does not transition merely because v2 exists.
10. A same-anchor source-only v2 input against active and completed states does not reopen the observation, append an accepted row, or rewrite accepted source.
11. Every newly persisted v2 value matches the exact grammar; malformed/unknown explicit prefixes fail closed and never fall back to v1.
12. Task 0 inventories every fingerprint consumer: compute helper, classifier, pending upsert, state serializer/`from_dict`, compaction, restart loader, runner tests and any length/hex-format assertion. If any consumer assumes a fingerprint is always exactly 64 characters and correcting it requires a path outside §13.1 or §13.2, STOP and report the call-site/assumption/required path; do not expand scope.
13. Crash after durable `revision_applied` but before adapter state append: restart reloads the raw revision, validates before schedule-row reduction, produces exactly one adapter-derived state transition, and proves the selected revision id, revision application id, applied revision ids, revision count, latest anchor-contract hash, source, basis and anchor are one validated tuple; no duplicate registry row, accepted row or watermark change.

### 12.2 Regression and safety gates

1. Existing formal-v1, anchor conflict, missing-anchor, exchangeinfo fallback, revision-contamination and completed-hash tests remain green.
2. Targeted test command must cover loader, state, F runner accepted-row wiring, and G integrity tests.
3. Run scoped Ruff, `git diff --check`, and a zero-diff gate for `configs/base.py`, 1.5D collector, state models, storage guard and all trading/execution modules.
4. Verify `RISK_LIVE_TRADING_ENABLED is False` and `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED is False`.

## 13. Preliminary Allowed Change Scope for Implementation Plan

### 13.1 Allowed implementation paths

```text
src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
src/research/external_signal_shadow/stage1_5g_live_depth_evidence_review.py
```

### 13.2 Allowed verification paths

```text
tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
tests/research/external_signal_shadow/test_stage1_5g_live_depth_evidence_review_integrity.py
tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
```

### 13.3 Affected but unchanged documentation paths during implementation

```text
docs/designs/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-design_CN.md
docs/plans/2026-08-20-external-signal-shadow-lab-stage1-5f-formal-v2-anchor-source-lineage-projection-hotfix-implementation-plan_CN.md
```

The Design and Plan are immutable implementation authority once their reviews
approve them; implementation must not edit either document. `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md` is also affected but unchanged. Any new-root deployment command requires a separate rollout review with fresh server identity, writer-count, D-root, watermark, storage and commit-attestation evidence. No generated artifact, `data/**`, `graphify-out/**` or VPS runtime output is committed.

### 13.4 Forbidden paths and actions

```text
configs/base.py
scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py
src/research/external_signal_shadow/stage1_5_launch_anchor_contract.py
src/research/external_signal_shadow/stage1_5_storage_guard.py
all execution, risk, strategy and exchange-order modules
all existing data/external_signal_shadow/** artifacts
any direct VPS deployment, restart, root deletion, JSONL rewrite, git clean, reset, or ruff --fix .
```

## 14. Rollout and Rollback

### 14.1 This Design authorizes no deployment

Implementation approval, completion audit and a separate explicit user deployment approval are required before any VPS operation. The current F process and all current roots remain untouched by this Design.

### 14.2 Future rollout prerequisite

Before a prospective rollout: complete the active observation, archive/review the existing root, confirm one D and zero/new F writer sessions, validate storage and ancestry gates, then create exactly one new F root with `--bootstrap-watermark`. It must consume the selected active D root only.

### 14.3 Rollback

If preflight, tests, runtime gate or lineage check fails: do not start the new F process. Preserve every existing root unchanged, stop only the newly created F session if it exists, and report the blocker. No rollback path writes old evidence.

## 15. 安全与权限边界

```text
RISK_LIVE_TRADING_ENABLED = False
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
trade_signal_allowed = false
alpha_interpretation_allowed = false
deployment_allowed = false until separate approval
```

This hotfix repairs evidence lineage only. It cannot establish an alpha, change position sizing, authorize an order, or convert a completed depth collection into a tradable conclusion.

## 16. 未解决问题

| Question | Status | Owner / next action |
|---|---|---|
| Is the known source-map fingerprint omission unresolved? | Resolved by Delta 1 | v2 includes `symbol_effective_observation_anchor_sources[symbol]`; v1 stays frozen and is not reinterpreted. The future Plan must record the exact v1/v2 call-site evidence, every fingerprint consumer/format assumption, and the same-anchor/source-only case. |
| Are there other missing source-map projections? | Blocking Task 0 preflight | Inspect `symbol_official_schedule_anchor_ms`, `symbol_anchor_evidence_levels`, `symbol_max_evidence_classes` and their resolver diagnostics/state projections. If a required field is neither projected nor proved invariant-equivalent, or fixing it needs a path outside §13.1, STOP, report field/call-site/impact in a table, and create a separate Design/Plan. Do not expand scope in place. |
| When should a new F root be deployed? | Deferred, blocking deployment only | User decides after this Design and its Implementation Plan are reviewed, audited and explicitly approved. |
| Can UNITREE ever become clean evidence? | Resolved: no | Keep it invalid and retain only as negative regression/incident evidence. |

## 17. Design Approval Boundary

This Design Delta is ready for independent review. It authorizes neither
implementation nor deployment. The pre-delta Implementation Plan is invalid
authority and must be rewritten only after review confirms all acceptance
invariants, the v1/v2 compatibility policy, registry-before-adapter crash
recovery, allowed scope, prospective-only rule and strict 1.5G boundary.
