# Binance Liquidation Snapshot Event Study Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this design task-by-task.

**Goal:** 用 Binance 公开历史 liquidation snapshot 替换失败的 Coinalyze `1m` 数据源，在尽量不改变既有 `1m shock -> fixed 5/10/15m response` 研究定义的前提下，验证 liquidation shock 结构是否在更连续的历史样本上得到支持。

**Architecture:** 这条分支不是新策略开发，而是一次数据源替换验证。第一轮固定使用 `2024-01 / 2024-02 / 2024-03` 三个连续月份、`BTC / ETH / SOL / XRP / DOGE` 五个币种、`1m` 价格与 `1m` liquidation snapshot 数据，在 Binance-only 范围内重跑现有 `1m shock event study`。研究方法默认保持不变，先过数据连续性与事件密度门槛，再判断跨月份结构是否成立。

**Tech Stack:** Python 3.11, pytest, JSON/JSONL, ZIP/CSV ingestion, Binance public historical data files, existing liquidation shock event-study scripts, markdown review + JSON summary artifacts.

---

## Background

当前 liquidation 主题的研究状态已经明确：

- `vol_breakout` 已退役。
- 当前版 `trend_regime/liquidation_cascade` 已退役。
- `5m liquidation-only baseline` 已退役。
- `1m shock event study` 在研究设计上曾出现 mean-reversion 倾向，但最终被 `Coinalyze 1m` 数据连续性与深度不足阻断，结论落在 `INSUFFICIENT_1M_DATA_DEPTH`。

因此，这条新分支的目标不是再换一套事件定义，而是优先回答一个更窄的问题：

- 如果只替换 `1m liquidation` 数据源，并保持研究定义尽量不变，原来的 `1m shock -> fixed 5/10/15m response` 研究线是否还能成立？

这条分支的价值在于做一次真正的 apples-to-apples 对照：

- 如果 Binance 历史样本下仍看不到稳定结构，更可能说明研究定义本身站不住；
- 如果 Binance 历史样本下结构明显改善，更可能说明前一轮主要是被 Coinalyze 的 `1m` 数据质量拖垮。

---

## Phase 1 Baseline Scope

第一轮只做最小、可复现、可比较的数据源替换验证，不扩写新研究问题。

### Data Scope

- Exchange: `Binance-only`
- Symbols: `BTC / ETH / SOL / XRP / DOGE`
- Windows:
  - `2024-01`
  - `2024-02`
  - `2024-03`
- Inputs:
  - `1m` price
  - `1m` liquidation snapshot

### Window Selection Rule

窗口选择采用固定月份，而不是先按 market regime 主观挑样：

- 先按月份下载、组织和复现；
- 后续再给月份补 regime 标签；
- 不在第一轮引入“高波动 / 低波动”主观筛样。

这条规则的目的，是降低窗口选择阶段的主观性，让第一轮结果更容易复核和复现。

### Method Boundary

第一轮默认完全沿用现有 `1m shock event study` 的研究定义：

- `1m` 单侧 liquidation shock
- `24h` trailing anomaly
- 绝对门槛
- dominance ratio
- 事件去重
- fixed `5 / 10 / 15m` response

允许做的适配仅限于：

- 将 Binance historical snapshot 规范化成当前 event-study 的输入格式；
- 处理 Binance 文件格式与既有脚本输入之间的 schema 映射；
- 不在第一轮修改事件逻辑、response 口径或阈值结构。

---

## Data Qualification Gates

这条 Binance 历史样本分支必须先过两层门槛，才允许进入结构分析。

### Gate 1: Continuity

每个币种、每个月都必须先验证 `1m` 数据是否足够连续，至少要求：

- `coverage_ratio >= 0.99`
- `max_gap_minutes <= 1`

这条门槛同时适用于：

- `1m liquidation snapshot`
- `1m price` 对齐结果

只要某个币种在某个月的数据连续性不合格，该月该币的样本就不能进入主研究结果。

### Gate 2: Event Density

即使连续性合格，如果三个月的 `shock events` 太少，这条线也不值得继续。第一轮至少同时检查：

- 三个月总事件数是否达到最低门槛
- 每个月是否都有最低事件数，而不是只靠单月支撑结论

第一轮先明确判据结构，不在设计文档里写死数字：

- 连续性先过
- 再看事件密度
- 再看 response structure

这意味着，这条分支不会因为“某个月有几个漂亮 shock”就自动通过。

---

## Structural Validation Outputs

如果连续性和事件密度都通过，第一轮应输出三类结果：

### 1. Data Qualification Outputs

- 每个币种、每个月的 `coverage_ratio`
- 每个币种、每个月的 `max_gap_minutes`
- 价格与 liquidation 的 join 完整性
- 哪些月份/币种进入主研究结果，哪些被排除

### 2. Event Density Outputs

- 三个月总事件数
- 每月事件数
- 是否满足总数与单月最低门槛

### 3. Structure Outputs

- continuation / mean reversion 的方向分布
- fixed `5 / 10 / 15m` response 的 response map
- 跨月份方向是否一致

第一轮的结论不是“策略能不能 live”，而是“换成 Binance 历史样本后，这套研究定义是否还站得住”。

---

## Decision States

这条分支的结论只能落在下列状态之一：

- `binance_snapshot_data_failed`
  - 连续性不过，数据源本身不合格
- `binance_snapshot_event_density_failed`
  - 数据连续，但 shock 事件太少
- `binance_snapshot_structure_not_confirmed`
  - 数据和事件数都够，但结构不稳定
- `binance_snapshot_structure_confirmed`
  - 数据、事件密度、跨月份结构都通过

即使得到 `binance_snapshot_structure_confirmed`，它也只代表：

- 这套研究定义在 Binance 历史样本上得到更强支持；
- 并不等于策略已经进入 live-safe 状态。

---

## Deferred Enhancements

以下增强项不进入 Phase 1 baseline，但如果第一轮通过，可以作为后续阶段推进。

### Data Expansion

- 扩展到更多月份
- 扩展到更多币种
- 对比不同下载组织方式（按月 / 按日）

### Regime Labeling

- 给 `2024-01 / 2024-02 / 2024-03` 打 market regime 标签
- 增加跨月份 regime 分层解释
- 比较平静 / 中等波动 / 高波动月份下的结构差异

### Binance-Specific Data Audit

- 强化 snapshot schema audit
- 强化 dedup / duplicate snapshot handling
- 对比 Binance historical snapshot 与未来自建 raw archive 的一致性

### Study Sensitivity

- 仅在 Phase 1 通过后，才允许做 Binance-specific event-definition sensitivity
- 例如：
  - dominance 阈值敏感性
  - absolute threshold 敏感性
  - dedup 逻辑敏感性

### Execution/Cost Layer

- 加入 cost sensitivity
- 加入 execution delay sensitivity
- 判断“结构存在”是否能转化为“个人可执行 edge”

所有增强项都应明确标记为：

- `out_of_scope_for_phase1`
- `only_if_phase1_passes`

---

## Escalation Conditions

只有在下面条件同时满足时，才允许进入增强阶段：

- 连续性门槛通过
- 事件密度门槛通过
- 跨月份结构方向一致
- 结果不是由单一月份支撑

如果这些条件不满足，就应停止在这条 Binance 历史样本分支上继续扩功能或调阈值。

---

## Deliverables

Phase 1 完成后，至少应落下这些产物：

- Binance 历史样本可用性 summary
- 数据对齐与连续性 audit
- event density summary
- response map summary
- 一份 markdown review
- 一份 JSON summary

建议后续实现计划直接落到：

- `docs/plans/2026-05-31-binance-liquidation-snapshot-event-study-implementation-plan.md`

并在 review 中明确写清：

- 本轮是数据源替换验证
- 不是最终策略推广结论

