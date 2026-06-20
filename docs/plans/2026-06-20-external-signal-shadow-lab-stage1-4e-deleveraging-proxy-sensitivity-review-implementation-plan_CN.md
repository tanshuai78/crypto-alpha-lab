# External Signal Shadow Lab Stage 1.4E Deleveraging Proxy Sensitivity Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` or `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 实现 `Stage 1.4E Deleveraging Proxy Sensitivity Review` 管线，用固定的 `OI drop + price flush` 两组预注册参数，判断该代理信号是否值得进入 external catalyst filter。

**Architecture:** 新增独立 `stage1_4e_deleveraging_proxy_*` 模块，保持和 `Stage 1.4B-Lite` 语义隔离；允许复用 B-Lite 的 signed replay / random baseline 思路，但 proxy 事件、source quality、decision summary 独立实现。所有阈值进入 `configs/base.py`，runner 只输出 JSON summary，review 脚本只解释边界，不产生 alpha / paper / live 结论。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、现有 `stage1_4b_lite_*` replay/baseline patterns、pytest、ruff、JSON/JSONL。

---

## 0.1 审核状态

```text
decision = approved_with_required_fixes
scope = deleveraging_proxy_sensitivity_review_only
force_order_used = false
vendor_data_used = false
liquidation_claim_allowed = false
full_composite_claim_allowed = false
paper_trading_allowed = false
live_trading_allowed = false
```

进入 coding 前必须已经吸收以下修正：

1. dedicated models test file
2. symbol-specific candidate window support
3. price interval support gate
4. exact 1h aggregation rules
5. random baseline matches event_label / signed_direction distribution
6. debug baseline override forces `research_result_valid = false`
7. configured OI / price staleness thresholds
8. review states 1.4E survives only permits Stage 1.5 filter usage, not primary signal

---

## 0. 执行前边界

本计划只实现：

```text
deleveraging_proxy_sensitivity_review_only
```

禁止实现：

```text
forceOrder trigger
vendor liquidation input
liquidation truth claim
full composite replay
paper/live enablement
post-hoc threshold tuning
third candidate parameter group
```

Summary 顶层必须固定写出：

```json
{
  "deleveraging_proxy_only": true,
  "liquidation_used": false,
  "force_order_used": false,
  "vendor_data_used": false,
  "liquidation_claim_allowed": false,
  "full_composite_claim_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "not_b_lite_restart": true,
  "previous_b_lite_crowding_only_branch_stopped": true,
  "stage1_5_allowed_only_as_filter": true
}
```

执行规则：

- 所有测试命令统一使用 `PYTHONPATH=src:.`。
- 本计划不包含任何自动 `git commit`。每个任务结束后最多执行 `git status --short`，由用户决定是否提交。
- 实现前先写测试；不要为了跑出好结果改阈值。

---

## 1. 文件结构

### 新增文件

- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_models.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_loader.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_quality.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_signals.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_replay.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_baseline.py`
- `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_summary.py`
- `scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py`
- `scripts/external_signal_shadow/review_stage1_4e_deleveraging_proxy_sensitivity_review.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_config.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_models.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_loader.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_quality.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_signals.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_replay.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_baseline.py`
- `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_summary.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_4e_deleveraging_proxy_sensitivity_review.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_4e_deleveraging_proxy_sensitivity_review.py`

### 修改文件

- `configs/base.py`

### 设计原则

- 不修改 B-Lite 候选定义来“顺手复用”。1.4E 是新阶段，不是 B-Lite restart。
- `sumOpenInterest` 是 trigger 主字段；`sumOpenInterestValue` 只能用于 diagnostic。
- candidate 先过 OI interval support gate，再允许 replay。
- `deleveraging_proxy_inconclusive + secondary_status=inconclusive_promising_sparse` 不能升级成 pass。

---

## 2. Task 1: 配置常量

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_config.py`

### Step 1: 写失败测试

覆盖所有硬阈值：

```python
from configs import base


def test_stage1_4e_deleveraging_proxy_config_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_PRICE_RETURN_THRESHOLD == 0.02
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_OI_DROP_THRESHOLD == -0.03
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_PRICE_RETURN_THRESHOLD == 0.03
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_OI_DROP_THRESHOLD == -0.05

    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_CONFIGURED_DATA_LAG_MS == 300_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_COOLDOWN_MS == 3_600_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_COOLDOWN_MS == 14_400_000

    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_OI_MEDIAN_INTERVAL_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_OI_P95_INTERVAL_MS == 30 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_OI_MEDIAN_INTERVAL_MS == 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_OI_P95_INTERVAL_MS == 2 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_PRICE_MEDIAN_INTERVAL_MS == 15 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_15M_MAX_PRICE_P95_INTERVAL_MS == 30 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_PRICE_MEDIAN_INTERVAL_MS <= 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_1H_MAX_PRICE_P95_INTERVAL_MS <= 2 * 60 * 60 * 1000
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_OI_STALENESS_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MAX_PRICE_STALENESS_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_RESEARCH_RESULT_HISTORY_DAYS >= 30

    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_FORWARD_WINDOWS_HOURS == (1, 4, 12)
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_COST_SCENARIOS_BPS == (30, 50, 80)
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_PRIMARY_COST_BPS == 50
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_RANDOM_BASELINE_TRIALS >= 500
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_LEFT_TAIL_PERCENTILE == 5

    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_PASS_EVENT_COUNT == 100
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_PASS_EVENT_DAYS == 20
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_SPARSE_EVENT_COUNT == 30
    assert base.EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_MIN_SPARSE_EVENT_DAYS == 10
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_config.py -q
```

### Step 3: 实现配置

在 `configs/base.py` 增加 `EXTERNAL_SIGNAL_STAGE1_4E_DELEVERAGING_PROXY_...` 常量。

### Step 4: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_config.py -q
git status --short
```

---

## 3. Task 2: 模型与枚举

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_models.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_models.py`

### Step 1: 写模型测试

覆盖：

- candidate names: `deleveraging_proxy_15m`, `deleveraging_proxy_1h`
- event labels: `down_flush_deleveraging_proxy`, `up_squeeze_deleveraging_proxy`
- decisions: `deleveraging_proxy_failed`, `deleveraging_proxy_inconclusive`, `deleveraging_proxy_survives_sensitivity_review`
- secondary status: `none`, `inconclusive_promising_sparse`
- source quality enums:
  - `binance_vision_metrics`
  - `exchange_reported_hourly_snapshot`
  - `binance_kline_normalized`
  - `close_price_proxy_not_fill_price`

测试名至少包括：

```text
test_models_define_candidate_and_decision_enums
test_models_define_source_quality_semantics
```

### Step 2: 实现 dataclass / typed dict

建议结构：

```python
@dataclass(frozen=True)
class ProxyEvent:
    symbol: str
    candidate_name: str
    event_label: str
    signed_direction: int
    bucket_start_ms: int
    bucket_end_ms: int
    event_time_ms: int
    event_available_at_ms: int
    entry_bar_start_ms: int | None
    price_return: float
    oi_change: float
    oi_start: float
    oi_end: float
    source: str
    source_quality: str
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_models.py -q
```

---

## 4. Task 3: JSON / JSONL loader 与 schema normalization

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_loader.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_loader.py`

### Step 1: 写失败测试

必须覆盖：

- `.json` list root
- `.jsonl` one object per line
- glob path
- OI fields:
  - `timestamp` / `timestamp_ms`
  - `sumOpenInterest`
  - `sumOpenInterestValue`
- price fields:
  - `bar_start_ms` / `open_time` / `timestamp`
  - `open/high/low/close`
  - `quote_volume` optional
- funding context fields:
  - `fundingTime`
  - `fundingRate`
- source semantics fields:
  - `source`
  - `source_quality`

测试名至少包括：

```text
test_loader_supports_json_and_jsonl_inputs
test_loader_normalizes_oi_timestamp_and_sum_open_interest
test_loader_preserves_sum_open_interest_value_for_diagnostic_only
test_loader_normalizes_price_open_high_low_close
test_loader_outputs_source_and_source_quality_fields
```

### Step 2: 实现 loader

实现函数：

```python
load_json_or_jsonl_paths(paths_or_globs: Sequence[str]) -> list[dict]
normalize_oi_rows(rows: Iterable[dict]) -> list[dict]
normalize_price_rows(rows: Iterable[dict]) -> list[dict]
normalize_funding_rows(rows: Iterable[dict]) -> list[dict]
```

输出字段统一为：

```text
OI: symbol, timestamp_ms, sumOpenInterest, sumOpenInterestValue, source, source_file
Price: symbol, bar_start_ms, open, high, low, close, quote_volume
Funding: symbol, funding_time_ms, funding_rate
```

同时必须输出数据源语义：

```json
{
  "oi_source": "binance_vision_metrics",
  "oi_source_quality": "exchange_reported_hourly_snapshot",
  "price_source": "binance_kline_normalized",
  "price_source_quality": "close_price_proxy_not_fill_price",
  "funding_source": "binance_settled_funding_rate",
  "funding_source_quality": "settled_rate_not_realtime_prediction"
}
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_loader.py -q
```

---

## 5. Task 4: Source quality、OI / price interval support gate

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_quality.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_quality.py`

### Step 1: 写失败测试

必须覆盖设计中列出的 review 测试：

```text
test_15m_candidate_rejected_when_oi_interval_too_sparse
test_1h_candidate_supported_when_oi_interval_within_limit
test_candidate_window_supported_is_symbol_specific
test_price_interval_gate_rejects_15m_candidate_when_price_bars_are_hourly
test_1h_candidate_requires_complete_1h_price_bucket_or_native_1h_bar
```

再覆盖 stale 指标：

```text
test_source_quality_reports_stale_oi_and_price_counts
test_source_quality_reports_oi_median_and_p95_interval
test_stale_thresholds_exist_in_config
```

### Step 2: 实现质量统计

实现：

```python
build_oi_interval_stats(oi_rows_by_symbol: dict[str, list[dict]]) -> dict
build_price_interval_stats(price_rows_by_symbol: dict[str, list[dict]]) -> dict
candidate_window_supported_by_symbol(candidate_name: str, oi_interval_stats: dict, price_interval_stats: dict) -> dict
build_source_quality_report(oi_rows: list[dict], price_rows: list[dict], expected_symbols: tuple[str, ...]) -> dict
```

必须输出：

```text
oi_median_interval_ms
oi_p95_interval_ms
price_median_interval_ms
price_p95_interval_ms
candidate_window_supported_by_symbol
candidate_window_supported_overall
unsupported_symbols
stale_oi_bucket_count
stale_price_bucket_count
max_oi_staleness_ms_observed
max_price_gap_ms_observed
oi_data_granularity_minutes
price_data_granularity_minutes
oi_source_quality
price_source_quality
```

`candidate_window_supported_by_symbol` 示例：

```json
{
  "BTCUSDT": true,
  "ETHUSDT": true,
  "SOLUSDT": false
}
```

如果 1h OI 数据被用于 15m candidate，必须降级：

```text
source_quality = hourly_oi_granularity_mismatch_warning
candidate_status = data_unsupported
```

在 Task 4 完成后，开始 Task 5 前，必须用真实 OI 数据跑一次 `build_oi_interval_stats`，确认 15m / 1h candidate 的实际 support 状态。

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_quality.py -q
```

---

## 6. Task 5: Proxy event detection

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_signals.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_signals.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_uses_sum_open_interest_not_sum_open_interest_value_for_trigger
test_down_flush_proxy_signed_long
test_up_squeeze_proxy_signed_short_but_no_short_execution_intent
test_configured_data_lag_applied_to_available_at
test_event_cooldown_deduplicates_cluster
```

具体断言：

- Down flush: `price_return <= -threshold` 且 `oi_change <= negative threshold` 生成 `signed_direction = +1`
- Up squeeze: `price_return >= +threshold` 且 `oi_change <= negative threshold` 生成 `signed_direction = -1`
- `event_available_at_ms = bucket_end_ms + configured_data_lag_ms`
- cooldown key 为 `symbol + candidate_name + event_label + signed_direction`
- OI trigger 使用 `sumOpenInterest`，即使 `sumOpenInterestValue` 大幅变化，也不能单独触发事件

### Step 2: 实现 detector

实现：

```python
detect_deleveraging_proxy_events(
    *,
    oi_rows: list[dict],
    price_rows: list[dict],
    candidate_name: str,
    source_quality: dict,
    expected_symbols: tuple[str, ...],
) -> tuple[list[ProxyEvent], dict]
```

如果当前 symbol 的 `candidate_window_supported_by_symbol[symbol] = false`，跳过该 symbol。

如果 candidate overall 不支持，返回：

```text
events = []
candidate_status = data_unsupported
```

1h bucket 规则必须写死：

```text
1h bucket_start_ms = floor(timestamp_ms / 1h) * 1h
1h price_return = close of last complete 15m bar in bucket / open of first complete 15m bar in bucket - 1
1h OI change = OI_asof_bucket_end / OI_asof_bucket_start - 1
```

如果 price 输入是 native 1h bar，必须先通过 `bar_interval_ms` 或相邻 bar 推断确认。  
如果使用 15m 聚合 1h，必须要求 4 根 15m bar 完整，否则该 1h bucket 跳过。

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_signals.py -q
```

---

## 7. Task 6: Signed replay

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_replay.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_replay.py`

### Step 1: 写失败测试

覆盖：

- `signed_direction = +1` 使用 forward return
- `signed_direction = -1` 使用负 forward return
- cost bps 从 signed return 中扣除
- forward windows `1h / 4h / 12h`
- entry bar 不存在时事件标记为 replay skipped
- `test_entry_bar_does_not_use_event_bar_close_to_prevent_lookahead`

Entry bar 定义必须固定：

```text
entry_bar = first 15m futures price bar where bar_start_ms >= event_available_at_ms
event_available_at_ms = bucket_end_ms + configured_data_lag_ms
```

不得使用 event bucket 的 close 作为 entry price。

### Step 2: 实现 replay

可以参考 `stage1_4b_lite_replay.py` 的价格索引和 cache 方式，但新模块命名必须保持 `stage1_4e`。

输出事件级 replay rows：

```text
symbol
candidate_name
event_label
event_time_ms
entry_bar_start_ms
signed_direction
forward_window_hours
gross_return_bps
net_return_bps_after_30bps
net_return_bps_after_50bps
net_return_bps_after_80bps
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_replay.py -q
```

---

## 8. Task 7: Random baseline 与 price baseline

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_baseline.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_baseline.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_price_baseline_uses_same_direction_and_cooldown
test_left_tail_uses_p05
```

再覆盖：

- symbol/hour matched random baseline event count 与 candidate 一致
- random baseline 匹配 candidate_name distribution
- random baseline 匹配 event_label / signed_direction distribution
- random baseline 排除 candidate timestamps
- baseline sampling failure count 可见
- price baseline 使用同 symbol universe、同 event window、同 cost、同 forward windows

### Step 2: 实现 baseline

实现：

```python
compute_symbol_hour_matched_random_baseline(...)
compute_price_move_baseline(...)
compute_left_tail(values: list[float], percentile: int = 5) -> float
```

Random baseline 每个 trial 必须匹配：

```text
event_count
symbol distribution
hour-of-day distribution
candidate_name distribution
event_label / signed_direction distribution
```

Price baseline 方向：

```text
down flush baseline:
  price_return <= same negative threshold
  signed_direction = +1

up squeeze baseline:
  price_return >= same positive threshold
  signed_direction = -1
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_baseline.py -q
```

---

## 9. Task 8: Summary decision engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_summary.py`

### Step 1: 写失败测试

必须覆盖：

```text
test_sparse_positive_result_is_inconclusive_not_pass
test_failed_result_does_not_invalidate_real_liquidation_or_external_catalyst
```

再覆盖：

- pass gates 全满足才输出 `deleveraging_proxy_survives_sensitivity_review`
- `event_count 30-99` 且表现良好输出 `deleveraging_proxy_inconclusive + inconclusive_promising_sparse`
- data unsupported 输出 `deleveraging_proxy_inconclusive`
- performance weak 输出 `deleveraging_proxy_failed`
- summary 顶层所有 safety flags 存在

### Step 2: 实现 summary

实现：

```python
build_candidate_summary(...)
decide_stage1_4e_summary(...)
```

顶层输出必须包含：

```json
{
  "decision": "...",
  "secondary_status": "...",
  "deleveraging_proxy_only": true,
  "liquidation_used": false,
  "force_order_used": false,
  "vendor_data_used": false,
  "liquidation_claim_allowed": false,
  "full_composite_claim_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false,
  "not_b_lite_restart": true,
  "stage1_5_allowed_only_as_filter": true
}
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_summary.py -q
```

---

## 10. Task 9: Runner CLI

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4e_deleveraging_proxy_sensitivity_review.py`

### Step 1: 写失败测试

覆盖：

- runner 接收 `--oi-archive`
- runner 接收 `--price-archive`
- runner 可选接收 `--funding-archive`
- runner 支持 `--random-baseline-trials` debug override
- runner 输出 summary JSON
- fixture run 必须可标记 `fixture_run = true`、`research_result_valid = false`
- `test_debug_baseline_override_marks_research_result_invalid`

### Step 2: 实现 CLI

参数建议：

```text
--oi-archive PATH_OR_GLOB
--price-archive PATH_OR_GLOB
--funding-archive PATH_OR_GLOB
--output-summary PATH
--random-baseline-trials INT
--fixture-run
```

真实输入运行时：

```text
fixture_run = false
research_result_valid = true only if:
  baseline_trials_override_used = false
  random_baseline_trials >= configured minimum
  min(source_quality.oi_history_days, source_quality.price_history_days) >= configured minimum
  at least one candidate_window_supported_overall = true
```

Debug override 时额外输出：

```text
baseline_trials_override_used = true
research_result_valid = false
decision = deleveraging_proxy_inconclusive
research_result_notes includes debug_baseline_override_used
```

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_run_stage1_4e_deleveraging_proxy_sensitivity_review.py -q
```

---

## 11. Task 10: Review generator

**Files:**
- Create: `scripts/external_signal_shadow/review_stage1_4e_deleveraging_proxy_sensitivity_review.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_4e_deleveraging_proxy_sensitivity_review.py`

### Step 1: 写失败测试

Review 必须写出：

- 这是 `deleveraging proxy sensitivity review`
- 不是 B-Lite restart
- 不使用 liquidation / forceOrder / vendor
- failed 不否定真实 liquidation
- survives 不允许 live / full composite
- sparse promising 只能是 inconclusive
- up squeeze signed replay is diagnostic only and not short execution intent
- survives only permits use as Stage 1.5 external catalyst filter, not a primary signal
- survives does not skip Stage 1.5 source selection

测试名至少包括：

```text
test_review_says_survives_only_allows_external_catalyst_filter_not_primary_signal
```

### Step 2: 实现 review script

参数：

```text
--summary PATH
--output-review PATH
```

输出中文 markdown。

### Step 3: 验证

```bash
PYTHONPATH=src:. uv run pytest tests/scripts/external_signal_shadow/test_review_stage1_4e_deleveraging_proxy_sensitivity_review.py -q
```

---

## 12. Task 11: Fixture smoke 与真实运行命令

**Files:**
- Create fixtures under `tests/fixtures/external_signal_shadow/`
- Generate reports under `reports/external_signal_shadow/`
- Generate review under `docs/reviews/`

### Step 1: Fixture smoke

使用极小 fixture 验证 runner/review 闭环。

命令：

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  --oi-archive tests/fixtures/external_signal_shadow/stage1_4e_oi_rows.jsonl \
  --price-archive tests/fixtures/external_signal_shadow/stage1_4e_price_rows.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4e_deleveraging_proxy_sensitivity_review_summary.json \
  --random-baseline-trials 10 \
  --fixture-run
```

Review:

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  --summary reports/external_signal_shadow/stage1_4e_deleveraging_proxy_sensitivity_review_summary.json \
  --output-review docs/reviews/2026-06-20-external-signal-shadow-lab-stage1-4e-deleveraging-proxy-sensitivity-review_CN.md
```

### Step 2: 真实 debug run

先用 10 trials 验证真实路径闭环。

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  --oi-archive data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl \
  --price-archive data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_price_normalized.jsonl \
  --funding-archive data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_funding_normalized.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4e_deleveraging_proxy_sensitivity_review_debug_real_summary.json \
  --random-baseline-trials 10
```

### Step 3: 正式 run

debug run 成功后再跑 500 trials。

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  --oi-archive data/external_signal_shadow/derivatives_stress/oi/binance_vision_metrics_oi_180d.jsonl \
  --price-archive data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_price_normalized.jsonl \
  --funding-archive data/external_signal_shadow/lq30_runtime/stage1_4a_lq30_funding_normalized.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4e_deleveraging_proxy_sensitivity_review_500trials_real_summary.json
```

---

## 13. Final Verification

实现完成后运行：

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_*.py tests/scripts/external_signal_shadow/test_*stage1_4e_deleveraging_proxy*.py -q
```

```bash
PYTHONPATH=src:. uv run ruff check \
  src/research/external_signal_shadow/stage1_4e_deleveraging_proxy_*.py \
  scripts/external_signal_shadow/run_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  scripts/external_signal_shadow/review_stage1_4e_deleveraging_proxy_sensitivity_review.py \
  tests/research/external_signal_shadow/test_stage1_4e_deleveraging_proxy_*.py \
  tests/scripts/external_signal_shadow/test_*stage1_4e_deleveraging_proxy*.py
```

```bash
git diff --check
git status --short
```

完成后，先不要提交。让用户确认是否把 `1.4C / 1.4D / 1.4E design + 1.4E plan` 分组提交。
