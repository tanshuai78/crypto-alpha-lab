# Trend Liquidation-Cascade Independent Review Report

> **范围声明**
> 本报告仅用于对 `liquidation_cascade`（爆仓瀑布）独立子策略在离线回放与数据源路线层面的可行性审查。本审计基于 1h K 线价格与持仓变化，并结合本地自采的强平订单数据。研究所采用的强平数据存在明显的覆盖范围局限，不代表实盘撮合的真实滑点或全市场成交表现。

---

## 1. 策略定义

为了克服旧混合分类器的方向模糊问题，我们将 `liquidation_cascade` 进行了物理方向的严格定义与解耦，不与波动突破逻辑混淆：
* **多头强平级联 (long_liquidation)**：对应多头头寸爆仓（SELL 强平单，即价格下跌引起的被动卖出），在回放中定义为：
  - Price Return < 0.0 (价格下跌)
  - Open Interest Change < 0.0 (持仓量萎缩，杠杆头寸被动出清)
  - `long_liquidation_notional_1h_usdt` 达到 symbol tier 门槛（SELL 强平金额触及强平压力上限）。
  - *对应交易假说*：顺势做空 (`continuation_direction = short`)，或逆势做多 (`mean_reversion_direction = long`)。
* **空头强平级联 (short_liquidation)**：对应空头头寸爆仓（BUY 强平单，即价格上涨引起的被动买回），在回放中定义为：
  - Price Return > 0.0 (价格上涨)
  - Open Interest Change < 0.0 (持仓量萎缩，杠杆头寸被动出清)
  - `short_liquidation_notional_1h_usdt` 达到 symbol tier 门槛（BUY 强平金额触及强平压力上限）。
  - *对应交易假说*：顺势做多 (`continuation_direction = long`)，或逆势做空 (`mean_reversion_direction = short`)。

---

## 2. 数据源路线比较

针对历史强平数据短缺的瓶颈，我们评估了三条具体的数据源推进路线：

| 数据路线 (Data Route) | 可用性 | 来源质量评级 | 覆盖深度 (Hours) | 决策约束与影响 |
| :--- | :---: | :--- | :---: | :--- |
| **Route A**: 自采 forceOrder 唯一 | **True** | `self_collected_partial_history` | 498.0h | **仅能支持 `continue_data_route_upgrade`**。禁止因 Route A 零信号而直接淘汰策略。 |
| **Route B**: 第三方历史唯一 | **False** | `not_connected` | 0.0h | feasibility 审计已完成：当前候选供应商为 Coinglass，具备 1h 粒度与 365d 历史深度潜力，但本环境缺少 paid API key，因此当前仍不可接通。 |
| **Route C**: 混合自采+第三方历史 | **False** | `requires_route_b_and_route_a` | 0.0h | 理想终局方案，支持历史长窗口回放与未来实盘漂移校验。 |

---

## 3. 当前历史覆盖

* **历史回放区间**: 2026-05-08 02:59:59.999 至 2026-05-28 21:59:59.999
* **时间覆盖**: 498.0 小时（约 20.75 天）
* **观察币种**: 5 个 (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `XRP/USDT`, `DOGE/USDT`)
* **本地强平数据加入率 (Liquidation Rows Joined)**: 0 行
* **未连接第三方数据 (Third-party data connected)**: 0 行

> [!WARNING]
> 由于强平流本地 WS 监听数据在回放时段内尚未积累（Joined = 0），本次回放实际处于**强平覆盖缺失状态**。

---

## 4. 独立 Cascade 事件密度

基于 `Route A`（当前自采数据缺口）：
* **触发入场事件数 (Entry Event Count)**: 0
* **30天换算事件数 (Events per 30d)**: 0.0
* **资本利用效率评估 (Capital Utilization)**: **too_sparse** (缺失强平数据导致无事件触发)

### 拦截 Bottleneck 分析
在总计 2,495 行回放记录中，拒绝原因分布如下：
- `missing_liquidation_fields`: 2,465 行 (占比 **98.8%**) —— 由于本地未累积对应时间戳的强平数据，导致数据链断裂被直接拦截。
- `volume_below_min`: 30 行 (占比 **1.2%**) —— DOGE 等币种 24h 交易额未达 minimum 门槛。

---

## 5. 成本后 shadow 结果

由于 `baseline_current` 下的事件触发数为 0：
* **模拟交易次数**: 0
* **中位数净收益**: 0.0 bps
* **平均净收益**: 0.0 bps
* **胜率 / 止损离场率**: 0.0%

---

## 6. 参数放宽后的变化 (Sensitivity Analysis)

即使将参数阶梯式放宽（下调强平金额压力要求），其信号密度依然为 0：
- **baseline_current** (`10M / 3M` 强平压力): 0 事件
- **moderately_relaxed** (`5M / 1.5M` 强平压力): 0 事件
- **aggressive_relaxed** (`2M / 0.5M` 强平压力): 0 事件

这印证了：**当前无信号是由于历史强平数据覆盖（Route A）为 0 导致的，并非由于阈值过严所致。**

---

## 7. 个人投资者视角评价

个人投资者运行 `liquidation_cascade` 的核心痛点是**数据获取能力不对称**。自采 WebSocket 链路（Route A）由于只能采集部署后的数据，且属于 Binance 的部分强平快照（lower-bound proxy），若以此为唯一依据，在 historical replay 阶段将面临长达数月的“无信号”观察期，资本利用率极低。必须打通 Route B 或 C 获取长达数月的第三方完整历史数据集，才能科学判断该策略是否具有可交易的 Alpha。

---

## 8. 数据源推荐路线

当前**不应直接推荐 Route C 作为已可执行主线**。更准确的推荐是：
1. **当前主动作**：继续执行 `continue_data_route_upgrade`，优先打通 Route B（第三方历史 liquidation 数据）。
2. **历史回放 (Replay)**：若 Route B 接通，则先用第三方历史 liquidation 数据回填过去数月的爆仓量，完成顺势与均值回归策略的期望校验。
3. **未来目标路线**：只有在 Route B 接通且能与本地自采 Route A 形成重叠窗口时，才升级为 **Route C (hybrid_forceorder_plus_third_party)**，用于后续 drift 校验。

---

## 9. 最终结论

本次审查执行的最终结论为：**continue_data_route_upgrade**。

### 决策依据与行动项
* **禁止淘汰策略**：由于当前 Route A 的覆盖窗口极短（498h）且 liquidation 字段完全缺失，无法判定策略本身的 Alpha 潜力。因此，禁止做出 `retire_liquidation_cascade_branch` 决策。
* **启动数据路线升级**：
  - 当前 feasibility 审计已确认 Coinglass 具备候选潜力，但缺少 paid developer API key；下一步应补齐凭证和接入条件，而不是继续假设 Route C 已可执行。
  - 在打通第三方强平数据（Route B）后，重新跑通 Task 4 中的 hypotheses 双模式回放，获取至少 720h 完整覆盖后再行做出去留审查决策。
