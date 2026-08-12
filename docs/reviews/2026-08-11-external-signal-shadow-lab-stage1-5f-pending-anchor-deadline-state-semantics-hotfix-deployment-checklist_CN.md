# Stage 1.5F Pending Anchor Deadline State Semantics Hotfix 部署验证清单

```text
status = deployment_checklist_approved
hotfix_scope = stage1_5f_pending_anchor_deadline_state_semantics_hotfix
producer_enabled_default = false
live_trading_enabled = false
```

## A. 部署前与启动阶段只读预检 (Pre-flight Verification)

1. **新 Output Root 隔离性**：
   - 必须在全新 1.5F output root 目录下启动。不得修改或覆盖已有 root 目录及 `observer_state.jsonl` 文件。
2. **Stage 1.5D 输入绑定位点**：
   - 确认 Stage 1.5D `live_safety_gate_summary.json` 决策为 `stage1_5d_runtime_gate_ready` 且 `status == "READY"`。
   - 确认 `--stage1-5d-events-glob` 展开路径与其 `source_root` 完全对应同一 Stage 1.5D 根路径。
3. **安全与权限状态断言**：
   - `RISK_LIVE_TRADING_ENABLED` 为 `False`。
   - `EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED` 为 `False`。

## B. 运行期观察与验收条件 (Deployment Acceptance)

1. **未来长提前量公告 (`pending_launch_time_in_future`) 观察**：
   - 读取新 root 的 `observer_state.jsonl`，检查包含有效 future anchor 的行：
     - `status == "pending_launch_time_in_future"`
     - `anchor_resolution_deadline_ms` 为 `null`
     - `next_anchor_resolution_at_ms` 为非 `null`
     - `next_admission_check_at_ms == observation_anchor_ms + guard`
   - 当该行进入 `first_seen + 6h` 时间节点后，确认其状态**不会**变为 `rejected_launch_anchor_unavailable_timeout`，继续保持 `pending_launch_time_in_future`。
2. **取消公告 (`pending_cancelled`) 观察**：
   - 当接收到官方取消 Revision 事件后，检查对应行：
     - `status == "pending_cancelled"`
     - `pending_reason == "official_schedule_cancelled"`
     - `pending_terminal_reason == ""`
     - `observation_anchor_ms`、`next_admission_check_at_ms`、`next_anchor_resolution_at_ms` 均为 `null`
   - 确认 `live_depth_observer_summary.json` 中的 `pending_launch_observation_count` 指标不再计入该 Symbol。
3. **未决与冲突 Fail-closed 观察**：
   - 缺失 anchor 或存在 conflict 的 pending 状态，达到 6h `anchor_resolution_deadline_ms` 后必须正常进入 `rejected_launch_anchor_unavailable_timeout` 或 `rejected_anchor_conflict_unresolved_timeout`。
