# Crypto Alpha Lab 研究路线图与决策记录

**创建时间：** 2026-05-23
**最新状态审计点：** 2026-09-26（证据时间戳：2026-09-26T08:50:00Z）
**主状态快照文件：** [docs/project-status/current-project-state_CN.md](project-status/current-project-state_CN.md)
**有效文档索引入口：** [docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)

---

## 1. 使命与风险边界 (Mission and Risk Boundary)

`crypto-alpha-lab` 是一个个人 Alpha 验证实验室和安全执行底座，针对 **5,000 – 50,000 USDT** 的资本规模进行研究，不以自动化利润为第一目标，而是验证可重复的统计优势。

### 核心安全不变量 (Hard Safety Invariants)

* **纯只读观察（Observation First）**：所有未经验证的策略候选均严格视为研究假设，系统严格运行于影子和观测模式。
* **禁用实盘交易（Live Trading Disabled）**：[configs/base.py](../configs/base.py) 与 [src/risk/limits.py](../src/risk/limits.py) 中锁定 `RISK_LIVE_TRADING_ENABLED = False`。
* **零交易信号 / 零执行可行性声明**：全观测管线强行断言 `trade_signal_allowed = False`、`paper_trading_allowed = False`、`live_trading_allowed = False`、`execution_engine_allowed = False`、以及 `execution_feasibility_claim_allowed = False`。
* **执行层冷冻保护（Execution Layer Preservation）**：包含 355 行的双腿原子化执行层代码（[src/execution/order_executor.py](../src/execution/order_executor.py)）原样迁移并冷冻，以保留经过实盘检验的 7 条失败恢复路径（限价挂单超时、净边际校验、对冲腿异常、微量成交回滚、异常中止、重复意图拦截、去杠杆锁定）。

### Alpha 研究方法论 v1 (Alpha Research Methodology v1)

全实验室 Alpha 研究遵循 [.agent/rules/L2_Alpha_Research_Methodology.md](../.agent/rules/L2_Alpha_Research_Methodology.md)。方法论的升级**绝不放宽** L0 资金安全或证据质量要求。它将核心研究问题从“是否每个事件都赚钱？”转变为“预注册规则是否在独立机会中表现出具有可承受尾部风险的成本后正期望收益？”

核心准则：

* 单凭胜率不是 Alpha 判定通过/失败的唯一标准；赔率分布、MAE/MFE、尾部亏损、摩擦成本以及资金容量同等重要。
* 日历时长不等于统计样本量；策略结论必须使用声明的独立事件/时段单元，必要时采用聚类切分（Clustered Splits）。
* 允许存在亏损样本；但绝不允许无上限的破产路径、扣除成本后为负的期望、后视调参、无效的时点（Point-in-time, PIT）数据或经济意义可忽略的微小容量。
* `phenomenon_supported`（现象支持）、`alpha_candidate`（候选 Alpha）、`alpha_validated`（已验证 Alpha）、`evidence_insufficient`（证据不足）与 `falsified`（已证伪）为严格区分的研究状态。
* 历史已被判定为 `falsified/stopped/superseded` 的路线不会自动重启。重新复议必须经过独立的方法论审计，证明旧的否决决策主要依赖于不完整或无效的判定口径；因扣除成本后边际非正或数据无效而关停的路线，在没有真正新证据支持下维持关闭。

---

## 2. 当前位置与运行状态 (Current Position)

*(本节更新至 2026-09-26，基于 Stage 1.6F 历史研究结题与 Stage 1.5 服务器实时观察)*

* **服务器活跃进程**：
  * **Stage 1.5D 实时公告采集器**：运行进程 PID 88580（tmux `stage1_5d_continuous_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`），运行根目录为 `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`。
  * **Stage 1.5F 实时盘口观察器**：运行进程 PID 88770（tmux `stage1_5f_live_depth_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`），运行根目录为 `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`。
* **活跃验证状态**：
  * Stage 1.5D：BAPI 详情页解析与 202 异步重试调度器稳定挂载，已消除重试饥饿。
  * Stage 1.5F：Watermark Schema V2 升级完成；已统计 2643 个 Heartbeat；76 个 pre-bootstrap 历史锚点被终端 Ignore 去重。
* **Stage 1.6F 历史研究状态**：
  * **Stage 1.6F-W2 证据扩展**：`w2_candidate_run_20260925_001`；180 个物理数据对象；41 个标的 / 27 个父事件；31 个标的 / 21 个父事件窗口完整。
  * **Stage 1.6F-W2-0 终局基差探索性诊断**：`w2_0_exploratory_20260926T071500Z`；29 个标的 / 19 个父事件完成探索性描述；`outcome_seen/exploratory_only` 19-parent 子集在 [-24h, 0h] 未显示常规自然终局收敛；3/19 负向；16/19 正向。

---

## 3. 研究路线矩阵 (Research Track Matrix)

> **状态枚举口径**：`active` (正在推进), `blocked` (被阻塞), `observation_only` (仅影子观测), `completed` (已结题), `falsified` (已证伪), `stopped` (已停止), `superseded` (已被替代), `planned` (仅计划).

| 研究方向 / 阶段 | 状态 (Status) | 最新证据时间/路径 | 核心决策 (Decision) | 下一阶段关卡 (Next Gate) | 停止条件 (Kill Criteria) |
|---|---|---|---|---|---|
| **Original Carry / MR** | `stopped` | `docs/roadmap.md` (2026-05-23) | BTC 期限斜率长期趋近 0.000（平坦 Carry）；OKX 现货超时破坏 60 周期历史。 | 无（历史基线） | 期限结构斜率持续趋平 > 30 天。 |
| **Extreme Funding Scanner** | `observation_only` | `docs/roadmap.md#historical-verification--backtest-results` (2026-05-23) | 5 年历史结算费率证实 DOGE/XRP 胜率 > 64%；74 天本地订单簿因交易所 10.95% API 封顶显示为 0 信号。 | 1.5 环境下的影子扫描器守护进程。 | 30 天内年化费率 > 100% 的信号为 0。 |
| **Trend / Liquidation Scanner** | `observation_only` | [configs/base.py:L124](../configs/base.py#L124) | 波动率突破 (2.5x 30d 基准) + OI 踩踏方向性候选。硬止损 1.5%，最大持仓 12h。 | 1.5 环境下的影子模拟回放。 | 20 个信号单次净边际扣除 20 bps 成本后 $\le 0$。 |
| **Tactical Carry** | `stopped` | `docs/roadmap.md` (2026-05-23) | 在平坦期限结构下无法获利，被 Extreme Funding 和 Basis Desk 替代。 | 无 | 期限结构斜率持续为负或零。 |
| **Long-Horizon Basis Desk** | `observation_only` | [configs/base.py:L145](../configs/base.py#L145) | 多日 Carry (10-25% 费率，持仓 3-7 天)。每 8h 必须通过基差回撤 > 50% 累计资金收益的熔断校验。 | 基差 DB 与 8h Funding Flip 检测器。 | 累计基差亏损 > 50% 费率收益，或挂单成交率 < 70%。 |
| **Cross-Sectional Factor Lab** | `falsified` | `docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10) | Stage A2 CMOM 截面动量因子超额收益在扣除交易摩擦成本后未能跑赢 Cash Fallback 现金基线。 | 结题 / 历史参考。 | 因子相比现金基准的夏普提升 $\le 0$。 |
| **Stage 0 – 1.2 (Shadow Setup)** | `completed` | `docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md` (2026-06-12) | 基础设施与公共只读采集器验证通过。 | Stage 1.3 信号发现。 | 网络读取失败率 > 5%。 |
| **Stage 1.3 – 1.4E (Derivatives Stress)** | `superseded` | `docs/reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md` (2026-06-20) | 本地强平快照受交易所频控降级。转向 Stage 1.5 催化剂公告。 | 被 Stage 1.5 替代。 | 强平数据流被交易所限频。 |
| **Stage 1.5A – 1.5C1 (Catalyst Replay)** | `completed` | `data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json` (2026-06-24) | 催化剂公告在历史重放中被证实产生显著的价格响应。 | Stage 1.5D 实时采集器。 | 价格覆盖率 < 80%。 |
| **Stage 1.5D (Live Event Collector)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5d/detail_retry_scheduler_state.json` (2026-07-26) | 服务器 PID 88580 持续运行。BAPI 详情页解析器 + 202 重试调度器保持活跃。 | 保持 7 天连续稳定运行。 | 详情页重试饥饿 > 1800 秒。 |
| **Stage 1.5E (Static Execution Feasibility)** | `completed` | `data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json` (2026-06-25) | 静态订单簿审计证实可承载 500 USDT 仓位深度。 | Stage 1.5F 实时观察器。 | 深度承载力 < 500 USDT。 |
| **Stage 1.5F (Live Depth Observer)** | `active` | `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/live_depth_observer_summary.json` (2026-07-26) | 服务器 PID 88770 持续运行。上线时间闸门正常；76 个 pre-bootstrap 历史锚点终端 Ignore。 | 捕获 Clean 级 L2 订单簿盘口证据。 | 网络错误率 > 5% 或 0 心跳。 |
| **Stage 1.5G (Depth Evidence Reviewer)** | `active` | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` (2026-09-23) | 离线审查器活跃。SPCXUSD1 和 MOONSHOTUSDT 审查通过 Clean (MOONSHOTUSDT 覆盖率 99.44%，P50点差 5.85 bps)；SKHYUSDT 通过 Quarantine；POPMARTUSDT 为 invalid/quarantine candidate。事件族证据持续累积（2 Clean，1 Quarantine）。 | 在当前证据门禁下累积至少 3 个独立标的与 2 篇来源公告（当前跨 2 篇公告累积 2 个 Clean 标的）。 | 连续运行 30 天无新增 clean/quarantine-valid 样本。 |
| **Stage 1.5H (Static Read-Only Report)** | `completed` | `data/external_signal_shadow/stage1_5h/reports/20260712T043755Z/stage1_5h_static_execution_proxy_report_summary.json` (2026-07-12) | 静态只读报告生成器实现并验证完成。严格执行硬安全标识约束。 | 维持只读工具定位。 | 出现任何交易信号或执行可行性声明。 |
| **Stage 1.6A (Futures Delisting Source Schema & Grammar)** | `completed` | `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md` (2026-08-24) | 验证币安期货下架公告源、BAPI H2 版本化语法及 3 个时间戳锚点。 | Stage 1.6B 下架目录。 | 交割/结算语义不明确或缺失时间戳锚点。 |
| **Stage 1.6B (Delisting Catalog & Event Burst Queue)** | `completed` | `docs/reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md` (2026-08-22) | 规范下架目录、突发队列故障恢复及 Checkpoint 契约已完成验证。 | Stage 1.6E 标的能力审计。 | 突发负载下出现不可恢复的队列丢包。 |
| **Stage 1.6E (Market Data Observer & Capability Audit)** | `completed` | `docs/reviews/2026-09-04-external-signal-shadow-lab-stage1-6e-b-live-semantic-trigger-event-market-data-observer-completion-audit_CN.md` (2026-09-04) | 实时语义触发观察器与历史 1s kline / mark / index 标的能力审计完成。 | Stage 1.6F 匹配对照。 | Kline/mark/index 覆盖率 < 80%。 |
| **Stage 1.6F (Historical Matched Control & Evidence Expansion)** | `completed` | `w2_candidate_run_20260925_001` | 180 个物理数据对象；41 个标的 / 27 个父事件；31 个标的 / 21 个父事件窗口完整。 | 仅限结论收敛闭环 (conclusion closure only) | 校验和不匹配。 |
| **Stage 1.6F-W2-0 (Exploratory Terminal Basis Diagnostic)** | `completed` | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | 29 个标的 / 19 个父事件完成探索性描述；`outcome_seen/exploratory_only` 19-parent 子集在 [-24h, 0h] 未显示常规自然终局收敛；3/19 负向；16/19 正向。 | 当前证据无后续门禁 (`none_from_current_evidence`) | 当前证据下无进一步关卡。 |

---

## 4. 当前活跃实施链 (Current Active Chain)

### 4.1 Stage 1.5 实时催化剂观察链 (Stage 1.5 Live Catalyst Observation Chain)

```text
Stage 1.5D 实时公告采集 (Tmux PID 88580)
  ├── 轮询币安公共 Catalog API + BAPI Article 详情页解析
  └── 处理 202 异步状态的重试调度器 (detail_retry_scheduler_state.json)
        │
        ▼ (输出 events/*.jsonl)
Stage 1.5F 实时盘口观察 (Tmux PID 88770)
  ├── 上线时间闸门 (拦截早于 onboardDate 的事件)
  ├── 锚点不可变水印 v2 保护 (bootstrap_max_seen_detected_at_ms)
  └── 历史数据 Ignore 分流 (pre-bootstrap 历史锚点 -> 终端 Ignore，非 Rejection)
        │
        ▼ (输出 L2 盘口快照及 observer_state.jsonl)
Stage 1.5G 盘口质量离线审查 (Offline reviewer)
  ├── 审计 L2 快照完整度、极性交叉与开盘预热空盘口 gap 延迟
  └── 标记事件状态为: Clean Pass / Quarantine Pass / Invalid Failure
        │
        ▼
Stage 1.5H 静态只读报告生成 (Offline reporter)
  └── 依据 1.5G 结果输出只读报告，严格断言禁止一切方向性交易信号 (trade_signal_allowed = False)
```

### 4.2 Stage 1.6 下架研究与诊断链 (Stage 1.6 Delisting Research & Diagnostic Chain)

```text
Stage 1.6F W1/W2 证据扩展
  -> 180 个物理数据对象
  -> 41 个标的 / 27 个父事件；31 个标的 / 21 个父事件窗口完整
Stage 1.6F-W2-0 探索性诊断
  -> 29 个标的 / 19 个父事件完成探索性描述
  -> outcome_seen/exploratory_only 19-parent 子集在 [-24h, 0h] 未显示常规自然终局收敛
  -> 3/19 负向；16/19 正向
  -> 仅限结论收敛闭环 (conclusion closure only)
```

---

## 5. 已结题与已证伪工作 (Completed and Falsified Work)

为保证项目认知框架不受幸存者偏差干扰，在此保留已证伪分支的负结论证据：

1. **Route C1 现货价格代理 7 天实盘烟雾测试 (Route C1 Price-Only Proxy 7-Day Live Smoke Test)**：
   - 证明文件：`docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` (2026-07-05)。
   - 结论：`falsified`。7 天实盘烟雾测试显示样本重叠率高，扣除费用后净边际 $\le 0$；胜率不足仅为描述性现象，并非独立关停原因。Route C1 纯价格代理分支在 L2 框架下维持终止，因为成本后期望门禁未通过。
2. **Stage 1.4B-Lite 衍生品拥挤度反转重放 (Stage 1.4B-Lite Crowding-Only Replay)**：
   - 证明文件：`docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md` (2026-06-18)。
   - 结论：`falsified`。500 次重抽样试验表明单纯衍生品拥挤度指标无统计显著的独立 Alpha。在 Stage 1.4C 中决定转向外生催化剂公告。
3. **Cross-Sectional Factor Lab 阶段 A2 (CMOM 动量因子) (Cross-Sectional Factor Lab Stage A2 (CMOM Factor))**：
   - 证明文件：`docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md` (2026-06-10)。
   - 结论：`falsified`。截面动量 (CMOM) 因子超额收益在扣除交易成本后未能战胜 Cash Fallback 现金基准。因子实验室闭环结题。

---

## 6. 当前阻塞项 (Current Blockers)

按类别整理：

* **数据与验证阻塞 (P3 - Stage 1.5G 实时盘口深度)**：
  * **问题描述**：Stage 1.5G 虽有 2 个 Clean 通过事件（`SPCXUSD1`, `MOONSHOTUSDT`），但新合约上线事件族样本量仍需持续累积至 $\ge 3$ 个独立标的。
  * **事实证据**：Stage 1.5G 历史评审记录及连续运行心跳。
  * **解封动作**：保持 VPS 端 1.5D + 1.5F 进程持续运行并监控新上线合约。

---

## 7. 下一阶段关卡校验门槛 (Next Gates)

### 关卡 3：Stage 1.5G 事件族证据充分性校验
* **前置依赖**：Stage 1.5D 和 1.5F 持续稳定运行。
* **所需证据**：累积至少 3 个独立上线标的的 `stage1_5g_live_depth_evidence_review_summary.json`。
* **通过标准**：达到事件族样本量门槛且无致命污染。
* **拒绝/停止条件**：连续 30 天无有效新样本或数据丢失率 $> 10\%$。
* **安全边界**：观察模式 (`trade_signal_allowed = False`)。

---

## 8. 决策日志记录 (Decision Log)

* **2026-05-23**：旧 carry/MR 期限趋平且频繁超时，决策封存，转向 `crypto-alpha-lab` 新架构。建立 5k-50k USDT 资金规模假设，原子化执行层原样迁移并冻结。
* **2026-06-10**：截面动量 (CMOM) 因子测试判定无法战胜 Cash Fallback，截面因子实验室结题闭环。
* **2026-06-18**：500 次 Monte Carlo 重放证明衍生品拥挤度反转无显著净收益。在 Stage 1.4C 决策转向 Stage 1.5 外生催化剂公告。
* **2026-06-24**：批准 Stage 1.5D 实时公告采集器设计，完成 Stage 1.5C 价格覆盖扩展审计。
* **2026-06-26**：批准 Stage 1.5F 实时盘口观察器设计，服务器上部署实时 L2 深度快照采集。
* **2026-07-05**：Route C1 7 天实盘烟雾测试评估未达标，现货价格代理策略被证伪结题。
* **2026-07-12**：批准 Stage 1.5H 静态代理只读报告生成器，确立严格只读治理契约。
* **2026-07-19**：发布 Master Assessment (`2026-07-19-event_source_master_assessment.md`)。批准 Stage 1.6A (期货下架) 作为最高优先级发现路线，Stage 1.6R (安全事故) 作为 Risk-Veto 辅助路线。
* **2026-07-24**：实施并验证 Stage 1.5F 历史锚点 Rejection Hygiene 热装补丁（水印 Schema v2、终端 Ignore 分流以防污染 `events_rejected`）。
* **2026-07-26**：验证服务器 1.5D/1.5F 影子运行状态；完成项目当前状态报告（`current-project-state_CN.md`）与统一文档事实索引（`current-document-index_CN.md`）。
* **2026-08-10**：批准 Stage 1.5D/1.5F Git Ancestry Attestation 设计并完成实施计划。Producer 发出版本 2 正式调度变更事件；Consumer 兼容 `[1, 2]`；Producer 配置维持默认禁用 (`EXTERNAL_SIGNAL_STAGE1_5D_SCHEDULE_REVISION_PRODUCER_ENABLED = False`)。
* **2026-09-24**：全实验室采纳 L2 Alpha 研究方法论：Alpha 评估依据独立机会下经过预注册的成本后数学期望、稳健性、资金容量与可生存尾部风险进行；胜率/单笔确定性不再作为通用通过/失败门禁。历史证伪路线除非经过单独重新审计，否则维持关闭。
* **2026-09-25**：完成 Stage 1.6F-W2 证据扩展 (`w2_candidate_run_20260925_001`)：180 个物理数据对象；41 个标的 / 27 个父事件；31 个标的 / 21 个父事件窗口完整。
* **2026-09-26**：完成 Stage 1.6F-W2-0 终局基差探索性诊断 (`w2_0_exploratory_20260926T071500Z`)：29 个标的 / 19 个父事件完成探索性描述；`outcome_seen/exploratory_only` 19-parent 子集在 [-24h, 0h] 未显示常规自然终局收敛；3/19 负向；16/19 正向。

---

## 9. 已替代历史文档清单 (Superseded Documents)

查看所有因热装补丁升级、证伪或架构转向而被后续设计/计划替代的历史文档清单与索引，请访问：

👉 **[docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)**
