# Crypto Alpha Lab 当前项目状态 (Current Project State)

> **文档生成时间：** 2026-10-07T23:45:00+08:00 (Local Evidence UTC: 2026-10-07T15:45:00Z)
> **双态事实数据源：**
> - **本地代码库与治理基线：** Git HEAD `23708b824ca0ff6ff82ad31e13cb36136fa5b8d2`（2026-10-07，包含 Stage 1.5J-A 历史数据归档覆盖度盘点结项、收据闭环审计、Stage 1.3 R10、Stage 1.5G N=3、Stage 1.5H N=3 与 Stage 1.6F W2-0 探索性诊断结项）
> - **服务器运行时快照基线：** `../../_project_context/server_runtime_snapshot_20260726T021054Z.txt`（2026-07-26 采集，PID 88580 与 PID 88770 稳定运行，直至下次 VPS 同步）
> - **生产回执与运行证据目录：** `data/external_signal_shadow/`（含 1.5J-A、1.5G N=3、1.5H N=3、1.6F W2-0 回执）与 `../../_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest`

---

## 1. 快照元数据 (Snapshot Metadata)

| 属性 | 当前真实状态 | 证据来源 |
|---|---|---|
| **文档更新时间** | 2026-10-07T23:45:00+08:00 (UTC 2026-10-07 15:45:00) | 本次 Stage 1.5J-A 归档覆盖度盘点结项更新 |
| **本地 Branch** | `feature/external-signal-shadow-stage1` | `git branch --show-current` |
| **本地 Commit** | `23708b824ca0ff6ff82ad31e13cb36136fa5b8d2` | `git rev-parse HEAD` |
| **服务器 Git Commit** | `unknown` | 2026-07-26 服务器快照未成功采集 `git rev-parse HEAD` |
| **关键部署文件 Hash Match** | `MATCH` (仅限 2026-07-26 快照比对) | 历史 SHA256 比对（见下表）；不能外推为当前服务器 Git commit 匹配 |
| **本地工作区状态** | `Clean` (跟踪文件无越界修改) | `git status --short` |
| **服务器工作区状态** | `unknown` | 2026-07-26 服务器快照未成功采集 `git status --short` |

### 历史部署文件 SHA256 校验比对表 (2026-07-26 快照)

| 核心文件 | 本地 Hash | 服务器部署 Hash | 匹配状态 | 证据路径 |
|---|---|---|---|---|
| `configs/base.py` | `75d316f66e7cd83e59c53e18334eedb621ea9571f17be9a125c707e813d70a3c` | `75d316f66e7cd83e59c53e18334eedb621ea9571f17be9a125c707e813d70a3c` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L151` |
| `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | `52b56b4267365bc5202a3f91607ff1952d7e33087794010d17193d9504c0476d` | `52b56b4267365bc5202a3f91607ff1952d7e33087794010d17193d9504c0476d` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L152` |
| `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` | `5bb3294968604175bc355066d3b4e4ac4fdbfacdc3c9c00db8d169add2a6700f` | `5bb3294968604175bc355066d3b4e4ac4fdbfacdc3c9c00db8d169add2a6700f` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L153` |

---

## 2. 项目当前使命与安全边界 (Mission & Safety Invariants)

#### 2.1 项目定位
本项目**不是套利系统**，**不是自动化收益机器**，而是**个人 Alpha 验证实验室与安全执行基座**（针对 5,000 – 50,000 USDT 资金规模，当前阶段仅进行纯只读观察与影子验证，严禁任何实盘交易）。
全项目研究方法论遵循 [.agent/rules/L2_Alpha_Research_Methodology.md](../../.agent/rules/L2_Alpha_Research_Methodology.md)，但 L2 从属于 L0/L1，绝不授予任何实盘、模拟盘或执行权限。

### 2.2 安全开关与硬边界表

| 安全开关 / 权限标志 | 当前真实值 | 约束效果 | 证据文件路径 |
|---|---|---|---|
| `RISK_LIVE_TRADING_ENABLED` | `False` | 拒绝任何实盘下单逻辑 | [configs/base.py:L86](../../configs/base.py#L86) |
| `RiskLimits.live_trading_enabled` | `False` | 风险引擎默认处于 Observation 模式 | [src/risk/limits.py:L39](../../src/risk/limits.py#L39) |
| `trade_signal_allowed` | `False` | 禁止策略输出可交易 SignalCandidate | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `paper_trading_allowed` | `False` | 禁止模拟盘下单或虚拟撮合 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `live_trading_allowed` | `False` | 禁止实盘交易 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `execution_engine_allowed` | `False` | 禁止连接执行引擎 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `alpha_interpretation_allowed` | `False` | 禁止将观察数据解构为独立 Alpha 结论 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `execution_feasibility_claim_allowed` | `False` | 禁止宣称流动性/深度具备可执行性 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `stage1_5g_gate3_complete` | `False` | Stage 1.5H N=3 诊断结论为证据不充分，Gate 3 未开放通过 | `data/external_signal_shadow/stage1_5h/.../summary.json` |
| `consumer_admission_allowed` | `False` | 下游消费者强制 Fail-Closed 硬阻断 (`STOP=...`) | Stage 1.3 R10 / 1.5G N=3 / 1.5H N=3 / 1.5J-A 核心模块 |

---

## 3. 当前架构 (Current Architecture)

代码库中真实存在并维护的核心架构模块如下：

```text
crypto-alpha-lab/
├── configs/
│   └── base.py                        # 全局配置单一事实来源 (Single Source of Truth, RISK_LIVE_TRADING_ENABLED=False)
├── src/
│   ├── execution/                     # 冻结的底层执行层 (Verbatim migrated, 355 lines)
│   │   └── order_executor.py          # 7 种异常恢复机制 (Maker timeout, rollback, unknown remote state)
│   ├── strategies/                    # 策略标准接口
│   │   └── base.py                    # SignalCandidate 强类型契约
│   ├── risk/                          # 风险控制模块
│   │   └── limits.py                  # RiskLimits 风险硬边界
│   └── research/external_signal_shadow/ # 外部催化剂影子观察管线 (Stage 1.3 - 1.6)
│       ├── stage1_3_r10_readmission.py # 1.3 R10 历史信号准入前置校验门禁 (AST防泄漏 + Git锚定 + flock原子发布)
│       ├── stage1_5d_live_event_source_* # 1.5D 公告采集 + BAPI 详情解析 + 202 Retry 调度器
│       ├── stage1_5f_live_depth_*     # 1.5F L2 盘口观察器 + 上线时间闸门 + 水印 v2 + 终端 Ignore Hygiene
│       ├── stage1_5g_live_depth_*     # 1.5G 离线盘口质量审查器 (Clean / Quarantine / Invalid)
│       ├── stage1_5g_n3_regime_stratified_admission.py # 1.5G N=3 产品机制分层事件族准入模块
│       ├── stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py # 1.5H N=3 产品机制分层流动性摩擦诊断模块
│       ├── stage1_5h_static_execution_* # 1.5H 历史静态执行代理报告生成器 (Strict Read-Only)
│       ├── stage1_5j_a_historical_archive_coverage_inventory.py # 1.5J-A 历史数据归档覆盖度盘点核心模块 (Two-pass scan + 365天全量盘点 + flock原子发布 + 严格反短路)
│       └── stage1_6*                  # 1.6 Futures Delisting 历史源契约、密封适配器、H2 语法回放与终局基差诊断模块
├── scripts/
│   ├── review_external_signal_shadow_stage1_3_r10_readmission.py # 1.3 R10 离线准入复核 CLI 脚本
│   └── external_signal_shadow/        # 影子观察、准入与审查脚本集 (含 1.5G N=3、1.5H N=3、1.5J-A runner)
```

---

## 4. Stage 状态矩阵 (Stage State Matrix)

> **状态分类标准：** `implemented_locally` (代码存在), `committed` (已提交 Git), `deployed` (已部署服务器), `running` (正在运行), `evidence_collected` (存在运行 Artifact), `reviewed` (有正式 Review 结论), `blocked` (有明确 Blocker), `planned_only` (仅计划/设计), `superseded` (已被替代), `unknown` (证据不足).

| Stage / 策略 | 目标 | 当前状态 | 本地实现 | 已部署 | 运行证据 | 当前结论 | 下一 Gate |
|---|---|---|---|---|---|---|---|
| **Extreme Funding Event Scanner** | 30%+ 资金费率 Carry 扫描 | `implemented_locally`, `committed`, `evidence_collected` | `Yes` | `False` | `docs/roadmap.md#historical-verification--backtest-results` | 5年结算数据验证 DOGE/XRP 胜率>64%；74天本地盘口因 API 10.95% 限制与贴水呈现 0 信号 | 影子模式 Scanner 挂载 |
| **Trend / Liquidation Scanner** | 波动率突破(2.5x)与清算级瀑布动量 | `implemented_locally`, `committed`, `planned_only` | `Yes` | `False` | [configs/base.py:L124](../../configs/base.py#L124) | 方向性 Alpha 候选，需硬止损(1.5%)与 12h 最大持仓 | 影子模式模拟 |
| **Long-Horizon Basis Desk** | 3-7天稳定 Carry (10-25% 资金费率) | `implemented_locally`, `committed`, `planned_only` | `Yes` | `False` | [configs/base.py:L145](../../configs/base.py#L145) | 每 8h 必须进行 Basis 亏损>50% 资金收益的熔断检查 | Basis 历史 DB 建立与 8h Funding Flip 检测器 |
| **Stage 1.3 - 1.4E** | Vision OI、爆仓快照与 Crowd Replay | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Historical | `docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-4e-review_CN.md` | 爆仓快照受到交易所限频影响，被 Stage 1.5 催化剂公告路线替代 | `superseded` |
| **Stage 1.3 R10** | 历史信号只读结构化准入前置校验 (无收益泄露/无未来函数) | `implemented_locally`, `committed`, `reviewed`, `audit_complete` | `Yes` | Offline Tool | Commit `8c6f3a0` | 69项测试通过，独立 Completion Audit 结论为 COMPLETE（0 OPEN finding）；下游消费者强制 Fail-Closed 阻断 | 等待候选 Manifest/Bars 离线运行 |
| **Stage 1.5A - 1.5C1** | 催化剂历史事件审计、最小表与重放 | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Completed | `data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json` | 证实公告后存在显著价格响应，通过可行性前置门槛 | 推进 1.5D 实时采集 |
| **Stage 1.5D** | Binance 公告实时采集 + BAPI 详情 + 202 重试调度 | `implemented_locally`, `committed`, `deployed`, `running`, `evidence_collected` | `Yes` | `True` (PID 88580) | `runtime_evidence/.../stage1_5d/detail_retry_scheduler_state.json` | BAPI 详情页解析与 202 重试调度器持续稳定运行，消除饥饿 | 维持 7 天连续运行 |
| **Stage 1.5E** | 执行可行性静态审计 | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Completed | `data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json` | 静态深度审计通过 500 USDT 深度承载力测试 | 推进 1.5F 实时盘口观察 |
| **Stage 1.5F** | L2 深度实时观察器 + 上线时间闸门 + 水印 v2 + 终端 Ignore | `implemented_locally`, `committed`, `deployed`, `running`, `evidence_collected` | `Yes` | `True` (PID 88770) | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json` | 进程持续运行(2643 heartbeats)，76个 pre-bootstrap 历史锚点终端 Ignore，0 报错 | 捕获新合约上线 L2 盘口证据 |
| **Stage 1.5G (历史单Root)** | L2 深度证据离线审查器 (Clean/Quarantine/Invalid) | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` | SPCXUSD1 与 MOONSHOTUSDT 审查通过 Clean (MOONSHOTUSDT 采样 716 点，覆盖率 99.44%，P50点差 5.85 bps，P50滑点 7.14/8.01 bps)；SKHYUSDT 审查通过 Quarantine；POPMARTUSDT 为 invalid / quarantine candidate | 样本量已扩充至 2 个 Clean 样本，被 N=3 分层准入覆盖 |
| **Stage 1.5G N=3** | N=3 产品机制分层事件族准入 | `implemented_locally`, `committed`, `reviewed`, `receipt_published`, `audit_complete` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z/stage1_5g_n3_regime_stratified_admission_summary.json` | 52 项测试全通，独立审计评定 COMPLETE (Commit `9484dd3`)；准入 3 篇独立公告、3 个父事件、9 个正式子标的（CTUSDT、MOONSHOTUSDT、7 个 batch7 标的）按 3 类产品机制分层 clean pass；**达成 Gate 3 样本数量门槛（$\ge 3$ 个独立事件且 $\ge 3$ 篇公告）**；下游消费强制 Fail-Closed 硬阻断 | 推进 Stage 1.5H N=3 机制分层流动性摩擦诊断 |
| **Stage 1.5H (历史静态报告)** | 静态执行代理报告生成器 (Read-Only Report Generator) | `implemented_locally`, `committed`, `reviewed` | `Yes` | Offline Tool | `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md` | 报告生成器治理审查通过；当前本地 `data/stage1_5h` artifact 未同步进工作区 | 维持纯只读报告工具定位，已被 N=3 诊断替代 |
| **Stage 1.5H N=3** | N=3 产品机制分层流动性摩擦诊断 | `implemented_locally`, `committed`, `reviewed`, `receipt_published`, `audit_complete` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z/stage1_5h_n3_regime_stratified_friction_summary.json` | 39 项测试通过；独立审计评定 COMPLETE (Commit `ab5043d`)；基于 1.5G N=3 的 3 个父事件与 9 个子标的完成机制分层 P95 滑点摩擦诊断；证实三种产品机制摩擦显著分化（标准加密 17.99 bps vs Pre-IPO 31.58 bps vs 传统股指 80.02 bps），严禁跨机制池化或统一定价；结论保持 `evidence_insufficient`，`stage1_5g_gate3_complete=false`；下游消费强制 Fail-Closed 硬阻断，无任何交易或执行权限 | 下游只读微观结构研究；维持零交易/执行权限 |
| **Stage 1.5J-A** | 历史数据归档覆盖度盘点 (365天全量历史与归档闭环审计) | `implemented_locally`, `committed`, `reviewed`, `receipt_published`, `audit_complete` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z/summary.json` | 88 项测试全通；独立审计与 Design §7.2 变异审计评定 COMPLETE (Commit `23708b8`)；盘点 365 天窗口内 335 篇公告，131 篇目标新上线公告，125 篇解析成功 (281 USDT 标的，278 标的归档完整，3 标的归档缺口)，118 篇父事件完整，13 篇父事件存在证据缺口 (6 detail unresolved, 4 no in-scope child, 3 archive gaps)；状态严格为 `coverage_inventory_evidence_gap`；13 项权限开关全 False，下游消费强制 Fail-Closed 硬阻断 | 推进 Stage 1.5J 历史事件驱动微观结构研究 (基于 118 个完整父事件) 或 1.5I 实时抽样中价响应诊断 |
| **Stage 1.6A-C** | Futures Delisting 历史源契约、密封导出与适配器 | `implemented_locally`, `committed`, `reviewed`, `audit_complete` | `Yes` | Completed | `docs/reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md` | 1.6A-C 历史源契约、密封导出与 H2 语法适配器完成独立审计 (`source_audit_passed=true`) | 1.6D 远端部署授权评估 |
| **Stage 1.6D** | Futures Delisting VPS 实时源观察 | `implemented_locally`, `committed`, `planned_only` | `Yes` | `False` (1_6D_not_deployed) | `docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md` | 部署设计与 Runbook 就绪；需 target preflight transcript 与显式用户部署授权 | 待用户显式授权 |
| **Stage 1.6F & W2-0** | 历史对照机制与终局基差探索性诊断结项 | `implemented_locally`, `committed`, `reviewed`, `audit_complete` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json` | 180 物理源对象；41 标的 / 27 父事件；19 个 window-defined 父事件子集证实终局基差发散/非自然收敛（仅 3/19 负值，16/19 正值）；严格保持 outcome_seen/exploratory_only，无后续交易权限，结项 closure only | `none_from_current_evidence` |

---

## 5. 当前 Stage 1.5D 状态 (Stage 1.5D Current Status)

- **数据源 (Source)**：Binance 官方公告 API (`https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query`) + BAPI 详情页接口 (`https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query?articleId=...`)
- **BAPI / Transport 机制**：
  - 具备 BAPI 正文解析器 ([src/research/external_signal_shadow/stage1_5d_bapi_parser.py](../../src/research/external_signal_shadow/stage1_5d_bapi_parser.py))
  - 自动处理 HTTP 202 Accepted 延迟响应与 transient empty 状态 ([stage1_5d_retry_scheduler.py](../../src/research/external_signal_shadow/stage1_5d_retry_scheduler.py))
- **重试 / 降级 / 调度器状态**：
  - 单文章最大重试次数：10 次 (`EXTERNAL_SIGNAL_STAGE1_5D_MAX_DETAIL_RETRIES_PER_ARTICLE = 10`)
  - 过期饥饿门槛：1800 秒 (`EXTERNAL_SIGNAL_STAGE1_5D_DETAIL_RETRY_OVERDUE_STARVATION_THRESHOLD_SEC = 1800`)
  - 运行状态文件证据：`_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5d/detail_retry_scheduler_state.json`
- **Symbol / 上线时间校验**：
  - 支持 USDT 永续、币本位永续及传统金融永续 (`TRADIFI_PERPETUAL`)
  - 支持从 Title/BAPI 详情页提取 secondary base asset 及 Title Symbol Override
- **当前运行 Root 路径**：
  - `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
- **最新 Summary 文件路径**：
  - `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix/binance_futures_launch_smoke_summary.json`
- **未解决阻塞项 (Unresolved Blockers)**：`None` (服务器 Tmux 会话 `stage1_5d_continuous_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` 正在稳定运行，进程 PID 88580).

---

## 6. 当前 Stage 1.5F 状态 (Stage 1.5F Current Status)

- **水印 Schema 版本 (Watermark Schema)**：Schema Version 2 (包含不可变根水印字段 `bootstrap_max_seen_detected_at_ms`, `bootstrap_root_id`, `bootstrap_source_root`, `seen_event_ids`, `seen_source_article_ids`, `seen_stable_event_keys`). 证据路径：`runtime_evidence/.../stage1_5f/watermark.json:L80-L84`
- **上线时间闸门 (Launch Anchor Gate)**：当发现合约公告检测时间早于合约上线时间 (`symbol_effective_launch_times_ms`) 时，事件状态被置入 `pending_launch_time_in_future` 挂起，直至上线时间到达后再开启 60 分钟 L2 深度采集。
- **挂起注册表 (Pending Registry) 实时统计**：
  - `pending_launch_observation_count`: 0
  - `pending_launch_time_in_future_count`: 0
  - `pending_launch_anchor_missing_count`: 0
  - `pending_anchor_conflict_count`: 0
  - `pending_observation_capacity_count`: 0
- **容量与恢复 (Capacity / Recovery)**：
  - 最大并发观察任务数：5 (`EXTERNAL_SIGNAL_STAGE1_5F_MAX_CONCURRENT_OBSERVATIONS = 5`)
  - 崩溃恢复工具：启动时自动执行 `reconcile_missing_accepted_rows` 与 `reconcile_missing_terminal_ignored_rows`
- **终端 Ignore / Rejection Hygiene**：
  - Pre-bootstrap 历史锚点（锚点候选 $\le \text{bootstrap\_max\_seen\_detected\_at\_ms}$）被分类为 `ignored_historical_anchor_pre_bootstrap` (`consumable_by_stage1_5g = False`)，持久化至 `observer_state.jsonl` 与样本上限 10 的 `historical_anchor_hygiene_diagnostics`，**严禁落入 `events_rejected`**。
  - 源身份畸形行被分类为 `diagnostic_only`，写入 `rejection_hygiene_diagnostics`，跳过 `events_rejected`。
  - Post-bootstrap 真实拒绝行写入 `events_rejected` 并带有 `terminal_hygiene_id` 持久化，防止跨 Poll 重复写入。
- **当前运行 Root 路径**：
  - `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
- **当前上游 Summary 接线边界**：
  - `cross_root_upstream_summary_dependency = true`
  - `stage1_5d_events_glob_root`: `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix/events/*.jsonl`
  - `stage1_5d_summary_path`: `data/external_signal_shadow/stage1_5d/live_event_source_smoke_20260627T032026Z/binance_futures_launch_smoke_summary.json`
  - 解释：服务器进程参数显示 1.5F 的事件输入来自当前 20260724 root，但 `--stage1-5d-summary` 仍指向 20260627 旧 summary。现有证据不能证明这是代码 bug；更准确地说，这是部署参数接线状态。下一次重启 1.5F 时应优先改为当前 1.5D root 的 summary，并确认 summary 文件存在。
- **最新 Summary (截至 2026-07-26T10:10:17Z)** 关键指标统计：
  - `decision`: `"stage1_5f_observer_running_no_new_event"`
  - `heartbeat_count`: 2643
  - `active_observation_count`: 0
  - `completed_observation_count`: 0
  - `terminal_ignored_pre_bootstrap_anchor_count`: 76
  - `rejected_event_symbol_count`: 0
  - 证据路径：`_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/live_depth_observer_summary.json`
- **未解决阻塞项 (Unresolved Blockers)**：`None` (服务器 Tmux 会话 `stage1_5f_live_depth_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix` 正在稳定运行，进程 PID 88770).

---

## 7. 当前 Stage 1.5G / 1.5H 状态 (Stage 1.5G & 1.5H Current Status)

### 7.1 Stage 1.5G 离线盘口审查与 N=3 产品机制分层准入

| 分类口径 | 数量 / 标的 | 事实与审查证据路径 | 说明 |
|---|---|---|---|
| **Clean Evidence (单Root历史)** | **2** (`SPCXUSD1`, `MOONSHOTUSDT`) | `data/external_signal_shadow/stage1_5g/reviews/20260923T025100Z_moonshot_review/stage1_5g_live_depth_evidence_review_summary.json` (`decision = stage1_5g_depth_evidence_clean_pass`) | SPCXUSD1 与 MOONSHOTUSDT 通过单 Root 深度审查 Clean；已纳入历史基线 |
| **Quarantined Evidence (单Root历史)** | **1** (`SKHYUSDT`) | `quarantine_summary.json:L7` (`quarantined_depth_evidence_pass = true`) | 前 11 分钟存在 12 个空盘口快照，隔离后有效快照 706 个 |
| **Stage 1.5G N=3 分层准入 (生产回执)** | **3 个独立事件 / 9 个子标的** | `data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z/stage1_5g_n3_regime_stratified_admission_summary.json` | 准入 3 篇独立公告、3 个父事件、9 个正式子标的（CTUSDT、MOONSHOTUSDT、7 个 batch7 标的）按 3 类产品机制分层 clean pass；**Gate 3 样本数量门槛已解封**（Commit `9484dd3`） |

> **机制分层说明**：
> - `crypto_standard_perpetual` (CTUSDT): 标准加密货币资产永续合约；
> - `pre_ipo_equity_perpetual` (MOONSHOTUSDT): Pre-IPO 股权类永续合约；
> - `tradfi_equity_or_etf_perpetual_batch` (7 个标的): 传统股票/ETF 挂钩类永续合约批次。

### 7.2 Stage 1.5H N=3 产品机制分层流动性摩擦诊断

- **生产诊断模块与入口**：`src/research/external_signal_shadow/stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py` 及 CLI `scripts/external_signal_shadow/run_stage1_5h_n3_regime_stratified_liquidity_friction_diagnostic.py`。
- **生产回执与结论**：
  - 回执路径：`data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z/stage1_5h_n3_regime_stratified_friction_summary.json`
  - 诊断结论：`research_classification = "evidence_insufficient"`，`stage1_5g_gate3_complete = False`。
- **经验发现（流动性摩擦显著分化）**：
  - `crypto_standard_perpetual` (CTUSDT): 边际 P95 滑点和为 **17.99 bps**；
  - `pre_ipo_equity_perpetual` (MOONSHOTUSDT): 边际 P95 滑点和为 **31.58 bps**；
  - `tradfi_equity_or_etf_perpetual_batch` (7 个标的): 边际 P95 滑点和中位数为 **80.02 bps**（最高达 87.43 bps）。
- **硬治理约束**：严禁跨机制池化、统一定价或外推任何 Alpha 假设；下游消费强制 Fail-Closed 硬阻断 (`STOP=stage1_5h_n3_future_consumer_not_authorized`)；零实盘/零模拟盘/零执行引擎权限。

### 7.3 Stage 1.5J-A 历史数据归档覆盖度盘点 (365天全量历史与归档闭环审计)

- **生产盘点模块与入口**：`src/research/external_signal_shadow/stage1_5j_a_historical_archive_coverage_inventory.py` 及 CLI `scripts/external_signal_shadow/run_stage1_5j_a_historical_archive_coverage_inventory.py`。
- **生产回执与结论**：
  - 回执路径：`data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z/summary.json` (744 MB)
  - 盘点时间窗口：`2025-10-01T00:00:00Z` 至 `2026-10-01T00:00:00Z` (整 365 天，即 `[1759276800000, 1790812800000)`)
  - 盘点统计：分母公告 335 篇，目标新上线父事件 131 篇，成功解析 125 篇，关联 281 个 in-scope USDT 子标的 (278 标的归档完整，3 标的归档缺口)；完整父事件 118 篇，存在证据缺口父事件 13 篇 (6 篇详情解析未决 `coverage_evidence_gap_detail`，4 篇无 in-scope USDT 子标的 `coverage_evidence_gap_no_in_scope_usdt_child`，3 篇归档校验缺口 `coverage_evidence_gap_archive`)。
  - 核心状态与决策：`analysis_state = "coverage_inventory_evidence_gap"`, `decision = "stage1_5j_a_historical_archive_coverage_evidence_gap_published"`。
- **闭环审计与加载器回放 (Design §7.2)**：
  - 公开 strict loader 对 744 MB 生产回执全量正向重放通过 (RC=0)。
  - 6 项独立 `/tmp` 单点语义变异审计探针 (analysis_state, decision, target_parent_count 计算式, Markdown 审查报告, authority Core SHA, manifest artifact hash) 全部以预期 `STOP=...` 错误码 fail-closed 闭环。
- **硬治理约束**：13 项治理标志严格全 `False`；下游消费强制 Fail-Closed 硬阻断 (`STOP=stage1_5j_a_future_consumer_not_authorized`)；严禁将归档覆盖度提升为 Alpha、回放、信号、执行或交易权限。

---

## 8. 最新真实运行证据汇总 (Latest Real Runtime Evidence)

所有结论均绑定真实文件路径：

1. **本地 Git 分支与 Commit**：
   - 路径：`git rev-parse HEAD`
   - 结论：Branch `feature/external-signal-shadow-stage1`, Commit `23708b824ca0ff6ff82ad31e13cb36136fa5b8d2`
2. **服务器运行进程与 Output Root (2026-07-26 采集快照)**：
   - 路径：`_project_context/server_runtime_snapshot_20260726T021054Z.txt:L20-L26`
   - 结论：
     - PID 88580 运行 1.5D，Root `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
     - PID 88770 运行 1.5F，Root `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
3. **安全硬开关状态**：
   - 路径：[configs/base.py:L86](../../configs/base.py#L86) 与各生产回执中的 governance vector
   - 结论：`RISK_LIVE_TRADING_ENABLED = False`，所有实盘/信号/模拟/引擎开关全为 `false`。
4. **Stage 1.5G N=3 生产准入回执证据**：
   - 路径：`data/external_signal_shadow/stage1_5g/n3_regime_stratified_admissions/stage1_5g_n3_regime_stratified_admission_20261002T110403Z/stage1_5g_n3_regime_stratified_admission_summary.json`
   - 结论：`receipt_published`，3 篇独立公告、3 个父事件、9 个正式子标的通过准入，Gate 3 样本数量门槛解封（Commit `9484dd3`）。
5. **Stage 1.5H N=3 生产诊断回执证据**：
   - 路径：`data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z/stage1_5h_n3_regime_stratified_friction_summary.json`
   - 结论：`receipt_published`，9 标的分层 P95 滑点摩擦诊断完成，结论严格为 `evidence_insufficient`，`stage1_5g_gate3_complete=false`（Commit `ab5043d`）。
6. **Stage 1.3 R10 历史信号准入前置校验闭环证据**：
   - 路径：`src/research/external_signal_shadow/stage1_3_r10_readmission.py` 与 Task 6 审计收据
   - 结论：69 项测试通过，独立 Completion Audit COMPLETE，下游消费者强制阻断（Commit `8c6f3a0`）。
7. **Stage 1.6F W2-0 终局基差探索性诊断结项证据**：
   - 路径：`data/external_signal_shadow/stage1_6f/w2_0_exploratory_diagnostics/w2_0_exploratory_20260926T071500Z/stage1_6f_w2_0_bundle_manifest.json`
   - 结论：180 物理源对象，19 个 window-defined 父事件子集证实终局基差发散，结项 closure only。
8. **Stage 1.5J-A 历史归档覆盖度盘点与闭环审计证据**：
   - 路径：`data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z/summary.json` (744 MB)
   - 结论：`receipt_published`，88 项测试全通，公开严格加载器正向全量重放通过，Design §7.2 6 项单点语义变异审计探针全部以预期 `STOP=...` fail-closed 闭环，118 个父事件完整，13 个父事件存在证据缺口，结论严格为 `coverage_inventory_evidence_gap`，零交易/执行权限（Commit `23708b8`）。

---

## 9. 当前阻塞项 (Current Blockers)

按优先级 P0 / P1 / P2 排序：

### P0 阻塞项
- **无**（服务器 1.5D 与 1.5F 进程持续稳定运行；本地各离线研究管线测试全通，0 崩溃）。

### P1 阻塞项
- **Blocker 1 (产品机制摩擦分化)**：Stage 1.5H N=3 机制分层诊断显示三种产品机制的流动性摩擦显著分化（17.99 bps vs 31.58 bps vs 80.02 bps），当前证据不足以支撑无差别成本模型或交易可行性。
  - **Evidence**：`data/external_signal_shadow/stage1_5h/n3_regime_stratified_friction/stage1_5h_n3_regime_stratified_friction_20261003T070500Z/stage1_5h_n3_regime_stratified_friction_summary.json` (`research_classification = "evidence_insufficient"`, `stage1_5g_gate3_complete = false`)
  - **Risk**：若跨机制池化或采用单一统一定价模型，将导致传统股票/ETF 永续的高额摩擦被低估，引入严重交易亏损风险。
  - **Required Next Action**：维持机制分层隔离；继续保持服务器 1.5D 与 1.5F 连续影子观察以累积长期自然样本；仅在机制分层约束下推进下游只读微观结构研究。
  - **Stop Condition**：严禁授予任何交易或执行权限；下游消费保持 Fail-Closed。
- **Blocker 2 (历史归档覆盖度证据缺口)**：Stage 1.5J-A 历史数据归档覆盖度盘点证实 365 天窗口内存在 13 篇父事件证据缺口（6 篇详情解析未决，4 篇无 in-scope USDT 子标的，3 篇归档校验缺口），不能将历史数据归档假设为 100% 无损完整。
  - **Evidence**：`data/external_signal_shadow/stage1_5j_a/historical_archive_coverage_inventory/stage1_5j_a_historical_archive_coverage_inventory_20261007T091336Z/summary.json` (`analysis_state = "coverage_inventory_evidence_gap"`)
  - **Risk**：若下游研究无视 13 个父事件缺口并强行外推全集无偏统计，将引入幸存者偏差或数据缺失偏差。
  - **Required Next Action**：下游历史微观结构研究仅能严格基于 118 个完整父事件（278 个完整子标的）展开；严禁填补合成数据或伪造缺口标的；下游消费保持 Fail-Closed。
  - **Stop Condition**：严禁将覆盖度盘点提升为 Alpha、回放、信号或交易权限。

### P2 阻塞项
- **Blocker**：Stage 1.6D (Futures Delisting VPS 实时源观察) 尚未获得生产部署授权。
- **Evidence**：`docs/ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md` (`deployment_status: 1_6D_not_deployed`)
- **Risk**：无法在服务器实时采集下架事件与盘口响应。
- **Required Next Action**：如需推进 1.6D 部署，须先完成目标环境 preflight transcript 验证并获得用户显式部署授权。
- **Stop Condition**：用户显式授权或维持未部署状态。

---

## 10. 下一步工作 (Next Steps)

仅列出当前可以执行的 5 项计划内任务：

1. **维持 1.5D 与 1.5F 连续影子观察进程**：监控 PID 88580 与 PID 88770 稳定运行，持续积累新合约上线事件的原始 L2 盘口数据。
2. **基于 Stage 1.5J-A 118 个完整父事件开展历史微观结构研究 (Stage 1.5J)**：在排除 13 个证据缺口父事件的前提下，对 118 个完整父事件（278 个 USDT 子标的）开展首个历史只读微观结构与价格形成分析。
3. **或推进 Stage 1.5I 实时抽样中价响应诊断**：针对实时观察捕获的有效事件开展中价响应测度。
4. **Stage 1.6D 部署前置条件评估**：若需开启期货下架实时源观察，按照 1.6D Runbook 收集目标环境前置证据并请求用户显式部署授权。
5. **维持 L0/L1 安全与权限阻断**：严格保持 `RISK_LIVE_TRADING_ENABLED = False`，维持下游消费者 fail-closed 硬门禁，零交易/执行权限。

---

## 11. 已停止或被证伪路线 (Stopped or Superseded Routes)

| 路线 / 策略 | 停止/降级状态 | 停止原因 | 保留价值 |
|---|---|---|---|
| **`carry_core` / `tactical_carry`** | `stopped` | BTC 期限结构进入 Flat 状态 (Term structure slope = 0.000)，无 Carry 收益空间 | 作为期限结构基线与过滤逻辑保留在代码库 |
| **`mr_core` / `medium_conviction_mr`** | `stopped` | OKX 现货 API 频繁超时，无法满足 60 周期连续历史要求 | 保留策略基线与超时防御逻辑 |
| **Stage 1.3 - 1.4E** (Vision OI & 爆仓快照) | `superseded` | 爆仓快照受到交易所严重限频，被 Stage 1.5 催化剂公告路线替代 | 留存历史 Replay 审查文档 |
| **Stage 1.6H** (Spot Listing After-First-Hour) | `abandoned` | 首小时由做市商/MEV 主导，扣除成本后胜率极低，且 1.5 已覆盖合约上线 | 仅留存为 `first_hour_no_trade` 执行纪律清单 |
| **Stage 1.6G** 复杂社交音量 (LunarCrush/Santiment) | `abandoned` | 极易被水军/KOL 操纵，数据噪声过高，依赖高价第三方 API | 仅保留 alternative.me F&G + Google Trends 简易日志 |
| **Stage 1.6D** (Scheduled Token Unlock) | `frozen` | 缺乏 Point-In-Time 历史快照容易落入后视镜偏差陷阱 (`unlocked != sold`) | 仅保留链上 Vesting 合约校验小课题研究 |
| **Stage 1.6C** (Prediction Market) & **1.6I** (Governance) | `downgraded` | 预测市场回测成本高，治理提案手动解析成本过高 (>1h/事件) | 降级为非量化宏观/季度基本面阅读指南 |

---

## 12. 当前有效文档入口 (Valid Document Entrypoints)

- **全局文档索引入口**：[docs/project-status/current-document-index_CN.md](current-document-index_CN.md)
- **项目 Roadmap 与决策日志**：[docs/roadmap.md](../roadmap.md)
- **后续事件源统一研究路线总纲**：[docs/strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md](../strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md)
- **运维与监控索引**：[docs/ops/2026-06-05-ops-index_CN.md](../ops/2026-06-05-ops-index_CN.md)
