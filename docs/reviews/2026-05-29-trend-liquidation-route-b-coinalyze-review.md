# Trend Liquidation Route-B Coinalyze Review Report

> **范围声明**
> 本报告仅用于对 `liquidation_cascade`（爆仓瀑布）独立子策略在 Coinalyze 适配器（Route B 数据升级路线）接通后的可行性审查与决策。由于当前会话环境暂未配置环境变量 `COINALYZE_API_KEY`，导致实际数据拉取降级为 `"no_api_key"` 状态，因此本次审计回放依然处于强平数据缺失状态，所产生的回放统计并不代表实际策略交易表现。

---

## 1. 范围声明
如范围声明所述，本期工作目标为：重构 Route B 的第三方数据适配器，实现由 Coinglass 临时实现向 Coinalyze 真实 API 适配器的平滑切换，并验证其数据转换与对齐逻辑的可行性。在配置有效的 API Key 之前，系统的决策边界仍受制于数据缺失。

---

## 2. Coinalyze Route B 可行性结果
* **适配层逻辑验证**：Coinalyze 的 Unix 时间戳秒（`t`）、做多爆仓量（`l`）和做空爆仓量（`s`）能够被完美映射并聚合（deduplicated by sum）为系统内毫秒级 `hour_bucket_ms` 架构及 `liquidation_notional_1h_usdt` 与 `total_liquidation_notional_1h_usdt` 字段。
* **API 授权与限频**：Coinalyze 免费 API 限制为 **40 requests/min**，历史回溯深度约 **1500-2000 points**。对于 1h 粒度，1500 个数据点相当于 **1500 小时（约 62.5 天）**，能够完美覆盖并满足策略 **720h+** 历史深度审计的需求，无需任何付费订阅（`requires_paid_plan = false`）。
* **接口参数锁定**：`from / to` 参数已在 fetch 适配器中锁定为以秒为单位发送，且固定参数 `convert_to_usd=true`。
* **请求审计字段已落盘**：Route B summary / feasibility 已写入 `request_count`、`requested_symbols`、`interval`、`from_ts_sec`、`to_ts_sec`，后续可直接区分是凭证缺失、请求窗口错误、还是 symbol 选择错误。

---

## 3. 历史 hourly 覆盖
* **历史回放区间**：2026-05-08 02:59:59.999 至 2026-05-28 21:59:59.999（共 498.0 小时，即 20.75 天）。
* **时间覆盖**：498.0 小时。
* **观察币种**：5 个 (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `XRP/USDT`, `DOGE/USDT`)。
* **Route B 实际强平数据导入 (Route B Joined Rows)**：0 行（降级导致）。
* **与自采 Route A 重叠小时数 (Route AB Overlap)**：0 小时。
* **本次 Route B 请求审计**：`request_count = 5`，`interval = 1hour`，`lookback = 1500h`，`route_b_status = no_api_key`。

---

## 4. Route A / B / C 路线状态
根据本次运行生成的 `2026-05-29_liquidation_cascade_data_source_comparison.json` 结果：
* **Route A (自采)**：`available = false`，`joined_count = 0`，`quality = not_connected`（本地 `data/trend_regime_liquidation_hourly.jsonl` 当前为空，因而没有可接入的 forceOrder 小时级历史）。
* **Route B (第三方历史)**：`available = false`，`joined_count = 0`，`vendor = coinalyze`，`route_b_status = no_api_key`。
* **Route C (混合)**：`available = false`，`overlap_symbol_hour_count = 0`。

---

## 5. continuation / mean_reversion 事件密度
由于无有效强平数据导入，触发的事件数量为 0。
### 拦截 Bottleneck 分析
在总计 2,495 行回放记录中，拒绝原因分布如下：
* `missing_liquidation_fields`: 2,465 行 (占比 **98.8%**) —— 数据链因缺少强平数值而被直接拦截。
* `volume_below_min`: 30 行 (占比 **1.2%**) —— DOGE 等币种 24h 交易额未达最低门槛。

---

## 6. 成本后 replay 结果
由于没有触发任何交易事件，在 4h、8h、12h 和 24h 的持仓周期以及 base_cost (30 bps) / stress_cost (50 bps) 成本下，
* **模拟交易次数**：0
* **中位数净收益**：0.0 bps
* **平均净收益**：0.0 bps
* **胜率 / 止损离场率**：0.0%

---

## 7. 个人投资者视角评价
对个人投资者而言，Coinalyze 的免费 API 是一个极具性价比的数据源路线。它打破了 Coinglass 付费 API （最低 $29/月）的硬性资金门槛，允许开发者直接用免费 Key 在本地重构长达 60 天以上的高频强平数据库。在工程上，利用 stdlib HTTP 请求与适配器结合，我们已为实盘和回放做好了零成本的接线准备。

---

## 8. 下一步路线建议
1. **配置环境变量**：用户在本地终端中运行 `export COINALYZE_API_KEY=your_free_key_here`。
2. **下载离线数据**：运行 `python scripts/fetch_third_party_liquidation_history.py` 脚本，将数据保存至本地。
3. **补齐 Route A 档案**：如需重新判断 Route C，需先让 `data/trend_regime_liquidation_hourly.jsonl` 不再为空，否则 Route A 会继续保持 `not_connected`。
4. **重跑审计**：在 `scripts/review_trend_liquidation_cascade.py` 中同时传入：
   * `--forceorder-hourly-input data/trend_regime_liquidation_hourly.jsonl`
   * `--third-party-hourly-input data/trend_regime_liquidation_hourly_third_party.jsonl`
   这样才能真实评估 Route A / B / C 三者的 joined_count 与 overlap。

---

## 9. 最终结论
本次审查执行的最终结论为：**`route_b_unavailable_no_key`**。

### 决策依据
由于未配置 `COINALYZE_API_KEY`，Route B 接口返回降级为空；同时本地 Route A 小时级档案当前也为空，因此本轮仍不能对 Route C 做真实 overlap 验证。适配器与 route summary 审计字段在工程上已完工并通过契约测试，下一步阻塞点已经收敛为：`API key + 非空 Route A 小时级档案`。
