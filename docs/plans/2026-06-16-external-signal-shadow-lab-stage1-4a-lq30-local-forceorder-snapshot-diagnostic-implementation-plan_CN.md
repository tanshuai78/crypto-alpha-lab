# External Signal Shadow Lab Stage 1.4A-LQ30 Local ForceOrder Snapshot Diagnostic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** 基于本地 `forceOrder` archive，实现一个只做 `15-30d` liquidation diagnostic 的 Stage 1.4A-LQ30 管线，用来判断这条本地清算快照代理线是否值得继续等待 `>=90d`、是否需要优先争取 vendor sample，以及当前本地 source quality 是否已经差到不值得继续等待。

**Architecture:** 复用现有 `stage1_4a_*` 体系里已经稳定的 funding/OI/price audit 能力，但不把 LQ30 塞进 `stage1_4a_orchestrator.py`。新增一套 `stage1_4a_lq30_*` 诊断模块，负责：

- local forceOrder JSONL / glob loader
- symbol normalization / nested schema parsing / duplicate quarantine
- UTC 固定桶聚合
- `data_alignment_overlap` 与 `stress_condition_overlap` 统计
- density / concentration / source quality / imbalance report
- 顶层 decision / review 输出

严格保持 `diagnostic-only` 边界：不做 forward return、不做 baseline、不做 replay alpha 解释。

**Tech Stack:** Python 3.11、标准库、`configs/base.py`、现有 `src/research/external_signal_shadow/stage1_4a_*` 模块、pytest、ruff、JSONL。

---

## 0. 执行前边界

本计划只实现：

```text
local forceOrder snapshot liquidation diagnostic
```

禁止实现：

```text
forward return
MFE / MAE
candidate replay
baseline comparison
alpha score
paper/live enablement
full composite pass
```

必须在 summary 顶层固定写出：

```json
{
  "liquidation_source_truth_level": "local_force_order_snapshot_rows_not_complete_tape",
  "complete_liquidation_tape_claim_allowed": false,
  "full_composite_claim_allowed": false,
  "alpha_interpretation_allowed": false,
  "paper_trading_allowed": false,
  "live_trading_allowed": false
}
```

补充说明：

- 这里的 `local_force_order_snapshot` 指 **本地采集到的 forceOrder snapshot row archive**。
- 它不是 complete liquidation tape，不得在 review 或 summary 中写成 `exact liquidation truth`。
- `archive 中没有事件` 不得直接解释为 `collector 掉线`；forceOrder 是稀疏事件流，没有清算时本来就没有消息。

---

## 1. 文件结构

### 新增文件

- `src/research/external_signal_shadow/stage1_4a_lq30_forceorder.py`
- `src/research/external_signal_shadow/stage1_4a_lq30_aggregation.py`
- `src/research/external_signal_shadow/stage1_4a_lq30_overlap.py`
- `src/research/external_signal_shadow/stage1_4a_lq30_summary.py`
- `scripts/external_signal_shadow/run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- `scripts/external_signal_shadow/review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- `tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py`
- `tests/research/external_signal_shadow/test_stage1_4a_lq30_forceorder.py`
- `tests/research/external_signal_shadow/test_stage1_4a_lq30_aggregation.py`
- `tests/research/external_signal_shadow/test_stage1_4a_lq30_overlap.py`
- `tests/research/external_signal_shadow/test_stage1_4a_lq30_summary.py`
- `tests/scripts/external_signal_shadow/test_run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- `tests/scripts/external_signal_shadow/test_review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- `tests/fixtures/external_signal_shadow/stage1_4a_lq30_forceorder_flat.jsonl`
- `tests/fixtures/external_signal_shadow/stage1_4a_lq30_forceorder_nested.jsonl`

### 修改文件

- `configs/base.py`
- `src/research/external_signal_shadow/stage1_4a_funding.py` 仅在必要时暴露 helper；否则不改
- `src/research/external_signal_shadow/stage1_4a_oi.py` 仅在必要时暴露 helper；否则不改
- `src/research/external_signal_shadow/stage1_4a_price.py` 仅在必要时暴露 helper；否则不改

### 设计原则

- 不把 LQ30 混入现有 `stage1_4a_orchestrator.py` full feasibility 分支。
- Loader、parser、aggregation、overlap、summary、review 各自独立，便于测试和隔离错误。
- 所有阈值进入 `configs/base.py`，禁止 `src/` 中散落 magic number。
- 所有验证命令统一使用 `PYTHONPATH=src:.`。
- 本计划不包含任何自动 `git commit`。每个任务后最多执行 `git status --short`，由用户决定是否提交。

---

## 2. Task 1: 配置常量、preview 阈值、顶层枚举

**Files:**
- Modify: `configs/base.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py`

### Step 1: 写失败测试

在 `tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py` 新增：

```python
from configs import base


def test_stage1_4a_lq30_threshold_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_HISTORY_DAYS == 15
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_SYMBOLS_WITH_EVENTS == 3
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_EVENT_DAYS == 10
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ALIGNMENT_OVERLAP_EVENT_DAYS == 10
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_SYMBOL_EVENT_SHARE == 0.60
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_DAY_EVENT_SHARE == 0.35
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_DAY_NOTIONAL_SHARE == 0.50
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP3_DAYS_NOTIONAL_SHARE == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_SYMBOL_NOTIONAL_SHARE == 0.70
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO == 0.001


def test_stage1_4a_lq30_bucket_and_alignment_constants_exist():
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_15M_MS == 900_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_1H_MS == 3_600_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_CONFIGURED_LAG_MS == 60_000
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_FUNDING_PUBLISH_LAG_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_OI_STALENESS_MS > 0
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_FUNDING_RATE_PREVIEW >= 0.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_OI_CHANGE_RATIO_PREVIEW >= 0.0
    assert base.EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_PRICE_RETURN_1H_PREVIEW >= 0.0
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py -q
```

### Step 3: 实现最小配置

在 `configs/base.py` 新增：

```python
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_HISTORY_DAYS = 15
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_SYMBOLS_WITH_EVENTS = 3
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ALIGNMENT_OVERLAP_EVENT_DAYS = 10
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_SYMBOL_EVENT_SHARE = 0.60
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_SINGLE_DAY_EVENT_SHARE = 0.35
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_DAY_NOTIONAL_SHARE = 0.50
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP3_DAYS_NOTIONAL_SHARE = 0.70
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_TOP1_SYMBOL_NOTIONAL_SHARE = 0.70
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_INVALID_JSON_LINE_RATIO = 0.001

EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_15M_MS = 15 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_LQ30_BUCKET_1H_MS = 60 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_LQ30_CONFIGURED_LAG_MS = 60_000
EXTERNAL_SIGNAL_STAGE1_4_LQ30_FUNDING_PUBLISH_LAG_MS = 5 * 60 * 1000
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MAX_OI_STALENESS_MS = 60 * 60 * 1000

EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_FUNDING_RATE_PREVIEW = 0.0
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_OI_CHANGE_RATIO_PREVIEW = 0.0
EXTERNAL_SIGNAL_STAGE1_4_LQ30_MIN_ABS_PRICE_RETURN_1H_PREVIEW = 0.0
```

说明：

- 第一版 preview 阈值设为 `0.0`，语义等于“字段存在即可”，但保留成 config，避免把 `stress_condition_overlap` 写成假独立条件。
- 如果后续要升级 preview 强度，只改配置，不改接口。

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 3. Task 2: real JSONL/glob loader、symbol normalization、schema parsing、去重

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4a_lq30_forceorder.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_lq30_forceorder.py`
- Fixtures: `tests/fixtures/external_signal_shadow/stage1_4a_lq30_forceorder_flat.jsonl`, `tests/fixtures/external_signal_shadow/stage1_4a_lq30_forceorder_nested.jsonl`

### Step 1: 写失败测试

至少覆盖：

- `load_forceorder_jsonl_files(paths_or_glob)` 支持 glob
- invalid JSON line 会 quarantine 并统计 ratio
- duplicate detection 生效
- symbol normalization 支持：`BTCUSDT` / `BTC/USDT` / `BTC/USDT:USDT`
- nested forceOrder timestamp 优先 `o.T`，回退 `E`
- `SELL = long_liquidation`，`BUY = short_liquidation`

示例测试：

```python
from research.external_signal_shadow.stage1_4a_lq30_forceorder import (
    load_forceorder_jsonl_files,
    normalize_derivatives_symbol,
    normalize_forceorder_row,
    parse_forceorder_rows,
)


def test_normalize_forceorder_symbol_handles_ccxt_symbol():
    assert normalize_derivatives_symbol("BTCUSDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("BTC/USDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("BTC/USDT:USDT") == "BTCUSDT"
    assert normalize_derivatives_symbol("btcusdt") == "BTCUSDT"


def test_nested_forceorder_uses_o_T_before_E():
    row = {
        "E": 1710000005000,
        "o": {
            "s": "ETHUSDT",
            "S": "BUY",
            "p": "3000",
            "q": "2",
            "T": 1710000001000,
        },
    }
    normalized = normalize_forceorder_row(row)
    assert normalized["timestamp_ms"] == 1710000001000
    assert normalized["liquidation_side"] == "short_liquidation"


def test_forceorder_jsonl_loader_counts_invalid_json_lines_and_dedupes(tmp_path):
    archive = tmp_path / "force_orders.jsonl"
    archive.write_text(
        '{"symbol":"BTCUSDT","side":"SELL","price":"65000","origQty":"0.1","time":1710000000000}\n'
        '{"symbol":"BTCUSDT","side":"SELL","price":"65000","origQty":"0.1","time":1710000000000}\n'
        'not-json\n',
        encoding="utf-8",
    )
    result = load_forceorder_jsonl_files([str(archive)])
    assert result["raw_line_count"] == 3
    assert result["invalid_json_line_count"] == 1
    assert result["duplicate_event_count"] == 1
    assert result["deduped_row_count"] == 1
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_forceorder.py -q
```

### Step 3: 实现 loader + parser

在 `stage1_4a_lq30_forceorder.py` 实现以下接口：

```python
load_forceorder_jsonl_files(paths_or_glob) -> dict
normalize_derivatives_symbol(symbol: str | None) -> str | None
normalize_forceorder_row(row: dict[str, Any]) -> dict[str, Any] | None
parse_forceorder_rows(rows: list[dict[str, Any]], expected_symbols: set[str]) -> dict[str, Any]
```

强制要求：

1. **loader 真实读取 JSONL / glob**
   - 输出：

```json
{
  "raw_line_count": 0,
  "invalid_json_line_count": 0,
  "invalid_json_line_ratio": 0.0,
  "duplicate_event_count": 0,
  "deduped_row_count": 0,
  "loaded_rows": [],
  "quarantined_invalid_lines": []
}
```

2. **schema 支持范围**
   - flat:
     - `symbol, side, price, origQty, time`
     - `symbol, side, price, qty, timestamp`
   - nested Binance forceOrder:
     - `o.s / o.S / o.p / o.q / o.T`
     - timestamp 优先级：`o.T` > `E` > `time/timestamp`

3. **symbol normalization**
   - 最小支持：
     - `BTCUSDT`
     - `BTC/USDT`
     - `BTC/USDT:USDT`
   - 限定 universe：
     - `BTCUSDT / ETHUSDT / SOLUSDT / XRPUSDT / DOGEUSDT`

4. **side mapping**
   - `SELL = long_liquidation`
   - `BUY = short_liquidation`

5. **notional 语义**
   - `notional_usd = price * quantity`
   - `notional_conversion_quality = estimated_from_price_qty`
   - `notional_is_lower_bound = True`

6. **duplicate key**
   - `symbol + side + price + quantity + timestamp_ms`
   - 聚合只使用 deduped rows

7. **统计输出**
   - `parsed_row_count`
   - `unknown_schema_count`
   - `missing_required_field_count`
   - `parse_error_count`
   - `duplicate_event_count`
   - `deduped_row_count`

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_forceorder.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 4. Task 3: UTC 15m/1h 聚合、density、event/notional concentration、imbalance distribution

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4a_lq30_aggregation.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_lq30_aggregation.py`

### Step 1: 写失败测试

至少覆盖：

- `15m bucket = floor(timestamp_ms / 15m) * 15m`
- `1h bucket = floor(timestamp_ms / 1h) * 1h`
- `available_at_ms = bucket_end_ms + configured_lag_ms`
- concentration 不只看 window count，还要看 event count 和 notional
- imbalance distribution 输出 long/short notional 与 ratio

示例测试：

```python
from research.external_signal_shadow.stage1_4a_lq30_aggregation import (
    aggregate_forceorder_windows,
    build_density_report,
    build_imbalance_distribution,
    compute_concentration_stats,
)


def test_aggregate_forceorder_windows_uses_fixed_utc_floor_buckets():
    rows = [
        {
            "symbol": "BTCUSDT",
            "liquidation_side": "long_liquidation",
            "notional_usd": 1000.0,
            "timestamp_ms": 900_001,
        }
    ]
    result = aggregate_forceorder_windows(rows, bucket_ms=900_000, configured_lag_ms=60_000)
    assert result[0]["bucket_start_ms"] == 900_000
    assert result[0]["bucket_end_ms"] == 1_800_000
    assert result[0]["available_at_ms"] == 1_860_000


def test_concentration_uses_event_count_not_only_window_count():
    windows = [
        {"symbol": "BTCUSDT", "day_key": "2026-06-01", "event_count": 100, "total_liquidation_notional_usd": 1000.0},
        {"symbol": "ETHUSDT", "day_key": "2026-06-02", "event_count": 1, "total_liquidation_notional_usd": 50.0},
    ]
    stats = compute_concentration_stats(windows)
    assert stats["event_count_concentration"]["top_1_day_event_share"] > 0.9
    assert stats["notional_concentration"]["top_1_day_notional_share"] > 0.9
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_aggregation.py -q
```

### Step 3: 实现聚合与 builder

在 `stage1_4a_lq30_aggregation.py` 实现：

```python
aggregate_forceorder_windows(rows, *, bucket_ms: int, configured_lag_ms: int) -> list[dict]
compute_concentration_stats(windows: list[dict]) -> dict
build_density_report(parsed_rows: list[dict], windows_15m: list[dict]) -> dict
build_imbalance_distribution(windows_15m: list[dict], windows_1h: list[dict]) -> dict
build_source_quality_report(...) -> dict  # 可放在 summary.py，二选一，但必须真实实现
```

强制要求：

1. `event_count` 使用原始 deduped event 数，不得用 `len(windows)` 冒充事件数。
2. concentration 至少输出三层：

```json
{
  "window_concentration": {},
  "event_count_concentration": {},
  "notional_concentration": {}
}
```

3. density report 至少包含：

```json
{
  "raw_history_days": 0.0,
  "liquidation_history_days": 0.0,
  "symbols_with_events": 0,
  "event_days": 0,
  "max_single_symbol_event_share": 0.0,
  "max_single_day_event_share": 0.0,
  "top_1_day_notional_share": 0.0,
  "top_3_days_notional_share": 0.0,
  "top_1_symbol_notional_share": 0.0
}
```

4. imbalance distribution 至少包含：

```json
{
  "long_short_imbalance_distribution_15m": {},
  "long_short_imbalance_distribution_1h": {},
  "long_liquidation_notional_total": 0.0,
  "short_liquidation_notional_total": 0.0
}
```

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_aggregation.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 5. Task 4: as-of alignment overlap 与 stress-condition overlap

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4a_lq30_overlap.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_lq30_overlap.py`

### Step 1: 明确接口策略

本计划选择 **方案 A**：`compute_overlap_reports(...)` 直接接受现有 `stage1_4a_funding.py / stage1_4a_oi.py / stage1_4a_price.py` 的**原始字段名**，函数内部完成 key / timestamp 规范化与 as-of 对齐。

原因：

- 现有模块真实字段并不统一：
  - funding: `fundingTime`, `fundingRate`
  - OI: `timestamp`, `sumOpenInterest`, 可额外计算 `oi_change_ratio`
  - price: `open_time` / `timestamp` / `bar_start_ms`
- 如果把规范化责任全丢给 runner，LQ30 很容易出现“runner 改名不完整 -> overlap 全 0”的假阴性。
- overlap 模块自己做 raw-field normalization，测试也必须使用现有 raw 风格字段。

### Step 2: 写失败测试

至少覆盖：

- funding 使用 `fundingTime` + publish lag 的 as-of 对齐，不做 exact 15m bucket match
- OI 使用 latest `timestamp <= bucket_end_ms` 且 age <= staleness 的 as-of 对齐
- price 使用 exact covering bucket
- 未传 funding/OI/price 时，要明确 `alignment_unavailable`
- `stress_condition_overlap` 与 `data_alignment_overlap` 分离

示例测试：

```python
from research.external_signal_shadow.stage1_4a_lq30_overlap import compute_overlap_reports


def test_overlap_uses_funding_asof_not_exact_bucket_match():
    liq_windows = [{"symbol": "BTCUSDT", "bucket_start_ms": 900_000, "bucket_end_ms": 1_800_000, "day_key": "2026-06-01"}]
    funding_rows = [{"symbol": "BTCUSDT", "fundingTime": 0, "fundingRate": "0.0005"}]
    oi_rows = [{"symbol": "BTCUSDT", "timestamp": 1_500_000, "sumOpenInterest": "100", "sumOpenInterestValue": "1000", "oi_change_ratio": -0.02}]
    price_rows = [{"symbol": "BTCUSDT", "bar_start_ms": 900_000, "close_price": 65000, "abs_return_1h": 0.015}]

    report = compute_overlap_reports(
        liq_windows,
        funding_rows,
        oi_rows,
        price_rows,
        funding_publish_lag_ms=300_000,
        max_oi_staleness_ms=3_600_000,
        min_abs_funding_rate_preview=0.0,
        min_abs_oi_change_ratio_preview=0.0,
        min_abs_price_return_1h_preview=0.0,
    )
    assert report["data_alignment_overlap_window_count_15m"] == 1
    assert report["stress_condition_overlap_window_count_15m"] == 1


def test_runner_without_alignment_inputs_marks_alignment_unavailable():
    report = compute_overlap_reports([], None, None, None, 300_000, 3_600_000, 0.0, 0.0, 0.0)
    assert report["alignment_overlap_available"] is False
```

### Step 3: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_overlap.py -q
```

### Step 4: 实现 overlap

在 `stage1_4a_lq30_overlap.py` 实现：

```python
compute_overlap_reports(
    liq_windows,
    funding_rows,
    oi_rows,
    price_rows,
    funding_publish_lag_ms,
    max_oi_staleness_ms,
    min_abs_funding_rate_preview,
    min_abs_oi_change_ratio_preview,
    min_abs_price_return_1h_preview,
) -> dict
```

强制要求：

1. **funding as-of policy**
   - `latest fundingTime <= bucket_end_ms - funding_publish_lag_ms`

2. **OI as-of policy**
   - `latest timestamp <= bucket_end_ms`
   - `bucket_end_ms - timestamp <= max_oi_staleness_ms`

3. **price policy**
   - exact 15m bucket or covering row
   - 接受原始字段：`open_time` / `timestamp` / `bar_start_ms`

4. **alignment vs stress 分离**
   - `data_alignment_overlap`: 只是能找到 funding/OI/price 输入
   - `stress_condition_overlap`: 在 alignment 通过后，再检查 preview 条件
   - 第一版 preview 阈值来自 config；默认 `0.0`，语义是“字段存在即可”，但实现上必须保留独立判断，不能 `stress_count += 1` 直接等于 `alignment_count`

5. **输出必须含 alignment policy**

```json
{
  "alignment_overlap_available": true,
  "alignment_policy": {
    "funding": "asof_latest_before_bucket_end_minus_lag",
    "oi": "asof_latest_before_bucket_end_with_staleness_limit",
    "price": "bucket_exact_or_covering"
  }
}
```

### Step 5: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_overlap.py -q
```

### Step 6: 检查工作区

```bash
git status --short
```

---

## 6. Task 5: source quality report 与顶层 decision engine

**Files:**
- Create: `src/research/external_signal_shadow/stage1_4a_lq30_summary.py`
- Test: `tests/research/external_signal_shadow/test_stage1_4a_lq30_summary.py`

### Step 1: 写失败测试

至少覆盖：

- `promising / weak / unusable` 三个 decision
- `source_quality_report` 真实字段
- `invalid_json_line_ratio` gate
- `collector_gap_verifiable = false` 时不得把 archive silence 写成 collector down

示例测试：

```python
from research.external_signal_shadow.stage1_4a_lq30_summary import (
    build_source_quality_report,
    evaluate_lq30_summary,
)


def test_lq30_summary_returns_promising_when_all_gates_pass():
    summary = evaluate_lq30_summary(
        density_report={
            "liquidation_history_days": 20,
            "symbols_with_events": 4,
            "event_days": 15,
            "max_single_symbol_event_share": 0.4,
            "max_single_day_event_share": 0.2,
        },
        overlap_report={"alignment_overlap_available": True, "data_alignment_overlap_event_days": 12},
        concentration_report={
            "notional_concentration": {
                "top_1_day_notional_share": 0.3,
                "top_3_days_notional_share": 0.5,
                "top_1_symbol_notional_share": 0.4,
            }
        },
        source_quality_report={
            "invalid_json_line_ratio": 0.0,
            "collector_gap_verifiable": False,
            "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime",
        },
    )
    assert summary["decision"] == "liquidation_diagnostic_promising"


def test_lq30_summary_returns_unusable_when_history_and_overlap_fail():
    summary = evaluate_lq30_summary(
        density_report={
            "liquidation_history_days": 7,
            "symbols_with_events": 1,
            "event_days": 3,
            "max_single_symbol_event_share": 1.0,
            "max_single_day_event_share": 1.0,
        },
        overlap_report={"alignment_overlap_available": True, "data_alignment_overlap_event_days": 2},
        concentration_report={
            "notional_concentration": {
                "top_1_day_notional_share": 0.95,
                "top_3_days_notional_share": 0.95,
                "top_1_symbol_notional_share": 0.95,
            }
        },
        source_quality_report={
            "invalid_json_line_ratio": 0.0,
            "collector_gap_verifiable": False,
            "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime",
        },
    )
    assert summary["decision"] == "liquidation_diagnostic_unusable"
```

### Step 2: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_summary.py -q
```

### Step 3: 实现 builder 与 decision

在 `stage1_4a_lq30_summary.py` 实现：

```python
build_source_quality_report(...) -> dict
evaluate_lq30_summary(*, density_report, overlap_report, concentration_report, source_quality_report) -> dict
```

source quality report 至少包含：

```json
{
  "raw_row_count": 0,
  "raw_history_days": 0.0,
  "raw_recent_event_count_24h": 0,
  "duplicate_event_count": 0,
  "invalid_json_line_count": 0,
  "invalid_json_line_ratio": 0.0,
  "missing_timestamp_count": 0,
  "expected_symbol_coverage": 5,
  "actual_symbol_coverage": 0,
  "rotation_fragment_count": 0,
  "collector_gap_verifiable": false,
  "archive_gap_observations": "event_sparse_stream_cannot_prove_uptime"
}
```

Decision 规则：

- `liquidation_diagnostic_promising`
  - history/density/alignment/concentration/source quality 全过
- `liquidation_diagnostic_weak`
  - 有有效 local history，但不够支持继续等 90d
- `liquidation_diagnostic_unusable`
  - 解析质量、history、density 或 concentration 明显失格

`next_action` 固定枚举：

- `continue_accumulating_exact_history`
- `continue_accumulating_but_do_not_wait_for_90d`
- `prioritize_vendor_sample`
- `stop_waiting_for_90d_until_source_quality_or_density_improves`

说明：

- `prioritize_vendor_sample` 用于：本地 source quality 或事件密度长期不足，但 alignment 输入已经齐备。
- `collector_gap_verifiable = false` 时，不得把 event silence 写成 collector outage。

### Step 4: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest tests/research/external_signal_shadow/test_stage1_4a_lq30_summary.py -q
```

### Step 5: 检查工作区

```bash
git status --short
```

---

## 7. Task 6: CLI runner 与中文 review 脚本

**Files:**
- Create: `scripts/external_signal_shadow/run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- Create: `scripts/external_signal_shadow/review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- Test: `tests/scripts/external_signal_shadow/test_run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`
- Test: `tests/scripts/external_signal_shadow/test_review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py`

### Step 1: 定义 CLI 两种模式

第一版 runner 明确两种模式：

```text
mode A: liquidation_only_density
  只传 --local-force-order-archive
  输出 density / concentration / source quality / imbalance
  overlap report 标记 alignment unavailable

mode B: liquidation_with_alignment_inputs
  传 --funding-archive --oi-archive --price-archive
  输出 overlap report
```

CLI 参数必须包含：

```text
--local-force-order-archive PATH_OR_GLOB
--funding-archive PATH_OR_GLOB   (optional)
--oi-archive PATH_OR_GLOB        (optional)
--price-archive PATH_OR_GLOB     (optional)
--output-summary PATH
```

### Step 2: 写失败测试

至少覆盖：

- 仅 forceOrder 输入时，`alignment_overlap_available = false`
- 带 alignment 输入时，能计算 overlap
- 单条样本 runner 输出必须是 `liquidation_diagnostic_unusable`
- review 必须列出 source quality report 与 diagnostic-only 边界

示例测试：

```python
import json

from scripts.external_signal_shadow.run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic import main


def test_lq30_runner_without_alignment_inputs_marks_alignment_unavailable(tmp_path):
    archive = tmp_path / "force_orders.jsonl"
    archive.write_text(
        json.dumps({
            "symbol": "BTCUSDT",
            "side": "SELL",
            "price": "65000",
            "origQty": "0.1",
            "time": 1710000000000,
        }) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "summary.json"
    rc = main([
        "--local-force-order-archive", str(archive),
        "--output-summary", str(output),
    ])
    assert rc == 0
    summary = json.loads(output.read_text(encoding="utf-8"))
    assert summary["decision"] == "liquidation_diagnostic_unusable"
    assert summary["overlap_report"]["alignment_overlap_available"] is False


def test_lq30_runner_with_alignment_inputs_computes_overlap(tmp_path):
    # 写 forceOrder + funding + oi + price 最小 fixture，然后断言 overlap > 0
    ...
```

### Step 3: 跑测试确认失败

```bash
PYTHONPATH=src:. uv run pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py -q
```

### Step 4: 实现 runner 与 review

Runner 责任：

- 读取 `--local-force-order-archive`
- 调 `load_forceorder_jsonl_files()`
- 解析 / 去重 / 聚合 `15m` 与 `1h`
- 构建 density / concentration / imbalance / source quality report
- 如果传了 funding/OI/price input，则读入并跑 overlap；否则标记 `alignment_overlap_available = false`
- 组装 summary JSON

Review 责任：

- 读取 summary
- 输出中文 review
- 必须明确写出：
  - `local_force_order_snapshot_rows_not_complete_tape`
  - `complete_liquidation_tape_claim_allowed = false`
  - `diagnostic-only`
  - `SELL = long liquidation`, `BUY = short liquidation`
  - `notional = price * quantity` 为 lower-bound estimate
  - `source_quality_report`
  - `alignment_policy`

### Step 5: 跑测试确认通过

```bash
PYTHONPATH=src:. uv run pytest \
  tests/scripts/external_signal_shadow/test_run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py -q
```

### Step 6: 检查工作区

```bash
git status --short
```

---

## 8. Task 7: focused verification 与 fixture smoke artifact

### Step 1: 跑 LQ30 focused tests

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_config.py \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_forceorder.py \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_aggregation.py \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_overlap.py \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_summary.py \
  tests/scripts/external_signal_shadow/test_run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  tests/scripts/external_signal_shadow/test_review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py -q
```

### Step 2: 跑 external signal 相关回归

```bash
PYTHONPATH=src:. uv run pytest \
  tests/research/external_signal_shadow/test_stage1_4a_*.py \
  tests/research/external_signal_shadow/test_stage1_4a2_vendor_*.py -q
```

### Step 3: 跑 ruff

```bash
PYTHONPATH=src:. uv run ruff check \
  configs/base.py \
  src/research/external_signal_shadow/stage1_4a_lq30_forceorder.py \
  src/research/external_signal_shadow/stage1_4a_lq30_aggregation.py \
  src/research/external_signal_shadow/stage1_4a_lq30_overlap.py \
  src/research/external_signal_shadow/stage1_4a_lq30_summary.py \
  scripts/external_signal_shadow/run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  scripts/external_signal_shadow/review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  tests/research/external_signal_shadow/test_stage1_4a_lq30_*.py \
  tests/scripts/external_signal_shadow/test_*lq30*.py
```

### Step 4: 生成 fixture smoke artifact

只用内置 fixture 跑一次：

```bash
PYTHONPATH=src:. uv run python scripts/external_signal_shadow/run_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  --local-force-order-archive tests/fixtures/external_signal_shadow/stage1_4a_lq30_forceorder_flat.jsonl \
  --output-summary reports/external_signal_shadow/stage1_4a_lq30_local_forceorder_snapshot_diagnostic_summary.json

PYTHONPATH=src:. uv run python scripts/external_signal_shadow/review_stage1_4a_lq30_local_forceorder_snapshot_diagnostic.py \
  --summary reports/external_signal_shadow/stage1_4a_lq30_local_forceorder_snapshot_diagnostic_summary.json \
  --output-review docs/reviews/2026-06-16-external-signal-shadow-lab-stage1-4a-lq30-local-forceorder-snapshot-diagnostic-review_CN.md
```

要求：

- 这组 artifact 必须在 review 顶部明确标注：`fixture smoke only`，不能推出 research-grade 结论。
- 如果只传 forceOrder、没有 funding/OI/price，则 review 里必须明确：`alignment unavailable in this run`。

### Step 5: 检查工作区

```bash
git status --short
```

---

## 9. 完成定义

只有同时满足以下条件，才能宣称 Stage 1.4A-LQ30 implementation complete：

```text
1. 所有 LQ30 阈值、preview 阈值、alignment lag/staleness 常量已进入 configs/base.py
2. real JSONL/glob loader 已实现，invalid lines 有 quarantine，duplicate events 有统计与去重
3. symbol normalization 支持 BTCUSDT / BTC/USDT / BTC/USDT:USDT
4. nested forceOrder timestamp 优先 o.T，回退 E
5. SELL / BUY -> long / short liquidation 映射被测试覆盖
6. notional 估算明确标记为 estimated_from_price_qty lower bound
7. 15m / 1h UTC 固定桶聚合已实现
8. data_alignment_overlap 与 stress_condition_overlap 已通过 as-of 策略真正分离
9. source_quality_report / density_report / imbalance_distribution / concentration_report 都是真实现，不是 stub
10. CLI 支持 liquidation-only 与 liquidation+alignment-inputs 两种模式
11. 顶层 summary 只输出 diagnostic 结论，不输出 alpha / paper / live
12. focused tests、external signal 回归、ruff 全通过
```

---

## 10. 执行后允许的解释

执行完这份计划后，允许的解释只有：

```text
LQ30 local forceOrder snapshot 这条腿是否值得继续等 90d
LQ30 local forceOrder snapshot 这条腿与 funding/OI/price 是否具备最小对齐条件
当前 source quality 是否已经差到不值得继续等待
是否应该优先争取 vendor sample，而不是继续盲等本地历史累积
```

禁止的解释仍然是：

```text
liquidation 有 alpha
composite 已通过
paper/live 可以进入
已经足够替代 vendor sample
```
