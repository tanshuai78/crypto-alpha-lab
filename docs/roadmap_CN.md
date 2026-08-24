# Crypto Alpha Lab 研究路线图与决策记录

**创建时间：** 2026-05-23
**最新状态审计点：** 2026-07-26（证据时间戳：2026-07-26T02:11:01Z）
**主状态快照文件：** [docs/project-status/current-project-state_CN.md](project-status/current-project-state_CN.md)
**有效文档索引入口：** [docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)

---

## 1. 使命与风险边界 (Mission and Risk Boundary)

`crypto-alpha-lab` 是一个个人 Alpha 验证实验室和安全执行底座，针对 **5,000 – 50,000 USDT** 的资本规模进行研究，不以自动化利润为第一目标，而是验证可重复的统计优势。

### 核心安全不变量 (Hard Safety Invariants)

* **纯只读观察**：所有未经验证的策略候选均严格视为研究假设，系统运行于影子和观测模式。
* **禁用实盘交易**：[configs/base.py](../configs/base.py) 与 [src/risk/limits.py](../src/risk/limits.py) 中锁定 `RISK_LIVE_TRADING_ENABLED = False`。
* **禁用自动化交易与模拟器解构**：全观测管线强行断言 `trade_signal_allowed = False`、`paper_trading_allowed = False`、`live_trading_allowed = False`、`execution_engine_allowed = False`、以及 `execution_feasibility_claim_allowed = False`。
* **执行层冷冻**：包含 355 行的双腿原子化执行层代码（[src/execution/order_executor.py](../src/execution/order_executor.py)）原样迁移并冷冻，以保留经过实盘检验的 7 条失败恢复路径（限价挂单超时、净边际校验、对冲腿异常、微量成交回滚、异常中止、重复意图拦截、去杠杆锁定）。

---

## 2. 当前位置与运行状态 (Current Position)

*(本节提取自 2026-07-26 服务器运行快照与状态报告 `current-project-state_CN.md`)*

* **服务器活跃进程**：
  * **Stage 1.5D 公告实时采集器**：运行进程 PID 88580（tmux `stage1_5d_continuous_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`），Output Root 路径为 `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`。
  * **Stage 1.5F 实时盘口观察器**：运行进程 PID 88770（tmux `stage1_5f_live_depth_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`），Output Root 路径为 `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`。
* **活跃验证状态**：
  * Stage 1.5D：BAPI 详情页解析与 202 异步重试调度器稳定挂载，已解决重试饥饿。
  * Stage 1.5F：Watermark Schema V2 升级完成；已统计 2643 个 Heartbeat；76 个 pre-bootstrap 历史锚点被终端 Ignore 去重。
* **当前第一阻塞项 (P1 Blocker)**：
  * Stage 1.5G 审查结果仍为 `clean_depth_evidence_pass = false`（全网尚无 0 gap 的 Clean 级 L2 深度盘口数据）。

---

## 3. 研究路线矩阵 (Research Track Matrix)

> **状态枚举口径**：`active` (正在推进), `blocked` (被阻塞), `observation_only` (仅影子观测), `completed` (已结题), `falsified` (已证伪), `stopped` (已停止), `superseded` (已被替代), `planned` (仅计划).

| 研究方向 / 阶段 | 状态 (Status) | 最新证据时间/路径 | 核心决策 (Decision) | 下一阶段关卡 (Next Gate) | 停止条件 (Kill Criteria) |
|---|---|---|---|---|---|
| **Original Carry / MR** | `stopped` | 2026-05-23 / `docs/roadmap.md` | BTC 期限斜率长期趋近 0.000，且 OKX 接口频发超时，无法交易 | 无（逻辑冷冻作为历史基线） | 期限结构斜率持续趋平 >30天 |
| **Extreme Funding** | `observation_only` | 2026-05-23 / 5年历史结算回测 | 证实 XRP/DOGE 年化 >100% 胜率 >64%，但本地 74d 数据受限幅限制为 0 信号 | 影子扫描器挂载与基差吸收检查 | 极端费率信号频率低于 1次/30d |
| **Trend / Liquidation** | `observation_only` | 2026-07-26 / [configs/base.py](../configs/base.py) | 波动率突破 (2.5x) 与未平仓量 (OI) 清算动量候选，止损 1.5% 且最大持仓 12h | 影子模式模拟回放 | 单次净边际扣除 20bps 成本后 $\le 0$ |
| **Tactical Carry** | `stopped` | 2026-05-23 / `docs/roadmap.md` | 在平坦期限结构下无法获利，被 Basis Desk 和 Extreme Funding 替代 | 无 | 期限结构斜率持续为负或零 |
| **Long-Horizon Basis** | `observation_only` | 2026-07-26 / [configs/base.py](../configs/base.py) | 多日 Delta 中性 Carry (10-25% 年化)。每 8h 必须通过基差回撤 >50% 资金收益的熔断校验 | 基差 DB 与 8h Funding Flip 检测器完成 | 累计基差亏损 > 50% 费率收益，或挂单成交率 < 70% |
| **Factor Lab** | `falsified` | 2026-06-10 / Stage A2 因子审查报告 | CMOM 截面动量因子扣除成本后无法产生超越 Cash Fallback 的稳定超额收益 | 结题并封存为历史参考 | 因子超额收益 (阿尔法) 均值 $\le 0$ |
| **Stage 0 – 1.2** | `completed` | 2026-06-12 / Stage 1.2 审查报告 | 实时只读采集管线基础验证通过 | 推进 Stage 1.3 信号发现 | 采集任务数据缺失率 > 5% |
| **Stage 1.3 – 1.4E** | `superseded` | 2026-06-20 / Stage 1.4E 审查报告 | 爆仓快照与大额委托受制于交易所频控，被 Stage 1.5 催化剂公告替代 | 转向 1.5 催化剂管线开发 | 数据完整性拦截率 > 10% |
| **Stage 1.5A – 1.5C1** | `completed` | 2026-06-24 / Stage 1.5C1 覆盖审计 | 历史重放证实公告发布后存在显著价格响应 | 推进 1.5D 采集器开发 | 价格响应延迟高于 120 秒 |
| **Stage 1.5D** | `active` | 2026-07-26 / `detail_retry_scheduler_state.json` | 进程 PID 88580 稳定运行。支持 202 状态调度与 Title/BAPI 币种覆盖 | 维持 7d 连续运行，监测异常 | 详情页重试队列死锁或超时 > 1800s |
| **Stage 1.5E** | `completed` | 2026-06-25 / 1.5E 静态深度审查 | 确认 L2 订单簿深度能稳定容纳 500 USDT 的单笔模拟仓位 | 推进 1.5F 实时盘口观察 | 可容纳深度限额 < 500 USDT |
| **Stage 1.5F** | `active` | 2026-07-26 / `live_depth_observer_summary.json` | 进程 PID 88770 稳定运行。上线时间闸门与 pre-bootstrap 终端 Ignore 去重工作正常 | 积累首个 Clean 级新币盘口证据 | 网络请求错误率 > 5% |
| **Stage 1.5G** | `blocked` | 2026-07-26 / `stage1_5g_quarantine_summary.json` | 离线审查通过 Quarantine 级 1 例 (`SKHYUSDT`)，Clean Pass 仍阻塞为 0 | 积累首个无盘口空洞的 Clean 级事件 | 无 Clean 级事件持续 > 30天 |
| **Stage 1.5H** | `completed` | 2026-07-12 / 1.5H 治理审查报告 | 静态只读报告生成器完成。锁定只读禁令标志 | 维持只读工具，防止策略越权 | 误写为执行模拟器或交易引擎 |
| **Stage 1.6 Futures Delisting** | `active_research_route` | 2026-08-24 / [路线地图](project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md) | 1.6A--C 已完成：范围契约、历史封签采集与真实语义审计；`source_audit_passed=true` | 仅推进 1.6D VPS live-source-observation deployment authorization | 未经单独授权不得部署；历史 source pass 不等于 PIT、replay 或交易许可 |

---

## 4. 当前活跃实施链 (Current Active Chain)

当前影子观察与证据收集的活跃工作流链条如下：

```text
Stage 1.5D 实时公告采集 (Tmux PID 88580)
  ├── 轮询 Catalog API + BAPI Article 详情页解析
  └── 处理 202 异步状态的重试调度器 (detail_retry_scheduler_state.json)
        │
        ▼ (输出 events/*.jsonl)
Stage 1.5F 实时盘口观察 (Tmux PID 88770)
  ├── 上线闸门拦截 (拦截早于 onboardDate 的事件)
  ├── 锚点不可变水印 v2 保护 (bootstrap_max_seen_detected_at_ms)
  └── 历史数据 Ignore Hygiene 分流 (pre-bootstrap 历史锚点 -> Ignore，非 Rejection)
        │
        ▼ (输出 120 个盘口快照及 observer_state.jsonl)
Stage 1.5G 盘口质量离线审查 (Offline reviewer)
  ├── 审计快照完整度、极性交叉、开盘空盘口 gap 延迟
  └── 标记事件状态为: Clean Pass / Quarantine Pass / Invalid Failure
        │
        ▼
Stage 1.5H 静态只读报告生成 (Offline reporter)
  └── 依据 1.5G 结果输出只读报告，禁止一切方向性可执行 Alpha 宣称
```

---

## 5. 已结题与已证伪工作 (Completed and Falsified Work)

为保证项目认知框架不受生存者偏差干扰，在此保留已证伪分支的负结论证据：

1. **Route C1 现货价格代理 7 天烟雾测试 (2026-07-05)**：
   - 证明文件：`docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md`。
   - 结论：`falsified`。实盘烟雾测试期间样本极易重叠，胜率低于基线，扣除成本后收益为负，价格代理路线结题。
2. **Stage 1.4B-Lite 衍生品拥挤度反转 (2026-06-18)**：
   - 证明文件：`docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md`。
   - 结论：`falsified`。500 次 Monte Carlo 重放重合试验证明，在控制偶然性后，单纯衍生品拥挤度反转没有产生超越随机基线的独立 Alpha，分支终止。
3. **Cross-Sectional Factor Lab 阶段 A2 (截面动量因子) (2026-06-10)**：
   - 证明文件：`docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md`。
   - 结论：`falsified`。CMOM 因子在截面溢价测试中表现极其疲软，收益被交易磨损完全侵蚀，无法跑赢 Cash Fallback 现金基线，实验室闭环结题。

---

## 6. 当前阻塞项 (Current Blockers)

* **数据与验证阻塞 (P1 Blocker)**：
  * **问题描述**：Stage 1.5G 目前积累的无 gap Clean 级盘口数据仍然为 0。
  * **事实证据**：`_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5g/stage1_5g_quarantine_summary.json:L6` (`clean_depth_evidence_pass = false`)。
  * **阻碍与风险**：在获得真正的 Clean 级盘口快照前，无法完全排除新币开盘前网络极性对报价深度完整性的干扰。
  * **解封动作**：维持服务器 1.5D 和 1.5F 7天影子程序常驻，静待下一次新币上线公告。
* **Stage 1.6D 部署授权阻塞 (P2 Blocker)**：
  * **问题描述**：Stage 1.6 Futures Delisting 已完成 1.6A--C 历史证据链，但 VPS `live_observed` 尚无运行 root，不能将历史下载时间当作 point-in-time 证据。
  * **事实证据**：[Stage 1.6 路线地图](project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md)；[1.6B deployment checklist](reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md)。
  * **解封动作**：只编写并审查 1.6D VPS live-source-observation deployment authorization；不得先启动 collector。

---

## 7. 下一阶段关卡校验门槛 (Next Gates)

### 关卡 1：Stage 1.5G 盘口 Clean Pass
* **前置依赖**：1.5D 与 1.5F 服务器观察器无间断影子运行。
* **所需证据**：审查器针对新上线币种生成 `stage1_5g_live_depth_evidence_review_summary.json`。
* **通过标准**：`clean_depth_evidence_pass = true`（空盘口快照数为 0，首快照延迟 $\le 5$ 秒，`book_availability_ratio = 100%`）。
* **拒绝/停止条件**：丢包或空快照比例 $> 10\%$，或者首包快照延迟超过 60 秒。
* **安全边界**：无交易信号生成 (`trade_signal_allowed = False`)。

### 关卡 2：Stage 1.6D VPS 实时来源观测部署授权
* **前置依赖**：1.6A--C 的完成证据、当前 Stage 1.5D/F 主机健康事实、VPS 磁盘与锁状态、有效 source-profile attestation。
* **所需证据**：[Stage 1.6 路线地图](project-status/2026-08-24-stage1-6-futures-delisting-route-map_CN.md) 和 [1.6B deployment checklist](reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md) 的全部只读 preflight transcript。
* **通过标准**：经审查的 deployment authorization 明确 live root、单 writer、300 秒轮询、storage stop 条件、attestation 绑定、终态/封签和 rollback。
* **拒绝/停止条件**：任何 Stage 1.5 健康、磁盘 reserve、锁、profile attestation 或运行时安全门禁不满足，立即停止且不创建 live root。
* **安全边界**：只读官方来源观察；不产生 PIT 交易结论、replay、paper/live trading 或执行权限。

---

## 8. 决策日志记录 (Decision Log)

* **2026-05-23**：旧 carry/MR 期限趋平且频繁超时，决策封存，转向 `crypto-alpha-lab` 新架构。建立 5k-50k USDT 资金规模假设。
* **2026-06-10**：截面动量 (CMOM) 因子测试判定无法战胜 Cash Fallback，截面因子实验室结题闭环。
* **2026-06-18**：500 次 Monte Carlo trials 重放证明衍生品拥挤度反转无显著 Alpha，决策转向公告催化剂。
* **2026-06-24**：1.5D 实时公告收集器设计通过审查，1.5C 价格覆盖重放通过门槛。
* **2026-06-26**：1.5F 实时盘口观察器设计通过审查，服务器上部署实时 L2 快照采集。
* **2026-07-05**：Route C1 7 天实盘烟雾测试最终评估不达标，现货价格代理策略被证伪结题。
* **2026-07-12**：1.5H 静态代理只读报告生成器通过审查，确立“只读诊断报告，无模拟器或执行声明”治理契约。
* **2026-08-18 至 2026-08-24**：Stage 1.6 Futures Delisting 完成 1.6A--C：来源/时间契约、1.6B 历史封签采集、sealed-export 语义审计与 H2 grammar 修补；历史 source audit 通过，但 VPS 实时观测仍未部署。
* **2026-07-19**：发布 Master Assessment。决定放弃 listing 开盘首小时、放弃社交热点音量、降级治理提案；批准 1.6A (下架公告) 与 1.6R (安全事故 Risk-Veto) 作为下一优先设计路线。
* **2026-07-24**：实施并验证 1.5F 历史锚点 Rejection Hygiene 热装补丁（水印 Schema v2、终端 Ignore 分流以防污染 `events_rejected`）。
* **2026-07-26**：验证服务器 1.5D/1.5F 影子运行状态；完成项目当前状态报告（`current-project-state_CN.md`）与统一文档事实索引（`current-document-index_CN.md`）。

---

## 9. 已替代历史文档清单 (Superseded Documents)

查看所有因热装补丁升级、证伪或架构转向而被后续设计/计划替代的历史文档清单与索引，请访问：

👉 **[docs/project-status/current-document-index_CN.md](project-status/current-document-index_CN.md)**
