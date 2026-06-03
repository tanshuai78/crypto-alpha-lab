# Route C1 Live Overlap 状态复核（中文版）

## 结论

当前 Route C1 已经推进到：

```text
decision = route_c1_overlap_ready_for_orderbook_aware
```

这意味着：

- `live liquidation 1m`
- `live 1m price`
- `historical orderbook`

三条链路里，已经有足够输入支撑 `price-only` 路径继续向前走，并且 orderbook-aware 所需的输入重叠门槛也已经满足。

但当前仍然：

```text
ready_for_orderbook_aware = true
```

所以现阶段的准确判断是：

1. Route C1 没有被否掉；
2. `price-only` live overlap 已经成立；
3. `orderbook-aware` 输入门槛也已经成立；
4. 当前最合理动作仍然是继续累计 overlap，等待接近 `7d / 168h` 后再启动正式 live smoke。

## 本次 Audit 结果

最新 overlap audit 摘要如下：

```json
{
  "decision": "route_c1_overlap_ready_for_orderbook_aware",
  "ready_for_price_only": true,
  "ready_for_orderbook_aware": true,
  "liquidation_1m_zero_fill_coverage_24h": 1.0,
  "price_1m_coverage_24h": 1.0,
  "orderbook_snapshot_coverage_24h": 1.0,
  "overlap_hours_by_symbol": {
    "BTCUSDT": 72.55,
    "ETHUSDT": 72.53333333333333,
    "SOLUSDT": 72.0,
    "XRPUSDT": 72.1,
    "DOGEUSDT": 72.08333333333333
  }
}
```

直接解释：

- liquidation 1m 覆盖是满的；
- live 1m price 覆盖是满的；
- orderbook 24h 总覆盖已经满格；
- `BTCUSDT`、`ETHUSDT`、`SOLUSDT`、`XRPUSDT`、`DOGEUSDT` 都已经形成正的 live overlap；
- `BTC/ETH/SOL` 三个主要币种都已经跨过了 orderbook-aware 的输入门槛。

因此，这一步已经不再是“部分 symbol 的 live overlap 还没追上来”，而是“输入链已经准备好，但时间长度还不够做 7 天结论”。

## 成因拆解

### 1. 为什么之前全是 `0.0h`

最开始全符号 `0.0h` 的原因，不是 liquidation 采集失败，也不是 orderbook 不可用，而是 `price-1m` 输入用错了时间窗口。

当时使用的是历史 Q1 2024 proxy 数据集：

- `2024-01-01` 到 `2024-03-31`

而本次 live liquidation 窗口已经在 2026 年，所以时间轴完全错开，overlap 必然全是 `0.0h`。

这个问题已经修复：现在已经基于同步回来的 live liquidation 1m，重新构建了 live 1m price 数据集，因此 `price-only` 链路已经对齐。

### 2. 为什么现在五个币都已经有 overlap

原因也很具体：本地 orderbook 档案已经补齐到了 6 月最新日期。

当前本地最新情况是：

- `BTCUSDT -> 2026-06-03`
- `DOGEUSDT -> 2026-06-03`
- `ETHUSDT -> 2026-06-03`
- `SOLUSDT -> 2026-06-03`
- `XRPUSDT -> 2026-06-03`

所以：

- 五个币种的 orderbook 都已经追上了当前 liquidation 窗口；
- 前一次 `ETH/SOL/XRP = 0.0h` 不是采集逻辑不支持，而是本地同步不完整；
- 补齐同步之后，五个币种都出现了约 `72h` 的正 overlap。

换句话说，现在不再是 orderbook 时间覆盖问题，而是单纯的“样本累计时间还不够长”。

## 对 Route C1 的实际意义

这次结果对 Route C1 有两个重要含义：

### 1. `price-only` 路径可以继续

因为 `ready_for_price_only = true`，说明：

- live liquidation 数据可用；
- live price 数据可用；
- 主要 symbol 已经形成真实 overlap。

这就足以支撑后续继续积累到 `7d live smoke`。

### 2. `orderbook-aware` 输入已经可以启动

`ready_for_orderbook_aware = true`，说明：

- orderbook coverage 已经满足门槛；
- `BTC/ETH/SOL` 都已有正 overlap；
- 当前已经具备进入 orderbook-aware 后续研究的输入条件。

但这仍不等于“orderbook-aware 结论已经成立”，因为：

- 当前 overlap 只有约 `72h`；
- 正式 `7d live smoke` 仍然需要接近 `168h`；
- 所以能下的结论是“输入 ready”，不是“研究结论 ready”。

## 下一步具体计划

### 阶段 1：继续累计 overlap

当前最优先的动作不是改脚本，而是继续收集并同步：

1. 继续让服务器上的 liquidation collector 运行；
2. 继续让 orderbook collector 运行；
3. 定期把服务器上的最新 liquidation / orderbook 同步回本地；
4. 每次同步后重跑 overlap audit。

目标从“让主要币种出现正 overlap”变成“让主要币种的 overlap 从 ~72h 继续累积到接近 168h”。

### 阶段 2：等到接近 7 天再做 live smoke

当前最合理 gate 仍然是：

```text
overlap_hours >= 168
```

在达到这个门槛前：

- 不启动正式 `7d live smoke` 结论；
- 不进入 `30d forward`；
- 不输出 `orderbook-aware C1` 的正式研究结论。

这不是保守过度，而是避免在样本还没长出来时误判。

### 阶段 3：转向“时间累计”而不是“文件补齐”

当前最具体的运维任务是：

1. 继续让 liquidation collector 和 orderbook collector 保持运行；
2. 每天同步一次本地；
3. 每次同步后重跑 overlap audit；
4. 观察 `BTC/ETH/SOL` 的 overlap 是否逐步接近 `168h`。

## 当前阶段的正确表述

当前最准确的研究状态表述应当是：

> Route C1 的历史 `price-only proxy` 结果仍然是 promising；  
> live overlap 已经推进到 `ready_for_orderbook_aware`；  
> 当前 orderbook-aware 输入门槛已满足；  
> 但时间长度仍不足以做 7d 结论，下一步应继续累计 BTC/ETH/SOL 的 overlap，并在接近 7 天后启动 live smoke。

## 不该做的事

当前阶段不应做：

- 不要继续调阈值；
- 不要因为输入门槛已满足，就提前宣布 live filter 可用；
- 不要把 `~72h overlap` 当成 `7d live smoke` 已完成；
- 不要跳过 7d overlap，直接推进 30d forward。

这些动作都会让结论失真。

## 最终判断

一句话总结：

> Route C1 已经从“输入未对齐”推进到“orderbook-aware 输入已准备好，但 live overlap 时长仍不足以做 7d 结论”的阶段。

这属于真实进展，不是最终通过。

下一步不是改研究框架，而是继续收集、同步、复核 overlap，直到满足 `7d live smoke` 的启动条件。
