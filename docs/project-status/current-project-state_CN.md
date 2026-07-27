# Crypto Alpha Lab 当前项目状态 (Current Project State)

> **文档生成时间：** 2026-07-26T11:12:57+08:00 (Server UTC: 2026-07-26T02:11:01Z)  
> **事实数据源：** 
> - 服务器运行快照：`../../_project_context/server_runtime_snapshot_20260726T021054Z.txt`
> - 本地工作区快照：`../../_project_context/workspace_snapshot_20260726T020922Z.txt`
> - 运行证据目录：`../../_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest`
> - 服务器归档 Artifacts：`../../_project_context/server_runtime_artifacts/20260726T024623Z`

---

## 1. 快照元数据 (Snapshot Metadata)

| 属性 | 当前真实状态 | 证据来源 |
|---|---|---|
| **文档更新时间** | 2026-07-26T11:12:57+08:00 (UTC 2026-07-26 02:11:01) | `_project_context/server_runtime_snapshot_20260726T021054Z.txt:L2` |
| **本地 Branch** | `feature/external-signal-shadow-stage1` | `workspace_snapshot_20260726T020922Z.txt:L12` |
| **本地 Commit** | `2502e1220ec0144c5d6f4915f89d3ba9804661f3` | `workspace_snapshot_20260726T020922Z.txt:L15` |
| **服务器 Git Commit** | `unknown` | 当前服务器快照未成功采集 `git rev-parse HEAD` |
| **关键部署文件 Hash Match** | `MATCH` (仅限下表三份部署关键文件) | SHA256 比对（见下表）；不能外推为服务器 Git commit 匹配 |
| **本地工作区状态** | `Clean` (仅存在未跟踪目录 `_project_context/`) | `workspace_snapshot_20260726T020922Z.txt:L22` |
| **服务器工作区状态** | `unknown` | 当前服务器快照未成功采集 `git status --short` |

### 核心部署文件 SHA256 校验比对表

| 核心文件 | 本地 Hash | 服务器部署 Hash | 匹配状态 | 证据路径 |
|---|---|---|---|---|
| `configs/base.py` | `75d316f66e7cd83e59c53e18334eedb621ea9571f17be9a125c707e813d70a3c` | `75d316f66e7cd83e59c53e18334eedb621ea9571f17be9a125c707e813d70a3c` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L151` |
| `scripts/external_signal_shadow/run_stage1_5d_live_event_source_smoke_collector.py` | `52b56b4267365bc5202a3f91607ff1952d7e33087794010d17193d9504c0476d` | `52b56b4267365bc5202a3f91607ff1952d7e33087794010d17193d9504c0476d` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L152` |
| `scripts/external_signal_shadow/run_stage1_5f_live_depth_observer.py` | `5bb3294968604175bc355066d3b4e4ac4fdbfacdc3c9c00db8d169add2a6700f` | `5bb3294968604175bc355066d3b4e4ac4fdbfacdc3c9c00db8d169add2a6700f` | `MATCH` | `server_runtime_snapshot_20260726T021054Z.txt:L153` |

---

## 2. 项目当前使命与安全边界 (Mission & Safety Invariants)

### 2.1 项目定位
本项目**不是套利系统**，**不是自动化收益机器**，而是**个人 Alpha 验证实验室与安全执行基座**（针对 5,000 – 50,000 USDT 资金规模，当前阶段仅进行纯只读观察与影子验证，严禁任何实盘交易）。

### 2.2 安全开关与硬边界表

| 安全开关 / 权限标志 | 当前真实值 | 约束效果 | 证据文件路径 |
|---|---|---|---|
| `RISK_LIVE_TRADING_ENABLED` | `False` | 拒绝任何实盘下单逻辑 | [configs/base.py:L86](../../configs/base.py#L86) |
| `RiskLimits.live_trading_enabled` | `False` | 风险引擎默认处于 Observation 模式 | [src/risk/limits.py:L39](../../src/risk/limits.py#L39) |
| `trade_signal_allowed` | `False` | 禁止策略输出可交易 SignalCandidate | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L50` |
| `paper_trading_allowed` | `False` | 禁止模拟盘下单或虚拟撮合 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L51` |
| `live_trading_allowed` | `False` | 禁止实盘交易 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L52` |
| `execution_engine_allowed` | `False` | 禁止连接执行引擎 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L53` |
| `alpha_interpretation_allowed` | `False` | 禁止将观察数据解构为独立 Alpha 结论 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L54` |
| `execution_feasibility_claim_allowed` | `False` | 禁止宣称流动性/深度具备可执行性 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L49` |
| `research_result_valid` | `False` | 当前阶段研究结论尚未通过 Stage 1.5G 完全验证 | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json:L55` |

---

## 3. 当前架构 (Current Architecture)

代码库中真实存在并维护的核心架构模块如下：

```text
crypto-alpha-lab/
├── configs/
│   └── base.py                        # 全局配置单一事实来源 (Single Source of Truth)
├── src/
│   ├── execution/                     # 冻结的底层执行层 (Verbatim migrated, 355 lines)
│   │   └── order_executor.py          # 7 种异常恢复机制 (Maker timeout, rollback, unknown remote state)
│   ├── strategies/                    # 策略标准接口
│   │   └── base.py                    # SignalCandidate 强类型契约
│   ├── risk/                          # 风险控制模块
│   │   └── limits.py                  # RiskLimits 风险硬边界
│   └── research/external_signal_shadow/ # 外部催化剂影子观察管线 (Stage 1.5)
│       ├── stage1_5d_live_event_source_* # 1.5D 公告采集 + BAPI 详情解析 + 202 Retry 调度器
│       ├── stage1_5f_live_depth_*       # 1.5F L2 盘口观察器 + 上线时间闸门 + 水印 v2 + 终端 Ignore Hygiene
│       ├── stage1_5g_live_depth_*       # 1.5G 离线盘口质量审查器 (Clean / Quarantine / Invalid)
│       └── stage1_5h_static_execution_* # 1.5H 静态执行代理报告生成器 (Strict Read-Only)
└── scripts/external_signal_shadow/     # 影子观察与审查脚本集 (Stage 1.3 - 1.5H)
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
| **Stage 1.5A - 1.5C1** | 催化剂历史事件审计、最小表与重放 | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Completed | `data/external_signal_shadow/stage1_5c1/price_coverage/price_coverage_expansion_summary.json` | 证实公告后存在显著价格响应，通过可行性前置门槛 | 推进 1.5D 实时采集 |
| **Stage 1.5D** | Binance 公告实时采集 + BAPI 详情 + 202 重试调度 | `implemented_locally`, `committed`, `deployed`, `running`, `evidence_collected` | `Yes` | `True` (PID 88580) | `runtime_evidence/.../stage1_5d/detail_retry_scheduler_state.json` | BAPI 详情页解析与 202 重试调度器持续稳定运行，消除饥饿 | 维持 7 天连续运行 |
| **Stage 1.5E** | 执行可行性静态审计 | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Completed | `data/external_signal_shadow/stage1_5e/execution_feasibility/execution_feasibility_audit_summary.json` | 静态深度审计通过 500 USDT 深度承载力测试 | 推进 1.5F 实时盘口观察 |
| **Stage 1.5F** | L2 深度实时观察器 + 上线时间闸门 + 水印 v2 + 终端 Ignore | `implemented_locally`, `committed`, `deployed`, `running`, `evidence_collected` | `Yes` | `True` (PID 88770) | `runtime_evidence/.../stage1_5f/live_depth_observer_summary.json` | 进程持续运行(2643 heartbeats)，76个 pre-bootstrap 历史锚点终端 Ignore，0 报错 | 捕获新合约上线 L2 盘口证据 |
| **Stage 1.5G** | L2 深度证据离线审查器 (Clean/Quarantine/Invalid) | `implemented_locally`, `committed`, `reviewed`, `evidence_collected` | `Yes` | Offline Tool | `data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json` | SPCXUSD1 审查通过 Clean；SKHYUSDT 审查通过 Quarantine；POPMARTUSDT 为 invalid / quarantine candidate | 继续积累新 root 下的 Clean 样本并推进 1.5H/1.6A |
| **Stage 1.5H** | 静态执行代理报告生成器 (Read-Only Report Generator) | `implemented_locally`, `committed`, `reviewed` | `Yes` | Offline Tool | `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md` | 报告生成器治理审查通过；当前本地 `data/stage1_5h` artifact 未同步进工作区 | 维持纯只读报告工具定位 |
| **Stage 1.6A - 1.6R** | 期货下架 (1.6A) 与安全事故 Risk-Veto (1.6R) | `planned_only` | `No` | `False` | `docs/strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md` | 1.6A 与 1.6R 已通过 Master Assessment，为下一阶段最高优先设计文档 | 撰写 1.6A 设计文档 |

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

### 7.1 Stage 1.5G 离线盘口审查分类统计

| 分类口径 | 数量 / 标的 | 事实与审查证据路径 | 说明 |
|---|---|---|---|
| **Clean Evidence (无瑕疵证据)** | **1** (`SPCXUSD1`) | `data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json` (`decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true`) | 已存在 1 个 Clean 级 L2 深度证据；`formal_announcement_and_launch_count = 1`，`book_availability_ratio = 99.86%` |
| **Quarantined Evidence (隔离级证据)** | **1** (`SKHYUSDT`) | `quarantine_summary.json:L7` (`quarantined_depth_evidence_pass = true`) | 前 11 分钟存在 12 个空盘口快照，隔离后有效快照 706 个，`book_availability_ratio = 98.06%` |
| **Invalid Evidence (本地可复核)** | **0** | `quarantine_summary.json:L11` | 当前本地 runtime evidence 包未包含 POPMARTUSDT 的 2026-07-23 服务器 review JSON，不能在本地独立复核该 invalid 结论 |

> **注**：`SPCXUSD1` clean pass 是当前本地已同步的服务器正式 review 证据。`POPMARTUSDT` 事件也于 2026-07-23 在服务器完成审查，但对应 `20260723T152909Z_popmartusdt` review JSON/Markdown 当前未出现在本地工作区；在同步前，只能作为会话历史结论引用，不能作为本地 source_upload 包内可独立复核证据。

### 7.2 Stage 1.5H 静态执行代理报告定位

- **静态/只读代理报告 (Static/Read-Only Proxy Report)**：生成脚本 `scripts/external_signal_shadow/review_stage1_5h_static_execution_proxy_report.py`。
- **绝对禁令硬断言**：
  - `execution_feasibility_claim_allowed = False`
  - `trade_signal_allowed = False`
- **定位声明**：Stage 1.5H **仅为静态只读报告生成器**，绝非回测模拟器，绝非交易执行引擎，严禁做出任何可执行性声明（Execution Feasibility Claim）。当前本地可用治理证据为 `docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md`；原始 `data/external_signal_shadow/stage1_5h/reports/...` artifact 当前未同步进本地工作区。

---

## 8. 最新真实运行证据汇总 (Latest Real Runtime Evidence)

所有结论均绑定真实文件路径：

1. **本地 Git 分支与 Commit**：
   - 路径：`_project_context/workspace_snapshot_20260726T020922Z.txt:L12-L19`
   - 结论：Branch `feature/external-signal-shadow-stage1`, Commit `2502e1220ec0144c5d6f4915f89d3ba9804661f3`
2. **服务器运行进程与 Output Root**：
   - 路径：`_project_context/server_runtime_snapshot_20260726T021054Z.txt:L20-L26`
   - 结论：
     - PID 88580 运行 1.5D，Root `data/external_signal_shadow/stage1_5d/live_event_source_continuous_20260724T065511Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
     - PID 88770 运行 1.5F，Root `data/external_signal_shadow/stage1_5f/live_depth_observer_20260724T070442Z_7d_bapi_detail_launch_gate_terminal_hygiene_hotfix`
3. **代码部署一致性 (File Hash Match)**：
   - 路径：`_project_context/server_runtime_snapshot_20260726T021054Z.txt:L150-L154` 与本地 `shasum -a 256`
   - 结论：`configs/base.py`、`run_stage1_5d...py`、`run_stage1_5f...py` 三文件 SHA256 哈希与服务器 100% 完全匹配；服务器 Git commit 与 worktree status 仍为 `unknown`。
4. **安全硬开关状态**：
   - 路径：[configs/base.py:L86](../../configs/base.py#L86) 与 `_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/live_depth_observer_summary.json:L49-L55`
   - 结论：`RISK_LIVE_TRADING_ENABLED = False`，所有实盘/信号/模拟/引擎开关全为 `false`。
5. **Stage 1.5F 水印 v2 与 Pre-Bootstrap 终端 Ignore 证据**：
   - 路径：`_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5f/watermark.json:L80-L84` 与 `live_depth_observer_summary.json:L36`
   - 结论：Watermark Schema Version 2，已统计 76 个历史 pre-bootstrap 锚点终端 Ignore。
6. **Stage 1.5G Clean 与隔离级证据**：
   - Clean 路径：`data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json`
   - Clean 结论：`decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true` (`SPCXUSD1`).
   - Quarantine 路径：`_project_context/runtime_evidence/crypto-alpha-runtime-evidence-latest/stage1_5g/stage1_5g_quarantine_summary.json`
   - Quarantine 结论：`quarantined_depth_evidence_pass = true` (`SKHYUSDT`).

---

## 9. 当前阻塞项 (Current Blockers)

按优先级 P0 / P1 / P2 排序：

### P0 阻塞项
- **无**（服务器 1.5D 与 1.5F 进程运行正常，无未捕获异常或主循环崩溃）。

### P1 阻塞项
- **Blocker**：Stage 1.5 已有 1 个 Clean 级 L2 深度证据，但事件族样本量仍不足以支持最终 family-level conclusion。
- **Evidence**：`data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json` (`decision = stage1_5g_depth_evidence_clean_pass`, `clean_depth_evidence_pass = true`)
- **Risk**：单一 Clean 样本只能支持继续推进 1.5H 只读报告/影子设计，不能代表 Binance 新合约上线事件族已经完成充分统计验证。
- **Required Next Action**：维持服务器 1.5D 与 1.5F 的连续影子观察进程，优先捕获新 hotfix root 下的新合约上线事件，并继续运行 Stage 1.5G 离线审查。
- **Stop Condition**：满足事件族审查门槛（至少 3 个 unique symbol 且至少 2 个 source article，按当前配置口径），并保持所有交易/信号/执行权限为 `False`。

### P2 阻塞项
- **Blocker**：Stage 1.6A (Futures Delisting Notice) 设计文档尚未撰写。
- **Evidence**：`docs/strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md:L305`
- **Risk**：无法开启下一代强流事件源（下架公告）的源审计与设计评审。
- **Required Next Action**：撰写 `docs/designs/2026-07-26-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`。
- **Stop Condition**：设计文档通过审查。

---

## 10. 下一步工作 (Next Steps)

仅列出当前可以执行的 4 项计划内任务：

1. **维持 1.5D 与 1.5F 7 天影子观察进程**：监控 PID 88580 与 PID 88770 稳定运行，积累新合约上线事件的数据。
2. **撰写 Stage 1.6A (Futures Delisting Notice) 设计文档**：按照已批准的路线图，制定 `docs/designs/2026-07-26-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`，定义合约下架源解析、隔离规则与三大时间锚点（`available_at_ms`, `non_reduce_only_start_time_ms`, `settlement_time_ms`）契约。
3. **撰写 Daily Capital & Supply Flow Regime Diagnostic 整合设计文档**：合并原 `1.6B` (ETF Daily Net Flow) 与 `1.6F` (BTC Exchange Net Position)，设计日频资金流/供给状态诊断过滤器。
4. **对新抓取的 L2 盘口数据运行 Stage 1.5G 离线审查**：当 1.5F 捕获新的合约上线事件后，执行 `review_stage1_5g_live_depth_evidence.py`，继续补充 Clean / Quarantine / Invalid 样本，并避免把单个 Clean 样本误读为事件族结论。

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
