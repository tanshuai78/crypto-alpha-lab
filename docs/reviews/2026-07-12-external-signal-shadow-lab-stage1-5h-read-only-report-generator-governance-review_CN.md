# External Signal Shadow Lab Stage 1.5H Read-Only Report Generator Governance Review

**日期:** 2026-07-12
**状态:** governance_review_completed
**治理对象:** Stage 1.5H read-only report generator implementation-plan admission
**关联设计:** `docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md`
**关联设计:** `docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md`

---

## 1. Governance Decision

本 review 明确批准下一步只写 Stage 1.5H read-only report generator 的 implementation plan。

它不批准实现，不批准运行 report generator，不批准 simulator，不批准任何 paper/live/execution claim。

```text
governance_decision = read_only_report_generator_plan_allowed_with_constraints
allowed_next_action = write_read_only_report_generator_implementation_plan
implementation_plan_allowed = true
implementation_allowed = false
scope = single_event_fixture_bound_report_generator
event_family_conclusion_allowed = false
multi_event_aggregation_allowed = false
cross_event_generalization_allowed = false
execution_feasibility_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
private_endpoint_allowed = false
api_key_allowed = false
order_endpoint_allowed = false
```

批准主体和批准方式：

```text
approval_owner = human_research_owner
approval_artifact = docs/reviews/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
governance_approval_must_be_explicit = true
```

---

## 2. Reviewed Inputs

本 review 基于以下已完成文档和 Stage 1.5G 审计事实：

```text
stage1_5h_governance_design = docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-design_CN.md
stage1_5h_static_proxy_design = docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md
stage1_5g_review = docs/reviews/2026-07-11-external-signal-shadow-lab-stage1-5g-live-depth-evidence-review_CN.md
input_event_symbol = SKHYUSDT
```

Stage 1.5G 审计事实：

```text
stage1_5g_decision = stage1_5g_depth_evidence_quarantined_pass
stage1_5g_allowed_next_action = write_stage1_5h_design_only
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
quarantine_candidate = true
formal_announcement_and_launch_count = 1
stage1_5g_blockers = []
```

Quarantine 摘要：

```text
observed_snapshot_count = 718
expected_snapshot_count = 720
invalid_book_row_count = 12
invalid_book_minute_bucket_count = 12
invalid_book_ratio_observed = 0.016713091922005572
valid_snapshot_count_after_quarantine = 706
book_availability_ratio = 0.9805555555555555
book_unavailable_ratio = 0.016666666666666666
max_consecutive_invalid = 11
max_consecutive_invalid_after_warmup = 1
first_valid_book_latency_ms = 661950
quarantine_blockers = []
quarantine_warnings = ["launch_time_missing_warmup_anchor_degraded"]
```

Invalid book phase / reason：

```text
invalid_book_by_phase.observation_initial = 11
invalid_book_by_phase.midrun = 1
invalid_book_by_phase.launch_warmup = 0
invalid_book_by_reason.observation_initial_empty_book = 11
invalid_book_by_reason.midrun_empty_book = 1
invalid_book_by_reason.crossed_or_negative_book = 0
invalid_book_by_reason.schema_invalid = 0
```

Depth quality 事实：

```text
depth_quality_input_mode = quarantined_valid_rows
input_valid_rows = 706
excluded_invalid_rows = 12
spread_bps_p50 ~= 1.1713
spread_bps_p95 ~= 2.9486
buy_slippage_bps_500usdt_p50 ~= 0.8744
buy_slippage_bps_500usdt_p95 ~= 2.0503
sell_slippage_bps_500usdt_p50 ~= 0.8679
sell_slippage_bps_500usdt_p95 ~= 1.8700
top_bid_depth_usdt_p05 ~= 49704.08
top_ask_depth_usdt_p05 ~= 50671.40
healthy_window_ratio = 1.0
```

---

## 3. Why Clean Pass Is Missing

本次治理批准不能把 quarantined pass 洗成 clean pass。

必须保留非 clean 原因：

```json
{
  "clean_depth_evidence_pass": false,
  "quarantined_depth_evidence_pass": true,
  "clean_pass_missing_reason": [
    "invalid_book_present",
    "observation_initial_empty_book_present",
    "midrun_empty_book_present",
    "launch_time_missing_warmup_anchor_degraded"
  ],
  "quarantine_blockers": [],
  "quarantine_warnings": [
    "launch_time_missing_warmup_anchor_degraded"
  ]
}
```

含义：

```text
1. 706 条有效盘口可以支持只读 static proxy report schema 验证。
2. 12 条 invalid book 必须继续作为 execution availability discount 的证据。
3. 前 11 条 observation-initial empty book 说明 launch 初期或 observation 初期不可验证。
4. 1 条 midrun empty book 说明稳定期仍存在低频不可用点。
5. 因缺少可靠 launch_time anchor，不能把 observation_initial 直接命名为 launch_warmup。
```

---

## 4. Governance Checklist

| 条件 | 状态 | 证据 |
|---|---:|---|
| `evidence_scope = single_event` | 通过 | 当前仅 SKHYUSDT |
| `event_family_conclusion_allowed = false` | 通过 | 本 review 显式限制 |
| `cross_event_generalization_allowed = false` | 通过 | 本 review 显式限制 |
| `clean_depth_evidence_pass = false` 被保留 | 通过 | 第 3 章 |
| `quarantined_depth_evidence_pass = true` | 通过 | Stage 1.5G 结果 |
| `execution_feasibility_claim_allowed = false` | 通过 | 第 1 章安全 flags |
| `book_availability_ratio` 存在 | 通过 | 0.9805555555555555 |
| `book_unavailable_ratio` 存在 | 通过 | 0.016666666666666666 |
| `invalid_book_by_phase` 存在 | 通过 | observation_initial 11, midrun 1 |
| `invalid_book_by_reason` 存在 | 通过 | empty book 分类明确 |
| `first_valid_book_latency_ms` 存在 | 通过 | 661950 ms |
| `max_consecutive_invalid_after_warmup` 存在 | 通过 | 1 |
| `depth_quality` 只基于 valid rows | 通过 | input_valid_rows 706, excluded_invalid_rows 12 |
| invalid rows 只进入 availability/stability/risk discount | 通过，但必须在 plan 中测试 | 本 review 作为硬约束 |
| `quarantine_blockers = []` | 通过 | Stage 1.5G quarantine summary |
| `quarantine_warnings` 原样保留 | 通过 | `launch_time_missing_warmup_anchor_degraded` |
| `clean_pass_missing_reason` 存在 | 通过 | 第 3 章定义 |

结论：满足写 read-only report generator implementation plan 的治理条件。

---

## 5. Approved Plan Scope

允许写的下一份 plan 只能是：

```text
docs/plans/YYYY-MM-DD-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
```

计划范围必须固定为：

```text
scope = single_event_fixture_bound_report_generator
input_scope = local_stage1_5g_artifacts_only
output_scope = markdown_and_json_report_only
implementation_allowed = false
```

计划可以设计未来实现以下只读能力：

```text
read stage1_5g_live_depth_evidence_review_summary.json
read stage1_5g_quarantine_summary.json
read depth_quality_input_rows.jsonl
read quarantined_invalid_book_rows.jsonl
validate upstream decisions and safety flags
compute static_proxy_metric
compute availability_discount
compute friction_floor
write single-event static proxy report
write required_next_evidence
```

计划不得扩大为：

```text
event_family_report_generator
multi_event_aggregation
shadow_execution_simulator
order simulation
trade recommendation
execution feasibility proof
paper/live readiness review
```

---

## 6. Downstream-Only Invariants

未来 implementation plan 必须把 Stage 1.5G 作为 source of truth。

必须禁止：

```text
recompute_stage1_5g_decision
override_1_5g_decision
promote_quarantined_to_clean
drop_invalid_rows_without_reporting
```

如果以下 artifacts 不一致，必须 hard fail：

```text
stage1_5g_live_depth_evidence_review_summary.json
stage1_5g_quarantine_summary.json
depth_quality_input_rows.jsonl
quarantined_invalid_book_rows.jsonl
```

Hard fail blocker：

```text
stage1_5h_upstream_artifact_mismatch
```

---

## 7. Safety Boundaries For Future Plan

未来 implementation plan 必须维持以下 flags：

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

严禁输出或实现：

```text
SignalCandidate
TradeIntent
buy/sell instruction
entry recommendation
position size recommendation
virtual_order
hypothetical_trade
entry_exit_path
fill_probability
order_lifecycle_state_machine
pnl_path
paper/live readiness
alpha confirmed claim
execution feasibility proven claim
```

允许输出的最高强度只能是：

```text
single_event_static_proxy_report
design_metric_report
availability_discount_report
friction_floor_report
required_next_evidence
```

---

## 8. Required Tests For Future Implementation Plan

下一份 implementation plan 必须从测试先行开始，至少覆盖：

```text
test_report_generator_requires_explicit_governance_approval_artifact
test_report_generator_rejects_invalid_stage1_5g_input
test_report_generator_accepts_quarantined_input_for_single_event_report_only
test_report_generator_preserves_clean_pass_missing_reason
test_report_generator_preserves_quarantine_warnings
test_report_generator_sets_event_family_conclusion_allowed_false
test_report_generator_sets_multi_event_aggregation_allowed_false
test_report_generator_sets_execution_feasibility_claim_allowed_false
test_report_generator_never_emits_signal_candidate_or_trade_intent
test_report_generator_never_reads_exchange_api
test_report_generator_uses_configs_base_thresholds_only
test_report_generator_invalid_rows_only_affect_availability_discount
test_report_generator_hard_fails_on_upstream_artifact_mismatch
test_report_generator_forbids_order_lifecycle_and_pnl_path_terms
```

Safety grep 必须拆成两类，避免 `orderbook` 噪声：

```bash
rg -n "SignalCandidate|TradeIntent|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true|execution_feasibility_claim_allowed.*true|apiKey|secret|private" src scripts tests docs

rg -n "\\bplace_order\\b|\\bcreate_order\\b|\\border_endpoint\\b|\\border_intent\\b|\\bOrderIntent\\b|\\bfill_simulation\\b|\\border_lifecycle\\b|\\bvirtual_order\\b|\\bhypothetical_trade\\b|\\bentry_exit_path\\b|\\bpnl_path\\b" src scripts tests docs
```

---

## 9. Explicit Non-Approval

本 review 不批准以下事项：

```text
implement_stage1_5h_report_generator
run_stage1_5h_report_generator
write_stage1_5h_shadow_execution_simulator_plan
implement_stage1_5h_simulator
run_shadow_execution_simulator
create SignalCandidate
create TradeIntent
create paper trading path
create live trading path
claim execution feasibility
claim alpha
claim profitability
```

如果后续需要实现 read-only report generator，必须先完成并通过单独的 implementation plan review。

---

## 10. Final Next Action

当前唯一被批准的下一步：

```text
allowed_next_action = write_read_only_report_generator_implementation_plan
implementation_plan_allowed = true
implementation_allowed = false
```

建议文件：

```text
docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
```

该 plan 必须继承本 review 的全部安全边界，并且不得把 SKHYUSDT 单一样本泛化为 event-family 结论。

## 11. Implementation Plan Written

已根据本 governance review 写入 implementation plan：

```text
plan = docs/plans/2026-07-12-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
implementation_plan_allowed = true
implementation_allowed = false
```

该 plan 仍需单独执行和 review，不能直接视为实现批准。
