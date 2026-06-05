# Route C1 Price-Only Precheck Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建 Route C1 的最小可执行研究链路：先做 live 数据重叠审计，再用现有 Binance snapshot 数据完成正式 price-only proxy precheck，并为 7 天 / 30 天 forward 判断提供清晰 gate。

**Architecture:** 本计划只实现 C1 Batch 0 和 Batch 1，不做 orderbook-aware C1、不做 C2、不做 C3、不接 live gating。新增两个 research scripts：一个负责数据 overlap audit，一个负责 C1 price-only event detection、post-event risk metrics、matched baseline、pass/fail decision。所有核心逻辑必须是 pure functions，并用 synthetic tests 覆盖防偷看、baseline matching、MAE 定义和 decision gate。

**Tech Stack:** Python 3.11, JSONL, CSV, pytest, existing Binance snapshot dataset, existing liquidation 1m dataset, reports under `reports/route_c1/`, review under `docs/reviews/`.

---

## Review Fixes Applied Before Execution

执行 Task 1-6 前必须先补齐以下修正：

1. Route C1 阈值进入 `configs/base.py`，不放在脚本 local constants。
2. 所有 symbol join / lookup 前统一用 `normalize_symbol(...)` 归一化为无斜杠大写格式，例如 `BTC/USDT -> BTCUSDT`。
3. `first_complete_5m_response_start_ms(...)` 的输入必须明确为 `shock_bar_start_ms`，不是 raw forceOrder event timestamp。
4. response entry price 固定为 first complete response window 的 `open_price`。
5. baseline matching 必须排除未来 5m window 不完整、任意微小 liquidation 非零、以及未来污染。
6. proxy / 7d live smoke / 30d forward 的 decision gate 分开计算。
7. Task 7 是 ops 路径说明，不作为 Task 1-6 当前完成条件。

Entry price 口径说明：

- 主指标使用 `entry = first complete response window first_row["open_price"]`。
- 不使用 shock minute close，也不使用 event bar 内价格。
- `response_start_ms - 60_000` 的 close 可作为诊断字段，但不作为主指标分母。

---

## 0. Scope Lock

本计划只做：

- Batch 0: `data overlap audit`
- Batch 1: `C1 price-only baseline / proxy precheck`
- 后续路径决策写入 summary

本计划禁止：

- 不做 C1 orderbook-aware 指标；
- 不做 C2 episode pressure；
- 不做 C3 context-conditioned directionality；
- 不修改 live scanner；
- 不接 live gating；
- 不因为 proxy 结果调阈值追结果。

第一版 C1 的核心问题：

> liquidation event 后，price-only 风险是否显著高于 matched baseline？

---

## 1. Output Files

新增文件：

- `scripts/audit_route_c1_data_overlap.py`
- `scripts/review_route_c1_price_only.py`
- `tests/scripts/test_audit_route_c1_data_overlap.py`
- `tests/scripts/test_review_route_c1_price_only.py`
- `docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md`（由脚本生成）

新增输出目录：

- `reports/route_c1/`

脚本输出：

- `reports/route_c1/route_c1_data_overlap_audit_summary.json`
- `reports/route_c1/route_c1_price_only_proxy_summary.json`
- `reports/route_c1/route_c1_price_only_live_smoke_summary.json`（7 天后可用）
- `reports/route_c1/route_c1_price_only_forward_30d_summary.json`（30 天后可用）

不要提交：

- raw dataset JSONL；
- downloaded ZIP；
- extracted CSV；
- large intermediate arrays。

## 1.1 Execution Status (2026-06-03)

当前计划的代码闭环已经跑通到 `Task 6`：

- `Task 0`: Route C1 config defaults 已落地；
- `Task 1`: overlap audit 脚本已按真实 flat orderbook JSONL 计算 `orderbook_snapshot_coverage_24h` 与 `orderbook_snapshot_coverage_by_symbol_24h`；当前状态已进一步推进到 `route_c1_overlap_ready_for_orderbook_aware`；
- `Task 2-6`: C1 price-only proxy precheck 已在修补统计契约后重新执行。

当前正式 proxy 结果：

```json
{
  "decision": "route_c1_price_risk_proxy_promising_wait_for_live_overlap",
  "event_count": 2958,
  "matched_event_count": 2950,
  "unmatched_event_count": 8,
  "baseline_match_rate": 0.9972954699121027,
  "post_event_vol_ratio_median": 1.7248341916772039,
  "post_event_range_ratio_median": 1.8288005784899104,
  "post_event_abs_excursion_p90_ratio": 4.535766980016738
}
```

解释：

- 修补后的 proxy 仍然通过了 C1 price-only gate；
- 这意味着 Route C1 暂时保留，继续等待 `7d live overlap + live smoke`；
- 这不等于 live filter 已通过；当前只是 `orderbook-aware` 输入门槛已经准备好，正式研究结论仍要等 `7d / 168h` 的 live overlap。

当前最新 overlap audit 结果：

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

这表示：

- Route C1 的 live `price-only` 输入链路已经打通；
- `orderbook-aware` 的输入门槛也已经打通；
- 当前真正的限制不再是 symbol coverage，而是 overlap 时长只有约 `72h`，尚未达到 `7d / 168h` 的 live smoke 门槛；
- 因此当前状态应理解为：`input ready, time not ready`。

---

## Task 0: Add Route C1 Config Defaults

**Files:**

- Modify: `configs/base.py`
- Test: `tests/test_route_c1_config.py`

**Step 1: Write failing config tests**

Create `tests/test_route_c1_config.py`.

Required tests:

```python
def test_route_c1_config_exports_required_thresholds():
    import configs.base as cfg
    assert cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD == 0.995
    assert cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS == 1440
    assert cfg.ROUTE_C1_DOMINANCE_RATIO_MIN == 0.65
    assert cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES == 5
    assert cfg.ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT == 50_000.0
    assert cfg.ROUTE_C1_ALT_ABS_THRESHOLD_USDT == 10_000.0
    assert cfg.ROUTE_C1_BASELINE_MATCH_COUNT == 20
    assert cfg.ROUTE_C1_BASELINE_MATCH_RATE_MIN == 0.70


def test_route_c1_proxy_weak_thresholds_are_explicit():
    import configs.base as cfg
    assert cfg.ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX == 1.2
    assert cfg.ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX == 1.2
    assert cfg.ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX == 1.1
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/test_route_c1_config.py
```

Expected:

```text
FAIL: attribute not found
```

**Step 3: Add config values**

Add to `configs/base.py` after the existing Liquidation Shock 1m config block:

```python
# ─── Strategy Research: Route C1 Post-Liquidation Price Risk ───────────────

ROUTE_C1_EVENT_PERCENTILE_THRESHOLD = 0.995
ROUTE_C1_REQUIRED_REFERENCE_BARS = 1440
ROUTE_C1_DOMINANCE_RATIO_MIN = 0.65
ROUTE_C1_DEDUP_BUCKET_MINUTES = 5
ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT = 50_000.0
ROUTE_C1_ALT_ABS_THRESHOLD_USDT = 10_000.0
ROUTE_C1_BASELINE_MATCH_COUNT = 20
ROUTE_C1_BASELINE_MATCH_RATE_MIN = 0.70
ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX = 1.2
ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX = 1.2
ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX = 1.1
```

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/test_route_c1_config.py
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add configs/base.py tests/test_route_c1_config.py
git commit -m "research: add route c1 config defaults"
```

---

## 2. Decision Labels

C1 price-only decision 必须限制在以下值：

```python
ALLOWED_C1_PRICE_ONLY_DECISIONS = (
    "route_c1_data_unavailable",
    "route_c1_baseline_match_failed",
    "route_c1_price_risk_not_confirmed",
    "route_c1_price_risk_proxy_promising_wait_for_live_overlap",
    "route_c1_price_risk_live_smoke_promising_continue_to_30d",
    "route_c1_price_risk_forward_provisional_pass",
    "route_c1_price_risk_forward_failed_stop_route_c",
)
```

Overlap audit decision 必须限制在以下值：

```python
ALLOWED_OVERLAP_DECISIONS = (
    "route_c1_overlap_not_ready",
    "route_c1_overlap_ready_for_price_only",
    "route_c1_overlap_ready_for_orderbook_aware",
)
```

---

## 3. Hard Statistical Contract

### 3.0 Symbol Normalization

所有核心 join、lookup、summary grouping 前必须统一 symbol：

```python
def normalize_symbol(sym: str) -> str:
    return sym.replace("/", "").replace(":USDT", "").upper()
```

示例：

```text
BTC/USDT      -> BTCUSDT
BTCUSDT       -> BTCUSDT
BTC/USDT:USDT -> BTCUSDT
```

测试必须覆盖：

```python
def test_normalize_symbol_matches_slash_and_non_slash_formats():
    ...
```

原因：

- `configs/base.py` 和 live data 常用 `BTC/USDT`；
- Binance historical processed dataset 使用 `BTCUSDT`；
- 不归一化会导致静默零匹配。

### 3.1 Event Detection

第一版事件算法：

- `event_score = same-symbol same-side trailing 24h percentile rank`
- `reference_window = previous 1440 1m bars`
- reference window 排除 current bar
- `event_threshold = percentile_rank >= 0.995`
- `dominance_ratio >= 0.65`
- dedup by `symbol + side + 5m bucket`
- keep max notional in dedup bucket

绝对 notional threshold：

- BTC/ETH: `50_000 USDT`
- SOL/XRP/DOGE: `10_000 USDT`

说明：

- 可以引用 `configs/base.py` 里已有的 major/alt absolute thresholds；
- Route C1 第一版阈值必须新增到 `configs/base.py`；
- 不允许把 risk thresholds 写成脚本 local constants。

新增配置项：

```python
ROUTE_C1_EVENT_PERCENTILE_THRESHOLD = 0.995
ROUTE_C1_REQUIRED_REFERENCE_BARS = 1440
ROUTE_C1_DOMINANCE_RATIO_MIN = 0.65
ROUTE_C1_DEDUP_BUCKET_MINUTES = 5
ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT = 50_000.0
ROUTE_C1_ALT_ABS_THRESHOLD_USDT = 10_000.0
ROUTE_C1_BASELINE_MATCH_COUNT = 20
ROUTE_C1_BASELINE_MATCH_RATE_MIN = 0.70
ROUTE_C1_PROXY_WEAK_VOL_RATIO_MAX = 1.2
ROUTE_C1_PROXY_WEAK_RANGE_RATIO_MAX = 1.2
ROUTE_C1_PROXY_WEAK_ABS_EXCURSION_P90_RATIO_MAX = 1.1
```

所有 summary 必须输出实际使用参数，避免后续阈值不可追踪。

### 3.2 Anti-Leakage Response Window

如果事件发生在：

```text
12:03:00 - 12:03:59
```

则：

```text
first_post_1m_window = 12:04:00
first_complete_5m_response_bar = 12:05:00 - 12:09:59
```

所有 C1 5m response metrics 必须从下一个完整 5m bar 开始。

函数签名必须写成：

```python
def first_complete_5m_response_start_ms(shock_bar_start_ms: int) -> int:
    ...
```

边界规则：

- 如果 `shock_bar_start_ms = 12:03:00`，response starts at `12:05:00`。
- 如果 `shock_bar_start_ms = 12:05:00`，response starts at `12:10:00`，因为 `12:05-12:09` 包含 shock minute。
- 如果输入是 raw forceOrder event timestamp，必须先 floor 到 1m shock bucket，再调用该函数。

### 3.3 Risk Metrics

Direction-agnostic metrics：

- `realized_vol_5m_bps`
- `high_low_range_5m_bps`
- `max_abs_excursion_5m_bps`

Strategy-conditioned MAE：

- `mae_if_long_5m_bps`
- `mae_if_short_5m_bps`

计算口径：

```python
entry = first_response_row["open_price"]
high = max(row["high_price"] for row in response_window)
low = min(row["low_price"] for row in response_window)
max_abs_excursion_bps = max(abs(high / entry - 1), abs(low / entry - 1)) * 10000
high_low_range_bps = (high / low - 1) * 10000
mae_if_long_bps = max(0.0, 1 - low / entry) * 10000
mae_if_short_bps = max(0.0, high / entry - 1) * 10000
```

输入 rows 必须包含：

```text
bar_start_ms
open_price
high_price
low_price
close_price
```

如果 dataset 缺少 high/low，CLI 必须从 kline CSV merge；不能用 open/close 替代 high/low。

### 3.4 Matched Baseline

每个 event 尝试匹配 `K = 20` 个 baseline windows。

主匹配条件：

1. same symbol；
2. same month；
3. same hour-of-day bucket，允许 `+-1h`；
4. pre-event 30m realized volatility percentile 位于同一个 10% 分位桶；
5. baseline candidate 自身、future response window、前 30m、后 30m 内任意 liquidation notional 都必须为 0；
6. 不与其他 event response window 重叠。

Pre-event 30m realized volatility 定义：

```python
pre30_vol = std(log(close_t / close_t_minus_1)) for the 30 one-minute returns before candidate_start
```

约束：

- candidate 的 `pre30_vol` 只使用 candidate_start 之前的数据；
- volatility percentile reference 是 same symbol + same month 的所有 rolling `pre30_vol`；
- baseline candidate 必须有完整 future 5m response window；
- baseline candidate 的自身窗口、future 5m response window、以及前后 30m 内，`total_liquidation_notional_1m_usdt` 必须全部为 `0.0`；
- 不能只排除达到 C1 threshold 的 shock，小额 liquidation 也会污染 baseline。

Fallback：

1. 先放宽 time-of-day；
2. 再把 vol percentile 放宽到 `+-20%`；
3. 仍匹配不到，则标记为 `no_matched_baseline`；
4. unmatched event 不进入主统计。

### 3.5 Pass / Fail Gate

正式 C1 price-only gate：

```text
event_count >= 100
matched_event_count >= 70
baseline_match_rate >= 0.70
post_event_vol_ratio_median >= 1.5
post_event_range_ratio_median >= 1.4
post_event_abs_excursion_p90 / baseline_abs_excursion_p90 >= 1.3
symbols_passing >= 2 among BTC/ETH/SOL
months_passing >= 2
max_single_symbol_event_share <= 0.60
max_single_month_event_share <= 0.60
```

Run-mode specific gates：

```text
proxy_snapshot:
  require months_passing >= 2
  emit can_promote_live_filter = false

live_smoke_7d:
  do not require months_passing
  require overlap_hours >= 168
  label only smoke; cannot promote C1

forward_30d:
  do not require months_passing >= 2
  require sample_days >= 30
  require day concentration gate instead of month gate
```

新增 summary 字段：

```json
{
  "sample_days": 0,
  "events_by_day": {},
  "max_single_day_event_share": 0.0
}
```

Proxy kill-switch 参考线：

```text
if proxy vol_ratio < 1.2
and proxy range_ratio < 1.2
and proxy abs_excursion_p90_ratio < 1.1
then proxy result is weak
```

注意：

- proxy weak 不等于立刻停止 live collector；
- proxy weak + 7d live smoke weak 才建议停止 Route C1，不等 30 天。

---

## 4. Task 1: Add Data Overlap Audit Script

**Files:**

- Create: `scripts/audit_route_c1_data_overlap.py`
- Create: `tests/scripts/test_audit_route_c1_data_overlap.py`
- Output: `reports/route_c1/route_c1_data_overlap_audit_summary.json`

**Step 1: Write failing tests**

Create `tests/scripts/test_audit_route_c1_data_overlap.py`.

Required tests:

```python
def test_compute_time_span_reports_earliest_latest_and_hours():
    ...

def test_compute_symbol_overlap_hours_intersects_liquidation_price_and_orderbook():
    ...

def test_overlap_audit_marks_price_only_ready_without_orderbook():
    ...

def test_overlap_audit_marks_orderbook_aware_false_when_orderbook_missing():
    ...

def test_overlap_decision_requires_coverage_thresholds():
    ...

def test_normalize_symbol_matches_slash_and_non_slash_formats():
    ...

def test_overlap_audit_reports_missing_liquidation_input_blocker():
    ...
```

Expected pure functions:

```python
normalize_symbol(sym)
compute_time_span(rows, timestamp_key)
compute_overlap_hours_by_symbol(liquidation_spans, price_spans, orderbook_spans)
compute_coverage_ratio(rows, expected_minutes)
compute_overlap_decision(summary)
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_audit_route_c1_data_overlap.py
```

Expected:

```text
FAIL: module or functions not found
```

**Step 3: Implement minimal audit script**

`scripts/audit_route_c1_data_overlap.py` must support:

```bash
PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \
  --mode live_overlap \
  --liquidation-1m data/trend_regime_liquidation_1m.jsonl \
  --price-1m reports/liquidation_shock_event_study/liquidation_shock_1m_dataset.jsonl \
  --orderbook-dir /Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output reports/route_c1/route_c1_data_overlap_audit_summary.json
```

Required output shape:

```json
{
  "mode": "live_overlap",
  "liquidation_input_exists": false,
  "price_input_exists": false,
  "orderbook_dir_exists": false,
  "primary_blocker": "missing_liquidation_1m_input",
  "liquidation_1m_zero_fill_coverage_24h": 0.0,
  "orderbook_snapshot_coverage_24h": 0.0,
  "price_1m_coverage_24h": 0.0,
  "overlap_hours_by_symbol": {},
  "ready_for_price_only": false,
  "ready_for_orderbook_aware": false,
  "decision": "route_c1_overlap_not_ready"
}
```

Decision logic:

- `--mode live_overlap` requires `--liquidation-1m`.
- If `--liquidation-1m` is missing or path does not exist, summary must set `liquidation_input_exists = false` and `primary_blocker = "missing_liquidation_1m_input"`.
- `--mode proxy_snapshot` does not require `--liquidation-1m`; it uses `--proxy-dataset`.
- `ready_for_price_only = true` if liquidation + price overlap exists and price coverage >= 0.95.
- `ready_for_orderbook_aware = true` if liquidation + price + orderbook overlap exists for at least 2 of BTC/ETH/SOL and orderbook coverage >= 0.80.
- 7d readiness requires at least 168 overlap hours for live forward audit; but script should also output partial overlap.

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_audit_route_c1_data_overlap.py
```

Expected:

```text
PASS
```

**Step 5: Run script on current local data**

```bash
PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \
  --mode live_overlap \
  --liquidation-1m data/trend_regime_liquidation_1m.jsonl \
  --price-1m reports/liquidation_shock_event_study/liquidation_shock_1m_dataset.jsonl \
  --orderbook-dir /Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output reports/route_c1/route_c1_data_overlap_audit_summary.json
```

Expected current result:

```text
decision = route_c1_overlap_not_ready
ready_for_orderbook_aware = false
primary_blocker = missing_liquidation_1m_input if data/trend_regime_liquidation_1m.jsonl is absent
```

Reason:

- local orderbook is `2026-02-10` to `2026-05-08`;
- existing local liquidation sample is `2026-05-26` to `2026-05-30`;
- no live overlap in local archive yet.

**Step 6: Commit**

```bash
git add scripts/audit_route_c1_data_overlap.py tests/scripts/test_audit_route_c1_data_overlap.py reports/route_c1/route_c1_data_overlap_audit_summary.json
git commit -m "research: add route c1 data overlap audit"
```

---

## 5. Task 2: Add C1 Price-Only Pure Metrics

**Files:**

- Create: `scripts/review_route_c1_price_only.py`
- Create: `tests/scripts/test_review_route_c1_price_only.py`

**Step 1: Write failing tests for response window and metrics**

Add tests:

```python
def test_first_complete_5m_response_bar_excludes_event_bar():
    ...

def test_first_complete_5m_response_bar_when_event_on_5m_boundary():
    ...

def test_compute_price_risk_metrics_direction_agnostic():
    ...

def test_compute_mae_if_long_and_short_are_side_conditioned():
    ...

def test_price_risk_metrics_use_first_response_open_as_entry():
    ...

def test_response_metrics_return_none_when_future_window_incomplete():
    ...
```

Expected functions:

```python
first_complete_5m_response_start_ms(shock_bar_start_ms)
compute_price_risk_metrics(rows, start_ms, horizon_minutes=5)
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "response or metric or mae"
```

Expected:

```text
FAIL
```

**Step 3: Implement pure metrics**

Implement:

```python
_MS_PER_MIN = 60_000
_MS_PER_5M = 300_000

def first_complete_5m_response_start_ms(shock_bar_start_ms: int) -> int:
    return ((shock_bar_start_ms // _MS_PER_5M) + 1) * _MS_PER_5M
```

Boundary expectation:

```python
# 12:05:00 shock bar start is inside the 12:05-12:09 5m bar.
# First complete post-event 5m response starts at 12:10:00.
```

`compute_price_risk_metrics(...)` returns:

```json
{
  "realized_vol_5m_bps": 0.0,
  "high_low_range_5m_bps": 0.0,
  "max_abs_excursion_5m_bps": 0.0,
  "mae_if_long_5m_bps": 0.0,
  "mae_if_short_5m_bps": 0.0
}
```

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "response or metric or mae"
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add scripts/review_route_c1_price_only.py tests/scripts/test_review_route_c1_price_only.py
git commit -m "research: add route c1 price risk metrics"
```

---

## 6. Task 3: Add C1 Event Detection

**Files:**

- Modify: `scripts/review_route_c1_price_only.py`
- Modify: `tests/scripts/test_review_route_c1_price_only.py`

**Step 1: Write failing event detection tests**

Add tests:

```python
def test_detect_c1_events_requires_previous_1440_reference_bars():
    ...

def test_detect_c1_events_excludes_current_bar_from_percentile_reference():
    ...

def test_detect_c1_events_requires_995_percentile():
    ...

def test_detect_c1_events_applies_major_and_alt_abs_thresholds():
    ...

def test_detect_c1_events_requires_dominance_ratio_065():
    ...

def test_detect_c1_events_deduplicates_symbol_side_5m_bucket_keep_largest():
    ...

def test_detect_c1_events_reads_thresholds_from_config():
    ...
```

Expected functions:

```python
detect_c1_events(rows, thresholds)
compute_percentile_rank(value, previous_values)
deduplicate_c1_events(events)
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "detect_c1"
```

Expected:

```text
FAIL
```

**Step 3: Implement event detection**

Use `configs/base.py` Route C1 constants:

```python
import configs.base as cfg

cfg.ROUTE_C1_EVENT_PERCENTILE_THRESHOLD
cfg.ROUTE_C1_REQUIRED_REFERENCE_BARS
cfg.ROUTE_C1_DOMINANCE_RATIO_MIN
cfg.ROUTE_C1_DEDUP_BUCKET_MINUTES
cfg.ROUTE_C1_MAJOR_ABS_THRESHOLD_USDT
cfg.ROUTE_C1_ALT_ABS_THRESHOLD_USDT
```

Event dict shape:

```json
{
  "symbol": "BTCUSDT",
  "shock_bar_start_ms": 1700000000000,
  "dominant_liquidation_side": "long",
  "shock_notional_usdt": 100000.0,
  "relative_score": 0.996,
  "reference_count": 1440,
  "dominance_ratio": 0.75,
  "dedup_bucket_start_ms": 1700000000000
}
```

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "detect_c1"
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add scripts/review_route_c1_price_only.py tests/scripts/test_review_route_c1_price_only.py
git commit -m "research: add route c1 event detection"
```

---

## 7. Task 4: Add Baseline Matching

**Files:**

- Modify: `scripts/review_route_c1_price_only.py`
- Modify: `tests/scripts/test_review_route_c1_price_only.py`

**Step 1: Write failing baseline tests**

Add tests:

```python
def test_compute_pre30_vol_bucket_uses_prior_returns_only():
    ...

def test_compute_pre30_vol_uses_log_return_std():
    ...

def test_match_baselines_returns_20_windows_when_available():
    ...

def test_match_baselines_excludes_windows_near_liquidation_shocks():
    ...

def test_match_baselines_excludes_any_nonzero_liquidation_notional():
    ...

def test_match_baselines_excludes_candidates_without_complete_future_window():
    ...

def test_match_baselines_falls_back_by_relaxing_time_then_vol_bucket():
    ...

def test_unmatched_events_are_excluded_from_main_statistics():
    ...
```

Expected functions:

```python
annotate_pre30_vol_buckets(rows)
match_baselines_for_event(event, candidate_rows, shock_index, k=20)
build_event_baseline_pairs(events, rows_by_symbol)
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "baseline"
```

Expected:

```text
FAIL
```

**Step 3: Implement baseline matching**

Rules:

- Primary: symbol + month + hour ±1 + same vol bucket.
- Fallback 1: relax time-of-day.
- Fallback 2: relax vol bucket to ±2 buckets.
- `pre30_vol` is `std(log(close_t / close_t_minus_1))` over the 30 one-minute returns before candidate start.
- Vol bucket reference distribution is same symbol + same month rolling `pre30_vol`.
- Exclude rows within ±30m of any nonzero liquidation notional, not only C1 shocks.
- Exclude candidate if candidate row, future 5m response window, or ±30m guard window has any `total_liquidation_notional_1m_usdt > 0`.
- Exclude candidate if its future 5m response window is incomplete.
- Exclude rows whose 5m response overlaps event response windows.
- Sample deterministically with fixed seed `7` for repeatability.

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "baseline"
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add scripts/review_route_c1_price_only.py tests/scripts/test_review_route_c1_price_only.py
git commit -m "research: add route c1 matched baseline"
```

---

## 8. Task 5: Add Summary And Decision Gate

**Files:**

- Modify: `scripts/review_route_c1_price_only.py`
- Modify: `tests/scripts/test_review_route_c1_price_only.py`

**Step 1: Write failing summary tests**

Add tests:

```python
def test_build_c1_summary_reports_required_counts_and_ratios():
    ...

def test_c1_ratios_are_computed_per_event_then_median_across_events():
    ...

def test_c1_decision_data_unavailable_when_no_events():
    ...

def test_c1_decision_baseline_match_failed_when_match_rate_below_070():
    ...

def test_c1_decision_price_risk_not_confirmed_when_ratios_below_gate():
    ...

def test_c1_decision_proxy_promising_when_proxy_ratios_pass():
    ...

def test_c1_summary_reports_concentration_limits():
    ...

def test_c1_decision_uses_run_mode_specific_gates():
    ...
```

Expected functions:

```python
build_c1_price_only_summary(event_metrics, baseline_metrics, metadata)
compute_c1_price_only_decision(summary, run_mode)
```

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "decision or summary"
```

Expected:

```text
FAIL
```

**Step 3: Implement summary and decision**

Required summary shape:

```json
{
  "run_mode": "proxy_snapshot",
  "data_source": "binance_vision_liquidation_snapshot",
  "data_semantics": "snapshot_proxy_not_complete_liquidation_tape",
  "generalization_allowed": false,
  "can_promote_live_filter": false,
  "event_count": 0,
  "matched_event_count": 0,
  "unmatched_event_count": 0,
  "matched_baseline_count": 0,
  "baseline_match_rate": 0.0,
  "post_event_vol_ratio_median": 0.0,
  "post_event_range_ratio_median": 0.0,
  "post_event_abs_excursion_p90_ratio": 0.0,
  "max_abs_excursion_p90_bps": 0.0,
  "mae_if_long_p90_bps": 0.0,
  "mae_if_short_p90_bps": 0.0,
  "events_by_symbol": {},
  "events_by_month": {},
  "events_by_day": {},
  "sample_days": 0,
  "max_single_symbol_event_share": 0.0,
  "max_single_month_event_share": 0.0,
  "max_single_day_event_share": 0.0,
  "route_c1_params": {},
  "proxy_kill_switch_weak": false,
  "decision": "route_c1_price_risk_not_confirmed"
}
```

Ratio aggregation contract:

```text
For each matched event:
  baseline_anchor = median(metric across that event's K matched baseline windows)
  event_ratio = event_metric / baseline_anchor

Summary ratio:
  median(event_ratio across matched events)
```

Do not compute:

```text
median(all event metrics) / median(all baseline metrics)
```

That would lose the matched-control structure.

Proxy-specific decision:

- If hard gate passes in proxy mode: `route_c1_price_risk_proxy_promising_wait_for_live_overlap`.
- If proxy kill-switch weak: still output `route_c1_price_risk_not_confirmed`, with `proxy_kill_switch_weak = true`.
- Proxy mode requires `months_passing >= 2`.
- Proxy mode always emits `can_promote_live_filter = false`.

Live smoke decision:

- If 7d live smoke ratios are promising but months gate unavailable: `route_c1_price_risk_live_smoke_promising_continue_to_30d`.
- If weak: `route_c1_price_risk_forward_failed_stop_route_c`.
- Live smoke requires `overlap_hours >= 168` and does not require `months_passing`.

Forward 30d decision:

- Requires `sample_days >= 30`.
- Does not require `months_passing >= 2`.
- Uses `max_single_day_event_share` instead of month concentration as the primary concentration gate.

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "decision or summary"
```

Expected:

```text
PASS
```

**Step 5: Commit**

```bash
git add scripts/review_route_c1_price_only.py tests/scripts/test_review_route_c1_price_only.py
git commit -m "research: add route c1 price-only decision gate"
```

---

## 9. Task 6: Add CLI For Formal Proxy Precheck

**Files:**

- Modify: `scripts/review_route_c1_price_only.py`
- Modify: `tests/scripts/test_review_route_c1_price_only.py`
- Output: `reports/route_c1/route_c1_price_only_proxy_summary.json`
- Output: `docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md`

**Step 1: Write failing CLI tests**

Add tests:

```python
def test_parse_args_supports_proxy_snapshot_mode():
    ...

def test_load_dataset_merges_high_low_from_kline_root_when_missing():
    ...

def test_load_dataset_normalizes_symbols_before_joining_kline_rows():
    ...

def test_review_markdown_includes_decision_and_next_path():
    ...

def test_review_markdown_declares_proxy_cannot_promote_live_filter():
    ...
```

CLI must support:

```bash
PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \
  --run-mode proxy_snapshot \
  --dataset data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl \
  --kline-root data/binance_liquidation_snapshot/extracted/klines \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_price_only_proxy_summary.json \
  --review-output docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md
```

Reason for `--kline-root`:

- existing processed Binance snapshot dataset has `open_price` / `close_price`;
- C1 needs `high_price` / `low_price`;
- extracted 1m kline CSVs contain high/low and must be merged by `symbol + bar_start_ms`.

**Step 2: Run tests and verify failure**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py -k "parse_args or kline or markdown"
```

Expected:

```text
FAIL
```

**Step 3: Implement CLI and markdown renderer**

Markdown review must include:

- data source and sample window;
- data semantics: `snapshot_proxy_not_complete_liquidation_tape`;
- `generalization_allowed = false`;
- `can_promote_live_filter = false`;
- event algorithm;
- anti-leakage response definition;
- matched baseline summary;
- price-risk ratios;
- pass/fail decision;
- next path:
  - `continue_collect_7d_overlap`;
  - `stop_after_7d_if_live_smoke_weak`;
  - `continue_to_30d_only_if_live_smoke_promising`.

**Step 4: Run tests**

```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_route_c1_price_only.py
```

Expected:

```text
PASS
```

**Step 5: Run formal proxy precheck**

```bash
PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \
  --run-mode proxy_snapshot \
  --dataset data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl \
  --kline-root data/binance_liquidation_snapshot/extracted/klines \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_price_only_proxy_summary.json \
  --review-output docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md
```

Current formal proxy result after statistical-contract repairs:

```text
decision = route_c1_price_risk_proxy_promising_wait_for_live_overlap
proxy_kill_switch_weak = false
event_count = 2958
matched_event_count = 2950
baseline_match_rate = 0.997
post_event_vol_ratio_median = 1.725
post_event_range_ratio_median = 1.829
post_event_abs_excursion_p90_ratio = 4.536
```

Do not tune thresholds after seeing this result.

Execution note:

- proxy 当前已经通过；
- 下一步不是继续调参，而是等待 `7d live overlap audit`；
- `Task 1` 的 overlap audit 已能对 flat orderbook JSONL 给出真实 24h coverage；当前仍不能推进 live smoke 的原因，是本地没有 `liquidation_1m` 输入，尚不存在可审计的 live overlap。

**Step 6: Commit**

```bash
git add \
  scripts/review_route_c1_price_only.py \
  tests/scripts/test_review_route_c1_price_only.py \
  reports/route_c1/route_c1_price_only_proxy_summary.json \
  docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md
git commit -m "research: add route c1 price-only proxy precheck"
```

---

## 10. Post-Task Ops Note: Add Live Smoke Run Instructions

This section is not part of the Task 1-6 completion condition.

Task 1-6 completion means:

- focused tests pass;
- formal proxy precheck runs;
- summary is generated;
- review markdown is generated;
- no threshold tuning is performed after seeing proxy result.

The following ops update can be done after the proxy code loop is complete.

**Files:**

- Modify: `docs/ops/2026-06-05-route-c-orderbook-weekly-sync-cleanup_CN.md`
- Modify: `docs/plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md` if needed after execution

**Step 1: Add live smoke commands to ops**

After 7 days of collection, run on server:

```bash
cd /root/crypto-alpha-lab
PYTHONPATH=. python3 scripts/check_liquidation_collector_health.py \
  --data-dir data \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT
```

Sync live liquidation aggregates and orderbook archive to local.

Then run locally:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/audit_route_c1_data_overlap.py \
  --liquidation-1m data/trend_regime_liquidation_1m.jsonl \
  --price-1m data/trend_regime_price_1m.jsonl \
  --orderbook-dir /Users/tanshuai/Desktop/AI-test/my-bitcoin-project/data/historical_orderbook_server_archive \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT \
  --output reports/route_c1/route_c1_data_overlap_audit_summary.json
```

If price 1m live file is not available, use a dedicated Binance kline fetcher or defer live smoke.

**Step 2: Add explicit 7d decision**

7d live smoke action:

- If overlap not ready: fix collection, do not start 30d countdown.
- If overlap ready but price-risk smoke weak: stop Route C1 and document.
- If overlap ready and smoke promising: continue to 30d forward review.

**Step 3: Commit**

```bash
git add docs/ops/2026-06-05-route-c-orderbook-weekly-sync-cleanup_CN.md docs/plans/2026-06-02-route-c1-price-only-implementation-plan_CN.md
git commit -m "docs: add route c1 live smoke path"
```

---

## 11. Verification Commands

Run focused tests:

```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_route_c1_config.py \
  tests/scripts/test_audit_route_c1_data_overlap.py \
  tests/scripts/test_review_route_c1_price_only.py
```

Run relevant existing liquidation tests:

```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_liquidation_shock_detection.py \
  tests/research/test_liquidation_shock_response_map.py \
  tests/scripts/test_build_binance_liquidation_snapshot_event_dataset.py \
  tests/scripts/test_review_binance_liquidation_snapshot_event_study.py
```

Run formal proxy review:

```bash
PYTHONPATH=src uv run python scripts/review_route_c1_price_only.py \
  --run-mode proxy_snapshot \
  --dataset data/binance_liquidation_snapshot/processed/binance_snapshot_dataset.jsonl \
  --kline-root data/binance_liquidation_snapshot/extracted/klines \
  --symbols BTCUSDT ETHUSDT SOLUSDT \
  --output reports/route_c1/route_c1_price_only_proxy_summary.json \
  --review-output docs/reviews/2026-06-02-route-c1-price-only-proxy-review.md
```

Inspect summary:

```bash
jq '{decision, proxy_kill_switch_weak, event_count, matched_event_count, baseline_match_rate, post_event_vol_ratio_median, post_event_range_ratio_median, post_event_abs_excursion_p90_ratio}' \
  reports/route_c1/route_c1_price_only_proxy_summary.json
```

---

## 12. Follow-Up Path

### Immediate Path: Existing Data Proxy

Use Binance snapshot to run formal C1 price-only proxy precheck now.

If result is weak:

- keep collectors running;
- do not wait 30 days blindly;
- wait only for 7d live overlap audit;
- if 7d live smoke also weak, stop Route C1.

If result is promising:

- keep collectors running;
- run 7d live overlap audit;
- continue to 30d forward review only if live smoke is also promising.

### 7-Day Path: Live Overlap Audit

After 7 days of simultaneous liquidation + orderbook collection:

- run overlap audit;
- confirm liquidation 1m coverage;
- confirm price 1m coverage;
- confirm orderbook coverage;
- run live smoke only if data overlap is ready.

7d live smoke cannot promote C1. It can only decide whether waiting for 30d is justified.

### 30-Day Path: Forward Provisional Review

After 30 days:

- run C1 price-only forward review;
- label result `forward_provisional`;
- do not require `months_passing >= 2` yet;
- require all other gates where sample size permits;
- if weak, stop Route C1;
- if promising, write separate implementation plan for C1 orderbook-aware.

### C2/C3 Path

Do not start C2 unless:

- C1 price-only passes;
- `event_count >= 100`;
- at least 2 symbols pass;
- `baseline_match_rate >= 0.70`.

Do not start C3 unless:

- C1 orderbook-aware passes; or
- C2 improves C1 metrics by at least 20%;
- each context bucket has at least 50 events;
- walk-forward split exists;
- estimated net edge after costs is positive.

---

## 13. Stop Conditions

Stop Route C1 without waiting 30 days if:

- formal proxy precheck is weak by kill-switch criteria; and
- 7d live smoke is also weak; and
- no orderbook/price data issue explains the weakness.

Stop Route C entirely if:

- C1 cannot identify post-liquidation price-risk elevation; and
- orderbook overlap later also fails to show spread/depth/impact deterioration.

This avoids spending another month collecting data for a signal that already failed both historical proxy and live smoke.
