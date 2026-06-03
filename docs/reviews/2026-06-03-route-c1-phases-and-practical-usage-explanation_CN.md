# Route C1 各阶段含义与实操用途说明

## 1. 这条线到底在研究什么

Route C1 研究的不是一个“直接预测涨跌、直接下单赚钱”的策略。

它研究的是一个更基础的问题：

> 当市场出现显著 liquidation shock 之后，接下来几分钟是否会进入一个更危险、更不适合进场的窗口？

这里的“更危险”主要指：

- 价格波动突然变大；
- 高低波动区间变宽；
- 最大不利波动变严重；
- 盘口可能变薄；
- spread 可能变宽；
- 实际执行成本可能上升。

所以，Route C1 更像一个：

```text
风险过滤器 / 不进场过滤器 / 执行风险预警层
```

而不是：

```text
独立进攻型 alpha 策略
```

---

## 2. 为什么不能一步到位，必须分阶段推进

因为这类研究最容易犯三种错：

1. 把历史样本里的巧合，当成稳定规律；
2. 把“价格更乱”误当成“执行风险一定更差”；
3. 在 live 样本还不够时，过早宣布结论成立。

所以 Route C1 要分成几层，一层一层回答不同问题。

这些阶段不是为了拖慢进度，而是为了防止我们在错误证据上做错误决策。

---

## 3. `price-only proxy` 是什么

### 3.1 它在做什么

`price-only proxy` 是最低成本的第一层验证。

它只看：

- liquidation shock 发生后；
- 未来 `5m / 10m / 15m` 的价格风险是否明显高于正常时段。

它关心的主要指标包括：

- realized volatility；
- high-low range；
- max adverse excursion；
- max absolute excursion。

它不看 orderbook，不看真实挂单成交，不看盘口厚度。

### 3.2 为什么叫 proxy

因为它不是直接测“执行风险”，而是先拿价格风险做替代信号。

也就是说，它先回答：

> 强平冲击之后，价格本身是不是明显变得更危险了？

如果连价格风险都没有明显恶化，那后面大概率没必要再继续做更重的 orderbook-aware 研究。

### 3.3 它回答的问题

它回答的是：

```text
这个方向值不值得继续研究？
```

它不回答：

```text
这个过滤器现在能不能上线？
```

### 3.4 当前状态

目前历史 `price-only proxy` 的结论是：

```text
promising
```

这表示：

- 历史 proxy 层面看到了风险恶化迹象；
- 这个方向暂时没有被否掉；
- 但还不能直接推广到 live 风控上线。

---

## 4. `live overlap audit` 是什么

### 4.1 它在做什么

`live overlap audit` 不是研究结论，它是数据准备检查。

它回答的问题是：

> liquidation、price、orderbook 这三类 live 数据，是否真的发生在同一个时间窗口里？

如果三类数据不同步，即使脚本能跑，也没有研究意义。

### 4.2 为什么这一步必须单独做

因为此前已经出现过典型问题：

- liquidation 用的是 2026 年 live 数据；
- `price-1m` 却误用了 2024 Q1 的历史 proxy 数据；
- 结果 overlap 全部是 `0h`。

这不是策略坏了，而是输入时间轴错位了。

所以 overlap audit 的作用是先确保：

```text
数据真的对上了，再讨论研究结论
```

### 4.3 这一步的几个状态

#### `route_c1_overlap_ready_for_price_only`

表示：

- liquidation 和 live `1m price` 已经形成有效重叠；
- 可以继续推进 `price-only` live 路径。

#### `route_c1_overlap_ready_for_orderbook_aware`

表示：

- liquidation、live `1m price`、orderbook 三者都已重叠；
- `BTC/ETH/SOL` 这些主集币种的 overlap 已满足 orderbook-aware 输入门槛；
- 可以进入 orderbook-aware 研究准备阶段。

### 4.4 当前状态

目前已经推进到：

```text
route_c1_overlap_ready_for_orderbook_aware
```

这表示：

- 输入链路已经准备好；
- 现在真正缺的不是数据类型，而是更多时间长度。

---

## 5. `orderbook-aware` 是什么

### 5.1 它和 `price-only` 的区别

`price-only` 只看价格；

`orderbook-aware` 则进一步看：

- spread 是否变宽；
- depth 是否变浅；
- impact cost 是否上升；
- maker 是否更容易被 adverse selection；
- 盘口恶化持续多久。

所以它关心的是：

> liquidation shock 后，执行环境是否也变差了？

### 5.2 为什么它更接近实盘

很多策略不是死在方向判断错，而是死在：

- spread 过宽；
- 深度突然不足；
- 市价吃单滑点超预算；
- maker 单挂出去反而接飞刀。

如果 Route C1 最终能证明：

> 强平后几分钟不仅价格更乱，而且盘口也更差

那它就能更像一个真实可用的执行风险过滤器。

### 5.3 当前这一步到底“过了”还是“没过”

这里必须区分两层含义。

#### A. `orderbook-aware input gate`

问的是：

> 数据是否足够做 orderbook-aware 研究？

这个现在已经通过了。

#### B. `orderbook-aware research conclusion`

问的是：

> spread / depth / impact 是否真的系统性恶化？

这个现在还没有正式计算并完成验证。

所以准确表述是：

```text
orderbook-aware 的输入门槛已通过，
但 orderbook-aware 的研究结论尚未完成。
```

这不是失败，而是研究还没走到那一步。

---

## 6. `7d live smoke` 是什么

### 6.1 它在做什么

`7d live smoke` 是第一个真正意义上的 live 小样本验证。

它要回答：

> 在真实 live 数据里，这个风险恶化现象有没有继续成立？

### 6.2 为什么是 7 天

因为：

- `1-2` 天太短，噪音大；
- `30` 天又太慢；
- `7` 天是一个比较合理的折中。

### 6.3 它和 overlap audit 的区别

overlap audit 只回答：

```text
能不能开始研究
```

`7d live smoke` 回答的是：

```text
研究方向在真实 live 数据中有没有继续成立
```

### 6.4 当前状态

当前大约只有：

```text
~72h overlap
```

还没有接近：

```text
168h
```

所以现在正确的状态是：

```text
input ready, time not ready
```

---

## 7. `30d forward` 是什么

### 7.1 它在做什么

`30d forward` 是更完整的前向验证。

它回答的问题是：

> 这个信号在更长的 live 窗口里，是否仍然稳定，而不是短期碰巧有效？

### 7.2 为什么要做这一步

一个方向即使在 7 天里表现不错，也可能是短期偶然现象。

只有拉长到 30 天，才更接近真正的稳定性验证。

### 7.3 它和 7d smoke 的关系

可以理解成：

- `7d smoke`：先看有没有延续迹象；
- `30d forward`：再看这种迹象能不能稳定站住。

---

## 8. 这些阶段为什么要一步步推进

因为每一层回答的问题都不一样。

### 第 1 层：`price-only proxy`

回答：

```text
这个方向值得继续研究吗？
```

### 第 2 层：`live overlap audit`

回答：

```text
数据是否真的对齐，可以支撑 live 研究？
```

### 第 3 层：`orderbook-aware`

回答：

```text
风险恶化是否不仅体现在价格，也体现在执行环境？
```

### 第 4 层：`7d live smoke`

回答：

```text
在真实 live 数据里，这个结论有没有继续成立？
```

### 第 5 层：`30d forward`

回答：

```text
这个现象是否足够稳定，值得进入更正式的 live 风控使用评估？
```

如果跳步，风险很大：

- 没做 proxy 就直接 live：容易在错误方向上浪费时间；
- 没做 overlap audit 就研究：容易时间轴错位；
- 只有 `72h` 就宣布成功：容易把短期噪音当成规律。

---

## 9. Route C1 既然不直接赚钱，有什么用

它的价值不在于“产生收益信号”，而在于“阻止坏交易”。

这类风控过滤器的目标通常是：

- 不在最危险的几分钟里贸然进场；
- 不在盘口明显恶化时按正常仓位去做单；
- 不让已有策略在最差时段把 edge 交给滑点和执行成本。

所以它的用途更像：

```text
风控层 / 执行保护层 / no-trade 过滤层
```

而不是：

```text
独立 alpha 引擎
```

---

## 10. 它在实操里会怎么用

如果后面 `price-only` 与 `orderbook-aware` 的 live 证据都成立，实盘里最可能的用法不是“单独上一套 Route C1 策略”，而是挂在现有策略前面。

### 用法 1：暂停入场

如果发生显著 liquidation shock：

- 接下来 `5m` / `10m`
- 暂停新的 maker / MR / carry 入场

目的：

- 避免在最危险的几分钟里误开仓。

### 用法 2：降低下单金额

不是完全不做，而是把：

- 正常 `1000 USDT`

降到：

- `300-500 USDT`

目的：

- 在高风险窗口里降低一次错误执行带来的伤害。

### 用法 3：提高执行保护

例如：

- 更严格的最大冲击成本限制；
- 更保守的 slippage reserve；
- 更短的 maker timeout；
- 更严格的 partial fill abort 条件。

### 用法 4：先 shadow，不直接接管 live

先记录：

- 如果这段时间本来要阻止交易，后验看是不是好事；
- 被阻止的交易和未被阻止的交易，后续表现有何差异。

这通常是最安全的第一步。

---

## 11. 当前 Route C1 处在哪个阶段

当前可以准确概括为：

- 历史 `price-only proxy`：`promising`
- live overlap：已推进到 `route_c1_overlap_ready_for_orderbook_aware`
- 当前样本长度：约 `72h`
- 当前未达到：`7d / 168h`

所以当前最准确的状态是：

```text
数据准备已完成，live 证据累计中
```

不是：

```text
live 风控已经验证通过
```

---

## 12. 最终一句话总结

`price-only proxy` 是低成本历史预筛；  
`live overlap audit` 是数据对齐验收；  
`orderbook-aware` 是执行风险层的升级研究；  
`7d live smoke` 和 `30d forward` 是把“看起来有道理”推进到“真实可信”的必要阶段。

Route C1 的真正价值，不是直接帮系统赚钱，而是帮助系统识别：

> 哪些 liquidation shock 之后的窗口，不适合按正常方式继续进场。
