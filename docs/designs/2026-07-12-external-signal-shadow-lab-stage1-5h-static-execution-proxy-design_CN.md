# External Signal Shadow Lab Stage 1.5H Static Execution Proxy Design

**日期:** 2026-07-12  
**状态:** design_draft  
**适用阶段:** Stage 1.5H  
**上游依赖:** Stage 1.5G Live Depth Evidence Review  
**当前允许动作:** `write_stage1_5h_design_only`

---

## 1. 一句话结论

Stage 1.5H 不是交易系统，也不是 alpha 证明器。

它的目标是设计一个只读、离线、可审计的 static execution proxy，用 Stage 1.5G 审计后的 live depth evidence 回答一个更窄的问题：

```text
在不下单、不产生 SignalCandidate、不接入 execution engine 的前提下，
公开 1-minute REST 盘口证据是否足以支持下一步设计更严格的执行代理模型？
```

当前 SKHYUSDT 的 Stage 1.5G 结论是：

```text
decision = stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
execution_feasibility_claim_allowed = false
```

因此本文件只能定义 1.5H 的设计边界、输入、指标和失败条件；不能写 implementation plan，不能启动 simulator implementation，不能运行任何 simulated orders。

证据范围：

```text
evidence_scope = single_event
event_family_conclusion_allowed = false
cross_event_generalization_allowed = false
```

---

## 2. 安全边界

Stage 1.5H 必须继承 1.5G 的全部安全边界。

```text
trade_signal_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
execution_feasibility_claim_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
```

禁止输出：

```text
SignalCandidate
TradeIntent
buy/sell instruction
entry recommendation
position size recommendation
paper/live readiness
alpha confirmed claim
execution feasibility proven claim
```

允许输出：

```text
static_execution_proxy_design_metrics
static_orderbook_execution_proxy
execution_availability_discount
friction_estimate
risk_blockers
required_next_evidence
```

核心约束：

```text
1. 1.5H 只能消费 1.5G 审计过的 evidence。
2. 1.5G invalid evidence 不能进入 1.5H。
3. 1.5G quarantined evidence 只能进入 design-only 分析。
4. clean evidence 也不能直接打开 paper/live；它只允许后续单独审核 implementation plan。
5. 当前 quarantined evidence 不允许推进 implementation plan。
6. 如果任何下游代码尝试 emit `SignalCandidate`、`TradeIntent`、order intent、paper/live flag 或 `execution_feasibility_claim`，Stage 1.5H 必须返回 safe no-op，并写 hard blocker。
```

---

## 3. 为什么需要 Stage 1.5H

Stage 1.5F 解决的是“有没有 live orderbook 录像”。

Stage 1.5G 解决的是“这段录像是否足够干净、完整、可审计”。

Stage 1.5H 要解决的是下一层问题：

```text
即使盘口 evidence 通过，个人小资金是否能在这些盘口条件下合理建模执行？
```

这不是收益判断。它只评估执行约束：

```text
spread 是否过宽
500 USDT taker slippage 是否过高
top-of-book depth 是否足够
launch 初期无盘口是否导致不可执行窗口
midrun invalid book 是否代表流动性中断
public REST 1-minute snapshot 是否足以支持后续更细模拟
```

当前 SKHYUSDT 样本说明：

```text
valid_snapshot_count_after_quarantine = 706
expected_snapshot_count = 720
book_availability_ratio = 0.9806
first_valid_book_latency_ms = 661950
max_consecutive_invalid = 11
max_consecutive_invalid_after_warmup = 1
spread_bps_p50 ~= 1.17
spread_bps_p95 ~= 2.95
buy_slippage_bps_500usdt_p95 ~= 2.05
sell_slippage_bps_500usdt_p95 ~= 1.87
```

这些数字说明有效盘口质量不错，但不是 clean evidence。1.5H 必须把 `book_availability_ratio < 1.0` 和 launch 初期连续 invalid 作为 execution availability discount，而不是把 706 条有效盘口洗成 100% 可执行。

---

## 4. Scope / Non-Scope

### 4.1 Scope

Stage 1.5H design 范围：

```text
input:
  - Stage 1.5G review summary
  - Stage 1.5G quarantine summary
  - Stage 1.5G depth_quality metrics
  - Stage 1.5F depth_quality_input_rows.jsonl if quarantined
  - Stage 1.5F raw depth_snapshots for audit reference only

output design:
  - execution availability model
  - static orderbook execution proxy
  - friction model
  - scenario matrix
  - blocker taxonomy
  - required future governance gates
```

对 quarantined input，`Stage 1.5F raw depth_snapshots` 只能用于审计追溯。`quarantined invalid rows` 不能参与 spread/slippage/top-depth 计算，只能参与 availability、stability 和 risk discount 计算。

如果未来单独获批实现，Stage 1.5H 也只能做离线 read-only report generator，名称应固定为：

```text
stage1_5h_static_execution_proxy_report_generator
```

允许行为：

```text
read local JSONL
compute proxy metrics
write reports
never call exchange
never place orders
never emit SignalCandidate or TradeIntent
```

### 4.2 Non-Scope

Stage 1.5H 不做：

```text
alpha forecast
forward return replay
real order placement
paper trading
live trading
execution engine integration
private endpoint query
account balance query
funding / liquidation / OI factor modelling
strategy entry signal generation
position sizing recommendation
```

如果后续需要研究收益，需要另建 Stage 1.5I / Stage 1.6 design，不能把收益逻辑塞进 1.5H。

---

## 5. Evidence Admission Rules

### 5.1 Clean evidence

允许作为最强 1.5H 输入：

```text
stage1_5g_depth_evidence_clean_pass
clean_depth_evidence_pass = true
quarantined_depth_evidence_pass = false
blockers = []
```

允许的下一步：

```text
write_stage1_5h_implementation_plan_after_separate_review
```

该路径要求：

```text
1. Stage 1.5G evidence 必须是 clean pass。
2. 必须另行通过 implementation-plan review。
3. clean pass 也不等于允许 implementation / paper / live。
```

仍然禁止：

```text
paper_trading
live_trading
execution_feasibility_claim
```

### 5.2 Quarantined evidence

允许作为 design-only 输入：

```text
stage1_5g_depth_evidence_quarantined_pass
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
quarantine_candidate = true
blockers = []
```

必须附带：

```text
execution_availability_discount
book_unavailable_ratio
first_valid_book_latency_ms
max_consecutive_invalid
max_consecutive_invalid_after_warmup
invalid_book_by_phase
invalid_book_by_reason
```

允许的下一步：

```text
revise_or_finalize_stage1_5h_design
```

禁止：

```text
write_stage1_5h_implementation_plan
implement_stage1_5h_simulator
run_shadow_execution_simulator
paper_trading
live_trading
execution_feasibility_claim
```

### 5.3 Invalid evidence

不得进入 Stage 1.5H：

```text
stage1_5g_depth_evidence_invalid
allowed_next_action = continue_observation
```

如果仍强行输入，应输出 hard blocker：

```text
stage1_5h_input_invalid_1_5g_evidence
```

---

## 6. Core Model

Stage 1.5H 只能使用 static public depth snapshots，不能假装知道真实成交队列、maker fill、撮合延迟或隐藏流动性。

因此第一版只设计三个模型层：

### 6.1 Execution availability model

衡量“该时间点是否存在可验证双边盘口”：

```text
book_available = depth_status == valid and best_bid > 0 and best_ask > best_bid
availability_ratio = valid_book_count / expected_snapshot_count
unavailable_ratio = invalid_book_count / expected_snapshot_count
```

对 quarantined evidence：

```text
execution_availability_discount = book_availability_ratio
unavailable_minutes_are_not_tradeable = true
```

解释：

```text
如果 availability_ratio = 0.9806，
不能说 12h 内 100% 可执行，只能说约 98.06% 的预期采样点有可验证盘口。
```

### 6.2 Static taker execution proxy

使用 1.5F 已计算的 500 USDT buy/sell slippage proxy：

```text
buy_slippage_bps_500usdt_p50
buy_slippage_bps_500usdt_p95
sell_slippage_bps_500usdt_p50
sell_slippage_bps_500usdt_p95
spread_bps_p50
spread_bps_p95
```

第一版只允许固定 notional：

```text
EXTERNAL_SIGNAL_STAGE1_5G_SLIPPAGE_TEST_NOTIONAL_USDT = 500.0
RISK_MAX_SINGLE_POSITION_USDT = 500.0
```

不允许在 1.5H design 中提高 notional。

### 6.3 Maker-first feasibility proxy

当前 1-minute REST snapshots 不能证明 maker order 会成交。

第一版只能输出弱代理：

```text
maker_queue_fill_probability = unknown
maker_first_feasibility = not_proven
```

可以设计观察项：

```text
spread_bps_p50
spread_bps_p95
best_bid/best_ask continuity
top_bid_depth_usdt_p05 / p50
top_ask_depth_usdt_p05 / p50
```

但不能把这些解释成 maker fill 证明。

Maker-first proxy 第一版不能输出 pass/fail feasibility，只能输出 `required_next_evidence`：

```text
higher_frequency_orderbook
trade prints
best_bid_ask_continuity_below_1min
post_only_rejection_model_design
queue_position_model_design
```

这些是后续研究需求，不是 1.5H 当前能解决的问题。

---

## 7. Friction Model

Stage 1.5H 必须把 execution friction 拆开，不得只看 spread 或 slippage 单项。

建议第一版指标：

```text
entry_taker_friction_bps = buy_slippage_bps_500usdt + taker_fee_bps
exit_taker_friction_bps = sell_slippage_bps_500usdt + taker_fee_bps
observed_static_depth_friction_bps = buy_slippage_bps_500usdt + sell_slippage_bps_500usdt
availability_adjusted_tradeable_ratio = book_availability_ratio
```

成本来源必须明确，且禁止 double-count：

```text
1. `EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS = 50.0` 是项目级保守总成本口径，不等同于 fee。
2. `observed_static_depth_friction_bps` 只来自 1.5G 的 buy/sell slippage proxy。
3. 两个口径不得相加，避免 double-count。
4. 如果未来引入 Binance futures taker fee，必须新增 configs/base.py 显式配置，不能硬编码。
```

第一版建议同时输出两组口径：

```text
observed_static_depth_friction_bps = buy_slippage_bps_500usdt + sell_slippage_bps_500usdt
configured_conservative_round_trip_cost_bps = EXTERNAL_SIGNAL_SHADOW_COST_ROUND_TRIP_BPS
effective_friction_floor_bps = max(observed_static_depth_friction_bps, configured_conservative_round_trip_cost_bps)
```

注意：

```text
slippage / spread / fee 都是成本，不是收益。
1.5H 不能因为成本低就推断有 alpha。
```

---

## 8. Scenario Matrix

第一版只设计场景，不实现。

### 8.1 Time windows

建议场景：

```text
launch_warmup_window:
  [launch_time_ms, launch_time_ms + 15min)

post_first_valid_book_window:
  [first_valid_book_at_ms, first_valid_book_at_ms + 60min)

full_12h_window:
  completed observation window
```

如果 `launch_time_ms` 缺失：

```text
launch_warmup_window 不可用
observation_initial_window 可用于降级分析
warning = launch_time_missing_warmup_anchor_degraded
```

### 8.2 Notional levels

第一版只允许不超过风险上限：

```text
100 USDT
250 USDT
500 USDT
```

其中 500 USDT 对齐：

```text
RISK_MAX_SINGLE_POSITION_USDT
EXTERNAL_SIGNAL_STAGE1_5G_SLIPPAGE_TEST_NOTIONAL_USDT
```

如果没有 100 / 250 USDT 的 depth ladder 细分数据，后续实现只能报告 500 USDT proxy，不得插值伪造。

### 8.3 Order style

第一版只允许两种代理口径：

```text
taker_proxy:
  使用 500 USDT buy/sell slippage proxy + cost model。

maker_first_proxy:
  只输出 not_proven，并列出需要更高频 orderbook / trade prints 的证据。
```

不允许设计：

```text
actual order placement
post-only fill simulation with unobserved queue position
market impact model beyond observed depth
```

---

## 9. Decision Taxonomy

Stage 1.5H 后续如果获批实现 read-only report generator，应输出独立 decision，不复用 1.5G decision。

建议 taxonomy：

| decision | 含义 | allowed_next_action |
|---|---|---|
| `stage1_5h_input_rejected` | 1.5G invalid / missing metrics | `continue_observation` |
| `stage1_5h_design_only_input_accepted` | 1.5G quarantined evidence 可用于设计讨论 | `revise_or_finalize_stage1_5h_design` |
| `stage1_5h_clean_input_ready_for_implementation_plan_review` | 1.5G clean evidence 可用于写 implementation plan 草案 | `write_stage1_5h_implementation_plan` |
| `stage1_5h_single_event_proxy_observation_pass` | 未来实现后，单事件静态代理观察通过 | `write_next_research_design_only` |
| `stage1_5h_static_execution_proxy_failed` | 代理指标不满足阈值 | `continue_observation_or_revise_hypothesis` |

第一版必须保证：

```text
stage1_5h_single_event_proxy_observation_pass != execution_feasibility_proven
stage1_5h_single_event_proxy_observation_pass != event_family_conclusion
quarantined input => implementation_plan_allowed = false
```

---

## 10. Blocker Taxonomy

必须 hard fail 的情况：

```text
input_stage1_5g_decision_invalid
missing_stage1_5g_summary
missing_depth_quality_metrics
missing_quarantine_metrics_for_quarantined_input
book_availability_ratio_below_threshold
first_valid_book_latency_too_high
max_consecutive_invalid_after_warmup_too_high
spread_p95_too_high
buy_slippage_p95_too_high
sell_slippage_p95_too_high
top_bid_depth_p05_too_low
top_ask_depth_p05_too_low
request_health_below_threshold
coverage_below_threshold
attempt_to_emit_trade_signal
attempt_to_enable_paper_or_live
```

Quarantined input 专属 blocker：

```text
quarantined_input_used_for_implementation
quarantined_input_missing_availability_discount
quarantined_input_claims_clean_evidence
```

阈值来源要求：

```text
所有 1.5H blocker 阈值必须来自 configs/base.py。
不得在 src/ 或 scripts/ 中硬编码。
```

后续 implementation plan 至少需要新增或复用以下配置：

```python
EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05
EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05
EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO
EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS
```

如果决定复用 `EXTERNAL_SIGNAL_STAGE1_5G_*` 阈值，也必须在 implementation plan 中显式说明复用理由，不能隐式继承。

---

## 11. Output Schema Sketch

后续实现计划应要求 summary 至少包含：

```json
{
  "decision": "stage1_5h_design_only_input_accepted",
  "allowed_next_action": "revise_or_finalize_stage1_5h_design",
  "implementation_plan_allowed": false,
  "input_stage1_5g_decision": "stage1_5g_depth_evidence_quarantined_pass",
  "clean_depth_evidence_input": false,
  "quarantined_depth_evidence_input": true,
  "execution_feasibility_claim_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "evidence_scope": "single_event",
  "event_family_conclusion_allowed": false,
  "cross_event_generalization_allowed": false,
  "risk_cap_notional_usdt": 500.0,
  "slippage_test_notional_usdt": 500.0,
  "book_availability_ratio": 0.9806,
  "execution_availability_discount": 0.9806,
  "first_valid_book_latency_ms": 661950,
  "max_consecutive_invalid": 11,
  "max_consecutive_invalid_after_warmup": 1,
  "spread_bps_p50": 1.17,
  "spread_bps_p95": 2.95,
  "buy_slippage_bps_500usdt_p95": 2.05,
  "sell_slippage_bps_500usdt_p95": 1.87,
  "configured_conservative_round_trip_cost_bps": 50.0,
  "observed_static_depth_friction_bps": 3.92,
  "effective_friction_floor_bps": 50.0,
  "maker_first_feasibility": "not_proven",
  "blockers": [],
  "warnings": [
    "quarantined_depth_evidence_not_clean",
    "execution_availability_discount_required",
    "maker_fill_not_proven_by_1m_rest_depth"
  ]
}
```

字段解释：

```text
execution_availability_discount:
  由于 invalid book / unavailable snapshot 导致的可执行时间折扣。

configured_conservative_round_trip_cost_bps:
  项目级保守总成本口径，不是实际 Binance fee tier，不能与 observed slippage 机械相加。

observed_static_depth_friction_bps:
  只来自有效盘口中的 buy/sell slippage proxy。

effective_friction_floor_bps:
  max(observed_static_depth_friction_bps, configured_conservative_round_trip_cost_bps)。

maker_first_feasibility:
  1-minute REST snapshots 无法证明 maker fill。
```

---

## 12. Testing Requirements For Future Implementation

后续如果写 implementation plan，必须先写测试：

```text
test_stage1_5h_rejects_invalid_stage1_5g_input
test_stage1_5h_accepts_quarantined_input_for_design_only
test_stage1_5h_quarantined_input_cannot_enable_implementation
test_stage1_5h_clean_input_can_write_implementation_plan_not_paper_live
test_stage1_5h_requires_availability_discount_for_quarantined_input
test_stage1_5h_never_emits_signal_candidate_or_trade_intent
test_stage1_5h_uses_risk_cap_from_configs_base
test_stage1_5h_reports_maker_fill_not_proven
test_stage1_5h_blocks_missing_depth_quality_metrics
test_stage1_5h_cost_model_does_not_infer_alpha
```

安全 grep：

```bash
rg -n "SignalCandidate|TradeIntent|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true|apiKey|secret|private" src scripts tests docs
```

期望：

```text
Stage 1.5H 新代码不得新增任何交易许可、私有 endpoint、API key 或 order endpoint 路径。
```

---

## 13. SKHYUSDT Design-Only Interpretation

基于当前已完成 1.5G review，SKHYUSDT 可以作为 1.5H design-only motivating example。

可说：

```text
1. 706 / 720 expected snapshots 在 quarantine 后可用于 post-first-valid-book static proxy 设计分析。
2. 500 USDT slippage proxy 在有效盘口中看起来低。
3. top-of-book depth 相对 500 USDT risk cap 有较大余量。
4. 盘口可用率不是 100%，需要 execution availability discount。
5. launch observation 初期存在连续 invalid book，不能证明 launch 首分钟或 launch warmup 可执行。
6. 本样本只能支持 single_event_execution_proxy_observation，不能推导 futures_contract_launch family execution quality。
```

窗口解释必须更窄：

```text
launch_warmup_window:
  unavailable / not_proven
  reason = first_valid_book_latency_ms ~= 661950 and max_consecutive_invalid = 11

post_first_valid_book_window:
  eligible_for_static_proxy_discussion

full_12h_window:
  availability_discounted_proxy_only
```

不可说：

```text
1. SKHYUSDT 已证明 execution feasible。
2. SKHYUSDT 有 alpha。
3. 500 USDT 可以实盘交易。
4. maker-first 一定能成交。
5. quarantined pass 等于 clean pass。
```

---

## 14. 下一步

当前允许：

```text
write_stage1_5h_design_review
revise_stage1_5h_design
wait_for_clean_or_additional_quarantined_evidence
```

当前不允许：

```text
write_stage1_5h_implementation_plan
implement_stage1_5h_simulator
run_shadow_execution_simulator
paper_trading
live_trading
execution_feasibility_claim
```

推进建议：

```text
1. 先审查本 design 是否过度放宽 quarantined evidence。
2. 让其他 agent 重点检查 fee/slippage/availability 三者是否被混淆。
3. 只有后续出现 clean evidence，或另写 governance/design 证明 quarantined evidence 也可用于 read-only report generator，才允许讨论 implementation plan。
4. implementation plan 若未来获批，必须 TDD，并且第一步就是 safety invariant tests。
```
