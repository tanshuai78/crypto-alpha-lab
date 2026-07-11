# Stage 1.5G Live Depth Evidence Review - SKHYUSDT

**审计日期:** 2026-07-11
**审计对象:** `SKHYUSDT` Binance Futures launch live depth evidence
**Stage 1.5F root:** `data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix`
**Stage 1.5G review run:** `data/external_signal_shadow/stage1_5g/reviews/20260711T131211Z`
**最终审计结论:** `stage1_5g_depth_evidence_quarantined_pass`
**允许的下一步行动:** `write_stage1_5h_design_only`

---

## 1. 结论摘要

本次 SKHYUSDT 事件已经完成 Stage 1.5D -> Stage 1.5F -> Stage 1.5G 的 formal live depth evidence 链路审计。

本次不是 clean pass，而是 quarantined pass：

```text
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
quarantine_candidate = true
blockers = []
allowed_next_action = write_stage1_5h_design_only
```

含义：

```text
1. 1.5D 成功捕获 post-watermark futures launch 事件。
2. 1.5F 完成 12h live depth observation。
3. 1.5G 已识别出 1 个 announcement_and_launch_time formal evidence。
4. coverage 与 request health 通过。
5. raw book 中存在 12 条 invalid book，因此不能 clean pass。
6. invalid book 比例低、分布可解释、quarantine 后有效样本仍满足阈值，因此得到 quarantined pass。
```

安全边界：

```text
stage1_5h_implementation_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

本次结果只允许进入 Stage 1.5H design，不允许进入 Stage 1.5H implementation，也不允许做 execution feasibility claim。

---

## 2. 核心审计结果

### 2.1 Evidence 与结论

```text
decision = stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
formal_announcement_and_launch_count = 1
blockers = []
warnings = [launch_time_missing_warmup_anchor_degraded]
```

`launch_time_missing_warmup_anchor_degraded` 的含义：

```text
1. 本次 1.5G 没有拿到可用于 warmup 锚定的 launch_time_ms。
2. 因此前 11 条初期 invalid book 不能严谨称为 launch_warmup_empty_book。
3. 它们被降级分类为 observation_initial_empty_book。
4. 该 warning 不阻断 quarantined pass，但说明本次样本不是 clean evidence。
```

### 2.2 Coverage 与 request health

```text
expected_snapshot_count = 720
observed_snapshot_count = 718
min_snapshot_count_required = 684
valid_snapshot_count_after_quarantine = 706
request_success_rate ~= 0.9986
```

解释：

```text
1. 12h 理论分钟级快照数是 720。
2. 实际审计到 718 条 snapshot。
3. quarantine 后仍有 706 条有效盘口，高于 684 条最低要求。
4. request health 不构成本次阻断。
```

---

## 3. Quarantine 结果

### 3.1 invalid book 总量

```text
invalid_book_row_count = 12
invalid_book_minute_bucket_count = 12
invalid_book_ratio_observed = 12 / 718 = 0.016713091922005572
book_availability_ratio = 706 / 720 = 0.9805555555555555
book_unavailable_ratio = 12 / 720 = 0.016666666666666666
```

解释：

```text
invalid_book_ratio_observed 衡量已抓到 raw rows 中有多少盘口无效。
book_availability_ratio 衡量整个应采集窗口中有多少有效盘口。
```

本次 `book_availability_ratio = 98.06%`，刚好超过第一版 quarantine 阈值 `0.98`。

### 3.2 invalid book 分类

```text
invalid_book_by_phase:
  launch_warmup = 0
  observation_initial = 11
  midrun = 1

invalid_book_by_reason:
  launch_warmup_empty_book = 0
  observation_initial_empty_book = 11
  midrun_empty_book = 1
  crossed_or_negative_book = 0
  schema_invalid = 0
```

解释：

```text
1. 前 11 条 invalid book 发生在 observation 初期，但由于缺少 launch_time_ms，只能标记为 observation_initial_empty_book。
2. 中途有 1 条 midrun_empty_book。
3. 没有 crossed book、negative book 或 schema invalid。
4. 因此这些 invalid rows 可以 quarantine，但不能 clean pass。
```

### 3.3 连续性与首个有效盘口

```text
max_consecutive_invalid = 11
max_consecutive_invalid_after_warmup = 1
first_valid_book_latency_ms = 661950
```

解释：

```text
1. 最大连续 invalid 是 11 条，集中在 observation 初期。
2. 初期之后最大连续 invalid 只有 1 条。
3. 首个有效盘口延迟约 11.03 分钟，低于 15 分钟阈值。
```

该结果说明：

```text
初期盘口可用性不干净，但稳定后只有 1 条中途空盘口。
```

---

## 4. Quarantine 后有效盘口质量

本节只统计 `706` 条 quarantine 后的有效盘口，不包含 `12` 条 invalid book。

### 4.1 Spread 与 slippage

```text
spread_bps_p50 = 1.1712687779075193
spread_bps_p95 = 2.948591635308917
buy_slippage_bps_500usdt_p50 = 0.874380647784001
buy_slippage_bps_500usdt_p95 = 2.050259958923384
sell_slippage_bps_500usdt_p50 = 0.8679232830582917
sell_slippage_bps_500usdt_p95 = 1.8699513715880745
```

解释：

```text
1 bps = 0.01%。
P50 是中位数，代表典型情况。
P95 是 95 分位数，代表较差但非极端最差的情况。
```

含义：

```text
在有效盘口样本中，500 USDT 级别的静态吃单滑点较低。
但这不是扣除成本后的收益，也不是交易可行性结论。
```

### 4.2 Top depth 与 capacity

```text
top_bid_depth_usdt_p05 = 49704.083725000004
top_bid_depth_usdt_p50 = 77252.31575000001
top_ask_depth_usdt_p05 = 50671.400125
top_ask_depth_usdt_p50 = 82837.82325
healthy_window_ratio = 1.0
depth_capacity_ratio_to_risk_cap_p50 = 154.50463150000002
```

解释：

```text
P05 是 5 分位数，代表偏差情况下的低深度底线。
P50 是中位数，代表典型深度。
healthy_window_ratio = 1.0 只针对 quarantine 后的 706 条有效盘口，不包括 12 条 invalid book。
depth_capacity_ratio_to_risk_cap_p50 = 154.5x 表示典型顶部深度约为 500 USDT 风险上限的 154.5 倍。
```

---

## 5. 这是否代表扣除成本后有收益

不代表。

本次 1.5G 只审计 live depth evidence 的数据质量与静态盘口质量。它没有验证：

```text
alpha return
方向收益
手续费后收益
funding / basis 成本
挂单成交概率
撤单失败
延迟风险
冲击成本
入场和退出路径
```

因此本次最多支持下面这个结论：

```text
在 706 条有效盘口样本中，500 USDT 级别的静态盘口摩擦较低；
但由于存在 12 条 invalid book，本样本只能作为 quarantined evidence，不能作为 clean execution feasibility evidence。
```

---

## 6. Artifact 输出

服务器复跑输出：

```text
stage1_5g_live_depth_evidence_review_summary.json
quarantined_invalid_book_rows.jsonl = 12 rows
depth_quality_input_rows.jsonl = 706 rows
stage1_5g_quarantine_summary.json
```

路径：

```text
data/external_signal_shadow/stage1_5g/reviews/20260711T131211Z/quarantined_invalid_book_rows.jsonl
data/external_signal_shadow/stage1_5g/reviews/20260711T131211Z/depth_quality_input_rows.jsonl
data/external_signal_shadow/stage1_5g/reviews/20260711T131211Z/stage1_5g_quarantine_summary.json
```

原始 Stage 1.5F `depth_snapshots/**/*.jsonl` 不允许被修改。上述 artifact 只是 Stage 1.5G 派生审计结果。

---

## 7. 风险与局限性

本次结论必须带 caveat：

```text
1. 本次不是 clean pass。
2. 本次存在 12 / 718 = 1.67% invalid book。
3. book availability 是 98.06%，不是 100%。
4. 由于缺少 launch_time_ms，前 11 条 invalid 只能归为 observation_initial_empty_book。
5. 1 条 midrun_empty_book 表明稳定后仍存在一次不可用盘口。
6. 本审计基于 1-minute REST polling 静态盘口，不代表真实高频撮合环境。
```

严禁事项：

```text
execution_feasibility_claim_allowed = false
stage1_5h_implementation_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

---

## 8. 下一步

允许：

```text
write_stage1_5h_design_only
```

Stage 1.5H design 可以研究：

```text
1. 如何消费 clean / quarantined 两种 1.5G evidence。
2. 如何把 invalid book 作为 execution availability discount。
3. 如何定义 entry/exit 的静态深度门槛。
4. 如何设计后续 shadow simulator 的输入 schema。
5. 哪些条件下 quarantined evidence 必须 hard veto。
```

不允许：

```text
Stage 1.5H implementation
shadow simulator implementation
paper trading
live trading
execution feasibility claim
alpha claim
```

最终结论：

```text
SKHYUSDT Stage 1.5G live depth evidence = quarantined pass。
它证明当前 pipeline 能捕获 post-watermark futures launch 并完成 12h live depth evidence 审计；
但由于存在少量不可用盘口，它只能作为下一阶段 design 输入，不能作为执行可行性证明。
```
