# Trend / Liquidation Historical Replay Revision Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修订 `Trend / Liquidation` 的历史回放链路，使 Phase 1A 可以不依赖 live 极端行情，也能用历史 rows 完成分类诊断与 dual-cost shadow 验证。

**Architecture:** 保持 live scanner 语义不变，`api_stale` 仍只用于实时观察保护；历史回放只在 replay 边界内显式做 freshness normalization，并输出可审计的 reject summary、coverage summary、base/stress cost shadow summary。历史行情行继续由现有 `build_trend_regime_market_rows.py` 生成，不在本轮把 replay 特殊语义反向写回 live rows builder。

**Tech Stack:** Python 3.11, pytest, dataclasses, existing `classify_trend_regime_snapshot(...)`, existing `simulate_trend_regime_shadow(...)`, JSONL rows under `data/`, replay reports under `reports/trend_regime/`, review artifacts under `docs/reviews/`.

---

## 1. Review Adoption Summary

本计划采纳并修正以下外部审计意见：

- 采纳：历史回放直接复用 live classifier 会被 `data_age_sec` / `api_stale` 误拦截，必须修 replay 边界。
- 采纳：历史回放不能只给出 `shadow_trade_count=0`，必须能解释主 blocker 是 `vol_breakout_below_threshold`、`return_below_min`、`oi_confirmation_below_min` 还是 `liquidation_not_confirmed`。
- 采纳：不能只等 live 市场配合，应立即使用更长历史窗口和更大 symbol 覆盖推进 Phase 1A 证据积累。
- 部分采纳：外部审计把“无信号”归因为 OI 不足，这只能在 `liquidation` 覆盖完整时成立；如果历史 rows 仍缺 `liquidation_notional_1h_usdt`，review 必须显式标注 coverage gap。
- 不采纳：`shadow_trade_count > 10` 且 `20 bps` 后均值为正即可通过。这与当前项目 Phase 1A gate 冲突。本轮仍沿用 `30 bps` / `50 bps` 与既有 review gate。

---

## 2. Boundary And Decision Rules

本计划只修 **历史回放推进能力**，不做以下事情：

- 不修改 live watchlist 的 `api_stale` 判定。
- 不降低当前 live 观察阈值。
- 不把历史 replay 结果解释为 live-ready。
- 不把 `liquidation_notional_1h_usdt` 缺失的样本误判为“市场不存在 liquidation cascade”。

本计划完成后必须能回答：

- 历史 replay 中，去除 stale 干扰后，真实主拒绝原因是什么。
- 在当前 `2.5x vol ratio + 2.0/2.5% return + 1.5/2.0% OI` 门槛下，历史上是否有足够多的 entry event。
- 在 `30 bps` base cost 和 `50 bps` stress cost 下，shadow 结果是否满足现有 Phase 1A review gate。
- 如果仍然不满足，是“策略定义过严”还是“策略本身缺乏 edge”。

---

## 3. Files

- Modify: `scripts/replay_trend_regime_shadow.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`
- Modify: `tests/strategies/test_trend_regime_scanner.py`
- Create: `docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md`
- Reuse (no code change expected): `scripts/build_trend_regime_market_rows.py`

---

## 4. Replay Contract

历史回放输入仍使用现有 raw rows 格式，不新增专用 schema：

```python
{
    "timestamp_ms": 1710000000000,
    "exchange": "binance",
    "symbol": "BTC/USDT",
    "close_price": 100000.0,
    "return_1h_pct": -2.4,
    "vol_1h_pct": 2.4,
    "vol_baseline_30d_pct": 0.7,
    "open_interest": 100000000.0,
    "oi_change_1h_pct": -1.8,
    "liquidation_notional_1h_usdt": None,
    "volume_24h_usdt": 12000000000.0,
    "estimated_spread_bps": 3.0,
    "estimated_slippage_bps": 2.0,
    "funding_state": "neutral",
    "data_age_sec": 86400.0,
}
```

历史 replay 语义：

- `data_age_sec` 在 replay normalization 后强制视为 `0.0`。
- normalization 只发生在 `replay_trend_regime_shadow.py` 内部，不回写原始 JSONL。
- replay summary 必须输出：
  - `historical_mode`
  - `historical_freshness_normalized_count`
  - `rows_originally_api_stale_count`
  - `classification_reject_counts`
  - `input_row_count`
  - `symbol_count`
  - `symbols`
  - `start_timestamp_ms`
  - `end_timestamp_ms`
  - `time_span_hours`
  - `entry_event_count_by_symbol`
  - `entry_event_count_by_regime`
  - `reject_counts_by_symbol`
  - `rows_missing_liquidation_notional_count`
  - `rows_with_liquidation_notional_count`
  - `liquidation_coverage_ratio`
  - `coverage_quality`

---

### Task 1: Add Historical Replay Contract Tests

**Files:**
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`
- Modify: `tests/strategies/test_trend_regime_scanner.py`

- [ ] **Step 1: Write failing replay test for stale historical rows**

Add to `tests/scripts/test_replay_trend_regime_shadow.py`:

```python
def test_historical_replay_normalizes_stale_rows_before_classification():
    rows = [
        _row(timestamp_ms=1000, data_age_sec=999999.0, close_price=100000.0),
        _row(
            timestamp_ms=2000,
            data_age_sec=999999.0,
            close_price=101000.0,
            return_1h_pct=2.4,
            vol_1h_pct=2.8,
            vol_baseline_30d_pct=1.0,
            oi_change_1h_pct=2.0,
            volume_24h_usdt=30_000_000_000.0,
            estimated_slippage_bps=2.0,
        ),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["historical_mode"] is True
    assert summary["historical_freshness_normalized_count"] == 2
    assert summary["rows_originally_api_stale_count"] == 2
    assert summary["entry_event_count"] == 1
```

- [ ] **Step 2: Write failing replay test for reject diagnostics**

Add:

```python
def test_historical_replay_outputs_classification_reject_counts():
    rows = [
        _row(timestamp_ms=1000, vol_1h_pct=1.0, vol_baseline_30d_pct=1.0),
        _row(timestamp_ms=2000, return_1h_pct=0.5),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert "classification_reject_counts" in summary
    assert "vol_breakout_below_threshold" in summary["classification_reject_counts"]
```

- [ ] **Step 3: Write failing replay test for liquidation coverage summary**

Add:

```python
def test_historical_replay_reports_liquidation_coverage_gap():
    rows = [
        _row(timestamp_ms=1000, liquidation_notional_1h_usdt=None),
        _row(timestamp_ms=2000, liquidation_notional_1h_usdt=4_000_000.0),
    ]

    summary = build_shadow_summary(rows, estimated_cost_bps=TREND_REGIME_OBSERVATION_COST_BPS)

    assert summary["rows_missing_liquidation_notional_count"] == 1
    assert summary["rows_with_liquidation_notional_count"] == 1
```

- [ ] **Step 4: Lock live scanner semantics**

Add to `tests/strategies/test_trend_regime_scanner.py`:

```python
def test_live_scanner_still_rejects_stale_rows():
    stale = classify_trend_regime_snapshot(_snapshot(data_age_sec=999999.0))
    assert stale.reject_reason == "api_stale"
```

- [ ] **Step 5: Run tests to verify failure**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_replay_trend_regime_shadow.py tests/strategies/test_trend_regime_scanner.py
```

Expected: FAIL because replay summary does not yet expose historical-mode normalization and reject diagnostics.

- [ ] **Step 6: Commit**

```bash
git add tests/scripts/test_replay_trend_regime_shadow.py tests/strategies/test_trend_regime_scanner.py
git commit -m "test: define trend historical replay contract"
```

---

### Task 2: Implement Replay Normalization And Diagnostics

**Files:**
- Modify: `scripts/replay_trend_regime_shadow.py`
- Modify: `tests/scripts/test_replay_trend_regime_shadow.py`

- [ ] **Step 1: Add replay-only normalization helper**

In `scripts/replay_trend_regime_shadow.py`, add:

```python
def normalize_rows_for_historical_replay(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    normalized: list[dict[str, Any]] = []
    rows_originally_api_stale_count = 0

    for row in rows:
        patched = dict(row)
        value = _number_or_none(row.get("data_age_sec"))
        if value is None or value > TREND_REGIME_MAX_DATA_AGE_SEC:
            rows_originally_api_stale_count += 1
        patched["data_age_sec"] = 0.0
        normalized.append(patched)

    return normalized, rows_originally_api_stale_count
```

- [ ] **Step 2: Add classification audit summary helper**

Add:

```python
def build_classification_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reject_counts: dict[str, int] = defaultdict(int)
    reject_counts_by_symbol: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    entry_event_count = 0
    entry_event_count_by_symbol: dict[str, int] = defaultdict(int)
    entry_event_count_by_regime: dict[str, int] = defaultdict(int)
    rows_missing_liquidation_notional_count = 0
    rows_with_liquidation_notional_count = 0

    for row in rows:
        liquidation_notional = _number_or_none(row.get("liquidation_notional_1h_usdt"))
        if liquidation_notional is None:
            rows_missing_liquidation_notional_count += 1
        else:
            rows_with_liquidation_notional_count += 1

        classification = classify_trend_regime_snapshot(row)
        if classification.event is None:
            reject_reason = str(classification.reject_reason or "unknown")
            reject_counts[reject_reason] += 1
            reject_counts_by_symbol[str(row.get("symbol") or "unknown")][reject_reason] += 1
            continue
        entry_event_count += 1
        entry_event_count_by_symbol[str(row.get("symbol") or "unknown")] += 1
        entry_event_count_by_regime[str(classification.event.regime)] += 1

    return {
        "entry_event_count": entry_event_count,
        "entry_event_count_by_symbol": dict(entry_event_count_by_symbol),
        "entry_event_count_by_regime": dict(entry_event_count_by_regime),
        "classification_reject_counts": dict(reject_counts),
        "reject_counts_by_symbol": {key: dict(value) for key, value in reject_counts_by_symbol.items()},
        "rows_missing_liquidation_notional_count": rows_missing_liquidation_notional_count,
        "rows_with_liquidation_notional_count": rows_with_liquidation_notional_count,
        "liquidation_coverage_ratio": (
            rows_with_liquidation_notional_count / len(rows) if rows else 0.0
        ),
    }
```

- [ ] **Step 3: Make `build_shadow_summary(...)` historical by default**

Update `build_shadow_summary(...)` to:

```python
normalized_rows, rows_originally_api_stale_count = normalize_rows_for_historical_replay(rows)
audit = build_classification_audit(normalized_rows)

for index, row in enumerate(normalized_rows):
    classification = classify_trend_regime_snapshot(row)
```

And extend the returned summary with:

```python
{
    "historical_mode": True,
    "historical_freshness_normalized_count": len(normalized_rows),
    "rows_originally_api_stale_count": rows_originally_api_stale_count,
    "input_row_count": len(normalized_rows),
    "symbol_count": len({str(row.get("symbol") or "") for row in normalized_rows if row.get("symbol")}),
    "symbols": sorted({str(row.get("symbol") or "") for row in normalized_rows if row.get("symbol")}),
    "start_timestamp_ms": min(int(_number_or_none(row.get("timestamp_ms")) or 0) for row in normalized_rows),
    "end_timestamp_ms": max(int(_number_or_none(row.get("timestamp_ms")) or 0) for row in normalized_rows),
    "time_span_hours": (
        (
            max(int(_number_or_none(row.get("timestamp_ms")) or 0) for row in normalized_rows)
            - min(int(_number_or_none(row.get("timestamp_ms")) or 0) for row in normalized_rows)
        ) / 3_600_000.0
        if normalized_rows
        else 0.0
    ),
    "entry_event_count_by_symbol": audit["entry_event_count_by_symbol"],
    "entry_event_count_by_regime": audit["entry_event_count_by_regime"],
    "classification_reject_counts": audit["classification_reject_counts"],
    "reject_counts_by_symbol": audit["reject_counts_by_symbol"],
    "rows_missing_liquidation_notional_count": audit["rows_missing_liquidation_notional_count"],
    "rows_with_liquidation_notional_count": audit["rows_with_liquidation_notional_count"],
    "liquidation_coverage_ratio": audit["liquidation_coverage_ratio"],
    "coverage_quality": "historical_rows_replay_not_live_freshness_aware",
}
```

- [ ] **Step 4: Keep dual-cost summary compatible**

`build_dual_cost_summary(...)` must continue returning:

```python
{
    "base_cost_bps": 30.0,
    "stress_cost_bps": 50.0,
    "base": {...},
    "stress": {...},
}
```

No schema break for existing downstream review scripts except added fields.

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run pytest -q tests/scripts/test_replay_trend_regime_shadow.py tests/strategies/test_trend_regime_scanner.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/replay_trend_regime_shadow.py tests/scripts/test_replay_trend_regime_shadow.py tests/strategies/test_trend_regime_scanner.py
git commit -m "feat: normalize stale rows in trend historical replay"
```

---

### Task 3: Define Historical Dataset Run Boundary

**Files:**
- Reuse: `scripts/build_trend_regime_market_rows.py`
- Create: `docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md`

- [ ] **Step 1: Use existing rows builder for expanded history**

Do not add a new builder script. Reuse existing CLI:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/build_trend_regime_market_rows.py \
  --output data/trend_regime_historical_rows.jsonl \
  --symbols BTC/USDT ETH/USDT SOL/USDT XRP/USDT DOGE/USDT ADA/USDT \
  --kline-limit 1500 \
  --oi-limit 1500 \
  --max-iterations 1
```

Expected: one-shot historical rows file with larger time depth than current live dataset.

- [ ] **Step 2: Verify historical rows were generated**

Run:

```bash
wc -l data/trend_regime_historical_rows.jsonl
python3 - <<'PY'
import json
from pathlib import Path
path = Path("data/trend_regime_historical_rows.jsonl")
rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
print(len(rows))
print(rows[0]["timestamp_ms"], rows[-1]["timestamp_ms"])
print(sorted({row["symbol"] for row in rows}))
print("kline_interval", "1h")
print("time_span_hours", (rows[-1]["timestamp_ms"] - rows[0]["timestamp_ms"]) / 3_600_000)
PY
```

Expected: non-zero rows across multiple symbols and longer historical span.

- [ ] **Step 3: Enforce minimum historical span**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
python3 - <<'PY'
import json
from pathlib import Path
rows = [json.loads(x) for x in Path("data/trend_regime_historical_rows.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
span_hours = (rows[-1]["timestamp_ms"] - rows[0]["timestamp_ms"]) / 3_600_000 if rows else 0.0
print(span_hours)
raise SystemExit(0 if span_hours >= 720 else 2)
PY
```

Expected: exit code `0`. If below `720h`（30 天）, this run is only a smoke replay and cannot be used for strategy validity conclusions.

- [ ] **Step 4: Commit**

No code changes expected here. Skip commit if only generated data artifacts are produced locally.

---

### Task 4: Run Historical Replay And Write Review Artifact

**Files:**
- Modify: `scripts/replay_trend_regime_shadow.py` (already done in Task 2)
- Create: `docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md`

- [ ] **Step 1: Run historical replay on expanded dataset**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
PYTHONPATH=src uv run python scripts/replay_trend_regime_shadow.py \
  --input data/trend_regime_historical_rows.jsonl \
  --output reports/trend_regime/2026-05-27_historical_replay_dual_cost_summary.json
```

Expected: summary JSON exists and includes historical-mode diagnostics plus base/stress cost results.

- [ ] **Step 2: Write review artifact with real JSON excerpts**

Create `docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md` with:

- input coverage (`row_count`, time span, symbols)
- `classification_reject_counts`
- `rows_missing_liquidation_notional_count`
- `rows_with_liquidation_notional_count`
- base cost replay summary
- stress cost replay summary
- explicit conclusion: one of
  - `keep_observation_only`
  - `redefine_thresholds_before_phase1b`
  - `eligible_for_phase1b_review`

Review first paragraph must explicitly state:

```markdown
本轮 historical replay 只解决“历史推进能力”和“主 blocker 诊断”问题，
不等于 live-ready，不等于 execution-ready。
```

Review must also include:

- `kline_interval = 1h`
- `time_span_hours`
- `entry_event_count_by_symbol`
- `entry_event_count_by_regime`
- `reject_counts_by_symbol`
- `liquidation_coverage_ratio`

- [ ] **Step 3: Run placeholder check**

Run:

```bash
cd /Users/tanshuai/Desktop/AI-test/crypto-alpha-lab
rg -n "TODO|TBD|待补|占位|PLAN_NEEDS_VALUE|UNRESOLVED" docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add reports/trend_regime/2026-05-27_historical_replay_dual_cost_summary.json docs/reviews/2026-05-27-trend-liquidation-historical-replay-review.md
git commit -m "docs: add trend historical replay review"
```

---

## 5. Review Gate

本轮 historical replay 修订完成后，review 必须回答：

- 是否仍存在 `api_stale` 主导 historical replay 的问题。
- 当前主 blocker 是否是 `vol_breakout_below_threshold`、`return_below_min`、`oi_confirmation_below_min`、`liquidation_not_confirmed` 中之一。
- `rows_missing_liquidation_notional_count` 是否过高，以至于 liquidation 路线结论暂不可用。
- `time_span_hours` 是否至少为 `720h`；若不足，只能得出 smoke replay 结论。
- 在 `30 bps` base cost 与 `50 bps` stress cost 下，是否满足现有 Phase 1A gate：
  - `signal_count >= 20`
  - `median_net_pnl_bps > 30`
  - `mean_net_pnl_bps > 40`
  - `win_rate > 55%`
  - stress cost `median_net_pnl_bps > 0`
  - `worst_trade_net_pnl_bps > -200`
  - `stop_loss_exit_rate < 35%`
- 是否至少有一个明确子类 `regime × direction × symbol_tier` 稳定通过，而不是只靠全局混合统计通过。

如果不满足，决策只能是：

- `keep_observation_only`
- 或 `redefine_thresholds_before_phase1b`

不得因为历史 replay 终于“能跑了”就直接进入 Phase 1B。

---

## 6. Done Definition

本计划完成后，必须同时满足：

- historical replay 不再被 `api_stale` 全量误拦截。
- live scanner 对 stale rows 的拒绝语义保持不变。
- replay summary 能直接回答“为什么没有 entry”。
- replay summary 能明确区分 liquidation coverage 完整与否。
- replay summary 能按 symbol / regime 解释 entry 与 reject 结构。
- expanded historical dataset 已经实际跑过一次 replay。
- review artifact 已落盘，且没有占位文本。
