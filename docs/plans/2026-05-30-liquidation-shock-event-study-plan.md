# Liquidation Shock Event Study Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一条独立于既有 `trend_regime` 与已退役 `liquidation_only_5m` baseline 的 `1m shock -> fixed 5/10/15 minute response` 事件研究链路，用于验证异常单侧 liquidation shock 之后，价格是否存在稳定、可重复、强于随机噪音的方向结构。

**Architecture:** 本计划不再继续优化已退役的 `5m liquidation-only baseline`，而是改做最后一次更干净的 `event study`。事件定义在 `1m liquidation`，response 使用 `1m` 价格构建固定 `5/10/15` 分钟观察窗口，避免标准 `5m` K 线带来的可变延迟偏差；Phase 1 只判断全样本结构是否存在，不直接给出可交易策略结论。

**Tech Stack:** Python 3.11, pytest, ruff, JSON/JSONL, Coinalyze historical liquidation API, Binance 1m OHLCV bars, trailing percentile anomaly scoring, standalone research scripts, markdown review + JSON summary.

---

## Background

当前研究状态已经明确：

- `vol_breakout` 已在 `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md` 中退役。
- 当前版 `liquidation_cascade` 已在 Route B-only 审计中退役，见 `docs/reviews/2026-05-29-trend-liquidation-route-b-coinalyze-review.md`。
- `5m liquidation-only baseline` 已得到 `RETIRE` 结论。它证明：单个 `5m liquidation bar` 的异常 notional 本身，不足以支撑成本后的可执行 edge。
- 这不等于 liquidation 主题本身无效，更可能说明：
  - 事件定义过粗；
  - response 被 `5m` bar 平均掉；
  - 入场时间定义带有可变延迟偏差；
  - 交易方向不应只由单个 `5m` bar 的单侧清算量直接推断。

因此，下一轮研究问题必须收敛为：

- 用 `1m` 定义异常 liquidation shock；
- 用 `1m` 价格构建固定 `5/10/15` 分钟 response 窗口；
- 先判断全样本是否存在稳定方向结构；
- 再决定是否值得进入上下文 edge 或执行可行性研究。

---

## Governance Boundary

本计划应被视为 **liquidation directional alpha 主线的最后一次结构验证**。

如果本计划在更细粒度、更严格时间对齐、更清晰事件定义下，仍然无法证明全样本存在稳定方向结构，则后续应停止继续沿着 liquidation directional alpha 主题做新的粒度/阈值/过滤器变体尝试。

---

## Archive Boundary

以下研究线视为**已归档**，不得继续作为本计划主线增强对象：

- `docs/plans/2026-05-30-liquidation-only-5m-research-plan.md`
- `src/research/liquidation_only_5m/`
- `docs/reviews/2026-05-30-liquidation-only-5m-baseline-review.md`

它们保留作为负结果证据，但不再继续叠加过滤器、调阈值、扩持有期或补 execution 细节。

---

## Scope Boundary

### In Scope For This Plan

- 新建独立 research namespace：`src/research/liquidation_shock_event_study/`
- 先做 `1m` liquidation 数据可得性 + 连续性探针
- 构建 `1m` shock event table
- 事件定义要求：
  - 单侧 liquidation notional 异常
  - `BTC/ETH` vs `SOL/XRP/DOGE` 两层绝对阈值
  - 过去 `24h` 同币种同方向 `1m liquidation` 分布上的相对异常
  - dominance ratio 过滤
  - 同币种同方向固定 `5m` dedup bucket 去重，仅保留 bucket 内最大 shock
- 构建基于 `1m` 价格的固定 response map：
  - entry = `M+1` 分钟 open
  - exits = `M+5 / M+10 / M+15` 分钟 close
- 输出两个方向判定口径：
  - 纯方向符号
  - 方向 + 最小幅度
- 输出方向分布与 bps 分布
- 先只做全样本 response 分析
- 输出 JSON summary 与 markdown review
- review 必须给出 falsification reason / failed checks

### Explicitly Out Of Scope For Phase 1

- OI confirmation
- breakout / return threshold
- funding / premium filter
- orderbook imbalance
- execution simulator
- strategy candidate generation
- live integration
- per-symbol individualized threshold tuning
- context bucket 切分（趋势、波动率、funding、OI）

### Deferred Enhancements (Only If Phase 1 Finds Structure)

- 按事件前 `30m` 趋势方向切分 response
- 按短期波动率状态切分 response
- 加入 OI / funding 作为上下文层，不做前置过滤
- interval clustering / mini-episode 合并替代固定 `5m` dedup bucket
- entry delay / taker cost / slippage 执行敏感性
- majors vs alts 独立 response map

---

## Repository Boundary Rule

1. 本研究不得继续修改或复用 `src/strategies/trend_regime/`。
2. 本研究不得继续把逻辑挂在 `src/research/liquidation_only_5m/` 下。
3. 所有新研究逻辑必须进入：
   - `src/research/liquidation_shock_event_study/`
   - `tests/research/`
   - `scripts/`
4. 如果需要复用 Coinalyze adapter，只能通过独立封装，不得破坏现有 `1h` 与 `5m` baseline 流程。
5. 必须添加回归测试，证明新增 `1m` 研究链路不会修改既有 `1h` Route B / `5m liquidation_only_5m` artifacts 的 schema 或行为。

---

## Required Config Additions

本计划中的新阈值必须进入 `configs/base.py`，至少包括：

- `LIQUIDATION_SHOCK_1M_MAJOR_ABS_THRESHOLD_USDT`
- `LIQUIDATION_SHOCK_1M_ALT_ABS_THRESHOLD_USDT`
- `LIQUIDATION_SHOCK_1M_RELATIVE_SCORE_THRESHOLD`
- `LIQUIDATION_SHOCK_1M_LOOKBACK_HOURS`
- `LIQUIDATION_SHOCK_1M_REQUIRED_REFERENCE_BARS`
- `LIQUIDATION_SHOCK_1M_DOMINANCE_RATIO_MIN`
- `LIQUIDATION_SHOCK_1M_DEDUP_BUCKET_MINUTES`
- `LIQUIDATION_SHOCK_RESPONSE_HORIZONS_MINUTES`
- `LIQUIDATION_SHOCK_DIRECTION_MIN_MOVE_BPS`
- `LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO`
- `LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES`
- `LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS`
- `LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS`
- `LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H`
- `LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT`
- `LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE`
- `LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS`
- `LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS`
- `LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT`
- `LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS`
- `LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS`

这些值在 Phase 1 中仅是 baseline defaults，不代表最终策略参数。

---

## Response Alignment Rule

本计划中 response 的时间对齐必须固定为：

- `shock_bar_start_ms = M`
- `shock_bar_end_ms = M + 60_000`
- `entry_price = open of minute M+1`
- `response_5m_exit = close of minute M+5`
- `response_10m_exit = close of minute M+10`
- `response_15m_exit = close of minute M+15`

禁止用以下任何口径替代：

- 包含 shock minute 的标准 `5m` bar close
- “最近一个完整 5m bar” 但未显式定义 entry/exit
- 事件发生所在 `5m` bar 的 close-to-close 响应

原因：这些口径会把不同 shock 发生分钟映射到不同实际等待时间，导致系统性高估或扭曲 response。

---

## Batch A: 1m Data Feasibility And Contracts

### Task 0: Probe 1m Liquidation Data Depth And Continuity Before Building The Event Study

**Files:**
- Create: `scripts/probe_liquidation_shock_event_study_feasibility.py`
- Create: `tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py`
- Create: `reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_feasibility.json`

**Step 1: Write failing tests for the feasibility probe**

Add tests asserting the probe reports:

- `vendor = coinalyze`
- `interval = 1min`
- `symbols_requested`
- `rows_per_symbol`
- `min_bar_start_ms`
- `max_bar_start_ms`
- `span_hours_per_symbol`
- `expected_1m_bars`
- `actual_1m_bars`
- `coverage_ratio`
- `max_gap_minutes`
- `usable_eval_hours_after_lookback`
- `supports_24h_lookback`
- `qualified_symbols`
- `decision`

Also add failure tests asserting a symbol is not Phase 1 eligible unless all of the following hold:

- `actual_1m_bars >= required_reference_bars + evaluation_bars`
- `coverage_ratio >= LIQUIDATION_SHOCK_FEASIBILITY_MIN_COVERAGE_RATIO`
- `max_gap_minutes <= LIQUIDATION_SHOCK_FEASIBILITY_MAX_GAP_MINUTES`
- `usable_eval_hours_after_lookback >= LIQUIDATION_SHOCK_FEASIBILITY_MIN_EVAL_HOURS`

**Step 2: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py
```
Expected: FAIL.

**Step 3: Implement the feasibility probe**

Allowed decisions:

- `proceed`
- `partial_symbol_support`
- `insufficient_1m_data_depth`
- `api_unavailable`

The probe must prove that the chosen vendor/source can support:

- `24h` trailing anomaly window
- fixed `5m` dedup buckets
- fixed `5/10/15` minute response windows
- at least a modest evaluation window after lookback

**Step 4: Gate the rest of the plan**

Do not continue unless feasibility proves the Phase 1 symbol set is viable, or a reduced symbol set is explicitly approved.

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py
```
Expected: PASS.

**Step 6: Commit**

```bash
git add scripts/probe_liquidation_shock_event_study_feasibility.py tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_feasibility.json
git commit -m "feat: add liquidation shock event study feasibility probe"
```

---

### Task 1: Add Config Constants And Shock Event Contract

**Files:**
- Modify: `configs/base.py`
- Create: `tests/test_liquidation_shock_event_study_config.py`
- Create: `src/research/liquidation_shock_event_study/__init__.py`
- Create: `src/research/liquidation_shock_event_study/event_contract.py`
- Create: `tests/research/test_liquidation_shock_event_contract.py`

**Step 1: Write failing config tests**

Add tests asserting all Phase 1 constants exist and have sane types.

**Step 2: Write failing tests for the shock event contract**

The event contract must distinguish:

- `symbol`
- `shock_bar_start_ms`
- `liquidated_position_side`
- `dominant_liquidation_side`
- `shock_notional_usdt`
- `relative_score`
- `relative_score_method`
- `reference_count`
- `required_reference_count`
- `dominance_ratio`
- `dedup_bucket_start_ms`
- `source_namespace`

Add tests asserting:

- short-liquidation shock maps to an upward-pressure event label
- long-liquidation shock maps to a downward-pressure event label
- mixed bars without sufficient dominance are rejected
- sub-threshold bars are rejected

**Step 3: Run the failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_shock_event_study_config.py \
  tests/research/test_liquidation_shock_event_contract.py
```
Expected: FAIL.

**Step 4: Implement config constants and minimal dataclasses**

Add:

- `LiquidationShock1mThresholds`
- `LiquidationShockEvent`
- minimal event classification helpers

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_shock_event_study_config.py \
  tests/research/test_liquidation_shock_event_contract.py
```
Expected: PASS.

**Step 6: Commit**

```bash
git add configs/base.py tests/test_liquidation_shock_event_study_config.py src/research/liquidation_shock_event_study/__init__.py src/research/liquidation_shock_event_study/event_contract.py tests/research/test_liquidation_shock_event_contract.py
git commit -m "feat: add liquidation shock event study contract"
```

---

## Batch B: 1m Shock Table And Fixed-Horizon Response Map

### Task 2: Add Isolated 1m Liquidation Fetch Path And Base Dataset Builder

**Files:**
- Create: `src/research/liquidation_shock_event_study/coinalyze_1m.py`
- Create: `scripts/fetch_liquidation_shock_1m_history.py`
- Create: `scripts/build_liquidation_shock_event_dataset.py`
- Create: `tests/scripts/test_fetch_liquidation_shock_1m_history.py`
- Create: `tests/scripts/test_build_liquidation_shock_event_dataset.py`
- Modify: `tests/scripts/test_fetch_third_party_liquidation_history.py`

**Step 1: Write failing tests for 1m Coinalyze normalization**

Add tests asserting:

- `normalize_interval("1m") -> "1min"` (or exact vendor-supported interval)
- vendor timestamps are converted from seconds to aligned `bar_start_ms`
- normalized rows preserve:
  - `symbol`
  - `bar_start_ms`
  - `long_liquidation_notional_1m_usdt`
  - `short_liquidation_notional_1m_usdt`
  - `total_liquidation_notional_1m_usdt`
  - `source_namespace = liquidation_shock_event_study`

**Step 2: Add failing tests protecting older artifacts**

Define tests asserting the new `1m` fetch path:

- does not modify existing `1h` Route B normalization behavior
- does not depend on `liquidation_only_5m` namespace
- writes a separate output schema for `1m`

**Step 3: Add failing tests for the base dataset builder**

Define tests asserting the builder:

- joins `1m` liquidation rows with `1m` price rows
- preserves symbol/time alignment
- emits dataset audit counts
- does not silently coerce liquidation gaps into response gaps without audit visibility

**Step 4: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_fetch_liquidation_shock_1m_history.py \
  tests/scripts/test_build_liquidation_shock_event_dataset.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: FAIL.

**Step 5: Implement isolated 1m fetch path**

Required behavior:

- keep all outputs separate from prior 1h/5m baseline artifacts
- preserve older Route B tests and behavior

**Step 6: Implement minimal base dataset builder**

The builder must:

- read normalized `1m` liquidation rows
- read matching `1m` price bars
- write a time-aligned research dataset
- emit join/data-quality audit JSON

**Step 7: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/scripts/test_fetch_liquidation_shock_1m_history.py \
  tests/scripts/test_build_liquidation_shock_event_dataset.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
```
Expected: PASS.

**Step 8: Commit**

```bash
git add src/research/liquidation_shock_event_study/coinalyze_1m.py scripts/fetch_liquidation_shock_1m_history.py scripts/build_liquidation_shock_event_dataset.py tests/scripts/test_fetch_liquidation_shock_1m_history.py tests/scripts/test_build_liquidation_shock_event_dataset.py tests/scripts/test_fetch_third_party_liquidation_history.py
git commit -m "feat: add liquidation shock 1m dataset builder"
```

---

### Task 3: Compute Same-Side Trailing Shock Scores And Order-Invariant Deduplicated Events

**Files:**
- Create: `src/research/liquidation_shock_event_study/shock_detection.py`
- Modify: `scripts/build_liquidation_shock_event_dataset.py`
- Create: `tests/research/test_liquidation_shock_detection.py`

**Step 1: Write failing tests for trailing anomaly and dedup logic**

Add tests asserting:

- anomaly is computed per symbol and per liquidation side, not globally
- the current `1m` bar is excluded from its own trailing reference window
- trailing window length is `24h`
- mixed bars fail dominance filter
- fewer than `required_reference_count = 1440` prior `1m` bars means no event may pass
- dedup is order-invariant within the same fixed `5m` bucket
- only the maximum-notional shock survives within a dedup bucket

**Step 2: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_shock_detection.py
```
Expected: FAIL.

**Step 3: Implement shock detection**

Required behavior:

- compute `relative_score` per symbol and same-side trailing history
- use percentile rank as the baseline method
- exclude current bar from reference window
- require full reference count
- apply major/alt absolute threshold
- apply dominance filter
- deduplicate by:
  - same symbol
  - same liquidated side
  - fixed `5m` dedup bucket
  - keep max-notional shock only

**Step 4: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_shock_detection.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/liquidation_shock_event_study/shock_detection.py scripts/build_liquidation_shock_event_dataset.py tests/research/test_liquidation_shock_detection.py
git commit -m "feat: add liquidation shock detection and dedup"
```

---

### Task 4: Build Fixed 5/10/15 Minute Response Map From 1m Price Bars

**Files:**
- Create: `src/research/liquidation_shock_event_study/response_map.py`
- Create: `tests/research/test_liquidation_shock_response_map.py`

**Step 1: Write failing tests for fixed-horizon response mapping**

Add tests asserting:

- each event maps to fixed forward windows with:
  - `entry = next minute open`
  - `exit_5m = minute M+5 close`
  - `exit_10m = minute M+10 close`
  - `exit_15m = minute M+15 close`
- the response excludes the `5m` bar containing the shock minute as a direct measurement basis
- output contains two direction schemes:
  - sign-only direction
  - sign + minimum move threshold
- events without complete forward horizons are dropped

**Step 2: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_shock_response_map.py
```
Expected: FAIL.

**Step 3: Implement response map builder**

Required outputs per event:

- fixed-horizon response at `5m / 10m / 15m`
- corresponding forward `bps` values
- sign-only direction labels
- minimum-move threshold direction labels
- per-horizon metadata indicating exact entry/exit minute timestamps

**Step 4: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/research/test_liquidation_shock_response_map.py
```
Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/liquidation_shock_event_study/response_map.py tests/research/test_liquidation_shock_response_map.py
git commit -m "feat: add liquidation shock response map"
```

---

## Batch C: Full-Sample Structure Review

### Task 5: Build Full-Sample Event Study Review And Decision Artifacts

**Files:**
- Create: `scripts/review_liquidation_shock_event_study.py`
- Create: `tests/scripts/test_review_liquidation_shock_event_study.py`
- Create: `docs/reviews/2026-05-30-liquidation-shock-event-study-review.md`
- Create: `reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json`

**Step 1: Write failing tests for the review script**

Add tests asserting summary includes:

- `event_count`
- `events_per_24h`
- `symbol_distribution`
- `direction_distribution_by_horizon`
- `minimum_move_filtered_direction_distribution`
- `bps_distribution_by_horizon`
- `directional_bias_by_horizon`
- `median_response_bps_by_horizon`
- `response_consistency`
- `decision`
- `primary_falsification_reason`
- `failed_checks`

**Step 2: Run failing tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_liquidation_shock_event_study.py
```
Expected: FAIL.

**Step 3: Implement review script**

The first-phase review must:

- analyze full-sample response map only
- not yet split by context buckets
- not yet claim tradability
- decide whether the all-sample structure is strong enough to justify Phase 2 context slicing

Allowed top-level decision states:

- `continue_to_context_bucketing`
- `retire_liquidation_shock_event_study`
- `insufficient_1m_data_depth`
- `insufficient_event_density`
- `data_quality_failed`

Required falsification details:

- `primary_falsification_reason`
- `failed_checks`
- `next_action`

**Step 4: Define machine-checkable Phase 1 success criteria**

Phase 1 baseline defaults must be configurable and checked explicitly. At minimum:

- `event_count >= LIQUIDATION_SHOCK_MIN_TOTAL_EVENTS`
- `events_per_24h >= LIQUIDATION_SHOCK_MIN_EVENTS_PER_24H`
- at least `LIQUIDATION_SHOCK_MIN_POSITIVE_SYMBOL_COUNT` symbols with `>= LIQUIDATION_SHOCK_MIN_SYMBOL_EVENTS`
- single-symbol share `<= LIQUIDATION_SHOCK_MAX_SINGLE_SYMBOL_EVENT_SHARE`
- at least `LIQUIDATION_SHOCK_MIN_ADJACENT_HORIZON_PASS_COUNT` adjacent horizons with directional bias `>= LIQUIDATION_SHOCK_MIN_DIRECTIONAL_BIAS`
- minimum-move filtered directional bias `>= LIQUIDATION_SHOCK_MIN_MINMOVE_DIRECTIONAL_BIAS`
- `abs(median_response_bps)` for included horizons `>= LIQUIDATION_SHOCK_MIN_ABS_MEDIAN_RESPONSE_BPS`

This phase is about structure, not net profitability, but it must still record the future tradability evidence needed for Phase 2.

**Step 5: Re-run tests**

Run:
```bash
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_liquidation_shock_event_study.py
```
Expected: PASS.

**Step 6: Generate artifacts from local data**

Write:

- `reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json`
- `docs/reviews/2026-05-30-liquidation-shock-event-study-review.md`

**Step 7: Run full verification including ruff**

Run:
```bash
PYTHONPATH=src uv run pytest -q \
  tests/test_liquidation_shock_event_study_config.py \
  tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py \
  tests/research/test_liquidation_shock_event_contract.py \
  tests/scripts/test_fetch_liquidation_shock_1m_history.py \
  tests/scripts/test_build_liquidation_shock_event_dataset.py \
  tests/research/test_liquidation_shock_detection.py \
  tests/research/test_liquidation_shock_response_map.py \
  tests/scripts/test_review_liquidation_shock_event_study.py \
  tests/scripts/test_fetch_third_party_liquidation_history.py
ruff check src/research tests/research tests/scripts scripts
ruff format --check src/research tests/research tests/scripts scripts
```
Expected: PASS.

**Step 8: Commit**

```bash
git add scripts/review_liquidation_shock_event_study.py tests/scripts/test_review_liquidation_shock_event_study.py docs/reviews/2026-05-30-liquidation-shock-event-study-review.md reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json
git commit -m "feat: add liquidation shock event study review"
```

---

## Success Criteria

Phase 1 may proceed to context bucketing only if all of the following are true:

1. `1m` data depth, continuity, and alignment are sufficient.
2. Event count is large enough to support interpretation under the configured minimums.
3. Full-sample response map shows repeatable directional structure stronger than random noise.
4. That structure persists across adjacent fixed horizons rather than appearing on a single isolated window.
5. Symbol concentration does not dominate the response map.
6. Minimum-move filtered direction results do not collapse relative to sign-only direction.
7. Median response magnitude is not economically trivial even before tradability analysis.

If any of the following holds, Phase 1 should be retired:

- no clear full-sample directional structure
- event density too sparse
- response structure carried mainly by one symbol
- structure disappears immediately under minimum-move filtering
- response magnitude remains too close to zero
- data quality or continuity gaps dominate event construction

---

## Deliverables

At the end of execution, the repository should contain:

- `configs/base.py` additions for shock event study
- `tests/test_liquidation_shock_event_study_config.py`
- `src/research/liquidation_shock_event_study/`
- `src/research/liquidation_shock_event_study/coinalyze_1m.py`
- `src/research/liquidation_shock_event_study/event_contract.py`
- `src/research/liquidation_shock_event_study/shock_detection.py`
- `src/research/liquidation_shock_event_study/response_map.py`
- `tests/research/test_liquidation_shock_event_contract.py`
- `tests/research/test_liquidation_shock_detection.py`
- `tests/research/test_liquidation_shock_response_map.py`
- `tests/scripts/test_probe_liquidation_shock_event_study_feasibility.py`
- `tests/scripts/test_fetch_liquidation_shock_1m_history.py`
- `tests/scripts/test_build_liquidation_shock_event_dataset.py`
- `tests/scripts/test_review_liquidation_shock_event_study.py`
- `scripts/probe_liquidation_shock_event_study_feasibility.py`
- `scripts/fetch_liquidation_shock_1m_history.py`
- `scripts/build_liquidation_shock_event_dataset.py`
- `scripts/review_liquidation_shock_event_study.py`
- `docs/reviews/2026-05-30-liquidation-shock-event-study-review.md`
- `reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_feasibility.json`
- `reports/liquidation_shock_event_study/2026-05-30_liquidation_shock_event_study_summary.json`

---

Plan complete and saved to `docs/plans/2026-05-30-liquidation-shock-event-study-plan.md`. Two execution options:

**1. Subagent-Driven（当前会话）**  
我按这份计划分任务推进，每一批做完都给你复核结论。

**2. Parallel Session（单独会话）**  
你开一个新会话，按 `executing-plans` 技能逐任务落地。

Which approach?
