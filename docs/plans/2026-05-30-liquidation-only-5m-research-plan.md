# Liquidation-Only 5m Research Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一条与 `trend_regime` 完全解耦的 `5m` 纯 liquidation-only 研究链路，用于独立评估 `continuation` 与 `mean_reversion` 两条假设在 `BTC/ETH/SOL/XRP/DOGE` 上是否存在可持续的条件收益。

**Architecture:** 本计划不延续当前 `trend_regime` 下的 `vol_breakout` 或 `liquidation_cascade` 定义。两者视为已归档的前序研究。本轮将新建独立的 `liquidation_only_5m` research namespace，单独完成 5m liquidation 数据可得性验证、5m 数据获取、事件表构建、双假设 forward-return 审计和 review 产物生成。第一轮 baseline 刻意保持极简：只用 liquidation 事件本身，不混入 OI、价格 breakout、funding、orderbook 或执行层过滤；但必须显式扣除最小 round-trip 成本，不允许用 gross return 直接决定是否继续 Phase 2。

**Tech Stack:** Python 3.11, pytest, ruff, JSON/JSONL, Coinalyze historical liquidation API, 5m OHLCV bars, trailing-window percentile anomaly scoring, standalone research scripts, markdown review + JSON reports.

---

## Background

当前证据已经比较明确：

- `vol_breakout` 子策略已在 `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md` 中得到 `retire_vol_breakout_branch`。
- 当前版 `liquidation_cascade` 在 Route B-only 条件下已完成 replay，结论为 `retire_liquidation_cascade_branch`，见 `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md`。
- 当前版 `liquidation_cascade` 不是纯 liquidation 策略，而是混合了 `1h vol / return / OI` 的 trend-regime 门槛，因此它的失败不能直接等价为“liquidation 主题不存在 alpha”。
- 接下来最干净的研究问题应收敛为：
  - 在 `5m` 粒度下；
  - 对 `BTC / ETH / SOL / XRP / DOGE`；
  - 当 liquidation 事件同时满足“绝对额够大 + 相对过去 7 天同币种 5m 分布显著异常”时；
  - 后续 `1 / 2 / 3` 个 `5m bar` 的条件收益，在 `continuation` 与 `mean_reversion` 两条假设下分别表现如何。

本计划的第一轮目标不是产出可实盘策略，而是做一次主题去伪存真的 baseline 研究：

- 如果 5m 数据深度都不支持 7 天 trailing lookback，则立即停止，不继续堆工程；
- 如果纯 liquidation 事件本身没有稳定条件收益，则停止继续堆工程；
- 如果至少一条 hypothesis 出现稳定正证据，再决定是否进入二级过滤增强阶段。

---

## Scope Boundary

### In Scope For This Plan

- 新建独立 research namespace：`src/research/liquidation_only_5m/`
- 先做 `5m` Route B 可得性探针，确认免费数据是否支持 7 天 trailing baseline
- 构建 `5m` liquidation + `5m` price 的最小事件表
- 使用双门槛定义异常 liquidation 事件：
  - 分层绝对阈值（`BTC/ETH` vs `SOL/XRP/DOGE`）
  - 过去 7 天同币种 `5m liquidation` 分布上的 trailing percentile 异常，且**排除当前 bar**
- 增加方向标签质量控制：dominance ratio
- 同时研究两条 hypothesis：
  - `continuation`
  - `mean_reversion`
- 使用固定短持有期：
  - `+1 bar`
  - `+2 bars`
  - `+3 bars`
- 主收益口径使用：
  - `next_open_to_horizon_close`
- 诊断口径附带输出：
  - `close_to_close`
- baseline review 必须同时输出：
  - gross returns
  - assumed-min-cost-adjusted returns
  - by-symbol
  - by-hypothesis
  - by-horizon
  - holdout / by-period consistency
- 输出 JSON summary 与 markdown review

### Explicitly Out Of Scope For Phase 1

- OI confirmation
- breakout / return threshold
- funding state
- orderbook imbalance
- slippage simulator / maker-taker path
- dynamic stop loss / trailing exits
- Route A / Route C overlap
- strategy-layer live execution integration
- symbol-specific threshold optimization beyond the major/alt two-tier split

### Deferred Enhancements (Only If Baseline Is Positive)

- `1m observe + 5m trigger`
- liquidation + OI contraction 二级确认
- liquidation + funding / premium state
- full orderbook-aware execution replay
- dynamic stop / decay exits
- majors vs large-alts 分层独立回测
- more advanced walk-forward / rolling retrain threshold sweeps

---

## Repository Boundary Rule

本轮研究必须遵守以下仓库边界：

1. **不得继续修改或复用当前 `src/strategies/trend_regime/` 下的分类器来承载 baseline。**
2. **不得把新 baseline 实现挂回 `review_trend_liquidation_cascade.py`。**
3. **不得为了 5m baseline 直接改变现有 1h Route B CLI 的行为。**
4. **所有 baseline 研究逻辑必须落在新的独立 namespace：**
   - `src/research/liquidation_only_5m/`
   - `tests/research/`
   - `scripts/`
5. `vol_breakout` 与当前版 `liquidation_cascade` 只作为历史对照，不再作为本计划的实现依赖。
6. 如果需要复用 Coinalyze vendor 适配逻辑，应通过单独 adapter module 或新脚本封装，确保现有 `1h` Route B 测试与行为保持不变。

---

## Required Config Additions

本计划中的新阈值必须进入 `configs/base.py`，不得写入 `src/` 作为魔法数字。Phase 1 至少需要以下常量：

- `LIQUIDATION_ONLY_5M_MAJOR_ABS_THRESHOLD_USDT`
- `LIQUIDATION_ONLY_5M_ALT_ABS_THRESHOLD_USDT`
- `LIQUIDATION_ONLY_5M_RELATIVE_SCORE_THRESHOLD`
- `LIQUIDATION_ONLY_5M_ROLLING_LOOKBACK_DAYS`
- `LIQUIDATION_ONLY_5M_FORWARD_HORIZONS_BARS`
- `LIQUIDATION_ONLY_5M_DOMINANCE_RATIO_MIN`
- `LIQUIDATION_ONLY_5M_ASSUMED_MIN_ROUND_TRIP_COST_BPS`

这些数值在 Phase 1 里只代表 baseline defaults，不代表已验证最优参数。

---

## Batch A: Feasibility First

### Task 0: Probe 5m Route B Depth Before Building The Research Stack

**Files:**
- Create: `scripts/probe_liquidation_only_5m_feasibility.py`
- Create: `tests/scripts/test_probe_liquidation_only_5m_feasibility.py`
- Create: `reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_feasibility.json`

**Step 1: Write failing tests for the feasibility probe**

Add tests asserting the probe reports:

- `vendor = coinalyze`
- `interval = 5min`
- `symbols_requested`
- `rows_per_symbol`
- `min_bar_start_ms`
- `max_bar_start_ms`
- `span_days_per_symbol`
- `supports_7d_lookback`
- `decision`

Also add a failure test asserting:

- if a symbol has fewer than `2016 + 288` usable 5m bars, it does **not** qualify for baseline replay

Rationale:

- `2016` bars are required for the trailing 7d reference window
- keep at least ~1 evaluation day (`288` bars) after lookback so the baseline has actual testable events

**Step 2: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_liquidation_only_5m_feasibility.py
```
Expected: FAIL because script/tests do not yet exist.

**Step 3: Implement the feasibility probe**

The probe must inspect actual 5m vendor history and emit a JSON summary shaped roughly like:

```json
{
  "vendor": "coinalyze",
  "interval": "5min",
  "symbols_requested": ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"],
  "rows_per_symbol": {},
  "min_bar_start_ms": {},
  "max_bar_start_ms": {},
  "span_days_per_symbol": {},
  "supports_7d_lookback": true,
  "decision": "proceed"
}
```

Allowed decisions:

- `proceed`
- `partial_symbol_support`
- `insufficient_5m_depth`
- `api_unavailable`

**Step 4: Gate the rest of the plan**

Do **not** continue to Task 1 unless the feasibility output proves:

- at least the intended baseline symbol set for Phase 1 has enough depth
- or a clearly documented reduced symbol set is approved based on `partial_symbol_support`

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_liquidation_only_5m_feasibility.py
```
Expected: PASS.

**Step 6: Commit**

```bash
git add scripts/probe_liquidation_only_5m_feasibility.py tests/scripts/test_probe_liquidation_only_5m_feasibility.py reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_feasibility.json
git commit -m "feat: add liquidation-only 5m feasibility probe"
```

---

### Task 1: Add Config Constants And Independent Event Contract

**Files:**
- Modify: `configs/base.py`
- Create: `tests/test_liquidation_only_5m_config.py`
- Create: `src/research/liquidation_only_5m/__init__.py`
- Create: `src/research/liquidation_only_5m/baseline.py`
- Create: `tests/research/test_liquidation_only_5m_baseline.py`

**Step 1: Write failing config tests**

Add tests asserting all Phase 1 constants exist in `configs/base.py` and have sane types.

**Step 2: Write failing tests for the baseline event contract**

The event contract must distinguish:

- `liquidated_position_side`
- `dominant_liquidation_side`
- `continuation_trade_side`
- `mean_reversion_trade_side`
- `dominance_ratio`

Example test shape:

```python
def test_short_liquidation_maps_to_long_continuation_and_short_reversion():
    row = {
        "symbol": "BTC/USDT",
        "bar_start_ms": 1780000000000,
        "short_liquidation_notional_5m_usdt": 12_000_000.0,
        "long_liquidation_notional_5m_usdt": 500_000.0,
        "liquidation_relative_score": 0.997,
        "liquidation_reference_count": 2016,
        "dominance_ratio": 0.96,
    }

    event = classify_liquidation_only_5m_event(row)

    assert event.liquidated_position_side == "short"
    assert event.continuation_trade_side == "long"
    assert event.mean_reversion_trade_side == "short"
```

Also add a failing test asserting mixed long/short liquidation bars without sufficient dominance are rejected.

**Step 3: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_only_5m_config.py \
  tests/research/test_liquidation_only_5m_baseline.py
```
Expected: FAIL.

**Step 4: Implement config constants and minimal dataclasses**

In `baseline.py`, add:

- `LiquidationOnly5mThresholds`
- `LiquidationOnly5mEvent`
- `classify_liquidation_only_5m_event(...)`

Required behavior:

- watchlist limited to `BTC/ETH/SOL/XRP/DOGE`
- two threshold tiers:
  - majors: `BTC/ETH`
  - large_alts: `SOL/XRP/DOGE`
- event triggers only when:
  - absolute liquidation notional >= tier threshold
  - relative anomaly score >= global threshold
  - reference count is sufficient
  - dominance ratio >= minimum threshold
- event contains both continuation and mean-reversion trade sides

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_only_5m_config.py \
  tests/research/test_liquidation_only_5m_baseline.py
```
Expected: PASS.

**Step 6: Commit**

```bash
git add configs/base.py tests/test_liquidation_only_5m_config.py src/research/liquidation_only_5m/__init__.py src/research/liquidation_only_5m/baseline.py tests/research/test_liquidation_only_5m_baseline.py
git commit -m "feat: add liquidation-only 5m baseline contract and config"
```

---

## Batch B: Build The 5m Dataset And Anomaly Layer

### Task 2: Add An Isolated 5m Route B Fetch Path And Dataset Builder

**Files:**
- Create: `src/research/liquidation_only_5m/coinalyze_5m.py`
- Create: `scripts/fetch_liquidation_only_5m_history.py`
- Create: `scripts/build_liquidation_only_5m_dataset.py`
- Create: `tests/scripts/test_fetch_liquidation_only_5m_history.py`
- Create: `tests/scripts/test_build_liquidation_only_5m_dataset.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Step 1: Write failing tests for 5m Coinalyze normalization**

Add tests asserting:

- `normalize_interval("5m") -> "5min"` (or exact vendor-supported value)
- Coinalyze 5m `t` values are converted explicitly from seconds to `bar_start_ms`
- `bar_start_ms` is aligned to UTC 5m bucket boundaries
- normalized 5m rows preserve:
  - `symbol`
  - `bar_start_ms`
  - `long_liquidation_notional_5m_usdt`
  - `short_liquidation_notional_5m_usdt`
  - `total_liquidation_notional_5m_usdt`
  - `liquidation_source = third_party_historical`

Also add a regression test asserting the existing 1h Route B normalization path is unchanged.

**Step 2: Add failing tests for dataset builder**

Define tests for a new builder script that joins:

- 5m price bars
- 5m liquidation rows

and emits rows with:

- `symbol`
- `bar_start_ms`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `long_liquidation_notional_5m_usdt`
- `short_liquidation_notional_5m_usdt`
- `total_liquidation_notional_5m_usdt`

The dataset builder must also emit audit counts:

- `price_rows`
- `liquidation_rows`
- `joined_rows`
- `missing_price_bar_count`
- `missing_liquidation_bar_count`

**Step 3: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_fetch_liquidation_only_5m_history.py \
  tests/scripts/test_build_liquidation_only_5m_dataset.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: FAIL on new 5m cases.

**Step 4: Implement isolated 5m fetch path**

Required behavior:

- support `5m` research interval for Coinalyze fetch in a dedicated module/script
- keep 5m artifacts separate from existing 1h Route B outputs
- preserve all existing 1h Route B behavior and tests

**Step 5: Implement the 5m dataset builder**

Create `scripts/build_liquidation_only_5m_dataset.py` that:

- reads normalized 5m liquidation rows
- reads matching 5m price bars
- aligns on `symbol + 5m bucket`
- emits JSONL for downstream research
- writes an audit summary JSON documenting join coverage and missing data

**Step 6: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_fetch_liquidation_only_5m_history.py \
  tests/scripts/test_build_liquidation_only_5m_dataset.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: PASS.

**Step 7: Commit**

```bash
git add src/research/liquidation_only_5m/coinalyze_5m.py scripts/fetch_liquidation_only_5m_history.py scripts/build_liquidation_only_5m_dataset.py tests/scripts/test_fetch_liquidation_only_5m_history.py tests/scripts/test_build_liquidation_only_5m_dataset.py tests/scripts/test_fetch_third_party_liquidation_history.py
git commit -m "feat: add isolated liquidation-only 5m data builder"
```

---

### Task 3: Compute Trailing 7-Day Relative Scores Excluding The Current Bar

**Files:**
- Modify: `src/research/liquidation_only_5m/baseline.py`
- Modify: `scripts/build_liquidation_only_5m_dataset.py`
- Modify: `tests/research/test_liquidation_only_5m_baseline.py`
- Modify: `tests/scripts/test_build_liquidation_only_5m_dataset.py`

**Step 1: Write failing tests for rolling anomaly computation**

Add tests asserting:

- anomaly is computed per symbol, not globally
- 7-day trailing window is used
- **current bar is excluded** from the reference window
- rows with fewer than `2016` prior 5m bars are marked unavailable
- baseline method is percentile rank, not ratio-to-median

Recommended output fields:

- `liquidation_relative_score`
- `liquidation_relative_method = trailing_7d_percentile_rank_excluding_current`
- `liquidation_reference_count`
- `liquidation_reference_window_ms`

**Step 2: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_liquidation_only_5m_baseline.py \
  tests/scripts/test_build_liquidation_only_5m_dataset.py
```
Expected: FAIL because anomaly computation is not yet implemented.

**Step 3: Implement rolling baseline enrichment**

Add the minimal enrichment required:

- per-symbol trailing liquidation distribution
- 7-day lookback window
- exclusion of current bar from its own score reference
- deterministic percentile-rank anomaly score
- `dominance_ratio`
- explicit unavailable state for insufficient lookback

Do not implement multiple anomaly methods in baseline.

**Step 4: Wire the classifier to require all baseline quality gates**

Update `classify_liquidation_only_5m_event(...)` so baseline trigger requires:

- absolute tier threshold met
- relative anomaly threshold met
- sufficient trailing reference count
- dominance ratio threshold met

No OI / breakout / funding / return filters are allowed in baseline.

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/research/test_liquidation_only_5m_baseline.py \
  tests/scripts/test_build_liquidation_only_5m_dataset.py
```
Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/liquidation_only_5m/baseline.py scripts/build_liquidation_only_5m_dataset.py tests/research/test_liquidation_only_5m_baseline.py tests/scripts/test_build_liquidation_only_5m_dataset.py
git commit -m "feat: add trailing 7d liquidation percentile scoring"
```

---

## Batch C: Forward Returns And Review

### Task 4: Add Forward-Return Audit With Executable Entry Basis And Minimum Cost Adjustment

**Files:**
- Create: `src/research/liquidation_only_5m/forward_returns.py`
- Create: `tests/research/test_liquidation_only_5m_forward_returns.py`

**Step 1: Write failing tests for event-to-forward-return expansion**

Define tests asserting:

- a qualifying event generates:
  - `continuation` forward returns
  - `mean_reversion` forward returns
- horizons are exactly:
  - `+1 bar`
  - `+2 bars`
  - `+3 bars`
- symbol alignment is preserved
- events without a full horizon are dropped
- primary return basis uses `next bar open` as entry

Example output fields should include both:

- `next_open_to_horizon_close_forward_return_bps`
- `close_to_close_forward_return_bps`

**Step 2: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_only_5m_forward_returns.py
```
Expected: FAIL.

**Step 3: Implement forward-return calculator**

Required baseline outputs:

- `event_count`
- `by_hypothesis`
- `by_holding_bar_count`
- `mean_forward_return_bps`
- `median_forward_return_bps`
- `win_rate`
- `worst_forward_return_bps`
- `gross_*`
- `cost_adjusted_*`

Required cost behavior:

- read assumed minimum round-trip cost from `configs/base.py`
- subtract it from gross return metrics in a transparent, deterministic way
- keep gross and cost-adjusted fields side by side

Do not yet add:

- stop loss
- dynamic exits
- orderbook simulator

**Step 4: Re-run the tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_only_5m_forward_returns.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/liquidation_only_5m/forward_returns.py tests/research/test_liquidation_only_5m_forward_returns.py
git commit -m "feat: add liquidation-only 5m forward return audit"
```

---

### Task 5: Build Baseline Review Script And Quantified Decision Artifacts

**Files:**
- Create: `scripts/review_liquidation_only_5m.py`
- Create: `tests/scripts/test_review_liquidation_only_5m.py`
- Create: `docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md`
- Create: `reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json`

**Step 1: Write failing tests for the review script**

Define tests asserting summary includes:

- `event_count`
- `events_per_30d`
- `by_symbol`
- `by_hypothesis`
- `by_holding_bar_count`
- `by_period`
- `period_consistency`
- `max_single_symbol_event_share`
- `gross_*`
- `cost_adjusted_*`
- final `decision`

The review script must write aggregated JSON only and the markdown review must explicitly explain:

- continuation result
- mean-reversion result
- capital utilization
- data quality status
- keep / retire decision

**Step 2: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_liquidation_only_5m.py
```
Expected: FAIL.

**Step 3: Implement review script**

Required behavior:

- read the enriched 5m event dataset
- compute continuation and mean-reversion summaries
- compute holdout or by-period consistency using a time-based split
- write JSON summary
- emit markdown review

Minimum anti-snooping requirement:

- use a trailing time split so the final decision is not based only on full-sample aggregates
- if data span is long enough, also report calendar-period breakdowns

Required decision states:

- `continue_to_phase2_enhancements`
- `retire_liquidation_only_5m_baseline`
- `insufficient_5m_data_depth`
- `insufficient_event_density`
- `data_quality_failed`

**Step 4: Quantify the continue/retire rule**

The final decision must not rely on mean alone. It must primarily use:

- cost-adjusted median
- win rate
- event density
- tail loss
- symbol concentration
- adjacent-horizon consistency

Baseline continue criteria should be machine-checkable and documented in the JSON summary.

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_liquidation_only_5m.py
```
Expected: PASS.

**Step 6: Generate baseline artifacts from local data**

Run the review script with actual local dataset inputs and write:

- `reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json`
- `docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md`

**Step 7: Run full verification including ruff**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_only_5m_config.py \
  tests/scripts/test_probe_liquidation_only_5m_feasibility.py \
  tests/research/test_liquidation_only_5m_baseline.py \
  tests/research/test_liquidation_only_5m_forward_returns.py \
  tests/scripts/test_fetch_liquidation_only_5m_history.py \
  tests/scripts/test_build_liquidation_only_5m_dataset.py \
  tests/scripts/test_review_liquidation_only_5m.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
ruff check src/research tests/research tests/scripts scripts
ruff format --check src/research tests/research tests/scripts scripts
```
Expected: PASS.

**Step 8: Commit**

```bash
git add scripts/review_liquidation_only_5m.py tests/scripts/test_review_liquidation_only_5m.py docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json
git commit -m "feat: add liquidation-only 5m baseline review"
```

---

## Quantified Success Criteria

The baseline may proceed to Phase 2 enhancements only if all of the following are true:

1. Total qualified events are not too sparse for inference.
2. At least one hypothesis (`continuation` or `mean_reversion`) is positive on a cost-adjusted basis.
3. The positive result is not carried entirely by a single symbol.
4. The result survives adjacent horizons rather than appearing only on one isolated bar count.
5. Tail loss is not so extreme that later execution realism would obviously kill the edge.

The JSON review must encode machine-checkable gates at minimum for:

- `min_total_events`
- `min_positive_symbols`
- `max_single_symbol_event_share`
- `min_events_per_30d`
- `min_cost_adjusted_median_bps`
- `min_gross_median_bps`
- `min_win_rate`
- `max_worst_forward_return_bps`
- `adjacent_horizon_consistency_required`

The final decision must be driven primarily by median + win rate + tail + event density, not by mean alone.

---

## Deliverables

At the end of execution, the repository should contain:

- `configs/base.py` additions for liquidation-only 5m research
- `tests/test_liquidation_only_5m_config.py`
- `src/research/liquidation_only_5m/`
- `src/research/liquidation_only_5m/coinalyze_5m.py`
- `tests/research/test_liquidation_only_5m_baseline.py`
- `tests/research/test_liquidation_only_5m_forward_returns.py`
- `tests/scripts/test_probe_liquidation_only_5m_feasibility.py`
- `tests/scripts/test_fetch_liquidation_only_5m_history.py`
- `tests/scripts/test_build_liquidation_only_5m_dataset.py`
- `tests/scripts/test_review_liquidation_only_5m.py`
- `scripts/probe_liquidation_only_5m_feasibility.py`
- `scripts/fetch_liquidation_only_5m_history.py`
- `scripts/build_liquidation_only_5m_dataset.py`
- `scripts/review_liquidation_only_5m.py`
- `docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md`
- `reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_feasibility.json`
- `reports/liquidation_only_5m/2026-05-30_liquidation_only_5m_baseline_summary.json`

---

Plan complete and saved to `docs/plans/2026-05-30-liquidation-only-5m-research-plan.md`. Two execution options:

**1. Subagent-Driven（当前会话）**  
我按这份计划分任务推进，每一批做完都给你复核结论。

**2. Parallel Session（单独会话）**  
你开一个新会话，按 `executing-plans` 技能逐任务落地。
