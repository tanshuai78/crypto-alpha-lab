# Stage 1.5G Live Depth Evidence Review - SKHYUSDT

**审计对象:** `SKHYUSDT` Binance Futures launch live depth evidence
**Stage 1.5F root:** `data/external_signal_shadow/stage1_5f/live_depth_observer_7d_detail_retry_scheduler_starvation_hotfix`
**最终审计结论:** `stage1_5g_depth_evidence_invalid`
**允许的下一步行动:** `continue_observation`
**交易权限:** `trade_signal_allowed=False`, `paper_trading_allowed=False`, `live_trading_allowed=False`, `execution_engine_allowed=False`

## 1. 结论摘要

本次 SKHYUSDT 事件已经完成从 1.5D 到 1.5F 的 live evidence 链路验证，但未通过 1.5G 的 raw snapshot integrity hard gate。

已通过部分：

- 1.5D 成功捕获 post-watermark futures launch 事件。
- 1.5F 成功接受 SKHYUSDT，并完成 12h live depth observation。
- 1.5G 已识别为 `announcement_and_launch_time` formal evidence。
- coverage 通过：`718` 条快照，高于最低要求 `684`。
- request health 通过：单币请求成功率约 `0.9986`。

未通过部分：

- raw snapshot integrity 未通过。
- blocker: `invalid_book`。
- invalid snapshot count: `12 / 718`，约 `1.67%`。
- 12 条异常快照均为 depth endpoint 返回空/无效盘口：`best_bid=null`, `best_ask=null`, `spread_bps=null`, `depth_status=invalid`, `slippage_status=invalid_depth`。

当前结论：

```text
Stage 1.5D event capture: pass
Stage 1.5F live depth collection: pass
Stage 1.5G formal evidence recognition: pass
Stage 1.5G coverage/request health: pass
Stage 1.5G raw snapshot integrity: fail
```

因此，本次样本不能作为完全 clean 的 1.5G formal depth evidence；不得据此进入交易信号、paper trading、live trading 或 alpha 结论解释。

## 2. 本次失败的直接原因

`invalid_book` 的 12 条异常行主要集中在观察开始后的前 11 分钟，另有 1 条出现在中途。

典型异常行特征：

```json
{
  "symbol": "SKHYUSDT",
  "best_bid": null,
  "best_ask": null,
  "spread_bps": null,
  "depth_status": "invalid",
  "slippage_status": "invalid_depth",
  "top_bid_depth_usdt": 0.0,
  "top_ask_depth_usdt": 0.0
}
```

这说明 1.5F 在这些分钟请求 Binance depth 时，没有拿到有效 bids/asks。对新上线合约，这类情况可能来自：

- 合约已进入 exchangeInfo，但盘口尚未稳定。
- Binance depth endpoint 在 launch 初期返回空 bids/asks。
- 做市/撮合初始化阶段出现短时不可用。
- 中途单次 API payload 可解析但盘口为空。

这不是 1.5D 未捕获事件，也不是 1.5F 没有采够 12h，而是 raw orderbook evidence 中存在少量无效盘口切片。

## 3. 这几轮 1.5G 修补内容

本次审计过程中，1.5G 暴露了多处与真实 1.5F artifacts 不兼容的问题。已经修补的是审查层兼容性问题，不是对原始数据做人工改写。

### 3.1 evidence label 字段兼容

问题：

- 1.5G 原来只读取 `evidence_label`。
- 真实 1.5F accepted event 写入的是 `live_depth_evidence_basis`。
- 导致 1.5G 误报 `missing_evidence_label`。

修补：

- 1.5G 现在读取 `evidence_label`，缺失时 fallback 到 `live_depth_evidence_basis`。

### 3.2 watermark 校验语义修正

问题：

- 1.5G 原来要求 accepted event 记录的 watermark 必须等于当前 `watermark.json`。
- 真实运行中，accepted event 记录的是事件被接收时的旧 watermark；当前 watermark 会继续推进。
- 导致正常 post-watermark event 被误判为 `watermark_max_seen_detected_at_ms_mismatch`。

修补：

- 合法条件改为：`event_watermark <= current_watermark`。
- 只有 event watermark 大于当前 watermark，才视为脏数据。

### 3.3 coverage 检查范围修正

问题：

- 1.5G 原来检查所有 observer states。
- 真实 `observer_state.jsonl` 是状态历史流，同一个 `event_symbol_id` 有多条 active/completed 行。
- 早期 active 行的 `depth_snapshot_count` 很低，导致误报 `insufficient_depth_snapshot_count`。

修补：

- 按 `event_symbol_id` 只取最新 state。
- coverage 只检查 formal completed event symbols。
- `checked_event_symbol_ids` 用于审计实际检查对象。

### 3.4 raw snapshot schema 兼容

问题：

- 1.5F `DepthSnapshot` 不写 `mid_price`。
- 1.5G raw integrity 原来强制要求 `mid_price` 非空。
- 导致真实 1.5F 快照被批量误判为 `invalid_book`。

修补：

- 当 `mid_price` 缺失但 `best_bid`/`best_ask` 存在时，1.5G 用 `(best_bid + best_ask) / 2` 推导。
- 仍保留 `bid<=0`, `ask<=0`, `bid>=ask`, `spread_bps<0` 等硬校验。

## 4. 为什么修补后仍然失败

前述修补清理的是审查层兼容性误判。修补后，1.5G 能正确进入真实 raw integrity 检查。

最终剩余的 `12` 条 invalid book 是真实数据问题：这些快照中没有有效 bid/ask，不是字段兼容问题。按当前 1.5G 设计，raw snapshot integrity 是 hard gate：只要存在 invalid book，就判定本次 evidence invalid。

这条规则保守但合理，因为如果 raw orderbook 自身不可用，后续 spread/slippage/top-depth 分位数会被污染。

## 5. Quarantine 思路说明

`quarantine` 的含义不是修改原始数据，也不是假装 invalid book 不存在。

它的含义是：

1. 保留所有原始 snapshot rows。
2. 将无效盘口行单独标记为 `quarantined_invalid_book_rows`。
3. 不让这些无效行参与 depth quality 计算。
4. 在 summary 中显式报告 invalid count、invalid ratio、发生位置和原因。
5. 只有在 invalid ratio 足够低、且不破坏 12h 证据完整性的前提下，才允许继续进入 depth quality。

对本次样本，quarantine 后的口径可能是：

```text
total_snapshots = 718
invalid_book_count = 12
invalid_book_ratio = 1.67%
valid_snapshots_for_depth_quality = 706
```

建议候选阈值，仅供后续 design 评审：

```text
EXTERNAL_SIGNAL_STAGE1_5G_MAX_INVALID_BOOK_RATIO = 0.02
EXTERNAL_SIGNAL_STAGE1_5G_MAX_LAUNCH_WARMUP_INVALID_MINUTES = 15
```

如果采用这个规则，本次前 11 分钟 launch warmup 空盘口可能被 quarantine；但第 321 条中途 invalid 仍需单独计入全局 invalid ratio。

## 6. Quarantine 的风险

采用 quarantine 会改变 1.5G 的证据定义，因此不能作为临时小补丁直接放行。

主要风险：

- 可能掩盖真实流动性不可用风险。
- 新合约 launch 初期正是交易风险最高阶段，过滤掉前几分钟可能高估执行可行性。
- 如果 invalid rows 集中在价格剧烈波动区间，删除它们会让 depth quality 看起来过于乐观。
- 对实盘执行而言，`best_bid/best_ask=null` 代表该分钟不可成交，不能简单视为无害噪声。

因此，即使采用 quarantine，也只能支持：

```text
allowed_next_action = write_stage1_5h_design_or_continue_observation
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
```

不得直接推出 event-family alpha 结论。

## 7. 待评审问题

建议请其他 agent 重点评估以下问题：

1. 1.5G 是否应保持 raw integrity hard gate，即任意 invalid book 都 invalid？
2. 是否允许 `invalid_book_ratio <= 2%` 时 quarantine 后继续 depth quality？
3. launch warmup invalid book 是否应与中途 invalid book 分开统计？
4. 如果前 15 分钟被 quarantine，depth quality 是否仍能代表 launch-time execution feasibility？
5. 1.5H 是否只需要 design evidence，还是必须要求 0 invalid book 的 clean evidence？
6. 对个人投资者 500 USDT 风险上限而言，1.67% invalid book 是否已经足够说明执行风险过高？

## 8. 当前建议

短期建议：

- 保留本次 1.5G invalid 结论，不手工改写为 pass。
- 继续保留 1.5D/1.5F 运行，等待下一个事件。
- 不要基于 SKHYUSDT 本次样本进入 1.5H execution simulator implementation。
- 若要推进，应先写 `Stage 1.5G raw snapshot quarantine design`，再决定是否实现。

最终状态：

```text
research_result_valid = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```
