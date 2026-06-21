# Stage 1.4E Deleveraging Proxy Sensitivity Review Report

> **注意：** 本次运行为 Deleveraging Proxy Sensitivity Review（去杠杆代理信号敏感性审查），旨在评估 `OI Drop + Price Flush` 作为外生事件过滤器的可行性。
> **本项工作绝非 B-Lite 阶段重启 (not B-Lite restart)，不涉及任何实盘或模拟盘交易决策许可。**

## 最终判定：未通过

| 候选信号 | 事件总数 | 活跃天数 | 4h Replay Median Bps | 4h Random Baseline Bps | 4h Price Baseline Bps | 审查判定 |
|---|---|---|---|---|---|---|
| `deleveraging_proxy_15m` | 11 | 9 | -43.39 | -54.15 | -67.03 | `deleveraging_proxy_failed` |
| `deleveraging_proxy_1h` | 1 | 1 | -31.10 | -57.64 | -16.86 | `deleveraging_proxy_failed` |

### 1. 总体判定
评估代理信号（去杠杆代理）在历史中的统计表现。本审查判定该代理信号是否能通过密度门槛及超额表现门槛，从而存活进入 Stage 1.5 外生事件源的过滤器。

### 2. 做得对的地方
- 实现了纯代理信号（`OI drop + price flush`）的隔离评测。
- 严格隔离了 execution / liquidation / vendor 数据，没有任何真实爆仓数据泄露或主观参数调优。
- 运用了 `symbol-hour matched random baseline` 与 `price-only baseline` 双重基准进行检验。

### 3. 必须修正的问题
本轮为敏感性审查，若存在 `debug_baseline_override_used`（即 trials 未达到 500 次）或 `insufficient_history_duration`（数据历史少于 30 天）或 `data_unsupported`，则 `research_result_valid` 强制设为 `false`。

### 4. 参数 / 阈值 / 证据边界审核
- 15m 价格波动阀值: 2% / OI 下降阀值: -3%
- 1h 价格波动阀值: 3% / OI 下降阀值: -5%
- Cooldown: 15m 候选为 1小时; 1h 候选为 4小时

### 5. 建议执行顺序
若存在 `research_result_valid = true` 且 `decision = deleveraging_proxy_survives_sensitivity_review` 的候选，才允许把对应代理参数作为 Stage 1.5 外生事件源过滤器继续检验。

### 6. 最终意见
仅在 `research_result_valid = true` 且判定为 `deleveraging_proxy_survives_sensitivity_review` 时，该参数组才被允许在 Stage 1.5 中作为过滤条件。

### 7. 数据证据语义风险
- 本项工作**没有使用 (liquidation_used=false)** 真实爆仓流 (forceOrder) 或 vendor 年包数据。
- **Price close** 是价格代理，并非实盘可执行价格 (close_price_proxy_not_fill_price)。
- **OI 数据** 为交易所每5分钟或1小时更新的快照，存在时间对齐误差。

### 8. 本轮能证明什么 / 不能证明什么
- **能证明**：在控制了日内时间效应与单纯价格波动后，去杠杆发生后的短时间内（4h内）是否存在统计学上的价格漂移。
- **不能证明**：真实清算爆仓发生后的阿尔法表现。

### 9. 禁止从本轮结果推出什么结论
- **禁止**将 `up_squeeze_deleveraging_proxy` (signed_direction = -1) 误读为具备做空执行意图 (up squeeze signed replay is diagnostic only and not short execution intent)。
- **禁止**因为通过敏感性审查就略过 Stage 1.5 外生事件源筛选而直接设计交易策略。
- **禁止**声称获得了可实盘交易的复合 Alpha (full_composite_claim_allowed=false)。
- **survives** 判定仅允许将其作为 Stage 1.5 外生事件源的过滤器 (survives only permits use as Stage 1.5 external catalyst filter, not a primary signal)。