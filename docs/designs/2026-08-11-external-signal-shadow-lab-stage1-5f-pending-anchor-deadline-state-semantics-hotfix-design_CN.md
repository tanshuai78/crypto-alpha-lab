# Stage 1.5F Pending Anchor Deadline State Semantics Hotfix Design

```text
status = design_draft
scope = stage1_5f_pending_anchor_deadline_state_semantics_hotfix
design_owner = human_research_owner
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

## 1. 已确认事实

1. Stage 1.5D 已正确解析 Binance 文章 `45c2f20d589b420e80063ab75feb41f2`，并写出一个 `formal_v2_valid` 的四 Symbol launch event。每个 Symbol 都有 `launch_anchor_validation_status = valid` 和 `symbol_effective_launch_times_ms`。
2. Stage 1.5F 对四个 Symbol 的初始状态均为 `pending_launch_time_in_future`，且 `observation_anchor_ms` 非空。
3. 四个 state 最终都变为 `rejected_launch_anchor_unavailable_timeout`。其 `pending_terminal_reason` 与 status 一致，但原 `pending_reason` 仍为 `pending_launch_time_in_future`。
4. 该事件的共同 `anchor_resolution_deadline_ms` 是 `2026-08-10T15:31:36.209Z`；四个 official anchor 是 `2026-08-11T02:00:00Z` 至 `02:15:00Z`。因此 terminal transition 分别发生在 anchor 前 628 至 643 分钟。
5. 当前 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 6h`，而 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 14d`。长于 6 小时的有效公告提前量本身是允许输入。
6. `re_resolve_pending_anchor()` 当前在重新解析 anchor 前，对所有 `pending_*` state 统一检查 `anchor_resolution_deadline_ms`。因此 `pending_launch_time_in_future` 也会被“缺失 anchor”的 deadline 终态拒绝。
7. `create_pending_observation_state()` 当前为所有 pending state 初始化 `anchor_resolution_deadline_ms` 和 5 分钟 `next_anchor_resolution_at_ms`，即使该 state 已有有效 future anchor。
8. `EventSymbolState` 已能兼容缺失的 nullable deadline/schedule 字段；本次无需新增 field 或提升 state schema version。
9. 当前生产 root 已写出的 terminal state 不可安全复活；本 hotfix 只约束新 root 和新 state，不能补采已错过的盘口。

**证据边界：** 本地未保存 `45c2...` 的原始 BAPI payload。上述事实来自服务器 1.5D event 行和 1.5F durable state 行；后续回归 fixture 必须标记为 `synthetic_offline_fixture_derived_from_server_evidence`，不得伪称 `real_frozen_bapi_payload`。

## 2. 显式假设

1. 已验证的 `formal_v1_valid` 或 `formal_v2_valid` launch event，其 `observation_anchor_ms` 是当前可用的观察时点；在该时点之前，Symbol 暂未出现在 exchangeInfo 是预期状态，不构成 terminal invalidation。
2. 正式 schedule revision 的处理仍遵循既有 revision registry；本设计不改变 revision producer、revision contract 或其 default-disabled 配置。
3. Stage 1.5F 只会在自己现有的 `events` 输入、runtime gate 和 exchangeInfo public read 中做 re-resolution；本次不添加网络请求、轮询频率、CLI flag 或配置项。

## 3. 根因与核心问题

`anchor_resolution_deadline_ms` 的原始用途是限制“没有可用 anchor”或“anchor 冲突尚未解决”的无限重试。它不是整个 pending 生命周期的最大寿命。

当前 reducer 把该 deadline 放在所有 `pending_*` state 的入口处：

```text
if now >= anchor_resolution_deadline_ms:
    terminal reject
else:
    resolve anchor
```

这使一个已经有正式、有效 future anchor 的状态无法等到自己的 `next_admission_check_at_ms`。它同时违反以下两个现有语义：

```text
valid future launch lead <= EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS
pending_launch_time_in_future waits until observation_anchor_ms
```

正确 reducer 必须先基于当前 poll 可见的最新 event 行重新确定 anchor 状态，再按该状态决定是否存在 resolution deadline。

## 4. 范围与非目标

### 4.1 范围内

1. 修正 `pending_launch_time_in_future` 的 deadline 语义、初始持久化和 re-resolution 顺序。
2. 明确有效 future anchor 在 schedule revision 到达时的 point-in-time refresh、advance/postpone/cancel 行为，以及 resolved-to-unresolved deadline episode。
3. 收紧 runner 的 pending promotion predicate，禁止仅凭过期的 `observation_anchor_ms` 推进 active。
4. 保留并验证缺失 anchor、冲突 anchor、legacy unvalidated source 的现有 fail-closed timeout。
5. 覆盖新建 state、重启后的 durable state、到达 anchor 的 runner promotion，以及 4 Symbol staggered long-lead 的离线状态矩阵。
6. 更新本 hotfix 对应 deployment checklist 的观察字段和 deployment acceptance 条件。

### 4.2 显式非目标

1. 不修改 Stage 1.5D parser、formal launch contract、anchor contract v2、schedule revision producer、schedule revision registry contract 或 Git ancestry attestation。
2. 不改变 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS`、`EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS`、轮询间隔或 depth 采集阈值。
3. 不尝试复活旧 root 中已写入的 terminal states，不补写历史 snapshot。
4. 不新增 state machine framework、抽象接口、配置开关、background worker、网络 endpoint 或第三方依赖。
5. 不允许 paper trading、live trading、execution、trade signal 或 alpha interpretation。

## 5. 决策与理由

### 5.1 状态专属 deadline，而不是扩大 6 小时阈值

保留 6 小时 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS`，但其只适用于当前仍未得到有效 anchor 的状态。不得把它改为 24 小时或更大。

理由：扩大阈值会掩盖真正缺失 anchor 的输入，并使无效 pending 占用容量更久；状态专属语义同时保留 fail-closed 与正常长提前公告覆盖。

### 5.2 有效 future anchor 不保留 resolution deadline，但保留 point-in-time evidence refresh

当 source 为 `formal_v1_valid` 或 `formal_v2_valid`、无 active conflict，且 `now_ms < observation_anchor_ms + launch_start_guard`：

```text
status = pending_launch_time_in_future
observation_anchor_ms = resolved anchor
next_admission_check_at_ms = observation_anchor_ms + launch_start_guard_ms
anchor_resolution_deadline_ms = null
anchor_resolution_started_at_ms = null
next_anchor_resolution_at_ms = now_ms + existing_retry_interval_ms
pending_reason = pending_launch_time_in_future
pending_terminal_reason = ""
```

这里的 5 分钟调度不再表示“等待 anchor 被解析出来”，而是既有的 **point-in-time anchor evidence refresh**。它保留 schedule revision、exchange evidence 和已存在 event revision 的及时可见性，但绝不能重新引入 resolution deadline 或 terminal reject。`next_anchor_resolution_at_ms = null` 的方案被明确排除：它会使 future state 失去现有 runner 的定期 re-resolution 触发点。

正式 schedule revision 不得等待旧 anchor 才生效。runner 在每个 poll 中必须先消费当前可见的 revision event，调用既有 `process_schedule_revision_event()` 更新 matching state，再对 pending state 做 re-resolution/admission。revision selection 必须按既有 schedule contract 的 `available_at_ms` / stable schedule identity / registry 幂等性决定，不得用 JSONL 输入顺序或“最后一行”推断 latest。

### 5.3 re-resolution 先解析，再决定 timeout

对旧 root/旧 state 或 revision 更新带来的 pending state，`re_resolve_pending_anchor()` 必须先读取当前 poll 的最新匹配 event、重新解析 anchor 与 conflict，再执行 reducer：

```text
1. load matching latest event evidence
2. classify source contract
3. resolve current anchor and conflict state
4. if valid formal anchor and now < anchor + guard:
       normalize to pending_launch_time_in_future
       clear resolution deadline and resolution episode start
       retain point-in-time refresh schedule
5. else if valid formal anchor and now >= anchor + guard:
       pending_ready_for_admission
6. else if unresolved conflict or anchor missing:
       create or preserve one unresolved episode deadline
       enforce that exact deadline
7. else if source remains legacy/unvalidated:
       enforce legacy-source deadline
```

在同一 poll 中，最新有效 anchor evidence 优先于此前持久化的 deadline；这避免“deadline 刚到而有效更新已被读到”时误杀事件。

### 5.4 Unresolved episode deadline

本设计复用已有 `anchor_resolution_started_at_ms` 和 `anchor_resolution_deadline_ms`，不新增 state field：

```text
new unresolved episode starts when:
  - a new state first lacks an anchor; or
  - a valid state becomes missing/conflict because a newly applied,
    distinct revision_application_id says so.

on episode start:
  anchor_resolution_started_at_ms = now_ms
  anchor_resolution_deadline_ms = now_ms + MAX_ANCHOR_RESOLUTION_AGE_MS

same unresolved episode:
  preserve both fields exactly across retries, restart, and missing <-> conflict changes

unresolved -> valid formal anchor:
  clear both fields

valid -> unresolved due to a later distinct revision_application_id:
  start one new episode
```

同一 revision application 下的 missing/conflict 分类变化不得滑动或重置 deadline。只有可审计的全新 `revision_application_id` 才能开启下一次 episode；普通 5 分钟 retry 永远不得延长 deadline。

### 5.5 显式 admission gate 与 revision terminal safety

runner 只允许以下 reducer 已明确给出的状态进入 capacity/admission path：

```text
pending_ready_for_admission
eligible_clean_start
eligible_recovery_only
```

必须删除以 `observation_anchor_ms is not None and now_ms >= observation_anchor_ms` 为条件的 generic promotion。`observation_anchor_ms` 是证据字段，不是 admission authorization。

对 revision 产生的状态：

```text
rescheduled_with_new_anchor:
  update anchor, next admission time and pending_reason

postponed_without_anchor / malformed applicable schedule:
  enter unresolved episode; stale old anchor may not be used

cancelled:
  keep a non-admissible cancelled state, clear old anchor and both schedules;
  it must not re-enter generic re-resolution or active promotion

official conflict:
  enter pending_anchor_conflict with one unresolved episode;
  stale old anchor may not authorize promotion
```

### 5.6 不改变合法 terminal 的不可逆性

本次只防止错误 terminal transition；对合法的 `rejected_launch_anchor_unavailable_timeout`、`rejected_anchor_conflict_unresolved_timeout` 和已过 recovery window 的 terminal state，既有不可逆/幂等处理保持不变。

理由：恢复旧 terminal state 会改变历史证据和 watermark 语义，超出本 hotfix，且无法补回实际错过的 L2 数据。

## 6. 验收不变量

| ID | 不变量 |
| --- | --- |
| `INV-01` | 对 `formal_v1_valid` 或 `formal_v2_valid` 的有效 future anchor，`now_ms < anchor + guard` 时 status 必须为 `pending_launch_time_in_future`。 |
| `INV-02` | `pending_launch_time_in_future` 不得因 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS` 到期而进入任何 terminal status。 |
| `INV-03` | 有效 future anchor 的 durable state 必须满足 `anchor_resolution_deadline_ms is None`、`anchor_resolution_started_at_ms is None`、`next_anchor_resolution_at_ms = now + existing retry interval`，并满足 `next_admission_check_at_ms == observation_anchor_ms + launch guard`。 |
| `INV-04` | `pending_launch_anchor_missing` 在当前 poll 重新解析后仍缺少 anchor，且达到 resolution deadline 时，必须保持 `rejected_launch_anchor_unavailable_timeout`。 |
| `INV-05` | `pending_anchor_conflict` 在当前 poll 仍冲突且达到 deadline 时，必须保持 `rejected_anchor_conflict_unresolved_timeout`。 |
| `INV-06` | legacy/unvalidated source 只能使用其既有 legacy-source deadline；有效 formal anchor 不得被误归类为 legacy timeout。 |
| `INV-07` | 到达有效 anchor 后，只有 reducer 显式输出 `pending_ready_for_admission`、`eligible_clean_start` 或 `eligible_recovery_only` 才可进入 runner capacity/admission path；本次不得绕过 capacity、runtime gate 或 source validation。 |
| `INV-08` | restart 后读取的旧 `pending_launch_time_in_future` state 即使仍持有过期的 6h deadline，也必须先 re-resolve 为 deadline-null future state；到达 anchor 时仍可正常推进。 |
| `INV-09` | 多 Symbol 事件按每 Symbol 的 own anchor 独立等待/推进；本次不得改变 candidate-set all-or-none emission、watermark 或 batch registry 语义。 |
| `INV-10` | 正常 launch collection 在缺失/冲突 anchor 的 fail-closed 路径不回退，不允许无限 pending。 |
| `INV-11` | `RISK_LIVE_TRADING_ENABLED = False`、producer configured false、所有 trade/paper/live/execution/alpha flags 均保持 false。 |
| `INV-12` | unresolved episode 的 deadline 在普通 retry、restart 和同一 revision 的 missing/conflict 变化中不得滑动；valid -> later distinct revision unresolved 时才可创建一个新 deadline。 |
| `INV-13` | postpone、advance 或 cancel revision 必须在同一 poll 被消费，并在旧 anchor 到达前更新/清除 pending state 的 admission schedule；不得依赖旧 `next_admission_check_at_ms`。 |
| `INV-14` | `pending_anchor_conflict`、`pending_source_event_unvalidated`、`pending_cancelled` 或 malformed state 即使持有 stale non-null anchor 且 `now >= anchor`，也不得 active。 |
| `INV-15` | 每次 normalisation 必须令 `status`、`pending_reason` 和 `pending_terminal_reason` 语义一致；future/missing/conflict state 不得保留旧 terminal reason。 |

## 7. 数据、状态与时间契约

### 7.1 状态矩阵

| 输入状态 | 当前解析结果 | deadline 语义 | 输出状态 | 下次调度 |
| --- | --- | --- | --- | --- |
| `pending_launch_anchor_missing` | anchor 缺失 | `anchor_resolution_deadline_ms` 有效 | pending 或 timeout terminal | 5 分钟 re-resolution |
| `pending_anchor_conflict` | conflict 仍 active | `anchor_resolution_deadline_ms` 有效 | pending 或 conflict terminal | 5 分钟 re-resolution |
| `pending_source_event_unvalidated` | source 仍 legacy/unvalidated | `legacy_source_revision_wait_deadline_ms` 有效 | pending 或 legacy terminal | 既有 retry 调度 |
| 任意 pending | valid formal future anchor | resolution deadline 不适用 | `pending_launch_time_in_future` | 5 分钟 evidence refresh；`anchor + guard` admission check |
| `pending_launch_time_in_future` | `now >= anchor + guard` | resolution deadline 不适用 | `pending_ready_for_admission` | immediate admission |
| `pending_ready_for_admission` | 容量/运行 gate 可用 | N/A | active | existing depth polling |
| `pending_ready_for_admission` | 容量不足 | existing capacity policy | existing pending capacity behavior | existing capacity check |
| valid future -> revision missing/conflict | valid anchor 被新的适用 revision 覆盖 | 新建一个 unresolved episode | missing/conflict pending | 5 分钟 re-resolution |
| pending future -> cancelled revision | 官方取消 | resolution deadline 不适用 | non-admissible `pending_cancelled` | 无 generic retry/admission |

### 7.2 时间定义

```text
anchor-resolution deadline
  = only unresolved anchor/conflict lifetime

admission time
  = observation_anchor_ms + EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS

recovery deadline
  = existing post-anchor exchange visibility/recovery policy

future lead validity
  = existing EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS policy
```

`anchor_resolution_deadline_ms` 不再表示 event 的总寿命，也不代表未来 anchor 的有效期。

### 7.3 Schema 与兼容性

不新增 JSON key、不提升 `observer_state_schema_version`。已有 `EventSymbolState.from_dict()` 对缺失 nullable 字段兼容。

新 root 写入的 future-anchor state 将以 `null` 保存两个 resolution-only field：`anchor_resolution_started_at_ms` 与 `anchor_resolution_deadline_ms`。`next_anchor_resolution_at_ms` 保持已有 retry interval，作为 evidence refresh，不作为 timeout 来源。

旧 root 的 pending future state 若仍持有 non-null deadline，runner 在首次 due poll 没有其他 deadline pre-check；它只会调用 `re_resolve_pending_anchor()`。该 reducer 必须先解析有效 future anchor，再归一化清空旧 episode 字段，即使 `now_ms` 已超过旧 deadline。已 terminal 的旧 state 不迁移、不复活。

## 8. Producer / Consumer 契约影响矩阵

| 组件 | 修改 | 不修改/兼容性要求 |
| --- | --- | --- |
| Stage 1.5D writer/parser | 无 | 继续提供 formal v1/v2 event 和 per-Symbol effective anchor。 |
| Stage 1.5F loader | 修改 | re-resolution 先解析再 timeout；仅 explicit admissible status 可 promotion；复用既有 schedule selection，不以 JSONL 顺序选 anchor。 |
| Stage 1.5F state writer | 修改 | 使用已有 episode 字段；future、missing/conflict、cancelled revision 分别写入正确 deadline/schedule/reason，不新增 schema。 |
| Stage 1.5F runner | 修改 | revision events 先于 pending re-evaluation 消费；删除 generic anchor-time promotion；不新增进程、worker 或轮询。 |
| Stage 1.5F summary | 无预期代码修改 | 现有 `pending_launch_time_in_future_count` 应继续反映等待状态。 |
| Stage 1.5G reviewer | 无 | 新 root 的 state 已有完整 lineage；本次不改变 review decision。 |
| schedule revision producer / Git ancestry | 无 | 默认关闭，不参与本次 reducer。 |

## 9. 异常处理、持久化与幂等性

### 9.1 Fail-closed reducer

1. exchangeInfo unavailable、runtime gate invalid 或容量不足时，沿用既有安全路径；本次不得把它们解释成有效 future anchor。
2. anchor 缺失、冲突或 source unvalidated 在相应 deadline 后仍必须 terminal，不允许无界重试。
3. 最新 event 与 pending state 的 stable event-symbol identity 不匹配时，沿用既有忽略逻辑，不能用同 Symbol 的不同文章覆盖 anchor。
4. normalisation 必须同步写入 `pending_reason`，并在 non-terminal state 清空 `pending_terminal_reason`；terminal transition 才能写 terminal reason。
5. cancelled 或 unresolved revision 不得让 stale launch row 重新成为 primary anchor；必须通过现有 schedule contract 的 point-in-time selection 选择当前适用 schedule。

### 9.2 重启

`observer_state.jsonl` 是唯一 durable state stream。重启后：

1. `pending_launch_time_in_future` 的 `next_admission_check_at_ms` 仍指向 `anchor + guard`。
2. `anchor_resolution_deadline_ms = null` 不得被 `create_pending_observation_state()` 或 reload 隐式重新填充。
3. future state 仍保留 5 分钟 evidence refresh；该 refresh 不得创建/延长 resolution deadline。
4. 首次 restart re-resolution 必须先完成 anchor classification；不存在 runner 侧先行 timeout path。

### 9.3 Crash window 与幂等性

本次不添加新文件、registry 或 watermark mutation。既有“state append 后 restart 重载 latest row”的模型保持。

若在 future-state normalisation 后、下一次 poll 前崩溃，持久化 state 已包含 anchor 和 anchor-time admission check；重启后必须得到相同状态，不得恢复 6h deadline。

## 10. 证据与 Fixture Provenance

新增一个最小 4 Symbol fixture，来源为 `45c2...` 的已保存服务器 event/state 证据：

```text
fixture_provenance = synthetic_offline_fixture_derived_from_server_evidence
source_article_id = 45c2f20d589b420e80063ab75feb41f2
symbols = KUAISHOUUSDT, MEITUANUSDT, CSOPSKHYNIX2LUSDT, CSOPSAMSUNG2LUSDT
```

fixture 只需要：归一化 formal v2 launch row、四个 per-Symbol anchor、`first_seen_at_ms`、一个超过 6h 且早于 anchor 的时钟点、以及 anchor 到达时钟点。还必须覆盖一个 point-in-time applicable revision 序列（postpone、advance、cancel 之一组最小 JSON rows）。不得伪造、引用或声称保有原始 BAPI body。

## 11. 验证策略

### 11.1 必须先失败的测试

1. 16 小时 future formal anchor，在 `first_seen + 6h + 1ms` 且仍早于 anchor 时，当前代码应错误 terminal；修补后必须仍为 `pending_launch_time_in_future`，deadline 为 null、future refresh schedule 存在、admission check 为 `anchor + guard`。
2. 4 Symbol fixture 必须分别在各自 anchor 前保持 pending，不得有任一 sibling terminal。
3. postpone revision 必须在旧 anchor 前把 admission check 移至新 anchor；advance revision 必须在新、较早 anchor 前完成更新；cancel revision 不得在旧 anchor active。
4. out-of-order event rows 不得改变 point-in-time applicable revision selection。

### 11.2 保留的防线测试

1. missing anchor 超过 deadline 仍为 `rejected_launch_anchor_unavailable_timeout`。
2. unresolved conflict 超过 deadline 仍为 `rejected_anchor_conflict_unresolved_timeout`。
3. legacy/unvalidated source 的既有 wait deadline 不变。
4. 同一 unresolved episode 的 repeated retry、restart 和 missing/conflict 变化不得延长 deadline；valid -> distinct revision unresolved 才创建一个新 deadline。
5. stale anchor 的 conflict/unvalidated/cancelled/malformed state 不得经过 runner promotion。

### 11.3 Restart 与 runner wiring

1. future state 写入 `observer_state.jsonl` 后重载，即使旧 deadline 已过，也必须在首个 due poll 归一化为 deadline-null future state。
2. 到达 anchor 后，runner 在 exchange/runtime/capacity 条件满足时写 accepted state 并开始 depth collection。
3. revision events 必须在同一 poll 的 pending re-evaluation 之前应用；advance revision 的新 anchor 不得等待旧 anchor。
4. 多 Symbol 的分别 anchor 时刻只能推进对应 Symbol；batch/watermark 行为保持现有测试断言。

### 11.4 部署验证

新 root 启动后，检查：

```text
pending_launch_time_in_future_count
pending_launch_observation_count
active_observation_count
observer_state.jsonl 的 observation_anchor_ms / next_admission_check_at_ms
```

仅在未来真实长提前公告出现并观察到：

```text
pending_launch_time_in_future -> active -> depth_snapshots
```

后，才可声明生产路径验证完成。

## 12. Rollout 与 Rollback

1. 本 hotfix 只以新 1.5F output root 部署；不修改正在运行 root 的 state 文件。
2. 新 root 必须绑定同一新 1.5D root 的 `events/*.jsonl` 和 runtime gate。
3. 若 runtime gate、summary 或 pending lifecycle 不符合本设计，停止新 root 的 admission，保留其 artifact 供审计；不得修改旧 root 或伪造状态恢复。
4. 本次若与 Git ancestry attestation 同次部署，服务器必须先满足该功能的非 shallow Git worktree 前提；该迁移是部署前提，不是本 reducer 的实现范围。

## 13. 安全与权限边界

本修补只决定 public depth observation 的等待时间。它不得：

```text
emit trade signal
claim execution feasibility
enable paper/live trading
enable execution engine
enable alpha interpretation
enable schedule revision producer
```

所有上述权限必须继续为 `false`。

## 14. 未解决问题

| 问题 | 是否阻断本次实现 | 决策 |
| --- | --- | --- |
| 服务器从 rsync-only 目录迁移为完整 Git worktree | 不阻断本地实现；阻断与 Git ancestry attestation 的合并部署 | 由下一份合并部署 checklist 明确定义，不能在本 hotfix 中隐式处理。 |
| `45c2...` 原始 BAPI payload 缺失 | 不阻断状态机修补 | fixture 明确为 server-evidence-derived synthetic；Implementation Plan Task 0 必须复核当前 workspace、保存的 server event/state artifact 和 provenance 标签。 |
| 旧 root 的已 terminal Symbol 是否应 salvage | 不阻断 | 不复活旧 state；只读离线分析另行处理。 |

### 14.1 Implementation Plan Allowed Change Scope 前提

后续 Implementation Plan 必须在顶部声明并限制为：

```text
Allowed implementation paths:
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py
  src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py
  scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py

Allowed verification paths:
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py
  tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_state.py
  tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py
  tests/fixtures/external_signal_shadow/stage1_5f/pending_anchor_deadline_state_semantics/

Allowed documentation paths:
  this design
  one new hotfix deployment checklist

Forbidden:
  configs/base.py
  Stage 1.5D parser/producer/contract code
  Git ancestry attestation code
  Stage 1.5G decision code
  producer enablement or any trading/execution permission change
```

runner 修改的唯一理由是：revision-before-pending ordering、explicit promotion gate，以及 durable state normalisation 的首轮执行路径；不得在 runner 中重写 loader 的 anchor selection。

没有会改变本次实现路径的未决问题。Design 审查通过并获得用户批准前，不得编写 implementation plan 或修改代码。
