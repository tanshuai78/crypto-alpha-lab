# External Signal Shadow Lab Stage 1.4C Joint Decision Review

日期：2026-06-18

## 1. 一句话结论

当前最合理的正式路线收敛是：

```text
停止 crowding-only 主线
继续 liquidation 主线
暂不开放 full composite replay
```

也就是说：

- `B-Lite failed` 是正式失败结论
- `LQ30 promising` 是正式保留结论
- 这两者并不矛盾

它们共同说明的是：

```text
funding / OI / price 单独不够强；
但 liquidation-assisted 路线仍值得继续积累和等待更强证据。
```

---

## 2. 当前两条子线分别说明什么

### 2.1 B-Lite failed 说明什么

`Stage 1.4B-Lite` 已经用真实输入、正式 `500 trials` random baseline 跑完。
当前结论是：

```text
crowding_lite_failed
```

它的正确含义是：

- `funding / OI / futures price` 这组三元 crowding-only 事件
- 在当前冻结定义下
- 没有形成足够密度、足够跨日、足够分散的独立研究分支

它的错误含义是：

- derivatives stress 全线失败
- liquidation 这条腿没价值
- full composite 已被证伪

### 2.2 LQ30 promising 说明什么

`Stage 1.4A-LQ30` 的结论是：

```text
liquidation_diagnostic_promising
continue_accumulating_exact_history
```

它的正确含义是：

- 本地 liquidation snapshot 数据值得继续积累
- 当前继续等更长 liquidation 历史不是盲等
- 这条线还有继续投入的价值

它的错误含义是：

- liquidation alpha 已成立
- full composite 已通过
- paper/live 可以开放

---

## 3. 为什么两者不矛盾

这两条子线研究的不是同一个问题。

### B-Lite 研究的问题

```text
如果完全不依赖 liquidation，
只看 funding / OI / futures price，
能不能单独形成一条稳定的 crowding-only 分支？
```

答案是：不能。

### LQ30 研究的问题

```text
本地 liquidation snapshot 数据本身，
是否已经显示出值得继续积累的密度、覆盖和状态切换价值？
```

答案是：可以继续积累。

所以：

```text
crowding-only 失败
+
liquidation 数据腿保留
=
当前主线应回到 liquidation-assisted 方向
```

---

## 4. liquidation 事件更少，是不是反而更危险？

会更难研究，但不自动更差。

需要明确两件事：

1. liquidation 事件更少，是正常现象
2. 更少不代表没有价值

原因很简单：

- `funding / OI / price` 更像“市场变得拥挤了”
- `liquidation` 更像“市场真的开始被迫出清了”

前者更常见，后者更少见。

所以 liquidation 的目标从来不是：

```text
比 crowding-only 事件更多
```

而是：

```text
哪怕更少，也更接近关键状态切换点
```

因此，liquidation 分支更适合被当成 **rare-event branch**，而不是普通高频事件分支。

---

## 5. `100 个事件 / 20 天` 这些门槛应该怎么理解

这些门槛不是金融行业宇宙真理。
它们更像是：

```text
研究级继续投入门槛
```

而不是：

```text
所有探索阶段都必须满足的自然门槛
```

因此本轮 Joint Decision Review 的判断是：

- 对 `B-Lite` 这种 crowding-only 分支，这套门槛是合适的
- 对 `liquidation` 这种 rare-event 分支，这套门槛不能直接照搬成早期否决标准

也就是说：

```text
B-Lite 可以被正式打回
但 liquidation 不应因为“事件少”就被同步打回
```

---

## 6. 正式联合结论

当前阶段的正式联合结论是：

```text
joint_decision = continue_liquidation_primary_track
crowding_only_branch = formally_stopped
full_composite_design_allowed = false_for_now
```

更直白地说：

1. `funding / OI / price` 单独这条线，不再继续当主线调参
2. `local forceOrder snapshot` 这条 liquidation 线，继续积累历史
3. 在 liquidation 历史更长、或 vendor-quality liquidation 更明确之前，不进入 fuller composite replay design

---

## 7. 下一步建议

下一步推荐路线：

```text
1. 继续积累本地 liquidation 历史
2. 保持 B-Lite 结论封板，不再继续用 crowding-only 当主线调参
3. 等 liquidation 历史更长后，再进入 fuller composite decision
```

如果后续需要新的文档阶段，建议命名为：

```text
Stage 1.4D Fuller Composite Readiness Review
```

而不是立刻跳到策略或执行阶段。

---

## 8. 本轮能证明什么 / 不能证明什么

### 能证明

- crowding-only 支线已经被正式证伪为“不适合继续当主线”
- liquidation 数据腿仍值得继续积累
- 当前研究路线应回到 liquidation-assisted 方向

### 不能证明

- liquidation alpha 已成立
- full composite 已成立
- 未来一定能得到可交易策略
- 当前就值得进入 paper/live

---

## 9. 最终一句话

这次 Stage 1.4C 的真正结论不是“我们失败了”，而是：

```text
我们已经用低成本正式淘汰了 crowding-only 主线，
并把研究重心收敛回更可能有信息量的 liquidation-assisted 路线。
```
