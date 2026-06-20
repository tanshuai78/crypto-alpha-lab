# External Signal Shadow Lab Stage 1.4C Joint Decision Review Design

日期：2026-06-18

## 1. 目标

Stage 1.4C 不是新的 alpha 回测，也不是新的数据接入工程。
它是一个 **联合决策层**，用于把已经完成的两条子线结果正式收敛成下一步研究路线：

```text
Stage 1.4A-LQ30 Local ForceOrder Snapshot Diagnostic
+
Stage 1.4B-Lite Funding/OI/Price Crowding Replay
->
Stage 1.4C Joint Decision Review
```

Stage 1.4C 要回答的核心问题不是“策略是否成立”，而是：

```text
在当前证据下，哪条路线应该继续投入，哪条路线应该停止，
以及 rare-event 分支是否需要和普通 crowding-only 分支使用不同的研究门槛？
```

本阶段的正确产出是：

- 对 `B-Lite failed` 的正确解释
- 对 `LQ30 promising` 的正确解释
- 对“liquidation 事件更少是否反而更有信息量”的明确判断框架
- 对下一阶段是否继续等待 90d liquidation、是否需要 vendor sample、是否允许 full composite design 的正式决策

本阶段明确 **不输出**：

- alpha pass
- paper/live
- full composite replay pass
- strategy ready

---

## 2. 当前证据输入

### 2.1 LQ30 真实输入结论

来自：
[2026-06-17-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-real-review_CN.md](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/reviews/2026-06-17-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-real-review_CN.md)

当前已知：

```text
decision = liquidation_diagnostic_promising
next_action = continue_accumulating_exact_history
truth_level = local_force_order_snapshot_rows_not_complete_tape
```

它说明的是：

- 本地 liquidation snapshot 数据已经显示出足够的数据密度、最小时间对齐能力、以及可继续积累的价值
- 当前继续积累本地 liquidation 历史不是“盲等”
- 但它仍不是完整 liquidation tape，也不等于 alpha 已成立

### 2.2 B-Lite 正式 500 trials 真实输入结论

来自：
[2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md](/Users/tanshuai/Desktop/AI-test/crypto-alpha-lab/docs/reviews/2026-06-18-external-signal-shadow-lab-stage1-4b-lite-funding-oi-price-crowding-replay-500trials-real-review_CN.md)

当前已知：

```text
decision = crowding_lite_failed
primary_blocker = day_concentration_limit_exceeded
random_baseline_trials = 500
```

它说明的是：

- `funding / OI / futures price` 这组三元 crowding-only label 在当前冻结参数下没有形成足够密度、足够跨日、足够分散的独立研究分支
- 该失败结论已经在 `10 / 50 / 500 trials` 下稳定出现
- 该失败只证伪了 `crowding-only` 支线，不证伪 liquidation-assisted composite

---

## 3. Stage 1.4C 需要解决的认知冲突

### 3.1 冲突 1：liquidation 事件更少，会不会更差？

不一定。

Stage 1.4C 必须明确区分：

- **事件数量少**
- **事件质量差**

在 derivatives stress 研究里，liquidation 更像“状态切换已经发生”的观察量；
funding / OI / price 更像“市场正在变拥挤”的状态量。

因此：

```text
liquidation 事件更少 = 正常
liquidation 事件更少 =/= 没有价值
```

真正需要回答的是：

```text
更少的 liquidation 事件，是否比更常见的 crowding-only 事件更接近关键状态切换点？
```

### 3.2 冲突 2：`100 个事件 / 20 天` 是否对 rare-event 分支过于严格？

Stage 1.4C 必须明确：

- `event_count >= 100`
- `event_days >= 20`
- `top_5_positive_events_gross_profit_share <= 0.30`

这些门槛是 **研究级批准门槛**，不是所有探索型分支都必须立刻满足的自然法则。

因此 Stage 1.4C 要区分两层：

```text
exploratory viability gate
vs
research-grade continuation gate
```

B-Lite 当前失败，说明它没有通过 research-grade continuation gate；
但 rare-event liquidation 分支是否必须使用同一套硬门槛，需要被明确讨论，而不是默认继承。

---

## 4. Stage 1.4C 的判断框架

Stage 1.4C 使用以下联合判断框架：

### 4.1 对 crowding-only 分支的解释

如果满足：

```text
B-Lite failed
AND
LQ30 promising
```

则默认解释为：

```text
crowding-only 不是主线
liquidation-assisted 路线仍值得继续
```

### 4.2 对 rare-event liquidation 分支的解释

Stage 1.4C 不要求 liquidation 分支立刻满足与 crowding-only 完全相同的样本门槛。
它应区分：

- **继续积累是否值得**
- **是否已经足够支持 full composite replay**

因此对 liquidation 分支采用两级状态：

```text
Level A: worth accumulating / diagnostic-positive
Level B: sufficient for fuller composite replay design
```

当前 LQ30 只足以支持 Level A，不足以直接升级到 Level B。

### 4.3 联合输出的正式状态

Stage 1.4C 顶层输出建议固定为：

```text
joint_decision = continue_liquidation_primary_track
crowding_only_branch = formally_stopped
full_composite_design_allowed = false_for_now
vendor_sample_priority = optional_not_required_now
```

---

## 5. Stage 1.4C 的正式结论模板

Stage 1.4C review 必须显式回答以下 5 个问题：

1. `B-Lite failed` 到底说明什么？
2. `LQ30 promising` 到底说明什么？
3. liquidation 事件更少是否自动构成负面证据？
4. 当前 `100 / 20 / 0.30` 这类门槛，哪些属于研究级批准门槛，哪些不应直接用于 rare-event 早期淘汰？
5. 下一步到底是：
   - 继续积累 liquidation
   - 等 vendor sample
   - 开 full composite design
   - 或停止整条路线

当前预期答案是：

```text
1. B-Lite failed = crowding-only 支线失败，不代表 composite 失败
2. LQ30 promising = 本地 liquidation snapshot 值得继续积累，不是盲等
3. liquidation 稀少是正常现象，不自动构成负面证据
4. 100/20/0.30 是研究级批准门槛，不应直接等同于 rare-event 早期否决门槛
5. 继续 liquidation 主线，停止 crowding-only 主线，暂不开放 full composite
```

---

## 6. Stage 1.4C 后的推荐路线

如果本轮 Joint Decision Review 按当前预期完成，则下一阶段路线应为：

```text
primary_track = continue_accumulating_local_liquidation_history
secondary_track = none_for_crowding_only
optional_track = vendor_liquidation_sample_if_low_friction
full_composite_design = deferred_until_more_liquidation_history
```

明确禁止的错误升级：

```text
B-Lite fail -> full composite fail
LQ30 promising -> alpha confirmed
LQ30 promising -> full replay allowed immediately
```

---

## 7. 本阶段不解决什么

Stage 1.4C 明确不解决：

- liquidation alpha 是否成立
- future full composite 的最佳阈值
- 是否应该立即采购 vendor data
- paper/live 是否允许

Stage 1.4C 只解决：

```text
路线选择
门槛解释
失败结论的正确边界
下一步研究资源如何分配
```
