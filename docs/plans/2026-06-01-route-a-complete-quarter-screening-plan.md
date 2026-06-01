# Route A Complete-Quarter Proxy Validation Screening Plan

**Date:** 2026-06-01

## Goal

在继续 Route A 之前，先做一个低成本的季度筛选步骤，只回答一个问题：

> 是否存在一个 **完整季度**，能让 `BTC/ETH/SOL` 在 Binance snapshot proxy 路径下形成一个足够完整的 3-coin proxy universe，值得继续跑完整的 `1m shock -> 5/10/15m response` 结构验证？

这个步骤**不直接跑 full event-study**，只做：

1. 数据可用性筛选
2. continuity 筛选
3. 最低事件密度筛选

如果连这一步都过不去，就不值得继续为 Route A 投入更多时间。

---

## Why This Step Exists

当前 `Q1 2024` 的 Binance snapshot 分支失败，不只是因为结构没有站稳，也因为研究 universe 本身不完整：

- `BTC/ETH` 完整
- `SOL` 缺 `2024-02`
- `XRP/DOGE` 完全缺席

因此，当前结果无法回答一个更窄但仍然有意义的问题：

- `如果换一个季度，BTC/ETH/SOL 能不能形成一个完整的 proxy study universe？`

Route A 的这一小步，就是专门回答这个问题。

---

## Screening Universe

本步骤固定：

- Symbols: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`
- Exchange semantics:
  - Price = Binance Vision `UM 1m kline`
  - Liquidation = Binance Vision `CM liquidationSnapshot` proxy

不包含：

- `XRPUSDT`
- `DOGEUSDT`

因为在当前 Binance Vision 路径下，它们不具备稳定可用的 liquidationSnapshot 映射。

---

## Candidate Quarter Rules

候选季度必须按自然季度筛：

- `2023-Q1`: `2023-01 / 2023-02 / 2023-03`
- `2023-Q2`: `2023-04 / 2023-05 / 2023-06`
- `2023-Q3`: `2023-07 / 2023-08 / 2023-09`
- `2023-Q4`: `2023-10 / 2023-11 / 2023-12`
- `2024-Q1`: `2024-01 / 2024-02 / 2024-03` as baseline reference

优先原则：

1. 优先挑 **能形成完整 3-coin 样本** 的季度
2. 如果多个季度都通过，再优先挑：
   - continuity 更干净
   - event density 更均匀
   - 非极端单一行情窗口

---

## Pass Criteria

一个季度只有同时满足下面条件，才允许进入 Route A 下一阶段。

### Gate 1: File Availability

对 `BTC/ETH/SOL` 每个月都要求：

- monthly `1m kline` 可用
- daily `liquidationSnapshot` 文件覆盖完整

季度总要求：

- `3 symbols × 3 months = 9 symbol-months`
- `available_symbol_months == 9`

### Gate 2: Price Continuity

每个 symbol-month：

- `price_coverage_ratio >= 0.99`
- `price_max_gap_minutes <= 1`

季度总要求：

- `price_continuity_pass_symbol_months == 9`

### Gate 3: Liquidation File Coverage

每个 symbol-month：

- `liquidation_file_coverage_ratio == 1.0`

季度总要求：

- `liq_file_pass_symbol_months == 9`

### Gate 4: Quarter Integrity

季度必须满足：

- `quarter_universe_integrity_ok = true`

也就是：

- `BTC/ETH/SOL` 三个币
- 三个月都完整通过

如果少一个月、少一个币，直接不进入完整 Route A。

### Gate 5: Minimum Event Density

在通过 continuity 的季度上，再做一个轻量事件密度检查：

- total deduplicated events >= `120`
- each month events >= `25`
- each symbol total events >= `20`

这是一个**继续门槛**，不是最终结构确认门槛。

---

## Stop Conditions

出现以下任一情况，就停止 Route A，不继续做完整季度 proxy validation：

1. 所有候选季度都无法形成完整 `BTC/ETH/SOL` 样本
2. 虽然有完整样本，但事件密度太低
3. 完整样本只出现在一个非常明显的单边极端季度，导致解释价值太低

如果出现这些情况，更合理的路线是：

- 转 Route C
- 或直接换更完整 vendor

---

## Output Artifacts

本步骤完成后，至少应输出：

- `reports/liquidation_shock_event_study/route_a_quarter_screening_summary.json`
- `docs/reviews/2026-06-01-route-a-quarter-screening-review.md`

summary 至少包含：

- candidate quarters
- per-quarter file availability
- per-quarter continuity pass count
- per-quarter liquidation file coverage pass count
- per-quarter event density
- final decision:
  - `route_a_quarter_found`
  - `route_a_quarter_not_found`

---

## Decision After Screening

### If a quarter passes

Then Route A can be redefined as:

- `BTC/ETH/SOL complete-quarter proxy validation`

and continue into a fresh implementation/review branch.

### If no quarter passes

Then Route A should be considered exhausted under the current Binance Vision proxy path.

At that point:

- do **not** keep forcing the original event-study on partial proxy data
- move to:
  - `Route B` if willing to pay for better historical data
  - `Route C` if willing to change the research question
