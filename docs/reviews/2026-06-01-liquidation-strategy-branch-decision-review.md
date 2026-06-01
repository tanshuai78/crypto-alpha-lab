# Liquidation Strategy Branch Decision Review

**Date:** 2026-06-01

## Core Conclusion

当前 liquidation 策略线的失败，不能只简单归因成“数据质量不行”。

更准确的说，失败分成三层：

1. **原始 Coinalyze 路线的数据连续性不够，导致原始 `1m shock -> 5/10/15m response` 研究前提不成立。**
2. **Binance historical snapshot 路线虽然能跑通，但它验证的是一个更弱、更窄的命题。**
3. **即使在这个更弱、更窄的命题上，当前结果也没有确认稳定结构。**

因此，当前不应把结果解读为：

- `liquidation alpha 已被彻底证伪`

更准确的解读是：

- `full-scope 5-symbol replacement validation failed`
- `Q1 2024 reduced snapshot-proxy validation also did not confirm structure`

---

## Clarifying The Key Confusion

一个很容易混淆的点是：

> “既然 Binance snapshot 不是完整逐笔 liquidation，只是每秒最大快照，那它不还是数据质量不够好吗？如果继续只做 3 个币，不还是同样不完整吗？”

答案是：

**要分清“数据质量问题”和“研究命题边界问题”。**

### Case 1: 对原始命题来说，它确实还是不够

如果你要验证的命题是：

- `BTC/ETH/SOL/XRP/DOGE`
- `2024-01 ~ 2024-03`
- “市场 `1m liquidation shock` 是否能稳定预测后续 `5/10/15m` 方向”

那么当前 Binance snapshot 数据确实还是**不够格**，因为：

- `XRP/DOGE` 根本没有进入有效样本
- `SOL 2024-02` 断档
- snapshot 语义也不是完整 liquidation tape

也就是说：

- **对原始 5-symbol 命题，这份卷子是不完整的**

### Case 2: 对更窄的新命题来说，它未必是不够

如果我们主动把问题改成：

- `BTC/ETH` only
- 或 `BTC/ETH/SOL` but requiring complete months only
- `Q1 2024 only`
- `Binance snapshot proxy only`

那这个问题就已经不是原来的“5 个币全范围验证”了，而是一个新的、更窄的问题：

- `在这个更窄的 proxy universe 里，是否存在局部结构`

这时，数据就不再只是“质量差”，而是：

- **语义较弱，但命题也更弱**

所以关键不是一句“数据不行”能概括的。

真正要问的是：

- **我们要验证的是原命题，还是缩窄后的新命题？**

---

## Why The Current 3-Coin Direction Still Does Not Automatically Give The Same Conclusion

如果当前真的有一个**完整的** 3-coin 子宇宙，例如：

- `BTC/ETH/SOL`
- 三个月都完整
- 所有 symbol-month continuity 都通过
- 并且我们明确承认它只是 snapshot proxy study

那么我们确实可以得到一个**新的、较窄的结论**：

- `在 BTC/ETH/SOL + Q1 2024 + Binance snapshot proxy 的范围内，结构成立或不成立`

但当前现实不是这样。

当前 summary 里已经明确：

- `required_symbol_months = 15`
- `passed_symbol_months = 8`
- `universe_integrity_ok = false`

具体缺失：

- `SOLUSDT / 2024-02`
- `XRPUSDT / 2024-01~03`
- `DOGEUSDT / 2024-01~03`

所以现在不是一个完整的 3-coin study，而更像：

- `BTC/ETH 完整`
- `SOL 部分完整`
- `XRP/DOGE 缺席`

这意味着：

- **它连一个完整的 3-coin proxy study 都还没完全成立**

因此当前结论仍然只能是：

- `structure_not_confirmed`

而不能说：

- “3 个币已经验证出和 5 个币相同的结论”

因为当前 3-coin 子样本本身也还没完整。

---

## Why Route A Still Has Meaning

Route A 不是为了“证明现在这条线差一点就成功”。

它的意义只有一个：

- **做最后一次低成本排除法**

它要回答的是：

> 如果我们只保留最有希望、最完整的子样本，这条原始 event-study 定义会不会改善？

它的价值在于区分下面两种情况：

1. **缩窄后仍然不过线**
   - 那说明原始 `1m shock -> 5/10/15m response` 定义本身大概率不强
   - 这时就不值得继续为更贵 vendor 付费

2. **缩窄后明显改善**
   - 那说明问题可能更多在 universe 和数据源
   - 这时才值得考虑更完整 vendor 或更长期自建 archive

所以 Route A 的作用是：

- **判断要不要继续给原始命题投更多成本**

它不是一个“补救成功线”。

---

## Why The Collector Still Matters

服务器上的 live collector 现在是有价值的，而且不应该停。

最新状态：

- `messages = 435`
- `accepted = 435`
- `symbols_with_liq = 5`

这说明：

- live public `forceOrder` 采集已经真实打通
- raw archive 正在积累

它的价值不在于：

- 立刻证明历史策略成立

它的价值在于：

1. **积累 forward raw archive**
   - 给未来更干净的前瞻研究用

2. **验证 live proxy 数据是否比历史 snapshot 更稳定**
   - 这是 Binance Vision 历史文件做不到的

3. **为后续 liquidation 主题研究保留基础设施**
   - 不管做方向、风险还是波动分支，这个 collector 都有价值

### Recommended Collection Horizon

- **最少：30 天**
- **更可靠：90 天**
- 如果资源允许：**长期不停**

原因：

- `7 天` 只够验证 collector 稳定性
- `30 天` 才够做第一版 forward proxy study
- `90 天` 才有资格比较不同 market regime

---

## What Route C Actually Means

Route C 不是换数据源，而是换研究问题。

它的核心判断是：

- **当前 liquidation 数据更像“市场压力信号”**
- 不像“裸方向预测信号”

也就是说，现在失败的可能不是 liquidation 主题本身，
而是我们要求它去回答的问题太苛刻、太具体：

- “某一分钟异常爆仓后，固定 5/10/15 分钟价格方向会不会稳定偏向某边”

Route C 的意思是：

- 不再逼它做这个问题
- 改问一个更适合这种数据语义的问题

### Route C Candidate Branches

1. **Episode Pressure**
   - 不看单分钟 shock
   - 改看连续几分钟同侧 liquidation pressure 的累积

2. **Post-Liquidation Volatility Filter**
   - 不预测方向
   - 改预测 liquidation pressure 后，未来 `5~30m` 的 realized vol / jump risk / slippage 风险

3. **Context-Conditioned Directionality**
   - 不做全样本裸方向预测
   - 只在 funding / OI / trend / momentum context 下看 continuation 或 reversion

Route C 的优势是：

- 更贴近现有数据的真实语义
- 更可能产出风险管理或 execution filter 价值

它的代价是：

- 这已经不是原策略验证
- 而是一个新研究分支

---

## Concrete Decision Table

| Route | What question it answers | What we would do next | Cost / Time | Continue if | Stop if | Current recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `A narrow_scope_and_continue` | 在更窄的 proxy universe 里，原始 `1m shock -> 5/10/15m` 定义是否还能成立 | 收窄到 `BTC/ETH` 或 `BTC/ETH/SOL`，要求完整月份，重跑同一套 event-study | Low | 缩窄后 directional bias 明显改善 | 缩窄后仍然不过线 | 可做，但只值一次排除法 |
| `B switch_vendor_and_restart` | 如果换成更完整、更连续的 vendor，原始命题是否成立 | 找更高质量历史 vendor，重做 full-scope validation | High | 你仍坚持原始 5-symbol 命题值得验证 | 更好数据下仍不过线 | 最干净，但最贵 |
| `C redefine_research_question` | liquidation 数据真正适合回答什么问题 | 开新分支：episode pressure / volatility filter / context-conditioned directionality | Medium | 你接受这不再是原策略验证 | 新问题也没有稳定统计价值 | **最推荐** |

---

## Final Recommendation

当前最合理的顺序是：

1. **collector 继续收，不停**
2. **如果你还想给原始命题最后一次机会，就做 Route A**
3. **真正更值得投入研究资源的是 Route C**

原因：

- 当前 full-scope replacement validation 已失败
- 当前 reduced proxy validation 也没有确认结构
- 但 live liquidation collector 已经开始提供长期研究基础设施

所以最现实的结论是：

- **不要再把这条线理解成“差一点成功”**
- **要么做最后一次低成本排除法（A）**
- **要么承认方向预测不强，转向更适合 liquidation 数据语义的新问题（C）**
