# Stage 1.6 Futures Delisting 路线地图

**日期:** 2026-08-24  
**状态:** `current_navigation_authority`  
**用途:** 统一 Stage 1.6 的研究对象、实施阶段、旧命名映射与当前运行边界。  
**不改变:** 任何已批准 Design/Plan 的技术契约、代码模块名、sealed export、历史 artifact 或交易权限。

## 1. 编号规则

Stage 数字只对应一个研究事件；字母只表示该事件的可验证实施阶段。

```text
Stage 1.6 = Binance USD-M Futures Delisting 研究路线

1.6A = source/schema/effective-time contract
1.6B = local historical capture and sealed export
1.6C = historical semantic source audit
1.6D = VPS live source observation and PIT provenance
1.6E = market-data / liquidity coverage audit
1.6F = matched historical mechanism diagnostic and replay design
1.6G = route conclusion: stop, remain diagnostic, or propose a separate alpha design
```

ETF Flow、Prediction Market、Token Unlock、Exchange Flow 和 Security Incident 是独立研究候选，不占用 Stage 1.6 的实施字母。它们只有在各自正式立项后才获得新的 Stage 数字和自己的 A--G 生命周期。

## 2. 当前路线状态

| 阶段 | 目标 | 状态 | 证据 / 当前边界 |
|---|---|---|---|
| 1.6A | 冻结官方来源、USD-M perpetual scope、时间与证据语义 | `completed` | 2026-08-18 baseline Design；不产生交易结论 |
| 1.6B | 本地历史公告抓取、双 sweep、详情 raw bytes、terminal status 与 sealed export | `completed` | 冻结 export `e9ec315753ea...b2007734`；历史下载不证明 PIT |
| 1.6C | 用独立 adapter 重新计算候选、语义、指标与 completion verdict | `completed` | G2 root `h2_g2_remediated_20260824T061701Z`；`source_audit_passed=true` |
| 1.6D | VPS 持续观察官方公告首次发现与可信详情可得时间 | `deployed_observing` | Operator 于 2026-08-30 报告 tmux 会话 `stage1_6d_live_stage1_6d_live_20260828T075150Z` 正在运行；仍仅记录 public source observation，runbook health gate 是持续运行事实的唯一验证方式 |
| 1.6E-A | 验证固定公开 REST market-data source profile 的单次有界能力与血统 | `completed` | 2026-09-03 VPS 实机探测封签完成；Manifest `e918b344...74b3`，4 profile 全部 PASS；详见 completion audit |
| 1.6E-B | live semantic trigger 与事件级 market-data observer | `not_started` | 待编写 1.6E-B Design；不得由 1.6D raw source evidence 直接触发 |
| 1.6F | 以匹配控制组检验强制流/流动性机制，并另行设计 replay | `not_started` | 不得直接生成方向或收益结论 |
| 1.6G | 对研究路线作 stop / diagnostic-only / separate-alpha-design 决定 | `not_started` | 仅在 1.6E--F 完成后讨论 |

所有阶段维持：

```text
RISK_LIVE_TRADING_ENABLED = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

## 3. 旧命名映射

历史路径不可重命名；下表只提供阅读和治理映射。

| 现有名称 / artifact | 在本路线地图中的含义 |
|---|---|
| `stage1_6a_futures_delisting_*` baseline Design / fixture audit | 1.6A 的初始 semantic contract |
| `stage1_6b_canonical_source_*` modules and runners | 1.6B 历史采集与 1.6D 实时观测共用的 legacy producer implementation namespace |
| `stage1_6b/historical_backfill/.../sealed_exports/...` | 1.6B sealed historical evidence |
| `stage1_6a_sealed_export_*` adapter and storage | 1.6C historical semantic audit consumer |
| 2026-08-24 H2 grammar delta | 1.6C 对真实 BAPI body grammar 的版本化修补 |

`stage1_6b_*` 中的字母 B 是既有代码/证据命名，不等于旧策略候选文档里的“ETF Flow 1.6B”。今后新增人类可读文档必须使用本路线地图的阶段含义。

## 4. 当前权威文档链

1. [1.6A baseline source/schema/effective-time Design](../designs/2026-08-18-external-signal-shadow-lab-stage1-6a-futures-delisting-source-schema-effective-time-design_CN.md)
2. [1.6B canonical official source producer Design](../designs/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-official-source-capture-live-observation-provenance-design_CN.md)
3. [1.6C sealed-export adapter v2 Design](../designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-historical-source-audit-adapter-design-v2_CN.md)
4. [1.6C derived-artifact schema delta](../designs/2026-08-23-external-signal-shadow-lab-stage1-6a-sealed-export-adapter-derived-artifact-schema-delta-design_CN.md)
5. [1.6C H2 grammar delta](../designs/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-design_CN.md)
6. [1.6C H2 completion audit](../reviews/2026-08-24-external-signal-shadow-lab-stage1-6a-bapi-h2-versioned-body-grammar-replay-delta-completion-audit_CN.md)
7. [1.6D VPS deployment authorization Design](../designs/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-deployment-authorization-design_CN.md)
8. [1.6D current VPS live-source-observation runbook](../ops/2026-08-25-external-signal-shadow-lab-stage1-6d-vps-live-source-observation-runbook_CN.md)
9. [1.6D historical preflight reference](../reviews/2026-08-19-external-signal-shadow-lab-stage1-6b-canonical-source-deployment-checklist_CN.md) (`historical_preflight_reference`; not the current procedure)
10. [1.6E-A capability audit Design](../designs/2026-08-30-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-design_CN.md)
11. [1.6E-A capability audit Plan](../plans/2026-08-31-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-implementation-plan_CN.md)
12. [1.6E-A capability audit Completion Audit](../reviews/2026-08-31-external-signal-shadow-lab-stage1-6e-a-market-data-source-capability-audit-completion-audit_CN.md)

旧策略路线文档保留其候选选择与优先级分析价值；其 `1.6B`、`1.6C` 等候选编号不再作为当前工程实施编号 authority。

## 5. 下一项唯一工作

下一项是 **Stage 1.6E-B live semantic trigger 与事件级 market-data observer Design**。

1.6E-A 已完成 VPS 实机能力证明，证实生产节点能够合规访问币安公开行情端点并防篡改持久化。下一步 Stage 1.6E-B 将设计针对下架公告的实时语义触发与事件级市场深度观测器。1.6D 保持运行并按 current runbook 做只读 health gate；不得为开始 1.6E-B 而重启、复用、修改或重新密封任何 1.6D/1.6E-A root。
