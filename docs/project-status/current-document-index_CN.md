# Crypto Alpha Lab 当前文档索引 (Current Document Index)

> **文档生成时间：** 2026-08-24（Stage 1.6 路线治理更新；其它历史索引条目保留原采集时间）
> **使用说明：** 本文档为仓库中所有研究、设计、计划、审查与状态文档的**统一事实索引入口**。未来的 AI Agent 在开展任何工作前，必须遵循《10. AI 使用规则》，严禁直接以历史被替代 (superseded) 或已证伪 (falsified) 的文档指导新开发。

---

## 1. 索引元数据 (Index Metadata)

| 属性 | 统计值 / 事实 | 凭据与说明 |
|---|---|---|
| **generated_at** | `2026-08-24` | Stage 1.6 路线治理更新日期；非全仓重新扫描 |
| **local_commit** | `4a15c1f8ab5f1893dc409270a88e5c3b153cf682` | 本次治理开始时的 `git rev-parse HEAD` |
| **server_git_commit** | `unknown` | 当前服务器快照未成功采集 Git commit；仅能证明三份关键部署文件 SHA256 与本地匹配 |
| **selected_deployed_file_hash_match** | `true` | `configs/base.py`、1.5D runner、1.5F runner 与服务器文件 SHA256 匹配 |
| **scanned_document_count** | `180` | 全仓库扫描的 Markdown 研究与架构文档总数 |
| **unknown_status_count** | `2` | 包含 `docs/reviews/2026-06-03-route-c1-phases-and-practical-usage-explanation_CN.md` 与 `docs/production_artifacts/Crypto_Trading_101.md` |
| **conflict_count** | `1` | 1.5D 详情页重试调度重叠计划冲突 (见 8. 文档冲突) |

---

## 2. 当前权威入口 (Current Authority Entrypoints)

| 领域 / 阶段 | Current Design | Current Plan | Current Review | Code Status | Deployment Status | 凭据与证据文件 |
|---|---|---|---|---|---|---|
| **项目全局状态** | N/A | N/A | N/A | N/A | N/A | [current-project-state_CN.md](current-project-state_CN.md) |
| **项目 Roadmap** | [roadmap.md](../roadmap.md) | N/A | N/A | N/A | N/A | [docs/roadmap.md](../roadmap.md) |
| **Stage 1.5D** (公告采集+BAPI详情) | [1.5D Design](../designs/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-design_CN.md) | [1.5D BAPI Plan](../plans/2026-07-22-external-signal-shadow-lab-stage1-5d-bapi-article-detail-source-hotfix-implementation-plan_CN.md) | [1.5D Review](../reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md) | `implemented` | `deployed` (PID 88580) | `server_runtime_snapshot...txt:L24` |
| **Stage 1.5F** (L2盘口观察+上线时间闸门) | [1.5F Design](../designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md) | [1.5F Terminal Hygiene Plan](../plans/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-terminal-ignore-rejection-hygiene-hotfix-plan_CN.md) | [1.5F Review](../reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md) | `implemented` | `deployed` (PID 88770) | `server_runtime_snapshot...txt:L26` |
| **Stage 1.5G** (盘口质量离线审查) | [1.5G Design](../designs/2026-07-06-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review-design_CN.md) | [1.5G Quarantine Plan](../plans/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-implementation-plan_CN.md) | [1.5G Clean Summary](../../data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json) | `implemented` | `implemented` (Offline) | SPCXUSD1 clean pass；SKHYUSDT quarantine pass；POPMARTUSDT invalid/quarantine candidate |
| **Stage 1.5H** (静态只读报告生成器) | [1.5H Design](../designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md) | [1.5H Plan](../plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md) | [1.5H Governance Review](../reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md) | `implemented` | `implemented` (Offline) | 原始 `data/stage1_5h` artifact 当前未同步进本地工作区 |
| **Stage 1.6 Futures Delisting** | [1.6 Route Map](2026-08-24-stage1-6-futures-delisting-route-map_CN.md) | [1.6C H2 Plan](../plans/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-implementation-plan_CN.md) | [1.6C H2 Completion Audit](../reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md) | `implemented_through_1_6C` | `1_6D_not_deployed` | 历史 source audit 已通过；下一步只能是 1.6D 部署授权，不是 collector 启动 |

---

## 3. External Signal Shadow Lab (Stage 0 – 1.5H)

| Stage | Document Type | File | Status | Decision | Implemented | Deployed | Supersedes | Superseded By | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **Stage 0** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 基础设施前置检查完成 |
| **Stage 1.1** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 手动 Payload Dry Run 审查 |
| **Stage 1.2** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 只读采集关卡通过 |
| **Stage 1.3** | Review | [docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md](../reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 候选信号发现完成 |
| **Stage 1.4A** | Review | [docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md](../reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md) | `superseded` | Feasibility Degraded | Yes | Completed | None | Stage 1.4E | 衍生品压力数据受限于交易所限频 |
| **Stage 1.4B** | Review | [docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md](../reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md) | `historical_reference` | No Alpha | Yes | Completed | None | Stage 1.4C | 500 次试验确认单纯拥挤度反转无独立 Alpha |
| **Stage 1.4C** | Review | [docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4c-joint-decision-review_CN.md](../reviews/2026-06-18-external-signal-shadow-lab-stage1-4c-joint-decision-review_CN.md) | `historical_reference` | Shift to Catalyst | Yes | Completed | Stage 1.4B | Stage 1.5A | 决定从衍生品拥挤度转向催化剂公告 |
| **Stage 1.4E** | Review | [docs/reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md](../reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md) | `superseded` | Degraded | Yes | Completed | Stage 1.4A | Stage 1.5A | 去杠杆代理敏感性分析通过，但确定转向公告 |
| **Stage 1.5A** | Plan | [docs/plans/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-implementation-plan_CN.md](../plans/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-implementation-plan_CN.md) | `implemented` | Approved | Yes | Completed | None | None | Binance 离线源审计实施计划 |
| **Stage 1.5A** | Review | [docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md](../reviews/2026-06-23-external-signal-shadow-lab-stage1-5a-binance-reviewed-high-confidence-source-audit-review_CN.md) | `review_approved` | Passed | Yes | Completed | None | None | 审定通过高置信度事件源表 |
| **Stage 1.5B** | Plan | [docs/plans/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-implementation-plan_CN.md](../plans/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-implementation-plan_CN.md) | `implemented` | Approved | Yes | Completed | None | None | 最小历史事件表构建计划 |
| **Stage 1.5B** | Review | [docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md](../reviews/2026-06-23-external-signal-shadow-lab-stage1-5b-minimal-historical-event-table-review_CN.md) | `review_approved` | Passed | Yes | Completed | None | None | 审定通过最小历史事件表 |
| **Stage 1.5C** | Plan | [docs/plans/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-implementation-plan_CN.md](../plans/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-implementation-plan_CN.md) | `implemented` | Approved | Yes | Completed | None | None | 外部催化剂历史重放计划 |
| **Stage 1.5C** | Review | [docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md](../reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md) | `review_approved` | Passed | Yes | Completed | None | None | 重放结果证实公告后显著响应 |
| **Stage 1.5C1** | Plan | [docs/plans/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-implementation-plan_CN.md](../plans/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-implementation-plan_CN.md) | `implemented` | Approved | Yes | Completed | None | None | 价格覆盖扩充实施计划 |
| **Stage 1.5C1** | Review | [docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md](../reviews/2026-06-24-external-signal-shadow-lab-stage1-5c1-price-coverage-expansion-review_CN.md) | `review_approved` | Passed | Yes | Completed | None | None | 价格覆盖扩展成功 |
| **Stage 1.5D** | Design | [docs/designs/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-design_CN.md](../designs/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-design_CN.md) | `current_authority` | Approved | Yes | Deployed | None | None | 实时公告采集器基础设计规范 |
| **Stage 1.5D** | Plan | [docs/plans/2026-07-22-external-signal-shadow-lab-stage1-5d-bapi-article-detail-source-hotfix-implementation-plan_CN.md](../plans/2026-07-22-external-signal-shadow-lab-stage1-5d-bapi-article-detail-source-hotfix-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Deployed | 2026-07-02 Hotfix Plan | BAPI 详情页解析与正文 Symbol 提取规范 |
| **Stage 1.5D** | Review | [docs/reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md](../reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md) | `review_approved` | Passed | Yes | Deployed | None | None | 采集器基础审查通过 |
| **Stage 1.5E** | Plan | [docs/plans/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-implementation-plan_CN.md](../plans/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-implementation-plan_CN.md) | `implemented` | Approved | Yes | Completed | None | None | 执行可行性静态深度审计计划 |
| **Stage 1.5E** | Review | [docs/reviews/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-review_CN.md](../reviews/2026-06-25-external-signal-shadow-lab-stage1-5e-execution-feasibility-data-audit-review_CN.md) | `review_approved` | Passed | Yes | Completed | None | None | 静态深度证实 500 USDT 承载力 |
| **Stage 1.5F** | Design | [docs/designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md](../designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md) | `current_authority` | Approved | Yes | Deployed | None | None | L2 盘口观察器主设计规范 |
| **Stage 1.5F** | Plan | [docs/plans/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-terminal-ignore-rejection-hygiene-hotfix-plan_CN.md](../plans/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-terminal-ignore-rejection-hygiene-hotfix-plan_CN.md) | `current_authority` | Approved | Yes | Deployed | 2026-07-23 Hotfix Plan | 水印 v2 与 Pre-bootstrap 历史锚点终端 Ignore 规范 |
| **Stage 1.5F** | Review | [docs/reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md](../reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md) | `review_approved` | Passed | Yes | Deployed | None | None | 盘口观察器框架审查通过 |
| **Stage 1.5G** | Design | [docs/designs/2026-07-06-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review-design_CN.md](../designs/2026-07-06-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review-design_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | None | 盘口证据质量离线审查设计规范 |
| **Stage 1.5G** | Plan | [docs/plans/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-implementation-plan_CN.md](../plans/2026-07-11-external-signal-shadow-lab-stage1-5g-raw-snapshot-quarantine-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Offline Tool | 2026-07-06 Impl Plan | 快照 Quarantine 机制实施规范 |
| **Stage 1.5G** | Review | [data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json](../../data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json) | `current_authority` | Clean Pass | Yes | Offline Tool | 2026-07-24 Review | SPCXUSD1 已通过 Clean；SKHYUSDT 为 Quarantine；POPMARTUSDT 为 invalid/quarantine candidate |
| **Stage 1.5H** | Design | [docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md](../designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md) | `current_authority` | Approved | Yes | Offline Tool | 2026-07-12 Static Proxy Design | 静态只读报告生成器治理规范 (Strict Read-Only) |
| **Stage 1.5H** | Plan | [docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md](../plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | 静态只读报告实施规范 |
| **Stage 1.5H** | Review | [docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md](../reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md) | `review_approved` | Passed | Yes | Offline Tool | None | 审定证实严禁交易/无模拟器解构；原始运行 artifact 未同步进本地 |

---

## 4. 其它研究路线 (Other Strategy & Research Routes)

### 4.1 Carry / MR 路线 (Frozen)
- **状态**：`falsified` / `historical_reference`
- **主要文档**：[docs/roadmap.md](../roadmap.md)
- **结论**：BTC 期限结构处于 Flat 状态 (Term structure slope = 0.000)，资金费率无法支付交易成本；OKX 现货 API 频繁超时打破 60 周期历史连续性。已停止开发，逻辑冻结作为历史基线。

### 4.2 Extreme Funding (Priority 1 Strategy)
- **状态**：`implemented` (代码存在于 `src/strategies/base.py`, `configs/base.py`)
- **核心文档**：
  - [docs/plans/extreme_funding_scanner_impl.md](../plans/extreme_funding_scanner_impl.md) (`implemented`)
  - [docs/reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md](../reviews/2026-05-25-extreme-funding-historical-basis-aware-replay-review.md) (`review_approved`)
  - [docs/reviews/2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md](../reviews/2026-05-26-extreme-funding-parameter-sensitivity-audit-review.md) (`review_approved`)
- **结论**：5 年历史数据验证 >100% 年化阈值下 DOGE/XRP 胜率 >64%，年化 >30% + 贴水吸收检查契约成立。

### 4.3 Trend Regime / Liquidation Cascade (Priority 2 Strategy & Route A/B/C/C1)
- **状态**：`implemented` (核心策略在 `configs/base.py`) / `falsified` (Route C1 7d 试验)
- **核心文档**：
  - [docs/plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md](../plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md) (`implemented`)
  - [docs/plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md](../plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md) (`implemented`)
  - [docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md](../reviews/2026-07-05-route-c1-live-smoke-7d-review.md) (`falsified`: Route C1 7 天烟雾测试样本重叠度与胜率不达标，分支终止)
- **结论**：Route A/B 受到 API 限频与数据完整性拦截，Route C1 纯价格代理已证伪；现仅保留 1h 波动率突破 (2.5x) + OI 动量方向性框架。

### 4.4 Cross-Sectional Factor Lab (截面因子实验室)
- **状态**：`historical_reference` / `falsified`
- **核心文档**：
  - [docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md](../strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md) (`historical_reference`)
  - [docs/reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md](../reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md) (`review_approved`)
  - [docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md](../reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md) (`falsified`: CMOM 截面动量因子超额收益不足以覆盖现金替代)
- **结论**：截面动量因子在扣除交易成本后未呈现超越 Cash Fallback 的稳定 Alpha，项目闭环结题。

### 4.5 Stage 1.6 Event-Source Candidate Registry (研究候选登记)
- **状态**：`strategic_reference_only`
- **核心文档**：
  - [2026-07-13 统一研究路线总纲](../strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md) (`strategic_reference_only`)
  - [2026-07-19 Master Assessment 评估](../strategy_specs/2026-07-19-event_source_master_assessment.md) (`strategic_reference_only`)
- **当前实施编号 authority**：[2026-08-24 Stage 1.6 Futures Delisting 路线地图](2026-08-24-stage1-6-futures-delisting-route-map_CN.md)。旧文档中 ETF Flow 等的 `1.6B`、`1.6C` 候选编号不再用于当前工程实施编号。
- **结论**：Futures Delisting 是当前唯一已立项的 Stage 1.6 研究事件；ETF Flow、Prediction Market 和 Security Incident 保留为未立项候选。

---

## 5. 当前有效实施链 (Active Implementation Chains)

仅保留当前可用于后续开发与运行维护的完整链路：

1. **Stage 1.5D 实时公告与 BAPI 详情采集链**：
   `Design (2026-06-24)` -> `Plan (2026-07-22 BAPI Hotfix Plan)` -> `Review (2026-06-24)` -> `Code (src/.../stage1_5d_*)` -> `Test (tests/.../test_stage1_5d_*)` -> `Deployment (Server PID 88580)` -> `Runtime Evidence (detail_retry_scheduler_state.json)`
2. **Stage 1.5F 实时 L2 深度观察与终端 Ignore 链**：
   `Design (2026-06-26)` -> `Plan (2026-07-24 Hygiene Hotfix Plan)` -> `Review (2026-06-26)` -> `Code (src/.../stage1_5f_*)` -> `Test (tests/.../test_stage1_5f_*)` -> `Deployment (Server PID 88770)` -> `Runtime Evidence (live_depth_observer_summary.json)`
3. **Stage 1.5G 离线盘口质量审查链**：
   `Design (2026-07-06)` -> `Plan (2026-07-11 Quarantine Plan)` -> `Review (2026-07-24 Review)` -> `Code (src/.../stage1_5g_*)` -> `Test (tests/.../test_stage1_5g_*)` -> `Deployment (Offline Tool)` -> `Runtime Evidence (stage1_5g_quarantine_summary.json)`
4. **Stage 1.5H 静态只读报告生成链**：
   `Design (2026-07-12 Governance Design)` -> `Plan (2026-07-12 Plan)` -> `Review (2026-07-12 Review)` -> `Code (scripts/.../review_stage1_5h_*)` -> `Test (tests/.../test_review_stage1_5h_*)` -> `Deployment (Offline Report Tool)` -> `Runtime Evidence (stage1_5h...summary.json)`
5. **Stage 1.6 Futures Delisting 历史证据与审计链**：
   `1.6A Source/Schema Contract (2026-08-18)` -> `1.6B Historical Capture and Sealed Export` -> `1.6C Sealed-Export Adapter v2` -> `H2 Grammar Delta` -> `Independent Completed-Consumer Audit (source_audit_passed=true)` -> `1.6D Live Observation (not deployed)`。

---

## 6. Superseded 文档 (Superseded Documents)

| 旧文档 (Old File) | 替代文档 (Superseded By) | 替代原因 (Reason) | 历史保留价值 (Historical Value) |
|---|---|---|---|
| `docs/plans/2026-07-01-external-signal-shadow-lab-stage1-5d-u-settlement-contract-symbol-hotfix-plan_CN.md` | `docs/plans/2026-07-22-external-signal-shadow-lab-stage1-5d-bapi-article-detail-source-hotfix-implementation-plan_CN.md` | 被更完善的 BAPI 详情页正文解析与 202 重试调度计划覆盖 | 记录 U 本位标的识别规则演进 |
| `docs/plans/2026-07-03-external-signal-shadow-lab-stage1-5f-delayed-launch-age-gate-hotfix-plan_CN.md` | `docs/plans/2026-07-23-external-signal-shadow-lab-stage1-5f-launch-time-gated-depth-observation-hotfix-plan_CN.md` | 被正式上线时间闸门与挂起注册表计划覆盖 | 记录开盘前空盘口抓取缺陷修复 |
| `docs/plans/2026-07-06-external-signal-shadow-lab-stage1-5f-request-manifest-symbol-key-hotfix-plan_CN.md` | `docs/plans/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-terminal-ignore-rejection-hygiene-hotfix-plan_CN.md` | 被终端 Ignore 状态与 Rejection Hygiene 规范覆盖 | 记录 Request Manifest Symbol 补全逻辑 |
| `docs/reviews/2026-06-16-route-c1-live-smoke-7d-review.md` | `docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md` | Route C1 7 天测试最终期满审定，结论确定为不达标终止 | 记录 Route C1 纯价格代理测试历程 |
| `docs/strategy_specs/2026-07-08-后续事件源路线说明-external_catalyst_event_sources_personal_investor_route_guide_CN.md` | `docs/strategy_specs/2026-07-13-整理的后续事件源研究路线图-external-catalyst-event-sources-unified-research-roadmap_CN.md` | 被 07-13 统一研究路线总纲完全替代 | 保留个人投资者早期视角分析 |

---

## 7. Blocked / Required Fixes (阻塞与待修订项)

1. **Stage 1.5G 事件族样本量不足阻塞**：
   - **证据文件**：`data/external_signal_shadow/stage1_5g/reviews/20260722T023908Z/stage1_5g_live_depth_evidence_review_summary.json`
   - **内容**：`SPCXUSD1` 已满足 `stage1_5g_depth_evidence_clean_pass`，但单一 Clean 样本不足以支持 Stage 1.5 event-family conclusion。
   - **解封要求**：维持服务器 1.5D 与 1.5F 连续运行，累计满足当前配置口径的事件族样本量（至少 3 个 unique symbol 且至少 2 个 source article）。

---

## 8. 文档冲突 (Document Conflicts)

1. **Conflict 1 (1.5D 详情页重试策略冲突)**：
   - **Document A**：`docs/plans/2026-07-10-external-signal-shadow-lab-stage1-5d-detail-endpoint-degraded-retry-cadence-and-fallback-hotfix-plan_CN.md`
   - **Document B**：`docs/plans/2026-07-10-external-signal-shadow-lab-stage1-5d-detail-retry-scheduler-starvation-hotfix-plan_CN.md`
   - **冲突内容**：Document A 提议使用固定指数退避退化节奏，而 Document B 提议使用基于优先级的动态重试队列以解决超时饥饿。
   - **推荐事实来源 (Recommended Source of Truth)**：以 `Document B` (`detail-retry-scheduler-starvation-hotfix-plan`) 及后续 `2026-07-22-bapi-article-detail-source-hotfix-implementation-plan` 为准（已被代码实现并部署运行）。

---

## 9. 缺失文档 (Missing Documents)

1. **Stage 1.6A--C 文件缺失项已关闭**：
   - **现状**：实际基线文件为 `docs/designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md`；后续 1.6B producer、1.6C adapter 和 H2 completion evidence 见 [Stage 1.6 路线地图](2026-08-24-stage1-6-futures-delisting-route-map_CN.md)。
2. **Stage 1.6R Security Incident Risk-Veto 设计文档尚未立项**：
   - **现状**：Roadmap 已确定 1.6R 为风控旁路线，但 `docs/designs/` 下尚无相关设计与 SOP 文档。
3. **缺失 Stage 1.5G Clean Markdown 正式审查报告索引**：
   - **现状**：本地已同步 `SPCXUSD1` Clean summary JSON，但 `docs/reviews/2026-07-22-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md` 曾被 pytest quarantine 产物污染；若需要人类可读正式结论，应以服务器正式 Markdown 覆盖或补写索引说明。

---

## 10. AI 使用规则 (Rules for Future AI Agents)

所有未来的 AI Agent 在本仓库中工作时，必须严格遵守以下规则：

1. **阅读顺序强制要求**：
   - **第一步**：必读 [docs/project-status/current-project-state_CN.md](current-project-state_CN.md)（获取服务器真实运行状态与安全硬开关）。
   - **第二步**：必读本文档 [docs/project-status/current-document-index_CN.md](current-document-index_CN.md)（获取领域权威文档入口）。
   - **第三步**：仅阅读本文档第 2 节中列出的 `current_authority` 权威设计与计划文档。
2. **严禁使用旧文档指导新开发**：
   - 严禁阅读被标记为 `superseded`、`falsified` 或 `historical_reference` 的文档并将其作为新代码实现的依据。
3. **严格区分文档类型与状态**：
   - 严禁将 `Design` 当作 `Implementation Plan`，严禁将 `Plan` 当作已完成代码，严禁将本地代码误写为服务器已部署。
