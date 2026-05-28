# Trend Vol-Breakout Viability Review Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 独立审查 `vol_breakout` 子策略在个人投资者约束下是否值得保留，避免继续把主时间投入到尚未证明有事件密度、资本利用效率和成本后正期望的方向性分支上。

**Architecture:** 不修改 live scanner 默认行为，不调整 `configs/base.py` 现行阈值，不把 `liquidation_cascade` 数据缺口继续作为主线阻塞。新增 `src/research/trend_vol_breakout_viability.py` 承接 research-only classifier、shadow replay 和 sensitivity 审查逻辑；该 research 模块显式接收 `VolBreakoutReviewThresholds`，绝不通过 monkeypatch 或全局状态切换 live 配置。最终 review 只允许三类结论：`retain_for_phase1b_review`、`redefine_thresholds_before_retry`、`retire_vol_breakout_branch`。

**Tech Stack:** Python 3.11, pytest, JSONL historical rows, existing `simulate_trend_regime_shadow(...)`, existing `configs/base.py`, research-only helper module under `src/research/`, reports under `reports/trend_regime/`, review artifact under `docs/reviews/`.

---

## 1. 决策边界

本计划只回答一个问题：

`vol_breakout` 这条子策略，在个人投资者约束下，是否值得继续保留为 Trend / Liquidation Phase 1B 候选主线。

本计划明确不做：

- 不接第三方历史 `liquidation` 数据源。
- 不把 `liquidation_cascade` 数据补齐作为本轮前置条件。
- 不改 `trend-forceorder` 服务器链路；它继续后台采集即可。
- 不修改 `src/strategies/trend_regime/scanner.py` 的 live / watchlist 主路径。
- 不把过去 `498h` 无信号简单解释为“策略已死”；但必须把“是否还值得继续投入”说清楚。
- 不把 `past 1h return` 当成 `expected_edge_bps`。

本计划必须把以下事实写死进 review：

- 当前主 blocker 是 `vol_breakout_below_threshold`，不是 `liquidation_not_confirmed`。
- `vol_breakout` 是独立于 `liquidation_cascade` 的一条子逻辑，应单独审查去留。
- 如果 `vol_breakout` 在更长样本或合理参数审查后仍无事件密度或无成本后正期望，则应优先淘汰该子策略，而不是继续为其补更多数据工程。
- `aggressive_relaxed` 只用于噪音边界诊断，不能直接支持 `redefine` 或 `retain`。

---

## 2. 目标输出

本轮执行完成后，必须产出 3 个可审计 artifact：

1. `reports/trend_regime/2026-05-28_vol_breakout_viability_summary.json`
2. `reports/trend_regime/2026-05-28_vol_breakout_viability_sensitivity.json`
3. `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md`

两个 JSON 报告必须只包含聚合统计数据，不得包含：

- 单条 K 线明细
- `results` 全量交易数组
- 大量逐笔路径记录

如果本地调试需要保留逐笔结果，只允许作为未提交的临时文件，不得进入本计划的 commit 边界。

summary / sensitivity 必须回答：

- 当前阈值下，`vol_breakout` 单独事件数是多少。
- `vol_breakout` 事件按 `symbol / direction / symbol_tier` 的分布。
- 30 bps / 50 bps 成本后，shadow PnL 是否仍为正。
- 主要 blocker 是 `vol_ratio`、`return`、`OI`、`volume` 中哪一个。
- 若放宽参数，仅在多大程度上才出现事件。
- 这种放宽是否超出个人投资者可接受的噪音/滑点/风险边界。
- `time_span_hours` 覆盖了多少小时。
- `events_per_30d` 与 `events_per_symbol_30d` 是否已经低到资本利用效率不可接受。

---

## 3. Files

- Create: `src/research/trend_vol_breakout_viability.py`
- Create: `scripts/review_trend_vol_breakout_viability.py`
- Create: `tests/research/test_trend_vol_breakout_viability.py`
- Create: `tests/scripts/test_review_trend_vol_breakout_viability.py`
- Create: `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md`

---

### Task 1: Add Research-Only Vol-Breakout Classifier Contract

**Files:**
- Create: `src/research/trend_vol_breakout_viability.py`
- Create: `tests/research/test_trend_vol_breakout_viability.py`

**Step 1: Write failing tests for research-only classifier**

Create `tests/research/test_trend_vol_breakout_viability.py` with a single shared `_row(...)` helper inside the file. Do not duplicate row builders across multiple test files unless fields differ materially.

Required tests:

```python
from src.research.trend_vol_breakout_viability import (
    VolBreakoutReviewThresholds,
    classify_vol_breakout_only_for_review,
)


def test_vol_breakout_accepts_long_continuation_with_positive_oi():
    result = classify_vol_breakout_only_for_review(_row())
    assert result.event is not None
    assert result.event.regime == "vol_breakout_long"


def test_vol_breakout_accepts_short_continuation_with_positive_oi():
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=-2.5, oi_change_1h_pct=3.0)
    )
    assert result.event is not None
    assert result.event.regime == "vol_breakout_short"


def test_vol_breakout_rejects_negative_oi_as_not_breakout_continuation():
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=-2.5, oi_change_1h_pct=-3.0)
    )
    assert result.event is None
    assert result.reject_reason == "oi_not_positive_for_vol_breakout"


def test_vol_breakout_reports_same_primary_breakout_gate():
    result = classify_vol_breakout_only_for_review(
        _row(vol_1h_pct=1.5, vol_baseline_30d_pct=1.0)
    )
    assert result.event is None
    assert result.reject_reason == "vol_breakout_below_threshold"


def test_vol_breakout_classifier_never_uses_liquidation_notional():
    low = classify_vol_breakout_only_for_review(_row(liquidation_notional_1h_usdt=0.0))
    high = classify_vol_breakout_only_for_review(_row(liquidation_notional_1h_usdt=999_999_999.0))
    assert low == high


def test_vol_breakout_classifier_accepts_explicit_threshold_overrides():
    thresholds = VolBreakoutReviewThresholds(
        name="custom",
        vol_multiplier=2.0,
        major_min_return_pct=1.5,
        large_alt_min_return_pct=2.0,
        major_min_oi_pct=1.0,
        large_alt_min_oi_pct=1.5,
        assumption_level="moderately_relaxed",
        eligible_for_redefinition=True,
    )
    result = classify_vol_breakout_only_for_review(
        _row(return_1h_pct=1.6, vol_1h_pct=2.1, vol_baseline_30d_pct=1.0, oi_change_1h_pct=1.1),
        thresholds=thresholds,
    )
    assert result.event is not None
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/research/test_trend_vol_breakout_viability.py
```

Expected: FAIL because module does not exist.

**Step 3: Implement research-only classifier**

Create `src/research/trend_vol_breakout_viability.py` with:

```python
@dataclass(frozen=True)
class VolBreakoutReviewThresholds:
    name: str
    vol_multiplier: float
    major_min_return_pct: float
    large_alt_min_return_pct: float
    major_min_oi_pct: float
    large_alt_min_oi_pct: float
    assumption_level: str
    eligible_for_redefinition: bool
```

and:

```python
def classify_vol_breakout_only_for_review(
    row: dict[str, Any],
    *,
    thresholds: VolBreakoutReviewThresholds | None = None,
) -> TrendRegimeClassification:
    ...
```

Requirements:

- Must live under `src/research/`, not `src/strategies/trend_regime/scanner.py`.
- If `thresholds is None`, use current baseline values from `configs/base.py`.
- Do not monkeypatch or mutate `configs/base.py`.
- Reuse current live semantics for:
  - `symbol` in watchlist
  - `data_age_sec`
  - `volume_24h_usdt`
  - `return_1h_pct`
  - `vol_1h_pct`
  - `vol_baseline_30d_pct`
  - `estimated_slippage_bps`
- `vol_breakout` direction semantics must be:
  - `return_1h_pct > 0` and `oi_change_1h_pct >= min_oi_pct` -> `vol_breakout_long`
  - `return_1h_pct < 0` and `oi_change_1h_pct >= min_oi_pct` -> `vol_breakout_short`
- If `abs(oi_change_1h_pct) < min_oi_pct`, reject with `oi_confirmation_below_min`.
- If `oi_change_1h_pct <= 0.0` while `abs(oi_change_1h_pct) >= min_oi_pct`, reject with `oi_not_positive_for_vol_breakout`.
- Never read `liquidation_notional_1h_usdt`.
- Never output or imply `expected_edge_bps`.

**Step 4: Run tests to verify it passes**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/research/test_trend_vol_breakout_viability.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/research/trend_vol_breakout_viability.py tests/research/test_trend_vol_breakout_viability.py
git commit -m "test: add research-only vol breakout classifier contract"
```

---

### Task 2: Add Research-Only Replay Summary

**Files:**
- Create: `scripts/review_trend_vol_breakout_viability.py`
- Create: `tests/scripts/test_review_trend_vol_breakout_viability.py`

**Step 1: Write failing summary tests**

Create `tests/scripts/test_review_trend_vol_breakout_viability.py`.

This file may define its own `_row(...)` helper if needed for replay-specific fields (`close_price`, `timestamp_ms`, path rows). Keep one shared helper per file; avoid repeated row builders inside the same file.

Required tests:

```python
from scripts.review_trend_vol_breakout_viability import (
    build_vol_breakout_audit_summary,
    build_vol_breakout_shadow_summary,
)


def test_vol_breakout_audit_summary_counts_only_breakout_events():
    rows = [
        _row(symbol="BTC/USDT"),
        _row(symbol="ETH/USDT", vol_1h_pct=1.0, vol_baseline_30d_pct=1.0),
    ]

    summary = build_vol_breakout_audit_summary(rows)

    assert summary["input_row_count"] == 2
    assert summary["entry_event_count"] == 1
    assert summary["entry_event_count_by_regime"] == {"vol_breakout_long": 1}
    assert summary["classification_reject_counts"]["vol_breakout_below_threshold"] == 1


def test_vol_breakout_shadow_summary_uses_only_accepted_breakout_entries():
    rows = [
        _row(timestamp_ms=1000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
        _row(timestamp_ms=3000, symbol="ETH/USDT", close_price=100.0, vol_1h_pct=1.0),
    ]

    summary = build_vol_breakout_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12)

    assert summary["entry_event_count"] == 1
    assert summary["shadow_trade_count"] == 1
    assert summary["holding_hours"] == 12


def test_shadow_path_uses_same_symbol_and_future_only():
    rows = [
        _row(timestamp_ms=2000, symbol="BTC/USDT", close_price=100000.0),
        _row(timestamp_ms=1500, symbol="BTC/USDT", close_price=90000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        _row(timestamp_ms=2500, symbol="BTC/USDT", close_price=101000.0, return_1h_pct=0.1, vol_1h_pct=1.0),
        _row(timestamp_ms=2600, symbol="ETH/USDT", close_price=110.0, return_1h_pct=0.1, vol_1h_pct=1.0),
    ]

    summary = build_vol_breakout_shadow_summary(rows, estimated_cost_bps=30.0, holding_hours=12)

    assert summary["shadow_trade_count"] == 1
    assert summary["accepted_entries_with_path_count"] == 1


def test_shadow_trade_count_never_exceeds_entry_event_count():
    summary = build_vol_breakout_shadow_summary([_row()], estimated_cost_bps=30.0, holding_hours=12)
    assert summary["shadow_trade_count"] <= summary["entry_event_count"]
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_vol_breakout_viability.py
```

Expected: FAIL because script does not exist.

**Step 3: Implement replay summary script**

Create `scripts/review_trend_vol_breakout_viability.py` with:

- `load_rows_jsonl(path: str | Path) -> list[dict[str, Any]]`
- `build_vol_breakout_audit_summary(...)`
- `build_vol_breakout_shadow_summary(..., holding_hours: int)`
- `build_dual_cost_viability_summary(...)`
- `main()`

Implementation requirements:

- Reuse the stale-row normalization pattern from `scripts/replay_trend_regime_shadow.py`.
- Use `classify_vol_breakout_only_for_review(...)`, not the mixed live classifier.
- Shadow simulation must use only accepted breakout entries.
- Future path must be:
  - same symbol
  - `timestamp_ms > entry_time_ms`
- Summary must include:

```json
{
  "input_row_count": 0,
  "symbol_count": 0,
  "symbols": [],
  "time_span_hours": 0.0,
  "entry_event_count": 0,
  "entry_event_count_by_symbol": {},
  "entry_event_count_by_regime": {},
  "classification_reject_counts": {},
  "reject_counts_by_symbol": {},
  "events_per_30d": 0.0,
  "events_per_symbol_30d": {},
  "capital_utilization_label": "too_sparse",
  "holding_hours": 12,
  "shadow_trade_count": 0,
  "accepted_entries_with_path_count": 0,
  "mean_net_pnl_bps": 0.0,
  "median_net_pnl_bps": 0.0,
  "win_rate": 0.0,
  "worst_trade_net_pnl_bps": 0.0,
  "stop_loss_exit_rate": 0.0,
  "coverage_quality": "historical_rows_replay_not_live_freshness_aware",
  "strategy_slice": "vol_breakout_only",
  "edge_status": "unknown_until_shadow"
}
```

- Do not include a `results` array in the committed summary JSON.

**Step 4: Run tests**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_review_trend_vol_breakout_viability.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/review_trend_vol_breakout_viability.py tests/scripts/test_review_trend_vol_breakout_viability.py
git commit -m "feat: add vol breakout viability replay summary"
```

---

### Task 3: Add Explicit Threshold Sensitivity And Holding Horizon Audit

**Files:**
- Modify: `src/research/trend_vol_breakout_viability.py`
- Modify: `scripts/review_trend_vol_breakout_viability.py`
- Modify: `tests/research/test_trend_vol_breakout_viability.py`
- Modify: `tests/scripts/test_review_trend_vol_breakout_viability.py`

**Step 1: Write failing sensitivity tests**

Extend `tests/scripts/test_review_trend_vol_breakout_viability.py`:

```python
from scripts.review_trend_vol_breakout_viability import run_vol_breakout_sensitivity
from src.research.trend_vol_breakout_viability import VolBreakoutReviewThresholds


def test_vol_breakout_sensitivity_reports_baseline_moderate_and_aggressive_sets():
    rows = [
        _row(symbol="BTC/USDT", return_1h_pct=2.2, vol_1h_pct=2.7, vol_baseline_30d_pct=1.0, oi_change_1h_pct=1.8),
        _row(symbol="BTC/USDT", timestamp_ms=2000, close_price=101000.0, return_1h_pct=0.2, vol_1h_pct=1.0),
    ]

    summaries = run_vol_breakout_sensitivity(
        rows,
        threshold_sets=[
            VolBreakoutReviewThresholds.baseline_current(),
            VolBreakoutReviewThresholds.moderately_relaxed(),
            VolBreakoutReviewThresholds.aggressive_relaxed(),
        ],
    )

    assert [item["threshold_set_name"] for item in summaries] == [
        "baseline_current",
        "moderately_relaxed",
        "aggressive_relaxed",
    ]
    assert summaries[2]["assumption_level"] == "diagnostic_noise_boundary"
    assert summaries[2]["eligible_for_redefinition"] is False


def test_sensitivity_does_not_mutate_live_config_thresholds():
    before = classify_vol_breakout_only_for_review(_row())
    run_vol_breakout_sensitivity([_row()], threshold_sets=[VolBreakoutReviewThresholds.moderately_relaxed()])
    after = classify_vol_breakout_only_for_review(_row())
    assert before == after
```

**Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/research/test_trend_vol_breakout_viability.py tests/scripts/test_review_trend_vol_breakout_viability.py
```

Expected: FAIL on missing threshold presets or sensitivity output fields.

**Step 3: Implement explicit threshold presets**

In `src/research/trend_vol_breakout_viability.py`, add classmethods:

```python
VolBreakoutReviewThresholds.baseline_current()
VolBreakoutReviewThresholds.moderately_relaxed()
VolBreakoutReviewThresholds.aggressive_relaxed()
```

Use:

```python
baseline_current = (2.5, 2.0, 2.5, 1.5, 2.0)
moderately_relaxed = (2.0, 1.5, 2.0, 1.0, 1.5)
aggressive_relaxed = (1.8, 1.2, 1.8, 0.8, 1.2)
```

Metadata requirements:

- `baseline_current.assumption_level = "current_live_baseline"`
- `moderately_relaxed.assumption_level = "candidate_redefinition_boundary"`
- `aggressive_relaxed.assumption_level = "diagnostic_noise_boundary"`
- `aggressive_relaxed.eligible_for_redefinition = False`

**Step 4: Add holding horizon audit**

In `scripts/review_trend_vol_breakout_viability.py`, `build_dual_cost_viability_summary(...)` must output:

```json
{
  "shadow_by_holding_hours": {
    "4": {...},
    "8": {...},
    "12": {...},
    "24": {...}
  }
}
```

Each holding bucket must have both:

- `base_cost_bps = 30.0`
- `stress_cost_bps = 50.0`

and aggregated fields only:

- `entry_event_count`
- `shadow_trade_count`
- `median_net_pnl_bps`
- `mean_net_pnl_bps`
- `win_rate`
- `worst_trade_net_pnl_bps`
- `stop_loss_exit_rate`

**Step 5: Run tests**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/research/test_trend_vol_breakout_viability.py tests/scripts/test_review_trend_vol_breakout_viability.py
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/research/trend_vol_breakout_viability.py scripts/review_trend_vol_breakout_viability.py tests/research/test_trend_vol_breakout_viability.py tests/scripts/test_review_trend_vol_breakout_viability.py
git commit -m "feat: add explicit vol breakout sensitivity and holding audit"
```

---

### Task 4: Generate Aggregated Viability Review Artifacts

**Files:**
- Create: `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md`
- Modify: `scripts/review_trend_vol_breakout_viability.py`

**Step 1: Run review script on existing historical rows**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/review_trend_vol_breakout_viability.py \
  --input data/trend_regime_historical_rows.jsonl \
  --summary-output reports/trend_regime/2026-05-28_vol_breakout_viability_summary.json \
  --sensitivity-output reports/trend_regime/2026-05-28_vol_breakout_viability_sensitivity.json
```

Expected:

- script exits `0`
- two report files created
- both files contain aggregated statistics only

**Step 2: Write review document**

Create `docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md` with these required sections:

1. `范围声明`
2. `历史覆盖与样本边界`
3. `当前阈值下事件密度`
4. `当前阈值下成本后 shadow 结果`
5. `主要 blocker 分布`
6. `参数放宽后的变化`
7. `holding horizon 敏感性`
8. `个人投资者视角的资本利用效率评价`
9. `最终结论`

Review must explicitly answer:

- `time_span_hours` 是否达到 `720h`
- baseline 下 `entry_event_count` 是否为 `0`
- `events_per_30d` 是否低到资本利用效率不可接受
- `moderately_relaxed` 是否开始出现事件
- 如果只有 `aggressive_relaxed` 才有事件，是否应视为噪音追逐
- 30 bps / 50 bps 后是否仍有稳定正期望
- `4h / 8h / 12h / 24h` 哪个 horizon 最稳定
- long / short、major / large_alt 分组是否有单独成立的子类

**Step 3: Enforce final decision gate**

Review 只允许以下三种结论之一：

1. `retain_for_phase1b_review`
2. `redefine_thresholds_before_retry`
3. `retire_vol_breakout_branch`

`retain_for_phase1b_review` 必须同时满足：

- `time_span_hours >= 720`
- `baseline_current.entry_event_count >= 10`
- `baseline_current.events_per_30d >= 10`
- `baseline_current.median_net_pnl_bps > 30`
- `baseline_current.win_rate > 0.55`
- `baseline_current.worst_trade_net_pnl_bps > -200`
- `stress_cost_50bps.median_net_pnl_bps > 0`
- `stop_loss_exit_rate < 0.35`
- 至少一个 `symbol_tier x direction` 分组不是单一 symbol 撑起

`redefine_thresholds_before_retry`：

- `time_span_hours >= 720`
- baseline 太严无事件；
- `moderately_relaxed` 开始出现事件；
- 但成本后结果仍不稳、样本过少，或资本利用效率仍偏弱；
- 且 `moderately_relaxed` 仍未进入明显噪音区

`retire_vol_breakout_branch`：

- `time_span_hours < 720` 且无法补足覆盖，只能停留在 `insufficient_time_coverage`；
- 或 baseline 无事件且只有 `aggressive_relaxed` 才有事件；
- 或放宽后仍无稳定正期望；
- 或事件密度对个人投资者而言过低，资本利用效率过差

默认倾向必须是保守的：除非 baseline 或 moderate 给出强证据，否则不要保留。

**Step 4: Placeholder check**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
rg -n "TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md
```

Expected: no output.

**Step 5: Commit**

只提交聚合 JSON 和 review，不提交任何明细结果：

```bash
git add \
  reports/trend_regime/2026-05-28_vol_breakout_viability_summary.json \
  reports/trend_regime/2026-05-28_vol_breakout_viability_sensitivity.json \
  docs/reviews/2026-05-28-trend-vol-breakout-viability-review.md
git commit -m "docs: add vol breakout viability review artifacts"
```

---

## 4. 执行顺序建议

按 3 批执行，不要一口气做到 review。

### Batch A：Research classifier，不碰 live scanner

执行：

- Task 1

通过标准：

- research-only classifier 位于 `src/research/`
- long / short 都有测试
- 不使用 `liquidation_notional_1h_usdt`
- 不输出 `expected_edge_bps`
- thresholds 显式传入

### Batch B：Replay + Sensitivity

执行：

- Task 2
- Task 3

通过标准：

- shadow 只使用 accepted entries
- future path 同 symbol 且 `timestamp_ms > entry_time_ms`
- baseline / moderate / aggressive 三组都有 summary
- 30 bps / 50 bps 双成本
- `4h / 8h / 12h / 24h` holding horizon 全部有聚合结果
- 配置不会被 sensitivity 污染

### Batch C：Review

执行：

- Task 4

通过标准：

- review 明确给出 `retain / redefine / retire`
- 结论基于 `time_span_hours`、`events_per_30d`、双成本、holding horizon、long/short 和 symbol tier 分组
- `aggressive_relaxed` 明确只作为噪音边界诊断

---

## 5. 预期结论范围

基于当前已有证据，最可能出现的不是 `retain_for_phase1b_review`，而是以下两种之一：

1. `redefine_thresholds_before_retry`
2. `retire_vol_breakout_branch`

如果最终是 `retire_vol_breakout_branch`，下一步不应再继续为 `vol_breakout` 分支补更多数据工程，而应：

- 保留 `trend-forceorder` 后台采集；
- 单独讨论 `liquidation_cascade` 是否值得作为独立子策略；
- 或直接把 Trend / Liquidation Phase 1A 降级为低优先级研究项。

如果最终是 `redefine_thresholds_before_retry`，下一步计划必须单独写：

- 哪些阈值允许调整；
- 调整上限是什么；
- 为什么这种放宽仍然符合“个人投资者保守方向性策略”的定义；
- 放宽后需要重新跑哪段历史窗口验证。

---

## 6. 完成定义

本计划完成后，必须做到：

- `vol_breakout` 与 `liquidation_cascade` 在研究审查层明确拆分；
- `vol_breakout` 的事件密度、资本利用效率、成本后收益、主要 blocker、参数敏感性都可审计；
- review 对“是否保留该子策略”给出明确结论；
- `trend-forceorder` 72h 等待不再阻塞项目主线。

