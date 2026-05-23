# crypto-alpha-lab — 路线图与决策记录（中文译本）

**创建时间：** 2026-05-23（Created：创建日期）  
**对话记录：** ID `1833b66a-1d4e-455c-aedd-1d6b8cb9b9ea`（Conversation ID：对话标识）  
**AI 代理必读：** 每次会话开始先读本文件，它是上下文桥。（context bridge：上下文桥接文件）

---

## 背景：为什么离开旧系统（Background：迁移原因）

前身项目 `my-bitcoin-project` 在工程上可靠，但在策略层面被卡死。（technically sound：工程可靠）
最近一次观测窗口的关键证据：

| 指标（Signal） | 数值（Value） | 含义（Meaning） |
|---|---:|---|
| `carry_builder_total` | 1030 | Builder 有足够数据可处理（Builder：候选构建阶段） |
| `carry_engine_reject` | 1000（97%） | **所有候选的期限结构斜率 `slope = 0.000`**（term structure slope：期限结构斜率） |
| `mr_builder_reject` | 1030（100%） | 全部被拒：`history_insufficient`（history：历史样本不足） |
| `medium_conviction_mr_total` | 0 | 该桶完全空（medium conviction：中等置信度） |

**根因（Root cause：根因）**
- **carry_core**：BTC 永续进入低 carry 状态（期限结构趋平）。过滤器是正确的，不是坏了；市场不付费时，工程再好也没用。（flat term structure：期限结构趋平）
- **mr_core**：OKX 现货拉取超时导致 60 样本历史无法累积；系统对端点连续性要求过高，而端点并不可靠。（endpoint fragility：端点脆弱）

**决策（Decision：决策）**：停止围绕“死掉的 Alpha”继续堆工程。旧系统擅长解释“为什么不交易”，新系统必须从“更好的 Alpha 假设”出发。（alpha hypothesis：Alpha 假设）

---

## 新项目使命（Mission：我们要做什么）

**不是**套利系统。  
**不是**收益机器。  
**是**：个人 Alpha 验证实验室 + 安全执行底座。（safe execution base：安全执行底座）

资金规模假设：**5,000 – 50,000 USDT**（capital scale：资金规模）。  
第一阶段（30 天）：**只做观测与影子模拟，不做实盘。**（shadow simulation：影子模拟）

---

## 架构决策（Architecture Decisions：关键架构选择）

### 执行层：原样迁移（Execution Layer: Verbatim Migration）

`src/execution/` 从旧项目 **原样迁移**（只改 import 路径）。（verbatim：逐字/原样）

**原因（Why：原因）**：`order_executor.py`（355 行）覆盖了 7 条真实失败路径：
1. Maker 超时 → 通过 `client_order_id` 走 `UNKNOWN_REMOTE_STATE` 恢复（maker timeout：挂单超时）
2. 成交后净边际 ≤ 0 → 立即回滚（net edge：净边际）
3. 对冲腿异常 → 回滚 maker 腿（hedge leg：对冲腿）
4. 对冲腿部分成交超过 dust 阈值 → 条件回滚（dust threshold：最小可忽略成交）
5. `abort_on_partial_fill` → 回滚并标记 `FAILED_SAFE`（abort：中止）
6. 重复 `intent_id` → 直接拒绝，不重放（intent_id：意图 ID）
7. `FORCE_DELEVERAGING` 锁 → 只允许 `reduce_only` 意图（force deleveraging：强平去杠杆）

任何“简化执行层”的行为都会把旧项目已经修过的 bug 重新造出来。**禁止简化执行层。**（do not simplify：不要简化）

### 策略接口：`SignalCandidate`（Strategy Interface：统一候选结构）

所有策略必须返回 `SignalCandidate`（定义在 `src/strategies/base.py`）。（SignalCandidate：统一信号候选结构）
策略不得输出裸 dict，也不得直接调用执行层。（no raw dicts：不允许裸字典）

### 配置：单一事实源（Configuration：Single Source of Truth）

所有阈值写在 `configs/base.py`；`src/` 中不允许魔法数字。（magic numbers：魔法数字）
修改阈值必须改同一个文件，且可审计。（auditable：可审计）

### 开源参考（Open-Source References：只借鉴不依赖）

| 项目（Project） | 借鉴点（What to Reference） | 禁止项（What NOT to do） |
|---|---|---|
| Freqtrade | 策略生命周期（entry+exit+stop 一体） | 不作为依赖集成（no dependency：不引入依赖） |
| Jesse | 策略代码风格（clean style） | 只读风格，不做框架迁移（not a framework：不是框架迁移） |
| Hummingbot | Connector 概念（我们已有执行层实现） | 不替换我们的执行层（do not replace：不要替换） |
| NautilusTrader | 事件驱动架构的思想 | Phase 1 不引入依赖（Phase 1：第一阶段） |

---

## 策略规格（Strategy Specifications：三条主线）

### 1. Extreme Funding Event Scanner（优先级 1）

**假设（Hypothesis：假设）**：当资金费年化超过约 30% 时，在 1–3 次结算窗口内收取资金费，扣除基差波动与成本后仍可能为正期望。（expected value：期望值）

| 参数（Parameter） | 值（Value） | 来源（Source） |
|---|---:|---|
| 最小年化 | 30% | `EXTREME_FUNDING_ANNUALIZED_THRESHOLD_PCT`（annualized threshold：年化阈值） |
| 最小持续性 | 0.70 | `EXTREME_FUNDING_MIN_PERSISTENCE`（persistence：持续性） |
| 最大持仓 | 24 小时 | `EXTREME_FUNDING_MAX_HOLDING_HOURS`（max holding：最大持仓） |
| 单笔最大仓位 | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT`（position size：单笔仓位） |
| 最大并发 | 2 | `RISK_MAX_CONCURRENT_POSITIONS`（concurrency：并发） |

**触发条件（Trigger condition：触发条件）**：年化 > 30% 且持续性 > 0.70 且基差没有“提前吸收”超额资金费（必须做反吸收检查）。（basis absorption：基差吸收）

**失效条件（Invalidation：失效）**：年化跌破 15% 或基差扩张超过累计资金费收入。（basis expansion：基差扩张）

**出场（Exit：出场）**：下一次结算若费率衰减到阈值以下则退出；或到达最大持仓边界时退出。（settlement：结算）

**影子验证目标（Shadow target：影子目标）**：30 天窗口内，至少达到“每 7 天 1 次”合格信号。（signal frequency：信号频率）

---

### 2. Trend / Liquidation Regime Scanner（优先级 2）

**假设（Hypothesis：假设）**：波动突破或清算级联之后，方向性动量在短周期内具有正期望。注意：这不是中性套利，而是明确的方向性策略。（directional：方向性）

| 参数（Parameter） | 值（Value） | 来源（Source） |
|---|---:|---|
| 波动突破倍数 | 相对 30d 基线 2.0× | `TREND_REGIME_VOL_BREAKOUT_MULTIPLIER`（vol breakout：波动突破） |
| 最大持仓 | 48 小时 | `TREND_REGIME_MAX_HOLDING_HOURS`（max holding：最大持仓） |
| 止损 | 入场价下 2.0% | `TREND_REGIME_STOP_LOSS_PCT`（stop-loss：止损） |
| 单笔最大仓位 | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT`（position size：单笔仓位） |

**触发条件（Trigger：触发）**：1h 波动率 > 2× 30d 基线，并由 OI 变化确认方向（OI 上升=动量，OI 下降=清算级联）。（OI：Open Interest，未平仓量）

**失效条件（Invalidation：失效）**：触发止损；或价格回穿入场区域；或超过持仓上限。（time stop：时间止损）

**出场（Exit：出场）**：止损或时间边界；Phase 2 可选加入移动止盈。（trailing stop：移动止盈）

**影子验证目标（Shadow target：影子目标）**：至少 5 个信号，且扣除 20 bps 往返成本后净边际 > 0。（round-trip cost：往返成本）

---

### 3. Long-Horizon Funding Basis Desk（优先级 3）

**假设（Hypothesis：假设）**：当资金费处于“中等 carry 稳定区间”（年化 10–25%，持续性 > 0.6）时，3–7 天的 delta-neutral 持仓能积累足够资金费来覆盖常见的基差波动。（delta-neutral：Delta 中性）

**与旧 carry_core 的关键区别（Key distinction：关键区别）**：不要求实时期限结构斜率为正；要求的是持仓周期内“累积资金费”足够稳定。（term slope：期限结构斜率）

| 参数（Parameter） | 值（Value） | 来源（Source） |
|---|---:|---|
| 最大持仓 | 7 天 | `BASIS_DESK_MAX_HOLDING_DAYS`（max holding：最大持仓） |
| 基差回撤停机 | 累计资金费收入的 50% | `BASIS_DESK_BASIS_DRAWDOWN_HALT_RATIO`（halt ratio：停机比例） |
| 最小持续性 | 0.60 | `BASIS_DESK_MIN_FUNDING_PERSISTENCE`（persistence：持续性） |
| 最小 Maker 成交率 | 70%（影子监控） | `BASIS_DESK_MIN_MAKER_FILL_RATE`（Maker fill rate：挂单成交率） |
| 单笔最大仓位 | 500 USDT | `RISK_MAX_SINGLE_POSITION_USDT`（position size：单笔仓位） |

**关键风险 1：趋势行情中的基差扩张**。BTC 若单日 +10%，永续溢价（基差）会扩张；多日持仓会承受未实现亏损。每 8h 结算后的基差回撤检查不可省略。（basis expansion：基差扩张）

**关键风险 2：Funding Flip**。若资金费在持仓中途翻负，delta-neutral 组合会变成“付费”而不是“收租”，必须立刻退出。（Funding Flip：资金费翻转）

**触发条件（Trigger：触发）**：年化在 10–25% 且持续性 > 0.60 且 30 天基差波动率 σ < 0.3%。（σ：标准差）

**失效/出场条件（Exit：出场，8h 检查一次）**：
- 累计基差亏损 > 累计资金费收入的 50% → 退出（drawdown halt：回撤停机）
- 资金费翻负 → 退出（funding flip exit：翻负退出）
- 持仓 > 7 天 → 强制退出或明确续仓决策（renewal decision：续仓决策）

**影子验证目标（Shadow target：影子目标）**：
- Day 21–25：只做数据建模，建立基差历史库，完成 8h Funding Flip 检测器测试。（data modeling：数据建模）
- Day 26–30：只有当观测期持续性 > 0.6 才启动影子持仓模拟。（gating：门控）
- 必须验证：影子执行中 Maker 成交率 > 70%。（Maker fill rate：挂单成交率）

---

## 30 天冲刺计划（Sprint Plan：节奏与门槛）

| 天数 | 阶段 | 交付物 | 进入下一阶段的门槛 |
|---|---|---|---|
| 1–3 | Setup | `make test` 100% 通过；`make smoke` 通过。 | 全绿（all green：全绿） |
| 4–10 | Extreme Funding（观测） | 扫描器产出日志；不执行。 | ≥1 合格信号 / 7 天 |
| 11–20 | Trend Regime（影子） | 影子模拟运行；扣费后期望值 > 0。 | ≥5 信号且正期望 |
| 21–25 | Basis Desk（数据） | 基差历史库完成；Funding Flip 检测器测试通过。 | 数据干净且触发正确 |
| 26–30 | Basis Desk（影子） | 影子持仓模拟；监控 Maker 成交率。 | 成交率 > 70% |
| 31+ | 实盘前评审 | 8 点清单（见下）。 | 8 点全部满足 |

---

## 实盘前 8 点清单（Pre-Live Checklist：必须全部满足）

真钱之前，必须满足以下 8 条：

- [ ] 信号频率 ≥ 每周 1 次（样本量足够）（signal frequency：信号频率）
- [ ] 扣除真实成本后的净边际 > 30 bps（不是纸面）。（net edge：净边际）
- [ ] 可执行容量 ≥ 计划仓位的 2×（通过深度验证）。（capacity：容量）
- [ ] 最大不利滑点 ≤ 10 bps（实测，不是估计）。（slippage：滑点）
- [ ] 最大持仓周期有硬上限（不能无限等）。（hard upper bound：硬上限）
- [ ] 模拟最大回撤 ≤ 总资本的 5%。（max drawdown：最大回撤）
- [ ] 信号出现时交易所充提状态正常（跨场地策略必须）。（withdraw/deposit：充提）
- [ ] `InventoryGuard` 与 `RiskLimits` 在边界场景模拟中能正确触发。（guards：风控护栏）

---

## 明确不迁移的内容（Not Migrated：刻意不搬的东西）

| 组件（Component） | 原因（Reason） |
|---|---|
| `carry_core` / `tactical_carry` 引擎 | 被期限结构趋平卡死，属于市场结构问题而非代码问题。（flat term structure：期限结构趋平） |
| `mr_core` / `medium_conviction_mr` | 被数据链路脆弱性卡死（OKX 超时）。（data pipeline fragility：数据链路脆弱） |
| `nextgen_paper_runtime/` | 诊断包装层，不产生 Alpha。（diagnostic wrapper：诊断包装） |
| `screening/`, `router/`, `buckets/` | 为另一套设计哲学服务的治理表面（不适配本项目）。（governance surface：治理表面） |
| `shadow_mode/` | 被“策略级 shadow simulation”替代。（strategy-level shadow：策略级影子） |
| Phase 4.5、bucket allocator、carry builder | 历史复杂度，缺乏前向价值。（historical complexity：历史复杂度） |

