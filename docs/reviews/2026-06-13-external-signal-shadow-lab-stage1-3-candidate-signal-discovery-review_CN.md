# External Signal Shadow Lab Stage 1.3 Candidate Signal Discovery Review

## 1. 结论

- decision: `stage1_3_candidate_signal_discovery_completed`
- next_action: `stop_gate_ticker_direction`
- 中文动作：停止 Gate ticker snapshot 派生方向
- fixture_run: `False`
- research_result_valid: `True`

本 review 基于历史 bars 输入；是否 research-valid 取决于 coverage/history_days。

## 2. 安全边界

- 不允许 alpha interpretation: `True`
- 不允许扩 collector: `True`
- 不要求立即 live shadow: `True`

## 3. 数据 venue

- historical_venue: `binance_proxy`
- venue_proxy_used: `True`

## 4. 候选事件与判定口径说明

### 4.1 本次数据如何得到

本次不是 fixture smoke，而是真实历史 replay：脚本从 Binance public spot klines 拉取 `BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT` 的 `180` 天 `15m OHLCV`，共 `86,400` 根 bar。由于 Stage 1.2 的实时 collector 来源是 Gate ticker，而本次历史数据来自 Binance，因此本 review 必须标记 `venue_proxy_used=True`。这表示：本次只能判断“这些候选信号在 Binance proxy 历史价格/成交量上是否有结构”，不能直接证明 Gate 实盘可用。

每根 bar 的 `quote_volume` 使用 Binance kline 原始字段 `quote asset volume`，不是 `base_volume * close` 估算。这样做是为了避免成交额估算误差污染 `volume_spike_1h`。

### 4.2 候选事件是什么意思

- `volume_spike_1h`：某个币最近完整 `1h` 的 quote volume，相比过去 `7` 天同一 UTC 小时的历史中位水平，达到 `3.0x` 以上。它表示“这个币在当前小时出现异常放量”，但不直接等于买入信号。
- `relative_strength_vs_btc`：某个 alt 最近完整 `1h` 收益率减去 BTC 同期收益率后，超过过去 `7` 天相对 BTC spread 的滚动中心 `1.5σ`。它表示“这个 alt 短期明显强于 BTC”。本轮评价采用 `outright_long_alt`，即只评估直接做多 alt 的结果，不假设可以做 BTC 对冲 pair trade。
- `volume_confirmed_relative_strength`：同时满足 `volume_spike_1h` 和 `relative_strength_vs_btc`。它试图过滤“无量拉升”或“单纯放量但价格不强”的噪声。
- `price_move_15m`：短周期价格冲击 baseline，只作为对照，不作为主候选。它用于判断“普通 price-only 短周期冲击”是否已经足够解释结果。
- `cross_symbol_rotation`：当前仍是 diagnostic/stub，本轮没有实现有效轮动事件，因此 `event_count=0`。

### 4.3 事件和收益如何计算

每个候选事件只允许使用已经完成的历史 bar：`15m` bar 完成后，再加 `configured_data_lag_ms=60,000` 作为信息可得时间，避免使用同一根未完成 bar 产生未来函数。入场评估使用事件可得后的第一根完整 `15m` bar open，主评价窗口为后续 `4h`，即 `16` 根 `15m` bar。

每个事件会计算扣除 `50bps` round-trip cost 后的 `4h terminal return`，这是本轮主评价指标。`30/50/80bps` 是 Stage A/External Signal 系列沿用的交易摩擦压力场景；这里用 `50bps` 作为 stress 门槛，是为了防止只在极低成本假设下看起来有效。

随机基准不是随便抽样。每个候选会跑 `500` 次 random baseline trials，并尽量匹配同 symbol 和同 hour-of-day。这样做是为了避免把“某个币本来波动大”或“某个时段本来波动大”误判成信号能力。

### 4.4 表格指标是什么意思

- `events`：候选触发次数。样本太少会触发 `event_count_below_min`。
- `symbols`：触发事件覆盖的币种数量。少于 `3` 个 symbol 说明过于集中。
- `days`：触发事件覆盖的自然日数量。少于 `20` 天说明可能只来自单一小行情。
- `excess_bps`：候选事件的主指标中位数，减去 500 次随机基准的中位数。大于 0 表示比匹配随机事件更好。
- `median_50bps`：候选事件扣 `50bps` 成本后的 `4h` 中位收益。必须大于 0 才能进入 live smoke；否则只是“少亏一点”，不是可执行 alpha。
- `left_tail_vs_baseline`：候选事件左尾风险相对随机基准的改善/恶化。负数表示候选事件在尾部亏损上比基准更差。
- `top5_profit_share`：前 5 个正收益事件贡献的 gross profit 占比。阈值设为 `<= 0.30`，用于防止结果靠极少数异常事件撑起来。

### 4.5 为什么这些阈值这样设

- `event_count >= 100`：低于 100 个事件时，样本太少，容易被几次行情噪声支配。
- `event_days >= 20`：至少跨 20 天，避免只靠某个单日/单周热点。
- `symbols_with_events >= 3`：至少覆盖 3 个币，避免单币过拟合。
- `max_single_symbol_event_share <= 0.50`：单币事件占比不能过半。
- `max_single_day_event_share <= 0.20`：单日事件占比不能过高。
- `top5_profit_share <= 0.30`：不能靠前 5 个暴利事件支撑结论。
- `baseline_excess_net_bps > 0`：必须跑赢 symbol/hour matched random baseline。
- `median_net_return_after_50bps > 0`：必须在 50bps stress cost 后中位收益仍为正。若这个不满足，最多只能标记为 `candidate_diagnostic_promising`，不能进入 Stage 1.4 live smoke。

### 4.6 本轮为什么没有通过

`volume_spike_1h` 和 `relative_strength_vs_btc` 的 `excess_bps` 为正，说明它们相对匹配随机基准有一点改善；但二者的 `median_50bps` 仍分别为 `-48.96bps` 和 `-52.29bps`，阻塞项都是 `median_net_return_not_positive`。这意味着它们不是可执行正收益结构，只是“比随机少亏一点”。因此只能标记为 `candidate_diagnostic_promising`，不允许进入 Stage 1.4。

`volume_confirmed_relative_strength` 和 `price_move_15m` 的 `baseline_excess_net_bps` 为负，阻塞项为 `no_positive_baseline_excess`。这表示它们连匹配随机基准都没跑赢，直接失败。

`cross_symbol_rotation` 当前没有有效事件，阻塞项为 `event_count_below_min`，只能视为未实现/样本不足，不构成策略证据。

结论：Gate ticker snapshot 派生出的低维 price/volume 候选，在本轮 180 天 Binance proxy 历史 replay 中没有形成可进入 live smoke 的进攻型 alpha 结构。

## 5. 候选结果

| candidate | events | decision | blocker | symbols | days | excess_bps | median_50bps | left_tail_vs_baseline | top5_profit_share |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
| volume_spike_1h | 5690 | candidate_diagnostic_promising | median_net_return_not_positive | 5 | 155 | 4.227560909976226 | -48.957880100499686 | -106.6775583220564 | 0.02133001103747346 |
| relative_strength_vs_btc | 4004 | candidate_diagnostic_promising | median_net_return_not_positive | 4 | 173 | 1.0123565699293735 | -52.286317691692076 | -58.67568477848698 | 0.023047053532591774 |
| volume_confirmed_relative_strength | 1076 | candidate_failed | no_positive_baseline_excess | 4 | 118 | -8.593865595688534 | -62.394840701969166 | -119.10601733665038 | 0.06804785414251893 |
| price_move_15m | 8674 | candidate_failed | no_positive_baseline_excess | 5 | 177 | -0.39581564163336935 | -52.18746617265508 | -52.78916561738515 | 0.013720419352585401 |
| cross_symbol_rotation | 0 | candidate_data_insufficient | event_count_below_min | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

## 6. 解释边界

本 review 不能推出任何实盘、paper trading 或自动交易结论。Stage 1.3 只判断预注册候选事件是否值得进入下一阶段研究。
