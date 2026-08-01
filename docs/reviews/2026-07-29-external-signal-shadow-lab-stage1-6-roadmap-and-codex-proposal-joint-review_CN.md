# Stage 1.6 事件源路线重构与 Codex 建议双 Agent 联合评审意见书

> **文档状态**：已完成联合评审 (Review Approved with Required Fixes)  
> **评审日期**：2026-07-29  
> **评审对象**：`docs/strategy_specs/2026-07-28-codex对新事件源的一些建议.md` 及 Stage 1.6 路线重构方案  
> **最终结论**：**条件通过 (Approved with Required Fixes)**。同意路线图剪枝与优先级重排；**严禁**对现有 `src/` 代码库进行任何架构重构；**坚决驳回** Codex 建议中的学术化过度工程 (7 维匹配控制组) 与虚构控制面语言 (自动 Block / Risk Budget=0)。

---

## 一、 评审结论与决策总纲

经过双 Agent 对 Codex 提案与项目实际运行快照 (`current-project-state_CN.md` 及 `configs/base.py`) 的交叉硬审计，做出如下终审裁定：

```yaml
overall_decision: approve_roadmap_realignment_with_hard_boundary_fixes

# 1. 代码库架构状态
codebase_status: healthy_no_refactoring_needed
tests_pass_rate: "100% (995/995 clean pass)"
vps_daemons_status: "continuous_running (PID 88580 / 88770)"

# 2. 路线剪枝裁定
stage1_6a_delisting: approved_as_p0_source_audit_only  # 仅作为 P0 数据源审计候选
stage1_6r_security: approved_as_p1_shadow_diagnostic    # 仅作为 P1 只读影子诊断网关
1_6b_etf_flow: quick_screen_timebox_4d_max               # 4 天硬时间盒快筛，失败即关
spot_listing_pipeline: killed                             # 现货上线：彻底放弃
complex_social_volume: killed                             # 复杂社交音量：彻底放弃
unlock_replay: frozen                                     # 代币解锁 Replay：冻结
prediction_market: downgraded_to_qualitative              # 预测市场：降级为定性宏观
governance_quant: downgraded_to_event_driven             # 治理量化：降级为事件驱动阅读

# 3. 核心风控禁令 (Hard Rules)
matched_controls_in_v1: forbidden                         # 严禁在 V1 设计中包含 7 维匹配控制组
auto_execution_control_in_1_6r: forbidden                 # 严禁在 1.6R 中包含任何自动 Block/撤单语言
composite_scoring_in_filters: forbidden                   # 严禁生成多因子复合加权打分
```

---

## 二、 P0 级致命缺陷与硬性整改要求 (Hard Stop Blockers)

### P0-1. 坚决剔除“Matched Controls（匹配控制组）”作为 1.6A 必答通过门槛
- **现象 (Finding)**：Codex §2.2 要求构建包含市值、7d/30d 动量、成交量衰减、Spread/Depth、Funding/OI、BTC Regime、挂牌覆盖面等 7 个维度的“精准匹配控制组 (Matched Controls)”。
- **工程证据 (Evidence)**：
  - 加密货币期货下架事件样本量极稀疏（每年仅低两位数）。
  - 在 7 个协变量维度强行做倾向得分匹配，匹配后的控制组有效样本量必然近乎为零 ($\text{Sample Size} \approx 0$)。
- **潜在风险 (Risk)**：将简单的 Source Audit 异化为无法完成的因果推断论文，导致 1.6A 永远无法通过 Source-Audit Gate，或被迫用极其稀疏的匹配制造伪稳健结论。
- **整改要求 (Required Fix)**：
  - **1.6A V1 设计中严禁将 Matched Controls 写进通过条件**。
  - V1 仅允许基础的 `same-symbol pre-trend` 与 `BTC regime` 基线对比。Matched Controls 降级为可选诊断项，且仅在历史样本总数满足统计显著性后方可独立开项。

### P0-2. 严格清除 1.6R 中“自动 Block / Risk Budget = 0 / 自动撤单”的虚构控制面语言
- **现象 (Finding)**：Codex §3.1 将 1.6R 描述为“允许自动禁止 Affected Scope 新开仓、自动将 Risk Budget 置零、自动阻止新挂单”。
- **工程证据 (Evidence)**：
  - 项目当前硬状态为 `RISK_LIVE_TRADING_ENABLED = False`，所有模块 `trade_signal_allowed = False`。
  - 系统当前没有任何运行中的 Live 策略，也没有任何可被“阻止”的自动挂单生成链路。
- **潜在风险 (Risk)**：在一个不存在的控制面上引入可执行控制语言，会污染研究证据（把只读研究 Flag 混淆为控制动作），若后续误接入执行层，将严重违反“安全传感器而非执行器”的 L0 安全铁律。
- **整改要求 (Required Fix)**：
  - **1.6R V1 输出必须 100% 为只读诊断字段**（`confirmed_status`, `confirmed_at_ms`, `affected_assets`, `risk_veto_flag`）。
  - 严禁出现任何 `auto-block`, `auto-cancel`, `risk-budget-zero` 等可执行控制语言。

### P0-3. 严禁使用未验证的假设作为工程硬约束
- **现象 (Finding)**：Codex 多处使用未验证的假设来反向约束工程（如强制要求 5 状态机恢复、强制要求 Residualization + Walk-Forward + Ablation 三连击后才能讨论合并）。
- **整改要求 (Required Fix)**：
  - 任何写入 Design 的工程约束必须且只能追溯至：
    1. `configs/base.py` 中已有的全局常量；
    2. 已通过 Review 的 Stage 1.5 正式契约；
    3. 明确标注为 `hypothesis_only` 且绝不阻塞 Source-Audit Pass 的研究项。

---

## 三、 P1 级缺陷与 Schema / 流程调整规范

### P1-1. 1.6A Timetable Schema 字段分层（拒绝一次性铺满）
- **整改规范**：
  - **V1 必选 Schema（数据源审计硬门槛）**：
    - `available_at_ms`: 详情页保守可用时间
    - `settlement_time_ms`: 结算锁定时间
    - `order_restriction_start_ms`: 限制开仓（如 Reduce-only）生效时间
    - `product_scope`: 影响范围 (`contract_only` vs `token_wide`)
    - `margin_family`: 合约类型 (`USD_M` vs `COIN_M`)
    - `historical_futures_existence`: 历史期货市场真实存在性校验
  - **V2+ 可选 Schema（仅作诊断，缺失绝不阻塞通过）**：
    - `insurance_fund_final_hour_policy`, `ioc_liquidation_policy`, `adl_possible` 等非结构化 PR 文本免责条款。允许为 `unknown`。

### P1-2. 1.6R 冷却状态机极简化（否定 80% 盘口恢复等 Magic Thresholds）
- **整改规范**：
  - 否定 Codex 提出的 `depth recovery > 80%` 与多 Venue 差价恢复指标（当前无多 Venue 盘口流与链上 Finality 监控 API）。
  - 1.6R V1 状态机严格限定为四态：`UNCONFIRMED | CONFIRMED | FALSE_ALARM | MANUAL_CLEARED`。
  - 解除警报仅依赖人工记录 + 官方公告确认时间。

### P1-3. 1.6B (ETF Flow) Quick Screen 增加硬性时间盒 (Timebox)
- **整改规范**：
  - ETF Flow (1.6B) 与 交易所头寸 (1.6F) 保持数据源 Adapter 物理隔离（采纳 Codex 建议）。
  - 若启动 1.6B Quick Screen，必须设定硬性 Timebox（$\le 4$ 个工作日）。若数据源不可靠或没有显著信号，直接删除 Adapter，做到**零工程债务**。
  - 在单因子 Source Audit 未通过前，严禁讨论 Composite Uplift 或 Ablation 复杂流水线。

### P1-4. 1.6E 与 1.6G 辅助过滤器规则
- **整改规范**：
  - **1.6E (杠杆通道)**：保持 Delayed，直到 Extreme Funding 策略出现完整的 Shadow Cycle 运行证据前，不开启设计。
  - **1.6G (情绪/Trends)**：仅作人工日志登记 (Manual Journal)，不建立任何代码 Adapter 或 Context Dict 输出。
  - **彻底禁止**在任何模块中生成形如 `0.5 * margin + 0.3 * F&G + 0.2 * Trends` 的复合加权分。

### P1-5. 术语对齐与纠偏
- **整改规范**：
  - Roadmap 及所有 Spec 文档中，Extreme Funding、Trend/Liquidation、Long-Horizon Basis 统一标注为：
    ```text
    [既有策略观察线 / Observation-Only Strategy Research]
    ```
  - 严禁任何文档将其误写为 `Active` 或 `Validated` 策略。

---

## 四、 P2 级次要优化与范围控制

1. **先验调低 vs 策略设计隔离**：
   - 认可“降低对即时方向 Alpha 的先验期待”，但不得将其解读为“可以提前编写做空策略”。方向性研究必须在 Source Audit 完全 Pass 之后单独立项。
2. **剪枝路线落 definitive 状态**：
   - **Spot Listing (1.6H)**：Status 修改为 `killed`（仅留 Stage 1.5 既有期货上线数据作 Negative Control）。
   - **Complex Social Volume**：Status 修改为 `killed`。
   - **Unlock Replay (1.6D)**：Status 修改为 `frozen`（分配 2~4 小时评估 Point-in-time 数据，若无低成本数据源立即停止）。
   - **Prediction Market (1.6C)**：Status 修改为 `downgraded_qualitative`。
   - **Governance Quant (1.6I)**：Status 修改为 `downgraded_event_driven`。

---

## 五、 项目代码库与架构健康度复盘 (Fact Check)

针对“重构后的整体路线架构”是否意味着要改动当前代码库的疑问，进行硬事实复盘：

```text
[当前项目真实代码与运行事实]
1. 核心执行器: src/execution/order_executor.py (355 行，纯粹单对双腿，完全冻结，绝不动刀)
2. 研究模块: src/research/external_signal_shadow/ (Stage 1.5D/1.5F/1.5G 模块化清晰，高内聚低耦合)
3. 测试套件: 995/995 (100% 全绿 Clean Pass)
4. VPS 进程: PID 88580 (1.5D 采集) 与 PID 88770 (1.5F 深度观察) 连续稳定运行 > 7 天
```

- **结论**：**当前 Python 代码库非常健康，完全不需要任何代码重构或目录重构**。
- Codex 文档中所说的“重构”，100% 是指 **Roadmap 路线图上的研究课题裁剪与重新对齐 (Research Roadmap Realignment)**，对 `src/` 代码没有一丝一毫的侵入性。

---

## 六、 下一步行动指南 (Actionable Next Steps)

1. **继续保持 VPS PID 88580 与 PID 88770 连续运行**，持续积累 Stage 1.5G 盘口 Clean 证据。
2. **撰写 Stage 1.6A 设计文档**：
   - 目标路径：`docs/designs/2026-07-29-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`
   - **严禁事项**：严禁包含 Matched Controls、12+ PR 文本布尔开关、做空逻辑、仓位计算及 Order Executor 接口。
   - **必答事项**：仅回答官方数据源稳定性、USD-M/COIN-M 隔离、6 个核心硬时间戳保守提取、历史期货市场真实存在性校验以及 Kill Criteria。
