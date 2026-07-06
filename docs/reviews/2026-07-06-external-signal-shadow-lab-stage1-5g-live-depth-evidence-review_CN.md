# Stage 1.5G Live Depth Evidence Review Report

**审计结论 (Decision):** `stage1_5g_depth_evidence_invalid`
**允许的下一步行动 (Allowed Next Action):** `continue_observation`
**证据范围 (Evidence Scope):** `none`
**是否允许推导家族级结论 (Event-Family Conclusion Allowed):** `False`

## 1. 安全边界审计 (Safety Boundaries)

| 安全控制项 (Safety Item) | 状态 (Status) |
| --- | --- |
| 实盘下单 (trade_signal_allowed) | `False` |
| 模拟盘下单 (paper_trading_allowed) | `False` |
| 实盘交易 (live_trading_allowed) | `False` |
| 执行引擎介入 (execution_engine_allowed) | `False` |
| Alpha判定解释 (alpha_interpretation_allowed) | `False` |
| 执行可行性确认 (execution_feasibility_claim_allowed) | `False` |

## 2. 阻断器与警告 (Blockers & Warnings)

### 阻断项 (Blockers):
- :x: `insufficient_depth_snapshot_count`


## 3. 水印审计与证据分类 (Watermark & Evidence Labels)

- **正式证据数量 (Formal announcement_and_launch_time count):** `1`
- **各证据标签统计 (Evidence label counts):**
  - `announcement_and_launch_time`: 1
  - `recovery_validation_only`: 0
  - `launch_time_only`: 0

## 4. 覆盖率与请求健康度审计 (Coverage & Request Health)

- **预估快照总数 (Expected snapshot count):** `720`
- **要求的最低快照数 (Min snapshot count required):** `684`
- **快照采样间隔 (Snapshot interval ms):** `60000 ms`
- **最大快照间隔时间 (Computed max gap allowed):** `600000 ms`
- **全局请求成功率 (Global request success rate):** `1.0`
- **单币最低请求成功率 (Per-symbol min request success rate):** `1.0`

## 5. 裸快照完整性审计 (Raw Snapshot Integrity)

- 未计算 (Not evaluated)

## 6. 深度与滑点审计 (Depth & Slippage Quality)

- 未计算 (Not evaluated)

## 7. 风险与局限性声明 (Risks & Limitations)

> [!IMPORTANT]
> 本审计所用到的 1-minute 静态深度/滑点，仅仅代表 Polling 采样时刻的静态订单簿数据截面（static lower-bound proxy），不能代表实盘高频爆拉或砸盘撮合下的真实 execution 可行性与深度。
> 本阶段依然严禁进行任何形式的实盘/模拟盘交易，或下达任何执行信号。

