# External Signal Shadow Lab Stage 0 Review

日期：2026-06-12

## 1. 结论

decision = `external_signal_shadow_stage0_passed`

failure_type = `stage0_completed`

本轮不是 alpha 通过；不是 paper/live 准入；不允许下单；不允许接钱包。

## 2. Stage 0 范围

本轮只验证 fixture-only 研究管线：

```text
fixture events -> Risk Guard -> no-CUSUM / CUSUM branches -> 三重屏障 shadow order -> summary
```

运行边界：

```text
live_trading_enabled = false
external_api_enabled = false
wallet_required = false
```

## 3. 数据与事件覆盖

- events_total: 9
- events_accepted: 7
- events_rejected: 2
- events_quarantined: 0
- price_bars_total: 23

## 4. Risk Guard 结果

Risk Guard 只用于过滤明显不可进入 shadow 的事件，不产生交易信号。

## 5. CUSUM 对照结果

CUSUM 是确认器，不是 alpha。它只回答外部事件后价格是否出现足够大的信息驱动变化。

- no-CUSUM shadow orders: 6
- CUSUM-confirmed shadow orders: 2

## 6. 三重屏障 shadow order 结果

三重屏障是 shadow 评估方法，不是实盘订单模块。

- take_profit_count: 1
- stop_loss_count: 3
- vertical_barrier_count: 2

## 7. 分支语义与参数边界

no-CUSUM branch 是 baseline control，不是策略。

CUSUM branch 是 confirmation-filtered shadow，不是策略。

固定 TP/SL/holding 参数只用于 Stage 0 基础设施 sanity check，不可迁移为真实策略参数。

Stage 1 才允许在预注册参数组下比较事件类型，但不得事后优化。

## 8. 失效类型与归因

可能失效类型：

- data_failure
- risk_guard_density_failure
- cusum_confirmation_failure
- shadow_order_structure_failure
- stage0_completed

本轮归因：`stage0_completed`

## 9. 不能推出的结论

- 不能推出外部 skills 信号有效。
- 不能推出 CUSUM 可以作为买入信号。
- 不能推出三重屏障参数可用于实盘。
- 不能推出 paper/live 可以启用。

## 10. 下一步建议

如果 Stage 0 通过，下一步只允许写 Stage 1 connector design，且每次只接一个只读外部源。
