# External Signal Shadow Lab Stage 1.4D Fuller Composite Readiness Review Design

日期：2026-06-19

## 1. 目标

Stage 1.4D 不是新的 alpha 回测阶段，也不是新的数据接入阶段。
它是一个 **readiness review（准入评审层）**，用于回答：

```text
在 Stage 1.4C 已经正式收敛出
“停止 crowding-only 主线、继续 liquidation-assisted 主线”
之后，我们当前是否已经具备进入 fuller composite replay 的条件？
```

这里的 fuller composite 指的是：

```text
liquidation
+ funding
+ OI
+ futures price
(+ optional orderbook / proxy diagnostic if later justified)
```

Stage 1.4D 的职责不是证明 alpha 成立，而是正式判断：

- liquidation 数据腿现在是“值得继续积累”，还是已经“足够支持更完整 replay 设计”？
- 当前 local forceOrder snapshot 是否仍只是 diagnostic-grade 资产，还是已经接近 research-grade input？
- 是否必须引入 vendor-grade liquidation sample，还是本地积累历史已经足以先进入 fuller replay？
- rare-event liquidation 分支是否已经跨过“探索可继续”门槛，进入“研究可升级”门槛？

本阶段的正确输出是：

```text
fuller_composite_replay_design_allowed = true | false
primary_blocker = ...
next_action = ...
```

本阶段明确 **不输出**：

- alpha pass
- strategy ready
- paper/live permission
- liquidation alpha confirmed
- final parameter search approval

---

## 2. 输入证据

Stage 1.4D 只接受已经完成的上游证据，不重新做自由探索。

### 2.1 Stage 1.4A-LQ30 输入

来自：
[2026-06-17-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-real-review_CN.md](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/reviews/2026-06-17-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-real-review_CN.md)

当前已知：

```text
decision = liquidation_diagnostic_promising
next_action = continue_accumulating_exact_history
truth_level = local_force_order_snapshot_rows_not_complete_tape
```

这说明：

- liquidation 数据腿值得继续积累
- 当前不是盲等
- 但 truth level 仍然偏弱，不是完整 liquidation tape

### 2.2 Stage 1.4B-Lite 输入

来自：
[2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md)

当前已知：

```text
decision = crowding_lite_failed
primary_blocker = day_concentration_limit_exceeded
```

这说明：

- crowding-only 支线不再继续当主线
- fuller composite 不能再假设“funding/OI/price 自己就够强”
- 如果未来 fuller composite 要成立，liquidation 这条腿必须提供额外信息量

### 2.3 Stage 1.4C 输入

来自：
[2026-06-18-external-signal-shadow-lab-stage1-4c-joint-decision-review_CN.md](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4c-joint-decision-review_CN.md)

当前联合结论：

```text
joint_decision = continue_liquidation_primary_track
crowding_only_branch = formally_stopped
full_composite_design_allowed = false_for_now
```

这意味着 `Stage 1.4D` 不是路线选择文档，而是路线升级文档。

---

## 3. Stage 1.4D 需要回答的核心问题

### 3.1 liquidation 数据腿现在是 Level A 还是 Level B？

沿用 Stage 1.4C 的两级解释：

```text
Level A = worth accumulating / diagnostic-positive
Level B = sufficient for fuller composite replay design
```

Stage 1.4D 的第一任务就是判断：

```text
当前 local liquidation history 仍然只是 Level A，
还是已经进入 Level B？
```

### 3.2 当前研究门槛是否需要对 rare-event 分支分级？

Stage 1.4C 已经指出：

- `event_count >= 100`
- `event_days >= 20`
- `top_5_positive_events_gross_profit_share <= 0.30`

更像是 **研究级批准门槛**，不应直接等同于所有 rare-event 早期否决门槛。

Stage 1.4D 需要正式把门槛分成两层：

```text
Tier 1: readiness-to-continue gate
Tier 2: readiness-for-fuller-composite-design gate
```

这一步非常关键，否则 liquidation 分支会被错误地用 crowding-only 的否决方式处理。

### 3.3 未来 fuller composite 的最小输入集合是什么？

Stage 1.4D 不设计完整策略，但必须定义最小研究输入集合：

```text
required:
- liquidation rows / buckets
- funding as-of series
- OI as-of series
- futures price bars

optional:
- orderbook depth / imbalance diagnostic
- vendor-grade liquidation sample
```

并回答：

```text
当前本地数据是否足以满足 required set？
```

---

## 4. Fuller Composite Readiness 的判断框架

Stage 1.4D 使用四层判断框架。

### 4.1 数据成熟度（Data Maturity）

看的是 liquidation 数据本身是否已经从“可继续积累”走向“可升级研究”。

必须评估：

- liquidation_history_days
- event_days
- symbols_with_events
- notional concentration
- recent event density
- truth level
- collector gap verifiability

### 4.2 对齐成熟度（Alignment Maturity）

看的是 liquidation 与 funding / OI / price 的联合可用性，而不是各自单独可用性。

必须评估：

- alignment_overlap_available
- overlap_event_days
- symbols_with_alignment_overlap
- stress-condition overlap 是否不再只是字段存在，而是有足够状态差异

### 4.3 解释成熟度（Interpretation Maturity）

看的是我们当前是否已经可以合理解释：

```text
liquidation 这条腿提供了 B-Lite 缺失的额外信息量
```

如果当前证据只能说明“liquidation 数据值得继续收”，但还不能说明“它足以进入 fuller composite replay”，则必须保持保守。

### 4.4 升级成本合理性（Upgrade Cost Reasonableness）

Stage 1.4D 还要正式回答：

- 继续本地积累历史是否是最低摩擦路径？
- vendor sample 是否是必要条件，还是可选增强项？
- fuller composite 的下一步工程复杂度，是否与当前证据强度匹配？

如果证据仍然偏弱，而工程复杂度过高，则应继续等待，不升级。

---

## 5. Stage 1.4D 的正式输出

Stage 1.4D 顶层只允许以下三种结论：

### 5.1 `fuller_composite_not_ready_continue_accumulating`

含义：

- liquidation 主线保留
- 当前还不足以进入 fuller composite design
- 继续本地积累历史

### 5.2 `fuller_composite_not_ready_vendor_or_history_needed`

含义：

- liquidation 主线保留
- 当前 readiness 的主要缺口是 truth level / history length / source quality
- 需要更长本地历史或 vendor-grade liquidation sample

### 5.3 `fuller_composite_design_allowed`

含义：

- 当前证据已经足以支持下一步 fuller composite replay design
- 仍然不代表 alpha 成立
- 仍然不允许 paper/live

---

## 6. 通过门槛的建议结构

Stage 1.4D 不直接继承 B-Lite 那套门槛，而是使用分级门槛。

### Tier 1: 继续积累门槛（Continue Gate）

这一级回答“是否继续 liquidation 主线”。

建议至少要求：

```text
liquidation_history_days >= 15
symbols_with_events >= 3
event_days >= 10
alignment_overlap_available = true
major source-quality blocker absent
```

### Tier 2: Fuller Composite 设计准入门槛（Design Readiness Gate）

这一级回答“是否允许进入 fuller composite design”。

建议至少要求：

```text
liquidation_history_days >= 45 or vendor-grade sample available
symbols_with_events >= 5
event_days >= 20
overlap_event_days >= 15
max_single_day_event_share below configured readiness cap
truth_level not worse than local_force_order_snapshot_rows_not_complete_tape
collector/source-quality risk explicitly bounded
```

注意：这里仍然不是 final alpha gate，只是 design readiness gate。

---

## 7. 与后续阶段的关系

如果 `Stage 1.4D` 输出：

```text
fuller_composite_design_allowed
```

下一阶段建议命名为：

```text
Stage 1.4E Fuller Composite Replay Design
```

如果 `Stage 1.4D` 输出：

```text
fuller_composite_not_ready_continue_accumulating
```

则继续维持：

```text
primary_track = local liquidation accumulation
secondary_track = none_for_crowding_only
```

---

## 8. 本阶段不解决什么

Stage 1.4D 明确不解决：

- liquidation alpha 是否成立
- fuller composite 的最终参数搜索
- execution feasibility
- paper/live readiness
- strategy launch decision

Stage 1.4D 只解决：

```text
是否具备进入 fuller composite replay design 的资格
```
