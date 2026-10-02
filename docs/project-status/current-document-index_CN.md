# Crypto Alpha Lab 当前文档索引 (Current Document Index)

> **文档生成时间：** 2026-08-25（Stage 1.6D deployment authorization/runbook governance 更新；其它历史索引条目保留原采集时间）
> **使用说明：** 本文档为仓库中所有研究、设计、计划、审查与状态文档的**统一事实索引入口**。未来的 AI Agent 在开展任何工作前，必须遵循《10. AI 使用规则》，严禁直接以历史被替代 (superseded) 或已证伪 (falsified) 的文档指导新开发。
> **局部治理纠偏 Design 日期：** 2026-09-28；仅修正 C1、B-Lite 与 Factor Lab 的历史决策措辞，未执行全仓库重新扫描。
> **纠偏 Design SHA-256：** `37ff23045de7519b426ff1da71e04ec8d61ce371ccafe3fae96711802201583f`。

---

## 1. 索引元数据 (Index Metadata)

| 属性 | 统计值 / 事实 | 凭据与说明 |
|---|---|---|
| **generated_at** | `2026-08-25` | Stage 1.6D deployment authorization/runbook governance 更新日期；非全仓重新扫描 |
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
| **Alpha 研究方法论** | [.agent/rules/L2_Alpha_Research_Methodology.md](../../.agent/rules/L2_Alpha_Research_Methodology.md) | N/A | N/A | N/A | N/A | 项目级研究方法 SSOT；L0/L1 优先级更高 |
| **Stage 1.5D** (公告采集+BAPI详情) | [1.5D Design](../designs/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-design_CN.md) | [1.5D BAPI Plan](../plans/2026-07-22-external-signal-shadow-lab-stage1-5d-bapi-article-detail-source-hotfix-implementation-plan_CN.md) | [1.5D Review](../reviews/2026-06-24-external-signal-shadow-lab-stage1-5d-live-event-source-smoke-collector-review_CN.md) | `implemented` | `deployed` (PID 88580) | `server_runtime_snapshot...txt:L24` |
| **Stage 1.5F** (L2盘口观察+上线时间闸门) | [1.5F Design](../designs/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-design_CN.md) | [1.5F Terminal Hygiene Plan](../plans/2026-07-24-external-signal-shadow-lab-stage1-5f-historical-anchor-terminal-ignore-rejection-hygiene-hotfix-plan_CN.md) | [1.5F Review](../reviews/2026-06-26-external-signal-shadow-lab-stage1-5f-live-depth-observer-review_CN.md) | `implemented` | `deployed` (PID 88770) | `server_runtime_snapshot...txt:L26` |
| **Stage 1.5G** (盘口审查与跨Root准入) | [1.5G 跨Root准入 Design](../designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md) | [1.5G 跨Root准入 Plan](../plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md) | [1.5G 生产准入回执](../../data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/stage1_5g_cross_root_admission_summary.json) | `implemented` | `implemented` (Offline) | 102 项自动化测试全通；独立审计 COMPLETE；通过 Gate 3 样本数量门槛（2 篇独立公告、2 个父事件、8 个正式子标的 clean pass）；下游消费强制 Fail-Closed 硬阻断 |
| **Stage 1.5H** (跨Root流动性摩擦诊断) | [1.5H V3 Design](../designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md) | [1.5H V3 Plan](../plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md) | [1.5H V3 生产诊断回执](../../data/external_signal_shadow/stage1_5h/v3_cross_root_friction/stage1_5h_v3_cross_root_friction_20261001T120000Z/stage1_5h_v3_cross_root_friction_summary.json) | `implemented` | `implemented` (Offline) | 26 项自动化测试通过；独立审计评定 COMPLETE；基于 1.5G 的 2 个父事件与 8 个子标的完成 P95 滑点摩擦诊断；结论保持 `evidence_insufficient`，`stage1_5g_gate3_complete=false`；下游消费强制 Fail-Closed 硬阻断，无任何交易或执行权限 |
| **Stage 1.3 R10** (历史信号准入前置校验) | [1.3 R10 Design](../designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md) | [1.3 R10 Plan](../plans/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-implementation-plan_CN.md) | Task 6 Independent Review Receipt (`7671bd...`) & Completion Audit (Commit `8c6f3a0`) | `implemented` | `implemented` (Offline) | 69 项自动化测试通过；独立审计评定 COMPLETE；下游消费者硬阻断；严禁任何收益泄漏或实盘权限 |
| **Stage 1.6 Futures Delisting** | [1.6D Deployment Authorization Design](../designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md) | [1.6D Runbook Governance Plan](../plans/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook-governance-implementation-plan_CN.md) | [1.6C H2 Completion Audit](../reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md) | `implemented_through_1_6C` | `1_6D_not_deployed` | [Current 1.6D Runbook](../ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md)；下一步是 target preflight transcript，随后仍需 explicit user deployment authorization |

---

## 3. External Signal Shadow Lab (Stage 0 – 1.5H)

| Stage | Document Type | File | Status | Decision | Implemented | Deployed | Supersedes | Superseded By | Notes |
|---|---|---|---|---|---|---|---|---|---|
| **Stage 0** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage0-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 基础设施前置检查完成 |
| **Stage 1.1** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage1-1-manual-payload-dry-run-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 手动 Payload Dry Run 审查 |
| **Stage 1.2** | Review | [docs/reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md](../reviews/2026-06-12-external-signal-shadow-lab-stage1-2-gate-public-read-only-collector-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 只读采集关卡通过 |
| **Stage 1.3** | Review | [docs/reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md](../reviews/2026-06-13-external-signal-shadow-lab-stage1-3-candidate-signal-discovery-review_CN.md) | `historical_reference` | Passed | Yes | Completed | None | None | 候选信号发现完成 |
| **Stage 1.3 R10** | Design | [docs/designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md](../designs/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-design_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | None | 历史信号准入前置校验设计规范 (L2 方法论落地、PIT 与结构化只读门禁) |
| **Stage 1.3 R10** | Plan | [docs/plans/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-implementation-plan_CN.md](../plans/2026-09-29-external-signal-shadow-lab-stage1-3-r10-readmission-preflight-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | None | 历史信号准入前置校验实施计划 (69 项测试全通，审计评定 COMPLETE，Commit `8c6f3a0`) |
| **Stage 1.4A** | Review | [docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md](../reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md) | `superseded` | Feasibility Degraded | Yes | Completed | None | Stage 1.4E | 衍生品压力数据受限于交易所限频 |
| **Stage 1.4B** | Review | [docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md](../reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md) | `historical_reference` | `stopped_crowding_only` | Yes | Completed | None | Stage 1.4C | 21 events / 6 days; 500 baseline resampling trials are not independent opportunities; evidence sparse/concentrated, not a full derivatives-stress or no-Alpha conclusion |
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
| **Stage 1.5G** | Design | [docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md](../designs/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-design_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | None | 跨 Root 事件族准入设计规范 (Gate 3 样本数量门槛、L2 独立事件聚类、13 项 false 治理安全标志) |
| **Stage 1.5G** | Plan | [docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md](../plans/2026-09-30-external-signal-shadow-lab-stage1-5g-cross-root-event-family-admission-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Offline Tool | None | None | 跨 Root 事件族准入实施计划 (102 项测试全通，审计评定 COMPLETE，产出首份生产回执，下游强制 Fail-Closed) |
| **Stage 1.5G** | Receipt | [data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/stage1_5g_cross_root_admission_summary.json](../../data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/stage1_5g_cross_root_admission_summary.json) | `current_authority` | Admission Pass | Yes | Offline Tool | 2026-09-23 Moonshot / 2026-09-30 Batch7 | None | 首份跨 Root 生产准入回执：2 篇独立公告、2 个父事件、8 个子标的 clean pass；达成 Gate 3 样本数量门槛 |
| **Stage 1.5H** (历史) | Design | [docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md](../designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md) | `historical_reference` | Approved | Yes | Offline Tool | 2026-07-12 Static Proxy Design | Stage 1.5H V3 | 静态只读报告生成器治理规范 (已被 Stage 1.5H V3 跨 Root 流动性摩擦诊断替代) |
| **Stage 1.5H** (历史) | Plan | [docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md](../plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md) | `historical_reference` | Approved | Yes | Offline Tool | None | Stage 1.5H V3 | 静态只读报告实施规范 |
| **Stage 1.5H** (历史) | Review | [docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md](../reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md) | `historical_reference` | Passed | Yes | Offline Tool | None | Stage 1.5H V3 | 审定证实严禁交易/无模拟器解构；原始运行 artifact 未同步进本地 |
| **Stage 1.5H V3** | Design | [docs/designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md](../designs/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-design_CN.md) | `current_authority` | Approved | Yes | Offline Tool | 2026-07-12 1.5H Design | None | 跨 Root 流动性摩擦只读诊断规范 (P95 滑点摩擦诊断、无消费/交易授权、14 项 false 否定授权向量) |
| **Stage 1.5H V3** | Plan | [docs/plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md](../plans/2026-09-30-external-signal-shadow-lab-stage1-5h-v3-cross-root-liquidity-friction-diagnostic-implementation-plan_CN.md) | `current_authority` | Approved | Yes | Offline Tool | 2026-07-12 1.5H Plan | None | 跨 Root 流动性摩擦诊断实施计划 (26 项测试全通，3 轮闭环审计 COMPLETE，产出生产诊断回执与 Markdown 报告) |
| **Stage 1.5H V3** | Receipt | [data/external_signal_shadow/stage1_5h/v3_cross_root_friction/stage1_5h_v3_cross_root_friction_20261001T120000Z/stage1_5h_v3_cross_root_friction_summary.json](../../data/external_signal_shadow/stage1_5h/v3_cross_root_friction/stage1_5h_v3_cross_root_friction_20261001T120000Z/stage1_5h_v3_cross_root_friction_summary.json) | `current_authority` | Diagnostic Complete | Yes | Offline Tool | None | None | 生产诊断回执：8 个子标的 P95 流动性摩擦评估；研究结论 strictly `evidence_insufficient`；`stage1_5g_gate3_complete=false`；无 Alpha/交易授权 |

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
- **状态**：`implemented` (核心策略在 `configs/base.py`) / `stopped_no_promotion` (Route C1 price-only proxy)
- **核心文档**：
  - [docs/plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md](../plans/2026-05-26-trend-liquidation-phase1a-implementation-plan.md) (`implemented`)
  - [docs/plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md](../plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md) (`implemented`)
  - [docs/reviews/2026-07-05-route-c1-live-smoke-7d-review.md](../reviews/2026-07-05-route-c1-live-smoke-7d-review.md) (`stopped_no_promotion`: 904 / 1536 baseline/control matches; 58.85416667% < 70%; economic edge not established)
- **结论**：Route A/B 受到 API 限频与数据完整性拦截，Route C1 纯价格代理因 baseline/control matching failed 而停止推广，不构成成本后 EV 或胜率证伪；现仅保留 1h 波动率突破 (2.5x) + OI 动量方向性框架。

### 4.4 Cross-Sectional Factor Lab (截面因子实验室)
- **状态**：`historical_reference` / `retain_closed_for_tested_price_only_specification`
- **核心文档**：
  - [docs/strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md](../strategy_specs/cross_sectional_factor_lab_implementation_guide_CN_v3.md) (`historical_reference`)
  - [docs/reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md](../reviews/2026-06-09-cross-sectional-factor-lab-stageA1-closure-review_CN.md) (`review_approved`)
  - [docs/reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md](../reviews/2026-06-10-cross-sectional-factor-lab-stageA2-cmom-diagnostic-review_CN.md) (`retain_closed_for_tested_price_only_specification`: tested 30d/14d pure-price momentum had negative 30 bps cost-scenario portfolio performance and large drawdowns)
- **结论**：已测试 pure-price 截面动量规格保持关闭；该结果不评估、也不证伪所有 cross-sectional factors。任何非价格因子研究必须另起 L2 Design。

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
3. **Stage 1.5G 离线盘口质量审查与跨 Root 准入链**：
   `单 Root 审查: Design (2026-07-06) -> Plan (2026-07-11) -> Summary (Clean/Quarantine)` -> `跨 Root 准入: Design (2026-09-30) -> Plan (2026-09-30) -> Code (stage1_5g_cross_root_event_family_admission.py) -> Test (102 passed) -> Production Receipt (stage1_5g_cross_root_admission_20260930T104859Z)`
4. **Stage 1.5H 静态只读报告生成链**：
   `Design (2026-07-12 Governance Design)` -> `Plan (2026-07-12 Plan)` -> `Review (2026-07-12 Review)` -> `Code (scripts/.../review_stage1_5h_*)` -> `Test (tests/.../test_review_stage1_5h_*)` -> `Deployment (Offline Report Tool)` -> `Runtime Evidence (stage1_5h...summary.json)`
5. **Stage 1.6 Futures Delisting 历史证据与审计链**：
   `1.6A Source/Schema Contract (2026-08-18)` -> `1.6B Historical Capture and Sealed Export` -> `1.6C Sealed-Export Adapter v2` -> `H2 Grammar Delta` -> `Independent Completed-Consumer Audit (source_audit_passed=true)` -> `1.6D Deployment Authorization Design` -> `1.6D current runbook` -> `target preflight transcript` -> `explicit user deployment authorization` -> `1.6D Live Observation (not deployed)`。

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

1. **Stage 1.5G 事件族样本量阻塞（数量门槛已解封，连续运行观测维持）**：
   - **证据文件**：`data/external_signal_shadow/stage1_5g/event_family_admissions/stage1_5g_cross_root_admission_20260930T104859Z/stage1_5g_cross_root_admission_summary.json`
   - **内容**：跨 Root 准入已成功准入 2 篇独立公告、2 个父事件、8 个子标的（`MOONSHOTUSDT` + 7 个 `batch7` 标的），已满足配置的事件族样本数量门槛（$\ge 3$ 个标的且 $\ge 2$ 篇公告）。
   - **解封与后续要求**：维持服务器 1.5D 与 1.5F 连续运行以捕获更多独立样本，同时推进下游 Stage 1.5H 执行代理仿真器设计。

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
4. **Alpha / 策略研究条件路由**：
   - 若任务涉及 alpha discovery、策略假设、event study、factor、replay/backtest、策略评估、promotion/falsification、expectancy、PnL 或 economic-edge claim，必须额外读取 `.agent/rules/L2_Alpha_Research_Methodology.md`。
   - L2 只规范研究方法，不覆盖 L0/L1，也不允许把 `phenomenon_supported`、`alpha_candidate` 或统计正期望升级为 paper/live/execution authority。
