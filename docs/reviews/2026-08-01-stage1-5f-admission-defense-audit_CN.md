# Stage 1.5F Admission Defense 审计

## Scope
- files_reviewed:
  - `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py`
  - `src/research/external_signal_shadow/stage1_5f_live_depth_observer_loader.py`
  - `src/research/external_signal_shadow/stage1_5f_live_depth_observer_state.py`
  - `src/research/external_signal_shadow/stage1_5f_live_depth_observer_models.py`
  - `src/research/external_signal_shadow/stage1_5f_live_depth_observer_storage.py`
  - `tests/scripts/external_signal_shadow/test_run_stage1_5f_live_depth_observer.py`
  - `tests/research/external_signal_shadow/test_stage1_5f_live_depth_observer_loader.py`
- focus: 审计 Stage 1.5F 准入防御（Admission Defense）逻辑，排查是否存在将未验证/缺失上线时间锚点（Launch Anchor）的 1.5D 事件过早判定为 `symbol_not_in_exchangeinfo` 终态拒绝（Terminal Reject），导致后续币种在 Binance `exchangeInfo` 实际上线后也彻底无法恢复的致命缺陷；重点针对 `GRVTUSDT` 提前发布误杀事故进行代码级归因。

## Admission Decision Matrix

| input_condition | current_behavior | terminal_state_written | recoverable_after_exchangeinfo_visible | expected_behavior | risk |
|---|---|---|---|---|---|
| **1. 缺失上线时间锚点 + 币种尚未上架** (`observation_anchor_ms is None` 且 `symbol not in exchangeinfo`) | 在 `loader.py` L810 执行 `symbol not in symbols_in_exchange` 判定，**早于**后续的 `observation_anchor_ms is None` 校验。直接返回 `("rejected", "symbol_not_in_exchangeinfo")`。 | **Yes** (`status="rejected"`, `terminal_reason="symbol_not_in_exchangeinfo"` 写入 `observer_state.jsonl` 与 `events_rejected/*.jsonl`) | **False (100% 无法恢复)**。后续轮询因命中 `terminal_revision_seen` 直接抑制。 | 应判定为 `"pending"` 状态（`pending_launch_anchor_missing`），并在重试窗口内等待 1.5D 补充正文 Payload 或由 1.5F 重新解析锚点，**禁止直接 Terminal Reject**。 | **CRITICAL (GRVT 事故核心原因)** |
| **2. 上线时间锚点在未来 + 币种尚未上架** (`now_ms < launch_anchor_ms` 且 `symbol not in exchangeinfo`) | 同样在 `loader.py` L810 先触发 `symbol not in exchangeinfo` 校验，直接返回 `("rejected", "symbol_not_in_exchangeinfo")`。 | **Yes** (`status="rejected"`) | **False (无法恢复)**。 | 应进入 `pending_launch_time_in_future` 挂起状态，在 `now_ms < launch_anchor_ms` 期间跳过 `exchangeInfo` 上架校验，保留至开盘时刻。 | **CRITICAL** |
| **3. 上线时间锚点在过去 + 币种尚未上架** (`now_ms >= launch_anchor_ms + guard` 且 `symbol not in exchangeinfo`) | 返回 `("rejected", "symbol_not_in_exchangeinfo")`。 | **Yes** (`status="rejected"`) | **False**。 | 开盘时刻过后若交易所仍未上架，判定为合法终态拒绝。 | **LOW (预期正常行为)** |
| **4. 1.5D 未验证/候选 Symbol + 币种尚未上架** (`symbol_validation_status != "validated"` 且 `symbol not in exchangeinfo`) | 返回 `("rejected", "symbol_not_in_exchangeinfo")`。 | **Yes** (`status="rejected"`) | **False (无法恢复)**。 | 应保持在 `pending` 状态等待 1.5D 产出 validated 事件修订版本。 | **HIGH** |

## Terminal Rejection Paths

在 Stage 1.5F 中，写终态拒绝（Terminal Rejection）的代码路径与影响分析如下：

| reason | file/function | trigger | writes_observer_state | duplicate_suppression_effect | safe_or_bug |
|---|---|---|---|---|---|
| `symbol_not_in_exchangeinfo` | `stage1_5f_live_depth_observer_loader.py` / `classify_event_symbol_eligibility_with_diagnostics` (L810) | 当交易所 `exchangeInfo` 当前币种集合中未找到 `symbol` 时触发。此时**尚未检查事件的开盘时间锚点**。 | **Yes** (`status="rejected"`, `terminal_status="rejected"`, `terminal_reason="symbol_not_in_exchangeinfo"`) | **永久抑制（Permanent Suppression）**：在 `loader.py` L360 `classify_event_symbol_revision_admission` 中，由于 `existing.status == "rejected"`，后续所有同 `event_symbol_id` 或 `stable_key` 的事件更新均触发 `"terminal_revision_seen"`，完全不再重新评估。 | **BUG (GRVT 事故直接原因)** |
| `rejected_launch_anchor_age_exceeded` | `stage1_5f_live_depth_observer_loader.py` / `classify_event_symbol_eligibility_with_diagnostics` (L842) | 事件开盘时间已过去超过 `EXTERNAL_SIGNAL_STAGE1_5F_MAX_RECOVERY_START_DELAY_MS` (24h)。 | **Yes** (`status="rejected"`) | 永久抑制。 | **SAFE (超时合法丢弃)** |
| `rejected_launch_anchor_unavailable_timeout` | `stage1_5f_live_depth_observer_loader.py` / `re_resolve_pending_anchor` (L523) | `pending` 状态事件达到 `anchor_resolution_deadline_ms` 超时仍未解析出开盘锚点。 | **Yes** (`status="rejected"`) | 永久抑制。 | **SAFE (Pending 重试超时正常拒绝)** |
| `budget_exceeded` | `run_stage1_5f_live_depth_observer.py` / `main()` (L1003) | 深度轮询速率达到容量预算上限 (`can_start_new_observation` 返回 False)。 | **Yes** (`status="rejected"`) | **永久抑制**。将临时容量不足错误误写为 Terminal Rejected。 | **BUG (容量不足应挂起而非杀死)** |
| `wrong_event_type` | `stage1_5f_live_depth_observer_loader.py` / `classify_event_symbol_eligibility_with_diagnostics` (L780) | `event_type != "futures_contract_launch"`。 | **Yes** (`status="rejected"`) | 永久抑制。 | **SAFE (非目标事件类型)** |
| `pre_watermark` | `stage1_5f_live_depth_observer_loader.py` / `classify_event_symbol_eligibility_with_diagnostics` (L804) | 事件时间戳早于 Watermark。 | **No** (跳过写入 `events_rejected`，仅递增 `pre_watermark_ignored` 计数) | 由 Watermark 本身过滤。 | **SAFE** |

## GRVT Incident Mapping

根据代码审计与服务器现场日志 `_project_context/server_evidence/20260801_grvt_title_gate/`，GRVTUSDT 事故在 Stage 1.5F 侧的失效链路如下：

| step | observed_evidence | code_path | expected_behavior |
|---|---|---|---|
| **1. 公告提前发布** | Binance 于 `11:30:11 UTC` 发布 GRVTUSDT 公告，合约实际开盘时间为 `12:45:00 UTC`。 | 外部源 | 系统应准备在 12:45 UTC 启动深度观测。 |
| **2. 1.5D 无锚点发射** | `grvt_events_hits.jsonl`: 1.5D 于 `11:32:39 UTC` 发射 `GRVTUSDT` 事件，`detail_fetch_status="not_needed"`，`symbol_effective_launch_times_ms={}`。 | `run_stage1_5d_live_event_source_smoke_collector.py` L1166 | 1.5D 应携带开盘时间锚点或标注 `launch_anchor_missing`。 |
| **3. 1.5F 判定顺序颠倒** | 1.5F 于 `11:33:36 UTC` 消费事件，调用 `classify_event_symbol_eligibility_with_diagnostics`。先执行 L810 `symbol not in exchangeinfo`，此时 11:33 UTC Binance `exchangeInfo` 尚无 GRVTUSDT。 | `stage1_5f_live_depth_observer_loader.py` L810 | 应先校验开盘时间锚点。若早于开盘时间或锚点缺失，应进入 `pending` 挂起，**绝对不应查询 exchangeInfo 或触发 Hard Reject**。 |
| **4. 写 Terminal Reject** | `grvt_rejected_hits.jsonl`: 1.5F 生成 `terminal_hygiene_id`，将 `status="rejected"`, `rejected_reason="symbol_not_in_exchangeinfo"` 写入 `events_rejected/20260731.jsonl` 及 `observer_state.jsonl`。 | `run_stage1_5f_live_depth_observer.py` L1013-L1047 | 应将状态置为 `pending_launch_anchor_missing` 或 `pending_launch_time_in_future`，写入 `events_pending/` 队列。 |
| **5. 开盘后永久不可恢复** | `12:45:00 UTC` GRVTUSDT 在 Binance 交易所正式开盘。1.5F 再次轮询时，`classify_event_symbol_revision_admission` (L360) 发现 `existing.status == "rejected"`，直接返回 `"terminal_revision_seen"` 并跳过，导致 GRVTUSDT 开盘后依然处于死锁状态。 | `stage1_5f_live_depth_observer_loader.py` L360 & `run_stage1_5f_live_depth_observer.py` L846 | 12:45 UTC 时，`pending` 状态的 GRVTUSDT 应被 `re_resolve_pending_anchor` 重新激活，并在 exchangeInfo 命中后晋升为 `active`。 |

## Defense Gaps

| severity | condition | why_it_matters | proposed_behavior | required_test |
|---|---|---|---|---|
| **CRITICAL** | `classify_event_symbol_eligibility_with_diagnostics` (L810) 判定顺序颠倒 | `symbol not in exchangeinfo` 校验早于开盘时间锚点判定，导致所有提前发布的公告在开盘前全部被判定为 Terminal Reject。 | **调整判定顺序**：先解析开盘时间锚点。若 `now_ms < anchor_ms`，直接返回 `("pending", "pending_launch_time_in_future")`；若 `anchor_ms is None`，返回 `("pending", "pending_launch_anchor_missing")`。只有在 `now_ms >= anchor_ms + guard_ms` 且 exchangeInfo 查无币种时，方可返回 `("rejected", "symbol_not_in_exchangeinfo")`。 | `test_symbol_not_in_exchangeinfo_before_launch_time_returns_pending` |
| **CRITICAL** | Terminal Rejected 终态抑制机制屏蔽后续恢复 | 一旦写入 `status="rejected"`，后续所有事件修订（Revision）或轮询均被 `classify_event_symbol_revision_admission` 判定为 `terminal_revision_seen` 抑制，彻底丧失恢复能力。 | **软拒绝（Soft Reject）与硬拒绝（Hard Reject）解耦**：对于 `symbol_not_in_exchangeinfo` 或未达超时期限的拒绝，允许在 `pending` 重试队列中定期重新评估 exchangeInfo 可用性，或允许来自 1.5D 的有效 Revision 将其从 `pending` 中唤醒。 | `test_pending_or_soft_rejected_event_recovers_when_exchangeinfo_becomes_available` |
| **HIGH** | `budget_exceeded` 深度观测容量超限时误写 `rejected` 终态 (L1003) | 遇到临时 API 限频或容量超限时，直接将事件置为 `rejected` 杀死，导致后续容量恢复后该事件也无法观测。 | 容量超限时应返回 `status="pending"`（如 `pending_capacity_deferred`），累加 `capacity_defer_count`，保留在队列中等待下一轮尝试。 | `test_budget_exceeded_defers_to_pending_not_terminal_rejected` |

## Conclusions

### 1. `symbol_not_in_exchangeinfo` 是否应对 unvalidated 1.5D event terminal reject？
**绝对不能（100% 缺陷）**。Unvalidated 1.5D event（如缺少上线时间锚点或未进行正文校验的事件）往往在公告发布初期尚未在交易所 `exchangeInfo` 中出现。对这类事件直接触发 Terminal Reject 会导致提前发布的合法公告被永久摧毁。

### 2. 缺少 `observation_anchor_ms` 的 event 应进入 pending、diagnostic、还是 reject？
必须进入 **`pending` 状态**（具体为 `pending_launch_anchor_missing`）。
- **原因**：缺少开盘时间锚点属于“暂缺信息/未解析完成”，而非“确定性非法事件”（如 `wrong_event_type`）。进入 `pending` 状态后，系统可通过 `re_resolve_pending_anchor()` 在后续轮询中持续尝试解析正文或重新检索 BAPI，直至达到 `anchor_resolution_deadline_ms` 超时；若直接 `reject` 则导致误杀无法恢复，若置为 `diagnostic_only` 则无法追踪状态晋升。

### 3. `rejected` terminal state 是否会阻止后续 revision/recovery？
**是的，100% 阻止且彻底不可恢复**。
- **代码死锁依据**：`stage1_5f_live_depth_observer_loader.py` Line 360 中，只要 `existing.status == "rejected"`，后续对该 `event_symbol_id` 的所有事件修订均被归类为 `terminal_revision_seen`；在 `run_stage1_5f_live_depth_observer.py` Line 846 中，代码仅递增 `duplicate_suppressed_count` 并丢弃，完全不再执行准入分类判定。

### 4. 核心修复路线划分
- must_fix_in_1_5f:
  1. **重构 `classify_event_symbol_eligibility_with_diagnostics` 判定顺序**：必须先判定 `observation_anchor_ms`。未到开盘时间或锚点缺失时，强制返回 `pending`，禁止在开盘前执行 `exchangeInfo` 硬拒绝。
  2. **将 `budget_exceeded` 改为 `pending_capacity_deferred`**，禁止因临时限频写 Terminal Reject。
  3. **修复 `re_resolve_pending_anchor` 的恢复逻辑**，确保开盘时刻到达且 exchangeInfo 可见时能顺利 Promote 为 `active`。

- can_rely_on_1_5d_fix:
  - 1.5D 侧修复（强制单 Symbol 标题发起 BAPI 详情正文抓取）可保证发往 1.5F 的事件均带有正确的 `symbol_effective_launch_times_ms`，从源头减少 `observation_anchor_ms is None` 的事件数量。

- recommended_diagnostics:
  - 在 `events_pending` 中新增 `pending_launch_time_in_future` 的诊断指标，实时监控挂起等待开盘的合约数量。

- not_in_scope:
  - 底层交易执行引擎与 `configs/base.py` 中 `RISK_LIVE_TRADING_ENABLED = False` 保持不变。
