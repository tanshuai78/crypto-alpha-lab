# External Signal Shadow Lab Stage 1.4 Derivatives Stress Event Feasibility Design

日期：2026-06-14

## 1. 设计结论

Stage 1.4 的目标不是继续围绕 `price / volume / change_percentage` 调阈值，也不是直接把 liquidation、funding、OI 写成交易策略。

Stage 1.4 只回答一个更窄的问题：

```text
公开可获得的 derivatives stress 数据，是否足够支持一个可审计、可回放、个人投资者可执行的高信息密度事件研究？
```

本阶段推荐方向：

```text
P0 = Derivatives Stress Composite
核心 = liquidation cluster / imbalance + funding / OI crowding
可选确认 = orderbook depth collapse
```

最终建议：执行 Stage 1.4，但必须先做数据可行性审计，再决定是否进入候选事件 replay。

```text
decision = proceed_to_stage1_4_derivatives_stress_event_feasibility_design
scope = derivatives_stress_data_feasibility_first
primary_source_family = liquidation_cluster_plus_funding_oi_crowding
optional_confirmation_source = orderbook_depth_collapse_later
expected_default_outcome = stage1_4_data_degraded
collector_expansion_allowed = false_by_default
historical_replay_first = true
live_shadow_required_now = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```

这里的 `expected_default_outcome = stage1_4_data_degraded` 是刻意保守的默认预期。

原因：

```text
funding history 通常较容易取得；
liquidation history 可能只能取得 partial snapshot proxy；
OI history 很可能是最大缺口，若没有 >=90d 本地 archive 或可靠 third-party history，就不能做完整 composite replay。
```

因此 Stage 1.4A 不能默认期待 `stage1_4_data_feasible`。只有在 implementation plan 通过实际探测证明以下条件后，才允许升级：

```text
local OI archive >= 90d
or third-party OI history >= 90d
or public historical OI source 被实测确认可覆盖 >=90d
```

Stage 1.4 不应同时铺开 `P1-P6`。第一版只聚焦：

```text
P1: liquidation cluster / liquidation imbalance
P2: funding + OI crowding
P3: orderbook depth / imbalance 只作为后置 confirmation，不作为第一版主 source
```

暂不纳入：

```text
P4: listing / delisting / unlock / event calendar
P5: cross-exchange divergence
P6: on-chain smart money / whale flow
```

这些方向并非无价值，而是会扩大研究面，导致 Stage 1.4 从“最小可证伪”变成“继续堆 collector”。

---

## 2. 为什么进入 Stage 1.4

Stage 1.3 已经完成真实历史 replay，使用 `180d` Binance proxy `15m OHLCV` 对 Gate ticker / 低维 price-volume 派生候选做了验证。

结果显示：

```text
volume_spike_1h: 样本足够，但 50bps 后中位收益为负
relative_strength_vs_btc: 样本足够，但 50bps 后中位收益为负
volume_confirmed_relative_strength: 未跑赢匹配随机基准
price_move_15m: 未跑赢匹配随机基准
cross_symbol_rotation: 事件密度不足
```

因此，当前结论不是：

```text
所有外部信号研究都无效
```

而是：

```text
仅靠 ticker / OHLCV / 短周期 price-volume 派生事件，信息密度不足。
```

Stage 1.4 的转向逻辑：

```text
普通成交量/价格 = 已发生的表层市场结果
liquidation / OI / funding = 杠杆仓位、强制成交、拥挤状态
```

后者理论上更接近“为什么价格会动”，而不是只观察“价格已经动了”。

这不保证有 alpha，但比继续调 `volume_spike_1h` 阈值更值得一次最小可证伪研究。

---

## 3. Stage 1.4 的核心假设

### 3.1 主假设

```text
derivatives stress event 比低维 price-volume event 更可能携带短中期结构。
```

这里的 derivatives stress 包括：

- `liquidation cluster`：一段时间内同方向强平集中出现；
- `liquidation imbalance`：多头强平或空头强平明显占优；
- `funding crowding`：资金费率显示某一侧杠杆仓位拥挤；
- `OI change`：未平仓合约量变化显示杠杆增减；
- `price move context`：价格已经 flush / spike / trend；
- optional `depth collapse`：盘口承接变薄。

### 3.2 为什么 liquidation 不应单独交易

看到 liquidation 不等于看到反转。

同样是多头爆仓，可能对应两种完全不同的市场结构：

```text
forced deleveraging exhaustion
= 强制去杠杆接近尾声，后续可能反弹

trend continuation liquidation
= 趋势行情中的连续清算，后续可能继续下跌
```

所以 Stage 1.4 不允许：

```text
long_liquidation_seen -> 直接 long
short_liquidation_seen -> 直接 short
liquidation_notional 超阈值 -> 直接生成 directional order
```

必须结合：

```text
liquidation side
liquidation notional relative z-score / percentile
OI contraction or expansion
funding crowding direction
price return context
optional liquidity depth state
```

### 3.3 为什么 funding 应被当作 crowding label，而不是收益来源

过去项目已经多次证明：把 funding / basis 直接当成进攻型 alpha 或收益来源，容易被手续费、basis 扩张和 regime shift 吞噬。

Stage 1.4 中，`funding` 的角色改为：

```text
crowding state label
```

也就是判断市场哪一侧更拥挤：

```text
positive funding high -> 多头拥挤概率更高
negative funding high abs -> 空头拥挤概率更高
funding percentile high + OI rising -> 杠杆趋势堆积
funding crowded + OI falling + liquidation -> 去杠杆发生
```

这比“赚 funding”更贴近 derivatives stress event 的语义。

---

## 4. 关键概念简释

### 4.1 `liquidation cluster`

`liquidation cluster` 指在一个窗口内，例如 `15m` 或 `1h`，同一 symbol 出现明显集中的强制平仓。

强平不是普通成交，而是杠杆仓位保证金不足后被交易所强制卖出或买回。因此它比普通 volume 更能代表“被迫行为”。

### 4.2 `liquidation imbalance`

`liquidation imbalance` 指多头强平和空头强平不对称。

示例：

```text
long_liquidation_notional_1h = 50M
short_liquidation_notional_1h = 5M
long_liquidation_dominance = 50 / (50 + 5) = 90.9%
```

这表示该窗口主要是多头被迫出清。

### 4.2.1 Liquidation side 映射规则

Stage 1.4 必须把 liquidation side 映射写死，不能让 implementation agent 自由解释。

统一规则：

```text
long liquidation = forced SELL pressure
short liquidation = forced BUY pressure
```

解释：

```text
多头爆仓 = 多头仓位被交易所强制卖出 -> forced SELL -> long_liquidation_notional
空头爆仓 = 空头仓位被交易所强制买回 -> forced BUY -> short_liquidation_notional
```

实现计划中必须增加测试：

```text
test_force_order_side_maps_sell_to_long_liquidation
test_force_order_side_maps_buy_to_short_liquidation
```

如果这个映射写反，`liquidation imbalance`、`exhaustion`、`trend continuation` 的全部结论都会反向，属于结构性研究错误。

### 4.3 `OI` / `open interest`

`OI` 是未平仓合约量，表示市场里还没有平掉的合约仓位规模。

粗略理解：

```text
OI rising -> 杠杆仓位正在增加
OI falling -> 杠杆仓位正在减少 / 去杠杆
```

单独看 OI 不够，必须结合价格方向和 liquidation。

### 4.4 `funding crowding`

永续合约通过资金费率让 perp 价格靠近现货价格。

在研究里可以粗略理解为：

```text
funding 很正 -> 多头愿意付费持仓，多头拥挤概率高
funding 很负 -> 空头愿意付费持仓，空头拥挤概率高
```

Stage 1.4 不把 funding 当收益来源，而是把它作为仓位拥挤状态标签。

### 4.5 `depth collapse`

`depth collapse` 指订单簿盘口深度突然变薄，例如 top20 bid/ask depth 跌到过去分布的底部百分位。

它不一定预测方向，但说明承接能力变差，价格更容易跳变。

Stage 1.4 第一版不优先做 orderbook，因为盘口半衰期短、撤单多、实现复杂。它只作为后续 confirmation 候选。

---

## 5. 现有本地证据与约束

本仓库已经有 liquidation 相关研究和数据工具，不能从零假设。

### 5.1 已知数据语义限制

本地脚本明确记录：

```text
Binance Vision only publishes liquidationSnapshot under /data/futures/cm/
UM futures liquidationSnapshot does not exist on Binance Vision
```

含义：

```text
Binance Vision historical liquidationSnapshot 是 COIN-M proxy，不是 USD-M 完整 liquidation tape。
```

同时，已有配置也写明：

```text
liquidationSnapshot = largest-order snapshot proxy per symbol per 1000ms interval
NOT a complete liquidation tape
```

所以 Stage 1.4 必须把 liquidation 数据标记为：

```text
partial_snapshot_lower_bound
cluster_proxy_not_complete_tape
```

禁止在 review 中写成：

```text
完整清算数据
完整逐笔 liquidation tape
真实全市场清算量
```

### 5.2 过去 liquidation 失败不等于主题完全证伪

已有 review 里出现过两类失败：

```text
Coinalyze 1m liquidation coverage sparse / discontinuous
原始 1m shock -> 5/10/15m direction 研究前提不成立
```

这说明过去失败的核心包括：

```text
数据连续性不足
时间窗口过短
把 liquidation 当成单点方向信号
```

Stage 1.4 必须避免重复这三个错误。

### 5.3 现有可复用资产

可复用资产包括：

```text
Binance public OHLCV historical bars
Stage 1.3 random baseline / forward metrics 思路
Binance liquidation snapshot manifest probe
Binance forceOrder live collector / hourly aggregation 相关脚本
funding history fetch 脚本
Route C1 / liquidation shock 的数据语义和失败 review
```

但 Stage 1.4 不能假设这些资产已经满足研究门槛。必须先审计 coverage、history_days、symbol overlap、timestamp alignment。

---

## 6. Stage 1.4 分层设计

Stage 1.4 必须拆成两层。

### 6.1 Stage 1.4A: Derivatives Stress Data Feasibility Audit

先回答数据问题：

```text
我们能否拿到足够长、足够连续、语义清楚、可对齐价格 bars 的 derivatives stress 数据？
```

不做候选收益评价，不输出 alpha 判断。

输出：

```text
source availability
history_days
symbol coverage
field coverage
bar alignment coverage
event density
missing gap summary
source semantics
usable_for_replay flag
```

### 6.2 Stage 1.4B: Derivatives Stress Candidate Replay

只有 Stage 1.4A 通过后，才允许定义并回放候选事件。

Stage 1.4B 才回答：

```text
这些 derivatives stress event 是否比 price-volume baseline 和 symbol/hour matched random baseline 更有结构？
```

如果 Stage 1.4A 不通过，不进入 Stage 1.4B。

这种拆分是必要的。否则很容易出现：

```text
候选逻辑写得很漂亮，但 liquidation / OI historical 数据根本不可用。
```

---

## 7. Stage 1.4A 数据源审计范围

Stage 1.4A 的第一版必须固定 data source audit order，避免 agent 到处探测、无意扩大范围。

审计顺序：

```text
1. Funding history: Binance public settled funding history, e.g. /fapi/v1/fundingRate
2. OI history: Binance public historical OI endpoint or documented equivalent; first confirm actual max lookback
3. Existing local OI archive: check whether local coverage >=90d
4. Existing forceOrder archive: check real local liquidation proxy coverage
5. Binance Vision COIN-M liquidationSnapshot manifest probe
6. Third-party only as documented external option; not implemented in Stage 1.4A v1
```

第一版不直接接 third-party 数据源。除非用户明确接受成本、授权、字段语义和可复现风险，否则 third-party 只作为 review 中的备选路线记录。

### 7.1 Liquidation source candidates

第一版允许审计三类 liquidation source。

#### A. Binance live `forceOrder` archive

含义：

```text
本地未来实时采集的 Binance forceOrder stream
```

优点：

```text
语义接近实时公开 liquidation proxy
可用 available_at_ms 记录真实到达时间
```

缺点：

```text
历史长度取决于我们已经采集多久
短期内无法立刻得到 90d / 180d replay
public stream 仍可能不是完整全市场 liquidation tape
```

适用：

```text
24h / 7d live smoke 或未来 rolling archive
```

不适合立刻做 180d historical replay。

#### B. Binance Vision COIN-M `liquidationSnapshot`

含义：

```text
Binance Vision 上 COIN-M futures 的 liquidationSnapshot 历史文件
```

优点：

```text
可能有较长历史
可以做离线 replay
不需要 API key
```

缺点：

```text
COIN-M proxy，不是 USD-M
largest-order snapshot / 1000ms proxy，不是完整 liquidation tape
部分 symbol 可能没有 CM perpetual
notional 换算和 symbol mapping 需要严格审计
```

COIN-M proxy 的 symbol mapping 必须单独审计，不能把它当作天然等价：

```text
BTCUSD_PERP -> BTCUSDT
ETHUSD_PERP -> ETHUSDT
SOLUSD_PERP -> SOLUSDT
XRPUSD_PERP -> XRPUSDT
DOGEUSD_PERP -> DOGEUSDT
```

注意：

```text
COIN-M = 币本位合约
USD-M = U 本位合约
```

它们的合约单位、notional 口径、流动性结构都可能不同。因此 Stage 1.4A summary 必须输出：

```json
{
  "liquidation_symbol_mapping_quality": "exact|proxy|missing",
  "cm_to_um_proxy_used": true,
  "notional_conversion_required": true,
  "notional_conversion_quality": "verified|estimated|unavailable"
}
```

如果 notional conversion 无法验证，只能进入：

```text
semantics_failure
or partial_diagnostic
```

不能进入完整 composite replay。

适用：

```text
Stage 1.4A historical feasibility probe
```

但 review 必须标记：

```text
liquidation_source_quality = cm_liquidation_snapshot_proxy
venue_proxy_used = true
```

#### C. Third-party historical liquidation dataset

含义：

```text
Coinalyze 或其他 vendor 的 liquidation aggregate / history
```

优点：

```text
可能直接提供 USD-M / exchange aggregate / long-short 分解
```

缺点：

```text
免费层覆盖可能稀疏
字段语义需要验证
供应商可能改口径
数据成本和授权不确定
```

适用：

```text
如果 A/B 不满足 coverage，再作为候选 source 审计
```

不允许为了让研究继续而忽略 vendor coverage 问题。

### 7.2 Funding source candidates

第一版优先使用 Binance public settled funding history：

```text
/fapi/v1/fundingRate
```

需要审计：

```text
symbol coverage
history_days
settlement interval consistency
missing funding settlements
funding timestamp alignment
```

Funding 通常比 liquidation 更容易拿到历史，但它是 `8h` 或交易所设定 settlement 频率，不是 `15m` 数据。Stage 1.4 必须明确：

```text
funding_state 在 event timestamp 前最近一次已知 funding record 上计算
不得使用 event 之后才公布的 funding
```

更严格的 as-of policy：

```text
funding_state_at_event =
  latest funding record where funding_time_ms <= event_available_at_ms - funding_publish_lag_ms
```

implementation plan 必须在 `configs/base.py` 增加：

```text
EXTERNAL_SIGNAL_STAGE1_4_FUNDING_PUBLISH_LAG_MS
```

如果无法确认交易所具体 funding 发布延迟，默认使用保守 lag，例如 `5min` 或 `15min`，并在 review 中标记：

```text
funding_publish_lag_assumption = conservative_unverified
```

### 7.3 OI source candidates

OI 是 Stage 1.4 的最大不确定项之一。

需要区分：

```text
current open interest endpoint
historical open interest statistics
本地 live OI archive
third-party OI history
```

风险：

```text
current open interest 只能给当前值，不能回放历史
historical OI public endpoint 可能有时间跨度限制
本地 OI archive 若不足 90d，只能做 live smoke，不能做 historical replay
```

Stage 1.4A 必须先输出：

```text
oi_history_available = true|false
oi_history_days = N
oi_interval = 5m|15m|1h|unknown
oi_source_quality = public_history|live_archive|third_party|missing
```

如果 OI 历史不可用，Stage 1.4B 不允许直接用“liquidation + funding”替代完整 composite 后宣称通过。只能降级为：

```text
liquidation_funding_partial_diagnostic
```

硬规则：

```text
if oi_history_days < 90:
  stage1_4b_candidate_replay_allowed = false
  composite_replay_allowed = false
  partial_diagnostic_allowed = true only if liquidation + funding coverage pass
  oi_blocks_full_composite = true
```

也就是说，`liquidation + funding` 不能冒充完整的 `liquidation + OI + funding` composite。

### 7.4 Price bars

Price source 默认必须从 futures 语义出发。

默认规则：

```text
default price_source = USD-M futures klines
fallback = spot klines proxy only if futures klines unavailable
```

原因：

```text
liquidation / OI / funding 都是 perp / futures 语义；
如果用 spot price 做 trigger/evaluation，会引入 basis mismatch。
```

Stage 1.3 的 Binance spot proxy `15m OHLCV` 流程可以作为 fallback 参考，但不能作为 Stage 1.4 的默认 price source。

第一版 price source 模式：

```text
mode A: futures_klines_default
mode B: spot_klines_proxy_fallback
```

若使用 spot proxy，summary 必须标记：

```text
price_venue_proxy_used = true
```

---

## 8. Stage 1.4A 可行性门槛

第一版数据可行性门槛建议如下。

### 8.1 必需字段

每个可用 symbol 至少需要：

```text
timestamp / available_at-like timestamp
symbol
price close/open/high/low
liquidation_long_notional
liquidation_short_notional
funding_rate_state
OI value or OI change proxy
source_quality metadata
```

如果 OI 不可得，必须显式标记为 partial diagnostic。

### 8.2 覆盖门槛

```text
history_days_preferred >= 180
history_days_min >= 90
symbols_with_usable_data >= 3
bar_coverage_ratio >= 0.95
liquidation_field_coverage_ratio >= 0.90
funding_field_coverage_ratio >= 0.95
oi_field_coverage_ratio >= 0.90 if OI is required
max_timestamp_alignment_gap <= one aggregation window
```

说明：

- `90d` 是进入最小 replay 的底线；
- `180d` 是 preferred；
- 如果只有 7d 或 30d，不适合做 historical alpha replay，只能做 data smoke；
- 如果只有 `BTC/ETH` 两个 symbol，不足以支撑多币候选，但可做 BTC/ETH diagnostic。

### 8.3 事件密度门槛

Feasibility 阶段只做粗事件密度，不做收益判断。

建议输出：

```text
preview_liquidation_nonzero_window_count
preview_liquidation_stress_window_count
preview_funding_crowding_window_count
preview_oi_change_window_count
preview_composite_overlap_window_count
```

字段名必须使用 `preview_` 前缀，避免误读为候选事件已经通过。

解释：

```text
preview = 数据密度预览
不是 alpha candidate
不是收益判断
不是进入 replay 的充分条件
```

初步门槛：

```text
preview_composite_overlap_window_count >= 50 for diagnostic
preview_composite_overlap_event_days >= 15
```

若低于门槛：

```text
decision = stage1_4_data_density_insufficient
```

不能降低阈值硬救。

---

## 9. Stage 1.4B 候选事件草案

以下候选只在 Stage 1.4A 通过后进入实现计划。当前设计先定义语义，不承诺阈值最终有效。

所有阈值必须在 implementation plan 中进入 `configs/base.py`，不能写死在 `src/`。

### 9.1 `long_liquidation_exhaustion_reversal`

语义：

```text
多头被集中强平，OI 同时下降，价格已经 flush，funding 显示此前多头拥挤。
```

候选条件草案：

```text
long_liquidation_notional_1h_zscore >= 3.0
long_liquidation_dominance >= 0.70
OI_1h_change_pct <= -1.0%
price_1h_return_pct <= -1.5%
funding_state = positive_or_long_crowded
```

研究假设：

```text
如果这是 forced deleveraging exhaustion，后续 4h/12h 可能出现反弹或左尾风险下降。
```

注意：这不是看到多头爆仓就做多。只有在 `OI contraction` 和 crowded funding 同时出现时，才可能解释为去杠杆接近尾声。

### 9.2 `short_liquidation_exhaustion_reversal`

语义：

```text
空头被集中强平，OI 同时下降，价格已经 spike，funding 显示此前空头拥挤。
```

候选条件草案：

```text
short_liquidation_notional_1h_zscore >= 3.0
short_liquidation_dominance >= 0.70
OI_1h_change_pct <= -1.0%
price_1h_return_pct >= +1.5%
funding_state = negative_or_short_crowded
```

研究假设：

```text
如果这是 short squeeze exhaustion，后续可能回落，或至少不再延续 spike。
```

### 9.3 `liquidation_trend_continuation`

语义：

```text
清算发生，但 OI 没有收缩，甚至继续扩张；这更像趋势加速，而不是尾声。
```

候选条件草案：

```text
liquidation_notional_1h_zscore >= 3.0
OI_1h_change_pct >= +1.0%
price_1h_return same direction as liquidation pressure
funding_state not clearly unwind
```

研究假设：

```text
liquidation 不是反转信号，而是趋势中继压力。
```

### 9.4 `funding_oi_crowding_unwind`

语义：

```text
funding 极端、OI 开始下降、价格反向运动，说明拥挤仓位可能在撤退。
```

候选条件草案：

```text
funding_abs_percentile >= 0.80
OI_4h_change_pct <= -2.0%
price_4h_return opposite to crowded side
optional liquidation confirmation present
```

研究假设：

```text
funding 本身不交易，但 funding + OI unwind 可能标记拥挤交易解除。
```

### 9.5 `oi_expansion_trend_confirmation`

语义：

```text
价格趋势同向，OI 增加，funding 尚未极端到拥挤崩塌，说明趋势可能仍在吸引新增杠杆。
```

候选条件草案：

```text
OI_4h_change_pct >= +3.0%
price_4h_return_abs above threshold
funding_abs_percentile between moderate and high, but not extreme unwind
liquidation exhaustion absent
```

研究假设：

```text
这更接近趋势确认，而不是反转。
```

---

## 10. 评价窗口与入场语义

Stage 1.4 不允许事件发生后立即用同一根 bar 的价格成交。

统一规则：

```text
event timestamp = 聚合窗口结束时间 + source/data lag
entry_bar = event available 后下一根完整 bar open
entry_delay_bars >= 1
```

候选评价窗口：

```text
4h terminal return
12h terminal return
24h terminal return
MFE / MAE using high-low path
left_tail_p05
right_tail_p95
```

主评价指标需要在 Stage 1.4B implementation plan 中按候选类型预注册。

建议：

```text
exhaustion reversal candidates: primary = 12h terminal net bps after 50bps
trend continuation candidates: primary = 4h or 12h terminal net bps after 50bps
risk-filter candidates: primary = left_tail_improvement_vs_baseline
```

原因：去杠杆尾声不一定在 15m 内反弹，若强行用过短窗口，会退化为低延迟游戏；但 24h 又可能混入太多非事件噪声。

第一版 review 必须同时输出 `4h / 12h / 24h`，但不能事后挑最漂亮的窗口晋级。

---

## 11. Baseline 设计

Stage 1.4B 至少需要四类 baseline。

### 11.1 Symbol/hour matched random baseline

沿用 Stage 1.3 思路：

```text
同 symbol 分布匹配
hour-of-day 分布匹配
event_count 相同
random_baseline_trials >= 500
排除 candidate 自身 timestamp
```

这是判断候选是否只是“刚好发生在高波动时段”的最低要求。

### 11.2 Price-move baseline

必须和简单价格冲击对照。

示例：

```text
price_move_1h_baseline
abs(price_1h_return) >= rolling threshold
```

如果 derivatives stress event 连普通 price-move baseline 都打不过，就没有必要进入 live smoke。

### 11.3 Liquidation-only baseline

为了判断 composite 是否真的增加信息量，需要一个单项 baseline：

```text
liquidation_cluster_only
```

如果 `liquidation + OI + funding` 不优于 `liquidation only`，说明 OI/funding 只是装饰，不应继续复杂化。

### 11.4 Funding/OI-only diagnostic

Funding/OI 单项不作为 pass/fail 主候选，但应输出 diagnostic：

```text
funding_extreme_only
OI_expansion_only
OI_contraction_only
```

目的是判断组合 edge 来自哪里，而不是把所有字段混在一起后无法解释。

---

## 12. 通过门槛

Stage 1.4B 候选要比 Stage 1.3 更严格，因为它已经是更高信息密度 source。

建议门槛：

```text
event_count >= 80
event_days >= 20
symbols_with_events >= 3
max_single_symbol_event_share <= 0.50
max_single_day_event_share <= 0.20
median_net_return_after_50bps > 0
baseline_excess_net_bps > 0
left_tail_vs_random_baseline_bps >= 0
top_5_positive_events_gross_profit_share <= 0.30
must_beat_price_move_baseline = true
must_beat_symbol_hour_random_baseline = true
```

若数据源本身稀疏，可允许：

```text
50 <= event_count < 80 -> candidate_diagnostic_only
```

但不能进入 Stage 1.5 / Stage 2。

如果候选只是：

```text
比随机少亏一点，但 50bps 后中位数仍为负
```

则不能晋级。

---

## 13. 失败分类

Review 必须按以下类型归因。

### 13.1 `data_failure`

历史数据无法下载、无法解析、字段缺失、时间戳不可对齐。

示例：

```text
OI history missing
liquidation source unavailable
funding timestamps cannot align
```

### 13.2 `density_failure`

数据能解析，但事件太少或集中度过高。

示例：

```text
event_count < 50
event_days < 15
single_symbol_event_share > 0.70
```

### 13.3 `semantics_failure`

数据语义不足以支撑研究假设。

示例：

```text
liquidation source is snapshot-only and too sparse
CM proxy cannot map to target USD-M symbols
funding available but OI unavailable, composite cannot be evaluated
```

### 13.4 `structure_failure`

数据足够、事件足够，但没有后续结构。

示例：

```text
median_net_return_after_50bps <= 0
baseline_excess_net_bps <= 0
left_tail worse than baseline
```

### 13.5 `execution_cost_failure`

30bps 下看起来有结构，但 50/80bps 后消失。

### 13.6 `confirmed_next_action`

只有候选通过历史 replay，且数据语义清楚，才允许进入：

```text
24h live smoke
7d shadow validation
30d shadow validation
```

不能直接进入 paper/live。

---

## 14. 明确排除项

Stage 1.4 不做：

```text
DEX / MEV / wallet / swap payload
copy trade
新币首分钟狙击
秒级 orderbook imbalance
跨所 spot price spread arbitrage
自动下单
paper account execution
任何 API key / private endpoint
```

原因：这些方向要么个人投资者执行劣势明显，要么会引入资金安全风险，要么超出 External Signal Shadow Lab 当前阶段。

---

## 15. 实施前必须确认的问题

Stage 1.4 implementation plan 之前必须先回答：

1. Liquidation historical source 选哪一个？
   - `Binance Vision CM liquidationSnapshot proxy`
   - `existing forceOrder live archive`
   - `third-party historical dataset`
2. OI historical source 是否可获得 `>=90d`？
3. Funding history 是否覆盖同一 symbol universe？
4. Price bars 使用 futures klines 还是 spot klines proxy？
5. Symbol universe 是否仍限定为：

```text
BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT
```

6. 如果 OI 不可得，是否允许降级为 partial diagnostic？
7. 是否接受 `CM liquidationSnapshot` 作为 USD-M stress proxy？如果接受，review 必须显式标记 `venue_proxy_used=true`。

默认建议：

```text
Stage 1.4A 先做 data feasibility audit，不做收益 replay。
```

Stage 1.4A implementation plan 必须明确禁止：

```text
不实现 long_liquidation_exhaustion_reversal
不实现 short_liquidation_exhaustion_reversal
不实现 liquidation_trend_continuation replay
不实现 funding_oi_crowding_unwind replay
不计算 forward return
不跑 random baseline
不生成 alpha review
不输出 candidate_promising_for_live_smoke
```

Stage 1.4A 只允许输出：

```text
stage1_4_data_feasible
stage1_4_data_degraded
stage1_4_data_unavailable
```

如果数据不可行，直接停止或换 source；不得为了推进进度而跳过数据语义审计。

---

## 16. Stage 1.4A 预期交付物

设计后的下一份 implementation plan 应只覆盖 Stage 1.4A。

预期输出：

```text
reports/external_signal_shadow/stage1_4_derivatives_stress_data_feasibility_summary.json
docs/reviews/2026-06-14-external-signal-shadow-lab-stage1-4-derivatives-stress-data-feasibility-review_CN.md
```

summary 至少包含：

```json
{
  "decision": "stage1_4_data_feasible|stage1_4_data_degraded|stage1_4_data_unavailable",
  "expected_default_outcome": "stage1_4_data_degraded",
  "source_family": "derivatives_stress",
  "liquidation_source": "...",
  "liquidation_source_quality": "...",
  "liquidation_symbol_mapping_quality": "exact|proxy|missing",
  "cm_to_um_proxy_used": false,
  "notional_conversion_required": false,
  "notional_conversion_quality": "verified|estimated|unavailable",
  "funding_source": "...",
  "funding_asof_policy": "latest_record_before_event_available_at_minus_lag",
  "funding_publish_lag_ms": 0,
  "oi_source": "...",
  "oi_history_limit_detected_days": 0,
  "oi_blocks_full_composite": true,
  "price_source": "...",
  "price_source_preference": "futures_klines_preferred",
  "price_venue_proxy_used": false,
  "history_days_by_source": {},
  "symbols_with_usable_data": [],
  "coverage_ratio_by_source": {},
  "timestamp_alignment_summary": {},
  "event_density_preview": {},
  "preview_not_alpha": true,
  "composite_replay_allowed": false,
  "partial_diagnostic_allowed": false,
  "stage1_4b_candidate_replay_allowed": false,
  "primary_blocker": "..."
}
```

Review 必须用中文解释：

```text
每个 source 是什么
它是否完整
它的语义限制是什么
能不能支撑 90d / 180d historical replay
是否允许进入 Stage 1.4B
```

---

## 17. 当前推荐路线

当前推荐路线不是“马上写 derivatives stress 策略”，而是：

```text
Stage 1.4A: Derivatives Stress Data Feasibility Audit
-> 如果 data_feasible，写 Stage 1.4B Candidate Replay Design / Plan
-> 如果 data_degraded，只允许 partial diagnostic，不允许 alpha 判断
-> 如果 data_unavailable，停止该 source 或换 source
```

优先级：

```text
第一优先：liquidation + OI + funding 的可行性审计
第二优先：如果 OI 缺失，判断 liquidation + funding partial diagnostic 是否仍有研究价值
第三优先：orderbook depth collapse 作为后续 confirmation，不抢先实现
```

不建议下一步做：

```text
P4 event calendar
P5 cross-exchange divergence
P6 on-chain smart money
```

这些可以保留在 roadmap，但不应与 Stage 1.4 混在一起。

---

## 18. 最终判断

Stage 1.4 值得做，但只能以数据可行性审计开始。

核心判断：

```text
低维 price-volume 方向已经失败。
衍生品压力状态是更合理的下一类高信息密度 source。
但 liquidation/OI/funding 的历史数据语义和覆盖率是硬门槛。
```

如果数据可行，Stage 1.4B 才研究：

```text
liquidation exhaustion reversal
liquidation trend continuation
funding/OI crowding unwind
OI expansion trend confirmation
```

如果数据不可行，应该停止或换 source，而不是强行用残缺数据做漂亮回测。

最终推荐：

```text
decision = proceed_to_stage1_4a_derivatives_stress_data_feasibility_implementation_plan
first_task = audit_liquidation_funding_oi_historical_availability
collector_expansion_allowed = false
live_shadow_required_now = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
```
