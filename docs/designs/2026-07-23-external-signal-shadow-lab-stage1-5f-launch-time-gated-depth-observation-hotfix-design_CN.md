# Stage 1.5F Launch-Time Gated Depth Observation Hotfix Design

```text
status = design_draft
scope = stage1_5f_launch_time_gated_depth_observation_hotfix
design_owner = human_research_owner
implementation_allowed = false
implementation_plan_allowed = after_design_review_only
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

## 1. 背景

Stage 1.5F 的目标是为 Binance futures contract launch 新事件采集上线后 12h public depth evidence，用于后续 Stage 1.5G 审计。它不产生交易信号，也不证明 execution feasibility。

现有 Stage 1.5F 已经有 delayed-launch age gate / watermark hotfix：

```text
symbol_effective_launch_times_ms / symbol_onboard_times_ms 可作为 age gate 的 observation_age_base_ms；
launch_time_in_future 时事件可 pending，不应直接 age_exceeded；
detected_at_ms 早于 running watermark 但 launch time 晚于 watermark 的 delayed launch，可进入 launch_time_only 观察通道。
```

但 POPMARTUSDT 事件暴露出一个新的时间锚点问题：现有实现仍可能在 accepted 后立刻调用 `start_observation(flat_event, now_ms)`，并用 accepted time 作为 `observation_started_at_ms`。如果事件缺少 per-symbol launch/onboard metadata，1.5F 会退回 `detected_at_ms` 作为 observation age basis，并在合约真实上线前开始采集 depth。

这会把 pre-launch `{}` empty book 写进 12h 窗口，污染 availability，并使观察窗口提前结束。

## 2. POPMARTUSDT 触发证据

2026-07-23 POPMARTUSDT 新事件实测：

```text
source_article_id = fcdc949b45a644c78e341c88331a35ef
symbol = POPMARTUSDT
Stage 1.5F root = live_depth_observer_20260722T074225Z_7d_detail_retry_overdue_starvation_hotfix
```

Stage 1.5F accepted row：

```text
detected_at_ms = 1784770354224
accepted_at_ms = 1784770461958
observation_age_base_ms = 1784770354224
observation_age_basis = detected_time
live_depth_evidence_basis = announcement_and_launch_time
```

Binance exchangeInfo 实测：

```text
symbol = POPMARTUSDT
status = TRADING
contractType = TRADIFI_PERPETUAL
quoteAsset = USDT
marginAsset = USDT
onboardDate = 1784773800000
```

也就是说，1.5F 在真实 `onboardDate` 前约 55 分钟开始观察。

早期 depth 统计：

```text
total_snapshot_rows = 72
healthy_snapshot_rows = 16
empty_snapshot_rows = 56
invalid_snapshot_rows = 0
healthy_ratio = 0.2222222222
```

上线后最新 request manifest 和 parsed snapshot 已恢复正常：

```text
payload_size_bytes > 4000
http_status = 200
best_bid / best_ask present
depth_status = healthy
```

因此本次问题不是 depth endpoint 请求错 symbol，也不是 Binance 当前无盘口，而是 observation start anchor 过早。

## 3. 根因

根因是 Stage 1.5F 没有严格区分三类时间：

```text
announcement_capture_time:
  detected_at_ms / available_at_ms / source_published_at_ms
  用于证明系统是否及时看到公告。

symbol_resolution_time:
  symbol_resolved_at_ms
  用于证明 parser / retry / exchangeInfo validation 何时完成。

launch_depth_observation_anchor:
  symbol_effective_launch_times_ms[symbol] / symbol_onboard_times_ms[symbol]
  用于决定何时开始 12h depth observation。
```

当前设计实际允许：

```text
缺少 launch/onboard metadata
-> resolve_observation_age_base_ms fallback 到 detected_at_ms
-> eligibility = eligible
-> start_observation(now_ms)
-> pre-launch empty book 被写入 depth_snapshots
```

这对 delayed launch / pre-trading futures 合约是不成立的。

## 4. 设计目标

本 hotfix 的目标是把 Stage 1.5F 的 depth observation 从“公告发现后立即启动”改为“合约 launch/onboard anchor 到达后启动”，同时保证 pending 状态可持久化、可重启恢复、不会被移动 watermark 误降级。

必须实现的语义：

```text
1. detected_at_ms 只用于 announcement capture evidence。
2. symbol_effective_launch_times_ms / symbol_onboard_times_ms / 严格校验后的 exchangeInfo.onboardDate 才能作为 depth observation anchor。
3. launch/onboard time 在未来时，event-symbol 必须进入持久化 pending registry，不写 events_accepted，不采 depth，不推进 moving watermark。
4. 到达 launch/onboard time 后，才允许 promotion to accepted，并从 anchor 开始完整 12h observation。
5. depth request 的硬不变量是 fetched_at_ms >= observation_anchor_ms；不得通过 clock skew tolerance 提前采集。
6. 如果没有 launch/onboard anchor，不能退回 detected_at_ms 作为 clean observation 起点；必须 pending / recovery-only / rejected diagnostic。
7. pre-launch empty book 不应成为 clean depth evidence 的一部分。
8. evidence label 必须基于 root bootstrap watermark / first-seen frozen watermark relation，而不是 acceptance 时的 moving watermark。
9. clean start SLA 与 recovery start window 必须分离，避免晚启动样本被误判为 clean。
```

非目标：

```text
不改变 Stage 1.5D event detection 逻辑。
不改变 BAPI article detail hotfix。
不在本 hotfix 中重写 Stage 1.5G decision 阈值；只定义 1.5F 必须输出的 anchor-integrity 字段，1.5G 兼容审计可单独写 design/plan。
不把 POPMARTUSDT 旧采集结果 retroactively 改成 clean pass。
不允许 paper/live/execution/alpha/trade signal。
```

## 5. 新 Observation Admission 规则

### 5.1 时间锚点优先级与冲突处理

Stage 1.5F 必须新增明确函数，例如：

```text
resolve_depth_observation_anchor_ms(event_row, symbol, exchangeinfo_snapshot)
```

返回：

```text
(anchor_ms, anchor_basis, anchor_confidence, anchor_required_for_clean_evidence, anchor_candidates, anchor_conflict_active)
```

候选来源：

```text
1. symbol_effective_launch_times_ms[symbol]
   anchor_basis = symbol_effective_launch_time
   anchor_confidence = high

2. symbol_onboard_times_ms[symbol]
   anchor_basis = symbol_onboard_time
   anchor_confidence = high

3. exchangeInfo.current.symbols[symbol].onboardDate
   anchor_basis = exchangeinfo_current_onboard_time
   anchor_confidence = medium
   使用条件：exchangeInfo row 必须 symbol/status/contractType/quoteAsset/marginAsset 全部匹配。

4. detected_at_ms fallback
   不可用于 futures launch clean depth observation。
   只能用于 legacy diagnostics，不能写 normal events_accepted。
```

不能静默处理 anchor 候选冲突。必须输出：

```text
observation_anchor_candidates = {
  symbol_effective_launch_time: <ms_or_null>,
  symbol_onboard_time: <ms_or_null>,
  exchangeinfo_current_onboard_time: <ms_or_null>
}
observation_anchor_selected_ms
observation_anchor_disagreement_max_ms
observation_anchor_conflict_active
```

配置：

```text
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_DISAGREEMENT_MS = 60000
```

规则：

```text
候选差异 <= MAX_ANCHOR_DISAGREEMENT_MS:
  按优先级选择 anchor，并保留全部候选证据。

候选差异 > MAX_ANCHOR_DISAGREEMENT_MS:
  status = pending_anchor_conflict
  no events_accepted
  no depth request
  clean evidence forbidden
```

### 5.2 exchangeInfo onboardDate 作为 anchor 的证据边界

`exchangeInfo.current.onboardDate` 可以作为 medium-confidence anchor，但不能作为无审计强证据。必须保留：

```text
exchangeinfo_fetched_at_ms
exchangeinfo_payload_sha256
exchangeinfo_raw_payload_path
onboard_date_raw_value
status_at_anchor_resolution
contractType
quoteAsset
marginAsset
```

Clean 资格附加条件：

```text
onboardDate > 0
onboardDate 在合理时间范围内，例如 root start - 30d <= onboardDate <= now + 30d
exchangeInfo snapshot 获取时间不晚于 onboardDate + MAX_CLEAN_START_DELAY_MS
不存在更高优先级 anchor conflict
raw exchangeInfo evidence 可审计
```

否则可以进入 `recovery_validation_only`，但不得标记为 clean。

### 5.3 PENDING_TRADING / TRADING 语义

为了测量真实 first-valid-book latency，Stage 1.5F 不应等到 `status = TRADING` 后才启动。

允许：

```text
pre-anchor anchor resolution:
  status in {PENDING_TRADING, TRADING}

at/after anchor depth observation:
  status in {PENDING_TRADING, TRADING}
```

含义：到达 anchor 后，即使 exchangeInfo 仍显示 `PENDING_TRADING`，也允许开始 public depth observation。此时 anchor 后的空盘口是真实 availability evidence，不是 pre-launch contamination。

禁止：

```text
status in {SETTLING, DELIVERING, DELIVERED, BREAK, unknown/empty}
-> reject or pending diagnostics, no clean start
```

### 5.4 Eligibility 状态

Implementation plan 必须显式定义配置：

```text
EXTERNAL_SIGNAL_STAGE1_5F_CLOCK_SKEW_TOLERANCE_MS = 30000
EXTERNAL_SIGNAL_STAGE1_5F_LAUNCH_START_GUARD_MS = 0
EXTERNAL_SIGNAL_STAGE1_5F_MAX_FUTURE_LAUNCH_LEAD_MS = 1209600000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_ANCHOR_RESOLUTION_AGE_MS = 21600000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_CLEAN_START_DELAY_MS = 120000
EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS = 900000
EXTERNAL_SIGNAL_STAGE1_5F_ANCHOR_RESOLUTION_RETRY_INTERVAL_SEC = 300
```

`CLOCK_SKEW_TOLERANCE_MS` 只用于诊断本地/交易所时间偏差和 scheduling due 判定，不得允许提前请求 depth。

新的 event-symbol eligibility 结果：

```text
pending_launch_time_in_future:
  anchor_ms exists
  now_ms < anchor_ms + LAUNCH_START_GUARD_MS
  action = persist pending registry, no events_accepted, no depth request, no moving watermark update

pending_launch_anchor_missing:
  event is futures_contract_launch but no per-symbol launch/onboard anchor available
  action = persist pending registry, schedule anchor resolution retry, no events_accepted, no depth request

pending_anchor_conflict:
  anchor candidates disagree beyond MAX_ANCHOR_DISAGREEMENT_MS
  action = persist pending registry, no events_accepted, no depth request, no clean evidence

pending_observation_capacity:
  anchor reached but new observation capacity/request budget unavailable
  action = persist pending registry, defer by fair queue

eligible_clean_start:
  anchor_ms exists
  now_ms >= anchor_ms + LAUNCH_START_GUARD_MS
  now_ms - anchor_ms <= MAX_CLEAN_START_DELAY_MS
  symbol exists in exchangeInfo with allowed metadata
  request/capacity budget allows new observation

eligible_recovery_only:
  anchor_ms exists
  MAX_CLEAN_START_DELAY_MS < now_ms - anchor_ms <= MAX_RECOVERY_START_DELAY_MS
  action = can start observation, but evidence_label = recovery_validation_only

rejected_launch_anchor_age_exceeded:
  anchor_ms exists but now_ms - anchor_ms > MAX_RECOVERY_START_DELAY_MS
  action = write events_rejected with full diagnostics

rejected_launch_anchor_unavailable_timeout:
  missing anchor unresolved after first_seen_at_ms + MAX_ANCHOR_RESOLUTION_AGE_MS
  action = write non-consumable diagnostic/rejected row, no clean evidence

rejected_anchor_conflict_timeout:
  anchor conflict unresolved after first_seen_at_ms + MAX_ANCHOR_RESOLUTION_AGE_MS
  action = write non-consumable diagnostic/rejected row, no clean evidence

rejected_observation_capacity_timeout:
  capacity pending after anchor_ms + MAX_RECOVERY_START_DELAY_MS
  action = do not start late observation; write capacity timeout diagnostics
```

硬禁止：

```text
futures_contract_launch + no anchor -> detected_time eligible
futures_contract_launch + anchor in future -> events_accepted
first depth_snapshot fetched_at_ms < observation_anchor_ms
futures_contract_launch + pre-launch empty book -> clean evidence
```

## 6. Pending Registry 与 Observation State 语义

### 6.1 Pending registry

Future/missing/conflict/capacity-deferred launch event-symbol 必须进入持久化 registry。可以新增：

```text
pending_launch_observations.jsonl
```

也可以复用 `observer_state.jsonl`，但必须有明确 `status = pending_*` 状态。最小字段：

```text
event_symbol_id
status
source_article_id
stable_event_key
symbol
event_id
first_seen_at_ms
announcement_capture_time_ms
observation_anchor_ms
observation_anchor_basis
observation_anchor_confidence
observation_anchor_candidates
next_admission_check_at_ms
next_anchor_resolution_at_ms
event_payload_hash
bootstrap_watermark_max_seen_detected_at_ms
admission_watermark_at_first_seen_ms
announcement_capture_post_bootstrap_watermark
launch_anchor_post_bootstrap_watermark
capacity_defer_count
anchor_resolution_started_at_ms
anchor_resolution_deadline_ms
last_anchor_resolution_at_ms
anchor_resolution_attempt_count
last_anchor_resolution_sources
pending_terminal_reason
acceptance_id
acceptance_state
observer_state_schema_version
```

Pending registry 必须满足：

```text
survive restart
independent of 1.5D source file retention
revision-aware: 以 stable_event_symbol_key 管理 pending，新 payload 可 upsert anchor metadata 且保留 first_seen/watermark 字段
idempotent promotion: 到 anchor 后用 stable acceptance_id 保证 events_accepted/state/watermark 崩溃恢复不重复
bounded by the pending-type-specific timeout:
known future anchor uses MAX_FUTURE_LAUNCH_LEAD_MS;
missing/conflict anchor uses MAX_ANCHOR_RESOLUTION_AGE_MS;
capacity pending uses anchor_ms + MAX_RECOVERY_START_DELAY_MS
```

### 6.2 Observation state

正式 accepted 后，`observer_state.jsonl` 必须新增或固定字段。未发生的 timestamp 字段使用 `null`，legacy `0` 在读取时迁移为 `null`：

```text
observation_anchor_ms
observation_anchor_basis
observation_anchor_confidence
observation_anchor_candidates
observation_anchor_disagreement_max_ms
observation_admitted_at_ms
observation_started_at_ms
observation_window_start_ms
observation_window_end_ms
first_depth_request_at_ms
first_depth_request_latency_ms
first_healthy_snapshot_at_ms
first_valid_book_latency_ms
market_valid_book_latency_after_first_request_ms
pre_launch_depth_request_allowed = false
evidence_start_class in {clean_start, recovery_start}
```

语义：

```text
observation_anchor_ms = launch/onboard anchor。
observation_admitted_at_ms = eligibility promotion to accepted 的本地时间。
observation_started_at_ms = 实际开始采集的本地时间。
observation_window_start_ms = observation_anchor_ms。
observation_window_end_ms = observation_anchor_ms + 12h。
first_depth_request_at_ms = 第一次实际 depth HTTP attempt 的 fetched_at_ms，不依赖是否解析成 healthy snapshot。
first_depth_request_latency_ms = first_depth_request_at_ms - observation_anchor_ms。
first_healthy_snapshot_at_ms = 第一次解析成功且 healthy 的盘口时间。
first_valid_book_latency_ms = first_healthy_snapshot_at_ms - observation_anchor_ms。
market_valid_book_latency_after_first_request_ms = first_healthy_snapshot_at_ms - first_depth_request_at_ms。
```

Clean gate 应分别约束：

```text
first_depth_request_latency_ms <= MAX_CLEAN_START_DELAY_MS
first_valid_book_latency_ms <= configured_warmup_tolerance
```

### 6.3 12h denominator

完整观察窗口 denominator 必须锚定 `anchor_ms -> anchor_ms + 12h`，不能锚定 `observation_started_at_ms -> end`。

如果实际启动晚了 N 分钟，前 N 分钟应记录为 missing buckets，而不是伪造 empty book rows。

必须用固定 bucket 计算 coverage：

```text
bucket_index = floor((fetched_at_ms - observation_window_start_ms) / poll_interval_ms)
valid bucket range = 0 <= bucket_index < expected_snapshot_count
coverage_ratio = unique_snapshot_bucket_count / expected_snapshot_count
```

必须输出：

```text
expected_snapshot_count
unique_snapshot_bucket_count
duplicate_snapshot_row_count
out_of_window_snapshot_row_count
missing_snapshot_bucket_count
pre_start_expected_snapshot_count
pre_start_missing_snapshot_count
coverage_ratio
coverage_ratio_pass
clean_start_sla_pass
clean_evidence_start_allowed
scheduled_snapshot_count
attempted_snapshot_count
successful_http_snapshot_count
valid_book_snapshot_count
empty_book_snapshot_count
invalid_book_snapshot_count
```

missing buckets 必须进入完整 anchor-based denominator，但 `coverage_ratio_pass` 只按配置阈值计算；晚启动是否 clean 由 `clean_start_sla_pass` / `clean_evidence_start_allowed` 单独判定。重复 snapshot、窗口外 snapshot 不能提高 coverage。

## 7. Watermark 规则

Pending launch event-symbol 不得推进 moving watermark：

```text
pending_launch_time_in_future -> no moving watermark update
pending_launch_anchor_missing -> no moving watermark update
pending_anchor_conflict -> no moving watermark update
pending_observation_capacity -> no moving watermark update
```

但 evidence label 不能使用运行中的 moving watermark，因为 pending 期间其他事件可能推进 `max_seen_detected_at_ms`。必须冻结 root bootstrap 关系：

```text
bootstrap_watermark_max_seen_detected_at_ms
admission_watermark_at_first_seen_ms
announcement_capture_post_bootstrap_watermark
launch_anchor_post_bootstrap_watermark
```

Evidence label 只基于 `bootstrap_watermark_max_seen_detected_at_ms` 和 first-seen frozen fields，不基于 acceptance 时的 moving watermark。

只有正式 accepted 或明确 rejected 的 event-symbol 才能更新对应 seen identity。但 `max_seen_detected_at_ms` 不得因为 delayed launch older detected event 回退。

Delayed launch 的去重必须依赖：

```text
event_symbol_id
source_article_id
stable_event_key
observer_state existing status
pending registry existing status
```

不得仅依赖 `detected_at_ms`。

Promotion 必须有 stable `acceptance_id`，并能在 restart 时修复以下 crash windows：

```text
accepted row 已写但 active state 缺失 -> 恢复 active state
active state 已写但 accepted row 缺失 -> 回补 accepted row
accepted/state 都存在 -> 不重复写 accepted
```


## 8. Evidence Label 边界

### 8.1 announcement_and_launch_time

允许条件：

```text
announcement_capture_post_bootstrap_watermark = true
launch_anchor_post_bootstrap_watermark = true
anchor_basis in {symbol_effective_launch_time, symbol_onboard_time, exchangeinfo_current_onboard_time}
anchor_conflict_active = false
evidence_start_class = clean_start
first_depth_request_at_ms >= observation_anchor_ms
first_depth_request_latency_ms <= MAX_CLEAN_START_DELAY_MS
```

含义：公告捕获和上线盘口观察都发生在 root bootstrap watermark 之后，且观察没有晚启动到 recovery。

### 8.2 launch_time_only

允许条件：

```text
announcement_capture_post_bootstrap_watermark = false
launch_anchor_post_bootstrap_watermark = true
source/event identity not seen before first-seen registry
anchor_conflict_active = false
evidence_start_class = clean_start
```

含义：只能证明上线盘口观察，不能证明公告捕获链路。

### 8.3 recovery_validation_only

任一条件成立即降级：

```text
observation anchor 缺失
observation anchor 来自 detected_at_ms fallback
anchor_conflict_active = true
pre-launch depth rows 已进入窗口
旧 root / 旧代码采集结果
manual replay / manual repair
late start: now_ms - anchor_ms > MAX_CLEAN_START_DELAY_MS
exchangeInfo onboardDate evidence 不满足 clean 附加条件
```

这类结果不得进入 clean 1.5G evidence。

## 9. POPMARTUSDT 历史样本处理

本次 POPMARTUSDT legacy evidence 不能被 retroactively 改写为 clean pass。

允许用途：

```text
1. 作为 1.5F launch-time gated observation hotfix 的真实触发证据。
2. 作为 1.5G invalid/quarantine 候选案例，但最终状态必须重新计算。
3. 验证上线后 depth endpoint 和 symbol-key manifest 正常。
```

禁止用途：

```text
clean_depth_evidence_pass
announcement_and_launch_time clean evidence
execution_feasibility_claim
paper/live trading readiness
```

POPMARTUSDT 最终状态不能预设为 quarantine pass。它必须基于 post-anchor coverage、有效 bucket 数和 legacy-evidence 规则重新计算：

```text
legacy evidence is not clean
final status = invalid or quarantined, depending on post-anchor coverage and 1.5G legacy-evidence rules
不能删除前 55 分钟后把剩余约 11h 当作完整 12h clean observation
```

## 10. 与 Stage 1.5D / BAPI Hotfix 的关系

BAPI hotfix 解决的是：support detail 202 empty 时，1.5D 是否能从 official article body 获取 symbol 和 launch schedule。

本 1.5F hotfix 解决的是：1.5F 是否必须等 launch/onboard anchor 后再启动 depth observation。

二者互补，不冲突：

```text
1.5D BAPI detail source
-> emits symbol_effective_launch_times_ms / symbol_onboard_times_ms when available
-> 1.5F launch-time gate consumes those anchors
-> future anchor enters persisted pending registry
-> starts depth observation only at/after anchor
```

如果 1.5D 没有提供 anchor，1.5F 可以使用当前 exchangeInfo 的 `onboardDate` 作为 medium-confidence anchor，但必须记录完整 exchangeInfo raw evidence 和 confidence。它不能绕过 exchangeInfo metadata validation，也不能自动等同 high-confidence detail-confirmed schedule。

## 11. Stage 1.5G 兼容边界

本 design 不直接改变 Stage 1.5G 阈值和 final decision 逻辑，避免 hotfix 范围扩大。

Stage 1.5F 必须先输出足够字段，让后续 1.5G anchor-integrity audit 可以单独实现：

```text
observation_started_before_launch_anchor_count
pre_launch_empty_book_row_count
observation_window_start_basis
first_depth_request_latency_ms
first_valid_book_latency_ms
market_valid_book_latency_after_first_request_ms
book_availability_after_launch_anchor_ratio
pre_start_missing_snapshot_count
```

如果要让 1.5G 使用这些字段作为 clean gate，必须另写或扩展 plan，至少覆盖：

```text
legacy root compatibility
decision migration
clean/quarantine/invalid 分层
POPMARTUSDT legacy regression
```

在 1.5G 兼容更新完成前，1.5F 新字段只能作为审计输出，不得单独声称 clean evidence。

## 12. Implementation Plan 前置要求

写 implementation plan 前必须确认：

```text
1. 当前 POPMARTUSDT 1.5F root 已跑完或已明确停止作为 clean evidence。
2. 不在正在运行的 1.5F root 上热替换代码。
3. BAPI hotfix 与本 hotfix 可同批部署，但必须使用新 root。
4. 旧 root 只作为 review/evidence artifact，不作为新代码恢复输入。
5. plan 必须把 pending registry、bootstrap watermark frozen fields、anchor conflict、clean/recovery start SLA 写成第一批测试。
```

建议 plan 文件：

```text
docs/plans/2026-07-23-external-signal-shadow-lab-stage1-5f-launch-time-gated-depth-observation-hotfix-plan_CN.md
```

## 13. 测试要求

必须新增测试：

```text
test_launch_time_in_future_does_not_start_observation_or_write_accepted
test_pending_launch_time_does_not_update_moving_watermark
test_pending_event_evidence_label_uses_bootstrap_watermark_not_current_watermark
test_future_launch_pending_survives_restart
test_pending_event_promotes_once_at_anchor
test_pending_event_remains_recoverable_after_global_watermark_advances
test_observation_starts_at_launch_anchor_not_detected_time
test_first_depth_request_is_never_before_anchor
test_missing_launch_anchor_does_not_fallback_to_detected_time_for_clean_observation
test_anchor_missing_retries_exchangeinfo_resolution_and_times_out
test_anchor_conflict_blocks_clean_observation
test_exchangeinfo_onboard_date_can_supply_medium_confidence_anchor_with_raw_evidence
test_pending_trading_at_anchor_allows_depth_observation
test_late_start_keeps_full_anchor_based_expected_snapshot_denominator
test_missing_pre_start_buckets_are_not_materialized_as_fake_empty_books
test_capacity_pending_remains_pending_while_active_slot_occupied
test_capacity_pending_promotes_if_slot_frees_before_recovery_deadline
test_capacity_pending_rejects_when_recovery_deadline_expires
test_capacity_failure_never_becomes_market_liquidity_failure
test_pre_launch_empty_books_are_excluded_from_clean_window_and_reported
test_popmart_regression_detected_before_onboard_does_not_clean_pass
test_existing_spcx_delayed_launch_watermark_behavior_still_passes
```

Runner-level 测试必须验证：

```text
1. 未来 launch event poll 1: pending registry written, no events_accepted, no depth_snapshots, no moving watermark update。
2. restart: pending registry reloads and remains eligible for future admission。
3. moving watermark advances due to another event: pending event keeps frozen bootstrap evidence label fields。
4. launch time poll: exactly one events_accepted row written, depth request starts。
5. observer_state observation_window_start_ms equals onboard/launch anchor。
6. request_manifest first depth_snapshot fetched_at_ms >= anchor_ms。
7. late collector start keeps full 12h expected denominator and records missing pre-start buckets。
```

## 14. 部署策略

部署必须等当前 POPMARTUSDT 旧 root 观察结束或被明确废弃后再做。

推荐顺序：

```text
1. 当前 root 跑完 12h，或明确停止并标记该 root 不参与 clean evidence。
2. 运行 1.5G / manual audit，记录 POPMARTUSDT legacy 结论。
3. 提交 BAPI hotfix + launch-time gate hotfix。
4. rsync 到服务器。
5. kill 旧 1.5D/1.5F tmux。
6. 用新 root suffix 启动：
   live_event_source_continuous_*_7d_bapi_detail_and_launch_time_gate_hotfix
   live_depth_observer_*_7d_bapi_detail_and_launch_time_gate_hotfix
7. bootstrap 新 1.5F watermark。
8. 等待下一次 futures launch event。
```

不得：

```text
复用旧 root
手工合并旧 depth snapshots
把 POPMARTUSDT legacy run 改成 clean pass
在 active observation 中途重启 1.5F
提前 anchor 请求 depth
```

## 15. Done Definition

本 design 通过后的 implementation 必须满足：

```text
1. futures launch event without launch/onboard anchor cannot start clean depth observation from detected_at_ms。
2. future launch anchor stays persisted pending without accepted/rejected pollution and survives restart。
3. evidence label uses bootstrap/first-seen frozen watermark relation, not moving watermark at acceptance time。
4. launch/onboard anchor reached 后才开始 12h observation。
5. first depth request fetched_at_ms >= observation_anchor_ms。
6. clean start SLA and recovery start window are separate；late start can only be recovery_validation_only。
7. expected snapshot denominator is anchor_ms -> anchor_ms + 12h, coverage uses unique buckets, and duplicate/out-of-window rows cannot inflate coverage。
8. observer_state 和 events_accepted 暴露 anchor basis/confidence/candidates/window start/end/start latency。
9. anchor conflicts block clean observation instead of silent priority selection。
10. exchangeInfo onboardDate medium-confidence anchor keeps raw payload/hash/path/status evidence。
11. simultaneous multi-symbol launch has bounded capacity service, fair defer diagnostics, and capacity timeout cannot become market-liquidity failure。
12. POPMARTUSDT regression prevents pre-launch empty book contamination from clean pass。
13. all safety flags remain false。
14. 1.5D BAPI hotfix tests and 1.5F launch-time gate tests both pass。
```
