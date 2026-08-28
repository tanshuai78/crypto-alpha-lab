# Stage 1.6B Live Detail Burst Queue and Controlled Failure Terminal Delta Design

- **日期:** 2026-08-26
- **状态:** `design_approved`
- **Review Mode:** `closure_confirmation`
- **类型:** live-observation scheduler and terminal-state contract delta
- **研究路线:** Stage 1.6 = Binance USD-M Futures Delisting；Stage 1.6D = VPS live source observation and PIT provenance
- **上游权威:** `2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md`、`2026-08-21-external-signal-shadow-lab-stage1-6b-catalog-delta-storage-consumer-scope-amendment-design_CN.md`、`2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md`
- **代码基线:** `d9de951`（起草时 HEAD）
- **触发证据:** VPS root `stage1_6d_live_20260826T031333Z` 的 operator transcript；该 root 仅用于本次 failure provenance，禁止恢复、修改、删除或封签
- **门禁状态:** `implementation_plan_allowed=true`；`implementation_allowed=false`；`deployment_allowed=false`

---

## 1. Confirmed Facts

1. 既有 live observer 每个 300 秒 poll 最多发出一个 index 和一个 detail 请求；Lane A（未尝试详情）按 `(first_discovered_poll_seq, source_article_id)` 优先于 Lane B（退避重试）。`EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_FIRST_ATTEMPT_MAX_POLLS=2`。
2. 既有源码和单元测试明确规定：同一 poll 发现 3 个候选、每 poll 只尝试一个详情时，第 3 poll 在发起请求前抛出 `ObserverSLAError(detail_first_attempt_sla_exceeded)`。这不是推测的运行路径。
3. VPS operator transcript 记录该 fresh live root 在第 1 poll 从当前 Delisting catalog 发现 4 个候选；第 1、2 poll 各成功写入一个 trusted detail/revision，checkpoint 在 `poll_seq=2` 中仍有两个 `detail_attempt_count=0` 的 Lane A 候选。此状态在第 3 poll 必然触发既有 SLA error。
4. 该 root 没有 `terminal_status.json`、`storage_failure_diagnostic.json` 或 sealed export。这符合 runner 仅捕获 `Stage16BSchemaDriftError` 并写 failure terminal；`ObserverSLAError` 和 `ObserverCapacityError` 会直接传播到 CLI，tmux pane 退出。
5. fresh root 的首次 index response 可能包含官网此前发布但仍在当前 catalog 中的公告。`ArticleDiscovery.notice_lineage_first_detected_at_ms` 的现有语义是该 root 首次观察到公告的时间，不是官网 publication/release time；当前 ArticleDiscovery schema 不持久化 catalog `releaseDate`。
6. 当前 StorageGuard 已对每一次 raw/JSONL/control-plane 写入独立 admission，并为 terminal control plane 保留 1 MiB root emergency reserve、256 KiB terminal write-set peak。正常 live root 最大 256 MiB，host start free-space 门槛仍为 8 GiB。
7. `RISK_LIVE_TRADING_ENABLED=False`；Stage 1.6B/1.6D 仅使用匿名 public HTTPS source profile。它不读取市场、账户或交易 endpoint，且不能授权 PIT verdict、replay、alpha、paper trading、live trading 或 execution。

## 2. Assumptions

1. 每次 HTTP request 最长仍受冻结的 `EXTERNAL_SIGNAL_STAGE1_6B_HTTP_TIMEOUT_SEC=10.0` 约束；不改变 endpoint、headers、locale、variant、payload cap 或 source-profile attestation contract。
2. live poll 的单线程顺序 I/O 可在最多一个 index 加四个 detail 的 50 秒网络 timeout 包络内完成；每一 request 仍由既有独立 StorageGuard admission 保护，无法写入时必须终止而不是跳过或重试。
3. 现有 checkpoint v2 live roots 不含本 Delta 的 admission snapshot、deadline 与 failure-intent 字段。历史 sealed export 保持只读可验证；未终态的旧 live v2 root 不能在新调度语义下恢复。

## 3. Root Cause / Core Issue

原 contract 同时要求：

```text
one live detail request per poll
AND
every Lane A candidate receives a first detail attempt within two polls
```

当同一 index poll 新发现 3 个或更多候选时，这两个要求不可同时满足。实际 VPS root 的 4 个 catalog backlog 候选已经证明该矛盾会在正常官方响应下发生，而不是只存在于 synthetic fixture。

此外，`terminal_status.json` 被冻结为唯一终态 authority，但已知的 scheduler/capacity failure 没有写该 authority。这使一个可解释的 fail-closed outcome 表现为可 resume 的 interrupted root，违反终态边界。

本 Delta 只修复 live scheduler 的可实现性与受控 failure 的终态记录。它不把 root 首次观察误写成官网新发布，也不新增 publication-time、PIT 或 downstream research authority。

## 4. Decisions

### 4.1 Exact supersession and unchanged authority

仅对 `capture_mode=live_observed`，本 Delta 精确替代上游 2026-08-19 Design 的以下条款：

```text
OLD D-03 / Section 7.3 / INV-09:
  at most one detail request per 300-second live poll

OLD Section 7.3 / INV-10:
  one global DETAIL_FIRST_ATTEMPT_MAX_POLLS=2 deadline
```

替换为本 Delta Section 4.2--4.3 的 four-detail bounded FIFO contract。`EXTERNAL_SIGNAL_STAGE1_6B_DETAIL_FIRST_ATTEMPT_MAX_POLLS=2` 此后仅属于 `historical_backfill`；`live_observed` 不得读取它来计算、检查或映射 first-attempt deadline。上游关于每 poll 一个 index、300 秒 sleep、单进程单线程、无 intra-poll retry、无并发、request/profile validation、raw-before-record、checkpoint/reconciliation、StorageGuard、terminal-before-seal、sealed consumer、历史 backfill 及所有 safety flags 的其他条款保持不变。

本 Delta 还仅覆盖上游 2026-08-25 1.6D deployment Design 的同-root resume 条款：缺少 v3 admission/deadline fields 的 pre-Delta live v2 root 不再是可 resume root，必须按 Section 4.4 作为 preserved interrupted evidence。v3 live root 的同 attestation/reconciliation resume contract 保持原样；complete/failure terminal 与 sealed root 一律不可 resume 的规则不变。

本 Delta 还精确覆盖上游 2026-08-21 Storage Consumer Scope Amendment 的以下原 scope restrictions：

```text
1. configs/base.py:
   add exactly EXTERNAL_SIGNAL_STAGE1_6B_LIVE_MAX_DETAIL_REQUESTS_PER_POLL

2. ObserverCheckpoint/reconciler:
   add capture-mode-scoped live v3 writer, reader and bounded-tail reconstruction

3. live terminal producer:
   add the controlled-failure intent/checkpoint/terminal sequence in Section 4.5

4. load_sealed_export():
   add only the capture-mode-scoped v3 live acceptance matrix in Section 4.4
```

该 Amendment 的 StorageGuard formulas、root accounting algebra、lock ownership、seal/export atomicity、artifact hashing、historical v2 producer/consumer rules及其余 scope restrictions 均保持不变。

### 4.2 Live request budget

新增唯一 SSOT config：

```text
EXTERNAL_SIGNAL_STAGE1_6B_LIVE_MAX_DETAIL_REQUESTS_PER_POLL = 4
```

对一个 live poll：最多一个 `LIVE_INDEX` request，随后最多四个 `LIVE_DETAIL` requests。详情必须逐个完成：一个 detail 的 fetch、raw persistence、DetailObservation/DetailRevision（若 trusted）和 candidate state mutation 完成后，才可选择下一个。禁止 worker pool、async、parallel HTTP、intra-poll retry、提高 index 频率或绕过每次写入的 guard。

每 poll 最多五个 public HTTPS request；在 10 秒 timeout 上限下，网络 timeout 包络为 50 秒。runner 仍在 poll 完成后 sleep 300 秒，因此这不是更高频的连续轮询。

### 4.3 FIFO Lane A service and durable deadline

Lane A 的顺序保持：

```text
(first_discovered_poll_seq, source_article_id)
```

在一个 poll 的全部新 `ArticleDiscovery` durable 写入后，先冻结该 poll admission snapshot。令 `N` 为 admission 前既有、未尝试 Lane A candidate 的数量；本 poll 新候选按 `(first_discovered_poll_seq, source_article_id)` 排序，候选 `j` 的取值从 `0` 开始。每个新 Lane A candidate 必须写入终身不可变字段：

```text
first_attempt_ahead_count_at_admission = N + j
first_attempt_deadline_poll_seq =
  first_discovered_poll_seq + floor(first_attempt_ahead_count_at_admission / 4)
```

`first_attempt_ahead_count_at_admission` 不是后续 poll 的当前队列排名；它只表达 candidate admission 时在其前方的未尝试 Lane A 数量。既有 Lane A 排在本 poll 新发现候选前；后续新候选不得改变任何既有 candidate 的两个字段或插队。字段一经赋值，在 Lane A、Lane B、trusted-detail terminal 和 terminal-detail-failure 生命周期内都不得清空、重算或覆盖。

本 poll 在 admission 后只做一次 lane snapshot selection：若 snapshot Lane A 非空，选择 FIFO 最早的最多四个 Lane A，且本 poll 不得切换至 Lane B 填充剩余 budget；若 snapshot Lane A 为空，才选择最多四个 due Lane B。该规则保留原有 Lane A precedence，避免 intra-poll lane-switch 解释空间。

在每个 poll 开始时，任何 `detail_attempt_count == 0` 且 `poll_seq > first_attempt_deadline_poll_seq` 的 candidate 都是 `detail_first_attempt_deadline_missed` controlled failure。它不是静默延迟，也不是把候选视为 trusted/terminal detail。

`EXTERNAL_SIGNAL_STAGE1_6B_MAX_PENDING_DETAIL_CANDIDATES=500` 保持硬上限。此上限下纯 Lane A 的最大 queue distance 为 `ceil(500 / 4) = 125` 个成功 live polls；不声明 wall-clock 首次请求上限，因为每 poll 还包含 HTTP、guard 与 persistence 时间。所有 root 内 `first observed` 与 `t_detail_receive_ms` 仍逐字段持久化，任何 consumer 均不得把排队延迟重写为较早的可用时间。

### 4.4 Checkpoint version and compatibility

新的 live writer 必须写：

```text
ObserverCheckpoint.schema_version = stage1_6b_observer_checkpoint_v3
CandidateState exact additional keys:
  first_attempt_ahead_count_at_admission
  first_attempt_deadline_poll_seq
ObserverCheckpoint exact additional key:
  pending_terminal_failure_reason
```

`first_attempt_ahead_count_at_admission` 在 candidate 一经 admission 后必须保持 non-null integer `>= 0`；`first_attempt_deadline_poll_seq` 必须保持 non-null positive integer。两个字段均必须满足 Section 4.3 公式，且不因 candidate 进入 Lane B 或 terminal 而清空。空 Lane A 中首个 candidate 的 exact state 为 `ahead_count=0` 且 `deadline=first_discovered_poll_seq`。`pending_terminal_failure_reason` 在 normal checkpoint 为 `null`，在 Section 4.5 的 failure-intent checkpoint 中为该 exact failure reason。所有既有 v2 keys 和语义不变。

兼容性必须按 `capture_mode` 与 root state 精确分支：

| `capture_mode` / root state | checkpoint writer | sealed loader | active resume |
|---|---|---|---|
| `historical_backfill` | v2 only | v2 only; v3 reject | unchanged historical rule |
| `live_observed`, pre-Delta sealed evidence | no writer | v2 accepted read-only | N/A |
| `live_observed`, post-Delta fresh root/export | v3 only | v3 accepted only after v3 validation | v3 reconciliation only |
| `live_observed`, pre-Delta unsealed v2 root | no writer | not consumable | reject |
| `live_observed`, v3 root with non-null `pending_terminal_failure_reason` | no writer after failure intent | not consumable | reject |

reader 必须按显式 schema/capture-mode branch 读取；禁止字段猜测、alias 或把缺少 deadline 的 v2 active root 当作 v3 resume input。所有 pre-Delta、unsealed live v2 root 包括本次 `stage1_6d_live_20260826T031333Z` 都是 legacy interrupted evidence：保留、不可 resume、不可 seal。新 deployment 只可用 fresh v3 root 与 fresh target-local attestation。

### 4.5 Controlled failure terminal

`terminal_status.json` schema 继续为 `stage1_6b_terminal_status_v1`，其 exact keys 不变。新增并冻结 live failure `terminal_reason` 值：

```text
detail_first_attempt_deadline_missed
pending_detail_candidate_capacity_exceeded
storage_exhausted
```

runner 必须将以下已知异常映射为唯一 failure terminal，并以 non-zero exit 结束：

| Exception class + exact code | `terminal_reason` | Seal / resume |
|---|---|---|
| `Stage16BSchemaDriftError` | `source_profile_schema_drift` | no seal; no resume |
| `ObserverSLAError.code == detail_first_attempt_deadline_missed` | `detail_first_attempt_deadline_missed` | no seal; no resume |
| `ObserverCapacityError` | `pending_detail_candidate_capacity_exceeded` | no seal; no resume |
| `Stage16BStorageBlocked` | `storage_exhausted` | no seal; no resume |

同名 exception class 的其它 code 不得映射为本表 reason；它们非零退出且不写 false terminal reason，直到另有 Design 定义。`ObserverSLAError` 必须持久化可比较的 `.code`，不得从 human-readable message 猜测。

受控 failure 路径的顺序为：停止网络 admission -> 尝试写 v3 failure-intent checkpoint（`pending_terminal_failure_reason` 非 null） -> 独立尝试以 terminal-control-plane reserve 写 `terminal_status.json` -> non-zero exit。若 failure-intent checkpoint 成功，terminal 的现有 `final_checkpoint_id` 必须引用该 checkpoint ID；若其失败，terminal 必须引用最后一个已提交 normal checkpoint ID，或在不存在该 checkpoint 时为 `null`。failure-intent checkpoint 是 ordinary control plane，不是 terminal authority，不可 seal，也不可被 consumer 当作 completion；它只证明 terminal write 之前已进入某个已知 controlled failure。failure-intent checkpoint admission 失败不得阻止 terminal-control-plane reserve 的独立尝试。

若 terminal 成功写入，root 是 failure terminal，且无论 failure-intent checkpoint 是否成功均不可 seal 或 resume。若 terminal 因 guard 或 I/O 无法写入但 failure-intent checkpoint 已成功，root 是 `interrupted_nonresumable`，因为 resume reader 必须拒绝 non-null `pending_terminal_failure_reason`。仅当 failure-intent checkpoint 与 terminal 都无法写入时，root 才保留为一般 interrupted evidence，并仅可按 v3 bounded-tail reconstruction contract 判断是否可 resume。未知程序异常、SIGKILL、host crash 和 operator cancellation 不在本 Delta 中改写为 failure terminal，仍按既有 interrupted-root 规则处理。

### 4.6 V3 bounded-tail reconstruction before resume

v3 resume 必须从最后一个 v3 checkpoint 与至多一个未完成 poll 的 durable tail 重建唯一调度状态，然后才允许下一次 HTTP request。reconstruction 不得使用当前队列位置或 wall-clock 重新分配 deadline。

```text
input = last committed v3 checkpoint C(p-1)
      + authoritative durable tails for poll p

1. Validate every tail row physically in `record_seq` order against its exact schema,
   run_id, poll_seq, monotonic request sequence, stream offset/hash and raw-byte linkage.
   `record_seq` is stream-integrity/replay evidence only, never queue-admission order.
2. Collect valid ArticleDiscovery tail rows that are newly admitted; reject duplicate
   source_article_id or a row already present in C(p-1).candidate_states.
3. Canonically sort that new-candidate set only by
   `(first_discovered_poll_seq, source_article_id)`. Let `N` be C(p-1)'s
   unattempted Lane A count, then recompute every immutable ahead_count/deadline
   with the exact Section 4.3 formula in that canonical order.
4. Replay DetailObservation tail rows in `record_seq` order. A trusted observation
   requires exactly one same-article raw SHA/path-matching DetailRevision tail row;
   otherwise reject resume. A non-trusted observation reconstructs its existing
   Lane B retry state from the persisted observation captured_at_ms and frozen retry config.
5. Reject an orphan DetailRevision, duplicated observation identity, detail row for
   a non-admitted candidate, ambiguous raw linkage, more than one incomplete poll,
   or any reconstructed state/deadline mismatch.
6. Write exactly one v3 reconciliation checkpoint with reconstructed state and
   pending_terminal_failure_reason=null, then permit the next network request.
```

Tail reconciliation is not allowed for a root whose last v3 checkpoint has non-null `pending_terminal_failure_reason`, a v2 live root, a terminal root or a sealed root.

### 4.7 Initial catalog backlog semantics

fresh root 第一次从当前 catalog 发现的候选可以是官网较早发布但仍展示的公告。无需新增 ArticleDiscovery schema：

```text
notice_lineage_first_detected_at_ms
  = first time this live root observed the article in the attested catalog
  != official publication/release time
  != proof that the article was newly published during this poll
```

本 Delta 不读取、推断、持久化或以 catalog `releaseDate` 宣称 official freshness。future source-publication authority 需要独立 Design；本次仅保证 backlog 也能按受限队列获得可信详情或显式 failure。

## 5. Scope / Non-Goals

### In Scope

- live observer 的 four-detail sequential budget、FIFO deadline、checkpoint v3 和受控 failure terminal mapping。
- live runner 的 terminal-before-exit behavior 与对应 tests/fixtures。
- 1.6D runbook 对 v3 fresh deployment、legacy v2 incident root 禁止 resume、failure terminal inspection 的最小更新。

### Non-Goals

- 不改变历史 backfill 的一个 detail request/request-cycle contract、historical coverage、terminal reason 或 existing sealed exports。
- 不把 current catalog backlog 分类为官网新发布，不实现 releaseDate watermark、跨 epoch dedupe 或 publication-time/PIT assertion。
- 不改变 source profile、request headers、endpoint、locale、HTML/body parser、semantic reducer、Stage 1.6A/1.6C artifact 或 audit verdict。
- 不修改 Stage 1.5D/F code、roots、process、watermark、storage quota 或 deployment。
- 不增并发、worker pool、数据库、外部 queue、网络重试、价格/L2/funding/OI/fee/account API、replay、signal、paper/live trading 或 execution。
- 不恢复、删除、封签或修改 VPS incident root。

## 6. Acceptance Invariants

| ID | Invariant |
|---|---|
| INV-01 | 一个 live poll 至多一个 index 与四个顺序 detail requests；没有并发、同 poll retry 或 profile/endpoint change。 |
| INV-02 | Lane A 以 `(first_discovered_poll_seq, source_article_id)` FIFO 优先；Lane B 只能在 snapshot Lane A 为空时消费最多四个 detail budget，且不得填充 Lane A 未用预算。 |
| INV-03 | 每个 admitted candidate 的 immutable ahead-count/deadline 必须持久化于 v3 checkpoint；新候选不能改变旧候选字段或插队。 |
| INV-04 | detail first attempt 不晚于其 persisted deadline；违反时只能形成 failure terminal，不能静默延迟、漏记或标为 trusted。 |
| INV-05 | pending candidates 超过 500 时必须以 `pending_detail_candidate_capacity_exceeded` 失败；所有已写 evidence 保留，root 不 seal、不 resume。 |
| INV-06 | snapshot Lane A 非空时，本 poll 只消费最多四个 Lane A；不得以 Lane B 填充剩余 budget。 |
| INV-07 | 已知 scheduler/capacity/storage/schema failure 必须先尝试持久化 v3 failure intent，并无条件独立尝试唯一 v1 failure terminal；terminal-control-plane reserve 不得被 ordinary intent admission 阻断。 |
| INV-08 | terminal 成功即为不可 seal/resume 的 failure root；terminal 无法持久化时不得制造 summary/diagnostic 替代终态，已写 failure intent 的 root 不可 resume，intent 与 terminal 均未写入的 root 仅可走 v3 bounded-tail reconstruction。 |
| INV-09 | v2/v3 reader/writer/resume 行为必须按 capture mode 与 root state matrix 分支；缺少 v3 deadline 的 active v2 root 不得 resume。 |
| INV-10 | fresh-root first detection 仅代表本系统首次观察；不得产生 official publication、PIT、market-data、replay、alpha 或 trading authority。 |
| INV-11 | 每一新增 request/record/checkpoint/terminal 继续单独通过现有 StorageGuard；256 MiB root cap、8 GiB host admission 和 terminal reserve 不变。 |
| INV-12 | 所有 `RISK_LIVE_TRADING_ENABLED`、trade/paper/live/execution、PIT、replay、market-data 和 alpha flags 保持 `false`。 |

## 7. Producer / Writer / Loader / Consumer / Reviewer Impact Matrix

| Role | Effect | Required behavior |
|---|---|---|
| `Stage16BObserver` | Changed live producer reducer | v3 immutable admission snapshot; at most four sequential detail requests; deterministic deadline enforcement |
| live runner | Changed failure terminal writer | exact exception class/code mapping; failure-intent checkpoint before terminal; no seal after failure |
| StorageGuard | Unchanged hard authority | admits every additional detail write independently; terminal reserve remains last-write protection |
| checkpoint reconciler | Changed reader/writer | capture-mode v2/v3 dispatch; v3 bounded-tail replay before live resume |
| `load_sealed_export()` | Compatibility consumer | historical v2 only; live v2 legacy read-only or v3 post-Delta branch; never migrates or rewrites artifacts |
| historical backfill | Unchanged producer | retains existing one-detail request-cycle contract and historical completion predicate |
| Stage 1.6A/1.6C | Unchanged downstream consumers | no new source audit, PIT, market-data, replay or alpha authority |
| Stage 1.5D/F | Unchanged co-tenant writers | no import, root/state/process/config or quota change |
| 1.6D runbook | Changed operator document | starts only fresh v3 root after re-approved deployment checks |

## 8. Data / State / Temporal Contract

```text
attested live index poll
  -> persist index/ListCapture/ArticleDiscovery
  -> assign immutable v3 Lane A ahead-count + deadline
  -> select up to four FIFO Lane A details
     OR, only if Lane A empty, up to four due Lane B details
  -> persist each detail raw -> observation -> optional revision
  -> v3 checkpoint last
  -> sleep 300 seconds
```

`first_attempt_deadline_poll_seq` is scheduling evidence, not a source timestamp. Source timing remains:

```text
T_article_discovered = notice_lineage_first_detected_at_ms
T_detail_receive     = DetailObservation.t_detail_receive_ms
T_detail_trusted     = DetailRevision.t_detail_trusted_ms only after trusted detail
```

No field permits a later detail result to backdate `T_article_discovered`, or permits a first observation to be treated as official publication time.

Normal v3 checkpoint is written only after a successful poll and has `pending_terminal_failure_reason=null`. A failure-intent v3 checkpoint is the sole exceptional controlled-failure checkpoint: it may be written during an incomplete poll, has a non-null reason, does not assert poll completion, is never resumable and is never sealable. A generic interruption without a durable failure intent may resume only through Section 4.6 reconstruction. No active or failure root is a sealed-export input.

## 9. Failure Semantics / Crash / Idempotency

| Condition | Required durable result | Operator action |
|---|---|---|
| Four or fewer new Lane A candidates | all receive first attempts in same poll unless a request/write failure occurs | continue normal observation |
| More than four candidates | deterministic FIFO queue/deadlines; no candidate dropped | continue while under capacity and deadlines remain satisfiable |
| deadline miss | attempt failure intent -> independently attempt v1 failure terminal `detail_first_attempt_deadline_missed`; no seal | preserve root; fresh root only after incident decision |
| pending count > 500 | attempt failure intent -> independently attempt v1 failure terminal `pending_detail_candidate_capacity_exceeded`; no seal | preserve root; no retry by queue bypass |
| StorageGuard rejection | attempt failure intent -> independently attempt v1 failure terminal `storage_exhausted` through terminal reserve; terminal write failure after durable intent is interrupted_nonresumable | preserve root; resolve host capacity outside collector |
| schema drift | existing v1 failure terminal `source_profile_schema_drift`; no seal | preserve root; no endpoint/field alias retry |
| terminal write failure after durable failure intent | no competing terminal claim | preserve interrupted_nonresumable root; fresh root only |
| failure-intent write failure but terminal succeeds | v1 failure terminal references last normal checkpoint ID or `null`; no seal | preserve terminal root; no resume |
| SIGKILL, host crash, unknown exception, or both failure-intent and terminal write failure | no competing terminal claim | preserve interrupted root; only Section 4.6 v3 reconstruction may decide resume |

Failure terminals are terminal authority only. They do not seal, do not make a root consumable, do not repair an incomplete poll, and do not assert that all discovered candidates have terminal detail state.

## 10. Compatibility / Migration / Existing Artifact Rules

1. Existing historical sealed export bundles and any completed v2 live sealed export are immutable, read-only evidence. Their v2 checkpoint parsing remains an exact explicit branch.
2. A new v3 writer never rewrites a v2 root. It never invents missing deadline fields or aliases v2 into v3.
3. The actual VPS root `stage1_6d_live_20260826T031333Z` is a preserved v2 interrupted incident root. It must not receive `--resume`, a manual terminal, a new checkpoint or a seal after this Delta is implemented.
4. The first post-implementation deployment must use a fresh run ID/root/session and fresh target-local profile attestation. It is a new epoch, not recovery of this incident.
5. Artifact profile IDs, source profile ID, record identity formulas, raw SHA paths, terminal status schema name, sealed export schema and historical loader authority remain unchanged unless this Delta explicitly says otherwise.

## 11. Evidence and Fixture Provenance

| Evidence | Role | Limitation |
|---|---|---|
| `test_observer_lane_a_sla_exceeded_fails_closed` synthetic fixture | proves pre-Delta three-candidate contradiction | does not prove VPS source contents |
| VPS operator transcript for `stage1_6d_live_20260826T031333Z` | proves four real current-catalog candidates and poll-2 state | unsealed root is not a source-audit or PIT artifact |
| existing source profile probe attestation | proves only target profile conformance at its probe time | does not prove an announcement is newly published |
| future burst fixtures | prove v3 FIFO/deadline/failure behavior without network calls | must be explicitly marked synthetic |

No unit test may call the network. No future test may use the VPS incident root as a mutable fixture.

## 12. Safety / Authority Boundary

All of the following remain false:

```text
RISK_LIVE_TRADING_ENABLED
source_audit_passed
point_in_time_source_validated
market_data_coverage_passed
replay_allowed
trade_signal_allowed
paper_trading_allowed
live_trading_allowed
execution_engine_allowed
alpha_interpretation_allowed
```

This Delta increases bounded public detail collection only. It grants no trading or research conclusion, and it cannot convert a current catalog row into a contemporaneous official event fact.

## 13. Verification Strategy

The future implementation plan must use RED first and include at least:

1. empty Lane A first candidate persists `ahead_count=0` and `deadline=first_discovered_poll_seq`; four same-poll discoveries produce four sequential detail requests, deterministic request observation IDs, raw/observation/revision linkage and one normal v3 checkpoint;
2. five through eight same-poll discoveries receive first attempts across exactly two polls, FIFO with persisted ahead-count/deadline;
3. a ninth candidate's v3 deadline is deterministic and no candidate is silently skipped;
4. later discoveries cannot move an existing candidate's persisted ahead-count/deadline or jump FIFO order;
5. snapshot Lane A non-empty means Lane B receives zero requests in that poll; Lane B receives up to four requests only when snapshot Lane A is empty;
6. deadline miss, pending-capacity and storage block each attempt failure intent then exactly one v1 failure terminal; no sealed export and no accepted resume after a durable failure intent;
7. failure-terminal write inability leaves no substitute terminal claim; a durable failure intent rejects resume, while absent intent follows the exact v3 reconstruction branch;
8. a durable tail whose `record_seq` order differs from `(first_discovered_poll_seq, source_article_id)` reconstructs candidate state field-equivalent to normal scheduler admission; partial trusted detail linkage, duplicate identity and reconstruction mismatch reject resume;
9. fresh v3 root can reconstruct one incomplete poll from exact bounded tails without changing ahead-count/deadline; v2 sealed reader compatibility remains intact; v2 interrupted root resume is rejected;
10. failure-intent checkpoint failure still independently attempts terminal reserve; a successful terminal references the last normal checkpoint ID or `null`, while intent and terminal dual failure follows the exact v3 reconstruction branch;
11. first current-catalog discovery remains first-observed only: no publication/release/PIT/trading field is emitted or enabled;
12. each of the additional up-to-three detail writes passes StorageGuard admission; quota/reserve boundary tests remain fail-closed;
13. focused 1.6B client/models/observer/storage/runner suite, `ruff check` for touched paths, and static proof of no Stage 1.5/market/risk/execution imports.

## 14. Rollout / Rollback

```text
Design review + user approval
  -> implementation plan review + explicit implementation authorization
  -> local RED/GREEN + completion audit
  -> commit/push
  -> fresh 1.6D deployment authorization/preflight using a new v3 root
  -> one live epoch health check with four-detail budget evidence
```

Rollback is no-start or stopping the new 1.6D process while preserving its root. It never restarts, modifies, deletes or seals the incident v2 root; it never alters Stage 1.5D/F.

## 15. Open Questions

**N/A for this Delta.** The fixed budget, ordering, deadline formula, v3 compatibility rule and controlled failure mapping are frozen above. Future work on official publication-time authority, catalog watermarks, cross-epoch dedupe, dynamic rate adaptation or a larger request budget requires a separate Design.

## 16. Approval Boundary

This Design authorizes neither code modification nor VPS redeployment. It may proceed to an implementation plan only when review confirms:

1. the live-only supersession is exact and historical producer/consumer behavior is unchanged;
2. four-detail sequential budget, FIFO deadline formula and checkpoint v3 contract are mechanically implementable;
3. all enumerated controlled failures end in a single failure terminal or remain explicitly interrupted when terminal persistence itself fails;
4. v2 evidence remains immutable and the VPS incident root is not resumed;
5. no safety, PIT, market-data, replay, alpha or trading authority is widened.
