# External Signal Shadow Lab Stage 1.5H Read-Only Report Generator Governance Design

**日期:** 2026-07-12  
**状态:** governance_design_draft  
**适用阶段:** Stage 1.5H governance  
**关联设计:** `docs/designs/2026-07-12-external-signal-shadow-lab-stage1-5h-static-execution-proxy-design_CN.md`  
**当前允许动作:** `write_governance_design_only`

---

## 1. 一句话结论

本 governance design 不授权实现 Stage 1.5H。

它只回答一个治理问题：

```text
在当前只有 stage1_5g_depth_evidence_quarantined_pass、没有 clean pass 的情况下，
是否允许未来另写 implementation plan，实现一个只读 report generator？
```

当前结论：

```text
governance_review_required = true
governance_review_artifact_required = true
governance_approval_must_be_explicit = true
implementation_plan_allowed_now = false
read_only_report_generator_allowed_now = false
required_next_action = governance_review
```

如果 governance review 后决定放行，也只能放行一个严格受限的 read-only report generator：

```text
read local Stage 1.5G / Stage 1.5F artifacts
compute static proxy metrics
write derived report
no exchange calls
no order simulation
no SignalCandidate
no TradeIntent
no paper/live/execution claim
```

---

## 2. Governance Problem

Stage 1.5G 已经为 SKHYUSDT 输出：

```text
decision = stage1_5g_depth_evidence_quarantined_pass
allowed_next_action = write_stage1_5h_design_only
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
execution_feasibility_claim_allowed = false
```

Stage 1.5H static proxy design 因此把当前 allowed action 收窄为：

```text
write_stage1_5h_design_review
revise_stage1_5h_design
wait_for_clean_or_additional_quarantined_evidence
```

问题是：

```text
如果我们永远等待 clean evidence，可能长期无法把 1.5H 的 report schema 和安全边界落地验证。
如果我们直接允许 implementation plan，又会把 quarantined evidence 错读成执行可行性。
```

本文件的作用是建立中间治理层：只有当 governance review 明确批准时，才允许写一个 read-only report generator implementation plan。

批准主体和批准方式：

```text
approval_owner = human_research_owner
approval_artifact_required = docs/reviews/YYYY-MM-DD-external-signal-shadow-lab-stage1-5h-read-only-report-generator-governance-review_CN.md
approval_must_include = governance_decision
```

该 review artifact 必须显式写入：

```text
governance_decision = read_only_report_generator_plan_allowed_with_constraints
```

否则默认：

```text
governance_decision = read_only_report_generator_plan_blocked
```

---

## 3. Non-Negotiable Safety Boundaries

无论 governance 结果如何，以下边界不能改变：

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

read-only report generator 也不得输出：

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

允许输出的最高强度只能是：

```text
single_event_static_proxy_report
design_metric_report
availability_discount_report
required_next_evidence
```

禁止输出：

```text
execution_feasible
tradeable
profitable
alpha_positive
ready_for_paper
ready_for_live
```

---

## 4. Evidence Governance

### 4.1 Clean evidence

如果未来出现：

```text
stage1_5g_depth_evidence_clean_pass
clean_depth_evidence_pass = true
blockers = []
```

则 governance 可以允许：

```text
allowed_next_action = write_stage1_5h_implementation_plan
implementation_allowed = false
```

含义：

```text
可以写 implementation plan，但仍不能直接实现。
implementation plan 必须再经过 review。
```

### 4.2 Quarantined evidence

当前 SKHYUSDT 属于：

```text
stage1_5g_depth_evidence_quarantined_pass
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
```

默认治理结论：

```text
implementation_plan_allowed = false
```

只有满足本文件第 5 章的额外治理条件，才可以把下一步提升为：

```text
allowed_next_action = write_read_only_report_generator_implementation_plan
implementation_allowed = false
```

注意：这仍然不是实现许可。

### 4.3 Invalid evidence

如果输入为：

```text
stage1_5g_depth_evidence_invalid
```

则必须：

```text
allowed_next_action = continue_observation
read_only_report_generator_plan_allowed = false
```

---

## 5. Quarantined Evidence 放行到 Implementation Plan 的额外条件

Quarantined evidence 只有在以下条件全部满足时，才允许写 read-only report generator implementation plan：

```text
1. evidence_scope = single_event
2. event_family_conclusion_allowed = false
3. cross_event_generalization_allowed = false
4. clean_depth_evidence_pass = false
5. quarantined_depth_evidence_pass = true
6. execution_feasibility_claim_allowed = false
7. book_availability_ratio 明确存在
8. execution_availability_discount 明确存在
9. invalid_book_by_phase / invalid_book_by_reason 明确存在
10. first_valid_book_latency_ms 明确存在
11. max_consecutive_invalid_after_warmup 明确存在
12. depth_quality 只基于 quarantined valid rows
13. invalid rows 只用于 availability/stability/risk discount
14. output schema 明确禁止 trade/execution/paper/live 字段为 true
15. quarantine_blockers = []
16. quarantine_warnings 必须原样保留到 output
17. clean_pass_missing_reason 必须存在
```

当前只有一个 SKHYUSDT quarantined event-symbol，因此即使 governance review 未来放行，也只能是 fixture-bound / single-event 范围：

```text
scope = single_event_fixture_bound_report_generator
event_family_report_generator_allowed = false
multi_event_aggregation_allowed = false
```

不能用一个 quarantined sample 建立治理惯例，也不能泛化为 futures_contract_launch family report generator。

必须保留非 clean evidence 的原因：

```json
{
  "clean_depth_evidence_pass": false,
  "quarantined_depth_evidence_pass": true,
  "clean_pass_missing_reason": [
    "invalid_book_present",
    "launch_warmup_empty_book_present",
    "midrun_empty_book_present"
  ],
  "quarantine_warnings": []
}
```

如果任一条件缺失：

```text
governance_decision = read_only_report_generator_plan_blocked
```

---

## 6. Allowed Read-Only Report Generator Scope

如果 governance review 通过，允许的实现范围仅限：

```text
input:
  - stage1_5g_live_depth_evidence_review_summary.json
  - stage1_5g_quarantine_summary.json
  - depth_quality_input_rows.jsonl
  - quarantined_invalid_book_rows.jsonl

processing:
  - validate safety flags
  - validate 1.5G decision and evidence scope
  - compute static proxy summary
  - compute availability discount
  - compute friction floor using approved config values
  - write markdown/json report

output:
  - stage1_5h_static_execution_proxy_report_summary.json
  - docs/reviews/YYYY-MM-DD-...stage1_5h-static-execution-proxy-report_CN.md
```

Downstream-only 不变量：

```text
1.5H report generator is downstream-only.
1.5G decision is source-of-truth.
```

禁止：

```text
recompute_stage1_5g_decision
override_1_5g_decision
promote_quarantined_to_clean
drop_invalid_rows_without_reporting
```

如果 `stage1_5g_live_depth_evidence_review_summary.json`、`stage1_5g_quarantine_summary.json`、`depth_quality_input_rows.jsonl`、`quarantined_invalid_book_rows.jsonl` 之间不一致：

```text
hard_fail = stage1_5h_upstream_artifact_mismatch
```

Explicitly forbidden:

```text
read exchange API
read account state
place or simulate order lifecycle
virtual_order
hypothetical_trade
entry_exit_path
fill_probability
order_lifecycle_state_machine
pnl_path
emit order intent
emit strategy signal
compute forward return
compute alpha PnL
generate paper/live readiness
```

允许的计算对象只能是：

```text
static_proxy_metric
availability_discount
friction_floor
required_next_evidence
```

---

## 7. Required Governance Output

本 governance design 若后续实现为 review 工具，必须输出：

```json
{
  "governance_decision": "read_only_report_generator_plan_blocked",
  "allowed_next_action": "revise_governance_design",
  "implementation_plan_allowed": false,
  "implementation_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "execution_feasibility_claim_allowed": false,
  "evidence_scope": "single_event",
  "event_family_conclusion_allowed": false,
  "cross_event_generalization_allowed": false,
  "blockers": [],
  "warnings": []
}
```

如果 governance review 允许写 plan，只能输出：

```json
{
  "governance_decision": "read_only_report_generator_plan_allowed_with_constraints",
  "allowed_next_action": "write_read_only_report_generator_implementation_plan",
  "implementation_plan_allowed": true,
  "implementation_allowed": false,
  "scope": "single_event_fixture_bound_report_generator",
  "event_family_conclusion_allowed": false,
  "multi_event_aggregation_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "execution_engine_allowed": false,
  "execution_feasibility_claim_allowed": false
}
```

重点：

```text
implementation_plan_allowed = true
不等于 implementation_allowed = true
```

---

## 8. Config Governance

如果未来写 implementation plan，所有 1.5H 阈值必须进入 `configs/base.py`。

建议配置命名：

```python
EXTERNAL_SIGNAL_STAGE1_5H_MAX_SPREAD_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MAX_BUY_SLIPPAGE_500USDT_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MAX_SELL_SLIPPAGE_500USDT_P95_BPS
EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_BID_DEPTH_USDT_P05
EXTERNAL_SIGNAL_STAGE1_5H_MIN_TOP_ASK_DEPTH_USDT_P05
EXTERNAL_SIGNAL_STAGE1_5H_MIN_BOOK_AVAILABILITY_RATIO
EXTERNAL_SIGNAL_STAGE1_5H_MAX_FIRST_VALID_BOOK_LATENCY_MS
EXTERNAL_SIGNAL_STAGE1_5H_MIN_EVENT_FAMILY_SAMPLE_REQUIRED
```

如果复用 `EXTERNAL_SIGNAL_STAGE1_5G_*` 阈值，implementation plan 必须逐项说明复用理由。

不得在 `src/` 或 `scripts/` 中硬编码阈值。

---

## 9. Required Tests For Future Plan

如果 governance review 允许写 implementation plan，implementation plan 必须从以下测试开始：

```text
test_governance_blocks_quarantined_input_by_default
test_governance_allows_only_read_only_report_generator_plan_after_explicit_approval
test_report_generator_rejects_invalid_stage1_5g_input
test_report_generator_accepts_quarantined_input_for_single_event_report_only
test_report_generator_sets_event_family_conclusion_allowed_false
test_report_generator_sets_execution_feasibility_claim_allowed_false
test_report_generator_never_emits_signal_candidate_or_trade_intent
test_report_generator_never_reads_exchange_api
test_report_generator_uses_configs_base_thresholds_only
test_report_generator_invalid_rows_only_affect_availability_discount
```

Safety grep:

```bash
rg -n "SignalCandidate|TradeIntent|paper_trading_allowed.*true|live_trading_allowed.*true|execution_engine_allowed.*true|execution_feasibility_claim_allowed.*true|apiKey|secret|private" src scripts tests docs

rg -n "\\bplace_order\\b|\\bcreate_order\\b|\\border_endpoint\\b|\\border_intent\\b|\\bOrderIntent\\b|\\bfill_simulation\\b|\\border_lifecycle\\b|\\bvirtual_order\\b|\\bhypothetical_trade\\b|\\bentry_exit_path\\b|\\bpnl_path\\b" src scripts tests docs
```

新增 1.5H 代码不得引入任何 private/order/API key 路径。

---

## 10. Current Decision

基于当前事实：

```text
input_evidence = SKHYUSDT
input_stage1_5g_decision = stage1_5g_depth_evidence_quarantined_pass
clean_depth_evidence_pass = false
quarantined_depth_evidence_pass = true
evidence_scope = single_event
```

本 governance design 当前不直接放行 implementation plan。

当前治理状态：

```text
governance_decision = read_only_report_generator_plan_blocked_pending_fixes
implementation_plan_allowed = false
implementation_allowed = false
```

当前允许：

```text
review_this_governance_design
revise_this_governance_design
wait_for_clean_or_additional_quarantined_evidence
```

当前不允许：

```text
write_stage1_5h_implementation_plan
implement_stage1_5h_report_generator
implement_stage1_5h_simulator
run_shadow_execution_simulator
paper_trading
live_trading
execution_feasibility_claim
```

只有在本 governance design 经过 review 并明确输出：

```text
governance_decision = read_only_report_generator_plan_allowed_with_constraints
```

之后，才允许写：

```text
docs/plans/YYYY-MM-DD-external-signal-shadow-lab-stage1-5h-read-only-report-generator-implementation-plan_CN.md
```
