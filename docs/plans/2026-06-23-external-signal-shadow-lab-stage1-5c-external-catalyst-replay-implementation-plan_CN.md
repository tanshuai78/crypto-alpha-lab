# External Signal Shadow Lab Stage 1.5C External Catalyst Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现 `Stage 1.5C External Catalyst Replay`，对 Stage 1.5B 生成的 Binance 高可信 external catalyst event table 做首小时延迟、价格覆盖、流动性代理、成本、baseline、cell-level replay 与集中度审计，判断事件表是否值得进入下一阶段 live smoke collector 设计。

**Architecture:** 新增独立 `stage1_5c_external_catalyst_replay_*` 模块，只读取 Stage 1.5B normalized symbol-event table 与 Binance USD-M futures 15m price archive。第一版只实现 `Group 1-3` 的 first-hour-delay base replay，不接入 funding/OI/liquidation context labels，不做 execution engine，不输出 paper/live/alpha 结论。所有方向、entry delay、forward window、baseline、pass gate 均预注册并写入 `configs/base.py`。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、JSON/JSONL、pytest、ruff、`PYTHONPATH=src:.`。

---

## 0. 执行边界

```text
decision = approved_for_implementation_plan_only
scope = external_catalyst_base_replay_only
source_stage_required = stage1_5b_event_table_ready
price_join_allowed = true
forward_return_allowed = true
random_baseline_allowed = true
price_baseline_allowed = true
context_label_join_allowed = false
funding_oi_liquidation_context_allowed = false
execution_engine_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
alpha_interpretation_allowed = false
short_execution_intent_allowed = false
mixed_event_type_pass_claim_allowed = false
top_level_promising_claim_allowed = false
```

Stage 1.5C 只能回答：

```text
在保守 available_at、首小时延迟、价格覆盖、成本、baseline 和集中度约束下，
external catalyst event type 是否出现值得继续审计的历史 replay 结构？
```

Stage 1.5C 不能回答：

```text
是否可以实盘
是否可以 paper trade
某个公告是否应该做多/做空
futures launch 或 delisting 是否已经确认 alpha
是否可以跳过 live smoke collector
```

### 0.1 上游输入事实

Stage 1.5B 当前输出：

```text
stage1_5b_decision = stage1_5b_event_table_ready
article_level_row_count = 94
normalized_symbol_event_count = 194
unique_event_days = 81
symbols_with_events = 191
replay_allowed = false
stage1_5c_replay_candidate_allowed = false
```

允许进入 1.5C loader 的 event types 仍然只有：

```text
exchange_delisting_notice
futures_contract_launch
```

### 0.2 第一版范围选择

第一版取消无延迟 `Group 0`。首小时不交易是 Stage 1.5 的硬安全约束，不再实现公告后立即入场的 event-only replay。

Filter group 与 entry delay 是两个独立维度：

```text
filter_group:
  G1_source_event_after_first_hour_delay
    = Stage 1.5B event + first_hour_no_trade_policy；只作为 attrition denominator，不单独声明收益结构。

  G2_price_coverage_only
    = G1 + price_coverage_pass；允许 close-price replay。

  G3_price_coverage_plus_liquidity_proxy
    = G2 + liquidity_proxy_pass；只说明 replay 的执行相关性更高，仍不证明可实盘。

entry_delay_dimension:
  entry_delay_hours = 1 / 4 / 12
```

第一版不实现 `asset_quality_pass`。理由：Stage 1.5B 的 `BASEUSDT` 是研究符号假设，不证明可交易 pair、流动性或主流资产质量。若在 1.5C v1 硬塞资产白名单，样本会被人为截断，无法判断失败来自事件无效还是白名单过窄。资产质量第一版只通过 price coverage 与 liquidity proxy 分层报告。

不实现：

```text
Group 4: local_liquidation_context_present
Group 5a/5b/5c: funding/OI context
Group 6: market_regime_context hard filter
```

理由：Stage 1.4B-Lite 与 1.4E 已经说明 funding/OI/price proxy 不应继续作为 primary entry rule。Stage 1.5C 第一版先验证 external catalyst 本身和基础安全过滤器是否有结构，避免把内生变量重新混入。

### 0.3 Review Fixes Absorbed Before Coding

```text
review_decision = approved_with_major_required_fixes_absorbed
must_not_code_original_plan_without_these_changes = true
```

Required corrections absorbed in this plan:

```text
1. Removed no-delay Group 0; first-hour no-trade is mandatory.
2. Removed undefined asset_quality_pass from v1.
3. Split price_coverage_pass from liquidity_proxy_pass.
4. Renamed Stage 1.5C quality gate fields to avoid collision with Stage 1.5B stage1_5c_replay_candidate_allowed.
5. Made decisions cell-level: event_type + signed_mode + entry_delay + filter_group.
6. Defined primary metric unit so event_count is not multiplied by forward windows or cost scenarios.
7. Kept futures launch long/short modes separate for density and pass gates.
8. Fixed delisting replay anchor as notice-time, not effective-time.
9. Excluded catalyst cooldown windows from price_move_baseline.
10. Added coverage attrition funnel.
11. Tightened max_single_symbol_event_share from 0.60 to 0.50.
12. Made gitignore check a hard gate.
```

---

## 1. Inputs / Outputs

### 1.1 Required inputs

Stage 1.5B normalized event table:

```text
data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl
```

Stage 1.5B summary:

```text
data/external_signal_shadow/stage1_5b/normalization_summary.json
```

Futures price archive:

```text
data/external_signal_shadow/derivatives_stress/price/binance_um_futures_15m_180d.jsonl
```

Optional report-only OI archive, not used for entry or pass gates in first version:

```text
data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl
```

### 1.2 Outputs

Replay candidate rows:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl
```

Per-event replay rows:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl
```

Machine-readable summary:

```text
data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

Chinese review:

```text
docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md
```

---

## 2. Core Semantics

### 2.1 Price archive schema normalization

The 15m price archive must normalize each row to:

```json
{
  "symbol": "BTCUSDT",
  "bar_start_ms": 1710000000000,
  "bar_end_ms": 1710000900000,
  "open": 0.0,
  "high": 0.0,
  "low": 0.0,
  "close": 0.0,
  "quote_volume": 0.0,
  "source": "binance_um_futures_15m"
}
```

Supported raw timestamp aliases:

```text
bar_start_ms
open_time
timestamp
timestamp_ms
```

Supported price field aliases:

```text
open / high / low / close
quote_volume / quoteVolume / volume_quote
```

### 2.2 Price coverage gate

For each symbol event, Stage 1.5C must verify:

```text
entry_bar exists after entry_candidate_time_ms
forward windows 1h / 4h / 12h / 24h are complete
price_bar_interval_median_ms <= 15m
price_bar_interval_p95_ms <= 30m
min_price_history_days_before_event >= 30
```

Rows failing coverage are not close-price replay candidates and must output fields that do not collide with Stage 1.5B naming:

```json
{
  "stage1_5b_replay_candidate_allowed_upstream": false,
  "price_coverage_gate_passed": false,
  "candidate_allowed_for_close_price_replay": false,
  "candidate_allowed_for_execution_relevance": false,
  "price_history_coverage_verified": false,
  "coverage_reject_reason": "missing_entry_bar|forward_window_incomplete|insufficient_pre_event_history|price_interval_unsupported"
}
```

Do not emit `stage1_5c_replay_candidate_allowed` from Stage 1.5C quality/candidate code. That field belongs to the upstream Stage 1.5B contract and means "1.5B did not pre-authorize replay".

### 2.3 Tradability and liquidity proxy gate

Stage 1.5C does not prove live tradability. It can only mark research feasibility via price archive coverage and quote volume proxy.

First version:

```text
market_pair_existence_verified = true only if symbol appears in 15m futures price archive before event
tradability_verified = false always
liquidity_proxy_verified = true only if median pre-event 24h quote_volume >= configured threshold
execution_feasibility_unknown = true unless orderbook/depth archive exists
```

Price coverage and liquidity proxy are separate gates:

```json
{
  "price_coverage_pass": true,
  "liquidity_proxy_pass": false,
  "candidate_allowed_for_close_price_replay": true,
  "candidate_allowed_for_execution_relevance": false
}
```

Replay rows may be produced for `price_coverage_pass=true` even when `liquidity_proxy_pass=false`. The summary must compare `G2_price_coverage_only` versus `G3_price_coverage_plus_liquidity_proxy` instead of silently dropping low-liquidity events.

No orderbook/depth archive means:

```text
close_price_replay_only = true
execution_relevance_claim_allowed = false
live_or_shadow_upgrade_allowed = false
```

### 2.4 Entry semantics

Entry is not event time. Entry is delayed.

Pre-registered delays:

```text
entry_delay_hours = 1h / 4h / 12h
primary_entry_delay_hours = 1h
```

Entry candidate time:

```text
entry_candidate_time_ms = available_at_ms + entry_delay_hours * 3600_000
```

Entry bar:

```text
entry_bar = first 15m bar where bar_start_ms >= entry_candidate_time_ms
entry_price = entry_bar.open
```

Do not use event bar close. Do not use any bar whose `bar_start_ms < entry_candidate_time_ms`.

### 2.5 Forward windows

Forward windows:

```text
forward_windows_hours = 1 / 4 / 12 / 24
primary_forward_window_hours = 4
```

Exit bar:

```text
exit_target_ms = entry_bar.bar_start_ms + forward_window_hours * 3600_000
exit_bar = first 15m bar where bar_start_ms >= exit_target_ms
exit_price = exit_bar.open
```

If exit bar does not exist, mark `forward_window_complete = false` and skip that replay row.

### 2.6 Event direction semantics

Stage 1.5C freezes event-type evaluation modes before implementation:

```text
exchange_delisting_notice:
  mode = delisting_avoid_long_or_signed_short_diagnostic
  signed_direction = -1
  short_execution_intent_allowed = false
  borrow_or_margin_feasibility_checked = false

futures_contract_launch:
  mode_a = futures_launch_long_attention_diagnostic
  signed_direction = +1
  mode_b = futures_launch_short_access_diagnostic
  signed_direction = -1
  both modes report separately
  no post-hoc best-mode selection allowed
```

Interpretation:

```text
signed_direction = +1 means signed replay return = long return.
signed_direction = -1 means signed replay return = -long return.
```

This is diagnostic signed replay only. It does not imply short execution is feasible or allowed.

Futures launch signed modes must report density separately:

```json
{
  "event_type": "futures_contract_launch",
  "raw_symbol_event_count": 94,
  "signed_mode_count": {
    "futures_launch_long_attention_diagnostic": 94,
    "futures_launch_short_access_diagnostic": 94
  },
  "do_not_sum_signed_modes_for_density_gate": true
}
```

Delisting replay anchor is explicitly notice-time based:

```text
delisting_replay_anchor = notice_time_available_at
effective_time_replay_not_implemented = true
```

Do not interpret delisting rows as effective-date replay unless a later stage parses and validates `effective_time_ms`.

### 2.7 Cost model

Cost scenarios:

```text
cost_scenarios_bps = 30 / 50 / 80
primary_cost_bps = 50
```

Gross and net return:

```text
long_gross_return_bps = (exit_price / entry_price - 1) * 10000
signed_gross_return_bps = long_gross_return_bps * signed_direction
net_return_bps_after_cost = signed_gross_return_bps - cost_bps
```

### 2.8 Baselines

Required baselines:

```text
symbol_hour_matched_random_baseline
price_move_baseline
event_type_matched_baseline
btc_regime_report_only_baseline
```

Random baseline sampling must match:

```text
event_count
symbol distribution
event_type distribution
signed_direction distribution
hour-of-day distribution
weekday if possible
exclude candidate timestamps
require complete forward windows
fixed random_seed
random_baseline_trials >= 500 for valid research result
```

Debug override is allowed only with:

```json
{
  "baseline_trials_override_used": true,
  "research_result_valid": false,
  "top_level_decision": "stage1_5c_replay_completed",
  "promising_cells": [],
  "debug_result_valid_for_research": false
}
```

Price move baseline:

```text
For signed_direction = +1:
  baseline events use same symbol/hour universe where prior 1h return >= configured threshold.
For signed_direction = -1:
  baseline events use same symbol/hour universe where prior 1h return <= -configured threshold.
Same entry delay, forward windows, cost scenarios, and cooldown must be applied.
Price move baseline must exclude exact candidate entry windows and the same symbol within configured cooldown_hours of any external catalyst event.
```

Event-type matched baseline:

```text
Within each event_type and signed_mode, sample random timestamps matching symbol/hour/weekday.
Do not mix exchange_delisting_notice and futures_contract_launch into a single pass claim.
```

BTC regime baseline is report-only in first version:

```text
btc_return_24h buckets: up / flat / down
Used for context report only, not pass gate.
```

### 2.9 Event cooldown / overlap control

Same symbol + event_type + signed_mode events must apply cooldown:

```text
cooldown_hours = 24
keep earliest event in a cooldown cluster
```

Reason: Binance may publish related updates close together; overlapping forward windows inflate sample count.

### 2.10 Cell-level decision scope

Stage 1.5C must decide at the cell level, not from a mixed top-level aggregate.

Cell key:

```text
cell_key = event_type + signed_mode + entry_delay_hours + filter_group
```

Cell decisions:

```text
stage1_5c_cell_promising
stage1_5c_cell_sparse_inconclusive
stage1_5c_cell_failed
stage1_5c_cell_invalid
```

Top-level summary is only an aggregate status:

```text
top_level_decision = stage1_5c_replay_completed | stage1_5c_replay_invalid
promising_cells = []
cell_summaries = {...}
```

Top-level `stage1_5c_replay_promising` is forbidden. A positive result means at least one pre-registered cell is promising, while mixed event-type totals remain report-only.

Even if a cell is promising, allowed next action is only:

```text
write_stage1_5d_live_event_source_smoke_collector_design
write_execution_feasibility_data_audit_plan_if_considering_shadow
```

It does not allow paper/live, execution readiness, or alpha confirmation.

---

## 3. Config Constants

Add to `configs/base.py`:

```python
# ─── External Signal Shadow Lab Stage 1.5C: External Catalyst Replay ────────

EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_P95_MAX_INTERVAL_MS = 30 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_PRICE_HISTORY_DAYS = 30

EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS = (1, 4, 12)
EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_ENTRY_DELAY_HOURS = 1
EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS = (1, 4, 12, 24)
EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS = 4

EXTERNAL_SIGNAL_STAGE1_5C_COST_SCENARIOS_BPS = (30, 50, 80)
EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS = 50

EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_TRIALS = 500
EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_SEED = 42
EXTERNAL_SIGNAL_STAGE1_5C_PRICE_MOVE_BASELINE_1H_RETURN_BPS = 150
EXTERNAL_SIGNAL_STAGE1_5C_LEFT_TAIL_PERCENTILE = 5
EXTERNAL_SIGNAL_STAGE1_5C_EVENT_COOLDOWN_HOURS = 24

EXTERNAL_SIGNAL_STAGE1_5C_MIN_EVENT_COUNT = 30
EXTERNAL_SIGNAL_STAGE1_5C_MIN_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_5C_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRIMARY_EVENT_TYPE_EVENTS = 20
EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_DAY_EVENT_SHARE = 0.30
EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.50
EXTERNAL_SIGNAL_STAGE1_5C_MAX_TOP5_POSITIVE_GROSS_PROFIT_SHARE = 0.40

EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_24H_QUOTE_VOLUME_USDT = 50_000_000
EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES = (
    "exchange_delisting_notice",
    "futures_contract_launch",
)
EXTERNAL_SIGNAL_STAGE1_5C_FILTER_GROUPS = (
    "G1_source_event_after_first_hour_delay",
    "G2_price_coverage_only",
    "G3_price_coverage_plus_liquidity_proxy",
)
```

---

## 4. Implementation Tasks

## Task 1: Add Stage 1.5C Config Tests

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_config.py`

**Step 1: Write failing test**

```python
from configs import base


def test_stage1_5c_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_INTERVAL_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRICE_BAR_P95_MAX_INTERVAL_MS == 30 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_MIN_PRE_EVENT_PRICE_HISTORY_DAYS == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_ENTRY_DELAY_HOURS == (1, 4, 12)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_ENTRY_DELAY_HOURS == 1
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_FORWARD_WINDOWS_HOURS == (1, 4, 12, 24)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_FORWARD_WINDOW_HOURS == 4
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_COST_SCENARIOS_BPS == (30, 50, 80)
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_PRIMARY_COST_BPS == 50
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_TRIALS == 500
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_RANDOM_BASELINE_SEED == 42
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_LEFT_TAIL_PERCENTILE == 5
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_EVENT_COOLDOWN_HOURS == 24
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_MAX_SINGLE_SYMBOL_EVENT_SHARE == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES == (
        "exchange_delisting_notice",
        "futures_contract_launch",
    )
    assert base.EXTERNAL_SIGNAL_STAGE1_5C_FILTER_GROUPS == (
        "G1_source_event_after_first_hour_delay",
        "G2_price_coverage_only",
        "G3_price_coverage_plus_liquidity_proxy",
    )
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_config.py -q
```

Expected: fail because constants do not exist.

**Step 3: Add constants to `configs/base.py`**

Append exactly the constants listed in Section 3.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_config.py -q
```

Expected: pass.

---

## Task 2: Add Models

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_models.py`

**Step 1: Write failing model tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
    ExternalCatalystReplayCellDecision,
    ExternalCatalystReplayResult,
    ExternalCatalystReplayTopLevelDecision,
)


def test_replay_candidate_safety_defaults():
    candidate = ExternalCatalystReplayCandidate(
        symbol_event_id="s1",
        event_type="exchange_delisting_notice",
        signed_mode="delisting_avoid_long_or_signed_short_diagnostic",
        signed_direction=-1,
        symbol="ABCUSDT",
        event_time_ms=1710000000000,
        available_at_ms=1710000900000,
        entry_delay_hours=1,
        entry_candidate_time_ms=1710004500000,
        entry_bar_start_ms=1710004500000,
        entry_price=1.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    assert candidate.replay_allowed is True
    assert candidate.paper_trading_allowed is False
    assert candidate.live_trading_allowed is False
    assert candidate.short_execution_intent_allowed is False
    assert candidate.execution_engine_allowed is False


def test_replay_result_cost_fields():
    result = ExternalCatalystReplayResult(
        symbol_event_id="s1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="ABCUSDT",
        entry_delay_hours=1,
        forward_window_hours=4,
        cost_bps=50,
        entry_price=100.0,
        exit_price=101.0,
        long_gross_return_bps=100.0,
        signed_gross_return_bps=100.0,
        net_return_bps=50.0,
        forward_window_complete=True,
    )
    assert result.net_return_bps == 50.0


def test_decision_enum_values():
    assert ExternalCatalystReplayTopLevelDecision.COMPLETED.value == "stage1_5c_replay_completed"
    assert ExternalCatalystReplayTopLevelDecision.INVALID.value == "stage1_5c_replay_invalid"
    assert ExternalCatalystReplayCellDecision.PROMISING.value == "stage1_5c_cell_promising"
    assert ExternalCatalystReplayCellDecision.SPARSE.value == "stage1_5c_cell_sparse_inconclusive"
    assert ExternalCatalystReplayCellDecision.FAILED.value == "stage1_5c_cell_failed"
    assert ExternalCatalystReplayCellDecision.INVALID.value == "stage1_5c_cell_invalid"
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_models.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement dataclasses and enum**

Use `@dataclass` and `Enum`. Keep safety defaults false.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_models.py -q
```

Expected: pass.

---

## Task 3: Add Loaders and Stage 1.5B Gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_loader.py`

**Step 1: Write failing loader tests**

```python
import json

import pytest

from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_loader import (
    assert_stage1_5b_ready,
    load_stage1_5b_symbol_events,
    load_price_bars,
)


def test_assert_stage1_5b_ready_rejects_non_ready_summary(tmp_path):
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({
        "decision": "stage1_5b_event_table_failed",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    with pytest.raises(ValueError, match="stage1_5b_event_table_ready"):
        assert_stage1_5b_ready(path)


def test_load_stage1_5b_symbol_events_requires_1_5c_pending_not_candidate_allowed(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 1710000000000,
        "available_at_ms": 1710000900000,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "directional_hypothesis": "undefined",
        "signed_direction": None,
    }) + "\n")
    rows = load_stage1_5b_symbol_events(path)
    assert len(rows) == 1
    assert rows[0]["stage1_5b_replay_candidate_allowed_upstream"] is False


def test_load_stage1_5b_symbol_events_rejects_replay_allowed_true(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 1710000000000,
        "available_at_ms": 1710000900000,
        "stage1_5c_review_pending": True,
        "price_coverage_gate_passed": True,
        "candidate_allowed_for_close_price_replay": True,
        "replay_allowed": True,
    }) + "\n")
    with pytest.raises(ValueError, match="Stage 1.5B must not pre-allow replay"):
        load_stage1_5b_symbol_events(path)


def test_load_price_bars_normalizes_jsonl(tmp_path):
    path = tmp_path / "price.jsonl"
    path.write_text(json.dumps({
        "symbol": "ABCUSDT",
        "open_time": 1710000000000,
        "open": "100",
        "high": "101",
        "low": "99",
        "close": "100.5",
        "quote_volume": "1234567",
    }) + "\n")
    rows = load_price_bars(path)
    assert rows[0]["symbol"] == "ABCUSDT"
    assert rows[0]["bar_start_ms"] == 1710000000000
    assert rows[0]["bar_end_ms"] == 1710000900000
    assert rows[0]["close"] == 100.5
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_loader.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement loader**

Functions:

```python
def load_jsonl(path: str | Path) -> list[dict]: ...
def assert_stage1_5b_ready(summary_path: str | Path) -> dict: ...
def load_stage1_5b_symbol_events(path: str | Path) -> list[dict]: ...
def load_price_bars(path: str | Path) -> list[dict]: ...
```

Required checks:

```text
Stage 1.5B summary decision == stage1_5b_event_table_ready
Stage 1.5B replay_allowed == false
Stage 1.5B stage1_5c_replay_candidate_allowed == false
Rename upstream field to stage1_5b_replay_candidate_allowed_upstream in loaded rows
Do not pass through stage1_5c_replay_candidate_allowed into Stage 1.5C candidate/quality outputs
Each event row event_type in EXTERNAL_SIGNAL_STAGE1_5C_ALLOWED_EVENT_TYPES
No event row may have replay_allowed/paper/live true from 1.5B
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_loader.py -q
```

Expected: pass.

---

## Task 4: Add Price Coverage and Tradability Proxy Gates

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_quality.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_quality.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_quality import (
    build_price_index,
    compute_price_interval_stats,
    evaluate_event_price_coverage,
)


def _bar(symbol, t, close=100.0, quote_volume=10_000_000):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "quote_volume": quote_volume,
    }


def test_price_interval_stats_accepts_15m_bars():
    bars = [_bar("ABCUSDT", i * 900_000) for i in range(10)]
    stats = compute_price_interval_stats(bars)
    assert stats["median_interval_ms"] == 900_000
    assert stats["p95_interval_ms"] == 900_000
    assert stats["price_interval_supported"] is True


def test_event_price_coverage_rejects_missing_entry_bar():
    price_index = build_price_index([_bar("ABCUSDT", 0)])
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": 0},
        price_index=price_index,
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is False
    assert report["candidate_allowed_for_close_price_replay"] is False
    assert report["coverage_reject_reason"] == "missing_entry_bar"


def test_event_price_coverage_accepts_complete_forward_windows():
    bars = [_bar("ABCUSDT", i * 900_000, close=100 + i) for i in range(0, 30 * 24 * 4 + 30)]
    event_time = 30 * 24 * 4 * 900_000
    price_index = build_price_index(bars)
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": event_time},
        price_index=price_index,
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is True
    assert report["candidate_allowed_for_close_price_replay"] is True
    assert report["market_pair_existence_verified"] is True
    assert report["price_history_coverage_verified"] is True


def test_price_coverage_and_liquidity_proxy_are_reported_separately():
    bars = [_bar("ABCUSDT", i * 900_000, close=100 + i, quote_volume=1_000) for i in range(0, 30 * 24 * 4 + 30)]
    event_time = 30 * 24 * 4 * 900_000
    report = evaluate_event_price_coverage(
        event={"symbol": "ABCUSDT", "available_at_ms": event_time},
        price_index=build_price_index(bars),
        entry_delay_hours=1,
        forward_windows_hours=(1, 4),
    )
    assert report["price_coverage_gate_passed"] is True
    assert report["candidate_allowed_for_close_price_replay"] is True
    assert report["liquidity_proxy_pass"] is False
    assert report["candidate_allowed_for_execution_relevance"] is False
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_quality.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement quality gates**

Functions:

```python
def build_price_index(price_bars: list[dict]) -> dict[str, list[dict]]: ...
def compute_price_interval_stats(symbol_bars: list[dict]) -> dict: ...
def find_first_bar_at_or_after(symbol_bars: list[dict], ts_ms: int) -> dict | None: ...
def evaluate_event_price_coverage(event: dict, price_index: dict, entry_delay_hours: int, forward_windows_hours: tuple[int, ...]) -> dict: ...
```

Do not use event bar close. Entry and exit are first bars at or after target times.
Do not emit `stage1_5c_replay_candidate_allowed` from this module.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_quality.py -q
```

Expected: pass.

---

## Task 5: Add Event Direction and Candidate Builder

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_candidates.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_candidates.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_candidates import (
    allowed_filter_groups,
    apply_event_cooldown,
    build_replay_candidates,
    event_direction_modes,
)


def test_event_direction_modes_are_frozen():
    assert event_direction_modes("exchange_delisting_notice") == [
        ("delisting_avoid_long_or_signed_short_diagnostic", -1)
    ]
    assert event_direction_modes("futures_contract_launch") == [
        ("futures_launch_long_attention_diagnostic", 1),
        ("futures_launch_short_access_diagnostic", -1),
    ]


def test_filter_group_semantics_make_first_hour_delay_mandatory():
    # There is no no-delay Group 0 in Stage 1.5C v1.
    assert "G1_source_event_after_first_hour_delay" in allowed_filter_groups()
    assert "G0_event_only" not in allowed_filter_groups()


def test_event_cooldown_keeps_earliest_same_symbol_type_mode():
    events = [
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "m", "event_time_ms": 0},
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "m", "event_time_ms": 1_000},
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_mode": "other", "event_time_ms": 1_000},
    ]
    kept = apply_event_cooldown(events, cooldown_hours=24)
    assert len(kept) == 2
    assert kept[0]["event_time_ms"] == 0


def test_build_replay_candidates_expands_futures_launch_two_modes():
    event = {
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 0,
        "available_at_ms": 0,
    }
    coverage = {
        "price_coverage_gate_passed": True,
        "candidate_allowed_for_close_price_replay": True,
        "entry_candidate_time_ms": 3_600_000,
        "entry_bar_start_ms": 3_600_000,
        "entry_price": 100.0,
        "price_history_coverage_verified": True,
        "market_pair_existence_verified": True,
        "liquidity_proxy_verified": False,
        "close_price_replay_only": True,
        "execution_feasibility_unknown": True,
    }
    candidates = build_replay_candidates([event], {("s1", 1): coverage}, entry_delay_hours=1)
    assert {c.signed_direction for c in candidates} == {1, -1}
    assert all(c.paper_trading_allowed is False for c in candidates)
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_candidates.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement candidate builder**

Important:

```text
Do not choose best futures launch direction after seeing returns.
Each signed mode is evaluated separately.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_candidates.py -q
```

Expected: pass.

---

## Task 6: Add Replay Engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_engine.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_engine.py`

**Step 1: Write failing tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_engine import (
    compute_signed_net_return_bps,
    replay_candidates,
)
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_models import (
    ExternalCatalystReplayCandidate,
)


def test_compute_signed_net_return_long_and_short():
    assert compute_signed_net_return_bps(100.0, 101.0, signed_direction=1, cost_bps=50) == 50.0
    assert compute_signed_net_return_bps(100.0, 101.0, signed_direction=-1, cost_bps=50) == -150.0


def test_replay_candidates_uses_entry_and_exit_open_prices():
    candidate = ExternalCatalystReplayCandidate(
        symbol_event_id="s1",
        event_type="exchange_delisting_notice",
        signed_mode="delisting_avoid_long_or_signed_short_diagnostic",
        signed_direction=-1,
        symbol="ABCUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=100.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    price_index = {"ABCUSDT": [
        {"bar_start_ms": 3_600_000, "open": 100.0},
        {"bar_start_ms": 18_000_000, "open": 95.0},
    ]}
    rows = replay_candidates([candidate], price_index, forward_windows_hours=(4,), cost_scenarios_bps=(50,))
    assert rows[0].long_gross_return_bps == -500.0
    assert rows[0].signed_gross_return_bps == 500.0
    assert rows[0].net_return_bps == 450.0


def test_replay_engine_does_not_cross_symbol_paths():
    abc = ExternalCatalystReplayCandidate(
        symbol_event_id="abc1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="ABCUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=100.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    xyz = ExternalCatalystReplayCandidate(
        symbol_event_id="xyz1",
        event_type="futures_contract_launch",
        signed_mode="futures_launch_long_attention_diagnostic",
        signed_direction=1,
        symbol="XYZUSDT",
        event_time_ms=0,
        available_at_ms=0,
        entry_delay_hours=1,
        entry_candidate_time_ms=3_600_000,
        entry_bar_start_ms=3_600_000,
        entry_price=200.0,
        price_history_coverage_verified=True,
        market_pair_existence_verified=True,
        liquidity_proxy_verified=False,
        close_price_replay_only=True,
        execution_feasibility_unknown=True,
    )
    price_index = {
        "ABCUSDT": [
            {"bar_start_ms": 3_600_000, "open": 100.0},
            {"bar_start_ms": 18_000_000, "open": 110.0},
        ],
        "XYZUSDT": [
            {"bar_start_ms": 3_600_000, "open": 200.0},
            {"bar_start_ms": 18_000_000, "open": 100.0},
        ],
    }
    rows = replay_candidates([abc, xyz], price_index, forward_windows_hours=(4,), cost_scenarios_bps=(50,))
    by_symbol = {r.symbol: r.net_return_bps for r in rows}
    assert by_symbol["ABCUSDT"] == 950.0
    assert by_symbol["XYZUSDT"] == -5050.0
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_engine.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement replay engine**

Functions:

```python
def compute_signed_net_return_bps(entry_price: float, exit_price: float, signed_direction: int, cost_bps: int) -> float: ...
def replay_candidates(candidates, price_index, forward_windows_hours, cost_scenarios_bps) -> list[ExternalCatalystReplayResult]: ...
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_engine.py -q
```

Expected: pass.

---

## Task 7: Add Baselines

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_baseline.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_baseline.py`

**Step 1: Write failing baseline tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_baseline import (
    compute_price_move_baseline_events,
    sample_symbol_hour_event_type_matched_random_baseline,
)


def _bar(symbol, t, open_price, close_price):
    return {
        "symbol": symbol,
        "bar_start_ms": t,
        "bar_end_ms": t + 900_000,
        "open": open_price,
        "close": close_price,
        "quote_volume": 10_000_000,
    }


def test_price_move_baseline_respects_signed_direction():
    price_index = {"ABCUSDT": [
        _bar("ABCUSDT", 0, 100, 100),
        _bar("ABCUSDT", 900_000, 100, 102),
        _bar("ABCUSDT", 1_800_000, 102, 102),
        _bar("ABCUSDT", 2_700_000, 102, 102),
        _bar("ABCUSDT", 3_600_000, 102, 102),
    ]}
    events = compute_price_move_baseline_events(
        price_index=price_index,
        symbol="ABCUSDT",
        signed_direction=1,
        threshold_bps=150,
    )
    assert events


def test_price_move_baseline_excludes_candidate_cooldown_windows():
    price_index = {"ABCUSDT": [_bar("ABCUSDT", i * 900_000, 100, 102 if i == 4 else 100) for i in range(20)]}
    events = compute_price_move_baseline_events(
        price_index=price_index,
        symbol="ABCUSDT",
        signed_direction=1,
        threshold_bps=150,
        excluded_event_times_ms=[0],
        cooldown_hours=24,
    )
    assert events == []


def test_random_baseline_matches_symbol_event_type_direction_distribution():
    candidates = [
        {"symbol": "ABCUSDT", "event_type": "futures_contract_launch", "signed_direction": 1, "entry_delay_hours": 1, "event_time_ms": 0},
        {"symbol": "XYZUSDT", "event_type": "exchange_delisting_notice", "signed_direction": -1, "entry_delay_hours": 1, "event_time_ms": 3_600_000},
    ]
    price_index = {
        "ABCUSDT": [_bar("ABCUSDT", i * 900_000, 100, 100) for i in range(100)],
        "XYZUSDT": [_bar("XYZUSDT", i * 900_000, 100, 100) for i in range(100)],
    }
    trials = sample_symbol_hour_event_type_matched_random_baseline(
        candidates=candidates,
        price_index=price_index,
        trials=5,
        random_seed=42,
    )
    assert len(trials) == 5
    assert all(len(trial) == 2 for trial in trials)
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_baseline.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement baselines**

Minimum functions:

```python
def compute_price_move_baseline_events(...): ...
def sample_symbol_hour_event_type_matched_random_baseline(...): ...
def compute_baseline_summary(...): ...
```

Baseline summary must output:

```json
{
  "random_baseline_trials": 500,
  "baseline_sampling_failure_count": 0,
  "baseline_sampling_insufficient": false,
  "random_baseline_median_net_bps_after_50bps_4h": 0.0,
  "price_baseline_median_net_bps_after_50bps_4h": 0.0,
  "event_type_matched_baseline_median_net_bps_after_50bps_4h": 0.0,
  "random_baseline_left_tail_p05_after_50bps_4h": 0.0
}
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_baseline.py -q
```

Expected: pass.

---

## Task 8: Add Metrics and Summary Decision Engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_summary.py`

**Step 1: Write failing summary tests**

```python
from src.research.external_signal_shadow.stage1_5c_external_catalyst_replay_summary import (
    compute_concentration_metrics,
    decide_stage1_5c_replay_summary,
)


def test_concentration_uses_primary_forward_and_primary_cost_only():
    rows = [
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 4, "cost_bps": 50, "net_return_bps": 100},
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 12, "cost_bps": 50, "net_return_bps": 80},
        {"candidate_event_unit_id": "a", "symbol": "ABCUSDT", "event_time_ms": 0, "forward_window_hours": 4, "cost_bps": 80, "net_return_bps": 70},
        {"candidate_event_unit_id": "b", "symbol": "XYZUSDT", "event_time_ms": 86_400_000, "forward_window_hours": 4, "cost_bps": 50, "net_return_bps": -10},
    ]
    m = compute_concentration_metrics(rows, primary_forward_window_hours=4, primary_cost_bps=50)
    assert m["event_count"] == 2
    assert m["max_single_symbol_event_share"] == 0.5


def test_futures_launch_signed_modes_have_separate_density_gates():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "futures_launch_density": {
            "raw_symbol_event_count": 40,
            "signed_mode_count": {
                "futures_launch_long_attention_diagnostic": 40,
                "futures_launch_short_access_diagnostic": 40,
            },
            "do_not_sum_signed_modes_for_density_gate": True,
        },
        "cell_summaries": {
            "futures_contract_launch|long|1h|G2_price_coverage_only": {"cell_event_count": 40},
            "futures_contract_launch|short|1h|G2_price_coverage_only": {"cell_event_count": 40},
        },
    })
    assert summary["futures_launch_density"]["do_not_sum_signed_modes_for_density_gate"] is True


def test_no_mixed_event_type_top_level_pass_claim():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "mixed_event_type_aggregate_only": True,
        "cell_summaries": {},
    })
    assert summary["top_level_decision"] == "stage1_5c_replay_completed"
    assert summary["promising_cells"] == []
    assert "no_cell_level_promising_result" in summary["blockers"]


def test_summary_outputs_coverage_attrition_funnel():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "coverage_attrition_funnel": {
            "stage1_5b_symbol_events": 194,
            "allowed_event_type_events": 194,
            "market_pair_existence_verified_count": 50,
            "price_history_coverage_pass_count": 40,
            "liquidity_proxy_pass_count": 20,
            "candidate_count_after_cooldown": 18,
            "replay_result_primary_rows": 18,
            "coverage_reject_reason_counts": {"missing_entry_bar": 3},
        },
        "cell_summaries": {},
    })
    funnel = summary["coverage_attrition_funnel"]
    assert funnel["stage1_5b_symbol_events"] == 194
    assert funnel["price_history_coverage_pass_count"] == 40
    assert funnel["coverage_reject_reason_counts"]["missing_entry_bar"] == 3


def test_concentration_metrics_uses_events_not_windows():
    rows = [
        {"symbol": "ABCUSDT", "event_time_ms": 0, "net_return_bps": 100, "signed_mode": "m"},
        {"symbol": "ABCUSDT", "event_time_ms": 0, "net_return_bps": 80, "signed_mode": "m"},
        {"symbol": "XYZUSDT", "event_time_ms": 86_400_000, "net_return_bps": -10, "signed_mode": "m"},
    ]
    m = compute_concentration_metrics(rows)
    assert m["max_single_symbol_event_share"] == 2 / 3
    assert m["max_single_day_event_share"] == 2 / 3


def test_decision_promising_requires_baseline_and_concentration_pass():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "event_count": 40,
        "event_days": 12,
        "symbols_with_events": 4,
        "primary_event_type_events": 30,
        "median_net_return_after_50bps_4h": 10.0,
        "baseline_excess_net_bps_4h": 5.0,
        "price_baseline_excess_net_bps_4h": 4.0,
        "left_tail_p05_after_50bps_4h": -20.0,
        "random_baseline_left_tail_p05_after_50bps_4h": -25.0,
        "top_5_positive_events_gross_profit_share": 0.20,
        "max_single_day_event_share": 0.20,
        "max_single_symbol_event_share": 0.30,
        "baseline_sampling_insufficient": False,
    })
    assert summary["cell_decision"] == "stage1_5c_cell_promising"
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False


def test_decision_failed_when_cost_after_median_negative():
    summary = decide_stage1_5c_replay_summary({
        "fixture_run": False,
        "research_result_valid": True,
        "event_count": 40,
        "event_days": 12,
        "symbols_with_events": 4,
        "primary_event_type_events": 30,
        "median_net_return_after_50bps_4h": -1.0,
        "baseline_excess_net_bps_4h": 5.0,
        "price_baseline_excess_net_bps_4h": 4.0,
        "left_tail_p05_after_50bps_4h": -20.0,
        "random_baseline_left_tail_p05_after_50bps_4h": -25.0,
        "top_5_positive_events_gross_profit_share": 0.20,
        "max_single_day_event_share": 0.20,
        "max_single_symbol_event_share": 0.30,
        "baseline_sampling_insufficient": False,
    })
    assert summary["cell_decision"] == "stage1_5c_cell_failed"
    assert "median_net_return_after_50bps_not_positive" in summary["blockers"]
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_summary.py -q
```

Expected: fail because module does not exist.

**Step 3: Implement summary engine**

Cell decision gates, evaluated separately for each `event_type + signed_mode + entry_delay_hours + filter_group` cell:

```text
research_result_valid == true
fixture_run == false
random_baseline_trials >= 500
baseline_sampling_insufficient == false
cell_event_count >= 30
cell_event_days >= 10
cell_symbols_with_events >= 3
no_mixed_event_type_pass_claim == true
median_net_return_after_50bps_4h > 0
baseline_excess_net_bps_4h > 0
price_baseline_excess_net_bps_4h > 0
left_tail_p05_after_50bps_4h >= random_baseline_left_tail_p05_after_50bps_4h
top_5_positive_events_gross_profit_share <= 0.40
max_single_day_event_share <= 0.30
max_single_symbol_event_share <= 0.50
```

`event_count`, `event_days`, concentration, and top-5 profit share must use the primary metric unit only:

```text
candidate_event_unit = unique(symbol_event_id, signed_mode, entry_delay_hours, filter_group)
primary_metric_unit = candidate_event_unit at primary_forward_window=4h and primary_cost=50bps
```

Do not multiply density by forward windows, cost scenarios, or futures launch long/short mode aggregation. Futures launch long and short diagnostic modes have separate density gates and must not be summed for pass.

Always output safety fields false.

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_summary.py -q
```

Expected: pass.

---

## Task 9: Add Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_5c_external_catalyst_replay.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py`

**Step 1: Write failing runner tests**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.run_stage1_5c_external_catalyst_replay import main


def test_runner_debug_override_marks_research_invalid(tmp_path):
    event_path = tmp_path / "events.jsonl"
    stage1_5b_summary = tmp_path / "stage1_5b_summary.json"
    price_path = tmp_path / "price.jsonl"
    candidates_out = tmp_path / "candidates.jsonl"
    results_out = tmp_path / "results.jsonl"
    summary_out = tmp_path / "summary.json"

    stage1_5b_summary.write_text(json.dumps({
        "decision": "stage1_5b_event_table_ready",
        "replay_allowed": False,
        "stage1_5c_replay_candidate_allowed": False,
    }))
    event_path.write_text(json.dumps({
        "symbol_event_id": "s1",
        "event_type": "futures_contract_launch",
        "symbol": "ABCUSDT",
        "event_time_ms": 30 * 24 * 3600 * 1000,
        "available_at_ms": 30 * 24 * 3600 * 1000,
        "stage1_5c_review_pending": True,
        "stage1_5c_replay_candidate_allowed": False,
        "replay_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "directional_hypothesis": "undefined",
        "signed_direction": None,
    }) + "\n")
    bars = []
    for i in range(30 * 24 * 4 + 120):
        bars.append({
            "symbol": "ABCUSDT",
            "bar_start_ms": i * 900_000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "quote_volume": 100_000_000,
        })
    price_path.write_text("\n".join(json.dumps(b) for b in bars) + "\n")

    args = [
        "run_stage1_5c_external_catalyst_replay.py",
        "--events-jsonl", str(event_path),
        "--stage1-5b-summary", str(stage1_5b_summary),
        "--price-jsonl", str(price_path),
        "--output-candidates-jsonl", str(candidates_out),
        "--output-results-jsonl", str(results_out),
        "--output-summary", str(summary_out),
        "--random-baseline-trials", "10",
    ]
    with patch("sys.argv", args):
        main()

    summary = json.loads(summary_out.read_text())
    assert summary["baseline_trials_override_used"] is True
    assert summary["research_result_valid"] is False
    assert summary["top_level_decision"] == "stage1_5c_replay_completed"
    assert summary["promising_cells"] == []
    assert summary["paper_trading_allowed"] is False
    assert summary["live_trading_allowed"] is False
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement runner**

CLI:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c_external_catalyst_replay.py \
  --events-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --price-jsonl data/external_signal_shadow/derivatives_stress/price/binance_um_futures_15m_180d.jsonl \
  --output-candidates-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl \
  --output-results-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

Runner sequence:

```text
assert Stage 1.5B ready
load Stage 1.5B symbol events
load price bars
build price index
for each entry_delay: evaluate coverage
build replay candidates
apply cooldown
replay forward windows and costs
compute baselines
compute coverage attrition funnel
compute per cell summaries: event_type + signed_mode + entry_delay_hours + filter_group
compute top-level aggregate status without mixed pass claim
write JSONL/JSON outputs
```

Summary must include coverage attrition funnel:

```json
{
  "stage1_5b_symbol_events": 194,
  "allowed_event_type_events": 194,
  "market_pair_existence_verified_count": 0,
  "price_history_coverage_pass_count": 0,
  "liquidity_proxy_pass_count": 0,
  "candidate_count_after_cooldown": 0,
  "replay_result_primary_rows": 0,
  "coverage_reject_reason_counts": {}
}
```

If `--random-baseline-trials` is provided and below config default, mark:

```text
baseline_trials_override_used = true
research_result_valid = false
top_level_decision = stage1_5c_replay_completed
promising_cells = []
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py -q
```

Expected: pass.

---

## Task 10: Add Review Generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_5c_external_catalyst_replay.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_5c_external_catalyst_replay.py`

**Step 1: Write failing review tests**

```python
import json
from unittest.mock import patch

from scripts.external_signal_shadow.review_stage1_5c_external_catalyst_replay import main


def test_review_states_research_only_and_no_alpha(tmp_path):
    summary = tmp_path / "summary.json"
    review = tmp_path / "review.md"
    summary.write_text(json.dumps({
        "top_level_decision": "stage1_5c_replay_completed",
        "research_result_valid": True,
        "promising_cells": [],
        "cell_summaries": {
            "futures_contract_launch|long_attention|1h|G2_price_coverage_only": {
                "cell_decision": "stage1_5c_cell_failed",
                "cell_event_count": 40,
                "cell_event_days": 12,
                "cell_symbols_with_events": 4,
                "median_net_return_after_50bps_4h": -5.0,
                "blockers": ["median_net_return_after_50bps_not_positive"]
            }
        },
        "random_baseline_trials": 500,
        "blockers": ["median_net_return_after_50bps_not_positive"],
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "alpha_interpretation_allowed": False,
        "execution_engine_allowed": False,
    }))
    args = [
        "review_stage1_5c_external_catalyst_replay.py",
        "--summary", str(summary),
        "--output-review", str(review),
    ]
    with patch("sys.argv", args):
        main()
    content = review.read_text()
    assert "Stage 1.5C" in content
    assert "research-only" in content
    assert "paper_trading_allowed" in content
    assert "live_trading_allowed" in content
    assert "alpha_interpretation_allowed" in content
    assert "median_net_return_after_50bps_not_positive" in content
    assert "-5.0" in content or "-5" in content
    for placeholder in ["TODO", "TBD", "placeholder", "FIXME"]:
        assert placeholder not in content
```

**Step 2: Run red test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5c_external_catalyst_replay.py -q
```

Expected: fail because script does not exist.

**Step 3: Implement review generator**

Review sections:

```text
1. 结论
2. Upstream Evidence
3. Price Coverage / Candidate Allowance
4. Coverage Attrition Funnel
5. Cell Replay Results by event_type / signed_mode / entry_delay / filter_group
6. Baseline Comparison
7. Concentration / Left Tail
8. Delisting Notice-Time Anchor Disclosure
9. Safety Boundaries
10. Blockers
11. Allowed Next Action
```

Must explicitly state:

```text
Stage 1.5C promising does not permit paper/live.
Stage 1.5C failed does not invalidate external catalyst source audit.
Signed short replay is diagnostic only.
No execution feasibility was proven without orderbook/depth.
Delisting replay uses notice_time_available_at; effective_time replay is not implemented.
A promising cell only allows live event-source smoke collector design, not execution/shadow readiness.
```

**Step 4: Run green test**

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_5c_external_catalyst_replay.py -q
```

Expected: pass.

---

## Task 11: End-to-End Real Smoke

**Step 1: Run replay with 500 trials**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_5c_external_catalyst_replay.py \
  --events-jsonl data/external_signal_shadow/stage1_5b/external_catalyst_events_normalized.jsonl \
  --stage1-5b-summary data/external_signal_shadow/stage1_5b/normalization_summary.json \
  --price-jsonl data/external_signal_shadow/derivatives_stress/price/binance_um_futures_15m_180d.jsonl \
  --output-candidates-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl \
  --output-results-jsonl data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl \
  --output-summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

Expected output constraints:

```text
research_result_valid = true
random_baseline_trials = 500
baseline_trials_override_used = false
top_level_decision in {stage1_5c_replay_completed, stage1_5c_replay_invalid}
promising_cells is present
cell_summaries is present
coverage_attrition_funnel is present
paper_trading_allowed = false
live_trading_allowed = false
execution_engine_allowed = false
alpha_interpretation_allowed = false
```

**Step 2: Generate review**

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_5c_external_catalyst_replay.py \
  --summary data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json \
  --output-review docs/reviews/2026-06-23-external-signal-shadow-lab-stage1-5c-external-catalyst-replay-review_CN.md
```

**Step 3: Inspect summary**

```bash
python3 - <<'PY'
import json
with open('data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json', encoding='utf-8') as f:
    s = json.load(f)
print(json.dumps({
    'top_level_decision': s.get('top_level_decision'),
    'promising_cells': s.get('promising_cells'),
    'research_result_valid': s.get('research_result_valid'),
    'coverage_attrition_funnel': s.get('coverage_attrition_funnel'),
    'event_days': s.get('event_days'),
    'symbols_with_events': s.get('symbols_with_events'),
    'median_net_return_after_50bps_4h': s.get('median_net_return_after_50bps_4h'),
    'baseline_excess_net_bps_4h': s.get('baseline_excess_net_bps_4h'),
    'price_baseline_excess_net_bps_4h': s.get('price_baseline_excess_net_bps_4h'),
    'blockers': s.get('blockers'),
    'paper_trading_allowed': s.get('paper_trading_allowed'),
    'live_trading_allowed': s.get('live_trading_allowed'),
}, ensure_ascii=False, indent=2))
PY
```

---

## 5. Verification Commands

Run all Stage 1.5C tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_config.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_models.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_loader.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_quality.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_candidates.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_engine.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_baseline.py \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5c_external_catalyst_replay.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5c_external_catalyst_replay.py \
  -q
```

Run Stage 1.5B handoff tests:

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_config.py \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_models.py \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_loader.py \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_normalizer.py \
  tests/research/external_signal_shadow/test_stage1_5b_event_table_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_5b_minimal_historical_event_table.py \
  tests/scripts/external_signal_shadow/test_review_stage1_5b_minimal_historical_event_table.py \
  -q
```

Run ruff:

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_5c_external_catalyst_replay_*.py \
  scripts/external_signal_shadow/*stage1_5c* \
  tests/research/external_signal_shadow/test_stage1_5c_external_catalyst_replay_*.py \
  tests/scripts/external_signal_shadow/*stage1_5c*
```

---

## 6. Non-Goals / Guardrails

Do not add:

```text
paper trading
live trading
execution engine wiring
TradeIntent
position sizing
orderbook execution claim without depth archive
funding/OI/liquidation context hard filters
post-hoc best group selection
mixed event-type pass claim
no-delay Group 0 replay
asset_quality_pass hard filter in v1
```


If event type results diverge:

```text
Report per event_type and signed_mode.
Do not combine delisting and futures launch to claim pass.
Do not choose the best futures launch direction after seeing returns.
```

If price coverage is poor:

```text
decision = stage1_5c_replay_invalid or sparse_inconclusive
next_action = extend_price_history_or_reduce_scope
```

---

## 7. Git / Artifact Hygiene

Before real smoke and before commit, this is a hard gate:

```bash
git check-ignore -v data/external_signal_shadow/stage1_5c/external_catalyst_replay_candidates.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c/external_catalyst_replay_results.jsonl
git check-ignore -v data/external_signal_shadow/stage1_5c/external_catalyst_replay_summary.json
```

If any path is not ignored, update `.gitignore` before running real smoke. Do not bypass with `|| true`.

Policy:

```text
data/external_signal_shadow/stage1_5c/*.jsonl should not be committed by default
docs/reviews/** can be committed as decision artifacts
summary JSON can be committed only if the project accepts Stage 1.5 summary JSON artifacts; otherwise commit review only
```

Do not commit automatically. End implementation with:

```bash
git status --short
```

and list changed files for user review.

---

## 8. Expected Final Status

After implementation and real smoke, top-level expected output is:

```text
stage1_5c_replay_completed
stage1_5c_replay_invalid
```

Cell-level output is one of:

```text
stage1_5c_cell_promising
stage1_5c_cell_sparse_inconclusive
stage1_5c_cell_failed
stage1_5c_cell_invalid
```

Allowed next actions:

```text
at least one promising cell -> write_stage1_5d_live_event_source_smoke_collector_design; if considering shadow, first write execution_feasibility_data_audit_plan
only sparse cells -> add more high-confidence sources/events or extend price coverage
all failed cells -> stop Binance-only external catalyst replay branch or add OKX source audit before retry
invalid -> fix data coverage / symbol mapping / price archive before replay
```

Always forbidden:

```text
paper/live approval
alpha confirmed claim
execution-ready claim
short execution intent
```
